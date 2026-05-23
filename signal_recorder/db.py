"""SQLite database for the unified signal log."""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent / "data" / "signal_log.db"


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS signal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            system_id TEXT NOT NULL,
            signal TEXT NOT NULL,
            strength REAL DEFAULT 0.5,
            entry_price REAL,
            take_profit REAL,
            stop_loss REAL,
            price_at_signal REAL,
            extra_json TEXT,
            batch_id TEXT
        );
        CREATE TABLE IF NOT EXISTS signal_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_log_id INTEGER NOT NULL,
            check_minutes INTEGER NOT NULL,
            price_at_check REAL NOT NULL,
            pnl_pct REAL NOT NULL,
            FOREIGN KEY (signal_log_id) REFERENCES signal_log(id)
        );
        CREATE TABLE IF NOT EXISTS combo_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            combo_key TEXT NOT NULL,
            symbol TEXT,
            direction TEXT NOT NULL,
            window_minutes INTEGER NOT NULL,
            total_trades INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            win_rate REAL NOT NULL,
            avg_pnl_pct REAL NOT NULL,
            sharpe REAL,
            p_value REAL,
            last_updated TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sl_timestamp ON signal_log(timestamp);
        CREATE INDEX IF NOT EXISTS idx_sl_symbol ON signal_log(symbol);
        CREATE INDEX IF NOT EXISTS idx_sl_system ON signal_log(system_id);
        CREATE INDEX IF NOT EXISTS idx_sl_batch ON signal_log(batch_id);
        CREATE INDEX IF NOT EXISTS idx_so_signal ON signal_outcomes(signal_log_id);
        CREATE INDEX IF NOT EXISTS idx_cr_combo ON combo_results(combo_key);
    """)
    conn.commit()


def log_signal(conn: sqlite3.Connection, system_id: str, symbol: str,
               signal: str, strength: float, price_at_signal: float,
               entry_price: float = None, take_profit: float = None,
               stop_loss: float = None, extra: dict = None,
               batch_id: str = None) -> int:
    if batch_id:
        existing = conn.execute(
            "SELECT id FROM signal_log WHERE system_id=? AND symbol=? AND batch_id=?",
            (system_id, symbol, batch_id)
        ).fetchone()
        if existing:
            return existing["id"]
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute("""
        INSERT INTO signal_log
            (timestamp, symbol, system_id, signal, strength, entry_price,
             take_profit, stop_loss, price_at_signal, extra_json, batch_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (now, symbol, system_id, signal, strength, entry_price,
          take_profit, stop_loss, price_at_signal,
          json.dumps(extra) if extra else None, batch_id))
    conn.commit()
    return cur.lastrowid


def record_outcome(conn: sqlite3.Connection, signal_log_id: int,
                   check_minutes: int, price_at_check: float, pnl_pct: float) -> None:
    conn.execute("""
        INSERT INTO signal_outcomes (signal_log_id, check_minutes, price_at_check, pnl_pct)
        VALUES (?, ?, ?, ?)
    """, (signal_log_id, check_minutes, price_at_check, pnl_pct))
    conn.commit()


def get_signals_in_window(conn: sqlite3.Connection, symbol: str,
                          start: str, end: str) -> list[dict]:
    rows = conn.execute("""
        SELECT * FROM signal_log
        WHERE symbol = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    """, (symbol, start, end)).fetchall()
    return [dict(r) for r in rows]


def save_combo_result(conn: sqlite3.Connection, combo_key: str,
                      direction: str, window_minutes: int,
                      total: int, wins: int, losses: int,
                      win_rate: float, avg_pnl: float,
                      sharpe: float = None, p_value: float = None,
                      symbol: str = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO combo_results
            (combo_key, symbol, direction, window_minutes, total_trades,
             wins, losses, win_rate, avg_pnl_pct, sharpe, p_value, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (combo_key, symbol, direction, window_minutes, total, wins, losses,
          win_rate, avg_pnl, sharpe, p_value, now))
    conn.commit()
