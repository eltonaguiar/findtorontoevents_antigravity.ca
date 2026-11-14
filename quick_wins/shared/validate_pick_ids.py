#!/usr/bin/env python3
"""
validate_pick_ids.py
====================
CI-enforced pick-ID uniqueness: id must be unique per strategy+symbol+date
(ideally strategy::symbol::date_timestamp). Fails CI (exit 1) on duplicates.
Also flags picks missing id / entry_price / direction.

Usage:
    python tools/validate_pick_ids.py multi_asset/data/multi_asset_closed.json \
        multi_asset/data/institutional_closed.json multi_asset/data/multi_asset_picks.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def validate_file(path: str) -> list[str]:
    errors: list[str] = []
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        errors.append(f"{path}: top-level JSON must be a list of picks")
        return errors
    seen: dict[str, list[int]] = {}
    for i, pick in enumerate(data):
        if not isinstance(pick, dict):
            errors.append(f"{path}[{i}]: not a pick object")
            continue
        pid = pick.get("id")
        if not pid:
            errors.append(f"{path}[{i}]: missing id (symbol={pick.get('symbol')})")
            continue
        seen.setdefault(str(pid), []).append(i)
        for field in ("entry_price", "direction", "symbol"):
            if pick.get(field) in (None, ""):
                errors.append(f"{path}[{i}] id={pid}: missing/empty {field}")
    dups = {pid: idxs for pid, idxs in seen.items() if len(idxs) > 1}
    for pid, idxs in dups.items():
        errors.append(f"{path}: duplicate id={pid} at rows {idxs}")
    return errors


def main(paths: list[str]) -> int:
    all_errors: list[str] = []
    for path in paths:
        try:
            all_errors.extend(validate_file(path))
        except Exception as exc:
            all_errors.append(f"{path}: ERROR {exc}")
    if all_errors:
        print(json.dumps({"valid": False, "errors": all_errors}, indent=2))
        return 1
    print(json.dumps({"valid": True, "files": len(paths)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
