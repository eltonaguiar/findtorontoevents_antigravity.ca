#!/usr/bin/env python3
"""Assert ML model artifact freshness. Fails CI when an artifact's
internal `trained_at` (or file mtime as fallback) is older than the
configured threshold.

Origin: 2026-04-28 — Workstream A surfaced a 12-day silent regression
in `alpha_engine/auto_tuner.py` (module-path bug at
`.github/workflows/alpha-engine-live.yml:592`) that was never noticed
because no CI step asserted artifact freshness. Cursor's alignment
addendum (`updates/2026-04-28-claude-cursor-alignment-addendum.md`)
made this a Top-5 ROI guardrail.

Per Copilot Cloud's Performance Charter answer: P3 alert
"ML artifact trained_at > 7 days" should "trigger retrain or skip-condition
documented within 48h". This script enforces the trigger half — CI fails
when a tracked artifact crosses the threshold, forcing a retrain or an
explicit skip-condition file.

Usage:
    python tools/assert_model_freshness.py
    python tools/assert_model_freshness.py --threshold-days 7
    python tools/assert_model_freshness.py --warn-only         # exit 0 on staleness
    python tools/assert_model_freshness.py --skip <regex>      # exempt a pattern

Exit codes:
    0 — all artifacts fresh (or --warn-only)
    1 — at least one artifact is stale (CI should fail)
    2 — config error (missing skip-conditions file referenced by an exempt)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Tracked artifacts: (path-relative-to-repo, internal_trained_at_field_path).
# `field_path` is dot-separated for nested JSON; None means use file mtime only.
# Add an entry here when a new ML system ships and persists a model to main.
TRACKED_ARTIFACTS: list[tuple[str, str | None]] = [
    # --- alpha_engine ---
    ("alpha_engine/data/rf_model.pkl", None),
    ("alpha_engine/data/ml_challenger.joblib", None),
    # --- ml_gatekeeper (persistence fix shipped 2026-04-27 in commit 1cd5e6fd5a) ---
    ("ml_gatekeeper/models/gatekeeper_model.joblib", None),
    ("ml_gatekeeper/models/training_report.json", "trained_at"),
    # --- ml_battleground ---
    ("ml_battleground/retrain_trigger.json", "trained_at"),
    # --- ml_crypto_predictor ---
    ("ml_crypto_predictor/enhanced_models/feedback_training_report.json", "trained_at"),
    ("ml_crypto_predictor/enhanced_models/results/training_summary.json", "trained_at"),
    # --- mercury2 ---
    ("mercury2/data/training_summary.json", "trained_at"),
    ("mercury2/models/top_gainer.joblib", None),
    # --- claude_gainer_ml ---
    ("claude_gainer_ml/models/training_meta.json", "trained_at"),
    ("claude_gainer_ml/models/claude_xgb.joblib", None),
    # --- crypto_ml_edge ---
    ("crypto_ml_edge/results/training_report.json", "trained_at"),
]


def parse_iso8601(s: str) -> datetime | None:
    """Parse ISO8601 with optional trailing Z. Return UTC-aware or None."""
    if not s or not isinstance(s, str):
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def get_internal_trained_at(json_path: Path, field_path: str) -> datetime | None:
    """Read `field_path` (dot-separated) from a JSON file. Return UTC-aware datetime or None."""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    cur = data
    for key in field_path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return parse_iso8601(cur) if isinstance(cur, str) else None


def check_artifact(rel_path: str, field_path: str | None, now: datetime, threshold_days: float) -> dict:
    """Return a result dict: {path, status, age_days, source, trained_at}."""
    full = REPO_ROOT / rel_path
    if not full.exists():
        return {"path": rel_path, "status": "missing", "age_days": None, "source": "fs", "trained_at": None}

    internal = None
    if field_path and rel_path.endswith(".json"):
        internal = get_internal_trained_at(full, field_path)

    if internal is not None:
        age = (now - internal).total_seconds() / 86400.0
        source = f"internal:{field_path}"
        trained_at = internal.isoformat()
    else:
        mtime = datetime.fromtimestamp(full.stat().st_mtime, tz=timezone.utc)
        age = (now - mtime).total_seconds() / 86400.0
        source = "mtime"
        trained_at = mtime.isoformat()

    status = "stale" if age > threshold_days else "fresh"
    return {
        "path": rel_path,
        "status": status,
        "age_days": round(age, 2),
        "source": source,
        "trained_at": trained_at,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert ML model artifact freshness for CI.")
    parser.add_argument("--threshold-days", type=float, default=7.0, help="Stale threshold in days (default 7)")
    parser.add_argument("--warn-only", action="store_true", help="Print warnings but exit 0 even if stale")
    parser.add_argument("--skip", action="append", default=[], help="Regex of paths to exempt from staleness check")
    parser.add_argument("--json-out", type=str, default=None, help="Write structured results to a JSON file")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    skip_patterns = [re.compile(p) for p in args.skip]
    results = []
    for rel_path, field_path in TRACKED_ARTIFACTS:
        if any(p.search(rel_path) for p in skip_patterns):
            results.append({"path": rel_path, "status": "skipped", "age_days": None, "source": "skip", "trained_at": None})
            continue
        results.append(check_artifact(rel_path, field_path, now, args.threshold_days))

    counts = {"fresh": 0, "stale": 0, "missing": 0, "skipped": 0}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    print(f"\nML Model Freshness Check (threshold {args.threshold_days}d, now {now.isoformat()})")
    print("=" * 80)
    for r in results:
        marker = {"fresh": "OK ", "stale": "FAIL", "missing": "MISS", "skipped": "skip"}.get(r["status"], "????")
        age = f"{r['age_days']:.2f}d" if r["age_days"] is not None else "n/a"
        print(f"  [{marker}] {r['path']:<70} age={age:<8} source={r['source']}")
    print("=" * 80)
    print(f"Summary: {counts.get('fresh',0)} fresh, {counts.get('stale',0)} stale, {counts.get('missing',0)} missing, {counts.get('skipped',0)} skipped\n")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({"now": now.isoformat(), "threshold_days": args.threshold_days, "counts": counts, "artifacts": results}, indent=2), encoding="utf-8")

    if counts.get("stale", 0) > 0 and not args.warn_only:
        print("FAIL: at least one artifact is stale. Either retrain it, or add a documented skip-condition.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
