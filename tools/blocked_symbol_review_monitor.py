#!/usr/bin/env python3
"""
blocked_symbol_review_monitor.py

Loads audit_trail/blocked_registry.json, compares review_date to today,
flags overdue items (review_date < today), writes
audit_trail/alerts/overdue_unblock_reviews.json, and prints a summary.

No external dependencies — stdlib only (json, datetime, pathlib).

Usage:
    python tools/blocked_symbol_review_monitor.py
    python tools/blocked_symbol_review_monitor.py --date 2026-06-01  # override "today"

Exit codes:
    0 — no overdue items
    1 — one or more overdue items found
"""

import json
import sys
import argparse
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "audit_trail" / "blocked_registry.json"
ALERTS_DIR = REPO_ROOT / "audit_trail" / "alerts"
ALERTS_PATH = ALERTS_DIR / "overdue_unblock_reviews.json"


def load_registry(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def check_overdue(registry: dict, today: date) -> list[dict]:
    """Return list of overdue items across all entity sections."""
    overdue = []

    sections = {
        "entities": registry.get("entities", {}),
        "source_systems": registry.get("source_systems", {}),
        "probation": registry.get("probation", {}),
    }

    for section_name, entries in sections.items():
        for key, entry in entries.items():
            review_date_str = entry.get("review_date")
            if not review_date_str:
                continue
            try:
                review_date = parse_date(review_date_str)
            except ValueError:
                continue

            if review_date < today:
                days_overdue = (today - review_date).days
                overdue.append(
                    {
                        "key": key,
                        "section": section_name,
                        "type": entry.get("type", section_name.rstrip("s")),
                        "asset_class": entry.get("asset_class"),
                        "stage": entry.get("stage"),
                        "review_date": review_date_str,
                        "days_overdue": days_overdue,
                        "block_reason": entry.get("block_reason"),
                        "current_stats": entry.get("current_stats"),
                        "notes": entry.get("notes"),
                    }
                )

    overdue.sort(key=lambda x: x["days_overdue"], reverse=True)
    return overdue


def write_alerts(overdue: list[dict], today: date, alerts_path: Path) -> None:
    alerts_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": today.isoformat(),
        "overdue_count": len(overdue),
        "items": overdue,
    }
    with open(alerts_path, "w") as f:
        json.dump(payload, f, indent=2)


def print_summary(overdue: list[dict], today: date) -> None:
    print(f"\n=== Blocked Symbol Review Monitor ===")
    print(f"Today: {today}")
    print(f"Registry: audit_trail/blocked_registry.json")
    print(f"Alerts: audit_trail/alerts/overdue_unblock_reviews.json")
    print()

    if not overdue:
        print("No overdue reviews found.")
        return

    print(f"OVERDUE REVIEWS ({len(overdue)}):")
    print("-" * 70)
    for item in overdue:
        cls = item.get("asset_class") or "N/A"
        stage = item.get("stage") or "N/A"
        days = item["days_overdue"]
        print(
            f"  [{item['key']}]  class={cls}  stage={stage}"
            f"  review_date={item['review_date']}  ({days}d overdue)"
        )
        if item.get("current_stats"):
            stats = item["current_stats"]
            n = stats.get("n", "?")
            wr = stats.get("wr_pct", "?")
            pf = stats.get("pf", "?")
            print(f"    current stats: n={n}, WR={wr}%, PF={pf}")
        if item.get("block_reason"):
            print(f"    block_reason: {item['block_reason'][:80]}")
    print("-" * 70)


def pending_reviews_upcoming(registry: dict, today: date, days_ahead: int = 30) -> list[dict]:
    """Return items with review_date within the next N days (not yet overdue)."""
    upcoming = []
    sections = {
        "entities": registry.get("entities", {}),
        "source_systems": registry.get("source_systems", {}),
        "probation": registry.get("probation", {}),
    }
    for section_name, entries in sections.items():
        for key, entry in entries.items():
            review_date_str = entry.get("review_date")
            if not review_date_str:
                continue
            try:
                review_date = parse_date(review_date_str)
            except ValueError:
                continue
            days_until = (review_date - today).days
            if 0 <= days_until <= days_ahead:
                upcoming.append(
                    {
                        "key": key,
                        "asset_class": entry.get("asset_class"),
                        "stage": entry.get("stage"),
                        "review_date": review_date_str,
                        "days_until": days_until,
                    }
                )
    upcoming.sort(key=lambda x: x["days_until"])
    return upcoming


def main() -> int:
    parser = argparse.ArgumentParser(description="Check blocked symbol review dates")
    parser.add_argument(
        "--date",
        default=None,
        help="Override today's date (YYYY-MM-DD). Default: system date.",
    )
    parser.add_argument(
        "--upcoming-days",
        type=int,
        default=30,
        help="Also show items due within N days (default 30).",
    )
    args = parser.parse_args()

    if args.date:
        today = parse_date(args.date)
    else:
        today = date.today()

    if not REGISTRY_PATH.exists():
        print(f"ERROR: Registry not found at {REGISTRY_PATH}", file=sys.stderr)
        return 2

    registry = load_registry(REGISTRY_PATH)
    overdue = check_overdue(registry, today)
    write_alerts(overdue, today, ALERTS_PATH)
    print_summary(overdue, today)

    # Print upcoming reviews
    upcoming = pending_reviews_upcoming(registry, today, days_ahead=args.upcoming_days)
    if upcoming:
        print(f"\nUPCOMING REVIEWS (next {args.upcoming_days} days):")
        for item in upcoming:
            cls = item.get("asset_class") or "N/A"
            print(
                f"  [{item['key']}]  class={cls}  stage={item.get('stage')}  "
                f"review_date={item['review_date']}  (in {item['days_until']}d)"
            )

    print(f"\nAlerts written to: {ALERTS_PATH}")
    return 1 if overdue else 0


if __name__ == "__main__":
    sys.exit(main())
