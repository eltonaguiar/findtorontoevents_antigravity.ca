"""Regression tests for the 2026-04-28 zombie-kill PR.

Two empirically-proven negative-EV source_systems are added to
``audit_trail.quality_gates.BLOCKED_SOURCE_SYSTEMS`` after the mutation
three-axis autopsy (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`) confirmed no
direction / symbol / strategy axis showed PF>1.2 with n>=30:

  * ``copy_trader_highscore`` -- 31.6% WR / PF 0.74 / -78.4% PnL on n=234
    resolved (n=283 universal-resolved). 90% SHORT bias on `hs_lb_None`
    (n=253) at 32.4% WR; LONG side n=5 below the statistical floor; the 6
    "100% WR" symbols are placeholder-stat artifacts (5 identical
    +3.50% TP_HIT rows each), same pattern as feedback_clone_hl_placeholder_stats.md.
  * ``goldmine_stocks`` -- 12.5% WR / PF 0.03 / -70.4% PnL on n=24 resolved
    (n=434 closed). All LONG (no inverse). Dominant variant
    `goldmine_6x_consensus` is 0/17 = deterministic loser. Last signal
    2026-04-27 (still active emitter at kill time).

Mutation-analysis reports:
  * ``reports/mutation_analysis_copy_trader_highscore_2026_04_28.txt``
  * ``reports/mutation_analysis_goldmine_stocks_2026_04_28.txt``
Protocol writeup: ``reports/zombie_kill_protocol_2026_04_28.md``
"""

from __future__ import annotations

import pytest

from audit_trail.quality_gates import BLOCKED_SOURCE_SYSTEMS, passes_active_gate


ZOMBIES = ("copy_trader_highscore", "goldmine_stocks")


def test_zombies_added_to_blocked_source_systems():
    """Both zombie sources must be in the canonical blocklist set."""
    for sys_name in ZOMBIES:
        assert sys_name in BLOCKED_SOURCE_SYSTEMS, (
            f"{sys_name!r} missing from BLOCKED_SOURCE_SYSTEMS — kill regressed"
        )


def test_blocklist_did_not_shrink():
    """Defense-in-depth: the existing kills must still be present so
    this PR is purely additive (no accidental removal of mercury2_fast,
    kimi_signal_tracking, etc.)."""
    must_keep = {
        "mercury2_fast",
        # kimi_signal_tracking intentionally unblocked 2026-05-16:
        # n=368, WR=76.6%, PF=7.70 — 2nd best source. Removal is data-driven, not a regression.
        "stocks_competition",
        "rocket_scanner",
        "crypto_winners",
    }
    assert must_keep.issubset(BLOCKED_SOURCE_SYSTEMS), (
        "Pre-existing blocklist entries are missing — kill PR "
        "regressed prior decisions"
    )


@pytest.mark.parametrize("sys_name", ZOMBIES)
def test_active_pick_with_zombie_source_is_rejected(sys_name):
    """A live-shaped active pick carrying the zombie source_system must be
    hard-rejected by ``passes_active_gate`` so the picks never surface on
    the audit dashboard or feed downstream paper accounts."""
    pick = {
        "id": f"sanity_{sys_name}_BTCUSDT",
        "symbol": "BTCUSDT",
        "strategy": "hs_lb_None" if sys_name == "copy_trader_highscore" else "goldmine_6x_consensus",
        "source_system": sys_name,
        "direction": "SHORT" if sys_name == "copy_trader_highscore" else "LONG",
        "asset_class": "CRYPTO" if sys_name == "copy_trader_highscore" else "EQUITY",
        "entry_price": 100.0,
        "take_profit": 97.0,
        "stop_loss": 102.0,
        "rr": 1.5,
        "confidence": 0.75,
        "elite_score": 80,
        "score": 80,
        "status": "ACTIVE",
        "timestamp": "2026-04-28T00:00:00Z",
        "created_at": "2026-04-28T00:00:00Z",
    }
    assert passes_active_gate(pick) is False, (
        f"Pick with source_system={sys_name!r} bypassed the active gate — "
        f"BLOCKED_SOURCE_SYSTEMS check at quality_gates.py:~4059 not firing"
    )


def test_case_insensitive_source_match():
    """The active gate lowercases source_system; verify a mixed-case zombie
    source is also rejected (defense against upstream casing drift)."""
    pick = {
        "id": "case_test",
        "symbol": "JNJ",
        "strategy": "goldmine_6x_consensus",
        "source_system": "Goldmine_Stocks",  # mixed case
        "direction": "LONG",
        "asset_class": "EQUITY",
        "entry_price": 150.0,
        "take_profit": 155.0,
        "stop_loss": 145.0,
        "rr": 1.0,
        "score": 80,
        "status": "ACTIVE",
        "timestamp": "2026-04-28T00:00:00Z",
        "created_at": "2026-04-28T00:00:00Z",
    }
    assert passes_active_gate(pick) is False


def test_unrelated_source_still_allowed_through_block_check():
    """Negative control: a non-zombie source_system must NOT be filtered by the
    blocklist branch at quality_gates.py:4059. (The pick may still fail other
    gates downstream — we just assert it's not specifically the BLOCKED_SOURCE
    filter that stops it.)"""
    assert "luxalgo_filters" not in BLOCKED_SOURCE_SYSTEMS
    assert "battleground" not in BLOCKED_SOURCE_SYSTEMS
