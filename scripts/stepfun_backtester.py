#!/usr/bin/env python3
"""
STEPFUN Backtesting Engine
Tests STEPFUN Pine Script strategies against crypto pairs
Saves optimal configurations per symbol
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# ============================================
# CONFIGURATION
# ============================================

BACKTEST_CONFIG = {
    'initial_capital': 10000,
    'commission': 0.001,  # 0.1%
    'slippage': 0.0005,   # 0.05%
    'timeframes': ['5m', '15m', '1h', '4h', '1D'],
    'test_period_years': 2,
    'min_trades': 50,
    'sharpe_threshold': 1.0,
    'max_drawdown_threshold': 0.25,
    'win_rate_threshold': 0.55
}

# Strategy configurations
STRATEGIES = {
    'RSI2_Optimized': {
        'file': 'RSI2_Optimized_STEPFUN.pine',
        'params': {
            'rsi_length': 2,
            'oversold': 30,
            'overbought': 70,
            'use_trend_filter': True,
            'trend_filter_period': 200,
            'use_volume_confirm': True,
            'volume_multiplier': 1.5,
            'exit_mode': 'TP/SL',
            'tp_percent': 3.0,
            'sl_percent': 1.5,
            'position_size_pct': 100.0
        }
    },
    'Volume_Spike': {
        'file': 'Volume_Spike_STEPFUN.pine',
        'params': {
            'volume_period': 20,
            'volume_multiplier': 2.0,
            'price_move_threshold': 1.0,
            'use_price_action': True,
            'require_volume_surge': True,
            'use_trend_filter': True,
            'trend_period': 50,
            'exit_mode': 'Fixed %',
            'fixed_tp_pct': 2.5,
            'fixed_sl_pct': 1.0,
            'position_size_pct': 100.0
        }
    },
    'MACD_Crossover': {
        'file': 'MACD_Crossover_STEPFUN.pine',
        'params': {
            'fast_length': 12,
            'slow_length': 26,
            'signal_length': 9,
            'use_histogram_confirm': True,
            'histogram_threshold': 0.0,
            'use_trend_filter': True,
            'trend_period': 50,
            'exit_mode': 'Opposite Signal',
            'tp_percent': 2.0,
            'sl_percent': 1.0,
            'position_size_pct': 100.0
        }
    },
    'Bollinger_Squeeze': {
        'file': 'Bollinger_Squeeze_STEPFUN.pine',
        'params': {
            'bb_length': 20,
            'bb_std': 2.0,
            'squeeze_threshold': 0.05,
            'breakout_confirmation': 1,
            'use_volume_confirm': True,
            'volume_multiplier': 1.5,
            'trade_direction': 'Both',
            'exit_mode': 'TP/SL',
            'tp_percent': 3.0,
            'sl_percent': 1.5,
            'position_size_pct': 100.0
        }
    },
    'Triple_EMA': {
        'file': 'Triple_EMA_STEPFUN.pine',
        'params': {
            'fast_ema': 5,
            'mid_ema': 10,
            'slow_ema': 20,
            'require_alignment': True,
            'use_momentum_confirm': True,
            'momentum_period': 14,
            'exit_mode': 'Opposite Signal',
            'tp_percent': 2.5,
            'sl_percent': 1.0,
            'position_size_pct': 100.0
        }
    },
    'Ichimoku_Cloud': {
        'file': 'Ichimoku_Cloud_STEPFUN.pine',
        'params': {
            'tenkan_period': 9,
            'kijun_period': 26,
            'senkou_span_b_period': 52,
            'require_cloud_confirmation': True,
            'use_chikou_span': False,
            'exit_mode': 'Opposite Signal',
            'tp_percent': 3.0,
            'sl_percent': 1.5,
            'position_size_pct': 100.0
        }
    }
}

# Crypto pairs to test
CRYPTO_PAIRS = [
    'BTCUSD', 'ETHUSD', 'SOLUSD', 'AVAXUSD', 'DOTUSD',
    'MATICUSD', 'LINKUSD', 'UNIUSD', 'ADAUSD', 'DOGEUSD'
]

# ============================================
# DATA FETCHER (Simulated for demo)
# ============================================

class DataFetcher:
    """Fetches historical crypto data"""
    
    def __init__(self, data_source='yahoo'):
        self.data_source = data_source
        
    def fetch_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical data for a symbol
        In production, this would use yfinance, ccxt, or API
        """
        # For demo, generate synthetic data
        # In production: return yf.download(symbol, start=start_date, end=end_date, interval=timeframe)
        
        periods = 10000  # Approximate number of bars for 2 years on 5m
        dates = pd.date_range(start=start_date, end=end_date, periods=periods)
        
        # Generate realistic crypto data
        np.random.seed(42)
        returns = np.random.normal(0.0001, 0.02, periods)
        price = 100 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'open': price * (1 + np.random.normal(0, 0.001, periods)),
            'high': price * (1 + np.abs(np.random.normal(0, 0.002, periods))),
            'low': price * (1 - np.abs(np.random.normal(0, 0.002, periods))),
            'close': price,
            'volume': np.random.lognormal(10, 1, periods)
        }, index=dates)
        
        return df

# ============================================
# STRATEGY SIMULATOR
# ============================================

class StrategySimulator:
    """Simulates a STEPFUN strategy on historical data"""
    
    def __init__(self, strategy_name: str, params: Dict):
        self.strategy_name = strategy_name
        self.params = params
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate buy/sell signals based on strategy logic"""
        signals = pd.DataFrame(index=df.index)
        signals['price'] = df['close']
        signals['signal'] = 0  # 0=hold, 1=buy, -1=sell
        signals['strength'] = 0
        
        # Simplified signal generation for demo
        # In production, this would parse and execute Pine Script logic
        
        if self.strategy_name == 'RSI2_Optimized':
            rsi = self._calculate_rsi(df['close'], 2)
            oversold = 30
            overbought = 70
            
            # Buy when RSI crosses above oversold
            buy_condition = (rsi.shift(1) <= oversold) & (rsi > oversold)
            # Sell when RSI crosses below overbought
            sell_condition = (rsi.shift(1) >= overbought) & (rsi < overbought)
            
            signals.loc[buy_condition, 'signal'] = 1
            signals.loc[sell_condition, 'signal'] = -1
            signals.loc[buy_condition, 'strength'] = 3
            signals.loc[sell_condition, 'strength'] = 3
            
        elif self.strategy_name == 'Volume_Spike':
            volume_ma = df['volume'].rolling(20).mean()
            volume_spike = df['volume'] > volume_ma * 2.0
            price_up = df['close'] > df['open']
            price_down = df['close'] < df['open']
            
            buy_condition = volume_spike & price_up & (df['close'] > df['close'].shift(1))
            sell_condition = volume_spike & price_down & (df['close'] < df['close'].shift(1))
            
            signals.loc[buy_condition, 'signal'] = 1
            signals.loc[sell_condition, 'signal'] = -1
            signals.loc[buy_condition, 'strength'] = 4
            signals.loc[sell_condition, 'strength'] = 4
            
        elif self.strategy_name == 'MACD_Crossover':
            macd_line, signal_line, _ = self._calculate_macd(df['close'])
            
            buy_condition = (macd_line.shift(1) <= signal_line.shift(1)) & (macd_line > signal_line)
            sell_condition = (macd_line.shift(1) >= signal_line.shift(1)) & (macd_line < signal_line)
            
            signals.loc[buy_condition, 'signal'] = 1
            signals.loc[sell_condition, 'signal'] = -1
            signals.loc[buy_condition, 'strength'] = 2
            signals.loc[sell_condition, 'strength'] = 2
            
        elif self.strategy_name == 'Bollinger_Squeeze':
            bb_basis = df['close'].rolling(20).mean()
            bb_upper = bb_basis + 2 * df['close'].rolling(20).std()
            bb_lower = bb_basis - 2 * df['close'].rolling(20).std()
            bb_width = (bb_upper - bb_lower) / bb_basis
            
            squeeze = bb_width < 0.05
            upper_break = df['close'] > bb_upper
            lower_break = df['close'] < bb_lower
            
            buy_condition = squeeze.shift(1) & upper_break
            sell_condition = squeeze.shift(1) & lower_break
            
            signals.loc[buy_condition, 'signal'] = 1
            signals.loc[sell_condition, 'signal'] = -1
            signals.loc[buy_condition, 'strength'] = 3
            signals.loc[sell_condition, 'strength'] = 3
            
        elif self.strategy_name == 'Triple_EMA':
            ema1 = df['close'].ewm(span=5).mean()
            ema2 = df['close'].ewm(span=10).mean()
            ema3 = df['close'].ewm(span=20).mean()
            
            bullish_stack = (ema1 > ema2) & (ema2 > ema3)
            bearish_stack = (ema1 < ema2) & (ema2 < ema3)
            
            buy_condition = bullish_stack & (ema1 > ema1.shift(1))
            sell_condition = bearish_stack & (ema1 < ema1.shift(1))
            
            signals.loc[buy_condition, 'signal'] = 1
            signals.loc[sell_condition, 'signal'] = -1
            signals.loc[buy_condition, 'strength'] = 2
            signals.loc[sell_condition, 'strength'] = 2
            
        elif self.strategy_name == 'Ichimoku_Cloud':
            # Simplified Ichimoku
            tenkan = (df['high'].rolling(9).max() + df['low'].rolling(9).min()) / 2
            kijun = (df['high'].rolling(26).max() + df['low'].rolling(26).min()) / 2
            
            tk_bullish = (tenkan.shift(1) <= kijun.shift(1)) & (tenkan > kijun)
            tk_bearish = (tenkan.shift(1) >= kijun.shift(1)) & (tenkan < kijun)
            
            signals.loc[tk_bullish, 'signal'] = 1
            signals.loc[tk_bearish, 'signal'] = -1
            signals.loc[tk_bullish, 'strength'] = 2
            signals.loc[tk_bearish, 'strength'] = 2
        
        return signals
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD"""
        ema12 = prices.ewm(span=12).mean()
        ema26 = prices.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

# ============================================
# BACKTEST ENGINE
# ============================================

class BacktestEngine:
    """Runs backtests and calculates performance metrics"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.data_fetcher = DataFetcher()
        
    def run_backtest(self, symbol: str, strategy_name: str, timeframe: str) -> Dict:
        """
        Run backtest for a single symbol/strategy/timeframe combination
        """
        # Fetch data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * self.config['test_period_years'])
        
        df = self.data_fetcher.fetch_data(
            symbol, timeframe,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if len(df) < 100:
            return None
            
        # Generate signals
        strategy = StrategySimulator(strategy_name, STRATEGIES[strategy_name]['params'])
        signals = strategy.generate_signals(df)
        
        # Simulate trades
        trades = self._simulate_trades(df, signals)
        
        if len(trades) < self.config['min_trades']:
            return None
            
        # Calculate metrics
        metrics = self._calculate_metrics(trades, df)
        
        return {
            'symbol': symbol,
            'strategy': strategy_name,
            'timeframe': timeframe,
            'total_trades': len(trades),
            'metrics': metrics,
            'trades': trades.to_dict('records') if len(trades) < 100 else 'truncated'
        }
    
    def _simulate_trades(self, df: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """Simulate trades based on signals"""
        trades = []
        position = 0
        entry_price = 0
        entry_date = None
        
        for i in range(len(signals)):
            date = signals.index[i]
            signal = signals['signal'].iloc[i]
            price = signals['price'].iloc[i]
            strength = signals['strength'].iloc[i]
            
            # Skip if strength below threshold
            if signal != 0 and strength < 2:
                continue
                
            if signal == 1 and position == 0:  # Buy
                position = 1
                entry_price = price
                entry_date = date
                
            elif signal == -1 and position == 0:  # Sell
                position = -1
                entry_price = price
                entry_date = date
                
            elif signal == 1 and position == -1:  # Close short, open long
                # Close short
                exit_price = price
                pnl = (entry_price - exit_price) / entry_price
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': date,
                    'direction': 'short',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl,
                    'pnl_abs': pnl * self.config['initial_capital'],
                    'strength': strength
                })
                # Open long
                position = 1
                entry_price = price
                entry_date = date
                
            elif signal == -1 and position == 1:  # Close long, open short
                exit_price = price
                pnl = (exit_price - entry_price) / entry_price
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': date,
                    'direction': 'long',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl,
                    'pnl_abs': pnl * self.config['initial_capital'],
                    'strength': strength
                })
                position = -1
                entry_price = price
                entry_date = date
        
        # Close any open position at end
        if position != 0 and entry_date is not None:
            exit_price = df['close'].iloc[-1]
            pnl = (exit_price - entry_price) / entry_price if position == 1 else (entry_price - exit_price) / entry_price
            trades.append({
                'entry_date': entry_date,
                'exit_date': df.index[-1],
                'direction': 'long' if position == 1 else 'short',
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl_pct': pnl,
                'pnl_abs': pnl * self.config['initial_capital'],
                'strength': signals['strength'].iloc[-1]
            })
            
        return pd.DataFrame(trades)
    
    def _calculate_metrics(self, trades: pd.DataFrame, df: pd.DataFrame) -> Dict:
        """Calculate performance metrics"""
        if len(trades) == 0:
            return {}
            
        winning_trades = trades[trades['pnl_pct'] > 0]
        losing_trades = trades[trades['pnl_pct'] < 0]
        
        total_pnl = trades['pnl_pct'].sum()
        win_rate = len(winning_trades) / len(trades) if len(trades) > 0 else 0
        
        avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0
        profit_factor = abs(avg_win * len(winning_trades)) / abs(avg_loss * len(losing_trades)) if avg_loss != 0 else np.inf
        
        # Sharpe ratio (simplified)
        returns = trades['pnl_pct'].values
        if len(returns) > 1:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252 * 24 * 60 / 5)  # Annualized for 5m
        else:
            sharpe = 0
            
        # Max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0
        
        return {
            'total_return_pct': total_pnl * 100,
            'win_rate': win_rate * 100,
            'avg_win_pct': avg_win * 100,
            'avg_loss_pct': avg_loss * 100,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': abs(max_drawdown) * 100,
            'total_trades': len(trades),
            'avg_trade_pct': trades['pnl_pct'].mean() * 100
        }

# ============================================
# BATCH BACKTESTER
# ============================================

class BatchBacktester:
    """Runs backtests across multiple symbols, strategies, and timeframes"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.engine = BacktestEngine(config)
        self.results = []
        
    def run_all_combinations(self) -> List[Dict]:
        """Test all symbol/strategy/timeframe combinations"""
        total_combinations = len(CRYPTO_PAIRS) * len(STRATEGIES) * len(self.config['timeframes'])
        print(f"Running {total_combinations} backtest combinations...")
        
        count = 0
        for symbol in CRYPTO_PAIRS:
            for strategy_name in STRATEGIES.keys():
                for timeframe in self.config['timeframes']:
                    count += 1
                    print(f"[{count}/{total_combinations}] Testing {symbol} - {strategy_name} - {timeframe}")
                    
                    result = self.engine.run_backtest(symbol, strategy_name, timeframe)
                    if result:
                        self.results.append(result)
                        
        print(f"\nCompleted: {len(self.results)} successful backtests")
        return self.results
    
    def find_optimal_configs(self) -> Dict:
        """
        Find optimal strategy+timeframe for each symbol
        Returns dict: {symbol: {strategy, timeframe, metrics}}
        """
        optimal = {}
        
        for result in self.results:
            symbol = result['symbol']
            score = self._calculate_score(result['metrics'])
            
            if symbol not in optimal or score > optimal[symbol]['score']:
                optimal[symbol] = {
                    'strategy': result['strategy'],
                    'timeframe': result['timeframe'],
                    'metrics': result['metrics'],
                    'score': score
                }
                
        return optimal
    
    def _calculate_score(self, metrics: Dict) -> float:
        """
        Calculate composite score for ranking
        Higher is better
        """
        if not metrics:
            return 0
            
        # Weighted combination
        sharpe = metrics.get('sharpe_ratio', 0) * 0.3
        win_rate = metrics.get('win_rate', 0) / 100 * 0.25
        profit_factor = min(metrics.get('profit_factor', 1), 3) * 0.2
        max_dd = -metrics.get('max_drawdown_pct', 100) / 100 * 0.15  # Negative weight
        trades = min(metrics.get('total_trades', 0) / 100, 1) * 0.1
        
        return sharpe + win_rate + profit_factor + max_dd + trades
    
    def save_results(self, output_dir: str = './backtest_results'):
        """Save backtest results to JSON"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save all results
        with open(os.path.join(output_dir, 'all_results.json'), 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
            
        # Save optimal configs
        optimal = self.find_optimal_configs()
        with open(os.path.join(output_dir, 'optimal_configs.json'), 'w') as f:
            json.dump(optimal, f, indent=2, default=str)
            
        # Generate summary report
        self._generate_report(output_dir)
        
        print(f"Results saved to {output_dir}")
        
    def _generate_report(self, output_dir: str):
        """Generate markdown report"""
        report = "# STEPFUN Backtest Results\n\n"
        report += f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Optimal configurations table
        report += "## Optimal Configurations Per Symbol\n\n"
        report += "| Symbol | Strategy | Timeframe | Win Rate | Profit Factor | Sharpe | Max DD |\n"
        report += "|--------|----------|-----------|----------|---------------|--------|--------|\n"
        
        optimal = self.find_optimal_configs()
        for symbol, data in sorted(optimal.items()):
            m = data['metrics']
            report += f"| {symbol} | {data['strategy']} | {data['timeframe']} | "
            report += f"{m.get('win_rate', 0):.1f}% | {m.get('profit_factor', 0):.2f} | "
            report += f"{m.get('sharpe_ratio', 0):.2f} | {m.get('max_drawdown_pct', 0):.1f}% |\n"
            
        # Top performers
        report += "\n## Top 10 Strategy Performers\n\n"
        report += "| Symbol | Strategy | Timeframe | Score | Win Rate | Sharpe |\n"
        report += "|--------|----------|-----------|-------|----------|--------|\n"
        
        sorted_results = sorted(self.results, key=lambda x: self._calculate_score(x['metrics']), reverse=True)[:10]
        for r in sorted_results:
            m = r['metrics']
            report += f"| {r['symbol']} | {r['strategy']} | {r['timeframe']} | "
            report += f"{self._calculate_score(m):.3f} | {m.get('win_rate', 0):.1f}% | {m.get('sharpe_ratio', 0):.2f} |\n"
            
        with open(os.path.join(output_dir, 'report.md'), 'w') as f:
            f.write(report)

# ============================================
# MAIN EXECUTION
# ============================================

def main():
    """Run the backtest suite"""
    print("=" * 60)
    print("STEPFUN BACKTEST ENGINE")
    print("=" * 60)
    
    # Initialize batch backtester
    batch = BatchBacktester(BACKTEST_CONFIG)
    
    # Run all combinations
    results = batch.run_all_combinations()
    
    # Find optimal configurations
    optimal = batch.find_optimal_configs()
    print("\n" + "=" * 60)
    print("OPTIMAL CONFIGURATIONS")
    print("=" * 60)
    for symbol, data in sorted(optimal.items()):
        m = data['metrics']
        print(f"\n{symbol}:")
        print(f"  Strategy: {data['strategy']}")
        print(f"  Timeframe: {data['timeframe']}")
        print(f"  Win Rate: {m.get('win_rate', 0):.1f}%")
        print(f"  Profit Factor: {m.get('profit_factor', 0):.2f}")
        print(f"  Sharpe: {m.get('sharpe_ratio', 0):.2f}")
        print(f"  Max DD: {m.get('max_drawdown_pct', 0):.1f}%")
        
    # Save results
    batch.save_results('./backtest_results')
    
    print("\n" + "=" * 60)
    print("BACKTEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
