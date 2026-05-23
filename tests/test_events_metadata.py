"""Tests for events metadata.json generation (homepage Last updated header)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from events_metadata import build_events_metadata, max_event_last_updated_iso  # noqa: E402


def test_build_events_metadata_shape():
    events = [
        {"title": "A", "source": "blogTO", "lastUpdated": "2026-05-20T10:00:00Z"},
        {"title": "B", "source": "Eventbrite", "last_updated": "2026-05-19T08:00:00Z"},
        {"title": "C", "source": "blogTO"},
    ]
    meta = build_events_metadata(events, "2026-05-20T13:00:55Z")
    assert meta["lastUpdated"] == "2026-05-20T13:00:55Z"
    assert meta["totalEvents"] == 3
    assert meta["sources"] == ["Eventbrite", "blogTO"]


def test_max_event_last_updated_iso():
    events = [
        {"lastUpdated": "2026-05-18T01:00:00Z"},
        {"last_updated": "2026-05-20T22:00:00Z"},
    ]
    assert max_event_last_updated_iso(events) == "2026-05-20T22:00:00Z"
