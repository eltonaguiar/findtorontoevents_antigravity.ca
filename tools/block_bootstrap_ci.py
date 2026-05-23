"""
Block bootstrap 95% CI on Profit Factor / Sharpe / WR per feed.

Phase 4 prerequisite (Mercury + DeepSeek reviewers). Uses arch.bootstrap.
- MovingBlockBootstrap (primary)
- StationaryBootstrap (cross-check)
- Block size = ceil(n^(1/3)) or 10 for small n
- Group-by-strategy_id blocking (DeepSeek recommendation) as an auxiliary run
- 10,000 resamples, 95% CI

Usage:
    .venv/Scripts/python.exe tools/block_bootstrap_ci.py

Outputs:
    tools/data/block_bootstrap_results_2026_04_20.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from arch.bootstrap import MovingBlockBootstrap, StationaryBootstrap

REPO = Path(__file__).resolve().parents[1]
DATA_IN = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
DATA_OUT = REPO / "tools" / "data" / "block_bootstrap_results_2026_04_20.json"

sys.path.insert(0, str(REPO))
from tools.dashboard_hc_rules import passes_high_conviction_heuristics_only  # noqa: E402

N_RESAMPLES = 10_000
CI_LO, CI_HI = 2.5, 97.5
RNG_SEED = 20260420


def pf(pnls: np.ndarray) -> float:
    if pnls.size == 0:
        return float("nan")
    pos = pnls[pnls > 0].sum()
    neg = -pnls[pnls < 0].sum()
    if neg <= 0:
        return float("inf") if pos > 0 else float("nan")
    return float(pos / neg)


def sharpe(pnls: np.ndarray) -> float:
    if pnls.size < 2:
        return float("nan")
    sd = pnls.std(ddof=1)
    if sd == 0:
        return float("nan")
    return float(pnls.mean() / sd * math.sqrt(252))


def wr(pnls: np.ndarray) -> float:
    if pnls.size == 0:
        return float("nan")
    return float((pnls > 0).mean())


def _safe_percentile(vals: list[float], q: float) -> float:
    finite = [v for v in vals if np.isfinite(v)]
    if not finite:
        return float("nan")
    return float(np.percentile(finite, q))


def _bootstrap_ci(
    pnls: np.ndarray,
    stat_fn: Callable[[np.ndarray], float],
    bootstrap_cls,
    block_size: int,
    n: int = N_RESAMPLES,
    seed: int = RNG_SEED,
) -> tuple[float, float]:
    if pnls.size < 2:
        return (float("nan"), float("nan"))
    bs = bootstrap_cls(block_size, pnls, seed=seed)
    vals: list[float] = []
    for data, _ in bs.bootstrap(n):
        arr = np.asarray(data[0])
        vals.append(stat_fn(arr))
    return (_safe_percentile(vals, CI_LO), _safe_percentile(vals, CI_HI))


def _bootstrap_bca_joint(
    pnls: np.ndarray,
    block_size: int,
    n: int = N_RESAMPLES,
    seed: int = RNG_SEED,
) -> dict[str, tuple[float, float]]:
    """BCa 95% CI for a joint vector statistic (PF, Sharpe, WR, MaxDD) via
    arch.bootstrap.StationaryBootstrap.conf_int(method="bca").

    Returns dict keyed by stat name -> (lo, hi). NaN tuple on failure.
    """
    names = ("pf", "sharpe", "wr", "maxdd")
    nan_out = {k: (float("nan"), float("nan")) for k in names}
    if pnls.size < 5:
        return nan_out

    def joint(arr: np.ndarray) -> np.ndarray:
        arr = np.asarray(arr, dtype=float)
        eq = np.cumsum(arr)
        peak = np.maximum.accumulate(eq)
        dd = eq - peak  # <= 0
        maxdd = float(dd.min()) if dd.size else 0.0
        return np.array([pf(arr), sharpe(arr), wr(arr), maxdd], dtype=float)

    try:
        bs = StationaryBootstrap(block_size, pnls, seed=seed)
        ci = bs.conf_int(joint, reps=n, method="bca", size=0.95, tail="two")
        # ci shape: (2, 4) -> lower row 0, upper row 1
        lo, hi = ci[0], ci[1]
        return {
            "pf": (float(lo[0]), float(hi[0])),
            "sharpe": (float(lo[1]), float(hi[1])),
            "wr": (float(lo[2]), float(hi[2])),
            "maxdd": (float(lo[3]), float(hi[3])),
        }
    except Exception as e:
        out = dict(nan_out)
        out["_error"] = str(e)  # type: ignore[assignment]
        return out


def _bootstrap_group_ci(
    pnls_by_group: list[np.ndarray],
    stat_fn: Callable[[np.ndarray], float],
    n: int = N_RESAMPLES,
    seed: int = RNG_SEED,
) -> tuple[float, float]:
    """Resample whole strategy-groups with replacement (DeepSeek block = strategy_id)."""
    groups = [g for g in pnls_by_group if g.size > 0]
    if len(groups) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    G = len(groups)
    vals: list[float] = []
    for _ in range(n):
        idx = rng.integers(0, G, size=G)
        resampled = np.concatenate([groups[i] for i in idx])
        vals.append(stat_fn(resampled))
    return (_safe_percentile(vals, CI_LO), _safe_percentile(vals, CI_HI))


def _block_size(n: int) -> int:
    """Block length for circular/stationary block bootstrap.

    Cube-root(n) ceil for n>=30, 2..10 band for small samples. Matches
    Politis-White (2004) asymptotics for near-i.i.d. trade P&L. May
    under-cover for strongly autocorrelated crypto returns — revisit if BCa
    coverage diagnostics show miscalibration. Not sqrt(n); see PR #314 Copilot #3.
    """
    if n < 30:
        return min(10, max(2, n // 2))
    return max(2, math.ceil(n ** (1.0 / 3.0)))


def _is_smart_pick(p: dict) -> bool:
    """Proxy: grade A/B and elite_score >= 70 and trust tier PROVEN/RELIABLE."""
    g = str(p.get("grade") or "").upper()
    tt = str(p.get("trust_tier") or "").upper()
    try:
        es = float(p.get("elite_score") or 0)
    except Exception:
        es = 0.0
    return g in ("A", "B") and tt in ("PROVEN", "RELIABLE") and es >= 70


def _is_verified_alpha(p: dict) -> bool:
    """Proxy from template.html definition: PROVEN tier OR fwd_wr>=0.55 on >=5 trades."""
    tt = str(p.get("trust_tier") or "").upper()
    if tt == "PROVEN":
        return True
    try:
        wr_v = float(p.get("strat_fwd_wr") or p.get("forward_wr") or 0)
        if wr_v > 1.5:
            wr_v /= 100.0
        n = int(p.get("strat_fwd_trades") or p.get("forward_trades") or 0)
    except Exception:
        return False
    return wr_v >= 0.55 and n >= 5


def _feeds(picks: list[dict]) -> dict[str, list[dict]]:
    feeds: dict[str, list[dict]] = {
        "All": [p for p in picks if p.get("pnl_pct") is not None],
    }
    feeds["HC"] = [p for p in feeds["All"] if passes_high_conviction_heuristics_only(p)]
    feeds["Smart Picks"] = [p for p in feeds["All"] if _is_smart_pick(p)]
    feeds["Verified Alpha"] = [p for p in feeds["All"] if _is_verified_alpha(p)]
    for ac in ("CRYPTO", "EQUITY", "FOREX", "ETF", "COMMODITY"):
        feeds[f"AC:{ac}"] = [p for p in feeds["All"] if str(p.get("asset_class") or "").upper() == ac]
    return feeds


def _pnls(picks: list[dict]) -> np.ndarray:
    out = []
    for p in picks:
        v = p.get("pnl_pct")
        if v is None:
            continue
        try:
            out.append(float(v))
        except Exception:
            pass
    return np.asarray(out, dtype=float)


def _group_pnls_by_strategy(picks: list[dict]) -> list[np.ndarray]:
    df = pd.DataFrame(
        [{"strategy": p.get("strategy") or p.get("source_system") or "_unknown", "pnl": p.get("pnl_pct")}
         for p in picks if p.get("pnl_pct") is not None]
    )
    if df.empty:
        return []
    df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce")
    df = df.dropna(subset=["pnl"])
    return [g["pnl"].to_numpy() for _, g in df.groupby("strategy")]


def analyze_feed(name: str, picks: list[dict]) -> dict[str, Any]:
    pnls = _pnls(picks)
    n = int(pnls.size)
    bs_size = _block_size(n)
    result: dict[str, Any] = {
        "feed": name,
        "n": n,
        "block_size": bs_size,
        "point": {
            "pf": pf(pnls),
            "sharpe": sharpe(pnls),
            "wr": wr(pnls),
        },
    }
    if n < 5:
        result["ci"] = {"note": "n<5, skipped"}
        return result

    ci: dict[str, Any] = {}
    for stat_name, fn in (("pf", pf), ("sharpe", sharpe), ("wr", wr)):
        lo_mb, hi_mb = _bootstrap_ci(pnls, fn, MovingBlockBootstrap, bs_size)
        lo_sb, hi_sb = _bootstrap_ci(pnls, fn, StationaryBootstrap, bs_size)
        ci[stat_name] = {
            "moving_block_95": [lo_mb, hi_mb],
            "stationary_95": [lo_sb, hi_sb],
        }

    # Group-bootstrap: resample whole strategies (DeepSeek recommendation)
    groups = _group_pnls_by_strategy(picks)
    if len(groups) >= 2:
        ci["pf"]["strategy_group_95"] = list(_bootstrap_group_ci(groups, pf))
        ci["sharpe"]["strategy_group_95"] = list(_bootstrap_group_ci(groups, sharpe))
        ci["wr"]["strategy_group_95"] = list(_bootstrap_group_ci(groups, wr))
        ci["_group_info"] = {"n_strategies": len(groups)}

    result["ci"] = ci
    # Flag: does PF CI include 1.0?
    pf_mb = ci["pf"]["moving_block_95"]
    if np.isfinite(pf_mb[0]) and np.isfinite(pf_mb[1]):
        result["pf_ci_includes_1"] = bool(pf_mb[0] <= 1.0 <= pf_mb[1])
    return result


def main() -> int:
    data = json.loads(DATA_IN.read_text(encoding="utf-8"))
    picks = data["picks"]["recent_closed"]
    feeds = _feeds(picks)

    out: dict[str, Any] = {
        "generated_at": "2026-04-20",
        "source": str(DATA_IN.relative_to(REPO)),
        "n_total_closed": len(picks),
        "config": {
            "n_resamples": N_RESAMPLES,
            "ci_percentiles": [CI_LO, CI_HI],
            "block_size_rule": "ceil(n^(1/3)), floor 2; min(10, n//2) if n<30",
            "bootstraps": ["MovingBlockBootstrap", "StationaryBootstrap", "strategy_group"],
            "seed": RNG_SEED,
        },
        "feeds": {},
    }
    for name, sub in feeds.items():
        print(f"[bootstrap] {name} n={len(sub)}", flush=True)
        out["feeds"][name] = analyze_feed(name, sub)

    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    DATA_OUT.write_text(json.dumps(out, indent=2, default=lambda x: None if (isinstance(x, float) and not np.isfinite(x)) else x), encoding="utf-8")
    print(f"[bootstrap] wrote {DATA_OUT}")

    # Banner summary
    hc = out["feeds"].get("HC", {})
    print("\n=== Banner ===")
    print(f"HC PF point = {hc.get('point', {}).get('pf')!r}")
    print(f"HC PF 95% CI (moving block) = {hc.get('ci', {}).get('pf', {}).get('moving_block_95')}")
    print(f"HC PF 95% CI (strategy group) = {hc.get('ci', {}).get('pf', {}).get('strategy_group_95')}")
    print("\nFeeds where PF 95% CI includes 1.0:")
    for name, res in out["feeds"].items():
        if res.get("pf_ci_includes_1"):
            print(f"  - {name}: PF={res['point']['pf']:.3f}, CI={res['ci']['pf']['moving_block_95']}")
    print("\nBlock sizes per feed:")
    for name, res in out["feeds"].items():
        print(f"  {name}: n={res['n']}, block={res['block_size']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
