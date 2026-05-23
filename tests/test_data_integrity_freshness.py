"""Unit tests for tools/data_integrity/freshness_check.py."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from tools.data_integrity import freshness_check as fc  # noqa: E402

NOW = datetime(2026, 4, 12, 12, 0, 0, tzinfo=timezone.utc)
MIN_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)


def test_analyze_detects_stale():
    rows = [
        {"created_at": "2026-04-12 08:00:00"},  # 4h
        {"created_at": "2026-04-10 12:00:00"},  # 48h
    ]
    s = fc.analyze(rows, NOW, MIN_DATE)
    assert s["parseable"] == 2
    assert s["newest_age_hours"] == 4.0
    assert s["oldest_age_hours"] == 48.0
    assert s["future_count"] == 0
    assert s["prehistoric_count"] == 0


def test_analyze_detects_future_and_prehistoric():
    rows = [
        {"created_at": "2030-01-01 00:00:00"},  # future
        {"created_at": "2020-01-01 00:00:00"},  # prehistoric
        {"created_at": "2026-04-12 11:00:00"},  # 1h ok
    ]
    s = fc.analyze(rows, NOW, MIN_DATE)
    assert s["future_count"] == 1
    assert s["prehistoric_count"] == 1
    assert s["newest_age_hours"] == 1.0


def test_analyze_detects_disorder():
    rows = [
        {"created_at": "2026-04-10 12:00:00"},
        {"created_at": "2026-04-11 12:00:00"},
        {"created_at": "2026-04-09 12:00:00"},  # out of order
    ]
    s = fc.analyze(rows, NOW, MIN_DATE)
    assert s["disorder_transitions"] == 1


def test_main_exits_on_stale(tmp_path):
    active = tmp_path / "active.json"
    closed = tmp_path / "closed.json"
    active.write_text(json.dumps([{"created_at": "2026-04-01 00:00:00"}]))
    closed.write_text(json.dumps([{"created_at": "2026-04-12 11:00:00"}]))
    rc = fc.main([
        "--active", str(active), "--closed", str(closed),
        "--now", "2026-04-12T12:00:00Z", "--max-age-hours", "24",
    ])
    assert rc == 2


def test_main_passes_when_fresh(tmp_path):
    active = tmp_path / "active.json"
    closed = tmp_path / "closed.json"
    active.write_text(json.dumps([{"created_at": "2026-04-12 11:00:00"}]))
    closed.write_text(json.dumps([{"created_at": "2026-04-12 11:30:00"}]))
    rc = fc.main([
        "--active", str(active), "--closed", str(closed),
        "--now", "2026-04-12T12:00:00Z", "--max-age-hours", "24",
    ])
    assert rc == 0
