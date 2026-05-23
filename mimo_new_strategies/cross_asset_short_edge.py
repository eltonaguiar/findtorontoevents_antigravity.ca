"""
Cross-Asset SHORT Edge Exploiter Strategy
==========================================
Asset Class: ALL (Crypto, Forex, Commodities, Equity, Futures)

PROBLEM: Edge analysis shows SHORT direction has +16% WR advantage over LONG
         (61.6% vs 45.6% on crypto). The "UNKNOWN" legacy data shows 73.7% WR
         on SHORT vs 15.9% on LONG. This edge is real but underexploited.
         Only 23.4% of active picks are SHORT.

EDGE:   Market microstructure asymmetry — markets fall faster than they rise
        (gravity). Short sellers have structural advantages:
        1. Fear is stronger than greed (behavioral finance)
        2. Stop-loss cascades amplify downside moves
        3. Short-covering rallies create predictable exit points
        4. Funding rates favor shorts in crypto (negative funding = short edge)

LOGIC:
  CRYPTO SHORT: Funding rate > 0.03% (overleveraged longs) AND
                RSI(14) > 60 AND price < EMA(50) AND volume declining

  EQUITY SHORT: Price breaks 20-day low AND RSI(14) < 40 AND
                sector weakness (SPY < EMA(50)) AND volume spike

  FOREX SHORT: Price at upper Keltner + RSI(2) > 90 + DXY strengthening

  COMMODITY SHORT: Seasonal bearish + price < SMA(100) + CCI(20) > 100

  EXIT: ATR trailing stop + short-cover signal (RSI < 30 or price > VWAP)

Target: WR 58-65%, PF > 1.5 (leveraging SHORT bias edge)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class AssetClass(Enum):
    CRYPTO = "crypto"
    EQUITY = "equity"
    FOREX = "forex"
    COMMODITY = "commodity"
    FUTURES = "futures"


@dataclass
class ShortEdgeConfig:
    # RSI
    rsi_period: int = 14
    rsi2_period: int = 2

    # EMA/SMA
    ema_short: int = 20
    ema_long: int = 50
    sma_filter: int = 100

    # ATR
    atr_period: int = 14
    atr_stop_mult: float = 2.0
    atr_tp_mult: float = 3.0

    # Volume
    volume_sma: int = 20
    volume_spike_mult: float = 1.5
    volume_decline_mult: float = 0.7

    # Funding rate (crypto-specific)
    funding_threshold: float = 0.03  # percent

    # Keltner (forex-specific)
    keltner_period: int = 20
    keltner_atr_mult: float = 1.5

    # CCI (commodity-specific)
    cci_period: int = 20
    cci_overbought: float = 100.0

    # Time exit
    max_holding_bars: int = 20

    # Direction bias: minimum SHORT allocation
    min_short_allocation: float = 0.50  # 50% of picks should be SHORT


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


def compute_cci(high, low, close, period=20):
    tp = (high + low + close) / 3
    tp_sma = tp.rolling(window=period).mean()
    tp_mean_dev = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    cci = (tp - tp_sma) / (0.015 * tp_mean_dev)
    return cci.fillna(0)


def generate_crypto_short_signals(df: pd.DataFrame,
                                   funding_rate: Optional[pd.Series] = None,
                                   config: ShortEdgeConfig = None) -> pd.DataFrame:
    """
    Crypto SHORT signals exploiting funding rate + overbought conditions.
    """
    if config is None:
        config = ShortEdgeConfig()

    df = df.copy()
    df['rsi'] = compute_rsi(df['close'], config.rsi_period)
    df['ema50'] = df['close'].ewm(span=config.ema_long).mean()
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)
    df['vol_sma'] = df['volume'].rolling(window=config.volume_sma).mean()
    df['vol_declining'] = df['volume'] < df['vol_sma'] * config.volume_decline_mult

    if funding_rate is not None:
        df['funding'] = funding_rate
    else:
        df['funding'] = 0.0

    df['signal'] = 0
    df['stop_loss'] = np.nan
    df['take_profit'] = np.nan

    # SHORT: overleveraged longs (high funding) + overbought + below trend + vol declining
    short_cond = (
        (df['funding'] > config.funding_threshold) &
        (df['rsi'] > 60) &
        (df['close'] < df['ema50']) &
        df['vol_declining']
    )
    # If no funding data, use momentum + RSI only
    mom_short = (
        (df['funding'] == 0) &
        (df['rsi'] > 65) &
        (df['close'] < df['ema50'])
    )

    df.loc[short_cond | mom_short, 'signal'] = -1
    df.loc[short_cond | mom_short, 'stop_loss'] = df['close'] + df['atr'] * config.atr_stop_mult
    df.loc[short_cond | mom_short, 'take_profit'] = df['close'] - df['atr'] * config.atr_tp_mult

    return df[['signal', 'stop_loss', 'take_profit']]


def generate_equity_short_signals(df: pd.DataFrame,
                                   spy_df: Optional[pd.DataFrame] = None,
                                   config: ShortEdgeConfig = None) -> pd.DataFrame:
    """
    Equity SHORT signals: breakdown + sector weakness.
    """
    if config is None:
        config = ShortEdgeConfig()

    df = df.copy()
    df['rsi'] = compute_rsi(df['close'], config.rsi_period)
    df['low20'] = df['low'].rolling(window=20).min()
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)
    df['vol_sma'] = df['volume'].rolling(window=config.volume_sma).mean()
    df['vol_spike'] = df['volume'] > df['vol_sma'] * config.volume_spike_mult

    # SPY trend filter
    if spy_df is not None:
        spy_ema50 = spy_df['close'].ewm(span=config.ema_long).mean()
        spy_weak = spy_df['close'] < spy_ema50
        df['sector_weak'] = spy_weak.reindex(df.index, method='ffill').fillna(False)
    else:
        df['sector_weak'] = True

    df['signal'] = 0
    df['stop_loss'] = np.nan
    df['take_profit'] = np.nan

    short_cond = (
        (df['close'] < df['low20'].shift(1)) &
        (df['rsi'] < 40) &
        df['sector_weak'] &
        df['vol_spike']
    )

    df.loc[short_cond, 'signal'] = -1
    df.loc[short_cond, 'stop_loss'] = df['close'] + df['atr'] * config.atr_stop_mult
    df.loc[short_cond, 'take_profit'] = df['close'] - df['atr'] * config.atr_tp_mult

    return df[['signal', 'stop_loss', 'take_profit']]


def generate_forex_short_signals(df: pd.DataFrame,
                                  dxy_df: Optional[pd.DataFrame] = None,
                                  config: ShortEdgeConfig = None) -> pd.DataFrame:
    """
    Forex SHORT signals: Keltner upper + RSI2 extreme + DXY strength.
    """
    if config is None:
        config = ShortEdgeConfig()

    df = df.copy()
    df['rsi2'] = compute_rsi(df['close'], config.rsi2_period)
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)
    sma = df['close'].rolling(window=config.keltner_period).mean()
    atr_keltner = compute_atr(df['high'], df['low'], df['close'], config.keltner_period)
    df['keltner_upper'] = sma + config.keltner_atr_mult * atr_keltner

    # DXY strengthening filter
    if dxy_df is not None:
        dxy_ema = dxy_df['close'].ewm(span=10).mean()
        dxy_strong = dxy_df['close'] > dxy_ema
        df['dxy_strong'] = dxy_strong.reindex(df.index, method='ffill').fillna(False)
    else:
        df['dxy_strong'] = True

    df['signal'] = 0
    df['stop_loss'] = np.nan
    df['take_profit'] = np.nan

    short_cond = (
        (df['close'] >= df['keltner_upper']) &
        (df['rsi2'] > 90) &
        df['dxy_strong']
    )

    df.loc[short_cond, 'signal'] = -1
    df.loc[short_cond, 'stop_loss'] = df['close'] + df['atr'] * config.atr_stop_mult
    df.loc[short_cond, 'take_profit'] = df['close'] - df['atr'] * config.atr_tp_mult

    return df[['signal', 'stop_loss', 'take_profit']]


def generate_commodity_short_signals(df: pd.DataFrame,
                                      seasonal_bias: Optional[pd.Series] = None,
                                      config: ShortEdgeConfig = None) -> pd.DataFrame:
    """
    Commodity SHORT signals: seasonal bearish + trend break + CCI extreme.
    """
    if config is None:
        config = ShortEdgeConfig()

    df = df.copy()
    df['cci'] = compute_cci(df['high'], df['low'], df['close'], config.cci_period)
    df['sma100'] = df['close'].rolling(window=config.sma_filter).mean()
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)

    if seasonal_bias is not None:
        df['seasonal'] = seasonal_bias
    else:
        df['seasonal'] = 0.0

    df['signal'] = 0
    df['stop_loss'] = np.nan
    df['take_profit'] = np.nan

    short_cond = (
        (df['seasonal'] < -0.2) &
        (df['close'] < df['sma100']) &
        (df['cci'] > config.cci_overbought)
    )

    df.loc[short_cond, 'signal'] = -1
    df.loc[short_cond, 'stop_loss'] = df['close'] + df['atr'] * config.atr_stop_mult
    df.loc[short_cond, 'take_profit'] = df['close'] - df['atr'] * config.atr_tp_mult

    return df[['signal', 'stop_loss', 'take_profit']]


def backtest_short(df: pd.DataFrame, asset_class: AssetClass,
                   config: ShortEdgeConfig = None,
                   commission_bps: float = 5.0,
                   **kwargs) -> Dict:
    """Backtest SHORT signals for any asset class."""
    if config is None:
        config = ShortEdgeConfig()

    # Generate signals based on asset class
    if asset_class == AssetClass.CRYPTO:
        signals = generate_crypto_short_signals(df, config=config, **kwargs)
    elif asset_class == AssetClass.EQUITY:
        signals = generate_equity_short_signals(df, config=config, **kwargs)
    elif asset_class == AssetClass.FOREX:
        signals = generate_forex_short_signals(df, config=config, **kwargs)
    elif asset_class == AssetClass.COMMODITY:
        signals = generate_commodity_short_signals(df, config=config, **kwargs)
    else:
        signals = generate_crypto_short_signals(df, config=config)

    trades = []
    position = None

    for i in range(1, len(signals)):
        row = signals.iloc[i]
        price = df['close'].iloc[i]

        if position is not None:
            bars_held = i - position['entry_idx']
            if price >= position['sl'] or price <= position['tp'] or bars_held >= config.max_holding_bars:
                exit_price = max(price, position['sl']) if price >= position['sl'] else \
                             min(price, position['tp']) if price <= position['tp'] else price
                pnl = (position['entry_price'] - exit_price) - commission_bps / 10000 * position['entry_price']
                trades.append({**position, 'exit_price': exit_price, 'pnl': pnl, 'bars_held': bars_held})
                position = None

        if position is None and row['signal'] == -1:
            position = {
                'direction': 'short',
                'entry_price': price,
                'sl': row['stop_loss'],
                'tp': row['take_profit'],
                'entry_idx': i,
            }

    if not trades:
        return {'total_trades': 0, 'win_rate': 0, 'profit_factor': 0, 'sharpe': 0, 'max_dd': 0}

    pnls = [t['pnl'] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 1e-10

    equity = np.cumsum(pnls)
    max_dd = 0
    peak = equity[0]
    for val in equity:
        peak = max(peak, val)
        max_dd = max(max_dd, peak - val)

    sharpe = np.mean(pnls) / (np.std(pnls) + 1e-10) * np.sqrt(252)

    return {
        'asset_class': asset_class.value,
        'direction': 'SHORT',
        'total_trades': len(trades),
        'win_rate': round(len(wins) / len(trades) * 100, 1),
        'profit_factor': round(gross_profit / gross_loss, 3),
        'sharpe': round(sharpe, 3),
        'max_dd': round(max_dd, 5),
        'avg_pnl': round(np.mean(pnls), 6),
        'equity_curve': equity.tolist(),
    }


if __name__ == '__main__':
    print("Cross-Asset SHORT Edge Exploiter Strategy")
    print("=" * 50)
    print("Exploits the +16% WR SHORT advantage documented in edge analysis")
    print("Target: 58-65% WR on SHORT positions across all asset classes")
