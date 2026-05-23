#!/usr/bin/env python3
"""
Data Lag Monitor — Computes staleness metrics for live data feeds.

Compares each feed entry's timestamp against the payload generation time.
Flags entries with lag > 60 minutes as stale.

Output: lag_stats.json with max_lag, avg_lag, stale_count, flagged list.

Usage:
    python data_lag_monitor.py --input feed_data.json --dry-run
    python data_lag_monitor.py --input feed_data.json --output lag_stats.json
"""

import json
import sys
import os
import argparse
from datetime import datetime, timezone


def parse_timestamp(ts_str):
    """Parse ISO-8601 timestamp string to datetime."""
    if ts_str is None:
        return None
    ts_str = ts_str.replace('Z', '+00:00')
    if '+' not in ts_str[-6:] and 'T' in ts_str:
        ts_str += '+00:00'
    try:
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def compute_lag_stats(feed_data):
    """Compute lag statistics from feed data.

    Args:
        feed_data: dict with 'feeds' list and optional 'generated_at'

    Returns:
        dict with max_lag_minutes, avg_lag_minutes, stale_count, flagged[]
    """
    generated_at = parse_timestamp(feed_data.get('generated_at'))
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)

    feeds = feed_data.get('feeds', feed_data.get('entries', feed_data.get('data', [])))
    if not feeds:
        return {
            'generated_at': generated_at.isoformat(),
            'max_lag_minutes': 0,
            'avg_lag_minutes': 0,
            'stale_count': 0,
            'total_feeds': 0,
            'flagged': [],
        }

    lags = []
    flagged = []

    for feed in feeds:
        ts = parse_timestamp(feed.get('timestamp') or feed.get('created_at') or feed.get('ts'))
        if ts is None:
            continue

        delta = generated_at - ts
        lag_minutes = delta.total_seconds() / 60.0

        # Handle slight clock skew (negative lag up to 1 min tolerance)
        if lag_minutes < -1:
            continue

        lag_minutes = max(0, lag_minutes)
        lags.append(lag_minutes)

        if lag_minutes > 60:
            flagged.append({
                'symbol': feed.get('symbol', feed.get('asset', feed.get('name', 'UNKNOWN'))),
                'lag_minutes': round(lag_minutes, 2),
                'timestamp': ts.isoformat(),
                'severity': 'critical' if lag_minutes > 120 else 'warning',
            })

    if not lags:
        return {
            'generated_at': generated_at.isoformat(),
            'max_lag_minutes': 0,
            'avg_lag_minutes': 0,
            'stale_count': 0,
            'total_feeds': 0,
            'flagged': [],
        }

    return {
        'generated_at': generated_at.isoformat(),
        'max_lag_minutes': round(max(lags), 2),
        'avg_lag_minutes': round(sum(lags) / len(lags), 2),
        'stale_count': len(flagged),
        'total_feeds': len(lags),
        'flagged': sorted(flagged, key=lambda x: x['lag_minutes'], reverse=True),
    }


def main():
    parser = argparse.ArgumentParser(description='Monitor data feed lag/staleness')
    parser.add_argument('--input', '-i', required=True,
                        help='Path to feed data JSON file')
    parser.add_argument('--output', '-o',
                        help='Output path for lag_stats.json')
    parser.add_argument('--threshold', type=float, default=60,
                        help='Staleness threshold in minutes (default: 60)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print stats without writing files')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, 'r') as f:
        feed_data = json.load(f)

    stats = compute_lag_stats(feed_data)

    if args.dry_run:
        print("=" * 50)
        print("DATA LAG MONITOR — DRY RUN")
        print("=" * 50)
        print(f"  Generated at:    {stats['generated_at']}")
        print(f"  Total feeds:     {stats['total_feeds']}")
        print(f"  Max lag (min):   {stats['max_lag_minutes']}")
        print(f"  Avg lag (min):   {stats['avg_lag_minutes']}")
        print(f"  Stale entries:   {stats['stale_count']}")
        if stats['flagged']:
            print("  Flagged feeds:")
            for f_entry in stats['flagged'][:10]:
                print(f"    {f_entry['symbol']:10s} lag={f_entry['lag_minutes']:7.1f}min "
                      f"[{f_entry['severity']}]")
        print("=" * 50)
    else:
        output_path = args.output or 'lag_stats.json'
        with open(output_path, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"Lag stats written to: {output_path}")
        if stats['stale_count'] > 0:
            print(f"WARNING: {stats['stale_count']} stale feed(s) detected!")


if __name__ == '__main__':
    main()
