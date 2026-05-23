"""Reconcile closed_picks.json against universal_resolved_picks.json.

Reports overlap, disjoint sets, date ranges, and asset_class breakdown.
Exit non-zero if overlap percentage is below --min-overlap (default 20).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

# Allow running as "python tools/data_integrity/ledger_reconciliation.py".
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from tools.data_integrity._common import (  # noqa: E402
    CLOSED_PICKS,
    UNIVERSAL_RESOLVED,
    classify_asset,
    ensure_out_dir,
    load_json_list,
    parse_ts,
)


def _key(p: dict) -> tuple:
    """Fuzzy identity key for cross-ledger matching.

    Uses (symbol, direction_upper, strategy, yyyy-mm-dd of created/timestamp).
    """
    sym = str(p.get("symbol", "")).upper()
    direction = str(p.get("direction", "")).upper()
    strat = str(p.get("strategy", "")).lower()
    ts = p.get("created_at") or p.get("timestamp") or p.get("entry_time")
    dt = parse_ts(ts)
    day = dt.strftime("%Y-%m-%d") if dt else ""
    return (sym, direction, strat, day)


def _date_range(rows: list[dict], *fields: str) -> tuple[str | None, str | None]:
    vals = []
    for p in rows:
        for f in fields:
            dt = parse_ts(p.get(f))
            if dt:
                vals.append(dt)
                break
    if not vals:
        return None, None
    return min(vals).isoformat(), max(vals).isoformat()


def _asset_breakdown(rows: list[dict]) -> dict:
    c: Counter = Counter()
    raw: Counter = Counter()
    for p in rows:
        c[classify_asset(p)] += 1
        raw[str(p.get("asset_class"))] += 1
    return {"inferred": dict(c), "raw_field": dict(raw)}


def reconcile(closed: list[dict], universal: list[dict]) -> dict:
    closed_keys = {_key(p) for p in closed}
    uni_keys = {_key(p) for p in universal}
    overlap = closed_keys & uni_keys
    only_closed = closed_keys - uni_keys
    only_uni = uni_keys - closed_keys
    max_side = max(len(closed_keys), len(uni_keys)) or 1

    c_lo, c_hi = _date_range(closed, "created_at", "entry_time", "opened_at")
    u_lo, u_hi = _date_range(universal, "timestamp", "resolved_at")

    return {
        "closed_rows": len(closed),
        "universal_rows": len(universal),
        "closed_unique_keys": len(closed_keys),
        "universal_unique_keys": len(uni_keys),
        "overlap_keys": len(overlap),
        "overlap_pct_of_max": round(100.0 * len(overlap) / max_side, 2),
        "only_in_closed": len(only_closed),
        "only_in_universal": len(only_uni),
        "closed_date_range": [c_lo, c_hi],
        "universal_date_range": [u_lo, u_hi],
        "closed_asset_breakdown": _asset_breakdown(closed),
        "universal_asset_breakdown": _asset_breakdown(universal),
    }


def print_report(summary: dict) -> None:
    print("=" * 70)
    print("LEDGER RECONCILIATION REPORT")
    print("=" * 70)
    print(f"closed_picks.json              : {summary['closed_rows']} rows")
    print(f"universal_resolved_picks.json  : {summary['universal_rows']} rows")
    print(f"unique keys (closed/universal) : {summary['closed_unique_keys']} / {summary['universal_unique_keys']}")
    print(f"overlap keys                   : {summary['overlap_keys']} ({summary['overlap_pct_of_max']}%)")
    print(f"only in closed                 : {summary['only_in_closed']}")
    print(f"only in universal              : {summary['only_in_universal']}")
    print(f"closed date range              : {summary['closed_date_range']}")
    print(f"universal date range           : {summary['universal_date_range']}")
    print()
    print("Asset-class breakdown (closed_picks):")
    for k, v in sorted(summary["closed_asset_breakdown"]["inferred"].items(), key=lambda x: -x[1]):
        print(f"  {k:12s} {v}")
    print("  raw asset_class field values:", summary["closed_asset_breakdown"]["raw_field"])
    print()
    print("Asset-class breakdown (universal_resolved):")
    for k, v in sorted(summary["universal_asset_breakdown"]["inferred"].items(), key=lambda x: -x[1]):
        print(f"  {k:12s} {v}")
    print("  raw asset_class field values:", summary["universal_asset_breakdown"]["raw_field"])
    print()
    print("DATA-QUALITY NOTES:")
    raw_cp = summary["closed_asset_breakdown"]["raw_field"]
    if set(raw_cp.keys()) <= {"None", "null", "UNKNOWN", ""}:
        print("  - closed_picks.json asset_class field is entirely None/UNKNOWN.")
    if summary["overlap_pct_of_max"] < 50:
        print("  - Ledgers are FRAGMENTED: majority of rows exist in only one side.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--closed", default=CLOSED_PICKS)
    ap.add_argument("--universal", default=UNIVERSAL_RESOLVED)
    ap.add_argument("--min-overlap", type=float, default=20.0,
                    help="Minimum overlap percent to pass (default 20).")
    ap.add_argument("--out", default=os.path.join(ensure_out_dir(), "ledger_reconciliation.json"))
    args = ap.parse_args(argv)

    closed = load_json_list(args.closed)
    universal = load_json_list(args.universal)
    summary = reconcile(closed, universal)
    print_report(summary)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nWrote summary to {args.out}")

    if summary["overlap_pct_of_max"] < args.min_overlap:
        print(f"\nFAIL: overlap {summary['overlap_pct_of_max']}% < threshold {args.min_overlap}%")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
