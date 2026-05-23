"""
Forward-Test Tracker — validates Claude's $1,000 allocation recommendation.

Recommendation (Mar 2, 2026):
  System 1: Keltner Mean Reversion  $600 (60%) — Sharpe 2.06, WR 67.6%
  System 2: Connors RSI-2           $400 (40%) — Sharpe 1.15, WR 68.3%

This module:
  1. Reads signals from the recommended systems in signal_log.db
  2. Logs paper trades into a forward_test table
  3. Tracks entry price, TP/SL, and actual outcomes
  4. Computes live Sharpe, WR, max drawdown vs. historical benchmarks
  5. Exports results to JSON for Hub/Discord consumption

Entry Rules (from validated_winners):
  Keltner: Price touches lower Keltner band (EMA20 - 2*ATR14), price > 200 SMA
  Connors RSI-2: Close > 200 SMA AND RSI(2) < 5 — exit when RSI(2) > 65 or 10-bar max

Called by signal-recorder.yml after outcome_tracker.
"""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import sys

# Use shared api_failover for resilient multi-exchange price fetching
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from alpha_engine import api_failover as _failover
except ImportError:
    _failover = None

DB_PATH = Path(__file__).parent / "data" / "signal_log.db"
OUTPUT_PATH = Path(__file__).parent / "data" / "forward_test_results.json"

# Recommended systems and allocation
ALLOCATION = {
    "keltner_mean_rev": {"budget": 600, "label": "Keltner Mean Reversion",
                         "hist_wr": 0.676, "hist_sharpe": 2.06},
    "connors_rsi2":     {"budget": 400, "label": "Connors RSI-2",
                         "hist_wr": 0.683, "hist_sharpe": 1.15},
}

# Map which signal_log system_ids correspond to each recommended system
# These strategies fire signals through multiple systems
SYSTEM_MAP = {
    "keltner_mean_rev": ["mercury2", "alpha_engine", "crypto_ml_edge", "ensemble"],
    "connors_rsi2":     ["mercury2", "alpha_engine", "crypto_ml_edge"],
}

MAX_HOLD_HOURS = 168  # 7 days — auto-close stale positions (was 240/10d, anomalous accumulation)
TP_PCT = 5.0   # 5% take-profit
SL_PCT = 3.0   # 3% stop-loss
MAX_CONCURRENT = 5  # max open trades per system


def _get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS forward_test (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system_key TEXT NOT NULL,
            signal_log_id INTEGER,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            take_profit REAL NOT NULL,
            stop_loss REAL NOT NULL,
            entry_time TEXT NOT NULL,
            exit_time TEXT,
            exit_price REAL,
            pnl_pct REAL,
            status TEXT DEFAULT 'OPEN',
            notes TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ft_status ON forward_test(status);
        CREATE INDEX IF NOT EXISTS idx_ft_system ON forward_test(system_key);
    """)
    conn.commit()
    return conn


def _fetch_price(symbol: str) -> float:
    """Fetch current price via api_failover (Binance->Bybit->CoinGecko->KuCoin)."""
    if _failover:
        price = _failover.fetch_price(symbol)
        if price is not None:
            return price
    # Direct Binance fallback if api_failover unavailable
    for base in ["https://api.binance.com", "https://api1.binance.com",
                 "https://api2.binance.com", "https://api3.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/price",
                             params={"symbol": symbol}, timeout=10)
            return float(r.json()["price"])
        except Exception:
            continue
    return 0.0


def _fetch_prices(symbols: list) -> dict:
    """Fetch multiple prices via api_failover with Binance fallback."""
    prices = {}
    if _failover:
        for sym in symbols:
            p = _failover.fetch_price(sym)
            if p is not None:
                prices[sym] = p
        if prices:
            return prices
    # Direct Binance fallback
    for base in ["https://api.binance.com", "https://api1.binance.com",
                 "https://api2.binance.com", "https://api3.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/price",
                             params={"symbols": json.dumps(symbols)}, timeout=10)
            return {t["symbol"]: float(t["price"]) for t in r.json()}
        except Exception:
            continue
    return {}


def enforce_max_concurrent(conn):
    """Close excess open trades per system so each system never exceeds MAX_CONCURRENT.

    This handles the bulk-insert anomaly where historical signals were loaded all at once
    bypassing the MAX_CONCURRENT gate in check_new_signals, resulting in 88 open trades
    across 2 systems (44 each) instead of the intended 5 per system.

    Strategy: keep the MAX_CONCURRENT newest open trades per system; close the rest as
    EXPIRED with the current price (fetched) or entry price if unavailable.
    """
    now = datetime.now(timezone.utc)

    for sys_key in ALLOCATION:
        open_trades = conn.execute(
            "SELECT * FROM forward_test WHERE system_key=? AND status='OPEN' ORDER BY entry_time DESC",
            (sys_key,)
        ).fetchall()

        if len(open_trades) <= MAX_CONCURRENT:
            continue

        # Keep the MAX_CONCURRENT newest; close the rest (oldest first)
        to_close = list(open_trades)[MAX_CONCURRENT:]  # oldest are at the end (DESC sort)
        symbols = list(set(t["symbol"] for t in to_close))
        prices = _fetch_prices(symbols)

        closed_count = 0
        for trade in to_close:
            sym = trade["symbol"]
            current = prices.get(sym, trade["entry_price"])  # fallback to entry
            entry = trade["entry_price"]
            direction = trade["direction"]

            try:
                entry_time = datetime.fromisoformat(trade["entry_time"])
                age_hours = (now - entry_time).total_seconds() / 3600
            except (ValueError, TypeError):
                age_hours = 0

            if direction == "BUY":
                pnl = round((current - entry) / entry * 100, 4)
            else:
                pnl = round((entry - current) / entry * 100, 4)

            conn.execute("""
                UPDATE forward_test
                SET status='EXPIRED', exit_price=?, exit_time=?, pnl_pct=?, notes=?
                WHERE id=?
            """, (current, now.isoformat(), pnl,
                  f"Closed by MAX_CONCURRENT enforcer after {age_hours:.1f}h (limit={MAX_CONCURRENT}/system)",
                  trade["id"]))
            closed_count += 1

        if closed_count:
            conn.commit()
            print(f"[FWD-TEST] MAX_CONCURRENT enforcer: closed {closed_count} excess open trades for {sys_key}")


def check_new_signals(conn):
    """Check signal_log for new signals from recommended systems and open paper trades."""
    now = datetime.now(timezone.utc)
    lookback = (now - timedelta(minutes=20)).isoformat()

    for sys_key, info in ALLOCATION.items():
        source_ids = SYSTEM_MAP.get(sys_key, [])
        if not source_ids:
            continue

        # Count open trades for this system
        open_count = conn.execute(
            "SELECT COUNT(*) FROM forward_test WHERE system_key=? AND status='OPEN'",
            (sys_key,)
        ).fetchone()[0]

        if open_count >= MAX_CONCURRENT:
            continue

        placeholders = ",".join("?" * len(source_ids))
        signals = conn.execute(f"""
            SELECT * FROM signal_log
            WHERE system_id IN ({placeholders})
              AND timestamp > ?
              AND signal IN ('BUY', 'SELL')
            ORDER BY timestamp DESC
        """, (*source_ids, lookback)).fetchall()

        for sig in signals:
            symbol = sig["symbol"]
            direction = sig["signal"]
            price = sig["price_at_signal"] or sig["entry_price"]
            if not price or price <= 0:
                continue

            # Check for duplicate
            existing = conn.execute(
                "SELECT id FROM forward_test WHERE system_key=? AND symbol=? AND status='OPEN'",
                (sys_key, symbol)
            ).fetchone()
            if existing:
                continue

            # Calculate TP/SL
            if direction == "BUY":
                tp = round(price * (1 + TP_PCT / 100), 8)
                sl = round(price * (1 - SL_PCT / 100), 8)
            else:
                tp = round(price * (1 - TP_PCT / 100), 8)
                sl = round(price * (1 + SL_PCT / 100), 8)

            conn.execute("""
                INSERT INTO forward_test
                    (system_key, signal_log_id, symbol, direction, entry_price,
                     take_profit, stop_loss, entry_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """, (sys_key, sig["id"], symbol, direction, price, tp, sl,
                  now.isoformat()))
            conn.commit()
            print(f"[FWD-TEST] Opened {sys_key} {direction} {symbol} @ {price}")


def check_open_trades(conn):
    """Check open paper trades against live prices."""
    open_trades = conn.execute(
        "SELECT * FROM forward_test WHERE status='OPEN'"
    ).fetchall()

    if not open_trades:
        print("[FWD-TEST] No open trades")
        return

    symbols = list(set(t["symbol"] for t in open_trades))
    prices = _fetch_prices(symbols)
    now = datetime.now(timezone.utc)

    for trade in open_trades:
        sym = trade["symbol"]
        if sym not in prices:
            continue

        current = prices[sym]
        direction = trade["direction"]
        entry = trade["entry_price"]
        tp = trade["take_profit"]
        sl = trade["stop_loss"]

        # Time exit
        try:
            entry_time = datetime.fromisoformat(trade["entry_time"])
            age_hours = (now - entry_time).total_seconds() / 3600
        except (ValueError, TypeError):
            age_hours = 0

        status = None
        exit_price = current

        # TP check
        if direction == "BUY" and current >= tp:
            status = "TP_HIT"
            exit_price = tp
        elif direction == "SELL" and current <= tp:
            status = "TP_HIT"
            exit_price = tp

        # SL check
        if direction == "BUY" and current <= sl:
            status = "SL_HIT"
            exit_price = sl
        elif direction == "SELL" and current >= sl:
            status = "SL_HIT"
            exit_price = sl

        # Time exit
        if not status and age_hours >= MAX_HOLD_HOURS:
            status = "EXPIRED"
            exit_price = current

        if status:
            if direction == "BUY":
                pnl = round((exit_price - entry) / entry * 100, 4)
            else:
                pnl = round((entry - exit_price) / entry * 100, 4)

            conn.execute("""
                UPDATE forward_test
                SET status=?, exit_price=?, exit_time=?, pnl_pct=?,
                    notes=?
                WHERE id=?
            """, (status, exit_price, now.isoformat(), pnl,
                  f"Closed after {age_hours:.1f}h", trade["id"]))
            conn.commit()
            print(f"[FWD-TEST] Closed {trade['system_key']} {sym} {status}: {pnl:+.2f}%")


def export_results(conn):
    """Export forward test results to JSON."""
    closed = conn.execute(
        "SELECT * FROM forward_test WHERE status != 'OPEN' ORDER BY exit_time DESC"
    ).fetchall()
    open_trades = conn.execute(
        "SELECT * FROM forward_test WHERE status = 'OPEN'"
    ).fetchall()

    results = {"recommendation_date": "2026-03-02", "total_budget": 1000}

    for sys_key, info in ALLOCATION.items():
        sys_closed = [dict(t) for t in closed if t["system_key"] == sys_key]
        sys_open = [dict(t) for t in open_trades if t["system_key"] == sys_key]

        wins = sum(1 for t in sys_closed if (t.get("pnl_pct") or 0) > 0)
        total = len(sys_closed)
        pnl_list = [t.get("pnl_pct", 0) or 0 for t in sys_closed]
        total_pnl = sum(pnl_list)
        avg_pnl = total_pnl / total if total else 0

        # Compute forward Sharpe
        if len(pnl_list) >= 2:
            import statistics
            mean = statistics.mean(pnl_list)
            stdev = statistics.stdev(pnl_list)
            sharpe = (mean / stdev * (252 ** 0.5)) if stdev > 0 else 0
        else:
            sharpe = 0

        # Max drawdown
        equity = 0
        peak = 0
        max_dd = 0
        for p in pnl_list:
            equity += p
            peak = max(peak, equity)
            dd = peak - equity
            max_dd = max(max_dd, dd)

        results[sys_key] = {
            "label": info["label"],
            "budget": info["budget"],
            "historical_wr": info["hist_wr"],
            "historical_sharpe": info["hist_sharpe"],
            "forward_trades": total,
            "forward_wins": wins,
            "forward_wr": round(wins / total, 4) if total else 0,
            "forward_total_pnl": round(total_pnl, 4),
            "forward_avg_pnl": round(avg_pnl, 4),
            "forward_sharpe": round(sharpe, 4),
            "forward_max_dd": round(max_dd, 4),
            "open_trades": len(sys_open),
            "closed_trades": [
                {k: v for k, v in t.items() if k != "id"} for t in sys_closed[:20]
            ],
        }

    # Overall portfolio metrics
    all_closed = [dict(t) for t in closed]
    all_pnl = [t.get("pnl_pct", 0) or 0 for t in all_closed]
    results["portfolio"] = {
        "total_trades": len(all_closed),
        "total_wins": sum(1 for p in all_pnl if p > 0),
        "total_pnl": round(sum(all_pnl), 4),
        "open_trades": len(open_trades),
    }

    results["updated_at"] = datetime.now(timezone.utc).isoformat()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2, default=str))
    print(f"[FWD-TEST] Exported: {len(all_closed)} closed, {len(open_trades)} open")


def run():
    if not DB_PATH.exists():
        print("[FWD-TEST] No signal_log.db yet, skipping")
        return

    conn = _get_db()
    enforce_max_concurrent(conn)  # trim excess open trades before processing new ones
    check_new_signals(conn)
    check_open_trades(conn)
    export_results(conn)
    conn.close()


if __name__ == "__main__":
    run()
