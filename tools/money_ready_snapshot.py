#!/usr/bin/env python3
"""Money-Ready Verdict snapshot producer — feeds the /audit "Money Ready" tab.

Runs the verdict orchestrator, writes a current snapshot, archives one file
per UTC day, and computes drift vs the most-recent prior archive so the
dashboard can show improvement / degradation per asset class.

DECOUPLING (swarm-design P0, 3/3 engine consensus): this producer NEVER
imports `alpha_engine/money_ready_verdict.py`. It execs it as a subprocess
(`python alpha_engine/money_ready_verdict.py --json`) and parses stdout. A
peer is actively tweaking that module on another machine — the subprocess
boundary keeps this tool and the dashboard tab immune to those edits, as long
as the `--json` output schema below holds. If the schema drifts, this tool
fails LOUD rather than writing a half-valid snapshot.

Outputs (all under audit_dashboard/data/):
  money_ready_verdict.json                  — current snapshot + drift block
  money_ready_archive/money_ready_<date>.json — one immutable file per UTC day
  money_ready_archive/index.json            — sorted archive-date manifest

Usage:
    python tools/money_ready_snapshot.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERDICT_SCRIPT = ROOT / "alpha_engine" / "money_ready_verdict.py"
DATA_DIR = ROOT / "audit_dashboard" / "data"
ARCHIVE_DIR = DATA_DIR / "money_ready_archive"
CURRENT_PATH = DATA_DIR / "money_ready_verdict.json"
INDEX_PATH = ARCHIVE_DIR / "index.json"

# Keys every per-class verdict record must carry — the contract with the
# upstream module. Validation fails loud if the peer drops one.
REQUIRED_KEYS = (
    "n_resolved", "wr", "pf", "verdict",
    "n_ok", "wr_ok", "pf_ok",
    "dsr_ok", "pbo_ok", "spa_ok", "data_source",
)
VALID_VERDICTS = {"MONEY_READY", "WATCH", "NOT_READY", "INSUFFICIENT_DATA"}
# Retain ~13 months of daily archives; older files are pruned.
ARCHIVE_RETENTION_DAYS = 400


def run_verdict() -> dict:
    """Exec the verdict script and parse its --json stdout. Fail loud."""
    if not VERDICT_SCRIPT.exists():
        sys.exit(f"ERROR: verdict script not found: {VERDICT_SCRIPT}")
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    proc = subprocess.run(
        [sys.executable, str(VERDICT_SCRIPT), "--json"],
        capture_output=True, text=True, cwd=str(ROOT), env=env,
    )
    if proc.returncode != 0:
        sys.exit(f"ERROR: money_ready_verdict.py exited {proc.returncode}\n"
                 f"--- stderr ---\n{proc.stderr.strip()}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: verdict stdout is not valid JSON: {exc}\n"
                 f"--- stdout (first 500) ---\n{proc.stdout[:500]}")
    if not isinstance(data, dict) or not data:
        sys.exit("ERROR: verdict JSON is empty or not a class-keyed dict")
    return data


def validate(classes: dict) -> None:
    """Assert the upstream schema before anything is written."""
    for ac, rec in classes.items():
        if not isinstance(ac, str) or not ac.strip():
            sys.exit(f"ERROR: verdict has an empty / non-string class key: {ac!r}")
        if not isinstance(rec, dict):
            sys.exit(f"ERROR: class '{ac}' record is not an object")
        missing = [k for k in REQUIRED_KEYS if k not in rec]
        if missing:
            sys.exit(f"ERROR: class '{ac}' missing keys {missing} — "
                     f"money_ready_verdict.py --json schema changed; "
                     f"update REQUIRED_KEYS / the tab renderer together.")
        if rec["verdict"] not in VALID_VERDICTS:
            sys.exit(f"ERROR: class '{ac}' has unknown verdict "
                     f"'{rec['verdict']}' (expected one of {VALID_VERDICTS})")


def _num_delta(cur, prev):
    """Signed delta of two numbers, or None if either is missing."""
    if isinstance(cur, (int, float)) and isinstance(prev, (int, float)):
        return round(cur - prev, 4)
    return None


def compute_drift(classes: dict, prev: dict | None) -> dict:
    """Drift of current snapshot vs the most-recent prior archive.

    Per swarm consensus the signals that matter are: verdict change, the
    DSR/PBO/SPA pass-flag flips, and WR / PF / n_resolved deltas.
    """
    if not prev:
        return {"baseline": None, "note": "no prior archive — first snapshot"}
    prev_classes = prev.get("classes", {})
    per_class = {}
    for ac, rec in classes.items():
        p = prev_classes.get(ac)
        if not p:
            per_class[ac] = {"new_class": True}
            continue
        flips = {g: [p.get(g), rec.get(g)]
                 for g in ("dsr_ok", "pbo_ok", "spa_ok")
                 if p.get(g) != rec.get(g)}
        per_class[ac] = {
            "verdict_from": p.get("verdict"),
            "verdict_to": rec.get("verdict"),
            "verdict_changed": p.get("verdict") != rec.get("verdict"),
            "wr_delta": _num_delta(rec.get("wr"), p.get("wr")),
            "pf_delta": _num_delta(rec.get("pf"), p.get("pf")),
            "n_delta": _num_delta(rec.get("n_resolved"), p.get("n_resolved")),
            "gate_flips": flips,
        }
    return {"baseline": prev.get("generated_at"), "per_class": per_class}


def load_prev_archive() -> dict | None:
    """Most-recent archive strictly before today (drift baseline)."""
    if not INDEX_PATH.exists():
        return None
    try:
        dates = sorted(json.loads(INDEX_PATH.read_text("utf-8")).get("archives", []))
    except (json.JSONDecodeError, OSError):
        return None
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prior = [d for d in dates if d < today]
    if not prior:
        return None
    path = ARCHIVE_DIR / f"money_ready_{prior[-1]}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def rebuild_index() -> list[str]:
    """Re-derive the archive manifest from files on disk + prune old ones."""
    dates = sorted(
        p.stem.replace("money_ready_", "")
        for p in ARCHIVE_DIR.glob("money_ready_*.json")
    )
    if len(dates) > ARCHIVE_RETENTION_DAYS:
        for stale in dates[:-ARCHIVE_RETENTION_DAYS]:
            (ARCHIVE_DIR / f"money_ready_{stale}.json").unlink(missing_ok=True)
        dates = dates[-ARCHIVE_RETENTION_DAYS:]
    INDEX_PATH.write_text(
        json.dumps({"archives": dates, "count": len(dates)}, indent=2) + "\n",
        encoding="utf-8",
    )
    return dates


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="compute + print, write nothing")
    args = ap.parse_args()

    classes = run_verdict()
    validate(classes)

    now = datetime.now(timezone.utc)
    prev = load_prev_archive()
    drift = compute_drift(classes, prev)

    snapshot = {
        "generated_at": now.isoformat(),
        "generated_date": now.strftime("%Y-%m-%d"),
        "source": "alpha_engine/money_ready_verdict.py --json",
        "classes": classes,
        "drift": drift,
        "summary": {
            "money_ready": sorted(ac for ac, r in classes.items()
                                  if r["verdict"] == "MONEY_READY"),
            "watch": sorted(ac for ac, r in classes.items()
                            if r["verdict"] == "WATCH"),
            "n_classes": len(classes),
        },
    }

    if args.dry_run:
        print(json.dumps(snapshot, indent=2))
        return 0

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(snapshot, indent=2) + "\n"
    CURRENT_PATH.write_text(blob, encoding="utf-8")
    # Daily archive: idempotent — a same-day rerun overwrites today's file.
    (ARCHIVE_DIR / f"money_ready_{snapshot['generated_date']}.json").write_text(
        blob, encoding="utf-8")
    dates = rebuild_index()

    print(f"# wrote {CURRENT_PATH.relative_to(ROOT)}")
    print(f"# archived money_ready_{snapshot['generated_date']}.json "
          f"({len(dates)} archives retained)")
    print(f"# MONEY_READY: {snapshot['summary']['money_ready'] or 'none'}")
    print(f"# WATCH:       {snapshot['summary']['watch'] or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
