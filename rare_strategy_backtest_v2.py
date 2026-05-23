#!/usr/bin/env python3
"""
RARE STRATEGY BACKTESTER v2 — Focus on What Actually Works
==========================================================
V1 showed all naive implementations fail. V2 uses:
1. Connors RSI-2 (proven 62.5% WR on BTC) adapted for 1H
2. Volume Spike Mean Reversion (capitulation → bounce)
3. Trend-Following with Vol Scaling (only trade WITH macro trend)
4. Multi-Timeframe Confluence (only trade when 4H+1H+15min agree)
5. Adaptive Momentum with Regime Filter
6. Mean Reversion Z-Score with Bollinger Squeeze Filter

Key research insights applied:
- Volatility scaling on every strategy
- Strict regime awareness (no counter-trend trades)
- Higher TP:SL ratios (asymmetric payoff)
- Minimum signal strength thresholds
"""

import json
import warnings
import os
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
os.environ['PYTHONIOENCODING'] = 'utf-8'


def fetch_crypto_1h(symbol: str = "BTC-USD", days: int = 729) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=f"{days}d", interval="1h")
    if df is None or len(df) < 500:
        raise ValueError(f"Insufficient data for {symbol}")
    df.columns = [c.lower() for c in df.columns]
    df = df[['open', 'high', 'low', 'close', 'volume']].copy()
    df.dropna(inplace=True)
    print(f"  {symbol}: {len(df)} bars, {df.index[0]} to {df.index[-1]}")
    return df


# ─── HELPER: Technical Indicators ───────────────────────────────────────────

def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Standard RSI."""
    n = len(close)
    result = np.full(n, 50.0)
    deltas = np.diff(close)

    avg_gain = 0.0
    avg_loss = 0.0

    # Initial average
    for j in range(period):
        if j < len(deltas):
            if deltas[j] > 0:
                avg_gain += deltas[j]
            else:
                avg_loss += abs(deltas[j])
    avg_gain /= period
    avg_loss /= period

    if avg_loss > 0:
        result[period] = 100 - (100 / (1 + avg_gain / avg_loss))
    else:
        result[period] = 100

    for j in range(period + 1, n):
        delta = deltas[j - 1] if j - 1 < len(deltas) else 0
        if delta > 0:
            avg_gain = (avg_gain * (period - 1) + delta) / period
            avg_loss = (avg_loss * (period - 1)) / period
        else:
            avg_gain = (avg_gain * (period - 1)) / period
            avg_loss = (avg_loss * (period - 1) + abs(delta)) / period

        if avg_loss > 0:
            result[j] = 100 - (100 / (1 + avg_gain / avg_loss))
        else:
            result[j] = 100

    return result


def ema(data: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    result = np.zeros(len(data))
    k = 2.0 / (period + 1)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = data[i] * k + result[i - 1] * (1 - k)
    return result


def sma(data: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average."""
    result = np.full(len(data), np.nan)
    for i in range(period - 1, len(data)):
        result[i] = np.mean(data[i - period + 1:i + 1])
    return result


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range."""
    n = len(close)
    tr = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))
    tr[0] = high[0] - low[0]
    return sma(tr, period)


def bollinger_bandwidth(close: np.ndarray, period: int = 20) -> np.ndarray:
    """Bollinger Band Width (volatility squeeze indicator)."""
    n = len(close)
    bbw = np.zeros(n)
    for i in range(period, n):
        window = close[i - period:i]
        mid = np.mean(window)
        std = np.std(window)
        if mid > 0:
            bbw[i] = (4 * std) / mid  # Bandwidth = 4*std/mid
    return bbw


def volume_zscore(volume: np.ndarray, window: int = 48) -> np.ndarray:
    """Z-score of volume vs rolling window."""
    n = len(volume)
    result = np.zeros(n)
    for i in range(window, n):
        w = volume[i - window:i]
        mean_v = np.mean(w)
        std_v = np.std(w)
        if std_v > 0:
            result[i] = (volume[i] - mean_v) / std_v
    return result


# ─── STRATEGY 1: CONNORS RSI-2 (1H Crypto Adapted) ─────────────────────────

def connors_rsi2_1h(df: pd.DataFrame) -> pd.Series:
    """
    Connors RSI-2 Mean Reversion for 1H crypto.
    Proven: 62.5% WR, Sharpe 2.35 on BTC daily.
    Adapted for 1H with:
    - RSI(2) for extreme oversold/overbought
    - 200h EMA trend filter (only long above, short below)
    - Volume confirmation
    - Vol scaling
    """
    close = df['close'].values
    vol = df['volume'].values
    n = len(close)

    rsi2 = rsi(close, 2)
    rsi14 = rsi(close, 14)
    ema200 = ema(close, 200)
    ema50 = ema(close, 50)
    vol_z = volume_zscore(vol, 48)

    # Realized vol for scaling
    returns = np.diff(np.log(close))
    returns = np.insert(returns, 0, 0)

    signals = np.zeros(n)

    for i in range(201, n):
        # Vol scaling
        rv = np.std(returns[i - 72:i]) * np.sqrt(8760)
        vol_scale = min(0.15 / max(rv, 0.05), 2.5)

        # Trend filter
        trend_up = close[i] > ema200[i] and ema50[i] > ema200[i]
        trend_down = close[i] < ema200[i] and ema50[i] < ema200[i]

        # RSI-2 extreme levels
        if trend_up and rsi2[i] < 10:
            # Extreme oversold in uptrend = strong buy
            strength = (10 - rsi2[i]) / 10  # 0-1
            if rsi14[i] < 45:  # Not overbought on 14-period either
                signals[i] = strength * vol_scale
        elif trend_up and rsi2[i] < 20:
            # Moderately oversold in uptrend
            strength = (20 - rsi2[i]) / 20
            if vol_z[i] > 1.0:  # Volume spike confirmation
                signals[i] = 0.5 * strength * vol_scale
        elif trend_down and rsi2[i] > 90:
            # Extreme overbought in downtrend = short
            strength = (rsi2[i] - 90) / 10
            if rsi14[i] > 55:
                signals[i] = -strength * vol_scale
        elif trend_down and rsi2[i] > 80:
            if vol_z[i] > 1.0:
                strength = (rsi2[i] - 80) / 20
                signals[i] = -0.5 * strength * vol_scale

    return pd.Series(signals, index=df.index)


# ─── STRATEGY 2: VOLUME SPIKE CAPITULATION REVERSAL ─────────────────────────

def volume_spike_reversal(df: pd.DataFrame) -> pd.Series:
    """
    Volume Spike Mean Reversion.
    Looks for capitulation volume (3+ std above mean) with price drop,
    then enters long for the bounce.

    Based on: "whale_accumulation_detector" concept + VIX spike reversal logic
    (proven 72% WR on equities).
    """
    close = df['close'].values
    vol = df['volume'].values
    high = df['high'].values
    low = df['low'].values
    n = len(close)

    vol_z = volume_zscore(vol, 72)
    rsi14 = rsi(close, 14)
    atr14 = atr(high, low, close, 14)

    returns = np.diff(np.log(close))
    returns = np.insert(returns, 0, 0)

    signals = np.zeros(n)

    for i in range(73, n):
        # Price change over last 4 bars
        price_change_4h = (close[i] / close[i - 4] - 1) * 100

        # Vol scaling
        rv = np.std(returns[i - 72:i]) * np.sqrt(8760)
        vol_scale = min(0.15 / max(rv, 0.05), 2.0)

        # Capitulation buy: huge volume + big price drop + oversold RSI
        if vol_z[i] > 2.5 and price_change_4h < -2.0 and rsi14[i] < 35:
            strength = min(vol_z[i] / 5.0, 1.0) * min(abs(price_change_4h) / 5.0, 1.0)
            signals[i] = strength * vol_scale

        # Euphoria short: huge volume + big price rise + overbought RSI
        elif vol_z[i] > 3.0 and price_change_4h > 3.0 and rsi14[i] > 70:
            strength = min(vol_z[i] / 6.0, 1.0) * min(price_change_4h / 6.0, 1.0)
            signals[i] = -0.5 * strength * vol_scale  # Smaller short size

    return pd.Series(signals, index=df.index)


# ─── STRATEGY 3: TREND-FOLLOWING WITH VOL SCALING ───────────────────────────

def trend_following_vol_scaled(df: pd.DataFrame) -> pd.Series:
    """
    Trend-Following with Volatility Scaling.
    Based on: Barroso & Santa-Clara (2015) + crypto adaptation.

    Only trades in direction of strong trend.
    Sizes inversely to volatility (free Sharpe improvement).
    Uses EMA crossover + ADX-like strength filter.
    """
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    n = len(close)

    ema9 = ema(close, 9)
    ema21 = ema(close, 21)
    ema50 = ema(close, 50)
    ema200 = ema(close, 200)
    atr14 = atr(high, low, close, 14)
    rsi14 = rsi(close, 14)

    returns = np.diff(np.log(close))
    returns = np.insert(returns, 0, 0)

    signals = np.zeros(n)

    for i in range(201, n):
        # Multi-EMA alignment check
        bullish_stack = ema9[i] > ema21[i] > ema50[i] > ema200[i]
        bearish_stack = ema9[i] < ema21[i] < ema50[i] < ema200[i]

        # Trend strength (distance between fast and slow EMA relative to ATR)
        if atr14[i] > 0:
            trend_strength = abs(ema9[i] - ema200[i]) / atr14[i]
        else:
            trend_strength = 0

        # Vol scaling
        rv = np.std(returns[i - 72:i]) * np.sqrt(8760)
        vol_scale = min(0.15 / max(rv, 0.05), 2.5)

        # Only enter when trend is STRONG and aligned
        if bullish_stack and trend_strength > 3.0:
            # Pullback entry: wait for price near ema21
            pullback = (close[i] - ema21[i]) / max(atr14[i], 1)
            if -1.5 < pullback < 0.5 and rsi14[i] < 55:
                # Price pulled back to 21 EMA in strong uptrend
                signals[i] = min(trend_strength / 5.0, 1.0) * vol_scale

        elif bearish_stack and trend_strength > 3.0:
            pullback = (ema21[i] - close[i]) / max(atr14[i], 1)
            if -1.5 < pullback < 0.5 and rsi14[i] > 45:
                signals[i] = -min(trend_strength / 5.0, 1.0) * vol_scale

    return pd.Series(signals, index=df.index)


# ─── STRATEGY 4: BOLLINGER SQUEEZE BREAKOUT ─────────────────────────────────

def bollinger_squeeze_breakout(df: pd.DataFrame) -> pd.Series:
    """
    Bollinger Squeeze (Keltner inside Bollinger) breakout.
    Volatility contraction precedes expansion (proven edge).

    Based on: John Carter's TTM Squeeze + academic vol clustering research.
    Adapted with trend filter and vol scaling.
    """
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    vol = df['volume'].values
    n = len(close)

    bb_period = 20
    kc_period = 20
    kc_mult = 1.5

    ema200 = ema(close, 200)
    atr20 = atr(high, low, close, kc_period)
    vol_z = volume_zscore(vol, 48)
    rsi14 = rsi(close, 14)

    returns = np.diff(np.log(close))
    returns = np.insert(returns, 0, 0)

    signals = np.zeros(n)

    squeeze_bars = 0  # Count how long we've been in squeeze

    for i in range(max(bb_period, kc_period) + 1, n):
        # Bollinger Bands
        bb_mid = np.mean(close[i - bb_period:i])
        bb_std = np.std(close[i - bb_period:i])
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std

        # Keltner Channel
        kc_mid = ema(close[:i + 1], kc_period)[-1]
        kc_upper = kc_mid + kc_mult * atr20[i]
        kc_lower = kc_mid - kc_mult * atr20[i]

        # Squeeze detection: BB inside KC
        in_squeeze = bb_upper < kc_upper and bb_lower > kc_lower

        if in_squeeze:
            squeeze_bars += 1
        else:
            if squeeze_bars >= 6:  # At least 6 bars of squeeze
                # Squeeze RELEASED — breakout!
                rv = np.std(returns[i - 72:i]) * np.sqrt(8760)
                vol_scale = min(0.15 / max(rv, 0.05), 2.0)

                # Direction: momentum of squeeze release
                mom = close[i] - bb_mid
                trend_bias = 1 if close[i] > ema200[i] else -1

                if mom > 0 and (trend_bias > 0 or vol_z[i] > 1.5):
                    strength = min(squeeze_bars / 20.0, 1.0)
                    signals[i] = strength * vol_scale
                elif mom < 0 and (trend_bias < 0 or vol_z[i] > 1.5):
                    strength = min(squeeze_bars / 20.0, 1.0)
                    signals[i] = -strength * vol_scale

            squeeze_bars = 0

    return pd.Series(signals, index=df.index)


# ─── STRATEGY 5: ADAPTIVE MOMENTUM WITH REGIME ──────────────────────────────

def adaptive_momentum(df: pd.DataFrame) -> pd.Series:
    """
    Adaptive Momentum with Regime Detection.
    Uses multiple lookback periods and picks the one currently working best.

    Based on: Levine & Pedersen (2016) "Which Trend Is Your Friend?"
    + crypto regime adaptation.
    """
    close = df['close'].values
    n = len(close)

    lookbacks = [24, 48, 72, 168, 336]  # 1d, 2d, 3d, 7d, 14d
    ema200 = ema(close, 200)

    returns = np.diff(np.log(close))
    returns = np.insert(returns, 0, 0)

    signals = np.zeros(n)

    for i in range(337, n):
        # Calculate momentum for each lookback
        moms = {}
        for lb in lookbacks:
            moms[lb] = close[i] / close[i - lb] - 1

        # Find which lookback has been most accurate recently (last 50 bars)
        best_lb = lookbacks[0]
        best_score = -999
        for lb in lookbacks:
            # Score = correlation between past momentum and future returns
            past_moms = []
            future_rets = []
            for j in range(50):
                idx = i - 50 + j
                if idx - lb >= 0 and idx + 1 < n:
                    past_moms.append(close[idx] / close[idx - lb] - 1)
                    future_rets.append(close[min(idx + 24, n - 1)] / close[idx] - 1)
            if len(past_moms) > 10:
                corr = np.corrcoef(past_moms, future_rets)[0, 1]
                if not np.isnan(corr) and corr > best_score:
                    best_score = corr
                    best_lb = lb

        # Use best lookback
        mom = moms[best_lb]

        # Vol scaling
        rv = np.std(returns[i - 72:i]) * np.sqrt(8760)
        vol_scale = min(0.15 / max(rv, 0.05), 2.0)

        # Only trade if momentum is significant
        if best_score > 0.1:  # Positive correlation = momentum works
            if mom > 0.02 and close[i] > ema200[i]:
                signals[i] = min(abs(mom) * 5, 1.0) * vol_scale * min(best_score * 3, 1.0)
            elif mom < -0.02 and close[i] < ema200[i]:
                signals[i] = -min(abs(mom) * 5, 1.0) * vol_scale * min(best_score * 3, 1.0)
        elif best_score < -0.1:  # Negative correlation = mean-reversion works
            if mom < -0.03 and close[i] > ema200[i]:
                signals[i] = min(abs(mom) * 3, 0.8) * vol_scale * min(abs(best_score) * 3, 1.0)
            elif mom > 0.03 and close[i] < ema200[i]:
                signals[i] = -min(abs(mom) * 3, 0.8) * vol_scale * min(abs(best_score) * 3, 1.0)

    return pd.Series(signals, index=df.index)


# ─── STRATEGY 6: MULTI-TIMEFRAME RSI CONFLUENCE ─────────────────────────────

def mtf_rsi_confluence(df: pd.DataFrame) -> pd.Series:
    """
    Multi-Timeframe RSI Confluence.
    Only enters when RSI is aligned across multiple periods.

    Based on: Elder Triple Screen adapted for crypto.
    Uses RSI(2), RSI(7), RSI(14) all needing to agree.
    """
    close = df['close'].values
    n = len(close)

    rsi2 = rsi(close, 2)
    rsi7 = rsi(close, 7)
    rsi14 = rsi(close, 14)
    ema200 = ema(close, 200)

    returns = np.diff(np.log(close))
    returns = np.insert(returns, 0, 0)

    signals = np.zeros(n)

    for i in range(201, n):
        rv = np.std(returns[i - 72:i]) * np.sqrt(8760)
        vol_scale = min(0.15 / max(rv, 0.05), 2.0)

        trend_up = close[i] > ema200[i]
        trend_down = close[i] < ema200[i]

        # Triple oversold confluence in uptrend
        if trend_up and rsi2[i] < 15 and rsi7[i] < 35 and rsi14[i] < 45:
            strength = ((15 - rsi2[i]) / 15 + (35 - rsi7[i]) / 35 + (45 - rsi14[i]) / 45) / 3
            signals[i] = strength * vol_scale

        # Triple overbought confluence in downtrend
        elif trend_down and rsi2[i] > 85 and rsi7[i] > 65 and rsi14[i] > 55:
            strength = ((rsi2[i] - 85) / 15 + (rsi7[i] - 65) / 35 + (rsi14[i] - 55) / 45) / 3
            signals[i] = -strength * vol_scale

    return pd.Series(signals, index=df.index)


# ─── BACKTESTER (Triple Barrier) ────────────────────────────────────────────

def backtest(df: pd.DataFrame, signals: pd.Series,
             tp_pct: float = 2.0, sl_pct: float = 1.5,
             max_hold: int = 48, commission_pct: float = 0.1,
             name: str = "Unknown",
             # Parameter sweep
             tp_range: list = None, sl_range: list = None) -> Dict:
    """Backtest with triple barrier. Optionally sweep TP/SL."""

    if tp_range and sl_range:
        # Parameter sweep
        best_result = None
        best_sharpe = -999
        for tp in tp_range:
            for sl in sl_range:
                r = _run_backtest(df, signals, tp, sl, max_hold, commission_pct, name)
                if r['sharpe'] > best_sharpe and r['total_trades'] >= 20:
                    best_sharpe = r['sharpe']
                    best_result = r
                    best_result['best_tp'] = tp
                    best_result['best_sl'] = sl
        return best_result if best_result else _run_backtest(df, signals, tp_pct, sl_pct, max_hold, commission_pct, name)
    else:
        return _run_backtest(df, signals, tp_pct, sl_pct, max_hold, commission_pct, name)


def _run_backtest(df, signals, tp_pct, sl_pct, max_hold, commission_pct, name):
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    n = len(close)

    trades = []
    i = 0

    while i < n - 1:
        sig = signals.iloc[i] if i < len(signals) else 0
        if abs(sig) < 0.1:
            i += 1
            continue

        direction = 1 if sig > 0 else -1
        size = min(abs(sig), 2.0)
        entry_price = close[i]
        entry_idx = i

        tp_price = entry_price * (1 + direction * tp_pct / 100)
        sl_price = entry_price * (1 - direction * sl_pct / 100)

        exit_reason = "max_hold"
        exit_price = close[min(i + max_hold, n - 1)]
        exit_idx = min(i + max_hold, n - 1)

        for j in range(i + 1, min(i + max_hold + 1, n)):
            if direction == 1:
                if high[j] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    exit_idx = j
                    break
                elif low[j] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    exit_idx = j
                    break
            else:
                if low[j] <= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    exit_idx = j
                    break
                elif high[j] >= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    exit_idx = j
                    break

        pnl_pct = direction * (exit_price / entry_price - 1) * 100 * size
        pnl_pct -= commission_pct * 2 * size

        trades.append({
            'entry_time': str(df.index[entry_idx]),
            'exit_time': str(df.index[exit_idx]),
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': round(entry_price, 2),
            'exit_price': round(exit_price, 2),
            'pnl_pct': round(pnl_pct, 4),
            'exit_reason': exit_reason,
            'bars_held': exit_idx - entry_idx,
        })

        i = exit_idx + 1

    if not trades:
        return {'strategy': name, 'total_trades': 0, 'win_rate': 0,
                'avg_pnl': 0, 'total_pnl': 0, 'sharpe': 0,
                'max_drawdown': 0, 'profit_factor': 0, 'trades': []}

    pnls = [t['pnl_pct'] for t in trades]
    wins = sum(1 for p in pnls if p > 0)

    equity = np.cumsum(pnls)
    running_max = np.maximum.accumulate(equity)
    max_dd = abs(min(equity - running_max))

    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p <= 0))

    return {
        'strategy': name,
        'total_trades': len(trades),
        'win_rate': round(wins / len(trades) * 100, 1),
        'avg_pnl': round(np.mean(pnls), 4),
        'total_pnl': round(sum(pnls), 2),
        'sharpe': round((np.mean(pnls) / max(np.std(pnls), 1e-10)) * np.sqrt(365), 2),
        'max_drawdown': round(max_dd, 2),
        'profit_factor': round(gross_profit / max(gross_loss, 1e-10), 2),
        'avg_win': round(np.mean([p for p in pnls if p > 0]), 4) if wins > 0 else 0,
        'avg_loss': round(abs(np.mean([p for p in pnls if p <= 0])), 4) if wins < len(pnls) else 0,
        'avg_bars': round(np.mean([t['bars_held'] for t in trades]), 1),
        'tp_count': sum(1 for t in trades if t['exit_reason'] == 'TP'),
        'sl_count': sum(1 for t in trades if t['exit_reason'] == 'SL'),
        'trades': trades,
    }


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 100)
    print("RARE STRATEGY BACKTESTER v2 -- Focus on What Actually Works")
    print("=" * 100)

    print("\n[*] Fetching BTCUSDT 1H data...")
    df_btc = fetch_crypto_1h("BTC-USD", days=400)

    # Split into train (first 70%) and test (last 30%)
    split_idx = int(len(df_btc) * 0.7)
    df_train = df_btc.iloc[:split_idx]
    df_test = df_btc.iloc[split_idx:]
    print(f"  Train: {len(df_train)} bars ({df_train.index[0]} to {df_train.index[-1]})")
    print(f"  Test:  {len(df_test)} bars ({df_test.index[0]} to {df_test.index[-1]})")

    strategies = [
        ("Connors RSI-2 (1H Crypto)", connors_rsi2_1h),
        ("Volume Spike Reversal", volume_spike_reversal),
        ("Trend Following + Vol Scale", trend_following_vol_scaled),
        ("Bollinger Squeeze Breakout", bollinger_squeeze_breakout),
        ("Adaptive Momentum", adaptive_momentum),
        ("MTF RSI Confluence", mtf_rsi_confluence),
    ]

    # TP/SL sweep ranges
    tp_range = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    sl_range = [1.0, 1.5, 2.0, 2.5, 3.0]
    max_holds = [24, 36, 48, 72]

    all_results = []

    for name, strat_fn in strategies:
        print(f"\n[*] {name}...")

        # Generate signals on FULL dataset
        signals_full = strat_fn(df_btc)

        # Test on FULL dataset first
        signals_count = sum(abs(signals_full) > 0.1)
        print(f"  Signals generated: {signals_count}")

        # Sweep parameters on train set
        signals_train = strat_fn(df_train)
        best_train = None
        best_train_sharpe = -999

        for tp in tp_range:
            for sl in sl_range:
                for mh in max_holds:
                    r = _run_backtest(df_train, signals_train, tp, sl, mh, 0.1, name)
                    if r['total_trades'] >= 15 and r['sharpe'] > best_train_sharpe:
                        best_train_sharpe = r['sharpe']
                        best_train = {'tp': tp, 'sl': sl, 'mh': mh, 'result': r}

        if best_train and best_train_sharpe > 0:
            tp_opt = best_train['tp']
            sl_opt = best_train['sl']
            mh_opt = best_train['mh']
            print(f"  Best train params: TP={tp_opt}%, SL={sl_opt}%, MaxHold={mh_opt}h")
            print(f"  Train: {best_train['result']['total_trades']}t, "
                  f"WR={best_train['result']['win_rate']}%, "
                  f"Sharpe={best_train['result']['sharpe']}, "
                  f"PnL={best_train['result']['total_pnl']:+.2f}%")

            # Out-of-sample test
            signals_test = strat_fn(df_test)
            test_result = _run_backtest(df_test, signals_test, tp_opt, sl_opt, mh_opt, 0.1, name + " [OOS]")
            print(f"  OOS:   {test_result['total_trades']}t, "
                  f"WR={test_result['win_rate']}%, "
                  f"Sharpe={test_result['sharpe']}, "
                  f"PnL={test_result['total_pnl']:+.2f}%")

            # Full dataset with best params
            full_result = _run_backtest(df_btc, signals_full, tp_opt, sl_opt, mh_opt, 0.1, name)
            full_result['train_sharpe'] = best_train['result']['sharpe']
            full_result['oos_sharpe'] = test_result['sharpe']
            full_result['best_tp'] = tp_opt
            full_result['best_sl'] = sl_opt
            full_result['best_mh'] = mh_opt
            all_results.append(full_result)
        else:
            # Default params
            full_result = _run_backtest(df_btc, signals_full, 2.5, 1.5, 48, 0.1, name)
            full_result['train_sharpe'] = 0
            full_result['oos_sharpe'] = 0
            all_results.append(full_result)
            print(f"  No profitable params found in train. Default: {full_result['total_trades']}t, Sharpe={full_result['sharpe']}")

    # ─── ENSEMBLE: Average all signal generators ───
    print("\n[*] Building ensemble...")
    ranked = sorted(all_results, key=lambda x: x.get('oos_sharpe', 0), reverse=True)
    all_sigs = [fn(df_btc) for _, fn in strategies]
    ensemble_signals = pd.Series(0.0, index=df_btc.index)
    for s in all_sigs:
        ensemble_signals += s / len(all_sigs)
    ensemble_signals[abs(ensemble_signals) < 0.15] = 0

    best_tp = ranked[0].get('best_tp', 2.5)
    best_sl = ranked[0].get('best_sl', 1.5)
    best_mh = ranked[0].get('best_mh', 48)
    ens_result = _run_backtest(df_btc, ensemble_signals, best_tp, best_sl, best_mh, 0.1, "ENSEMBLE (All Avg)")
    all_results.append(ens_result)
    ranked = sorted(all_results, key=lambda x: x.get('sharpe', 0), reverse=True)

    # ─── RESULTS ───
    print("\n" + "=" * 120)
    print("FINAL RESULTS (sorted by Sharpe)")
    print("=" * 120)
    header = (f"{'Strategy':<40} {'Trades':>6} {'WR%':>6} {'AvgPnL':>8} {'TotalPnL':>10} "
              f"{'Sharpe':>7} {'OOS-Sh':>7} {'MaxDD':>7} {'PF':>6} {'TP/SL/MH':>12}")
    print(header)
    print("-" * 120)

    for r in sorted(all_results, key=lambda x: x.get('sharpe', 0), reverse=True):
        params = f"{r.get('best_tp','?')}/{r.get('best_sl','?')}/{r.get('best_mh','?')}"
        print(f"{r['strategy']:<40} {r['total_trades']:>6} {r['win_rate']:>5.1f}% "
              f"{r.get('avg_pnl', 0):>+7.3f}% {r['total_pnl']:>+9.2f}% "
              f"{r['sharpe']:>6.2f} {r.get('oos_sharpe', 0):>6.2f} "
              f"{r.get('max_drawdown', 0):>6.2f}% {r.get('profit_factor', 0):>5.2f} "
              f"{params:>12}")

    # Save
    output = Path("rare_strategy_results_v2.json")
    save_data = [{k: v for k, v in r.items() if k != 'trades'} for r in all_results]
    output.write_text(json.dumps(save_data, indent=2))
    print(f"\nResults saved to {output}")

    # Save best strategy full trades
    best = max(all_results, key=lambda x: x.get('sharpe', 0))
    if best['sharpe'] > 0:
        best_path = Path("rare_strategy_best_v2.json")
        best_path.write_text(json.dumps(best, indent=2))
        print(f"Best strategy ({best['strategy']}, Sharpe {best['sharpe']}) saved to {best_path}")
    else:
        print("\nWARNING: No strategy achieved positive Sharpe.")

    return all_results


if __name__ == "__main__":
    main()
