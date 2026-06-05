"""Pick-data-quality gate — offline tests (thresholds + pass/fail + report-only)."""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import pick_data_quality_gate as g  # noqa: E402


def _clean(n=50):
    return [{"symbol": f"S{i}", "signal_ts": f"t{i}", "strategy": "x", "status": "CLOSED",
             "outcome": "WON" if i % 2 else "LOST", "pnl_pct": 1.0 if i % 2 else -1.0,
             "close_ts": "c", "source_system": "lux"} for i in range(n)]


def test_clean_ledger_passes():
    rep = g.evaluate(_clean())
    assert rep["passed"] is True
    assert all(c["pass"] for c in rep["checks"])


def test_mislabel_fails():
    picks = _clean()
    picks[0]["status"] = "EXPIRED"; picks[0]["outcome"] = "WON"  # EXPIRED->WON mislabel
    rep = g.evaluate(picks)
    assert rep["passed"] is False
    assert any(c["name"] == "mislabels" and not c["pass"] for c in rep["checks"])


def test_toxic_flood_fails(monkeypatch):
    picks = _clean(20)
    for p in picks[:12]:  # 60% toxic > 40% cap
        p["exit_reason"] = "FORCE_CLOSED_TOXIC"
    rep = g.evaluate(picks)
    assert rep["passed"] is False
    assert any(c["name"] == "toxic_pct" and not c["pass"] for c in rep["checks"])


def test_missing_provenance_fails():
    picks = _clean(20)
    for p in picks[:10]:  # 50% missing > 30% cap
        p.pop("source_system")
    rep = g.evaluate(picks)
    assert any(c["name"] == "missing_provenance_pct" and not c["pass"] for c in rep["checks"])


def test_report_only_no_mutation():
    picks = _clean(10)
    before = copy.deepcopy(picks)
    rep = g.evaluate(picks)
    assert picks == before
    assert rep["_mutated_ledger"] is False
