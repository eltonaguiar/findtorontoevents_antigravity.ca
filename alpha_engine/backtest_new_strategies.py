#!/usr/bin/env python3
"""
Backtest 3 candidate strategies for Elton's Predictions v6.0:
  1. Donchian Turtle Breakout (KAMA + ADX filter)
  2. Z-Score Mean Reversion (triple filter)
  3. HMA Trend (Hull Moving Average crossover)

Usage:
  py backtest_new_strategies.py [strategy] [symbols...]
  py backtest_new_strategies.py all             # Run all 3
  py backtest_new_strategies.py donchian SPY QQQ BTC-USD
  py backtest_new_strategies.py zscore BTC-USD ETH-USD
  py backtest_new_strategies.py hma BTC-USD SPY
"""

import math
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf


# --- UTILITY FUNCTIONS ---------------------------------------------------------

def binomial_p(wins: int, n: int, p_null: float = 0.5) -> float:
    """One-tailed binomial test: P(X >= wins) under null hypothesis p=p_null."""
    if n == 0:
        return 1.0
    p_val = 0.0
    for k in range(wins, n + 1):
        p_val += math.comb(n, k) * (p_null ** k) * ((1 - p_null) ** (n - k))
    return p_val


def calc_sharpe(pnls: list, annualize: float = 252.0) -> float:
    """Annualized Sharpe ratio from list of per-trade P&L percentages."""
    if len(pnls) < 2:
        return 0.0
    arr = np.array(pnls)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    if std == 0:
        return 0.0
    return float((mean / std) * np.sqrt(annualize))


def fetch_data(symbol: str, period: str = "5y") -> pd.DataFrame:
    """Download OHLCV data via yfinance."""
    df = yf.download(symbol, period=period, interval="1d",
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    return df


def report(name: str, results: dict):
    """Pretty-print backtest results."""
    print(f"\n{'='*60}")
    print(f"  BACKTEST: {name} on {results['symbol']} ({results.get('period', '5y')})")
    print(f"{'='*60}")
    n = results["n_trades"]
    if n == 0:
        print("  No trades generated.")
        return
    wr = results["win_rate"]
    sig = results["significant"]
    sig_mark = "[Y] SIGNIFICANT" if sig else "[X] Not significant"
    print(f"  Total trades:   {n}")
    print(f"  Win rate:       {wr*100:.1f}% {sig_mark}")
    print(f"  Avg P&L/trade:  {results['avg_pnl_pct']:+.3f}%")
    print(f"  Total return:   {results['total_return_pct']:+.1f}%")
    print(f"  Sharpe ratio:   {results['sharpe']:.3f}")
    print(f"  Binomial p:     {results['binomial_p']:.6f}")
    print(f"  Avg hold time:  {results['avg_days_held']:.1f} days")
    print(f"  Max consec loss: {results.get('max_consec_loss', 'N/A')}")
    # Last 5 trades
    trades = results.get("trades", [])
    if trades:
        print(f"\n  Last 5 trades:")
        for t in trades[-5:]:
            w = "WIN" if t["won"] else "LOSS"
            print(f"    {t['entry_date']} -> {t['exit_date']}  "
                  f"{t['pnl_pct']:+.2f}%  [{w}]  {t['exit_reason']}")
    print()


def summarize_trades(trades: list, symbol: str, period: str = "5y") -> dict:
    """Calculate standard metrics from a list of trade dicts."""
    n = len(trades)
    if n == 0:
        return {"symbol": symbol, "period": period, "n_trades": 0,
                "win_rate": 0, "avg_pnl_pct": 0, "total_return_pct": 0,
                "sharpe": 0, "binomial_p": 1.0, "significant": False,
                "avg_days_held": 0, "max_consec_loss": 0, "trades": []}

    wins = sum(1 for t in trades if t["won"])
    pnls = [t["pnl_pct"] for t in trades]
    days = [t["days"] for t in trades]

    # Max consecutive losses
    max_cl = 0
    cl = 0
    for t in trades:
        if not t["won"]:
            cl += 1
            max_cl = max(max_cl, cl)
        else:
            cl = 0

    return {
        "symbol": symbol,
        "period": period,
        "n_trades": n,
        "win_rate": round(wins / n, 4),
        "avg_pnl_pct": round(np.mean(pnls), 4),
        "total_return_pct": round(sum(pnls), 2),
        "sharpe": round(calc_sharpe(pnls), 3),
        "binomial_p": round(binomial_p(wins, n), 6),
        "significant": binomial_p(wins, n) < 0.05,
        "avg_days_held": round(np.mean(days), 1),
        "max_consec_loss": max_cl,
        "trades": trades[-20:],
    }


# --- STRATEGY 1: DONCHIAN TURTLE BREAKOUT --------------------------------------
# Reference: Turtle Trading (Richard Dennis, 1983), KAMA (Kaufman 1998)
# Entry: Close > 20-bar high AND KAMA rising AND ADX > 20
# Exit: Close < 10-bar low (trailing) OR 20 days max hold
# Short: Close < 20-bar low AND KAMA falling AND ADX > 20

def backtest_donchian_turtle(symbol: str = "BTC-USD", period: str = "5y") -> dict:
    """Donchian Channel breakout with KAMA slope + ADX filter."""
    df = fetch_data(symbol, period)
    if len(df) < 250:
        return summarize_trades([], symbol, period)

    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values
    dates = df.index

    # Parameters
    dc_len = 20       # Donchian channel length
    dc_exit_len = 10  # Exit channel length
    kama_len = 21     # KAMA efficiency ratio window
    kama_fast = 2     # KAMA fast smoothing
    kama_slow = 30    # KAMA slow smoothing
    adx_len = 14      # ADX length
    adx_floor = 20.0  # Minimum ADX for entry
    max_hold = 20     # Maximum holding period

    # Calculate KAMA
    kama = np.full(len(close), np.nan)
    kama[kama_len] = close[kama_len]
    fast_sc = 2.0 / (kama_fast + 1.0)
    slow_sc = 2.0 / (kama_slow + 1.0)
    for i in range(kama_len + 1, len(close)):
        change_abs = abs(close[i] - close[i - kama_len])
        vol_abs = sum(abs(close[j] - close[j-1]) for j in range(i - kama_len + 1, i + 1))
        er = change_abs / vol_abs if vol_abs > 0 else 0.0
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
        kama[i] = kama[i-1] + sc * (close[i] - kama[i-1])

    # Calculate ADX
    def calc_adx(high, low, close, length):
        adx_arr = np.full(len(close), np.nan)
        tr_arr = np.zeros(len(close))
        plus_dm = np.zeros(len(close))
        minus_dm = np.zeros(len(close))

        for i in range(1, len(close)):
            h_diff = high[i] - high[i-1]
            l_diff = low[i-1] - low[i]
            tr_arr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
            plus_dm[i] = h_diff if h_diff > l_diff and h_diff > 0 else 0
            minus_dm[i] = l_diff if l_diff > h_diff and l_diff > 0 else 0

        # Wilder smoothing (RMA)
        atr = np.zeros(len(close))
        pdi = np.zeros(len(close))
        mdi = np.zeros(len(close))

        atr[length] = np.mean(tr_arr[1:length+1])
        s_plus = np.mean(plus_dm[1:length+1])
        s_minus = np.mean(minus_dm[1:length+1])

        for i in range(length + 1, len(close)):
            atr[i] = (atr[i-1] * (length - 1) + tr_arr[i]) / length
            s_plus = (s_plus * (length - 1) + plus_dm[i]) / length
            s_minus = (s_minus * (length - 1) + minus_dm[i]) / length
            pdi[i] = 100 * s_plus / atr[i] if atr[i] > 0 else 0
            mdi[i] = 100 * s_minus / atr[i] if atr[i] > 0 else 0

        dx = np.zeros(len(close))
        for i in range(length, len(close)):
            denom = pdi[i] + mdi[i]
            dx[i] = 100 * abs(pdi[i] - mdi[i]) / denom if denom > 0 else 0

        adx_arr[2 * length] = np.mean(dx[length:2*length+1])
        for i in range(2 * length + 1, len(close)):
            adx_arr[i] = (adx_arr[i-1] * (length - 1) + dx[i]) / length

        return adx_arr

    adx = calc_adx(high, low, close, adx_len)

    # Donchian Channels
    trades = []
    in_trade = False
    trade_dir = 0  # 1=long, -1=short
    entry_price = 0.0
    entry_idx = 0

    warmup = max(dc_len, kama_len, 2 * adx_len) + 5

    for i in range(warmup, len(close)):
        # Donchian levels
        dc_high = max(high[i-dc_len:i])     # Previous 20-bar high (not including current)
        dc_low = min(low[i-dc_len:i])       # Previous 20-bar low
        exit_high = max(high[i-dc_exit_len:i])
        exit_low = min(low[i-dc_exit_len:i])

        # KAMA direction
        kama_up = not np.isnan(kama[i]) and not np.isnan(kama[i-1]) and kama[i] > kama[i-1]
        kama_dn = not np.isnan(kama[i]) and not np.isnan(kama[i-1]) and kama[i] < kama[i-1]

        # ADX filter
        adx_ok = not np.isnan(adx[i]) and adx[i] >= adx_floor

        if not in_trade:
            # Long entry: close breaks above Donchian high + KAMA up + ADX
            if close[i] > dc_high and kama_up and adx_ok:
                in_trade = True
                trade_dir = 1
                entry_price = close[i]
                entry_idx = i
            # Short entry: close breaks below Donchian low + KAMA down + ADX
            elif close[i] < dc_low and kama_dn and adx_ok:
                in_trade = True
                trade_dir = -1
                entry_price = close[i]
                entry_idx = i
        else:
            days_held = i - entry_idx
            exit_reason = None

            if trade_dir == 1:
                # Exit long: close < 10-bar low OR max hold
                if close[i] < exit_low:
                    exit_reason = "trail_exit"
                elif days_held >= max_hold:
                    exit_reason = "time_exit"
            else:
                # Exit short: close > 10-bar high OR max hold
                if close[i] > exit_high:
                    exit_reason = "trail_exit"
                elif days_held >= max_hold:
                    exit_reason = "time_exit"

            if exit_reason:
                exit_price = close[i]
                if trade_dir == 1:
                    pnl = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl = (entry_price - exit_price) / entry_price * 100

                trades.append({
                    "entry_date": str(dates[entry_idx].date()),
                    "exit_date": str(dates[i].date()),
                    "entry": round(float(entry_price), 2),
                    "exit": round(float(exit_price), 2),
                    "pnl_pct": round(pnl, 4),
                    "days": days_held,
                    "won": pnl > 0,
                    "direction": "long" if trade_dir == 1 else "short",
                    "exit_reason": exit_reason,
                })
                in_trade = False
                trade_dir = 0

    return summarize_trades(trades, symbol, period)


# --- STRATEGY 2: Z-SCORE MEAN REVERSION ----------------------------------------
# Reference: Corbet & Katsiampa 2018, Ornstein-Uhlenbeck framework
# Entry LONG: Z-score < -2.0 AND ADX < 25 AND BB width > 0.02 AND ATR% > 0.3
# Entry SHORT: Z-score > +2.0 AND same filters
# Exit: Z-score returns to 0 (mean) OR RSI crosses 50 OR 10 days max hold

def backtest_zscore_mr(symbol: str = "BTC-USD", period: str = "5y") -> dict:
    """Z-Score mean reversion with triple filter (ADX + BBW + ATR%)."""
    df = fetch_data(symbol, period)
    if len(df) < 250:
        return summarize_trades([], symbol, period)

    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values
    dates = df.index

    # Parameters
    z_len = 20         # Z-score lookback
    z_entry = 2.0      # Entry threshold (standard deviations)
    z_exit = 0.0       # Exit at mean
    adx_threshold = 25  # ADX must be BELOW this (ranging market)
    bbw_threshold = 0.02  # BB width must be ABOVE this (not dead)
    atr_pct_floor = 0.3  # ATR% must be ABOVE this
    rsi_len = 14
    rsi_exit_long = 50   # Exit long when RSI > 50
    rsi_exit_short = 50  # Exit short when RSI < 50
    max_hold = 10

    # Calculate Z-score
    z_scores = np.full(len(close), np.nan)
    for i in range(z_len, len(close)):
        window = close[i-z_len:i+1]
        mean = np.mean(window)
        std = np.std(window, ddof=1)
        z_scores[i] = (close[i] - mean) / std if std > 0 else 0.0

    # Calculate ADX (reuse from above concept)
    def calc_adx_simple(high, low, close, length):
        n = len(close)
        adx_arr = np.full(n, np.nan)
        tr_arr = np.zeros(n)
        plus_dm = np.zeros(n)
        minus_dm = np.zeros(n)
        for i in range(1, n):
            h_diff = high[i] - high[i-1]
            l_diff = low[i-1] - low[i]
            tr_arr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
            plus_dm[i] = h_diff if h_diff > l_diff and h_diff > 0 else 0
            minus_dm[i] = l_diff if l_diff > h_diff and l_diff > 0 else 0
        atr = np.zeros(n)
        if length + 1 > n: return adx_arr
        atr[length] = np.mean(tr_arr[1:length+1])
        s_plus = np.mean(plus_dm[1:length+1])
        s_minus = np.mean(minus_dm[1:length+1])
        pdi = np.zeros(n)
        mdi = np.zeros(n)
        for i in range(length + 1, n):
            atr[i] = (atr[i-1] * (length - 1) + tr_arr[i]) / length
            s_plus = (s_plus * (length - 1) + plus_dm[i]) / length
            s_minus = (s_minus * (length - 1) + minus_dm[i]) / length
            pdi[i] = 100 * s_plus / atr[i] if atr[i] > 0 else 0
            mdi[i] = 100 * s_minus / atr[i] if atr[i] > 0 else 0
        dx = np.zeros(n)
        for i in range(length, n):
            denom = pdi[i] + mdi[i]
            dx[i] = 100 * abs(pdi[i] - mdi[i]) / denom if denom > 0 else 0
        if 2 * length >= n: return adx_arr
        adx_arr[2 * length] = np.mean(dx[length:2*length+1])
        for i in range(2 * length + 1, n):
            adx_arr[i] = (adx_arr[i-1] * (length - 1) + dx[i]) / length
        return adx_arr

    adx = calc_adx_simple(high, low, close, 14)

    # Calculate Bollinger BandWidth
    bb_width = np.full(len(close), np.nan)
    bb_len = 20
    for i in range(bb_len, len(close)):
        window = close[i-bb_len:i+1]
        basis = np.mean(window)
        dev = 2.0 * np.std(window, ddof=1)
        bb_width[i] = (2 * dev) / basis if basis > 0 else 0.0

    # Calculate ATR%
    atr_pct = np.full(len(close), np.nan)
    atr_len = 14
    for i in range(atr_len + 1, len(close)):
        trs = []
        for j in range(i - atr_len, i):
            tr = max(high[j+1] - low[j+1],
                     abs(high[j+1] - close[j]),
                     abs(low[j+1] - close[j]))
            trs.append(tr)
        atr_val = np.mean(trs)
        atr_pct[i] = (atr_val / close[i]) * 100 if close[i] > 0 else 0.0

    # Calculate RSI
    rsi = np.full(len(close), np.nan)
    for i in range(rsi_len + 1, len(close)):
        gains = []
        losses = []
        for j in range(i - rsi_len, i):
            chg = close[j+1] - close[j]
            gains.append(max(chg, 0))
            losses.append(max(-chg, 0))
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))

    # Trade loop
    trades = []
    in_trade = False
    trade_dir = 0
    entry_price = 0.0
    entry_idx = 0

    warmup = 50

    for i in range(warmup, len(close)):
        z = z_scores[i]
        if np.isnan(z):
            continue

        # Filter checks
        adx_ok = not np.isnan(adx[i]) and adx[i] < adx_threshold
        bbw_ok = not np.isnan(bb_width[i]) and bb_width[i] > bbw_threshold
        atr_ok = not np.isnan(atr_pct[i]) and atr_pct[i] > atr_pct_floor
        all_pass = adx_ok and bbw_ok and atr_ok

        if not in_trade:
            if z < -z_entry and all_pass:
                in_trade = True
                trade_dir = 1
                entry_price = close[i]
                entry_idx = i
            elif z > z_entry and all_pass:
                in_trade = True
                trade_dir = -1
                entry_price = close[i]
                entry_idx = i
        else:
            days_held = i - entry_idx
            exit_reason = None

            # Z-score return to mean
            if trade_dir == 1 and z >= z_exit:
                exit_reason = "zscore_mean"
            elif trade_dir == -1 and z <= -z_exit:
                exit_reason = "zscore_mean"
            # RSI exit
            elif trade_dir == 1 and not np.isnan(rsi[i]) and rsi[i] > rsi_exit_long:
                exit_reason = "rsi_exit"
            elif trade_dir == -1 and not np.isnan(rsi[i]) and rsi[i] < rsi_exit_short:
                exit_reason = "rsi_exit"
            # Time exit
            elif days_held >= max_hold:
                exit_reason = "time_exit"

            if exit_reason:
                exit_price = close[i]
                if trade_dir == 1:
                    pnl = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl = (entry_price - exit_price) / entry_price * 100

                trades.append({
                    "entry_date": str(dates[entry_idx].date()),
                    "exit_date": str(dates[i].date()),
                    "entry": round(float(entry_price), 2),
                    "exit": round(float(exit_price), 2),
                    "pnl_pct": round(pnl, 4),
                    "days": days_held,
                    "won": pnl > 0,
                    "direction": "long" if trade_dir == 1 else "short",
                    "exit_reason": exit_reason,
                })
                in_trade = False
                trade_dir = 0

    return summarize_trades(trades, symbol, period)


# --- STRATEGY 3: HMA TREND -----------------------------------------------------
# Reference: Alan Hull's HMA = WMA(2*WMA(n/2) - WMA(n), sqrt(n))
# Entry LONG: HMA turns up (HMA > HMA[1]) AND close > SMA(50) AND RSI < 70
# Entry SHORT: HMA turns down (HMA < HMA[1]) AND close < SMA(50) AND RSI > 30
# Exit: HMA reverses direction OR 15 days max hold

def backtest_hma_trend(symbol: str = "BTC-USD", period: str = "5y") -> dict:
    """Hull Moving Average trend-following strategy."""
    df = fetch_data(symbol, period)
    if len(df) < 250:
        return summarize_trades([], symbol, period)

    close = df["Close"].values
    dates = df.index

    # Parameters
    hma_len = 50       # HMA length (shorter than Crypto Wolf's 100 for more signals)
    sma_filter_len = 50  # Trend filter
    max_hold = 15

    # Calculate WMA helper
    def wma(data, length, start, end):
        """Weighted Moving Average at each position."""
        result = np.full(len(data), np.nan)
        for i in range(start, min(end, len(data))):
            if i < length - 1:
                continue
            window = data[i-length+1:i+1]
            weights = np.arange(1, length + 1)
            result[i] = np.average(window, weights=weights)
        return result

    # Calculate HMA: WMA(2*WMA(n/2) - WMA(n), sqrt(n))
    half_len = int(hma_len / 2)
    sqrt_len = int(math.floor(math.sqrt(hma_len)))

    wma_half = wma(close, half_len, half_len, len(close))
    wma_full = wma(close, hma_len, hma_len, len(close))

    # 2*WMA(n/2) - WMA(n)
    diff = np.full(len(close), np.nan)
    for i in range(hma_len, len(close)):
        if not np.isnan(wma_half[i]) and not np.isnan(wma_full[i]):
            diff[i] = 2.0 * wma_half[i] - wma_full[i]

    # HMA = WMA(diff, sqrt(n))
    hma_vals = wma(diff, sqrt_len, hma_len + sqrt_len, len(close))

    # SMA filter
    sma50 = np.full(len(close), np.nan)
    for i in range(sma_filter_len, len(close)):
        sma50[i] = np.mean(close[i-sma_filter_len:i+1])

    # RSI
    rsi = np.full(len(close), np.nan)
    rsi_len = 14
    for i in range(rsi_len + 1, len(close)):
        gains = []
        losses = []
        for j in range(i - rsi_len, i):
            chg = close[j+1] - close[j]
            gains.append(max(chg, 0))
            losses.append(max(-chg, 0))
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))

    # Trade loop
    trades = []
    in_trade = False
    trade_dir = 0
    entry_price = 0.0
    entry_idx = 0

    warmup = hma_len + sqrt_len + 5

    for i in range(warmup, len(close)):
        if np.isnan(hma_vals[i]) or np.isnan(hma_vals[i-1]):
            continue

        hma_up = hma_vals[i] > hma_vals[i-1]
        hma_dn = hma_vals[i] < hma_vals[i-1]
        above_sma = not np.isnan(sma50[i]) and close[i] > sma50[i]
        below_sma = not np.isnan(sma50[i]) and close[i] < sma50[i]
        rsi_ok_long = np.isnan(rsi[i]) or rsi[i] < 70
        rsi_ok_short = np.isnan(rsi[i]) or rsi[i] > 30

        if not in_trade:
            # Long: HMA turns up + above SMA50 + RSI not overbought
            if hma_up and not hma_vals[i-1] > hma_vals[i-2] and above_sma and rsi_ok_long:
                # HMA just turned up (crossover)
                in_trade = True
                trade_dir = 1
                entry_price = close[i]
                entry_idx = i
            # Short: HMA turns down + below SMA50 + RSI not oversold
            elif hma_dn and not hma_vals[i-1] < hma_vals[i-2] and below_sma and rsi_ok_short:
                in_trade = True
                trade_dir = -1
                entry_price = close[i]
                entry_idx = i
        else:
            days_held = i - entry_idx
            exit_reason = None

            # Exit when HMA reverses
            if trade_dir == 1 and hma_dn:
                exit_reason = "hma_reversal"
            elif trade_dir == -1 and hma_up:
                exit_reason = "hma_reversal"
            elif days_held >= max_hold:
                exit_reason = "time_exit"

            if exit_reason:
                exit_price = close[i]
                if trade_dir == 1:
                    pnl = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl = (entry_price - exit_price) / entry_price * 100

                trades.append({
                    "entry_date": str(dates[entry_idx].date()),
                    "exit_date": str(dates[i].date()),
                    "entry": round(float(entry_price), 2),
                    "exit": round(float(exit_price), 2),
                    "pnl_pct": round(pnl, 4),
                    "days": days_held,
                    "won": pnl > 0,
                    "direction": "long" if trade_dir == 1 else "short",
                    "exit_reason": exit_reason,
                })
                in_trade = False
                trade_dir = 0

    return summarize_trades(trades, symbol, period)


# --- MAIN ----------------------------------------------------------------------

def run_all():
    """Run all 3 backtests on multiple symbols."""
    symbols = ["BTC-USD", "SPY", "QQQ", "ETH-USD"]
    strategies = [
        ("Donchian Turtle Breakout", backtest_donchian_turtle),
        ("Z-Score Mean Reversion", backtest_zscore_mr),
        ("HMA Trend", backtest_hma_trend),
    ]

    all_results = {}

    for strat_name, strat_fn in strategies:
        print(f"\n{'#'*60}")
        print(f"  {strat_name}")
        print(f"{'#'*60}")
        strat_results = {}
        for sym in symbols:
            try:
                res = strat_fn(sym)
                report(strat_name, res)
                strat_results[sym] = res
            except Exception as e:
                print(f"  ERROR on {sym}: {e}")
                strat_results[sym] = {"error": str(e)}
        all_results[strat_name] = strat_results

    # Summary table
    print("\n" + "=" * 80)
    print("  SUMMARY: All Strategy Backtests")
    print("=" * 80)
    print(f"  {'Strategy':<30} {'Symbol':<10} {'Trades':>7} {'WR%':>7} {'Sharpe':>8} {'p-val':>10} {'Sig?':>5}")
    print("-" * 80)

    for strat_name, strat_results in all_results.items():
        for sym, res in strat_results.items():
            if "error" in res:
                print(f"  {strat_name:<30} {sym:<10} {'ERROR':>7}")
                continue
            n = res["n_trades"]
            wr = res["win_rate"] * 100
            sh = res["sharpe"]
            pv = res["binomial_p"]
            sig = "YES" if res["significant"] else "no"
            print(f"  {strat_name:<30} {sym:<10} {n:>7} {wr:>6.1f}% {sh:>8.3f} {pv:>10.6f} {sig:>5}")

    # Save results
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    out_file = data_dir / "new_strategy_backtests.json"

    # Clean for JSON serialization
    json_results = {}
    for strat_name, strat_results in all_results.items():
        json_results[strat_name] = {}
        for sym, res in strat_results.items():
            clean = {k: v for k, v in res.items() if k != "trades"}
            if "trades" in res:
                clean["last_trades"] = res.get("trades", [])[-5:]
            json_results[strat_name][sym] = clean

    with open(out_file, "w") as f:
        json.dump(json_results, f, indent=2, default=str)
    print(f"\n  Results saved to: {out_file}")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "all":
        run_all()
    elif args[0] == "donchian":
        symbols = args[1:] if len(args) > 1 else ["BTC-USD", "SPY"]
        for sym in symbols:
            res = backtest_donchian_turtle(sym)
            report("Donchian Turtle Breakout", res)
    elif args[0] == "zscore":
        symbols = args[1:] if len(args) > 1 else ["BTC-USD", "SPY"]
        for sym in symbols:
            res = backtest_zscore_mr(sym)
            report("Z-Score Mean Reversion", res)
    elif args[0] == "hma":
        symbols = args[1:] if len(args) > 1 else ["BTC-USD", "SPY"]
        for sym in symbols:
            res = backtest_hma_trend(sym)
            report("HMA Trend", res)
    else:
        print(__doc__)
