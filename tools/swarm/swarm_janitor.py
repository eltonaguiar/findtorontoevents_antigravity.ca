#!/usr/bin/env python3
"""Daily janitor for swarm session DB.

Marks `active` sessions older than `--hours` as `expired` (default 72h) and
optionally vacuums the SQLite file to reclaim disk. Suitable for a cron or
GHA workflow.

Usage:

    python tools/swarm/swarm_janitor.py [--hours 72] [--vacuum] [--db <path>]

Output is a single human-readable line:

    Expired N sessions older than 72h. Reclaimed 12 KB.

Exit codes:
    0 — success (zero or more sessions expired).
    1 — IO/sqlite error reaching the DB.

Schedule via cron / GHA when DB grows past ~10 MB. See
`tools/swarm/SPEC.md` (Session Manager section).
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from session_manager import DB_PATH, expire_older_than  # noqa: E402

# Tracked log file (committable). The DB itself is gitignored under
# `swarm_runs/*` so we record janitor activity here so GHA workflows have
# something to commit. See `.gitignore` exception `!swarm_runs/_janitor.log`.
LOG_PATH = DB_PATH.parent / "_janitor.log"


def _human_bytes(n: int) -> str:
    if n < 0:
        n = 0
    units = ("B", "KB", "MB", "GB")
    f = float(n)
    for u in units:
        if f < 1024.0 or u == units[-1]:
            if u == "B":
                return f"{int(f)} {u}"
            return f"{f:.1f} {u}"
        f /= 1024.0
    return f"{int(n)} B"


def _db_size(p: Path) -> int:
    """Sum size of the main DB file plus -wal / -shm sidecars."""
    total = 0
    for suffix in ("", "-wal", "-shm"):
        candidate = p.with_name(p.name + suffix) if suffix else p
        try:
            total += candidate.stat().st_size
        except FileNotFoundError:
            continue
    return total


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hours", type=float, default=72.0,
                    help="Mark active sessions older than this many hours as "
                         "expired (default: 72).")
    ap.add_argument("--vacuum", action="store_true",
                    help="Run sqlite VACUUM after expiry to reclaim disk.")
    ap.add_argument("--db", default=None,
                    help="Override DB path (default: swarm_runs/_sessions.db).")
    args = ap.parse_args(argv)

    db_path = Path(args.db) if args.db else DB_PATH

    size_before = _db_size(db_path)

    try:
        n_expired = expire_older_than(hours=args.hours, db_path=db_path)
    except sqlite3.DatabaseError as e:
        print(f"[swarm_janitor] sqlite error: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"[swarm_janitor] IO error: {e}", file=sys.stderr)
        return 1

    if args.vacuum:
        try:
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("VACUUM")
                conn.commit()
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            print(f"[swarm_janitor] vacuum failed (non-fatal): {e}", file=sys.stderr)

    size_after = _db_size(db_path)
    reclaimed = max(0, size_before - size_after)

    msg = (
        f"Expired {n_expired} session(s) older than {args.hours:g}h. "
        f"Reclaimed {_human_bytes(reclaimed)}."
    )
    print(msg)

    # Append to the tracked log so GHA workflows have a committable artifact
    # (the DB stays gitignored).
    try:
        log_path = LOG_PATH if not args.db else (
            Path(args.db).parent / "_janitor.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{ts} hours={args.hours:g} expired={n_expired} "
                     f"reclaimed={_human_bytes(reclaimed)} "
                     f"vacuum={'yes' if args.vacuum else 'no'}\n")
    except OSError as e:
        print(f"[swarm_janitor] log write failed (non-fatal): {e}",
              file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
