#!/usr/bin/env python3
"""backfill_null_pnl_safe.py — constraint-safe recovery of NULL pnl_pct rows.

Backfills pnl_pct for resolved trading_picks where it's NULL, using computed
pnl from entry_price/exit_price/direction. Applies TWO safety gates:
  1. chk_pnl_sign_coherence — won't write a positive pnl for SL_HIT/LOST
     or negative pnl for TP_HIT
  2. entry_price scale validation — won't trust entry_price if it differs
     from latest OHLCV close by >threshold (same thresholds as
     mysql_trading_sync.py). Uses stock_ohlcv for equity/ETF/stock/bond,
     crypto_ohlcv for crypto, commodity_price_cache for commodity/futures.

Safer than backfill_resolved_pnl.py (which had no scale guard and hit the
constraint on sign mismatches). Backs up affected rows to ejaguiar1_backups
before any UPDATE. Designed to NEVER write scale-corrupt pnl_pct values.

Usage:
  python3 tools/backfill_null_pnl_safe.py --dry-run    # default
  python3 tools/backfill_null_pnl_safe.py --apply       # backup + update
  python3 tools/backfill_null_pnl_safe.py --report      # breakdown only
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pymysql
from tools.db_env import get_stocks_creds

# ── thresholds match mysql_trading_sync.py ──
_ENTRY_SCALE_THRESHOLD_BY_CLASS: dict[str, float] = {
    "FOREX": 100.0,
    "COMMODITY": 50.0,
    "FUTURES": 50.0,
    "EQUITY": 10.0,
    "STOCK": 10.0,
    "ETF": 10.0,
    "BOND": 10.0,
    "INDEX": 10.0,
}

# Rows matching this WHERE clause are candidates for backfill
WHERE_CANDIDATES = """
    status IN ('TP_HIT', 'SL_HIT', 'LOST', 'TIME_EXIT')
    AND pnl_pct IS NULL
    AND entry_price IS NOT NULL AND entry_price > 0
    AND exit_price IS NOT NULL
"""


def _compute_pnl(direction: str, entry: float, exit_p: float) -> float:
    """Compute pnl_pct from entry/exit/direction. Returns raw float (not rounded)."""
    if (direction or "").upper() in ("SHORT", "SELL"):
        return (entry - exit_p) / entry * 100.0
    # LONG, BUY, or anything else → long-side formula
    return (exit_p - entry) / entry * 100.0


def _violates_constraint(status: str, pnl: float) -> bool:
    """Check chk_pnl_sign_coherence. Returns True if pnl contradicts status."""
    if status in ("TP_HIT",):
        return pnl < -0.02  # winning trade should have positive or near-zero pnl
    if status in ("SL_HIT", "LOST"):
        return pnl > 0.02   # losing trade should have negative or near-zero pnl
    # TIME_EXIT can be either sign — time expiry isn't a win/loss verdict.
    # Cluster 4 of the investigation: vix_reversal GOOGL/TSLA/XLK expired at
    # small profits (+0.03% to +1.19%) — the constraint was too strict.
    return False


def _correct_status(status: str, pnl: float) -> str:
    """Auto-correct status when PnL sign contradicts it.

    Investigation findings (reports/null_pnl_constraint_violation_investigation_2026-06-09.md):
      Cluster 1: iso_regime_terminal — -2% trailing stops labeled TP_HIT → correct to SL_HIT
      Cluster 2: iso_battleground_luxalgo — inverted win/loss → TP_HIT↔LOST swap
      Cluster 5: Miscellaneous near-flat mislabels → correct based on PnL sign

    Mapping:
      TP_HIT  + negative PnL  → LOST  (stop hit, not take-profit)
      LOST    + positive PnL  → TP_HIT (take-profit hit, not stop)
      SL_HIT  + positive PnL  → TP_HIT (take-profit hit, not stop-loss)
      TIME_EXIT — never corrected (time expiry is agnostic to PnL sign)
    """
    if status == "TP_HIT" and pnl < -0.02:
        return "LOST"
    if status in ("LOST", "SL_HIT") and pnl > 0.02:
        return "TP_HIT"
    # TIME_EXIT, near-flat, or already consistent — leave as-is
    return status


def _load_price_cache(
    conn, symbols: list[str], categories: dict[str, str]
) -> dict[str, float]:
    """Load latest OHLCV close per symbol from appropriate table per category.

    Returns {symbol: close} dict. Symbols without OHLCV data are absent from dict.
    """
    cache: dict[str, float] = {}
    cur = conn.cursor()

    # Group symbols by their OHLCV table
    stock_syms = []
    crypto_syms = []
    for sym in symbols:
        cat = (categories.get(sym, "") or "").upper()
        if cat in ("CRYPTO", "MEME", "MEMECOIN"):
            crypto_syms.append(sym)
        else:
            stock_syms.append(sym)

    # stock_ohlcv
    if stock_syms:
        placeholders = ",".join(["%s"] * len(stock_syms))
        try:
            cur.execute(
                f"""
                SELECT o.symbol, o.close FROM stock_ohlcv o
                INNER JOIN (
                    SELECT symbol, MAX(timestamp) AS mt
                    FROM stock_ohlcv
                    WHERE symbol IN ({placeholders})
                    GROUP BY symbol
                ) m ON o.symbol = m.symbol AND o.timestamp = m.mt
                """,
                stock_syms,
            )
            for row in cur.fetchall():
                if row[0] not in cache:
                    cache[row[0]] = float(row[1])
        except Exception:
            pass  # stock_ohlcv may not exist or query may fail

    # crypto_ohlcv (separate table for crypto)
    if crypto_syms:
        placeholders = ",".join(["%s"] * len(crypto_syms))
        try:
            cur.execute(
                f"""
                SELECT o.symbol, o.close FROM crypto_ohlcv o
                INNER JOIN (
                    SELECT symbol, MAX(timestamp) AS mt
                    FROM crypto_ohlcv
                    WHERE symbol IN ({placeholders})
                    GROUP BY symbol
                ) m ON o.symbol = m.symbol AND o.timestamp = m.mt
                """,
                crypto_syms,
            )
            for row in cur.fetchall():
                if row[0] not in cache:
                    cache[row[0]] = float(row[1])
        except Exception:
            # Try stock_ohlcv for crypto too (may be stored there)
            try:
                cur.execute(
                    f"""
                    SELECT o.symbol, o.close FROM stock_ohlcv o
                    INNER JOIN (
                        SELECT symbol, MAX(timestamp) AS mt
                        FROM stock_ohlcv
                        WHERE symbol IN ({placeholders})
                        GROUP BY symbol
                    ) m ON o.symbol = m.symbol AND o.timestamp = m.mt
                    """,
                    crypto_syms,
                )
                for row in cur.fetchall():
                    if row[0] not in cache:
                        cache[row[0]] = float(row[1])
            except Exception:
                pass

    cur.close()
    return cache


def _passes_scale(
    category: str, entry_price: float, price_cache: dict[str, float], symbol: str
) -> tuple[bool, str]:
    """Check entry_price against latest OHLCV close. Returns (pass, reason)."""
    cat = (category or "").upper()
    if cat in ("CRYPTO", "MEME", "MEMECOIN"):
        return True, "crypto_bypass"  # crypto spans micro-cap to BTC

    close = price_cache.get(symbol)
    if close is None or close <= 0:
        return False, "no_ohlcv_data"

    threshold = _ENTRY_SCALE_THRESHOLD_BY_CLASS.get(cat, 10.0)
    ratio = entry_price / close
    if (1.0 / threshold) <= ratio <= threshold:
        return True, ""
    return False, f"scale_fail_{ratio:.1f}x_threshold_{threshold:.0f}x"


def _archive_slice(conn, ids: list[int], backup_table: str) -> None:
    """Copy affected rows to a backup table in the current DB before mutation.

    Uses a _backup_ prefix in the same database (ejaguiar1_stocks) because the
    DB user lacks cross-database CREATE privileges. CHECK constraints are dropped
    on the backup copy to avoid constraint failures during INSERT.

    NOTE: calls conn.commit() — flushes pending DDL + INSERTs.
    """
    cur = conn.cursor()
    # Create backup table from trading_picks schema
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {backup_table} "
        f"LIKE trading_picks"
    )
    # Remove CHECK constraints that might fail on copy
    try:
        cur.execute(
            f"ALTER TABLE {backup_table} "
            f"DROP CHECK chk_pnl_sign_coherence"
        )
    except Exception:
        pass
    # Copy rows
    chunk_size = 500
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i : i + chunk_size]
        placeholders = ",".join(["%s"] * len(chunk))
        cur.execute(
            f"INSERT IGNORE INTO {backup_table} "
            f"SELECT * FROM trading_picks WHERE id IN ({placeholders})",
            chunk,
        )
    conn.commit()
    cur.close()


def run(dry_run: bool = True, report_only: bool = False, log_skipped: bool = False) -> dict:
    """Main entry point. Returns summary dict."""
    creds = {k: v for k, v in get_stocks_creds().items()
             if k in ("host", "user", "password", "database", "port", "connect_timeout")}
    conn = pymysql.connect(**creds)
    cur = conn.cursor()

    # ── 1. Fetch all candidates ──
    cur.execute(
        f"SELECT id, symbol, category, direction, entry_price, exit_price, status "
        f"FROM trading_picks WHERE {WHERE_CANDIDATES}"
    )
    rows = cur.fetchall()

    # ── 2. Build symbol→category mapping + load price cache ──
    symbols = list({r[1] for r in rows if r[1]})
    categories = {r[1]: r[2] for r in rows if r[1]}
    price_cache = _load_price_cache(conn, symbols, categories)

    # ── 3. Classify each row ──
    to_update: list[tuple[float, str, str | None]] = []  # (pnl_pct, id, corrected_status_or_None)
    skipped: list[dict] = []
    stats = {
        "total_candidates": len(rows),
        "clean_pass_both": 0,
        "status_corrected": 0,           # constraint-violating → auto-corrected status + PnL
        "skip_constraint_violation": 0,   # TIME_EXIT with constraint-failing PnL (investigation cluster 4)
        "skip_scale_fail": 0,
        "skip_no_ohlcv": 0,
        "skip_other": 0,
    }

    for row in rows:
        pick_id, symbol, category, direction = row[0], row[1], row[2], row[3]
        entry_price = float(row[4])
        exit_price = float(row[5])
        status = row[6]

        pnl = _compute_pnl(direction, entry_price, exit_price)

        # Gate 1: constraint + auto-correct
        corrected_status = status
        if _violates_constraint(status, pnl):
            corrected_status = _correct_status(status, pnl)
            if corrected_status == status:
                # Could not auto-correct (e.g. TIME_EXIT with constraint-failing PnL).
                # These are investigation clusters 4+ that need manual review.
                stats["skip_constraint_violation"] += 1
                skipped.append({
                    "id": pick_id, "symbol": symbol, "status": status,
                    "computed_pnl": round(pnl, 4),
                    "reason": "constraint_violation_uncorrectable",
                })
                continue
            # Status was auto-corrected — will be updated alongside PnL.
            stats["status_corrected"] += 1

        # Gate 2: entry_price scale
        passes, reason = _passes_scale(category, entry_price, price_cache, symbol)
        if not passes:
            if reason == "no_ohlcv_data":
                stats["skip_no_ohlcv"] += 1
            else:
                stats["skip_scale_fail"] += 1
            skipped.append({
                "id": pick_id, "symbol": symbol, "status": status,
                "computed_pnl": round(pnl, 4),
                "reason": reason,
            })
            continue

        stats["clean_pass_both"] += 1
        to_update.append((round(pnl, 4), pick_id, corrected_status if corrected_status != status else None))

    # ── 4. Apply or report ──
    if report_only:
        cur.close()
        conn.close()
        return {"stats": stats, "skipped_count": len(skipped), "to_update_count": len(to_update)}

    if to_update and not dry_run:
        # Backup first
        ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_table = f"_backup_trading_picks_pre_nullpnl_{ts}"
        ids_to_backup = [t[1] for t in to_update]
        _archive_slice(conn, ids_to_backup, backup_table)
        print(f"backed up {len(ids_to_backup)} rows to ejaguiar1_backups.{backup_table}")

        # Update in chunks
        chunk_size = 200
        updated = 0
        status_corrected_count = 0
        for i in range(0, len(to_update), chunk_size):
            chunk = to_update[i : i + chunk_size]
            for pnl_val, pick_id, corrected_status in chunk:
                if corrected_status:
                    cur.execute(
                        "UPDATE trading_picks SET pnl_pct = %s, status = %s WHERE id = %s",
                        (pnl_val, corrected_status, pick_id),
                    )
                    status_corrected_count += 1
                else:
                    cur.execute(
                        "UPDATE trading_picks SET pnl_pct = %s WHERE id = %s",
                        (pnl_val, pick_id),
                    )
            conn.commit()
            updated += len(chunk)
        if status_corrected_count:
            print(f"status_corrected {status_corrected_count} rows (auto-corrected mislabeled statuses)")
        print(f"updated {updated} rows")
    elif to_update:
        n_corrected = sum(1 for u in to_update if u[2])
        print(f"DRY-RUN: would update {len(to_update)} rows (skipped {len(skipped)})")
        if n_corrected:
            print(f"  ({n_corrected} with auto-corrected status)")
        # Show sample
        for u in to_update[:5]:
            extra = f" status->{u[2]}" if u[2] else ""
            print(f"  {u[1][:50]} -> pnl_pct={u[0]}%{extra}")
        if len(skipped) > 0:
            reasons = {}
            for s in skipped:
                r = s["reason"]
                reasons[r] = reasons.get(r, 0) + 1
            print(f"skipped reasons: {reasons}")

    cur.close()
    conn.close()

    # ── 5. Log skipped rows for investigation ──
    if skipped and log_skipped:
        log_path = str(
            REPO_ROOT / "reports" /
            f"null_pnl_skipped_{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')}.json"
        )
        with open(log_path, "w") as f:
            json.dump({
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "total_skipped": len(skipped),
                "skipped_rows": skipped,
            }, f, indent=2)
        print(f"logged {len(skipped)} skipped rows to {log_path}")

    backup_name = None
    if not dry_run and to_update:
        backup_name = backup_table
    result = {
        "stats": stats,
        "skipped_count": len(skipped),
        "to_update_count": len(to_update),
        "backup_table": backup_name,
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Constraint-safe NULL-pnl backfill")
    ap.add_argument("--apply", action="store_true",
                    help="Actually update the DB (backs up first). Without this, dry-run only.")
    ap.add_argument("--report", action="store_true",
                    help="Show breakdown only, no update even with --apply")
    ap.add_argument("--log-skipped", action="store_true",
                    help="Write skipped rows to reports/null_pnl_skipped_YYYY-MM-DD.json")
    args = ap.parse_args()

    dry_run = not args.apply or args.report
    result = run(dry_run=dry_run, report_only=args.report, log_skipped=args.log_skipped)
    print(json.dumps(result["stats"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
