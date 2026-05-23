#!/usr/bin/env python3
"""Regenerate metadata.json from existing events.json / next/events.json (no scrape)."""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from events_metadata import max_event_last_updated_iso, write_events_metadata  # noqa: E402


def _load_events(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("events", [])


def main() -> int:
    events_path = PROJECT_ROOT / "next" / "events.json"
    if not events_path.is_file():
        events_path = PROJECT_ROOT / "events.json"
    if not events_path.is_file():
        print(f"No events file at {events_path}", file=sys.stderr)
        return 1

    events = _load_events(events_path)
    last_updated = None
    last_update_path = PROJECT_ROOT / "last_update.json"
    if last_update_path.is_file():
        with open(last_update_path, encoding="utf-8") as f:
            last_updated = json.load(f).get("timestamp")

    event_max = max_event_last_updated_iso(events)
    if event_max and (not last_updated or event_max > last_updated):
        last_updated = event_max

    meta = write_events_metadata(events, last_updated)
    print(
        f"OK: lastUpdated={meta['lastUpdated']} totalEvents={meta['totalEvents']} "
        f"sources={len(meta['sources'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
