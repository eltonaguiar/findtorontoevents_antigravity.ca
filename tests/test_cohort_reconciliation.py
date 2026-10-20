# tests/test_cohort_reconciliation.py
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.cohort_reconciliation import load_json, parse_ts


def _write_tmp(tmp_path, data):
    p = tmp_path / "f.json"
    p.write_text(json.dumps(data))
    return str(p)


def test_load_json_reads_valid(tmp_path):
    p = _write_tmp(tmp_path, {"a": 1})
    assert load_json(p) == {"a": 1}


def test_load_json_returns_none_when_missing(tmp_path):
    assert load_json(str(tmp_path / "nope.json")) is None


def test_load_json_raises_on_malformed(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    try:
        load_json(str(p))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_parse_ts_normalizes_z_and_microseconds():
    dt = parse_ts("2026-10-19T19:32:56.089767Z")
    assert dt.isoformat().startswith("2026-10-19T19:32:56")
    assert dt.tzinfo is not None
    dt2 = parse_ts("2026-06-21T06:31:08+00:00")
    assert dt2.tzinfo is not None
