#!/usr/bin/env python3
"""
Create v2 DB schema and seed from existing data.
"""
import sqlite3, json, os, sys
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'alpha_engine.db')
CLOSED_PICKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'alpha_engine', 'data', 'closed_picks.json')
SCHEMA_SQL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'alpha_engine', 'data', 'v2_schema.sql')

def create_schema(conn):
    """Create all v2 tables and indexes."""
    schema = """
    CREATE TABLE IF NOT EXISTS picks (
        pick_id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        asset_class TEXT NOT NULL DEFAULT 'EQUITY',
        direction TEXT NOT NULL DEFAULT 'LONG',
        entry_price REAL,
        exit_price REAL,
        entry_time TEXT NOT NULL,
        exit_time TEXT,
        stop_loss REAL,
        take_profit REAL,
        confidence REAL DEFAULT 0.5,
        status TEXT DEFAULT 'unresolved',
        pnl_pct REAL,
        resolved_at TEXT,
        outcome TEXT,
        metadata TEXT DEFAULT '{}',
        resolution_version TEXT,
        created_at TEXT,
        updated_at TEXT,
        source_system TEXT,
        strategy TEXT,
        _resolved_asset_class TEXT,
        _replay_bar_date TEXT,
        _resolve_retry_count INTEGER DEFAULT 0,
        _resolve_max_retries_hit INTEGER DEFAULT 0,
        _pnl_implausible INTEGER DEFAULT 0,
        _pnl_implausible_raw REAL,
        _pnl_implausible_cap REAL,
        _resolver_v2_no_touch INTEGER DEFAULT 0,
        _resolver_v2_no_ohlc INTEGER DEFAULT 0,
        _resolver_fallback INTEGER DEFAULT 0,
        _legacy_pnl_pct REAL,
        _legacy_exit_reason TEXT,
        _blacklist_reason TEXT,
        _time_exit_age_hours REAL,
        _resolve_retry_needed INTEGER DEFAULT 0,
        exit_reason TEXT
    );

    CREATE TABLE IF NOT EXISTS resolution_audit (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        pick_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        outcome TEXT,
        pnl_pct REAL,
        exit_price REAL,
        resolution_time_ms REAL,
        slippage_estimate REAL,
        market_impact_estimate REAL,
        error_message TEXT,
        resolver_version TEXT,
        resolved_at TEXT NOT NULL,
        FOREIGN KEY (pick_id) REFERENCES picks(pick_id)
    );

    CREATE TABLE IF NOT EXISTS strategies (
        strategy_id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_name TEXT NOT NULL,
        category TEXT,
        asset_class TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS strategy_performance (
        perf_id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id INTEGER NOT NULL,
        sharpe_30d REAL,
        sharpe_90d REAL,
        total_return REAL,
        max_drawdown REAL,
        n_trades INTEGER,
        win_rate REAL,
        computed_at TEXT,
        FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
    );

    CREATE INDEX IF NOT EXISTS idx_picks_symbol ON picks(symbol);
    CREATE INDEX IF NOT EXISTS idx_picks_status ON picks(status);
    CREATE INDEX IF NOT EXISTS idx_picks_entry_time ON picks(entry_time);
    CREATE INDEX IF NOT EXISTS idx_picks_asset_class ON picks(asset_class);
    CREATE INDEX IF NOT EXISTS idx_picks_source_system ON picks(source_system);
    CREATE INDEX IF NOT EXISTS idx_picks_strategy ON picks(strategy);
    CREATE INDEX IF NOT EXISTS idx_audit_pick_id ON resolution_audit(pick_id);
    CREATE INDEX IF NOT EXISTS idx_audit_resolved_at ON resolution_audit(resolved_at);
    CREATE INDEX IF NOT EXISTS idx_strategies_name ON strategies(strategy_name);
    CREATE INDEX IF NOT EXISTS idx_strategies_active ON strategies(is_active);
    CREATE INDEX IF NOT EXISTS idx_perf_strategy_id ON strategy_performance(strategy_id);
    CREATE INDEX IF NOT EXISTS idx_perf_computed_at ON strategy_performance(computed_at);
    """
    conn.executescript(schema)
    print(f"Schema created: picks, resolution_audit, strategies, strategy_performance + 11 indexes")

def seed_picks(conn, json_path):
    """Seed picks table from closed_picks.json."""
    if not os.path.exists(json_path):
        print(f"WARNING: {json_path} not found, skipping seed")
        return 0

    with open(json_path, 'r') as f:
        picks = json.load(f)

    if isinstance(picks, dict):
        picks = picks.get('picks', picks.get('data', []))

    inserted = 0
    for p in picks:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO picks
                (pick_id, symbol, asset_class, direction, entry_price, exit_price,
                 entry_time, exit_time, stop_loss, take_profit, confidence, status,
                 pnl_pct, resolved_at, outcome, metadata, resolution_version,
                 created_at, updated_at, source_system, strategy,
                 _resolved_asset_class, _replay_bar_date, _resolve_retry_count,
                 _resolve_max_retries_hit, _pnl_implausible, _pnl_implausible_raw,
                 _pnl_implausible_cap, _resolver_v2_no_touch, _resolver_v2_no_ohlc,
                 _resolver_fallback, _legacy_pnl_pct, _legacy_exit_reason,
                 _blacklist_reason, _time_exit_age_hours, _resolve_retry_needed, exit_reason)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p.get('pick_id'), p.get('symbol', ''),
                p.get('asset_class', 'EQUITY'), p.get('direction', 'LONG'),
                p.get('entry_price'), p.get('exit_price'),
                p.get('entry_time'), p.get('exit_time'),
                p.get('stop_loss'), p.get('take_profit'),
                p.get('confidence', 0.5), p.get('status', 'unresolved'),
                p.get('pnl_pct'), p.get('resolved_at'),
                p.get('outcome'), json.dumps(p.get('metadata', {})),
                p.get('resolution_version'), p.get('created_at'),
                p.get('updated_at'), p.get('source_system'), p.get('strategy'),
                p.get('_resolved_asset_class'), p.get('_replay_bar_date'),
                p.get('_resolve_retry_count', 0),
                p.get('_resolve_max_retries_hit', 0),
                p.get('_pnl_implausible', 0), p.get('_pnl_implausible_raw'),
                p.get('_pnl_implausible_cap'), p.get('_resolver_v2_no_touch', 0),
                p.get('_resolver_v2_no_ohlc', 0), p.get('_resolver_fallback', 0),
                p.get('_legacy_pnl_pct'), p.get('_legacy_exit_reason'),
                p.get('_blacklist_reason'), p.get('_time_exit_age_hours'),
                p.get('_resolve_retry_needed', 0), p.get('exit_reason')
            ))
            inserted += 1
            if inserted % 1000 == 0:
                print(f"  Seeded {inserted} picks...")
        except Exception as e:
            pass  # Skip malformed rows

    conn.commit()
    print(f"Seeded {inserted} picks into DB")
    return inserted

def verify(conn):
    """Verify schema and counts."""
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"\nTables: {[t[0] for t in tables]}")
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
        print(f"  {t[0]}: {count} rows")

def main():
    print(f"DB path: {DB_PATH}")
    print(f"Picks source: {CLOSED_PICKS}")

    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    seed_picks(conn, CLOSED_PICKS)
    verify(conn)
    conn.close()
    print("\nDone!")

if __name__ == '__main__':
    main()