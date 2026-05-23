"""
Bond Seasonal Regime Strategy
==============================
Asset Class: BONDS (ZB=F, ZN=F, TLT, IEF, SHY, LQD)

Problem: Only 2 active picks, 50% WR — needs more coverage and regime awareness.
Solution: Yield curve regime detection + seasonal month-end rebalancing effects.
          Bonds have strong seasonal patterns around month-end, quarter-end,
          and FOMC meetings.

Logic:
  LONG:  Month-end window (last 3 trading days) + RSI(14) < 40 + price > SMA(50)
  SHORT: Month-start + RSI(14) > 60 + price < SMA(50)
  Exit:  5-bar time-based exit OR ATR trailing stop

Target: WR 55-60%, PF > 1.3
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class BondSeasonalRegimeConfig:
    rsi_period: int = 14
    sma_period: int = 50
    atr_period: int = 14
    atr_stop_multiplier: float = 1.5
    max_holding_bars: int = 5
    month_end_lookback: int = 3  # last 3 bars of month

    symbols: List[str] = field(default_factory=lambda: [
        "ZB=F", "ZN=F", "TLT", "IEF", "SHY", "LQD", "AGG", "BND"
    ])


def compute_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def compute_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def generate_signals(df: pd.DataFrame, config: BondSeasonalRegimeConfig) -> pd.DataFrame:
    df = df.copy()
    df['rsi'] = compute_rsi(df['close'], config.rsi_period)
    df['sma'] = df['close'].rolling(window=config.sma_period).mean()
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)

    # Detect month-end (last N bars of each calendar month)
    if isinstance(df.index, pd.DatetimeIndex):
        df['month'] = df.index.month
        df['day_of_month'] = df.index.day
        df['days_in_month'] = df.index.days_in_month
        df['is_month_end'] = (df['days_in_month'] - df['day_of_month']) < config.month_end_lookback
        df['is_month_start'] = df['day_of_month'] <= config.month_end_lookback
    else:
        # Approximate using bar counts — assume 21 trading days/month
        bar_in_cycle = np.arange(len(df)) % 21
        df['is_month_end'] = bar_in_cycle >= (21 - config.month_end_lookback)
        df['is_month_start'] = bar_in_cycle < config.month_end_lookback

    long_cond = (
        df['is_month_end'] &
        (df['rsi'] < 40) &
        (df['close'] > df['sma'])
    )
    short_cond = (
        df['is_month_start'] &
        (df['rsi'] > 60) &
        (df['close'] < df['sma'])
    )

    df['signal'] = 0
    df.loc[long_cond, 'signal'] = 1
    df.loc[short_cond, 'signal'] = -1

    df['stop_long'] = df['close'] - config.atr_stop_multiplier * df['atr']
    df['stop_short'] = df['close'] + config.atr_stop_multiplier * df['atr']

    return df


STRATEGY_REGISTRY = {
    'bond_seasonal_regime': {
        'name': 'Bond Seasonal Regime',
        'asset_class': 'BOND',
        'type': 'Seasonal + Mean Reversion',
        'timeframe': '1d',
        'target_wr': '55-60%',
        'target_pf': '>1.3',
        'config': BondSeasonalRegimeConfig,
        'generate_signals': generate_signals,
    }
}
