"""
ETF VWAP Mean Reversion Strategy
=================================
Asset Class: ETFs (SPY, QQQ, IWM, XLF, XLE, XLK, etc.)

Problem: 42.1% WR from dashboard — needs improvement.
Solution: VWAP-based mean reversion with volume confirmation.
          VWAP is the institutional benchmark — price reverts to VWAP
          especially in liquid ETFs.

Logic:
  LONG:  Price < VWAP - 1.5σ AND RSI(2) < 10 AND volume > 1.5x avg
  SHORT: Price > VWAP + 1.5σ AND RSI(2) > 90 AND volume > 1.5x avg
  Exit:  Price crosses back through VWAP OR ATR trailing stop

Target: WR 60-68%, PF > 1.5
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class ETFVWAPMeanReversionConfig:
    vwap_std_mult: float = 1.5
    rsi_period: int = 2
    rsi_oversold: float = 10.0
    rsi_overbought: float = 90.0
    atr_period: int = 14
    atr_stop_multiplier: float = 2.0
    volume_mult_threshold: float = 1.5
    volume_sma_period: int = 20

    symbols: List[str] = field(default_factory=lambda: [
        "SPY", "QQQ", "IWM", "XLF", "XLE", "XLK", "XLV", "XLI",
        "XLP", "XLU", "TLT", "GLD", "SLV", "USO", "EEM", "EFA"
    ])


def compute_rsi(prices, period=2):
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


def generate_signals(df: pd.DataFrame, config: ETFVWAPMeanReversionConfig) -> pd.DataFrame:
    df = df.copy()

    # VWAP (cumulative volume-weighted average price)
    if 'volume' in df.columns:
        typical = (df['high'] + df['low'] + df['close']) / 3
        cum_vol = df['volume'].cumsum()
        cum_tp_vol = (typical * df['volume']).cumsum()
        df['vwap'] = cum_tp_vol / cum_vol.replace(0, np.nan)

        # VWAP standard deviation bands
        vwap_var = ((typical - df['vwap']) ** 2 * df['volume']).cumsum() / cum_vol.replace(0, np.nan)
        df['vwap_std'] = np.sqrt(vwap_var)
        df['vwap_upper'] = df['vwap'] + config.vwap_std_mult * df['vwap_std']
        df['vwap_lower'] = df['vwap'] - config.vwap_std_mult * df['vwap_std']

        df['vol_sma'] = df['volume'].rolling(window=config.volume_sma_period).mean()
        vol_confirm = df['volume'] > config.volume_mult_threshold * df['vol_sma']
    else:
        df['vwap'] = df['close'].rolling(window=20).mean()
        df['vwap_upper'] = df['vwap'] * 1.02
        df['vwap_lower'] = df['vwap'] * 0.98
        vol_confirm = True

    df['rsi'] = compute_rsi(df['close'], config.rsi_period)
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)

    long_cond = (
        (df['close'] < df['vwap_lower']) &
        (df['rsi'] < config.rsi_oversold) &
        vol_confirm
    )
    short_cond = (
        (df['close'] > df['vwap_upper']) &
        (df['rsi'] > config.rsi_overbought) &
        vol_confirm
    )

    df['signal'] = 0
    df.loc[long_cond, 'signal'] = 1
    df.loc[short_cond, 'signal'] = -1

    df['stop_long'] = df['close'] - config.atr_stop_multiplier * df['atr']
    df['stop_short'] = df['close'] + config.atr_stop_multiplier * df['atr']

    return df


STRATEGY_REGISTRY = {
    'etf_vwap_mean_reversion': {
        'name': 'ETF VWAP Mean Reversion',
        'asset_class': 'ETF',
        'type': 'Mean Reversion / VWAP',
        'timeframe': '1d',
        'target_wr': '60-68%',
        'target_pf': '>1.5',
        'config': ETFVWAPMeanReversionConfig,
        'generate_signals': generate_signals,
    }
}
