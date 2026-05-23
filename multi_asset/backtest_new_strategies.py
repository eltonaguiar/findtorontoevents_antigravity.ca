#!/usr/bin/env python3
"""
COMPREHENSIVE BACKTEST: Institutional Picks Engine Strategies
==============================================================
Tests 5 strategies over 2 years of daily data across all asset classes.
Validates sustained positive PnL over thousands of simulated picks.

Strategies tested:
  1. penny_deep_oversold    - RSI(2)<3 + >8% off 20d high on penny stocks
  2. futures_mean_reversion - BB(15,2.5) + RSI(3)<20 LONG / RSI(3)>80 SHORT
  3. forex_carry_momentum   - Carry pairs + EMA20/50 momentum + RSI extremes
  4. extreme_oversold_bounce - RSI(2)<5 + below BB on any symbol
  5. hyperopt_connors_rsi2  - Per-symbol tuned Connors RSI

Usage:
  python multi_asset/backtest_new_strategies.py
"""

from __future__ import annotations
import json
import os
import sys
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance required. pip install yfinance")
    sys.exit(1)

# ============================================================================
# PATHS
# ============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_FILE = DATA_DIR / "backtest_results.json"

# ============================================================================
# TECHNICAL INDICATORS (exact copy from institutional_picks_engine.py)
# ============================================================================
def sma(s, p):
    return s.rolling(p).mean()

def ema(s, p):
    return s.ewm(span=p, adjust=False).mean()

def rsi(s, p=14):
    d = s.diff()
    g = d.where(d > 0, 0.0).rolling(p).mean()
    l = (-d.where(d < 0, 0.0)).rolling(p).mean()
    rs = g / l.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def bollinger_bands(s, p=20, std=2.0):
    mid = sma(s, p)
    sd = s.rolling(p).std()
    return mid, mid + std * sd, mid - std * sd

# ============================================================================
# RISK PARAMETERS (exact copy from institutional_picks_engine.py)
# ============================================================================
RISK_PARAMS = {
    "EQUITY":      {"sl": -0.04, "tp": 0.08, "max_hold": 10},
    "PENNY_STOCK": {"sl": -0.08, "tp": 0.15, "max_hold": 5},
    "ETF":         {"sl": -0.03, "tp": 0.06, "max_hold": 15},
    "FUTURES":     {"sl": -0.03, "tp": 0.06, "max_hold": 10},
    "FOREX":       {"sl": -0.02, "tp": 0.03, "max_hold": 14},
}

# ============================================================================
# SYMBOL UNIVERSE
# ============================================================================
SYMBOLS = {
    # Penny stocks
    "SOFI":  {"class": "PENNY_STOCK", "name": "SoFi"},
    "MARA":  {"class": "PENNY_STOCK", "name": "Marathon"},
    "RIOT":  {"class": "PENNY_STOCK", "name": "Riot"},
    "IONQ":  {"class": "PENNY_STOCK", "name": "IonQ"},
    "AMC":   {"class": "PENNY_STOCK", "name": "AMC"},
    "PLTR":  {"class": "PENNY_STOCK", "name": "Palantir"},
    "NIO":   {"class": "PENNY_STOCK", "name": "NIO"},
    "HOOD":  {"class": "PENNY_STOCK", "name": "Robinhood"},
    "LCID":  {"class": "PENNY_STOCK", "name": "Lucid"},

    # Futures
    "ES=F":  {"class": "FUTURES", "name": "S&P E-mini"},
    "NQ=F":  {"class": "FUTURES", "name": "Nasdaq E-mini"},
    "YM=F":  {"class": "FUTURES", "name": "Dow E-mini"},
    "GC=F":  {"class": "FUTURES", "name": "Gold"},
    "CL=F":  {"class": "FUTURES", "name": "Crude Oil"},
    "ZN=F":  {"class": "FUTURES", "name": "10Y T-Note"},
    "HG=F":  {"class": "FUTURES", "name": "Copper"},

    # Forex
    "EURUSD=X": {"class": "FOREX", "name": "EUR/USD"},
    "GBPUSD=X": {"class": "FOREX", "name": "GBP/USD"},
    "USDJPY=X": {"class": "FOREX", "name": "USD/JPY"},
    "AUDUSD=X": {"class": "FOREX", "name": "AUD/USD"},
    "NZDUSD=X": {"class": "FOREX", "name": "NZD/USD"},
    "USDCHF=X": {"class": "FOREX", "name": "USD/CHF"},

    # Stocks/ETFs
    "SPY":   {"class": "ETF",    "name": "S&P 500"},
    "QQQ":   {"class": "ETF",    "name": "Nasdaq 100"},
    "AAPL":  {"class": "EQUITY", "name": "Apple"},
    "MSFT":  {"class": "EQUITY", "name": "Microsoft"},
    "NVDA":  {"class": "EQUITY", "name": "Nvidia"},
    "GOOGL": {"class": "EQUITY", "name": "Alphabet"},
    "JPM":   {"class": "EQUITY", "name": "JPMorgan"},
    "V":     {"class": "EQUITY", "name": "Visa"},
}

# Carry designation for forex strategy
HIGH_CARRY = ["AUDUSD=X", "NZDUSD=X", "USDJPY=X"]
LOW_CARRY = ["USDCHF=X"]

# Connors RSI per-symbol params
CONNORS_PARAMS = {
    "GC=F":  {"rsi_p": 3, "rsi_buy": 10, "sma_trend": 200},
    "SPY":   {"rsi_p": 2, "rsi_buy": 15, "sma_trend": 150},
    "ES=F":  {"rsi_p": 3, "rsi_buy": 15, "sma_trend": 150},
    "QQQ":   {"rsi_p": 2, "rsi_buy": 15, "sma_trend": 150},
    "NQ=F":  {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 150},
    "V":     {"rsi_p": 3, "rsi_buy": 15, "sma_trend": 150},
    "GOOGL": {"rsi_p": 3, "rsi_buy": 10, "sma_trend": 200},
    "JPM":   {"rsi_p": 3, "rsi_buy": 10, "sma_trend": 200},
}


# ============================================================================
# STRATEGY SCANNERS (day-by-day backtestable versions)
# Each returns (signal_direction, tp_price, sl_price) or None
# ============================================================================

def scan_penny_deep_oversold(df, i, symbol, info):
    """RSI(2)<3 AND >8% off 20d high -> LONG penny stocks."""
    if info["class"] != "PENNY_STOCK":
        return None
    if i < 50:
        return None

    close = df["Close"].iloc[:i+1]
    rsi2 = rsi(close, 2).iloc[-1]
    price = float(close.iloc[-1])

    if np.isnan(rsi2):
        return None

    high_20d = float(close.rolling(20).max().iloc[-1])
    pct_off_high = 1 - (price / high_20d) if high_20d > 0 else 0

    if rsi2 < 3 and pct_off_high > 0.08:
        params = RISK_PARAMS["PENNY_STOCK"]
        tp = price * (1 + abs(params["tp"]))
        sl = price * (1 + params["sl"])  # sl is negative
        return ("LONG", tp, sl)
    return None


def scan_futures_mean_reversion(df, i, symbol, info):
    """BB(15,2.5) + RSI(3)<20 -> LONG / RSI(3)>80 -> SHORT futures."""
    if info["class"] != "FUTURES":
        return None
    if i < 50:
        return None

    close = df["Close"].iloc[:i+1]
    rsi_val = rsi(close, 3).iloc[-1]
    price = float(close.iloc[-1])
    mid, upper, lower = bollinger_bands(close, 15, 2.5)
    mid_v = float(mid.iloc[-1])
    lower_v = float(lower.iloc[-1])
    upper_v = float(upper.iloc[-1])

    if any(np.isnan([rsi_val, mid_v, lower_v, upper_v])):
        return None

    params = RISK_PARAMS["FUTURES"]

    # LONG signal
    if price < lower_v * 1.02 and rsi_val < 20:
        tp = mid_v  # Target mid band
        sl = price * (1 + params["sl"])
        return ("LONG", tp, sl)

    # SHORT signal
    if price > upper_v * 0.98 and rsi_val > 80:
        tp = mid_v  # Target mid band
        sl = price * (1 - params["sl"])  # sl for short is above entry
        return ("SHORT", tp, sl)

    return None


def scan_forex_carry_momentum(df, i, symbol, info):
    """Carry + EMA20/50 momentum + RSI extremes for forex."""
    if info["class"] != "FOREX":
        return None
    if i < 100:
        return None

    close = df["Close"].iloc[:i+1]
    price = float(close.iloc[-1])
    ema20 = float(ema(close, 20).iloc[-1])
    ema50 = float(ema(close, 50).iloc[-1])
    rsi_val = float(rsi(close, 14).iloc[-1])

    if any(np.isnan([price, ema20, ema50, rsi_val])):
        return None

    params = RISK_PARAMS["FOREX"]

    # LONG high-carry pairs with momentum
    if symbol in HIGH_CARRY and ema20 > ema50 and 40 < rsi_val < 70:
        tp = price * (1 + abs(params["tp"]))
        sl = price * (1 + params["sl"])
        return ("LONG", tp, sl)

    # SHORT low-carry pairs with momentum
    if symbol in LOW_CARRY and ema20 < ema50 and 30 < rsi_val < 60:
        tp = price * (1 - abs(params["tp"]))
        sl = price * (1 - params["sl"])
        return ("SHORT", tp, sl)

    # Mean reversion: RSI(2) extreme oversold
    rsi2 = float(rsi(close, 2).iloc[-1])
    if not np.isnan(rsi2) and rsi2 < 5:
        tp = price * (1 + abs(params["tp"]))
        sl = price * (1 + params["sl"])
        return ("LONG", tp, sl)

    return None


def scan_extreme_oversold_bounce(df, i, symbol, info):
    """RSI(2)<5 AND below BB(20,2) -> LONG any symbol."""
    if i < 50:
        return None

    close = df["Close"].iloc[:i+1]
    rsi2 = rsi(close, 2).iloc[-1]
    price = float(close.iloc[-1])
    mid, _, lower = bollinger_bands(close, 20, 2.0)
    lower_v = float(lower.iloc[-1])
    mid_v = float(mid.iloc[-1])

    if any(np.isnan([rsi2, price, lower_v, mid_v])):
        return None

    if rsi2 < 5 and price < lower_v * 1.01:
        ac = info["class"]
        params = RISK_PARAMS.get(ac, RISK_PARAMS["EQUITY"])
        tp = min(price * (1 + abs(params["tp"])), mid_v)  # Tight TP
        sl = price * (1 + params["sl"])
        return ("LONG", tp, sl)

    return None


def scan_hyperopt_connors_rsi2(df, i, symbol, info):
    """Per-symbol tuned Connors RSI LONG/SHORT."""
    p = CONNORS_PARAMS.get(symbol)
    if not p:
        return None
    if i < 200:
        return None

    close = df["Close"].iloc[:i+1]
    rsi_val = float(rsi(close, p["rsi_p"]).iloc[-1])
    trend = float(sma(close, p["sma_trend"]).iloc[-1])
    price = float(close.iloc[-1])

    if any(np.isnan([rsi_val, price, trend])):
        return None

    ac = info["class"]
    params = RISK_PARAMS.get(ac, RISK_PARAMS["EQUITY"])

    # LONG signal
    if rsi_val < p["rsi_buy"] and price > trend:
        tp = price * (1 + abs(params["tp"]))
        sl = price * (1 + params["sl"])
        return ("LONG", tp, sl)

    # SHORT signal
    rsi_sell = 90 - (p["rsi_buy"] - 10) * 2
    if rsi_val > rsi_sell and price < trend:
        tp = price * (1 - abs(params["tp"]))
        sl = price * (1 - params["sl"])
        return ("SHORT", tp, sl)

    return None


# ============================================================================
# STRATEGY REGISTRY
# ============================================================================
STRATEGIES = {
    "penny_deep_oversold":    scan_penny_deep_oversold,
    "futures_mean_reversion": scan_futures_mean_reversion,
    "forex_carry_momentum":   scan_forex_carry_momentum,
    "extreme_oversold_bounce": scan_extreme_oversold_bounce,
    "hyperopt_connors_rsi2":  scan_hyperopt_connors_rsi2,
}


# ============================================================================
# TRADE SIMULATOR
# ============================================================================
def simulate_trade(df, entry_idx, direction, tp, sl, max_hold):
    """
    Simulate a trade from entry_idx forward.
    Returns (exit_idx, exit_price, pnl_pct, exit_reason).
    """
    entry_price = float(df["Close"].iloc[entry_idx])
    end_idx = min(entry_idx + max_hold, len(df) - 1)

    for j in range(entry_idx + 1, end_idx + 1):
        high = float(df["High"].iloc[j])
        low = float(df["Low"].iloc[j])
        close_j = float(df["Close"].iloc[j])

        if direction == "LONG":
            # Check SL first (worst case)
            if low <= sl:
                pnl = (sl - entry_price) / entry_price * 100
                return (j, sl, pnl, "SL_HIT")
            # Check TP
            if high >= tp:
                pnl = (tp - entry_price) / entry_price * 100
                return (j, tp, pnl, "TP_HIT")
        else:  # SHORT
            # Check SL first (price goes up)
            if high >= sl:
                pnl = (entry_price - sl) / entry_price * 100
                return (j, sl, pnl, "SL_HIT")
            # Check TP (price goes down)
            if low <= tp:
                pnl = (entry_price - tp) / entry_price * 100
                return (j, tp, pnl, "TP_HIT")

    # Max hold expiry
    exit_price = float(df["Close"].iloc[end_idx])
    if direction == "LONG":
        pnl = (exit_price - entry_price) / entry_price * 100
    else:
        pnl = (entry_price - exit_price) / entry_price * 100
    return (end_idx, exit_price, pnl, "MAX_HOLD")


# ============================================================================
# BACKTEST ENGINE
# ============================================================================
def backtest_strategy(strat_name, strat_fn, all_data, symbols_info):
    """Run a strategy across all applicable symbols, day by day."""
    trades = []
    cooldown = {}  # (strat, symbol) -> cooldown until idx

    for sym, df in all_data.items():
        info = symbols_info[sym]
        ac = info["class"]
        params = RISK_PARAMS.get(ac, RISK_PARAMS["EQUITY"])

        for i in range(50, len(df) - 1):  # Need at least 1 day forward
            # Cooldown: don't re-enter same symbol within max_hold days
            key = (strat_name, sym)
            if key in cooldown and i < cooldown[key]:
                continue

            signal = strat_fn(df, i, sym, info)
            if signal is None:
                continue

            direction, tp, sl = signal
            entry_price = float(df["Close"].iloc[i])
            entry_date = str(df.index[i].date()) if hasattr(df.index[i], 'date') else str(df.index[i])

            exit_idx, exit_price, pnl, exit_reason = simulate_trade(
                df, i, direction, tp, sl, params["max_hold"]
            )

            exit_date = str(df.index[exit_idx].date()) if hasattr(df.index[exit_idx], 'date') else str(df.index[exit_idx])

            trades.append({
                "strategy": strat_name,
                "symbol": sym,
                "asset_class": ac,
                "direction": direction,
                "entry_date": entry_date,
                "exit_date": exit_date,
                "entry_price": round(entry_price, 4),
                "exit_price": round(exit_price, 4),
                "tp": round(tp, 4),
                "sl": round(sl, 4),
                "pnl_pct": round(pnl, 4),
                "exit_reason": exit_reason,
                "hold_days": exit_idx - i,
            })

            # Set cooldown
            cooldown[key] = exit_idx + 1

    return trades


# ============================================================================
# STATISTICAL ANALYSIS
# ============================================================================
def analyze_trades(trades, label="Overall"):
    """Compute comprehensive statistics for a list of trades."""
    if not trades:
        return {
            "label": label, "total_trades": 0, "win_rate": 0,
            "avg_pnl": 0, "sharpe": 0, "profit_factor": 0,
            "max_drawdown": 0, "t_stat": 0, "p_value": 1.0,
            "avg_hold_days": 0, "tp_rate": 0, "sl_rate": 0, "expire_rate": 0,
        }

    pnls = [t["pnl_pct"] for t in trades]
    n = len(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    win_rate = len(wins) / n * 100 if n > 0 else 0
    avg_pnl = np.mean(pnls)
    std_pnl = np.std(pnls, ddof=1) if n > 1 else 1
    sharpe = (avg_pnl / std_pnl) * np.sqrt(252 / max(1, np.mean([t["hold_days"] for t in trades]))) if std_pnl > 0 else 0

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.001
    profit_factor = gross_profit / gross_loss

    # Max drawdown (cumulative PnL)
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    dd = cum - peak
    max_dd = float(np.min(dd)) if len(dd) > 0 else 0

    # T-test: is mean PnL significantly > 0?
    if n >= 2:
        t_stat, p_val = stats.ttest_1samp(pnls, 0)
        # One-tailed: we want mean > 0
        p_val_one = p_val / 2 if t_stat > 0 else 1 - p_val / 2
    else:
        t_stat, p_val_one = 0, 1.0

    # Exit reason breakdown
    tp_hits = sum(1 for t in trades if t["exit_reason"] == "TP_HIT")
    sl_hits = sum(1 for t in trades if t["exit_reason"] == "SL_HIT")
    expires = sum(1 for t in trades if t["exit_reason"] == "MAX_HOLD")

    return {
        "label": label,
        "total_trades": n,
        "win_rate": round(win_rate, 2),
        "avg_pnl": round(avg_pnl, 4),
        "median_pnl": round(float(np.median(pnls)), 4),
        "std_pnl": round(std_pnl, 4),
        "sharpe": round(sharpe, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_dd, 2),
        "total_return": round(sum(pnls), 2),
        "avg_win": round(np.mean(wins), 4) if wins else 0,
        "avg_loss": round(np.mean(losses), 4) if losses else 0,
        "best_trade": round(max(pnls), 4),
        "worst_trade": round(min(pnls), 4),
        "avg_hold_days": round(np.mean([t["hold_days"] for t in trades]), 1),
        "tp_rate": round(tp_hits / n * 100, 1),
        "sl_rate": round(sl_hits / n * 100, 1),
        "expire_rate": round(expires / n * 100, 1),
        "t_stat": round(t_stat, 3),
        "p_value": round(p_val_one, 6),
        "significant_at_005": p_val_one < 0.05,
        "significant_at_001": p_val_one < 0.01,
    }


def monte_carlo_simulation(pnls, n_picks=1000, n_simulations=10000):
    """Monte Carlo: sample from observed PnL distribution, simulate n_picks."""
    if len(pnls) < 5:
        return {"mean": 0, "ci_95_low": 0, "ci_95_high": 0, "prob_positive": 0, "prob_loss_gt_10": 0}

    pnl_arr = np.array(pnls)
    # Bootstrap: sample with replacement
    sims = np.random.choice(pnl_arr, size=(n_simulations, n_picks), replace=True)
    total_returns = sims.sum(axis=1)

    mean_ret = float(np.mean(total_returns))
    ci_low = float(np.percentile(total_returns, 2.5))
    ci_high = float(np.percentile(total_returns, 97.5))
    prob_positive = float(np.mean(total_returns > 0))
    prob_loss_gt_10 = float(np.mean(total_returns < -10 * n_picks * 0.01))

    return {
        "n_picks": n_picks,
        "n_simulations": n_simulations,
        "mean_total_return_pct": round(mean_ret, 2),
        "ci_95_low": round(ci_low, 2),
        "ci_95_high": round(ci_high, 2),
        "prob_positive": round(prob_positive * 100, 2),
        "median_total_return": round(float(np.median(total_returns)), 2),
    }


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("=" * 72)
    print("  INSTITUTIONAL PICKS ENGINE - COMPREHENSIVE BACKTEST")
    print("  Testing 5 strategies across 30 symbols over 2 years")
    print("=" * 72)
    start_time = time.time()

    # ---- Fetch data ----
    all_symbols = list(SYMBOLS.keys())
    print(f"\n[1/4] Fetching 2Y daily data for {len(all_symbols)} symbols...")

    try:
        raw = yf.download(all_symbols, period="2y", interval="1d",
                          group_by="ticker", progress=True, threads=True)
    except Exception as e:
        print(f"  FATAL: {e}")
        sys.exit(1)

    all_data = {}
    for sym in all_symbols:
        try:
            if len(all_symbols) == 1:
                df = raw.dropna()
            else:
                df = raw[sym].dropna()
            # Flatten multi-index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if len(df) > 50:
                all_data[sym] = df
                print(f"    {sym:12s} -> {len(df)} bars")
        except Exception as e:
            print(f"    {sym:12s} -> FAILED: {e}")

    print(f"  Loaded {len(all_data)}/{len(all_symbols)} symbols successfully")

    if len(all_data) < 5:
        print("FATAL: Not enough data. Exiting.")
        sys.exit(1)

    # ---- Run backtests ----
    print(f"\n[2/4] Running backtests on {len(STRATEGIES)} strategies...")
    all_trades = []
    strategy_results = {}

    for strat_name, strat_fn in STRATEGIES.items():
        print(f"\n  --- {strat_name} ---")
        t0 = time.time()
        trades = backtest_strategy(strat_name, strat_fn, all_data, SYMBOLS)
        elapsed = time.time() - t0
        print(f"    {len(trades)} trades found ({elapsed:.1f}s)")

        # Analyze
        result = analyze_trades(trades, label=strat_name)
        strategy_results[strat_name] = result
        all_trades.extend(trades)

        # Print summary
        if trades:
            print(f"    WR={result['win_rate']:.1f}% | Avg PnL={result['avg_pnl']:+.3f}% | "
                  f"Sharpe={result['sharpe']:.2f} | PF={result['profit_factor']:.2f} | "
                  f"MaxDD={result['max_drawdown']:.1f}% | p={result['p_value']:.4f}")
            print(f"    TP={result['tp_rate']:.0f}% | SL={result['sl_rate']:.0f}% | "
                  f"Expire={result['expire_rate']:.0f}% | "
                  f"Avg hold={result['avg_hold_days']:.1f}d")

    # ---- Per-asset-class analysis ----
    print(f"\n[3/4] Analyzing by asset class...")
    asset_class_results = {}
    for ac in ["PENNY_STOCK", "FUTURES", "FOREX", "ETF", "EQUITY"]:
        ac_trades = [t for t in all_trades if t["asset_class"] == ac]
        if ac_trades:
            result = analyze_trades(ac_trades, label=ac)
            asset_class_results[ac] = result
            print(f"  {ac:15s} | {result['total_trades']:4d} trades | "
                  f"WR={result['win_rate']:.1f}% | Avg={result['avg_pnl']:+.3f}% | "
                  f"Sharpe={result['sharpe']:.2f} | PF={result['profit_factor']:.2f} | "
                  f"p={result['p_value']:.4f}")

    # ---- Overall analysis ----
    print(f"\n[4/4] Overall analysis + Monte Carlo simulation...")
    overall = analyze_trades(all_trades, label="OVERALL")

    # Monte Carlo
    all_pnls = [t["pnl_pct"] for t in all_trades]
    mc_1000 = monte_carlo_simulation(all_pnls, n_picks=1000, n_simulations=10000)
    mc_5000 = monte_carlo_simulation(all_pnls, n_picks=5000, n_simulations=10000)

    # ---- Print comprehensive report ----
    print("\n" + "=" * 72)
    print("  COMPREHENSIVE BACKTEST REPORT")
    print("=" * 72)

    print(f"\n  Period:          ~2 years of daily data")
    print(f"  Symbols tested:  {len(all_data)}")
    print(f"  Strategies:      {len(STRATEGIES)}")
    print(f"  Total trades:    {overall['total_trades']}")
    print(f"  Total return:    {overall['total_return']:+.2f}% (sum of all trade PnLs)")

    print(f"\n  --- PER-STRATEGY BREAKDOWN ---")
    print(f"  {'Strategy':<28s} {'Trades':>6s} {'WR%':>7s} {'AvgPnL':>8s} {'Sharpe':>7s} {'PF':>6s} {'MaxDD':>7s} {'p-val':>8s} {'Sig?':>5s}")
    print(f"  {'-'*88}")
    for name, r in strategy_results.items():
        sig = "***" if r["significant_at_001"] else ("**" if r["significant_at_005"] else "")
        print(f"  {name:<28s} {r['total_trades']:>6d} {r['win_rate']:>6.1f}% {r['avg_pnl']:>+7.3f}% "
              f"{r['sharpe']:>7.2f} {r['profit_factor']:>6.2f} {r['max_drawdown']:>6.1f}% "
              f"{r['p_value']:>8.4f} {sig:>5s}")

    print(f"\n  --- PER-ASSET-CLASS BREAKDOWN ---")
    print(f"  {'Class':<15s} {'Trades':>6s} {'WR%':>7s} {'AvgPnL':>8s} {'Sharpe':>7s} {'PF':>6s} {'MaxDD':>7s} {'p-val':>8s}")
    print(f"  {'-'*72}")
    for ac, r in asset_class_results.items():
        print(f"  {ac:<15s} {r['total_trades']:>6d} {r['win_rate']:>6.1f}% {r['avg_pnl']:>+7.3f}% "
              f"{r['sharpe']:>7.2f} {r['profit_factor']:>6.2f} {r['max_drawdown']:>6.1f}% "
              f"{r['p_value']:>8.4f}")

    print(f"\n  --- OVERALL STATISTICS ---")
    print(f"  Total trades:        {overall['total_trades']}")
    print(f"  Win rate:            {overall['win_rate']:.1f}%")
    print(f"  Average PnL:         {overall['avg_pnl']:+.4f}%")
    print(f"  Median PnL:          {overall['median_pnl']:+.4f}%")
    print(f"  Std PnL:             {overall['std_pnl']:.4f}%")
    print(f"  Sharpe ratio:        {overall['sharpe']:.2f}")
    print(f"  Profit factor:       {overall['profit_factor']:.2f}")
    print(f"  Max drawdown:        {overall['max_drawdown']:.2f}%")
    print(f"  Best trade:          {overall['best_trade']:+.2f}%")
    print(f"  Worst trade:         {overall['worst_trade']:+.2f}%")
    print(f"  Avg hold days:       {overall['avg_hold_days']:.1f}")
    print(f"  TP hit rate:         {overall['tp_rate']:.1f}%")
    print(f"  SL hit rate:         {overall['sl_rate']:.1f}%")
    print(f"  Max hold expiry:     {overall['expire_rate']:.1f}%")
    print(f"  t-statistic:         {overall['t_stat']:.3f}")
    print(f"  p-value (one-tail):  {overall['p_value']:.6f}")
    print(f"  Significant (5%):    {'YES' if overall['significant_at_005'] else 'NO'}")
    print(f"  Significant (1%):    {'YES' if overall['significant_at_001'] else 'NO'}")

    print(f"\n  --- MONTE CARLO SIMULATION ---")
    print(f"  Simulating 1,000 picks (10,000 iterations):")
    print(f"    Mean total return:   {mc_1000['mean_total_return_pct']:+.2f}%")
    print(f"    95% CI:              [{mc_1000['ci_95_low']:+.2f}%, {mc_1000['ci_95_high']:+.2f}%]")
    print(f"    Prob(positive):      {mc_1000['prob_positive']:.1f}%")
    print(f"    Median return:       {mc_1000['median_total_return']:+.2f}%")

    print(f"\n  Simulating 5,000 picks (10,000 iterations):")
    print(f"    Mean total return:   {mc_5000['mean_total_return_pct']:+.2f}%")
    print(f"    95% CI:              [{mc_5000['ci_95_low']:+.2f}%, {mc_5000['ci_95_high']:+.2f}%]")
    print(f"    Prob(positive):      {mc_5000['prob_positive']:.1f}%")
    print(f"    Median return:       {mc_5000['median_total_return']:+.2f}%")

    # ---- Sustainability verdict ----
    print(f"\n  --- SUSTAINABILITY VERDICT ---")
    can_sustain = (
        overall["avg_pnl"] > 0 and
        overall["profit_factor"] > 1.0 and
        mc_1000["prob_positive"] > 80
    )
    if can_sustain:
        print(f"  VERDICT: YES - These strategies can sustain positive PnL over 1000s of picks")
        print(f"    - Average PnL per trade is positive ({overall['avg_pnl']:+.4f}%)")
        print(f"    - Profit factor > 1 ({overall['profit_factor']:.2f})")
        print(f"    - Monte Carlo shows {mc_1000['prob_positive']:.1f}% probability of profit over 1000 picks")
    else:
        issues = []
        if overall["avg_pnl"] <= 0:
            issues.append(f"Negative avg PnL ({overall['avg_pnl']:+.4f}%)")
        if overall["profit_factor"] <= 1.0:
            issues.append(f"Profit factor <= 1 ({overall['profit_factor']:.2f})")
        if mc_1000["prob_positive"] <= 80:
            issues.append(f"MC prob positive only {mc_1000['prob_positive']:.1f}%")
        print(f"  VERDICT: CAUTION - Issues found:")
        for issue in issues:
            print(f"    - {issue}")

        # Per-strategy verdict
        print(f"\n  Per-strategy sustainability:")
        for name, r in strategy_results.items():
            ok = r["avg_pnl"] > 0 and r["profit_factor"] > 1.0
            status = "PASS" if ok else "FAIL"
            print(f"    {name:<28s} -> {status} (avg={r['avg_pnl']:+.4f}%, PF={r['profit_factor']:.2f})")

    # ---- Save results ----
    elapsed_total = time.time() - start_time
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "elapsed_seconds": round(elapsed_total, 1),
        "symbols_tested": len(all_data),
        "total_trades": overall["total_trades"],
        "overall": overall,
        "per_strategy": strategy_results,
        "per_asset_class": asset_class_results,
        "monte_carlo_1000": mc_1000,
        "monte_carlo_5000": mc_5000,
        "can_sustain_positive_pnl": can_sustain,
        "top_10_trades": sorted(all_trades, key=lambda x: -x["pnl_pct"])[:10],
        "worst_10_trades": sorted(all_trades, key=lambda x: x["pnl_pct"])[:10],
    }

    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to: {RESULTS_FILE}")
    print(f"  Total time: {elapsed_total:.1f}s")
    print("=" * 72)


if __name__ == "__main__":
    main()
