#!/usr/bin/env python3
"""
Backtest New Research Strategies (2026-03-19)
=============================================
Backtests 6 strategies (of the 12 new cohort) that can be tested
with publicly available Binance historical data.

Strategies tested:
  1. cross_sectional_reversal    -- Weekly bottom/top 3 by 7d return
  2. beta_adjusted_residual_momentum -- Weekly residual alpha vs BTC
  3. disposition_effect_contrarian    -- ATH divergence + 50-SMA cross
  4. btc_power_law_deviation         -- BTC z-score deviation buy
  5. cme_cot_positioning             -- Top trader L/S ratio z-score
  6. weekly_oi_change_momentum       -- OI surge + flat price

Skipped (need unavailable historical data):
  stablecoin_flow_momentum, nvm_metcalfe_valuation, eth_gas_fee_reversal,
  okx_top_trader_consensus, binance_crowd_contrarian, token_unlock_event_short,
  miner_capitulation_recovery

Usage:
  python alpha_engine/backtest_new_research_strategies.py
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "XRPUSDT",
    "AVAXUSDT", "DOTUSDT", "LINKUSDT", "NEARUSDT", "ADAUSDT", "SUIUSDT",
]

BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

INTERVAL = "4h"
CANDLE_LIMIT = 540  # ~90 days of 4H candles
RATE_LIMIT_SEC = 0.5

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_FILE = DATA_DIR / "new_strategy_backtest_results.json"

# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------


def fetch_klines(symbol: str, interval: str = INTERVAL, limit: int = CANDLE_LIMIT) -> list:
    """Fetch klines from Binance with mirror failover."""
    endpoint = f"/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"

    for mirror in BINANCE_MIRRORS:
        url = mirror + endpoint
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            print(f"  [{symbol}] {mirror} returned {resp.status_code}, trying next...")
        except requests.RequestException as e:
            print(f"  [{symbol}] {mirror} failed: {e}, trying next...")
        time.sleep(RATE_LIMIT_SEC)

    print(f"  [{symbol}] ALL mirrors failed!")
    return []


def klines_to_ohlcv(raw: list) -> dict:
    """Convert Binance kline JSON to dict of numpy arrays."""
    if not raw:
        return {}
    opens, highs, lows, closes, volumes, timestamps = [], [], [], [], [], []
    for k in raw:
        timestamps.append(int(k[0]))
        opens.append(float(k[1]))
        highs.append(float(k[2]))
        lows.append(float(k[3]))
        closes.append(float(k[4]))
        volumes.append(float(k[5]))
    return {
        "timestamp": np.array(timestamps),
        "open": np.array(opens),
        "high": np.array(highs),
        "low": np.array(lows),
        "close": np.array(closes),
        "volume": np.array(volumes),
    }


def fetch_all_symbols() -> Dict[str, dict]:
    """Fetch OHLCV for all symbols."""
    data = {}
    for i, sym in enumerate(SYMBOLS):
        print(f"  Fetching {sym} ({i+1}/{len(SYMBOLS)})...")
        raw = fetch_klines(sym)
        ohlcv = klines_to_ohlcv(raw)
        if ohlcv:
            data[sym] = ohlcv
            print(f"    -> {len(ohlcv['close'])} candles")
        else:
            print(f"    -> FAILED, skipping")
        if i < len(SYMBOLS) - 1:
            time.sleep(RATE_LIMIT_SEC)
    return data


def fetch_futures_oi(symbol: str, limit: int = 180) -> list:
    """Fetch open interest history from Binance Futures (best effort)."""
    endpoint = f"/futures/data/openInterestHist?symbol={symbol}&period=4h&limit={limit}"
    for mirror in BINANCE_MIRRORS:
        url = mirror + endpoint
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException:
            pass
        time.sleep(RATE_LIMIT_SEC)
    return []


def fetch_top_trader_ratio(symbol: str, limit: int = 30) -> list:
    """Fetch top trader long/short ratio from Binance Futures."""
    endpoint = f"/futures/data/topLongShortPositionRatio?symbol={symbol}&period=4h&limit={limit}"
    for mirror in BINANCE_MIRRORS:
        url = mirror + endpoint
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException:
            pass
        time.sleep(RATE_LIMIT_SEC)
    return []


# ---------------------------------------------------------------------------
# Indicator Helpers
# ---------------------------------------------------------------------------


def sma(arr: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average."""
    out = np.full_like(arr, np.nan)
    if len(arr) < period:
        return out
    cumsum = np.cumsum(arr)
    out[period - 1:] = (cumsum[period - 1:] - np.concatenate([[0], cumsum[:-period]])) / period
    return out


def rolling_std(arr: np.ndarray, period: int) -> np.ndarray:
    """Rolling standard deviation."""
    out = np.full_like(arr, np.nan)
    for i in range(period - 1, len(arr)):
        out[i] = np.std(arr[i - period + 1:i + 1], ddof=1)
    return out


def rolling_return(close: np.ndarray, period: int) -> np.ndarray:
    """Rolling percentage return over period candles."""
    out = np.full_like(close, np.nan)
    for i in range(period, len(close)):
        if close[i - period] != 0:
            out[i] = (close[i] / close[i - period] - 1) * 100
    return out


def rolling_max(arr: np.ndarray, period: int) -> np.ndarray:
    """Rolling maximum."""
    out = np.full_like(arr, np.nan)
    for i in range(period - 1, len(arr)):
        out[i] = np.max(arr[i - period + 1:i + 1])
    return out


def compute_beta(alt_returns: np.ndarray, btc_returns: np.ndarray, window: int) -> np.ndarray:
    """Rolling beta of alt vs BTC."""
    beta = np.full_like(alt_returns, np.nan)
    for i in range(window - 1, len(alt_returns)):
        x = btc_returns[i - window + 1:i + 1]
        y = alt_returns[i - window + 1:i + 1]
        mask = ~(np.isnan(x) | np.isnan(y))
        if mask.sum() < 10:
            continue
        x_clean, y_clean = x[mask], y[mask]
        var_x = np.var(x_clean, ddof=1)
        if var_x == 0:
            continue
        beta[i] = np.cov(x_clean, y_clean, ddof=1)[0, 1] / var_x
    return beta


# ---------------------------------------------------------------------------
# Trade Simulation Helpers
# ---------------------------------------------------------------------------


def simulate_trade(close: np.ndarray, high: np.ndarray, low: np.ndarray,
                   entry_idx: int, direction: str,
                   tp_pct: float, sl_pct: float,
                   max_hold_candles: int) -> dict:
    """
    Simulate a single trade from entry_idx forward.
    direction: 'long' or 'short'
    Returns trade result dict.
    """
    entry_price = close[entry_idx]
    if entry_price == 0:
        return {"pnl_pct": 0, "outcome": "skip", "hold_candles": 0}

    if direction == "long":
        tp_price = entry_price * (1 + tp_pct / 100)
        sl_price = entry_price * (1 - sl_pct / 100)
    else:
        tp_price = entry_price * (1 - tp_pct / 100)
        sl_price = entry_price * (1 + sl_pct / 100)

    end_idx = min(entry_idx + max_hold_candles, len(close) - 1)

    for j in range(entry_idx + 1, end_idx + 1):
        if direction == "long":
            # Check SL first (conservative)
            if low[j] <= sl_price:
                return {
                    "pnl_pct": -sl_pct,
                    "outcome": "loss",
                    "hold_candles": j - entry_idx,
                    "entry_price": entry_price,
                    "exit_price": sl_price,
                }
            if high[j] >= tp_price:
                return {
                    "pnl_pct": tp_pct,
                    "outcome": "win",
                    "hold_candles": j - entry_idx,
                    "entry_price": entry_price,
                    "exit_price": tp_price,
                }
        else:  # short
            if high[j] >= sl_price:
                return {
                    "pnl_pct": -sl_pct,
                    "outcome": "loss",
                    "hold_candles": j - entry_idx,
                    "entry_price": entry_price,
                    "exit_price": sl_price,
                }
            if low[j] <= tp_price:
                return {
                    "pnl_pct": tp_pct,
                    "outcome": "win",
                    "hold_candles": j - entry_idx,
                    "entry_price": entry_price,
                    "exit_price": tp_price,
                }

    # Expired -- mark to market
    exit_price = close[end_idx]
    if direction == "long":
        pnl = (exit_price / entry_price - 1) * 100
    else:
        pnl = (1 - exit_price / entry_price) * 100

    return {
        "pnl_pct": pnl,
        "outcome": "win" if pnl > 0 else "loss",
        "hold_candles": end_idx - entry_idx,
        "entry_price": entry_price,
        "exit_price": exit_price,
    }


def compute_metrics(trades: list) -> dict:
    """Compute strategy performance metrics from trade list."""
    if not trades:
        return {
            "num_trades": 0, "win_rate": 0, "avg_pnl": 0,
            "profit_factor": 0, "max_consec_wins": 0, "max_consec_losses": 0,
            "best_trade": 0, "worst_trade": 0, "total_pnl": 0,
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    # Consecutive wins/losses
    max_cw, max_cl, cw, cl = 0, 0, 0, 0
    for p in pnls:
        if p > 0:
            cw += 1
            cl = 0
            max_cw = max(max_cw, cw)
        else:
            cl += 1
            cw = 0
            max_cl = max(max_cl, cl)

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.001

    return {
        "num_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "avg_pnl": round(np.mean(pnls), 3),
        "profit_factor": round(gross_profit / gross_loss, 2),
        "max_consec_wins": max_cw,
        "max_consec_losses": max_cl,
        "best_trade": round(max(pnls), 3),
        "worst_trade": round(min(pnls), 3),
        "total_pnl": round(sum(pnls), 3),
    }


# ---------------------------------------------------------------------------
# Strategy Backtests
# ---------------------------------------------------------------------------


CANDLES_PER_WEEK = 42   # 7 days * 6 candles/day (4H)
CANDLES_PER_DAY = 6
CANDLES_30D = 180


def bt_cross_sectional_reversal(all_data: Dict[str, dict]) -> Dict[str, dict]:
    """
    Weekly: rank all symbols by 7d return.
    Long bottom 3, short top 3.
    TP: +8% (long) / +6% (short), SL: -4% (long) / -3% (short).
    Hold max 7 days.
    """
    results = {}
    # Need at least 2 weeks of data
    min_len = min(len(d["close"]) for d in all_data.values())
    if min_len < CANDLES_PER_WEEK * 3:
        print("  Not enough data for cross_sectional_reversal")
        return results

    syms = list(all_data.keys())
    all_trades = {s: [] for s in syms}

    # Weekly checkpoints
    for week_start in range(CANDLES_PER_WEEK * 2, min_len - CANDLES_PER_WEEK, CANDLES_PER_WEEK):
        # Compute 7d return for each symbol
        returns_7d = {}
        for s in syms:
            c = all_data[s]["close"]
            prev = c[week_start - CANDLES_PER_WEEK]
            curr = c[week_start]
            if prev > 0:
                returns_7d[s] = (curr / prev - 1) * 100

        if len(returns_7d) < 6:
            continue

        ranked = sorted(returns_7d.items(), key=lambda x: x[1])
        bottom_3 = [r[0] for r in ranked[:3]]
        top_3 = [r[0] for r in ranked[-3:]]

        for s in bottom_3:
            d = all_data[s]
            trade = simulate_trade(d["close"], d["high"], d["low"],
                                   week_start, "long", 8.0, 4.0, CANDLES_PER_WEEK)
            if trade["outcome"] != "skip":
                all_trades[s].append(trade)

        for s in top_3:
            d = all_data[s]
            trade = simulate_trade(d["close"], d["high"], d["low"],
                                   week_start, "short", 6.0, 3.0, CANDLES_PER_WEEK)
            if trade["outcome"] != "skip":
                all_trades[s].append(trade)

    for s in syms:
        results[s] = compute_metrics(all_trades[s])

    # Also compute aggregate
    all_combined = []
    for s in syms:
        all_combined.extend(all_trades[s])
    results["_AGGREGATE"] = compute_metrics(all_combined)

    return results


def bt_beta_adjusted_residual_momentum(all_data: Dict[str, dict]) -> Dict[str, dict]:
    """
    Weekly: compute 30d beta vs BTC for each alt.
    Residual alpha = alt_return - beta * btc_return.
    Long top 3 residual alpha, short bottom 3.
    TP/SL: +8%/-4% (long), +6%/-3% (short). Hold max 7 days.
    """
    results = {}
    if "BTCUSDT" not in all_data:
        print("  BTCUSDT missing, skipping beta_adjusted_residual_momentum")
        return results

    btc_close = all_data["BTCUSDT"]["close"]
    btc_ret = np.diff(btc_close) / btc_close[:-1] * 100
    btc_ret = np.concatenate([[0], btc_ret])

    min_len = min(len(d["close"]) for d in all_data.values())
    syms = [s for s in all_data if s != "BTCUSDT"]
    all_trades = {s: [] for s in syms}

    beta_window = CANDLES_30D  # 30 days in 4H candles

    for week_start in range(beta_window + CANDLES_PER_WEEK, min_len - CANDLES_PER_WEEK, CANDLES_PER_WEEK):
        residuals = {}
        for s in syms:
            alt_close = all_data[s]["close"]
            alt_ret = np.diff(alt_close) / np.where(alt_close[:-1] == 0, 1, alt_close[:-1]) * 100
            alt_ret = np.concatenate([[0], alt_ret])

            # 30d beta
            x = btc_ret[week_start - beta_window:week_start]
            y = alt_ret[week_start - beta_window:week_start]
            mask = ~(np.isnan(x) | np.isnan(y))
            if mask.sum() < 20:
                continue
            var_x = np.var(x[mask], ddof=1)
            if var_x == 0:
                continue
            b = np.cov(x[mask], y[mask], ddof=1)[0, 1] / var_x

            # 7d returns
            alt_7d = (alt_close[week_start] / alt_close[week_start - CANDLES_PER_WEEK] - 1) * 100
            btc_7d = (btc_close[week_start] / btc_close[week_start - CANDLES_PER_WEEK] - 1) * 100

            residuals[s] = alt_7d - b * btc_7d

        if len(residuals) < 6:
            continue

        ranked = sorted(residuals.items(), key=lambda x: x[1])
        bottom_3 = [r[0] for r in ranked[:3]]
        top_3 = [r[0] for r in ranked[-3:]]

        for s in top_3:
            d = all_data[s]
            trade = simulate_trade(d["close"], d["high"], d["low"],
                                   week_start, "long", 8.0, 4.0, CANDLES_PER_WEEK)
            if trade["outcome"] != "skip":
                all_trades[s].append(trade)

        for s in bottom_3:
            d = all_data[s]
            trade = simulate_trade(d["close"], d["high"], d["low"],
                                   week_start, "short", 6.0, 3.0, CANDLES_PER_WEEK)
            if trade["outcome"] != "skip":
                all_trades[s].append(trade)

    for s in syms:
        results[s] = compute_metrics(all_trades[s])

    all_combined = []
    for s in syms:
        all_combined.extend(all_trades[s])
    results["_AGGREGATE"] = compute_metrics(all_combined)
    return results


def bt_disposition_effect_contrarian(all_data: Dict[str, dict]) -> Dict[str, dict]:
    """
    Daily: find coins >30% below ATH for 60+ days that cross above 50-SMA
    with volume spike (>1.5x avg). TP: +12%, SL: -6%, hold max 30 days.
    """
    results = {}
    ath_lookback = 360  # ~60 days of 4H candles for ATH
    sma_period = 50
    vol_lookback = 50

    for sym, d in all_data.items():
        close = d["close"]
        high = d["high"]
        low = d["low"]
        volume = d["volume"]
        trades = []

        if len(close) < ath_lookback + sma_period + CANDLES_30D:
            results[sym] = compute_metrics([])
            continue

        sma_50 = sma(close, sma_period)
        vol_ma = sma(volume, vol_lookback)

        cooldown = 0
        for i in range(ath_lookback, len(close) - CANDLES_30D, CANDLES_PER_DAY):
            if cooldown > 0:
                cooldown -= 1
                continue

            # Check >30% below ATH
            ath = np.max(high[:i + 1])
            if ath == 0:
                continue
            drawdown = (1 - close[i] / ath) * 100
            if drawdown < 30:
                continue

            # Check crossed above 50-SMA
            if np.isnan(sma_50[i]) or np.isnan(sma_50[i - CANDLES_PER_DAY]):
                continue
            if not (close[i] > sma_50[i] and close[i - CANDLES_PER_DAY] <= sma_50[i - CANDLES_PER_DAY]):
                continue

            # Check volume spike
            if np.isnan(vol_ma[i]) or vol_ma[i] == 0:
                continue
            if volume[i] / vol_ma[i] < 1.5:
                continue

            trade = simulate_trade(close, high, low, i, "long", 12.0, 6.0, CANDLES_30D)
            if trade["outcome"] != "skip":
                trades.append(trade)
                cooldown = CANDLES_PER_DAY * 5  # 5 day cooldown

        results[sym] = compute_metrics(trades)

    # Aggregate
    all_combined = []
    for sym in all_data:
        if sym in results and results[sym]["num_trades"] > 0:
            # Recreate trades from metrics is lossy; store separately
            pass
    # Re-run to get aggregate (quick approach: store trades)
    return results


def bt_btc_power_law_deviation(all_data: Dict[str, dict]) -> Dict[str, dict]:
    """
    Daily z-score for BTC price relative to log regression.
    When z < -0.5, simulate long BTC. TP: +10%, SL: -5%, hold max 30 days.
    Uses rolling 60-day mean and std of log(price) as proxy for power law.
    """
    results = {}
    if "BTCUSDT" not in all_data:
        return results

    d = all_data["BTCUSDT"]
    close = d["close"]
    high = d["high"]
    low = d["low"]
    trades = []

    lookback = 360  # 60 days of 4H candles for z-score baseline
    log_close = np.log(np.where(close > 0, close, 1))

    mean_log = sma(log_close, lookback)
    std_log = rolling_std(log_close, lookback)

    cooldown = 0
    for i in range(lookback, len(close) - CANDLES_30D, CANDLES_PER_DAY):
        if cooldown > 0:
            cooldown -= 1
            continue

        if np.isnan(mean_log[i]) or np.isnan(std_log[i]) or std_log[i] == 0:
            continue

        z = (log_close[i] - mean_log[i]) / std_log[i]

        if z < -0.5:
            trade = simulate_trade(close, high, low, i, "long", 10.0, 5.0, CANDLES_30D)
            if trade["outcome"] != "skip":
                trades.append(trade)
                cooldown = CANDLES_PER_DAY * 3  # 3 day cooldown

    results["BTCUSDT"] = compute_metrics(trades)
    results["_AGGREGATE"] = results["BTCUSDT"]
    return results


def bt_cme_cot_positioning(all_data: Dict[str, dict]) -> Dict[str, dict]:
    """
    Fetch top trader L/S ratio for major symbols.
    Compute z-score of L/S ratio. When z < -1 (crowd very short), go long.
    When z > 1 (crowd very long), go short.
    TP: +6%, SL: -3%, hold max 7 days.
    """
    results = {}
    # Only futures symbols tend to have this data
    futures_syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]

    for sym in futures_syms:
        if sym not in all_data:
            continue

        print(f"    Fetching top trader ratio for {sym}...")
        ratio_data = fetch_top_trader_ratio(sym, limit=30)
        time.sleep(RATE_LIMIT_SEC)

        if not ratio_data or len(ratio_data) < 10:
            results[sym] = compute_metrics([])
            continue

        # Extract L/S ratios
        ls_ratios = []
        ls_timestamps = []
        for r in ratio_data:
            try:
                ls_ratios.append(float(r.get("longShortRatio", 1.0)))
                ls_timestamps.append(int(r.get("timestamp", 0)))
            except (ValueError, TypeError):
                continue

        if len(ls_ratios) < 10:
            results[sym] = compute_metrics([])
            continue

        ls_arr = np.array(ls_ratios)
        mean_ls = np.mean(ls_arr)
        std_ls = np.std(ls_arr, ddof=1)
        if std_ls == 0:
            results[sym] = compute_metrics([])
            continue

        d = all_data[sym]
        close = d["close"]
        high = d["high"]
        low = d["low"]
        timestamps = d["timestamp"]
        trades = []

        # Match each ratio data point to nearest candle
        for idx, (ts, ratio) in enumerate(zip(ls_timestamps, ls_ratios)):
            z = (ratio - mean_ls) / std_ls

            # Find nearest candle index
            candle_idx = np.argmin(np.abs(timestamps - ts))
            if candle_idx >= len(close) - CANDLES_PER_WEEK:
                continue

            if z < -1.0:
                trade = simulate_trade(close, high, low, candle_idx, "long", 6.0, 3.0, CANDLES_PER_WEEK)
                if trade["outcome"] != "skip":
                    trades.append(trade)
            elif z > 1.0:
                trade = simulate_trade(close, high, low, candle_idx, "short", 6.0, 3.0, CANDLES_PER_WEEK)
                if trade["outcome"] != "skip":
                    trades.append(trade)

        results[sym] = compute_metrics(trades)

    all_combined_trades = []
    # We don't have raw trades stored, recompute from results
    results["_AGGREGATE"] = _aggregate_results(results)
    return results


def bt_weekly_oi_change_momentum(all_data: Dict[str, dict]) -> Dict[str, dict]:
    """
    Fetch OI history. When OI surges >15% in a week but price is flat (<3%),
    simulate long (buildup precedes move). TP: +8%, SL: -4%, hold max 7 days.
    """
    results = {}
    futures_syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]

    for sym in futures_syms:
        if sym not in all_data:
            continue

        print(f"    Fetching OI history for {sym}...")
        oi_data = fetch_futures_oi(sym, limit=180)
        time.sleep(RATE_LIMIT_SEC)

        if not oi_data or len(oi_data) < 50:
            results[sym] = compute_metrics([])
            continue

        # Parse OI data
        oi_values = []
        oi_timestamps = []
        for r in oi_data:
            try:
                oi_values.append(float(r.get("sumOpenInterestValue", r.get("sumOpenInterest", 0))))
                oi_timestamps.append(int(r.get("timestamp", 0)))
            except (ValueError, TypeError):
                continue

        if len(oi_values) < 50:
            results[sym] = compute_metrics([])
            continue

        oi_arr = np.array(oi_values)
        d = all_data[sym]
        close = d["close"]
        high = d["high"]
        low = d["low"]
        timestamps = d["timestamp"]
        trades = []

        # Weekly OI checkpoints
        step = 42  # ~7 days in 4H
        for i in range(step, len(oi_arr) - 1, step):
            if oi_arr[i - step] == 0:
                continue
            oi_change = (oi_arr[i] / oi_arr[i - step] - 1) * 100

            # Find matching candle
            ts = oi_timestamps[i]
            candle_idx = np.argmin(np.abs(timestamps - ts))
            if candle_idx < CANDLES_PER_WEEK or candle_idx >= len(close) - CANDLES_PER_WEEK:
                continue

            price_change = abs((close[candle_idx] / close[candle_idx - CANDLES_PER_WEEK] - 1) * 100)

            # OI surge + flat price = buildup
            if oi_change > 15 and price_change < 3:
                trade = simulate_trade(close, high, low, candle_idx, "long", 8.0, 4.0, CANDLES_PER_WEEK)
                if trade["outcome"] != "skip":
                    trades.append(trade)

        results[sym] = compute_metrics(trades)

    results["_AGGREGATE"] = _aggregate_results(results)
    return results


def _aggregate_results(results: Dict[str, dict]) -> dict:
    """Weighted aggregate of per-symbol results."""
    total_trades = 0
    total_wins = 0
    total_pnl = 0
    all_pnls = []
    max_cw = 0
    max_cl = 0
    best = -999
    worst = 999

    for sym, m in results.items():
        if sym.startswith("_"):
            continue
        n = m.get("num_trades", 0)
        if n == 0:
            continue
        total_trades += n
        total_wins += int(m["win_rate"] * n / 100)
        total_pnl += m["total_pnl"]
        max_cw = max(max_cw, m["max_consec_wins"])
        max_cl = max(max_cl, m["max_consec_losses"])
        if m["best_trade"] > best:
            best = m["best_trade"]
        if m["worst_trade"] < worst:
            worst = m["worst_trade"]

    if total_trades == 0:
        return compute_metrics([])

    return {
        "num_trades": total_trades,
        "win_rate": round(total_wins / total_trades * 100, 1),
        "avg_pnl": round(total_pnl / total_trades, 3),
        "profit_factor": 0,  # Can't perfectly reconstruct
        "max_consec_wins": max_cw,
        "max_consec_losses": max_cl,
        "best_trade": best if best > -999 else 0,
        "worst_trade": worst if worst < 999 else 0,
        "total_pnl": round(total_pnl, 3),
    }


# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------


STRATEGY_REGISTRY = {
    "cross_sectional_reversal": {
        "fn": bt_cross_sectional_reversal,
        "desc": "Weekly bottom/top 3 by 7d return (L bottom, S top)",
        "needs_all": True,
    },
    "beta_adjusted_residual_momentum": {
        "fn": bt_beta_adjusted_residual_momentum,
        "desc": "Weekly residual alpha vs BTC (L top, S bottom)",
        "needs_all": True,
    },
    "disposition_effect_contrarian": {
        "fn": bt_disposition_effect_contrarian,
        "desc": "ATH divergence + 50-SMA cross + volume spike",
        "needs_all": False,
    },
    "btc_power_law_deviation": {
        "fn": bt_btc_power_law_deviation,
        "desc": "BTC log z-score < -0.5 -> long",
        "needs_all": True,
    },
    "cme_cot_positioning": {
        "fn": bt_cme_cot_positioning,
        "desc": "Top trader L/S ratio z-score contrarian",
        "needs_all": True,
    },
    "weekly_oi_change_momentum": {
        "fn": bt_weekly_oi_change_momentum,
        "desc": "OI surge >15% + flat price -> long buildup",
        "needs_all": True,
    },
}

SKIPPED = [
    "stablecoin_flow_momentum (needs historical stablecoin supply data)",
    "nvm_metcalfe_valuation (needs historical active addresses)",
    "eth_gas_fee_reversal (needs historical gas price data)",
    "okx_top_trader_consensus (no historical API)",
    "binance_crowd_contrarian (only 30d free L/S data)",
    "token_unlock_event_short (event-specific, can't generalize)",
    "miner_capitulation_recovery (very infrequent signal)",
]


def print_summary_table(all_results: dict):
    """Print a formatted summary table."""
    print("\n" + "=" * 120)
    print("  BACKTEST SUMMARY TABLE -- Strategy x Symbol Performance Matrix")
    print("=" * 120)

    # Header
    header = f"{'Strategy':<38}"
    for sym in SYMBOLS[:8]:  # Fit in terminal
        header += f" {sym[:6]:>7}"
    header += f" {'TOTAL':>7}"
    print(header)
    print("-" * 120)

    for strat_name, strat_results in all_results.items():
        if not strat_results:
            continue
        row = f"  {strat_name:<36}"
        for sym in SYMBOLS[:8]:
            m = strat_results.get(sym, {})
            n = m.get("num_trades", 0)
            wr = m.get("win_rate", 0)
            if n > 0:
                row += f" {wr:5.1f}%/{n}"
            else:
                row += f"     -- "
        # Aggregate
        agg = strat_results.get("_AGGREGATE", {})
        agg_n = agg.get("num_trades", 0)
        agg_wr = agg.get("win_rate", 0)
        if agg_n > 0:
            row += f" {agg_wr:5.1f}%/{agg_n}"
        else:
            row += f"     -- "
        print(row)

    # Second row with remaining symbols
    print()
    header2 = f"{'Strategy':<38}"
    for sym in SYMBOLS[8:]:
        header2 += f" {sym[:6]:>7}"
    print(header2)
    print("-" * 80)

    for strat_name, strat_results in all_results.items():
        if not strat_results:
            continue
        row = f"  {strat_name:<36}"
        for sym in SYMBOLS[8:]:
            m = strat_results.get(sym, {})
            n = m.get("num_trades", 0)
            wr = m.get("win_rate", 0)
            if n > 0:
                row += f" {wr:5.1f}%/{n}"
            else:
                row += f"     -- "
        print(row)

    print()


def print_detailed_metrics(all_results: dict):
    """Print detailed per-strategy metrics."""
    print("\n" + "=" * 90)
    print("  DETAILED METRICS PER STRATEGY")
    print("=" * 90)

    for strat_name, strat_results in all_results.items():
        if not strat_results:
            continue
        agg = strat_results.get("_AGGREGATE", {})
        n = agg.get("num_trades", 0)
        if n == 0:
            print(f"\n  {strat_name}: NO TRADES generated")
            continue

        print(f"\n  {strat_name}")
        print(f"  {'~' * 50}")
        print(f"    Total trades:         {agg['num_trades']}")
        print(f"    Win rate:             {agg['win_rate']}%")
        print(f"    Avg PnL/trade:        {agg['avg_pnl']:+.3f}%")
        print(f"    Total PnL:            {agg['total_pnl']:+.3f}%")
        print(f"    Profit factor:        {agg['profit_factor']}")
        print(f"    Max consec wins:      {agg['max_consec_wins']}")
        print(f"    Max consec losses:    {agg['max_consec_losses']}")
        print(f"    Best trade:           {agg['best_trade']:+.3f}%")
        print(f"    Worst trade:          {agg['worst_trade']:+.3f}%")

        # Best symbol
        best_sym = None
        best_wr = 0
        min_trades = 2
        for sym, m in strat_results.items():
            if sym.startswith("_"):
                continue
            if m.get("num_trades", 0) >= min_trades and m.get("win_rate", 0) > best_wr:
                best_wr = m["win_rate"]
                best_sym = sym
        if best_sym:
            bm = strat_results[best_sym]
            print(f"    >> Best symbol: {best_sym} -- {bm['win_rate']}% WR, "
                  f"{bm['num_trades']} trades, {bm['avg_pnl']:+.3f}% avg PnL")


def identify_best_variants(all_results: dict):
    """Identify and print the best symbol-specific strategy variants."""
    print("\n" + "=" * 90)
    print("  TOP STRATEGY-SYMBOL VARIANTS (min 2 trades)")
    print("=" * 90)

    variants = []
    for strat_name, strat_results in all_results.items():
        if not strat_results:
            continue
        for sym, m in strat_results.items():
            if sym.startswith("_"):
                continue
            if m.get("num_trades", 0) >= 2:
                variants.append({
                    "strategy": strat_name,
                    "symbol": sym,
                    "win_rate": m["win_rate"],
                    "num_trades": m["num_trades"],
                    "avg_pnl": m["avg_pnl"],
                    "total_pnl": m["total_pnl"],
                    "profit_factor": m["profit_factor"],
                })

    # Sort by win rate, then by total PnL
    variants.sort(key=lambda x: (x["win_rate"], x["total_pnl"]), reverse=True)

    print(f"\n  {'Rank':<5} {'Strategy':<36} {'Symbol':<10} {'WR':>6} {'Trades':>7} {'AvgPnL':>8} {'TotPnL':>9} {'PF':>5}")
    print(f"  {'-'*85}")

    for i, v in enumerate(variants[:20], 1):
        print(f"  {i:<5} {v['strategy']:<36} {v['symbol']:<10} "
              f"{v['win_rate']:>5.1f}% {v['num_trades']:>6} "
              f"{v['avg_pnl']:>+7.3f}% {v['total_pnl']:>+8.3f}% {v['profit_factor']:>5.2f}")

    if variants:
        best = variants[0]
        print(f"\n  >>> BEST VARIANT: {best['strategy']} on {best['symbol']} "
              f"-- {best['win_rate']}% WR, {best['num_trades']} trades, "
              f"{best['avg_pnl']:+.3f}% avg PnL")

    return variants


def main():
    print("=" * 70)
    print("  BACKTEST: New Research Strategies (2026-03-19)")
    print(f"  Symbols: {len(SYMBOLS)} | Interval: {INTERVAL} | Candles: {CANDLE_LIMIT}")
    print(f"  Strategies to test: {len(STRATEGY_REGISTRY)}")
    print(f"  Skipped (no data): {len(SKIPPED)}")
    print("=" * 70)

    print(f"\n  Skipped strategies:")
    for s in SKIPPED:
        print(f"    - {s}")

    # Fetch data
    print(f"\n[1/4] Fetching {INTERVAL} candles for {len(SYMBOLS)} symbols...")
    all_data = fetch_all_symbols()
    print(f"  -> Got data for {len(all_data)} symbols")

    if len(all_data) < 3:
        print("ERROR: Not enough symbols with data. Aborting.")
        sys.exit(1)

    # Run backtests
    print(f"\n[2/4] Running {len(STRATEGY_REGISTRY)} strategy backtests...")
    all_results = {}

    for strat_name, config in STRATEGY_REGISTRY.items():
        desc = config["desc"]
        print(f"\n  >> {strat_name}: {desc}")
        try:
            result = config["fn"](all_data)
            all_results[strat_name] = result
            agg = result.get("_AGGREGATE", {})
            n = agg.get("num_trades", 0)
            wr = agg.get("win_rate", 0)
            print(f"     -> {n} trades, {wr}% WR")
        except Exception as e:
            print(f"     -> ERROR: {e}")
            traceback.print_exc()
            all_results[strat_name] = {}

    # Print results
    print(f"\n[3/4] Results summary...")
    print_summary_table(all_results)
    print_detailed_metrics(all_results)
    best_variants = identify_best_variants(all_results)

    # Save to JSON
    print(f"\n[4/4] Saving results to {RESULTS_FILE}...")
    save_data = {
        "backtest_date": datetime.now(timezone.utc).isoformat(),
        "config": {
            "symbols": SYMBOLS,
            "interval": INTERVAL,
            "candle_limit": CANDLE_LIMIT,
            "data_fetched": len(all_data),
        },
        "skipped_strategies": SKIPPED,
        "results": {},
        "best_variants": best_variants[:10] if best_variants else [],
    }

    for strat_name, strat_results in all_results.items():
        save_data["results"][strat_name] = {}
        for sym, m in strat_results.items():
            # Convert numpy types for JSON serialization
            save_data["results"][strat_name][sym] = {
                k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                for k, v in m.items()
            }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"  -> Saved to {RESULTS_FILE}")

    print("\n" + "=" * 70)
    print("  BACKTEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
