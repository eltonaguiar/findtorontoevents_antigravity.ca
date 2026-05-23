"""Source-liveness watchdog.

Measures modification-time (mtime) and row-count delta for every
JSON_PICK_SOURCES file. Produces a warn-only artifact at
``reports/health/source_liveness_<date>.json`` so the operator can
distinguish genuine silent failures (emitter stopped writing) from
dashboard-layer artifacts (cap/filter/stratification changes).

Per Fix 4 of reports/silent_failure_investigation_2026_04_29.md:
  The panel's >70% volume-drop watchdog MUST measure at the source-file
  layer (mtime + row count by date), not the dashboard layer, or it
  will keep producing false-positive SEV-1 alerts.

Exit code: always 0 (warn-only). Never raises; log.warning() for issues.

Usage:
    python -m tools.source_liveness_watchdog
    python -m tools.source_liveness_watchdog --output-dir reports/health
    python -m tools.source_liveness_watchdog --stale-hours 12 --drop-pct 70
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent

# Default thresholds
DEFAULT_STALE_HOURS = 26       # warn if file not touched in >26h (covers daily crons with buffer)
DEFAULT_DROP_PCT = 70          # warn if row count drops >70% vs previous snapshot
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "health"
SNAPSHOT_KEY = "source_liveness_snapshot"


def _count_picks(data: Any) -> int:
    """Return the best estimate of pick count from a loaded JSON payload."""
    if isinstance(data, list):
        return len(data)
    if not isinstance(data, dict):
        return 0
    # Try common pick-array keys in priority order
    for key in (
        "long_picks", "active_picks", "picks", "consensus_picks", "activePicks",
        "open_picks", "signals", "predictions", "trades", "top", "winners",
    ):
        val = data.get(key)
        if isinstance(val, list):
            return len(val)
    # Count all list values combined (some sources split by bucket)
    total = 0
    for val in data.values():
        if isinstance(val, list) and val and isinstance(val[0], dict):
            total += len(val)
    return total


def _load_json_safe(path: Path) -> Any:
    """Load JSON file; return None on any error."""
    try:
        return json.loads(path.read_bytes())
    except Exception:
        return None


def check_sources(
    stale_hours: float = DEFAULT_STALE_HOURS,
    drop_pct: float = DEFAULT_DROP_PCT,
    previous_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check all JSON_PICK_SOURCES for staleness and row-count drops.

    Returns a result dict with:
      - ``checked``: total sources checked
      - ``stale``: list of {source, path, age_hours, last_modified}
      - ``dropped``: list of {source, path, prev_count, curr_count, drop_pct}
      - ``missing``: list of {source, path} where file doesn't exist
      - ``snapshot``: {source: {count, mtime}} for next run comparison
      - ``ok``: count of sources with no issues
    """
    # Import here to avoid circular-import during module-level analysis
    try:
        from audit_trail.dashboard_generator import JSON_PICK_SOURCES
    except ImportError as e:
        log.error("Cannot import JSON_PICK_SOURCES: %s", e)
        return {"error": str(e), "checked": 0}

    now_ts = time.time()
    stale_threshold_s = stale_hours * 3600

    stale: list[dict] = []
    dropped: list[dict] = []
    missing: list[dict] = []
    snapshot: dict[str, dict] = {}
    ok = 0

    seen_paths: set[str] = set()  # deduplicate active + closed paths

    for source_name, active_path, closed_path in JSON_PICK_SOURCES:
        for path_str in (active_path, closed_path):
            if path_str is None or path_str in seen_paths:
                continue
            seen_paths.add(path_str)

            path = ROOT / path_str
            if not path.exists():
                missing.append({"source": source_name, "path": path_str})
                continue

            try:
                mtime = path.stat().st_mtime
            except OSError:
                missing.append({"source": source_name, "path": path_str})
                continue

            age_h = (now_ts - mtime) / 3600.0

            data = _load_json_safe(path)
            curr_count = _count_picks(data) if data is not None else 0

            snapshot_key = path_str
            snapshot[snapshot_key] = {"count": curr_count, "mtime": mtime}

            has_issue = False

            # Staleness check
            if age_h > stale_hours:
                stale.append({
                    "source": source_name,
                    "path": path_str,
                    "age_hours": round(age_h, 1),
                    "last_modified": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                })
                has_issue = True

            # Row-count-drop check (only if we have a previous snapshot)
            if previous_snapshot and snapshot_key in previous_snapshot:
                prev_count = previous_snapshot[snapshot_key].get("count", 0)
                if prev_count > 0 and curr_count < prev_count:
                    actual_drop = (1 - curr_count / prev_count) * 100
                    if actual_drop >= drop_pct:
                        dropped.append({
                            "source": source_name,
                            "path": path_str,
                            "prev_count": prev_count,
                            "curr_count": curr_count,
                            "drop_pct": round(actual_drop, 1),
                        })
                        has_issue = True

            if not has_issue:
                ok += 1

    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "thresholds": {"stale_hours": stale_hours, "drop_pct": drop_pct},
        "checked": len(seen_paths),
        "ok": ok,
        "stale_count": len(stale),
        "dropped_count": len(dropped),
        "missing_count": len(missing),
        "stale": stale,
        "dropped": dropped,
        "missing": missing,
        "snapshot": snapshot,
    }


def load_previous_snapshot(output_dir: Path) -> dict[str, Any] | None:
    """Load the most recent snapshot from a prior watchdog run."""
    latest = output_dir / "source_liveness_latest.json"
    if not latest.exists():
        return None
    data = _load_json_safe(latest)
    if isinstance(data, dict):
        return data.get("snapshot")
    return None


def write_report(result: dict[str, Any], output_dir: Path) -> Path:
    """Write the watchdog report to output_dir. Returns path to the file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M")
    dated_path = output_dir / f"source_liveness_{date_str}.json"
    latest_path = output_dir / "source_liveness_latest.json"

    payload = json.dumps(result, indent=2, default=str)
    dated_path.write_text(payload, encoding="utf-8")
    latest_path.write_text(payload, encoding="utf-8")

    return dated_path


def log_summary(result: dict[str, Any]) -> None:
    """Log a human-readable summary of the watchdog result."""
    level = logging.WARNING if (result.get("stale_count", 0) + result.get("dropped_count", 0) + result.get("missing_count", 0)) > 0 else logging.INFO
    log.log(
        level,
        "[LIVENESS] checked=%d ok=%d stale=%d dropped=%d missing=%d",
        result.get("checked", 0),
        result.get("ok", 0),
        result.get("stale_count", 0),
        result.get("dropped_count", 0),
        result.get("missing_count", 0),
    )
    for item in result.get("stale", []):
        log.warning(
            "[STALE] %s @ %s — %.1fh old (last modified %s)",
            item["source"], item["path"], item["age_hours"], item["last_modified"],
        )
    for item in result.get("dropped", []):
        log.warning(
            "[DROP] %s @ %s — %d → %d picks (%.1f%% drop)",
            item["source"], item["path"],
            item["prev_count"], item["curr_count"], item["drop_pct"],
        )
    for item in result.get("missing", [])[:10]:  # cap at 10 to avoid spam
        log.warning("[MISSING] %s @ %s", item["source"], item["path"])


def main(argv: list[str] | None = None) -> int:
    """Entry point. Always returns 0 (warn-only)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--stale-hours", type=float, default=DEFAULT_STALE_HOURS)
    parser.add_argument("--drop-pct", type=float, default=DEFAULT_DROP_PCT)
    parser.add_argument("--no-snapshot", action="store_true",
                        help="Skip loading previous snapshot (first-run mode)")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    prev_snapshot = None if args.no_snapshot else load_previous_snapshot(output_dir)

    result = check_sources(
        stale_hours=args.stale_hours,
        drop_pct=args.drop_pct,
        previous_snapshot=prev_snapshot,
    )

    log_summary(result)

    report_path = write_report(result, output_dir)
    log.info("[LIVENESS] Report written: %s", report_path)

    return 0  # always 0 — warn-only


if __name__ == "__main__":
    raise SystemExit(main())
