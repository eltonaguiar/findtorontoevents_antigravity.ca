"""
Commodity Keltner CCI Mean Reversion Strategy
==============================================
Asset Class: COMMODITIES (CL=F, GC=F, SI=F, NG=F, ZC=F, ZS=F)

Problem: 43.6% WR, middling performance.
Solution: Keltner Channel mean reversion + CCI extreme + regime filter.
          Commodities mean-revert strongly within channels due to
          physical supply/demand anchoring.

Logic:
  LONG:  CCI(20) < -100 AND close touches lower Keltner AND close > SMA(100)
  SHORT: CCI(20) > 100  AND close touches upper Keltner AND close < SMA(100)
  Exit:  CCI crosses zero OR ATR trailing stop

Target: WR 58-65%, PF > 1.4
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class CommodityKeltnerCCIConfig:
    keltner_period: int = 20
    keltner_atr_mult: float = 1.5
    cci_period: int = 20
    cci_oversold: float = -100.0
    cci_overbought: float = 100.0
    sma_filter_period: int = 100
    atr_period: int = 14
    atr_stop_multiplier: float = 2.0

    symbols: List[str] = field(default_factory=lambda: [
        "CL=F", "GC=F", "SI=F", "NG=F", "ZC=F", "ZS=F", "HG=F"
    ])


def compute_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def compute_cci(high, low, close, period=20):
    tp = (high + low + close) / 3
    tp_sma = tp.rolling(window=period).mean()
    tp_mean_dev = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    cci = (tp - tp_sma) / (0.015 * tp_mean_dev)
    return cci.fillna(0)


def generate_signals(df: pd.DataFrame, config: CommodityKeltnerCCIConfig) -> pd.DataFrame:
    df = df.copy()

    # Keltner Channels
    df['keltner_mid'] = df['close'].ewm(span=config.keltner_period, adjust=False).mean()
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)
    df['keltner_upper'] = df['keltner_mid'] + config.keltner_atr_mult * df['atr']
    df['keltner_lower'] = df['keltner_mid'] - config.keltner_atr_mult * df['atr']

    # CCI
    df['cci'] = compute_cci(df['high'], df['low'], df['close'], config.cci_period)

    # Trend filter
    df['sma_filter'] = df['close'].rolling(window=config.sma_filter_period).mean()

    long_cond = (
        (df['cci'] < config.cci_oversold) &
        (df['low'] <= df['keltner_lower']) &
        (df['close'] > df['sma_filter'])
    )
    short_cond = (
        (df['cci'] > config.cci_overbought) &
        (df['high'] >= df['keltner_upper']) &
        (df['close'] < df['sma_filter'])
    )

    df['signal'] = 0
    df.loc[long_cond, 'signal'] = 1
    df.loc[short_cond, 'signal'] = -1

    df['stop_long'] = df['close'] - config.atr_stop_multiplier * df['atr']
    df['stop_short'] = df['close'] + config.atr_stop_multiplier * df['atr']

    return df


STRATEGY_REGISTRY = {
    'commodity_keltner_cci_reversion': {
        'name': 'Commodity Keltner CCI Mean Reversion',
        'asset_class': 'COMMODITY',
        'type': 'Mean Reversion',
        'timeframe': '1d',
        'target_wr': '58-65%',
        'target_pf': '>1.4',
        'config': CommodityKeltnerCCIConfig,
        'generate_signals': generate_signals,
    }
}
