"""Tests for the ETF SHORT class-level gate (2026-11-15).

Evidence behind the gate (ai_tournament_picks_latest.json, 2,242 closed picks):
  ETF SHORT n=75  WR 10.7%  mean -2.56%/trade  PF 0.09
  ETF LONG  n=116 WR 84.5%  mean +2.66%/trade  PF 8.28
The SHORT inversion survives a time split (8.1% first half / 13.2% second half).

What these tests pin down:
  * only SHORT/SELL are blocked - ETF LONG must never be blocked by this gate
  * the gate tags the rejection reason, so it is distinguishable from other gates
  * the kill-switch and the measurement lanes (forward_test_only etc.) bypass it
  * the pre-existing CRYPTO LONG block is untouched
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RED = "etf_short_class_block"


def _pick(direction: str, **kw):
    p = {
        "id": "etf-short-gate-test",
        "symbol": "SPY",
        "asset_class": "ETF",
        "strategy": "etf_sector_rotation",
        "direction": direction,
        "confidence": 0.6,
        "score": 60,
    }
    p.update(kw)
    return p


def test_config_blocks_short_side_only():
    from alpha_engine.config import ETF_BLOCKED_DIRECTIONS

    assert "SHORT" in ETF_BLOCKED_DIRECTIONS
    assert "SELL" in ETF_BLOCKED_DIRECTIONS
    for long_dir in ("LONG", "BUY", "STRONG_BUY"):
        assert long_dir not in ETF_BLOCKED_DIRECTIONS


def test_crypto_long_block_is_untouched():
    from alpha_engine.config import CRYPTO_BLOCKED_DIRECTIONS

    assert {"BUY", "LONG", "STRONG_BUY"} <= set(CRYPTO_BLOCKED_DIRECTIONS)


def test_etf_short_is_rejected_with_reason(monkeypatch):
    monkeypatch.delenv("ETF_SHORT_GATE_ENABLED", raising=False)
    from audit_trail.quality_gates import passes_active_gate

    p = _pick("SHORT")
    assert passes_active_gate(p) is False
    assert p.get("_hf_quality_gate_reason") == RED


def test_etf_sell_alias_also_rejected(monkeypatch):
    monkeypatch.delenv("ETF_SHORT_GATE_ENABLED", raising=False)
    from audit_trail.quality_gates import passes_active_gate

    p = _pick("SELL")
    passes_active_gate(p)
    assert p.get("_hf_quality_gate_reason") == RED


def test_kill_switch_bypasses_gate(monkeypatch):
    monkeypatch.setenv("ETF_SHORT_GATE_ENABLED", "0")
    from audit_trail.quality_gates import passes_active_gate

    p = _pick("SHORT")
    passes_active_gate(p)  # may still be rejected by unrelated gates
    assert p.get("_hf_quality_gate_reason") != RED


def test_measurement_lane_is_exempt(monkeypatch):
    monkeypatch.delenv("ETF_SHORT_GATE_ENABLED", raising=False)
    from audit_trail.quality_gates import passes_active_gate

    for kw in ({"forward_test_only": True}, {"forward_observation": True},
               {"paper_pilot": True}, {"_monitor_mode": True}):
        p = _pick("SHORT", **kw)
        passes_active_gate(p)
        assert p.get("_hf_quality_gate_reason") != RED, kw


def test_etf_long_never_tagged_by_this_gate(monkeypatch):
    monkeypatch.delenv("ETF_SHORT_GATE_ENABLED", raising=False)
    from audit_trail.quality_gates import passes_active_gate

    p = _pick("LONG")
    passes_active_gate(p)
    assert p.get("_hf_quality_gate_reason") != RED
