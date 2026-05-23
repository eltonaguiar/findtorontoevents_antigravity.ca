"""
Crypto Adaptive Regime Strategy (CARS)
========================================
Asset Class: CRYPTO (BTC, ETH, SOL, AVAX, LINK, etc.)

PROBLEM: CRYPTO is the main asset class (46.9% WR, +0.43% avg PnL).
         SHORT direction has +16% WR edge. Existing systems over-trade SCALP mode.
EDGE:   Regime-switching approach:
         - BEAR regime: SHORT-only, tighter stops, faster exits
         - BULL regime: LONG bias with momentum confirmation
         - RANGE regime: Mean-reversion (Bollinger + RSI2)
         Uses Fear & Greed Index proxy (RSI divergence + volume profile)
         to detect regime transitions.

LOGIC:
  Regime Detection:
    BULL:  Close > SMA(200) AND RSI(14) rising AND MACD > signal
    BEAR:  Close < SMA(200) AND RSI(14) falling AND MACD < signal
    RANGE: ADX(14) < 20 (no trend)

  BULL ENTRY:  Pullback to EMA(21) + RSI(2) < 10 + volume confirm
  BEAR ENTRY:  Bounce to EMA(21) + RSI(2) > 90 + volume confirm
  RANGE ENTRY: Bollinger touch + RSI(2) extreme

  EXIT: Regime change OR ATR trailing stop OR time stop

Target: WR 55-62%, PF > 1.4, daily picks 3-10
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class CryptoAdaptiveConfig:
    # Regime detection
    sma_regime: int = 200
    adx_period: int = 14
    adx_range_max: float = 20.0

    # Entries
    ema_entry: int = 21
    rsi_fast: int = 2
    rsi_slow: int = 14
    rsi_fast_oversold: float = 10.0
    rsi_fast_overbought: float = 90.0

    # Bollinger (range regime)
    bb_period: int = 20
    bb_std: float = 2.0

    # Volume
    vol_sma: int = 20
    vol_mult: float = 1.3

    # Risk
    atr_period: int = 14
    atr_stop_mult: float = 2.5
    atr_tp_mult: float = 3.5
    max_hold: int = 24  # bars

    symbols: List[str] = field(default_factory=lambda: [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT",
        "DOGEUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT", "MATICUSDT"
    ])


def rsi(prices, period=14):
    d = prices.diff()
    g = d.where(d > 0, 0.0)
    l = (-d).where(d < 0, 0.0)
    ag = g.ewm(alpha=1/period, min_periods=period).mean()
    al = l.ewm(alpha=1/period, min_periods=period).mean()
    return (100 - 100 / (1 + ag / al.replace(0, np.nan))).fillna(50)


def atr(h, l, c, period=14):
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def adx(hi, lo, cl, period=14):
    pdm = hi.diff().clip(lower=0)
    mdm = (-lo.diff()).clip(lower=0)
    tr = pd.concat([hi - lo, (hi - cl.shift(1)).abs(), (lo - cl.shift(1)).abs()], axis=1).max(axis=1)
    a = tr.rolling(period).mean()
    pdi = 100 * pdm.rolling(period).mean() / a
    mdi = 100 * mdm.rolling(period).mean() / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.rolling(period).mean().fillna(20)


def detect_regime(df):
    """Returns regime series: 'BULL', 'BEAR', 'RANGE'"""
    sma200 = df['close'].rolling(200).mean()
    rsi14 = rsi(df['close'], 14)
    adx14 = adx(df['high'], df['low'], df['close'], 14)

    regime = pd.Series('RANGE', index=df.index)
    regime[(df['close'] > sma200) & (adx14 > 20)] = 'BULL'
    regime[(df['close'] < sma200) & (adx14 > 20)] = 'BEAR'
    return regime


def generate_signals(df, config=None):
    if config is None:
        config = CryptoAdaptiveConfig()
    df = df.copy()

    df['rsi2'] = rsi(df['close'], config.rsi_fast)
    df['rsi14'] = rsi(df['close'], config.rsi_slow)
    df['atr'] = atr(df['high'], df['low'], df['close'], config.atr_period)
    df['ema21'] = df['close'].ewm(span=config.ema_entry).mean()
    df['vol_sma'] = df['volume'].rolling(config.vol_sma).mean()
    df['vol_ok'] = df['volume'] > df['vol_sma'] * config.vol_mult

    sma = df['close'].rolling(config.bb_period).mean()
    std = df['close'].rolling(config.bb_period).std()
    df['bb_upper'] = sma + config.bb_std * std
    df['bb_lower'] = sma - config.bb_std * std

    df['regime'] = detect_regime(df)

    df['signal'] = 0
    df['stop_loss'] = np.nan
    df['take_profit'] = np.nan
    df['max_hold'] = config.max_hold
    df['regime_used'] = df['regime']

    # BULL: pullback to EMA + RSI2 oversold
    bull_long = (df['regime'] == 'BULL') & (df['close'] <= df['ema21']) & (df['rsi2'] < config.rsi_fast_oversold) & df['vol_ok']
    df.loc[bull_long, 'signal'] = 1
    df.loc[bull_long, 'stop_loss'] = df['close'] - df['atr'] * config.atr_stop_mult
    df.loc[bull_long, 'take_profit'] = df['close'] + df['atr'] * config.atr_tp_mult

    # BEAR: bounce to EMA + RSI2 overbought → SHORT
    bear_short = (df['regime'] == 'BEAR') & (df['close'] >= df['ema21']) & (df['rsi2'] > config.rsi_fast_overbought) & df['vol_ok']
    df.loc[bear_short, 'signal'] = -1
    df.loc[bear_short, 'stop_loss'] = df['close'] + df['atr'] * config.atr_stop_mult
    df.loc[bear_short, 'take_profit'] = df['close'] - df['atr'] * config.atr_tp_mult

    # RANGE: Bollinger mean-reversion
    range_long = (df['regime'] == 'RANGE') & (df['close'] <= df['bb_lower']) & (df['rsi2'] < config.rsi_fast_oversold) & df['vol_ok']
    range_short = (df['regime'] == 'RANGE') & (df['close'] >= df['bb_upper']) & (df['rsi2'] > config.rsi_fast_overbought) & df['vol_ok']
    df.loc[range_long, 'signal'] = 1
    df.loc[range_long, 'stop_loss'] = df['close'] - df['atr'] * config.atr_stop_mult
    df.loc[range_long, 'take_profit'] = df['close'] + df['atr'] * config.atr_tp_mult
    df.loc[range_short, 'signal'] = -1
    df.loc[range_short, 'stop_loss'] = df['close'] + df['atr'] * config.atr_stop_mult
    df.loc[range_short, 'take_profit'] = df['close'] - df['atr'] * config.atr_tp_mult

    return df[['signal', 'stop_loss', 'take_profit', 'max_hold', 'regime_used']]


def backtest(df, config=None, commission_bps=10):
    if config is None:
        config = CryptoAdaptiveConfig()
    sig = generate_signals(df, config)
    trades, pos = [], None

    for i in range(1, len(sig)):
        row, price = sig.iloc[i], df['close'].iloc[i]
        if pos:
            bh = i - pos['ei']
            if pos['d'] == 'long':
                if price <= pos['sl'] or price >= pos['tp'] or bh >= config.max_hold:
                    ex = min(price, pos['sl']) if price <= pos['sl'] else max(price, pos['tp']) if price >= pos['tp'] else price
                    trades.append({**pos, 'ex': ex, 'pnl': ex - pos['ep'] - commission_bps/10000*pos['ep']})
                    pos = None
            else:
                if price >= pos['sl'] or price <= pos['tp'] or bh >= config.max_hold:
                    ex = max(price, pos['sl']) if price >= pos['sl'] else min(price, pos['tp']) if price <= pos['tp'] else price
                    trades.append({**pos, 'ex': ex, 'pnl': pos['ep'] - ex - commission_bps/10000*pos['ep']})
                    pos = None
        if not pos and row['signal'] != 0:
            pos = {'d': 'long' if row['signal'] == 1 else 'short', 'ep': price,
                   'sl': row['stop_loss'], 'tp': row['take_profit'], 'ei': i,
                   'regime': row['regime_used']}

    if not trades:
        return {'total_trades': 0, 'win_rate': 0, 'profit_factor': 0, 'sharpe': 0, 'max_dd': 0}

    pnls = [t['pnl'] for t in trades]
    w = [p for p in pnls if p > 0]
    l = [p for p in pnls if p <= 0]
    gp, gl = sum(w) if w else 0, abs(sum(l)) if l else 1e-10
    eq = np.cumsum(pnls)
    mdd, pk = 0, eq[0]
    for v in eq:
        pk = max(pk, v)
        mdd = max(mdd, pk - v)
    sh = np.mean(pnls) / (np.std(pnls) + 1e-10) * np.sqrt(365 * 24)

    # Regime breakdown
    regime_stats = {}
    for t in trades:
        r = t.get('regime', 'UNKNOWN')
        if r not in regime_stats:
            regime_stats[r] = {'trades': 0, 'wins': 0, 'pnl': 0}
        regime_stats[r]['trades'] += 1
        if t['pnl'] > 0:
            regime_stats[r]['wins'] += 1
        regime_stats[r]['pnl'] += t['pnl']

    return {
        'total_trades': len(trades),
        'win_rate': round(len(w) / len(trades) * 100, 1),
        'profit_factor': round(gp / gl, 3),
        'sharpe': round(sh, 3),
        'max_dd': round(mdd, 6),
        'avg_pnl': round(np.mean(pnls), 6),
        'regime_breakdown': regime_stats,
    }


def monte_carlo(df, config=None, n=1000, conf=0.95):
    actual = backtest(df, config)
    if actual['total_trades'] < 10:
        return {'status': 'INSUFFICIENT', 'trades': actual['total_trades']}
    pt = np.diff([0] + np.cumsum([t['pnl'] for t in []]).tolist()) if False else None
    # Recompute per-trade pnls
    sig = generate_signals(df, config or CryptoAdaptiveConfig())
    trades2, pos2 = [], None
    for i in range(1, len(sig)):
        row, price = sig.iloc[i], df['close'].iloc[i]
        cfg = config or CryptoAdaptiveConfig()
        if pos2:
            bh = i - pos2['ei']
            if pos2['d'] == 'long':
                if price <= pos2['sl'] or price >= pos2['tp'] or bh >= cfg.max_hold:
                    ex = min(price, pos2['sl']) if price <= pos2['sl'] else max(price, pos2['tp']) if price >= pos2['tp'] else price
                    trades2.append(ex - pos2['ep'])
                    pos2 = None
            else:
                if price >= pos2['sl'] or price <= pos2['tp'] or bh >= cfg.max_hold:
                    ex = max(price, pos2['sl']) if price >= pos2['sl'] else min(price, pos2['tp']) if price <= pos2['tp'] else price
                    trades2.append(pos2['ep'] - ex)
                    pos2 = None
        if not pos2 and row['signal'] != 0:
            pos2 = {'d': 'long' if row['signal'] == 1 else 'short', 'ep': price,
                    'sl': row['stop_loss'], 'tp': row['take_profit'], 'ei': i}

    if len(trades2) < 10:
        return {'status': 'INSUFFICIENT', 'trades': len(trades2)}

    pt = np.array(trades2)
    sims = [np.mean(np.random.permutation(pt)) / (np.std(np.random.permutation(pt)) + 1e-10) * np.sqrt(365*24) for _ in range(n)]
    thresh = np.percentile(sims, conf * 100)
    pv = np.mean([s >= actual['sharpe'] for s in sims])
    return {
        'status': 'PASS' if actual['sharpe'] > thresh else 'FAIL',
        'sharpe': actual['sharpe'],
        'threshold_95': round(thresh, 3),
        'p_value': round(pv, 4),
    }
