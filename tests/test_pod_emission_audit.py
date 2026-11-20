import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.pod_emission_audit import audit  # noqa: E402


def _man(*pods):
    return {"pods": list(pods)}


def test_flags_strategies_with_zero_rows_in_both_tables():
    m = _man({"id": "P", "status": "pre_registered", "strategies": ["ghost"]})
    r = audit(m, {"ghost": {"picks": 0, "intrabar": 0}})
    assert r["ok"] is False and r["n_phantom"] == 1
    assert r["phantom"][0]["strategy"] == "ghost"


def test_emitted_in_either_table_is_enough():
    m = _man({"id": "P", "strategies": ["a", "b"]})
    r = audit(m, {"a": {"picks": 3, "intrabar": 0}, "b": {"picks": 0, "intrabar": 2}})
    assert r["ok"] is True and r["n_phantom"] == 0


def test_unemitted_approved_pod_is_exempt():
    m = _man({"id": "P", "status": "unemitted_approved", "strategies": ["ghost"]})
    r = audit(m, {"ghost": {"picks": 0, "intrabar": 0}})
    assert r["ok"] is True
    assert r["strategies"][0]["approved_unemitted"] is True


def test_missing_strategy_in_counts_is_phantom():
    m = _man({"id": "P", "strategies": ["unknown"]})
    r = audit(m, {})
    assert r["ok"] is False and r["n_phantom"] == 1


def test_flags_a_strategy_that_emits_only_in_undeclared_asset_classes():
    """The 2026-11-20 trap: an 'equity' pod pointed at crypto-only emitters."""
    m = _man({"id": "P", "status": "pre_registered", "asset_classes": ["EQUITY", "ETF"],
              "strategies": ["donchian_breakout_scalp"]})
    c = {"donchian_breakout_scalp": {"picks": 81, "intrabar": 26, "classes": ["CRYPTO", "MEMECOIN"]}}
    r = audit(m, c)
    assert r["ok"] is False and r["n_class_mismatch"] == 1
    assert r["phantom"] == []
    assert r["class_mismatch"][0]["emitted_classes"] == ["CRYPTO", "MEMECOIN"]


def test_matching_class_is_not_flagged_and_unknown_class_is_not_assumed():
    m = _man({"id": "P", "asset_classes": ["ETF"], "strategies": ["a", "b"]})
    r = audit(m, {"a": {"picks": 5, "intrabar": 2, "classes": ["ETF"]},
                  "b": {"picks": 5, "intrabar": 2, "classes": []}})
    assert r["ok"] is True and r["n_class_mismatch"] == 0
