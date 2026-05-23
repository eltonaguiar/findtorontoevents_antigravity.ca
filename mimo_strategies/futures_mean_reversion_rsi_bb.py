"""
Futures Mean Reversion RSI + Bollinger Bands Strategy
=====================================================
Asset Class: FUTURES (ES, NQ, CL, GC, SI, ZB, 6E, etc.)

Problem: Current futures WR is 6.3% — catastrophically broken.
Root Cause: Existing strategies use trend-following on choppy futures.
Solution: Mean reversion on oversold/overbought + BB band touch.
          Mean reversion works on futures because they oscillate around fair value.

Logic:
  LONG:  RSI(2) < 10 AND price touches Lower Bollinger Band(20,2) AND close > SMA(200)
  SHORT: RSI(2) > 90 AND price touches Upper Bollinger Band(20,2) AND close < SMA(200)
  Exit:  RSI(2) crosses back through 50, OR ATR-based trailing stop (2x ATR)

Backtest Params:
  - Universe: ES=F, NQ=F, CL=F, GC=F, SI=F, ZB=F, 6E=F, YM=F, RTY=F
  - Period: 5yr daily
  - Walk-forward: 70/15/15 split
  - Monte Carlo: 10,000 paths, 95% CI
  - Transaction costs: $2.50/contract round-trip + 1 tick slippage

Target: WR 58-65%, PF > 1.5, Sharpe > 1.2
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class FuturesMeanReversionConfig:
    """Configuration for Futures Mean Reversion RSI+BB strategy."""
    # RSI parameters
    rsi_period: int = 2
    rsi_oversold: float = 10.0
    rsi_overbought: float = 90.0
    rsi_exit: float = 50.0

    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0

    # Trend filter
    sma_long_period: int = 200

    # Risk management
    atr_period: int = 14
    atr_stop_multiplier: float = 2.0
    atr_tp_multiplier: float = 3.0

    # Position sizing
    risk_per_trade: float = 0.01  # 1% of account per trade
    max_position_pct: float = 0.05  # Max 5% in one position

    # Universe
    symbols: List[str] = field(default_factory=lambda: [
        "ES=F", "NQ=F", "CL=F", "GC=F", "SI=F",
        "ZB=F", "6E=F", "YM=F", "RTY=F"
    ])


def compute_rsi(prices: pd.Series, period: int = 2) -> pd.Series:
    """Compute RSI with Wilder's smoothing."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def compute_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Compute Bollinger Bands."""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return upper, sma, lower


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Compute Average True Range."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def generate_signals(df: pd.DataFrame, config: FuturesMeanReversionConfig) -> pd.DataFrame:
    """
    Generate trading signals for futures mean reversion.

    Args:
        df: OHLCV DataFrame with columns: open, high, low, close, volume
        config: Strategy configuration

    Returns:
        DataFrame with signal columns added
    """
    df = df.copy()

    # Indicators
    df['rsi'] = compute_rsi(df['close'], config.rsi_period)
    df['bb_upper'], df['bb_mid'], df['bb_lower'] = compute_bollinger_bands(
        df['close'], config.bb_period, config.bb_std
    )
    df['sma_200'] = df['close'].rolling(window=config.sma_long_period).mean()
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)

    # Signal conditions
    # LONG: RSI oversold + price at lower BB + above 200 SMA (uptrend dip buy)
    long_cond = (
        (df['rsi'] < config.rsi_oversold) &
        (df['low'] <= df['bb_lower']) &
        (df['close'] > df['sma_200'])
    )

    # SHORT: RSI overbought + price at upper BB + below 200 SMA (downtrend rally fade)
    short_cond = (
        (df['rsi'] > config.rsi_overbought) &
        (df['high'] >= df['bb_upper']) &
        (df['close'] < df['sma_200'])
    )

    df['signal'] = 0
    df.loc[long_cond, 'signal'] = 1
    df.loc[short_cond, 'signal'] = -1

    # Exit signals
    df['exit_long'] = (df['rsi'] > config.rsi_exit) & (df['signal'].shift(1) == 1)
    df['exit_short'] = (df['rsi'] < config.rsi_exit) & (df['signal'].shift(1) == -1)

    # ATR-based stops
    df['stop_long'] = df['close'] - config.atr_stop_multiplier * df['atr']
    df['tp_long'] = df['close'] + config.atr_tp_multiplier * df['atr']
    df['stop_short'] = df['close'] + config.atr_stop_multiplier * df['atr']
    df['tp_short'] = df['close'] - config.atr_tp_multiplier * df['atr']

    return df


def backtest(
    df: pd.DataFrame,
    config: FuturesMeanReversionConfig,
    initial_capital: float = 100000.0,
    commission_per_contract: float = 2.50,
    slippage_ticks: float = 1.0,
    tick_value: float = 12.50  # ES tick value
) -> Dict:
    """
    Run backtest with transaction costs.

    Returns dict with: trades, equity_curve, metrics
    """
    trades = []
    equity = initial_capital
    position = 0
    entry_price = 0.0
    entry_bar = 0
    equity_curve = [initial_capital]

    signals = generate_signals(df, config)

    for i in range(1, len(signals)):
        row = signals.iloc[i]
        prev = signals.iloc[i - 1]

        # Close existing position
        if position != 0:
            exit_signal = False
            exit_price = row['close']

            if position > 0:  # Long position
                if row['exit_long'] or row['low'] <= prev['stop_long']:
                    exit_price = min(row['close'], prev['stop_long'])
                    exit_signal = True
                elif row['close'] >= prev['tp_long']:
                    exit_price = prev['tp_long']
                    exit_signal = True
            elif position < 0:  # Short position
                if row['exit_short'] or row['high'] >= prev['stop_short']:
                    exit_price = max(row['close'], prev['stop_short'])
                    exit_signal = True
                elif row['close'] <= prev['tp_short']:
                    exit_price = prev['tp_short']
                    exit_signal = True

            if exit_signal:
                pnl = position * (exit_price - entry_price)
                costs = commission_per_contract + (slippage_ticks * tick_value)
                net_pnl = pnl - costs
                equity += net_pnl

                trades.append({
                    'entry_bar': entry_bar,
                    'exit_bar': i,
                    'direction': 'LONG' if position > 0 else 'SHORT',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': net_pnl,
                    'pnl_pct': net_pnl / initial_capital * 100,
                    'holding_period': i - entry_bar,
                    'exit_reason': 'stop' if abs(exit_price - entry_price) > abs(prev.get('tp_long', exit_price) - entry_price) * 0.5 else 'target/signal'
                })
                position = 0

        # Open new position
        if position == 0 and row['signal'] != 0:
            position = row['signal']
            entry_price = row['close']
            entry_bar = i

        equity_curve.append(equity)

    # Compute metrics
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    metrics = compute_metrics(trades_df, equity_curve, initial_capital)

    return {
        'trades': trades_df,
        'equity_curve': equity_curve,
        'metrics': metrics
    }


def compute_metrics(trades_df: pd.DataFrame, equity_curve: List[float], initial_capital: float) -> Dict:
    """Compute backtest performance metrics."""
    if trades_df.empty:
        return {
            'total_trades': 0, 'win_rate': 0, 'profit_factor': 0,
            'sharpe_ratio': 0, 'max_drawdown': 0, 'avg_pnl_pct': 0,
            'avg_winner': 0, 'avg_loser': 0, 'expectancy': 0,
            'calmar_ratio': 0, 'avg_holding_period': 0
        }

    wins = trades_df[trades_df['pnl'] > 0]
    losses = trades_df[trades_df['pnl'] <= 0]

    total_trades = len(trades_df)
    win_rate = len(wins) / total_trades if total_trades > 0 else 0

    gross_profit = wins['pnl'].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses['pnl'].sum()) if len(losses) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    # Equity curve metrics
    eq = np.array(equity_curve)
    returns = np.diff(eq) / eq[:-1]
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0

    # Max drawdown
    peak = np.maximum.accumulate(eq)
    drawdown = (peak - eq) / peak
    max_dd = np.max(drawdown) if len(drawdown) > 0 else 0

    avg_pnl_pct = trades_df['pnl_pct'].mean()
    avg_winner = wins['pnl_pct'].mean() if len(wins) > 0 else 0
    avg_loser = losses['pnl_pct'].mean() if len(losses) > 0 else 0
    expectancy = avg_pnl_pct

    calmar = (eq[-1] / initial_capital - 1) / max_dd if max_dd > 0 else 0

    return {
        'total_trades': total_trades,
        'win_rate': round(win_rate * 100, 1),
        'profit_factor': round(profit_factor, 2),
        'sharpe_ratio': round(sharpe, 2),
        'max_drawdown': round(max_dd * 100, 1),
        'avg_pnl_pct': round(avg_pnl_pct, 3),
        'avg_winner': round(avg_winner, 3),
        'avg_loser': round(avg_loser, 3),
        'expectancy': round(expectancy, 3),
        'calmar_ratio': round(calmar, 2),
        'avg_holding_period': round(trades_df['holding_period'].mean(), 1),
        'total_return_pct': round((eq[-1] / initial_capital - 1) * 100, 1),
        'long_trades': len(trades_df[trades_df['direction'] == 'LONG']),
        'short_trades': len(trades_df[trades_df['direction'] == 'SHORT']),
        'long_wr': round(len(wins[wins['direction'] == 'LONG']) / max(len(trades_df[trades_df['direction'] == 'LONG']), 1) * 100, 1),
        'short_wr': round(len(wins[wins['direction'] == 'SHORT']) / max(len(trades_df[trades_df['direction'] == 'SHORT']), 1) * 100, 1),
    }


def monte_carlo_simulation(
    trades_df: pd.DataFrame,
    n_simulations: int = 10000,
    confidence: float = 0.95,
    initial_capital: float = 100000.0
) -> Dict:
    """
    Monte Carlo simulation on trade returns.

    Randomly resamples trades with replacement to build
    distribution of terminal equity and max drawdown.
    """
    if trades_df.empty:
        return {'error': 'No trades to simulate'}

    pnls = trades_df['pnl'].values
    n_trades = len(pnls)

    terminal_equities = []
    max_drawdowns = []

    for _ in range(n_simulations):
        # Resample trades with replacement
        sampled = np.random.choice(pnls, size=n_trades, replace=True)
        equity = initial_capital + np.cumsum(sampled)
        equity = np.insert(equity, 0, initial_capital)

        terminal_equities.append(equity[-1])

        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / peak
        max_drawdowns.append(np.max(dd))

    terminal_equities = np.array(terminal_equities)
    max_drawdowns = np.array(max_drawdowns)

    alpha = 1 - confidence
    return {
        'n_simulations': n_simulations,
        'confidence_level': confidence,
        'terminal_equity': {
            'mean': round(np.mean(terminal_equities), 2),
            'median': round(np.median(terminal_equities), 2),
            'std': round(np.std(terminal_equities), 2),
            f'ci_{int(confidence*100)}_lower': round(np.percentile(terminal_equities, alpha/2 * 100), 2),
            f'ci_{int(confidence*100)}_upper': round(np.percentile(terminal_equities, (1 - alpha/2) * 100), 2),
            'prob_profit': round(np.mean(terminal_equities > initial_capital) * 100, 1),
            'prob_ruin': round(np.mean(terminal_equities < initial_capital * 0.5) * 100, 1),
        },
        'max_drawdown': {
            'mean': round(np.mean(max_drawdowns) * 100, 1),
            'median': round(np.median(max_drawdowns) * 100, 1),
            f'ci_{int(confidence*100)}_worst': round(np.percentile(max_drawdowns, confidence * 100) * 100, 1),
            'prob_dd_gt_20pct': round(np.mean(max_drawdowns > 0.20) * 100, 1),
            'prob_dd_gt_30pct': round(np.mean(max_drawdowns > 0.30) * 100, 1),
        }
    }


# Registry entry for integration
STRATEGY_REGISTRY = {
    'futures_mean_reversion_rsi_bb': {
        'name': 'Futures Mean Reversion RSI+BB',
        'asset_class': 'FUTURES',
        'type': 'Mean Reversion',
        'timeframe': '1d',
        'target_wr': '58-65%',
        'target_pf': '>1.5',
        'config': FuturesMeanReversionConfig,
        'generate_signals': generate_signals,
        'backtest': backtest,
        'monte_carlo': monte_carlo_simulation,
    }
}
