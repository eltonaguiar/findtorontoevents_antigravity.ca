"""Live-data kill verification tests (2026-05-02).

Issues #686, #688, #689 — forex_carry_momentum + goldmine_6x_consensus
have demonstrable zero edge in 30d live data; both added to
BLOCKED_ASSET_STRATEGY_PAIRS. These tests pin the kill so a future
peer cannot accidentally remove it without explicit attention.
"""
from __future__ import annotations

from audit_trail.quality_gates import BLOCKED_ASSET_STRATEGY_PAIRS, passes_active_gate


def _base_pick(**overrides):
    pick = {
        "id": "kill-test-1",
        "symbol": "EURUSD=X",
        "asset_class": "FOREX",
        "source_system": "test",
        "strategy": "forex_carry_momentum",
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 1.10,
        "take_profit": 1.12,
        "stop_loss": 1.08,
        "score": 80,
        "trust_score": 6,
        "trust_label": "MODERATE",
        "trust_tier": "RELIABLE",
        "confidence": 0.75,
        "rr_ratio": 1.7,
        "forward_wr": 0.0,
        "forward_trades": 8,
    }
    pick.update(overrides)
    return pick


def test_forex_carry_momentum_in_blocklist():
    """Issue #688 — strategy has 0% WR on n=8 non-JPY (30d) and bypassed
    JPY rule (now fixed in PR #687); kill the strategy class-wide."""
    assert ("FOREX", "forex_carry_momentum") in BLOCKED_ASSET_STRATEGY_PAIRS


def test_goldmine_6x_consensus_in_blocklist():
    """Issue #689 — extends goldmine_1x/2x/3x/4x EQUITY blocks;
    n=16 / 0% WR / -55.41% sum over 30d live data."""
    assert ("EQUITY", "goldmine_6x_consensus") in BLOCKED_ASSET_STRATEGY_PAIRS


def test_forex_carry_momentum_active_gate_rejects():
    """End-to-end: a forex_carry_momentum pick on a non-JPY symbol must
    be rejected by passes_active_gate via the blocklist."""
    pick = _base_pick(symbol="NZDUSD=X", strategy="forex_carry_momentum")
    assert passes_active_gate(pick) is False


def test_goldmine_6x_consensus_active_gate_rejects():
    """End-to-end: goldmine_6x_consensus EQUITY pick must be rejected."""
    pick = _base_pick(
        symbol="AAPL",
        asset_class="EQUITY",
        strategy="goldmine_6x_consensus",
    )
    assert passes_active_gate(pick) is False


def test_other_forex_strategies_still_pass():
    """Sanity: the kill is strategy-specific, not asset-class-wide.
    forex_rsi2_mean_reversion has 60% WR on n=164 non-JPY (30d) and
    must NOT be blocked by this addition."""
    assert ("FOREX", "forex_rsi2_mean_reversion") not in BLOCKED_ASSET_STRATEGY_PAIRS


def test_goldmine_5x_still_passes_class_check():
    """Sanity: 5x is NOT in the kill list; only 1x/2x/3x/4x/6x are.
    5x had +75% WR / +1.71% sum in 7d live data (issue #686 EQUITY table)."""
    assert ("EQUITY", "goldmine_5x_consensus") not in BLOCKED_ASSET_STRATEGY_PAIRS


def test_quan_engine_hypeusdt_in_strategy_symbol_blocklist():
    """Issue #691 — quan_engine HYPEUSDT n=553, WR 41.6%, -0.22% avg.
    Mutation-analysis-based symbol-allowlist kill (not class-wide kill —
    XRPUSDT/TRXUSDT/BNBUSDT variants retain edge per the same analysis)."""
    from audit_trail.quality_gates import BLOCKED_STRATEGY_SYMBOL_PAIRS
    assert ("quan_engine", "HYPEUSDT") in BLOCKED_STRATEGY_SYMBOL_PAIRS


def test_quan_engine_xrpusdt_still_passes_blocklist_check():
    """Sanity: only HYPEUSDT is blocked; quan_engine on XRPUSDT (51% WR, n=51,
    the BEST symbol per mutation analysis) must NOT be blocked."""
    from audit_trail.quality_gates import BLOCKED_STRATEGY_SYMBOL_PAIRS
    assert ("quan_engine", "XRPUSDT") not in BLOCKED_STRATEGY_SYMBOL_PAIRS
    assert ("quan_engine", "TRXUSDT") not in BLOCKED_STRATEGY_SYMBOL_PAIRS
    assert ("quan_engine", "BNBUSDT") not in BLOCKED_STRATEGY_SYMBOL_PAIRS
