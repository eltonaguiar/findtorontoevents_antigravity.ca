import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # repo root


def run(tmp, rows):
    p = tmp / "payload.json"
    p.write_text(json.dumps({"picks": {"recent_closed": rows}}))
    return subprocess.run([sys.executable,
                           str(HERE / "tools" / "excluded_cohorts_report.py"),
                           "--payload", str(p), "--json"],
                          capture_output=True, text=True)


def test_report_json_counts(tmp_path):
    rows = [
        {"symbol": "A", "pnl_pct": 1.0},
        {"symbol": "B", "pnl_pct": 2.0},
        {"symbol": "C", "pnl_pct": 0.0, "_auto_expired": True},
        {"symbol": "D", "pnl_pct": 0.0, "_auto_expired": True},
    ]
    r = run(tmp_path, rows)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["payload_rows"] == 4 and out["retained_rows"] == 2
    assert out["excluded_rows"] == 2
    assert out["included"]["mean_pnl_pct"] == 1.5
    assert out["retained_minus_excluded_pp"] == 1.5


def test_report_no_rows_exits_2(tmp_path):
    r = run(tmp_path, [])
    assert r.returncode == 2


def test_stale_reason_counts_as_excluded(tmp_path):
    rows = [{"symbol": "A", "pnl_pct": 1.0},
            {"symbol": "B", "pnl_pct": 0.0,
             "exit_reason": "STALE (auto-expired >168h)"}]
    r = run(tmp_path, rows)
    out = json.loads(r.stdout)
    assert out["excluded_rows"] == 1 and out["retained_rows"] == 1


def test_counts_only_mode(tmp_path):
    p = tmp_path / "payload.json"
    p.write_text(json.dumps({"resolved_closed_picks_net": {"counts": {
        "input_rows": 10, "kept_rows": 6, "excluded_rows": 4,
        "excluded_by_reason": {"invalid_row": 3, "mirror_duplicate": 1}}}}))
    r = subprocess.run([sys.executable,
                        str(HERE / "tools" / "excluded_cohorts_report.py"),
                        "--payload", str(p), "--json"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["measurement"] == "counts_only"
    assert out["excluded_rows"] == 4
    assert out["pnl_available"] is False
