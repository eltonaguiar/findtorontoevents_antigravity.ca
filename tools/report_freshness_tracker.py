#!/usr/bin/env python3
"""Report freshness tracker — produces a summary of all audit JSON files
and their freshness status.

Scans ``audit_dashboard/data/`` and ``audit_trail/data/`` for JSON files
that contain a ``generated_at`` (or ``generated_at_utc``) timestamp,
computes their age, and classifies them:

  GREEN  — generated within the last 24 hours
  YELLOW — generated within the last 7 days
  RED    — older than 7 days

Output is written to ``reports/report_freshness_YYYY-MM-DD.json`` and
printed to stdout as a summary table.

Usage:
    python -m tools.report_freshness_tracker
    python -m tools.report_freshness_tracker --green-hours 12   # tighten green threshold
    python -m tools.report_freshness_tracker --yellow-days 3    # tighten yellow threshold
    python -m tools.report_freshness_tracker --scan-dir audit_trail/data  # scan a single dir
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent

# Default scan directories (relative to ROOT)
DEFAULT_SCAN_DIRS = ["audit_dashboard/data", "audit_trail/data"]

# Subdirectories to skip (archives, research dumps, etc.)
SKIP_SUBDIRS = {"ai_leaderboard", "edge_stability", "money_ready_archive", "research"}


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON from a file, returning None on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _extract_generated_at(data: Any) -> Optional[datetime]:
    """Extract generated_at timestamp from various field names.

    Handles both dict and list top-level JSON structures.
    For lists, looks for generated_at in the first element if it's a dict.
    """
    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            return _extract_generated_at(data[0])
        return None
    if not isinstance(data, dict):
        return None

    for key in ("generated_at", "generated_at_utc", "timestamp", "snapshot_ts"):
        val = data.get(key)
        if not val:
            continue
        if isinstance(val, (int, float)):
            return datetime.fromtimestamp(val, tz=timezone.utc)
        if isinstance(val, str):
            try:
                ts = val
                if ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"
                dt = datetime.fromisoformat(ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, TypeError):
                continue
    return None


def _age_hours(gen_at: datetime, now: datetime) -> float:
    delta = now - gen_at
    return max(0, delta.total_seconds() / 3600.0)


def classify_freshness(
    age_hours: float,
    green_threshold_hours: float,
    yellow_threshold_hours: float,
) -> str:
    """Classify report freshness.

    GREEN  — strictly less than green_threshold_hours
    YELLOW — green_threshold_hours <= age < yellow_threshold_hours
    RED    — age >= yellow_threshold_hours
    """
    if age_hours < green_threshold_hours:
        return "GREEN"
    if age_hours < yellow_threshold_hours:
        return "YELLOW"
    return "RED"


def scan_directory(
    dir_path: Path,
    root: Path,
    now: datetime,
    green_hours: float,
    yellow_hours: float,
    skip_subdirs: set,
    min_size_bytes: int = 50,
) -> List[Dict[str, Any]]:
    """Scan a directory for JSON files with generated_at timestamps."""
    if not dir_path.is_dir():
        return []

    results: List[Dict[str, Any]] = []
    for json_file in sorted(dir_path.iterdir()):
        # Skip subdirectories in skip list
        if json_file.is_dir():
            if json_file.name in skip_subdirs:
                continue
            # Recurse into allowed subdirectories
            results.extend(
                scan_directory(json_file, root, now, green_hours, yellow_hours, skip_subdirs, min_size_bytes)
            )
            continue

        if not json_file.is_file() or not json_file.name.endswith(".json"):
            continue

        # Skip tiny files (likely placeholders or empty)
        if json_file.stat().st_size < min_size_bytes:
            continue

        data = _load_json(json_file)
        if data is None:
            continue

        gen_at = _extract_generated_at(data)
        if gen_at is None:
            continue

        age_h = _age_hours(gen_at, now)
        freshness = classify_freshness(age_h, green_hours, yellow_hours)

        rel_path = str(json_file.relative_to(root))

        results.append({
            "file": rel_path,
            "generated_at": gen_at.isoformat(),
            "age_hours": round(age_h, 1),
            "age_days": round(age_h / 24, 1),
            "freshness": freshness,
            "size_bytes": json_file.stat().st_size,
        })

    return results


def run_tracker(
    scan_dirs: Optional[List[str]] = None,
    green_hours: float = 24,
    yellow_hours: float = 168,  # 7 days
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the freshness tracker and return results."""
    now = datetime.now(timezone.utc)
    dirs_to_scan = scan_dirs if scan_dirs else DEFAULT_SCAN_DIRS

    all_results: List[Dict[str, Any]] = []
    for dir_name in dirs_to_scan:
        dir_path = ROOT / dir_name
        all_results.extend(
            scan_directory(dir_path, ROOT, now, green_hours, yellow_hours, SKIP_SUBDIRS)
        )

    # Sort by freshness (RED first, then YELLOW, then GREEN), then by age
    freshness_order = {"RED": 0, "YELLOW": 1, "GREEN": 2}
    all_results.sort(key=lambda x: (freshness_order.get(x["freshness"], 3), -x["age_hours"]))

    # Summary counts
    counts = {"GREEN": 0, "YELLOW": 0, "RED": 0}
    for r in all_results:
        c = r.get("freshness", "RED")
        counts[c] = counts.get(c, 0) + 1

    oldest_red = None
    for r in all_results:
        if r["freshness"] == "RED":
            oldest_red = r
            break

    summary = {
        "scan_at": now.isoformat(),
        "total_files_with_timestamp": len(all_results),
        "counts": counts,
        "oldest_red": oldest_red,
        "files": all_results,
    }

    # Write output
    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = ROOT / "reports"
    out_path.mkdir(parents=True, exist_ok=True)

    date_str = now.strftime("%Y-%m-%d")
    output_file = out_path / f"report_freshness_{date_str}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    return summary


def print_summary(summary: Dict[str, Any]) -> None:
    """Print a human-readable summary to stdout."""
    counts = summary["counts"]
    total = summary["total_files_with_timestamp"]

    print(f"\n{'='*70}")
    print(f"  Report Freshness Summary  ({summary['scan_at'][:19]} UTC)")
    print(f"{'='*70}")
    print(f"  Files with timestamp: {total}")
    print(f"  GREEN (<24h):  {counts.get('GREEN', 0)}")
    print(f"  YELLOW (<7d):  {counts.get('YELLOW', 0)}")
    print(f"  RED (>7d):     {counts.get('RED', 0)}")
    print(f"{'='*70}\n")

    files = summary.get("files", [])
    if not files:
        print("  No JSON files with generated_at found.")
        return

    # Print RED files first
    red_files = [f for f in files if f["freshness"] == "RED"]
    if red_files:
        print("  RED (stale):")
        for f in red_files:
            age_str = f"{f['age_hours']}h" if f["age_hours"] < 48 else f"{f['age_days']}d"
            print(f"    {f['file']:60s}  age={age_str:>7s}  gen={f['generated_at'][:19]}")
        print()

    yellow_files = [f for f in files if f["freshness"] == "YELLOW"]
    if yellow_files:
        print("  YELLOW (aging):")
        for f in yellow_files:
            age_str = f"{f['age_hours']}h" if f["age_hours"] < 48 else f"{f['age_days']}d"
            print(f"    {f['file']:60s}  age={age_str:>7s}  gen={f['generated_at'][:19]}")
        print()

    green_files = [f for f in files if f["freshness"] == "GREEN"]
    if green_files:
        print(f"  GREEN (fresh) — {len(green_files)} files")
        for f in green_files[:10]:
            age_str = f"{f['age_hours']:.1f}h"
            print(f"    {f['file']:60s}  age={age_str:>7s}")
        if len(green_files) > 10:
            print(f"    ... and {len(green_files) - 10} more")
        print()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Audit report freshness tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--green-hours",
        type=float,
        default=24,
        help="GREEN threshold in hours (default: 24)",
    )
    ap.add_argument(
        "--yellow-days",
        type=float,
        default=7,
        help="YELLOW threshold in days (default: 7)",
    )
    ap.add_argument(
        "--scan-dir",
        action="append",
        default=None,
        help="Override default scan directories (can specify multiple)",
    )
    ap.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override output directory for JSON report",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress stdout summary (only write JSON)",
    )
    args = ap.parse_args()

    yellow_hours = args.yellow_days * 24

    summary = run_tracker(
        scan_dirs=args.scan_dir,
        green_hours=args.green_hours,
        yellow_hours=yellow_hours,
        output_dir=args.output_dir,
    )

    if not args.quiet:
        print_summary(summary)

    # Exit non-zero if any RED files found
    red_count = summary["counts"].get("RED", 0)
    if red_count > 0:
        print(f"  WARNING: {red_count} stale (RED) reports found")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
