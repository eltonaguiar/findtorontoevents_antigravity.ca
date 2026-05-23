"""
Equity Volume Momentum Breakout Strategy
==========================================
Asset Class: EQUITY (SPY, QQQ, individual stocks)

Problem: Equity WR is 70.8% but only 5 active picks — needs scale.
Solution: Volume-confirmed momentum breakout that catches trending stocks
          with institutional accumulation.

Logic:
  LONG:  Price breaks 20-day high AND RVOL > 2.0 AND RSI(14) > 50 AND close > EMA(50)
  SHORT: Price breaks 20-day low  AND RVOL > 2.0 AND RSI(14) < 50 AND close < EMA(50)
  Exit:  Trailing stop at 2x ATR(14) OR time-based exit at 20 bars

Key insight from edge analysis:
  - "stocks_mom_breakout" has 65% WR target in the 600-variant library
  - Volume confirmation is critical (RVOL > 1.5 from existing strategy)
  - Equity mean reversion (Bollinger MR) works at 3.80% avg PnL on 5 trades

Target: WR 62-70%, PF > 1.6, picks/day 5-15
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class EquityVolumeMomentumConfig:
    breakout_lookback: int = 20
    rsi_period: int = 14
    rsi_min_long: float = 50.0
    rsi_max_short: float = 50.0
    ema_period: int = 50
    atr_period: int = 14
    atr_stop_multiplier: float = 2.0
    rvol_threshold: float = 2.0
    rvol_sma_period: int = 20
    max_holding_bars: int = 20

    symbols: List[str] = field(default_factory=lambda: [
        "SPY", "QQQ", "AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "META",
        "TSLA", "AMD", "JPM", "V", "JNJ", "XOM", "WMT", "UNH"
    ])


def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)


def compute_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def generate_signals(df: pd.DataFrame, config: EquityVolumeMomentumConfig) -> pd.DataFrame:
    df = df.copy()

    # Indicators
    df['high_20d'] = df['high'].rolling(window=config.breakout_lookback).max()
    df['low_20d'] = df['low'].rolling(window=config.breakout_lookback).min()
    df['rsi'] = compute_rsi(df['close'], config.rsi_period)
    df['ema_50'] = df['close'].ewm(span=config.ema_period, adjust=False).mean()
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)

    # Relative Volume
    if 'volume' in df.columns:
        df['vol_sma'] = df['volume'].rolling(window=config.rvol_sma_period).mean()
        df['rvol'] = df['volume'] / df['vol_sma'].replace(0, np.nan)
    else:
        df['rvol'] = 1.0

    # LONG breakout
    long_cond = (
        (df['close'] > df['high_20d'].shift(1)) &
        (df['rsi'] > config.rsi_min_long) &
        (df['close'] > df['ema_50']) &
        (df['rvol'] > config.rvol_threshold)
    )

    # SHORT breakdown
    short_cond = (
        (df['close'] < df['low_20d'].shift(1)) &
        (df['rsi'] < config.rsi_max_short) &
        (df['close'] < df['ema_50']) &
        (df['rvol'] > config.rvol_threshold)
    )

    df['signal'] = 0
    df.loc[long_cond, 'signal'] = 1
    df.loc[short_cond, 'signal'] = -1

    # Trailing stops
    df['stop_long'] = df['close'] - config.atr_stop_multiplier * df['atr']
    df['stop_short'] = df['close'] + config.atr_stop_multiplier * df['atr']

    return df


STRATEGY_REGISTRY = {
    'equity_volume_momentum_breakout': {
        'name': 'Equity Volume Momentum Breakout',
        'asset_class': 'EQUITY',
        'type': 'Momentum / Breakout',
        'timeframe': '1d',
        'target_wr': '62-70%',
        'target_pf': '>1.6',
        'config': EquityVolumeMomentumConfig,
        'generate_signals': generate_signals,
    }
}
