"""Tests for add_missing_events.py manual-overrides patcher."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from add_missing_events import (  # noqa: E402
    _ensure_event_fields,
    merge_overrides,
)


def test_ensure_event_fields_fills_id_and_timestamps():
    raw = {"title": "Test Event", "date": "2026-06-01T12:00:00Z", "source": "manual"}
    out = _ensure_event_fields(raw)
    assert out["id"]
    assert isinstance(out["id"], str)
    assert out["last_updated"]
    assert out["lastUpdated"] == out["last_updated"]
    assert out["status"] == "UPCOMING"


def test_ensure_event_fields_preserves_existing_id():
    raw = {"title": "X", "date": "2026-06-01T12:00:00Z", "id": "preexisting123"}
    out = _ensure_event_fields(raw)
    assert out["id"] == "preexisting123"


def test_merge_overrides_skips_exact_duplicate():
    catalog = [{"title": "Toronto Jazz Fest", "date": "2026-06-20T12:00:00Z", "source": "scraper"}]
    overrides = [{"title": "Toronto Jazz Fest", "date": "2026-06-20T12:00:00Z", "source": "manual"}]
    new_catalog, added, skipped = merge_overrides(list(catalog), overrides)
    assert added == 0
    assert skipped == 1
    assert len(new_catalog) == 1


def test_merge_overrides_appends_new_event():
    catalog = [{"title": "Existing Show", "date": "2026-05-10T12:00:00Z"}]
    overrides = [{"title": "Brand New Show", "date": "2026-07-04T19:00:00Z", "source": "manual"}]
    new_catalog, added, skipped = merge_overrides(list(catalog), overrides)
    assert added == 1
    assert skipped == 0
    assert len(new_catalog) == 2
    assert new_catalog[1]["title"] == "Brand New Show"


def test_merge_overrides_skips_invalid_entries():
    catalog = []
    overrides = [
        {"title": "OK Event", "date": "2026-06-01T12:00:00Z"},
        {"title": ""},
        {"date": "2026-06-01T12:00:00Z"},
        "not a dict",
        {},
    ]
    new_catalog, added, skipped = merge_overrides(list(catalog), overrides)
    assert added == 1
    assert skipped == 4


def test_merge_overrides_dedup_uses_normalized_title():
    catalog = [{"title": "Toronto Jazz Fest", "date": "2026-06-20T12:00:00Z"}]
    overrides = [{"title": "TORONTO JAZZ FEST!", "date": "2026-06-20T12:00:00Z"}]
    _, added, skipped = merge_overrides(list(catalog), overrides)
    assert added == 0
    assert skipped == 1
