#!/usr/bin/env python3
"""
normalize_pnl_units.py
======================
One-time repair + guard: recompute pnl_pct = (exit_price / entry_price - 1) * direction
for every CLOSED pick in a JSON picks file and store as a DECIMAL RATIO
(e.g. -0.04 = -4%). OPEN / forward-test-only picks keep pnl_pct=None.
Writes a .bak backup before modifying.

Usage:
    python tools/normalize_pnl_units.py multi_asset/data/multi_asset_closed.json
    python tools/normalize_pnl_units.py multi_asset/data/institutional_closed.json
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

DIRECTION_MULT = {"LONG": 1, "SHORT": -1, "BUY": 1, "SELL": -1}


def _direction_mult(direction: str | None) -> int | None:
    if direction is None:
        return None
    return DIRECTION_MULT.get(str(direction).upper())


def normalize_picks(picks: list[dict[str, Any]]) -> dict[str, int]:
    stats = {
        "total": 0, "closed": 0, "fixed": 0, "skipped_no_exit": 0,
        "skipped_bad_price": 0, "converted_percent": 0, "ambiguous": 0,
    }
    for p in picks:
        stats["total"] += 1
        entry = p.get("entry_price")
        exit_px = p.get("exit_price") or p.get("close_price")
        direction = _direction_mult(p.get("direction"))
        status = p.get("status")

        # OPEN / forward-test-only picks: no PnL possible, leave null
        if status and str(status).upper() in ("OPEN", "ACTIVE"):
            p["pnl_pct"] = None
            stats["skipped_no_exit"] += 1
            continue

        if entry in (None, 0) or direction is None:
            stats["skipped_bad_price"] += 1
            continue

        stats["closed"] += 1

        # Case 1: we have exit_price -> recompute ratio from prices (authoritative)
        if exit_px not in (None, 0):
            ratio = round((float(exit_px) / float(entry) - 1.0) * direction, 6)
            existing = p.get("pnl_pct")
            if isinstance(existing, (int, float)) and existing is not None:
                if abs(float(existing)) > 1.0 and abs(float(existing) - ratio) > 1e-6:
                    p["pnl_pct"] = round(float(existing) / 100.0, 6)
                    stats["converted_percent"] += 1
                elif abs(float(existing) - ratio) > 1e-6:
                    p["pnl_pct"] = ratio
                    stats["fixed"] += 1
                else:
                    stats["fixed"] += 1
            else:
                p["pnl_pct"] = ratio
                stats["fixed"] += 1
            continue

        # Case 2: no exit_price but realized_pnl_pct exists (percent units -> ratio)
        realized = p.get("realized_pnl_pct")
        if isinstance(realized, (int, float)) and realized is not None:
            p["pnl_pct"] = round(float(realized) / 100.0, 6)
            stats["converted_percent"] += 1
            continue

        stats["skipped_bad_price"] += 1
    return stats


def main(path: str) -> int:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("ERROR: top-level JSON must be a list of picks", file=sys.stderr)
        return 2
    shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))
    stats = normalize_picks(data)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"file": str(p), **stats}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
