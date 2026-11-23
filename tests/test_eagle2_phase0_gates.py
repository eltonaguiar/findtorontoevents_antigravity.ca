"""Tests for EAGLE2 Phase 0 concentration and depromotion gates."""
from audit_trail.quality_gates import (
    BLOCKED_ASSET_SOURCE_PAIRS,
    BLOCKED_ASSET_STRATEGY_PAIRS,
    BLOCKED_SOURCE_SYSTEMS,
    passes_active_gate,
)
from alpha_engine.eagle2_class_source_cap import enforce_class_single_source_cap


def _pick(symbol="BTCUSDT", source="incubator_gainer", ac="CRYPTO", score=50, strategy="test_strat"):
    return {
        "symbol": symbol,
        "source_system": source,
        "asset_class": ac,
        "strategy": strategy,
        "smart_score": score,
        "ml_composite": score,
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "score": score,
        "confidence": 0.8,
        "trust_label": "PROVEN",
        "timestamp": "2026-06-02T12:00:00+00:00",
    }


def test_single_source_cap_trims_dominant_low_scored():
    picks = [
        _pick(source="incubator_gainer", score=90),
        _pick(source="incubator_gainer", score=80),
        _pick(source="incubator_gainer", score=70),
        _pick(source="alpha_engine", score=60),
    ]
    out, stats = enforce_class_single_source_cap(picks, max_share=0.60)
    assert len(out) == 3
    assert stats["trimmed"] == 1
    sources = [p["source_system"] for p in out]
    assert sources.count("incubator_gainer") == 2


def test_single_source_cap_no_trim_when_balanced():
    picks = [
        _pick(source="a", score=90),
        _pick(source="b", score=80),
        _pick(source="c", score=70),
    ]
    out, stats = enforce_class_single_source_cap(picks, max_share=0.60)
    assert len(out) == 3
    assert stats["trimmed"] == 0


def test_incubator_gainer_blocked_for_crypto():
    assert ("CRYPTO", "incubator_gainer") in BLOCKED_ASSET_SOURCE_PAIRS
    assert "incubator_gainer" in BLOCKED_SOURCE_SYSTEMS


def test_regime_terminal_blocked_equity_crypto_forex():
    assert ("EQUITY", "regime_terminal") in BLOCKED_ASSET_STRATEGY_PAIRS
    assert ("CRYPTO", "regime_terminal") in BLOCKED_ASSET_SOURCE_PAIRS
    assert ("FOREX", "regime_terminal") in BLOCKED_ASSET_SOURCE_PAIRS


def test_equity_copytrader_block_was_reversed_on_record_and_stays_reversed():
    """The 2026-06-05 EQUITY block on multi_asset_copytrader was DELIBERATELY reversed.

    `audit_trail/quality_gates.py` records the decision in place:

        # cta_replicator/COMMODITY, multi_asset_copytrader/FOREX+EQUITY REMOVED:
        #     insufficient [evidence]

    This test previously asserted the block still existed, so it had been failing on
    main ever since that reversal. The fix is NOT to re-add the pair: CLAUDE.md
    requires docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md and the mutation analysis
    before EXPANDING a BLOCKED_* list, and the recorded investigation is what removed
    it. Re-adding it to make an old assertion green would be a silent production
    change in the direction the rules forbid.

    So the assertion is inverted into a guard: the removal stays, and the blocks that
    DO exist for this strategy are protected against accidental deletion.
    """
    # the deliberate removal is still in effect for EQUITY...
    assert ("EQUITY", "multi_asset_copytrader") not in BLOCKED_ASSET_STRATEGY_PAIRS
    # ...while the surviving blocks for the same strategy are intact.
    assert ("FUTURES", "multi_asset_copytrader") in BLOCKED_ASSET_STRATEGY_PAIRS
    assert ("FOREX", "multi_asset_copytrader") in BLOCKED_ASSET_SOURCE_PAIRS


def test_regime_accumulation_is_not_a_blockable_strategy_name():
    """The old test asserted a block on ('EQUITY', 'regime_accumulation').

    No such strategy exists: 'regime_accumulation' is a REGIME LABEL used in
    alpha_engine/smart_picks_engine.py, not a strategy id (the closest real strategy
    is crypto_vol_regime_accumulation). The assertion could never have been satisfied,
    which is why this test failed for two independent reasons.
    """
    assert ("EQUITY", "regime_accumulation") not in BLOCKED_ASSET_STRATEGY_PAIRS


def test_incubator_gainer_rejected_by_active_gate():
    pick = _pick(source="incubator_gainer", ac="CRYPTO", strategy="gainer_scout")
    assert passes_active_gate(pick) is False
