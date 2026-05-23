"""
Backtest Script for Justin & J Bravo Strategies
===============================================
Comprehensive backtesting across crypto pairs with variations.
Stores results in audit database for tracking.
"""

import sqlite3
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from justin_bravo_strategies import (
    JUSTIN_BRAVO_STRATEGIES,
    run_all_justin_strategies
)


@dataclass
class Trade:
    symbol: str
    direction: str
    entry_price: float
    take_profit: float
    stop_loss: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    pnl_pct: Optional[float] = None
    strategy: str = ''
    confidence: float = 0.5


@dataclass
class BacktestResult:
    strategy: str
    symbol: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    avg_pnl: float
    total_pnl: float
    profit_factor: float
    max_drawdown: float
    sharpe: float
    trades: List[Trade]


class JustinBravoBacktester:
    """Backtester for Justin & J Bravo strategies."""
    
    def __init__(self, data_source: str = 'crypto_data.db'):
        self.data_source = data_source
        self.results: List[BacktestResult] = []
        
    def load_crypto_data(self, symbol: str, lookback_days: int = 90) -> pd.DataFrame:
        """Load historical data for a symbol."""
        try:
            conn = sqlite3.connect(self.data_source)
            
            # Handle symbol format (BTCUSDT -> BTC/USDT)
            db_symbol = symbol
            if '/' not in symbol:
                db_symbol = symbol.replace('USDT', '/USDT').replace('BTC', '/BTC')
            
            # Try to load from crypto_data.db
            query = f"""
                SELECT timestamp, open, high, low, close, volume
                FROM klines
                WHERE pair = '{db_symbol}'
                ORDER BY timestamp DESC
                LIMIT {lookback_days * 288}  -- ~288 5m candles per day
            """
            df = pd.read_sql(query, conn)
            conn.close()
            
            if len(df) == 0:
                return pd.DataFrame()
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"Error loading {symbol}: {e}")
            return pd.DataFrame()
    
    def simulate_trade(self, trade: Trade, df: pd.DataFrame, 
                       entry_idx: int, max_hold_bars: int = 100) -> Trade:
        """Simulate a trade from entry to exit."""
        if entry_idx >= len(df) - 1:
            return trade
        
        entry_price = trade.entry_price
        tp = trade.take_profit
        sl = trade.stop_loss
        direction = trade.direction
        
        # Walk forward through price data
        for i in range(entry_idx + 1, min(entry_idx + max_hold_bars, len(df))):
            bar = df.iloc[i]
            high = bar['high']
            low = bar['low']
            close = bar['close']
            
            if direction == 'LONG':
                # Check TP hit
                if high >= tp:
                    trade.exit_price = tp
                    trade.exit_reason = 'TP'
                    trade.pnl_pct = (tp - entry_price) / entry_price * 100
                    trade.exit_time = bar.name if hasattr(bar, 'name') else None
                    return trade
                
                # Check SL hit
                if low <= sl:
                    trade.exit_price = sl
                    trade.exit_reason = 'SL'
                    trade.pnl_pct = (sl - entry_price) / entry_price * 100
                    trade.exit_time = bar.name if hasattr(bar, 'name') else None
                    return trade
            
            else:  # SHORT
                # Check TP hit (price went down)
                if low <= tp:
                    trade.exit_price = tp
                    trade.exit_reason = 'TP'
                    trade.pnl_pct = (entry_price - tp) / entry_price * 100
                    trade.exit_time = bar.name if hasattr(bar, 'name') else None
                    return trade
                
                # Check SL hit (price went up)
                if high >= sl:
                    trade.exit_price = sl
                    trade.exit_reason = 'SL'
                    trade.pnl_pct = (entry_price - sl) / entry_price * 100
                    trade.exit_time = bar.name if hasattr(bar, 'name') else None
                    return trade
        
        # Time-based exit
        final_bar = df.iloc[min(entry_idx + max_hold_bars - 1, len(df) - 1)]
        final_price = final_bar['close']
        
        if direction == 'LONG':
            trade.pnl_pct = (final_price - entry_price) / entry_price * 100
        else:
            trade.pnl_pct = (entry_price - final_price) / entry_price * 100
        
        trade.exit_price = final_price
        trade.exit_reason = 'TIME'
        trade.exit_time = final_bar.name if hasattr(final_bar, 'name') else None
        
        return trade
    
    def run_strategy(self, strategy_name: str, strategy_fn, 
                     symbol: str, df: pd.DataFrame) -> BacktestResult:
        """Run a single strategy on a symbol."""
        trades = []
        
        # Walk forward analysis
        min_bars = 55  # Minimum bars needed for indicators
        step = 5  # Check every 5 bars (25 minutes for 5m data)
        
        for i in range(min_bars, len(df) - 100, step):
            # Get data up to current point
            hist_df = df.iloc[:i]
            
            # Create data dict for strategy
            data = {symbol: hist_df}
            
            # Generate signals
            try:
                picks = strategy_fn(data)
            except Exception as e:
                continue
            
            if not picks:
                continue
            
            # Process each pick
            for pick in picks:
                # Check if we have enough data to simulate exit
                if i >= len(df) - 10:
                    continue
                
                trade = Trade(
                    symbol=symbol,
                    direction=pick['direction'],
                    entry_price=pick['entry_price'],
                    take_profit=pick['take_profit'],
                    stop_loss=pick['stop_loss'],
                    entry_time=hist_df.index[-1],
                    strategy=strategy_name,
                    confidence=pick.get('confidence', 0.5)
                )
                
                # Simulate the trade
                completed_trade = self.simulate_trade(trade, df, i)
                trades.append(completed_trade)
        
        # Calculate statistics
        if not trades:
            return BacktestResult(
                strategy=strategy_name,
                symbol=symbol,
                total_trades=0,
                wins=0,
                losses=0,
                win_rate=0,
                avg_pnl=0,
                total_pnl=0,
                profit_factor=0,
                max_drawdown=0,
                sharpe=0,
                trades=[]
            )
        
        wins = sum(1 for t in trades if t.pnl_pct and t.pnl_pct > 0)
        losses = sum(1 for t in trades if t.pnl_pct and t.pnl_pct <= 0)
        total = wins + losses
        
        win_rate = (wins / total * 100) if total > 0 else 0
        
        pnls = [t.pnl_pct for t in trades if t.pnl_pct is not None]
        avg_pnl = np.mean(pnls) if pnls else 0
        total_pnl = sum(pnls)
        
        # Profit factor
        gross_profit = sum(t.pnl_pct for t in trades if t.pnl_pct and t.pnl_pct > 0)
        gross_loss = abs(sum(t.pnl_pct for t in trades if t.pnl_pct and t.pnl_pct <= 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Max drawdown
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_drawdown = abs(min(drawdown)) if len(drawdown) > 0 else 0
        
        # Sharpe ratio (simplified)
        if len(pnls) > 1 and np.std(pnls) > 0:
            sharpe = (np.mean(pnls) / np.std(pnls)) * np.sqrt(252)  # Annualized
        else:
            sharpe = 0
        
        return BacktestResult(
            strategy=strategy_name,
            symbol=symbol,
            total_trades=total,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            avg_pnl=avg_pnl,
            total_pnl=total_pnl,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe=sharpe,
            trades=trades
        )
    
    def run_full_backtest(self, symbols: List[str], 
                          strategies: Optional[Dict] = None) -> List[BacktestResult]:
        """Run backtest for all symbols and strategies."""
        if strategies is None:
            strategies = JUSTIN_BRAVO_STRATEGIES
        
        all_results = []
        
        for symbol in symbols:
            print(f"\n{'='*60}")
            print(f"Testing {symbol}")
            print('='*60)
            
            df = self.load_crypto_data(symbol)
            if len(df) < 100:
                print(f"  Insufficient data for {symbol}")
                continue
            
            print(f"  Loaded {len(df)} bars")
            
            for strategy_name, strategy_fn in strategies.items():
                print(f"  Running {strategy_name}...", end=' ')
                
                result = self.run_strategy(strategy_name, strategy_fn, symbol, df)
                all_results.append(result)
                
                if result.total_trades > 0:
                    print(f"Trades: {result.total_trades}, WR: {result.win_rate:.1f}%, "
                          f"PF: {result.profit_factor:.2f}, PnL: {result.total_pnl:.2f}%")
                else:
                    print("No trades")
        
        self.results = all_results
        return all_results
    
    def get_best_performers(self, min_trades: int = 5) -> List[BacktestResult]:
        """Get best performing strategy-symbol combinations."""
        filtered = [r for r in self.results if r.total_trades >= min_trades]
        
        # Sort by win rate, then profit factor, then total PnL
        sorted_results = sorted(
            filtered,
            key=lambda x: (x.win_rate, x.profit_factor, x.total_pnl),
            reverse=True
        )
        
        return sorted_results
    
    def analyze_by_symbol(self) -> Dict[str, Dict]:
        """Analyze performance by symbol."""
        symbol_stats = {}
        
        for result in self.results:
            if result.symbol not in symbol_stats:
                symbol_stats[result.symbol] = {
                    'strategies': [],
                    'total_trades': 0,
                    'best_strategy': None,
                    'best_win_rate': 0
                }
            
            stats = symbol_stats[result.symbol]
            stats['strategies'].append(result.strategy)
            stats['total_trades'] += result.total_trades
            
            if result.win_rate > stats['best_win_rate'] and result.total_trades >= 5:
                stats['best_win_rate'] = result.win_rate
                stats['best_strategy'] = result.strategy
        
        return symbol_stats
    
    def analyze_by_strategy(self) -> Dict[str, Dict]:
        """Analyze performance by strategy."""
        strategy_stats = {}
        
        for result in self.results:
            if result.strategy not in strategy_stats:
                strategy_stats[result.strategy] = {
                    'symbols': [],
                    'total_trades': 0,
                    'total_pnl': 0,
                    'avg_win_rate': 0,
                    'profitable_symbols': 0
                }
            
            stats = strategy_stats[result.strategy]
            stats['symbols'].append(result.symbol)
            stats['total_trades'] += result.total_trades
            stats['total_pnl'] += result.total_pnl
            
            if result.total_pnl > 0:
                stats['profitable_symbols'] += 1
        
        # Calculate averages
        for strategy, stats in strategy_stats.items():
            relevant_results = [r for r in self.results if r.strategy == strategy and r.total_trades >= 5]
            if relevant_results:
                stats['avg_win_rate'] = np.mean([r.win_rate for r in relevant_results])
        
        return strategy_stats
    
    def save_to_audit_db(self, db_path: str = 'data/audit_trail.db'):
        """Save backtest results to audit database."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            run_id = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            
            for result in self.results:
                if result.total_trades == 0:
                    continue
                
                # Insert into bt_backtest_runs
                cursor.execute("""
                    INSERT OR REPLACE INTO bt_backtest_runs
                    (id, source_db, source_table, strategy, symbol, asset_class,
                     total_trades, wins, losses, win_rate, profit_factor,
                     total_return, sharpe, max_drawdown, imported_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"{run_id}_{result.strategy}_{result.symbol}",
                    'justin_bravo_backtest',
                    'backtest_results',
                    result.strategy,
                    result.symbol,
                    'CRYPTO',
                    result.total_trades,
                    result.wins,
                    result.losses,
                    result.win_rate / 100,  # Store as decimal
                    result.profit_factor,
                    result.total_pnl,
                    result.sharpe,
                    result.max_drawdown,
                    datetime.now(timezone.utc).isoformat()
                ))
                
                # Insert individual trades
                for trade in result.trades:
                    cursor.execute("""
                        INSERT INTO bt_backtest_trades
                        (backtest_run_id, source_db, source_table, symbol, asset_class,
                         direction, strategy, entry_price, exit_price, take_profit, stop_loss,
                         entry_time, exit_time, pnl_pct, status, imported_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"{run_id}_{result.strategy}_{result.symbol}",
                        'justin_bravo_backtest',
                        'backtest_trades',
                        trade.symbol,
                        'CRYPTO',
                        trade.direction,
                        result.strategy,
                        trade.entry_price,
                        trade.exit_price,
                        trade.take_profit,
                        trade.stop_loss,
                        trade.entry_time.isoformat() if trade.entry_time else None,
                        trade.exit_time.isoformat() if trade.exit_time else None,
                        trade.pnl_pct,
                        'WON' if trade.pnl_pct and trade.pnl_pct > 0 else 'LOST',
                        datetime.now(timezone.utc).isoformat()
                    ))
            
            conn.commit()
            conn.close()
            print(f"\nOK Saved results to {db_path}")
            
        except Exception as e:
            print(f"Error saving to audit DB: {e}")
    
    def generate_report(self) -> str:
        """Generate a comprehensive backtest report."""
        lines = []
        lines.append("="*80)
        lines.append("JUSTIN & J BRAVO STRATEGIES - BACKTEST REPORT")
        lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        lines.append("="*80)
        
        # Top performers
        lines.append("\n*** TOP PERFORMERS (min 5 trades) ***")
        lines.append("-"*80)
        top = self.get_best_performers(min_trades=5)[:20]
        
        for i, r in enumerate(top, 1):
            lines.append(f"{i:2}. {r.strategy:35} | {r.symbol:12} | "
                        f"Trades: {r.total_trades:3} | WR: {r.win_rate:5.1f}% | "
                        f"PF: {r.profit_factor:5.2f} | PnL: {r.total_pnl:8.2f}%")
        
        # Best by symbol
        lines.append("\n*** BEST STRATEGY BY SYMBOL ***")
        lines.append("-"*80)
        symbol_analysis = self.analyze_by_symbol()
        for symbol, stats in sorted(symbol_analysis.items()):
            if stats['best_strategy']:
                lines.append(f"  {symbol:12} -> {stats['best_strategy']:35} "
                            f"(WR: {stats['best_win_rate']:.1f}%)")
        
        # Strategy summary
        lines.append("\n*** STRATEGY SUMMARY ***")
        lines.append("-"*80)
        strategy_analysis = self.analyze_by_strategy()
        for strategy, stats in sorted(strategy_analysis.items(), 
                                       key=lambda x: x[1]['total_pnl'], reverse=True):
            lines.append(f"  {strategy:35} | Symbols: {len(stats['symbols']):2} | "
                        f"Trades: {stats['total_trades']:4} | "
                        f"Profitable: {stats['profitable_symbols']:2}/{len(stats['symbols'])} | "
                        f"Avg WR: {stats['avg_win_rate']:5.1f}% | "
                        f"Total PnL: {stats['total_pnl']:10.2f}%")
        
        lines.append("\n" + "="*80)
        
        return '\n'.join(lines)


def main():
    """Main backtest execution."""
    # Crypto pairs to test
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
        'DOGEUSDT', 'SHIBUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT',
        'MATICUSDT', 'UNIUSDT', 'LTCUSDT', 'BCHUSDT', 'ETCUSDT',
        'ATOMUSDT', 'VETUSDT', 'FILUSDT', 'TRXUSDT', 'EOSUSDT',
        'AAVEUSDT', 'XLMUSDT', 'ALGOUSDT', 'XTZUSDT', 'SUSHIUSDT'
    ]
    
    print("="*80)
    print("JUSTIN & J BRAVO STRATEGY BACKTEST")
    print("="*80)
    print(f"Testing {len(symbols)} crypto pairs across {len(JUSTIN_BRAVO_STRATEGIES)} strategies")
    
    # Initialize backtester
    bt = JustinBravoBacktester(data_source='crypto_data.db')
    
    # Run backtest
    results = bt.run_full_backtest(symbols)
    
    # Generate and print report
    report = bt.generate_report()
    print(report)
    
    # Save to file
    report_file = f'backtest_results/justin_bravo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    os.makedirs('backtest_results', exist_ok=True)
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"\nOK Report saved to {report_file}")
    
    # Save to audit database
    bt.save_to_audit_db()
    
    # Return top 5 strategies for further analysis
    top5 = bt.get_best_performers(min_trades=5)[:5]
    print("\n🎯 TOP 5 STRATEGIES FOR PRODUCTION:")
    for r in top5:
        print(f"   {r.strategy} on {r.symbol}: {r.win_rate:.1f}% WR, {r.profit_factor:.2f} PF")
    
    return top5


if __name__ == '__main__':
    top_strategies = main()
