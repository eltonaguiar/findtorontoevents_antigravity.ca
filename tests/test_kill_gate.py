"""Tests for the M-055 statistical kill-gate (audit_trail/kill_gate.py).

Includes a regression suite that replays the 7 Phase 2-D COMMODITY kills
through the gate — proving the gate would have blocked the small-n
mis-kills (CL=F n=6, CT=F n=12, KC=F n=12).
"""
from __future__ import annotations

import math

from audit_trail.kill_gate import (
    ALPHA,
    BREAKEVEN_WR,
    VERDICT_EDGE_UNPROVEN,
    VERDICT_INSUFFICIENT,
    VERDICT_KILL_JUSTIFIED,
    binomial_p_below,
    evaluate_kill,
    wilson_lower_bound,
)


# ── Wilson lower bound ────────────────────────────────────────────────
def test_wilson_zero_n():
    assert wilson_lower_bound(0, 0) == 0.0


def test_wilson_bounds_0_1():
    for wins, n in [(0, 10), (5, 10), (10, 10), (1, 100), (99, 100)]:
        lb = wilson_lower_bound(wins, n)
        assert 0.0 <= lb <= 1.0


def test_wilson_small_n_conservative():
    # 1/12 wins — point estimate 8.3%, but Wilson LB is even lower and the
    # interval is wide. LB stays well under break-even.
    assert wilson_lower_bound(1, 12) < 0.30


def test_wilson_large_n_tightens():
    # Same 50% point estimate: larger n -> tighter (higher) lower bound.
    lb_small = wilson_lower_bound(15, 30)
    lb_large = wilson_lower_bound(150, 300)
    assert lb_large > lb_small


# ── Binomial p-value ──────────────────────────────────────────────────
def test_binomial_zero_n():
    assert binomial_p_below(0, 0) == 1.0


def test_binomial_all_wins_p_is_one():
    # X <= n always true -> p == 1.0
    assert math.isclose(binomial_p_below(20, 20), 1.0, rel_tol=1e-9)


def test_binomial_half_is_about_half():
    # P(X <= n/2 | Binom(n, 0.5)) ~ 0.5 (slightly above, includes the median)
    p = binomial_p_below(50, 100)
    assert 0.5 <= p <= 0.6


def test_binomial_extreme_low_is_significant():
    # 1 win in 12 at p0=0.5 is very unlikely.
    assert binomial_p_below(1, 12) < 0.01


# ── evaluate_kill — guards ────────────────────────────────────────────
def test_evaluate_kill_invalid_stats():
    allow, verdict, _ = evaluate_kill(wins=5, n=2)  # wins > n
    assert allow is False and verdict == VERDICT_INSUFFICIENT


def test_evaluate_kill_non_numeric():
    allow, verdict, _ = evaluate_kill(wins="x", n="y")  # type: ignore[arg-type]
    assert allow is False and verdict == VERDICT_INSUFFICIENT


# ── evaluate_kill — small-n is always blocked ─────────────────────────
def test_evaluate_kill_small_n_blocked():
    # n=12 COMMODITY is below the 30 floor — blocked regardless of WR.
    allow, verdict, _ = evaluate_kill(wins=1, n=12, asset_class="COMMODITY")
    assert allow is False
    assert verdict == VERDICT_INSUFFICIENT


def test_evaluate_kill_crypto_higher_floor():
    # n=40 passes the 30 default but fails the CRYPTO floor of 50.
    allow, verdict, _ = evaluate_kill(wins=10, n=40, asset_class="CRYPTO")
    assert allow is False and verdict == VERDICT_INSUFFICIENT


# ── evaluate_kill — genuine kill ──────────────────────────────────────
def test_evaluate_kill_genuine_loser_allowed():
    # n=200, 30% WR — large sample, significantly below break-even.
    allow, verdict, detail = evaluate_kill(wins=60, n=200, asset_class="CRYPTO")
    assert allow is True
    assert verdict == VERDICT_KILL_JUSTIFIED


def test_evaluate_kill_break_even_strategy_not_killed():
    # n=200 at exactly 50% — not significantly below break-even.
    allow, verdict, _ = evaluate_kill(wins=100, n=200, asset_class="EQUITY")
    assert allow is False
    assert verdict == VERDICT_EDGE_UNPROVEN


def test_evaluate_kill_marginal_loser_not_killed():
    # n=60, 47% WR — below 50% but NOT statistically significant.
    allow, verdict, _ = evaluate_kill(wins=28, n=60, asset_class="EQUITY")
    assert allow is False
    assert verdict == VERDICT_EDGE_UNPROVEN


# ── Phase 2-D regression suite ────────────────────────────────────────
# Replays the 7 Phase 2-D COMMODITY kills (cited figures from
# audit_trail/quality_gates.py:1254-1262) through the gate.
#
# The gate blocks 4 of the 5 cited kills:
#   - CL=F n=6, CT=F n=12, KC=F n=12 -> INSUFFICIENT_EVIDENCE (below min-n)
#   - SI=F n=181 WR 44.2% -> EDGE_INTACT_OR_UNPROVEN (binom p=0.069, NOT
#     significantly below 50% even at large n — a kill on this is unjustified)
#   - GC=F n=91 WR 39.6% -> KILL_JUSTIFIED (p<0.05, the one defensible kill
#     IF its cited n=91 were real; the Phase 2-D audit found GC=F has only
#     n=3 in the resolver-v2 ledger, so even this is provenance-suspect).

PHASE_2D_KILLS = [
    # (symbol, n, cited_wr, expect_allow_kill, expect_verdict_kind)
    ("GC=F", 91, 0.396, True, VERDICT_KILL_JUSTIFIED),
    ("SI=F", 181, 0.442, False, VERDICT_EDGE_UNPROVEN),
    ("CL=F", 6, 0.167, False, VERDICT_INSUFFICIENT),
    ("CT=F", 12, 0.083, False, VERDICT_INSUFFICIENT),
    ("KC=F", 12, 0.083, False, VERDICT_INSUFFICIENT),
]


def test_phase2d_kills_replayed_through_gate():
    """Each Phase 2-D kill must produce the expected gate verdict."""
    for symbol, n, cited_wr, expect_allow, expect_verdict in PHASE_2D_KILLS:
        wins = round(cited_wr * n)
        allow, verdict, detail = evaluate_kill(wins=wins, n=n, asset_class="COMMODITY")
        assert allow == expect_allow, (
            f"{symbol}: n={n} cited_wr={cited_wr:.1%} -> allow_kill={allow} "
            f"(expected {expect_allow}); verdict={verdict}; {detail}"
        )
        assert verdict == expect_verdict, (
            f"{symbol}: verdict={verdict} (expected {expect_verdict})"
        )


def test_phase2d_blocked_count():
    """The gate blocks 4 of the 5 cited Phase 2-D kills (only GC=F passes)."""
    blocked = sum(
        1
        for _symbol, n, cited_wr, _ea, _ev in PHASE_2D_KILLS
        if not evaluate_kill(wins=round(cited_wr * n), n=n, asset_class="COMMODITY")[0]
    )
    assert blocked == 4, f"expected 4 Phase 2-D kills blocked, got {blocked}"


def test_phase2d_cotton_kill_specifically_blocked():
    """The cotton (CT=F) kill — the trigger for M-055 — is blocked."""
    allow, verdict, _ = evaluate_kill(wins=1, n=12, asset_class="COMMODITY")
    assert allow is False
    assert verdict == VERDICT_INSUFFICIENT
