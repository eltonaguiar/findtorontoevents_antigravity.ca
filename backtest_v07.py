"""
SSK_Claude v0.07 Backtester — "Next Level" Architecture
========================================================
Tests research-backed improvements against v0.06 baseline.

v0.07 Changes (each independently toggleable):
  1. Daily HTF Trend Gate (only trade in direction of Daily EMA21>EMA50)
  2. Volume >= 1.5x SMA(20) filter
  3. ATR Percentile filter (only trade when 20th-95th percentile)
  4. Connors RSI replacing standard RSI-14
  5. MACD Histogram acceleration (hist > 0 AND rising, not just positive)
  6. Adaptive SuperTrend (factor varies by ATR percentile)
  7. Partial TP at 1R + breakeven stop on remainder
  8. Kaufman Efficiency Ratio regime detection
"""

import pandas as pd
import numpy as np
import json
import os
import sys
import time
from math import erfc, sqrt

sys.path.insert(0, os.path.dirname(__file__))
from backtest_v05_vs_v06 import (
    download_binance_klines, calc_ema, calc_sma, calc_atr,
    calc_adx, calc_wavetrend, calc_stochrsi, calc_macd,
    get_v05_tier, get_tier_params, get_special_overrides
)


# ══════════════════════════════════════════════════════════════════════════════
# NEW INDICATOR CALCULATIONS FOR v0.07
# ══════════════════════════════════════════════════════════════════════════════

def calc_connors_rsi(close, rsi_period=3, streak_period=2, pctrank_period=100):
    """Connors RSI = (RSI(close,3) + RSI(streak,2) + PercentRank(change,100)) / 3"""
    from backtest_v05_vs_v06 import calc_rsi

    # Component 1: RSI of price
    rsi_price = calc_rsi(close, rsi_period)

    # Component 2: RSI of streak
    changes = close.diff()
    streak = pd.Series(0.0, index=close.index)
    for i in range(1, len(close)):
        if changes.iloc[i] > 0:
            streak.iloc[i] = max(streak.iloc[i-1], 0) + 1
        elif changes.iloc[i] < 0:
            streak.iloc[i] = min(streak.iloc[i-1], 0) - 1
        else:
            streak.iloc[i] = 0
    rsi_streak = calc_rsi(streak, streak_period)

    # Component 3: Percent rank of price change
    pct_change = close.diff()
    pct_rank = pct_change.rolling(pctrank_period).apply(
        lambda x: (x.iloc[:-1] < x.iloc[-1]).sum() / (len(x) - 1) * 100 if len(x) > 1 else 50,
        raw=False
    )

    crsi = (rsi_price + rsi_streak + pct_rank) / 3.0
    return crsi


def calc_kaufman_er(close, period=10):
    """Kaufman Efficiency Ratio = |change over N| / sum(|bar-to-bar changes| over N)"""
    direction = (close - close.shift(period)).abs()
    volatility = close.diff().abs().rolling(period).sum()
    er = direction / volatility.replace(0, np.nan)
    return er.fillna(0)


def calc_atr_percentile(high, low, close, atr_period=14, lookback=100):
    """ATR percentile rank over lookback period."""
    atr = calc_atr(high, low, close, atr_period)
    pctile = atr.rolling(lookback).apply(
        lambda x: (x.iloc[:-1] < x.iloc[-1]).sum() / (len(x) - 1) * 100 if len(x) > 1 else 50,
        raw=False
    )
    return atr, pctile


def calc_adaptive_supertrend(high, low, close, atr_val, atr_pctile):
    """SuperTrend with adaptive factor based on ATR percentile.
    Low vol (pctile<25): factor=4.0 (wider to avoid noise)
    Normal vol (25-75): factor=2.5
    High vol (pctile>75): factor=1.5 (tighter, moves are real)
    """
    n = len(close)
    hl2 = (high + low) / 2

    # Compute adaptive factor per bar
    factor = pd.Series(2.5, index=close.index)
    factor = factor.where(~(atr_pctile < 25), 4.0)
    factor = factor.where(~(atr_pctile > 75), 1.5)
    factor = factor.where(~((atr_pctile >= 25) & (atr_pctile <= 75)), 2.5)

    upper = hl2 + factor * atr_val
    lower = hl2 - factor * atr_val

    direction = pd.Series(1, index=close.index)

    for i in range(1, n):
        if close.iloc[i] > upper.iloc[i-1]:
            direction.iloc[i] = -1
        elif close.iloc[i] < lower.iloc[i-1]:
            direction.iloc[i] = 1
        else:
            direction.iloc[i] = direction.iloc[i-1]
            if direction.iloc[i] == -1 and lower.iloc[i] < lower.iloc[i-1]:
                lower.iloc[i] = lower.iloc[i-1]
            if direction.iloc[i] == 1 and upper.iloc[i] > upper.iloc[i-1]:
                upper.iloc[i] = upper.iloc[i-1]

    return direction


def resample_to_daily(df):
    """Resample 1H OHLCV to Daily and compute trend EMAs."""
    daily = df.resample('D').agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    }).dropna()
    daily['ema21'] = calc_ema(daily['close'], 21)
    daily['ema50'] = calc_ema(daily['close'], 50)
    daily['trend_bull'] = daily['ema21'] > daily['ema50']
    return daily


# ══════════════════════════════════════════════════════════════════════════════
# BACKTESTER
# ══════════════════════════════════════════════════════════════════════════════

def run_v07(df, base, config):
    """
    Run the v0.07 backtester.
    config dict controls which features are enabled:
      htf_filter: bool — Daily trend gate
      vol_filter: bool — Volume >= 1.5x SMA(20)
      atr_filter: bool — ATR percentile 20-95
      connors_rsi: bool — Use Connors RSI instead of standard RSI
      macd_accel: bool — MACD histogram acceleration
      adaptive_st: bool — Adaptive SuperTrend factor
      partial_tp: bool — Partial TP at 1R + breakeven
      kaufman_er: bool — Kaufman ER regime detection
    """
    from backtest_v05_vs_v06 import calc_rsi, calc_supertrend

    # Get tier and params (v0.06 with APE→EXTR)
    tier_map = {
        'TRX': 'LOW',
        'BTC': 'MED', 'BNB': 'MED', 'ALGO': 'MED', 'LTC': 'MED',
        'ETH': 'MHIGH', 'DOT': 'MHIGH', 'LINK': 'MHIGH', 'BCH': 'MHIGH', 'TON': 'MHIGH', 'HBAR': 'MHIGH',
        'DOGE': 'EXTR', 'SHIB': 'EXTR', 'FET': 'EXTR', 'SUI': 'EXTR', 'SEI': 'EXTR',
        'TIA': 'EXTR', 'DYDX': 'EXTR', 'STRK': 'EXTR', 'ZK': 'EXTR', 'APE': 'EXTR',
    }
    tier = tier_map.get(base, 'HIGH')
    p = get_tier_params(tier, 'v05')
    p.setdefault('rsi_len', 14)
    p.setdefault('macd_f', 12)
    p.setdefault('macd_s', 26)
    p.setdefault('macd_sig', 9)
    p = get_special_overrides(base, p)

    min_sig = 4 if tier == 'EXTR' else 3  # v0.06 adaptive minSig

    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']
    hlc3 = (high + low + close) / 3
    n = len(df)

    # ── Indicators ──
    # RSI / Connors RSI
    if config.get('connors_rsi', False):
        crsi = calc_connors_rsi(close, 3, 2, 100)
    else:
        crsi = None
    rsi = calc_rsi(close, p['rsi_len'])

    # MACD
    macd_l, sig_l, macd_h = calc_macd(close, p['macd_f'], p['macd_s'], p['macd_sig'])

    # SuperTrend
    atr_val, atr_pctile = calc_atr_percentile(high, low, close, 14, 100)
    if config.get('adaptive_st', False):
        st_dir = calc_adaptive_supertrend(high, low, close, atr_val, atr_pctile)
    else:
        _, st_dir = calc_supertrend(high, low, close, p['st_fact'], p['st_per'])

    # EMA Stack
    ema_f = calc_ema(close, 9)
    ema_m = calc_ema(close, 21)
    ema_s = calc_ema(close, 50)

    # WaveTrend
    wt1, wt2 = calc_wavetrend(hlc3, 10, 21)

    # StochRSI
    srsi_k, srsi_d = calc_stochrsi(close, 14, 3, 3)

    # ADX
    di_plus, di_minus, adx = calc_adx(high, low, close, 14)

    # Kaufman ER
    ker = calc_kaufman_er(close, 10)

    # Volume SMA
    vol_sma = calc_sma(volume, 20)

    # Daily HTF trend
    daily_trend = None
    if config.get('htf_filter', False):
        daily = resample_to_daily(df)
        # Map daily trend back to hourly bars
        daily_trend = daily['trend_bull'].reindex(df.index, method='ffill')

    # ── TP/SL Setup ──
    tp_base = 2.0
    sl_base = 1.0
    tp_mult = tp_base * p['vol_adj']
    sl_mult = sl_base * p['vol_adj']

    # ── Trade Loop ──
    trades = []
    in_trade = False
    pending = False
    entry_price = 0.0
    entry_bar = 0
    tp_level = 0.0
    sl_level = 0.0
    original_sl = 0.0
    hit_1r = False  # For partial TP tracking
    partial_locked = 0.0  # PnL locked from partial
    max_hold = 15
    use_partial = config.get('partial_tp', False)

    start_bar = max(105, p.get('rsi_len', 14) + 5)  # Need enough bars for lookback

    for i in range(start_bar, n):
        if np.isnan(adx.iloc[i]) or np.isnan(atr_val.iloc[i]):
            continue

        # ── Gate Filters ──

        # HTF Daily Trend Gate
        if config.get('htf_filter', False) and daily_trend is not None:
            if pd.isna(daily_trend.iloc[i]):
                continue
            htf_bullish = bool(daily_trend.iloc[i])
        else:
            htf_bullish = True  # No filter = allow all

        # Volume Filter
        if config.get('vol_filter', False):
            if np.isnan(vol_sma.iloc[i]) or vol_sma.iloc[i] == 0:
                vol_ok = True
            else:
                vol_ok = volume.iloc[i] >= 1.5 * vol_sma.iloc[i]
        else:
            vol_ok = True

        # ATR Percentile Filter (20-95)
        if config.get('atr_filter', False):
            if np.isnan(atr_pctile.iloc[i]):
                atr_ok = True
            else:
                atr_ok = 20 <= atr_pctile.iloc[i] <= 95
        else:
            atr_ok = True

        # Kaufman ER regime (only trade when trending: ER > 0.3)
        if config.get('kaufman_er', False):
            if np.isnan(ker.iloc[i]):
                ker_ok = True
            else:
                ker_ok = ker.iloc[i] > 0.3
        else:
            ker_ok = True

        # ── Regime Classification ──
        adx_v = adx.iloc[i]
        regime = 'TREND' if adx_v >= p['adx_trend'] else ('MIXED' if adx_v >= p['adx_range'] else 'RANGE')
        is_trend = regime == 'TREND'
        is_range = regime == 'RANGE'

        # ── Signal Conditions ──

        # RSI / Connors RSI
        if config.get('connors_rsi', False) and crsi is not None:
            rsi_buy_raw = not np.isnan(crsi.iloc[i]) and crsi.iloc[i] < 15
            rsi_sell_raw = not np.isnan(crsi.iloc[i]) and crsi.iloc[i] > 85
        else:
            rsi_buy_raw = rsi.iloc[i] < p['rsi_os']
            rsi_sell_raw = rsi.iloc[i] > p['rsi_ob']

        # MACD with optional histogram acceleration
        if config.get('macd_accel', False):
            macd_buy_raw = macd_h.iloc[i] > 0 and macd_h.iloc[i] > macd_h.iloc[i-1]
            macd_sell_raw = macd_h.iloc[i] < 0 and macd_h.iloc[i] < macd_h.iloc[i-1]
        else:
            macd_buy_raw = macd_l.iloc[i] > sig_l.iloc[i] and macd_h.iloc[i] > 0
            macd_sell_raw = macd_l.iloc[i] < sig_l.iloc[i] and macd_h.iloc[i] < 0

        # SuperTrend (adaptive or standard)
        st_buy_raw = st_dir.iloc[i] < 0
        st_sell_raw = st_dir.iloc[i] > 0

        # EMA Stack
        ema_bull_raw = ema_f.iloc[i] > ema_m.iloc[i] and ema_m.iloc[i] > ema_s.iloc[i]
        ema_bear_raw = ema_f.iloc[i] < ema_m.iloc[i] and ema_m.iloc[i] < ema_s.iloc[i]

        # WaveTrend
        if i > 0:
            wt_buy_raw = (wt1.iloc[i] > wt2.iloc[i] and wt1.iloc[i-1] <= wt2.iloc[i-1] and wt1.iloc[i] < -60)
            wt_sell_raw = (wt1.iloc[i] < wt2.iloc[i] and wt1.iloc[i-1] >= wt2.iloc[i-1] and wt1.iloc[i] > 60)
        else:
            wt_buy_raw = False
            wt_sell_raw = False

        # StochRSI
        if i > 0 and not np.isnan(srsi_k.iloc[i]) and not np.isnan(srsi_d.iloc[i]):
            sr_buy = srsi_k.iloc[i] > srsi_d.iloc[i] and srsi_k.iloc[i-1] <= srsi_d.iloc[i-1] and srsi_k.iloc[i] < 20
            sr_sell = srsi_k.iloc[i] < srsi_d.iloc[i] and srsi_k.iloc[i-1] >= srsi_d.iloc[i-1] and srsi_k.iloc[i] > 80
        else:
            sr_buy = False
            sr_sell = False

        # ADX Direction
        adx_bull = di_plus.iloc[i] > di_minus.iloc[i]
        adx_bear = di_minus.iloc[i] > di_plus.iloc[i]

        # ── Regime Gating ──
        rsi_buy = False if is_trend else rsi_buy_raw
        rsi_sell = False if is_trend else rsi_sell_raw
        st_buy = False if is_range else st_buy_raw
        st_sell = False if is_range else st_sell_raw
        ema_bull = False if is_range else ema_bull_raw
        ema_bear = False if is_range else ema_bear_raw
        wt_buy = False if is_trend else wt_buy_raw
        wt_sell = False if is_trend else wt_sell_raw

        # ── Weighted Consensus ──
        b_score = 0
        b_score += (2 if is_range else 1) if rsi_buy else 0
        b_score += (2 if is_trend else 1) if macd_buy_raw else 0
        b_score += (2 if is_trend else 1) if st_buy else 0
        b_score += (2 if is_trend else 1) if ema_bull else 0
        b_score += (2 if is_range else 1) if wt_buy else 0
        b_score += 1 if sr_buy else 0
        b_score += 1 if adx_bull else 0

        s_score = 0
        s_score += (2 if is_range else 1) if rsi_sell else 0
        s_score += (2 if is_trend else 1) if macd_sell_raw else 0
        s_score += (2 if is_trend else 1) if st_sell else 0
        s_score += (2 if is_trend else 1) if ema_bear else 0
        s_score += (2 if is_range else 1) if wt_sell else 0
        s_score += 1 if sr_sell else 0
        s_score += 1 if adx_bear else 0

        # Apply ALL gate filters
        is_buy = (b_score >= min_sig and b_score > s_score
                  and htf_bullish and vol_ok and atr_ok and ker_ok)

        # ── Trade Management ──
        if pending and not in_trade:
            entry_price = df['open'].iloc[i]
            entry_bar = i
            atr_now = atr_val.iloc[i] if not np.isnan(atr_val.iloc[i]) else entry_price * 0.02
            tp_level = entry_price + atr_now * tp_mult
            sl_level = entry_price - atr_now * sl_mult
            original_sl = sl_level
            hit_1r = False
            partial_locked = 0.0
            in_trade = True
            pending = False

        if in_trade:
            tp_hit = high.iloc[i] >= tp_level
            sl_hit = low.iloc[i] <= sl_level
            bars_held = i - entry_bar

            # Check for 1R profit (for partial TP)
            one_r_level = entry_price + (entry_price - original_sl)  # 1R = risk distance
            if use_partial and not hit_1r and high.iloc[i] >= one_r_level:
                hit_1r = True
                # Lock in 50% at 1R
                partial_locked = (one_r_level - entry_price) / entry_price * 100 * 0.5
                # Move SL to breakeven on remaining 50%
                sl_level = entry_price

            if tp_hit and sl_hit:
                if use_partial and hit_1r:
                    pnl = partial_locked + 0  # Remaining 50% exits at breakeven (worst case)
                else:
                    pnl = -(abs(entry_price - sl_level) / entry_price * 100)
                result = 'win' if pnl > 0.1 else 'loss'
                trades.append({'pnl': pnl, 'result': result})
                in_trade = False
            elif tp_hit:
                if use_partial and hit_1r:
                    remaining_pnl = (tp_level - entry_price) / entry_price * 100 * 0.5
                    pnl = partial_locked + remaining_pnl
                else:
                    pnl = (tp_level - entry_price) / entry_price * 100
                trades.append({'pnl': pnl, 'result': 'win'})
                in_trade = False
            elif sl_hit:
                if use_partial and hit_1r:
                    # SL was moved to breakeven, remaining exits at 0
                    pnl = partial_locked
                    result = 'win' if pnl > 0.1 else ('loss' if pnl < -0.1 else 'flat')
                else:
                    pnl = -(abs(entry_price - sl_level) / entry_price * 100)
                    result = 'loss'
                trades.append({'pnl': pnl, 'result': result})
                in_trade = False
            elif bars_held >= max_hold:
                if use_partial and hit_1r:
                    remaining_pnl = (close.iloc[i] - entry_price) / entry_price * 100 * 0.5
                    pnl = partial_locked + remaining_pnl
                else:
                    pnl = (close.iloc[i] - entry_price) / entry_price * 100
                result = 'win' if pnl > 0.1 else ('loss' if pnl < -0.1 else 'flat')
                trades.append({'pnl': pnl, 'result': result})
                in_trade = False

        if not in_trade and not pending and is_buy:
            pending = True

    # ── Metrics ──
    if not trades:
        return {'trades': 0, 'net_pnl': 0, 'pf': 0, 'wr': 0, 'sharpe': 0, 'max_dd': 0, 'avg_trade': 0}

    wins = [t for t in trades if t['result'] == 'win']
    losses = [t for t in trades if t['result'] == 'loss']
    total = len(wins) + len(losses)
    wr = len(wins) / total * 100 if total > 0 else 0
    sum_win = sum(t['pnl'] for t in wins)
    sum_loss = sum(abs(t['pnl']) for t in losses)
    pf = sum_win / sum_loss if sum_loss > 0 else (99.9 if sum_win > 0 else 0)
    net_pnl = sum(t['pnl'] for t in trades)
    avg_trade = net_pnl / total if total > 0 else 0

    equity = [0]
    for t in trades:
        equity.append(equity[-1] + t['pnl'])
    equity = np.array(equity)
    peak = np.maximum.accumulate(equity)
    max_dd = (equity - peak).min()

    pnl_arr = np.array([t['pnl'] for t in trades])
    sharpe = np.mean(pnl_arr) / np.std(pnl_arr) * np.sqrt(min(total, 365)) if np.std(pnl_arr) > 0 else 0

    return {
        'trades': total, 'net_pnl': round(net_pnl, 2),
        'pf': round(pf, 3), 'wr': round(wr, 2),
        'sharpe': round(sharpe, 3), 'max_dd': round(max_dd, 2),
        'avg_trade': round(avg_trade, 4)
    }


# ══════════════════════════════════════════════════════════════════════════════
# TEST CONFIGURATIONS
# ══════════════════════════════════════════════════════════════════════════════

TEST_PAIRS = [
    ('TRXUSDT', 'TRX'), ('BTCUSDT', 'BTC'), ('ALGOUSDT', 'ALGO'),
    ('ETHUSDT', 'ETH'), ('DOTUSDT', 'DOT'),
    ('SOLUSDT', 'SOL'), ('XRPUSDT', 'XRP'),
    ('INJUSDT', 'INJ'), ('ARBUSDT', 'ARB'), ('APEUSDT', 'APE'),
    ('DOGEUSDT', 'DOGE'), ('FETUSDT', 'FET'),
    ('DYDXUSDT', 'DYDX'), ('SHIBUSDT', 'SHIB'),
]

CONFIGS = {
    'v06_baseline': {
        'label': 'v0.06 BASELINE',
        'htf_filter': False, 'vol_filter': False, 'atr_filter': False,
        'connors_rsi': False, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': False, 'kaufman_er': False,
    },
    'htf_only': {
        'label': '+HTF Daily Trend Gate',
        'htf_filter': True, 'vol_filter': False, 'atr_filter': False,
        'connors_rsi': False, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': False, 'kaufman_er': False,
    },
    'vol_only': {
        'label': '+Volume 1.5x Filter',
        'htf_filter': False, 'vol_filter': True, 'atr_filter': False,
        'connors_rsi': False, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': False, 'kaufman_er': False,
    },
    'atr_pctile': {
        'label': '+ATR Percentile 20-95',
        'htf_filter': False, 'vol_filter': False, 'atr_filter': True,
        'connors_rsi': False, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': False, 'kaufman_er': False,
    },
    'crsi': {
        'label': '+Connors RSI',
        'htf_filter': False, 'vol_filter': False, 'atr_filter': False,
        'connors_rsi': True, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': False, 'kaufman_er': False,
    },
    'macd_acc': {
        'label': '+MACD Histogram Accel',
        'htf_filter': False, 'vol_filter': False, 'atr_filter': False,
        'connors_rsi': False, 'macd_accel': True, 'adaptive_st': False,
        'partial_tp': False, 'kaufman_er': False,
    },
    'adapt_st': {
        'label': '+Adaptive SuperTrend',
        'htf_filter': False, 'vol_filter': False, 'atr_filter': False,
        'connors_rsi': False, 'macd_accel': False, 'adaptive_st': True,
        'partial_tp': False, 'kaufman_er': False,
    },
    'partial': {
        'label': '+Partial TP at 1R + BE',
        'htf_filter': False, 'vol_filter': False, 'atr_filter': False,
        'connors_rsi': False, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': True, 'kaufman_er': False,
    },
    'ker': {
        'label': '+Kaufman ER > 0.3',
        'htf_filter': False, 'vol_filter': False, 'atr_filter': False,
        'connors_rsi': False, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': False, 'kaufman_er': True,
    },
    'v07_full': {
        'label': 'v0.07 FULL (all changes)',
        'htf_filter': True, 'vol_filter': True, 'atr_filter': True,
        'connors_rsi': True, 'macd_accel': True, 'adaptive_st': True,
        'partial_tp': True, 'kaufman_er': True,
    },
    'v07_top3': {
        'label': 'v0.07 TOP3 (HTF+Vol+ATR)',
        'htf_filter': True, 'vol_filter': True, 'atr_filter': True,
        'connors_rsi': False, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': False, 'kaufman_er': False,
    },
    'v07_filters_exits': {
        'label': 'v0.07 Filters+Exits (HTF+Vol+ATR+Partial)',
        'htf_filter': True, 'vol_filter': True, 'atr_filter': True,
        'connors_rsi': False, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': True, 'kaufman_er': False,
    },
}


def main():
    print("=" * 80)
    print("  SSK_Claude v0.07 BACKTESTER — Individual + Combined Tests")
    print("=" * 80)

    # Download data
    print("\nDownloading 1H data...")
    data_cache = {}
    for symbol, base in TEST_PAIRS:
        print(f"  {symbol}...", end='', flush=True)
        df = download_binance_klines(symbol, '1h', 1095)
        if df is not None and len(df) >= 500:
            data_cache[base] = df
            print(f" {len(df)} bars")
        else:
            print(f" SKIP")

    bases = list(data_cache.keys())
    print(f"\n{len(bases)} pairs loaded\n")

    # Run all configs
    all_results = {}
    for cfg_key, cfg in CONFIGS.items():
        label = cfg['label']
        print(f"{'='*70}")
        print(f"  {label}")
        print(f"{'='*70}")
        all_results[cfg_key] = {}
        for base, df in data_cache.items():
            r = run_v07(df, base, cfg)
            all_results[cfg_key][base] = r
            print(f"  {base:6s}: Tr={r['trades']:4d}  PnL={r['net_pnl']:>8.2f}%  PF={r['pf']:.3f}  WR={r['wr']:.1f}%  Sh={r['sharpe']:.3f}  DD={r['max_dd']:.1f}%  AvgTr={r['avg_trade']:.4f}%")

    # ── Comparison ──
    baseline = all_results['v06_baseline']
    non_baseline = [k for k in CONFIGS if k != 'v06_baseline']

    print(f"\n{'='*120}")
    print("  COMPARISON vs v0.06 BASELINE")
    print(f"{'='*120}")
    print(f"\n{'Config':<42} {'MeanΔPnL':>9} {'MeanΔPF':>8} {'MeanΔWR':>8} {'MeanΔSh':>8} {'MeanΔDD':>8} {'I/W':>5} {'t-stat':>7} {'p-val':>8} {'Sig':>4}")
    print("-" * 120)

    for cfg_key in non_baseline:
        changed = all_results[cfg_key]
        common = [b for b in bases if baseline[b]['trades'] > 0 and changed[b]['trades'] > 0]
        if not common:
            continue

        bp = np.array([baseline[b]['net_pnl'] for b in common])
        cp = np.array([changed[b]['net_pnl'] for b in common])
        diffs = cp - bp
        mean_d = np.mean(diffs)
        std_d = np.std(diffs, ddof=1) if len(diffs) > 1 else 0
        t_stat = mean_d / (std_d / np.sqrt(len(diffs))) if std_d > 0 else 0
        p_value = erfc(abs(t_stat) / sqrt(2)) if std_d > 0 else 1.0

        bwr = np.array([baseline[b]['wr'] for b in common])
        cwr = np.array([changed[b]['wr'] for b in common])
        bpf = np.array([baseline[b]['pf'] for b in common])
        cpf = np.array([changed[b]['pf'] for b in common])
        bsh = np.array([baseline[b]['sharpe'] for b in common])
        csh = np.array([changed[b]['sharpe'] for b in common])
        bdd = np.array([baseline[b]['max_dd'] for b in common])
        cdd = np.array([changed[b]['max_dd'] for b in common])

        imp = sum(1 for d in diffs if d > 0.5)
        wrs = sum(1 for d in diffs if d < -0.5)
        sig = "***" if p_value < 0.01 else ("**" if p_value < 0.05 else ("*" if p_value < 0.10 else ""))

        print(f"{CONFIGS[cfg_key]['label']:<42} {mean_d:>+8.1f}% {np.mean(cpf-bpf):>+7.4f} {np.mean(cwr-bwr):>+7.2f} {np.mean(csh-bsh):>+7.3f} {np.mean(cdd-bdd):>+7.1f} {imp:>2}/{wrs:<2} {t_stat:>7.3f} {p_value:>8.4f} {sig:>4}")

    # Per-pair detail for the best combined config
    for detail_key in ['v07_full', 'v07_top3', 'v07_filters_exits']:
        changed = all_results[detail_key]
        print(f"\n{'='*100}")
        print(f"  PER-PAIR DETAIL: {CONFIGS[detail_key]['label']}")
        print(f"{'='*100}")
        print(f"{'Pair':<6} {'Base PnL':>9} {'New PnL':>9} {'Delta':>8} {'Base WR':>8} {'New WR':>8} {'Base Tr':>7} {'New Tr':>7} {'Base Sh':>8} {'New Sh':>8} {'New DD':>8}")
        print("-" * 100)
        total_base = 0
        total_new = 0
        for b in bases:
            if baseline[b]['trades'] > 0 and changed[b]['trades'] > 0:
                d = changed[b]['net_pnl'] - baseline[b]['net_pnl']
                marker = '+' if d > 0.5 else ('-' if d < -0.5 else '=')
                total_base += baseline[b]['net_pnl']
                total_new += changed[b]['net_pnl']
                print(f"{b:<6} {baseline[b]['net_pnl']:>8.1f}% {changed[b]['net_pnl']:>8.1f}% {d:>+7.1f}% {baseline[b]['wr']:>7.1f}% {changed[b]['wr']:>7.1f}% {baseline[b]['trades']:>7} {changed[b]['trades']:>7} {baseline[b]['sharpe']:>8.3f} {changed[b]['sharpe']:>8.3f} {changed[b]['max_dd']:>7.1f}% {marker}")
        print(f"{'TOTAL':<6} {total_base:>8.1f}% {total_new:>8.1f}% {total_new-total_base:>+7.1f}%")

    # Save results
    os.makedirs('backtest_results', exist_ok=True)
    output = {}
    for cfg_key in all_results:
        output[cfg_key] = {b: r for b, r in all_results[cfg_key].items()}
    with open('backtest_results/v07_results.json', 'w') as f:
        json.dump(output, f, indent=2, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else x)
    print(f"\nResults saved to backtest_results/v07_results.json")


if __name__ == '__main__':
    main()
