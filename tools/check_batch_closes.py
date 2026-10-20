#!/usr/bin/env python3
"""Operational batch-close validation (2026-10-20).

Scans a dashboard payload (or the nightly full export) and reports, per strategy:
  * any minute with >3 closes (the resolver run-time batch artifact), and
  * any rows with exit_price == 0.0 (fabricated flat-0% closes).

Exit 1 if either defect is present — this is the gate the fix must satisfy:
"no strategy with >3 closes in the same minute (unless the hit bars really
match)" and "zero rows with exit_price=0.0".

Usage:
  python tools/check_batch_closes.py --payload /path/to/dashboard_data.json
  python tools/check_batch_closes.py --payload audit_dashboard/data/closed_picks_full.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict


def _rows(payload: dict) -> list[dict]:
    """Accept either a dashboard_data.json or a closed_picks_full.json shape."""
    if isinstance(payload.get("rows"), list):
        return payload["rows"]  # full export
    return (payload.get("picks", {}) or {}).get("recent_closed", []) or []


def check(payload: dict, per_minute_cap: int = 3) -> int:
    rows = _rows(payload)
    print(f"scanned {len(rows)} closed rows")

    # 1) batch closes: group by (strategy, resolved/closed minute)
    by_strat_minute: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        strat = str(r.get("strategy") or r.get("source_system") or "UNKNOWN")
        ts = str(r.get("closed_at") or r.get("resolved_at") or "")
        minute = ts[:16]  # YYYY-MM-DDTHH:MM
        by_strat_minute[strat][minute] += 1

    batch_violations = []
    for strat, minutes in by_strat_minute.items():
        for minute, n in minutes.items():
            if n > per_minute_cap:
                batch_violations.append((strat, minute, n))

    # 2) fabricated flat-0% closes
    zero_price = [
        r for r in rows
        if r.get("exit_price") is not None
        and _is_zero(r.get("exit_price"))
        and str(r.get("status", "")).upper() != "UNRESOLVED_NO_PRICE"
    ]

    print(f"\n== batch closes (>{per_minute_cap} in one minute, per strategy) ==")
    if batch_violations:
        for strat, minute, n in sorted(batch_violations, key=lambda x: -x[2]):
            print(f"  {strat}: {n} closes at {minute}")
    else:
        print("  none")

    print(f"\n== exit_price == 0.0 rows (fabricated flat-0%) ==")
    if zero_price:
        for r in zero_price[:20]:
            print(f"  {r.get('strategy')} {r.get('symbol')} status={r.get('status')}")
        print(f"  ... total {len(zero_price)}")
    else:
        print("  none")

    defects = len(batch_violations) + len(zero_price)
    print(f"\nRESULT: {'FAIL' if defects else 'PASS'} ({defects} defects)")
    return 1 if defects else 0


def _is_zero(v) -> bool:
    try:
        return float(v) == 0.0
    except (TypeError, ValueError):
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--payload", required=True, help="dashboard_data.json or closed_picks_full.json")
    ap.add_argument("--cap", type=int, default=3, help="max same-minute closes per strategy")
    args = ap.parse_args()
    with open(args.payload, encoding="utf-8") as f:
        payload = json.load(f)
    sys.exit(check(payload, args.cap))


if __name__ == "__main__":
    main()
