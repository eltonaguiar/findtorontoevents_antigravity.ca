"""Wire-up tests for the opt-in HF Quality Gate companion in passes_smart_gate.

PR: feat/wire-hf-quality-gate-2026-04-28
Wire site: audit_trail/quality_gates.py::passes_smart_gate (after high_conviction_gate_passed)
"""
from datetime import datetime, timedelta, timezone

import pytest

from audit_trail import hf_gate_telemetry as _hfgt
from audit_trail.quality_gates import passes_smart_gate


@pytest.fixture(autouse=True)
def _reset_hf_telemetry():
    _hfgt._reset_for_tests()
    yield
    _hfgt._reset_for_tests()


def _safe_timestamp():
    """Recent timestamp (fresh, no -35 stale penalty) at an hour outside
    the PHASE1 dead-zone windows (08-11, 13-15, 16-21 UTC). Falls back to
    "now" when no safe hour is reachable in the last 24h, since the
    forward-bypass on the fixture clears the score floor regardless."""
    now = datetime.now(timezone.utc)
    # 22:00 UTC is the empirically-best window per the dead_zone_evening
    # comment block in quality_gates.py.
    candidate = now.replace(hour=22, minute=0, second=0, microsecond=0)
    if candidate > now:
        candidate -= timedelta(days=1)
    return candidate.isoformat()


def _pick(**overrides):
    p = {
        "id": "p", "symbol": "BTCUSDT", "asset_class": "CRYPTO",
        "source_system": "pm_whale_signals", "strategy": "pm_whale_test",
        "status": "OPEN", "direction": "LONG",
        "entry_price": 100.0, "take_profit": 110.0, "stop_loss": 95.0,
        "score": 65, "trust_score": 6, "trust_label": "MODERATE",
        "confidence": 0.80, "timestamp": _safe_timestamp(),
        "source_tier": "PROVEN",
        # Avoid null_ml_solo_source -20 score penalty.
        "ml_score": 0.72,
        # Forward-bypass evidence (≥30 trades @ ≥55% WR) clears the smart-gate
        # score floor regardless of penalty stacking, so these tests exercise
        # the HF wire-up rather than the active-gate score path.
        "forward_trades": 30,
        "forward_wr": 0.65,
        "strat_fwd_trades": 30,
        "strat_fwd_wr": 0.65,
        # PR #644 added explicit forward_validated requirement at the top of
        # passes_smart_gate. Without it, smart-gate short-circuits to False
        # before the HF block (the wire-up under test here) can fire.
        "forward_validated": True,
    }
    p.update(overrides)
    return p


def test_hf_off_baseline_unchanged(monkeypatch):
    # 2026-04-28: default flipped to ON. Use explicit "0" to assert OFF path.
    monkeypatch.setenv("HF_QUALITY_GATE_ENABLED", "0")
    p = _pick()
    assert passes_smart_gate(p) is True
    # Explicit OFF must not even consult the HF module:
    assert "_hf_quality_gate_pass" not in p


def test_hf_off_passes_pick_hf_would_reject(monkeypatch):
    """Smart-gate-passing pick in CRYPTO dead-band [0.60,0.70) must still pass when HF is off."""
    monkeypatch.setenv("HF_QUALITY_GATE_ENABLED", "0")
    assert passes_smart_gate(_pick(confidence=0.65, score=70)) is True


def test_hf_on_baseline_pick_passes(monkeypatch):
    monkeypatch.setenv("HF_QUALITY_GATE_ENABLED", "1")
    p = _pick()
    assert passes_smart_gate(p) is True
    assert p.get("_hf_quality_gate_pass") is True


def test_hf_on_tightens_dead_band(monkeypatch):
    monkeypatch.setenv("HF_QUALITY_GATE_ENABLED", "1")
    p = _pick(confidence=0.65, score=70)
    assert passes_smart_gate(p) is False
    assert "dead band" in p.get("_hf_quality_gate_reason", "")


def test_hf_on_rejects_banned_symbol(monkeypatch):
    monkeypatch.setenv("HF_QUALITY_GATE_ENABLED", "1")
    p = _pick(symbol="DOGEUSDT")
    assert passes_smart_gate(p) is False
    assert "DOGEUSDT" in p.get("_hf_quality_gate_reason", "")


def test_hf_module_exception_soft_fails(monkeypatch):
    """If the HF module raises, smart-gate falls through to its pre-HF verdict."""
    monkeypatch.setenv("HF_QUALITY_GATE_ENABLED", "1")
    import alpha_engine.hedge_fund_quality_gate as hfq

    def _boom(_p):
        raise RuntimeError("simulated HF module failure")
    monkeypatch.setattr(hfq, "passes_hedge_fund_gate", _boom)
    assert passes_smart_gate(_pick()) is True
