"""Tests for audit_trail.pick_schema (requires pydantic)."""

import pytest

pytest.importorskip("pydantic")

from audit_trail.pick_schema import PYDANTIC_AVAILABLE, validate_and_coerce_pick


@pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="pydantic not installed")
def test_coerce_pair_to_symbol():
    ok, errs, d = validate_and_coerce_pick({"pair": "ETHUSDT", "direction": "LONG"})
    assert ok is True
    assert errs == []
    assert d.get("symbol") == "ETHUSDT"


@pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="pydantic not installed")
def test_coerce_preserves_extra_keys():
    ok, _, d = validate_and_coerce_pick(
        {"symbol": "BTCUSDT", "data_lineage": {"stage": "test"}, "foo": 1}
    )
    assert ok is True
    assert d.get("data_lineage") == {"stage": "test"}
    assert d.get("foo") == 1
