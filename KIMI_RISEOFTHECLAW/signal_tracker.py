#!/usr/bin/env python3
"""
ANTIGRAVITY_FEB172026 ? Signal Tracker & Validator
====================================================
Tracks live signals, monitors real-time prices, validates TP/SL outcomes.

Workflow:
  1. RECORD: Reads signals from data/live_signals_now.json -> stores in SQLite
  2. MONITOR: Fetches current Binance prices for all tracked symbols
  3. VALIDATE: Checks if TP or SL was hit -> marks WIN / LOSS / OPEN
  4. REPORT: Prints scoreboard + saves results to data/signal_tracking.json

Run:  python signal_tracker.py              (one-shot check)
      python signal_tracker.py --loop 300   (continuous, check every 300s)
"""

import json
import sys
import time
import sqlite3
import argparse
import requests
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DB_PATH = DATA_DIR / "signal_tracker.db"
SIGNALS_INPUT = DATA_DIR / "live_signals_now.json"
TRACKING_OUTPUT = DATA_DIR / "signal_tracking.json"

_BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://api.binance.us",
    "https://data-api.binance.vision",
]
BINANCE_BASE = "https://api.binance.com"

# Time-based expiry: close signals that have been open too long without hitting TP/SL
# This prevents infinite open positions and generates closed trade data faster
MAX_HOLD_DAYS_CRYPTO = 7   # Crypto moves fast, 24/7 markets
MAX_HOLD_DAYS_FOREX = 14   # Forex is slower, need more time
MAX_HOLD_DAYS_DEFAULT = 7  # Default for unknown asset classes

YF_TO_BINANCE = {
    "BTC-USD": "BTCUSDT",  "ETH-USD": "ETHUSDT",  "SOL-USD": "SOLUSDT",
    "BNB-USD": "BNBUSDT",  "AVAX-USD": "AVAXUSDT", "XRP-USD": "XRPUSDT",
    "ADA-USD": "ADAUSDT",  "DOGE-USD": "DOGEUSDT", "SHIB-USD": "SHIBUSDT",
    "MATIC-USD": "MATICUSDT", "LINK-USD": "LINKUSDT", "DOT-USD": "DOTUSDT",
    "ATOM-USD": "ATOMUSDT", "NEAR-USD": "NEARUSDT", "LTC-USD": "LTCUSDT",
    "BCH-USD": "BCHUSDT",  "PEPE-USD": "PEPEUSDT", "INJ-USD": "INJUSDT",
    "TIA-USD": "TIAUSDT",  "OP-USD":   "OPUSDT",   "ARB11841-USD": "ARBUSDT",
    "SUI20947-USD": "SUIUSDT", "SEI-USD": "SEIUSDT", "FIL-USD": "FILUSDT",
    "APT21794-USD": "APTUSDT", "BONK-USD": "BONKUSDT", "FLOKI-USD": "FLOKIUSDT",
    "WIF-USD": "WIFUSDT",  "VET-USD": "VETUSDT",
}

# Forex symbols use yfinance format
FOREX_SYMBOLS = ["EURUSD=X", "GBPUSD=X", "JPY=X", "AUDUSD=X", "CAD=X", "NZDUSD=X", "CHF=X", "GBPJPY=X"]


# ===========================================================================
# DATABASE
# ===========================================================================

def init_db():
    """Create tracking database if it doesn't exist."""
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tracked_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT UNIQUE,
            symbol TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            confidence INTEGER,
            entry_price REAL NOT NULL,
            take_profit REAL NOT NULL,
            stop_loss REAL NOT NULL,
            risk_reward REAL,
            reasons TEXT,
            entry_time TEXT NOT NULL,
            current_price REAL,
            highest_price REAL,
            lowest_price REAL,
            pnl_pct REAL DEFAULT 0,
            status TEXT DEFAULT 'OPEN',
            exit_price REAL,
            exit_time TEXT,
            exit_reason TEXT,
            last_checked TEXT,
            checks_count INTEGER DEFAULT 0,
            market_context_at_entry TEXT
        )
    """)
    # Migration: add market_context_at_entry column if it was created without it
    try:
        conn.execute("ALTER TABLE tracked_signals ADD COLUMN market_context_at_entry TEXT")
        conn.commit()
    except Exception:
        pass  # Column already exists — normal case
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT,
            timestamp TEXT,
            price REAL,
            pnl_pct REAL,
            FOREIGN KEY (signal_id) REFERENCES tracked_signals(signal_id)
        )
    """)
    conn.commit()
    return conn


# ===========================================================================
# RESTORE: Rehydrate DB from signal_tracking.json (DB doesn't persist in git)
# ===========================================================================

def restore_from_json(conn):
    """Restore previously tracked signals from signal_tracking.json into SQLite.

    The .db file is excluded from git commits (too large), so every CI run
    starts with an empty database.  This function rehydrates the DB from the
    JSON file that IS committed, preserving status, exit info, highest/lowest
    prices, and check counts so that validation can continue where it left off.
    """
    if not TRACKING_OUTPUT.exists():
        print("  No signal_tracking.json to restore from")
        return 0

    try:
        with open(TRACKING_OUTPUT, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        print(f"  Error reading signal_tracking.json: {e}")
        return 0

    signals = data.get("signals", [])
    if not signals:
        print("  signal_tracking.json has no signals")
        return 0

    cursor = conn.cursor()
    restored = 0

    for sig in signals:
        signal_id = sig.get("signal_id", "")
        if not signal_id:
            # Generate a fallback signal_id from symbol + entry_time
            symbol = sig.get("symbol", "unknown")
            entry_time = sig.get("entry_time", "")
            signal_id = f"{symbol}_{entry_time[:19]}"

        # Skip if already in DB (from a previous restore in same run)
        cursor.execute("SELECT id FROM tracked_signals WHERE signal_id = ?", (signal_id,))
        if cursor.fetchone():
            continue

        # Parse reasons back to JSON string if it's a list
        reasons = sig.get("reasons", [])
        if isinstance(reasons, list):
            reasons = json.dumps(reasons)
        elif not isinstance(reasons, str):
            reasons = json.dumps([str(reasons)])

        # Serialize market_context_at_entry for DB storage
        mctx = sig.get("market_context_at_entry")
        mctx_json = json.dumps(mctx) if mctx else None

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO tracked_signals
                (signal_id, symbol, asset_class, signal_type, confidence,
                 entry_price, take_profit, stop_loss, risk_reward, reasons,
                 entry_time, current_price, highest_price, lowest_price,
                 pnl_pct, status, exit_price, exit_time, exit_reason,
                 last_checked, checks_count, market_context_at_entry)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id,
                sig.get("symbol", ""),
                sig.get("asset_class", "crypto"),
                sig.get("signal_type", "BUY"),
                sig.get("confidence", 0),
                sig.get("entry_price", 0),
                sig.get("take_profit", 0),
                sig.get("stop_loss", 0),
                sig.get("risk_reward", 0),
                reasons,
                sig.get("entry_time", ""),
                sig.get("current_price"),
                sig.get("highest_price"),
                sig.get("lowest_price"),
                sig.get("pnl_pct", 0),
                sig.get("status", "OPEN"),
                sig.get("exit_price"),
                sig.get("exit_time"),
                sig.get("exit_reason"),
                sig.get("last_checked"),
                sig.get("checks_count", 0),
                mctx_json,
            ))
            if cursor.rowcount > 0:
                restored += 1
        except Exception as e:
            print(f"  Error restoring {signal_id}: {e}")

    conn.commit()
    return restored


# ===========================================================================
# RECORD: Import signals from live_signals_now.json
# ===========================================================================

def record_signals(conn):
    """Import new signals from live_signals_now.json into tracking DB."""
    if not SIGNALS_INPUT.exists():
        print("  No live_signals_now.json found")
        return 0

    with open(SIGNALS_INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    generated_at = data.get("generated_at", "")
    crypto_signals = data.get("crypto_signals", [])
    forex_signals = data.get("forex_signals", [])

    new_count = 0
    cursor = conn.cursor()

    def _record_signal(sig, asset_class):
        """Record a signal, skipping if an OPEN signal with same (symbol, entry_price, signal_type) exists."""
        nonlocal new_count
        signal_id = f"{sig['symbol']}_{generated_at[:19]}"
        symbol = sig["symbol"]
        signal_type = sig["signal"]
        entry_price = sig["price"]

        try:
            # Check for existing OPEN signal with same key fields to prevent duplicates
            cursor.execute("""
                SELECT id FROM tracked_signals
                WHERE symbol = ? AND entry_price = ? AND signal_type = ? AND status = 'OPEN'
                LIMIT 1
            """, (symbol, entry_price, signal_type))
            existing = cursor.fetchone()

            if existing:
                # Already tracking this signal — update confidence/reasons if needed
                cursor.execute("""
                    UPDATE tracked_signals
                    SET confidence = ?, reasons = ?, last_checked = ?
                    WHERE id = ?
                """, (
                    sig.get("confidence", 0),
                    json.dumps(sig.get("reasons", [])),
                    datetime.now(timezone.utc).isoformat(),
                    existing[0],
                ))
                return

            # Persist market context at entry for ML training (fixes train/serve skew)
            market_context = {
                "rsi_at_entry": sig.get("rsi_at_entry", sig.get("rsi", sig.get("RSI", 0))),
                "volume_ratio": sig.get("volume_ratio", sig.get("volumeRatio", 0)),
                "fear_greed": sig.get("fear_greed", sig.get("fearGreed", sig.get("fg_index", 0))),
                "risk_reward": sig.get("risk_reward", 0),
                "hour_of_day": datetime.now(timezone.utc).hour,
                "btc_24h_change": sig.get("btc_24h_change", sig.get("btc24hChange", 0)),
            }

            cursor.execute("""
                INSERT OR IGNORE INTO tracked_signals
                (signal_id, symbol, asset_class, signal_type, confidence,
                 entry_price, take_profit, stop_loss, risk_reward, reasons,
                 entry_time, current_price, highest_price, lowest_price, status,
                 market_context_at_entry)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
            """, (
                signal_id,
                symbol,
                asset_class,
                signal_type,
                sig.get("confidence", 0),
                entry_price,
                sig["take_profit"],
                sig["stop_loss"],
                sig.get("risk_reward", 0),
                json.dumps(sig.get("reasons", [])),
                sig.get("timestamp", generated_at),
                entry_price,
                entry_price,
                entry_price,
                json.dumps(market_context),
            ))
            if cursor.rowcount > 0:
                new_count += 1
        except Exception as e:
            print(f"  Error recording {symbol}: {e}")

    for sig in crypto_signals:
        _record_signal(sig, "crypto")

    for sig in forex_signals:
        _record_signal(sig, "forex")

    conn.commit()
    return new_count


# ===========================================================================
# MONITOR: Fetch current prices from Binance
# ===========================================================================

def fetch_current_prices(conn=None):
    """Fetch current prices for all tracked symbols."""
    prices = {}

    # Crypto: Binance (with endpoint failover)
    binance_ok = False
    for _base in _BINANCE_SPOT_BASES:
        try:
            resp = requests.get(f"{_base}/api/v3/ticker/price", timeout=10)
            if resp.status_code in (451, 403):
                continue
            if resp.status_code == 200:
                bn_to_yf = {v: k for k, v in YF_TO_BINANCE.items()}
                for t in resp.json():
                    yf_sym = bn_to_yf.get(t["symbol"])
                    if yf_sym:
                        prices[yf_sym] = float(t["price"])
                binance_ok = True
                break
        except Exception as e:
            print(f"  Binance price fetch from {_base} failed: {e}")
            continue
    if not binance_ok:
        print("  [WARN] All Binance endpoints failed for price fetch")

    # Build forex symbol list: hardcoded + any tracked forex symbols from DB
    forex_to_fetch = set(FOREX_SYMBOLS)
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT symbol FROM tracked_signals WHERE asset_class = 'forex' AND status = 'OPEN'")
            for row in cursor.fetchall():
                forex_to_fetch.add(row[0])
        except Exception:
            pass

    # Forex: yfinance (quick fetch)
    try:
        import yfinance as yf
        for sym in forex_to_fetch:
            try:
                ticker = yf.Ticker(sym)
                info = ticker.fast_info
                if hasattr(info, "last_price") and info.last_price:
                    prices[sym] = float(info.last_price)
                else:
                    hist = ticker.history(period="1d")
                    if hist is not None and len(hist) > 0:
                        prices[sym] = float(hist["Close"].iloc[-1])
            except Exception:
                continue
    except ImportError:
        pass  # yfinance not available

    return prices


# ===========================================================================
# VALIDATE: Check TP/SL for each open signal
# ===========================================================================

def validate_signals(conn, prices):
    """Check each OPEN signal against current prices. Mark WIN/LOSS."""
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.cursor()

    # Get all OPEN signals
    cursor.execute("SELECT * FROM tracked_signals WHERE status = 'OPEN'")
    columns = [desc[0] for desc in cursor.description]
    open_signals = [dict(zip(columns, row)) for row in cursor.fetchall()]

    results = {"wins": 0, "losses": 0, "open": 0, "checked": 0}

    for sig in open_signals:
        symbol = sig["symbol"]
        current_price = prices.get(symbol)
        if current_price is None:
            results["open"] += 1
            continue

        entry_price = sig["entry_price"]
        tp = sig["take_profit"]
        sl = sig["stop_loss"]
        signal_type = (sig.get("signal_type") or "BUY").upper()
        is_long = signal_type in ("BUY", "LONG")
        highest = max(sig["highest_price"] or entry_price, current_price)
        lowest = min(sig["lowest_price"] or entry_price, current_price)
        checks = (sig["checks_count"] or 0) + 1

        # P&L depends on direction
        if is_long:
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # Record price history
        cursor.execute("""
            INSERT INTO price_history (signal_id, timestamp, price, pnl_pct)
            VALUES (?, ?, ?, ?)
        """, (sig["signal_id"], now, current_price, round(pnl_pct, 4)))

        # Check if TP or SL hit (direction-aware)
        status = "OPEN"
        exit_reason = None
        exit_price = None

        # SL_BUFFER: only trigger early when price is AT or BELOW the stop (with a small
        # downside buffer for slippage).  The previous 0.5% UPSIDE buffer incorrectly
        # fired for long trades where price was still above SL (positive PnL), causing
        # 155 profitable trades to be mis-classified as LOSS.
        if is_long:
            # LONG/BUY: price UP = TP, price DOWN = SL
            if current_price >= tp:
                status = "WIN"
                exit_reason = f"TP hit at ${current_price:,.6f} (target was ${tp:,.6f})"
                exit_price = current_price
                results["wins"] += 1
            elif current_price <= sl:
                # Price at or below stop — genuine SL hit
                status = "LOSS"
                exit_price = sl  # book at SL price for realistic PnL
                exit_reason = f"SL hit at ${exit_price:,.6f} (stop was ${sl:,.6f}, live=${current_price:,.6f})"
                results["losses"] += 1
            elif highest >= tp:
                status = "WIN"
                exit_reason = f"TP was touched (highest=${highest:,.6f}, target=${tp:,.6f})"
                exit_price = tp
                results["wins"] += 1
            elif lowest <= sl:
                status = "LOSS"
                exit_reason = f"SL was touched (lowest=${lowest:,.6f}, stop=${sl:,.6f})"
                exit_price = sl  # use SL price, not lowest
                results["losses"] += 1
        else:
            # SHORT/SELL: price DOWN = TP (tp < entry), price UP = SL (sl > entry)
            if current_price <= tp:
                status = "WIN"
                exit_reason = f"TP hit at ${current_price:,.6f} (target was ${tp:,.6f})"
                exit_price = current_price
                results["wins"] += 1
            elif current_price >= sl:
                # Price at or above stop — genuine SL hit for shorts
                status = "LOSS"
                exit_price = sl  # book at SL price for realistic PnL
                exit_reason = f"SL hit at ${exit_price:,.6f} (stop was ${sl:,.6f}, live=${current_price:,.6f})"
                results["losses"] += 1
            elif lowest <= tp:
                status = "WIN"
                exit_reason = f"TP was touched (lowest=${lowest:,.6f}, target=${tp:,.6f})"
                exit_price = tp
                results["wins"] += 1
            elif highest >= sl:
                status = "LOSS"
                exit_reason = f"SL was touched (highest=${highest:,.6f}, stop=${sl:,.6f})"
                exit_price = sl  # use SL price, not highest
                results["losses"] += 1

        if status == "OPEN":
            # Time-based expiry: close positions that have been open too long
            # This prevents infinite open positions and generates closed trade data faster
            try:
                entry_time = datetime.fromisoformat(sig["entry_time"].replace("Z", "+00:00"))
                hold_days = (datetime.now(timezone.utc) - entry_time).days
            except (ValueError, TypeError):
                hold_days = 0

            asset_class = sig.get("asset_class", "crypto")
            max_hold = {
                "crypto": MAX_HOLD_DAYS_CRYPTO,
                "forex": MAX_HOLD_DAYS_FOREX,
            }.get(asset_class, MAX_HOLD_DAYS_DEFAULT)

            if hold_days >= max_hold:
                # EXPIRED: close at current price with actual P&L
                exit_price = current_price
                if pnl_pct >= 0:
                    status = "WIN"
                    exit_reason = (f"EXPIRED after {hold_days}d (max {max_hold}d) "
                                   f"at ${current_price:,.6f} P&L: {pnl_pct:+.2f}%")
                    results["wins"] += 1
                else:
                    status = "LOSS"
                    exit_reason = (f"EXPIRED after {hold_days}d (max {max_hold}d) "
                                   f"at ${current_price:,.6f} P&L: {pnl_pct:+.2f}%")
                    results["losses"] += 1
            else:
                results["open"] += 1

        # Recompute pnl_pct using exit_price for closed trades (not current_price)
        if status != "OPEN" and exit_price is not None and entry_price > 0:
            if is_long:
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        # Update the signal
        update_fields = {
            "current_price": current_price,
            "highest_price": highest,
            "lowest_price": lowest,
            "pnl_pct": round(pnl_pct, 4),
            "last_checked": now,
            "checks_count": checks,
            "status": status,
        }
        if status != "OPEN":
            update_fields["exit_price"] = exit_price
            update_fields["exit_time"] = now
            update_fields["exit_reason"] = exit_reason

        set_clause = ", ".join(f"{k} = ?" for k in update_fields)
        values = list(update_fields.values()) + [sig["signal_id"]]
        cursor.execute(f"UPDATE tracked_signals SET {set_clause} WHERE signal_id = ?", values)

        results["checked"] += 1

    conn.commit()
    return results


# ===========================================================================
# REPORT: Print scoreboard
# ===========================================================================

def print_scoreboard(conn):
    """Print full tracking scoreboard."""
    cursor = conn.cursor()
    now = datetime.now(timezone.utc)

    # Get all signals
    cursor.execute("""
        SELECT * FROM tracked_signals
        ORDER BY
            CASE status WHEN 'WIN' THEN 1 WHEN 'LOSS' THEN 2 ELSE 3 END,
            confidence DESC
    """)
    columns = [desc[0] for desc in cursor.description]
    all_signals = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if not all_signals:
        print("  No tracked signals")
        return

    # Stats
    wins = [s for s in all_signals if s["status"] == "WIN"]
    losses = [s for s in all_signals if s["status"] == "LOSS"]
    opens = [s for s in all_signals if s["status"] == "OPEN"]

    total_closed = len(wins) + len(losses)
    win_rate = (len(wins) / total_closed * 100) if total_closed > 0 else 0

    # Calculate average P&L
    closed_pnls = [s["pnl_pct"] for s in wins + losses if s["pnl_pct"] is not None]
    avg_pnl = np.mean(closed_pnls) if closed_pnls else 0
    total_pnl = sum(closed_pnls) if closed_pnls else 0

    print("\n" + "=" * 80)
    print("ANTIGRAVITY SIGNAL TRACKER ? SCOREBOARD")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)

    print(f"\n  TOTAL: {len(all_signals)} signals tracked")
    print(f"  WINS:  {len(wins)} ({win_rate:.0f}% win rate)")
    print(f"  LOSS:  {len(losses)}")
    print(f"  OPEN:  {len(opens)}")
    if closed_pnls:
        print(f"  AVG P&L: {avg_pnl:+.2f}%")
        print(f"  TOTAL P&L: {total_pnl:+.2f}%")

    # Closed signals
    if wins or losses:
        print(f"\n{'-' * 80}")
        print("  CLOSED SIGNALS:")
        print(f"{'-' * 80}")
        for s in wins + losses:
            icon = "WIN " if s["status"] == "WIN" else "LOSS"
            pnl = s["pnl_pct"] or 0
            entry_t = s["entry_time"][:16] if s["entry_time"] else "?"
            exit_t = s["exit_time"][:16] if s["exit_time"] else "?"
            print(f"  [{icon}] {s['symbol']:15s} "
                  f"Entry: ${s['entry_price']:>12,.6f}  "
                  f"Exit: ${(s['exit_price'] or 0):>12,.6f}  "
                  f"P&L: {pnl:+.2f}%  "
                  f"({entry_t} -> {exit_t})")
            if s.get("exit_reason"):
                print(f"         {s['exit_reason']}")

    # Open signals
    if opens:
        print(f"\n{'-' * 80}")
        print("  OPEN SIGNALS:")
        print(f"{'-' * 80}")
        for s in opens:
            pnl = s["pnl_pct"] or 0
            entry = s["entry_price"]
            current = s["current_price"] or entry
            tp = s["take_profit"]
            sl = s["stop_loss"]

            # Progress toward TP/SL
            tp_dist = ((tp - current) / (tp - entry)) * 100 if (tp - entry) != 0 else 0
            sl_dist = ((current - sl) / (entry - sl)) * 100 if (entry - sl) != 0 else 0

            if pnl > 0:
                bar = "+" * min(int(pnl), 20)
                status_icon = "UP "
            elif pnl < 0:
                bar = "-" * min(int(abs(pnl)), 20)
                status_icon = "DN "
            else:
                bar = "~"
                status_icon = "..."

            conf = s["confidence"] or 0
            checks = s["checks_count"] or 0
            highest = s["highest_price"] or entry
            lowest = s["lowest_price"] or entry

            print(f"\n  {status_icon} {s['symbol']:15s}  [{s['signal_type']}]  Conf: {conf}%")
            print(f"      Entry:   ${entry:>12,.6f}")
            print(f"      Current: ${current:>12,.6f}  P&L: {pnl:+.2f}%  [{bar}]")
            print(f"      TP:      ${tp:>12,.6f}  ({((tp-entry)/entry)*100:+.1f}% from entry)")
            print(f"      SL:      ${sl:>12,.6f}  ({((sl-entry)/entry)*100:+.1f}% from entry)")
            print(f"      High:    ${highest:>12,.6f}  Low: ${lowest:>12,.6f}")
            print(f"      Checks: {checks}  |  Distance to TP: {100-tp_dist:.0f}%  |  Buffer to SL: {sl_dist:.0f}%")

    print(f"\n{'=' * 80}")
    return all_signals


def save_tracking_json(conn):
    """Save tracking results to JSON for dashboard consumption."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tracked_signals ORDER BY confidence DESC")
    columns = [desc[0] for desc in cursor.description]
    all_signals = [dict(zip(columns, row)) for row in cursor.fetchall()]

    wins = [s for s in all_signals if s["status"] == "WIN"]
    losses = [s for s in all_signals if s["status"] == "LOSS"]
    opens = [s for s in all_signals if s["status"] == "OPEN"]
    total_closed = len(wins) + len(losses)

    # Parse reasons and market_context_at_entry back from JSON strings
    for s in all_signals:
        if isinstance(s.get("reasons"), str):
            try:
                s["reasons"] = json.loads(s["reasons"])
            except Exception:
                s["reasons"] = [s["reasons"]]
        if isinstance(s.get("market_context_at_entry"), str):
            try:
                s["market_context_at_entry"] = json.loads(s["market_context_at_entry"])
            except Exception:
                s["market_context_at_entry"] = None

    output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_signals": len(all_signals),
            "wins": len(wins),
            "losses": len(losses),
            "open": len(opens),
            "win_rate": round(len(wins) / total_closed * 100, 1) if total_closed > 0 else 0,
            "avg_pnl": round(
                np.mean([s["pnl_pct"] for s in wins + losses if s["pnl_pct"]])
                if wins + losses else 0, 2
            ),
            "total_pnl": round(
                sum(s["pnl_pct"] for s in wins + losses if s["pnl_pct"])
                if wins + losses else 0, 2
            ),
        },
        "by_asset_class": {},
        "signals": all_signals,
    }

    # Group by asset class
    for ac in ["crypto", "forex"]:
        ac_sigs = [s for s in all_signals if s["asset_class"] == ac]
        ac_wins = [s for s in ac_sigs if s["status"] == "WIN"]
        ac_losses = [s for s in ac_sigs if s["status"] == "LOSS"]
        ac_closed = len(ac_wins) + len(ac_losses)
        output["by_asset_class"][ac] = {
            "total": len(ac_sigs),
            "wins": len(ac_wins),
            "losses": len(ac_losses),
            "open": len([s for s in ac_sigs if s["status"] == "OPEN"]),
            "win_rate": round(len(ac_wins) / ac_closed * 100, 1) if ac_closed > 0 else 0,
        }

    DATA_DIR.mkdir(exist_ok=True)
    with open(TRACKING_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    # Also write closed_picks.json in flat format for FC-PRO aggregator
    # Status normalisation map: internal WIN/LOSS → canonical WON/LOST used by
    # meta_consensus_scorer, audit_trail and other downstream consumers.
    _STATUS_MAP = {"WIN": "WON", "LOSS": "LOST", "WON": "WON", "LOST": "LOST"}

    closed_picks = []
    for s in all_signals:
        if s["status"] in ("WIN", "LOSS", "WON", "LOST"):
            # Compute PnL from entry/exit if pnl_pct is missing or zero
            stored_pnl = s.get("pnl_pct", 0) or 0
            if stored_pnl == 0 and s.get("entry_price") and s.get("exit_price"):
                ep = float(s["entry_price"])
                xp = float(s["exit_price"])
                direction = (s.get("direction") or s.get("signal_type") or "BUY").upper()
                if ep > 0:
                    if direction in ("BUY", "LONG"):
                        stored_pnl = round(((xp - ep) / ep) * 100, 4)
                    else:
                        stored_pnl = round(((ep - xp) / ep) * 100, 4)

            # Re-classify status using PnL when SL_BUFFER caused a false LOSS
            # (price was within the 0.5% buffer above SL but exit PnL was positive)
            raw_status = s["status"]
            if raw_status in ("WIN", "WON"):
                norm_status = "WON"
            elif raw_status in ("LOSS", "LOST"):
                # If actual realised PnL is positive the trade was profitable despite
                # the SL-buffer early trigger — promote to WON so WR is accurate.
                if stored_pnl > 0:
                    norm_status = "WON"
                else:
                    norm_status = "LOST"
            else:
                norm_status = _STATUS_MAP.get(raw_status, raw_status)

            closed_picks.append({
                "symbol": s.get("symbol", ""),
                "direction": s.get("direction", "BUY"),
                "entry_price": s.get("entry_price", 0),
                "exit_price": s.get("exit_price", 0),
                "take_profit": s.get("tp", 0),
                "stop_loss": s.get("sl", 0),
                "status": norm_status,  # WON/LOST — canonical form for all consumers
                "realized_pnl_pct": stored_pnl,
                "pnl_pct": stored_pnl,  # alias for consumers expecting pnl_pct
                "exit_reason": s.get("exit_reason", ""),
                "algorithm": s.get("algorithm", s.get("strategy", "unknown")),
                "entry_time": s.get("entry_time", ""),
                "exit_time": s.get("exit_time", ""),
                "asset_class": s.get("asset_class", "crypto"),
                "market_context_at_entry": s.get("market_context_at_entry"),
            })
    closed_path = DATA_DIR / "closed_picks.json"
    with open(closed_path, "w", encoding="utf-8") as f:
        json.dump(closed_picks, f, indent=2, default=str)

    return output


# ===========================================================================
# MAIN
# ===========================================================================

def run_check():
    """Single pass: record, fetch prices, validate, report."""
    print("\n" + "=" * 80)
    print("ANTIGRAVITY SIGNAL TRACKER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)

    conn = init_db()

    # 0. Restore state from JSON (DB doesn't persist in git)
    print("\n0. Restoring state from signal_tracking.json...")
    restored = restore_from_json(conn)
    print(f"   {restored} signals restored from JSON")

    # 1. Record any new signals
    print("\n1. Recording signals from live_signals_now.json...")
    new_count = record_signals(conn)
    print(f"   {new_count} new signals recorded")

    # 2. Fetch current prices
    print("\n2. Fetching current prices (Binance + yfinance)...")
    prices = fetch_current_prices(conn)
    print(f"   Got prices for {len(prices)} symbols")

    # 3. Validate TP/SL
    print("\n3. Validating signals against current prices...")
    results = validate_signals(conn, prices)
    print(f"   Checked: {results['checked']}  |  "
          f"Wins: {results['wins']}  |  "
          f"Losses: {results['losses']}  |  "
          f"Open: {results['open']}")

    # 4. Print scoreboard
    print_scoreboard(conn)

    # 5. Save to JSON
    output = save_tracking_json(conn)
    print(f"\nResults saved to {TRACKING_OUTPUT}")
    print(f"Database: {DB_PATH}")

    conn.close()
    return output


def main():
    parser = argparse.ArgumentParser(description="ANTIGRAVITY Signal Tracker")
    parser.add_argument("--loop", type=int, default=0,
                        help="Continuous mode: check every N seconds (0 = one-shot)")
    args = parser.parse_args()

    if args.loop > 0:
        print(f"Continuous tracking mode: checking every {args.loop}s")
        print("Press Ctrl+C to stop\n")
        while True:
            try:
                run_check()
                print(f"\nNext check in {args.loop}s...")
                time.sleep(args.loop)
            except KeyboardInterrupt:
                print("\nStopped by user")
                break
    else:
        run_check()

    return 0


if __name__ == "__main__":
    sys.exit(main())
