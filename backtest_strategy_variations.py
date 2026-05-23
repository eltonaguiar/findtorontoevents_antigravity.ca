#!/usr/bin/env python3
"""
Backtest Strategy Variations
============================

Backtests generated strategy variations against historical data.
Uses vectorized backtesting for speed.

Reference: Marcos Lopez de Prado's "Advances in Financial Machine Learning"
for backtesting best practices.
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import logging
import yfinance as yf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Results from a single backtest"""
    strategy_name: str
    symbol: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    num_trades: int
    avg_trade: float
    avg_win: float
    avg_loss: float
    
    def to_dict(self) -> Dict:
        return {
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'total_return': round(self.total_return, 4),
            'sharpe_ratio': round(self.sharpe_ratio, 2),
            'max_drawdown': round(self.max_drawdown, 4),
            'win_rate': round(self.win_rate, 2),
            'profit_factor': round(self.profit_factor, 2),
            'num_trades': self.num_trades,
            'avg_trade': round(self.avg_trade, 4),
            'avg_win': round(self.avg_win, 4),
            'avg_loss': round(self.avg_loss, 4)
        }


class DataFetcher:
    """Fetches and caches price data"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {}
    
    def fetch(self, symbol: str, period: str = "3mo", interval: str = "1h") -> pd.DataFrame:
        """Fetch data with caching"""
        cache_key = f"{symbol}_{period}_{interval}"
        cache_file = self.cache_dir / f"{cache_key}.csv"
        
        # Check memory cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Check file cache
        if cache_file.exists():
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            self._cache[cache_key] = df
            return df
        
        # Fetch from yfinance
        logger.info(f"Fetching data for {symbol}")
        try:
            # Convert symbol format
            yf_symbol = symbol.replace('USDT', '-USD')
            df = yf.download(yf_symbol, period=period, interval=interval, progress=False)
            
            if len(df) > 0:
                df.to_csv(cache_file)
                self._cache[cache_key] = df
                return df
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
        
        return pd.DataFrame()


class KeltnerStrategy:
    """Keltner Channel Compression-Expansion Strategy"""
    
    def __init__(self, params: Dict):
        self.atr_period = params.get('atr_period', 14)
        self.atr_mult = params.get('atr_multiplier', 2.0)
        self.compression_bars = params.get('compression_bars', 3)
        self.band_width_thresh = params.get('band_width_threshold', 0.5)
        self.tp_mult = params.get('tp_atr_mult', 2.5)
        self.sl_mult = params.get('sl_atr_mult', 1.5)
        self.time_exit = params.get('time_exit_hours', 12)
    
    def calculate_keltner(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Keltner Channels"""
        df = df.copy()
        
        # Typical Price
        df['tp'] = (df['High'] + df['Low'] + df['Close']) / 3
        
        # ATR
        df['tr1'] = df['High'] - df['Low']
        df['tr2'] = abs(df['High'] - df['Close'].shift())
        df['tr3'] = abs(df['Low'] - df['Close'].shift())
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(self.atr_period).mean()
        
        # EMA of typical price
        df['ema_tp'] = df['tp'].ewm(span=self.atr_period).mean()
        
        # Keltner Bands
        df['upper'] = df['ema_tp'] + self.atr_mult * df['atr']
        df['lower'] = df['ema_tp'] - self.atr_mult * df['atr']
        df['band_width'] = (df['upper'] - df['lower']) / df['ema_tp']
        
        # Band width moving average for compression detection
        df['band_width_ma'] = df['band_width'].rolling(self.compression_bars).mean()
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate entry/exit signals"""
        df = self.calculate_keltner(df)
        
        # Compression detection
        df['is_compressed'] = df['band_width'] < self.band_width_thresh
        df['compression_count'] = df['is_compressed'].rolling(self.compression_bars).sum()
        df['was_compressed'] = df['compression_count'] >= self.compression_bars
        
        # Expansion breakout
        df['breakout_up'] = (df['Close'] > df['upper']) & df['was_compressed'].shift(1)
        df['breakout_down'] = (df['Close'] < df['lower']) & df['was_compressed'].shift(1)
        
        return df
    
    def backtest(self, df: pd.DataFrame) -> BacktestResult:
        """Run vectorized backtest"""
        df = self.generate_signals(df)
        
        trades = []
        in_position = False
        entry_price = 0
        entry_time = None
        direction = None
        
        for i in range(len(df)):
            if i < self.atr_period + 10:
                continue
            
            row = df.iloc[i]
            
            if not in_position:
                # Check for entry
                if row['breakout_up']:
                    in_position = True
                    direction = 'LONG'
                    entry_price = row['Close']
                    entry_time = df.index[i]
                    atr = row['atr']
                    tp_price = entry_price + self.tp_mult * atr
                    sl_price = entry_price - self.sl_mult * atr
                elif row['breakout_down']:
                    in_position = True
                    direction = 'SHORT'
                    entry_price = row['Close']
                    entry_time = df.index[i]
                    atr = row['atr']
                    tp_price = entry_price - self.tp_mult * atr
                    sl_price = entry_price + self.sl_mult * atr
            
            else:
                # Check for exit
                exit_trade = False
                exit_price = row['Close']
                exit_reason = None
                
                # Time exit
                bars_held = i - df.index.get_loc(entry_time)
                if bars_held >= self.time_exit:
                    exit_trade = True
                    exit_reason = 'TIME'
                
                # TP/SL for LONG
                elif direction == 'LONG':
                    if row['High'] >= tp_price:
                        exit_trade = True
                        exit_price = tp_price
                        exit_reason = 'TP'
                    elif row['Low'] <= sl_price:
                        exit_trade = True
                        exit_price = sl_price
                        exit_reason = 'SL'
                
                # TP/SL for SHORT
                elif direction == 'SHORT':
                    if row['Low'] <= tp_price:
                        exit_trade = True
                        exit_price = tp_price
                        exit_reason = 'TP'
                    elif row['High'] >= sl_price:
                        exit_trade = True
                        exit_price = sl_price
                        exit_reason = 'SL'
                
                if exit_trade:
                    # Calculate PnL
                    if direction == 'LONG':
                        pnl_pct = (exit_price - entry_price) / entry_price
                    else:
                        pnl_pct = (entry_price - exit_price) / entry_price
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': df.index[i],
                        'direction': direction,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl_pct': pnl_pct,
                        'exit_reason': exit_reason
                    })
                    
                    in_position = False
                    direction = None
        
        # Calculate metrics
        if len(trades) == 0:
            return BacktestResult(
                strategy_name='keltner_compression',
                symbol=df.index.name or 'unknown',
                total_return=0, sharpe_ratio=0, max_drawdown=0,
                win_rate=0, profit_factor=0, num_trades=0,
                avg_trade=0, avg_win=0, avg_loss=0
            )
        
        trades_df = pd.DataFrame(trades)
        returns = trades_df['pnl_pct']
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        
        total_return = (1 + returns).prod() - 1
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # Max drawdown
        equity = (1 + returns).cumprod()
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max
        max_dd = drawdown.min()
        
        win_rate = len(wins) / len(returns)
        profit_factor = abs(wins.sum() / losses.sum()) if len(losses) > 0 else float('inf')
        
        return BacktestResult(
            strategy_name='keltner_compression',
            symbol=df.index.name or 'unknown',
            total_return=total_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            win_rate=win_rate,
            profit_factor=profit_factor,
            num_trades=len(trades),
            avg_trade=returns.mean(),
            avg_win=wins.mean() if len(wins) > 0 else 0,
            avg_loss=losses.mean() if len(losses) > 0 else 0
        )


class VWAPStrategy:
    """VWAP Mean Reversion Strategy"""
    
    def __init__(self, params: Dict):
        self.deviation_thresh = params.get('deviation_threshold', 2.0)
        self.tp_pct = params.get('tp_pct', 1.0)
        self.sl_pct = params.get('sl_pct', 1.5)
        self.time_exit = params.get('time_exit_hours', 8)
        self.use_rsi = params.get('rsi_confirmation', True)
    
    def calculate_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate VWAP"""
        df = df.copy()
        
        # Typical Price * Volume
        df['tp_vol'] = (df['High'] + df['Low'] + df['Close']) / 3 * df['Volume']
        
        # Reset VWAP calculation daily (simplified)
        df['cumulative_tp_vol'] = df['tp_vol'].cumsum()
        df['cumulative_vol'] = df['Volume'].cumsum()
        df['vwap'] = df['cumulative_tp_vol'] / df['cumulative_vol']
        
        # Deviation from VWAP
        df['vwap_deviation'] = (df['Close'] - df['vwap']) / df['vwap']
        
        # RSI
        if self.use_rsi:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
        
        return df
    
    def backtest(self, df: pd.DataFrame) -> BacktestResult:
        """Run backtest"""
        df = self.calculate_vwap(df)
        
        trades = []
        in_position = False
        entry_price = 0
        entry_time = None
        direction = None
        
        for i in range(50, len(df)):
            row = df.iloc[i]
            
            if not in_position:
                # Long entry: price below VWAP with RSI confirmation
                if row['vwap_deviation'] < -self.deviation_thresh / 100:
                    if not self.use_rsi or row['rsi'] < 40:
                        in_position = True
                        direction = 'LONG'
                        entry_price = row['Close']
                        entry_time = df.index[i]
                
                # Short entry: price above VWAP
                elif row['vwap_deviation'] > self.deviation_thresh / 100:
                    if not self.use_rsi or row['rsi'] > 60:
                        in_position = True
                        direction = 'SHORT'
                        entry_price = row['Close']
                        entry_time = df.index[i]
            
            else:
                exit_trade = False
                exit_price = row['Close']
                
                bars_held = i - df.index.get_loc(entry_time)
                
                # Time exit
                if bars_held >= self.time_exit:
                    exit_trade = True
                
                # PnL based exit
                if direction == 'LONG':
                    pnl = (row['Close'] - entry_price) / entry_price
                    if pnl >= self.tp_pct / 100 or pnl <= -self.sl_pct / 100:
                        exit_trade = True
                else:
                    pnl = (entry_price - row['Close']) / entry_price
                    if pnl >= self.tp_pct / 100 or pnl <= -self.sl_pct / 100:
                        exit_trade = True
                
                if exit_trade:
                    if direction == 'LONG':
                        pnl_pct = (exit_price - entry_price) / entry_price
                    else:
                        pnl_pct = (entry_price - exit_price) / entry_price
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': df.index[i],
                        'direction': direction,
                        'pnl_pct': pnl_pct
                    })
                    
                    in_position = False
        
        if len(trades) == 0:
            return BacktestResult(
                strategy_name='vwap_reversion',
                symbol='unknown',
                total_return=0, sharpe_ratio=0, max_drawdown=0,
                win_rate=0, profit_factor=0, num_trades=0,
                avg_trade=0, avg_win=0, avg_loss=0
            )
        
        trades_df = pd.DataFrame(trades)
        returns = trades_df['pnl_pct']
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        
        total_return = (1 + returns).prod() - 1
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        equity = (1 + returns).cumprod()
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max
        max_dd = drawdown.min()
        
        win_rate = len(wins) / len(returns)
        profit_factor = abs(wins.sum() / losses.sum()) if len(losses) > 0 else float('inf')
        
        return BacktestResult(
            strategy_name='vwap_reversion',
            symbol=df.index.name or 'unknown',
            total_return=total_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            win_rate=win_rate,
            profit_factor=profit_factor,
            num_trades=len(trades),
            avg_trade=returns.mean(),
            avg_win=wins.mean() if len(wins) > 0 else 0,
            avg_loss=losses.mean() if len(losses) > 0 else 0
        )


class BacktestRunner:
    """Runs backtests for strategy variations"""
    
    def __init__(self):
        self.data_fetcher = DataFetcher()
        self.results = []
    
    def load_strategy_variations(self, manifest_path: str = "strategy_variations/manifest.json") -> List[Dict]:
        """Load strategy variations from manifest"""
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            return manifest.get('variations', [])
        except FileNotFoundError:
            logger.error(f"Manifest not found: {manifest_path}")
            return []
    
    def run_backtest(self, strategy_config: Dict) -> Optional[BacktestResult]:
        """Run backtest for a single strategy variation"""
        strategy_file = f"strategy_variations/{strategy_config['file']}"
        
        try:
            with open(strategy_file, 'r') as f:
                dna = json.load(f)
        except Exception as e:
            logger.error(f"Error loading {strategy_file}: {e}")
            return None
        
        entry_logic = dna.get('entry_logic', {})
        exit_logic = dna.get('exit_logic', {})
        symbols = dna.get('symbols', ['BTCUSDT'])
        
        all_results = []
        
        for symbol in symbols:
            # Fetch data
            df = self.data_fetcher.fetch(symbol, period="3mo", interval="1h")
            
            if len(df) == 0:
                logger.warning(f"No data for {symbol}")
                continue
            
            # Select strategy type
            strategy_type = entry_logic.get('type', 'keltner_compression')
            
            if strategy_type == 'keltner_compression':
                params = {
                    'atr_period': entry_logic.get('atr_period', 14),
                    'atr_multiplier': entry_logic.get('atr_multiplier', 2.0),
                    'compression_bars': entry_logic.get('compression_bars', 3),
                    'band_width_threshold': entry_logic.get('band_width_threshold', 0.5),
                    'tp_atr_mult': exit_logic.get('tp_atr_mult', 2.5),
                    'sl_atr_mult': exit_logic.get('sl_atr_mult', 1.5),
                    'time_exit_hours': exit_logic.get('time_exit_hours', 12)
                }
                strategy = KeltnerStrategy(params)
                result = strategy.backtest(df)
                result.strategy_name = dna['name']
                result.symbol = symbol
                all_results.append(result)
            
            elif strategy_type == 'vwap_deviation':
                params = {
                    'deviation_threshold': entry_logic.get('deviation_threshold', 2.0),
                    'tp_pct': exit_logic.get('tp_pct', 1.0),
                    'sl_pct': exit_logic.get('sl_pct', 1.5),
                    'time_exit_hours': exit_logic.get('time_exit_hours', 8),
                    'rsi_confirmation': entry_logic.get('rsi_confirmation', True)
                }
                strategy = VWAPStrategy(params)
                result = strategy.backtest(df)
                result.strategy_name = dna['name']
                result.symbol = symbol
                all_results.append(result)
        
        # Aggregate results across symbols
        if len(all_results) == 0:
            return None
        
        if len(all_results) == 1:
            return all_results[0]
        
        # Combine results
        total_trades = sum(r.num_trades for r in all_results)
        if total_trades == 0:
            return None
        
        # Weighted averages
        weights = [r.num_trades for r in all_results]
        avg_return = np.average([r.total_return for r in all_results], weights=weights)
        avg_sharpe = np.average([r.sharpe_ratio for r in all_results], weights=weights)
        avg_drawdown = np.average([r.max_drawdown for r in all_results], weights=weights)
        avg_winrate = np.average([r.win_rate for r in all_results], weights=weights)
        
        return BacktestResult(
            strategy_name=dna['name'],
            symbol='combined',
            total_return=avg_return,
            sharpe_ratio=avg_sharpe,
            max_drawdown=avg_drawdown,
            win_rate=avg_winrate,
            profit_factor=all_results[0].profit_factor,
            num_trades=total_trades,
            avg_trade=np.average([r.avg_trade for r in all_results], weights=weights),
            avg_win=np.average([r.avg_win for r in all_results], weights=weights),
            avg_loss=np.average([r.avg_loss for r in all_results], weights=weights)
        )
    
    def run_all_backtests(self, variations: List[Dict]) -> List[BacktestResult]:
        """Run backtests for all variations"""
        results = []
        
        for i, var in enumerate(variations):
            logger.info(f"Backtesting {i+1}/{len(variations)}: {var['name']}")
            result = self.run_backtest(var)
            if result:
                results.append(result)
        
        return results
    
    def export_results(self, results: List[BacktestResult], output_path: str = "backtest_results/variation_results.json"):
        """Export backtest results"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        results_data = {
            'backtest_date': datetime.now().isoformat(),
            'total_strategies': len(results),
            'results': [r.to_dict() for r in results]
        }
        
        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        logger.info(f"Exported {len(results)} results to {output_path}")
    
    def print_summary(self, results: List[BacktestResult]):
        """Print summary of results"""
        print("\n" + "="*80)
        print("BACKTEST RESULTS SUMMARY")
        print("="*80)
        
        if len(results) == 0:
            print("No results to display")
            return
        
        # Sort by Sharpe ratio
        sorted_results = sorted(results, key=lambda x: x.sharpe_ratio, reverse=True)
        
        print(f"\n{'Rank':<5} {'Strategy':<40} {'Symbol':<10} {'Sharpe':<8} {'WR':<6} {'Trades':<7} {'Return':<8}")
        print("-"*80)
        
        for i, r in enumerate(sorted_results[:20], 1):
            print(f"{i:<5} {r.strategy_name[:39]:<40} {r.symbol[:9]:<10} {r.sharpe_ratio:<8.2f} {r.win_rate:<6.1%} {r.num_trades:<7} {r.total_return:<8.2%}")
        
        # Top performers
        print("\n" + "="*80)
        print("TOP PERFORMERS BY CATEGORY")
        print("="*80)
        
        best_sharpe = max(results, key=lambda x: x.sharpe_ratio)
        best_wr = max(results, key=lambda x: x.win_rate)
        best_return = max(results, key=lambda x: x.total_return)
        most_trades = max(results, key=lambda x: x.num_trades)
        
        print(f"\nBest Sharpe Ratio: {best_sharpe.sharpe_ratio:.2f} - {best_sharpe.strategy_name}")
        print(f"Best Win Rate: {best_wr.win_rate:.1%} - {best_wr.strategy_name}")
        print(f"Best Return: {best_return.total_return:.2%} - {best_return.strategy_name}")
        print(f"Most Trades: {most_trades.num_trades} - {most_trades.strategy_name}")
        
        print("\n" + "="*80)


def main():
    """Run backtests for all strategy variations"""
    runner = BacktestRunner()
    
    # Load variations
    variations = runner.load_strategy_variations()
    
    if len(variations) == 0:
        logger.error("No strategy variations found. Run strategy_variation_generator.py first.")
        return
    
    logger.info(f"Loaded {len(variations)} strategy variations")
    
    # Run backtests
    results = runner.run_all_backtests(variations)
    
    # Export and print
    runner.export_results(results)
    runner.print_summary(results)


if __name__ == "__main__":
    main()
