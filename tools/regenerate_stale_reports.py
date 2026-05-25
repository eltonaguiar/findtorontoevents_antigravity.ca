#!/usr/bin/env python3
"""Regenerate stale audit reports.

Scans ``audit_dashboard/data/`` (and ``audit_trail/data/``) for JSON files
that contain a ``generated_at`` timestamp, compares against configurable
freshness thresholds, and either lists (``--dry-run``) or runs (``--execute``)
the corresponding generator scripts.

Usage:
    # See what would be regenerated (default)
    python -m tools.regenerate_stale_reports

    # Actually run the generators
    python -m tools.regenerate_stale_reports --execute

    # Override the stale threshold (default 7 days)
    python -m tools.regenerate_stale_reports --threshold-days 3

    # Regenerate a specific report by name
    python -m tools.regenerate_stale_reports --only health_report.json --execute
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Registry: report file -> (generator command, default freshness in days)
# ---------------------------------------------------------------------------
# Commands are relative to ROOT; they are executed with cwd=ROOT.
# generator can be:
#   - a string: run as ``python <cmd>``
#   - a dict with "cmd" (required) and optional "kwargs" dict for subprocess.run
#   - None: no known generator (manual / orphaned / external)
#
REGISTRY: Dict[str, Dict[str, Any]] = {
    "health_report.json": {
        "cmd": "tools/audit_data_health_pipeline.py",
        "freshness_days": 1,
        "scan_dirs": ["audit_dashboard/data"],
        "notes": "Runs health + edge counterfactual pipeline; also invokes analyze_audit_scores_vs_pnl.py",
    },
    "qa_report.json": {
        "cmd": "audit_dashboard/database_consolidation.py",
        "freshness_days": 7,
        "scan_dirs": ["audit_dashboard/data"],
        "notes": "Full QA report: duplicates, symbol normalization, JS error scan",
    },
    "edge_decay_heatmap.json": {
        "cmd": "tools/edge_decay_heatmap.py",
        "freshness_days": 7,
        "scan_dirs": ["audit_dashboard/data"],
        "notes": "Rolling 30d Profit Factor + Win Rate per strategy",
    },
    "hourly_asset_class_24h_report.json": {
        "cmd": None,
        "freshness_days": 1,
        "scan_dirs": ["audit_dashboard/data"],
        "notes": "No Python generator — drift system (JS/PS1). Manual regeneration required.",
    },
    "hf_quality_report.json": {
        "cmd": "audit_trail/hf_pick_validator.py --all --report",
        "freshness_days": 7,
        "scan_dirs": ["audit_trail/data"],
        "notes": "Hedge-fund pick quality validator; reads active_picks.json + friends",
    },
    "system_concentration.json": {
        "cmd": None,
        "freshness_days": 1,
        "scan_dirs": ["audit_trail/data"],
        "notes": "Written inline by audit_trail/dashboard_generator.py (M-004 module). Re-run dashboard_generator.",
    },
}


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    """Load a JSON file, returning None on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _extract_generated_at(data: Any) -> Optional[datetime]:
    """Extract generated_at timestamp from various field names.

    Handles both dict and list top-level JSON structures.
    Also checks common nested locations: data.snapshot.generated_at, data.snapshot.metadata.generated_at.
    """
    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            return _extract_generated_at(data[0])
        return None
    if not isinstance(data, dict):
        return None

    # Top-level keys
    for key in ("generated_at", "generated_at_utc"):
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

    # Common nested locations
    snapshot = data.get("snapshot")
    if isinstance(snapshot, dict):
        # snapshot.generated_at
        result = _extract_generated_at(snapshot)
        if result:
            return result
        # snapshot.metadata.generated_at
        metadata = snapshot.get("metadata")
        if isinstance(metadata, dict):
            result = _extract_generated_at(metadata)
            if result:
                return result

    return None


def _scan_for_reports(scan_dirs: List[str], only: Optional[str] = None) -> Dict[str, Path]:
    """Find all registered report files on disk."""
    found: Dict[str, Path] = {}
    for dir_name in scan_dirs:
        d = ROOT / dir_name
        if not d.is_dir():
            continue
        for report_name in REGISTRY:
            if only and report_name != only:
                continue
            candidate = d / report_name
            if candidate.is_file():
                found[report_name] = candidate
    return found


def _age_hours(dt: datetime, now: datetime) -> float:
    """Return age in hours between two datetimes."""
    delta = now - dt
    return delta.total_seconds() / 3600.0


def _age_days(dt: datetime, now: datetime) -> float:
    return _age_hours(dt, now) / 24.0


def classify_freshness(age_days: float, threshold_days: float) -> str:
    """Classify freshness: GREEN (<24h), YELLOW (<7d), RED (>=7d or >=threshold)."""
    if age_days < 1:
        return "GREEN"
    if age_days < 7:
        return "YELLOW"
    return "RED"


def check_staleness(
    only: Optional[str] = None,
    threshold_days: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Scan for stale reports and return a list of findings."""
    now = datetime.now(timezone.utc)
    results: List[Dict[str, Any]] = []

    for report_name, meta in REGISTRY.items():
        if only and report_name != only:
            continue

        scan_dirs = meta.get("scan_dirs", ["audit_dashboard/data"])
        found = _scan_for_reports(scan_dirs, only=only)
        report_path = found.get(report_name)

        entry: Dict[str, Any] = {
            "report": report_name,
            "path": str(report_path) if report_path else "NOT FOUND",
            "exists": report_path is not None,
            "freshness_threshold_days": threshold_days or meta.get("freshness_days", 7),
            "generator": meta.get("cmd"),
            "notes": meta.get("notes", ""),
        }

        if report_path is None:
            entry["status"] = "NOT_FOUND"
            results.append(entry)
            continue

        data = _load_json(report_path)
        if data is None:
            entry["status"] = "INVALID_JSON"
            entry["generated_at"] = None
            results.append(entry)
            continue

        gen_at = _extract_generated_at(data)
        entry["generated_at"] = gen_at.isoformat() if gen_at else None

        if gen_at is None:
            entry["status"] = "NO_TIMESTAMP"
            results.append(entry)
            continue

        age_d = _age_days(gen_at, now)
        entry["age_hours"] = round(age_d * 24, 1)
        entry["age_days"] = round(age_d, 1)

        effective_threshold = threshold_days if threshold_days is not None else meta.get("freshness_days", 7)
        freshness = classify_freshness(age_d, effective_threshold)
        entry["freshness"] = freshness

        if age_d > effective_threshold:
            entry["status"] = "STALE"
        else:
            entry["status"] = "FRESH"

        results.append(entry)

    return results


def _run_generator(report_name: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Run the generator for a single report. Returns result dict."""
    cmd = meta.get("cmd")
    if cmd is None:
        return {
            "report": report_name,
            "success": False,
            "error": "No generator registered — manual regeneration required",
        }

    # Parse command (may include args like --all --report)
    parts = cmd.split()
    full_cmd = [sys.executable] + parts

    try:
        result = subprocess.run(
            full_cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        return {
            "report": report_name,
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-500:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {
            "report": report_name,
            "success": False,
            "error": "Generator timed out after 600s",
        }
    except Exception as e:
        return {
            "report": report_name,
            "success": False,
            "error": str(e),
        }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Regenerate stale audit reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be regenerated (default)",
    )
    ap.add_argument(
        "--execute",
        action="store_true",
        help="Actually run the generators",
    )
    ap.add_argument(
        "--threshold-days",
        type=float,
        default=None,
        help="Override freshness threshold in days (default: per-report)",
    )
    ap.add_argument(
        "--only",
        type=str,
        default=None,
        help="Only check/regenerate this specific report file",
    )
    ap.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="Write findings to this JSON file",
    )
    args = ap.parse_args()

    findings = check_staleness(only=args.only, threshold_days=args.threshold_days)

    stale = [f for f in findings if f["status"] == "STALE"]
    fresh = [f for f in findings if f["status"] == "FRESH"]
    not_found = [f for f in findings if f["status"] in ("NOT_FOUND", "INVALID_JSON", "NO_TIMESTAMP")]

    # --- Summary ---
    print(f"\n{'='*70}")
    print(f"  Report Freshness Scan  ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})")
    print(f"{'='*70}")
    print(f"  Total registered:  {len(findings)}")
    print(f"  Fresh:             {len(fresh)}")
    print(f"  Stale:             {len(stale)}")
    print(f"  Not found/invalid: {len(not_found)}")
    print(f"{'='*70}\n")

    if stale:
        print("STALE REPORTS:")
        for f in stale:
            age_str = f"{f['age_hours']}h" if f.get("age_hours", 0) < 48 else f"{f['age_days']}d"
            gen = f["generator"] if f["generator"] else "NONE (manual)"
            print(f"  [{f['freshness']}] {f['report']:45s}  age={age_str:>6s}  gen={gen}")
        print()

    if fresh:
        print("FRESH REPORTS:")
        for f in fresh:
            age_str = f"{f['age_hours']}h" if f.get("age_hours", 0) < 48 else f"{f['age_days']}d"
            print(f"  [{f['freshness']}] {f['report']:45s}  age={age_str:>6s}")
        print()

    if not_found:
        print("NOT FOUND / INVALID:")
        for f in not_found:
            print(f"  [{f['status']}] {f['report']}")
        print()

    # --- Execute or dry-run ---
    if args.execute and stale:
        print(f"\n{'='*70}")
        print("  REGENERATING STALE REPORTS")
        print(f"{'='*70}\n")

        results = []
        for f in stale:
            report_name = f["report"]
            # Look up registry meta for the generator
            meta = REGISTRY.get(report_name, {})
            if not meta.get("cmd"):
                print(f"  SKIP {report_name}: {meta.get('notes', 'No generator')}")
                results.append({"report": report_name, "success": False, "error": "No generator"})
                continue

            print(f"  RUNNING {report_name} ...")
            res = _run_generator(report_name, meta)
            status = "OK" if res["success"] else "FAILED"
            print(f"  [{status}] {report_name}")
            if res.get("stderr"):
                print(f"    stderr: {res['stderr'][:200]}")
            results.append(res)

        ok_count = sum(1 for r in results if r.get("success"))
        print(f"\n  {ok_count}/{len(results)} generators succeeded")

        if args.json_output:
            output_path = Path(args.json_output)
        else:
            output_path = ROOT / "reports" / "regenerate_stale_results.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump({
                "run_at": datetime.now(timezone.utc).isoformat(),
                "findings": findings,
                "execution_results": results,
            }, fh, indent=2, default=str)
        print(f"  Results written to {output_path}")

    elif args.execute and not stale:
        print("\n  No stale reports to regenerate.")
    else:
        print("  (dry-run mode — use --execute to regenerate)")

    # --- JSON output (always, if requested) ---
    if args.json_output and not args.execute:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump({
                "run_at": datetime.now(timezone.utc).isoformat(),
                "mode": "dry-run",
                "findings": findings,
            }, fh, indent=2, default=str)
        print(f"  Dry-run results written to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
