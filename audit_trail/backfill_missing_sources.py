#!/usr/bin/env python3
"""
Backfill 5 missing sources into at_local_picks:
  1. Claude Gainer ML (claude_live_picks.json) — 32 picks
  2. Super Signals (cross_aggregation/data/super_signals.json) — 31 signals
  3. Regime Terminal (regime_terminal/data/active_signals.json) — 6 signals
  4. Genome DNA (genome/active_picks.json) — 3 picks
  5. Predictions Engine (predictions/data/active_predictions.json) — 300+ predictions

Run:  py -m audit_trail.backfill_missing_sources
"""

import json
import sys
from pathlib import Path

try:
    import pymysql
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql"],
                          stdout=subprocess.DEVNULL)
    import pymysql

REPO = Path(__file__).resolve().parent.parent

INSERT_SQL = """
    INSERT IGNORE INTO at_local_picks
    (symbol, direction, entry_price, take_profit, stop_loss, confidence,
     strategy, source_system, source_file, asset_class, status,
     exit_price, exit_reason, pnl_pct, signal_timestamp, created_at)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
"""


def safe_float(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if f != f else f
    except (ValueError, TypeError):
        return None


def derive_asset_class(symbol):
    s = symbol.upper().replace("-", "").replace("/", "")
    forex = {"EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "USD", "SEK", "NOK"}
    equity = {"SPY", "QQQ", "IWM", "TLT", "GLD", "SLV", "SOFI", "RIVN", "OPEN",
              "NFLX", "MA", "AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "META", "GOOG"}
    for e in equity:
        if s.startswith(e) or s == e:
            return "EQUITY"
    for b in forex:
        if s.startswith(b) and len(s) >= 6 and not s.endswith("USDT"):
            partner = s[len(b):len(b)+3]
            if partner in forex:
                return "FOREX"
    if s.endswith("USDT") or s.endswith("USD") or s.endswith("BTC"):
        return "CRYPTO"
    return "CRYPTO"


def backfill_claude_gainer(cur):
    """Claude Gainer ML — claude_live_picks.json"""
    fpath = REPO / "claude_gainer_ml" / "tracker" / "claude_live_picks.json"
    if not fpath.exists():
        print(f"  SKIP: {fpath} not found")
        return 0

    data = json.loads(fpath.read_text(encoding="utf-8"))
    picks = data.get("picks", [])
    count = 0

    for p in picks:
        symbol = p.get("symbol", "")
        if not symbol:
            continue
        direction = "LONG"  # all gainer picks are LONG
        status = p.get("status", "OPEN")
        exit_reason = p.get("exit_reason")
        pnl = safe_float(p.get("pnl_pct"))

        # Map confidence text to numeric
        conf_map = {"VERY HIGH": 0.9, "HIGH": 0.8, "MEDIUM": 0.6, "LOW": 0.4}
        conf = conf_map.get(p.get("confidence", ""), safe_float(p.get("pump_probability")))

        ts = p.get("entry_time", data.get("updated_at"))
        params = (
            symbol, direction,
            safe_float(p.get("entry_price")),
            safe_float(p.get("tp1_price")),
            safe_float(p.get("sl_price")),
            conf,
            f"claude_gainer_{p.get('coin_id', symbol).lower()}",
            "claude_gainer_ml",
            "claude_gainer_ml/tracker/claude_live_picks.json",
            derive_asset_class(symbol),
            status,
            safe_float(p.get("exit_price")),
            exit_reason,
            pnl,
            ts, ts,
        )
        try:
            cur.execute(INSERT_SQL, params)
            if cur.rowcount == 1:
                count += 1
        except Exception as e:
            print(f"    ERR {symbol}: {e}")
    return count


def backfill_super_signals(cur):
    """Super Signals — cross_aggregation/data/super_signals.json"""
    fpath = REPO / "cross_aggregation" / "data" / "super_signals.json"
    if not fpath.exists():
        print(f"  SKIP: {fpath} not found")
        return 0

    data = json.loads(fpath.read_text(encoding="utf-8"))
    signals = data.get("super_signals", [])
    ts = data.get("generated_at")
    count = 0

    for s in signals:
        symbol = s.get("symbol", "")
        if not symbol:
            continue
        agreeing = s.get("agreeing_systems", [])
        strategy = f"super_signal_{s.get('signal_tier', 'STANDARD').lower()}"

        params = (
            symbol, s.get("direction", "LONG"),
            safe_float(s.get("entry_price")),
            safe_float(s.get("take_profit")),
            safe_float(s.get("stop_loss")),
            safe_float(s.get("confidence")),
            strategy,
            "super_signals",
            "cross_aggregation/data/super_signals.json",
            derive_asset_class(symbol),
            "ACTIVE",
            None, None, None,
            ts, ts,
        )
        try:
            cur.execute(INSERT_SQL, params)
            if cur.rowcount == 1:
                count += 1
        except Exception as e:
            print(f"    ERR {symbol}: {e}")
    return count


def backfill_regime_terminal(cur):
    """Regime Terminal — regime_terminal/data/active_signals.json"""
    fpath = REPO / "regime_terminal" / "data" / "active_signals.json"
    if not fpath.exists():
        print(f"  SKIP: {fpath} not found")
        return 0

    data = json.loads(fpath.read_text(encoding="utf-8"))
    signals = data.get("signals", [])
    ts = data.get("generated_at")
    count = 0

    for s in signals:
        ticker = s.get("ticker", "")
        if not ticker:
            continue
        direction = s.get("signal", "LONG").upper()
        if direction == "SHORT":
            direction = "SHORT"
        else:
            direction = "LONG"

        strategy = f"regime_{s.get('regime', 'unknown').lower().replace(' ', '_')}"

        params = (
            ticker, direction,
            safe_float(s.get("price")),
            None, None,  # no TP/SL for regime signals
            safe_float(s.get("confidence")),
            strategy,
            "regime_terminal",
            "regime_terminal/data/active_signals.json",
            derive_asset_class(ticker),
            "ACTIVE",
            None, None, None,
            ts, ts,
        )
        try:
            cur.execute(INSERT_SQL, params)
            if cur.rowcount == 1:
                count += 1
        except Exception as e:
            print(f"    ERR {ticker}: {e}")
    return count


def backfill_genome(cur):
    """Genome DNA — genome/active_picks.json"""
    fpath = REPO / "genome" / "active_picks.json"
    if not fpath.exists():
        print(f"  SKIP: {fpath} not found")
        return 0

    data = json.loads(fpath.read_text(encoding="utf-8"))
    picks = data.get("picks", [])
    ts = data.get("metadata", {}).get("generated_at")
    count = 0

    for p in picks:
        symbol = p.get("symbol", "")
        if not symbol:
            continue

        dna = p.get("strategy_dna", {})
        strategy = dna.get("strategy_id", "genome_unknown")

        params = (
            symbol, p.get("direction", "LONG"),
            safe_float(p.get("entry_price")),
            safe_float(p.get("take_profit")),
            safe_float(p.get("stop_loss")),
            safe_float(p.get("confidence")),
            strategy,
            "genome_dna",
            "genome/active_picks.json",
            derive_asset_class(symbol),
            p.get("status", "OPEN").upper(),
            None, None, None,
            ts, ts,
        )
        try:
            cur.execute(INSERT_SQL, params)
            if cur.rowcount == 1:
                count += 1
        except Exception as e:
            print(f"    ERR {symbol}: {e}")
    return count


def backfill_predictions(cur):
    """Predictions Engine — predictions/data/active_predictions.json"""
    fpath = REPO / "predictions" / "data" / "active_predictions.json"
    if not fpath.exists():
        print(f"  SKIP: {fpath} not found")
        return 0

    data = json.loads(fpath.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        data = data.get("predictions", [])
    count = 0

    for p in data:
        symbol = p.get("symbol", "")
        if not symbol:
            continue

        conf = safe_float(p.get("sentiment_score"))
        strategy = f"predictions_{p.get('analyst_category', 'community')}"
        ts = p.get("scraped_at")
        status = p.get("status", "ACTIVE").upper()

        params = (
            symbol, p.get("direction", "LONG"),
            safe_float(p.get("entry_price")),
            safe_float(p.get("take_profit")),
            safe_float(p.get("stop_loss")),
            conf,
            strategy,
            "predictions_engine",
            "predictions/data/active_predictions.json",
            derive_asset_class(symbol),
            status,
            safe_float(p.get("resolution_price")),
            p.get("resolved_at"),
            safe_float(p.get("outcome_pnl_pct")),
            ts, ts,
        )
        try:
            cur.execute(INSERT_SQL, params)
            if cur.rowcount == 1:
                count += 1
        except Exception as e:
            print(f"    ERR {symbol}: {e}")
    return count


def main():
    # Resolve credentials via tools.db_env so the 2026-05-13 rotation
    # (DB_PASS_STOCKS) is picked up. Previous hardcoded password="stocks123"
    # broke after the secret rotation and caused
    # "Packet sequence number wrong - got 4 expected 2" on the auth handshake.
    # See docs/DB_ROTATION_RUNBOOK_2026-05-13.md.
    try:
        from tools.db_env import get_stocks_creds
        creds = get_stocks_creds()
    except Exception as _e:
        import logging as _lg2
        _lg2.getLogger(__name__).warning(
            "get_stocks_creds() failed (%s) — set DB_PASS_STOCKS env var; proceeding without password", _e)
        creds = dict(
            host="mysql.50webs.com", user="ejaguiar1_stocks",
            password="", database="ejaguiar1_stocks",
        )
    creds.setdefault("connect_timeout", 30)
    creds.setdefault("read_timeout", 30)
    creds.setdefault("write_timeout", 30)
    creds.setdefault("autocommit", True)
    conn = pymysql.connect(**creds)
    cur = conn.cursor()

    total = 0
    sources = [
        ("Claude Gainer ML", backfill_claude_gainer),
        ("Super Signals", backfill_super_signals),
        ("Regime Terminal", backfill_regime_terminal),
        ("Genome DNA", backfill_genome),
        ("Predictions Engine", backfill_predictions),
    ]

    for name, fn in sources:
        print(f"\n--- {name} ---")
        n = fn(cur)
        print(f"  Inserted: {n}")
        total += n

    # Verify
    cur.execute("SELECT source_system, COUNT(*) FROM at_local_picks GROUP BY source_system ORDER BY 2 DESC")
    print(f"\n=== COMPLETE INVENTORY ({total} new rows) ===")
    grand = 0
    for sys, cnt in cur.fetchall():
        print(f"  {sys:<40} {cnt:>5}")
        grand += cnt
    print(f"  {'TOTAL':<40} {grand:>5}")

    conn.close()


if __name__ == "__main__":
    main()
