"""SQLite persistence for paper trading portfolios."""
import sqlite3
import pathlib
from datetime import datetime, timezone

DB_PATH = pathlib.Path(__file__).parent / "data" / "paper.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS positions (
        id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL NOT NULL,
        current_price REAL NOT NULL,
        tp REAL NOT NULL,
        sl REAL NOT NULL,
        strategy TEXT NOT NULL,
        strategy_name TEXT NOT NULL,
        portfolio_type TEXT NOT NULL,
        conviction_tier TEXT NOT NULL,
        position_size_usd REAL NOT NULL,
        shares REAL NOT NULL,
        entry_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        exit_price REAL,
        exit_date TEXT,
        pnl_pct REAL DEFAULT 0.0,
        pnl_usd REAL DEFAULT 0.0,
        mfe REAL DEFAULT 0.0,
        mae REAL DEFAULT 0.0,
        confidence REAL DEFAULT 0.5,
        reason TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS portfolios (
        name TEXT PRIMARY KEY,
        portfolio_type TEXT NOT NULL,
        starting_capital REAL NOT NULL DEFAULT 10000.0,
        cash REAL NOT NULL DEFAULT 10000.0,
        equity REAL NOT NULL DEFAULT 10000.0,
        total_trades INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        peak_equity REAL DEFAULT 10000.0,
        max_drawdown_pct REAL DEFAULT 0.0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS equity_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_name TEXT NOT NULL,
        equity REAL NOT NULL,
        timestamp TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_pos_status ON positions(status);
    CREATE INDEX IF NOT EXISTS idx_pos_portfolio ON positions(portfolio_type);
    CREATE INDEX IF NOT EXISTS idx_snap_portfolio ON equity_snapshots(portfolio_name);
    """)
    conn.commit()


def init_portfolios(conn: sqlite3.Connection):
    """Initialize all 9 portfolios if they don't exist."""
    now = datetime.now(timezone.utc).isoformat()
    portfolios = [
        # By strategy type
        ("technical", "strategy_type"),
        ("sentiment", "strategy_type"),
        ("onchain", "strategy_type"),
        ("derivatives", "strategy_type"),
        ("smart_money", "strategy_type"),
        ("macro", "strategy_type"),
        # Correlation & Leap strategies — $1,000 each
        ("correlation", "strategy_type"),
        ("leap", "strategy_type"),
        # Verified strategies — $1,000 each (FundedRelay + researched)
        ("verified", "strategy_type"),
        # By conviction tier
        ("high_conviction", "conviction_tier"),
        ("medium_conviction", "conviction_tier"),
        ("speculative", "conviction_tier"),
    ]
    for name, ptype in portfolios:
        conn.execute("""
            INSERT OR IGNORE INTO portfolios (name, portfolio_type, created_at)
            VALUES (?, ?, ?)
        """, (name, ptype, now))
    conn.commit()
