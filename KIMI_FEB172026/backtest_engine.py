"""
KIMI_FEB172026 - Backtest Engine
Validates strategies against historical data
Optimizes parameters for each asset class
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from pathlib import Path
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KIMI_BACKTEST")

@dataclass
class BacktestResult:
    """Backtest result container"""
    algorithm: str
    asset_class: str
    total_trades: int
    win_rate: float
    total_return_pct: float
    avg_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    profit_factor: float
    expectancy: float
    avg_trade_duration_hours: float
    tp_hit_rate: float
    sl_hit_rate: float
    time_exit_rate: float
    best_params: Dict
    equity_curve: List[float]


class BacktestEngine:
    """
    Backtesting engine for strategy validation
    Tests on historical data before live deployment
    """
    
    def __init__(self, data_dir: str = "KIMI_FEB172026/data"):
        self.data_dir = Path(data_dir)
        self.results = []
        
        # Default parameter grid for optimization
        self.param_grid = {
            "confidence_threshold": [0.50, 0.60, 0.65, 0.70, 0.75, 0.80],
            "tp_multiplier": [1.5, 2.0, 2.5, 3.0, 3.5],
            "sl_multiplier": [0.8, 1.0, 1.2, 1.5, 2.0],
            "time_exit_hours": [12, 18, 24, 36, 48],
            "position_size_pct": [0.05, 0.10, 0.15, 0.20]
        }
    
    def load_historical_data(self, symbol: str, days: int = 90) -> pd.DataFrame:
        """
        Load historical OHLCV data for backtesting
        In production, this would fetch from exchange APIs
        """
        # This is a placeholder - in real implementation would fetch from:
        # - Binance historical data
        # - Yahoo Finance
        # - Local database
        
        logger.info(f"Loading historical data for {symbol}...")
        
        # Generate synthetic data for demonstration
        # In production, replace with actual historical data fetch
        np.random.seed(42)
        n_periods = days * 24  # Hourly data
        
        dates = pd.date_range(end=datetime.now(), periods=n_periods, freq='H')
        
        # Generate realistic crypto price movement
        returns = np.random.normal(0.0005, 0.02, n_periods)  # Mean 0.05%, std 2%
        prices = 50000 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.001, n_periods)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, n_periods))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, n_periods))),
            'close': prices,
            'volume': np.random.lognormal(15, 0.5, n_periods)
        })
        
        return df
    
    def simulate_signal(self, df: pd.DataFrame, idx: int, direction: str,
                       tp_multiplier: float, sl_multiplier: float) -> Dict:
        """
        Simulate a single trade from entry to exit
        Returns outcome information
        """
        entry_price = df['close'].iloc[idx]
        
        # Calculate TP/SL levels
        atr = self._calculate_atr(df.iloc[max(0, idx-14):idx+1])
        
        if direction == "LONG":
            tp = entry_price + (atr * tp_multiplier)
            sl = entry_price - (atr * sl_multiplier)
        else:
            tp = entry_price - (atr * tp_multiplier)
            sl = entry_price + (atr * sl_multiplier)
        
        # Simulate forward
        for j in range(idx + 1, min(idx + 48, len(df))):  # Max 48 hours
            current_price = df['close'].iloc[j]
            
            if direction == "LONG":
                if current_price >= tp:
                    return {
                        "exited": True,
                        "exit_reason": "TP_HIT",
                        "exit_price": tp,
                        "pnl_pct": (tp - entry_price) / entry_price * 100,
                        "duration_hours": j - idx
                    }
                elif current_price <= sl:
                    return {
                        "exited": True,
                        "exit_reason": "SL_HIT",
                        "exit_price": sl,
                        "pnl_pct": (sl - entry_price) / entry_price * 100,
                        "duration_hours": j - idx
                    }
            else:
                if current_price <= tp:
                    return {
                        "exited": True,
                        "exit_reason": "TP_HIT",
                        "exit_price": tp,
                        "pnl_pct": (entry_price - tp) / entry_price * 100,
                        "duration_hours": j - idx
                    }
                elif current_price >= sl:
                    return {
                        "exited": True,
                        "exit_reason": "SL_HIT",
                        "exit_price": sl,
                        "pnl_pct": (entry_price - sl) / entry_price * 100,
                        "duration_hours": j - idx
                    }
        
        # Time exit
        final_price = df['close'].iloc[min(idx + 47, len(df) - 1)]
        return {
            "exited": True,
            "exit_reason": "TIME_EXIT",
            "exit_price": final_price,
            "pnl_pct": (final_price - entry_price) / entry_price * 100 if direction == "LONG" 
                       else (entry_price - final_price) / entry_price * 100,
            "duration_hours": 48
        }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(df) < 2:
            return df['close'].iloc[-1] * 0.02
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        return atr if not np.isnan(atr) else df['close'].iloc[-1] * 0.02
    
    def backtest_strategy(self, symbol: str, algorithm: str, 
                         signal_func: Callable, params: Dict) -> BacktestResult:
        """
        Backtest a strategy with given parameters
        """
        df = self.load_historical_data(symbol, days=90)
        
        trades = []
        equity = [10000]  # Start with $10k
        
        for i in range(50, len(df) - 48):  # Skip first 50 for indicators
            # Check for signal
            signal_data = signal_func(df.iloc[:i+1], params)
            
            if signal_data and signal_data.get('signal'):
                direction = signal_data['direction']
                
                # Simulate trade
                outcome = self.simulate_signal(
                    df, i, direction,
                    params.get('tp_multiplier', 2.0),
                    params.get('sl_multiplier', 1.0)
                )
                
                trades.append(outcome)
                
                # Update equity
                position_size = params.get('position_size_pct', 0.1)
                trade_return = outcome['pnl_pct'] / 100 * position_size
                new_equity = equity[-1] * (1 + trade_return)
                equity.append(new_equity)
        
        if not trades:
            return None
        
        # Calculate metrics
        pnls = [t['pnl_pct'] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        total_return = (equity[-1] - equity[0]) / equity[0] * 100
        win_rate = len(wins) / len(trades) if trades else 0
        
        # Sharpe
        returns = np.array(pnls) / 100
        sharpe = 0
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(365)
        
        # Max drawdown
        equity_arr = np.array(equity)
        running_max = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - running_max) / running_max
        max_dd = abs(drawdown.min()) * 100
        
        # Profit factor
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Expectancy
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        # Exit reasons
        tp_hits = len([t for t in trades if t['exit_reason'] == 'TP_HIT'])
        sl_hits = len([t for t in trades if t['exit_reason'] == 'SL_HIT'])
        time_exits = len([t for t in trades if t['exit_reason'] == 'TIME_EXIT'])
        
        return BacktestResult(
            algorithm=algorithm,
            asset_class="crypto",
            total_trades=len(trades),
            win_rate=round(win_rate, 4),
            total_return_pct=round(total_return, 4),
            avg_return_pct=round(np.mean(pnls), 4),
            sharpe_ratio=round(sharpe, 4),
            max_drawdown_pct=round(max_dd, 4),
            profit_factor=round(pf, 4),
            expectancy=round(expectancy, 4),
            avg_trade_duration_hours=round(np.mean([t['duration_hours'] for t in trades]), 2),
            tp_hit_rate=round(tp_hits / len(trades), 4),
            sl_hit_rate=round(sl_hits / len(trades), 4),
            time_exit_rate=round(time_exits / len(trades), 4),
            best_params=params,
            equity_curve=equity
        )
    
    def optimize_parameters(self, symbol: str, algorithm: str,
                           signal_func: Callable) -> BacktestResult:
        """
        Grid search to find optimal parameters
        """
        logger.info(f"Optimizing {algorithm} for {symbol}...")
        
        best_result = None
        best_score = -float('inf')
        
        # Grid search
        for confidence in self.param_grid["confidence_threshold"]:
            for tp_mult in self.param_grid["tp_multiplier"]:
                for sl_mult in self.param_grid["sl_multiplier"]:
                    for time_exit in self.param_grid["time_exit_hours"]:
                        params = {
                            "confidence_threshold": confidence,
                            "tp_multiplier": tp_mult,
                            "sl_multiplier": sl_mult,
                            "time_exit_hours": time_exit,
                            "position_size_pct": 0.1
                        }
                        
                        result = self.backtest_strategy(symbol, algorithm, signal_func, params)
                        
                        if result is None:
                            continue
                        
                        # Score based on risk-adjusted return
                        score = result.total_return_pct / (result.max_drawdown_pct + 1) * result.sharpe_ratio
                        
                        if score > best_score:
                            best_score = score
                            best_result = result
        
        logger.info(f"Optimization complete. Best Sharpe: {best_result.sharpe_ratio}")
        return best_result
    
    def run_full_backtest(self, symbols: List[str], algorithms: Dict[str, Callable]) -> List[BacktestResult]:
        """
        Backtest all strategies on all symbols
        """
        results = []
        
        for symbol in symbols:
            for algo_name, signal_func in algorithms.items():
                logger.info(f"Backtesting {algo_name} on {symbol}...")
                
                result = self.optimize_parameters(symbol, algo_name, signal_func)
                
                if result:
                    results.append(result)
        
        # Sort by Sharpe ratio
        results.sort(key=lambda x: x.sharpe_ratio, reverse=True)
        
        return results
    
    def generate_report(self, results: List[BacktestResult]) -> str:
        """Generate text report of backtest results"""
        report = []
        report.append("=" * 80)
        report.append("KIMI_FEB172026 - Backtest Results")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Strategies Tested: {len(results)}")
        report.append("")
        
        # Summary table
        report.append("TOP PERFORMING STRATEGIES:")
        report.append("-" * 80)
        report.append(f"{'Rank':<5} {'Algorithm':<30} {'Trades':<8} {'Win%':<8} {'Return%':<10} {'Sharpe':<8} {'MaxDD%':<8}")
        report.append("-" * 80)
        
        for i, r in enumerate(results[:10], 1):
            report.append(
                f"{i:<5} {r.algorithm:<30} {r.total_trades:<8} "
                f"{r.win_rate*100:>6.1f}   {r.total_return_pct:>7.1f}    "
                f"{r.sharpe_ratio:>6.2f}   {r.max_drawdown_pct:>6.1f}"
            )
        
        report.append("")
        report.append("BEST PARAMETERS BY STRATEGY:")
        report.append("-" * 80)
        
        for r in results[:5]:
            report.append(f"\n{r.algorithm} ({r.asset_class}):")
            report.append(f"  Win Rate: {r.win_rate:.1%}")
            report.append(f"  Total Return: {r.total_return_pct:+.2f}%")
            report.append(f"  Sharpe: {r.sharpe_ratio:.2f}")
            report.append(f"  Max DD: {r.max_drawdown_pct:.2f}%")
            report.append(f"  Profit Factor: {r.profit_factor:.2f}")
            report.append(f"  Expectancy: {r.expectancy:.2f}%")
            report.append(f"  TP Hit Rate: {r.tp_hit_rate:.1%}")
            report.append(f"  SL Hit Rate: {r.sl_hit_rate:.1%}")
            report.append(f"  Optimal Params: {r.best_params}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


# =============================================================================
# Example signal functions for backtesting
# =============================================================================
def example_pump_detector(df: pd.DataFrame, params: Dict) -> Optional[Dict]:
    """Example pump detection strategy for backtesting"""
    if len(df) < 20:
        return None
    
    # Calculate metrics
    price_change_4h = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5] * 100
    volume_sma = df['volume'].rolling(window=20).mean().iloc[-1]
    volume_ratio = df['volume'].iloc[-1] / volume_sma if volume_sma > 0 else 0
    
    # Simple RSI calculation
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]
    
    if (price_change_4h >= 8 and 
        volume_ratio >= 5 and 
        rsi < 65):
        return {"signal": True, "direction": "LONG"}
    
    return None


def example_mean_reversion(df: pd.DataFrame, params: Dict) -> Optional[Dict]:
    """Example mean reversion strategy"""
    if len(df) < 20:
        return None
    
    # Bollinger Bands
    sma = df['close'].rolling(window=20).mean().iloc[-1]
    std = df['close'].rolling(window=20).std().iloc[-1]
    upper = sma + (std * 2)
    lower = sma - (std * 2)
    
    current = df['close'].iloc[-1]
    
    if current < lower:
        return {"signal": True, "direction": "LONG"}
    elif current > upper:
        return {"signal": True, "direction": "SHORT"}
    
    return None


# =============================================================================
# Entry point
# =============================================================================
def main():
    """Run backtest example"""
    engine = BacktestEngine()
    
    algorithms = {
        "pump-detector": example_pump_detector,
        "mean-reversion": example_mean_reversion
    }
    
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
    
    print("=" * 80)
    print("KIMI_FEB172026 - Backtest Engine")
    print("=" * 80)
    print("\nRunning backtests...\n")
    
    results = engine.run_full_backtest(symbols, algorithms)
    
    print(engine.generate_report(results))
    
    # Save results
    output_file = "KIMI_FEB172026/data/backtest_results.json"
    with open(output_file, 'w') as f:
        json.dump([r.__dict__ for r in results], f, indent=2, default=str)
    
    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()
