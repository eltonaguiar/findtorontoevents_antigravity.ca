"""2026-11-16 audit: prediction-market families must never leave shadow sizing.

Evidence: PM PnL is derived from spot-proxy TP/SL on binary contract odds, PM
copy-trading is structurally rejected, and the documented decision is
"prediction markets stay shadow (PBO 0.603)". Before this pin the only thing
holding PM in shadow was the generic 10-step gate — a tier-CORE PM row would
have been sized "tiny" (0.2%).
"""
import pytest

from alpha_engine.admissibility_pipeline import (
    AdmissibilityVerdict,
    apply_prediction_market_shadow_pin,
    is_prediction_market_strategy,
    prediction_markets_shadow_only,
)


@pytest.mark.parametrize("name", [
    "polymarket_prediction",
    "polymarket_momentum",
    "kalshi_mtf_consensus",
    "prediction_market_consensus",
    "copy_pm_alice",
    "pm_whale_signals",
    "pm_momentum_signals",
    "pm_kalshi_signals",
])
def test_pm_names_are_detected(name):
    assert is_prediction_market_strategy(name) is True


@pytest.mark.parametrize("name", [
    "ema_momentum_m006",
    "mega_mutation",
    "forex_rsi2_mean_reversion",
    "stocks_rsi2_pullback",
    "",
])
def test_non_pm_names_are_ignored(name):
    assert is_prediction_market_strategy(name) is False


def test_pin_forces_core_sizing_to_shadow(monkeypatch):
    monkeypatch.delenv("PREDICTION_MARKETS_SHADOW_ONLY", raising=False)
    v = AdmissibilityVerdict(recommended_sizing="tiny")
    out = apply_prediction_market_shadow_pin(v, "kalshi_mtf_consensus")
    assert out.recommended_sizing == "shadow"
    assert out.shadow_pin is True
    assert any("Prediction-market shadow pin" in w for w in out.warnings)


def test_pin_is_idempotent(monkeypatch):
    monkeypatch.delenv("PREDICTION_MARKETS_SHADOW_ONLY", raising=False)
    v = AdmissibilityVerdict(recommended_sizing="tiny")
    apply_prediction_market_shadow_pin(v, "polymarket_prediction")
    apply_prediction_market_shadow_pin(v, "polymarket_prediction")
    pin_warnings = [w for w in v.warnings if "shadow pin" in w]
    assert len(pin_warnings) == 1


def test_kill_switch_disables_pin(monkeypatch):
    monkeypatch.setenv("PREDICTION_MARKETS_SHADOW_ONLY", "0")
    assert prediction_markets_shadow_only() is False
    v = AdmissibilityVerdict(recommended_sizing="tiny")
    out = apply_prediction_market_shadow_pin(v, "polymarket_prediction")
    assert out.recommended_sizing == "tiny"
    assert out.shadow_pin is False


def test_flag_on_by_default(monkeypatch):
    monkeypatch.delenv("PREDICTION_MARKETS_SHADOW_ONLY", raising=False)
    assert prediction_markets_shadow_only() is True


def test_non_pm_verdict_untouched(monkeypatch):
    monkeypatch.delenv("PREDICTION_MARKETS_SHADOW_ONLY", raising=False)
    v = AdmissibilityVerdict(recommended_sizing="tiny")
    out = apply_prediction_market_shadow_pin(v, "stocks_rsi2_pullback")
    assert out.recommended_sizing == "tiny"
    assert out.shadow_pin is False
    assert out.warnings == []
