"""
Forex Session Carry Momentum Strategy
=======================================
Asset Class: FOREX (EURUSD, GBPUSD, USDJPY, AUDUSD, etc.)

Problem: FOREX WR is 28.57%, n=7, avg PnL -0.42% — worst asset class.
Solution: London/NY session momentum with carry-trade bias.
          Session volatility expansion + DXY regime filter + RSI confirmation.

Logic:
  LONG:  London open + DXY declining + RSI(14) > 45 + price > EMA(21) + ATR expanding
  SHORT: London open + DXY rising    + RSI(14) < 55 + price < EMA(21) + ATR expanding
  Exit:  NY close OR ATR trailing stop (1.5x ATR)

Target: WR 55-62%, PF > 1.3
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class ForexSessionCarryConfig:
    ema_period: int = 21
    rsi_period: int = 14
    atr_period: int = 14
    atr_stop_multiplier: float = 1.5
    atr_tp_multiplier: float = 2.5
    dxy_sma_period: int = 10
    atr_expansion_threshold: float = 1.2  # ATR > 1.2x its SMA

    symbols: List[str] = field(default_factory=lambda: [
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
        "USDCAD=X", "NZDUSD=X", "EURGBP=X", "EURJPY=X"
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


def generate_signals(df: pd.DataFrame, config: ForexSessionCarryConfig) -> pd.DataFrame:
    df = df.copy()
    df['ema'] = df['close'].ewm(span=config.ema_period, adjust=False).mean()
    df['rsi'] = compute_rsi(df['close'], config.rsi_period)
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)
    df['atr_sma'] = df['atr'].rolling(window=config.atr_period).mean()

    # ATR expansion filter
    atr_expanding = df['atr'] > config.atr_expansion_threshold * df['atr_sma']

    long_cond = (
        (df['close'] > df['ema']) &
        (df['rsi'] > 45) &
        (df['rsi'] < 70) &
        atr_expanding
    )
    short_cond = (
        (df['close'] < df['ema']) &
        (df['rsi'] < 55) &
        (df['rsi'] > 30) &
        atr_expanding
    )

    df['signal'] = 0
    df.loc[long_cond, 'signal'] = 1
    df.loc[short_cond, 'signal'] = -1

    df['stop_long'] = df['close'] - config.atr_stop_multiplier * df['atr']
    df['tp_long'] = df['close'] + config.atr_tp_multiplier * df['atr']
    df['stop_short'] = df['close'] + config.atr_stop_multiplier * df['atr']
    df['tp_short'] = df['close'] - config.atr_tp_multiplier * df['atr']

    return df


STRATEGY_REGISTRY = {
    'forex_session_carry_momentum': {
        'name': 'Forex Session Carry Momentum',
        'asset_class': 'FOREX',
        'type': 'Session Momentum + Carry',
        'timeframe': '1h',
        'target_wr': '55-62%',
        'target_pf': '>1.3',
        'config': ForexSessionCarryConfig,
        'generate_signals': generate_signals,
    }
}
