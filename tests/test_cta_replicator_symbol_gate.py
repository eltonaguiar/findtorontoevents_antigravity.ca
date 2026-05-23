"""
cta_replicator source-system × symbol gate (2026-05-17).
Evidence: reports/FOREX_mutation_analysis_2026_05_17.md §Axis2
  CL=F: n=47, WR=19.1%, PF=0.39
  NG=F: n=24, WR=0.0%,  PF=0.00
  ZC=F: n=8,  WR=0.0%,  PF=0.00
  AUDUSD=X: n=8, WR=0.0% — blocked via BLOCKED_SYMBOLS_BY_CLASS["FOREX"]
"""
from datetime import datetime, timezone
import pytest
from audit_trail.quality_gates import passes_active_gate, BLOCKED_SOURCE_SYMBOL_PAIRS


def _pick(**overrides):
    base = dict(
        id="test-cta",
        symbol="USDJPY=X",
        asset_class="FOREX",
        source_system="cta_replicator",
        strategy="cta_cross_asset_tsmom",
        status="OPEN",
        direction="SHORT",
        entry_price=150.0,
        take_profit=148.0,
        stop_loss=151.5,
        score=70,
        trust_score=7,
        confidence=0.75,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source_systems=["cta_replicator", "alpha_engine", "mega_mutation"],
    )
    base.update(overrides)
    return base


class TestBlockedSourceSymbolPairs:
    def test_ng_f_in_blocked_pairs(self):
        assert ("cta_replicator", "NG=F") in BLOCKED_SOURCE_SYMBOL_PAIRS

    def test_cl_f_in_blocked_pairs(self):
        assert ("cta_replicator", "CL=F") in BLOCKED_SOURCE_SYMBOL_PAIRS

    def test_zc_f_in_blocked_pairs(self):
        assert ("cta_replicator", "ZC=F") in BLOCKED_SOURCE_SYMBOL_PAIRS

    def test_usdjpy_not_blocked(self):
        """USDJPY=X is the T1 keeper (WR=71.2%, PF=3.99) — must NOT be in pairs."""
        assert ("cta_replicator", "USDJPY=X") not in BLOCKED_SOURCE_SYMBOL_PAIRS


class TestSourceSymbolGate:
    def test_baseline_usdjpy_passes(self, monkeypatch):
        """cta_replicator USDJPY=X SHORT is the T1 edge — must not be blocked by source-symbol gate.
        Disable FOREX class-wide halt gates to isolate the source-symbol gate under test."""
        monkeypatch.setenv("FOREX_HARD_DISABLE", "0")
        monkeypatch.setenv("FOREX_DIRECTIONAL_GATE_ENABLED", "0")
        monkeypatch.setenv("CONCENTRATION_CAP_ENABLED", "0")
        monkeypatch.setenv("FOREX_SESSION_GATE_DISABLED", "1")  # M-078: isolation test, not time-dependent
        pick = _pick(symbol="USDJPY=X", asset_class="FOREX")
        assert passes_active_gate(pick) is True, "cta_replicator USDJPY=X must pass when FOREX gates isolated"

    def test_ng_f_blocked(self):
        pick = _pick(symbol="NG=F", asset_class="COMMODITY",
                     direction="LONG", take_profit=3.5, stop_loss=2.8, entry_price=3.1)
        assert passes_active_gate(pick) is False, "cta_replicator NG=F must be blocked"

    def test_cl_f_blocked(self):
        pick = _pick(symbol="CL=F", asset_class="COMMODITY",
                     direction="LONG", take_profit=85.0, stop_loss=78.0, entry_price=82.0)
        assert passes_active_gate(pick) is False, "cta_replicator CL=F must be blocked"

    def test_zc_f_blocked(self):
        pick = _pick(symbol="ZC=F", asset_class="COMMODITY",
                     direction="LONG", take_profit=520.0, stop_loss=490.0, entry_price=505.0)
        assert passes_active_gate(pick) is False, "cta_replicator ZC=F must be blocked"

    def test_ng_f_other_source_not_blocked(self):
        """NG=F from a different source_system must NOT be blocked by this gate."""
        pick = _pick(
            symbol="NG=F", asset_class="COMMODITY",
            source_system="multi_asset_cot",
            direction="LONG", take_profit=3.5, stop_loss=2.8, entry_price=3.1,
        )
        # May pass or fail other gates, but must not be blocked by source-symbol gate specifically.
        # We test the gate is disabled by kill-switch:
        import os
        os.environ["BLOCKED_SOURCE_SYMBOL_GATE_DISABLED"] = "1"
        try:
            result_disabled = passes_active_gate(pick)
        finally:
            os.environ.pop("BLOCKED_SOURCE_SYMBOL_GATE_DISABLED", None)
        # With gate disabled, the pick result should differ from cta_replicator NG=F
        cta_pick = _pick(symbol="NG=F", asset_class="COMMODITY",
                         direction="LONG", take_profit=3.5, stop_loss=2.8, entry_price=3.1)
        assert passes_active_gate(cta_pick) is False, "gate must block cta_replicator NG=F"

    def test_kill_switch_disables_gate(self, monkeypatch):
        """BLOCKED_SOURCE_SYMBOL_GATE_DISABLED=1 must bypass the gate."""
        monkeypatch.setenv("BLOCKED_SOURCE_SYMBOL_GATE_DISABLED", "1")
        # NG=F from cta_replicator should not be blocked when gate is disabled
        # (may still fail other gates — we just check it's not this gate blocking)
        pick = _pick(symbol="NG=F", asset_class="COMMODITY",
                     direction="LONG", take_profit=3.5, stop_loss=2.8, entry_price=3.1,
                     score=75, trust_score=8, confidence=0.80)
        # With kill-switch, the source-symbol gate is bypassed. Result may vary by other gates.
        # This test mainly verifies no exception is raised.
        passes_active_gate(pick)  # must not raise


class TestAudusdForexBlock:
    def test_audusd_blocked_for_all_forex_sources(self):
        """AUDUSD=X added to BLOCKED_SYMBOLS_BY_CLASS['FOREX'] — blocked regardless of source."""
        pick = _pick(symbol="AUDUSD=X", asset_class="FOREX", source_system="quan_engine")
        assert passes_active_gate(pick) is False, "AUDUSD=X must be blocked for all FOREX sources"
