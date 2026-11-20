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
