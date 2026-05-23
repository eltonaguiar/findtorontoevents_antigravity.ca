"""
Futures Trend-Following Dual EMA Strategy
==========================================
Asset Class: FUTURES (ES, NQ, CL, GC, SI, etc.)

Problem: Existing futures trend strategies have 6.3% WR —
         likely using too-short EMAs that whipsaw on noisy futures.
Solution: Dual EMA (21/55) on 4h timeframe with ADX trend strength filter
          and volume confirmation. Longer EMAs reduce whipsaws.

Logic:
  LONG:  EMA(21) > EMA(55) AND ADX > 25 AND close > EMA(21) AND volume > SMA(volume, 20)
  SHORT: EMA(21) < EMA(55) AND ADX > 25 AND close < EMA(21) AND volume > SMA(volume, 20)
  Exit:  EMA crossover reversal OR ATR trailing stop (2.5x ATR)

Target: WR 55-62%, PF > 1.4, Sharpe > 1.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class FuturesTrendDualEMAConfig:
    """Configuration for Futures Dual EMA Trend strategy."""
    ema_fast: int = 21
    ema_slow: int = 55
    adx_period: int = 14
    adx_threshold: float = 25.0
    atr_period: int = 14
    atr_stop_multiplier: float = 2.5
    atr_tp_multiplier: float = 4.0
    volume_sma_period: int = 20

    symbols: List[str] = field(default_factory=lambda: [
        "ES=F", "NQ=F", "CL=F", "GC=F", "SI=F", "YM=F", "RTY=F"
    ])


def compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Compute ADX, +DI, -DI."""
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1/period, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1/period, min_periods=period).mean()

    return adx.fillna(0), plus_di.fillna(0), minus_di.fillna(0)


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Compute ATR."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def generate_signals(df: pd.DataFrame, config: FuturesTrendDualEMAConfig) -> pd.DataFrame:
    """Generate trading signals for futures dual EMA trend following."""
    df = df.copy()

    df['ema_fast'] = df['close'].ewm(span=config.ema_fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=config.ema_slow, adjust=False).mean()
    df['adx'], df['plus_di'], df['minus_di'] = compute_adx(
        df['high'], df['low'], df['close'], config.adx_period
    )
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)

    if 'volume' in df.columns:
        df['vol_sma'] = df['volume'].rolling(window=config.volume_sma_period).mean()
        vol_confirm = df['volume'] > df['vol_sma']
    else:
        vol_confirm = True  # Skip volume filter if no volume data

    # LONG: Fast EMA > Slow EMA + ADX confirms trend + price above fast EMA
    long_cond = (
        (df['ema_fast'] > df['ema_slow']) &
        (df['adx'] > config.adx_threshold) &
        (df['close'] > df['ema_fast']) &
        (df['plus_di'] > df['minus_di']) &
        vol_confirm
    )

    # SHORT: Fast EMA < Slow EMA + ADX confirms trend + price below fast EMA
    short_cond = (
        (df['ema_fast'] < df['ema_slow']) &
        (df['adx'] > config.adx_threshold) &
        (df['close'] < df['ema_fast']) &
        (df['minus_di'] > df['plus_di']) &
        vol_confirm
    )

    df['signal'] = 0
    df.loc[long_cond, 'signal'] = 1
    df.loc[short_cond, 'signal'] = -1

    # Exit on crossover
    df['exit_long'] = (df['ema_fast'] < df['ema_slow']) & (df['signal'].shift(1) == 1)
    df['exit_short'] = (df['ema_fast'] > df['ema_slow']) & (df['signal'].shift(1) == -1)

    # ATR stops/targets
    df['stop_long'] = df['close'] - config.atr_stop_multiplier * df['atr']
    df['tp_long'] = df['close'] + config.atr_tp_multiplier * df['atr']
    df['stop_short'] = df['close'] + config.atr_stop_multiplier * df['atr']
    df['tp_short'] = df['close'] - config.atr_tp_multiplier * df['atr']

    return df


STRATEGY_REGISTRY = {
    'futures_trend_dual_ema': {
        'name': 'Futures Trend Dual EMA (21/55)',
        'asset_class': 'FUTURES',
        'type': 'Trend Following',
        'timeframe': '4h',
        'target_wr': '55-62%',
        'target_pf': '>1.4',
        'config': FuturesTrendDualEMAConfig,
        'generate_signals': generate_signals,
    }
}
