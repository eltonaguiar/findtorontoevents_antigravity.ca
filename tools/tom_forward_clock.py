#!/usr/bin/env python3
"""tom_forward_clock.py — forward-only harness for H-2026-11-23-01 (turn-of-month CRYPTO).

Pre-registered 2026-11-23. This harness REFUSES any entry dated before
FREEZE (2026-11-23). It emits 0 rows until a post-freeze turn-of-month date has
closed and a real bar is available — a forward measurement, not a backtest.

Kill rule is frozen in reports/prereg_H-2026-11-23-01.json and enforced by
tools/two_hurdle_kill.py semantics. This harness never computes an edge from
pre-freeze data.
"""
import argparse, json, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

FREEZE = date(2026, 11, 23)
OUT = Path("reports/tom_forward_clock.json")


def last_trading_day_of_month(y, m):
    d = date(y, m + 1, 1) - timedelta(days=1) if m < 12 else date(y, 12, 31)
    return d


def candidate_entries(start=date.today()):
    """Turn-of-month entry dates at or after max(start, FREEZE)."""
    cur = max(start, FREEZE)
    out = []
    y, m = cur.year, cur.month
    for _ in range(12):
        ltd = last_trading_day_of_month(y, m)
        if ltd >= max(start, FREEZE):
            out.append(ltd.isoformat())
        m += 1
        if m > 12:
            m = 1; y += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=None, help="override today (ISO) for testing")
    args = ap.parse_args()
    today = date.fromisoformat(args.today) if args.today else datetime.now(timezone.utc).date()

    if today < FREEZE:
        print(f"REFUSED: today {today} < freeze {FREEZE}; harness will not measure pre-freeze data", file=sys.stderr)
        return 2

    cands = candidate_entries(today)
    state = {
        "hypothesis":"H-2026-11-23-01", "frozen_at":FREEZE.isoformat(),
        "today":today.isoformat(),
        "candidate_entry_dates":cands,
        "n_records":0,
        "records":[],
        "note":"0 records is correct until a post-freeze TOM entry has closed and a real bar exists. This is a forward harness, not a claim.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state, indent=2) + "\n")
    print(f"tom_forward_clock: {len(cands)} candidate entry dates, n_records=0 (no closed post-freeze TOM entries yet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
