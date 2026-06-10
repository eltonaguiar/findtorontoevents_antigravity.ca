#!/usr/bin/env python3
"""quarantine_scale_corrupt_exits.py — quarantine rows with implausible exit_prices.

Follows the JUPUSDT/SHIBUSDT quarantine pattern:
  1. Find rows where exit_price differs from latest OHLCV close by >threshold
  2. Backup those rows to a _backup_ table
  3. NULL out exit_price and pnl_pct (the corrupt values)
  4. Log what was done

Also audits: for each quarantined row, reports whether the new exit_price
scale validation in mysql_trading_sync.py would have caught it at ingest.

Refs: reports/null_pnl_constraint_violation_investigation_2026-06-09.md Cluster 3

Usage:
  python3 tools/quarantine_scale_corrupt_exits.py --dry-run    # preview only
  python3 tools/quarantine_scale_corrupt_exits.py --apply       # backup + quarantine
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pymysql
from tools.db_env import get_stocks_creds

# ── Scale thresholds (mirrors mysql_trading_sync.py) ──
_EXIT_SCALE_THRESHOLD_BY_CLASS: dict[str, float] = {
    "FOREX": 100.0,
    "COMMODITY": 50.0,
    "FUTURES": 50.0,
    "EQUITY": 10.0,
    "ETF": 10.0,
    "BOND": 10.0,
    "STOCK": 10.0,
    "INDEX": 10.0,
}
_THRESHOLD_DEFAULT = 10.0

# Specific known scale-corrupt rows from the investigation.
# id_substring is used with LIKE matching.
KNOWN_CORRUPT: list[dict] = [
    {"id_sub": "feature_commodity_mom::NG=F", "symbol": "NG=F",
     "note": "exit=63095.76 vs real ~3.50 (~18,800x)"},
    {"id_sub": "iso_genome_ENAUSDT_608238764", "symbol": "RENDERUSDT",
     "note": "exit=1.94 vs real ~0.20 (~10x); id≠symbol (id says ENAUSDT)"},
    {"id_sub": "multi_asset_forex_rsi2::AUDUSD=X", "symbol": "AUDUSD=X",
     "note": "exit=3.211 vs real ~0.64 (~5x)"},
    {"id_sub": "iso_regime_terminal_QUBT_7834983377", "symbol": "QUBT",
     "note": "exit=1.208 vs real ~11 (entry at 11.2, exit wrongly scaled)"},
    {"id_sub": "iso_battleground_luxalgo_WIFUSDT_5821597090", "symbol": "CL=F",
     "note": "exit=0.1539 vs real ~70; id≠symbol (id says WIFUSDT, symbol is CL=F)"},
    {"id_sub": "iso_regime_terminal_QUBT_4957612416", "symbol": "KC=F",
     "note": "symbol mismatch: id says QUBT but symbol is KC=F; entry=11.2 looks like QUBT equity price"},
    {"id_sub": "iso_regime_terminal_USDJPY=X", "symbol": "USDCAD=X",
     "note": "symbol mismatch: id says USDJPY but symbol is USDCAD"},
    {"id_sub": "multi_asset_futures_connors_rsi2::NQ=F", "symbol": "NQ=F",
     "note": "scale_fail 0.0x — exit price near zero relative to NQ (~22,000)"},
]


def _load_price_cache(conn, symbols: list[str]) -> dict[str, float]:
    """Load latest OHLCV close per symbol from stock_ohlcv."""
    cache: dict[str, float] = {}
    if not symbols:
        return cache
    cur = conn.cursor()
    placeholders = ",".join(["%s"] * len(symbols))
    try:
        cur.execute(
            f"""
            SELECT o.symbol, o.close FROM stock_ohlcv o
            INNER JOIN (
                SELECT symbol, MAX(timestamp) AS mt
                FROM stock_ohlcv WHERE symbol IN ({placeholders})
                GROUP BY symbol
            ) m ON o.symbol = m.symbol AND o.timestamp = m.mt
            """,
            symbols,
        )
        for row in cur.fetchall():
            if row[0] not in cache:
                cache[row[0]] = float(row[1])
    except Exception:
        pass
    # Also try crypto_ohlcv for crypto symbols
    crypto_syms = [s for s in symbols if s not in cache]
    if crypto_syms:
        try:
            cplaceholders = ",".join(["%s"] * len(crypto_syms))
            cur.execute(
                f"""
                SELECT o.symbol, o.close FROM crypto_ohlcv o
                INNER JOIN (
                    SELECT symbol, MAX(timestamp) AS mt
                    FROM crypto_ohlcv WHERE symbol IN ({cplaceholders})
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


def _check_exit_scale(
    symbol: str, exit_price: float, category: str, price_cache: dict[str, float]
) -> tuple[bool, float | None, str]:
    """Return (would_catch, ratio, reason). would_catch=True means validation would reject."""
    if exit_price is None or exit_price <= 0:
        return False, None, "no_exit_price"
    cat = (category or "").upper()
    if cat in ("CRYPTO", "MEME", "MEMECOIN"):
        return False, None, "crypto_bypassed"  # crypto skipped by design
    close = price_cache.get(symbol)
    if close is None or close <= 0:
        return False, None, "no_ohlcv_data"
    threshold = _EXIT_SCALE_THRESHOLD_BY_CLASS.get(cat, _THRESHOLD_DEFAULT)
    ratio = max(exit_price / close, close / exit_price)
    if ratio > threshold:
        return True, round(ratio, 1), f"ratio_{ratio:.1f}x_threshold_{threshold:.0f}x"
    return False, round(ratio, 1), "pass"


def run(dry_run: bool = True) -> dict:
    creds = {k: v for k, v in get_stocks_creds().items()
             if k in ("host", "user", "password", "database", "port", "connect_timeout")}
    conn = pymysql.connect(**creds)
    cur = conn.cursor()

    # ── 1. Find rows to quarantine ──
    quarantined: list[dict] = []
    audit_results: list[dict] = []

    # Collect unique symbols from known corrupt list for price cache
    symbols_for_cache = list({k["symbol"] for k in KNOWN_CORRUPT if k.get("symbol")})
    price_cache = _load_price_cache(conn, symbols_for_cache)
    print(f"Price cache: {len(price_cache)} of {len(symbols_for_cache)} symbols have OHLCV data")

    for entry in KNOWN_CORRUPT:
        id_sub = entry["id_sub"]
        rows_for_this = []

        # Try exact match first
        cur.execute(
            "SELECT id, symbol, category, direction, entry_price, exit_price, status, pnl_pct "
            "FROM trading_picks WHERE id = %s",
            (id_sub,),
        )
        row = cur.fetchone()
        if row:
            rows_for_this.append(row)
        else:
            # LIKE search
            cur.execute(
                "SELECT id, symbol, category, direction, entry_price, exit_price, status, pnl_pct "
                "FROM trading_picks WHERE id LIKE %s LIMIT 5",
                (f"%{id_sub}%",),
            )
            rows_for_this.extend(cur.fetchall())

        for row in rows_for_this:
            pick_id, symbol, category, direction = row[0], row[1], row[2], row[3]
            entry_price = float(row[4]) if row[4] else None
            exit_price = float(row[5]) if row[5] else None
            status = row[6]
            pnl_pct = float(row[7]) if row[7] else None

            # Skip rows with no corrupt exit_price
            if exit_price is None:
                continue

            # Audit: would exit_price scale validation have caught this?
            would_catch, ratio, reason = _check_exit_scale(
                symbol, exit_price, category, price_cache
            )
            audit_results.append({
                "id": pick_id,
                "symbol": symbol,
                "category": category,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "status": status,
                "pnl_pct": pnl_pct,
                "ohclv_close": price_cache.get(symbol),
                "ratio_vs_close": ratio,
                "would_catch_at_ingest": would_catch,
                "audit_reason": reason,
                "investigation_note": entry["note"],
            })

            quarantined.append({
                "id": pick_id,
                "symbol": symbol,
                "category": category,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "status": status,
                "pnl_pct": pnl_pct,
                "note": entry["note"],
            })

    # ── 2. Report ──
    print(f"\n=== Found {len(quarantined)} rows to quarantine ===\n")
    for q in quarantined:
        print(f"  {q['id'][:60]}")
        print(f"    symbol={q['symbol']} cat={q['category']} status={q['status']}")
        print(f"    entry={q['entry_price']} exit={q['exit_price']} pnl={q['pnl_pct']}")
        print(f"    note: {q['note']}")
        print()

    # ── 3. Audit ──
    print("=== EXIT_PRICE SCALE VALIDATION AUDIT ===\n")
    for a in audit_results:
        catch_str = "WOULD CATCH" if a["would_catch_at_ingest"] else "would MISS"
        print(f"  {a['id'][:60]}")
        print(f"    symbol={a['symbol']} cat={a['category']} exit={a['exit_price']}")
        print(f"    OHLCV close={a['ohclv_close']} ratio={a['ratio_vs_close']}")
        print(f"    audit: {catch_str} — {a['audit_reason']}")
        print(f"    investigation: {a['investigation_note']}")
        print()

    caught = sum(1 for a in audit_results if a["would_catch_at_ingest"])
    missed = sum(1 for a in audit_results if not a["would_catch_at_ingest"] and a["audit_reason"] != "crypto_bypassed")
    print(f"Audit summary: {caught} would be caught, {missed} would be missed by exit_price scale validation")
    print()

    if dry_run:
        print("[DRY RUN] No changes made. Use --apply to quarantine.")
        cur.close()
        conn.close()
        return {"quarantine_count": len(quarantined), "audit": audit_results}

    # ── 4. Apply: backup then NULL ──
    if not quarantined:
        print("Nothing to quarantine.")
        cur.close()
        conn.close()
        return {"quarantine_count": 0, "audit": audit_results}

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_table = f"_backup_scale_corrupt_exits_{ts}"
    ids_to_backup = [q["id"] for q in quarantined]

    # Backup: create table from trading_picks schema, drop constraint, copy rows
    cur.execute(f"CREATE TABLE IF NOT EXISTS {backup_table} LIKE trading_picks")
    try:
        cur.execute(f"ALTER TABLE {backup_table} DROP CHECK chk_pnl_sign_coherence")
    except Exception:
        pass
    for pid in ids_to_backup:
        cur.execute(
            f"INSERT IGNORE INTO {backup_table} SELECT * FROM trading_picks WHERE id = %s",
            (pid,),
        )
    conn.commit()
    print(f"Backed up {len(ids_to_backup)} rows to {backup_table}")

    # NULL out exit_price and pnl_pct
    nulled = 0
    for pid in ids_to_backup:
        cur.execute(
            "UPDATE trading_picks SET exit_price = NULL, pnl_pct = NULL WHERE id = %s",
            (pid,),
        )
        if cur.rowcount > 0:
            nulled += 1
    conn.commit()
    print(f"NULLed exit_price/pnl_pct for {nulled} rows")

    # Write audit report
    report_path = REPO_ROOT / "reports" / f"scale_corrupt_exit_quarantine_{ts}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump({
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "backup_table": backup_table,
            "quarantined_count": len(quarantined),
            "quarantined_rows": quarantined,
            "exit_scale_audit": {
                "caught_by_validation": caught,
                "missed_by_validation": missed,
                "details": audit_results,
            },
        }, f, indent=2, default=str)
    print(f"Audit report written to {report_path}")

    cur.close()
    conn.close()
    return {
        "quarantine_count": len(quarantined),
        "backup_table": backup_table,
        "audit_caught": caught,
        "audit_missed": missed,
        "report_path": str(report_path),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Quarantine scale-corrupt exit prices")
    ap.add_argument("--apply", action="store_true", help="Actually NULL the exit_price/pnl_pct")
    args = ap.parse_args()
    result = run(dry_run=not args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
