#!/usr/bin/env python3
"""
Simpleton v0.01_Claude* -- Python Backtester
Tests all 12 strategies across multiple crypto/equity symbols.
Usage:
    py simpleton_backtester.py                      # Full run (all symbols, all strategies)
    py simpleton_backtester.py --symbol BTC-USD     # Single symbol
    py simpleton_backtester.py --strategy sfp       # Single strategy across all pairs
    py simpleton_backtester.py --quick              # Fast mode (daily only, top 6 symbols)
    py simpleton_backtester.py --mix                # Test consensus/mix combos

Built by Claude Opus 4.6 | Feb 21, 2026
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

try:
    import yfinance as yf
    import numpy as np
    import pandas as pd
except ImportError:
    print("Install required packages: pip install yfinance numpy pandas")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SYMBOLS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "DOT-USD", "AVAX-USD",
    "DOGE-USD", "XRP-USD", "BNB-USD", "LINK-USD", "SPY", "QQQ"
]

QUICK_SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "SPY", "QQQ"]

STRATEGIES = [
    "connors_rsi2", "vix_spike", "macd_momentum", "ema_crossover",
    "bollinger_squeeze", "vwap_reversion", "rsi_divergence", "supertrend",
    "sfp", "bos", "consensus"
]

COMMISSION = 0.001  # 0.1%


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------
def sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df, period=14):
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift(1)).abs()
    lc = (df["Low"] - df["Close"].shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger(series, period=20, mult=2.0):
    mid = sma(series, period)
    std = series.rolling(window=period).std()
    upper = mid + mult * std
    lower = mid - mult * std
    return mid, upper, lower


def supertrend(df, factor=3.0, atr_period=10):
    atr_val = atr(df, atr_period)
    hl2 = (df["High"] + df["Low"]) / 2
    upper = hl2 + factor * atr_val
    lower = hl2 - factor * atr_val

    st_upper = upper.copy()
    st_lower = lower.copy()
    direction = pd.Series(1, index=df.index)

    for i in range(1, len(df)):
        if lower.iloc[i] > st_lower.iloc[i - 1]:
            st_lower.iloc[i] = lower.iloc[i]
        else:
            st_lower.iloc[i] = st_lower.iloc[i - 1]

        if upper.iloc[i] < st_upper.iloc[i - 1]:
            st_upper.iloc[i] = upper.iloc[i]
        else:
            st_upper.iloc[i] = st_upper.iloc[i - 1]

        if df["Close"].iloc[i] > st_upper.iloc[i - 1]:
            direction.iloc[i] = 1
        elif df["Close"].iloc[i] < st_lower.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

    return direction


def vwap_zscore(df):
    """Simple VWAP z-score using cumulative price*volume / cumulative volume."""
    cum_vol = df["Volume"].cumsum()
    cum_pv = (df["Close"] * df["Volume"]).cumsum()
    vwap_val = cum_pv / cum_vol.replace(0, np.nan)
    atr_val = atr(df)
    z = (df["Close"] - vwap_val) / atr_val.replace(0, np.nan)
    return z


# ---------------------------------------------------------------------------
# Strategies (each returns long_signal, short_signal Series)
# ---------------------------------------------------------------------------
def strat_connors_rsi2(df):
    r2 = rsi(df["Close"], 2)
    e200 = ema(df["Close"], 200)
    long_sig = (r2 < 10) & (df["Close"] > e200)
    short_sig = (r2 > 90) & (df["Close"] < e200)
    return long_sig, short_sig


def strat_vix_spike(df):
    r14 = rsi(df["Close"], 14)
    e50 = ema(df["Close"], 50)
    vol_sma = sma(df["Volume"], 20)
    vol_spike = df["Volume"] > vol_sma * 1.5
    long_sig = (r14 < 25) & (df["Close"] > e50) & vol_spike
    short_sig = (r14 > 75) & (df["Close"] < e50) & vol_spike
    return long_sig, short_sig


def strat_macd_momentum(df):
    ml, ms, mh = macd(df["Close"])
    long_sig = (ml > ms) & (ml.shift(1) <= ms.shift(1)) & (mh > 0)
    short_sig = (ml < ms) & (ml.shift(1) >= ms.shift(1)) & (mh < 0)
    return long_sig, short_sig


def strat_ema_crossover(df):
    e9 = ema(df["Close"], 9)
    e21 = ema(df["Close"], 21)
    e50 = ema(df["Close"], 50)
    long_sig = (e9 > e21) & (e9.shift(1) <= e21.shift(1)) & (df["Close"] > e50)
    short_sig = (e9 < e21) & (e9.shift(1) >= e21.shift(1)) & (df["Close"] < e50)
    return long_sig, short_sig


def strat_bollinger_squeeze(df):
    mid, upper, lower = bollinger(df["Close"])
    width = (upper - lower) / mid
    squeeze_pctrank = width.rolling(120).apply(lambda x: (x < x.iloc[-1]).mean() * 100 if len(x) > 0 else 50, raw=False)
    long_sig = (squeeze_pctrank < 20) & (df["Close"] > mid) & (df["Close"] > upper)
    short_sig = (squeeze_pctrank < 20) & (df["Close"] < mid) & (df["Close"] < lower)
    return long_sig, short_sig


def strat_vwap_reversion(df):
    z = vwap_zscore(df)
    r14 = rsi(df["Close"], 14)
    long_sig = (z < -2.0) & (r14 < 35)
    short_sig = (z > 2.0) & (r14 > 65)
    return long_sig, short_sig


def strat_rsi_divergence(df):
    r14 = rsi(df["Close"], 14)
    rsi_lo = r14.rolling(20).min().shift(1)
    price_lo = df["Low"].rolling(20).min().shift(1)
    rsi_hi = r14.rolling(20).max().shift(1)
    price_hi = df["High"].rolling(20).max().shift(1)
    long_sig = (df["Low"] < price_lo) & (r14 > rsi_lo) & (r14 < 40)
    short_sig = (df["High"] > price_hi) & (r14 < rsi_hi) & (r14 > 60)
    return long_sig, short_sig


def strat_supertrend(df):
    direction = supertrend(df)
    long_sig = (direction == 1) & (direction.shift(1) == -1)
    short_sig = (direction == -1) & (direction.shift(1) == 1)
    return long_sig, short_sig


def strat_sfp(df):
    sw_hi = df["High"].rolling(20).max().shift(1)
    sw_lo = df["Low"].rolling(20).min().shift(1)
    long_sig = (df["High"] > sw_hi) & (df["Close"] < sw_hi) & (df["Close"] > df["Open"])
    short_sig = (df["Low"] < sw_lo) & (df["Close"] > sw_lo) & (df["Close"] < df["Open"])
    return long_sig, short_sig


def strat_bos(df):
    sw_hi = df["High"].rolling(20).max().shift(1)
    sw_lo = df["Low"].rolling(20).min().shift(1)
    long_sig = (df["Close"] > sw_hi) & (df["Close"].shift(1) <= sw_hi.shift(1))
    short_sig = (df["Close"] < sw_lo) & (df["Close"].shift(1) >= sw_lo.shift(1))
    return long_sig, short_sig


def strat_consensus(df):
    """Majority vote across all strategies."""
    strats = [
        strat_connors_rsi2, strat_vix_spike, strat_macd_momentum,
        strat_ema_crossover, strat_bollinger_squeeze, strat_vwap_reversion,
        strat_rsi_divergence, strat_supertrend, strat_sfp, strat_bos,
    ]
    long_votes = pd.Series(0, index=df.index)
    short_votes = pd.Series(0, index=df.index)
    for fn in strats:
        try:
            ls, ss = fn(df)
            long_votes += ls.astype(int)
            short_votes += ss.astype(int)
        except Exception:
            pass
    long_sig = long_votes >= 3
    short_sig = short_votes >= 3
    return long_sig, short_sig


STRATEGY_MAP = {
    "connors_rsi2": strat_connors_rsi2,
    "vix_spike": strat_vix_spike,
    "macd_momentum": strat_macd_momentum,
    "ema_crossover": strat_ema_crossover,
    "bollinger_squeeze": strat_bollinger_squeeze,
    "vwap_reversion": strat_vwap_reversion,
    "rsi_divergence": strat_rsi_divergence,
    "supertrend": strat_supertrend,
    "sfp": strat_sfp,
    "bos": strat_bos,
    "consensus": strat_consensus,
}


# ---------------------------------------------------------------------------
# Backtester
# ---------------------------------------------------------------------------
def backtest(df, long_sig, short_sig, commission=COMMISSION, max_bars=50):
    """Simple long/short backtest with commission and time exit."""
    pos = 0  # 1=long, -1=short, 0=flat
    entry_price = 0.0
    bars_held = 0
    pnl_list = []

    for i in range(len(df)):
        if pos != 0:
            bars_held += 1

        # Time exit
        if pos != 0 and bars_held >= max_bars:
            exit_price = df["Close"].iloc[i]
            raw_pnl = (exit_price / entry_price - 1) * pos
            pnl_list.append(raw_pnl - 2 * commission)
            pos = 0
            bars_held = 0

        # Entry signals
        if pos == 0 and i < len(df) - 1:
            if long_sig.iloc[i]:
                pos = 1
                entry_price = df["Close"].iloc[i]
                bars_held = 0
            elif short_sig.iloc[i]:
                pos = -1
                entry_price = df["Close"].iloc[i]
                bars_held = 0

        # Exit on opposite signal
        elif pos == 1 and short_sig.iloc[i]:
            exit_price = df["Close"].iloc[i]
            raw_pnl = exit_price / entry_price - 1
            pnl_list.append(raw_pnl - 2 * commission)
            pos = -1
            entry_price = df["Close"].iloc[i]
            bars_held = 0
        elif pos == -1 and long_sig.iloc[i]:
            exit_price = df["Close"].iloc[i]
            raw_pnl = -(exit_price / entry_price - 1)
            pnl_list.append(raw_pnl - 2 * commission)
            pos = 1
            entry_price = df["Close"].iloc[i]
            bars_held = 0

    # Close any open position
    if pos != 0:
        exit_price = df["Close"].iloc[-1]
        raw_pnl = (exit_price / entry_price - 1) * pos
        pnl_list.append(raw_pnl - 2 * commission)

    return pnl_list


def calc_metrics(pnl_list):
    """Calculate performance metrics from a list of trade PnLs."""
    if not pnl_list:
        return {"trades": 0, "win_rate": 0, "total_pnl": 0, "profit_factor": 0, "sharpe": 0, "max_dd": 0}

    arr = np.array(pnl_list)
    wins = arr[arr > 0]
    losses = arr[arr <= 0]
    total = len(arr)
    wr = len(wins) / total * 100 if total > 0 else 0
    gross_profit = wins.sum() if len(wins) > 0 else 0
    gross_loss = abs(losses.sum()) if len(losses) > 0 else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else 0
    total_pnl = arr.sum() * 100  # as percentage

    # Sharpe (annualized, assuming ~252 trading days)
    if len(arr) > 1 and arr.std() > 0:
        sharpe = arr.mean() / arr.std() * np.sqrt(min(len(arr), 252))
    else:
        sharpe = 0

    # Max drawdown from cumulative equity curve
    cum = np.cumsum(arr)
    running_max = np.maximum.accumulate(cum)
    dd = running_max - cum
    max_dd = dd.max() * 100 if len(dd) > 0 else 0

    return {
        "trades": total,
        "win_rate": round(wr, 1),
        "total_pnl": round(total_pnl, 2),
        "profit_factor": round(pf, 2),
        "sharpe": round(sharpe, 2),
        "max_dd": round(max_dd, 2),
    }


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
def fetch_data(symbol, period="2y", interval="1d"):
    """Fetch OHLCV data from Yahoo Finance."""
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty:
            return None
        # Flatten multi-index columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print(f"  [!] Failed to fetch {symbol}: {e}")
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Simpleton v0.01_Claude* Backtester")
    parser.add_argument("--symbol", type=str, help="Test single symbol (e.g., BTC-USD)")
    parser.add_argument("--strategy", type=str, help="Test single strategy (e.g., sfp)")
    parser.add_argument("--quick", action="store_true", help="Quick mode: top 6 symbols, daily only")
    parser.add_argument("--mix", action="store_true", help="Test consensus/mix combos")
    parser.add_argument("--output", type=str, default="simpleton_results", help="Output directory")
    args = parser.parse_args()

    symbols = [args.symbol] if args.symbol else (QUICK_SYMBOLS if args.quick else SYMBOLS)
    strategies = [args.strategy] if args.strategy else STRATEGIES

    # Validate strategy name
    for s in strategies:
        if s not in STRATEGY_MAP:
            print(f"Unknown strategy: {s}")
            print(f"Available: {', '.join(STRATEGY_MAP.keys())}")
            sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    all_results = []
    best_per_symbol = {}

    print("=" * 70)
    print("  Simpleton v0.01_Claude* Backtester")
    print(f"  {len(symbols)} symbols x {len(strategies)} strategies = {len(symbols) * len(strategies)} combos")
    print("=" * 70)

    for sym in symbols:
        print(f"\n--- {sym} ---")
        df = fetch_data(sym)
        if df is None or len(df) < 200:
            print(f"  [!] Skipped (insufficient data)")
            continue

        best_sharpe = -999
        best_strat = ""
        best_metrics = {}

        for strat_name in strategies:
            fn = STRATEGY_MAP[strat_name]
            try:
                long_sig, short_sig = fn(df)
                # Fill NaN with False
                long_sig = long_sig.fillna(False)
                short_sig = short_sig.fillna(False)
                pnl_list = backtest(df, long_sig, short_sig)
                metrics = calc_metrics(pnl_list)
            except Exception as e:
                print(f"  [!] {strat_name}: Error - {e}")
                metrics = {"trades": 0, "win_rate": 0, "total_pnl": 0, "profit_factor": 0, "sharpe": 0, "max_dd": 0}

            result = {"symbol": sym, "strategy": strat_name, **metrics}
            all_results.append(result)

            status = "+" if metrics["total_pnl"] > 0 else "-"
            print(f"  {status} {strat_name:20s} | WR: {metrics['win_rate']:5.1f}% | PF: {metrics['profit_factor']:5.2f}x | Sharpe: {metrics['sharpe']:6.2f} | PnL: {metrics['total_pnl']:+7.1f}% | Trades: {metrics['trades']}")

            if metrics["sharpe"] > best_sharpe and metrics["trades"] >= 5:
                best_sharpe = metrics["sharpe"]
                best_strat = strat_name
                best_metrics = metrics

        if best_strat:
            best_per_symbol[sym] = {"strategy": best_strat, **best_metrics}
            print(f"  -> Best: {best_strat} (Sharpe {best_sharpe:.2f})")

    # Save results
    results_file = os.path.join(args.output, "full_backtest_results.json")
    top_file = os.path.join(args.output, "top_strategies_per_symbol.json")

    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)
    with open(top_file, "w") as f:
        json.dump(best_per_symbol, f, indent=2)

    print(f"\n{'=' * 70}")
    print(f"  Results saved to: {results_file}")
    print(f"  Top strategies:   {top_file}")
    print(f"  Total combos:     {len(all_results)}")
    print(f"{'=' * 70}")

    # Summary table
    if best_per_symbol:
        print(f"\n  {'Symbol':10s} {'Best Strategy':20s} {'WR':>6s} {'PF':>7s} {'Sharpe':>8s} {'PnL':>8s}")
        print(f"  {'-'*10} {'-'*20} {'-'*6} {'-'*7} {'-'*8} {'-'*8}")
        for sym, data in sorted(best_per_symbol.items(), key=lambda x: -x[1]["sharpe"]):
            print(f"  {sym:10s} {data['strategy']:20s} {data['win_rate']:5.1f}% {data['profit_factor']:6.2f}x {data['sharpe']:7.2f} {data['total_pnl']:+7.1f}%")


if __name__ == "__main__":
    main()
