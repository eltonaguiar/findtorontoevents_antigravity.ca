"""SQLite persistence: ratios, signals, paper portfolio, snapshots."""
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from . import config

logger = logging.getLogger(__name__)


def _connect():
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create all tables."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ratios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                symbol TEXT NOT NULL,
                source TEXT NOT NULL,
                global_ratio REAL,
                top_trader_account_ratio REAL,
                top_trader_position_ratio REAL,
                taker_ratio REAL,
                funding_rate REAL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(ts, symbol)
            );

            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                strategy TEXT NOT NULL,
                confidence REAL,
                entry_price REAL,
                take_profit REAL,
                stop_loss REAL,
                ratios_snapshot TEXT,
                reason TEXT,
                generated_at TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE'
            );

            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                take_profit REAL NOT NULL,
                stop_loss REAL NOT NULL,
                quantity REAL NOT NULL,
                risk_amount REAL NOT NULL,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                exit_price REAL,
                exit_reason TEXT,
                pnl_dollar REAL,
                pnl_pct REAL,
                status TEXT DEFAULT 'OPEN'
            );

            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                equity REAL NOT NULL,
                open_positions INTEGER,
                total_trades INTEGER,
                wins INTEGER,
                losses INTEGER,
                win_rate REAL,
                total_pnl REAL,
                max_drawdown REAL
            );

            CREATE INDEX IF NOT EXISTS idx_ratios_symbol_ts
                ON ratios(symbol, ts);
            CREATE INDEX IF NOT EXISTS idx_positions_status
                ON positions(status);
        """)
    logger.info("Initialized coinglass DB at %s", config.DB_PATH)


def store_ratios(symbol: str, data: Dict, funding_rate: float = None):
    """Store fetched ratio data."""
    ts = data.get("fetched_at") or datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO ratios
            (ts, symbol, source, global_ratio, top_trader_account_ratio,
             top_trader_position_ratio, taker_ratio, funding_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ts, symbol, data.get("source") or "unknown",
              data.get("global"), data.get("top_trader_account"),
              data.get("top_trader_position"), data.get("taker"),
              funding_rate))


def get_recent_ratios(symbol: str, window_minutes: int = 1440) -> List[Dict]:
    """Return ratio rows within window, ordered ascending."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "SELECT * FROM ratios WHERE symbol = ? AND ts >= ? ORDER BY ts ASC",
            (symbol, cutoff))
        return [dict(row) for row in cur.fetchall()]


def store_signal(signal: Dict):
    """Persist a generated signal."""
    with _connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO signals
            (signal_id, symbol, direction, strategy, confidence,
             entry_price, take_profit, stop_loss, ratios_snapshot,
             reason, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (signal["signal_id"], signal["symbol"], signal["direction"],
              signal["strategy"], signal["confidence"],
              signal.get("entry_price"), signal.get("take_profit"),
              signal.get("stop_loss"),
              json.dumps(signal.get("ratios", {})),
              signal.get("reason", ""),
              signal.get("generated_at")))


def open_position(signal: Dict, quantity: float, risk_amount: float):
    """Open a paper trading position."""
    with _connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO positions
            (signal_id, symbol, direction, entry_price, take_profit,
             stop_loss, quantity, risk_amount, opened_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (signal["signal_id"], signal["symbol"], signal["direction"],
              signal["entry_price"], signal["take_profit"],
              signal["stop_loss"], quantity, risk_amount,
              signal["generated_at"]))


def close_position(signal_id: str, exit_price: float, exit_reason: str):
    """Close a paper position with P&L calculation."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM positions WHERE signal_id = ? AND status = 'OPEN'",
            (signal_id,)).fetchone()
        if not row:
            return
        entry = row["entry_price"]
        direction = row["direction"]
        qty = row["quantity"]
        if direction == "LONG":
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100
        pnl_dollar = qty * (pnl_pct / 100)
        conn.execute("""
            UPDATE positions SET status='CLOSED', closed_at=?,
            exit_price=?, exit_reason=?, pnl_pct=?, pnl_dollar=?
            WHERE signal_id=? AND status='OPEN'
        """, (datetime.now(timezone.utc).isoformat(), exit_price,
              exit_reason, round(pnl_pct, 4), round(pnl_dollar, 2),
              signal_id))


def get_open_positions() -> List[Dict]:
    """Return all open positions."""
    with _connect() as conn:
        cur = conn.execute("SELECT * FROM positions WHERE status = 'OPEN'")
        return [dict(row) for row in cur.fetchall()]


def get_closed_positions(limit: int = 100) -> List[Dict]:
    """Return recent closed positions."""
    with _connect() as conn:
        cur = conn.execute(
            "SELECT * FROM positions WHERE status='CLOSED' ORDER BY closed_at DESC LIMIT ?",
            (limit,))
        return [dict(row) for row in cur.fetchall()]


def get_portfolio_equity() -> float:
    """Compute current equity = starting capital + closed P&L.

    Note: unrealized P&L from open positions is not included here because
    we'd need real-time prices. The portfolio summary function in
    paper_portfolio.py handles that separately when prices are available.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(pnl_dollar), 0) as total FROM positions WHERE status='CLOSED'"
        ).fetchone()
        return config.STARTING_CAPITAL + (row["total"] if row else 0)


def save_snapshot():
    """Save a portfolio snapshot for the equity curve."""
    closed = get_closed_positions(limit=9999)
    wins = sum(1 for p in closed if (p.get("pnl_pct") or 0) > 0)
    losses = sum(1 for p in closed if (p.get("pnl_pct") or 0) <= 0)
    total = wins + losses
    equity = get_portfolio_equity()
    open_pos = len(get_open_positions())
    total_pnl = sum(float(p.get("pnl_dollar", 0) or 0) for p in closed)
    with _connect() as conn:
        conn.execute("""
            INSERT INTO portfolio_snapshots
            (ts, equity, open_positions, total_trades, wins, losses,
             win_rate, total_pnl, max_drawdown)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now(timezone.utc).isoformat(), equity, open_pos,
              total, wins, losses,
              round(wins / total * 100, 2) if total else 0,
              round(total_pnl, 2), 0))


def get_strategy_stats(strategy: str = None) -> Dict[str, Dict]:
    """Return win/loss/WR/PF stats per strategy (or one strategy if given)."""
    with _connect() as conn:
        query = """
            SELECT s.strategy,
                   COUNT(*) as total,
                   SUM(CASE WHEN p.pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN p.pnl_pct <= 0 THEN 1 ELSE 0 END) as losses,
                   ROUND(AVG(p.pnl_pct), 2) as avg_pnl,
                   ROUND(SUM(CASE WHEN p.pnl_pct > 0 THEN p.pnl_pct ELSE 0 END), 2) as win_pnl,
                   ROUND(SUM(CASE WHEN p.pnl_pct < 0 THEN ABS(p.pnl_pct) ELSE 0 END), 2) as loss_pnl
            FROM positions p
            JOIN signals s ON p.signal_id = s.signal_id
            WHERE p.status = 'CLOSED'
        """
        params = ()
        if strategy:
            query += " AND s.strategy = ?"
            params = (strategy,)
        query += " GROUP BY s.strategy"
        rows = conn.execute(query, params).fetchall()
        result = {}
        for r in rows:
            total = r["total"]
            wins = r["wins"]
            wr = round(wins / total * 100, 1) if total else 0
            pf = round(r["win_pnl"] / r["loss_pnl"], 2) if r["loss_pnl"] > 0 else float("inf")
            result[r["strategy"]] = {
                "total": total, "wins": wins, "losses": r["losses"],
                "win_rate": wr, "avg_pnl": r["avg_pnl"],
                "profit_factor": pf if pf != float("inf") else "∞",
            }
        return result


def get_symbol_direction_stats(symbol: str, direction: str) -> Dict:
    """Return win/loss stats for a specific symbol+direction combo."""
    with _connect() as conn:
        row = conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN p.pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN p.pnl_pct <= 0 THEN 1 ELSE 0 END) as losses
            FROM positions p
            JOIN signals s ON p.signal_id = s.signal_id
            WHERE p.status = 'CLOSED' AND s.symbol = ? AND s.direction = ?
        """, (symbol, direction)).fetchone()
        if not row or row["total"] == 0:
            return {"total": 0, "wins": 0, "losses": 0}
        return {"total": row["total"], "wins": row["wins"], "losses": row["losses"]}


def prune_old(days: int = 60):
    """Delete ratio rows older than N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with _connect() as conn:
        conn.execute("DELETE FROM ratios WHERE ts < ?", (cutoff,))
