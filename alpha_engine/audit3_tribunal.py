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
                     approximation; n_trials = every emitted strategy).
G5  Stability        chronological split-half: both halves net expectancy > 0.
G6  Concentration    no single symbol > 60% of a cell's trades, no single
                     source system > 90% (report-only at 60%).
G7  Cost realism      slippage is deducted BEFORE every statistic. A 7bp gross
                     win is a net loss on COMMODITY (12bp round trip).
G8  Repeated looks    a CANDIDATE/PROVEN_T2 verdict must persist across K
                     consecutive runs (verdict-history sidecar); the run that
                     began the streak is recorded as first_pass_at. BH is
                     per-run, so without this a cell eventually crosses by chance.
G9  Selection alpha   direction-adjusted selection alpha (pick net - hold) 95%
                     CI lower bound must be > 0 to reach PROVEN_T2; otherwise
                     the cell is beta-dominant, not skill-proven.
G10 Cost stress      the net-expectancy bootstrap CI at 2x the class slippage
                     must keep a positive lower bound to reach PROVEN_T2 or
                     CANDIDATE; an edge that dies at 2x cost is a cost
                     assumption, so the cell is WEAK regardless of any pod.

Verdicts
--------
PROVEN_T2    all gates pass (n>=100)                -> eligible for real risk
CANDIDATE    n>=30, net CI>0, q<=0.20               -> forward paper, n->100
WEAK         n>=20, no claim either way             -> KEEP collecting (default)
KILL         proven harm only                      -> stop emitting
INSUFFICIENT n<20                                   -> no claim either way

Doctrine: innocent until proven guilty (2026-11-19)
---------------------------------------------------
A cell that has not proven edge is NOT a failed cell. The default state of every
strategy, symbol, section and asset class is "not proven yet -- keep it", because
the thing worth finding is usually a small sub-population (e.g. one asset class
inside a section that looks bad in aggregate). Therefore:

  * KILL requires affirmative evidence of harm: the bootstrap 95% CI of net
    expectancy is entirely below zero AND the one-sided harm p-value survives
    Benjamini-Hochberg at q <= 0.10 across the killed cells.
  * A low profit factor (PF < 0.80) is a WATCH flag, never a kill on its own.
  * WEAK carries no negative connotation: it means "no claim", and the cell
    stays in the ledger, the section matrix and the hypothesis queue.
  * Nothing is removed from the closed-pick ledger by this module.

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
import hashlib
import json
import math
import os
import random
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Iterable

try:  # shared canonicaliser; inline fallback keeps this module standalone
    from alpha_engine.symbol_identity import canonical_symbol as _canon_symbol
    from alpha_engine.symbol_identity import direction_key as _dir_key
except ImportError:  # pragma: no cover
    def _canon_symbol(symbol, asset_class=None):
        return str(symbol or "").strip().upper()

    def _dir_key(direction):
        return str(direction or "").strip().upper()

WR_MIN_N = 20
PROVEN_MIN_N = 100
CANDIDATE_MIN_N = 30
# Materiality floor for promotion, in net percent per trade (2026-11-19). A cell
# whose net-CI lower bound is below this is statistically positive but not worth
# risking capital on: 5bp/trade is inside the error of the cost model itself.
PROVEN_MIN_NET_CI_LO_PCT = 0.05
# N4 (2026-11-19): the materiality floor scales with the applied cost model. A flat
# 5bp floor is meaningful for FOREX (5bp cost) and inside the noise for CRYPTO
# (15bp cost). The floor is the larger of the flat minimum and this fraction of
# the cell's mean round-trip cost, so a verdict cannot rest on an edge smaller
# than half the cost it had to overcome.
MATERIALITY_COST_FRACTION = 0.5
GENERATOR_VERSION = "audit3.v2"
KILL_PF_N = 50          # n floor for the PF watch flag
HARM_PF_WATCH = 0.80    # PF below this is a watch flag, never proof of harm
FDR_Q = 0.10
CANDIDATE_Q = 0.20
DSR_THRESHOLD = 0.95
BOOT_N = 2000
BOOT_SEED = 42
MAX_SYMBOL_SHARE = 0.60
MAX_SOURCE_SHARE = 0.90

# DSR multiplicity floor (2026-11-19). The 2026-11-14 pf_registry audit counted
# 658 distinct strategies in the live search space. A payload slice sees far
# fewer, so feeding the slice count into deflated_sharpe under-corrects. PROVEN
# pays max(observed, this floor); CANDIDATE uses the observed bucket width so the
# forward queue is not emptied.
GLOBAL_TRIAL_FLOOR = 658
# Selection-alpha coverage floor: a small price-covered sample may not prove a
# much larger cell. alpha_n must reach max(ALPHA_MIN_N, ALPHA_MIN_COVERAGE*n).
ALPHA_MIN_N = 20
ALPHA_MIN_COVERAGE = 0.50


def global_trial_count(*counts: int) -> int:
    """Trial count for DSR: the whole search space, never just the loaded slice."""
    return max([GLOBAL_TRIAL_FLOOR, *(int(c) for c in counts if c)])

# N1 (2026-11-19): repeated-looks correction. BH FDR is computed per run, but the
# ledger is re-scored every ~6h, so a cell that crosses q<=0.10 once will
# eventually do so by chance. A CANDIDATE/PROVEN_T2 verdict must therefore persist
# across this many consecutive runs before it is granted, and the run that first
# passed is recorded as ``first_pass_at``.
PERSISTENCE_RUNS = 2
PERSISTENCE_VERDICTS = ("CANDIDATE", "PROVEN_T2")

# N2 (2026-11-19): verdict-churn monitor. A cell flipping verdicts between runs
# means the judge is noisy, not that the edge is real. Churn is measured on the
# RAW verdict (before the N1 persistence gate), so the intentional hold-at-WEAK
# delay is not mistaken for instability.
CHURN_ALERT_THRESHOLD = 0.30
CHURN_MIN_TRACKED = 20

# N3 (2026-11-19): recency/regime gate. A cell whose edge came from a stale regime
# must not be promoted on the full-history statistic alone. The trailing window
# (last ~25% of closes, at least this many trades) must have a non-negative net
# mean, else PROVEN_T2 is capped at CANDIDATE.
RECENCY_WINDOW_FRACTION = 0.25
RECENCY_MIN_TRADES = 5

# Round-trip execution cost, in percent (pnl_pct is a percent).
#
# 2026-11-19: these are now the FALLBACK only. `load_rows` reads the publishing
# dashboard's own measured slippage (`slippage_validation.asset_class_stats`, and
# per-strategy from `flagged_strategies`) and overwrites the class table with the
# measured value, so audit3 and the canonical view price execution identically.
# The old constants were above measured for CRYPTO/EQUITY/ETF/FOREX (conservative)
# and BELOW it for FUTURES/COMMODITY (optimistic), which meant a futures verdict
# could survive a cost it never paid.
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

#: Measured per-strategy round-trip cost in percent, keyed by casefolded strategy.
#: Filled from the payload's slippage_validation.flagged_strategies.
STRATEGY_SLIPPAGE_PCT: dict[str, float] = {}
#: What the last load actually applied, for the report's provenance block.
COST_BASIS: dict[str, Any] = {}

#: A class cost is only trusted when it rests on this many measured closes.
MIN_COST_SAMPLE = 30

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


def _circular_blocks(rng: random.Random, n: int, block_len: int) -> list[int]:
    """Circular moving-block index sequence covering n positions.

    Each block starts at a uniform random offset and wraps around the end of the
    series, so every position is reachable from any start. The sequence is
    truncated to exactly n positions.
    """
    idx: list[int] = []
    while len(idx) < n:
        j = rng.randrange(n)
        for t in range(block_len):
            idx.append((j + t) % n)
    return idx[:n]


def bootstrap_mean_ci(values: list[float], n_boot: int = BOOT_N,
                      seed: int = BOOT_SEED,
                      block: bool = False) -> dict[str, Any]:
    """Percentile bootstrap 95% CI for the mean. Deterministic per seed.

    ``block=True`` uses a circular moving-block bootstrap with block length
    ``~sqrt(n)``, which preserves temporal autocorrelation and widens the CI when
    trades are clustered in time -- the honest interval for overlapping
    positions, and the only one that keeps the G2 edge gate honest. The default
    (``block=False``) is the historical i.i.d. resample and is unchanged, so a
    call that does not opt in cannot silently alter a verdict.
    """
    n = len(values)
    if n < 2:
        return {"mean": (values[0] if values else 0.0), "ci_lo": None,
                "ci_hi": None, "frac_positive": None, "n_boot": 0}
    rng = random.Random(seed)
    block_len = max(1, int(math.sqrt(n))) if block else 1
    means = []
    for _ in range(n_boot):
        if block and block_len > 1:
            idx = _circular_blocks(rng, n, block_len)
            s = sum(values[i] for i in idx) / n
        else:
            s = 0.0
            for _ in range(n):
                s += values[rng.randrange(n)]
            s /= n
        means.append(s)
    means.sort()
    return {
        "mean": sum(values) / n,
        "ci_lo": means[int(0.025 * n_boot)],
        "ci_hi": means[int(0.975 * n_boot) - 1],
        "frac_positive": sum(1 for m in means if m > 0) / n_boot,
        "n_boot": n_boot,
        "bootstrap_mode": "block" if block else "iid",
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


def split_half_ok(values: list[float],
                   min_mean: float = 0.0) -> tuple[bool, dict[str, float]]:
    """Chronological split-half stability.

    Both halves must have a mean strictly above ``min_mean`` (default 0.0
    preserves the historical "positive mean" requirement). Passing a materiality
    floor (F2, 2026-11-19) stops a microscopically-positive half from counting as
    stable when a cell is promoted.
    """
    if len(values) < 10:
        return False, {}
    mid = len(values) // 2
    first, second = values[:mid], values[mid:]
    m1 = sum(first) / len(first) if first else 0.0
    m2 = sum(second) / len(second) if second else 0.0
    return (m1 > min_mean and m2 > min_mean), {"first_half_mean": m1, "second_half_mean": m2}


def recency_ok(rows: list[dict], nets: list[float],
               fraction: float = RECENCY_WINDOW_FRACTION,
               min_trades: int = RECENCY_MIN_TRADES) -> tuple[bool, dict[str, Any]]:
    """Trailing-window sanity check (N3).

    The last ``max(min_trades, round(fraction * n))`` closes must have a
    non-negative net mean. Rows are ordered by ``closed_at``/``timestamp`` so a
    caller passing an unsorted slice is still measured on the true recent window.
    """
    n = len(nets)
    if n == 0:
        return False, {"window_trades": 0, "window_net_mean": None}
    pairs = list(zip(rows, nets))

    def stamp(row: dict) -> datetime:
        return (_to_dt(row.get("closed_at") or row.get("timestamp"))
                or datetime.min.replace(tzinfo=timezone.utc))

    pairs.sort(key=lambda pair: stamp(pair[0]))
    k = min(n, max(min_trades, int(round(fraction * n))))
    tail = [net for _, net in pairs[-k:]]
    mean = sum(tail) / len(tail)
    return mean >= 0.0, {
        "window_trades": k,
        "window_frac": round(k / n, 4),
        "window_net_mean": round(mean, 4),
    }


# ────────────────────────────────────────────────────────────────── loading ──
#: Set by :func:`load_rows` — which denominator this process actually loaded, and
#: why (hash-verified sidecar vs fallback). Read by :func:`payload_coverage`.
LAST_DENOMINATOR: dict[str, Any] = {}


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


def load_rows(path: str, drops: dict[str, int] | None = None
              ) -> tuple[list[dict], str | None]:
    """Load closed picks and the ledger's own generated_at, if present.

    drops: optional counter filled with why input rows did not become a scored
    row. The export slice is already filtered upstream, so a page that only
    reports ``len(rows)`` silently hides both those filters and these ones.
    """
    LAST_DENOMINATOR.clear()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _apply_measured_costs(data)
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
    # Canonical view (review action A2). The publishing dashboard writes
    # resolved_closed_picks_net.json next to the payload; when its row hash matches
    # the block embedded in the payload, score THOSE rows. /audit counts the same
    # book, so the two surfaces cannot disagree about n without one of them being
    # visibly wrong. Absent or hash-mismatched sidecar → fall back to the export
    # slice below, and `payload_coverage` records which denominator was used.
    if isinstance(data, dict):
        _block = data.get("resolved_closed_picks_net")
        if isinstance(_block, dict):
            try:
                from alpha_engine.resolved_closed_view import load_sidecar
                _view = load_sidecar(path, _block)
            except Exception:
                _view = None
            if _view and isinstance(_view.get("rows"), list) and len(_view["rows"]) >= 100:
                rows = _view["rows"]
                LAST_DENOMINATOR.update({
                    "mode": "canonical",
                    "rows_sha256": _view.get("rows_sha256"),
                    "kept_rows": len(_view["rows"]),
                    "reason": "sidecar_loaded_and_hashed",
                })
            else:
                # The block exists but the rows behind it do not match (absent,
                # unreadable, or a different hash). Record the FACT; do not infer
                # it from row counts, because a 3,500-row export slice and a
                # 3,500-row canonical book are indistinguishable by size.
                LAST_DENOMINATOR.update({
                    "mode": "payload_slice",
                    "rows_sha256": None,
                    "kept_rows": ((_block.get("counts") or {}).get("kept_rows")),
                    "reason": "sidecar_missing_or_hash_mismatch",
                })
        else:
            LAST_DENOMINATOR.update({"mode": "payload_slice", "rows_sha256": None,
                                     "kept_rows": None,
                                     "reason": "no_canonical_block"})

    if not rows:
        raise ValueError(f"no closed-pick list found in {path}")

    seen: set[str] = set()
    clean: list[dict] = []
    drop = drops if drops is not None else {}
    for r in rows:
        if not isinstance(r, dict):
            drop["not_a_record"] = drop.get("not_a_record", 0) + 1
            continue
        pnl = r.get("pnl_pct")
        if not isinstance(pnl, (int, float)):
            drop["no_numeric_pnl"] = drop.get("no_numeric_pnl", 0) + 1
            continue
        status = str(r.get("status") or "").upper()
        if status in ("OPEN", "PENDING", ""):
            drop["not_closed"] = drop.get("not_closed", 0) + 1
            continue
        key = str(r.get("id") or "") or (
            f"{r.get('strategy')}|{r.get('symbol')}|{r.get('direction')}|"
            f"{r.get('closed_at') or r.get('timestamp')}|{pnl}")
        if key in seen:
            drop["duplicate"] = drop.get("duplicate", 0) + 1
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


def _coverage_statement(scored: int, total: int | None, integrity: int | None,
                        expired: int | None, overlap: bool) -> str:
    if not total:
        return ("The source payload carries no closed-book counts, so this ledger "
                f"cannot state what share of the book its {scored:,} scored rows "
                "represent.")
    share = 100.0 * scored / total
    parts = []
    if integrity:
        parts.append(f"{integrity:,} integrity-excluded")
    if expired:
        parts.append(f"{expired:,} auto-expired")
    txt = (f"audit3 scores {scored:,} of {total:,} closed picks ({share:.1f}%). "
           f"The other {max(0, total - scored):,} are not in this ledger")
    if parts:
        txt += (": the publishing dashboard reports " + " and ".join(parts)
                + " rows, and no surface scores any of them.")
    else:
        txt += "."
    if overlap:
        txt += (" Those cohorts overlap, so they do not sum to the gap — read them as "
                "reasons rows are missing, not as a partition.")
    return txt


def payload_coverage(data: Any, scored_rows: list[dict],
                     drops: dict[str, int] | None = None) -> dict[str, Any]:
    """How much of the published closed book this ledger actually judges.

    The tribunal reads ``picks.recent_closed``, which is an export slice, not the
    whole closed book: the publishing dashboard also reports cohorts it removes
    before export (integrity failures, auto-expiries). Without this block the page
    implies its verdicts cover every closed pick, which they do not.
    """
    summary = data.get("summary") if isinstance(data, dict) else None
    summary = summary if isinstance(summary, dict) else {}

    def _int(key: str) -> int | None:
        v = summary.get(key)
        return int(v) if isinstance(v, (int, float)) else None

    total = _int("total_closed_picks")
    valid = _int("valid_closed_picks")
    integrity = _int("integrity_excluded")
    expired = _int("auto_expired_excluded")
    resolved = _int("total_resolved")
    zero_pnl = _int("zero_pnl_count")
    anomalies = summary.get("resolver_anomalies")
    anomalies = anomalies if isinstance(anomalies, dict) else {}
    scored = len(scored_rows)
    stamps = sorted(s for s in ((r.get("closed_at") or r.get("timestamp"))
                                for r in scored_rows)
                    if isinstance(s, str) and s)

    excluded: list[dict[str, Any]] = []
    if integrity:
        excluded.append({
            "cohort": "integrity_excluded", "n": integrity,
            "reason": "failed the publishing dashboard's own integrity checks "
                      "(ghost rows, WON-vs-PnL sign contradictions, constant/zero "
                      "pnl) and is removed before the export slice",
        })
    if expired:
        excluded.append({
            "cohort": "auto_expired", "n": expired,
            "reason": "resolved by timeout instead of TP/SL; a timeout is neither a "
                      "win nor a loss, so it is dropped before scoring and never "
                      "counted against the strategy either",
        })
    overlap = bool(total and integrity and expired and integrity + expired > total)

    # A2: which denominator did this run actually score? 'canonical' means the
    # row count equals the published resolved_closed_picks_net view, so a reader
    # can compare this page against /audit without guessing.
    canon = data.get("resolved_closed_picks_net") if isinstance(data, dict) else None
    canon = canon if isinstance(canon, dict) else {}
    canon_counts = canon.get("counts") if isinstance(canon.get("counts"), dict) else {}
    canon_kept = canon_counts.get("kept_rows")
    # Authoritative only when the load stage recorded a hash-verified sidecar for
    # THIS book (same kept_rows), so a stale module-level record cannot leak in.
    den_state = LAST_DENOMINATOR if LAST_DENOMINATOR.get("kept_rows") == canon_kept else {}
    loaded_from_sidecar = den_state.get("mode") == "canonical"
    canonical_mode = bool(loaded_from_sidecar and canon_kept and scored == canon_kept)
    denominator = {
        "mode": "canonical" if canonical_mode else "payload_slice",
        "loaded_from_sidecar": loaded_from_sidecar,
        "fallback_reason": (None if canonical_mode
                            else den_state.get("reason") or "no_canonical_block"),
        "canonical_schema": canon.get("schema"),
        "canonical_rows_sha256": canon.get("rows_sha256"),
        "canonical_kept_rows": canon_kept,
        "canonical_excluded_by_reason": canon_counts.get("excluded_by_reason"),
        "share_of_canonical_pct": (round(100.0 * scored / canon_kept, 2)
                                   if canonical_mode and canon_kept else None),
        "note": ("scores the published canonical view; /audit counts the same rows"
                 if canonical_mode else
                 "scores the payload export slice — the canonical view was absent, "
                 "stale, or hashed differently, so this is NOT the same denominator "
                 "as /audit"),
    }
    # A "share of valid" above 100% is not a rounding artefact: `scored` can be
    # the canonical view while `valid_closed_picks` comes from a narrower payload
    # summary. Publishing 105% invites misreading, so null it with the reason.
    share_of_valid = (round(100.0 * scored / valid, 2) if valid else None)
    share_of_valid_note = None
    if share_of_valid is not None and share_of_valid > 100.0:
        share_of_valid_note = (
            "not comparable: the scored rows come from the canonical view while "
            "valid_closed_picks comes from the payload summary, so the ratio "
            f"exceeded 100% ({share_of_valid}%)")
        share_of_valid = None

    cov_statement = _coverage_statement(scored, total, integrity, expired, overlap)
    if canonical_mode:
        cov_statement = (f"{cov_statement} This run scores the canonical resolved "
                         f"view (sha256 {str(canon.get('rows_sha256'))[:12]}…).")

    return {
        "denominator": denominator,
        "scored_rows": scored,
        "total_closed_picks": total,
        "valid_closed_picks": valid,
        "total_resolved": resolved,
        "zero_pnl_count": zero_pnl,
        "scored_share_of_total_pct": (round(100.0 * scored / total, 2)
                                      if total else None),
        "scored_share_of_valid_pct": share_of_valid,
        "scored_share_of_valid_pct_status": ("ok" if share_of_valid is not None
                                            else "not_comparable"),
        "scored_share_of_valid_note": share_of_valid_note,
        "unscored_rows": (max(0, total - scored) if total else None),
        "cohorts_overlap": overlap,
        "excluded_cohorts": excluded,
        "row_drops": dict(sorted((drops or {}).items())),
        "window": {"first_closed_at": stamps[0] if stamps else None,
                   "last_closed_at": stamps[-1] if stamps else None},
        "resolver_anomalies": {k: v for k, v in anomalies.items()
                               if isinstance(v, (int, float))},
        "statement": cov_statement,
    }


# ─────────────────────────────────────────────────────────────────── cells ──
def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _cost_pct(r: dict) -> float:
    """Round-trip cost for one row: measured per-strategy, else measured class."""
    strat = str(r.get("strategy") or "").strip().casefold()
    if strat:
        measured = STRATEGY_SLIPPAGE_PCT.get(strat)
        if measured is not None:
            return measured
    ac = str(r.get("asset_class") or "UNKNOWN").upper()
    return SLIPPAGE_PCT.get(ac, DEFAULT_SLIPPAGE_PCT)


def _net(r: dict) -> float:
    return float(r["pnl_pct"]) - _cost_pct(r)


def materiality_floor(mean_cost_pct: float) -> float:
    """N4: per-cell promotion floor, scaled by the applied cost model."""
    return max(PROVEN_MIN_NET_CI_LO_PCT,
               MATERIALITY_COST_FRACTION * float(mean_cost_pct))


def _apply_measured_costs(data: Any) -> dict[str, Any]:
    """Adopt the dashboard's measured slippage for this run.

    Reads `slippage_validation.asset_class_stats` (per-class measured mean) and
    `flagged_strategies` (per-strategy measured mean). A class with fewer than
    MIN_COST_SAMPLE measured closes keeps the flat fallback rather than inheriting
    a noisy estimate. Never raises: a payload without the block prices exactly as
    before and the report says so.
    """
    sv = (data or {}).get("slippage_validation") if isinstance(data, dict) else None
    sv = sv if isinstance(sv, dict) else {}
    applied: dict[str, float] = {}
    for ac, row in (sv.get("asset_class_stats") or {}).items():
        row = row if isinstance(row, dict) else {}
        pct = _num(row.get("avg_slippage_pct"))
        n = _num(row.get("n")) or 0
        if pct and pct > 0 and n >= MIN_COST_SAMPLE:
            applied[str(ac).upper()] = round(pct, 4)
    strat: dict[str, float] = {}
    flagged = sv.get("flagged_strategies")
    if isinstance(flagged, dict):
        for name, row in flagged.items():
            row = row if isinstance(row, dict) else {}
            pct = _num(row.get("avg_slippage_pct"))
            if pct and pct > 0:
                strat[str(name).strip().casefold()] = round(pct, 4)
    if applied:
        SLIPPAGE_PCT.update(applied)
    STRATEGY_SLIPPAGE_PCT.clear()
    STRATEGY_SLIPPAGE_PCT.update(strat)
    COST_BASIS.clear()
    COST_BASIS.update({
        "model": "measured" if applied else "flat_fallback",
        "class_cost_pct": dict(sorted(SLIPPAGE_PCT.items())),
        "n_strategy_costs": len(strat),
        "min_cost_sample": MIN_COST_SAMPLE,
        "source": "payload.slippage_validation" if sv else "none",
        "note": ("per-strategy measured where available, measured class otherwise"
                 if applied else
                 "payload carried no measured slippage; flat class constants used"),
    })
    return dict(COST_BASIS)


def _direction(r: dict) -> str:
    """BUY/SELL/L/S all normalise onto LONG/SHORT so the denylist can match."""
    return _dir_key(r.get("direction")) or "UNKNOWN"


def _family(r: dict) -> str:
    hay = f"{r.get('strategy') or ''} {r.get('source_system') or ''} {r.get('system') or ''}".lower()
    for name, pats in FAMILY_PATTERNS:
        if any(p in hay for p in pats):
            return name
    return "other"


DEFAULT_CONFIRMATORY = "reports/audit3_confirmatory.json"


def load_confirmatory(path: str | None = None) -> dict[str, Any]:
    """Load the pre-registered pod manifest (``reports/audit3_confirmatory.json``).

    An empty or missing manifest is not an error: it means nothing has been
    pre-registered, so every cell is discovery and nothing may be promoted.
    """
    target = path or DEFAULT_CONFIRMATORY
    try:
        with open(target, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        return {"available": False, "path": target, "pods": [], "error": str(exc)}
    pods = [p for p in (data.get("pods") or []) if isinstance(p, dict)]
    return {"available": True, "path": target, "pods": pods,
            "rule": data.get("rule")}


def _pod_for(asset_class: str, strategy: str, direction: str,
             manifest: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return the pod that pre-registered this cell, else None."""
    if not manifest:
        return None
    name = str(strategy or "").strip().casefold()
    for pod in manifest.get("pods") or []:
        # Only a pod declared as pre-registered may confer confirmatory status. A pod
        # extracted from the results being judged (post_hoc), one we have declined,
        # or one still in observe (registered but below the forward floor) would
        # launder rows into a promotion.
        if str(pod.get("status") or "").strip().lower() != "pre_registered":
            continue
        strategies = {str(s).strip().casefold() for s in (pod.get("strategies") or [])}
        classes = {str(c).strip().upper() for c in (pod.get("asset_classes") or [])}
        directions = {str(d).strip().upper() for d in (pod.get("directions") or [])}
        if not (strategies or classes or directions):
            continue  # a pod with no matcher would capture everything
        if strategies and name not in strategies:
            continue
        if classes and str(asset_class).upper() not in classes:
            continue
        if directions and str(direction).upper() not in directions:
            continue
        return pod
    return None


def evaluate_cell(rows: list[dict], n_trials: int, label: dict[str, Any],
                  *, apply_source_gate: bool = True,
                  n_trials_local: int | None = None) -> dict[str, Any]:
    """Compute every gate for one cell. Never raises.

    apply_source_gate: a single strategy is normally emitted by one source
    system, so source concentration is only meaningful for aggregate cells
    (asset class, source family). Per-strategy/symbol cells pass False.

    n_trials: global search-space size for the PROVEN DSR gate (G4).
    n_trials_local: observed bucket width, used for the CANDIDATE tier only.
    """
    nets = [_net(r) for r in rows]
    n = len(nets)
    wins = sum(1 for v in nets if v > 0)
    wr = wins / n if n else 0.0
    lo, hi = wilson_interval(wins, n) if n else (0.0, 1.0)
    pf = profit_factor(nets)
    # F1 (2026-11-19): block bootstrap — overlapping picks are not i.i.d., so the
    # G2 net-expectancy CI uses the circular block bootstrap to avoid overstating
    # precision. The cost-stress companion uses the same block mode.
    boot = bootstrap_mean_ci(nets, block=True) if n >= 2 else {"mean": 0.0,
                                                               "ci_lo": None,
                                                               "ci_hi": None,
                                                               "frac_positive": None}
    # Cost-stress companion: the same net CI at twice the class slippage. It is
    # a required gate for PROVEN_T2 and CANDIDATE (an edge that dies at 2x cost
    # is a cost assumption, not skill); it is still reported on every cell.
    nets_2x = [float(r["pnl_pct"]) - 2.0 * _cost_pct(r) for r in rows]
    boot_2x = bootstrap_mean_ci(nets_2x, block=True) if n >= 2 else {"ci_lo": None, "ci_hi": None}
    mean_cost = (sum(_cost_pct(r) for r in rows) / n) if n else 0.0
    floor_pct = materiality_floor(mean_cost)
    stable, halves = split_half_ok(nets, min_mean=floor_pct)
    # Edge test (2026-11-19): expectancy, not P(win). A trend cell at WR 35% with
    # a 2.5 payoff is positive expectancy and cannot be judged by "won more often
    # than not"; a 60% WR cell with PF < 1 (EQUITY) is negative expectancy and
    # must not be promoted. WR stays a reported descriptor.
    p_wr = binom_sf(wins, n) if n else 1.0
    frac_pos = boot.get("frac_positive")
    if frac_pos is not None:
        # Bootstrap p with the +1 resolution correction: 2,000 resamples cannot
        # support "p = 0", and a zero p would hand the top-ranked cell a BH
        # q of exactly 0 — infinite certainty from a finite simulation.
        n_boot = int(boot.get("n_boot") or BOOT_N)
        n_le = int(round((1.0 - frac_pos) * n_boot))
        n_ge = int(round(frac_pos * n_boot))
        p_exp = (n_le + 1.0) / (n_boot + 1.0)
        p_harm = (n_ge + 1.0) / (n_boot + 1.0)
    else:
        p_exp = p_harm = 1.0
    symbols = [_canon_symbol(r.get("symbol"), r.get("asset_class")) or "?"
               for r in rows]
    top_sym_share = (max(symbols.count(s) for s in set(symbols)) / n) if n else 0.0
    sources = [str(r.get("source_system") or r.get("system") or "?") for r in rows]
    top_src_share = (max(sources.count(s) for s in set(sources)) / n) if n else 0.0

    reasons: list[str] = []
    verdict = "INSUFFICIENT_N"
    if n >= WR_MIN_N:
        ci_lo, ci_hi = boot.get("ci_lo"), boot.get("ci_hi")
        expect_ci_negative = ci_hi is not None and ci_hi < 0
        expect_ci_positive = ci_lo is not None and ci_lo > 0
        if expect_ci_negative:
            verdict = "KILL"
            reasons.append("net expectancy 95% CI entirely below zero")
            if pf is not None and pf < HARM_PF_WATCH:
                reasons.append(f"profit factor {pf:.2f} < {HARM_PF_WATCH}")
            if wr < 0.40:
                reasons.append(f"win rate {wr:.1%} below 40%")
        elif pf is not None and pf < HARM_PF_WATCH and n >= KILL_PF_N:
            # Innocent until proven guilty: PF alone is a watch flag. Killing on
            # it would discard cells whose net CI still includes zero -- exactly
            # the "one asset class keeps winning inside a bad-looking section"
            # case the section matrix exists to surface.
            lo_s = "n/a" if boot.get("ci_lo") is None else f"{boot['ci_lo']:+.2f}"
            hi_s = "n/a" if boot.get("ci_hi") is None else f"{boot['ci_hi']:+.2f}"
            verdict = "WEAK"
            reasons.append(
                f"profit factor {pf:.2f} < {HARM_PF_WATCH} at n={n} — watch only, "
                f"harm not proven (net CI [{lo_s}, {hi_s}]) so it keeps observing")
        elif (n >= PROVEN_MIN_N
              and expect_ci_positive
              and (boot.get("ci_lo") if boot.get("ci_lo") is not None else -1.0)
              >= floor_pct
              and boot.get("mean", 0) > 0
              and stable and top_sym_share <= MAX_SYMBOL_SHARE
              and (not apply_source_gate or top_src_share <= MAX_SOURCE_SHARE)
              and boot_2x.get("ci_lo") is not None and boot_2x["ci_lo"] > 0):
            verdict = "PROVEN_T2"
            if top_src_share > MAX_SOURCE_SHARE:
                # A single emitter can be PROVEN on the ledger; it is not
                # sizing-eligible until an independent source replicates it.
                reasons.append(
                    f"single source {top_src_share:.0%} of trades — proven on the "
                    "ledger, not sizing-eligible until replicated independently")
        elif (n >= CANDIDATE_MIN_N and boot.get("mean", 0) > 0
              and expect_ci_positive
              and (not apply_source_gate or top_src_share <= MAX_SOURCE_SHARE)
              and boot_2x.get("ci_lo") is not None and boot_2x["ci_lo"] > 0):
            verdict = "CANDIDATE"
        else:
            verdict = "WEAK"
            if not expect_ci_positive:
                # The primary blocker: the edge is not distinguishable from zero.
                # Without this line a cell with a high WR, stable halves and no
                # concentration ended up WEAK with reasons==[] (11 live cells).
                lo_s = "n/a" if ci_lo is None else f"{ci_lo:+.3f}"
                reasons.append(
                    f"net-expectancy CI lower bound {lo_s} <= 0 — edge not "
                    "distinguishable from zero")
            if wr < 0.5:
                reasons.append(f"win rate {wr:.1%} <= 50%")
            if not stable:
                reasons.append("split-half unstable (one half mean <= 0)")
            if top_sym_share > MAX_SYMBOL_SHARE:
                reasons.append(f"single symbol {top_sym_share:.0%} of trades")
            if apply_source_gate and top_src_share > MAX_SOURCE_SHARE:
                reasons.append(f"single source {top_src_share:.0%} of trades")
            if (n >= CANDIDATE_MIN_N and expect_ci_positive
                    and boot.get("mean", 0) > 0
                    and not (boot_2x.get("ci_lo") is not None and boot_2x["ci_lo"] > 0)):
                reasons.append("fails 2x-cost stress gate (net CI at 2x slippage crosses zero)")
    else:
        reasons.append(f"n={n} < {WR_MIN_N}: no statistical claim")

    # Power / MDE: how many trades this cell would need to confirm an edge of
    # its observed size at 80% power (two-sided 5%), and the smallest effect
    # the current n can detect. The n>=100 floor is a floor; this is the
    # effect-sized number that tells a reader how far a cell still has to go.
    sd = statistics.stdev(nets) if n >= 2 else None
    mean_net = boot.get("mean", 0.0)
    required_n = None
    mde_pct = None
    if sd is not None and sd > 0 and mean_net:
        required_n = int(math.ceil((2.8 * sd / abs(mean_net)) ** 2))
        mde_pct = round(2.8 * sd / math.sqrt(n), 4)
    # N3 (recency/regime): an edge that came from a stale regime must not be
    # promoted on the full-history statistic alone.
    recent_ok, recency = recency_ok(rows, nets)
    if verdict == "PROVEN_T2" and not recent_ok:
        verdict = "CANDIDATE"
        reasons.append(
            f"recency: trailing {recency['window_trades']} trades net mean "
            f"{recency['window_net_mean']:+.4f}% < 0 — capped at CANDIDATE")

    out = dict(label)
    out.update({
        "n": n,
        "required_n": required_n,
        "mde_pct": mde_pct,
        "wins": wins,
        "wr": round(wr, 4),
        "wr_ci": [round(lo, 4), round(hi, 4)],
        "pf": round(pf, 4) if pf is not None else None,
        "gross_expectancy_pct": round(sum(float(r["pnl_pct"]) for r in rows) / n, 4) if n else 0.0,
        "net_expectancy_pct": round(boot.get("mean", 0.0), 4),
        "net_ci_pct": [round(boot["ci_lo"], 4) if boot.get("ci_lo") is not None else None,
                       round(boot["ci_hi"], 4) if boot.get("ci_hi") is not None else None],
        "p_value": round(p_exp, 6),        # expectancy test — the BH family
        "p_wr": round(p_wr, 6),            # WR descriptor, not a promotion gate
        "q_value": None,  # filled after BH across the family
        "p_harm": round(p_harm, 6),        # bootstrap P(net mean >= 0)
        "harm_q": None,   # filled after BH across the killed cells
        "net_ci_pct_2x": [round(boot_2x["ci_lo"], 4) if boot_2x.get("ci_lo") is not None else None,
                          round(boot_2x["ci_hi"], 4) if boot_2x.get("ci_hi") is not None else None],
        "stress_2x_ok": bool(boot_2x.get("ci_lo") is not None and boot_2x["ci_lo"] > 0),
        "dsr": None,
        "split_half": ({"stable": stable, **{k: round(v, 4) for k, v in halves.items()}}
                       if halves else None),
        "recency": recency,
        "recent_ok": recent_ok,
        "mean_cost_pct": round(mean_cost, 4),
        "materiality_floor_pct": round(floor_pct, 4),
        "top_symbol_share": round(top_sym_share, 4),
        "top_source_share": round(top_src_share, 4),
        "single_source": bool(top_src_share > MAX_SOURCE_SHARE),
        "verdict": verdict,
        "reasons": reasons,
    })
    # DSR is reported only inside the gated family (n >= WR_MIN_N). Showing a DSR
    # on a cell that is excluded from BH/Bonferroni told a second, inconsistent
    # multiplicity story (45 tested vs 59 DSR-scored).
    if n >= WR_MIN_N:
        dsr = deflated_sharpe(nets, n_trials)
        if dsr:
            out["dsr"] = round(dsr["dsr"], 4)
            # A DSR without its trial count is not a multiplicity correction.
            # Publish it on every bucket so a class DSR of 0.9 with n_trials=1
            # becomes impossible to display.
            out["dsr_n_trials"] = int(n_trials)
            out["sharpe"] = round(dsr["sharpe"], 4)
            out["sr0"] = round(dsr["sr0"], 4)
        if n_trials_local is not None and n_trials_local != n_trials:
            if int(n_trials_local) >= 2:
                dloc = deflated_sharpe(nets, int(n_trials_local))
                if dloc:
                    out["dsr_local"] = round(dloc["dsr"], 4)
                    out["dsr_local_n_trials"] = int(n_trials_local)
            else:
                out["dsr_local"] = None
    return out


def _group(rows: list[dict], key_fn) -> dict[Any, list[dict]]:
    out: dict[Any, list[dict]] = {}
    for r in rows:
        out.setdefault(key_fn(r), []).append(r)
    return out


def _promote(cell: dict, forward: dict[str, Any] | None = None) -> None:
    """Apply the FDR, DSR and forward-evidence gates.

    forward: the block from forward_gate_block(). Only PROVEN_T2 is affected, and
    only for its own pod's rows. ``None`` means the caller supplied no forward
    evidence (library callers, unit tests) and preserves pre-gate behaviour; the
    CLI always supplies a block, so the published ledger is always gated.
    """
    if cell["n"] < WR_MIN_N:
        return
    # Multiplicity families are separate (2026-11-19): a pre-registered pod must
    # not share a BH budget with 40+ exploratory cells, and only a pod may be
    # sizing-eligible. Discovery can reach CANDIDATE (forward paper), never PROVEN.
    if cell["verdict"] == "PROVEN_T2" and cell.get("namespace") != "confirmatory":
        cell["verdict"] = "CANDIDATE"
        cell["reasons"].append(
            "discovery namespace: promotion requires a pod in "
            "reports/audit3_confirmatory.json")
        # Stop here. Falling through would re-judge the demoted cell in the
        # CANDIDATE branch and demote it again on a q-value it never faced as a
        # candidate (the discovery family is the larger one).
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
        if cell["verdict"] == "PROVEN_T2" and forward is not None:
            # The ledger can only re-score history. A pod is confirmed by forward
            # rows closed after it registered, never by the rows that motivated it.
            gate = (forward.get("pods") or {}).get(cell.get("pod") or "") or {}
            cell["forward_gate"] = {
                "pod": cell.get("pod"),
                "hypothesis_id": gate.get("hypothesis_id"),
                "since": gate.get("since"),
                "n_forward": gate.get("n_forward", 0),
                "min_n": gate.get("min_n"),
                "pf_ci_lb": gate.get("pf_ci_lb"),
                "ir": gate.get("ir"),
                "eligible": bool(gate.get("eligible")),
            }
            if not gate.get("eligible"):
                cell["verdict"] = "CANDIDATE"
                cell["reasons"].append(
                    "forward gate: " + "; ".join(
                        gate.get("reasons") or
                        ["no forward rows for this pod — PROVEN_T2 needs forward "
                         "evidence, not re-scored history"]))
    elif cell["verdict"] == "CANDIDATE":
        if q > CANDIDATE_Q:
            cell["verdict"] = "WEAK"
        else:
            # CANDIDATE is the forward-paper tier: judge it against the breadth
            # actually observed, not the whole 658-trial registry. When the local
            # DSR is not computable (bucket < 2 cells) fall back to the global,
            # multiplicity-corrected DSR — skipping the floor let a 1-local-trial
            # candidate escape the gate entirely.
            d_c = cell.get("dsr_local")
            if d_c is None:
                d_c = cell.get("dsr")
            if d_c is not None and d_c < 0.50:
                cell["verdict"] = "WEAK"
                cell["reasons"].append(f"DSR {d_c:.3f} < 0.50")


def apply_harm_gate(bucket: list[dict]) -> None:
    """Confirm KILL only when the negative result survives multiplicity.

    A raw 95% CI below zero is one test; with dozens of cells some will cross by
    chance. Killing is a destructive verdict, so it carries the same BH burden as
    promotion -- otherwise the tribunal throws away cells that are merely noisy.
    """
    negatives = [c for c in bucket if c["verdict"] == "KILL"]
    if not negatives:
        return
    for c, q in zip(negatives, benjamini_hochberg([c["p_harm"] for c in negatives])):
        c["harm_q"] = round(q, 6)
        if q > FDR_Q:
            c["verdict"] = "WEAK"
            c["reasons"].append(
                f"negative but harm q={q:.3f} > {FDR_Q}: not proven, keep observing")


# ─────────────────────────────────────────────── N1 repeated looks ──
_PERSISTENCE_KEY_FIELDS = ("asset_class", "strategy", "symbol", "direction",
                          "namespace", "pod", "segment", "segment_value", "family")


def cell_key(cell: dict) -> str:
    """Stable identity for a cell across runs, from its label fields only."""
    label = {k: cell.get(k) for k in _PERSISTENCE_KEY_FIELDS
             if cell.get(k) is not None}
    blob = json.dumps(label, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def load_history(path: str | None) -> dict[str, dict]:
    """Read the verdict-persistence sidecar. Missing/corrupt file -> empty."""
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    cells = data.get("cells") if isinstance(data, dict) else None
    return cells if isinstance(cells, dict) else {}


def save_history(path: str | None, history: dict[str, dict], *, run_at: str,
                 runs_required: int) -> None:
    if not path:
        return
    payload = {
        "schema": "audit3.verdict_history.v1",
        "updated_at": run_at,
        "persistence_runs": runs_required,
        "n_cells": len(history),
        "cells": history,
    }
    # Atomic write: a crash mid-write must not leave a truncated sidecar that
    # load_history silently reads as empty (which would reset every streak).
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=True, allow_nan=False)
        f.write("\n")
    os.replace(tmp, path)


def apply_persistence_gate(buckets: list[list[dict]], history: dict[str, dict],
                           *, run_at: str, runs_required: int = PERSISTENCE_RUNS
                           ) -> dict[str, int]:
    """Demote any CANDIDATE/PROVEN_T2 that has not persisted across K runs.

    ``history`` is mutated in place: for every cell seen this run it stores the
    consecutive-run streak of raw (pre-gate) passes, the first run that passed
    (``first_pass_at``), and the final verdict. A cell absent from this run has
    its streak reset, because persistence means consecutive runs, not cumulative
    runs with gaps.

    Returns counters for the report's ``persistence`` block.
    """
    seen: set[str] = set()
    demoted = 0
    promoted = 0
    for bucket in buckets:
        for cell in bucket:
            key = cell_key(cell)
            seen.add(key)
            rec = dict(history.get(key) or {})
            prior_ok = rec.get("last_raw_verdict") in PERSISTENCE_VERDICTS
            prior_passes = int(rec.get("passes") or 0)
            raw = cell.get("verdict")
            if raw in PERSISTENCE_VERDICTS:
                streak = prior_passes + 1 if prior_ok else 1
                first_pass_at = rec.get("first_pass_at") or run_at
                if streak < runs_required:
                    cell["verdict"] = "WEAK"
                    cell["reasons"].append(
                        f"repeated-looks: verdict persisted {streak}/{runs_required} "
                        "consecutive runs (BH is per-run; a single cross is not enough)")
                    demoted += 1
                else:
                    cell["first_pass_at"] = first_pass_at
                    promoted += 1
                rec["passes"] = streak
                rec["first_pass_at"] = first_pass_at
            else:
                rec["passes"] = 0
                rec["first_pass_at"] = None
            rec["last_raw_verdict"] = raw
            rec["last_verdict"] = cell.get("verdict")
            rec["last_seen"] = run_at
            history[key] = rec
            cell["raw_verdict"] = raw
    # A gap is not persistence: cells not scored this run lose their streak.
    for key in list(history):
        if key not in seen:
            history[key]["passes"] = 0
            history[key]["first_pass_at"] = None
    return {"demoted": demoted, "promoted": promoted}


def load_prev_verdicts(path: str | None) -> dict[str, str]:
    """Read verdicts from a previous ledger for the churn monitor."""
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for bucket in ("cells", "symbols", "classes", "segments"):
        for cell in data.get(bucket) or []:
            if not isinstance(cell, dict):
                continue
            # Only a ledger that already carries raw_verdict is comparable. A
            # legacy ledger stores post-gate final verdicts; comparing those to
            # today's raw verdicts would report a false churn spike on the
            # first N1/N3 run (and could trip --max-churn before anything is
            # written). Skip legacy rows rather than invent a comparison.
            verdict = cell.get("raw_verdict")
            if verdict:
                out[cell_key(cell)] = verdict
    return out


def compute_verdict_churn(buckets: list[list[dict]],
                          prev: dict[str, str]) -> dict[str, Any]:
    """Count cells whose raw verdict changed since the previous ledger.

    Compares raw verdicts (pre-persistence) so the N1 hold-at-WEAK delay does not
    register as instability. Alert only when enough cells are tracked.
    """
    tracked = 0
    flipped = 0
    flips: list[dict[str, Any]] = []
    for bucket in buckets:
        for cell in bucket:
            key = cell_key(cell)
            if key not in prev:
                continue
            tracked += 1
            now = cell.get("raw_verdict") or cell.get("verdict")
            if now != prev[key]:
                flipped += 1
                flips.append({
                    "asset_class": cell.get("asset_class"),
                    "strategy": cell.get("strategy") or cell.get("symbol"),
                    "direction": cell.get("direction"),
                    "from": prev[key], "to": now, "n": cell.get("n"),
                })
    rate = round(flipped / tracked, 4) if tracked else 0.0
    alert = bool(tracked >= CHURN_MIN_TRACKED and rate > CHURN_ALERT_THRESHOLD)
    return {
        "available": bool(prev),
        "n_tracked": tracked,
        "n_flipped": flipped,
        "churn_rate": rate,
        "alert_threshold": CHURN_ALERT_THRESHOLD,
        "min_tracked": CHURN_MIN_TRACKED,
        "alert": alert,
        "flips": flips[:50],
    }

# Which sidecar fields reach the published ledger. `by_class` was missing until
# 2026-11-19: per-class alpha was measured, used by the G8 gate, and then dropped
# by this whitelist, so the page could show a class gate "measured" with no number
# and no way to see why. `bar_coverage` was added at the same time so an
# "unmeasured" verdict carries its cause (no table / no symbol / stale bars).
ALPHA_PASSTHROUGH_KEYS: tuple[str, ...] = (
    "generated_at", "covered", "n_universe", "missing", "overall",
    "by_class", "by_slice", "by_strategy", "bar_coverage",
)


def demote_proven_without_alpha(buckets: Iterable[list[dict]]) -> int:
    """Fail-closed fallback for the published ledger when alpha is missing."""
    demoted = 0
    for bucket in buckets:
        for c in bucket:
            if c.get("verdict") != "PROVEN_T2":
                continue
            c["verdict"] = "CANDIDATE"
            c["reasons"].append(
                "G9 selection-alpha gate: alpha sidecar unavailable - PROVEN_T2 "
                "requires a measured selection alpha")
            demoted += 1
    return demoted


def apply_selection_alpha_gate(bucket: list[dict], alpha: dict | None) -> dict[str, Any]:
    """G9 - selection alpha must be proven at the same scope it proves.

    A cell profitable only because the underlying rose (market beta) must not
    reach PROVEN_T2. Alpha is looked up in order of decreasing specificity:

      * ``by_strategy[CLASS/STRATEGY/DIR]`` -> scope ``strategy`` (proves a cell)
      * ``by_slice[CLASS/DIR]`` / ``by_class[CLASS]`` -> scope ``class_proxy``
        for a strategy/symbol cell (informs, never proves)
      * a class aggregate is proved by ``by_class[CLASS]`` -> scope ``class``

    An unmeasured alpha demotes PROVEN_T2 but is not labelled beta-dominant
    (that would claim knowledge we do not have). A measured non-positive alpha
    is labelled beta-dominant. Coverage must reach max(20, 0.5*cell.n).

    Fail-open only when the sidecar is absent or empty. The published CLI path
    passes ``require_alpha=True`` to ``build_report``, which demotes instead.
    """
    if not isinstance(alpha, dict):
        return {"applied": False, "reason": "no alpha sidecar"}
    by_class = alpha.get("by_class") or {}
    by_slice = alpha.get("by_slice") or {}
    by_strategy = alpha.get("by_strategy") or {}
    if not by_class and not by_slice and not by_strategy:
        return {"applied": False, "reason": "alpha sidecar empty"}

    def _entry(entry: Any) -> tuple[float | None, float | None, int]:
        if not entry or not entry.get("n"):
            return None, None, 0
        ci = entry.get("alpha_ci") or [None, None]
        return ci[0], ci[1], int(entry.get("n") or 0)

    def _lookup(cell: dict) -> tuple[float | None, float | None, str, int]:
        ac = str(cell.get("asset_class") or "").strip().upper()
        d = str(cell.get("direction") or "").strip().upper()
        strat = cell.get("strategy")
        if strat:
            lo, hi, n = _entry(by_strategy.get(f"{ac}/{strat}/{d}"))
            if lo is not None:
                return lo, hi, "strategy", n
            lo, hi, n = _entry(by_slice.get(f"{ac}/{d}"))
            if lo is not None:
                return lo, hi, "class_proxy", n
            lo, hi, n = _entry(by_class.get(ac))
            return lo, hi, "class_proxy", n
        if cell.get("symbol"):
            lo, hi, n = _entry(by_slice.get(f"{ac}/{d}"))
            if lo is not None:
                return lo, hi, "class_proxy", n
            lo, hi, n = _entry(by_class.get(ac))
            return lo, hi, "class_proxy", n
        lo, hi, n = _entry(by_class.get(ac))
        return lo, hi, "class", n

    summary: dict[str, Any] = {"applied": True, "tested": 0, "demoted": 0, "scopes": {}}
    for c in bucket:
        lo, hi, scope, alpha_n = _lookup(c)
        cell_n = int(c.get("n") or 0)
        need_n = max(ALPHA_MIN_N, int(ALPHA_MIN_COVERAGE * cell_n))
        covered = alpha_n >= need_n
        proven = lo is not None and lo > 0 and scope in ("strategy", "class") and covered
        # "unproven" (CI straddles 0) is NOT "beta_dominant": the latter needs
        # evidence that alpha is negative, i.e. the whole CI below zero. Labelling
        # every null-alpha cell beta-dominant claimed knowledge we do not have and
        # made ~97% of cells look like a measured market failure.
        if lo is None:
            status = "unmeasured"
        elif lo > 0 and not covered:
            status = "insufficient_coverage"
        elif lo > 0 and scope not in ("strategy", "class"):
            status = "proxy"
        elif lo > 0:
            status = "proven"
        elif hi is not None and hi < 0:
            status = "beta_dominant"
        else:
            status = "unproven"
        c["alpha_gate"] = {"alpha_ci_lo": lo, "alpha_ci_hi": hi, "scope": scope,
                           "alpha_n": alpha_n, "need_n": need_n,
                           "alpha_coverage_ok": bool(covered),
                           "passed": bool(proven) if lo is not None else None,
                           "status": status}
        summary["tested"] += 1
        summary["scopes"][scope] = summary["scopes"].get(scope, 0) + 1
        if proven:
            continue
        if lo is None:
            if c["verdict"] == "PROVEN_T2":
                c["verdict"] = "CANDIDATE"
                summary["demoted"] += 1
                c["reasons"].append(
                    "G9 selection-alpha gate: selection alpha unmeasured - "
                    "promotion requires a positive CI lower bound")
            continue
        if status == "beta_dominant":
            c["beta_dominant"] = True
        if c["verdict"] == "PROVEN_T2":
            c["verdict"] = "CANDIDATE"
            summary["demoted"] += 1
            if lo <= 0:
                why = (f"selection alpha CI lower bound {lo:+.4f} not > 0 "
                       f"(status {status})")
            else:
                why = f"selection alpha covers {alpha_n}/{cell_n} rows (need {need_n})"
            c["reasons"].append(f"G9 selection-alpha gate ({scope}): {why}")
    return summary


def segment_tags(r: dict) -> list[tuple[str, str]]:
    """Reconstruct the published /audit section gates from fields the row carries.

    These are proxies, not the live gate decisions (the generator does not stamp
    the section name onto closed rows), so every segment cell is marked
    ``reconstructed: true``. The point is to see whether a section that looks bad
    in aggregate contains an asset class that wins again and again.
    """
    tags: list[tuple[str, str]] = []
    for field in ("trust_tier", "grade", "elite_grade"):
        val = str(r.get(field) or "").strip().upper()
        if val and val != "NONE":
            tags.append((field, val))
    score = _num(r.get("score"))
    if score is not None:
        tags.append(("score_gate", "score>=60" if score >= 60 else "score<60"))
    rr = _num(r.get("rr_ratio"))
    if rr is not None:
        tags.append(("rr_gate", "rr>=1.5" if rr >= 1.5 else "rr<1.5"))
    tags.append(("origin", "paper" if r.get("paper_trade") else "live"))
    if r.get("is_ac_survivor") is not None:
        tags.append(("survivor", "ac_survivor" if r.get("is_ac_survivor")
                     else "not_survivor"))
    fwd = _num(r.get("strat_fwd_trades"))
    if fwd is not None:
        tags.append(("forward_gate", "fwd_n>=20" if fwd >= 20 else "fwd_n<20"))
    return tags


def _sha256(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _git_sha() -> str | None:
    env = os.environ.get("GITHUB_SHA")
    if env:
        return env[:12]
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return (out.stdout or "").strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def forward_gate_block(manifest: dict[str, Any] | None,
                       ledger: str | None) -> dict[str, Any]:
    """Forward evidence per pre-registered pod, judged by the ledger's own rule.

    Only rows closed on/after the pod's ``registered_at`` count: a pod judged on
    rows that predate its registration is a backtest with extra steps. Hypotheses
    that are not pods are reported too, so an accruing lead is visible on the page
    without becoming promotable.
    """
    from alpha_engine import forward_observations as FO

    rows, read_errors = FO.load(ledger) if ledger else ([], [])
    block: dict[str, Any] = {
        "enforced": True,
        "rule": ("a pod's cell reaches PROVEN_T2 only when its own forward rows "
                 "(closed on/after registered_at) clear: "
                 f"n>={FO.PROMOTION_MIN_N}, net PF CI-LB > {FO.PROMOTION_PF_CI_LB} "
                 f"or IR >= {FO.PROMOTION_IR}, honest intrabar first-touch on 100%, "
                 f"benchmark coverage >= {FO.BENCHMARK_COVERAGE_MIN:.0%}"),
        "ledger": ledger,
        "n_rows": len(rows),
        "fingerprint": FO.ledger_fingerprint(ledger) if ledger else "absent",
        "read_errors": read_errors,
        "pods": {},
        "hypotheses": {},
    }
    for pod in (manifest or {}).get("pods") or []:
        status = str(pod.get("status") or "").strip().lower()
        # `observe` pods are shown so their forward clock is visible on /audit3,
        # but only pre_registered pods may promote a cell: an observe pod's rows
        # are informational by construction. Declined/post-hoc/retired are hidden.
        if status not in {"pre_registered", "observe"}:
            continue
        hid = str(pod.get("hypothesis_id") or "").strip().upper()
        since = str(pod.get("registered_at") or "").strip()
        subset = [r for r in rows
                  if str(r.get("hypothesis_id") or "").strip().upper() == hid
                  and not (since and str(r.get("closed_at") or "")[:10] < since[:10])]
        res = dict(FO.promotion(subset))
        if status != "pre_registered":
            res["eligible"] = False
            res["reasons"] = [f"pod is {status} - registered for observation only"]
            res["promotion_blocked_by_status"] = status
        res.update({"pod": pod.get("id"), "hypothesis_id": hid or None,
                    "status": status, "since": since or None})
        block["pods"][pod.get("id")] = res
    seen = sorted({str(r.get("hypothesis_id") or "").upper()
                   for r in rows if r.get("hypothesis_id")})
    for hid in seen:
        block["hypotheses"][hid] = FO.promotion(
            [r for r in rows if str(r.get("hypothesis_id") or "").upper() == hid])
    return block


def _denylist_hit_summary() -> dict[str, Any]:
    """What the emission gate blocked, from the CI-persisted hit log.

    Best-effort: a missing or unreadable log must never fail the ledger build.
    """
    try:
        from alpha_engine.audit3_denylist_hits import summarize
        s = summarize()
        return {
            "available": True,
            "n": s.get("n", 0),
            "first_ts": s.get("first_ts"),
            "last_ts": s.get("last_ts"),
            "by_class": s.get("by_class") or {},
            "top_strategies": dict(list((s.get("by_strategy") or {}).items())[:10]),
            "path": s.get("path"),
        }
    except Exception:
        return {"available": False, "n": 0}


def build_report(rows: list[dict], source: str, source_generated_at: str | None,
                 coverage: dict[str, Any] | None = None,
                 alpha: dict[str, Any] | None = None,
                 input_sha256: str | None = None,
                 confirmatory: dict[str, Any] | None = None,
                 forward: dict[str, Any] | None = None,
                 history: dict[str, dict] | None = None,
                 run_at: str | None = None,
                 persistence_runs: int = PERSISTENCE_RUNS,
                 prev_verdicts: dict[str, str] | None = None,
                 require_alpha: bool = False) -> dict[str, Any]:
    """Score every cell, then attach what the verdicts do NOT cover.

    coverage: from payload_coverage() — the share of the closed book being judged.
    alpha: optional sidecar from audit3_selection_alpha.py (needs price tables),
           merged onto the class aggregates so the class table can lead with
           selection skill instead of gross profit factor.
    history: verdict-persistence sidecar (N1). ``None`` disables the repeated-looks
             gate entirely, so a standalone run without the sidecar keeps the
             historical per-run behaviour.
    """
    run_at = run_at or datetime.now(timezone.utc).isoformat()
    n_cells = 0
    cells: list[dict] = []
    classes: list[dict] = []
    symbols: list[dict] = []
    families: list[dict] = []
    segments: list[dict] = []

    # PASS 1: count every distinct cell so DSR knows the FULL multiplicity. DSR
    # corrects for the number of hypotheses tried, so it must see the whole search
    # space, not only the n >= WR_MIN_N survivors; filtering first under-corrects
    # G4 and lets overfit cells clear the bar.
    strat_groups = _group(rows, lambda r: (str(r.get("asset_class") or "UNKNOWN").upper(),
                                           str(r.get("strategy") or r.get("source_system") or "(unattributed)"),
                                           _direction(r)))
    # P0-5: DSR is a multiple-testing correction, so the trial count is every
    # configuration that was emitted and scored -- not only the ones that
    # cleared the WR floor. Counting tested-only cells understated SR0.
    n_trials = global_trial_count(len(strat_groups))

    for (ac, strat, direction), group in strat_groups.items():
        pod = _pod_for(ac, strat, direction, confirmatory)
        label = {"asset_class": ac, "strategy": strat, "direction": direction,
                 "namespace": "confirmatory" if pod else "discovery"}
        if pod:
            label["pod"] = pod.get("id")
        cell = evaluate_cell(group, n_trials, label, apply_source_gate=False,
                             n_trials_local=len(strat_groups))
        cells.append(cell)
    cells.sort(key=lambda c: (-c["n"], c["asset_class"], c["strategy"]))

    # BH within each namespace separately, across tested cells only.
    tested = [c for c in cells if c["n"] >= WR_MIN_N]
    bh_families: dict[str, list[dict]] = {}
    for c in tested:
        bh_families.setdefault(c.get("namespace") or "discovery", []).append(c)
    for fam in bh_families.values():
        for c, q in zip(fam, benjamini_hochberg([c["p_value"] for c in fam])):
            c["q_value"] = round(q, 6)
            c["bh_family_n"] = len(fam)
    for c in tested:
        _promote(c, forward)
    apply_harm_gate(cells)

    # Class-level aggregate.
    class_groups = _group(rows, lambda r: str(r.get("asset_class") or "UNKNOWN").upper())
    class_trials = global_trial_count(len(class_groups))
    for ac, group in class_groups.items():
        cls = evaluate_cell(group, class_trials, {"asset_class": ac},
                            n_trials_local=len(class_groups))
        # Class promotion needs the stricter charter floor (n>=100).
        if cls["verdict"] == "PROVEN_T2" and cls["n"] < PROVEN_MIN_N:
            cls["verdict"] = "WEAK"
        classes.append(cls)
    for c, q in zip(classes, benjamini_hochberg([c["p_value"] for c in classes])):
        c["q_value"] = round(q, 6)
    for c in classes:
        _promote(c, forward)
    classes.sort(key=lambda c: (-c["n"], c["asset_class"]))

    # Symbol x direction cells (n>=20 only — the rest is noise by construction).
    # One instrument, one cell: BTC-USD and BTCUSDT are the same coin. Without
    # this the ledger split it into two verdicts (KILL at n=25 vs WEAK at n=120).
    sym_groups = _group(rows, lambda r: (str(r.get("asset_class") or "UNKNOWN").upper(),
                                         _canon_symbol(r.get("symbol"), r.get("asset_class")) or "?",
                                         _direction(r)))
    sym_tested = {k: g for k, g in sym_groups.items() if len(g) >= WR_MIN_N}
    for (ac, sym, direction), group in sym_tested.items():
        symbols.append(evaluate_cell(group, global_trial_count(len(sym_tested)),
                                     {"asset_class": ac, "symbol": sym,
                                      "direction": direction, "namespace": "discovery"},
                                     apply_source_gate=False,
                                     n_trials_local=len(sym_tested)))
    for c, q in zip(symbols, benjamini_hochberg([c["p_value"] for c in symbols])):
        c["q_value"] = round(q, 6)
    for c in symbols:
        _promote(c, forward)
    apply_harm_gate(symbols)
    symbols.sort(key=lambda c: (-c["n"], c["asset_class"], c["symbol"]))

    # Section x asset-class matrix. Answers "smart picks look bad overall, but
    # does one class inside them win again and again?" without trusting the
    # aggregate. Reconstruction proxies are declared on every cell.
    seg_groups: dict[tuple[str, str, str], list[dict]] = {}
    for r in rows:
        ac = str(r.get("asset_class") or "UNKNOWN").upper()
        for seg, val in segment_tags(r):
            seg_groups.setdefault((seg, val, ac), []).append(r)
    seg_tested = {k: g for k, g in seg_groups.items() if len(g) >= WR_MIN_N}
    for (seg, val, ac), group in seg_tested.items():
        seg_cell = evaluate_cell(group, global_trial_count(len(seg_tested)),
                                 {"segment": seg, "segment_value": val,
                                  "asset_class": ac, "namespace": "discovery"},
                                 apply_source_gate=False,
                                 n_trials_local=len(seg_tested))
        seg_cell["reconstructed"] = True
        segments.append(seg_cell)
    for c, q in zip(segments, benjamini_hochberg([c["p_value"] for c in segments])):
        c["q_value"] = round(q, 6)
    for c in segments:
        _promote(c, forward)
        # Section membership is reconstructed from row fields, not the live gate
        # decision, so a proxy may never carry the sizing-eligible verdict.
        if c["verdict"] == "PROVEN_T2":
            c["verdict"] = "CANDIDATE"
            c["reasons"].append("reconstructed section proxy: CANDIDATE is the ceiling")
    apply_harm_gate(segments)
    segments.sort(key=lambda c: (-c["net_expectancy_pct"], -c["n"]))

    # Source families: copytrader / polymarket / kalshi / ml_enhanced / ...
    fam_groups = _group(rows, _family)
    for fam, group in sorted(fam_groups.items(), key=lambda kv: -len(kv[1])):
        families.append(evaluate_cell(group, global_trial_count(len(fam_groups)),
                                      {"family": fam},
                                      n_trials_local=len(fam_groups)))
    # Families are verdict-bearing rows on the page, so they get the same gates
    # as every other bucket. Previously they skipped BH/DSR/forward/harm.
    fam_tested = [c for c in families if c["n"] >= WR_MIN_N]
    for c, q in zip(fam_tested, benjamini_hochberg([c["p_value"] for c in fam_tested])):
        c["q_value"] = round(q, 6)
    for c in families:
        _promote(c, forward)
    apply_harm_gate(families)

    # Selection alpha (M1b) joined onto the class aggregates when a sidecar was
    # supplied. Kept optional: it needs per-symbol OHLC, so a job without DB
    # credentials must still be able to publish an honest ledger.
    alpha_by_class = (alpha or {}).get("by_class") or {} if isinstance(alpha, dict) else {}
    for c in classes:
        a = alpha_by_class.get(c["asset_class"]) or {}
        if a.get("n"):
            c["alpha_pct"] = a.get("alpha_pct")
            c["alpha_ci"] = a.get("alpha_ci")
            c["alpha_n"] = a.get("n")
            c["alpha_wr"] = a.get("alpha_wr")
            c["hold_net_pct"] = a.get("hold_net_pct")
    # Selection-alpha gate: a cell whose picks do not beat holding the same
    # instrument over the same window is beta, not skill. It cannot be PROVEN_T2
    # even when its own net-expectancy CI is positive. Alpha is supplied per
    # asset class, so a class-level alpha governs every cell in that class. Only
    # applied when the sidecar supplied alpha for the class; absent data changes
    # nothing.
    for c in cells:
        if c.get("verdict") != "PROVEN_T2":
            continue
        a = alpha_by_class.get(c.get("asset_class")) or {}
        ci = a.get("alpha_ci")
        if not ci or ci[0] is None:
            continue
        if ci[0] <= 0:
            c["verdict"] = "CANDIDATE"
            c["reasons"].append(
                f"selection alpha CI includes zero (alpha {a.get('alpha_pct')}%/pick, "
                f"CI-LB {ci[0]}) - expectancy is beta, not skill")

    # N1 repeated-looks gate. Applied after every per-run gate (BH, DSR, harm) so
    # it is the last word on a claim, and only when a history sidecar is present.
    persistence_counters = {"demoted": 0, "promoted": 0}
    if history is not None:
        persistence_counters = apply_persistence_gate(
            [cells, symbols, classes, segments], history,
            run_at=run_at, runs_required=persistence_runs)
    # Stamp the pre-persistence verdict on every cell so the churn monitor
    # compares raw-with-raw even when the persistence gate is off.
    for _bucket in (cells, symbols, classes, segments):
        for _c in _bucket:
            _c.setdefault("raw_verdict", _c.get("verdict"))
    churn = compute_verdict_churn([cells, symbols, classes, segments],
                                  prev_verdicts or {})


    selection: dict[str, Any] = {
        "available": bool(alpha_by_class),
        "definition": "alpha = pick net return - direction-adjusted buy & hold over "
                      "the same entry..exit window (M1b)",
        "source": "alpha_engine/audit3_selection_alpha.py (needs the price tables)",
        "why_it_matters": "A +40% pick on a symbol that returned +60% is a selection "
                          "failure; a win-rate or PF table cannot see that.",
    }
    if isinstance(alpha, dict):
        for key in ALPHA_PASSTHROUGH_KEYS:
            if alpha.get(key) is not None:
                selection[key] = alpha[key]

    # G9 - selection alpha is a promotion gate, not just a class display column.
    # Applied to the strategy, symbol and class buckets (all direction-aware);
    # segments and source families are reconstructed/aggregate proxies.
    alpha_gate_report: dict[str, Any] = {"applied": False, "tested": 0,
                                         "demoted": 0, "scopes": {}}
    for bucket in (cells, symbols, classes):
        part = apply_selection_alpha_gate(bucket, alpha)
        if not part.get("applied"):
            alpha_gate_report.setdefault("reason", part.get("reason"))
            continue
        alpha_gate_report["applied"] = True
        alpha_gate_report["tested"] += part.get("tested", 0)
        alpha_gate_report["demoted"] += part.get("demoted", 0)
        for scope, count in (part.get("scopes") or {}).items():
            alpha_gate_report["scopes"][scope] = alpha_gate_report["scopes"].get(scope, 0) + count
    if require_alpha and not alpha_gate_report.get("applied"):
        # Published path: a missing sidecar must not read as "all cells passed".
        alpha_gate_report["require_alpha"] = True
        alpha_gate_report["demoted"] += demote_proven_without_alpha(
            (cells, symbols, classes))
    selection["gate"] = alpha_gate_report

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
        "n_cells_dsr_scored": sum(1 for c in cells if c.get("dsr") is not None),
        "n_confirmatory_cells": sum(1 for c in cells if c.get("namespace") == "confirmatory"),
        "n_discovery_cells": sum(1 for c in cells if c.get("namespace") == "discovery"),
        "n_proven": count("PROVEN_T2", cells),
        "n_candidate": count("CANDIDATE", cells),
        "n_weak": count("WEAK", cells),
        "n_kill": count("KILL", cells),
        "n_insufficient": count("INSUFFICIENT_N", cells),
        "kill_rate_pct": round(100.0 * count("KILL", cells) / len(tested), 2) if tested else 0.0,
        "n_proven_symbols": count("PROVEN_T2", symbols),
        "n_candidate_symbols": count("CANDIDATE", symbols),
        "n_weak_symbols": count("WEAK", symbols),
        "summary_scope": "cell-level: n_proven/n_candidate count strategy cells only; "
                         "symbol and class buckets are counted separately",
        "n_proven_classes": count("PROVEN_T2", classes),
        "n_kill_symbols": count("KILL", symbols),
        "n_segment_cells": len(segments),
        "n_proven_segments": count("PROVEN_T2", segments),
        "n_harmful_segments": count("KILL", segments),
        "n_positive_segments": sum(1 for c in segments
                                  if (c["net_ci_pct"][0] or 0) > 0),
        "n_kill_classes": count("KILL", classes),
    }

    cov = coverage if coverage is not None else payload_coverage(None, rows)
    provenance = {
        "population": cov["denominator"].get("mode"),
        "population_rows": cov.get("scored_rows"),
        "population_total": cov.get("total_closed_picks"),
        "cost_model": ("per-class round-trip slippage percent "
                       + ", ".join(f"{k}={v}" for k, v in sorted(SLIPPAGE_PCT.items()))
                       + "; the 2x stress gate doubles it"),
        "win_definition": "net pnl_pct > 0 after round-trip class slippage",
        "source": source,
        "generated_at": run_at,
    }
    provenance["id"] = hashlib.sha256(
        json.dumps(provenance, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    report = {
        "schema": "audit3.v1",
        "generated_at": run_at,
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
            "cost_basis": dict(COST_BASIS),
            "win_definition": "net pnl_pct > 0 after per-class round-trip slippage",
            "edge_test": "net-expectancy bootstrap CI, one-sided; WR is a descriptor only",
            "p_value": "one-sided bootstrap P(net mean <= 0), 2,000 seeded resamples",
            "p_wr": "one-sided exact binomial P(X>=wins) under p=0.5 — reported, never gated",
            "promotion_rule": "PROVEN_T2 = n>=100, net CI lower bound >= "
                              f"max({PROVEN_MIN_NET_CI_LO_PCT}%/trade, "
                              f"{MATERIALITY_COST_FRACTION:.0%} of the cell's mean "
                              "round-trip cost), stable halves, no symbol > "
                              f"{MAX_SYMBOL_SHARE:.0%}, source share <= {MAX_SOURCE_SHARE:.0%}, "
                              f"BH q <= {FDR_Q}, DSR >= {DSR_THRESHOLD}, "
                              "selection alpha CI lower bound > 0 (G9)",
            "cost_stress": "net CI lower bound at 2x the class slippage must stay "
                           "positive to reach PROVEN_T2 or CANDIDATE (G10); "
                           "otherwise the cell is WEAK",
            "selection_alpha_gate": "G9: PROVEN_T2 requires direction-adjusted "
                                    "selection alpha (pick net - hold) bootstrap CI "
                                    "lower bound > 0; a beta-only profitable cell is "
                                    "demoted to CANDIDATE and flagged beta_dominant",
            "multiplicity": "Benjamini-Hochberg across tested cells; Bonferroni "
                            f"alpha/m = {0.05 / max(1, len(tested)):.6f}",
            "stability": "chronological split-half, both halves net mean > 0",
            "recency_rule": (
                f"PROVEN_T2 requires the trailing "
                f"{RECENCY_WINDOW_FRACTION:.0%} of closes (min "
                f"{RECENCY_MIN_TRADES}) to have a non-negative net mean; "
                "otherwise the verdict is capped at CANDIDATE"),
            "persistence_runs": persistence_runs if history is not None else None,
            "persistence_rule": (
                "a CANDIDATE/PROVEN_T2 verdict must persist across "
                f"{persistence_runs} consecutive runs; BH is per-run, so a single "
                "cross is not enough" if history is not None else
                "disabled: no verdict-history sidecar supplied"),
            "max_symbol_share": MAX_SYMBOL_SHARE,
            "max_source_share": MAX_SOURCE_SHARE,
            "random_entry_mc": "not run here (needs per-symbol price series); "
                               "see alpha_engine/benchmark_closed_ledger.py for the "
                               "timing-null companion report.",
        },
        "summary": summary,
        "coverage": coverage if coverage is not None else payload_coverage(None, rows),
        "selection_alpha": selection,
        "forward_gate": (forward if isinstance(forward, dict) else {
            "enforced": False,
            "why": ("no forward ledger supplied to build_report(); PROVEN_T2 was not "
                    "gated on forward evidence by this caller"),
        }),
        "doctrine": {
            "name": "innocent-until-proven-guilty",
            "default_state": "not proven -- keep observing; absence of proof of "
                            "edge is not evidence of harm",
            "kill_requires": "net-expectancy bootstrap 95% CI entirely < 0 AND "
                             "Benjamini-Hochberg harm q <= 0.10",
            "pf_rule": f"PF < {HARM_PF_WATCH} is a watch flag only",
            "nothing_deleted": "no closed pick, strategy or section is removed "
                               "from the ledger by this module",
        },
        "multiplicity": {
            "rule": "BH is computed within each namespace; only confirmatory cells "
                    "(pre-registered pods) may reach PROVEN_T2",
            "manifest_path": (confirmatory or {}).get("path"),
            "manifest_available": bool((confirmatory or {}).get("available")),
            "n_pods": len((confirmatory or {}).get("pods") or []),
            "families": {ns: {"n_tested": len(f),
                              "n_proven": sum(1 for c in f if c["verdict"] == "PROVEN_T2")}
                          for ns, f in bh_families.items()},
        },
        "persistence": {
            "rule": "repeated-looks: a CANDIDATE/PROVEN_T2 verdict must persist "
                    f"across {persistence_runs} consecutive runs before it is granted",
            "runs_required": persistence_runs if history is not None else None,
            "available": history is not None,
            "n_demoted_this_run": persistence_counters["demoted"],
            "n_promoted_this_run": persistence_counters["promoted"],
            "history_cells": len(history) if history is not None else 0,
            "first_pass_at_field": "cells that cleared the gate carry first_pass_at "
                                   "(the run that began the passing streak)",
        },
        "verdict_churn": churn,
        "denylist_hits": _denylist_hit_summary(),
        "classes": classes,
        "segments": segments,
        "cells": cells,
        "symbols": symbols,
        "source_families": families,
        "kill_tribunal": {
            "criteria": [
                "net expectancy 95% CI entirely < 0",
                f"BH harm q <= {FDR_Q} across killed cells",
                f"PF < {HARM_PF_WATCH} at n >= {KILL_PF_N} is a WATCH flag, "
                "never a kill on its own",
                "WR < 40% (diagnostic, not sufficient alone)",
            ],
            "kills": kills,
        },
        "hypotheses": hyp,
        "provenance": {
            "module": "alpha_engine/audit3_tribunal.py",
            "generator_version": GENERATOR_VERSION,
            "id": provenance["id"],
            "population": provenance["population"],
            "population_rows": provenance["population_rows"],
            "population_total": provenance["population_total"],
            "cost_model": provenance["cost_model"],
            "win_definition": provenance["win_definition"],
            "source_file": source,
            "source_generated_at": source_generated_at,
            "input_sha256": input_sha256,
            "git_sha": _git_sha(),
            "n_cells_scored_with_dsr": sum(1 for c in cells if c.get("dsr") is not None),
            "n_trials_dsr": n_trials,
            "registry_note": "multiplicity is counted two ways on purpose: "
                             "BH/Bonferroni operate on tested cells (n >= sample "
                             "floor); DSR uses the global trial count, every "
                             "distinct cell scored.",
        },
    }
    # Every rendered number must be joinable to its (population, cost, win) triple.
    for bucket in (cells, symbols, classes, segments, families):
        for c in bucket:
            c["provenance_id"] = provenance["id"]
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="audit3 quantitative kill tribunal")
    ap.add_argument("--picks", required=True, help="dashboard_data.json or flat closed-pick list")
    ap.add_argument("--out", help="write ledger JSON here (else stdout)")
    ap.add_argument("--alpha", help="selection-alpha sidecar from "
                                     "alpha_engine/audit3_selection_alpha.py")
    ap.add_argument("--confirmatory", help="pre-registered pod manifest "
                                            f"(default {DEFAULT_CONFIRMATORY})")
    from alpha_engine.forward_observations import DEFAULT_LEDGER as _FWD_LEDGER
    ap.add_argument("--forward-ledger", default=str(_FWD_LEDGER),
                    help="forward-observations ledger that gates PROVEN_T2 "
                         "(0 rows means no pod can promote)")
    ap.add_argument("--history", help="verdict-persistence sidecar (N1). Supplying "
                                      "an existing file enables the repeated-looks gate")
    ap.add_argument("--history-write", action="store_true",
                    help="write the updated persistence sidecar back to --history")
    ap.add_argument("--persistence-runs", type=int, default=PERSISTENCE_RUNS,
                    help="consecutive runs a verdict must persist (default "
                         f"{PERSISTENCE_RUNS})")
    ap.add_argument("--prev-ledger", help="previous audit3 ledger for the "
                                          "verdict-churn monitor")
    ap.add_argument("--max-churn", type=float, default=None,
                    help="exit 3 if the raw-verdict churn rate exceeds this "
                         f"(alert threshold is {CHURN_ALERT_THRESHOLD})")
    args = ap.parse_args(argv)
    drops: dict[str, int] = {}
    try:
        rows, generated_at = load_rows(args.picks, drops=drops)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    try:
        with open(args.picks, encoding="utf-8") as f:
            source_payload = json.load(f)
    except (OSError, ValueError):
        source_payload = None
    coverage = payload_coverage(source_payload, rows, drops)
    alpha = None
    if args.alpha:
        try:
            with open(args.alpha, encoding="utf-8") as f:
                alpha = json.load(f)
        except (OSError, ValueError) as exc:
            print(f"WARNING: alpha sidecar unreadable ({exc}); continuing without it",
                  file=sys.stderr)
    manifest = load_confirmatory(args.confirmatory)
    # No --history means the repeated-looks gate is OFF (standalone behaviour is
    # unchanged); an existing sidecar means it is ON. A missing file under an
    # explicit --history is an empty history, i.e. the first seeded run.
    history = load_history(args.history) if args.history else None
    prev_verdicts = load_prev_verdicts(args.prev_ledger)
    run_at = datetime.now(timezone.utc).isoformat()
    report = build_report(rows, args.picks, generated_at, coverage=coverage,
                          require_alpha=True,
                          alpha=alpha, input_sha256=_sha256(args.picks),
                          confirmatory=manifest,
                          forward=forward_gate_block(manifest, args.forward_ledger),
                          history=history, run_at=run_at,
                          persistence_runs=args.persistence_runs,
                          prev_verdicts=prev_verdicts)
    churn = report["verdict_churn"]
    if (args.max_churn is not None and churn["available"]
            and churn["n_tracked"] >= CHURN_MIN_TRACKED
            and churn["churn_rate"] > args.max_churn):
        print(f"ERROR: verdict churn {churn['churn_rate']:.1%} "
              f"({churn['n_flipped']}/{churn['n_tracked']}) exceeds "
              f"--max-churn {args.max_churn:.1%}", file=sys.stderr)
        return 3
    if args.history_write:
        save_history(args.history, history, run_at=run_at,
                     runs_required=args.persistence_runs)
    payload = json.dumps(report, indent=1, allow_nan=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
        print(f"wrote {args.out}: {report['summary']}")
        print(f"coverage: {report['coverage']['statement']}")
        print(f"selection alpha: {'joined' if report['selection_alpha']['available'] else 'not available'}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
