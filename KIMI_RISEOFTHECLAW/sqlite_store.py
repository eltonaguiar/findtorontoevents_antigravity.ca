"""
sqlite_store.py -- KIMI Rise of the Claw v11.0
SQLite Persistence Layer

Provides queryable storage alongside JSON files for:
- ML feature extraction
- Historical signal querying
- Tournament snapshot tracking
- Market regime history

Database: data/kimi_trading.db
"""

import json
import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "kimi_trading.db"


def get_connection() -> sqlite3.Connection:
    """Get SQLite connection with WAL mode for concurrent access."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            algorithm TEXT NOT NULL,
            tier TEXT,
            strategy TEXT,
            symbol TEXT NOT NULL,
            signal TEXT NOT NULL,
            reason TEXT,
            price REAL,
            regime TEXT,
            crypto_regime TEXT,
            breadth_pct REAL,
            vix_proxy TEXT,
            hmm_confidence REAL
        );

        CREATE INDEX IF NOT EXISTS idx_signals_algo ON signals(algorithm);
        CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
        CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(timestamp);

        CREATE TABLE IF NOT EXISTS picks (
            id TEXT PRIMARY KEY,
            algorithm TEXT NOT NULL,
            symbol TEXT NOT NULL,
            category TEXT,
            tier TEXT,
            entry_price REAL,
            entry_date TEXT,
            exit_price REAL,
            exit_date TEXT,
            exit_reason TEXT,
            pnl_pct REAL,
            pnl_dollar REAL,
            status TEXT,
            reason TEXT,
            regime TEXT,
            regime_confidence REAL,
            breadth_pct REAL,
            vol_20d REAL,
            rsi_at_entry REAL,
            volume_ratio REAL,
            ml_win_prob REAL
        );

        CREATE INDEX IF NOT EXISTS idx_picks_algo ON picks(algorithm);
        CREATE INDEX IF NOT EXISTS idx_picks_status ON picks(status);
        CREATE INDEX IF NOT EXISTS idx_picks_symbol ON picks(symbol);

        CREATE TABLE IF NOT EXISTS rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL,
            algorithm TEXT NOT NULL,
            score REAL,
            league TEXT,
            total_return REAL,
            sharpe REAL,
            sortino REAL,
            win_rate REAL,
            max_drawdown REAL,
            closed_picks INTEGER,
            regime TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_rankings_algo ON rankings(algorithm);
        CREATE INDEX IF NOT EXISTS idx_rankings_date ON rankings(snapshot_date);

        CREATE TABLE IF NOT EXISTS regime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            regime TEXT,
            crypto_regime TEXT,
            vix_proxy TEXT,
            hmm_regime TEXT,
            hmm_confidence REAL,
            vol_20d REAL,
            btc_eth_ratio REAL,
            spy_vs_sma200 REAL
        );
""")
    conn.commit()
    conn.close()
    logger.info(f"SQLite DB initialized at {DB_PATH}")


class SQLiteStore:
    """Main interface for KIMI trading database."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        initialize_db()

    def write_signal(self, entry: dict):
        """Write a single audit signal entry."""
        conn = get_connection()
        try:
            conn.execute("""
                INSERT OR IGNORE INTO signals
                (timestamp, algorithm, tier, strategy, symbol, signal, reason, price,
                 regime, crypto_regime, breadth_pct, vix_proxy, hmm_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
                entry.get("timestamp", ""),
                entry.get("algorithm", ""),
                entry.get("tier"),
                entry.get("strategy"),
                entry.get("symbol", ""),
                entry.get("signal", "BUY"),
                entry.get("reason"),
                entry.get("price"),
                entry.get("regime"),
                entry.get("crypto_regime"),
                entry.get("breadth_pct"),
                entry.get("vix_proxy"),
                entry.get("hmm_confidence"),
            ))
            conn.commit()
        except Exception as e:
            logger.warning(f"write_signal failed: {e}")
        finally:
            conn.close()

    def write_pick(self, pick: dict):
        """Write or update a pick (open or closed)."""
        _a = pick.get("algorithm", "?")
        _s = pick.get("symbol", "?")
        _d = pick.get("entry_date", "?")
        pick_id = pick.get("id") or (_a + "_" + _s + "_" + _d)
        conn = get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO picks
                (id, algorithm, symbol, category, tier, entry_price, entry_date,
                 exit_price, exit_date, exit_reason, pnl_pct, pnl_dollar, status,
                 reason, regime, regime_confidence, breadth_pct, vol_20d,
                 rsi_at_entry, volume_ratio, ml_win_prob)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
                pick_id,
                pick.get("algorithm", ""),
                pick.get("symbol", ""),
                pick.get("category"),
                pick.get("tier"),
                pick.get("entryPrice") or pick.get("entry_price"),
                pick.get("entryDate") or pick.get("entry_date"),
                pick.get("exitPrice") or pick.get("exit_price"),
                pick.get("exitDate") or pick.get("exit_date"),
                pick.get("exitReason") or pick.get("exit_reason"),
                pick.get("pnl_pct"),
                pick.get("pnl_dollar"),
                pick.get("status", "OPEN"),
                pick.get("reason"),
                pick.get("regime"),
                pick.get("regime_confidence"),
                pick.get("breadth_pct"),
                pick.get("vol_20d"),
                pick.get("rsi_at_entry"),
                pick.get("volume_ratio"),
                pick.get("ml_win_prob"),
            ))
            conn.commit()
        except Exception as e:
            logger.warning(f"write_pick failed: {e}")
        finally:
            conn.close()

    def write_ranking_snapshot(self, rankings: list, regime: str = "neutral"):
        """Write daily tournament snapshot."""
        snap_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        conn = get_connection()
        try:
            for r in rankings:
                conn.execute("""
                    INSERT INTO rankings
                    (snapshot_date, algorithm, score, league, total_return,
                     sharpe, sortino, win_rate, max_drawdown, closed_picks, regime)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
                    snap_date,
                    r.get("id", ""),
                    r.get("score", 0),
                    r.get("league", ""),
                    r.get("totalReturn", 0),
                    r.get("sharpe", 0),
                    r.get("sortino", 0),
                    r.get("winRate", 0),
                    r.get("maxDrawdown", 0),
                    r.get("closedPicks", 0),
                    regime,
                ))
            conn.commit()
        except Exception as e:
            logger.warning(f"write_ranking_snapshot failed: {e}")
        finally:
            conn.close()

    def write_regime(self, regime_data: dict):
        """Write market regime snapshot."""
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO regime
                (timestamp, regime, crypto_regime, vix_proxy, hmm_regime,
                 hmm_confidence, vol_20d, btc_eth_ratio, spy_vs_sma200)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
                regime_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                regime_data.get("regime"),
                regime_data.get("crypto_regime"),
                regime_data.get("vix_proxy"),
                regime_data.get("hmm_regime"),
                regime_data.get("hmm_confidence"),
                regime_data.get("vol_20d"),
                regime_data.get("btc_eth_ratio"),
                regime_data.get("spy_vs_sma200"),
            ))
            conn.commit()
        except Exception as e:
            logger.warning(f"write_regime failed: {e}")
        finally:
            conn.close()

    def ingest_audit_log(self, audit_log_path: Optional[Path] = None) -> int:
        """Bulk import existing audit_log.json into signals table."""
        if audit_log_path is None:
            audit_log_path = DATA_DIR / "audit_log.json"
        if not audit_log_path.exists():
            return 0
        try:
            with open(audit_log_path) as f:
                entries = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read audit_log.json: {e}")
            return 0
        conn = get_connection()
        count = 0
        try:
            for entry in entries:
                conn.execute("""
                    INSERT OR IGNORE INTO signals
                    (timestamp, algorithm, tier, strategy, symbol, signal, reason, price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
                    entry.get("timestamp", ""),
                    entry.get("algorithm", ""),
                    entry.get("tier"),
                    entry.get("strategy"),
                    entry.get("symbol", ""),
                    entry.get("signal", "BUY"),
                    entry.get("reason"),
                    entry.get("price"),
                ))
                count += 1
            conn.commit()
            logger.info(f"Ingested {count} signals from audit_log.json")
        except Exception as e:
            logger.warning(f"ingest_audit_log failed: {e}")
        finally:
            conn.close()
        return count

    def ingest_competition_picks(self, comp_path: Optional[Path] = None) -> int:
        """Extract all closed picks from live_competition.json -> picks table."""
        if comp_path is None:
            comp_path = DATA_DIR / "live_competition.json"
        if not comp_path.exists():
            return 0
        try:
            with open(comp_path) as f:
                comp = json.load(f)
        except Exception:
            return 0
        count = 0
        for algo in comp.get("algorithms", []):
            algo_id = algo.get("id", "")
            category = algo.get("category", "stock")
            tier = algo.get("tier", "SCOUT")
            for pick in algo.get("closedPicks", []) + algo.get("activePicks", []):
                pick["algorithm"] = algo_id
                pick["category"] = category
                pick["tier"] = tier
                self.write_pick(pick)
                count += 1
        logger.info(f"Ingested {count} picks from live_competition.json")
        return count

    def get_algo_stats(self, algo_id: str) -> dict:
        """Get win rate, avg pnl, total picks for an algorithm."""
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) as wins,
                    AVG(pnl_pct) as avg_pnl,
                    MIN(pnl_pct) as worst,
                    MAX(pnl_pct) as best
                FROM picks
                WHERE algorithm = ? AND status IN ('WON','LOST','EXPIRED')
""", (algo_id,)).fetchone()
            if row and row["total"] > 0:
                return {
                    "total": row["total"],
                    "wins": row["wins"],
                    "win_rate": round((row["wins"] or 0) / row["total"], 3),
                    "avg_pnl": round(row["avg_pnl"] or 0, 3),
                    "worst": round(row["worst"] or 0, 3),
                    "best": round(row["best"] or 0, 3),
                }
        except Exception as e:
            logger.debug(f"get_algo_stats failed: {e}")
        finally:
            conn.close()
        return {}

    def export_training_dataset(self) -> "pd.DataFrame":
        """Export closed picks as DataFrame for ML training."""
        import pandas as pd
        conn = get_connection()
        try:
            df = pd.read_sql("""
                SELECT * FROM picks
                WHERE status IN ('WON', 'LOST', 'EXPIRED')
                ORDER BY entry_date ASC
""", conn)
            return df
        except Exception as e:
            logger.warning(f"export_training_dataset failed: {e}")
            return pd.DataFrame()
        finally:
            conn.close()

    def get_signal_count(self) -> int:
        """Return total signals in DB."""
        conn = get_connection()
        try:
            return conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        finally:
            conn.close()

    def get_picks_summary(self) -> dict:
        """Return summary statistics for picks table."""
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) as open,
                    SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) as won,
                    SUM(CASE WHEN status='LOST' THEN 1 ELSE 0 END) as lost,
                    SUM(CASE WHEN status='EXPIRED' THEN 1 ELSE 0 END) as expired
                FROM picks
""").fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    print("SQLiteStore -- initializing and importing existing data...")
    store = SQLiteStore()
    n_sig = store.ingest_audit_log()
    n_picks = store.ingest_competition_picks()
    print(f"Signals imported: {n_sig}")
    print(f"Picks imported: {n_picks}")
    print(f"Total signals in DB: {store.get_signal_count()}")
    print(f"Picks summary: {store.get_picks_summary()}")
    print(f"DB created at: {DB_PATH}")