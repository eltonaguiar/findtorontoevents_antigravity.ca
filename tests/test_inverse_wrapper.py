"""Unit tests for baby_strategies.inverse_wrapper."""
from __future__ import annotations

import pytest

from baby_strategies import inverse_wrapper as IW


# ---------------------------------------------------------------------------
# Pick factory
# ---------------------------------------------------------------------------
def _pick(
    strategy: str = "quan_engine",
    symbol: str = "ETHUSDT",
    direction: str = "LONG",
    confidence: float = 0.65,
    entry_price: float = 2000.0,
    take_profit: float = 2060.0,
    stop_loss: float = 1970.0,
) -> dict:
    return {
        "strategy": strategy,
        "source_system": strategy,
        "symbol": symbol,
        "direction": direction,
        "confidence": confidence,
        "entry_price": entry_price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "extra": {"existing": "field"},
    }


# ---------------------------------------------------------------------------
# Direction flip
# ---------------------------------------------------------------------------
def test_transform_flips_long_to_short():
    out = IW.transform([_pick(direction="LONG")],
                       source_strategy="quan_engine",
                       new_strategy_name="quan_engine_inverse")
    assert len(out) == 1
    assert out[0]["direction"] == "SHORT"
    assert out[0]["strategy"] == "quan_engine_inverse"
    assert out[0]["source_system"] == "inverse_quan_engine"


def test_transform_flips_short_to_long():
    out = IW.transform([_pick(direction="SHORT", entry_price=2000, take_profit=1940, stop_loss=2030)],
                       source_strategy="quan_engine",
                       new_strategy_name="quan_engine_inverse")
    assert len(out) == 1
    assert out[0]["direction"] == "LONG"


def test_transform_flips_buy_to_sell_and_vice_versa():
    picks = [
        _pick(direction="BUY"),
        _pick(direction="SELL", entry_price=2000, take_profit=1940, stop_loss=2030),
    ]
    out = IW.transform(picks,
                       source_strategy="quan_engine",
                       new_strategy_name="quan_engine_inverse")
    assert len(out) == 2
    assert out[0]["direction"] == "SELL"
    assert out[1]["direction"] == "BUY"


def test_transform_drops_neutral_and_unknown_directions():
    picks = [
        _pick(direction="NEUTRAL"),
        _pick(direction="HOLD"),
        _pick(direction=""),
        _pick(direction="LONG"),  # baseline keeper
    ]
    out = IW.transform(picks,
                       source_strategy="quan_engine",
                       new_strategy_name="quan_engine_inverse")
    assert len(out) == 1
    assert out[0]["direction"] == "SHORT"


# ---------------------------------------------------------------------------
# TP/SL swap math
# ---------------------------------------------------------------------------
def test_transform_mirrors_tp_and_sl_around_entry():
    # LONG: entry=2000, TP=2060 (+60), SL=1970 (-30)
    # SHORT inverted: TP should be 2000-60=1940, SL should be 2000-(-30)=2030
    p = _pick(direction="LONG", entry_price=2000, take_profit=2060, stop_loss=1970)
    out = IW.transform([p], "quan_engine", "quan_engine_inverse")
    assert out[0]["take_profit"] == 1940.0
    assert out[0]["stop_loss"] == 2030.0


def test_transform_mirror_is_its_own_inverse():
    # Applying the transform twice (with swapped names) should recover the
    # original entry/tp/sl values.
    p = _pick(direction="LONG", entry_price=2000, take_profit=2060, stop_loss=1970)
    once = IW.transform([p], "quan_engine", "quan_engine_inverse")
    # Flip the resulting pick back by calling with the intermediate as source.
    twice = IW.transform([{**once[0], "strategy": "mid"}],
                         source_strategy="mid", new_strategy_name="quan_engine")
    assert twice[0]["direction"] == "LONG"
    assert twice[0]["take_profit"] == 2060.0
    assert twice[0]["stop_loss"] == 1970.0


# ---------------------------------------------------------------------------
# Confidence band filter
# ---------------------------------------------------------------------------
def test_confidence_band_filter_inclusive_low():
    picks = [_pick(confidence=0.60)]
    out = IW.transform(picks, "quan_engine", "quan_engine_inverse",
                       only_if_confidence_in=(0.60, 0.69))
    assert len(out) == 1


def test_confidence_band_filter_inclusive_high():
    picks = [_pick(confidence=0.69)]
    out = IW.transform(picks, "quan_engine", "quan_engine_inverse",
                       only_if_confidence_in=(0.60, 0.69))
    assert len(out) == 1


def test_confidence_band_filter_rejects_below():
    picks = [_pick(confidence=0.59)]
    out = IW.transform(picks, "quan_engine", "quan_engine_inverse",
                       only_if_confidence_in=(0.60, 0.69))
    assert len(out) == 0


def test_confidence_band_filter_rejects_above():
    picks = [_pick(confidence=0.70)]
    out = IW.transform(picks, "quan_engine", "quan_engine_inverse",
                       only_if_confidence_in=(0.60, 0.69))
    assert len(out) == 0


def test_confidence_band_none_passes_all():
    picks = [_pick(confidence=0.30), _pick(confidence=0.95)]
    out = IW.transform(picks, "quan_engine", "quan_engine_inverse")
    assert len(out) == 2


def test_confidence_band_with_missing_confidence_drops():
    p = _pick()
    p.pop("confidence")
    out = IW.transform([p], "quan_engine", "quan_engine_inverse",
                       only_if_confidence_in=(0.60, 0.69))
    assert len(out) == 0


# ---------------------------------------------------------------------------
# Symbol exclusion
# ---------------------------------------------------------------------------
def test_symbol_exclusion_blocks_listed_symbols():
    picks = [
        _pick(symbol="TAOUSDT"),
        _pick(symbol="HYPEUSDT"),
        _pick(symbol="TRXUSDT"),
        _pick(symbol="ETHUSDT"),  # keeper
    ]
    out = IW.transform(picks, "quan_engine", "quan_engine_inverse",
                       exclude_symbols={"TAOUSDT", "HYPEUSDT", "TRXUSDT"})
    assert len(out) == 1
    assert out[0]["symbol"] == "ETHUSDT"


def test_symbol_exclusion_none_passes_all():
    picks = [_pick(symbol="TAOUSDT"), _pick(symbol="ETHUSDT")]
    out = IW.transform(picks, "quan_engine", "quan_engine_inverse")
    assert len(out) == 2


# ---------------------------------------------------------------------------
# Strategy filtering
# ---------------------------------------------------------------------------
def test_transform_ignores_picks_from_other_strategies():
    picks = [
        _pick(strategy="other_strategy"),
        _pick(strategy="quan_engine"),
    ]
    out = IW.transform(picks, "quan_engine", "quan_engine_inverse")
    assert len(out) == 1
    assert out[0]["strategy"] == "quan_engine_inverse"


def test_transform_raises_if_new_name_equals_source():
    with pytest.raises(ValueError):
        IW.transform([_pick()], "quan_engine", "quan_engine")


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------
def test_extra_inverted_from_contains_audit_trail():
    p = _pick(direction="LONG", take_profit=2060, stop_loss=1970)
    out = IW.transform([p], "quan_engine", "quan_engine_inverse")
    aud = out[0]["extra"]["inverted_from"]
    assert aud["original_strategy"] == "quan_engine"
    assert aud["original_direction"] == "LONG"
    assert aud["original_tp"] == 2060.0
    assert aud["original_sl"] == 1970.0


def test_existing_extra_fields_are_preserved():
    p = _pick()
    out = IW.transform([p], "quan_engine", "quan_engine_inverse")
    assert out[0]["extra"]["existing"] == "field"
    assert "inverted_from" in out[0]["extra"]


# ---------------------------------------------------------------------------
# Input immutability
# ---------------------------------------------------------------------------
def test_original_picks_are_not_mutated():
    p = _pick(direction="LONG", take_profit=2060, stop_loss=1970)
    original = {**p, "extra": {**p["extra"]}}
    IW.transform([p], "quan_engine", "quan_engine_inverse")
    assert p == original


# ---------------------------------------------------------------------------
# Signal-field variant (some pipelines use "signal" not "direction")
# ---------------------------------------------------------------------------
def test_signal_field_variant_is_flipped():
    p = _pick()
    p.pop("direction")
    p["signal"] = "BUY"
    out = IW.transform([p], "quan_engine", "quan_engine_inverse")
    assert len(out) == 1
    assert out[0]["signal"] == "SELL"


# ---------------------------------------------------------------------------
# Missing required fields
# ---------------------------------------------------------------------------
def test_missing_entry_price_drops_pick():
    p = _pick()
    p.pop("entry_price")
    out = IW.transform([p], "quan_engine", "quan_engine_inverse")
    assert len(out) == 0


def test_missing_take_profit_drops_pick():
    p = _pick()
    p.pop("take_profit")
    out = IW.transform([p], "quan_engine", "quan_engine_inverse")
    assert len(out) == 0


def test_missing_stop_loss_drops_pick():
    p = _pick()
    p.pop("stop_loss")
    out = IW.transform([p], "quan_engine", "quan_engine_inverse")
    assert len(out) == 0


# ---------------------------------------------------------------------------
# Integration: quan_engine caller config from meta.json
# ---------------------------------------------------------------------------
def test_quan_engine_configured_caller_end_to_end():
    picks = [
        # Inside band, not excluded -> KEEP + FLIP
        _pick(symbol="ETHUSDT", confidence=0.65, direction="LONG"),
        # Edge symbol -> EXCLUDE
        _pick(symbol="TAOUSDT", confidence=0.65, direction="LONG"),
        # Below band -> DROP
        _pick(symbol="ETHUSDT", confidence=0.55, direction="LONG"),
        # Above band -> DROP
        _pick(symbol="ETHUSDT", confidence=0.75, direction="LONG"),
        # Wrong strategy -> IGNORE
        _pick(symbol="ETHUSDT", confidence=0.65, direction="LONG", strategy="other"),
    ]
    out = IW.transform(
        picks,
        source_strategy="quan_engine",
        new_strategy_name="quan_engine_inverse",
        only_if_confidence_in=(0.60, 0.69),
        exclude_symbols={"TAOUSDT", "HYPEUSDT", "TRXUSDT"},
    )
    assert len(out) == 1
    assert out[0]["symbol"] == "ETHUSDT"
    assert out[0]["direction"] == "SHORT"
    assert out[0]["strategy"] == "quan_engine_inverse"
