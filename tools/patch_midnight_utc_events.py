#!/usr/bin/env python3
"""
Patch existing events.json files to fix midnight UTC timestamps.

Events stored as "2026-04-17T00:00:00Z" appear on the previous day in EDT/EST
because midnight UTC is 8 PM EDT / 7 PM EST the day before.

This script rewrites T00:00:00Z → T12:00:00Z for date, end_date, and endDate
fields, which keeps the event on the intended Toronto calendar day
(12:00 UTC = 8:00 AM EDT / 7:00 AM EST).

Usage:
    python tools/patch_midnight_utc_events.py
"""
import json
import sys
from pathlib import Path


def patch_event(event: dict) -> tuple[dict, bool]:
    """Return (patched_event, was_modified)."""
    modified = False
    for key in ("date", "end_date", "endDate"):
        val = event.get(key)
        if isinstance(val, str) and val.endswith("T00:00:00Z"):
            event[key] = val.replace("T00:00:00Z", "T12:00:00Z")
            modified = True
    return event, modified


def patch_file(path: Path) -> int:
    """Patch a single events.json file. Returns number of events modified."""
    if not path.exists():
        print(f"  SKIP: {path} not found")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    events = data if isinstance(data, list) else data.get("events", [])
    total = len(events)
    modified_count = 0

    for event in events:
        _, was_modified = patch_event(event)
        if was_modified:
            modified_count += 1

    with open(path, "w", encoding="utf-8") as f:
        if isinstance(data, list):
            json.dump(events, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  {path}: {modified_count}/{total} events patched")
    return modified_count


def main() -> int:
    workspace = Path(__file__).resolve().parent.parent
    files = [
        workspace / "events.json",
        workspace / "next" / "events.json",
    ]

    total_modified = 0
    for path in files:
        total_modified += patch_file(path)

    print(f"\nTotal events patched: {total_modified}")
    return 0 if total_modified >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
