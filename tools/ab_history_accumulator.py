#!/usr/bin/env python3
"""ab_history_accumulator.py — make the ml_gatekeeper A/B experiment produce durable data.

INCIDENT_OVERALL#134 (sharpened 2026-06-12): the A/B dual-write's NEW-arm file
(ml_gatekeeper/data/active_picks_ab_new.json) was a CI-local artifact never
committed, hourly snapshots overwrite each other, tags never survive into
closed_picks, and two stamp fields compete (_ab_arm vs _ab_sleeve). Net: the
"does leakage-purged ML help?" question was unanswerable — no data survived.

This accumulator runs right after the gatekeeper step and appends BOTH arms'
tagged picks to an append-only JSONL history with a canonical `_ab_arm` field
(accepts either stamp on read). Dedup key: (symbol, direction, arm, UTC-day).
Resolution happens later via the first-touch sidecar pattern
(tools/swarm/retro_resolve_swarm_archive.py) once history accrues.

Usage: python3 tools/ab_history_accumulator.py
Output: ml_gatekeeper/data/ab_history.jsonl  (committed by the workflow)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCES = [
    ("NEW", REPO / "ml_gatekeeper" / "data" / "active_picks_ab_new.json"),
    ("OLD", REPO / "alpha_engine" / "data" / "active_picks.json"),
]
HISTORY = REPO / "ml_gatekeeper" / "data" / "ab_history.jsonl"
KEEP = ("symbol", "direction", "entry_price", "take_profit", "stop_loss",
        "asset_class", "strategy", "source_system", "gatekeeper_score",
        "ml_score", "confidence", "timestamp", "created_at", "entry_time")


def main() -> int:
    seen: set[str] = set()
    if HISTORY.exists():
        for line in HISTORY.read_text().splitlines():
            try:
                seen.add(json.loads(line)["_dedup_key"])
            except Exception:
                continue

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    today = now[:10]
    added = 0
    with HISTORY.open("a") as out:
        for default_arm, path in SOURCES:
            if not path.exists():
                continue
            try:
                picks = json.loads(path.read_text())
            except Exception:
                continue
            for p in picks:
                if not isinstance(p, dict):
                    continue
                arm = p.get("_ab_arm") or p.get("_ab_sleeve")
                if arm is None and default_arm == "NEW":
                    arm = "NEW"  # everything in the NEW sidecar file is NEW-arm
                if arm not in ("OLD", "NEW"):
                    continue  # untagged production picks are not part of the A/B
                key = f"{p.get('symbol')}|{str(p.get('direction')).upper()}|{arm}|{today}"
                if key in seen:
                    continue
                seen.add(key)
                row = {k: p.get(k) for k in KEEP if p.get(k) is not None}
                row.update({"_ab_arm": arm, "_dedup_key": key, "_accumulated_at": now})
                out.write(json.dumps(row, default=str) + "\n")
                added += 1
    total = sum(1 for _ in HISTORY.open()) if HISTORY.exists() else 0
    print(f"[ab-accumulator] +{added} rows (history total {total})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
