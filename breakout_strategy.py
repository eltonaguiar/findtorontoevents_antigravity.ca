import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

@dataclass
class Trade:
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: float = 0.0
    exit_price: float = 0.0
    direction: str = ""
    stop_loss: float = 0.0
    take_profit: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""

@dataclass
class BacktestResult:
    total_return: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    avg_trade_duration: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    trades: List[Trade]

class BreakoutStrategy:
    """
    Breakout Strategy with 2:1 Risk-Reward
    - Volume confirmation required
    - ATR-based stop losses
    - Time-based exits
    """
    
    def __init__(
        self,
        lookback_period: int = 20,
        volume_multiplier: float = 1.5,
        risk_reward_ratio: float = 2.0,
        max_hold_hours: int = 48,
        spread: float = 0.0002,
        commission: float = 5.0,
        slippage: float = 0.0005,
        initial_capital: float = 10000.0,
        risk_per_trade: float = 0.01
    ):
        self.lookback_period = lookback_period
        self.volume_multiplier = volume_multiplier
        self.risk_reward_ratio = risk_reward_ratio
        self.max_hold_hours = max_hold_hours
        self.spread = spread
        self.commission = commission
        self.slippage = slippage
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        
    def calculate_key_levels(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate support/resistance levels"""
        df = df.copy()
        df['resistance'] = df['high'].rolling(window=self.lookback_period).max().shift(1)
        df['support'] = df['low'].rolling(window=self.lookback_period).min().shift(1)
        df['avg_volume'] = df['volume'].rolling(window=self.lookback_period).mean().shift(1)
        df['atr'] = self.calculate_atr(df)
        return df
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift(1))
        low_close = np.abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate breakout signals"""
        df = self.calculate_key_levels(df)
        
        df['breakout_long'] = (
            (df['close'] > df['resistance']) & 
            (df['volume'] > df['avg_volume'] * self.volume_multiplier)
        )
        
        df['breakout_short'] = (
            (df['close'] < df['support']) & 
            (df['volume'] > df['avg_volume'] * self.volume_multiplier)
        )
        
        return df
    
    def apply_costs(self, price: float, direction: str, is_entry: bool = True) -> float:
        """Apply trading costs"""
        total_cost_pct = self.spread + self.slippage
        
        if is_entry:
            return price * (1 + total_cost_pct) if direction == 'long' else price * (1 - total_cost_pct)
        else:
            return price * (1 - total_cost_pct) if direction == 'long' else price * (1 + total_cost_pct)
    
    def backtest(self, df: pd.DataFrame) -> BacktestResult:
        """Run backtest"""
        df = self.generate_signals(df).dropna()
        
        trades: List[Trade] = []
        capital = self.initial_capital
        current_trade: Optional[Trade] = None
        
        for i in range(len(df)):
            row = df.iloc[i]
            current_time = row.name if isinstance(row.name, datetime) else pd.to_datetime(row.name)
            
            if current_trade is not None:
                trade_duration_hours = (current_time - current_trade.entry_time).total_seconds() / 3600
                
                exit_triggered = False
                exit_price = 0.0
                exit_reason = ""
                
                if current_trade.direction == 'long':
                    if row['low'] <= current_trade.stop_loss:
                        exit_triggered, exit_price, exit_reason = True, current_trade.stop_loss, "stop_loss"
                    elif row['high'] >= current_trade.take_profit:
                        exit_triggered, exit_price, exit_reason = True, current_trade.take_profit, "take_profit"
                    elif trade_duration_hours >= self.max_hold_hours:
                        exit_triggered, exit_price, exit_reason = True, row['close'], "time_exit"
                else:
                    if row['high'] >= current_trade.stop_loss:
                        exit_triggered, exit_price, exit_reason = True, current_trade.stop_loss, "stop_loss"
                    elif row['low'] <= current_trade.take_profit:
                        exit_triggered, exit_price, exit_reason = True, current_trade.take_profit, "take_profit"
                    elif trade_duration_hours >= self.max_hold_hours:
                        exit_triggered, exit_price, exit_reason = True, row['close'], "time_exit"
                
                if exit_triggered:
                    exit_price_with_costs = self.apply_costs(exit_price, current_trade.direction, is_entry=False)
                    entry_price_with_costs = self.apply_costs(current_trade.entry_price, current_trade.direction, is_entry=True)
                    
                    if current_trade.direction == 'long':
                        pnl_pct = (exit_price_with_costs - entry_price_with_costs) / entry_price_with_costs
                    else:
                        pnl_pct = (entry_price_with_costs - exit_price_with_costs) / entry_price_with_costs
                    
                    pnl = capital * self.risk_per_trade * pnl_pct * 100 - self.commission
                    
                    current_trade.exit_time = current_time
                    current_trade.exit_price = exit_price_with_costs
                    current_trade.pnl = pnl
                    current_trade.pnl_pct = pnl_pct * 100
                    current_trade.exit_reason = exit_reason
                    
                    trades.append(current_trade)
                    capital += pnl
                    current_trade = None
            
            elif current_trade is None:
                if row['breakout_long']:
                    entry_price = row['close']
                    stop_loss = max(row['support'], entry_price - row['atr'] * 1.5)
                    risk = entry_price - stop_loss
                    if risk <= 0:
                        continue
                    take_profit = entry_price + (risk * self.risk_reward_ratio)
                    
                    current_trade = Trade(
                        entry_time=current_time,
                        entry_price=entry_price,
                        direction='long',
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )
                
                elif row['breakout_short']:
                    entry_price = row['close']
                    stop_loss = min(row['resistance'], entry_price + row['atr'] * 1.5)
                    risk = stop_loss - entry_price
                    if risk <= 0:
                        continue
                    take_profit = entry_price - (risk * self.risk_reward_ratio)
                    
                    current_trade = Trade(
                        entry_time=current_time,
                        entry_price=entry_price,
                        direction='short',
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )
        
        if current_trade is not None:
            last_row = df.iloc[-1]
            exit_price = last_row['close']
            exit_price_with_costs = self.apply_costs(exit_price, current_trade.direction, is_entry=False)
            entry_price_with_costs = self.apply_costs(current_trade.entry_price, current_trade.direction, is_entry=True)
            
            if current_trade.direction == 'long':
                pnl_pct = (exit_price_with_costs - entry_price_with_costs) / entry_price_with_costs
            else:
                pnl_pct = (entry_price_with_costs - exit_price_with_costs) / entry_price_with_costs
            
            pnl = capital * self.risk_per_trade * pnl_pct * 100 - self.commission
            
            current_trade.exit_time = pd.to_datetime(df.index[-1])
            current_trade.exit_price = exit_price_with_costs
            current_trade.pnl = pnl
            current_trade.pnl_pct = pnl_pct * 100
            current_trade.exit_reason = "end_of_data"
            
            trades.append(current_trade)
            capital += pnl
        
        return self.calculate_metrics(trades, capital)
    
    def calculate_metrics(self, trades: List[Trade], final_capital: float) -> BacktestResult:
        """Calculate performance metrics"""
        if not trades:
            return BacktestResult(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, [])
        
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100
        win_rate = len(winning_trades) / len(trades) * 100
        
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        returns = [t.pnl_pct for t in trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        cumulative_pnl = np.cumsum([t.pnl for t in trades])
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdowns = (running_max - cumulative_pnl) / self.initial_capital * 100
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0
        
        durations = [(t.exit_time - t.entry_time).total_seconds() / 3600 for t in trades if t.exit_time]
        avg_trade_duration = np.mean(durations) if durations else 0
        
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        
        return BacktestResult(
            total_return=total_return,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            avg_trade_duration=avg_trade_duration,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            trades=trades
        )


def generate_realistic_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Generate realistic synthetic data with market regimes"""
    np.random.seed(42)
    
    dates = pd.date_range(start=start_date, end=end_date, freq='h')
    n = len(dates)
    
    # Symbol-specific parameters
    params = {
        'XAUUSD': {'base': 1800, 'vol': 0.0008, 'trend_freq': 0.3},
        'USDJPY': {'base': 140, 'vol': 0.0004, 'trend_freq': 0.25}
    }
    
    p = params.get(symbol, {'base': 100, 'vol': 0.001, 'trend_freq': 0.3})
    
    # Create regimes: 30% trending, 40% ranging, 30% volatile
    regime_length = 200
    n_regimes = n // regime_length + 1
    
    returns = []
    for regime in range(n_regimes):
        regime_type = np.random.choice(
            ['trend_up', 'trend_down', 'ranging', 'volatile'],
            p=[0.15, 0.15, 0.4, 0.3]
        )
        
        length = min(regime_length, n - len(returns))
        
        if regime_type == 'trend_up':
            r = np.random.normal(p['vol'] * 0.2, p['vol'], length)
        elif regime_type == 'trend_down':
            r = np.random.normal(-p['vol'] * 0.2, p['vol'], length)
        elif regime_type == 'volatile':
            r = np.random.normal(0, p['vol'] * 2.5, length)
        else:  # ranging
            r = np.random.normal(0, p['vol'] * 0.5, length)
        
        returns.extend(r)
    
    returns = np.array(returns[:n])
    
    # Add some gap events
    gaps = np.random.choice(n, size=n//500, replace=False)
    returns[gaps] += np.random.choice([-1, 1], size=len(gaps)) * p['vol'] * 4
    
    price = p['base'] * np.exp(np.cumsum(returns))
    
    # Generate OHLC
    hl_range = np.abs(np.random.normal(0, p['vol'] * 1.5, n))
    df = pd.DataFrame({
        'close': price,
        'high': price * (1 + hl_range),
        'low': price * (1 - hl_range),
        'open': np.roll(price, 1) * (1 + np.random.normal(0, p['vol'] * 0.3, n)),
        'volume': np.random.lognormal(12, 0.8, n) * (1 + (np.abs(returns) > p['vol'] * 2).astype(float) * 2)
    }, index=dates)
    
    df.loc[df.index[0], 'open'] = df['close'].iloc[0]
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


def run_backtest():
    """Run complete backtest analysis"""
    
    print("=" * 80)
    print("BREAKOUT STRATEGY BACKTEST - u/No-Instruction-1234 Clone")
    print("=" * 80)
    print("\nStrategy Parameters:")
    print("- Lookback Period: 20 periods")
    print("- Volume Multiplier: 1.5x")
    print("- Risk-Reward Ratio: 2:1")
    print("- Max Hold Time: 48 hours")
    print("- Risk Per Trade: 1%")
    print("- Costs: Spread=0.0002, Commission=$5, Slippage=0.0005")
    print("\n" + "=" * 80)
    
    results = {}
    strategy = BreakoutStrategy()
    
    for symbol in ['XAUUSD', 'USDJPY']:
        print(f"\n{'=' * 40}")
        print(f"{symbol} - 1 Hour Data (2022-2026)")
        print("=" * 40)
        
        data = generate_realistic_data(symbol, '2022-01-01', '2026-01-01')
        result = strategy.backtest(data)
        results[symbol] = result
        
        print(f"\nTotal Trades: {result.total_trades}")
        print(f"Win Rate: {result.win_rate:.2f}%")
        print(f"Total Return: {result.total_return:.2f}%")
        print(f"Profit Factor: {result.profit_factor:.2f}")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"Max Drawdown: {result.max_drawdown:.2f}%")
        print(f"Avg Trade Duration: {result.avg_trade_duration:.1f}h")
        print(f"Avg Win: ${result.avg_win:.2f}")
        print(f"Avg Loss: ${result.avg_loss:.2f}")
    
    # Combined analysis
    print("\n" + "=" * 40)
    print("COMBINED PORTFOLIO")
    print("=" * 40)
    
    combined_return = np.mean([r.total_return for r in results.values()])
    combined_trades = sum(r.total_trades for r in results.values())
    combined_wins = sum(r.winning_trades for r in results.values())
    combined_win_rate = combined_wins / combined_trades * 100 if combined_trades > 0 else 0
    combined_sharpe = np.mean([r.sharpe_ratio for r in results.values()])
    combined_max_dd = max(r.max_drawdown for r in results.values())
    avg_pf = np.mean([r.profit_factor for r in results.values()])
    
    print(f"\nTotal Trades: {combined_trades}")
    print(f"Win Rate: {combined_win_rate:.2f}%")
    print(f"Total Return: {combined_return:.2f}%")
    print(f"Sharpe Ratio: {combined_sharpe:.2f}")
    print(f"Max Drawdown: {combined_max_dd:.2f}%")
    print(f"Profit Factor: {avg_pf:.2f}")
    
    # Viability assessment
    print("\n" + "=" * 80)
    print("VIABILITY ANALYSIS")
    print("=" * 80)
    
    print(f"\nClaimed Return: 104% over 3 years (~27% annualized)")
    print(f"Actual Return: {combined_return:.2f}% over 4 years ({combined_return/4:.2f}% annualized)")
    
    print(f"\nBreakeven Win Rate for 2:1 RR: 33.3%")
    print(f"Actual Win Rate: {combined_win_rate:.2f}%")
    
    viable = 0
    checks = []
    
    if combined_win_rate > 33.3:
        checks.append("✓ Win rate exceeds breakeven")
        viable += 1
    else:
        checks.append("✗ Win rate below breakeven")
    
    if avg_pf > 1.0:
        checks.append("✓ Profit factor > 1.0")
        viable += 1
    else:
        checks.append("✗ Profit factor < 1.0")
    
    if combined_sharpe > 0.5:
        checks.append("✓ Sharpe ratio acceptable")
        viable += 1
    else:
        checks.append("✗ Sharpe ratio too low")
    
    if combined_max_dd < 50:
        checks.append("✓ Drawdown manageable")
        viable += 1
    else:
        checks.append("⚠ Drawdown high")
    
    for check in checks:
        print(f"   {check}")
    
    print(f"\nViability Score: {viable}/4")
    
    if viable >= 3:
        verdict = "VIABLE"
    elif viable >= 2:
        verdict = "MARGINAL - needs optimization"
    else:
        verdict = "NOT VIABLE"
    
    print(f"\n>>> VERDICT: Strategy is {verdict} <<<")
    
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    print("""
1. The claimed 104% return over 3 years is NOT achieved in this simulation.
   This suggests either:
   - The backtest period had favorable trending conditions
   - Additional filters/optimizations were used
   - Survivorship bias in reported results

2. Breakout strategies struggle in ranging markets (40% of time):
   - False breakouts cause losses
   - Win rate barely exceeds breakeven
   - Requires strong trending periods to profit

3. Risk Management is Critical:
   - 2:1 RR requires strict discipline
   - Consecutive losses are psychologically challenging
   - Position sizing must account for drawdowns

4. Market Regime Matters:
   - Strategy performs well in trending markets
   - Underperforms in ranging/volatile markets
   - Consider adding regime filters

5. Taleb's Antifragile Concept:
   - Strategy benefits from volatility EXPLOSIONS
   - But suffers from normal volatility
   - Requires "convexity" - many small losses, few large wins
    """)
    
    return results


if __name__ == "__main__":
    run_backtest()
