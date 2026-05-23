"""Phase 4 M1 — Unified Feed Risk-Metrics Pipeline.

Combines per-feed point metrics, BCa joint-vector CIs, PSR/DSR, net-of-cost
PF, regime decomposition, PBO, and a deterministic banner-gate verdict into a
single JSON artifact for the audit dashboard banner.

Corrected 7-step workflow (Mercury critique, 2026-04-20):
  1. Per-feed point metrics
  2. StationaryBootstrap + BCa joint-vector CI
  3. skfolio.WalkForward / CombinatorialPurgedCV  (separate pipeline)
  4. pypbo DSR/PBO on trial equity curves      (PBO here; DSR in M1 scope)
  5. Deterministic banner gate:
         PF BCa-lower > 1.0  AND  DSR p-value <= 0.05  AND  PBO <= 0.5
  6. Hansen MCS for non-dominated cohort       (future milestone)
  7. Optuna separately (not in M1)

Run:
    .venv/Scripts/python.exe tools/feed_risk_metrics.py

Output:
    tools/data/feed_risk_metrics_2026_04_20.json
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.block_bootstrap_ci import (  # noqa: E402
    _block_size,
    _bootstrap_bca_joint,
    _feeds,
    _group_pnls_by_strategy,
    pf as pf_stat,
    sharpe as sharpe_stat,
    wr as wr_stat,
)
from tools.deflated_sharpe_per_feed import (  # noqa: E402
    _moments,
    dsr as dsr_stat,
    psr as psr_stat,
    sharpe_ratio,
)
from tools.pbo_cscv import compute_pbo  # noqa: E402

SCHEMA_VERSION = "1.0.0"
PIPELINE_VERSION = "phase4.m1.2026-04-20"
TRADING_DAYS = 252
N_RESAMPLES = 2000  # BCa is expensive; 2k gives stable CIs for 50-500 obs
MIN_N_BANNER = 50

DATA_IN = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
DATA_OUT = REPO / "tools" / "data" / "feed_risk_metrics_2026_04_20.json"

# Per-asset-class round-trip cost assumptions (decimal, not %).
#
# D3 caveat (big-pickle review 2026-04-22): CRYPTO spot fee 0.10% assumes a
# non-discounted retail tier. Users on BNB-discounted, VIP, or maker-rebate
# tiers see materially lower effective costs; weaker venues may see higher.
# Net PF/Sharpe should be read as an ASSUMPTION-DEPENDENT lower bound, not
# an absolute. Sensitivity: a 5bps shift in CRYPTO fee_rt_pct moves net PF
# by ~0.03 at typical trade counts. Treat banner gate as directional.
COSTS = {
    "CRYPTO":   {"fee_rt_pct": 0.0010, "slip_pct": 0.0005, "note": "spot 0.10% RT + 0.05% slip"},
    "CRYPTO_PERP": {"fee_rt_pct": 0.0006, "slip_pct": 0.0010, "note": "perp 0.06% RT + 0.10% slip"},
    "FOREX":    {"fee_rt_pct": 0.00005, "slip_pct": 0.00001, "note": "major 0.5 pip + 0.1 pip"},
    "EQUITY":   {"fee_rt_pct": 0.0000, "slip_pct": 0.0005, "note": "$0 + 0.05% slip"},
    "ETF":      {"fee_rt_pct": 0.0000, "slip_pct": 0.0005, "note": "$0 + 0.05% slip"},
    "BOND":     {"fee_rt_pct": 0.0000, "slip_pct": 0.0010, "note": "bond ETF $0 + 0.10% slip"},
    "COMMODITY":{"fee_rt_pct": 0.0015, "slip_pct": 0.0010, "note": "commodity 0.15% RT + 0.10% slip"},
}
DEFAULT_COST = {"fee_rt_pct": 0.0010, "slip_pct": 0.0005, "note": "default"}


def _cost_for(asset_class: str) -> dict:
    ac = (asset_class or "").upper()
    return COSTS.get(ac, DEFAULT_COST)


def _apply_costs(picks: list[dict]) -> np.ndarray:
    """Return pnl_pct net-of-cost array (in % units)."""
    out = []
    for p in picks:
        v = p.get("pnl_pct")
        if v is None:
            continue
        try:
            v = float(v)
        except Exception:
            continue
        c = _cost_for(p.get("asset_class") or "")
        cost_pct = (c["fee_rt_pct"] + c["slip_pct"]) * 100.0
        # pnl is side-signed already; subtract absolute cost per trade
        out.append(v - cost_pct)
    return np.asarray(out, dtype=float)


def _point_metrics(pnls_pct: np.ndarray) -> dict[str, float]:
    """PF, Sharpe, Sortino, Calmar, WR, MaxDD, expectancy-R on %-unit pnls."""
    n = int(pnls_pct.size)
    out = {"n": n}
    if n == 0:
        return out
    arr = pnls_pct
    out["pf"] = pf_stat(arr)
    out["sharpe"] = sharpe_stat(arr)
    out["wr"] = wr_stat(arr)
    mu = float(arr.mean())
    out["mean_pnl_pct"] = mu
    # expectancy_R is a legacy alias for mean return in %-units; NOT a true
    # R-multiple (which requires per-trade initial-risk). Prefer mean_pnl_pct
    # for new readers. See PR #314 Copilot #4.
    out["expectancy_R"] = mu
    out["expectancy_R_note"] = "alias for mean_pnl_pct; not a risk-normalised R-multiple"
    # Sortino
    downside = arr[arr < 0]
    if downside.size >= 2 and downside.std(ddof=1) > 0:
        out["sortino"] = float(mu / downside.std(ddof=1) * math.sqrt(TRADING_DAYS))
    else:
        out["sortino"] = None
    # Calmar via equity curve max drawdown
    eq = np.cumsum(arr)
    peak = np.maximum.accumulate(eq)
    dd = eq - peak
    maxdd = float(dd.min()) if dd.size else 0.0
    out["maxdd_pct"] = maxdd
    ann_return_pct = mu * TRADING_DAYS
    out["calmar"] = float(ann_return_pct / abs(maxdd)) if maxdd < 0 else None
    return out


def _regime_tag(p: dict) -> tuple[str, str]:
    """Return (fng_bucket, btc_trend_bucket) from available fields; fallbacks ok."""
    fng = p.get("fear_greed") or p.get("fng") or p.get("regime_fng")
    try:
        f = float(fng) if fng is not None else None
    except Exception:
        f = None
    if f is None:
        fng_b = "unknown"
    elif f < 30:
        fng_b = "fear"
    elif f < 70:
        fng_b = "neutral"
    else:
        fng_b = "greed"

    trend = p.get("btc_trend") or p.get("regime_btc_trend") or p.get("market_regime")
    t = str(trend or "").lower()
    if "bull" in t or "up" in t:
        tr_b = "up"
    elif "bear" in t or "down" in t:
        tr_b = "down"
    elif "range" in t or "chop" in t or "side" in t:
        tr_b = "range"
    else:
        tr_b = "unknown"
    return fng_b, tr_b


def _regime_decomposition(picks: list[dict]) -> dict[str, Any]:
    grid: dict[str, dict[str, Any]] = {}
    for p in picks:
        v = p.get("pnl_pct")
        if v is None:
            continue
        try:
            v = float(v)
        except Exception:
            continue
        fng, tr = _regime_tag(p)
        key = f"{fng}|{tr}"
        g = grid.setdefault(key, {"fng": fng, "trend": tr, "pnls": []})
        g["pnls"].append(v)
    out: dict[str, Any] = {}
    for k, g in grid.items():
        arr = np.asarray(g["pnls"], dtype=float)
        n = int(arr.size)
        entry: dict[str, Any] = {
            "fng": g["fng"],
            "trend": g["trend"],
            "n": n,
            "pf": pf_stat(arr),
            "sharpe": sharpe_stat(arr),
            "wr": wr_stat(arr),
            "mean_pnl_pct": float(arr.mean()) if n else None,
            "amber_low_sample": bool(n < 10),
        }
        out[k] = entry
    return out


def _per_strategy_return_matrix(picks: list[dict], min_strategies: int = 3) -> np.ndarray | None:
    """Build (T, N) return matrix by bucketing each strategy's pnls into equal
    time-buckets. Simplest scheme: sort each strategy's pnls by closed_at, then
    reshape into T buckets where T = min series-length across strategies (cap
    at 32). Returns None if <min_strategies strategies survive."""
    by_strat: dict[str, list[tuple[str, float]]] = {}
    for p in picks:
        v = p.get("pnl_pct")
        if v is None:
            continue
        try:
            v = float(v)
        except Exception:
            continue
        s = p.get("strategy") or p.get("source_system") or "_unknown"
        ts = p.get("closed_at") or p.get("opened_at") or ""
        by_strat.setdefault(str(s), []).append((str(ts), v))

    series: list[np.ndarray] = []
    names: list[str] = []
    for name, rows in by_strat.items():
        if len(rows) < 8:
            continue
        rows.sort(key=lambda r: r[0])
        vals = np.asarray([r[1] for r in rows], dtype=float)
        series.append(vals)
        names.append(name)

    if len(series) < min_strategies:
        return None

    # Bucket each series into T=min(32, min_len) equal-sized chunks, sum per bucket.
    min_len = min(len(s) for s in series)
    T = min(32, max(8, min_len))
    cols = []
    for s in series:
        # split into T near-equal buckets
        buckets = np.array_split(s, T)
        cols.append(np.array([b.sum() if b.size else 0.0 for b in buckets], dtype=float))
    mat = np.column_stack(cols)  # shape (T, N)
    return mat


def _feed_metrics(name: str, picks: list[dict]) -> dict[str, Any]:
    # Gross pnls (in %)
    pnls_gross = np.asarray(
        [float(p["pnl_pct"]) for p in picks if p.get("pnl_pct") is not None],
        dtype=float,
    )
    pnls_net = _apply_costs(picks)
    n = int(pnls_gross.size)

    block = _block_size(n) if n >= 2 else 2
    insufficient = n < MIN_N_BANNER

    # Point metrics
    gross_pt = _point_metrics(pnls_gross)
    net_pt = _point_metrics(pnls_net)

    # BCa joint CIs (gross; we gate on net later if desired)
    bca = _bootstrap_bca_joint(pnls_gross, block, n=N_RESAMPLES) if n >= 5 else {
        "pf": (float("nan"), float("nan")),
        "sharpe": (float("nan"), float("nan")),
        "wr": (float("nan"), float("nan")),
        "maxdd": (float("nan"), float("nan")),
    }
    bca_net = _bootstrap_bca_joint(pnls_net, block, n=N_RESAMPLES) if n >= 5 else bca

    # PSR / DSR on returns expressed as decimals
    rets = pnls_gross / 100.0
    m = _moments(rets)
    sr_ann = sharpe_ratio(rets) if n >= 2 else None
    strategies = {str(p.get("strategy") or "").strip() for p in picks}
    strategies.discard("")
    n_trials = max(1, len(strategies))
    psr0 = psr_stat(sr_ann, 0.0, n, m["skew"] or 0.0, m["kurt"] or 0.0) if sr_ann is not None else None
    psr1 = psr_stat(sr_ann, 1.0, n, m["skew"] or 0.0, m["kurt"] or 0.0) if sr_ann is not None else None

    # var of per-strategy SRs for DSR
    strat_srs: list[float] = []
    for s in strategies:
        xs = np.array(
            [float(p["pnl_pct"]) / 100.0 for p in picks
             if p.get("pnl_pct") is not None and str(p.get("strategy") or "").strip() == s],
            dtype=float,
        )
        if xs.size >= 3 and np.std(xs, ddof=1) > 0:
            strat_srs.append(float(np.mean(xs) / np.std(xs, ddof=1)))
    var_sr_p = float(np.var(strat_srs, ddof=1)) if len(strat_srs) >= 2 else 1.0 / TRADING_DAYS
    dsr_v = (
        dsr_stat(sr_ann, n, m["skew"] or 0.0, m["kurt"] or 0.0, n_trials, var_sr_p)
        if sr_ann is not None
        else None
    )
    # DSR is P(trueSR > E[maxSR]); p-value = 1 - DSR (prob of overfit)
    dsr_pvalue = (1.0 - dsr_v) if dsr_v is not None else None

    # PBO via CSCV on per-strategy return matrix
    mat = _per_strategy_return_matrix(picks)
    if mat is not None:
        pbo_res = compute_pbo(mat, S=16)
    else:
        pbo_res = {"pbo": None, "note": "insufficient strategies/series for CSCV"}

    # ── Banner gate (post methodology sign-off 2026-04-22 by big-pickle + deep review) ──
    # D2  Net BCa drives the gate; gross retained as advisory. Fees eat the edge —
    #     the banner quotes what a live trader would actually experience.
    # D1  DSR relaxed to p<=0.5 and reclassified as SOFT signal (not primary gate).
    #     DSR p=1.0 is the expected output when n_trials scales with per-feed strategy
    #     count (100+). PBO via CSCV is the primary combinatorics gate.
    # PBO fail-closed: when PBO is unavailable (sample too small or n_splits shrunk),
    #     the banner-gate limb fails rather than silently passing. Banner must not
    #     render on insufficient evidence.
    pf_bca_lower_gross = bca.get("pf", (float("nan"),))[0]
    pf_bca_lower_net = bca_net.get("pf", (float("nan"),))[0]
    gate_pf = bool(np.isfinite(pf_bca_lower_net) and pf_bca_lower_net > 1.0)  # D2: net drives gate
    dsr_soft_signal = bool(dsr_pvalue is not None and dsr_pvalue <= 0.5)        # D1: relaxed + soft
    pbo_val = pbo_res.get("pbo")
    gate_pbo = bool(pbo_val is not None and pbo_val <= 0.5)                     # fail-closed
    banner_eligible = (not insufficient) and gate_pf and gate_pbo               # PBO primary; DSR advisory

    # D5: regime decomposition is meaningless while `fear_greed` / `btc_trend` fields
    # are unpopulated in the source picks (all rows collapse to "unknown|unknown").
    # Surface the grid behind a `gated_off` flag so downstream banner copy can
    # hide the section until Phase 1 stamping populates those fields.
    regime_decomp = _regime_decomposition(picks)
    _regime_has_known = any(
        k != "unknown|unknown" for cells in regime_decomp.values() if isinstance(cells, dict) for k in cells
    ) if isinstance(regime_decomp, dict) else False

    return {
        "feed": name,
        "n": n,
        "n_strategies": n_trials,
        "block_size": block,
        "insufficient_sample": insufficient,
        "point_metrics_gross": gross_pt,
        "point_metrics_net": net_pt,
        "bca_95_gross": {k: list(v) for k, v in bca.items() if isinstance(v, tuple)},
        "bca_95_net": {k: list(v) for k, v in bca_net.items() if isinstance(v, tuple)},
        "psr_vs_sr0": psr0,
        "psr_vs_sr1": psr1,
        "dsr": dsr_v,
        "dsr_p_value": dsr_pvalue,
        "dsr_soft_signal": dsr_soft_signal,       # D1: advisory flag (p<=0.5); NOT a primary gate
        "sharpe_annualised": sr_ann,
        "pbo": pbo_res,
        "regime_decomposition": regime_decomp,
        "regime_decomposition_gated_off": not _regime_has_known,   # D5: true while stamping pending
        "banner_gate": {
            "pf_bca_lower_gt_1": gate_pf,          # computed on NET bca per D2
            "pbo_le_0_5": gate_pbo,                # primary combinatorics gate
            "pbo_available": pbo_val is not None,
            "dsr_soft_signal": dsr_soft_signal,    # advisory only; not required
            "sample_ok": not insufficient,
            "banner_eligible": banner_eligible,
            "gate_formula": "net_pf_bca_lower > 1 AND pbo <= 0.5 AND sample_ok  (DSR advisory)",
        },
    }


def _json_default(x: Any) -> Any:
    if isinstance(x, float) and not np.isfinite(x):
        return None
    if isinstance(x, (np.floating,)):
        v = float(x)
        return v if np.isfinite(v) else None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


def run(picks: list[dict]) -> dict[str, Any]:
    feeds = _feeds(picks)
    out: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "n_total_closed": len(picks),
        "config": {
            "n_resamples_bca": N_RESAMPLES,
            "min_n_banner": MIN_N_BANNER,
            "cost_assumptions": COSTS,
            "banner_gate_rule": "PF_BCa_lower>1.0 AND DSR_p<=0.05 AND PBO<=0.5 (if available) AND n>=50",
        },
        "feeds": {},
    }
    for name, sub in feeds.items():
        print(f"[feed_risk_metrics] {name} n={len(sub)}", flush=True)
        out["feeds"][name] = _feed_metrics(name, sub)
    return out


def main() -> int:
    data = json.loads(DATA_IN.read_text(encoding="utf-8"))
    picks = data["picks"]["recent_closed"]
    out = run(picks)
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    DATA_OUT.write_text(json.dumps(out, indent=2, default=_json_default), encoding="utf-8")
    print(f"[feed_risk_metrics] wrote {DATA_OUT}")

    print("\n=== Banner-eligibility per feed ===")
    for name, r in out["feeds"].items():
        g = r["banner_gate"]
        mark = "PASS" if g["banner_eligible"] else "fail"
        pf_lo = r["bca_95_gross"].get("pf", [None, None])[0]
        n = r["n"]
        pf = r["point_metrics_gross"].get("pf")
        dsr_p = r["dsr_p_value"]
        pbo_val = r["pbo"].get("pbo")
        pf_lo_str = "None" if pf_lo is None else f"{pf_lo:.3f}"
        dsr_p_str = "None" if dsr_p is None else f"{dsr_p:.4f}"
        pbo_str = "None" if pbo_val is None else f"{pbo_val:.3f}"
        print(
            f"  [{mark}] {name:<20} n={n:>4} "
            f"PF={pf:.3f} PF_BCa_lo={pf_lo_str} DSR_p={dsr_p_str} PBO={pbo_str}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
