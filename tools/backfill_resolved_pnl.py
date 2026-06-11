#!/usr/bin/env python3
"""Backfill pnl_pct on resolved trading_picks (NULL or zero-with-exit).

Addresses updates/2026-06-05-zero-pnl-safeguard-stale-pick-resolver-fixes.md and
forward-tracking gaps (inverse_ml ADA: closed_at set, pnl_pct NULL).

Safety: --apply archives affected rows to ejaguiar1_backups first (archive_table_slice).

Usage:
  python3 tools/backfill_resolved_pnl.py --dry-run
  python3 tools/backfill_resolved_pnl.py --apply --limit 500
  python3 tools/backfill_resolved_pnl.py --apply --strategy inverse_ml_enhanced_ADAUSDT_15m_D
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _compute_pnl(entry: float, exit_price: float, direction: str) -> float:
    """Mirror universal_pick_resolver zero-safeguard (2026-06-05)."""
    if not entry or entry <= 0:
        return 0.0
    mult = 1.0 if direction == "LONG" else -1.0
    pnl = round(((exit_price - entry) / entry) * 100 * mult, 2)
    if pnl == 0.0:
        fallback = ((exit_price - entry) / entry) * 100 * mult
        if fallback != 0.0:
            return fallback
    return pnl

TERMINAL = (
    "WON", "LOST", "WIN", "LOSS", "TP_HIT", "SL_HIT", "TIME_EXIT", "EXPIRED", "TIME_EXIT_MAX_HOLD"
)
WHERE_BASE = (
    "closed_at IS NOT NULL AND entry_price > 0 AND status IN ("
    + ",".join(f"'{s}'" for s in TERMINAL)
    + ") AND (pnl_pct IS NULL OR (ABS(COALESCE(pnl_pct,0)) < 0.0001 AND exit_price IS NOT NULL "
    "AND ABS(entry_price - exit_price) > 0.0001))"
)


def _connect():
    import pymysql
    from tools.db_env import get_stocks_creds

    return pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)


def _direction_norm(direction: str | None) -> str:
    d = (direction or "LONG").upper()
    return "SHORT" if d in ("SELL", "SHORT") else "LONG"


def _candidate_where(strategy: str | None) -> str:
    where = WHERE_BASE
    if strategy:
        safe = strategy.replace("'", "''")
        where += f" AND strategy = '{safe}'"
    return where


def _fetch_candidates(conn, *, strategy: str | None, limit: int) -> list[dict]:
    where = _candidate_where(strategy)
    sql = f"""
        SELECT id, symbol, direction, entry_price, exit_price, pnl_pct, status, strategy
        FROM trading_picks WHERE {where} ORDER BY closed_at DESC
    """
    if limit > 0:
        sql += f" LIMIT {int(limit)}"
    with conn.cursor() as cur:
        cur.execute(sql)
        return list(cur.fetchall())


def _recompute(row: dict) -> float | None:
    """Recompute pnl_pct, returning None if the result would violate
    the chk_pnl_sign_coherence constraint (status says WON but pnl < 0, or
    status says LOST but pnl > 0)."""
    entry = float(row.get("entry_price") or 0)
    exit_p = row.get("exit_price")
    if exit_p is None:
        return None
    exit_p = float(exit_p)
    if exit_p <= 0:
        return None
    # 2026-06-11 price-sanity guard: the 06-10 run resurrected 87 corrupt-exit
    # rows (wrong-symbol prices, e.g. AUDUSD=X exit 663 on a 0.70 entry ->
    # +93,965% "win"; TRX exits pinned at a stale 0.067). Sign-coherence alone
    # cannot catch these (a corrupt LOSS is still sign-coherent). Skip any row
    # whose exit/entry ratio is physically implausible for its class — those
    # rows need exit-price repair, not pnl backfill.
    if entry > 0:
        ratio = exit_p / entry
        cat = (row.get("category") or "").lower()
        if cat in ("crypto", "memecoin", "meme"):
            if ratio > 4 or ratio < 0.25:
                return None
        elif ratio > 1.8 or ratio < 0.45:
            return None
    d = _direction_norm(row.get("direction"))
    new_pnl = _compute_pnl(entry, exit_p, d)

    # chk_pnl_sign_coherence: WON/TP_HIT/closed_win must have pnl >= -0.01;
    # LOST/SL_HIT/closed_loss must have pnl <= 0.01.  Skip rows where the
    # recomputed pnl would violate this — the status label is the ground truth
    # and we should not overwrite it.
    status = (row.get("status") or "").upper()
    if status in ("WON", "TP_HIT", "CLOSED_WIN") and new_pnl < -0.01:
        return None
    if status in ("LOST", "SL_HIT", "CLOSED_LOSS") and new_pnl > 0.01:
        return None

    return new_pnl


def _json_archive(where: str, archive_name: str, n: int, mysql_err: Exception) -> None:
    """Fallback when cross-DB CREATE is denied: JSON slice under reports/ (operator audit)."""
    path = ROOT / "reports" / "db_archive_slices" / f"{archive_name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM trading_picks WHERE {where}")
            rows = cur.fetchall()
    finally:
        conn.close()
    payload = {
        "archive_name": archive_name,
        "row_count": n,
        "mysql_fallback_reason": str(mysql_err),
        "where": where,
        "rows": rows,
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"[backfill] WARN: MySQL cross-DB archive failed ({mysql_err})")
    print(f"[backfill] JSON slice backup: {path} ({len(rows)} rows)")


def _archive_before_apply(where: str) -> None:
    """Archive affected rows to ejaguiar1_backups (CREATE AS SELECT — avoids CHECK dup names)."""
    import pymysql
    from datetime import datetime, timezone
    from tools.db_env import get_stocks_creds

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_name = f"trading_picks_pre_backfill_resolved_pnl_{ts}"
    creds = get_stocks_creds()
    stocks_db = creds["database"]
    src = pymysql.connect(**creds)
    backup_db = "ejaguiar1_backups"
    n = 0
    try:
        with src.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM `{stocks_db}`.`trading_picks` WHERE {where}")
            n = int(cur.fetchone()[0])
        if n == 0:
            raise RuntimeError("Refusing apply: zero rows to back up")
        if n > 500_000:
            raise RuntimeError(f"Refusing apply: {n} rows > 500k — narrow --strategy or --limit")
        with src.cursor() as cur:
            cur.execute(
                f"CREATE TABLE `{backup_db}`.`{archive_name}` AS SELECT * FROM `{stocks_db}`.`trading_picks` WHERE {where}"
            )
            src.commit()
            print(f"[backfill] Archived {n} rows to {backup_db}.{archive_name}")
    except pymysql.err.OperationalError as e:
        _json_archive(where, archive_name, n, e)
    except RuntimeError:
        raise
    finally:
        src.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--strategy", default=None)
    ap.add_argument("--skip-backup", action="store_true")
    args = ap.parse_args()
    dry = not args.apply

    where = _candidate_where(args.strategy)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS n FROM trading_picks WHERE {where}")
            total = int(cur.fetchone()["n"])
        rows = _fetch_candidates(conn, strategy=args.strategy, limit=args.limit or 0)
    finally:
        conn.close()

    print(f"candidates: {total} (fetched {len(rows)})")
    updates: list[tuple[float, str]] = []
    skip = 0
    for r in rows:
        new_pnl = _recompute(r)
        if new_pnl is None:
            skip += 1
            continue
        old = r.get("pnl_pct")
        if old is not None and abs(float(old) - new_pnl) < 0.0001:
            skip += 1
            continue
        updates.append((new_pnl, str(r["id"])))
        if len(updates) <= 5:
            print(f"  plan id={r['id']} {r.get('symbol')} {r.get('strategy')} → {new_pnl:.4f}%")

    print(f"plan fix={len(updates)} skip={skip}")
    if dry:
        print("(dry-run)")
        return 0

    if not args.skip_backup:
        _archive_before_apply(where)

    conn = _connect()
    fixed = 0
    try:
        with conn.cursor() as cur:
            for pnl, row_id in updates:
                cur.execute(
                    "UPDATE trading_picks SET pnl_pct=%s WHERE id=%s "
                    "AND (pnl_pct IS NULL OR ABS(COALESCE(pnl_pct,0)) < 0.0001) "
                    # chk_pnl_sign_coherence defense-in-depth: guard against
                    # any existing pnl_pct that already violates the constraint
                    # (shouldn't happen after _recompute, but belt-and-suspenders).
                    "AND NOT (status IN ('WON','TP_HIT','closed_win') AND pnl_pct IS NOT NULL AND pnl_pct < -0.01) "
                    "AND NOT (status IN ('LOST','SL_HIT','closed_loss') AND pnl_pct IS NOT NULL AND pnl_pct > 0.01)",
                    (pnl, row_id),
                )
                fixed += cur.rowcount
        conn.commit()
    finally:
        conn.close()
    print(f"APPLIED: {fixed} rows updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
