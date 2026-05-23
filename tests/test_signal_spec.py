"""Tests for tools/research/signal_spec.py — v3b SignalSpec validator.

Covers user-provided baseline tests + in-repo superset coverage
(schema_version, PAIR_LONG/PAIR_SHORT, valid_to ordering, extended
asset_class set, dxy_trend enum).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

pytest.importorskip("pydantic")  # signal_spec requires pydantic; skip if missing in CI env

from tools.research.signal_spec import (
    Feature, RegimeGate, SignalSpec, SCHEMA_VERSION, validate,
)


def _good_payload(**overrides) -> dict:
    base = {
        "signal_id": "cot_steepener_ctf_20260512",
        "asset_class": "COMMODITY",
        "direction": "LONG",
        "confidence": 0.78,
        "valid_from": "2026-05-12T14:00:00Z",
        "valid_to": "2026-05-19T14:00:00Z",
        "primary_ticker": "CT=F",
        "regime_gate": {
            "vix_max": 22,
            "dxy_trend": "FALLING",
        },
        "features": [
            {"name": "cot_net_position_zscore", "value": 1.84, "source": "CFTC"},
            {"name": "roll_yield_pct", "value": 8.2, "source": "futures_curve"},
        ],
        "rationale": "Strong commercial net positioning + positive roll yield",
    }
    base.update(overrides)
    return base


# ── User-provided baseline tests ─────────────────────────────────────

def test_valid_signal():
    spec = SignalSpec(
        signal_id="cot_steepener_ctf_20260512",
        asset_class="COMMODITY",
        direction="LONG",
        confidence=0.78,
        valid_from=datetime.fromisoformat("2026-05-12T14:00:00"),
        primary_ticker="CT=F",
        regime_gate=RegimeGate(vix_max=22, dxy_trend="FALLING"),
        features=[
            Feature(name="cot_net_position_zscore", value=1.84, source="CFTC"),
            Feature(name="roll_yield_pct", value=8.2, source="futures_curve"),
        ],
        rationale="Strong commercial net positioning",
    )
    assert spec.direction == "LONG"
    assert spec.confidence == 0.78
    assert spec.schema_version == SCHEMA_VERSION


def test_invalid_asset_class_raises():
    with pytest.raises(Exception):
        SignalSpec(
            signal_id="test",
            asset_class="INVALID",
            direction="LONG",
            confidence=0.7,
            valid_from=datetime.now(),
            primary_ticker="BTCUSDT",
        )


# ── In-repo superset coverage ────────────────────────────────────────

def test_validate_helper_happy_path():
    spec = validate(_good_payload())
    assert spec.signal_id == "cot_steepener_ctf_20260512"
    assert spec.asset_class == "COMMODITY"


def test_bad_direction_rejected():
    with pytest.raises(Exception):
        validate(_good_payload(direction="FOO"))


def test_confidence_above_one_rejected():
    with pytest.raises(Exception):
        validate(_good_payload(confidence=1.5))


def test_confidence_below_zero_rejected():
    with pytest.raises(Exception):
        validate(_good_payload(confidence=-0.1))


def test_valid_to_before_valid_from_rejected():
    with pytest.raises(Exception):
        validate(_good_payload(
            valid_from="2026-05-12T00:00:00Z",
            valid_to="2024-01-01T00:00:00Z",
        ))


def test_schema_version_mismatch_rejected():
    with pytest.raises(Exception):
        validate(_good_payload(schema_version="v3a/v1"))


def test_pair_long_direction_accepted():
    p = _good_payload(direction="PAIR_LONG", secondary_ticker="IEF")
    spec = validate(p)
    assert spec.direction == "PAIR_LONG"
    assert spec.secondary_ticker == "IEF"


def test_memecoin_asset_class_accepted():
    p = _good_payload(asset_class="MEMECOIN", primary_ticker="PEPEUSDT")
    spec = validate(p)
    assert spec.asset_class == "MEMECOIN"


def test_signal_id_pattern_rejects_uppercase():
    with pytest.raises(Exception):
        validate(_good_payload(signal_id="BadCamelCase"))


def test_regime_gate_dxy_trend_enum():
    with pytest.raises(Exception):
        validate(_good_payload(regime_gate={"dxy_trend": "SIDEWAYS"}))


def test_regime_gate_none_allowed():
    spec = validate(_good_payload(regime_gate=None))
    assert spec.regime_gate is None


def test_features_default_empty():
    p = _good_payload()
    del p["features"]
    spec = validate(p)
    assert spec.features == []


def test_rationale_max_length():
    long_text = "x" * 1000
    with pytest.raises(Exception):
        validate(_good_payload(rationale=long_text))
