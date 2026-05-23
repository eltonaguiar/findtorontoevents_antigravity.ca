"""Statistical kill-gate (M-055).

Before any strategy / symbol / source is killed, this gate verifies the kill
is statistically justified — not a small-n rolling-window artifact.

WHY THIS EXISTS
---------------
The Phase 2-D COMMODITY panel (2026-04-29) killed CT=F (cotton) citing
"n=12 WR 8.3%". The resolver-v2 ledger later showed those same 12 picks
resolved to 66.7% WR. CL=F was killed on n=6. KC=F on n=12. None of these
samples is large enough for ANY win-rate verdict — a 1-of-12 outcome is
entirely consistent with a true 50% strategy having a bad run.

See reports/deep_dive_cotton_2026-05-15.md + reports/phase2d_kill_audit_2026-05-15.md.

The map of the existing kill machinery (M-055 step 1) found ZERO binomial
or Wilson-CI checks enforced at any of the ~6 kill data structures or
~4 kill-decision paths. This module is the missing statistical guardrail.

USAGE
-----
    from audit_trail.kill_gate import evaluate_kill
    allow, verdict, detail = evaluate_kill(wins=1, n=12, asset_class="COMMODITY")
    # allow == False, verdict == "INSUFFICIENT_EVIDENCE"
    # -> the kill must NOT proceed; strategy stays in incubation.

A kill is only allowed when the gate returns allow_kill=True, which requires:
  1. n >= MIN_N_BY_ASSET_CLASS  (enough resolved trades to test anything)
  2. one-sided binomial p-value < ALPHA  (WR significantly below break-even)
  3. Wilson 95% lower bound on WR < break-even  (CI does not straddle 50%)

WIRE-UP STATUS: opt-in sidecar. No production caller yet — see the
`## Wiring Plan` in the PR that introduces this file. The 3 recommended
wire-in points (per M-055 step 1 map) are passes_active_gate +
the BLOCKED_*_PAIRS hard-reject sites in audit_trail/quality_gates.py.
"""

from __future__ import annotations

import math
from typing import Tuple

# Minimum resolved trades before a kill verdict is statistically meaningful.
# CRYPTO higher because crypto picks are noisier + over-emitted.
MIN_N_BY_ASSET_CLASS = {
    "CRYPTO": 50,
    "EQUITY": 30,
    "FOREX": 30,
    "COMMODITY": 30,
    "ETF": 30,
    "BOND": 30,
    "FUTURES": 30,
}
MIN_N_DEFAULT = 30

# Break-even win rate a kill must prove the strategy is *significantly* below.
BREAKEVEN_WR = 0.50

# Significance level for the one-sided binomial test.
ALPHA = 0.05

# Verdict strings.
VERDICT_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
VERDICT_KILL_JUSTIFIED = "KILL_JUSTIFIED"
VERDICT_EDGE_UNPROVEN = "EDGE_INTACT_OR_UNPROVEN"


def wilson_lower_bound(wins: int, n: int, z: float = 1.96) -> float:
    """Wilson score interval lower bound for a binomial proportion.

    Robust at small n (unlike the normal-approx interval, which can go
    negative or exceed 1). z=1.96 -> 95% one-sided-equivalent lower bound.
    """
    if n <= 0:
        return 0.0
    phat = wins / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = phat + z2 / (2 * n)
    margin = z * math.sqrt((phat * (1.0 - phat) + z2 / (4 * n)) / n)
    return max(0.0, (centre - margin) / denom)


def binomial_p_below(wins: int, n: int, p0: float = BREAKEVEN_WR) -> float:
    """One-sided p-value: P(X <= wins | X ~ Binomial(n, p0)).

    A small p-value means the observed win count is implausibly low if the
    strategy's true win rate were p0 (break-even) — i.e. the strategy is
    significantly *worse* than break-even. Exact computation (no scipy).
    """
    if n <= 0:
        return 1.0
    wins = max(0, min(wins, n))
    total = 0.0
    for k in range(wins + 1):
        total += math.comb(n, k) * (p0 ** k) * ((1.0 - p0) ** (n - k))
    return min(1.0, total)


def evaluate_kill(
    wins: int,
    n: int,
    asset_class: str = "",
    pf: float | None = None,
) -> Tuple[bool, str, str]:
    """Decide whether a proposed kill is statistically justified.

    Returns (allow_kill, verdict, detail).

    allow_kill is True ONLY when there is enough evidence to conclude the
    strategy is significantly below break-even. Otherwise the kill is
    blocked and the strategy should stay in incubation / accrue more data.

    pf is accepted for logging/parity with caller stats but is NOT a gate
    input — PF alone (without n + significance) is exactly the metric that
    produced the Phase 2-D mis-kills.
    """
    try:
        n = int(n)
        wins = int(wins)
    except (TypeError, ValueError):
        return (False, VERDICT_INSUFFICIENT, f"non-numeric stats: wins={wins!r} n={n!r}")

    if n < 0 or wins < 0 or wins > n:
        return (False, VERDICT_INSUFFICIENT, f"invalid stats: wins={wins} n={n}")

    min_n = MIN_N_BY_ASSET_CLASS.get(str(asset_class).upper(), MIN_N_DEFAULT)
    if n < min_n:
        return (
            False,
            VERDICT_INSUFFICIENT,
            f"n={n} < min_n={min_n} for {asset_class or 'default'} — "
            f"too few trades to justify a kill (Phase-2-D mis-kill class)",
        )

    wr = wins / n
    wlb = wilson_lower_bound(wins, n)
    p = binomial_p_below(wins, n)

    if p < ALPHA and wlb < BREAKEVEN_WR:
        return (
            True,
            VERDICT_KILL_JUSTIFIED,
            f"n={n} WR={wr:.1%} Wilson95LB={wlb:.1%} binom_p={p:.4f} < {ALPHA} "
            f"(pf={pf}) — significantly below break-even, kill justified",
        )

    return (
        False,
        VERDICT_EDGE_UNPROVEN,
        f"n={n} WR={wr:.1%} Wilson95LB={wlb:.1%} binom_p={p:.4f} "
        f"(pf={pf}) — NOT significantly below break-even; kill blocked",
    )
