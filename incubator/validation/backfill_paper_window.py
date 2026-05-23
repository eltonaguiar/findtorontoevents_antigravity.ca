#!/usr/bin/env python3
"""
Backfill started_at for zero-trade paper strategies to bootstrap FW evaluation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "incubator" / "agents"


def _load(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Backfill paper started_at for zero-trade strategies.")
    p.add_argument("--hours", type=int, default=72)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    now = datetime.now(timezone.utc)
    new_start = now - timedelta(hours=max(1, int(args.hours)))

    scanned = 0
    changed = 0
    for meta_path in AGENTS.rglob("*.py.meta.json"):
        scanned += 1
        meta = _load(meta_path)
        if str(meta.get("status", "")).lower() != "paper_trading":
            continue
        fwd = meta.get("forward_metrics", {}) if isinstance(meta.get("forward_metrics"), dict) else {}
        if int(fwd.get("total_trades") or 0) > 0:
            continue
        paper = meta.get("paper_trading", {}) if isinstance(meta.get("paper_trading"), dict) else {}
        if not paper.get("started_at"):
            continue

        paper["started_at"] = new_start.isoformat()
        paper["end_date"] = (now + timedelta(days=30)).isoformat()
        meta["paper_trading"] = paper
        changed += 1
        if not args.dry_run:
            _save(meta_path, meta)

    print(f"[BACKFILL] scanned={scanned} changed={changed} hours={args.hours} dry_run={bool(args.dry_run)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
