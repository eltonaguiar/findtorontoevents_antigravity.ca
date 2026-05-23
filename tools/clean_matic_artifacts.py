#!/usr/bin/env python3
"""One-shot clean of MATICUSDT data artifacts (2026-04-24).

Two distinct artifacts, both rooted in the Sep-2024 MATIC->POL Polygon rebrand.
Both inflate or deflate WR aggregates and contaminate downstream analyses.

Artifact A — `quan_engine` 100%-WR (positive)
=============================================
File: audit_trail/data/universal_resolved_picks.json
Pattern: source_system='quan_engine' AND symbol='MATICUSDT' AND
         abs(entry_price - 0.3794) < 1e-4 AND abs(pnl_pct - 2.5) < 1e-3
Cause: yfinance MATIC-USD feed frozen at ~$0.3794 post-rebrand. Scanner
emitted MATICUSDT LONG every ~45 min with TP at 2.5%; resolver compared
stale entry vs live POL price and marked TP_HIT.
Fix in PR #371 (MATICUSDT removed from quan_engine.config.SYMBOLS); this
script removes the legacy rows.

Artifact B — `-0.15` TIME_EXIT ghost (negative)
================================================
File: alpha_engine/data/closed_picks.json
Pattern: symbol='MATICUSDT' AND abs(pnl_pct - (-0.15)) < 1e-3 AND
         exit_reason in ('TIME_EXIT', 'TIME_EXPIRY')
Cause: MATIC->POL migration left placeholder TIME_EXIT rows that never
got cleaned up. Documented in memory project_confidence_rho_matic_artifact.

Usage
=====
Dry-run (default): just report counts.
    py -3.14 tools/clean_matic_artifacts.py

Apply: actually rewrite the JSONs.
    py -3.14 tools/clean_matic_artifacts.py --apply

Removed rows are archived to audit_trail/data/quarantine/<timestamp>/
for forensic recovery if needed.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

UNIVERSAL = REPO / "audit_trail" / "data" / "universal_resolved_picks.json"
CLOSED = REPO / "alpha_engine" / "data" / "closed_picks.json"
QUARANTINE_DIR = REPO / "audit_trail" / "data" / "quarantine"


def is_artifact_a(row: dict) -> bool:
    """quan_engine MATICUSDT @ entry=0.3794, pnl=2.5%, TP_HIT positive ghost."""
    if row.get("source_system") != "quan_engine":
        return False
    if row.get("symbol") != "MATICUSDT":
        return False
    try:
        ep = float(row.get("entry_price") or 0)
        pnl = float(row.get("pnl_pct") or 0)
    except (TypeError, ValueError):
        return False
    return abs(ep - 0.3794) < 1e-4 and abs(pnl - 2.5) < 1e-3


def is_artifact_b(row: dict) -> bool:
    """closed_picks MATICUSDT @ pnl=-0.15 TIME_EXIT/TIME_EXPIRY ghost."""
    if row.get("symbol") != "MATICUSDT":
        return False
    try:
        pnl = float(row.get("pnl_pct") or 0)
    except (TypeError, ValueError):
        return False
    if abs(pnl - (-0.15)) >= 1e-3:
        return False
    return str(row.get("exit_reason") or "").upper() in ("TIME_EXIT", "TIME_EXPIRY")


def split(rows: list[dict], predicate) -> tuple[list[dict], list[dict]]:
    keep, remove = [], []
    for r in rows:
        (remove if predicate(r) else keep).append(r)
    return keep, remove


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="Rewrite the JSONs (default is dry-run report only).")
    args = ap.parse_args()

    summary = []
    quarantines: list[tuple[Path, list[dict], str]] = []

    # --- Artifact A: universal_resolved_picks.json ---
    if UNIVERSAL.exists():
        with UNIVERSAL.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"!! {UNIVERSAL.name}: top-level not a list; skipping for safety",
                  file=sys.stderr)
        else:
            keep, remove = split(data, is_artifact_a)
            summary.append(("artifact_A_universal_resolved_picks",
                             len(data), len(keep), len(remove)))
            quarantines.append((UNIVERSAL, remove, "artifact_A"))
            if args.apply and remove:
                with UNIVERSAL.open("w", encoding="utf-8") as f:
                    json.dump(keep, f, ensure_ascii=False, indent=2)

    # --- Artifact B: closed_picks.json ---
    if CLOSED.exists():
        with CLOSED.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"!! {CLOSED.name}: top-level not a list; skipping",
                  file=sys.stderr)
        else:
            keep, remove = split(data, is_artifact_b)
            summary.append(("artifact_B_closed_picks_ghost",
                             len(data), len(keep), len(remove)))
            quarantines.append((CLOSED, remove, "artifact_B"))
            if args.apply and remove:
                with CLOSED.open("w", encoding="utf-8") as f:
                    json.dump(keep, f, ensure_ascii=False, indent=2)

    # --- Quarantine ---
    if args.apply:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        qdir = QUARANTINE_DIR / ts
        qdir.mkdir(parents=True, exist_ok=True)
        for src, removed, label in quarantines:
            if not removed:
                continue
            qpath = qdir / f"{src.stem}_{label}_removed.jsonl"
            with qpath.open("w", encoding="utf-8") as f:
                for row in removed:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"\nQuarantine archive: {qdir}")

    # --- Report ---
    print(f"\n{'mode':30s} {'before':>8s} {'after':>8s} {'removed':>8s}")
    print("-" * 60)
    total_removed = 0
    for label, before, after, removed in summary:
        print(f"{label:30s} {before:8d} {after:8d} {removed:8d}")
        total_removed += removed
    print("-" * 60)
    print(f"{'TOTAL':30s} {'':>8s} {'':>8s} {total_removed:8d}")

    if not args.apply:
        print("\n(dry-run; pass --apply to rewrite files)")
    else:
        print("\nApplied. Files rewritten.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
