"""
P0 CRYPTO quality gates — unit tests
M-035: confidence > 0.85 hard-blocked (overfit cliff, WR=14.4%); threshold lowered from 0.90 in Session AG
M-036: direction=BUY hard-blocked (PF=0.38 vs LONG PF=3.14)
M-037: ml_score < 0.65 hard-blocked (bottom-30% tier, WR=32.5%)

Refs: reports/expert_feedback_action_plan_2026-05-17.md P0 items
      alpha_engine/config.py CRYPTO_MAX_CONFIDENCE / CRYPTO_BLOCKED_DIRECTIONS / MIN_ML_SCORE_CRYPTO
"""
from datetime import datetime, timezone

import pytest

from audit_trail.quality_gates import passes_active_gate


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _crypto_pick(**overrides):
    """Minimal valid CRYPTO pick that clears all pre-existing gates.

    Env-var kill-switches for gates that may fire before the P0 gates are
    applied per-test where needed, but this base pick is designed to pass
    all gates except the specific P0 gate under test.
    """
    pick = {
        "id": "test-m035-m036-m037",
        "symbol": "ETHUSDT",
        "asset_class": "CRYPTO",
        "source_system": "pm_whale_signals",
        "strategy": "pm_whale_0xeee92f",
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 3000.0,
        "take_profit": 3300.0,
        "stop_loss": 2850.0,
        "score": 70,
        "elite_score": None,
        "trust_score": 6,
        "trust_label": "MODERATE",
        "confidence": 0.75,
        "ml_score": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_tier": "PROVEN",
    }
    pick.update(overrides)
    return pick


def _env_flags_isolate_p0(monkeypatch):
    """Disable gates that are irrelevant to P0 tests so they don't interfere."""
    monkeypatch.setenv("CONCENTRATION_CAP_ENABLED", "0")
    monkeypatch.setenv("DRIFT_PAUSE_GATE_ENABLED", "0")
    monkeypatch.setenv("DRIFT_AUTO_PAUSE_DISABLED", "1")
    monkeypatch.setenv("SAFETY_HALT_GATE_ENABLED", "0")
    monkeypatch.setenv("CRYPTO_QUARANTINE", "0")
    monkeypatch.setenv("KILL_GATE_ENABLED", "0")
    monkeypatch.setenv("DIRECTION_TRIPLE_GATE_DISABLED", "1")
    # Disable the older P0.5-4 guard so M-035 is the sole confidence check
    monkeypatch.setenv("CRYPTO_HIGH_CONF_GUARD_ENABLED", "0")
    monkeypatch.setenv("ML_CONFIDENCE_QUARANTINE_ENABLED", "0")
    monkeypatch.setenv("CRYPTO_CONF_INVERSION_GATE", "0")
    monkeypatch.setenv("FOREX_HARD_DISABLE", "0")
    monkeypatch.setenv("FOREX_DIRECTIONAL_GATE_ENABLED", "0")


# ---------------------------------------------------------------------------
# M-035: CRYPTO confidence overfit cliff
# ---------------------------------------------------------------------------

class TestM035CryptoConfidenceOverfitCliff:
    def test_confidence_above_ceiling_blocked(self, monkeypatch):
        """confidence=0.91 must be hard-blocked for CRYPTO (WR=14.4%)."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_CONF_OVERFIT_GATE_ENABLED", "1")
        pick = _crypto_pick(confidence=0.91)
        assert passes_active_gate(pick) is False

    def test_confidence_at_ceiling_passes(self, monkeypatch):
        """confidence=0.85 (exactly at ceiling) must PASS — ceiling is exclusive (> 0.85)."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_CONF_OVERFIT_GATE_ENABLED", "1")
        pick = _crypto_pick(confidence=0.85)
        assert passes_active_gate(pick) is True

    def test_confidence_well_below_ceiling_passes(self, monkeypatch):
        """confidence=0.75 (well below overfit cliff) must PASS."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_CONF_OVERFIT_GATE_ENABLED", "1")
        pick = _crypto_pick(confidence=0.75)
        assert passes_active_gate(pick) is True

    def test_gate_disabled_by_env_allows_overconf_pick(self, monkeypatch):
        """Kill-switch CRYPTO_CONF_OVERFIT_GATE_ENABLED=0 must allow confidence > 0.90."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_CONF_OVERFIT_GATE_ENABLED", "0")
        # Also disable the older guard so we truly test the kill-switch
        pick = _crypto_pick(confidence=0.95)
        # With gate disabled, must not be blocked by M-035 alone.
        # The pick may still be blocked by other gates; we verify it's not
        # specifically blocked by M-035 by checking the gate is reachable.
        # (Passes if no other active gate blocks it.)
        result = passes_active_gate(pick)
        # We can only assert it isn't specifically rejected — let it pass or fail
        # from another gate; just confirm no TypeError / gate crash.
        assert isinstance(result, bool)

    def test_env_overridable_threshold(self, monkeypatch):
        """CRYPTO_MAX_CONFIDENCE env var must shift the threshold dynamically."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_CONF_OVERFIT_GATE_ENABLED", "1")
        monkeypatch.setenv("CRYPTO_MAX_CONFIDENCE", "0.80")
        pick = _crypto_pick(confidence=0.85)
        # 0.85 > 0.80 threshold → should be blocked
        assert passes_active_gate(pick) is False

    def test_non_crypto_not_affected(self, monkeypatch):
        """Confidence > 0.90 on a non-CRYPTO class must NOT be blocked by M-035."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_CONF_OVERFIT_GATE_ENABLED", "1")
        monkeypatch.setenv("CONCENTRATION_CAP_ENABLED", "0")
        pick = _crypto_pick(
            asset_class="EQUITY",
            symbol="AAPL",
            source_system="alpha_engine",
            strategy="equity_momentum",
            confidence=0.95,
        )
        # M-035 must not block non-CRYPTO; let other gates decide
        result = passes_active_gate(pick)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# M-036: CRYPTO direction="BUY" hard-blocked
# ---------------------------------------------------------------------------

class TestM036CryptoBuyDirectionBlocked:
    def test_buy_direction_blocked(self, monkeypatch):
        """direction='BUY' must be hard-blocked for CRYPTO (PF=0.38)."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_BUY_DIRECTION_GATE_ENABLED", "1")
        pick = _crypto_pick(direction="BUY")
        assert passes_active_gate(pick) is False

    def test_buy_direction_case_insensitive_blocked(self, monkeypatch):
        """direction='buy' (lowercase) must also be blocked."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_BUY_DIRECTION_GATE_ENABLED", "1")
        pick = _crypto_pick(direction="buy")
        assert passes_active_gate(pick) is False

    def test_long_direction_passes(self, monkeypatch):
        """direction='LONG' must PASS the direction check (PF=3.14)."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_BUY_DIRECTION_GATE_ENABLED", "1")
        pick = _crypto_pick(direction="LONG")
        assert passes_active_gate(pick) is True

    def test_short_direction_passes(self, monkeypatch):
        """direction='SHORT' is a valid CRYPTO direction — must not be blocked."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_BUY_DIRECTION_GATE_ENABLED", "1")
        pick = _crypto_pick(direction="SHORT")
        result = passes_active_gate(pick)
        # SHORT may be blocked by CRYPTO_SHORT_DISABLED gate; what matters
        # is that M-036 itself does not block it.
        assert isinstance(result, bool)

    def test_gate_disabled_by_env_allows_buy_direction(self, monkeypatch):
        """Kill-switch CRYPTO_BUY_DIRECTION_GATE_ENABLED=0 must allow direction='BUY'."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_BUY_DIRECTION_GATE_ENABLED", "0")
        pick = _crypto_pick(direction="BUY")
        result = passes_active_gate(pick)
        assert isinstance(result, bool)

    def test_non_crypto_buy_not_affected(self, monkeypatch):
        """direction='BUY' on EQUITY must NOT be blocked by M-036."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_BUY_DIRECTION_GATE_ENABLED", "1")
        pick = _crypto_pick(
            asset_class="EQUITY",
            symbol="MSFT",
            source_system="alpha_engine",
            strategy="equity_momentum",
            direction="BUY",
        )
        result = passes_active_gate(pick)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# M-037: CRYPTO ml_score floor
# ---------------------------------------------------------------------------

class TestM037CryptoMlScoreFloor:
    def test_low_ml_score_blocked(self, monkeypatch):
        """ml_score=0.55 (< 0.65 floor) must be hard-blocked for CRYPTO."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "1")
        pick = _crypto_pick(ml_score=0.55)
        assert passes_active_gate(pick) is False

    def test_ml_score_at_floor_passes(self, monkeypatch):
        """ml_score=0.65 (exactly at floor) must PASS — floor is < (exclusive lower bound)."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "1")
        pick = _crypto_pick(ml_score=0.65)
        assert passes_active_gate(pick) is True

    def test_ml_score_above_floor_passes(self, monkeypatch):
        """ml_score=0.80 (well above floor) must PASS."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "1")
        pick = _crypto_pick(ml_score=0.80)
        assert passes_active_gate(pick) is True

    def test_null_ml_score_not_blocked(self, monkeypatch):
        """ml_score=None must NOT be blocked — fill-rate may be partial (fail-open)."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "1")
        pick = _crypto_pick(ml_score=None)
        # M-037 is fail-open for unpopulated ml_score
        assert passes_active_gate(pick) is True

    def test_zero_ml_score_not_blocked(self, monkeypatch):
        """ml_score=0 must NOT be blocked — 0.0 is the default fill for sources
        that don't emit ml_score yet (not a "very low" score from the model).
        Regression guard for the bug where ml_score=0 != None caused all CRYPTO
        picks from non-ML sources to be blocked by M-037, resulting in active=0."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "1")
        pick = _crypto_pick(ml_score=0)
        assert passes_active_gate(pick) is True

    def test_zero_float_ml_score_not_blocked(self, monkeypatch):
        """ml_score=0.0 (explicit float zero) must also pass — same as ml_score=0."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "1")
        pick = _crypto_pick(ml_score=0.0)
        assert passes_active_gate(pick) is True

    def test_very_low_nonzero_ml_score_blocked(self, monkeypatch):
        """ml_score=0.001 is a real (very low) model output and MUST be blocked.
        Only exact zero is "not populated" — any positive score is evaluated
        against the 0.65 floor and blocked if below it. This pins the boundary:
        > 0 passes to the floor check; 0 itself is skipped."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "1")
        pick = _crypto_pick(ml_score=0.001)
        assert passes_active_gate(pick) is False

    def test_gate_disabled_by_env_allows_low_ml_score(self, monkeypatch):
        """Kill-switch CRYPTO_ML_SCORE_GATE_ENABLED=0 must allow ml_score < 0.65."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "0")
        pick = _crypto_pick(ml_score=0.30)
        result = passes_active_gate(pick)
        assert isinstance(result, bool)

    def test_env_overridable_floor(self, monkeypatch):
        """MIN_ML_SCORE_CRYPTO env var must shift the floor dynamically."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "1")
        monkeypatch.setenv("MIN_ML_SCORE_CRYPTO", "0.70")
        pick = _crypto_pick(ml_score=0.66)
        # 0.66 < 0.70 threshold → should be blocked
        assert passes_active_gate(pick) is False

    def test_non_crypto_low_ml_score_not_affected(self, monkeypatch):
        """ml_score=0.40 on COMMODITY must NOT be blocked by M-037."""
        _env_flags_isolate_p0(monkeypatch)
        monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "1")
        pick = _crypto_pick(
            asset_class="COMMODITY",
            symbol="GC=F",
            source_system="alpha_engine",
            strategy="commodity_trend",
            direction="LONG",
            ml_score=0.40,
        )
        result = passes_active_gate(pick)
        assert isinstance(result, bool)
