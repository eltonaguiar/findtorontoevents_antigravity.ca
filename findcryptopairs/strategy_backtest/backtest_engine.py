#!/usr/bin/env python3
"""
100 Strategy Backtesting Engine for Volatile Crypto Pairs
Backtests strategies across multiple timeframes and pairs
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StrategyBacktester:
    """Main backtesting engine for crypto strategies"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.results = {}
        self.audit_log = []
        
    def load_strategies(self, filepath: str) -> List[Dict]:
        """Load 100 strategies from JSON"""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for strategies"""
        # Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Volatility
        df['volatility'] = df['close'].pct_change().rolling(20).std() * np.sqrt(365)
        
        return df
    
    def apply_strategy(self, df: pd.DataFrame, strategy: Dict) -> pd.DataFrame:
        """Apply a specific strategy to the data"""
        df = df.copy()
        df['signal'] = 0  # 0 = no signal, 1 = buy, -1 = sell
        
        strategy_type = strategy.get('type', '').lower()
        params = strategy.get('params', {})
        
        try:
            if strategy_type == 'momentum_rsi':
                # RSI Momentum: Buy when RSI crosses above oversold, sell when overbought
                oversold = params.get('oversold', 30)
                overbought = params.get('overbought', 70)
                df['signal'] = np.where(
                    (df['rsi'] < oversold) & (df['rsi'].shift(1) >= oversold), 1,
                    np.where((df['rsi'] > overbought) & (df['rsi'].shift(1) <= overbought), -1, 0)
                )
                
            elif strategy_type == 'macd_crossover':
                # MACD Crossover
                df['signal'] = np.where(
                    (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1)), 1,
                    np.where((df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1)), -1, 0)
                )
                
            elif strategy_type == 'bollinger_bounce':
                # Bollinger Bands Mean Reversion
                df['signal'] = np.where(
                    (df['close'] < df['bb_lower']) & (df['close'].shift(1) >= df['bb_lower'].shift(1)), 1,
                    np.where((df['close'] > df['bb_upper']) & (df['close'].shift(1) <= df['bb_upper'].shift(1)), -1, 0)
                )
                
            elif strategy_type == 'breakout':
                # Breakout strategy
                lookback = params.get('lookback', 20)
                df['high_max'] = df['high'].rolling(lookback).max()
                df['low_min'] = df['low'].rolling(lookback).min()
                df['signal'] = np.where(
                    (df['close'] > df['high_max'].shift(1)), 1,
                    np.where((df['close'] < df['low_min'].shift(1)), -1, 0)
                )
                
            elif strategy_type == 'trend_following':
                # Trend Following with moving averages
                df['signal'] = np.where(
                    (df['sma_20'] > df['sma_50']) & (df['sma_20'].shift(1) <= df['sma_50'].shift(1)), 1,
                    np.where((df['sma_20'] < df['sma_50']) & (df['sma_20'].shift(1) >= df['sma_50'].shift(1)), -1, 0)
                )
                
            elif strategy_type == 'volume_spike':
                # Volume-based breakout
                vol_threshold = params.get('volume_threshold', 2.0)
                df['signal'] = np.where(
                    (df['volume_ratio'] > vol_threshold) & (df['close'] > df['close'].shift(1)), 1,
                    np.where((df['volume_ratio'] > vol_threshold) & (df['close'] < df['close'].shift(1)), -1, 0)
                )
                
            elif strategy_type == 'atr_trailing_stop':
                # ATR-based trailing stop
                atr_mult = params.get('atr_multiplier', 3.0)
                df['trailing_stop'] = df['close'] - (df['atr'] * atr_mult)
                df['signal'] = np.where(
                    (df['close'] > df['trailing_stop'].shift(1)) & (df['close'].shift(1) <= df['trailing_stop'].shift(2)), 1,
                    np.where((df['close'] < df['trailing_stop'].shift(1)), -1, 0)
                )
                
            elif strategy_type == 'composite_momentum':
                # Multi-factor composite (like KIMI-MTF)
                mom_1h = df['close'].pct_change(1)
                mom_4h = df['close'].pct_change(4)
                mom_24h = df['close'].pct_change(24)
                
                score = 0
                score += np.where((mom_1h > 0) & (mom_4h > 0) & (mom_24h > 0), 40, 0)
                score += np.where(mom_1h > 0.01, 30, np.where(mom_1h > 0.005, 15, 0))
                score += np.where((df['rsi'] >= 45) & (df['rsi'] <= 75), 30, 0)
                
                df['signal'] = np.where(score >= 70, 1, np.where(score <= 30, -1, 0))
                
            else:
                # Default: Buy and Hold for baseline
                df.loc[df.index[0], 'signal'] = 1
                
        except Exception as e:
            logger.error(f"Error applying strategy {strategy_type}: {e}")
            
        return df
    
    def run_backtest(self, df: pd.DataFrame, strategy: Dict, 
                     pair: str, timeframe: str) -> Dict:
        """Run a single backtest"""
        df = self.calculate_indicators(df)
        df = self.apply_strategy(df, strategy)
        
        # Execute trades
        position = 0
        equity = self.initial_capital
        trades = []
        entry_price = 0
        
        for i, row in df.iterrows():
            if position == 0 and row['signal'] == 1:
                # Enter long
                position = 1
                entry_price = row['close']
                entry_time = i
                
            elif position == 1 and row['signal'] == -1:
                # Exit long
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price
                equity *= (1 + pnl)
                
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl * 100,
                    'equity': equity
                })
                position = 0
        
        # Calculate metrics
        return self.calculate_metrics(trades, equity, strategy, pair, timeframe)
    
    def calculate_metrics(self, trades: List[Dict], final_equity: float,
                         strategy: Dict, pair: str, timeframe: str) -> Dict:
        """Calculate comprehensive performance metrics"""
        
        if not trades:
            return {
                'strategy': strategy.get('name', 'Unknown'),
                'pair': pair,
                'timeframe': timeframe,
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'total_return': 0,
                'status': 'NO_TRADES'
            }
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl_pct'] > 0]
        losing_trades = [t for t in trades if t['pnl_pct'] <= 0]
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        gross_profit = sum(t['pnl_pct'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl_pct'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calculate returns for Sharpe
        returns = [t['pnl_pct'] for t in trades]
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        sharpe_ratio = (avg_return / std_return * np.sqrt(252)) if std_return > 0 else 0
        
        # Max Drawdown
        equity_curve = [t['equity'] for t in trades]
        peak = equity_curve[0]
        max_dd = 0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            max_dd = max(max_dd, dd)
        
        # Total return
        total_return = (final_equity - self.initial_capital) / self.initial_capital * 100
        
        return {
            'strategy': strategy.get('name', 'Unknown'),
            'pair': pair,
            'timeframe': timeframe,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'profit_factor': round(profit_factor, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_dd, 2),
            'avg_trade_return': round(avg_return, 2),
            'total_return': round(total_return, 2),
            'final_equity': round(final_equity, 2)
        }


class EliminationFramework:
    """Progressive elimination framework for strategies"""
    
    def __init__(self):
        self.elimination_log = []
        
    def round1_basic_viability(self, results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Round 1: Eliminate strategies with basic viability issues"""
        passed = []
        eliminated = []
        
        for result in results:
            reasons = []
            
            if result['win_rate'] < 40:
                reasons.append(f"Win rate {result['win_rate']}% < 40%")
            if result['profit_factor'] < 1.2:
                reasons.append(f"Profit factor {result['profit_factor']} < 1.2")
            if result['max_drawdown'] > 50:
                reasons.append(f"Max drawdown {result['max_drawdown']}% > 50%")
            if result['total_trades'] < 20:
                reasons.append(f"Only {result['total_trades']} trades < 20")
            
            if reasons:
                result['elimination_round'] = 1
                result['elimination_reasons'] = reasons
                eliminated.append(result)
                self.elimination_log.append({
                    'round': 1,
                    'strategy': result['strategy'],
                    'pair': result['pair'],
                    'reasons': reasons
                })
            else:
                passed.append(result)
                
        return passed, eliminated
    
    def round2_risk_adjusted(self, results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Round 2: Risk-adjusted performance filtering"""
        passed = []
        eliminated = []
        
        for result in results:
            reasons = []
            
            if result['sharpe_ratio'] < 1.0:
                reasons.append(f"Sharpe ratio {result['sharpe_ratio']} < 1.0")
            if result['max_drawdown'] > 30:
                reasons.append(f"Max drawdown {result['max_drawdown']}% > 30% (strict)")
            
            if reasons:
                result['elimination_round'] = 2
                result['elimination_reasons'] = reasons
                eliminated.append(result)
                self.elimination_log.append({
                    'round': 2,
                    'strategy': result['strategy'],
                    'pair': result['pair'],
                    'reasons': reasons
                })
            else:
                passed.append(result)
                
        return passed, eliminated
    
    def round3_consistency(self, results: List[Dict], all_results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Round 3: Consistency across pairs"""
        passed = []
        eliminated = []
        
        # Group by strategy
        strategy_groups = {}
        for r in all_results:
            name = r['strategy']
            if name not in strategy_groups:
                strategy_groups[name] = []
            strategy_groups[name].append(r)
        
        for result in results:
            name = result['strategy']
            group = strategy_groups.get(name, [])
            
            # Check if strategy works on multiple pairs
            positive_pairs = [r for r in group if r['total_return'] > 0]
            
            reasons = []
            if len(positive_pairs) < 3:
                reasons.append(f"Only {len(positive_pairs)} pairs with positive returns < 3")
            
            if reasons:
                result['elimination_round'] = 3
                result['elimination_reasons'] = reasons
                eliminated.append(result)
                self.elimination_log.append({
                    'round': 3,
                    'strategy': result['strategy'],
                    'pair': result['pair'],
                    'reasons': reasons
                })
            else:
                passed.append(result)
                
        return passed, eliminated


def main():
    """Main execution"""
    logger.info("Starting 100 Strategy Backtesting System")
    
    # Initialize components
    backtester = StrategyBacktester(initial_capital=10000)
    eliminator = EliminationFramework()
    
    # Define volatile pairs
    volatile_pairs = [
        ('POPCAT', 'USD'),
        ('PENGU', 'USD'),
        ('DOGE', 'USD'),
        ('SHIB', 'USD'),
        ('PEPE', 'USD'),
        ('FLOKI', 'USD'),
        ('BONK', 'USD'),
        ('WIF', 'USD'),
        ('BTC', 'USD'),
        ('ETH', 'USD')
    ]
    
    timeframes = ['1h', '4h', '1d']
    
    # Load strategies (simplified for demo - would load 100)
    strategies = [
        {'name': 'Momentum_RSI', 'type': 'momentum_rsi', 'params': {'oversold': 30, 'overbought': 70}},
        {'name': 'MACD_Crossover', 'type': 'macd_crossover'},
        {'name': 'Bollinger_Bounce', 'type': 'bollinger_bounce'},
        {'name': 'Trend_Following_MA', 'type': 'trend_following'},
        {'name': 'Volume_Spike', 'type': 'volume_spike', 'params': {'volume_threshold': 2.0}},
        {'name': 'ATR_Trailing_Stop', 'type': 'atr_trailing_stop', 'params': {'atr_multiplier': 3.0}},
        {'name': 'Composite_Momentum', 'type': 'composite_momentum'},
        {'name': 'Breakout_20', 'type': 'breakout', 'params': {'lookback': 20}},
    ]
    
    logger.info(f"Loaded {len(strategies)} strategies for {len(volatile_pairs)} pairs")
    
    # This would run actual backtests with historical data
    # For now, create simulated results to demonstrate the system
    all_results = []
    
    for strategy in strategies:
        for pair, quote in volatile_pairs:
            for tf in timeframes:
                # Simulate backtest result
                result = {
                    'strategy': strategy['name'],
                    'pair': f'{pair}/{quote}',
                    'timeframe': tf,
                    'total_trades': np.random.randint(15, 100),
                    'win_rate': np.random.uniform(35, 75),
                    'profit_factor': np.random.uniform(0.8, 2.5),
                    'sharpe_ratio': np.random.uniform(0.5, 2.5),
                    'max_drawdown': np.random.uniform(10, 60),
                    'avg_trade_return': np.random.uniform(-2, 5),
                    'total_return': np.random.uniform(-30, 150),
                    'final_equity': np.random.uniform(7000, 25000)
                }
                all_results.append(result)
    
    # Apply elimination rounds
    logger.info("Applying elimination framework...")
    
    round1_passed, round1_elim = eliminator.round1_basic_viability(all_results)
    logger.info(f"Round 1: {len(round1_passed)} passed, {len(round1_elim)} eliminated")
    
    round2_passed, round2_elim = eliminator.round2_risk_adjusted(round1_passed)
    logger.info(f"Round 2: {len(round2_passed)} passed, {len(round2_elim)} eliminated")
    
    round3_passed, round3_elim = eliminator.round3_consistency(round2_passed, all_results)
    logger.info(f"Round 3: {len(round3_passed)} passed, {len(round3_elim)} eliminated")
    
    # Save results
    with open('results/round1_basic_viability.json', 'w') as f:
        json.dump({'passed': round1_passed, 'eliminated': round1_elim}, f, indent=2)
    
    with open('results/final_rankings.json', 'w') as f:
        json.dump({'top_strategies': round3_passed}, f, indent=2)
    
    with open('audit_logs/elimination_reasons.json', 'w') as f:
        json.dump(eliminator.elimination_log, f, indent=2)
    
    logger.info("Backtesting complete. Results saved.")
    
    return round3_passed


if __name__ == '__main__':
    main()
