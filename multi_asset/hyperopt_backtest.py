#!/usr/bin/env python3
"""
HYPERPARAMETER OPTIMIZATION ENGINE v1.0
=========================================
Exhaustive parameter sweep across all strategies x asset classes.
Finds optimal TP/SL, indicator periods, and entry thresholds per symbol/class.

Usage:
  python multi_asset/hyperopt_backtest.py                     # Full sweep
  python multi_asset/hyperopt_backtest.py --symbol AAPL       # Single symbol
  python multi_asset/hyperopt_backtest.py --asset-class etf   # Single class
  python multi_asset/hyperopt_backtest.py --quick             # Reduced grid

Output: multi_asset/data/hyperopt_results.json
"""

from __future__ import annotations

import argparse
import json
import itertools
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance required. pip install yfinance")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RESULTS_FILE = DATA_DIR / "hyperopt_results.json"
WINNER_FILE = DATA_DIR / "optimal_params.json"

# ---------------------------------------------------------------------------
# Symbol universes
# ---------------------------------------------------------------------------
UNIVERSES = {
    "futures": {
        "ES=F": "S&P 500 E-mini", "NQ=F": "Nasdaq 100 E-mini",
        "YM=F": "Dow E-mini", "CL=F": "Crude Oil WTI",
        "GC=F": "Gold", "SI=F": "Silver", "ZN=F": "10-Year T-Note",
    },
    "stock": {
        "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia",
        "GOOGL": "Alphabet", "AMZN": "Amazon", "META": "Meta",
        "TSLA": "Tesla", "JPM": "JPMorgan", "V": "Visa",
    },
    "forex": {
        "EURUSD=X": "EUR/USD", "USDJPY=X": "USD/JPY",
        "GBPUSD=X": "GBP/USD", "AUDUSD=X": "AUD/USD",
        "NZDUSD=X": "NZD/USD",
    },
    "etf": {
        "SPY": "S&P 500 ETF", "QQQ": "Nasdaq 100 ETF",
        "XLK": "Technology", "XLF": "Financial", "XLE": "Energy",
        "GLD": "Gold ETF", "TLT": "20+ Year Treasury", "IWM": "Russell 2000",
    },
    "penny": {
        "SOFI": "SoFi", "NIO": "NIO", "PLTR": "Palantir",
        "MARA": "Marathon", "RIOT": "Riot", "IONQ": "IonQ",
    },
}

# ---------------------------------------------------------------------------
# Technical Indicators
# ---------------------------------------------------------------------------
def sma(s, p):
    return s.rolling(p).mean()

def ema(s, p):
    return s.ewm(span=p, adjust=False).mean()

def rsi(s, p=14):
    delta = s.diff()
    gain = delta.where(delta > 0, 0.0).rolling(p).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(p).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(h, l, c, p=14):
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(p).mean()

def bollinger_bands(s, p=20, std=2.0):
    mid = sma(s, p)
    sd = s.rolling(p).std()
    return mid, mid + std * sd, mid - std * sd

def macd(s, fast=12, slow=26, sig=9):
    ml = ema(s, fast) - ema(s, slow)
    sl = ema(ml, sig)
    return ml, sl, ml - sl

def adx_calc(h, l, c, p=14):
    plus_dm = h.diff()
    minus_dm = -l.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr_val = atr(h, l, c, p)
    plus_di = 100 * ema(plus_dm, p) / atr_val.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, p) / atr_val.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return ema(dx, p)


# ---------------------------------------------------------------------------
# Parameterized Strategy Signal Generators
# ---------------------------------------------------------------------------

def gen_connors_rsi2(df, params):
    """Connors RSI-2 with parameterized thresholds."""
    signals = []
    rsi_period = params.get("rsi_period", 2)
    sma_trend = params.get("sma_trend", 200)
    rsi_buy = params.get("rsi_buy_threshold", 10)
    rsi_sell = params.get("rsi_sell_threshold", 90)

    if len(df) < max(sma_trend, 50):
        return signals

    close = df["Close"]
    rsi_vals = rsi(close, rsi_period)
    sma_vals = sma(close, sma_trend)

    for i in range(sma_trend, len(df)):
        r = float(rsi_vals.iloc[i])
        p = float(close.iloc[i])
        s = float(sma_vals.iloc[i])
        if not all(np.isfinite([r, p, s])):
            continue
        if r < rsi_buy and p > s:
            signals.append({"idx": i, "dir": "LONG", "price": p})
        elif r > rsi_sell and p < s:
            signals.append({"idx": i, "dir": "SHORT", "price": p})
    return signals


def gen_bollinger_mr(df, params):
    """Bollinger mean reversion with parameterized BB and RSI."""
    signals = []
    bb_period = params.get("bb_period", 20)
    bb_std = params.get("bb_std", 2.0)
    rsi_period = params.get("rsi_period", 14)
    rsi_buy = params.get("rsi_buy_threshold", 30)
    rsi_sell = params.get("rsi_sell_threshold", 70)

    if len(df) < max(bb_period, rsi_period) + 10:
        return signals

    close = df["Close"]
    rsi_vals = rsi(close, rsi_period)
    mid, upper, lower = bollinger_bands(close, bb_period, bb_std)

    start = max(bb_period, rsi_period) + 5
    for i in range(start, len(df)):
        p = float(close.iloc[i])
        r = float(rsi_vals.iloc[i])
        lo = float(lower.iloc[i])
        up = float(upper.iloc[i])
        if not all(np.isfinite([p, r, lo, up])):
            continue
        if p < lo and r < rsi_buy:
            signals.append({"idx": i, "dir": "LONG", "price": p})
        elif p > up and r > rsi_sell:
            signals.append({"idx": i, "dir": "SHORT", "price": p})
    return signals


def gen_ema_stack(df, params):
    """EMA stack momentum with parameterized EMAs and ADX."""
    signals = []
    e_fast = params.get("ema_fast", 9)
    e_mid = params.get("ema_mid", 21)
    e_slow = params.get("ema_slow", 50)
    e_trend = params.get("ema_trend", 200)
    adx_thresh = params.get("adx_threshold", 25)

    if len(df) < e_trend + 10:
        return signals

    close = df["Close"]
    ef = ema(close, e_fast)
    em = ema(close, e_mid)
    es = ema(close, e_slow)
    et = ema(close, e_trend)
    ax = adx_calc(df["High"], df["Low"], close, 14)

    for i in range(e_trend + 5, len(df)):
        vals = [float(ef.iloc[i]), float(em.iloc[i]), float(es.iloc[i]),
                float(et.iloc[i]), float(ax.iloc[i]), float(close.iloc[i])]
        if not all(np.isfinite(vals)):
            continue
        ef_v, em_v, es_v, et_v, ax_v, price = vals
        if ef_v > em_v > es_v > et_v and ax_v > adx_thresh:
            signals.append({"idx": i, "dir": "LONG", "price": price})
        elif ef_v < em_v < es_v < et_v and ax_v > adx_thresh:
            signals.append({"idx": i, "dir": "SHORT", "price": price})
    return signals


def gen_macd_div(df, params):
    """MACD divergence with parameterized MACD."""
    signals = []
    fast = params.get("macd_fast", 12)
    slow = params.get("macd_slow", 26)
    sig = params.get("macd_signal", 9)
    lookback = params.get("div_lookback", 10)

    if len(df) < slow + lookback + 10:
        return signals

    close = df["Close"]
    ml, sl, hist = macd(close, fast, slow, sig)

    start = slow + lookback + 5
    for i in range(start, len(df)):
        p = float(close.iloc[i])
        h = float(hist.iloc[i])
        h_prev = float(hist.iloc[i - lookback])
        p_low = float(close.iloc[i-lookback:i].min())
        p_prev_low = float(close.iloc[max(0,i-2*lookback):i-lookback].min())
        if not all(np.isfinite([p, h, h_prev, p_low, p_prev_low])):
            continue
        # Bullish: price lower low, MACD higher low
        if p_low < p_prev_low and h > h_prev and h < 0:
            signals.append({"idx": i, "dir": "LONG", "price": p})
    return signals


STRATEGY_GENERATORS = {
    "connors_rsi2": gen_connors_rsi2,
    "bollinger_mr": gen_bollinger_mr,
    "ema_stack": gen_ema_stack,
    "macd_div": gen_macd_div,
}

# ---------------------------------------------------------------------------
# Parameter grids
# ---------------------------------------------------------------------------

PARAM_GRIDS = {
    "connors_rsi2": {
        "rsi_period": [2, 3, 5],
        "sma_trend": [100, 150, 200],
        "rsi_buy_threshold": [5, 10, 15, 20],
        "rsi_sell_threshold": [80, 85, 90, 95],
    },
    "bollinger_mr": {
        "bb_period": [15, 20, 30],
        "bb_std": [1.5, 2.0, 2.5],
        "rsi_period": [10, 14, 20],
        "rsi_buy_threshold": [20, 25, 30, 35],
        "rsi_sell_threshold": [65, 70, 75, 80],
    },
    "ema_stack": {
        "ema_fast": [5, 8, 9, 12],
        "ema_mid": [15, 21, 25],
        "ema_slow": [40, 50, 65],
        "ema_trend": [150, 200],
        "adx_threshold": [20, 25, 30],
    },
    "macd_div": {
        "macd_fast": [8, 12, 16],
        "macd_slow": [20, 26, 32],
        "macd_signal": [7, 9, 12],
        "div_lookback": [5, 10, 15],
    },
}

PARAM_GRIDS_QUICK = {
    "connors_rsi2": {
        "rsi_period": [2, 3],
        "sma_trend": [150, 200],
        "rsi_buy_threshold": [10, 15],
        "rsi_sell_threshold": [85, 90],
    },
    "bollinger_mr": {
        "bb_period": [20],
        "bb_std": [1.5, 2.0, 2.5],
        "rsi_period": [14],
        "rsi_buy_threshold": [25, 30],
        "rsi_sell_threshold": [70, 75],
    },
    "ema_stack": {
        "ema_fast": [8, 9],
        "ema_mid": [21],
        "ema_slow": [50],
        "ema_trend": [200],
        "adx_threshold": [20, 25],
    },
    "macd_div": {
        "macd_fast": [12],
        "macd_slow": [26],
        "macd_signal": [9],
        "div_lookback": [5, 10],
    },
}

# TP/SL grid to sweep
TPSL_GRID = {
    "futures": {"sl": [-0.02, -0.03, -0.04, -0.06], "tp": [0.04, 0.06, 0.08, 0.10]},
    "stock":   {"sl": [-0.03, -0.05, -0.06, -0.08], "tp": [0.06, 0.08, 0.10, 0.12, 0.15]},
    "forex":   {"sl": [-0.01, -0.015, -0.02, -0.025], "tp": [0.015, 0.02, 0.025, 0.03, 0.04]},
    "etf":     {"sl": [-0.03, -0.04, -0.05, -0.07], "tp": [0.05, 0.08, 0.10, 0.12]},
    "penny":   {"sl": [-0.08, -0.10, -0.12, -0.15], "tp": [0.15, 0.20, 0.25, 0.30]},
}

TPSL_GRID_QUICK = {
    "futures": {"sl": [-0.03, -0.04], "tp": [0.06, 0.08]},
    "stock":   {"sl": [-0.05, -0.06], "tp": [0.08, 0.12]},
    "forex":   {"sl": [-0.02, -0.025], "tp": [0.025, 0.03]},
    "etf":     {"sl": [-0.04, -0.05], "tp": [0.08, 0.10]},
    "penny":   {"sl": [-0.10, -0.12], "tp": [0.20, 0.25]},
}

MAX_HOLD_DAYS = {"futures": 10, "stock": 10, "forex": 14, "etf": 15, "penny": 5}


# ---------------------------------------------------------------------------
# Walk-forward backtester
# ---------------------------------------------------------------------------

def backtest_signals(df, signals, sl_pct, tp_pct, max_hold, step=2):
    """Simulate trades from signal list with given TP/SL."""
    trades = []
    in_trade = False
    entry_idx = 0
    entry_price = 0
    direction = ""

    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values

    for sig in signals:
        idx = sig["idx"]
        if in_trade:
            continue  # skip if already in a trade

        entry_price = sig["price"]
        direction = sig["dir"]
        entry_idx = idx
        in_trade = True

        # Simulate forward from entry
        for j in range(idx + 1, min(idx + max_hold + 1, len(df))):
            if direction == "LONG":
                # Check SL first
                if low[j] <= entry_price * (1 + sl_pct):
                    exit_price = entry_price * (1 + sl_pct)
                    pnl = sl_pct
                    trades.append({"entry": entry_price, "exit": exit_price, "pnl": pnl, "reason": "SL", "bars": j - idx})
                    in_trade = False
                    break
                # Check TP
                if high[j] >= entry_price * (1 + tp_pct):
                    exit_price = entry_price * (1 + tp_pct)
                    pnl = tp_pct
                    trades.append({"entry": entry_price, "exit": exit_price, "pnl": pnl, "reason": "TP", "bars": j - idx})
                    in_trade = False
                    break
            else:  # SHORT
                if high[j] >= entry_price * (1 - sl_pct):
                    exit_price = entry_price * (1 - sl_pct)
                    pnl = sl_pct  # sl_pct is negative
                    trades.append({"entry": entry_price, "exit": exit_price, "pnl": pnl, "reason": "SL", "bars": j - idx})
                    in_trade = False
                    break
                if low[j] <= entry_price * (1 - tp_pct):
                    exit_price = entry_price * (1 - tp_pct)
                    pnl = tp_pct
                    trades.append({"entry": entry_price, "exit": exit_price, "pnl": pnl, "reason": "TP", "bars": j - idx})
                    in_trade = False
                    break
        else:
            # Max hold time expired — close at current price
            if in_trade and entry_idx + max_hold < len(df):
                last_idx = min(entry_idx + max_hold, len(df) - 1)
                exit_price = float(close[last_idx])
                if direction == "LONG":
                    pnl = (exit_price - entry_price) / entry_price
                else:
                    pnl = (entry_price - exit_price) / entry_price
                trades.append({"entry": entry_price, "exit": exit_price, "pnl": pnl, "reason": "EXPIRY", "bars": last_idx - entry_idx})
                in_trade = False

    return trades


def calc_metrics(trades):
    """Calculate comprehensive metrics from trade list."""
    if len(trades) == 0:
        return None

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    bars = [t["bars"] for t in trades]

    n = len(pnls)
    wr = len(wins) / n if n > 0 else 0
    mean_pnl = np.mean(pnls)
    std_pnl = np.std(pnls) if n > 1 else 1.0

    # Sharpe
    sharpe = float((mean_pnl / std_pnl) * np.sqrt(252)) if std_pnl > 0 else 0

    # Sortino
    down_pnls = [p for p in pnls if p < 0]
    down_std = np.sqrt(np.mean([p**2 for p in down_pnls])) if len(down_pnls) > 0 else 1.0
    sortino = float((mean_pnl / down_std) * np.sqrt(252)) if down_std > 0 else 0

    # Profit factor
    gross_w = sum(wins) if wins else 0
    gross_l = abs(sum(losses)) if losses else 0
    pf = gross_w / gross_l if gross_l > 0 else (99 if gross_w > 0 else 0)

    # Expectancy
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0
    expectancy = (wr * avg_win) + ((1 - wr) * avg_loss)

    # Max drawdown
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    dd = cum - peak
    max_dd = float(np.min(dd)) if len(dd) > 0 else 0

    # Calmar
    total_ret = float(np.sum(pnls))
    calmar = total_ret / abs(max_dd) if abs(max_dd) > 0.001 else 0

    # Avg hold time
    avg_bars = np.mean(bars) if bars else 0

    # Composite fitness (for ranking)
    fitness = (
        wr * 30 +
        min(max(sortino, -5), 10) * 2.5 +
        min(max(sharpe, -5), 10) * 1.5 +
        min(pf, 5) * 3 +
        max(0, 15 - abs(max_dd) * 100)
    )

    return {
        "trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(wr, 4),
        "mean_pnl": round(float(mean_pnl), 6),
        "total_return": round(total_ret, 4),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "calmar": round(calmar, 3),
        "profit_factor": round(pf, 3),
        "expectancy": round(float(expectancy), 6),
        "max_drawdown": round(float(max_dd), 4),
        "avg_win": round(float(avg_win), 6),
        "avg_loss": round(float(avg_loss), 6),
        "avg_hold_bars": round(float(avg_bars), 1),
        "fitness": round(fitness, 2),
    }


# ---------------------------------------------------------------------------
# Fetch data
# ---------------------------------------------------------------------------

def fetch_data(symbols: dict, period="2y", interval="1d") -> dict:
    """Fetch OHLCV data for all symbols."""
    data = {}
    sym_list = list(symbols.keys())
    print(f"  Fetching {len(sym_list)} symbols ({period} {interval})...")

    try:
        raw = yf.download(sym_list, period=period, interval=interval, group_by="ticker",
                          auto_adjust=True, progress=False, threads=True)
        for sym in sym_list:
            try:
                if len(sym_list) == 1:
                    df = raw.copy()
                else:
                    df = raw[sym].copy()
                df = df.dropna(subset=["Close"])
                if len(df) >= 50:
                    # Flatten multi-level columns if needed
                    if hasattr(df.columns, 'levels'):
                        df.columns = df.columns.get_level_values(0)
                    data[sym] = df
            except Exception:
                pass
    except Exception as e:
        print(f"  Bulk download failed: {e}")

    print(f"  Got data for {len(data)}/{len(sym_list)} symbols")
    return data


# ---------------------------------------------------------------------------
# Main optimization loop
# ---------------------------------------------------------------------------

def optimize_strategy(strategy_name, gen_fn, param_grid, tpsl_grid, data, asset_class, quick=False):
    """Run exhaustive grid search for one strategy across all symbols in data."""
    results = []

    # Generate all parameter combinations
    param_keys = sorted(param_grid.keys())
    param_values = [param_grid[k] for k in param_keys]
    param_combos = list(itertools.product(*param_values))

    max_hold = MAX_HOLD_DAYS.get(asset_class, 10)
    sl_list = tpsl_grid.get(asset_class, tpsl_grid["stock"])["sl"]
    tp_list = tpsl_grid.get(asset_class, tpsl_grid["stock"])["tp"]

    total_combos = len(param_combos) * len(sl_list) * len(tp_list)
    print(f"  [{strategy_name}] {len(param_combos)} indicator combos x {len(sl_list)*len(tp_list)} TP/SL = {total_combos} total configs")

    for sym, df in data.items():
        best_for_sym = None
        tested = 0

        for combo in param_combos:
            params = dict(zip(param_keys, combo))

            try:
                signals = gen_fn(df, params)
            except Exception:
                continue

            if len(signals) < 3:
                continue

            for sl in sl_list:
                for tp in tp_list:
                    trades = backtest_signals(df, signals, sl, tp, max_hold)
                    if len(trades) < 3:
                        continue

                    metrics = calc_metrics(trades)
                    if metrics is None:
                        continue

                    tested += 1
                    result = {
                        "strategy": strategy_name,
                        "symbol": sym,
                        "asset_class": asset_class,
                        "params": params,
                        "sl": sl,
                        "tp": tp,
                        "max_hold": max_hold,
                        **metrics,
                    }

                    if best_for_sym is None or metrics["fitness"] > best_for_sym["fitness"]:
                        best_for_sym = result

                    # Keep results with WR > 50% and 5+ trades for analysis
                    if metrics["win_rate"] >= 0.50 and metrics["trades"] >= 5:
                        results.append(result)

        if best_for_sym:
            best_for_sym["_is_best"] = True
            if best_for_sym not in results:
                results.append(best_for_sym)
            print(f"    {sym}: best WR={best_for_sym['win_rate']*100:.1f}% | "
                  f"{best_for_sym['trades']} trades | Sharpe={best_for_sym['sharpe']:.2f} | "
                  f"Sortino={best_for_sym['sortino']:.2f} | PF={best_for_sym['profit_factor']:.2f} | "
                  f"SL={best_for_sym['sl']*100:.1f}%/TP={best_for_sym['tp']*100:.1f}% | "
                  f"tested {tested} configs")

    return results


def _sanitize(obj):
    """Replace NaN/Inf with None for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


def find_winner_patterns(results):
    """Analyze results to find correlations between parameters and win rate."""
    if not results:
        return {}

    patterns = {}
    # Group by strategy + asset class
    groups = {}
    for r in results:
        key = f"{r['strategy']}::{r['asset_class']}"
        if key not in groups:
            groups[key] = []
        groups[key].append(r)

    for key, group in groups.items():
        # Sort by fitness
        group.sort(key=lambda x: x["fitness"], reverse=True)
        top_n = group[:min(10, len(group))]
        bottom_n = group[-min(10, len(group)):]

        # Analyze which params correlate with high fitness
        param_analysis = {}
        for param_key in (top_n[0].get("params", {}).keys() if top_n else []):
            top_vals = [r["params"][param_key] for r in top_n if param_key in r.get("params", {})]
            bottom_vals = [r["params"][param_key] for r in bottom_n if param_key in r.get("params", {})]
            if top_vals and bottom_vals:
                param_analysis[param_key] = {
                    "top_avg": float(np.mean(top_vals)),
                    "bottom_avg": float(np.mean(bottom_vals)),
                    "top_values": sorted(set(top_vals)),
                }

        # TP/SL analysis
        top_sl = [r["sl"] for r in top_n]
        top_tp = [r["tp"] for r in top_n]

        patterns[key] = {
            "total_configs_tested": len(group),
            "best": {
                "symbol": group[0]["symbol"],
                "win_rate": group[0]["win_rate"],
                "sharpe": group[0]["sharpe"],
                "sortino": group[0]["sortino"],
                "profit_factor": group[0]["profit_factor"],
                "fitness": group[0]["fitness"],
                "params": group[0].get("params", {}),
                "sl": group[0]["sl"],
                "tp": group[0]["tp"],
                "trades": group[0]["trades"],
            },
            "avg_top10_wr": float(np.mean([r["win_rate"] for r in top_n])),
            "optimal_sl_range": [float(min(top_sl)), float(max(top_sl))],
            "optimal_tp_range": [float(min(top_tp)), float(max(top_tp))],
            "param_insights": param_analysis,
        }

    return patterns


def main():
    parser = argparse.ArgumentParser(description="Hyperparameter optimization backtest")
    parser.add_argument("--symbol", type=str, help="Single symbol to test")
    parser.add_argument("--asset-class", type=str, help="Single asset class: futures/stock/forex/etf/penny")
    parser.add_argument("--strategy", type=str, help="Single strategy to test")
    parser.add_argument("--quick", action="store_true", help="Reduced parameter grid for faster results")
    parser.add_argument("--period", type=str, default="2y", help="Data period (default: 2y)")
    args = parser.parse_args()

    print("=" * 70)
    print("HYPERPARAMETER OPTIMIZATION ENGINE v1.0")
    print("=" * 70)
    start_time = time.time()

    # Select grids
    p_grids = PARAM_GRIDS_QUICK if args.quick else PARAM_GRIDS
    tp_grids = TPSL_GRID_QUICK if args.quick else TPSL_GRID

    # Filter universes
    universes = UNIVERSES
    if args.asset_class:
        ac = args.asset_class.lower()
        universes = {k: v for k, v in UNIVERSES.items() if k == ac}
        if not universes:
            print(f"ERROR: Unknown asset class '{ac}'. Choose from: {list(UNIVERSES.keys())}")
            sys.exit(1)

    # Filter to single symbol
    if args.symbol:
        found = False
        for ac, syms in list(universes.items()):
            if args.symbol in syms:
                universes = {ac: {args.symbol: syms[args.symbol]}}
                found = True
                break
        if not found:
            print(f"ERROR: Symbol '{args.symbol}' not found in any universe")
            sys.exit(1)

    # Filter strategies
    strategies = STRATEGY_GENERATORS
    if args.strategy:
        if args.strategy in strategies:
            strategies = {args.strategy: strategies[args.strategy]}
        else:
            print(f"ERROR: Unknown strategy '{args.strategy}'. Choose from: {list(strategies.keys())}")
            sys.exit(1)

    all_results = []

    for asset_class, symbols in universes.items():
        print(f"\n{'='*50}")
        print(f"ASSET CLASS: {asset_class.upper()} ({len(symbols)} symbols)")
        print(f"{'='*50}")

        data = fetch_data(symbols, period=args.period)
        if not data:
            print("  No data available, skipping")
            continue

        for strat_name, gen_fn in strategies.items():
            grid = p_grids.get(strat_name, {})
            print(f"\n  Strategy: {strat_name}")
            results = optimize_strategy(strat_name, gen_fn, grid, tp_grids, data, asset_class, args.quick)
            all_results.extend(results)

    # Analyze patterns
    print(f"\n{'='*70}")
    print("ANALYSIS & PATTERN DISCOVERY")
    print(f"{'='*70}")

    patterns = find_winner_patterns(all_results)

    # Print summary
    for key, p in sorted(patterns.items(), key=lambda x: x[1]["best"]["fitness"], reverse=True):
        b = p["best"]
        print(f"\n  {key}")
        print(f"    Best: {b['symbol']} WR={b['win_rate']*100:.1f}% | {b['trades']} trades | "
              f"Sharpe={b['sharpe']:.2f} | Sortino={b['sortino']:.2f} | PF={b['profit_factor']:.2f}")
        print(f"    Optimal SL: {p['optimal_sl_range'][0]*100:.1f}% to {p['optimal_sl_range'][1]*100:.1f}%")
        print(f"    Optimal TP: {p['optimal_tp_range'][0]*100:.1f}% to {p['optimal_tp_range'][1]*100:.1f}%")
        if p.get("param_insights"):
            for pk, pv in p["param_insights"].items():
                print(f"    {pk}: top avg={pv['top_avg']:.1f}, bottom avg={pv['bottom_avg']:.1f}")

    # Save results
    output = _sanitize({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
        "mode": "quick" if args.quick else "full",
        "period": args.period,
        "total_configs_tested": len(all_results),
        "patterns": patterns,
        "top_results": sorted(all_results, key=lambda x: x.get("fitness", 0), reverse=True)[:200],
    })

    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {RESULTS_FILE}")

    # Save optimal params per strategy::symbol
    optimal = {}
    for r in sorted(all_results, key=lambda x: x.get("fitness", 0), reverse=True):
        key = f"{r['strategy']}::{r['symbol']}"
        if key not in optimal:
            optimal[key] = {
                "strategy": r["strategy"],
                "symbol": r["symbol"],
                "asset_class": r["asset_class"],
                "params": r.get("params", {}),
                "sl": r["sl"],
                "tp": r["tp"],
                "win_rate": r["win_rate"],
                "sharpe": r["sharpe"],
                "sortino": r["sortino"],
                "profit_factor": r["profit_factor"],
                "expectancy": r["expectancy"],
                "trades": r["trades"],
                "fitness": r["fitness"],
            }

    with open(WINNER_FILE, "w") as f:
        json.dump(_sanitize({"generated_at": datetime.now(timezone.utc).isoformat(), "optimal": optimal}), f, indent=2)
    print(f"Optimal params saved to {WINNER_FILE}")

    elapsed = time.time() - start_time
    print(f"\nCompleted in {elapsed:.1f}s ({len(all_results)} viable configs found)")


if __name__ == "__main__":
    main()
