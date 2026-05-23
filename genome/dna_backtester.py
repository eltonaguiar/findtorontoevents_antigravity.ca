"""
DNA Backtester Module
=====================
Walk-forward backtesting for DNA strategy combinations with:
- Symbol-specific optimization
- Regime-aware testing
- Phoenix revival detection
- Comprehensive performance metrics
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

_GENOME_DIR = Path(__file__).resolve().parent
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import pandas as pd

try:
    from .dna_engine import (
        StrategyDNA, DNAPermutationEngine, FitnessScore,
        MarketRegime, CombinationLogic
    )
except ImportError:
    from dna_engine import (
        StrategyDNA, DNAPermutationEngine, FitnessScore,
        MarketRegime, CombinationLogic
    )

# Configure logging
import os as _os
_log_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'logs')
_os.makedirs(_log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(_os.path.join(_log_dir, 'dna_backtester.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DNABacktester')


@dataclass
class Trade:
    """Represents a single trade."""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    direction: str = "LONG"  # LONG or SHORT
    size: float = 1.0
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    exit_reason: Optional[str] = None
    strategy_dna: Optional[str] = None
    
    def close(self, exit_time: datetime, exit_price: float, reason: str):
        """Close the trade and calculate P&L."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason
        
        if self.direction == "LONG":
            self.pnl = (exit_price - self.entry_price) * self.size
            self.pnl_pct = (exit_price - self.entry_price) / self.entry_price
        else:
            self.pnl = (self.entry_price - exit_price) * self.size
            self.pnl_pct = (self.entry_price - exit_price) / self.entry_price


@dataclass
class BacktestResult:
    """Comprehensive backtest results for a strategy."""
    strategy_dna: StrategyDNA
    symbol: str
    start_date: datetime
    end_date: datetime
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_trade: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Returns
    total_return: float = 0.0
    total_return_pct: float = 0.0
    annualized_return: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    volatility: float = 0.0
    
    # Ratios
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    omega_ratio: float = 0.0
    
    # Regime-specific results
    regime_performance: Dict[str, Dict] = None
    
    # Additional metrics
    expectancy: float = 0.0
    sqn: float = 0.0  # System Quality Number
    ulcer_index: float = 0.0
    
    # Trade list
    trades: List[Trade] = None
    equity_curve: List[float] = None
    
    def __post_init__(self):
        if self.regime_performance is None:
            self.regime_performance = {}
        if self.trades is None:
            self.trades = []
        if self.equity_curve is None:
            self.equity_curve = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'strategy_id': self.strategy_dna.strategy_id,
            'dna_hash': self.strategy_dna.dna_hash,
            'symbol': self.symbol,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate, 4),
            'avg_trade': round(self.avg_trade, 4),
            'avg_win': round(self.avg_win, 4),
            'avg_loss': round(self.avg_loss, 4),
            'profit_factor': round(self.profit_factor, 4),
            'total_return': round(self.total_return, 4),
            'total_return_pct': round(self.total_return_pct, 4),
            'annualized_return': round(self.annualized_return, 4),
            'max_drawdown': round(self.max_drawdown, 4),
            'max_drawdown_pct': round(self.max_drawdown_pct, 4),
            'volatility': round(self.volatility, 4),
            'sharpe_ratio': round(self.sharpe_ratio, 4),
            'sortino_ratio': round(self.sortino_ratio, 4),
            'calmar_ratio': round(self.calmar_ratio, 4),
            'omega_ratio': round(self.omega_ratio, 4),
            'expectancy': round(self.expectancy, 4),
            'sqn': round(self.sqn, 4),
            'ulcer_index': round(self.ulcer_index, 4),
            'regime_performance': self.regime_performance
        }
    
    def to_fitness_score(self) -> FitnessScore:
        """Convert to fitness score for genetic algorithm."""
        return FitnessScore(
            sharpe_ratio=self.sharpe_ratio,
            win_rate=self.win_rate,
            profit_factor=self.profit_factor,
            max_drawdown=self.max_drawdown_pct,
            total_return=self.total_return_pct,
            volatility=self.volatility,
            calmar_ratio=self.calmar_ratio,
            sortino_ratio=self.sortino_ratio,
            omega_ratio=self.omega_ratio
        )


class PhoenixRevivalTracker:
    """
    Tracks failed strategies that may revive under specific conditions.
    
    The Phoenix system identifies strategies that performed poorly overall
    but showed promise in specific regimes or symbols - potential candidates
    for conditional reactivation.
    """
    
    def __init__(self, db_path: str = ""):
        self.db_path = db_path or str(_GENOME_DIR / "phoenix_registry.db")
        self.failed_strategies: Dict[str, Dict] = {}
        self.revival_candidates: List[Dict] = []
        self._init_db()
    
    def _init_db(self):
        """Initialize Phoenix database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phoenix_registry (
                strategy_id TEXT PRIMARY KEY,
                dna_hash TEXT UNIQUE,
                failed_date TEXT,
                reason TEXT,
                last_sharpe REAL,
                best_regime TEXT,
                best_symbol TEXT,
                revival_signals INTEGER DEFAULT 0,
                status TEXT DEFAULT 'dormant',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phoenix_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT,
                signal_date TEXT,
                regime TEXT,
                symbol TEXT,
                expected_edge REAL,
                FOREIGN KEY (strategy_id) REFERENCES phoenix_registry(strategy_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_failure(self, backtest_result: BacktestResult, reason: str = ""):
        """Register a failed strategy for Phoenix tracking."""
        # Only track strategies that failed overall but have some positive aspects
        if backtest_result.sharpe_ratio < 0.5 and backtest_result.win_rate > 0.4:
            
            # Find best regime and symbol
            best_regime = None
            best_symbol = None
            best_regime_sharpe = 0
            
            for regime, metrics in backtest_result.regime_performance.items():
                if metrics.get('sharpe_ratio', 0) > best_regime_sharpe:
                    best_regime_sharpe = metrics['sharpe_ratio']
                    best_regime = regime
            
            entry = {
                'strategy_id': backtest_result.strategy_dna.strategy_id,
                'dna_hash': backtest_result.strategy_dna.dna_hash,
                'failed_date': datetime.utcnow().isoformat(),
                'reason': reason or f"Sharpe: {backtest_result.sharpe_ratio:.2f}",
                'last_sharpe': backtest_result.sharpe_ratio,
                'best_regime': best_regime,
                'best_symbol': backtest_result.symbol,
                'win_rate': backtest_result.win_rate,
                'avg_win': backtest_result.avg_win,
                'avg_loss': backtest_result.avg_loss,
                'regime_performance': backtest_result.regime_performance
            }
            
            self.failed_strategies[entry['strategy_id']] = entry
            
            # Add to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO phoenix_registry 
                (strategy_id, dna_hash, failed_date, reason, last_sharpe, best_regime, best_symbol)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry['strategy_id'], entry['dna_hash'], entry['failed_date'],
                entry['reason'], entry['last_sharpe'], entry['best_regime'], entry['best_symbol']
            ))
            conn.commit()
            conn.close()
            
            logger.info(f"Registered Phoenix candidate: {entry['strategy_id']} (best in {best_regime})")
    
    def check_revival_conditions(
        self,
        strategy_id: str,
        current_regime: MarketRegime,
        symbol: str,
        recent_performance: Optional[Dict] = None
    ) -> Dict:
        """
        Check if a dormant strategy should be revived.
        
        Returns:
            Dict with revival recommendation and confidence
        """
        if strategy_id not in self.failed_strategies:
            return {'should_revive': False, 'reason': 'Not in Phoenix registry'}
        
        strategy = self.failed_strategies[strategy_id]
        
        # Check regime match
        regime_match = strategy['best_regime'] == current_regime.value
        symbol_match = strategy['best_symbol'] == symbol
        
        # Calculate revival score
        score = 0.0
        signals = []
        
        if regime_match:
            regime_metrics = strategy['regime_performance'].get(current_regime.value, {})
            regime_sharpe = regime_metrics.get('sharpe_ratio', 0)
            if regime_sharpe > 1.0:
                score += 0.4
                signals.append(f"Strong regime match (Sharpe: {regime_sharpe:.2f})")
        
        if symbol_match:
            score += 0.3
            signals.append("Symbol specialization match")
        
        if recent_performance:
            if recent_performance.get('win_rate', 0) > 0.55:
                score += 0.2
                signals.append("Recent win rate improvement")
            if recent_performance.get('profit_factor', 0) > 1.5:
                score += 0.1
                signals.append("Recent profit factor improvement")
        
        should_revive = score > 0.5
        
        # Log signal if close to revival
        if score > 0.3:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO phoenix_signals (strategy_id, signal_date, regime, symbol, expected_edge)
                VALUES (?, ?, ?, ?, ?)
            ''', (strategy_id, datetime.utcnow().isoformat(), current_regime.value, symbol, score))
            
            cursor.execute('''
                UPDATE phoenix_registry 
                SET revival_signals = revival_signals + 1
                WHERE strategy_id = ?
            ''', (strategy_id,))
            
            conn.commit()
            conn.close()
        
        return {
            'should_revive': should_revive,
            'revival_score': score,
            'signals': signals,
            'strategy_id': strategy_id,
            'best_regime': strategy['best_regime'],
            'recommended_position_size': min(0.5, score)  # Scale position by confidence
        }
    
    def get_revival_candidates(
        self,
        current_regime: Optional[MarketRegime] = None,
        symbol: Optional[str] = None,
        min_score: float = 0.5
    ) -> List[Dict]:
        """Get all strategies that meet revival conditions."""
        candidates = []
        
        for strategy_id in self.failed_strategies:
            result = self.check_revival_conditions(strategy_id, current_regime or MarketRegime.RANGING, symbol or "")
            if result['should_revive'] and result['revival_score'] >= min_score:
                candidates.append(result)
        
        # Sort by score
        candidates.sort(key=lambda x: x['revival_score'], reverse=True)
        return candidates


class WalkForwardTester:
    """
    Walk-forward analysis for robust strategy validation.
    
    Tests strategies on multiple periods to avoid overfitting.
    """
    
    def __init__(self, train_ratio: float = 0.7, n_splits: int = 5):
        self.train_ratio = train_ratio
        self.n_splits = n_splits
        self.results: List[Dict] = []
    
    def split_data(self, data: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Create walk-forward train/test splits."""
        n_samples = len(data)
        split_size = n_samples // self.n_splits
        splits = []
        
        for i in range(self.n_splits):
            train_end = (i + 1) * split_size
            test_end = min(train_end + int(split_size * (1 - self.train_ratio)), n_samples)
            
            if test_end <= train_end:
                break
            
            train_data = data.iloc[:train_end]
            test_data = data.iloc[train_end:test_end]
            splits.append((train_data, test_data))
        
        return splits
    
    def validate_strategy(
        self,
        strategy: StrategyDNA,
        data: pd.DataFrame,
        backtest_func
    ) -> Dict:
        """
        Run walk-forward validation.
        
        Args:
            strategy: StrategyDNA to validate
            data: Full price data DataFrame
            backtest_func: Function that takes (strategy, data) and returns BacktestResult
            
        Returns:
            Dictionary with walk-forward statistics
        """
        splits = self.split_data(data)
        split_results = []
        
        for i, (train_data, test_data) in enumerate(splits):
            # Train would happen here in a ML context
            # For rule-based strategies, we just test
            result = backtest_func(strategy, test_data)
            split_results.append({
                'split': i,
                'sharpe': result.sharpe_ratio,
                'win_rate': result.win_rate,
                'return': result.total_return_pct,
                'max_dd': result.max_drawdown_pct
            })
        
        # Calculate consistency metrics
        sharpes = [r['sharpe'] for r in split_results]
        win_rates = [r['win_rate'] for r in split_results]
        
        validation = {
            'splits': split_results,
            'avg_sharpe': np.mean(sharpes),
            'sharpe_std': np.std(sharpes),
            'sharpe_consistency': np.mean(sharpes) / (np.std(sharpes) + 1e-6),
            'avg_win_rate': np.mean(win_rates),
            'win_rate_std': np.std(win_rates),
            'profitable_splits': sum(1 for s in sharpes if s > 0),
            'is_robust': np.mean(sharpes) > 0.5 and np.std(sharpes) < 1.0
        }
        
        return validation


class DNABacktester:
    """
    Main backtesting engine for DNA strategy permutations.
    """
    
    def __init__(
        self,
        db_path: str = "",
        phoenix_db_path: str = ""
    ):
        self.db_path = db_path or str(_GENOME_DIR / "dna_backtests.db")
        self.engine = DNAPermutationEngine()
        self.phoenix = PhoenixRevivalTracker(phoenix_db_path)
        self.walk_forward = WalkForwardTester()
        self._init_db()
    
    def _init_db(self):
        """Initialize backtest database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT,
                dna_hash TEXT,
                symbol TEXT,
                start_date TEXT,
                end_date TEXT,
                total_trades INTEGER,
                win_rate REAL,
                profit_factor REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                total_return REAL,
                regime TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(strategy_id, symbol, start_date, end_date)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_id INTEGER,
                entry_time TEXT,
                exit_time TEXT,
                entry_price REAL,
                exit_price REAL,
                direction TEXT,
                pnl REAL,
                pnl_pct REAL,
                exit_reason TEXT,
                FOREIGN KEY (backtest_id) REFERENCES backtests(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def run_backtest(
        self,
        strategy: StrategyDNA,
        data: pd.DataFrame,
        symbol: str,
        initial_capital: float = 10000.0,
        position_size: float = 0.1,
        commission: float = 0.001,
        detect_regimes: bool = True
    ) -> BacktestResult:
        """
        Run a complete backtest for a strategy.
        
        This is a simplified backtester - in production, you'd integrate
        with your existing backtest framework.
        """
        result = BacktestResult(
            strategy_dna=strategy,
            symbol=symbol,
            start_date=data.index[0] if hasattr(data.index[0], 'to_pydatetime') else datetime.now(),
            end_date=data.index[-1] if hasattr(data.index[-1], 'to_pydatetime') else datetime.now()
        )
        
        # Extract strategy parameters
        genes = strategy.genes
        entry_logic = genes.get('entry_logic', 'golden_cross')
        exit_logic = genes.get('exit_logic', 'death_cross')
        
        # Generate signals based on DNA genes
        signals = self._generate_signals(data, genes)
        
        # Simulate trading
        capital = initial_capital
        position = None
        equity_curve = [capital]
        
        for i in range(1, len(data)):
            current_price = data['close'].iloc[i]
            current_time = data.index[i]
            
            # Check exit conditions
            if position:
                should_exit, exit_reason = self._check_exit(
                    position, current_price, signals.iloc[i], genes, data.iloc[i]
                )
                
                if should_exit:
                    position.close(current_time, current_price, exit_reason)
                    result.trades.append(position)
                    
                    # Update capital
                    trade_pnl = position.pnl * capital * position_size
                    capital += trade_pnl
                    position = None
            
            # Check entry conditions
            if not position:
                signal = signals.iloc[i]
                if signal['long_signal']:
                    position = Trade(
                        entry_time=current_time,
                        entry_price=current_price,
                        direction="LONG",
                        size=position_size,
                        strategy_dna=strategy.strategy_id
                    )
                elif signal['short_signal']:
                    position = Trade(
                        entry_time=current_time,
                        entry_price=current_price,
                        direction="SHORT",
                        size=position_size,
                        strategy_dna=strategy.strategy_id
                    )
            
            equity_curve.append(capital)
        
        # Close any open position at end
        if position:
            position.close(
                data.index[-1],
                data['close'].iloc[-1],
                "end_of_data"
            )
            result.trades.append(position)
        
        # Calculate metrics
        result.equity_curve = equity_curve
        result.total_trades = len(result.trades)
        result.winning_trades = sum(1 for t in result.trades if t.pnl and t.pnl > 0)
        result.losing_trades = result.total_trades - result.winning_trades
        
        if result.total_trades > 0:
            result.win_rate = result.winning_trades / result.total_trades
            
            wins = [t.pnl_pct for t in result.trades if t.pnl_pct and t.pnl_pct > 0]
            losses = [t.pnl_pct for t in result.trades if t.pnl_pct and t.pnl_pct <= 0]
            
            result.avg_win = np.mean(wins) if wins else 0
            result.avg_loss = np.mean(losses) if losses else 0
            result.avg_trade = np.mean([t.pnl_pct for t in result.trades if t.pnl_pct]) if result.trades else 0
            
            total_wins = sum(wins) if wins else 0
            total_losses = abs(sum(losses)) if losses else 0
            result.profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            result.total_return = capital - initial_capital
            result.total_return_pct = (capital - initial_capital) / initial_capital
            
            # Calculate drawdown
            peak = initial_capital
            max_dd = 0
            for eq in equity_curve:
                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak
                max_dd = max(max_dd, dd)
            result.max_drawdown_pct = max_dd
            
            # Calculate Sharpe (simplified)
            returns = np.diff(equity_curve) / equity_curve[:-1]
            if len(returns) > 1 and np.std(returns) > 0:
                result.sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
                result.volatility = np.std(returns) * np.sqrt(252)
        
        # Store in database
        self._save_backtest_result(result)
        
        # Check for Phoenix registration
        if result.sharpe_ratio < 0.5 and result.win_rate > 0.4:
            self.phoenix.register_failure(result, f"Low Sharpe: {result.sharpe_ratio:.2f}")
        
        return result
    
    def _generate_signals(self, data: pd.DataFrame, genes: Dict) -> pd.DataFrame:
        """Generate trading signals based on strategy genes."""
        signals = pd.DataFrame(index=data.index)
        signals['long_signal'] = False
        signals['short_signal'] = False
        
        primary = genes.get('primary_indicator', 'EMA')
        entry = genes.get('entry_logic', 'golden_cross')
        
        # EMA signals
        if primary == 'EMA':
            fast = genes.get('ema_fast', 20)
            slow = genes.get('ema_slow', 50)
            data['ema_fast'] = data['close'].ewm(span=fast).mean()
            data['ema_slow'] = data['close'].ewm(span=slow).mean()
            
            if entry == 'golden_cross':
                signals['long_signal'] = (data['ema_fast'] > data['ema_slow']) & \
                                        (data['ema_fast'].shift(1) <= data['ema_slow'].shift(1))
                signals['short_signal'] = (data['ema_fast'] < data['ema_slow']) & \
                                         (data['ema_fast'].shift(1) >= data['ema_slow'].shift(1))
        
        # RSI signals
        elif primary == 'RSI':
            period = genes.get('rsi_period', 14)
            oversold = genes.get('rsi_oversold', 30)
            overbought = genes.get('rsi_overbought', 70)
            
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            data['rsi'] = 100 - (100 / (1 + rs))
            
            if entry == 'rsi_oversold':
                signals['long_signal'] = data['rsi'] < oversold
                signals['short_signal'] = data['rsi'] > overbought
        
        # MACD signals
        elif primary == 'MACD':
            exp1 = data['close'].ewm(span=12).mean()
            exp2 = data['close'].ewm(span=26).mean()
            data['macd'] = exp1 - exp2
            data['signal'] = data['macd'].ewm(span=9).mean()
            
            if entry == 'macd_crossover':
                signals['long_signal'] = (data['macd'] > data['signal']) & \
                                        (data['macd'].shift(1) <= data['signal'].shift(1))
                signals['short_signal'] = (data['macd'] < data['signal']) & \
                                         (data['macd'].shift(1) >= data['signal'].shift(1))
        
        return signals
    
    def _check_exit(
        self,
        position: Trade,
        current_price: float,
        signal: pd.Series,
        genes: Dict,
        current_data: pd.Series
    ) -> Tuple[bool, str]:
        """Check if position should be closed."""
        exit_logic = genes.get('exit_logic', 'death_cross')
        
        # Check signal-based exit
        if position.direction == "LONG" and signal.get('short_signal'):
            return True, "signal_reverse"
        if position.direction == "SHORT" and signal.get('long_signal'):
            return True, "signal_reverse"
        
        # Check stop loss / take profit
        entry = position.entry_price
        
        # Default 2% SL, 4% TP
        sl_pct = genes.get('stop_loss_pct', 0.02)
        tp_pct = genes.get('take_profit_pct', 0.04)
        
        if position.direction == "LONG":
            if current_price <= entry * (1 - sl_pct):
                return True, "stop_loss"
            if current_price >= entry * (1 + tp_pct):
                return True, "take_profit"
        else:
            if current_price >= entry * (1 + sl_pct):
                return True, "stop_loss"
            if current_price <= entry * (1 - tp_pct):
                return True, "take_profit"
        
        return False, ""
    
    def _save_backtest_result(self, result: BacktestResult):
        """Save backtest result to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO backtests
                (strategy_id, dna_hash, symbol, start_date, end_date, total_trades,
                 win_rate, profit_factor, sharpe_ratio, max_drawdown, total_return, regime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.strategy_dna.strategy_id,
                result.strategy_dna.dna_hash,
                result.symbol,
                result.start_date.isoformat(),
                result.end_date.isoformat(),
                result.total_trades,
                result.win_rate,
                result.profit_factor,
                result.sharpe_ratio,
                result.max_drawdown_pct,
                result.total_return_pct,
                None
            ))
            
            backtest_id = cursor.lastrowid
            
            # Save trades
            for trade in result.trades:
                cursor.execute('''
                    INSERT INTO backtest_trades
                    (backtest_id, entry_time, exit_time, entry_price, exit_price,
                     direction, pnl, pnl_pct, exit_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    backtest_id,
                    trade.entry_time.isoformat() if hasattr(trade.entry_time, 'isoformat') else str(trade.entry_time),
                    trade.exit_time.isoformat() if hasattr(trade.exit_time, 'isoformat') else str(trade.exit_time),
                    trade.entry_price,
                    trade.exit_price,
                    trade.direction,
                    trade.pnl,
                    trade.pnl_pct,
                    trade.exit_reason
                ))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save backtest: {e}")
        finally:
            conn.close()
    
    def optimize_for_symbol(
        self,
        base_strategies: List[StrategyDNA],
        symbol: str,
        data: pd.DataFrame,
        target_metric: str = "sharpe_ratio",
        n_permutations: int = 100
    ) -> List[Tuple[StrategyDNA, BacktestResult]]:
        """
        Find optimal strategy permutations for a specific symbol.
        
        Args:
            base_strategies: Base strategies to permute
            symbol: Symbol to optimize for
            data: Historical price data
            target_metric: Metric to optimize
            n_permutations: Max number of permutations to test
            
        Returns:
            Sorted list of (StrategyDNA, BacktestResult) tuples
        """
        logger.info(f"Optimizing for {symbol} with {len(base_strategies)} base strategies")
        
        # Generate permutations
        permutations = self.engine.generate_all_permutations(
            base_strategies,
            max_combo_size=min(3, len(base_strategies))
        )
        
        # Limit permutations
        if len(permutations) > n_permutations:
            permutations = random.sample(permutations, n_permutations)
        
        # Backtest each
        results = []
        for perm in permutations:
            result = self.run_backtest(perm, data, symbol)
            results.append((perm, result))
        
        # Sort by target metric
        results.sort(
            key=lambda x: getattr(x[1], target_metric, 0),
            reverse=True
        )
        
        logger.info(f"Optimization complete. Best {target_metric}: {getattr(results[0][1], target_metric, 0):.3f}")
        
        return results
    
    def get_symbol_specialization(
        self,
        strategy: StrategyDNA,
        symbols: List[str],
        data_dict: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Determine which symbols a strategy performs best on.
        
        Returns:
            Dictionary with specialization analysis
        """
        symbol_performance = {}
        
        for symbol in symbols:
            if symbol not in data_dict:
                continue
            
            result = self.run_backtest(strategy, data_dict[symbol], symbol)
            symbol_performance[symbol] = {
                'sharpe': result.sharpe_ratio,
                'win_rate': result.win_rate,
                'return': result.total_return_pct,
                'profit_factor': result.profit_factor
            }
        
        # Find best symbol
        best_symbol = max(
            symbol_performance.items(),
            key=lambda x: x[1]['sharpe']
        )[0] if symbol_performance else None
        
        return {
            'best_symbol': best_symbol,
            'performance_by_symbol': symbol_performance,
            'is_specialized': (
                best_symbol and 
                symbol_performance[best_symbol]['sharpe'] > 1.5 and
                len([s for s in symbol_performance.values() if s['sharpe'] > 0.5]) <= 2
            )
        }


if __name__ == "__main__":
    import argparse
    import os
    import sys

    parser = argparse.ArgumentParser(description="DNA Backtester CLI")
    parser.add_argument("--lookback", type=str, default="90d",
                        help="Lookback period for backtesting (e.g. 90d, 30d)")
    parser.add_argument("--symbols", type=str, default="BTC,ETH,SOL",
                        help="Comma-separated symbols to backtest (e.g. BTC,ETH,SOL)")
    parser.add_argument("--data-dir", type=str, default="data/market",
                        help="Directory with market data JSON files (default: data/market)")
    parser.add_argument("--results-dir", type=str, default="results",
                        help="Directory with permutation results (default: results)")
    args = parser.parse_args()

    # Handle imports for both execution contexts
    try:
        from dna_engine import DNAPermutationEngine, create_strategy_dna, StrategyDNA
    except ImportError:
        from genome.dna_engine import DNAPermutationEngine, create_strategy_dna, StrategyDNA

    symbols = [s.strip() for s in args.symbols.split(",")]
    data_dir = args.data_dir
    results_dir = args.results_dir

    print(f"[INFO] Lookback: {args.lookback}")
    print(f"[INFO] Symbols: {symbols}")
    print(f"[INFO] Data dir: {data_dir}")

    # Load market data from JSON files
    data_dict = {}
    for sym in symbols:
        # Try multiple naming patterns: BTC_USDT_1h.json, BTCUSDT_1h.json, etc.
        candidates = [
            os.path.join(data_dir, f"{sym}_USDT_1h.json"),
            os.path.join(data_dir, f"{sym}USDT_1h.json"),
            os.path.join(data_dir, f"{sym}-USDT_1h.json"),
            os.path.join(data_dir, f"{sym}_USDT_4h.json"),
            os.path.join(data_dir, f"{sym}USDT_4h.json"),
        ]
        loaded = False
        for fpath in candidates:
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'r') as f:
                        raw = json.load(f)
                    candles = raw.get('candles', [])
                    if not candles:
                        continue
                    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    data_dict[f"{sym}USDT"] = df
                    print(f"[OK] Loaded {sym} from {fpath}: {len(df)} candles")
                    loaded = True
                    break
                except Exception as e:
                    print(f"[WARN] Failed to load {fpath}: {e}")
        if not loaded:
            print(f"[WARN] No market data found for {sym}, generating synthetic data")
            dates = pd.date_range(start='2024-01-01', periods=1000, freq='1h')
            np.random.seed(42)
            returns = np.random.normal(0.0001, 0.01, 1000)
            prices = 50000 * np.exp(np.cumsum(returns))
            df = pd.DataFrame({
                'open': prices * (1 + np.random.normal(0, 0.001, 1000)),
                'high': prices * (1 + abs(np.random.normal(0, 0.005, 1000))),
                'low': prices * (1 - abs(np.random.normal(0, 0.005, 1000))),
                'close': prices,
                'volume': np.random.lognormal(10, 1, 1000)
            }, index=dates)
            data_dict[f"{sym}USDT"] = df

    # Load permutations from results
    permutations_path = os.path.join(results_dir, "permutations.json")
    strategies_to_test = []
    if os.path.exists(permutations_path):
        try:
            with open(permutations_path, 'r') as f:
                perm_data = json.load(f)
            for p in perm_data.get('permutations', []):
                strategies_to_test.append(StrategyDNA.from_dict(p))
            print(f"[INFO] Loaded {len(strategies_to_test)} permutations from {permutations_path}")
        except Exception as e:
            print(f"[WARN] Failed to load permutations: {e}")

    if not strategies_to_test:
        print("[INFO] No permutations found, creating sample strategies")
        strategies_to_test = [
            create_strategy_dna("EMA Cross", timeframe="1h", primary_indicator="EMA",
                                entry_logic="golden_cross", exit_logic="death_cross", ema_fast=20, ema_slow=50),
            create_strategy_dna("RSI Reversion", timeframe="1h", primary_indicator="RSI",
                                entry_logic="rsi_oversold", rsi_period=14, rsi_oversold=30),
        ]

    # Run backtests
    backtester = DNABacktester()
    all_results = []

    for symbol, df in data_dict.items():
        print(f"\n[INFO] Backtesting {len(strategies_to_test)} strategies on {symbol}...")
        for strat in strategies_to_test[:50]:  # Limit to 50 per symbol to avoid timeout
            try:
                result = backtester.run_backtest(strat, df, symbol)
                all_results.append(result.to_dict())
            except Exception as e:
                logger.warning(f"Backtest failed for {strat.strategy_id} on {symbol}: {e}")

    print(f"\n[OK] Completed {len(all_results)} backtests")

    # Save results
    os.makedirs(results_dir, exist_ok=True)
    output_path = os.path.join(results_dir, "backtest_results.json")
    with open(output_path, 'w') as f:
        json.dump({
            'generated_at': datetime.utcnow().isoformat(),
            'lookback': args.lookback,
            'symbols': symbols,
            'total_backtests': len(all_results),
            'results': all_results
        }, f, indent=2)
    print(f"[OK] Saved backtest results to {output_path}")
