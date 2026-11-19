"""audit3_tribunal.py — audit3: quantitative kill tribunal for every closed pick cell.

Purpose
-------
`/audit` accumulated many overlapping surfaces (filters, tiers, controllers,
smart picks, money-ready, copytrader, prediction markets). audit3 replaces the
pile with one question, asked once per (asset_class, strategy, direction) cell:

    "Is the realized net edge distinguishable from luck, after we correct for
     the number of cells we tested?"

This module is the computational half of `/audit3/`. It reads a closed-pick
ledger (dashboard_data.json or a flat list exported from MySQL), and emits a
small JSON sidecar (`audit3_ledger.json`) that the static page renders.

Statistical contract (all gates are pre-declared, never tuned on the data)
--------------------------------------------------------------------------
G0  Sample floor     n >= 20 for a verdict; n >= 100 for PROVEN.
G1  Edge direction   one-sided exact binomial test of WR > 0.5 (H0: coin flip).
G2  Net expectancy   per-trade net return (gross minus per-class slippage)
                     bootstrap 95% CI (2,000 seeded resamples) must exclude 0.
G3  Multiplicity     Benjamini-Hochberg FDR q <= 0.10 across all tested cells;
                     Bonferroni threshold reported alongside.
G4  Overfit          Deflated Sharpe Ratio >= 0.95 (Bailey & Lopez de Prado
                     approximation; n_trials = tested cells).
G5  Stability        chronological split-half: both halves net expectancy > 0.
G6  Concentration    no single symbol > 60% of a cell's trades, no single
                     source system > 90% (report-only at 60%).
G7  Cost realism      slippage is deducted BEFORE every statistic. A 7bp gross
                     win is a net loss on COMMODITY (12bp round trip).

Verdicts
--------
PROVEN_T2    all gates pass (n>=100)                -> eligible for real risk
CANDIDATE    n>=30, net CI>0, q<=0.20               -> forward paper, n->100
WEAK         n>=20, not proven, not clearly losing  -> keep observing
KILL         net CI entirely <0, or PF<0.8 at n>=50 -> stop emitting
INSUFFICIENT n<20                                   -> no claim either way

Why one-sided: the product only acts on positive edge. Losing cells are caught
by the expectancy/PF tests, not by a two-sided WR test.

Usage
-----
  python3 -m alpha_engine.audit3_tribunal \
      --picks audit_dashboard/data/dashboard_data.json \
      --out audit_dashboard/data/audit3_ledger.json

Exit codes: 0 report written; 2 unusable input.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from datetime import datetime, timezone
from typing import Any, Iterable

WR_MIN_N = 20
PROVEN_MIN_N = 100
CANDIDATE_MIN_N = 30
KILL_PF_N = 50
FDR_Q = 0.10
CANDIDATE_Q = 0.20
DSR_THRESHOLD = 0.95
BOOT_N = 2000
BOOT_SEED = 42
MAX_SYMBOL_SHARE = 0.60
MAX_SOURCE_SHARE = 0.90

# Round-trip execution cost, in percent (pnl_pct is a percent).
SLIPPAGE_PCT = {
    "CRYPTO": 0.15,
    "EQUITY": 0.10,
    "COMMODITY": 0.12,
    "ETF": 0.08,
    "FOREX": 0.05,
    "BOND": 0.08,
    "FUTURES": 0.10,
    "MEME": 0.30,
    "PENNY_STOCK": 0.30,
    "MUTUAL_FUND": 0.08,
}
DEFAULT_SLIPPAGE_PCT = 0.12

# Source-family buckets for the "is any surface actually good?" question.
FAMILY_PATTERNS = (
    ("copytrader", ("copytrad", "copy_trad", "copy-trad")),
    ("polymarket", ("polymarket", "poly_market")),
    ("kalshi", ("kalshi",)),
    ("prediction_market", ("prediction_market", "prediction-market")),
    ("ml_enhanced", ("ml_enhanced", "ml-enhanced")),
    ("mega_mutation", ("mega_mutation", "mutation")),
    ("luxalgo", ("luxalgo",)),
    ("hyro", ("hyro",)),
    ("wired_in", ("wired_in",)),
    ("manual", ("manual",)),
)


# ─────────────────────────────────────────────────────────────── statistics ──
def wilson_interval(wins: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion."""
    n = int(n)
    if n <= 0:
        return (0.0, 1.0)
    p = wins / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _log_binom_pmf(k: int, n: int) -> float:
    """log C(n,k) - n*log(2), i.e. log P(X=k) under p=0.5."""
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
            - n * math.log(2.0))


def binom_sf(k: int, n: int) -> float:
    """One-sided exact p-value P(X >= k) under Binomial(n, 0.5).

    Computed in log space so n=3000 does not underflow to a false 0.0.
    """
    if n <= 0:
        return 1.0
    k = max(0, min(int(k), n))
    if k == 0:
        return 1.0
    logs = [_log_binom_pmf(i, n) for i in range(k, n + 1)]
    m = max(logs)
    return min(1.0, math.exp(m) * sum(math.exp(x - m) for x in logs))


def bootstrap_mean_ci(values: list[float], n_boot: int = BOOT_N,
                      seed: int = BOOT_SEED) -> dict[str, Any]:
    """Percentile bootstrap 95% CI for the mean. Deterministic per seed."""
    n = len(values)
    if n < 2:
        return {"mean": (values[0] if values else 0.0), "ci_lo": None,
                "ci_hi": None, "frac_positive": None, "n_boot": 0}
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += values[rng.randrange(n)]
        means.append(s / n)
    means.sort()
    return {
        "mean": sum(values) / n,
        "ci_lo": means[int(0.025 * n_boot)],
        "ci_hi": means[int(0.975 * n_boot) - 1],
        "frac_positive": sum(1 for m in means if m > 0) / n_boot,
        "n_boot": n_boot,
    }


def profit_factor(values: Iterable[float]) -> float | None:
    gross = sum(v for v in values if v > 0)
    loss = -sum(v for v in values if v < 0)
    if loss <= 1e-12:
        return None
    return gross / loss


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Acklam's inverse normal CDF (|error| < 1.15e-9)."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def deflated_sharpe(values: list[float], n_trials: int) -> dict[str, float] | None:
    """Deflated Sharpe Ratio (Bailey/Lopez de Prado, 2014), per-trade units.

    SR0 is the expected maximum of n_trials independent null Sharpes with
    variance ~1/n, so the correction tightens automatically as the ledger
    grows. Returns None when the sample is too small or degenerate.
    """
    n = len(values)
    # n_trials < 2 means no multiplicity correction is possible and the
    # expected-max formula diverges (-inf); DSR is undefined, not perfect.
    if n < 10 or n_trials < 2:
        return None
    sd = statistics.pstdev(values)
    if sd <= 1e-12:
        return None
    sr = (sum(values) / n) / sd
    m = values
    mu = sum(m) / n
    skew = sum((x - mu) ** 3 for x in m) / n / (sd ** 3)
    kurt = sum((x - mu) ** 4 for x in m) / n / (sd ** 4)
    # Expected max of N standard normals (Bailey/LdP eq. 6).
    gamma = 0.5772156649015329
    e = math.e
    sr0 = ((1 - gamma) * _norm_ppf(1 - 1.0 / n_trials)
           + gamma * _norm_ppf(1 - 1.0 / (n_trials * e)))
    sr0 *= math.sqrt(1.0 / n)  # scale to per-trade Sharpe units
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4.0 * sr * sr))
    z = (sr - sr0) * math.sqrt(n - 1) / denom
    return {
        "sharpe": sr,
        "sr0": sr0,
        "dsr": _norm_cdf(z),
        "skew": skew,
        "kurtosis": kurt,
        "n_trials": n_trials,
    }


def benjamini_hochberg(pvalues: list[float], q: float = FDR_Q) -> list[float]:
    """Return BH-adjusted q-values in the input order (monotone step-up)."""
    m = len(pvalues)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [1.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        val = min(prev, pvalues[i] * m / rank)
        adjusted[i] = val
        prev = val
    return adjusted


def split_half_ok(values: list[float]) -> tuple[bool, dict[str, float]]:
    """Chronological split-half stability: both halves must have mean > 0."""
    if len(values) < 10:
        return False, {}
    mid = len(values) // 2
    first, second = values[:mid], values[mid:]
    m1 = sum(first) / len(first) if first else 0.0
    m2 = sum(second) / len(second) if second else 0.0
    return (m1 > 0 and m2 > 0), {"first_half_mean": m1, "second_half_mean": m2}


# ────────────────────────────────────────────────────────────────── loading ──
def _to_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_rows(path: str) -> tuple[list[dict], str | None]:
    """Load closed picks and the ledger's own generated_at, if present."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    generated_at = None
    rows: Any = None
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        generated_at = data.get("generated_at")
        for key_path in (("picks", "recent_closed"), ("picks",), ("candidates",),
                         ("records",), ("closed_picks",)):
            cur: Any = data
            for k in key_path:
                cur = cur.get(k) if isinstance(cur, dict) else None
                if cur is None:
                    break
            if isinstance(cur, list):
                rows = cur
                break
    if not rows:
        raise ValueError(f"no closed-pick list found in {path}")

    seen: set[str] = set()
    clean: list[dict] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        pnl = r.get("pnl_pct")
        if not isinstance(pnl, (int, float)):
            continue
        status = str(r.get("status") or "").upper()
        if status in ("OPEN", "PENDING", ""):
            continue
        key = str(r.get("id") or "") or (
            f"{r.get('strategy')}|{r.get('symbol')}|{r.get('direction')}|"
            f"{r.get('closed_at') or r.get('timestamp')}|{pnl}")
        if key in seen:
            continue
        seen.add(key)
        clean.append(r)
    if not clean:
        raise ValueError(f"{path}: found {len(rows)} rows, none usable")
    # Chronological order so split-half is actually chronological.
    clean.sort(key=lambda r: (
        _to_dt(r.get("closed_at") or r.get("timestamp")) or
        datetime(1970, 1, 1, tzinfo=timezone.utc)))
    return clean, generated_at


# ─────────────────────────────────────────────────────────────────── cells ──
def _net(r: dict) -> float:
    ac = str(r.get("asset_class") or "UNKNOWN").upper()
    return float(r["pnl_pct"]) - SLIPPAGE_PCT.get(ac, DEFAULT_SLIPPAGE_PCT)


def _direction(r: dict) -> str:
    d = str(r.get("direction") or "").upper()
    if d.startswith("L"):
        return "LONG"
    if d.startswith("S"):
        return "SHORT"
    return d or "UNKNOWN"


def _family(r: dict) -> str:
    hay = f"{r.get('strategy') or ''} {r.get('source_system') or ''} {r.get('system') or ''}".lower()
    for name, pats in FAMILY_PATTERNS:
        if any(p in hay for p in pats):
            return name
    return "other"


def evaluate_cell(rows: list[dict], n_trials: int, label: dict[str, Any],
                  *, apply_source_gate: bool = True) -> dict[str, Any]:
    """Compute every gate for one cell. Never raises.

    apply_source_gate: a single strategy is normally emitted by one source
    system, so source concentration is only meaningful for aggregate cells
    (asset class, source family). Per-strategy/symbol cells pass False.
    """
    nets = [_net(r) for r in rows]
    n = len(nets)
    wins = sum(1 for v in nets if v > 0)
    wr = wins / n if n else 0.0
    lo, hi = wilson_interval(wins, n) if n else (0.0, 1.0)
    pf = profit_factor(nets)
    boot = bootstrap_mean_ci(nets) if n >= 2 else {"mean": 0.0, "ci_lo": None,
                                                   "ci_hi": None, "frac_positive": None}
    stable, halves = split_half_ok(nets)
    p = binom_sf(wins, n) if n else 1.0
    symbols = [str(r.get("symbol") or "?") for r in rows]
    top_sym_share = (max(symbols.count(s) for s in set(symbols)) / n) if n else 0.0
    sources = [str(r.get("source_system") or r.get("system") or "?") for r in rows]
    top_src_share = (max(sources.count(s) for s in set(sources)) / n) if n else 0.0

    reasons: list[str] = []
    verdict = "INSUFFICIENT_N"
    if n >= WR_MIN_N:
        ci_lo, ci_hi = boot.get("ci_lo"), boot.get("ci_hi")
        expect_ci_negative = ci_hi is not None and ci_hi < 0
        expect_ci_positive = ci_lo is not None and ci_lo > 0
        if expect_ci_negative or (pf is not None and pf < 0.8 and n >= KILL_PF_N):
            verdict = "KILL"
            if expect_ci_negative:
                reasons.append("net expectancy 95% CI entirely below zero")
            if pf is not None and pf < 0.8:
                reasons.append(f"profit factor {pf:.2f} < 0.80 at n={n}")
            if wr < 0.40:
                reasons.append(f"win rate {wr:.1%} below 40%")
        elif (n >= PROVEN_MIN_N and lo > 0.5 and boot.get("mean", 0) > 0
              and expect_ci_positive and stable and top_sym_share <= MAX_SYMBOL_SHARE
              and (not apply_source_gate or top_src_share <= MAX_SOURCE_SHARE)):
            verdict = "PROVEN_T2"
        elif (n >= CANDIDATE_MIN_N and boot.get("mean", 0) > 0
              and expect_ci_positive
              and (not apply_source_gate or top_src_share <= MAX_SOURCE_SHARE)):
            verdict = "CANDIDATE"
        else:
            verdict = "WEAK"
            if wr < 0.5:
                reasons.append(f"win rate {wr:.1%} <= 50%")
            if not stable:
                reasons.append("split-half unstable (one half mean <= 0)")
            if top_sym_share > MAX_SYMBOL_SHARE:
                reasons.append(f"single symbol {top_sym_share:.0%} of trades")
            if apply_source_gate and top_src_share > MAX_SOURCE_SHARE:
                reasons.append(f"single source {top_src_share:.0%} of trades")
    else:
        reasons.append(f"n={n} < {WR_MIN_N}: no statistical claim")

    out = dict(label)
    out.update({
        "n": n,
        "wins": wins,
        "wr": round(wr, 4),
        "wr_ci": [round(lo, 4), round(hi, 4)],
        "pf": round(pf, 4) if pf is not None else None,
        "gross_expectancy_pct": round(sum(float(r["pnl_pct"]) for r in rows) / n, 4) if n else 0.0,
        "net_expectancy_pct": round(boot.get("mean", 0.0), 4),
        "net_ci_pct": [round(boot["ci_lo"], 4) if boot.get("ci_lo") is not None else None,
                       round(boot["ci_hi"], 4) if boot.get("ci_hi") is not None else None],
        "p_value": round(p, 6),
        "q_value": None,  # filled after BH across the family
        "dsr": None,
        "split_half": ({"stable": stable, **{k: round(v, 4) for k, v in halves.items()}}
                       if halves else None),
        "top_symbol_share": round(top_sym_share, 4),
        "top_source_share": round(top_src_share, 4),
        "verdict": verdict,
        "reasons": reasons,
    })
    dsr = deflated_sharpe(nets, n_trials)
    if dsr:
        out["dsr"] = round(dsr["dsr"], 4)
        out["sharpe"] = round(dsr["sharpe"], 4)
        out["sr0"] = round(dsr["sr0"], 4)
    return out


def _group(rows: list[dict], key_fn) -> dict[Any, list[dict]]:
    out: dict[Any, list[dict]] = {}
    for r in rows:
        out.setdefault(key_fn(r), []).append(r)
    return out


def _promote(cell: dict) -> None:
    """Apply the FDR and DSR gates that need the full tested family."""
    if cell["n"] < WR_MIN_N:
        return
    q = cell.get("q_value")
    if q is None:
        return
    if cell["verdict"] == "PROVEN_T2":
        if q > FDR_Q:
            cell["verdict"] = "CANDIDATE"
            cell["reasons"].append(f"BH q={q:.3f} > {FDR_Q}")
        elif cell.get("dsr") is not None and cell["dsr"] < DSR_THRESHOLD:
            cell["verdict"] = "CANDIDATE"
            cell["reasons"].append(f"DSR {cell['dsr']:.3f} < {DSR_THRESHOLD}")
    elif cell["verdict"] == "CANDIDATE":
        if q > CANDIDATE_Q:
            cell["verdict"] = "WEAK"
        elif cell.get("dsr") is not None and cell["dsr"] < 0.50:
            cell["verdict"] = "WEAK"
            cell["reasons"].append(f"DSR {cell['dsr']:.3f} < 0.50")


def build_report(rows: list[dict], source: str, source_generated_at: str | None) -> dict[str, Any]:
    n_cells = 0
    cells: list[dict] = []
    classes: list[dict] = []
    symbols: list[dict] = []
    families: list[dict] = []

    # PASS 1: count tested cells so DSR knows the multiplicity.
    strat_groups = _group(rows, lambda r: (str(r.get("asset_class") or "UNKNOWN").upper(),
                                           str(r.get("strategy") or r.get("source_system") or "(unattributed)"),
                                           _direction(r)))
    n_trials = sum(1 for g in strat_groups.values() if len(g) >= WR_MIN_N)

    for (ac, strat, direction), group in strat_groups.items():
        cell = evaluate_cell(group, max(1, n_trials),
                             {"asset_class": ac, "strategy": strat, "direction": direction},
                             apply_source_gate=False)
        cells.append(cell)
    cells.sort(key=lambda c: (-c["n"], c["asset_class"], c["strategy"]))

    # BH across the tested cells only.
    tested = [c for c in cells if c["n"] >= WR_MIN_N]
    for c, q in zip(tested, benjamini_hochberg([c["p_value"] for c in tested])):
        c["q_value"] = round(q, 6)
    for c in tested:
        _promote(c)

    # Class-level aggregate.
    class_groups = _group(rows, lambda r: str(r.get("asset_class") or "UNKNOWN").upper())
    class_trials = len(class_groups)
    for ac, group in class_groups.items():
        cls = evaluate_cell(group, max(1, class_trials), {"asset_class": ac})
        # Class promotion needs the stricter charter floor (n>=100).
        if cls["verdict"] == "PROVEN_T2" and cls["n"] < PROVEN_MIN_N:
            cls["verdict"] = "WEAK"
        classes.append(cls)
    for c, q in zip(classes, benjamini_hochberg([c["p_value"] for c in classes])):
        c["q_value"] = round(q, 6)
    for c in classes:
        _promote(c)
    classes.sort(key=lambda c: (-c["n"], c["asset_class"]))

    # Symbol x direction cells (n>=20 only — the rest is noise by construction).
    sym_groups = _group(rows, lambda r: (str(r.get("asset_class") or "UNKNOWN").upper(),
                                         str(r.get("symbol") or "?"), _direction(r)))
    sym_tested = {k: g for k, g in sym_groups.items() if len(g) >= WR_MIN_N}
    for (ac, sym, direction), group in sym_tested.items():
        symbols.append(evaluate_cell(group, max(1, len(sym_tested)),
                                     {"asset_class": ac, "symbol": sym, "direction": direction},
                                     apply_source_gate=False))
    for c, q in zip(symbols, benjamini_hochberg([c["p_value"] for c in symbols])):
        c["q_value"] = round(q, 6)
    for c in symbols:
        _promote(c)
    symbols.sort(key=lambda c: (-c["n"], c["asset_class"], c["symbol"]))

    # Source families: copytrader / polymarket / kalshi / ml_enhanced / ...
    fam_groups = _group(rows, _family)
    for fam, group in sorted(fam_groups.items(), key=lambda kv: -len(kv[1])):
        families.append(evaluate_cell(group, max(1, len(fam_groups)),
                                      {"family": fam}))

    # Kill tribunal: everything KILL plus near-kill (WEAK with negative mean).
    kills = []
    for scope, bucket in (("strategy", cells), ("symbol", symbols), ("class", classes)):
        for c in bucket:
            if c["verdict"] != "KILL":
                continue
            mutation = []
            if c["wr"] < 0.40:
                mutation.append("invert or heavily filter: WR<40% often means the emitter is a fade signal")
            if c["top_symbol_share"] > MAX_SYMBOL_SHARE:
                mutation.append("drop the dominant symbol and re-measure; edge is a single-name bet")
            if c["top_source_share"] > MAX_SOURCE_SHARE:
                mutation.append("require a second source before emitting")
            if not mutation:
                mutation.append("retire the emitter; no residual edge after costs")
            kills.append({
                "scope": scope,
                "asset_class": c.get("asset_class"),
                "strategy": c.get("strategy") or c.get("symbol") or "(class aggregate)",
                "direction": c.get("direction") or "-",
                "n": c["n"],
                "wr": c["wr"],
                "pf": c["pf"],
                "net_expectancy_pct": c["net_expectancy_pct"],
                "q_value": c.get("q_value"),
                "reasons": c["reasons"],
                "mutation": mutation,
            })

    # Hypothesis registry: coverage + status counts, no re-interpretation.
    hyp = {"registry_path": "reports/hypothesis_registry.json", "available": False,
           "total": 0, "by_status": {}, "open": [], "untested_strategies": [],
           "rule": "M-107: pre-register before any backtest; a strategy with no "
                   "registered hypothesis cannot be promoted past CANDIDATE."}
    try:
        with open(hyp["registry_path"], encoding="utf-8") as f:
            reg = json.load(f)
        hs = reg.get("hypotheses") or []
        hyp["available"] = True
        hyp["total"] = len(hs)
        for h in hs:
            st = str(h.get("status") or "UNKNOWN").upper()
            hyp["by_status"][st] = hyp["by_status"].get(st, 0) + 1
        hyp["open"] = [{
            "id": h.get("id"), "asset_class": h.get("asset_class"),
            "family": h.get("family"), "status": h.get("status"),
            "description": (h.get("description") or "")[:200],
        } for h in hs if str(h.get("status") or "").upper() in
            ("OPEN", "REGISTERED", "TESTING", "PENDING", "ADMISSIBLE")]
        registered = {str(h.get("family") or "") for h in hs}
        hyp["untested_strategies"] = sorted(
            {c["strategy"] for c in cells
             if c["verdict"] == "PROVEN_T2" and c["strategy"] not in registered})
    except (OSError, ValueError) as exc:
        hyp["error"] = str(exc)

    def count(v: str, bucket: list[dict]) -> int:
        return sum(1 for c in bucket if c["verdict"] == v)

    summary = {
        "n_rows": len(rows),
        "n_cells_tested": len(tested),
        "n_cells_total": len(cells),
        "n_symbol_cells": len(symbols),
        "n_proven": count("PROVEN_T2", cells),
        "n_candidate": count("CANDIDATE", cells),
        "n_weak": count("WEAK", cells),
        "n_kill": count("KILL", cells),
        "n_insufficient": count("INSUFFICIENT_N", cells),
        "kill_rate_pct": round(100.0 * count("KILL", cells) / len(tested), 2) if tested else 0.0,
        "n_proven_symbols": count("PROVEN_T2", symbols),
        "n_proven_classes": count("PROVEN_T2", classes),
        "n_kill_symbols": count("KILL", symbols),
    }

    return {
        "schema": "audit3.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "source_generated_at": source_generated_at,
        "not_money_ready_disclaimer": (
            "audit3 is an evidence ledger, not a signal service. PROVEN_T2 means "
            "the realized closed-pick ledger survives the listed gates; it does "
            "not guarantee future returns. No position sizing is emitted here."),
        "conventions": {
            "wr_floor_n": WR_MIN_N,
            "proven_min_n": PROVEN_MIN_N,
            "candidate_min_n": CANDIDATE_MIN_N,
            "fdr_q": FDR_Q,
            "dsr_threshold": DSR_THRESHOLD,
            "bootstrap_resamples": BOOT_N,
            "bootstrap_seed": BOOT_SEED,
            "slippage_pct_by_class": SLIPPAGE_PCT,
            "win_definition": "net pnl_pct > 0 after per-class round-trip slippage",
            "p_value": "one-sided exact binomial P(X>=wins) under p=0.5",
            "multiplicity": "Benjamini-Hochberg across tested cells; Bonferroni "
                            f"alpha/m = {0.05 / max(1, len(tested)):.6f}",
            "stability": "chronological split-half, both halves net mean > 0",
            "max_symbol_share": MAX_SYMBOL_SHARE,
            "max_source_share": MAX_SOURCE_SHARE,
            "random_entry_mc": "not run here (needs per-symbol price series); "
                               "see alpha_engine/benchmark_closed_ledger.py for the "
                               "timing-null companion report.",
        },
        "summary": summary,
        "classes": classes,
        "cells": cells,
        "symbols": symbols,
        "source_families": families,
        "kill_tribunal": {
            "criteria": [
                "net expectancy 95% CI entirely < 0",
                f"PF < 0.80 at n >= {KILL_PF_N}",
                "WR < 40% (diagnostic, not sufficient alone)",
            ],
            "kills": kills,
        },
        "hypotheses": hyp,
        "provenance": {
            "module": "alpha_engine/audit3_tribunal.py",
            "source_file": source,
            "source_generated_at": source_generated_at,
            "n_cells_scored_with_dsr": sum(1 for c in cells if c.get("dsr") is not None),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="audit3 quantitative kill tribunal")
    ap.add_argument("--picks", required=True, help="dashboard_data.json or flat closed-pick list")
    ap.add_argument("--out", help="write ledger JSON here (else stdout)")
    args = ap.parse_args(argv)
    try:
        rows, generated_at = load_rows(args.picks)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    report = build_report(rows, args.picks, generated_at)
    payload = json.dumps(report, indent=1, allow_nan=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
        print(f"wrote {args.out}: {report['summary']}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
