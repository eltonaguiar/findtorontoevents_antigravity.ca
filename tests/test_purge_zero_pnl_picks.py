"""Tests for P0.0a: purge_zero_pnl_picks.py."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_dry_run_does_not_mutate(tmp_path):
    src = tmp_path / "picks.json"
    src.write_text(json.dumps([
        {"id": "1", "pnl_pct": 5.0},
        {"id": "2", "pnl_pct": 0.0},
        {"id": "3", "pnl_pct": None},
        {"id": "4", "pnl_pct": -2.0},
    ]))
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "purge_zero_pnl_picks.py"),
         "--source", str(src), "--quarantine", str(tmp_path / "q.json")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    data = json.loads(src.read_text())
    assert len(data) == 4  # dry-run: no mutation


def test_apply_quarantines_zero_and_null(tmp_path):
    src = tmp_path / "picks.json"
    src.write_text(json.dumps([
        {"id": "1", "pnl_pct": 5.0},
        {"id": "2", "pnl_pct": 0.0},
        {"id": "3", "pnl_pct": None},
        {"id": "4", "pnl_pct": -2.0},
    ]))
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "purge_zero_pnl_picks.py"),
         "--source", str(src), "--quarantine", str(tmp_path / "q.json"), "--apply"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    data = json.loads(src.read_text())
    assert len(data) == 2
    assert {p["id"] for p in data} == {"1", "4"}
    q = json.loads((tmp_path / "q.json").read_text())
    assert q["quarantined_count"] == 2


def test_report_written(tmp_path):
    src = tmp_path / "picks.json"
    src.write_text(json.dumps([{"id": "1", "pnl_pct": 1.0}]))
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "purge_zero_pnl_picks.py"),
         "--source", str(src), "--quarantine", str(tmp_path / "q.json")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    report = ROOT / "reports" / "purge_zero_pnl_report.json"
    assert report.exists()
    d = json.loads(report.read_text())
    assert d["total_picks"] == 1
    assert d["kept"] == 1
    assert d["quarantined"] == 0


def test_suspicious_zero_pnl_with_price_move():
    """A zero pnl with price move should be flagged as suspicious."""
    from tools.purge_zero_pnl_picks import _quarantine_reason
    p = {"pnl_pct": 0.0, "entry_price": 100.0, "exit_price": 110.0}
    assert _quarantine_reason(p) == "suspicious_zero_pnl_with_price_move"


def test_genuine_zero_pnl():
    from tools.purge_zero_pnl_picks import _quarantine_reason
    p = {"pnl_pct": 0.0, "entry_price": 100.0, "exit_price": 100.0}
    assert _quarantine_reason(p) == "genuine_zero_pnl"


def test_null_pnl():
    from tools.purge_zero_pnl_picks import _quarantine_reason
    p = {"pnl_pct": None}
    assert _quarantine_reason(p) == "null_pnl"