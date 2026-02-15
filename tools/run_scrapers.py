#!/usr/bin/env python3
"""
Run all Toronto event scrapers and merge results into events.json.

Usage:
    python tools/run_scrapers.py                    # Merge into events.json
    python tools/run_scrapers.py --output new.json  # Write to a different file
    python tools/run_scrapers.py --dry-run          # Print stats only
    python tools/run_scrapers.py --new-only         # Only run new scrapers
"""
import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.scrapers.unified_scraper import UnifiedTorontoScraper

# Multi-day title keywords (must match UI logic in index.html isMultiDayEvent())
MULTI_DAY_KEYWORDS = [
    'festival', 'exhibition', 'exhibit', 'runs until', 'conference',
    'ongoing', 'all month', 'all week', 'multiple dates', 'series',
]


def load_events(path):
    """Load existing events from JSON file."""
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_events(events, path):
    """Save events to JSON file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


def normalize_multiday_fields(event):
    """Ensure every event has both snake_case and camelCase multi-day fields.

    This is critical because:
      - Scraped events use snake_case (is_multi_day, end_date, duration_category)
      - Legacy AllEvents.in / UI events use camelCase (isMultiDay, endDate)
      - The React UI checks BOTH: event.is_multi_day || event.isMultiDay
      - detect_multiday.js sets isMultiDay (camelCase only)
    """
    # Sync end_date <-> endDate
    end_date = event.get("end_date") or event.get("endDate")
    if end_date:
        event["end_date"] = end_date
        event["endDate"] = end_date

    # Compute is_multi_day from date range (>=18h threshold matches UI)
    is_multi = event.get("is_multi_day", False) or event.get("isMultiDay", False)

    start_date = event.get("date", "")
    if not is_multi and start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date.replace("Z", "").split("+")[0].split("-05")[0])
            end = datetime.fromisoformat(end_date.replace("Z", "").split("+")[0].split("-05")[0])
            hours = (end - start).total_seconds() / 3600
            if hours >= 18:
                is_multi = True
        except (ValueError, TypeError):
            pass

    # Title keyword detection
    if not is_multi:
        text = f"{event.get('title', '')} {event.get('description', '')}".lower()
        if any(kw in text for kw in MULTI_DAY_KEYWORDS):
            is_multi = True

    # Set both conventions
    event["is_multi_day"] = is_multi
    event["isMultiDay"] = is_multi

    # Duration category
    dur = event.get("duration_category") or event.get("durationCategory") or "single"
    if is_multi and dur == "single" and start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date.replace("Z", "").split("+")[0].split("-05")[0])
            end = datetime.fromisoformat(end_date.replace("Z", "").split("+")[0].split("-05")[0])
            days = (end - start).days
            if days <= 7:
                dur = "short"
            elif days <= 30:
                dur = "medium"
            else:
                dur = "long"
        except (ValueError, TypeError):
            pass
    event["duration_category"] = dur
    event["durationCategory"] = dur

    # Sync other field pairs
    for snake, camel in [("is_free", "isFree"), ("price_amount", "priceAmount"),
                         ("last_updated", "lastUpdated"), ("is_recurring", "isRecurring")]:
        val = event.get(snake) if event.get(snake) is not None else event.get(camel)
        if val is not None:
            event[snake] = val
            event[camel] = val

    return event


def normalize_title(title):
    """Normalize title for dedup comparison."""
    import re
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def is_duplicate(event, existing_events):
    """Check if event is duplicate of an existing one."""
    norm_title = normalize_title(event.get("title", ""))
    event_date = event.get("date", "")[:10]

    for existing in existing_events:
        existing_norm = normalize_title(existing.get("title", ""))
        existing_date = existing.get("date", "")[:10]

        # Exact title match on same date
        if norm_title == existing_norm and event_date == existing_date:
            return True

        # Similar title (80% word overlap) on same date
        title_words = set(norm_title.split())
        existing_words = set(existing_norm.split())
        if title_words and existing_words:
            overlap = len(title_words & existing_words)
            max_words = max(len(title_words), len(existing_words))
            if overlap / max_words > 0.8 and event_date == existing_date:
                return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Run Toronto event scrapers")
    parser.add_argument("--output", "-o", default="events.json",
                        help="Output/merge target file (default: events.json)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print stats without writing")
    parser.add_argument("--backup", action="store_true", default=True,
                        help="Create backup before merging (default: true)")
    args = parser.parse_args()

    print("=" * 60)
    print(f"Toronto Event Scraper - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Load existing events
    existing = load_events(args.output)
    print(f"\nExisting events: {len(existing)}")

    # Backup
    if args.backup and existing and not args.dry_run:
        backup_path = args.output.replace('.json', '_backup.json')
        save_events(existing, backup_path)
        print(f"Backup saved to: {backup_path}")

    # Run all scrapers
    scraper = UnifiedTorontoScraper()
    new_events = scraper.scrape_all()
    print(f"\nScraped events: {len(new_events)}")

    # Normalize multi-day fields on existing events (backfill camelCase)
    print("\nNormalizing multi-day fields on existing events...")
    multi_before = sum(1 for e in existing if e.get("isMultiDay") or e.get("is_multi_day"))
    for event in existing:
        normalize_multiday_fields(event)
    multi_after = sum(1 for e in existing if e.get("isMultiDay"))
    print(f"  Multi-day events: {multi_before} -> {multi_after} (after keyword+date detection)")

    # Merge with existing (dedup)
    merged = existing.copy()
    added = 0
    sources_added = {}

    for event in new_events:
        normalize_multiday_fields(event)
        if not is_duplicate(event, merged):
            merged.append(event)
            added += 1
            source = event.get("source", "Unknown")
            sources_added[source] = sources_added.get(source, 0) + 1

    # Sort by date
    merged.sort(key=lambda x: x.get("date", ""))

    # Multi-day stats
    total_multi = sum(1 for e in merged if e.get("isMultiDay"))
    print(f"\n  Total multi-day events: {total_multi} / {len(merged)}")

    # Report
    print(f"\n{'='*60}")
    print("MERGE RESULTS")
    print('='*60)
    print(f"  Existing events: {len(existing)}")
    print(f"  New events scraped: {len(new_events)}")
    print(f"  New unique events added: {added}")
    print(f"  Total after merge: {len(merged)}")
    print()
    print("  New events by source:")
    for source, count in sorted(sources_added.items(), key=lambda x: -x[1]):
        print(f"    {source}: +{count}")

    # Events for today
    today_str = datetime.now().strftime('%Y-%m-%d')
    today_events = [e for e in merged if today_str in e.get('date', '')]
    print(f"\n  Events for today ({today_str}): {len(today_events)}")

    # All sources
    all_sources = {}
    for e in merged:
        s = e.get('source', 'Unknown')
        all_sources[s] = all_sources.get(s, 0) + 1
    print(f"\n  All sources ({len(all_sources)}):")
    for s, count in sorted(all_sources.items(), key=lambda x: -x[1]):
        print(f"    {s}: {count}")

    if not args.dry_run:
        save_events(merged, args.output)
        print(f"\nSaved {len(merged)} events to {args.output}")
    else:
        print("\n[DRY RUN] No files written.")


if __name__ == "__main__":
    main()
