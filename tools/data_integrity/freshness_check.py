"""Freshness check for active_picks.json and closed_picks.json.

Exits non-zero when:
  - newest pick is older than --max-age-hours (default 24)
  - any pick has created_at in the future
  - any pick has created_at before --min-date (default 2025-01-01)
  - any file has out-of-order timestamps (count > --max-disorder)
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from tools.data_integrity._common import (  # noqa: E402
    ACTIVE_PICKS,
    CLOSED_PICKS,
    load_json_list,
    parse_ts,
)


def analyze(rows: list[dict], now: datetime, min_date: datetime) -> dict:
    ages_hours: list[float] = []
    future: list[dict] = []
    prehistoric: list[dict] = []
    parseable = 0
    for p in rows:
        ts = parse_ts(p.get("created_at") or p.get("entry_time") or p.get("opened_at"))
        if ts is None:
            continue
        parseable += 1
        if ts > now:
            future.append(p)
            continue
        if ts < min_date:
            prehistoric.append(p)
            continue
        ages_hours.append((now - ts).total_seconds() / 3600.0)

    # Out-of-order check: iterate in file order, count descending transitions.
    disorder = 0
    prev = None
    for p in rows:
        ts = parse_ts(p.get("created_at") or p.get("entry_time") or p.get("opened_at"))
        if ts is None:
            continue
        if prev is not None and ts < prev:
            disorder += 1
        prev = ts

    # Age buckets for histogram.
    buckets = Counter()
    for h in ages_hours:
        if h < 1:
            buckets["<1h"] += 1
        elif h < 24:
            buckets["1-24h"] += 1
        elif h < 24 * 7:
            buckets["1-7d"] += 1
        elif h < 24 * 30:
            buckets["7-30d"] += 1
        else:
            buckets[">30d"] += 1

    newest = min(ages_hours) if ages_hours else None
    oldest = max(ages_hours) if ages_hours else None
    return {
        "total": len(rows),
        "parseable": parseable,
        "newest_age_hours": newest,
        "oldest_age_hours": oldest,
        "age_buckets": dict(buckets),
        "future_count": len(future),
        "prehistoric_count": len(prehistoric),
        "disorder_transitions": disorder,
    }


def print_report(name: str, s: dict) -> None:
    print(f"\n--- {name} ---")
    print(f"  total rows            : {s['total']}")
    print(f"  parseable timestamps  : {s['parseable']}")
    if s["newest_age_hours"] is not None:
        print(f"  newest age (hours)    : {s['newest_age_hours']:.2f}")
        print(f"  oldest age (hours)    : {s['oldest_age_hours']:.2f}")
    print(f"  age buckets           : {s['age_buckets']}")
    print(f"  future timestamps     : {s['future_count']}")
    print(f"  prehistoric (<min)    : {s['prehistoric_count']}")
    print(f"  out-of-order trans    : {s['disorder_transitions']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--active", default=ACTIVE_PICKS)
    ap.add_argument("--closed", default=CLOSED_PICKS)
    ap.add_argument("--max-age-hours", type=float, default=24.0)
    ap.add_argument("--min-date", default="2025-01-01")
    ap.add_argument("--max-disorder", type=int, default=50)
    ap.add_argument("--now", default=None, help="Override current time (ISO).")
    args = ap.parse_args(argv)

    now = parse_ts(args.now) if args.now else datetime.now(timezone.utc)
    min_date = parse_ts(args.min_date) or datetime(2025, 1, 1, tzinfo=timezone.utc)

    print("=" * 70)
    print("FRESHNESS REPORT")
    print(f"now={now.isoformat()}  min_date={min_date.isoformat()}")
    print("=" * 70)

    failures: list[str] = []
    for label, path in (("active_picks", args.active), ("closed_picks", args.closed)):
        try:
            rows = load_json_list(path)
        except FileNotFoundError:
            print(f"\n--- {label} --- SKIP (file not found: {path})")
            continue
        s = analyze(rows, now, min_date)
        print_report(label, s)
        if s["newest_age_hours"] is not None and s["newest_age_hours"] > args.max_age_hours:
            failures.append(f"{label}: newest pick {s['newest_age_hours']:.1f}h > {args.max_age_hours}h")
        if s["future_count"]:
            failures.append(f"{label}: {s['future_count']} future timestamps")
        if s["prehistoric_count"]:
            failures.append(f"{label}: {s['prehistoric_count']} prehistoric timestamps")
        if s["disorder_transitions"] > args.max_disorder:
            failures.append(f"{label}: {s['disorder_transitions']} out-of-order > {args.max_disorder}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        return 2
    print("\nOK: all freshness thresholds satisfied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
