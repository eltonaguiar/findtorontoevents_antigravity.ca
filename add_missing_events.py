#!/usr/bin/env python3
"""
Manual event-overrides patcher for findtorontoevents.ca.

Reads `data/manual_event_overrides.json` (a curated list of Toronto events that
human reviewers have verified are missing from the unified scraper output),
deduplicates against the live `events.json` catalog using the same
`UnifiedTorontoScraper.is_duplicate()` rules as the merge path, and appends
any new entries to both `events.json` and `next/events.json`.

Wired into `.github/workflows/scrape-events.yml` to run after the unified
scraper / sync step. Safe to run locally - it is idempotent.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent
EVENTS_PATH = PROJECT_ROOT / "events.json"
NEXT_EVENTS_PATH = PROJECT_ROOT / "next" / "events.json"
OVERRIDES_PATH = PROJECT_ROOT / "data" / "manual_event_overrides.json"

sys.path.insert(0, str(PROJECT_ROOT / "tools"))
from scrapers.unified_scraper import UnifiedTorontoScraper  # noqa: E402


def _load_json_array(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "events" in data and isinstance(data["events"], list):
        return data["events"]
    raise ValueError(f"{path}: expected JSON array or object with 'events' key")


def _save_json_array(path: Path, data: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _ensure_event_fields(event: dict) -> dict:
    """Fill in derived fields (id, *Updated timestamps) the catalog expects."""
    e = dict(event)
    if not e.get("id") or not isinstance(e.get("id"), str):
        raw = f"{e.get('title', '')}|{e.get('date', '')}|{e.get('source', '')}"
        e["id"] = hashlib.md5(raw.encode("utf-8")).hexdigest()
    now_iso = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    e.setdefault("last_updated", now_iso)
    e.setdefault("lastUpdated", e["last_updated"])
    e.setdefault("status", "UPCOMING")
    return e


def merge_overrides(catalog: List[dict], overrides: List[dict]) -> tuple[List[dict], int, int]:
    """Append non-duplicate overrides to catalog. Returns (catalog, added, skipped)."""
    scraper = UnifiedTorontoScraper()
    added = 0
    skipped = 0
    for raw in overrides:
        if not isinstance(raw, dict) or not raw.get("title") or not raw.get("date"):
            skipped += 1
            continue
        ev = _ensure_event_fields(raw)
        if scraper.is_duplicate(ev, catalog):
            skipped += 1
            continue
        catalog.append(ev)
        added += 1
    return catalog, added, skipped


def main() -> int:
    if not EVENTS_PATH.exists():
        print(f"ERROR: {EVENTS_PATH} not found", file=sys.stderr)
        return 1
    if not OVERRIDES_PATH.exists():
        print(f"No overrides file at {OVERRIDES_PATH}; nothing to do.")
        return 0

    catalog = _load_json_array(EVENTS_PATH)
    overrides = _load_json_array(OVERRIDES_PATH)
    print(f"Loaded {len(catalog)} catalog events and {len(overrides)} override candidates")

    if not overrides:
        print("Override list is empty; no changes.")
        return 0

    catalog, added, skipped = merge_overrides(catalog, overrides)
    print(f"Merged: +{added} new, {skipped} skipped (duplicate or invalid)")

    if added == 0:
        print("No new events to write.")
        return 0

    _save_json_array(EVENTS_PATH, catalog)
    print(f"Wrote {len(catalog)} events to {EVENTS_PATH}")

    NEXT_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EVENTS_PATH, NEXT_EVENTS_PATH)
    print(f"Mirrored to {NEXT_EVENTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
