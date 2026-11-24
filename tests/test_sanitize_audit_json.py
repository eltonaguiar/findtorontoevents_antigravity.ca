"""Publish-time strict-JSON sanitizer: NaN/Infinity must never reach the browser."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "sanitize_audit_json.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args], capture_output=True, text=True, cwd=str(REPO)
    )


def test_nan_and_infinity_become_null(tmp_path):
    f = tmp_path / "verdict.json"
    f.write_text(
        '{"classes": {"COMMODITY": {"dsr_score": NaN, "pf": Infinity, "n": 229}}}\n',
        encoding="utf-8",
    )
    r = _run(str(f))
    assert r.returncode == 0, r.stderr
    data = json.loads(f.read_text(encoding="utf-8"))
    rec = data["classes"]["COMMODITY"]
    assert rec["dsr_score"] is None and rec["pf"] is None
    assert rec["n"] == 229  # real numbers untouched, not zeroed
    # re-emitted strictly: a browser-style parser must accept it now
    json.loads(f.read_text(encoding="utf-8"), parse_constant=lambda t: (_ for _ in ()).throw(ValueError(t)))


def test_clean_file_is_not_rewritten(tmp_path):
    f = tmp_path / "clean.json"
    original = json.dumps({"a": 1, "b": [None, 2.5]}, indent=2) + "\n"
    f.write_text(original, encoding="utf-8")
    r = _run(str(f), "--report")
    assert r.returncode == 0
    assert "1 clean" in r.stdout
    assert f.read_text(encoding="utf-8") == original


def test_check_mode_reports_without_writing(tmp_path):
    f = tmp_path / "ic.json"
    bad = '{"rows": [{"pf": Infinity}]}\n'
    f.write_text(bad, encoding="utf-8")
    r = _run(str(f), "--check")
    assert r.returncode == 1
    assert "non-strict" in r.stdout
    assert f.read_text(encoding="utf-8") == bad  # --check must not mutate


def test_unparseable_file_is_left_alone(tmp_path):
    f = tmp_path / "truncated.json"
    bad = '{"rows": [{"pf": 1.0'
    f.write_text(bad, encoding="utf-8")
    r = _run(str(f))
    assert r.returncode == 1
    assert "unparseable" in r.stdout
    assert f.read_text(encoding="utf-8") == bad
