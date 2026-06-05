#!/usr/bin/env python3
"""Alias pick_summary_stats_2w.json → pick_summary_stats_14d.json for live /audit."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "audit_dashboard/data/pick_summary_stats_2w.json"
DST = ROOT / "audit_dashboard/data/pick_summary_stats_14d.json"


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: missing {SRC}", file=sys.stderr)
        return 1
    shutil.copy2(SRC, DST)
    data = json.loads(DST.read_text(encoding="utf-8"))
    data["alias_of"] = "pick_summary_stats_2w.json"
    data["window_label"] = "14d"
    DST.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"OK: {DST} ({DST.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())