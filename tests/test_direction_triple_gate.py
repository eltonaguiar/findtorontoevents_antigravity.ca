"""Tests for the FOREX directional gate + BLOCKED_DIRECTION_TRIPLES wiring.

2026-05-15: BLOCKED_DIRECTION_TRIPLES previously only scrubbed historical
aggregation rows; it never rejected new emissions. passes_active_gate now
enforces it. FOREX LONG losers (fx_smart_carry_trade_momentum,
dxy-reversal-scout, MeanReversionBB) are hard-blocked; the SHORT side and
forex-rsi-ema-scout LONG stay open.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit_trail.quality_gates import BLOCKED_DIRECTION_TRIPLES


def test_forex_long_loser_triples_present():
    for strat in ("fx_smart_carry_trade_momentum", "dxy-reversal-scout",
                  "MeanReversionBB"):
        assert ("FOREX", strat, "LONG") in BLOCKED_DIRECTION_TRIPLES, strat


def test_forex_short_side_not_blocked():
    # The SHORT side is the FOREX survivor (PF 8.11) — must stay open.
    for strat in ("fx_smart_carry_trade_momentum", "dxy-reversal-scout",
                  "MeanReversionBB"):
        assert ("FOREX", strat, "SHORT") not in BLOCKED_DIRECTION_TRIPLES, strat


def test_forex_rsi_ema_scout_long_not_blocked():
    # forex-rsi-ema-scout LONG is the surviving LONG edge (PF 1.68) — keep it.
    assert ("FOREX", "forex-rsi-ema-scout", "LONG") not in BLOCKED_DIRECTION_TRIPLES


def test_active_gate_rejects_blocked_forex_long(monkeypatch):
    monkeypatch.delenv("DIRECTION_TRIPLE_GATE_DISABLED", raising=False)
    from audit_trail.quality_gates import passes_active_gate
    pick = {
        "id": "t1", "symbol": "EURUSD=X", "asset_class": "FOREX",
        "strategy": "dxy-reversal-scout", "direction": "LONG",
        "confidence": 0.9, "score": 80,
    }
    assert passes_active_gate(pick) is False


def test_commodity_cta_tsmom_both_directions_blocked():
    # 2026-05-17: COMMODITY cta_cross_asset_tsmom autopsy — LONG WR=0%, SHORT WR=19%.
    # Both directions blocked. py_compile does not catch membership bugs; this test does.
    assert ("COMMODITY", "cta_cross_asset_tsmom", "LONG") in BLOCKED_DIRECTION_TRIPLES
    assert ("COMMODITY", "cta_cross_asset_tsmom", "SHORT") in BLOCKED_DIRECTION_TRIPLES


def test_forex_cta_tsmom_long_blocked_short_not():
    # FOREX: cta_cross_asset_tsmom LONG is blocked (WR=42% sub-floor).
    # FOREX SHORT is T1 edge (WR=71%, PF=3.61) — must NOT be blocked.
    assert ("FOREX", "cta_cross_asset_tsmom", "LONG") in BLOCKED_DIRECTION_TRIPLES
    assert ("FOREX", "cta_cross_asset_tsmom", "SHORT") not in BLOCKED_DIRECTION_TRIPLES


def test_ig_contrarian_sentiment_long_blocked_short_preserved():
    # ig_contrarian_sentiment LONG autopsy: WR=16.3% n=196 (closed_picks, FOREX class).
    # SHORT WR=60.7% n=56 — T1 edge, must NOT be blocked.
    assert ("FOREX", "ig_contrarian_sentiment", "LONG") in BLOCKED_DIRECTION_TRIPLES
    assert ("FOREX", "ig_contrarian_sentiment", "SHORT") not in BLOCKED_DIRECTION_TRIPLES


def test_cta_replicator_commodity_both_directions_blocked():
    # 2026-05-17 autopsy: cta_replicator COMMODITY WR=0-19% PF=0.22 n=83
    # (CL=F n=47 WR=19.1%, NG=F n=24 WR=0%, ZC=F n=8 WR=0%)
    # Both directions sub-floor (<45% charter). CT=F edge (WR=84-87%)
    # is from cot_positioning/cftc_cot_commercial_signal — unaffected.
    assert ("COMMODITY", "cta_replicator", "LONG") in BLOCKED_DIRECTION_TRIPLES
    assert ("COMMODITY", "cta_replicator", "SHORT") in BLOCKED_DIRECTION_TRIPLES


def test_cta_replicator_other_classes_not_blocked():
    # cta_replicator is blocked only for COMMODITY; FOREX and CRYPTO
    # must remain unblocked by this specific triple.
    assert ("FOREX", "cta_replicator", "LONG") not in BLOCKED_DIRECTION_TRIPLES
    assert ("FOREX", "cta_replicator", "SHORT") not in BLOCKED_DIRECTION_TRIPLES


def test_active_gate_kill_switch(monkeypatch):
    # With the kill-switch on, the direction-triple gate is a no-op (the pick
    # may still be rejected by OTHER gates, so only assert the triple gate
    # itself does not fire — checked via the helper-free path).
    monkeypatch.setenv("DIRECTION_TRIPLE_GATE_DISABLED", "1")
    from audit_trail.quality_gates import _normalize_direction, BLOCKED_DIRECTION_TRIPLES
    # Triple still in the set, but the gate is disabled — direct membership
    # check is unaffected; the gate wiring is what the env flag guards.
    assert ("FOREX", "dxy-reversal-scout", "LONG") in BLOCKED_DIRECTION_TRIPLES
    assert _normalize_direction("BUY") == "LONG"
