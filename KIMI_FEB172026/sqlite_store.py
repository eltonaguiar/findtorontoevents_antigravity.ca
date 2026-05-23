"""
KIMI_FEB172026 - SQLite Store
Persistent database for signals, picks, and ML training data
Replaces JSON files with queryable SQLite database
"""

import sqlite3
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SignalEntry:
    """Signal database entry"""
    timestamp: str
    algorithm: str
    tier: str
    strategy: str
    symbol: str
    signal: str
    reason: str
    price: float
    regime: str
    crypto_regime: str
    breadth_pct: float
    vix_proxy: str
    hmm_confidence: float

@dataclass
class PickEntry:
    """Pick outcome entry"""
    pick_id: str
    algorithm: str
    symbol: str
    category: str
    tier: str
    entry_price: float
    entry_date: str
    exit_price: Optional[float]
    exit_date: Optional[str]
    exit_reason: str
    pnl_pct: float
    pnl_dollar: float
    status: str
    reason: str
    regime: str
    regime_confidence: float
    breadth_pct: float
    vol_20d: float
    rsi_at_entry: float
    volume_ratio: float
    ml_win_prob: float


class SQLiteStore:
    """
    SQLite database manager for trading data
    Handles signals, picks, rankings, and regime history
    """
    
    def __init__(self, db_path: str = "KIMI_FEB172026/data/kimi_trading.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = None
        self.init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Signals table - all audit signals
        cursor.execute("""
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
                hmm_confidence REAL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Picks table - all picks with outcomes (key ML training table)
        cursor.execute("""
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
                ml_win_prob REAL,
                features TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Rankings table - daily tournament snapshots
        cursor.execute("""
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
                regime TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Market regime history
        cursor.execute("""
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
                spy_vs_sma200 REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_pnl REAL,
                win_rate REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                active_positions INTEGER,
                closed_positions INTEGER,
                best_algo TEXT,
                worst_algo TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_algo ON signals(algorithm)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_picks_algo ON picks(algorithm)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_picks_symbol ON picks(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_picks_status ON picks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rankings_date ON rankings(snapshot_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_regime_time ON regime(timestamp)")
        
        conn.commit()
        conn.close()
        
        logger.info("Database initialized successfully")
    
    # =========================================================================
    # Signal Operations
    # =========================================================================
    def write_signal(self, entry: Dict) -> int:
        """Write a signal to the database"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO signals 
            (timestamp, algorithm, tier, strategy, symbol, signal, reason, 
             price, regime, crypto_regime, breadth_pct, vix_proxy, hmm_confidence, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.get('timestamp', datetime.now().isoformat()),
            entry.get('algorithm', ''),
            entry.get('tier', ''),
            entry.get('strategy', ''),
            entry.get('symbol', ''),
            entry.get('signal', ''),
            entry.get('reason', ''),
            entry.get('price', 0.0),
            entry.get('regime', ''),
            entry.get('crypto_regime', ''),
            entry.get('breadth_pct', 0.0),
            entry.get('vix_proxy', ''),
            entry.get('hmm_confidence', 0.0),
            json.dumps(entry.get('metadata', {}))
        ))
        
        signal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return signal_id
    
    def get_signals(self, algorithm: Optional[str] = None, 
                   symbol: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   limit: int = 100) -> pd.DataFrame:
        """Query signals with filters"""
        conn = self._get_connection()
        
        query = "SELECT * FROM signals WHERE 1=1"
        params = []
        
        if algorithm:
            query += " AND algorithm = ?"
            params.append(algorithm)
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += f" ORDER BY timestamp DESC LIMIT {limit}"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    # =========================================================================
    # Pick Operations
    # =========================================================================
    def write_pick(self, pick: Dict) -> str:
        """Write a new pick to the database"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        pick_id = pick.get('id', f"{pick['algorithm']}_{pick['symbol']}_{datetime.now().strftime('%Y%m%d')}")
        
        cursor.execute("""
            INSERT OR REPLACE INTO picks 
            (id, algorithm, symbol, category, tier, entry_price, entry_date,
             exit_price, exit_date, exit_reason, pnl_pct, pnl_dollar, status,
             reason, regime, regime_confidence, breadth_pct, vol_20d, 
             rsi_at_entry, volume_ratio, ml_win_prob, features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pick_id,
            pick.get('algorithm', ''),
            pick.get('symbol', ''),
            pick.get('category', ''),
            pick.get('tier', ''),
            pick.get('entry_price', 0.0),
            pick.get('entry_date', datetime.now().isoformat()),
            pick.get('exit_price'),
            pick.get('exit_date'),
            pick.get('exit_reason', ''),
            pick.get('pnl_pct', 0.0),
            pick.get('pnl_dollar', 0.0),
            pick.get('status', 'OPEN'),
            pick.get('reason', ''),
            pick.get('regime', ''),
            pick.get('regime_confidence', 0.0),
            pick.get('breadth_pct', 0.0),
            pick.get('vol_20d', 0.0),
            pick.get('rsi_at_entry', 0.0),
            pick.get('volume_ratio', 0.0),
            pick.get('ml_win_prob', 0.5),
            json.dumps(pick.get('features', {}))
        ))
        
        conn.commit()
        conn.close()
        
        return pick_id
    
    def close_pick(self, pick_id: str, exit_price: float, 
                  exit_reason: str, pnl_pct: float) -> bool:
        """Close an open pick with outcome"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE picks 
            SET exit_price = ?, 
                exit_date = ?,
                exit_reason = ?,
                pnl_pct = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            exit_price,
            datetime.now().isoformat(),
            exit_reason,
            pnl_pct,
            'WON' if pnl_pct > 0 else 'LOST',
            pick_id
        ))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def get_picks(self, status: Optional[str] = None,
                 algorithm: Optional[str] = None,
                 symbol: Optional[str] = None,
                 start_date: Optional[str] = None,
                 limit: int = 100) -> pd.DataFrame:
        """Query picks with filters"""
        conn = self._get_connection()
        
        query = "SELECT * FROM picks WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if algorithm:
            query += " AND algorithm = ?"
            params.append(algorithm)
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if start_date:
            query += " AND entry_date >= ?"
            params.append(start_date)
        
        query += f" ORDER BY entry_date DESC LIMIT {limit}"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_open_picks(self) -> pd.DataFrame:
        """Get all open picks"""
        return self.get_picks(status='OPEN', limit=1000)
    
    def get_closed_picks(self, min_picks: int = 50) -> pd.DataFrame:
        """Get closed picks for ML training"""
        return self.get_picks(status=None, limit=10000)
    
    # =========================================================================
    # ML Feature Extraction
    # =========================================================================
    def get_ml_features(self, algo_id: str, symbol: str, 
                       regime: str) -> Dict[str, float]:
        """Get features for ML prediction"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get algorithm stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) as wins,
                AVG(pnl_pct) as avg_pnl,
                AVG(CASE WHEN pnl_pct > 0 THEN pnl_pct END) as avg_win,
                AVG(CASE WHEN pnl_pct < 0 THEN pnl_pct END) as avg_loss
            FROM picks 
            WHERE algorithm = ?
        """, (algo_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        total = row['total'] if row else 0
        wins = row['wins'] if row else 0
        
        return {
            "algo_total_closed": total,
            "algo_current_wr": wins / total if total > 0 else 0.5,
            "algo_avg_pnl": row['avg_pnl'] if row else 0,
            "algo_avg_win": row['avg_win'] if row else 0.02,
            "algo_avg_loss": row['avg_loss'] if row else -0.01,
        }
    
    def get_algo_stats(self, algo_id: str) -> Dict:
        """Get comprehensive algorithm statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_closed,
                SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) as losses,
                AVG(pnl_pct) as avg_pnl,
                AVG(CASE WHEN pnl_pct > 0 THEN pnl_pct END) as avg_win_pct,
                AVG(CASE WHEN pnl_pct < 0 THEN pnl_pct END) as avg_loss_pct,
                MAX(pnl_pct) as best_trade,
                MIN(pnl_pct) as worst_trade,
                SUM(pnl_pct) as total_return
            FROM picks 
            WHERE algorithm = ? AND status IN ('WON', 'LOST')
        """, (algo_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row or row['total_closed'] == 0:
            return {
                "algorithm": algo_id,
                "total_closed": 0,
                "win_rate": 0,
                "avg_pnl": 0,
                "sharpe": 0
            }
        
        total = row['total_closed']
        wins = row['wins'] or 0
        
        # Calculate Sharpe (simplified)
        returns = self._get_algo_returns(algo_id)
        sharpe = 0
        if len(returns) > 1:
            mean_ret = np.mean(returns)
            std_ret = np.std(returns)
            if std_ret > 0:
                sharpe = mean_ret / std_ret * np.sqrt(252)  # Annualized
        
        return {
            "algorithm": algo_id,
            "total_closed": total,
            "wins": wins,
            "losses": row['losses'] or 0,
            "win_rate": round(wins / total, 4),
            "avg_pnl_pct": round(row['avg_pnl'] or 0, 4),
            "avg_win_pct": round(row['avg_win_pct'] or 0, 4),
            "avg_loss_pct": round(row['avg_loss_pct'] or 0, 4),
            "best_trade": round(row['best_trade'] or 0, 4),
            "worst_trade": round(row['worst_trade'] or 0, 4),
            "total_return_pct": round(row['total_return'] or 0, 4),
            "sharpe": round(sharpe, 4)
        }
    
    def _get_algo_returns(self, algo_id: str) -> List[float]:
        """Get list of returns for Sharpe calculation"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pnl_pct FROM picks 
            WHERE algorithm = ? AND status IN ('WON', 'LOST')
            ORDER BY entry_date
        """, (algo_id,))
        
        returns = [row['pnl_pct'] for row in cursor.fetchall()]
        conn.close()
        
        return returns
    
    def export_training_dataset(self) -> pd.DataFrame:
        """Export dataset for ML training"""
        conn = self._get_connection()
        
        query = """
            SELECT * FROM picks 
            WHERE status IN ('WON', 'LOST') 
            AND features IS NOT NULL
            ORDER BY entry_date DESC
            LIMIT 10000
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Parse features JSON
        if 'features' in df.columns:
            features_df = df['features'].apply(lambda x: pd.Series(json.loads(x)) if x else {})
            df = pd.concat([df.drop('features', axis=1), features_df], axis=1)
        
        return df
    
    # =========================================================================
    # Ranking Operations
    # =========================================================================
    def write_ranking_snapshot(self, snapshot_date: str, 
                               rankings: List[Dict]) -> bool:
        """Write daily ranking snapshot"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for rank in rankings:
            cursor.execute("""
                INSERT INTO rankings 
                (snapshot_date, algorithm, score, league, total_return, 
                 sharpe, sortino, win_rate, max_drawdown, closed_picks, regime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_date,
                rank.get('algorithm', ''),
                rank.get('score', 0),
                rank.get('league', ''),
                rank.get('total_return', 0),
                rank.get('sharpe', 0),
                rank.get('sortino', 0),
                rank.get('win_rate', 0),
                rank.get('max_drawdown', 0),
                rank.get('closed_picks', 0),
                rank.get('regime', '')
            ))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_ranking_history(self, algorithm: Optional[str] = None,
                           days: int = 30) -> pd.DataFrame:
        """Get ranking history"""
        conn = self._get_connection()
        
        query = """
            SELECT * FROM rankings 
            WHERE snapshot_date >= date('now', '-{} days')
        """.format(days)
        
        params = []
        if algorithm:
            query += " AND algorithm = ?"
            params.append(algorithm)
        
        query += " ORDER BY snapshot_date DESC, score DESC"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    # =========================================================================
    # Regime Operations
    # =========================================================================
    def write_regime(self, regime_data: Dict) -> int:
        """Write regime snapshot"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO regime 
            (timestamp, regime, crypto_regime, vix_proxy, hmm_regime,
             hmm_confidence, vol_20d, btc_eth_ratio, spy_vs_sma200)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            regime_data.get('timestamp', datetime.now().isoformat()),
            regime_data.get('regime', ''),
            regime_data.get('crypto_regime', ''),
            regime_data.get('vix_proxy', ''),
            regime_data.get('hmm_regime', ''),
            regime_data.get('hmm_confidence', 0),
            regime_data.get('vol_20d', 0),
            regime_data.get('btc_eth_ratio', 0),
            regime_data.get('spy_vs_sma200', 0)
        ))
        
        regime_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return regime_id
    
    def get_current_regime(self) -> Optional[Dict]:
        """Get most recent regime"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM regime 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    # =========================================================================
    # Import/Export
    # =========================================================================
    def ingest_audit_log(self, audit_path: str) -> int:
        """Bulk import existing audit_log.json to signals table"""
        try:
            with open(audit_path, 'r') as f:
                audit_data = json.load(f)
            
            count = 0
            for entry in audit_data:
                self.write_signal(entry)
                count += 1
            
            logger.info(f"Imported {count} audit entries")
            return count
            
        except Exception as e:
            logger.error(f"Error importing audit log: {e}")
            return 0
    
    def export_to_csv(self, table: str, csv_path: str) -> bool:
        """Export table to CSV"""
        try:
            conn = self._get_connection()
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            conn.close()
            
            df.to_csv(csv_path, index=False)
            logger.info(f"Exported {table} to {csv_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting {table}: {e}")
            return False
    
    # =========================================================================
    # Statistics
    # =========================================================================
    def get_performance_summary(self, days: int = 30) -> Dict:
        """Get overall performance summary"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_picks,
                SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) as losses,
                SUM(pnl_pct) as total_pnl,
                AVG(pnl_pct) as avg_pnl,
                COUNT(DISTINCT algorithm) as active_algos
            FROM picks 
            WHERE entry_date >= date('now', '-{} days')
        """.format(days))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {}
        
        total = row['total_picks'] or 0
        wins = row['wins'] or 0
        
        return {
            "period_days": days,
            "total_picks": total,
            "wins": wins,
            "losses": row['losses'] or 0,
            "win_rate": round(wins / total, 4) if total > 0 else 0,
            "total_pnl_pct": round(row['total_pnl'] or 0, 4),
            "avg_pnl_pct": round(row['avg_pnl'] or 0, 4),
            "active_algorithms": row['active_algos'] or 0
        }


# =============================================================================
# Main Entry Point
# =============================================================================
def main():
    """Test the SQLite store"""
    print("=" * 80)
    print("KIMI_FEB172026 - SQLite Store")
    print("Database Persistence Layer")
    print("=" * 80)
    
    store = SQLiteStore()
    
    # Test write signal
    signal = {
        "timestamp": datetime.now().isoformat(),
        "algorithm": "pump-detector-scout",
        "tier": "TIER_1",
        "strategy": "PumpAcceleration",
        "symbol": "BTC-USD",
        "signal": "BUY",
        "reason": "Early pump detection: +12% in 4h",
        "price": 96500.0,
        "regime": "bull",
        "crypto_regime": "risk_on",
        "breadth_pct": 65.5,
        "vix_proxy": "bull",
        "hmm_confidence": 0.75,
        "metadata": {"volume_ratio": 5.5, "rsi": 55}
    }
    
    signal_id = store.write_signal(signal)
    print(f"\nWrote signal ID: {signal_id}")
    
    # Test write pick
    pick = {
        "algorithm": "pump-detector-scout",
        "symbol": "BTC-USD",
        "category": "crypto",
        "tier": "TIER_1",
        "entry_price": 96500.0,
        "status": "OPEN",
        "reason": "Early pump detection",
        "regime": "bull",
        "regime_confidence": 0.75,
        "breadth_pct": 65.5,
        "vol_20d": 0.025,
        "rsi_at_entry": 55,
        "volume_ratio": 5.5,
        "ml_win_prob": 0.72,
        "features": {"algo_current_wr": 0.68, "volume_ratio": 5.5}
    }
    
    pick_id = store.write_pick(pick)
    print(f"Wrote pick ID: {pick_id}")
    
    # Test close pick
    store.close_pick(pick_id, 98500.0, "TP_HIT", 2.07)
    print(f"Closed pick {pick_id} with +2.07% PnL")
    
    # Test queries
    print("\n" + "=" * 80)
    print("Recent Signals:")
    print("=" * 80)
    signals_df = store.get_signals(limit=5)
    print(signals_df[['timestamp', 'algorithm', 'symbol', 'signal']].to_string())
    
    print("\n" + "=" * 80)
    print("Closed Picks:")
    print("=" * 80)
    picks_df = store.get_picks(status='WON', limit=5)
    print(picks_df[['id', 'algorithm', 'symbol', 'pnl_pct', 'status']].to_string())
    
    print("\n" + "=" * 80)
    print("Performance Summary (30 days):")
    print("=" * 80)
    summary = store.get_performance_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)
    print("Algo Stats:")
    print("=" * 80)
    stats = store.get_algo_stats("pump-detector-scout")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nDatabase ready!")


if __name__ == "__main__":
    main()
