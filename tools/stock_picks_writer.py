#!/usr/bin/env python3
"""Restore the missing writer for `ejaguiar1_stocks.stock_picks`.

WHY THIS EXISTS
---------------
`stock_picks` is read by 11 PHP files, several of them served live:
`live-monitor/api/spike_scanner.php`, `live-monitor/api/pair_fingerprint.php`,
`investments/goldmines/antigravity/api/unified_predictions.php`, and
`findstocks/portfolio2/api/stock_intel.php`. The dead-data checker reported it
STALE at 5,047 hours against a 72h threshold on 2026-11-23.

There is no writer for it anywhere — not in this tree, and not in the Windows
source tree (`findstr /s /i /c:"INSERT INTO stock_picks"` over
`E:\\findtorontoevents_antigravity.ca\\*.php` returns nothing). The equity pick
pipeline did not break; it MOVED. It now runs in the sibling repo
`eltonaguiar/STOCKSUNIFY2`, is pulled daily by `tools/sync_stocksunify2.py`
(workflow `stocksunify2-pull.yml`, 13:05 UTC) and lands in
`audit_dashboard/data/stocksunify2_active_picks.json`, which feeds /audit.
The legacy table was simply left behind.

This adapter closes that gap: canonical pick -> `stock_picks` row.

IDEMPOTENCY
-----------
`stock_picks` indexes `pick_hash` (`idx_hash`) but the column is NOT UNIQUE, so
`INSERT ... ON DUPLICATE KEY UPDATE` cannot be used. We SELECT the hashes
already present for the batch and skip them, which makes re-running a no-op.

SAFETY
------
Dry-run is the default. Nothing is written without an explicit --commit.
Paper only. Zero capital. Not investment advice.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "audit_dashboard" / "data" / "stocksunify2_active_picks.json"

# stock_picks column order for INSERT. Kept as a module constant so the SQL and
# the row dict can never drift apart.
COLUMNS = (
    "ticker",
    "algorithm_id",
    "algorithm_name",
    "pick_date",
    "pick_time",
    "entry_price",
    "simulated_entry_price",
    "score",
    "rating",
    "risk_level",
    "timeframe",
    "stop_loss_price",
    "pick_hash",
    "indicators_json",
    "verified",
)

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


# --------------------------------------------------------------------------
# pure mapping layer (no DB, fully unit-testable)
# --------------------------------------------------------------------------
def _dec(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def parse_ts(value):
    """Parse an ISO timestamp into a naive UTC datetime, or None."""
    if not value:
        return None
    try:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def derive_hash(symbol: str, strategy: str, generated_at: str) -> str:
    """Deterministic content hash used when the source omits pick_hash.

    Same (symbol, strategy, generated_at) always yields the same hash, so
    re-runs stay idempotent instead of piling up duplicates.
    """
    raw = f"{symbol}|{strategy}|{generated_at}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def to_row(pick: dict):
    """Map one canonical pick to a `stock_picks` row, or None if unusable."""
    symbol = (pick.get("symbol") or "").strip().upper()
    if not symbol:
        return None

    strategy = (pick.get("strategy") or pick.get("source_system") or "unknown")
    strategy = str(strategy).strip()[:100] or "unknown"

    generated_at = pick.get("generated_at")
    dt = parse_ts(generated_at)
    if dt is None:
        return None

    pick_hash = (pick.get("pick_hash") or "").strip().lower()
    if not _HASH_RE.match(pick_hash):
        pick_hash = derive_hash(symbol, strategy, str(generated_at))

    entry = _dec(pick.get("entry_price"))
    simulated = _dec(pick.get("simulated_entry_price")) or entry

    risk = (pick.get("risk") or "Medium")
    risk = str(risk).strip()[:20] or "Medium"

    return {
        "ticker": symbol[:10],
        "algorithm_id": 0,
        "algorithm_name": strategy,
        "pick_date": dt.date().isoformat(),
        "pick_time": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "entry_price": entry,
        "simulated_entry_price": simulated,
        "score": int(round(_dec(pick.get("score")))),
        "rating": str(pick.get("rating") or "").strip()[:20],
        "risk_level": risk,
        "timeframe": str(pick.get("timeframe") or "").strip()[:20],
        "stop_loss_price": _dec(pick.get("stop_loss")),
        "pick_hash": pick_hash,
        "indicators_json": json.dumps(pick.get("indicators") or {}, sort_keys=True),
        "verified": 0,
    }


def plan_inserts(picks, existing_hashes, limit=None):
    """Return (rows_to_insert, skipped) given picks and hashes already stored."""
    rows = []
    skipped = []
    seen = set(existing_hashes or ())
    for pick in picks:
        row = to_row(pick)
        if row is None:
            skipped.append(("invalid", pick))
            continue
        if row["pick_hash"] in seen:
            skipped.append(("duplicate", row))
            continue
        seen.add(row["pick_hash"])
        rows.append(row)
    if limit is not None and limit >= 0:
        rows = rows[:limit]
    return rows, skipped


# --------------------------------------------------------------------------
# DB layer (thin, injected cursor so it can be tested without MySQL)
# --------------------------------------------------------------------------
def load_picks(path: Path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    picks = payload.get("active_picks")
    if picks is None:
        picks = payload.get("picks") or []
    return picks


def fetch_existing_hashes(cursor, hashes):
    """SELECT which of `hashes` already exist in stock_picks."""
    hashes = [h for h in hashes if h]
    if not hashes:
        return set()
    placeholders = ",".join(["%s"] * len(hashes))
    cursor.execute(
        f"SELECT pick_hash FROM stock_picks WHERE pick_hash IN ({placeholders})",
        tuple(hashes),
    )
    found = cursor.fetchall() or ()
    out = set()
    for item in found:
        if isinstance(item, dict):
            value = item.get("pick_hash")
        elif isinstance(item, (tuple, list)):
            value = item[0]
        else:
            value = item
        if value:
            out.add(str(value).lower())
    return out


def insert_rows(cursor, rows):
    """INSERT the given rows. Returns number of rows sent."""
    if not rows:
        return 0
    columns = ", ".join(COLUMNS)
    placeholders = ", ".join(["%s"] * len(COLUMNS))
    sql = f"INSERT INTO stock_picks ({columns}) VALUES ({placeholders})"
    sent = 0
    for row in rows:
        cursor.execute(sql, tuple(row[c] for c in COLUMNS))
        sent += 1
    return sent


def connect():
    """Build a pymysql connection from the house credential resolver."""
    from tools.db_env import get_stocks_creds  # imported late so tests need no driver

    import pymysql

    return pymysql.connect(**get_stocks_creds())


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--input", default=str(DEFAULT_INPUT),
                    help="canonical picks JSON (default: stocksunify2_active_picks.json)")
    ap.add_argument("--commit", action="store_true",
                    help="actually write to MySQL (default is dry-run)")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap the number of rows inserted this run")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    def say(msg):
        if not args.quiet:
            print(msg)

    path = Path(args.input)
    if not path.exists():
        print(f"[stock_picks_writer] input not found: {path}", file=sys.stderr)
        return 2

    picks = load_picks(path)
    say(f"[stock_picks_writer] source: {path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path}")
    say(f"[stock_picks_writer] candidate picks: {len(picks)}")

    if not args.commit:
        rows, skipped = plan_inserts(picks, set(), limit=args.limit)
        say(f"[stock_picks_writer] DRY RUN -- would insert {len(rows)} row(s), "
            f"skipped {len(skipped)}")
        for row in rows:
            say(f"  + {row['ticker']:<6} {row['algorithm_name'][:38]:<38} "
                f"{row['pick_date']} score={row['score']:<4} hash={row['pick_hash'][:12]}")
        if skipped:
            for reason, item in skipped:
                label = item.get("symbol") if isinstance(item, dict) else item
                say(f"  - skipped ({reason}): {label}")
        say("[stock_picks_writer] nothing written (pass --commit to write)")
        return 0

    try:
        conn = connect()
    except Exception as exc:
        print(f"[stock_picks_writer] cannot connect: {exc}", file=sys.stderr)
        return 3

    try:
        cursor = conn.cursor()
        candidate_rows, skipped = plan_inserts(picks, set())
        existing = fetch_existing_hashes(cursor, [r["pick_hash"] for r in candidate_rows])
        rows, _ = plan_inserts(picks, existing, limit=args.limit)
        sent = insert_rows(cursor, rows)
        conn.commit()
        say(f"[stock_picks_writer] inserted {sent} row(s); "
            f"{len(existing)} already present; {len(skipped)} skipped")
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[stock_picks_writer] write failed, rolled back: {exc}", file=sys.stderr)
        return 4
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
