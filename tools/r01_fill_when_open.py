#!/usr/bin/env python3
"""Wait for the equity round open, then run the R01 fill exactly once.

Why a waiter instead of a cron entry: the fill is only honest if it runs after
14:30Z, and the tool itself refuses any earlier. This simply removes the human
from the timing loop. It is idempotent -- a filled artefact blocks a re-fill.

    python3 tools/r01_fill_when_open.py                 # today's open, 14:32Z guard
    python3 tools/r01_fill_when_open.py --target 2026-11-24T14:32:00Z

Paper only. Zero capital. Not investment advice.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "r01_round_open_fill_2026-11-23.json"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def default_target() -> datetime:
    """Two minutes past the 14:30Z open, so the first bar exists and is closed."""
    now = utcnow()
    t = now.replace(hour=14, minute=32, second=0, microsecond=0)
    return t if t > now else t + timedelta(days=1)


def already_filled() -> bool:
    try:
        d = json.loads(OUT.read_text())
    except Exception:
        return False
    filled = d.get("filled") or d.get("positions") or []
    return bool(filled) and d.get("status") not in (None, "NOT_OPEN_YET")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", help="ISO-8601 UTC time to fire, default today's 14:32Z")
    ap.add_argument("--round-start", default=None, help="round start passed to the fill tool")
    a = ap.parse_args()
    target = datetime.fromisoformat(a.target.replace("Z", "+00:00")) if a.target else default_target()
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)

    wait = (target - utcnow()).total_seconds()
    print(f"[waiter] {utcnow().isoformat()} target {target.isoformat()} wait {wait/60:.1f} min", flush=True)
    while wait > 0:
        time.sleep(min(wait, 300))
        wait = (target - utcnow()).total_seconds()
        print(f"[waiter] {utcnow().isoformat()} {wait/60:.1f} min to go", flush=True)

    if already_filled():
        print("[waiter] artefact already holds a fill; refusing to overwrite", flush=True)
        return 0

    cmd = [sys.executable, str(ROOT / "tools" / "r01_round_open_fill.py"),
           "--picks", "/tmp/r01_field.json", "--out", str(OUT)]
    start = a.round_start or target.replace(hour=14, minute=30, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    cmd += ["--round-start", start]
    print(f"[waiter] running {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=str(ROOT))
    print(f"[waiter] fill exited {r.returncode} at {utcnow().isoformat()}", flush=True)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
