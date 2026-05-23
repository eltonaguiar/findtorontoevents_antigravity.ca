"""
Strategy Registry Module
========================
Central SQLite-based registry for strategies, permutations, backtest results,
and live signals. Provides CRUD operations and auto-registration.
"""

import sqlite3
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
from contextlib import contextmanager

try:
    from .dna_engine import StrategyDNA, FitnessScore
except ImportError:
    from dna_engine import StrategyDNA, FitnessScore


def _safe_json_loads(value, default=None):
    """Parse JSON string, returning default on any error (corrupt data in DB)."""
    if not value:
        return default if default is not None else {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}

# Configure logging
import os as _os
_log_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'logs')
_os.makedirs(_log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(_os.path.join(_log_dir, 'strategy_registry.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('StrategyRegistry')


@dataclass
class StrategyRecord:
    """Database record for a strategy."""
    id: str
    name: str
    dna_hash: str
    status: str  # 'active', 'inactive', 'phoenix', 'deprecated'
    created_at: str
    generation: int
    parent_ids: List[str]
    genes: Dict
    symbol_specialization: Optional[str]
    metadata: Dict


@dataclass
class PermutationRecord:
    """Database record for a strategy permutation."""
    combo_id: str
    component_ids: List[str]
    combination_logic: str
    created_at: str
    status: str
    fitness_score: Optional[float]
    performance_metrics: Dict


@dataclass
class BacktestRecord:
    """Database record for backtest results."""
    id: int
    strategy_id: str
    symbol: str
    start_date: str
    end_date: str
    total_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    regime: Optional[str]
    created_at: str


@dataclass
class LiveSignalRecord:
    """Database record for live trading signals."""
    id: int
    strategy_id: str
    symbol: str
    direction: str
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float
    risk_reward: float
    generated_at: str
    executed_at: Optional[str]
    status: str  # 'pending', 'executed', 'closed', 'cancelled'
    exit_price: Optional[float]
    pnl: Optional[float]


class StrategyRegistry:
    """
    Central registry for all DNA-based strategies.
    
    Manages:
    - Strategy definitions and metadata
    - Permutation tracking
    - Backtest results
    - Live signal history
    - Performance analytics
    """
    
    def __init__(self, db_path: str = "genome/strategy_registry.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
        logger.info(f"StrategyRegistry initialized at {db_path}")
    
    def _ensure_db_directory(self):
        """Ensure database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Strategies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    dna_hash TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    generation INTEGER DEFAULT 0,
                    parent_ids TEXT,  -- JSON array
                    genes TEXT NOT NULL,  -- JSON object
                    symbol_specialization TEXT,
                    metadata TEXT,  -- JSON object
                    fitness_score REAL,
                    win_rate REAL,
                    sharpe_ratio REAL,
                    total_trades INTEGER DEFAULT 0
                )
            ''')
            
            # Permutations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS permutations (
                    combo_id TEXT PRIMARY KEY,
                    component_ids TEXT NOT NULL,  -- JSON array of strategy IDs
                    combination_logic TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'untested',
                    fitness_score REAL,
                    win_rate REAL,
                    sharpe_ratio REAL,
                    profit_factor REAL,
                    max_drawdown REAL,
                    performance_metrics TEXT,  -- JSON object
                    UNIQUE(component_ids, combination_logic)
                )
            ''')
            
            # Backtest results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_rate REAL,
                    avg_trade REAL,
                    avg_win REAL,
                    avg_loss REAL,
                    profit_factor REAL,
                    total_return REAL,
                    total_return_pct REAL,
                    annualized_return REAL,
                    max_drawdown REAL,
                    max_drawdown_pct REAL,
                    volatility REAL,
                    sharpe_ratio REAL,
                    sortino_ratio REAL,
                    calmar_ratio REAL,
                    omega_ratio REAL,
                    expectancy REAL,
                    sqn REAL,
                    regime TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_id) REFERENCES strategies(id),
                    UNIQUE(strategy_id, symbol, start_date, end_date)
                )
            ''')
            
            # Live signals table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS live_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    permutation_id TEXT,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL,
                    take_profit REAL,
                    stop_loss REAL,
                    confidence REAL,
                    risk_reward REAL,
                    position_size REAL,
                    generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    executed_at TEXT,
                    closed_at TEXT,
                    status TEXT DEFAULT 'pending',
                    exit_price REAL,
                    pnl REAL,
                    pnl_pct REAL,
                    exit_reason TEXT,
                    market_regime TEXT,
                    metadata TEXT,  -- JSON object
                    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
                )
            ''')
            
            # Audit log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    action TEXT NOT NULL,  -- 'CREATE', 'UPDATE', 'DELETE'
                    old_values TEXT,  -- JSON
                    new_values TEXT,  -- JSON
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT
                )
            ''')
            
            # Indices for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_strategies_status 
                ON strategies(status)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_strategies_specialization 
                ON strategies(symbol_specialization)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_backtests_strategy 
                ON backtest_results(strategy_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_backtests_symbol 
                ON backtest_results(symbol)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_signals_status 
                ON live_signals(status)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_signals_symbol 
                ON live_signals(symbol)
            ''')
            
            conn.commit()
            logger.info("Database schema initialized")
    
    # ==================== Strategy CRUD ====================
    
    def register_strategy(
        self,
        strategy: StrategyDNA,
        auto_update: bool = True
    ) -> bool:
        """
        Register a new strategy or update existing.
        
        Args:
            strategy: StrategyDNA to register
            auto_update: If True, update existing; if False, skip if exists
            
        Returns:
            True if registered/updated, False if skipped
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if exists
            cursor.execute(
                "SELECT id FROM strategies WHERE dna_hash = ?",
                (strategy.dna_hash,)
            )
            existing = cursor.fetchone()
            
            if existing and not auto_update:
                logger.debug(f"Strategy {strategy.strategy_id} already exists, skipping")
                return False
            
            data = {
                'id': strategy.strategy_id,
                'name': strategy.name,
                'dna_hash': strategy.dna_hash,
                'generation': strategy.generation,
                'parent_ids': json.dumps(strategy.parent_strategies),
                'genes': json.dumps(strategy.genes),
                'symbol_specialization': strategy.symbol_specialization,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if existing:
                # Update
                cursor.execute('''
                    UPDATE strategies SET
                        name = ?,
                        generation = ?,
                        parent_ids = ?,
                        genes = ?,
                        symbol_specialization = ?,
                        updated_at = ?
                    WHERE id = ?
                ''', (
                    data['name'], data['generation'], data['parent_ids'],
                    data['genes'], data['symbol_specialization'],
                    data['updated_at'], data['id']
                ))
                action = 'UPDATE'
            else:
                # Insert
                cursor.execute('''
                    INSERT INTO strategies 
                    (id, name, dna_hash, generation, parent_ids, genes, symbol_specialization, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['id'], data['name'], data['dna_hash'], data['generation'],
                    data['parent_ids'], data['genes'], data['symbol_specialization'],
                    data['updated_at'], data['updated_at']
                ))
                action = 'CREATE'
            
            # Log audit
            cursor.execute('''
                INSERT INTO audit_log (table_name, record_id, action, new_values)
                VALUES (?, ?, ?, ?)
            ''', ('strategies', data['id'], action, json.dumps(data)))
            
            conn.commit()
            logger.info(f"Strategy {strategy.strategy_id} {action.lower()}d")
            return True
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyDNA]:
        """Retrieve a strategy by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM strategies WHERE id = ?",
                (strategy_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_strategy(dict(row))
    
    def get_strategy_by_hash(self, dna_hash: str) -> Optional[StrategyDNA]:
        """Retrieve a strategy by DNA hash."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM strategies WHERE dna_hash = ?",
                (dna_hash,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_strategy(dict(row))
    
    def list_strategies(
        self,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        min_sharpe: Optional[float] = None,
        limit: int = 100
    ) -> List[StrategyDNA]:
        """List strategies with optional filtering."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM strategies WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            if symbol:
                query += " AND symbol_specialization = ?"
                params.append(symbol)
            if min_sharpe is not None:
                query += " AND sharpe_ratio >= ?"
                params.append(min_sharpe)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_strategy(dict(row)) for row in rows]
    
    def update_strategy_status(
        self,
        strategy_id: str,
        status: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Update strategy status."""
        valid_statuses = ['active', 'inactive', 'phoenix', 'deprecated', 'testing']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get old values for audit
            cursor.execute(
                "SELECT status, metadata FROM strategies WHERE id = ?",
                (strategy_id,)
            )
            old = cursor.fetchone()
            
            if not old:
                return False
            
            cursor.execute('''
                UPDATE strategies 
                SET status = ?, metadata = ?, updated_at = ?
                WHERE id = ?
            ''', (
                status,
                json.dumps(metadata) if metadata else old['metadata'],
                datetime.utcnow().isoformat(),
                strategy_id
            ))
            
            # Audit log
            cursor.execute('''
                INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                'strategies', strategy_id, 'UPDATE',
                json.dumps({'status': old['status']}),
                json.dumps({'status': status})
            ))
            
            conn.commit()
            logger.info(f"Strategy {strategy_id} status updated to {status}")
            return True
    
    def delete_strategy(self, strategy_id: str) -> bool:
        """Soft delete a strategy (marks as deprecated)."""
        return self.update_strategy_status(strategy_id, 'deprecated')
    
    # ==================== Permutation CRUD ====================
    
    def register_permutation(
        self,
        strategy: StrategyDNA,
        performance: Optional[Dict] = None
    ) -> bool:
        """Register a strategy permutation."""
        if not strategy.parent_strategies:
            logger.warning(f"Strategy {strategy.strategy_id} has no parents, not a permutation")
            return False
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            component_ids = json.dumps(sorted(strategy.parent_strategies))
            combo_logic = strategy.genes.get('combination_logic', 'unknown')
            
            # Check if exists
            cursor.execute('''
                SELECT combo_id FROM permutations 
                WHERE component_ids = ? AND combination_logic = ?
            ''', (component_ids, combo_logic))
            
            existing = cursor.fetchone()
            
            data = {
                'combo_id': strategy.strategy_id,
                'component_ids': component_ids,
                'combination_logic': combo_logic,
                'performance_metrics': json.dumps(performance) if performance else None,
                'fitness_score': performance.get('fitness_score') if performance else None,
                'win_rate': performance.get('win_rate') if performance else None,
                'sharpe_ratio': performance.get('sharpe_ratio') if performance else None,
                'profit_factor': performance.get('profit_factor') if performance else None,
                'max_drawdown': performance.get('max_drawdown') if performance else None
            }
            
            if existing:
                # Update with new performance
                cursor.execute('''
                    UPDATE permutations SET
                        status = ?,
                        fitness_score = ?,
                        win_rate = ?,
                        sharpe_ratio = ?,
                        profit_factor = ?,
                        max_drawdown = ?,
                        performance_metrics = ?
                    WHERE combo_id = ?
                ''', (
                    'tested' if performance else 'untested',
                    data['fitness_score'], data['win_rate'], data['sharpe_ratio'],
                    data['profit_factor'], data['max_drawdown'],
                    data['performance_metrics'], existing['combo_id']
                ))
            else:
                cursor.execute('''
                    INSERT INTO permutations
                    (combo_id, component_ids, combination_logic, status,
                     fitness_score, win_rate, sharpe_ratio, profit_factor, max_drawdown, performance_metrics)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['combo_id'], data['component_ids'], data['combination_logic'],
                    'tested' if performance else 'untested',
                    data['fitness_score'], data['win_rate'], data['sharpe_ratio'],
                    data['profit_factor'], data['max_drawdown'], data['performance_metrics']
                ))
            
            conn.commit()
            logger.info(f"Permutation {strategy.strategy_id} registered")
            return True
    
    def get_top_permutations(
        self,
        metric: str = "sharpe_ratio",
        limit: int = 10,
        min_trades: int = 10
    ) -> List[Dict]:
        """Get top performing permutations."""
        valid_metrics = ['fitness_score', 'sharpe_ratio', 'win_rate', 'profit_factor']
        if metric not in valid_metrics:
            metric = 'sharpe_ratio'
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT * FROM permutations 
                WHERE status = 'tested' AND {metric} IS NOT NULL
                ORDER BY {metric} DESC
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Backtest Results ====================
    
    def save_backtest_result(self, result: Dict) -> int:
        """Save a backtest result."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO backtest_results
                (strategy_id, symbol, start_date, end_date, total_trades, winning_trades,
                 losing_trades, win_rate, avg_trade, avg_win, avg_loss, profit_factor,
                 total_return, total_return_pct, annualized_return, max_drawdown, max_drawdown_pct,
                 volatility, sharpe_ratio, sortino_ratio, calmar_ratio, omega_ratio,
                 expectancy, sqn, regime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.get('strategy_id'),
                result.get('symbol'),
                result.get('start_date'),
                result.get('end_date'),
                result.get('total_trades'),
                result.get('winning_trades'),
                result.get('losing_trades'),
                result.get('win_rate'),
                result.get('avg_trade'),
                result.get('avg_win'),
                result.get('avg_loss'),
                result.get('profit_factor'),
                result.get('total_return'),
                result.get('total_return_pct'),
                result.get('annualized_return'),
                result.get('max_drawdown'),
                result.get('max_drawdown_pct'),
                result.get('volatility'),
                result.get('sharpe_ratio'),
                result.get('sortino_ratio'),
                result.get('calmar_ratio'),
                result.get('omega_ratio'),
                result.get('expectancy'),
                result.get('sqn'),
                result.get('regime')
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_strategy_performance(
        self,
        strategy_id: str,
        symbol: Optional[str] = None
    ) -> List[Dict]:
        """Get all backtest results for a strategy."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM backtest_results WHERE strategy_id = ?"
            params = [strategy_id]
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Live Signals ====================
    
    def record_signal(self, signal: Dict) -> int:
        """Record a new live trading signal."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO live_signals
                (strategy_id, permutation_id, symbol, direction, entry_price, take_profit,
                 stop_loss, confidence, risk_reward, position_size, market_regime, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.get('strategy_id'),
                signal.get('permutation_id'),
                signal.get('symbol'),
                signal.get('direction'),
                signal.get('entry_price'),
                signal.get('take_profit'),
                signal.get('stop_loss'),
                signal.get('confidence'),
                signal.get('risk_reward'),
                signal.get('position_size'),
                signal.get('market_regime'),
                json.dumps(signal.get('metadata', {}))
            ))
            
            conn.commit()
            signal_id = cursor.lastrowid
            logger.info(f"Signal recorded: {signal_id} for {signal.get('symbol')}")
            return signal_id
    
    def update_signal_status(
        self,
        signal_id: int,
        status: str,
        exit_price: Optional[float] = None,
        pnl: Optional[float] = None,
        exit_reason: Optional[str] = None
    ) -> bool:
        """Update signal execution status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if status == 'executed':
                cursor.execute('''
                    UPDATE live_signals 
                    SET status = ?, executed_at = ?
                    WHERE id = ?
                ''', (status, datetime.utcnow().isoformat(), signal_id))
            elif status == 'closed':
                cursor.execute('''
                    UPDATE live_signals 
                    SET status = ?, closed_at = ?, exit_price = ?, pnl = ?, exit_reason = ?
                    WHERE id = ?
                ''', (status, datetime.utcnow().isoformat(), exit_price, pnl, exit_reason, signal_id))
            else:
                cursor.execute(
                    "UPDATE live_signals SET status = ? WHERE id = ?",
                    (status, signal_id)
                )
            
            conn.commit()
            return True
    
    def get_active_signals(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all active (pending or executed) signals."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM live_signals WHERE status IN ('pending', 'executed')"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            query += " ORDER BY generated_at DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_signal_history(
        self,
        strategy_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get historical signal performance."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM live_signals WHERE status = 'closed'"
            params = []
            
            if strategy_id:
                query += " AND strategy_id = ?"
                params.append(strategy_id)
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            query += " ORDER BY closed_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Analytics ====================
    
    def get_strategy_stats(self, strategy_id: str) -> Dict:
        """Get comprehensive stats for a strategy."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Backtest stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_backtests,
                    AVG(sharpe_ratio) as avg_sharpe,
                    AVG(win_rate) as avg_win_rate,
                    AVG(total_return_pct) as avg_return,
                    MAX(sharpe_ratio) as best_sharpe,
                    MIN(max_drawdown_pct) as best_dd
                FROM backtest_results
                WHERE strategy_id = ?
            ''', (strategy_id,))
            backtest_stats = dict(cursor.fetchone())
            
            # Live signal stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_signals,
                    AVG(pnl) as avg_pnl,
                    SUM(pnl) as total_pnl
                FROM live_signals
                WHERE strategy_id = ? AND status = 'closed'
            ''', (strategy_id,))
            signal_stats = dict(cursor.fetchone())
            
            return {
                'backtest': backtest_stats,
                'live_signals': signal_stats
            }
    
    def get_leaderboard(
        self,
        metric: str = "sharpe_ratio",
        timeframe: str = "all",
        limit: int = 20
    ) -> List[Dict]:
        """Get top performing strategies leaderboard."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            timeframe_filter = ""
            if timeframe == "30d":
                timeframe_filter = "AND created_at >= date('now', '-30 days')"
            elif timeframe == "7d":
                timeframe_filter = "AND created_at >= date('now', '-7 days')"
            
            cursor.execute(f'''
                SELECT 
                    s.id,
                    s.name,
                    s.symbol_specialization,
                    s.status,
                    AVG(b.sharpe_ratio) as avg_sharpe,
                    AVG(b.win_rate) as avg_win_rate,
                    AVG(b.profit_factor) as avg_profit_factor,
                    AVG(b.total_return_pct) as avg_return,
                    COUNT(b.id) as backtest_count
                FROM strategies s
                LEFT JOIN backtest_results b ON s.id = b.strategy_id
                WHERE s.status = 'active' {timeframe_filter}
                GROUP BY s.id
                HAVING backtest_count > 0
                ORDER BY avg_sharpe DESC NULLS LAST
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Helper Methods ====================
    
    def _row_to_strategy(self, row: Dict) -> StrategyDNA:
        """Convert database row to StrategyDNA."""
        return StrategyDNA(
            strategy_id=row['id'],
            name=row['name'],
            genes=_safe_json_loads(row['genes'], {}),
            parent_strategies=_safe_json_loads(row['parent_ids'], []),
            created_at=row['created_at'],
            generation=row['generation'],
            dna_hash=row['dna_hash'],
            symbol_specialization=row['symbol_specialization']
        )
    
    def export_to_json(self, filepath: str, strategy_ids: Optional[List[str]] = None):
        """Export registry data to JSON."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            data = {
                'exported_at': datetime.utcnow().isoformat(),
                'strategies': [],
                'permutations': [],
                'backtests': [],
                'signals': []
            }
            
            # Strategies
            if strategy_ids:
                placeholders = ','.join('?' * len(strategy_ids))
                cursor.execute(f"SELECT * FROM strategies WHERE id IN ({placeholders})", strategy_ids)
            else:
                cursor.execute("SELECT * FROM strategies")
            data['strategies'] = [dict(row) for row in cursor.fetchall()]
            
            # Permutations
            cursor.execute("SELECT * FROM permutations")
            data['permutations'] = [dict(row) for row in cursor.fetchall()]
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Exported registry to {filepath}")
    
    def auto_register_strategies(self, strategies: List[StrategyDNA]) -> Dict:
        """Auto-register multiple strategies, skipping existing."""
        results = {'registered': 0, 'updated': 0, 'skipped': 0}
        
        for strategy in strategies:
            try:
                # Check if exists
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id FROM strategies WHERE dna_hash = ?",
                        (strategy.dna_hash,)
                    )
                    existing = cursor.fetchone()
                
                if existing:
                    results['skipped'] += 1
                else:
                    if self.register_strategy(strategy, auto_update=False):
                        results['registered'] += 1
                    
                # Also register as permutation if it has parents
                if strategy.parent_strategies:
                    self.register_permutation(strategy)
                    
            except Exception as e:
                logger.error(f"Failed to register {strategy.strategy_id}: {e}")
                results['skipped'] += 1
        
        logger.info(f"Auto-registration complete: {results}")
        return results


if __name__ == "__main__":
    import argparse
    import os
    import sys
    import random

    parser = argparse.ArgumentParser(description="Strategy Registry CLI")
    parser.add_argument("--update-performance", action="store_true",
                        help="Update performance metrics from latest backtest results")
    parser.add_argument("--list", action="store_true",
                        help="List all registered strategies")
    parser.add_argument("--leaderboard", action="store_true",
                        help="Show strategy leaderboard")
    parser.add_argument("--results-dir", type=str, default="results",
                        help="Directory with backtest results (default: results)")
    args = parser.parse_args()

    # Handle imports for both execution contexts
    try:
        from dna_engine import create_strategy_dna, StrategyDNA
    except ImportError:
        from genome.dna_engine import create_strategy_dna, StrategyDNA

    registry = StrategyRegistry()

    if args.update_performance:
        print("[INFO] Updating strategy performance from backtest results...")

        # Load permutations and register strategies
        permutations_path = os.path.join(args.results_dir, "permutations.json")
        if os.path.exists(permutations_path):
            try:
                with open(permutations_path, 'r') as f:
                    perm_data = json.load(f)
                strategies = [StrategyDNA.from_dict(p) for p in perm_data.get('permutations', [])]
                reg_results = registry.auto_register_strategies(strategies)
                print(f"[OK] Registration: {reg_results}")
            except Exception as e:
                print(f"[WARN] Failed to load permutations: {e}")

        # Load backtest results and update performance
        backtest_path = os.path.join(args.results_dir, "backtest_results.json")
        if os.path.exists(backtest_path):
            try:
                with open(backtest_path, 'r') as f:
                    bt_data = json.load(f)
                results = bt_data.get('results', [])
                saved = 0
                for r in results:
                    try:
                        registry.save_backtest_result(r)
                        saved += 1
                    except Exception as e:
                        logger.warning(f"Failed to save result for {r.get('strategy_id')}: {e}")
                print(f"[OK] Saved {saved} backtest results to registry")
            except Exception as e:
                print(f"[WARN] Failed to load backtest results: {e}")
        else:
            print(f"[INFO] No backtest results found at {backtest_path}")

        # Show leaderboard
        leaderboard = registry.get_leaderboard(limit=10)
        print(f"\n[INFO] Top strategies:")
        for i, entry in enumerate(leaderboard, 1):
            print(f"  [{i}] {entry.get('name', 'unknown')} | "
                  f"Sharpe: {entry.get('avg_sharpe', 0):.3f} | "
                  f"WR: {entry.get('avg_win_rate', 0):.2%}")

    elif args.list:
        strategies = registry.list_strategies(limit=50)
        print(f"Total strategies: {len(strategies)}")
        for s in strategies:
            print(f"  {s.strategy_id}: {s.name} (gen {s.generation})")

    elif args.leaderboard:
        leaderboard = registry.get_leaderboard(limit=20)
        print("Strategy Leaderboard:")
        for i, entry in enumerate(leaderboard, 1):
            print(f"  [{i}] {entry.get('name', 'unknown')} | "
                  f"Sharpe: {entry.get('avg_sharpe', 0):.3f} | "
                  f"WR: {entry.get('avg_win_rate', 0):.2%}")

    else:
        # Demo mode
        strategies = [
            create_strategy_dna(f"Strategy_{i}", timeframe=random.choice(["1h", "4h"]))
            for i in range(5)
        ]
        results = registry.auto_register_strategies(strategies)
        print(f"Registration results: {results}")
        all_strategies = registry.list_strategies()
        print(f"Total strategies in registry: {len(all_strategies)}")
