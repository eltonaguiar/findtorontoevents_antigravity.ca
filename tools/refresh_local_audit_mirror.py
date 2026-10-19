#!/usr/bin/env python3
"""
Refresh the LOCAL audit_dashboard/data/*.json mirror from the live site.

WHY (2026-10-18, P1 "stop the local data rot"):
  - `audit_dashboard/data/dashboard_data.json` is intentionally gitignored
    (.gitignore:218) because it is ~24 MB and regenerated hourly in CI. Nothing
    ever regenerates it on a dev box, so the local copy silently rotted: the
    mirror here read `generated_at = 2026-06-02` — 4.5 months stale — while
    production served fresh numbers.
  - Local tooling (skill queries, one-off analyses, watchdog fallbacks) that
    reads the repo copy was therefore reasoning about June data and never
    noticed.
  - The remaining tracked sidecars are only as fresh as the last commit/worktree
    update, which for a long-lived branch can also be months old.

WHAT IT DOES:
  - Downloads the CORE list (the payloads that actually drive /audit headline
    stats) straight from https://findtorontoevents.ca/audit/data/.
  - `--all` refreshes every JSON currently present locally (live-404 files are
    skipped with a note; nothing is deleted).
  - Writes are atomic (tmp + rename) so a half-finished run can't leave a
    truncated 24 MB JSON for a local reader to trip over.
  - Refuses to shrink a file to nothing: a non-2xx / empty body never overwrites
    an existing local copy (fail-open on the file we already have).

USAGE:
  python3 tools/refresh_local_audit_mirror.py            # CORE payloads only
  python3 tools/refresh_local_audit_mirror.py --all      # every local *.json
  python3 tools/refresh_local_audit_mirror.py --dry-run
"""
from __future__ import annotations

import argparse
import gzip
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCAL_DIR = REPO / "audit_dashboard" / "data"
SITE = os.environ.get("AUDIT_LIVE_BASE", "https://findtorontoevents.ca")
HEADERS = {"User-Agent": "Mozilla/5.0 local-audit-mirror-refresh"}

# Payloads that drive the /audit headline core stats (summary WR/PF, per-class
# health, money-ready verdicts, funnel). Keep this list short and high-value;
# --all covers the long tail.
CORE = [
    "dashboard_data.json",
    "money_ready_verdict.json",
    "pick_funnel_today.json",
    "pick_funnel_90d.json",
    "strategy_perf_by_class.json",
    "audit_surface_truth.json",
    "verified_edge_status.json",
    "asset_class_freshness_report.json",
    "hourly_update_last_run.json",
]


def _fetch(name: str, timeout: int = 180) -> tuple[bool, str]:
    url = f"{SITE}/audit/data/{name}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    if status not in (200, 206):
        return False, f"HTTP {status}"
    if not body:
        return False, "empty body"
    if name.endswith(".json"):
        # Never clobber a local copy with a non-JSON error page.
        try:
            import json
            json.loads(body.decode("utf-8", "replace"))
        except Exception as e:
            return False, f"invalid JSON ({e})"
    tmp = LOCAL_DIR / f".{name}.tmp"
    tmp.write_bytes(body)
    os.replace(tmp, LOCAL_DIR / name)
    return True, f"{len(body):,} bytes"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="refresh every local *.json, not just CORE")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.all:
        names = sorted(p.name for p in LOCAL_DIR.glob("*.json"))
    else:
        names = [n for n in CORE if (LOCAL_DIR / n).exists() or n == CORE[0]]

    print(f"Mirroring {len(names)} file(s) from {SITE}/audit/data/ -> {LOCAL_DIR}")
    ok = skip = 0
    for n in names:
        local = LOCAL_DIR / n
        before = local.stat().st_mtime if local.exists() else 0
        age_h = (time.time() - before) / 3600 if before else float("inf")
        if args.dry_run:
            print(f"  would fetch {n:45s} (local age {age_h:8.1f}h)")
            continue
        good, msg = _fetch(n)
        if good:
            ok += 1
            print(f"  OK    {n:45s} {msg}   (was {age_h:.0f}h old)")
        else:
            skip += 1
            print(f"  SKIP  {n:45s} {msg}   (kept local copy)")
    print(f"\n{ok} refreshed, {skip} skipped/failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
