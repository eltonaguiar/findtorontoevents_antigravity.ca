"""
Strategy Validation and Kill Switch System
==========================================
A production-ready module for validating trading strategies before they go live.
Includes kill switches, promotion pipeline, Monte Carlo simulation, and statistical testing.

Author: Quantitative Finance Research Team
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Callable, Any
from enum import Enum, auto
from collections import defaultdict
import json
import logging
from scipy import stats
from scipy.stats import norm
import warnings

# Handle deprecated binom_test
try:
    from scipy.stats import binom_test
except ImportError:
    # For newer scipy versions, use binomtest
    from scipy.stats import binomtest as _binomtest
    def binom_test(x, n, p, alternative='two-sided'):
        result = _binomtest(x, n, p, alternative=alternative)
        return result.pvalue
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyStage(Enum):
    """Strategy promotion pipeline stages."""
    INCUBATOR = "incubator"      # Initial stage, < 50 trades
    SANDBOX = "sandbox"          # 50-100 trades, basic validation
    FRESH_PICKS = "fresh_picks"  # 100-200 trades, advanced validation
    LIVE = "live"                # 200+ trades, production ready
    DISABLED = "disabled"        # Kill switch triggered
    ARCHIVED = "archived"        # Permanently retired


class KillReason(Enum):
    """Reasons for strategy kill switch activation."""
    WIN_RATE_THRESHOLD = "win_rate_below_threshold"
    SHARPE_THRESHOLD = "sharpe_below_threshold"
    SORTINO_THRESHOLD = "sortino_below_threshold"
    MAX_DRAWDOWN = "max_drawdown_exceeded"
    PROFIT_FACTOR = "profit_factor_below_threshold"
    CONSECUTIVE_LOSSES = "consecutive_losses_exceeded"
    VOLATILITY_SPIKE = "volatility_spike_detected"
    MANUAL_DISABLE = "manual_disable"
    STATISTICAL_INVALID = "statistically_invalid"


@dataclass
class Trade:
    """Represents a single trade."""
    trade_id: str
    strategy_id: str
    timestamp: datetime
    pnl: float  # Profit/Loss in currency units
    pnl_pct: float  # Profit/Loss percentage
    direction: str  # 'long' or 'short'
    entry_price: float
    exit_price: float
    holding_period: int  # in minutes
    market_regime: str = "unknown"  # e.g., 'trending', 'ranging', 'volatile'
    
    def to_dict(self) -> Dict:
        return {
            'trade_id': self.trade_id,
            'strategy_id': self.strategy_id,
            'timestamp': self.timestamp.isoformat(),
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'holding_period': self.holding_period,
            'market_regime': self.market_regime
        }


@dataclass
class StrategyMetrics:
    """Comprehensive performance metrics for a strategy."""
    strategy_id: str
    timestamp: datetime
    
    # Basic metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L metrics
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    # Risk-adjusted metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Drawdown metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    current_drawdown: float = 0.0
    
    # Volatility metrics
    volatility: float = 0.0
    downside_deviation: float = 0.0
    
    # Statistical significance
    wr_p_value: float = 1.0
    is_statistically_significant: bool = False
    
    # Consecutive metrics
    consecutive_losses: int = 0
    max_consecutive_losses: int = 0
    
    # Recent performance
    last_20_trades_wr: float = 0.0
    last_50_trades_wr: float = 0.0
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        # Convert datetime to ISO format string for JSON serialization
        if isinstance(d.get('timestamp'), datetime):
            d['timestamp'] = d['timestamp'].isoformat()
        # Convert numpy types to Python native types
        for key, value in d.items():
            if isinstance(value, np.bool_):
                d[key] = bool(value)
            elif isinstance(value, np.integer):
                d[key] = int(value)
            elif isinstance(value, np.floating):
                d[key] = float(value)
            elif isinstance(value, np.ndarray):
                d[key] = value.tolist()
        return d


@dataclass
class KillSwitchConfig:
    """Configuration for kill switch thresholds."""
    # Minimum trades before kill switch can trigger
    min_trades_for_kill: int = 20
    
    # Win rate thresholds
    wr_threshold: float = 0.45  # Kill if WR < 45%
    wr_min_trades: int = 50
    
    # Sharpe ratio threshold
    sharpe_threshold: float = 1.0
    sharpe_min_trades: int = 50
    
    # Sortino ratio threshold
    sortino_threshold: float = 1.0
    sortino_min_trades: int = 50
    
    # Drawdown threshold
    max_drawdown_pct: float = -0.15  # Kill if DD > 15%
    
    # Profit factor threshold
    profit_factor_threshold: float = 1.0
    
    # Consecutive losses
    max_consecutive_losses: int = 10
    
    # Volatility spike detection
    volatility_spike_multiplier: float = 3.0
    
    # Statistical significance
    require_statistical_significance: bool = True
    significance_level: float = 0.05


@dataclass
class PromotionCriteria:
    """Criteria for promoting strategies through pipeline stages."""
    # To SANDBOX (from INCUBATOR)
    sandbox_min_trades: int = 50
    sandbox_min_wr: float = 0.48
    sandbox_max_drawdown: float = -0.10
    
    # To FRESH_PICKS (from SANDBOX)
    fresh_picks_min_trades: int = 100
    fresh_picks_min_wr: float = 0.50
    fresh_picks_min_sharpe: float = 0.8
    fresh_picks_max_drawdown: float = -0.12
    
    # To LIVE (from FRESH_PICKS)
    live_min_trades: int = 200
    live_min_wr: float = 0.52
    live_min_sharpe: float = 1.0
    live_min_sortino: float = 1.0
    live_max_drawdown: float = -0.15
    live_min_profit_factor: float = 1.2
    live_require_statistical_significance: bool = True


class StrategyValidator:
    """
    Main class for strategy validation, kill switches, and promotion pipeline.
    """
    
    def __init__(self, 
                 db_path: str = "strategy_validation.db",
                 kill_config: Optional[KillSwitchConfig] = None,
                 promotion_criteria: Optional[PromotionCriteria] = None):
        """
        Initialize the StrategyValidator.
        
        Args:
            db_path: Path to SQLite database for persistence
            kill_config: Configuration for kill switch thresholds
            promotion_criteria: Criteria for strategy promotion
        """
        self.db_path = db_path
        self.kill_config = kill_config or KillSwitchConfig()
        self.promotion_criteria = promotion_criteria or PromotionCriteria()
        
        # In-memory storage (backed by database)
        self.trades: Dict[str, List[Trade]] = defaultdict(list)
        self.strategies: Dict[str, Dict] = {}
        self.metrics_cache: Dict[str, StrategyMetrics] = {}
        
        # Initialize database
        self._init_database()
        
        # Load existing data
        self._load_from_database()
        
        logger.info(f"StrategyValidator initialized with database: {db_path}")
    
    def _init_database(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Strategies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                strategy_id TEXT PRIMARY KEY,
                stage TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                disabled_at TEXT,
                kill_reason TEXT,
                metadata TEXT
            )
        ''')
        
        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                strategy_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                pnl REAL NOT NULL,
                pnl_pct REAL NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                holding_period INTEGER NOT NULL,
                market_regime TEXT,
                FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
            )
        ''')
        
        # Metrics history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metrics TEXT NOT NULL,
                FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
            )
        ''')
        
        # Kill switch events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kill_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                kill_reason TEXT NOT NULL,
                metrics_at_kill TEXT NOT NULL,
                FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
            )
        ''')
        
        # Promotion events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promotion_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                from_stage TEXT NOT NULL,
                to_stage TEXT NOT NULL,
                metrics_at_promotion TEXT NOT NULL,
                FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
            )
        ''')
        
        # Monte Carlo results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monte_carlo_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                num_simulations INTEGER NOT NULL,
                results TEXT NOT NULL,
                is_robust BOOLEAN NOT NULL,
                FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database schema initialized")
    
    def _load_from_database(self):
        """Load existing strategies and trades from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load strategies
        cursor.execute("SELECT * FROM strategies")
        for row in cursor.fetchall():
            strategy_id, stage, created_at, updated_at, disabled_at, kill_reason, metadata = row
            self.strategies[strategy_id] = {
                'strategy_id': strategy_id,
                'stage': StrategyStage(stage),
                'created_at': datetime.fromisoformat(created_at),
                'updated_at': datetime.fromisoformat(updated_at),
                'disabled_at': datetime.fromisoformat(disabled_at) if disabled_at else None,
                'kill_reason': KillReason(kill_reason) if kill_reason else None,
                'metadata': json.loads(metadata) if metadata else {}
            }
        
        # Load trades
        cursor.execute("SELECT * FROM trades ORDER BY timestamp")
        for row in cursor.fetchall():
            trade = Trade(
                trade_id=row[0],
                strategy_id=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                pnl=row[3],
                pnl_pct=row[4],
                direction=row[5],
                entry_price=row[6],
                exit_price=row[7],
                holding_period=row[8],
                market_regime=row[9] if row[9] else "unknown"
            )
            self.trades[trade.strategy_id].append(trade)
        
        conn.close()
        logger.info(f"Loaded {len(self.strategies)} strategies and {sum(len(t) for t in self.trades.values())} trades")
    
    def register_strategy(self, strategy_id: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Register a new strategy in the incubator stage.
        
        Args:
            strategy_id: Unique identifier for the strategy
            metadata: Optional metadata dictionary
            
        Returns:
            Strategy info dictionary
        """
        if strategy_id in self.strategies:
            logger.warning(f"Strategy {strategy_id} already registered")
            return self.strategies[strategy_id]
        
        now = datetime.now()
        strategy_info = {
            'strategy_id': strategy_id,
            'stage': StrategyStage.INCUBATOR,
            'created_at': now,
            'updated_at': now,
            'disabled_at': None,
            'kill_reason': None,
            'metadata': metadata or {}
        }
        
        self.strategies[strategy_id] = strategy_info
        
        # Persist to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO strategies (strategy_id, stage, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (strategy_id, StrategyStage.INCUBATOR.value, now.isoformat(), 
              now.isoformat(), json.dumps(metadata or {})))
        conn.commit()
        conn.close()
        
        logger.info(f"Registered new strategy {strategy_id} in INCUBATOR stage")
        return strategy_info
    
    def record_trade(self, trade: Trade) -> Tuple[StrategyMetrics, Optional[KillReason]]:
        """
        Record a new trade and update metrics.
        
        Args:
            trade: Trade object to record
            
        Returns:
            Tuple of (updated metrics, kill reason if triggered)
        """
        # Ensure strategy exists
        if trade.strategy_id not in self.strategies:
            self.register_strategy(trade.strategy_id)
        
        # Check if strategy is disabled
        if self.strategies[trade.strategy_id]['stage'] == StrategyStage.DISABLED:
            logger.warning(f"Trade recorded for disabled strategy {trade.strategy_id}")
        
        # Add to memory
        self.trades[trade.strategy_id].append(trade)
        
        # Persist to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO trades 
            (trade_id, strategy_id, timestamp, pnl, pnl_pct, direction, 
             entry_price, exit_price, holding_period, market_regime)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (trade.trade_id, trade.strategy_id, trade.timestamp.isoformat(),
              trade.pnl, trade.pnl_pct, trade.direction, trade.entry_price,
              trade.exit_price, trade.holding_period, trade.market_regime))
        conn.commit()
        conn.close()
        
        # Recalculate metrics
        metrics = self.calculate_metrics(trade.strategy_id)
        
        # Check kill conditions
        kill_reason = self.check_kill_conditions(trade.strategy_id, metrics)
        
        if kill_reason:
            self._disable_strategy(trade.strategy_id, kill_reason, metrics)
        else:
            # Check for promotion
            self._check_promotion(trade.strategy_id, metrics)
        
        return metrics, kill_reason
    
    def calculate_metrics(self, strategy_id: str) -> StrategyMetrics:
        """
        Calculate comprehensive performance metrics for a strategy.
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            StrategyMetrics object
        """
        trades = self.trades.get(strategy_id, [])
        
        if not trades:
            return StrategyMetrics(strategy_id=strategy_id, timestamp=datetime.now())
        
        # Sort trades by timestamp
        trades = sorted(trades, key=lambda t: t.timestamp)
        
        # Extract P&L series
        pnls = np.array([t.pnl for t in trades])
        pnl_pcts = np.array([t.pnl_pct for t in trades])
        
        # Basic counts
        total_trades = len(trades)
        winning_trades = sum(1 for p in pnls if p > 0)
        losing_trades = sum(1 for p in pnls if p <= 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = np.sum(pnls)
        avg_pnl = np.mean(pnls)
        
        wins = pnls[pnls > 0]
        losses = pnls[pnls <= 0]
        
        avg_win = np.mean(wins) if len(wins) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0
        
        # Profit factor
        gross_profit = np.sum(wins)
        gross_loss = abs(np.sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Expectancy
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        
        # Calculate equity curve for drawdown
        equity_curve = np.cumsum(pnls)
        running_max = np.maximum.accumulate(equity_curve)
        drawdowns = equity_curve - running_max
        max_drawdown = np.min(drawdowns)
        max_drawdown_pct = max_drawdown / running_max[np.argmin(drawdowns)] if np.min(drawdowns) < 0 else 0
        current_drawdown = drawdowns[-1]
        
        # Volatility (annualized, assuming daily trades)
        volatility = np.std(pnl_pcts) * np.sqrt(252) if len(pnl_pcts) > 1 else 0
        
        # Downside deviation for Sortino
        downside_returns = pnl_pcts[pnl_pcts < 0]
        downside_deviation = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 1 else 0
        
        # Sharpe ratio (assuming 0 risk-free rate for simplicity)
        sharpe_ratio = (np.mean(pnl_pcts) * 252) / (np.std(pnl_pcts) * np.sqrt(252)) if np.std(pnl_pcts) > 0 else 0
        
        # Sortino ratio
        sortino_ratio = (np.mean(pnl_pcts) * 252) / downside_deviation if downside_deviation > 0 else 0
        
        # Calmar ratio
        calmar_ratio = (np.mean(pnl_pcts) * 252) / abs(max_drawdown_pct) if max_drawdown_pct < 0 else 0
        
        # Statistical significance of win rate (binomial test)
        wr_p_value = self._calculate_wr_significance(winning_trades, total_trades)
        is_statistically_significant = wr_p_value < self.kill_config.significance_level
        
        # Consecutive losses
        consecutive_losses = 0
        max_consecutive_losses = 0
        for pnl in pnls:
            if pnl <= 0:
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            else:
                consecutive_losses = 0
        
        # Recent performance
        last_20 = pnls[-20:] if len(pnls) >= 20 else pnls
        last_50 = pnls[-50:] if len(pnls) >= 50 else pnls
        
        last_20_wr = sum(1 for p in last_20 if p > 0) / len(last_20) if len(last_20) > 0 else 0
        last_50_wr = sum(1 for p in last_50 if p > 0) / len(last_50) if len(last_50) > 0 else 0
        
        metrics = StrategyMetrics(
            strategy_id=strategy_id,
            timestamp=datetime.now(),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_pnl=avg_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            current_drawdown=current_drawdown,
            volatility=volatility,
            downside_deviation=downside_deviation,
            wr_p_value=wr_p_value,
            is_statistically_significant=is_statistically_significant,
            consecutive_losses=consecutive_losses,
            max_consecutive_losses=max_consecutive_losses,
            last_20_trades_wr=last_20_wr,
            last_50_trades_wr=last_50_wr
        )
        
        # Cache metrics
        self.metrics_cache[strategy_id] = metrics
        
        # Persist to database
        self._persist_metrics(strategy_id, metrics)
        
        return metrics
    
    def _calculate_wr_significance(self, wins: int, total: int, null_wr: float = 0.5) -> float:
        """
        Calculate p-value for win rate significance using binomial test.
        
        Args:
            wins: Number of winning trades
            total: Total number of trades
            null_wr: Null hypothesis win rate (default 50%)
            
        Returns:
            p-value
        """
        if total < 10:
            return 1.0
        
        # Two-tailed binomial test
        try:
            p_value = binom_test(wins, total, null_wr, alternative='two-sided')
        except:
            # Fallback to normal approximation for large n
            p = wins / total
            se = np.sqrt(null_wr * (1 - null_wr) / total)
            z = (p - null_wr) / se
            p_value = 2 * (1 - norm.cdf(abs(z)))
        
        return p_value
    
    def _persist_metrics(self, strategy_id: str, metrics: StrategyMetrics):
        """Persist metrics to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO metrics_history (strategy_id, timestamp, metrics)
            VALUES (?, ?, ?)
        ''', (strategy_id, metrics.timestamp.isoformat(), json.dumps(metrics.to_dict())))
        conn.commit()
        conn.close()
    
    def check_kill_conditions(self, strategy_id: str, metrics: StrategyMetrics) -> Optional[KillReason]:
        """
        Check if any kill switch conditions are triggered.
        
        Args:
            strategy_id: Strategy identifier
            metrics: Current strategy metrics
            
        Returns:
            KillReason if triggered, None otherwise
        """
        config = self.kill_config
        
        # Minimum trades check
        if metrics.total_trades < config.min_trades_for_kill:
            return None
        
        # Win rate check
        if metrics.total_trades >= config.wr_min_trades:
            if metrics.win_rate < config.wr_threshold:
                logger.warning(f"Kill switch: WR {metrics.win_rate:.2%} < {config.wr_threshold:.2%}")
                return KillReason.WIN_RATE_THRESHOLD
        
        # Sharpe ratio check
        if metrics.total_trades >= config.sharpe_min_trades:
            if metrics.sharpe_ratio < config.sharpe_threshold:
                logger.warning(f"Kill switch: Sharpe {metrics.sharpe_ratio:.2f} < {config.sharpe_threshold:.2f}")
                return KillReason.SHARPE_THRESHOLD
        
        # Sortino ratio check
        if metrics.total_trades >= config.sortino_min_trades:
            if metrics.sortino_ratio < config.sortino_threshold:
                logger.warning(f"Kill switch: Sortino {metrics.sortino_ratio:.2f} < {config.sortino_threshold:.2f}")
                return KillReason.SORTINO_THRESHOLD
        
        # Max drawdown check
        if metrics.max_drawdown_pct < config.max_drawdown_pct:
            logger.warning(f"Kill switch: Max DD {metrics.max_drawdown_pct:.2%} < {config.max_drawdown_pct:.2%}")
            return KillReason.MAX_DRAWDOWN
        
        # Profit factor check
        if metrics.total_trades >= 30 and metrics.profit_factor < config.profit_factor_threshold:
            logger.warning(f"Kill switch: Profit Factor {metrics.profit_factor:.2f} < {config.profit_factor_threshold:.2f}")
            return KillReason.PROFIT_FACTOR
        
        # Consecutive losses check
        if metrics.consecutive_losses >= config.max_consecutive_losses:
            logger.warning(f"Kill switch: Consecutive losses {metrics.consecutive_losses}")
            return KillReason.CONSECUTIVE_LOSSES
        
        # Statistical significance check
        if config.require_statistical_significance and metrics.total_trades >= 50:
            if not metrics.is_statistically_significant and metrics.win_rate < 0.5:
                logger.warning(f"Kill switch: Statistically invalid WR")
                return KillReason.STATISTICAL_INVALID
        
        return None
    
    def _disable_strategy(self, strategy_id: str, kill_reason: KillReason, metrics: StrategyMetrics):
        """Disable a strategy due to kill switch."""
        self.strategies[strategy_id]['stage'] = StrategyStage.DISABLED
        self.strategies[strategy_id]['disabled_at'] = datetime.now()
        self.strategies[strategy_id]['kill_reason'] = kill_reason
        self.strategies[strategy_id]['updated_at'] = datetime.now()
        
        # Persist to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE strategies 
            SET stage = ?, disabled_at = ?, kill_reason = ?, updated_at = ?
            WHERE strategy_id = ?
        ''', (StrategyStage.DISABLED.value, datetime.now().isoformat(),
              kill_reason.value, datetime.now().isoformat(), strategy_id))
        
        cursor.execute('''
            INSERT INTO kill_events (strategy_id, timestamp, kill_reason, metrics_at_kill)
            VALUES (?, ?, ?, ?)
        ''', (strategy_id, datetime.now().isoformat(), kill_reason.value,
              json.dumps(metrics.to_dict())))
        
        conn.commit()
        conn.close()
        
        logger.warning(f"Strategy {strategy_id} DISABLED due to {kill_reason.value}")
    
    def _check_promotion(self, strategy_id: str, metrics: StrategyMetrics):
        """Check if strategy should be promoted to next stage."""
        current_stage = self.strategies[strategy_id]['stage']
        criteria = self.promotion_criteria
        
        new_stage = None
        
        if current_stage == StrategyStage.INCUBATOR:
            if (metrics.total_trades >= criteria.sandbox_min_trades and
                metrics.win_rate >= criteria.sandbox_min_wr and
                metrics.max_drawdown_pct >= criteria.sandbox_max_drawdown):
                new_stage = StrategyStage.SANDBOX
        
        elif current_stage == StrategyStage.SANDBOX:
            if (metrics.total_trades >= criteria.fresh_picks_min_trades and
                metrics.win_rate >= criteria.fresh_picks_min_wr and
                metrics.sharpe_ratio >= criteria.fresh_picks_min_sharpe and
                metrics.max_drawdown_pct >= criteria.fresh_picks_max_drawdown):
                new_stage = StrategyStage.FRESH_PICKS
        
        elif current_stage == StrategyStage.FRESH_PICKS:
            if (metrics.total_trades >= criteria.live_min_trades and
                metrics.win_rate >= criteria.live_min_wr and
                metrics.sharpe_ratio >= criteria.live_min_sharpe and
                metrics.sortino_ratio >= criteria.live_min_sortino and
                metrics.max_drawdown_pct >= criteria.live_max_drawdown and
                metrics.profit_factor >= criteria.live_min_profit_factor):
                
                if (not criteria.live_require_statistical_significance or 
                    metrics.is_statistically_significant):
                    new_stage = StrategyStage.LIVE
        
        if new_stage:
            old_stage = self.strategies[strategy_id]['stage']
            self.strategies[strategy_id]['stage'] = new_stage
            self.strategies[strategy_id]['updated_at'] = datetime.now()
            
            # Persist promotion event
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE strategies SET stage = ?, updated_at = ? WHERE strategy_id = ?
            ''', (new_stage.value, datetime.now().isoformat(), strategy_id))
            
            cursor.execute('''
                INSERT INTO promotion_events (strategy_id, timestamp, from_stage, to_stage, metrics_at_promotion)
                VALUES (?, ?, ?, ?, ?)
            ''', (strategy_id, datetime.now().isoformat(), old_stage.value,
                  new_stage.value, json.dumps(metrics.to_dict())))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Strategy {strategy_id} promoted from {old_stage.value} to {new_stage.value}")
    
    def monte_carlo_sim(self, 
                        strategy_id: str, 
                        num_simulations: int = 1000,
                        confidence_level: float = 0.95) -> Dict:
        """
        Perform Monte Carlo simulation to test strategy robustness.
        
        Args:
            strategy_id: Strategy identifier
            num_simulations: Number of Monte Carlo simulations
            confidence_level: Confidence level for intervals
            
        Returns:
            Dictionary with simulation results
        """
        trades = self.trades.get(strategy_id, [])
        if len(trades) < 30:
            return {'error': 'Insufficient trades for Monte Carlo simulation (minimum 30)'}
        
        pnls = np.array([t.pnl for t in trades])
        
        # Bootstrap resampling
        np.random.seed(42)
        simulation_results = []
        
        for _ in range(num_simulations):
            # Resample trades with replacement
            resampled = np.random.choice(pnls, size=len(pnls), replace=True)
            
            # Calculate metrics for this simulation
            total_pnl = np.sum(resampled)
            win_rate = np.mean(resampled > 0)
            sharpe = np.mean(resampled) / np.std(resampled) if np.std(resampled) > 0 else 0
            
            # Calculate max drawdown
            equity = np.cumsum(resampled)
            running_max = np.maximum.accumulate(equity)
            drawdown = np.min(equity - running_max)
            
            simulation_results.append({
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'sharpe': sharpe,
                'max_drawdown': drawdown
            })
        
        # Aggregate results
        sim_df = pd.DataFrame(simulation_results)
        
        alpha = 1 - confidence_level
        results = {
            'strategy_id': strategy_id,
            'num_simulations': num_simulations,
            'num_trades': len(trades),
            'confidence_level': confidence_level,
            'total_pnl': {
                'mean': sim_df['total_pnl'].mean(),
                'std': sim_df['total_pnl'].std(),
                'median': sim_df['total_pnl'].median(),
                'ci_lower': sim_df['total_pnl'].quantile(alpha/2),
                'ci_upper': sim_df['total_pnl'].quantile(1 - alpha/2),
                'prob_profit': (sim_df['total_pnl'] > 0).mean()
            },
            'win_rate': {
                'mean': sim_df['win_rate'].mean(),
                'std': sim_df['win_rate'].std(),
                'ci_lower': sim_df['win_rate'].quantile(alpha/2),
                'ci_upper': sim_df['win_rate'].quantile(1 - alpha/2),
                'prob_above_50': (sim_df['win_rate'] > 0.5).mean()
            },
            'sharpe': {
                'mean': sim_df['sharpe'].mean(),
                'std': sim_df['sharpe'].std(),
                'ci_lower': sim_df['sharpe'].quantile(alpha/2),
                'ci_upper': sim_df['sharpe'].quantile(1 - alpha/2),
                'prob_positive': (sim_df['sharpe'] > 0).mean()
            },
            'max_drawdown': {
                'mean': sim_df['max_drawdown'].mean(),
                'worst': sim_df['max_drawdown'].min(),
                'ci_lower': sim_df['max_drawdown'].quantile(alpha/2),
                'ci_upper': sim_df['max_drawdown'].quantile(1 - alpha/2)
            }
        }
        
        # Robustness assessment
        is_robust = bool(
            results['total_pnl']['prob_profit'] > 0.8 and
            results['win_rate']['prob_above_50'] > 0.7 and
            results['sharpe']['prob_positive'] > 0.8
        )
        
        results['is_robust'] = is_robust
        results['robustness_score'] = float(
            results['total_pnl']['prob_profit'] * 0.4 +
            results['win_rate']['prob_above_50'] * 0.3 +
            results['sharpe']['prob_positive'] * 0.3
        )
        
        # Convert all numpy types to Python native types for JSON serialization
        def convert_to_native(obj):
            if isinstance(obj, dict):
                return {k: convert_to_native(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_native(item) for item in obj]
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        results_native = convert_to_native(results)
        
        # Persist results
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO monte_carlo_results (strategy_id, timestamp, num_simulations, results, is_robust)
            VALUES (?, ?, ?, ?, ?)
        ''', (strategy_id, datetime.now().isoformat(), num_simulations,
              json.dumps(results_native), is_robust))
        conn.commit()
        conn.close()
        
        return results_native
    
    def get_metrics(self, strategy_id: str) -> Optional[StrategyMetrics]:
        """Get cached metrics for a strategy."""
        if strategy_id in self.metrics_cache:
            return self.metrics_cache[strategy_id]
        return self.calculate_metrics(strategy_id)
    
    def get_strategy_info(self, strategy_id: str) -> Optional[Dict]:
        """Get strategy information."""
        return self.strategies.get(strategy_id)
    
    def get_all_strategies(self, stage: Optional[StrategyStage] = None) -> List[Dict]:
        """Get all strategies, optionally filtered by stage."""
        if stage:
            return [s for s in self.strategies.values() if s['stage'] == stage]
        return list(self.strategies.values())
    
    def manual_disable(self, strategy_id: str, reason: str = "Manual disable"):
        """Manually disable a strategy."""
        metrics = self.get_metrics(strategy_id)
        self._disable_strategy(strategy_id, KillReason.MANUAL_DISABLE, metrics)
    
    def manual_promote(self, strategy_id: str, to_stage: StrategyStage):
        """Manually promote a strategy (use with caution)."""
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        old_stage = self.strategies[strategy_id]['stage']
        self.strategies[strategy_id]['stage'] = to_stage
        self.strategies[strategy_id]['updated_at'] = datetime.now()
        
        metrics = self.get_metrics(strategy_id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE strategies SET stage = ?, updated_at = ? WHERE strategy_id = ?
        ''', (to_stage.value, datetime.now().isoformat(), strategy_id))
        
        cursor.execute('''
            INSERT INTO promotion_events (strategy_id, timestamp, from_stage, to_stage, metrics_at_promotion)
            VALUES (?, ?, ?, ?, ?)
        ''', (strategy_id, datetime.now().isoformat(), old_stage.value,
              to_stage.value, json.dumps(metrics.to_dict() if metrics else {})))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Strategy {strategy_id} manually promoted from {old_stage.value} to {to_stage.value}")


class FalseDiscoveryRateControl:
    """
    Controls false discovery rate when testing multiple strategies.
    Implements Benjamini-Hochberg and Benjamini-Yekutieli procedures.
    """
    
    @staticmethod
    def benjamini_hochberg(p_values: Dict[str, float], 
                           alpha: float = 0.05) -> Dict[str, bool]:
        """
        Apply Benjamini-Hochberg procedure to control FDR.
        
        Args:
            p_values: Dictionary mapping strategy_id to p-value
            alpha: Desired false discovery rate
            
        Returns:
            Dictionary mapping strategy_id to rejection decision
        """
        m = len(p_values)
        if m == 0:
            return {}
        
        # Sort p-values
        sorted_items = sorted(p_values.items(), key=lambda x: x[1])
        
        # Find largest k such that p(k) <= (k/m) * alpha
        k = 0
        for i, (strategy_id, p) in enumerate(sorted_items, 1):
            if p <= (i / m) * alpha:
                k = i
        
        # Reject null hypotheses for the k smallest p-values
        rejections = {strategy_id: (i < k) for i, (strategy_id, _) in enumerate(sorted_items)}
        
        return rejections
    
    @staticmethod
    def benjamini_yekutieli(p_values: Dict[str, float], 
                            alpha: float = 0.05) -> Dict[str, bool]:
        """
        Apply Benjamini-Yekutieli procedure (works under arbitrary dependence).
        
        Args:
            p_values: Dictionary mapping strategy_id to p-value
            alpha: Desired false discovery rate
            
        Returns:
            Dictionary mapping strategy_id to rejection decision
        """
        m = len(p_values)
        if m == 0:
            return {}
        
        # Calculate harmonic sum
        c_m = sum(1 / i for i in range(1, m + 1))
        
        # Sort p-values
        sorted_items = sorted(p_values.items(), key=lambda x: x[1])
        
        # Find largest k such that p(k) <= (k/m) * (alpha / c_m)
        k = 0
        for i, (strategy_id, p) in enumerate(sorted_items, 1):
            if p <= (i / m) * (alpha / c_m):
                k = i
        
        rejections = {strategy_id: (i < k) for i, (strategy_id, _) in enumerate(sorted_items)}
        
        return rejections
    
    @staticmethod
    def bonferroni(p_values: Dict[str, float], 
                   alpha: float = 0.05) -> Dict[str, bool]:
        """
        Apply Bonferroni correction (controls family-wise error rate).
        
        Args:
            p_values: Dictionary mapping strategy_id to p-value
            alpha: Significance level
            
        Returns:
            Dictionary mapping strategy_id to rejection decision
        """
        m = len(p_values)
        adjusted_alpha = alpha / m if m > 0 else alpha
        
        return {sid: (p < adjusted_alpha) for sid, p in p_values.items()}


class WalkForwardAnalysis:
    """
    Walk-forward analysis framework for strategy validation.
    """
    
    def __init__(self, validator: StrategyValidator):
        self.validator = validator
    
    def perform_wfa(self,
                    strategy_id: str,
                    train_size: int = 50,
                    test_size: int = 20,
                    step_size: int = 10) -> Dict:
        """
        Perform walk-forward analysis on a strategy.
        
        Args:
            strategy_id: Strategy identifier
            train_size: Number of trades in training window
            test_size: Number of trades in test window
            step_size: Number of trades to step forward
            
        Returns:
            Dictionary with WFA results
        """
        trades = self.validator.trades.get(strategy_id, [])
        if len(trades) < train_size + test_size:
            return {'error': f'Insufficient trades. Need {train_size + test_size}, have {len(trades)}'}
        
        trades = sorted(trades, key=lambda t: t.timestamp)
        pnls = [t.pnl for t in trades]
        
        windows = []
        window_results = []
        
        # Slide window through data
        for start in range(0, len(pnls) - train_size - test_size + 1, step_size):
            train_start = start
            train_end = start + train_size
            test_start = train_end
            test_end = test_start + test_size
            
            if test_end > len(pnls):
                break
            
            train_pnls = pnls[train_start:train_end]
            test_pnls = pnls[test_start:test_end]
            
            # Calculate metrics for train and test
            train_wr = sum(1 for p in train_pnls if p > 0) / len(train_pnls)
            test_wr = sum(1 for p in test_pnls if p > 0) / len(test_pnls)
            
            train_sharpe = np.mean(train_pnls) / np.std(train_pnls) if np.std(train_pnls) > 0 else 0
            test_sharpe = np.mean(test_pnls) / np.std(test_pnls) if np.std(test_pnls) > 0 else 0
            
            train_pnl = sum(train_pnls)
            test_pnl = sum(test_pnls)
            
            windows.append({
                'train_start': train_start,
                'train_end': train_end,
                'test_start': test_start,
                'test_end': test_end
            })
            
            window_results.append({
                'train_wr': train_wr,
                'test_wr': test_wr,
                'train_sharpe': train_sharpe,
                'test_sharpe': test_sharpe,
                'train_pnl': train_pnl,
                'test_pnl': test_pnl,
                'wr_consistency': abs(train_wr - test_wr) < 0.1,
                'sharpe_consistency': abs(train_sharpe - test_sharpe) < 0.5
            })
        
        # Aggregate results
        if not window_results:
            return {'error': 'No valid windows generated'}
        
        results_df = pd.DataFrame(window_results)
        
        results = {
            'strategy_id': strategy_id,
            'num_windows': len(window_results),
            'train_size': train_size,
            'test_size': test_size,
            'step_size': step_size,
            'win_rate': {
                'train_mean': results_df['train_wr'].mean(),
                'test_mean': results_df['test_wr'].mean(),
                'consistency_rate': results_df['wr_consistency'].mean()
            },
            'sharpe': {
                'train_mean': results_df['train_sharpe'].mean(),
                'test_mean': results_df['test_sharpe'].mean(),
                'consistency_rate': results_df['sharpe_consistency'].mean()
            },
            'pnl': {
                'train_total': results_df['train_pnl'].sum(),
                'test_total': results_df['test_pnl'].sum(),
                'out_of_sample_ratio': results_df['test_pnl'].sum() / abs(results_df['train_pnl'].sum()) if results_df['train_pnl'].sum() != 0 else 0
            },
            'is_consistent': (
                results_df['wr_consistency'].mean() > 0.7 and
                results_df['sharpe_consistency'].mean() > 0.7
            )
        }
        
        return results
    
    def cross_validate_strategies(self,
                                   strategy_ids: List[str],
                                   min_windows: int = 3) -> Dict[str, Dict]:
        """
        Perform walk-forward analysis on multiple strategies.
        
        Args:
            strategy_ids: List of strategy identifiers
            min_windows: Minimum number of windows required
            
        Returns:
            Dictionary mapping strategy_id to WFA results
        """
        results = {}
        
        for sid in strategy_ids:
            wfa_result = self.perform_wfa(sid)
            if 'error' not in wfa_result and wfa_result['num_windows'] >= min_windows:
                results[sid] = wfa_result
        
        return results


class StrategyDashboard:
    """
    Dashboard for monitoring strategy performance and pipeline status.
    """
    
    def __init__(self, validator: StrategyValidator):
        self.validator = validator
    
    def get_pipeline_summary(self) -> Dict:
        """Get summary of strategies in each pipeline stage."""
        summary = {stage: [] for stage in StrategyStage}
        
        for strategy_id, info in self.validator.strategies.items():
            stage = info['stage']
            metrics = self.validator.get_metrics(strategy_id)
            
            summary[stage].append({
                'strategy_id': strategy_id,
                'total_trades': metrics.total_trades if metrics else 0,
                'win_rate': metrics.win_rate if metrics else 0,
                'sharpe': metrics.sharpe_ratio if metrics else 0,
                'max_dd': metrics.max_drawdown_pct if metrics else 0,
                'total_pnl': metrics.total_pnl if metrics else 0
            })
        
        return {
            stage.value: {
                'count': len(strategies),
                'strategies': strategies
            }
            for stage, strategies in summary.items()
        }
    
    def get_kill_switch_summary(self) -> Dict:
        """Get summary of kill switch events."""
        conn = sqlite3.connect(self.validator.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT kill_reason, COUNT(*) as count 
            FROM kill_events 
            GROUP BY kill_reason
        ''')
        
        reason_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT strategy_id, timestamp, kill_reason 
            FROM kill_events 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''')
        
        recent_kills = [
            {'strategy_id': row[0], 'timestamp': row[1], 'reason': row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            'total_killed': sum(reason_counts.values()),
            'by_reason': reason_counts,
            'recent_kills': recent_kills
        }
    
    def get_strategies_ready_for_promotion(self) -> Dict[str, List[Dict]]:
        """Get strategies that meet criteria for promotion."""
        ready = {
            'to_sandbox': [],
            'to_fresh_picks': [],
            'to_live': []
        }
        
        for strategy_id, info in self.validator.strategies.items():
            if info['stage'] in [StrategyStage.DISABLED, StrategyStage.ARCHIVED]:
                continue
            
            metrics = self.validator.get_metrics(strategy_id)
            if not metrics:
                continue
            
            criteria = self.validator.promotion_criteria
            
            if info['stage'] == StrategyStage.INCUBATOR:
                if (metrics.total_trades >= criteria.sandbox_min_trades and
                    metrics.win_rate >= criteria.sandbox_min_wr):
                    ready['to_sandbox'].append({
                        'strategy_id': strategy_id,
                        'metrics': metrics.to_dict()
                    })
            
            elif info['stage'] == StrategyStage.SANDBOX:
                if (metrics.total_trades >= criteria.fresh_picks_min_trades and
                    metrics.win_rate >= criteria.fresh_picks_min_wr and
                    metrics.sharpe_ratio >= criteria.fresh_picks_min_sharpe):
                    ready['to_fresh_picks'].append({
                        'strategy_id': strategy_id,
                        'metrics': metrics.to_dict()
                    })
            
            elif info['stage'] == StrategyStage.FRESH_PICKS:
                if (metrics.total_trades >= criteria.live_min_trades and
                    metrics.win_rate >= criteria.live_min_wr and
                    metrics.sharpe_ratio >= criteria.live_min_sharpe):
                    ready['to_live'].append({
                        'strategy_id': strategy_id,
                        'metrics': metrics.to_dict()
                    })
        
        return ready


# ==================== USAGE EXAMPLES ====================

def example_usage():
    """Example usage of the StrategyValidator system."""
    import uuid
    
    # Initialize validator with custom configuration
    kill_config = KillSwitchConfig(
        wr_threshold=0.40,  # More lenient for demo
        sharpe_threshold=0.5,
        max_drawdown_pct=-0.30,  # More lenient for demo
        min_trades_for_kill=50
    )
    
    promotion_criteria = PromotionCriteria(
        sandbox_min_trades=50,
        live_min_trades=200,
        live_min_wr=0.52,
        live_min_sharpe=1.0
    )
    
    validator = StrategyValidator(
        db_path=f"/mnt/okcomputer/output/strategy_validation_{uuid.uuid4().hex[:8]}.db",
        kill_config=kill_config,
        promotion_criteria=promotion_criteria
    )
    
    # Register a new strategy with unique ID
    strategy_id = f"strategy_demo_{uuid.uuid4().hex[:6]}"
    validator.register_strategy(strategy_id, metadata={
        "type": "momentum",
        "timeframe": "1h",
        "symbols": ["BTC-USD", "ETH-USD"]
    })
    
    # Simulate recording trades
    np.random.seed(42)
    
    for i in range(250):
        # Simulate trade P&L (profitable strategy with some variance)
        pnl = np.random.normal(15, 40)  # Positive mean = profitable
        
        trade = Trade(
            trade_id=f"trade_{i:04d}",
            strategy_id=strategy_id,
            timestamp=datetime.now() - timedelta(days=250-i),
            pnl=pnl,
            pnl_pct=pnl / 1000,
            direction="long" if i % 2 == 0 else "short",
            entry_price=50000 + i * 10,
            exit_price=50000 + i * 10 + pnl,
            holding_period=60,
            market_regime="trending" if i % 3 == 0 else "ranging"
        )
        
        metrics, kill_reason = validator.record_trade(trade)
        
        if kill_reason:
            print(f"Trade {i}: Strategy KILLED - {kill_reason.value}")
            break
    
    # Get final metrics
    final_metrics = validator.get_metrics(strategy_id)
    print(f"\nFinal Metrics for {strategy_id}:")
    print(f"  Stage: {validator.get_strategy_info(strategy_id)['stage'].value}")
    print(f"  Total Trades: {final_metrics.total_trades}")
    print(f"  Win Rate: {final_metrics.win_rate:.2%}")
    print(f"  Sharpe: {final_metrics.sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {final_metrics.max_drawdown_pct:.2%}")
    print(f"  Statistically Significant: {final_metrics.is_statistically_significant}")
    print(f"  WR p-value: {final_metrics.wr_p_value:.4f}")
    
    # Run Monte Carlo simulation
    print("\nRunning Monte Carlo simulation...")
    mc_results = validator.monte_carlo_sim(strategy_id, num_simulations=1000)
    if 'error' in mc_results:
        print(f"  Error: {mc_results['error']}")
    else:
        print(f"  Is Robust: {mc_results.get('is_robust', 'N/A')}")
        print(f"  Robustness Score: {mc_results.get('robustness_score', 0):.2%}")
        print(f"  Prob Profit: {mc_results['total_pnl']['prob_profit']:.2%}")
    
    # Walk-forward analysis
    print("\nRunning Walk-Forward Analysis...")
    wfa = WalkForwardAnalysis(validator)
    wfa_results = wfa.perform_wfa(strategy_id, train_size=50, test_size=20, step_size=10)
    print(f"  Num Windows: {wfa_results.get('num_windows', 'N/A')}")
    print(f"  Is Consistent: {wfa_results.get('is_consistent', 'N/A')}")
    
    # Dashboard summary
    print("\nPipeline Summary:")
    dashboard = StrategyDashboard(validator)
    summary = dashboard.get_pipeline_summary()
    for stage, data in summary.items():
        if data['count'] > 0:
            print(f"  {stage}: {data['count']} strategies")
    
    return validator


def test_multiple_strategies():
    """Test with multiple strategies to demonstrate FDR control."""
    
    validator = StrategyValidator(
        db_path="/mnt/okcomputer/output/strategy_validation_fdr.db"
    )
    
    # Create 20 strategies with varying performance
    np.random.seed(123)
    
    for s in range(20):
        strategy_id = f"strategy_fdr_{s:03d}"
        validator.register_strategy(strategy_id, metadata={"test": True})
        
        # Vary performance - some good, some bad
        if s < 5:  # Good strategies
            mean_pnl = 20
        elif s < 10:  # Okay strategies
            mean_pnl = 5
        elif s < 15:  # Poor strategies
            mean_pnl = -5
        else:  # Bad strategies
            mean_pnl = -15
        
        for i in range(100):
            pnl = np.random.normal(mean_pnl, 40)
            trade = Trade(
                trade_id=f"trade_{i:04d}",
                strategy_id=strategy_id,
                timestamp=datetime.now() - timedelta(days=100-i),
                pnl=pnl,
                pnl_pct=pnl / 1000,
                direction="long",
                entry_price=100,
                exit_price=100 + pnl,
                holding_period=30
            )
            validator.record_trade(trade)
    
    # Collect p-values for FDR control
    p_values = {}
    for s in range(20):
        strategy_id = f"strategy_fdr_{s:03d}"
        metrics = validator.get_metrics(strategy_id)
        p_values[strategy_id] = metrics.wr_p_value
    
    # Apply FDR control
    print("\nFalse Discovery Rate Control:")
    print(f"  Total strategies: {len(p_values)}")
    
    bh_results = FalseDiscoveryRateControl.benjamini_hochberg(p_values, alpha=0.05)
    by_results = FalseDiscoveryRateControl.benjamini_yekutieli(p_values, alpha=0.05)
    bonferroni_results = FalseDiscoveryRateControl.bonferroni(p_values, alpha=0.05)
    
    print(f"  Benjamini-Hochberg rejections: {sum(bh_results.values())}")
    print(f"  Benjamini-Yekutieli rejections: {sum(by_results.values())}")
    print(f"  Bonferroni rejections: {sum(bonferroni_results.values())}")
    
    # Dashboard
    dashboard = StrategyDashboard(validator)
    summary = dashboard.get_pipeline_summary()
    print("\nPipeline Status:")
    for stage, data in summary.items():
        print(f"  {stage}: {data['count']} strategies")
    
    return validator, p_values


def test_kill_switches():
    """Test kill switch functionality with a failing strategy."""
    
    validator = StrategyValidator(
        db_path="/mnt/okcomputer/output/strategy_validation_kill.db",
        kill_config=KillSwitchConfig(
            wr_threshold=0.45,
            min_trades_for_kill=30,
            max_consecutive_losses=8
        )
    )
    
    # Register a strategy that will fail
    validator.register_strategy("strategy_doomed", metadata={"test": "kill_switch"})
    
    np.random.seed(999)
    
    kill_triggered = False
    for i in range(100):
        # Simulate losing trades
        pnl = np.random.normal(-20, 30)  # Negative mean = losing strategy
        
        trade = Trade(
            trade_id=f"trade_{i:04d}",
            strategy_id="strategy_doomed",
            timestamp=datetime.now() - timedelta(days=100-i),
            pnl=pnl,
            pnl_pct=pnl / 1000,
            direction="long",
            entry_price=100,
            exit_price=100 + pnl,
            holding_period=30
        )
        
        metrics, kill_reason = validator.record_trade(trade)
        
        if kill_reason and not kill_triggered:
            print(f"\nKill switch triggered at trade {i}!")
            print(f"  Reason: {kill_reason.value}")
            print(f"  Win Rate at kill: {metrics.win_rate:.2%}")
            print(f"  Total Trades: {metrics.total_trades}")
            kill_triggered = True
    
    # Check final status
    info = validator.get_strategy_info("strategy_doomed")
    print(f"\nFinal Status: {info['stage'].value}")
    if info['kill_reason']:
        print(f"Kill Reason: {info['kill_reason'].value}")
    
    return validator


if __name__ == "__main__":
    print("=" * 60)
    print("STRATEGY VALIDATION SYSTEM - TEST SUITE")
    print("=" * 60)
    
    print("\n1. Testing Basic Strategy Validation...")
    print("-" * 40)
    validator1 = example_usage()
    
    print("\n\n2. Testing Multiple Strategies with FDR Control...")
    print("-" * 40)
    validator2, p_values = test_multiple_strategies()
    
    print("\n\n3. Testing Kill Switches...")
    print("-" * 40)
    validator3 = test_kill_switches()
    
    print("\n\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY")
    print("=" * 60)
