"""Optional Pydantic contracts for HF validation (skip if pydantic missing)."""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_TOOLS = _ROOT / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

pytest.importorskip("pydantic")

from hf_pick_contracts import PickValidationRow, validate_pick_dict  # noqa: E402


def test_validate_minimal_ok():
    ok, errs = validate_pick_dict({"symbol": "BTCUSDT", "asset_class": "CRYPTO"})
    assert ok and not errs


def test_validate_empty_symbol_fails():
    ok, errs = validate_pick_dict({"symbol": "", "asset_class": "CRYPTO"})
    assert not ok


def test_model_extra_allowed():
    row = PickValidationRow(symbol="X", extra_field=123).model_dump()
    assert row["symbol"] == "X"
