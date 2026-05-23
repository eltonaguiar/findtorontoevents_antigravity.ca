#!/usr/bin/env python3
"""
Backfill historical Discord sends into MySQL at_discord_notifications.

Sources:
  1. data/freshpicks_gate_state.json — today's gate dedup with full details
  2. data/freshpicks_consensus_sent.json — historical consensus dedup keys
  3. alpha_engine/data/freshpicks_sent.json — alpha engine send keys
  4. KIMI_RISEOFTHECLAW/data/freshpicks_sent.json — KIMI send keys
  5. data/audit_trail.db — SQLite consensus_picks (cross-aggregator)
  6. Cross-reference consensus_tracked to mark discord_sent

Run:  py -m audit_trail.backfill_discord
"""

import json
import os
import sys
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

try:
    import pymysql
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql"],
                          stdout=subprocess.DEVNULL)
    import pymysql


def derive_asset_class(s):
    s = s.upper().replace("-", "")
    equity = {"SPY", "QQQ", "IWM", "TLT", "GLD", "SLV", "COPX", "VIX", "DIA"}
    meme = {"DOGE", "SHIB", "PEPE", "BONK", "FLOKI", "WIF", "BOME"}
    if any(s.startswith(e) for e in equity) or s in equity:
        return "EQUITY"
    for m in meme:
        if m in s:
            return "MEMECOIN"
    forex = {"EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"}
    for b in forex:
        if s.startswith(b) and len(s) >= 6 and not s.endswith("USDT"):
            return "FOREX"
    return "CRYPTO"


def main():
    try:
        from tools.db_env import get_stocks_creds
        _creds = get_stocks_creds()
    except Exception:
        import logging as _lg
        _lg.getLogger(__name__).warning("get_stocks_creds() failed — check DB_PASS_STOCKS env var")
        _creds = dict(host="mysql.50webs.com", user="ejaguiar1_stocks",
                      password="", database="ejaguiar1_stocks",
                      connect_timeout=15, autocommit=True)
    conn = pymysql.connect(**{**_creds, "autocommit": True})
    cur = conn.cursor()
    total_inserted = 0

    # ── 1. freshpicks_gate_state.json ──
    f1 = REPO / "data" / "freshpicks_gate_state.json"
    if f1.exists():
        state = json.loads(f1.read_text())
        dedup = state.get("dedup", {})
        cnt = 0
        for key, info in dedup.items():
            parts = key.split("__")
            symbol = parts[0] if parts else key
            direction = parts[1] if len(parts) > 1 else "LONG"
            if direction == "BUY":
                direction = "LONG"
            if direction == "SELL":
                direction = "SHORT"
            sent_at = info.get("sent_at", "")
            sent_at = sent_at.replace("+00:00", "").replace("T", " ")[:19]
            if not sent_at:
                continue
            try:
                cur.execute(
                    "INSERT IGNORE INTO at_discord_notifications "
                    "(symbol, direction, entry_price, take_profit, stop_loss, confidence, "
                    "asset_class, discord_channel, event_type, created_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (symbol, direction, info.get("entry"), info.get("tp"),
                     info.get("sl"), info.get("confidence"),
                     derive_asset_class(symbol), "freshpicks", "PICK_POSTED", sent_at),
                )
                if cur.rowcount:
                    cnt += 1
            except Exception as e:
                print(f"  Error gate_state {key}: {e}")
        print(f"[1] Gate state: {cnt} inserted")
        total_inserted += cnt

    # ── 2. freshpicks_consensus_sent.json ──
    f2 = REPO / "data" / "freshpicks_consensus_sent.json"
    if f2.exists():
        data = json.loads(f2.read_text())
        cnt = 0
        if isinstance(data, list):
            for key in data:
                parts = key.split("__")
                symbol = parts[0] if parts else key
                direction = parts[1] if len(parts) > 1 else "LONG"
                entry = None
                try:
                    entry = float(parts[2]) if len(parts) > 2 else None
                except (ValueError, IndexError):
                    pass
                if direction == "BUY":
                    direction = "LONG"
                if direction == "SELL":
                    direction = "SHORT"
                try:
                    cur.execute(
                        "INSERT IGNORE INTO at_discord_notifications "
                        "(symbol, direction, entry_price, asset_class, discord_channel, "
                        "event_type, created_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (symbol, direction, entry, derive_asset_class(symbol),
                         "consensus", "PICK_POSTED", "2026-03-01 00:00:00"),
                    )
                    if cur.rowcount:
                        cnt += 1
                except Exception:
                    pass
        print(f"[2] Consensus sent: {cnt} inserted")
        total_inserted += cnt

    # ── 3. alpha_engine/data/freshpicks_sent.json ──
    f3 = REPO / "alpha_engine" / "data" / "freshpicks_sent.json"
    if f3.exists():
        data = json.loads(f3.read_text())
        cnt = 0
        for key in (data if isinstance(data, list) else []):
            parts = key.split("::")
            if len(parts) >= 3:
                strategy, symbol, date_str = parts[0], parts[1], parts[2]
                symbol = symbol.upper().replace("-", "")
                if not symbol.endswith("USDT") and symbol.endswith("USD"):
                    symbol += "T"
                try:
                    cur.execute(
                        "INSERT IGNORE INTO at_discord_notifications "
                        "(symbol, direction, strategy, asset_class, discord_channel, "
                        "event_type, created_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (symbol, "LONG", strategy, derive_asset_class(symbol),
                         "freshpicks", "PICK_POSTED", date_str + " 00:00:00"),
                    )
                    if cur.rowcount:
                        cnt += 1
                except Exception:
                    pass
        print(f"[3] Alpha freshpicks: {cnt} inserted")
        total_inserted += cnt

    # ── 4. KIMI freshpicks_sent.json ──
    f4 = REPO / "KIMI_RISEOFTHECLAW" / "data" / "freshpicks_sent.json"
    if f4.exists():
        data = json.loads(f4.read_text())
        cnt = 0
        for key in (data if isinstance(data, list) else []):
            parts = key.split("__")
            symbol = parts[0] if parts else key
            strategy = parts[1] if len(parts) > 1 else None
            entry = None
            try:
                entry = float(parts[2]) if len(parts) > 2 else None
            except (ValueError, IndexError):
                pass
            try:
                cur.execute(
                    "INSERT IGNORE INTO at_discord_notifications "
                    "(symbol, direction, entry_price, strategy, asset_class, "
                    "discord_channel, event_type, created_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (symbol, "LONG", entry, strategy, derive_asset_class(symbol),
                     "freshpicks", "PICK_POSTED", "2026-03-01 00:00:00"),
                )
                if cur.rowcount:
                    cnt += 1
            except Exception:
                pass
        print(f"[4] KIMI freshpicks: {cnt} inserted")
        total_inserted += cnt

    # ── 5. SQLite consensus_picks ──
    db_path = REPO / "data" / "audit_trail.db"
    if db_path.exists():
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM consensus_picks").fetchall()
        cnt = 0
        for r in rows:
            d = dict(r)
            generated = (d.get("generated_at") or "").replace("T", " ").replace("Z", "")[:19]
            if not generated:
                continue
            try:
                cur.execute(
                    "INSERT IGNORE INTO at_discord_notifications "
                    "(symbol, direction, entry_price, take_profit, stop_loss, "
                    "confidence, agreement_count, source_systems, signal_tier, "
                    "asset_class, discord_channel, event_type, created_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (d["symbol"], d.get("direction", "LONG"),
                     d.get("entry_price"), d.get("take_profit"), d.get("stop_loss"),
                     d.get("confidence"), d.get("agreement_count"),
                     d.get("source_systems"), d.get("consensus_tier"),
                     d.get("asset_class", "CRYPTO"), "consensus", "PICK_POSTED",
                     generated),
                )
                if cur.rowcount:
                    cnt += 1
            except Exception:
                pass
        db.close()
        print(f"[5] SQLite consensus: {cnt} inserted")
        total_inserted += cnt

    # ── 6. Cross-reference consensus_tracked ──
    try:
        cur.execute(
            "UPDATE consensus_tracked ct "
            "INNER JOIN at_discord_notifications dn "
            "  ON ct.ticker = dn.symbol AND ct.direction = dn.direction "
            "SET ct.discord_sent = 1, "
            "    ct.discord_channel = dn.discord_channel, "
            "    ct.discord_sent_at = dn.created_at "
            "WHERE ct.discord_sent = 0"
        )
        matched = cur.rowcount
        print(f"[6] consensus_tracked marked discord_sent: {matched}")
    except Exception as e:
        print(f"[6] consensus_tracked update error: {e}")

    # ── Summary ──
    cur.execute("SELECT COUNT(*) FROM at_discord_notifications")
    total = cur.fetchone()[0]
    cur.execute("SELECT event_type, COUNT(*) FROM at_discord_notifications GROUP BY event_type")
    by_type = dict(cur.fetchall())
    cur.execute("SELECT discord_channel, COUNT(*) FROM at_discord_notifications GROUP BY discord_channel")
    by_channel = dict(cur.fetchall())

    print(f"\n=== BACKFILL COMPLETE ===")
    print(f"New rows inserted this run: {total_inserted}")
    print(f"Total at_discord_notifications: {total}")
    print(f"By event_type: {by_type}")
    print(f"By channel: {by_channel}")

    conn.close()


if __name__ == "__main__":
    main()
