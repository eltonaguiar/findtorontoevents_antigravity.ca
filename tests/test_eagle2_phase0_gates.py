"""Tests for EAGLE2 Phase 0 concentration and depromotion gates."""
from datetime import datetime, timezone

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
        # 2026-11-23: was a fixed literal ("2026-06-02T12:00:00+00:00"). A fixed
        # timestamp ages past the pick-staleness threshold (quality_gates.py:9176
        # "stale pick (age=4173.2h, pnl=0.00%)"), so by late 2026 every pick from
        # this helper was silently rejected as stale -- a clock-dependent fixture,
        # not a code defect. A real active pick has a recent timestamp.
        "timestamp": datetime.now(timezone.utc).isoformat(),
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


def test_equity_dragger_strategies_unblocked_below_n30_floor(monkeypatch):
    """The 2026-05-19 protocol decision SUPERSEDES the 2026-06-05 edge-hunt P0.

    audit_trail/quality_gates.py:2709 records the removal:
      "cta_replicator/COMMODITY, multi_asset_copytrader/FOREX+EQUITY REMOVED:
       insufficient policy-clean picks (n=1, n=25, n=2) -- below 30-pick floor
       required for a block verdict. 2-engine swarm consensus (DeepSeek+Cerebras)
       2026-05-19. Re-evaluate when n>=30."

    A duplicate ("EQUITY", "multi_asset_copytrader") entry in
    HARDCODED_TOXIC_PAIRS kept silently re-imposing a block that had been ruled
    out on the protocol's own n>=30 floor. Removed 2026-11-23 (operator decision:
    the removal is correct). This pins that both structures agree and the pick is
    admitted. Re-evaluate when either pair reaches n>=30 policy-clean picks.
    """
    assert ("EQUITY", "multi_asset_copytrader") not in BLOCKED_ASSET_STRATEGY_PAIRS
    assert ("EQUITY", "regime_accumulation") not in BLOCKED_ASSET_STRATEGY_PAIRS
    from alpha_engine import emitter_whitelist as _ew

    assert ("EQUITY", "multi_asset_copytrader") not in _ew.HARDCODED_TOXIC_PAIRS
    # The matrix symbol allow-list is an orthogonal, data-file-driven filter
    # (alpha_engine/matrix_symbol_gates.py) that restricts this source to its own
    # symbol set. This test is about pair-level blocking, not symbol gating, and
    # the M-096 tests already isolate the same way. Do not disable it repo-wide.
    monkeypatch.setenv("MATRIX_SYMBOL_GATES", "0")
    pick = _pick(
        symbol="AAPL",
        ac="EQUITY",
        strategy="multi_asset_copytrader",
        source="multi_asset_copytrader",
        score=80,
    )
    assert passes_active_gate(pick) is True


def test_incubator_gainer_rejected_by_active_gate():
    pick = _pick(source="incubator_gainer", ac="CRYPTO", strategy="gainer_scout")
    assert passes_active_gate(pick) is False
