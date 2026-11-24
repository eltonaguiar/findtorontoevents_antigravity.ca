"""Tests for tools/check_excluded_summary.py (Block 61).

Stdlib only, no network: every case feeds the checker local files under
``tmp_path``. The one thing these tests exist to protect is the Block 59/60
trap -- ``total: 0`` and an absent ``_excluded_cohort_rows`` key must produce
*distinct* messages, because ``total: 0`` is what an un-wired payload also
looks like.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "check_excluded_summary.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True, text=True, cwd=str(ROOT),
    )


def _write(tmp_path: Path, name: str, data) -> str:
    path = tmp_path / name
    path.write_text(data if isinstance(data, str) else json.dumps(data),
                    encoding="utf-8")
    return str(path)


def _fed_payload() -> dict:
    return {
        "metadata": {"repo_sha": "abc1234"},
        "_excluded_cohort_rows": {
            "integrity_excluded": [
                {"asset_class": "CRYPTO", "exclude_reason": "invalid_row"},
                {"asset_class": "EQUITY", "exclude_reason": "invalid_row"},
            ],
            "auto_expired": [
                {"asset_class": "CRYPTO", "exclude_reason": "auto_expired"},
            ],
        },
    }


def _fed_ledger() -> dict:
    return {"coverage": {"excluded_summary": {
        "total": 3,
        "by_class": {"CRYPTO": 2, "EQUITY": 1},
        "by_reason": {"invalid_row": 2, "auto_expired": 1},
    }}}


def test_fed_payload_and_ledger_exit_zero(tmp_path):
    payload = _write(tmp_path, "payload.json", _fed_payload())
    ledger = _write(tmp_path, "ledger.json", _fed_ledger())
    proc = _run("--payload", payload, "--ledger", ledger)
    assert proc.returncode == 0, proc.stderr
    assert "FED" in proc.stdout
    assert "abc1234" in proc.stdout


def test_missing_key_exits_one_with_key_absent_message(tmp_path):
    payload = _write(tmp_path, "payload.json",
                     {"metadata": {"repo_sha": "deadbee"}})
    proc = _run("--payload", payload)
    assert proc.returncode == 1
    assert "key absent" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_zero_total_exits_one_with_not_yet_fed_message(tmp_path):
    payload = _write(tmp_path, "payload.json", {
        "metadata": {"repo_sha": "abc1234"},
        "_excluded_cohort_rows": {"integrity_excluded": []},
    })
    proc = _run("--payload", payload)
    assert proc.returncode == 1
    assert "not yet fed" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_zero_total_from_ledger_exits_one(tmp_path):
    payload = _write(tmp_path, "payload.json", _fed_payload())
    ledger = _write(tmp_path, "ledger.json", {"coverage": {"excluded_summary": {
        "total": 0, "by_class": {}, "by_reason": {}}}})
    proc = _run("--payload", payload, "--ledger", ledger)
    assert proc.returncode == 1
    assert "not yet fed" in proc.stderr


def test_total_positive_but_empty_by_class_exits_one(tmp_path):
    payload = _write(tmp_path, "payload.json", _fed_payload())
    ledger = _write(tmp_path, "ledger.json", {"coverage": {"excluded_summary": {
        "total": 5, "by_class": {}, "by_reason": {"invalid_row": 5}}}})
    proc = _run("--payload", payload, "--ledger", ledger)
    assert proc.returncode == 1
    assert "by_class is empty" in proc.stderr


def test_expect_min_above_actual_total_exits_one(tmp_path):
    payload = _write(tmp_path, "payload.json", _fed_payload())
    proc = _run("--payload", payload, "--expect-min", "99")
    assert proc.returncode == 1
    assert "--expect-min" in proc.stderr


def test_malformed_json_exits_one_without_traceback(tmp_path):
    payload = _write(tmp_path, "payload.json", "{not valid json")
    proc = _run("--payload", payload)
    assert proc.returncode == 1
    assert "malformed JSON" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_missing_file_exits_one_without_traceback(tmp_path):
    proc = _run("--payload", str(tmp_path / "nope.json"))
    assert proc.returncode == 1
    assert "no such file" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_zero_total_and_absent_key_messages_are_distinct(tmp_path):
    """The Block 59/60 trap: these two states must never read the same."""
    absent = _run("--payload", _write(tmp_path, "a.json", {"metadata": {}}))
    zero = _run("--payload", _write(tmp_path, "z.json", {
        "_excluded_cohort_rows": {"integrity_excluded": []}}))
    assert absent.returncode == 1 and zero.returncode == 1
    assert absent.stderr.strip() != zero.stderr.strip(), (
        "an absent key and a zero total must not produce the same message")
    assert "key absent" in absent.stderr
    assert "key absent" not in zero.stderr
    assert "not yet fed" in zero.stderr
    assert "not yet fed" not in absent.stderr
