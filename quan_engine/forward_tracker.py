"""
ForwardTracker — SQLite Persistence + Binance Price Validation
===============================================================
Tracks every signal: entry, TP/SL levels, actual outcome, hold time.
Auto-validates against Binance spot prices.
"""
import os
import sys
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import urllib.request

from quan_engine import config

logger = logging.getLogger("QuanEngine.ForwardTracker")


def _init_db(db_path: str) -> sqlite3.Connection:
    """Create tables if they don't exist."""
    if db_path != ":memory:":
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            mode TEXT NOT NULL,
            entry_price REAL NOT NULL,
            take_profit REAL NOT NULL,
            stop_loss REAL NOT NULL,
            trailing_stop REAL,
            confidence REAL,
            consensus_pct REAL,
            strategies_agreed TEXT,
            position_size REAL,
            max_hold_bars INTEGER,
            status TEXT DEFAULT 'ACTIVE',
            entry_time TEXT NOT NULL,
            exit_time TEXT,
            exit_price REAL,
            exit_reason TEXT,
            pnl_pct REAL,
            hold_bars INTEGER,
            health_at_entry TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            computed_at TEXT NOT NULL,
            total_trades INTEGER,
            active_trades INTEGER,
            win_rate REAL,
            avg_pnl REAL,
            total_pnl REAL,
            sharpe REAL,
            profit_factor REAL,
            max_drawdown REAL,
            avg_hold_bars REAL,
            by_mode TEXT,
            by_strategy TEXT
        )
    """)
    conn.commit()
    return conn


def get_binance_price(symbol: str) -> Optional[float]:
    """Fetch current spot price with multi-tier failover."""
    from quan_engine.failover_system import fetch_price_with_failover
    return fetch_price_with_failover(symbol)


class ForwardTracker:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        self.conn = _init_db(self.db_path)

    def record_signal(self, setup, position_size: float, health: str = "SAFE") -> int:
        """Record a new active signal. Returns the signal ID."""
        cursor = self.conn.execute("""
            INSERT INTO signals (symbol, direction, mode, entry_price, take_profit,
                stop_loss, trailing_stop, confidence, consensus_pct, strategies_agreed,
                position_size, max_hold_bars, status, entry_time, health_at_entry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
        """, (
            setup.symbol, setup.direction, setup.mode,
            setup.entry_price, setup.take_profit, setup.stop_loss,
            setup.trailing_stop, setup.confidence, setup.consensus_pct,
            json.dumps(setup.strategies_agreed),
            position_size, setup.max_hold_bars,
            datetime.utcnow().isoformat(), health,
        ))
        self.conn.commit()
        signal_id = cursor.lastrowid
        logger.info(f"Recorded signal #{signal_id}: {setup.symbol} {setup.direction} @ {setup.entry_price}")
        return signal_id

    def validate_active_signals(self) -> List[dict]:
        """Check all active signals against current Binance prices.

        Works even when DB was just restored from git (re-reads from disk).
        Closes trades that hit TP/SL/TIME_EXIT and syncs results to JSON.
        """
        # Re-open connection to pick up DB restored from git
        try:
            self.conn.close()
        except Exception:
            pass
        self.conn = _init_db(self.db_path)

        cursor = self.conn.execute(
            "SELECT * FROM signals WHERE status = 'ACTIVE'"
        )
        columns = [desc[0] for desc in cursor.description]
        active = [dict(zip(columns, row)) for row in cursor.fetchall()]

        if not active:
            logger.info("No active signals in DB to validate")
            return []

        logger.info(f"Validating {len(active)} active signals against live prices")

        results = []
        price_cache: Dict[str, Optional[float]] = {}
        for sig in active:
            symbol = sig["symbol"]
            if symbol not in price_cache:
                price_cache[symbol] = get_binance_price(symbol)
                if price_cache[symbol] is None:
                    logger.warning(f"Could not fetch price for {symbol}, skipping validation")

            price = price_cache[symbol]
            if price is None:
                continue

            result = self._check_exit(sig, price)
            if result:
                results.append(result)

        # If any trades were closed, immediately sync to JSON so the
        # dashboard and next run see updated outcomes
        if results:
            logger.info(f"Closed {len(results)} signals, syncing to JSON")
            self.export_active_json()

        return results

    def _check_exit(self, sig: dict, current_price: float) -> Optional[dict]:
        """Check if a signal should be exited."""
        direction = sig["direction"]
        tp = sig["take_profit"]
        sl = sig["stop_loss"]
        entry_price = sig["entry_price"]
        entry_time = datetime.fromisoformat(sig["entry_time"])
        bars_elapsed = int((datetime.utcnow() - entry_time).total_seconds() / 3600)  # Approx hourly bars

        exit_reason = None
        exit_price = current_price

        if direction == "BUY":
            if current_price >= tp:
                exit_reason = "TP"
                exit_price = tp
            elif current_price <= sl:
                exit_reason = "SL"
                exit_price = sl
        else:  # SELL
            if current_price <= tp:
                exit_reason = "TP"
                exit_price = tp
            elif current_price >= sl:
                exit_reason = "SL"
                exit_price = sl

        # Time exit
        if not exit_reason and bars_elapsed >= sig["max_hold_bars"]:
            exit_reason = "TIME_EXIT"
            exit_price = current_price

        if exit_reason:
            # Calculate P&L
            if direction == "BUY":
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100

            pnl_pct -= config.ROUND_TRIP_COST_PCT * 100

            self.conn.execute("""
                UPDATE signals SET status = 'CLOSED', exit_time = ?, exit_price = ?,
                    exit_reason = ?, pnl_pct = ?, hold_bars = ?
                WHERE id = ?
            """, (
                datetime.utcnow().isoformat(), round(exit_price, 8),
                exit_reason, round(pnl_pct, 4), bars_elapsed, sig["id"],
            ))
            self.conn.commit()

            logger.info(
                f"Closed signal #{sig['id']}: {sig['symbol']} {exit_reason} "
                f"P&L={pnl_pct:+.2f}%"
            )

            return {
                "id": sig["id"],
                "symbol": sig["symbol"],
                "direction": direction,
                "exit_reason": exit_reason,
                "pnl_pct": round(pnl_pct, 4),
                "hold_bars": bars_elapsed,
            }

        return None

    def get_active_signals(self) -> List[dict]:
        """Get all active signals as dicts."""
        cursor = self.conn.execute(
            "SELECT * FROM signals WHERE status = 'ACTIVE' ORDER BY entry_time DESC"
        )
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_closed_signals(self, limit: int = 100) -> List[dict]:
        """Get recent closed signals."""
        cursor = self.conn.execute(
            "SELECT * FROM signals WHERE status = 'CLOSED' ORDER BY exit_time DESC LIMIT ?",
            (limit,)
        )
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def compute_performance(self) -> dict:
        """Compute aggregate performance metrics and save to DB."""
        closed = self.get_closed_signals(limit=10000)
        active = self.get_active_signals()

        if not closed:
            return {"total_trades": 0, "active_trades": len(active)}

        pnls = [t["pnl_pct"] for t in closed]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        import numpy as np
        win_rate = len(wins) / len(pnls) if pnls else 0
        avg_pnl = np.mean(pnls)
        total_pnl = sum(pnls)
        std_pnl = np.std(pnls) if len(pnls) > 1 else 1
        sharpe = (avg_pnl / std_pnl * np.sqrt(252)) if std_pnl > 0 else 0

        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0.001
        profit_factor = gross_profit / gross_loss

        cumulative = np.cumsum(pnls)
        peak = np.maximum.accumulate(cumulative)
        max_dd = abs(np.min(cumulative - peak)) if len(cumulative) > 0 else 0

        avg_hold = np.mean([t.get("hold_bars", 0) for t in closed])

        # By mode
        by_mode = {}
        for t in closed:
            m = t.get("mode", "UNKNOWN")
            if m not in by_mode:
                by_mode[m] = {"trades": 0, "wins": 0, "total_pnl": 0}
            by_mode[m]["trades"] += 1
            if t["pnl_pct"] > 0:
                by_mode[m]["wins"] += 1
            by_mode[m]["total_pnl"] += t["pnl_pct"]

        for m in by_mode:
            by_mode[m]["win_rate"] = round(
                by_mode[m]["wins"] / by_mode[m]["trades"], 4
            ) if by_mode[m]["trades"] > 0 else 0

        perf = {
            "total_trades": len(closed),
            "active_trades": len(active),
            "win_rate": round(win_rate, 4),
            "avg_pnl": round(avg_pnl, 4),
            "total_pnl": round(total_pnl, 4),
            "sharpe": round(sharpe, 4),
            "profit_factor": round(profit_factor, 4),
            "max_drawdown": round(max_dd, 4),
            "avg_hold_bars": round(avg_hold, 1),
            "by_mode": by_mode,
        }

        # Save to DB
        self.conn.execute("""
            INSERT INTO performance (computed_at, total_trades, active_trades,
                win_rate, avg_pnl, total_pnl, sharpe, profit_factor,
                max_drawdown, avg_hold_bars, by_mode, by_strategy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            perf["total_trades"], perf["active_trades"],
            perf["win_rate"], perf["avg_pnl"], perf["total_pnl"],
            perf["sharpe"], perf["profit_factor"],
            perf["max_drawdown"], perf["avg_hold_bars"],
            json.dumps(by_mode), "{}",
        ))
        self.conn.commit()

        return perf

    def export_active_json(self, output_path: str = None) -> str:
        """Export active signals to JSON for the dashboard."""
        if output_path is None:
            output_path = config.SIGNALS_PATH
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        active = self.get_active_signals()
        closed = self.get_closed_signals(limit=10000)
        perf = self.compute_performance()

        # Generate EST timestamp
        from datetime import timezone, timedelta as td
        utc_now = datetime.now(timezone.utc)
        est_offset = timezone(td(hours=-5))
        est_now = utc_now.astimezone(est_offset)
        try:
            est_readable = est_now.strftime("%b %-d, %-I:%M %p EST")
        except ValueError:
            est_readable = est_now.strftime("%b %d, %I:%M %p EST").replace(" 0", " ")

        # Add EST entry_time to each active pick
        for pick in active:
            if pick.get("entry_time"):
                try:
                    et = datetime.fromisoformat(pick["entry_time"]).replace(tzinfo=timezone.utc)
                    et_est = et.astimezone(est_offset)
                    try:
                        pick["entry_time_est"] = et_est.strftime("%b %-d, %-I:%M %p EST")
                    except ValueError:
                        pick["entry_time_est"] = et_est.strftime("%b %d, %I:%M %p EST").replace(" 0", " ")
                except Exception:
                    pick["entry_time_est"] = ""

        data = {
            "updated_at": datetime.utcnow().isoformat(),
            "updated_at_est": est_readable,
            "engine": "QuanEngine v1.0",
            "active_picks": active,
            "closed_picks": closed,
            "performance": perf,
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Exported {len(active)} active signals to {output_path}")
        return output_path

    def close(self):
        self.conn.close()
