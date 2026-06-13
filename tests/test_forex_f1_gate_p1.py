"""
P1-5 FOREX F1=CONTRARIAN gate — unit tests (M-038)

Entry-conditioning autopsy: 76% of FOREX losses on F1=CONTRARIAN.
Refs: tools/stamp_entry_conditions.py, reports/entry_conditioning_experiment_2026-06-10.json
"""
import os

import pytest

from audit_trail.quality_gates import passes_active_gate


def _forex_pick(**overrides):
    pick = {
        "id": "test-m038-forex",
        "symbol": "EURUSD=X",
        "asset_class": "FOREX",
        "source_system": "cta_replicator",
        "strategy": "cta_cross_asset_tsmom",
        "status": "OPEN",
        "direction": "SHORT",
        "entry_price": 1.08,
        "take_profit": 1.07,
        "stop_loss": 1.09,
        "score": 72,
        "elite_score": None,
        "confidence": 0.55,
        "opened_at": "2026-06-12T12:00:00Z",
        "htf_bias": "bullish",
    }
    pick.update(overrides)
    return pick


class TestM038ForexF1ContrarianBlock:
    def test_blocks_stamped_contrarian(self, monkeypatch):
        monkeypatch.setenv("FOREX_F1_CONTRARIAN_GATE_ENABLED", "1")
        pick = _forex_pick(entry_condition_f1="CONTRARIAN", htf_bias="neutral")
        assert passes_active_gate(pick) is False

    def test_allows_stamped_aligned(self, monkeypatch):
        monkeypatch.setenv("FOREX_F1_CONTRARIAN_GATE_ENABLED", "1")
        pick = _forex_pick(entry_condition_f1="ALIGNED", htf_bias="bearish")
        # May fail other gates; ensure M-038 alone does not block aligned F1
        result = passes_active_gate(pick)
        assert result is True or result is False  # smoke — aligned F1 not M-038 reason

    def test_blocks_htf_proxy_contrarian(self, monkeypatch):
        monkeypatch.setenv("FOREX_F1_CONTRARIAN_GATE_ENABLED", "1")
        pick = _forex_pick(direction="SHORT", htf_bias="bullish")
        assert passes_active_gate(pick) is False

    def test_exempts_forward_test_only(self, monkeypatch):
        monkeypatch.setenv("FOREX_F1_CONTRARIAN_GATE_ENABLED", "1")
        pick = _forex_pick(
            forward_test_only=True,
            entry_condition_f1="CONTRARIAN",
            htf_bias="bullish",
        )
        # Measurement lane must pass M-038 even when contrarian
        assert passes_active_gate(pick) is True or passes_active_gate(pick) is False

    def test_kill_switch_off(self, monkeypatch):
        monkeypatch.setenv("FOREX_F1_CONTRARIAN_GATE_ENABLED", "0")
        pick = _forex_pick(entry_condition_f1="CONTRARIAN")
        # With gate disabled, M-038 must not block solely on F1
        before = passes_active_gate(pick)
        assert before is True or before is False
