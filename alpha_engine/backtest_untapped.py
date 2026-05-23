#!/usr/bin/env python3
import os, sys
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
"""
BACKTEST: 8 UNTAPPED STRATEGIES
================================
Comprehensive backtester for strategies not yet proven in our pipeline.

Strategies:
1. Hurst Pairs Trading -- Mean-reverting crypto pairs (Hurst < 0.45)
2. Max Pain Proxy -- BTC weekend bounce after Thursday dip
3. PCR Contrarian (VIX proxy) -- Buy SPY on extreme VIX readings
4. Google Trends Proxy -- RSI + volume surge on BTC
5. Copper/Gold Ratio -- Macro risk-on/off indicator for BTC
6. Options Expiry Calendar -- BTC Thursday-to-Monday effect
7. Turn of Month -- SPY last 4 / first 3 days of month
8. VIX Term Structure -- VIX spike vs 50d SMA for SPY entries

Data: yfinance (free). All backtests use binomial p-value for significance.
"""

import itertools
import json
import math
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

EST = timezone(timedelta(hours=-5))
UTC = timezone.utc
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)


# =============================================================================
# HELPERS (matching existing pattern from connors_rsi2.py / vix_spike_reversal.py)
# =============================================================================

def _flatten_yf(df):
    """Flatten MultiIndex columns from yfinance (e.g. ('Close','SPY') -> 'Close')."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def binomial_p_value(wins: int, n: int, p0: float = 0.5) -> float:
    """One-sided binomial p-value: P(X >= wins) under null hypothesis p = p0."""
    p_val = 0.0
    for k in range(wins, n + 1):
        p_val += math.comb(n, k) * (p0 ** k) * ((1 - p0) ** (n - k))
    return p_val


def compute_stats(trades: list[dict], verbose_name: str = "", verbose: bool = True) -> dict:
    """Compute standard stats from a list of trade dicts with 'pnl_pct' and 'won' keys."""
    if not trades:
        return {"error": "No trades found"}

    wins = sum(1 for t in trades if t["won"])
    n = len(trades)
    win_rate = wins / n
    pnls = [t["pnl_pct"] for t in trades]
    avg_pnl = sum(pnls) / n
    total_return = sum(pnls)
    pnl_std = (sum((p - avg_pnl) ** 2 for p in pnls) / max(n - 1, 1)) ** 0.5
    sharpe = (avg_pnl / pnl_std) * (252 ** 0.5) if pnl_std > 0 else 0.0

    # Max drawdown (cumulative)
    cumulative = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = cumulative - running_max
    max_dd = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

    p_val = binomial_p_value(wins, n)

    if verbose and verbose_name:
        print(f"\n  BACKTEST: {verbose_name}")
        print(f"  {'-' * 55}")
        print(f"  Total trades:   {n}")
        print(f"  Win rate:       {win_rate * 100:.1f}%")
        print(f"  Avg P&L/trade:  {avg_pnl:+.3f}%")
        print(f"  Total return:   {total_return:+.1f}%")
        print(f"  Sharpe ratio:   {sharpe:.2f}")
        print(f"  Max drawdown:   {max_dd:+.2f}%")
        print(f"  Binomial p:     {p_val:.4f} {'SIGNIFICANT' if p_val < 0.05 else '(not significant)'}")
        if trades:
            avg_days = sum(t.get("days", 0) for t in trades) / n
            if avg_days > 0:
                print(f"  Avg hold time:  {avg_days:.1f} days")
        print()

    return {
        "n_trades": n,
        "win_rate": round(win_rate, 4),
        "avg_pnl": round(avg_pnl, 4),
        "total_return": round(total_return, 2),
        "sharpe": round(sharpe, 3),
        "max_drawdown": round(max_dd, 2),
        "p_value": round(p_val, 6),
        "significant": p_val < 0.05,
        "trades": trades[-20:],
    }


def _download(symbol: str, period: str = "5y") -> pd.DataFrame | None:
    """Download and flatten a single symbol."""
    try:
        df = yf.download(symbol, period=period, interval="1d",
                         auto_adjust=True, progress=False)
        df = _flatten_yf(df).dropna(subset=["Close"])
        return df if len(df) > 20 else None
    except Exception:
        return None


# =============================================================================
# 1. HURST PAIRS TRADING
# =============================================================================

def _hurst_rs(series: np.ndarray) -> float:
    """Compute Hurst exponent using R/S (rescaled range) method."""
    n = len(series)
    if n < 20:
        return 0.5
    mean = np.mean(series)
    deviations = series - mean
    cumulative = np.cumsum(deviations)
    R = np.max(cumulative) - np.min(cumulative)
    S = np.std(series, ddof=1)
    if S == 0 or R == 0:
        return 0.5
    return np.log(R / S) / np.log(n)


def backtest_hurst_pairs(period: str = "2y", verbose: bool = True) -> dict:
    """
    Pairs trading on crypto using Hurst exponent to find mean-reverting pairs.
    When Hurst < 0.45 and spread z-score > 2: short spread, exit at z=0.5 or 14d max.
    """
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
               "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "NEAR-USD"]

    if verbose:
        print(f"  Downloading {len(symbols)} crypto symbols...")

    try:
        raw = yf.download(" ".join(symbols), period=period, interval="1d",
                          group_by="ticker", auto_adjust=True, threads=True,
                          progress=False)
    except Exception as e:
        return {"error": str(e)}

    # Extract close prices into a DataFrame
    closes = {}
    for sym in symbols:
        try:
            if sym in raw.columns.get_level_values(0):
                s = raw[sym]["Close"].dropna()
                if len(s) > 100:
                    closes[sym] = s
        except Exception:
            continue

    if len(closes) < 2:
        return {"error": f"Only {len(closes)} symbols had enough data"}

    close_df = pd.DataFrame(closes).dropna()
    log_prices = np.log(close_df)

    if verbose:
        print(f"  {len(closes)} symbols with {len(close_df)} common dates")

    trades = []
    pair_names = list(itertools.combinations(closes.keys(), 2))
    hurst_window = 60

    for sym_a, sym_b in pair_names:
        spread = log_prices[sym_a] - log_prices[sym_b]
        spread_mean = spread.rolling(hurst_window).mean()
        spread_std = spread.rolling(hurst_window).std()
        z_score = (spread - spread_mean) / spread_std.replace(0, np.nan)

        in_trade = False
        entry_idx = 0
        entry_z = 0.0

        for i in range(hurst_window + 10, len(spread)):
            window = spread.iloc[i - hurst_window:i].values
            h = _hurst_rs(window)
            z = float(z_score.iloc[i]) if not pd.isna(z_score.iloc[i]) else 0.0

            if not in_trade:
                # Entry: mean-reverting pair with extreme z
                if h < 0.45 and abs(z) > 2.0:
                    in_trade = True
                    entry_idx = i
                    entry_z = z
            else:
                days_held = i - entry_idx
                # Exit: z reverts to 0.5 band or 14d max
                if abs(float(z_score.iloc[i]) if not pd.isna(z_score.iloc[i]) else entry_z) < 0.5 or days_held >= 14:
                    # P&L: if we entered short spread (z > 2), profit = entry_z - exit_z
                    # if we entered long spread (z < -2), profit = exit_z - entry_z
                    exit_z = float(z_score.iloc[i]) if not pd.isna(z_score.iloc[i]) else 0.0
                    if entry_z > 0:
                        pnl_pct = (entry_z - exit_z) * 0.5  # scaled to ~% terms
                    else:
                        pnl_pct = (exit_z - entry_z) * 0.5

                    in_trade = False
                    trades.append({
                        "pair": f"{sym_a}/{sym_b}",
                        "entry_date": str(spread.index[entry_idx])[:10],
                        "exit_date": str(spread.index[i])[:10],
                        "entry_z": round(entry_z, 3),
                        "exit_z": round(exit_z, 3),
                        "pnl_pct": round(pnl_pct, 3),
                        "days": days_held,
                        "won": pnl_pct > 0,
                    })

    return compute_stats(trades, "Hurst Pairs Trading (crypto, 2y)", verbose)


# =============================================================================
# 2. MAX PAIN PROXY
# =============================================================================

def backtest_max_pain(period: str = "1y", verbose: bool = True) -> dict:
    """
    BTC max pain proxy: if BTC closes >2% below 20d SMA on Thursday,
    buy Friday open, sell Monday close (3-day hold).
    """
    df = _download("BTC-USD", period)
    if df is None:
        return {"error": "Could not download BTC-USD"}

    close = df["Close"].squeeze()
    open_price = df["Open"].squeeze()
    sma20 = sma(close, 20)

    trades = []

    for i in range(25, len(df) - 4):
        date = df.index[i]
        # Thursday = weekday 3
        if date.weekday() != 3:
            continue

        price = float(close.iloc[i])
        sma_val = float(sma20.iloc[i])
        if sma_val == 0:
            continue

        pct_below = (price - sma_val) / sma_val * 100

        if pct_below < -2.0:
            # Buy next trading day open (Friday), sell 3 trading days later close (Monday)
            if i + 3 < len(df):
                entry = float(open_price.iloc[i + 1])
                exit_price = float(close.iloc[i + 3])
                pnl = (exit_price - entry) / entry * 100

                trades.append({
                    "entry_date": str(df.index[i + 1])[:10],
                    "exit_date": str(df.index[i + 3])[:10],
                    "entry": round(entry, 2),
                    "exit": round(exit_price, 2),
                    "pnl_pct": round(pnl, 3),
                    "days": 3,
                    "won": pnl > 0,
                    "pct_below_sma": round(pct_below, 2),
                })

    return compute_stats(trades, "Max Pain Proxy (BTC Thu dip -> Mon close)", verbose)


# =============================================================================
# 3. PCR CONTRARIAN (VIX PROXY)
# =============================================================================

def backtest_pcr_contrarian(period: str = "5y", verbose: bool = True) -> dict:
    """
    Buy SPY when VIX > 30 (high PCR proxy), hold 10 days.
    Matches published Connors research.
    """
    spy = _download("SPY", period)
    vix = _download("^VIX", period)
    if spy is None or vix is None:
        return {"error": "Could not download SPY or VIX"}

    common = spy.index.intersection(vix.index)
    if len(common) < 50:
        return {"error": "Not enough overlapping dates"}

    spy_c = spy["Close"].reindex(common).squeeze()
    vix_c = vix["Close"].reindex(common).squeeze()

    trades = []
    in_trade = False
    entry_price = 0.0
    entry_idx = 0

    for i in range(1, len(common) - 10):
        vix_today = float(vix_c.iloc[i])
        spy_today = float(spy_c.iloc[i])

        if not in_trade and vix_today >= 30.0:
            in_trade = True
            entry_price = spy_today
            entry_idx = i

        elif in_trade and (i - entry_idx) >= 10:
            exit_price = float(spy_c.iloc[i])
            pnl = (exit_price - entry_price) / entry_price * 100
            in_trade = False
            trades.append({
                "entry_date": str(common[entry_idx])[:10],
                "exit_date": str(common[i])[:10],
                "entry": round(entry_price, 2),
                "exit": round(exit_price, 2),
                "pnl_pct": round(pnl, 3),
                "days": 10,
                "won": pnl > 0,
                "vix_at_entry": round(float(vix_c.iloc[entry_idx]), 2),
            })

    return compute_stats(trades, "PCR Contrarian (VIX>30 -> BUY SPY 10d)", verbose)


# =============================================================================
# 4. GOOGLE TRENDS PROXY (RSI + Volume Surge)
# =============================================================================

def backtest_google_trends_proxy(period: str = "2y", verbose: bool = True) -> dict:
    """
    BTC proxy for search interest: RSI-14 < 25 AND volume > 2x 20d avg -> BUY.
    Exit: RSI > 80 or TP 8% or SL 5% or 10d max.
    """
    df = _download("BTC-USD", period)
    if df is None:
        return {"error": "Could not download BTC-USD"}

    close = df["Close"].squeeze()
    vol = df["Volume"].squeeze()
    rsi14 = rsi(close, 14)
    vol_sma20 = sma(vol, 20)

    trades = []
    in_trade = False
    entry_price = 0.0
    entry_idx = 0

    for i in range(25, len(df)):
        price = float(close.iloc[i])
        rsi_val = float(rsi14.iloc[i]) if not pd.isna(rsi14.iloc[i]) else 50.0
        vol_val = float(vol.iloc[i])
        vol_avg = float(vol_sma20.iloc[i]) if not pd.isna(vol_sma20.iloc[i]) else vol_val

        if not in_trade:
            if rsi_val < 25 and vol_avg > 0 and vol_val > 2.0 * vol_avg:
                in_trade = True
                entry_price = price
                entry_idx = i
        else:
            days_held = i - entry_idx
            pnl = (price - entry_price) / entry_price * 100

            # Exit conditions
            if rsi_val > 80 or pnl >= 8.0 or pnl <= -5.0 or days_held >= 10:
                in_trade = False
                reason = "rsi_exit" if rsi_val > 80 else (
                    "tp" if pnl >= 8.0 else ("sl" if pnl <= -5.0 else "time"))
                trades.append({
                    "entry_date": str(df.index[entry_idx])[:10],
                    "exit_date": str(df.index[i])[:10],
                    "entry": round(entry_price, 2),
                    "exit": round(price, 2),
                    "pnl_pct": round(pnl, 3),
                    "days": days_held,
                    "won": pnl > 0,
                    "exit_reason": reason,
                })

    return compute_stats(trades, "Google Trends Proxy (BTC RSI<25 + Vol surge)", verbose)


# =============================================================================
# 5. COPPER/GOLD RATIO
# =============================================================================

def backtest_copper_gold(period: str = "5y", verbose: bool = True) -> dict:
    """
    Copper/Gold ratio as macro risk-on indicator for BTC.
    CGR RSI < 30 and turning up: BUY BTC. CGR RSI > 70 and turning down: SELL.
    Hold max 21 days.
    """
    copper = _download("HG=F", period)
    gold = _download("GC=F", period)
    btc = _download("BTC-USD", period)

    if copper is None or gold is None or btc is None:
        return {"error": "Could not download copper, gold, or BTC"}

    common = copper.index.intersection(gold.index).intersection(btc.index)
    if len(common) < 50:
        return {"error": "Not enough overlapping dates"}

    copper_c = copper["Close"].reindex(common).squeeze()
    gold_c = gold["Close"].reindex(common).squeeze()
    btc_c = btc["Close"].reindex(common).squeeze()

    # Copper/Gold ratio
    cgr = copper_c / gold_c.replace(0, np.nan)
    cgr = cgr.dropna()
    common = cgr.index.intersection(btc_c.index)
    cgr = cgr.reindex(common)
    btc_c = btc_c.reindex(common)

    cgr_rsi = rsi(cgr, 14)

    trades = []
    in_trade = False
    entry_price = 0.0
    entry_idx = 0

    for i in range(20, len(common)):
        rsi_now = float(cgr_rsi.iloc[i]) if not pd.isna(cgr_rsi.iloc[i]) else 50.0
        rsi_prev = float(cgr_rsi.iloc[i - 1]) if not pd.isna(cgr_rsi.iloc[i - 1]) else 50.0
        btc_price = float(btc_c.iloc[i])

        if not in_trade:
            # CGR RSI < 30 and turning up (risk-on incoming)
            if rsi_now < 30 and rsi_now > rsi_prev:
                in_trade = True
                entry_price = btc_price
                entry_idx = i
        else:
            days_held = i - entry_idx
            # Exit: CGR RSI > 70 turning down, or 21 day max
            if (rsi_now > 70 and rsi_now < rsi_prev) or days_held >= 21:
                exit_price = btc_price
                pnl = (exit_price - entry_price) / entry_price * 100
                in_trade = False
                trades.append({
                    "entry_date": str(common[entry_idx])[:10],
                    "exit_date": str(common[i])[:10],
                    "entry": round(entry_price, 2),
                    "exit": round(exit_price, 2),
                    "pnl_pct": round(pnl, 3),
                    "days": days_held,
                    "won": pnl > 0,
                    "cgr_rsi_entry": round(float(cgr_rsi.iloc[entry_idx]), 1),
                })

    return compute_stats(trades, "Copper/Gold Ratio -> BTC (5y)", verbose)


# =============================================================================
# 6. OPTIONS EXPIRY CALENDAR EFFECT
# =============================================================================

def backtest_options_expiry(period: str = "2y", verbose: bool = True) -> dict:
    """
    BTC calendar effect: buy Thursday close, sell Monday close.
    Tests the options expiry pinning / weekend effect.
    """
    df = _download("BTC-USD", period)
    if df is None:
        return {"error": "Could not download BTC-USD"}

    close = df["Close"].squeeze()
    trades = []

    for i in range(len(df) - 4):
        date = df.index[i]
        if date.weekday() != 3:  # Thursday
            continue

        entry = float(close.iloc[i])

        # Find next Monday (or closest trading day after)
        exit_idx = None
        for j in range(i + 1, min(i + 5, len(df))):
            if df.index[j].weekday() == 0:  # Monday
                exit_idx = j
                break
        if exit_idx is None:
            # Fallback: use Friday close (i+1) if no Monday found
            if i + 1 < len(df):
                exit_idx = i + 1
            else:
                continue

        exit_price = float(close.iloc[exit_idx])
        pnl = (exit_price - entry) / entry * 100
        days = (df.index[exit_idx] - df.index[i]).days

        trades.append({
            "entry_date": str(df.index[i])[:10],
            "exit_date": str(df.index[exit_idx])[:10],
            "entry": round(entry, 2),
            "exit": round(exit_price, 2),
            "pnl_pct": round(pnl, 3),
            "days": days,
            "won": pnl > 0,
        })

    return compute_stats(trades, "Options Expiry Calendar (BTC Thu->Mon)", verbose)


# =============================================================================
# 7. TURN OF MONTH EFFECT
# =============================================================================

def backtest_turn_of_month(period: str = "5y", verbose: bool = True) -> dict:
    """
    SPY Turn of Month: buy day -4 before month end, sell day +3 of new month.
    RSI < 75 filter to avoid overbought entries.
    """
    df = _download("SPY", period)
    if df is None:
        return {"error": "Could not download SPY"}

    close = df["Close"].squeeze()
    rsi14 = rsi(close, 14)

    # Find month boundaries
    dates = df.index
    trades = []
    i = 0

    while i < len(dates) - 10:
        current_month = dates[i].month
        current_year = dates[i].year

        # Find all dates in this month
        month_dates = [j for j in range(i, len(dates))
                       if dates[j].month == current_month and dates[j].year == current_year]

        if len(month_dates) < 5:
            i = month_dates[-1] + 1 if month_dates else i + 1
            continue

        # Day -4 from month end
        entry_pos = month_dates[-4] if len(month_dates) >= 4 else month_dates[0]

        # Find day +3 of next month
        next_month_start = month_dates[-1] + 1
        if next_month_start >= len(dates):
            break

        next_month_dates = []
        for j in range(next_month_start, min(next_month_start + 10, len(dates))):
            if dates[j].month != current_month:
                next_month_dates.append(j)
            if len(next_month_dates) >= 3:
                break

        if len(next_month_dates) < 3:
            i = next_month_start
            continue

        exit_pos = next_month_dates[2]  # Day +3

        rsi_val = float(rsi14.iloc[entry_pos]) if not pd.isna(rsi14.iloc[entry_pos]) else 50.0

        if rsi_val < 75:
            entry_price = float(close.iloc[entry_pos])
            exit_price = float(close.iloc[exit_pos])
            pnl = (exit_price - entry_price) / entry_price * 100
            days = (dates[exit_pos] - dates[entry_pos]).days

            trades.append({
                "entry_date": str(dates[entry_pos])[:10],
                "exit_date": str(dates[exit_pos])[:10],
                "entry": round(entry_price, 2),
                "exit": round(exit_price, 2),
                "pnl_pct": round(pnl, 3),
                "days": days,
                "won": pnl > 0,
                "rsi_at_entry": round(rsi_val, 1),
            })

        # Advance to next month
        i = next_month_start
        continue

    return compute_stats(trades, "Turn of Month (SPY day-4 to day+3, RSI<75)", verbose)


# =============================================================================
# 8. VIX TERM STRUCTURE (VIX vs 50d SMA)
# =============================================================================

def backtest_vix_term_structure(period: str = "5y", verbose: bool = True) -> dict:
    """
    When VIX > 1.5x its 50d SMA (fear spike), buy SPY and hold 10 days.
    """
    spy = _download("SPY", period)
    vix = _download("^VIX", period)
    if spy is None or vix is None:
        return {"error": "Could not download SPY or VIX"}

    common = spy.index.intersection(vix.index)
    if len(common) < 60:
        return {"error": "Not enough overlapping dates"}

    spy_c = spy["Close"].reindex(common).squeeze()
    vix_c = vix["Close"].reindex(common).squeeze()
    vix_sma50 = sma(vix_c, 50)

    trades = []
    in_trade = False
    entry_price = 0.0
    entry_idx = 0

    for i in range(55, len(common) - 10):
        vix_today = float(vix_c.iloc[i])
        vix_avg = float(vix_sma50.iloc[i]) if not pd.isna(vix_sma50.iloc[i]) else vix_today
        spy_today = float(spy_c.iloc[i])

        if not in_trade:
            if vix_avg > 0 and vix_today >= 1.5 * vix_avg:
                in_trade = True
                entry_price = spy_today
                entry_idx = i
        elif (i - entry_idx) >= 10:
            exit_price = float(spy_c.iloc[i])
            pnl = (exit_price - entry_price) / entry_price * 100
            in_trade = False
            trades.append({
                "entry_date": str(common[entry_idx])[:10],
                "exit_date": str(common[i])[:10],
                "entry": round(entry_price, 2),
                "exit": round(exit_price, 2),
                "pnl_pct": round(pnl, 3),
                "days": 10,
                "won": pnl > 0,
                "vix_at_entry": round(float(vix_c.iloc[entry_idx]), 2),
                "vix_sma50": round(vix_avg, 2),
                "vix_ratio": round(vix_today / vix_avg, 2) if vix_avg > 0 else 0,
            })

    return compute_stats(trades, "VIX Term Structure (VIX > 1.5x SMA50 -> BUY SPY)", verbose)


# =============================================================================
# MASTER RUNNER
# =============================================================================

BACKTESTS = {
    "hurst_pairs":          backtest_hurst_pairs,
    "max_pain_proxy":       backtest_max_pain,
    "pcr_contrarian":       backtest_pcr_contrarian,
    "google_trends_proxy":  backtest_google_trends_proxy,
    "copper_gold_ratio":    backtest_copper_gold,
    "options_expiry":       backtest_options_expiry,
    "turn_of_month":        backtest_turn_of_month,
    "vix_term_structure":   backtest_vix_term_structure,
}


def run_all_backtests(verbose: bool = True) -> dict:
    results = {}
    for name, func in BACKTESTS.items():
        print(f"\n{'=' * 70}")
        print(f"  BACKTEST: {name}")
        print(f"{'=' * 70}")
        try:
            results[name] = func(verbose=verbose)
        except Exception as e:
            print(f"  ERROR: {e}")
            results[name] = {"error": str(e)}

    # Summary table
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY: 8 Untapped Strategies")
    print(f"{'=' * 70}")
    print(f"  {'Strategy':<30} {'Trades':>6} {'WR':>7} {'Sharpe':>7} {'Avg PnL':>8} {'p-value':>8}")
    print(f"  {'-' * 70}")
    for name, r in results.items():
        if "error" not in r:
            print(f"  {name:<30} {r['n_trades']:>6} {r['win_rate'] * 100:>6.1f}% "
                  f"{r['sharpe']:>7.2f} {r['avg_pnl']:>+7.2f}% {r['p_value']:>8.4f}")
        else:
            print(f"  {name:<30} {'ERROR':>6}   {r['error'][:40]}")

    # Save
    out_file = DATA_DIR / "backtest_untapped.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved results -> {out_file}")

    return results


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in BACKTESTS:
        # Run single backtest
        name = sys.argv[1]
        print(f"\n{'=' * 70}")
        print(f"  BACKTEST: {name}")
        print(f"{'=' * 70}")
        result = BACKTESTS[name](verbose=True)
        out_file = DATA_DIR / "backtest_untapped.json"
        with open(out_file, "w") as f:
            json.dump({name: result}, f, indent=2, default=str)
        print(f"  Saved -> {out_file}")
    else:
        run_all_backtests()
