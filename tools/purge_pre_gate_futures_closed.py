#!/usr/bin/env python3
"""Remove pre-gate FUTURES closed picks (dashboard score 30–36) from persisted history.

Default: dry-run only. Use --write to rewrite ``alpha_engine/data/closed_picks.json``.
A timestamped ``.bak`` is written before --write.

Headline/dashboard exclusion is handled in ``audit_trail.dashboard_generator``; this tool
optionaly shrinks the canonical closed ledger so backtests and validators do not re-ingest
the toxic cohort.

Does not remove scanner futures outside 30–36 unless you pass --also-scanner-lt55 (destructive).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_CLOSED = REPO / "alpha_engine" / "data" / "closed_picks.json"

_SCORE_LO = 30.0
_SCORE_HI = 36.0


def _is_futures(p: dict) -> bool:
    ac = str(p.get("asset_class") or p.get("category") or "").upper()
    return ac in ("FUTURES", "FUTURE")


def _score(p: dict) -> float:
    try:
        return float(p.get("score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _scanner_sourced(p: dict) -> bool:
    src = str(p.get("source_system") or "").lower()
    strat = str(p.get("strategy") or "").lower()
    return (
        "scanner" in src
        or "scanner" in strat
        or "multi_asset_scanner" in src
    )


def should_purge_row(p: dict, *, also_scanner_lt55: bool) -> bool:
    if not _is_futures(p):
        return False
    sc = _score(p)
    if _SCORE_LO <= sc <= _SCORE_HI:
        return True
    if also_scanner_lt55 and _scanner_sourced(p) and sc < 55:
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", default=str(DEFAULT_CLOSED), help="closed_picks.json path")
    ap.add_argument(
        "--write",
        action="store_true",
        help="Apply removal (default: print counts only)",
    )
    ap.add_argument(
        "--also-scanner-lt55",
        action="store_true",
        help="Also drop scanner-sourced futures with score <55 (matches dashboard legacy rule)",
    )
    args = ap.parse_args()
    path = Path(args.path)
    if not path.is_file():
        print("missing", path, file=sys.stderr)
        return 1

    raw = path.read_text(encoding="utf-8", errors="replace")
    rows = json.loads(raw)
    if not isinstance(rows, list):
        print("expected list JSON", file=sys.stderr)
        return 1

    purge_idx = [
        i
        for i, p in enumerate(rows)
        if isinstance(p, dict)
        and should_purge_row(p, also_scanner_lt55=args.also_scanner_lt55)
    ]
    kept = [p for i, p in enumerate(rows) if i not in set(purge_idx)]

    print(
        "path=%s total=%d purge=%d keep=%d write=%s also_scanner_lt55=%s"
        % (
            path,
            len(rows),
            len(purge_idx),
            len(kept),
            args.write,
            args.also_scanner_lt55,
        )
    )
    if args.write and purge_idx:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = path.with_suffix(path.suffix + ".bak." + ts)
        shutil.copy2(path, bak)
        print("backup", bak)
        path.write_text(
            json.dumps(kept, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
