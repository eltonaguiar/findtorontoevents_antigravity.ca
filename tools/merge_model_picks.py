#!/usr/bin/env python3
"""Merge model picks (picks_now_model_finpredict_v4.json) into picks_now.json.

Why this exists: picks_now.json is regenerated from scratch by
tools/picks_now_professional.py on the 06/12/18 UTC refresh, which wipes any
model picks previously merged into it. This script re-appends the model picks
after each regeneration so they survive. Both workflows (picks-now-refresh and
model-picks-emission) call it before save_picks_to_db.py / the freshness assert.

Behavior:
- Appends each model pick whose `symbol` is not already present in the
  destination (case-insensitive compare). Never overwrites or duplicates.
- Destination's other keys (notably `generated_at`) are preserved untouched,
  so the freshness assert (age < 2h) keeps passing after the merge.
- Missing or unparsable model file -> clear warning, exit 0 (non-fatal).
- Staleness: if the model file's `generated_at` is older than 48 hours we
  print a warning but STILL merge (documented choice). Rationale: the model is
  a monthly-rebalance Faber/dual-momentum allocation; its picks stay valid
  between monthly runs, and a hard skip would silently drop allocation picks
  from the live page for days. The warning surfaces the age in the CI log.
- Atomic write: temp file in the same dir + os.replace.

Usage:
  python3 tools/merge_model_picks.py                 # real repo paths
  python3 tools/merge_model_picks.py --dest D --src S  # test override
  python -m tools.merge_model_picks                  # also works
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DEST = REPO_ROOT / "audit_dashboard/data/picks_now.json"
DEFAULT_SRC = REPO_ROOT / "audit_dashboard/data/picks_now_model_finpredict_v4.json"
STALENESS_HOURS = 48


def _parse_ts(value):
    """Return a timezone-aware datetime or None."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_json(path, label):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        print(f"[merge_model_picks] WARNING: {label} not found at {path} — skipping merge (non-fatal).")
        return None
    except (json.JSONDecodeError, OSError) as e:
        print(f"[merge_model_picks] WARNING: could not read {label} at {path}: {e} — skipping merge (non-fatal).")
        return None


def atomic_write_json(path, payload):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description="Merge model picks into picks_now.json (non-fatal on missing model file).")
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="destination picks_now.json path")
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC, help="source model picks JSON path")
    args = ap.parse_args(argv)

    model = load_json(args.src, "model picks file")
    if model is None:
        return 0

    dest = load_json(args.dest, "destination picks file")
    if dest is None:
        # Destination problems are a real error (the pipeline needs picks_now.json).
        print(f"[merge_model_picks] ERROR: destination unavailable: {args.dest}", file=sys.stderr)
        return 1

    # Staleness warning (still merges — see module docstring).
    model_ts = _parse_ts(model.get("generated_at"))
    if model_ts is None:
        print(f"[merge_model_picks] WARNING: model file has no parsable generated_at ({model.get('generated_at')!r}) — merging anyway.")
    else:
        age_h = (datetime.now(timezone.utc) - model_ts).total_seconds() / 3600
        if age_h > STALENESS_HOURS:
            print(
                f"[merge_model_picks] WARNING: model picks are {age_h:.1f}h old "
                f"(> {STALENESS_HOURS}h) — stale but still merging (monthly-rebalance model)."
            )

    dest_picks = dest.get("picks") or []
    existing = {(p.get("symbol") or "").strip().lower() for p in dest_picks}
    model_picks = model.get("picks") or []

    merged, skipped = 0, 0
    for p in model_picks:
        sym = (p.get("symbol") or "").strip().lower()
        if not sym:
            continue
        if sym in existing:
            skipped += 1
            continue
        dest_picks.append(p)
        existing.add(sym)
        merged += 1

    if merged:
        # Preserve every other top-level key (incl. generated_at) untouched.
        dest["picks"] = dest_picks
        atomic_write_json(args.dest, dest)
        print(f"[merge_model_picks] merged {merged} new picks, skipped {skipped} duplicates -> {args.dest}")
    else:
        print(f"[merge_model_picks] merged 0 new picks, skipped {skipped} duplicates (no write needed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
