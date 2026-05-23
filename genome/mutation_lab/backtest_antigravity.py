#!/usr/bin/env python3
"""
Antigravity Mutations — Comprehensive Backtester
=================================================

Backtests all 5 AG mutations across 40+ crypto symbols, categorized:
  - TIER_1_MAJORS:  BTC, ETH, BNB, SOL, XRP (ultra liquid)
  - TIER_2_LARGE:   ADA, AVAX, LINK, DOT, LTC, NEAR, APT, SUI (large caps)
  - TIER_3_MIDCAP:  ARB, OP, INJ, FET, TIA, SEI, JUP, FIL, UNI, AAVE (mid caps)
  - MEME_COINS:     DOGE, SHIB, PEPE, WLD, BONK, FLOKI, WIF (memes, separate category)
  - KIMI_WATCHLIST:  STRK, APE, ZK, DYDX, ALGO, TAO, CHZ, TRX, HBAR (KIMI watchlist extras)

Tests across multiple time periods (recent, 1w ago, 2w ago) using
Binance endTime parameter to get independent data samples.

Outputs:
  - Console summary with per-mutation, per-category, and per-symbol metrics
  - JSON: genome/data/antigravity_backtest_results.json
  - Markdown: genome/data/antigravity_backtest_report.md

Usage:
    python -m genome.mutation_lab.backtest_antigravity
"""

from __future__ import annotations

import json
import sys
import time
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import requests

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from genome.mutation_lab.antigravity_mutations import (
    battleground_elite_dual,
    volatility_regime_switch,
    volume_exhaustion_reversal,
    multi_timeframe_alignment,
    drawdown_sniper_v2,
    fetch_binance_klines,
    ALL_ANTIGRAVITY_MUTATIONS,
)
from genome.mutation_lab.antigravity_mutations_v2 import (
    tidal_force,
    gravity_well,
    momentum_cascade,
    ALL_V2_MUTATIONS,
    ALL_V2_SYMBOLS,
)

# Merge V1 + V2 mutations into one dict
COMBINED_MUTATIONS = {**ALL_ANTIGRAVITY_MUTATIONS, **ALL_V2_MUTATIONS}

# ══════════════════════════════════════════════════════════════════════
# Symbol Universe (categorized)
# ══════════════════════════════════════════════════════════════════════

SYMBOL_CATEGORIES = {
    "TIER_1_MAJORS": [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    ],
    "TIER_2_LARGE": [
        "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "LTCUSDT",
        "NEARUSDT", "APTUSDT", "SUIUSDT",
    ],
    "TIER_3_MIDCAP": [
        "ARBUSDT", "OPUSDT", "INJUSDT", "FETUSDT", "TIAUSDT",
        "SEIUSDT", "JUPUSDT", "FILUSDT", "UNIUSDT", "AAVEUSDT",
        "ATOMUSDT", "ICPUSDT",
    ],
    "MEME_COINS": [
        "DOGEUSDT", "SHIBUSDT", "1000PEPEUSDT", "WLDUSDT",
        "1000BONKUSDT", "1000FLOKIUSDT", "WIFUSDT",
    ],
    "KIMI_WATCHLIST": [
        "STRKUSDT", "APEUSDT", "DYDXUSDT",
        "ALGOUSDT", "TAOUSDT", "CHZUSDT", "TRXUSDT", "HBARUSDT",
        "BCHUSDT",
    ],
}

# Flatten all symbols (include V2 symbol universe too)
ALL_SYMBOLS = []
for cat_syms in SYMBOL_CATEGORIES.values():
    ALL_SYMBOLS.extend(cat_syms)
# Add any V2 symbols not already in the list
for s in ALL_V2_SYMBOLS:
    if s not in ALL_SYMBOLS:
        ALL_SYMBOLS.append(s)
ALL_SYMBOLS = list(dict.fromkeys(ALL_SYMBOLS))  # dedupe preserving order

# Reverse lookup: symbol → category
SYMBOL_TO_CATEGORY = {}
for cat, syms in SYMBOL_CATEGORIES.items():
    for s in syms:
        SYMBOL_TO_CATEGORY[s] = cat

# Test periods
TIME_PERIODS = {
    "recent":  None,   # most recent data
    "1w_ago":  7,      # data ending 1 week ago
    "2w_ago":  14,     # data ending 2 weeks ago
}

# Binance mirrors
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://data-api.binance.vision",
]


# ══════════════════════════════════════════════════════════════════════
# Data Fetching
# ══════════════════════════════════════════════════════════════════════

def fetch_klines_historical(symbol: str, interval: str = "1h",
                            limit: int = 500, end_time_ms: int = None) -> pd.DataFrame:
    """Fetch OHLCV from Binance with optional endTime for historical periods."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        if end_time_ms is not None:
            params["endTime"] = end_time_ms
        try:
            resp = requests.get(url, params=params,
                                headers={"User-Agent": "AGBacktest/1.0"},
                                timeout=12)
            resp.raise_for_status()
            data = resp.json()
            if not data or not isinstance(data, list) or len(data) < 50:
                continue

            df = pd.DataFrame(data, columns=[
                "open_time", "Open", "High", "Low", "Close", "Volume",
                "close_time", "qav", "num_trades", "taker_buy_base",
                "taker_buy_quote", "ignore"
            ])
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
            df.set_index("open_time", inplace=True)
            return df[["Open", "High", "Low", "Close", "Volume"]]
        except Exception:
            continue
    return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════
# Trade Simulator (walk-forward)
# ══════════════════════════════════════════════════════════════════════

COMMISSION_PCT = 0.001    # 0.1% per side
SLIPPAGE_PCT = 0.0005     # 0.05% per side
MAX_HOLD_BARS = 24        # 24 hours at 1h


def simulate_signals(signals: list[dict], df: pd.DataFrame) -> list[dict]:
    """Simulate trades from signals against historical data. Walk-forward."""
    if not signals or df.empty:
        return []

    trades = []
    position = None

    for i in range(len(df)):
        row = df.iloc[i]
        high = float(row["High"])
        low = float(row["Low"])
        close = float(row["Close"])

        # Check exits
        if position is not None:
            bars_held = i - position["entry_bar"]
            exit_price = None
            exit_reason = None

            if position["direction"] == "BUY":
                if low <= position["sl"]:
                    exit_price = position["sl"] * (1 - SLIPPAGE_PCT)
                    exit_reason = "SL"
                elif high >= position["tp"]:
                    exit_price = position["tp"] * (1 - SLIPPAGE_PCT)
                    exit_reason = "TP"
                elif bars_held >= MAX_HOLD_BARS:
                    exit_price = close * (1 - SLIPPAGE_PCT)
                    exit_reason = "TIME"
            else:  # SELL
                if high >= position["sl"]:
                    exit_price = position["sl"] * (1 + SLIPPAGE_PCT)
                    exit_reason = "SL"
                elif low <= position["tp"]:
                    exit_price = position["tp"] * (1 + SLIPPAGE_PCT)
                    exit_reason = "TP"
                elif bars_held >= MAX_HOLD_BARS:
                    exit_price = close * (1 + SLIPPAGE_PCT)
                    exit_reason = "TIME"

            if exit_price is not None:
                entry = position["entry"]
                if position["direction"] == "BUY":
                    pnl_pct = (exit_price - entry) / entry * 100
                else:
                    pnl_pct = (entry - exit_price) / entry * 100
                pnl_pct -= COMMISSION_PCT * 2 * 100  # round-trip commission

                trades.append({
                    "pnl_pct": pnl_pct,
                    "exit_reason": exit_reason,
                    "direction": position["direction"],
                    "hold_bars": bars_held,
                    "symbol": position["symbol"],
                    "strategy": position["strategy"],
                })
                position = None

        # Check entries (only if not in position)
        if position is None:
            # Find signals that match current bar's timestamp range
            current_time = df.index[i]
            for sig in signals:
                if sig["symbol"] != df.attrs.get("symbol", ""):
                    continue
                sig_entry = sig["entry_price"]
                # Simple proximity check: signal entry near current close
                if abs(close - sig_entry) / sig_entry < 0.005:  # within 0.5%
                    entry = close * (1 + SLIPPAGE_PCT) if sig["signal_type"] == "BUY" else close * (1 - SLIPPAGE_PCT)
                    position = {
                        "entry": entry,
                        "tp": sig["take_profit"],
                        "sl": sig["stop_loss"],
                        "direction": sig["signal_type"],
                        "entry_bar": i,
                        "symbol": sig["symbol"],
                        "strategy": sig["strategy"],
                    }
                    break

    return trades


def simulate_signals_direct(signals: list[dict], df: pd.DataFrame,
                            symbol: str) -> list[dict]:
    """
    Directly simulate each signal against forward bars.
    More realistic: each signal is tested independently against subsequent bars.
    """
    trades = []

    for sig in signals:
        if sig["symbol"] != symbol:
            continue

        entry = sig["entry_price"]
        tp = sig["take_profit"]
        sl = sig["stop_loss"]
        direction = sig["signal_type"]

        # Find the entry bar (closest price to entry)
        price_diffs = (df["Close"] - entry).abs()
        entry_bar = int(price_diffs.idxmin().timestamp()) if hasattr(price_diffs.idxmin(), 'timestamp') else 0

        # Use last N bars as forward simulation window
        start_idx = max(0, len(df) - MAX_HOLD_BARS - 5)

        exit_price = None
        exit_reason = None
        hold_bars = 0

        for j in range(start_idx, min(start_idx + MAX_HOLD_BARS, len(df))):
            row = df.iloc[j]
            high = float(row["High"])
            low = float(row["Low"])
            close = float(row["Close"])
            hold_bars = j - start_idx + 1

            if direction == "BUY":
                if low <= sl:
                    exit_price = sl * (1 - SLIPPAGE_PCT)
                    exit_reason = "SL"
                    break
                elif high >= tp:
                    exit_price = tp * (1 - SLIPPAGE_PCT)
                    exit_reason = "TP"
                    break
            else:
                if high >= sl:
                    exit_price = sl * (1 + SLIPPAGE_PCT)
                    exit_reason = "SL"
                    break
                elif low <= tp:
                    exit_price = tp * (1 + SLIPPAGE_PCT)
                    exit_reason = "TP"
                    break

        if exit_price is None:
            # Time exit at last bar
            exit_price = float(df["Close"].iloc[-1])
            exit_reason = "TIME"

        if direction == "BUY":
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100
        pnl_pct -= COMMISSION_PCT * 2 * 100

        trades.append({
            "pnl_pct": round(pnl_pct, 4),
            "exit_reason": exit_reason,
            "direction": direction,
            "hold_bars": hold_bars,
            "symbol": symbol,
            "strategy": sig["strategy"],
        })

    return trades


# ══════════════════════════════════════════════════════════════════════
# Metrics Computation
# ══════════════════════════════════════════════════════════════════════

def compute_metrics(trades: list[dict]) -> dict:
    """Compute comprehensive performance metrics."""
    if not trades:
        return {
            "total_trades": 0, "win_rate": 0, "avg_pnl_pct": 0,
            "total_pnl_pct": 0, "profit_factor": 0, "max_drawdown_pct": 0,
            "sharpe": 0, "avg_hold_bars": 0, "tp_rate": 0, "sl_rate": 0,
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.001

    # Max drawdown
    equity = [0]
    for p in pnls:
        equity.append(equity[-1] + p)
    peak = equity[0]
    max_dd = 0
    for e in equity:
        peak = max(peak, e)
        max_dd = max(max_dd, peak - e)

    # Sharpe
    if len(pnls) > 1 and np.std(pnls) > 0:
        sharpe = (np.mean(pnls) / np.std(pnls)) * np.sqrt(252)
    else:
        sharpe = 0

    tp_count = sum(1 for t in trades if t["exit_reason"] == "TP")
    sl_count = sum(1 for t in trades if t["exit_reason"] == "SL")

    return {
        "total_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_pnl_pct": round(sum(pnls) / len(trades), 3),
        "total_pnl_pct": round(sum(pnls), 2),
        "profit_factor": round(gross_profit / gross_loss, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe": round(sharpe, 2),
        "avg_hold_bars": round(sum(t["hold_bars"] for t in trades) / len(trades), 1),
        "tp_rate": round(tp_count / len(trades) * 100, 1),
        "sl_rate": round(sl_count / len(trades) * 100, 1),
    }


# ══════════════════════════════════════════════════════════════════════
# Historical Backtest Engine
# ══════════════════════════════════════════════════════════════════════

def _indicators_inline(df: pd.DataFrame) -> pd.DataFrame:
    """Add ATR, RSI, EMA etc. to DataFrame for historical signal generation."""
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    # ATR
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - 100 / (1 + rs)

    # EMAs
    df["EMA9"] = close.ewm(span=9, adjust=False).mean()
    df["EMA21"] = close.ewm(span=21, adjust=False).mean()
    df["EMA50"] = close.ewm(span=50, adjust=False).mean()

    # Bollinger Bands
    df["SMA20"] = close.rolling(20).mean()
    df["BB_std"] = close.rolling(20).std()
    df["BB_upper"] = df["SMA20"] + 2 * df["BB_std"]
    df["BB_lower"] = df["SMA20"] - 2 * df["BB_std"]

    # Keltner Channels
    df["KC_mid"] = close.ewm(span=20, adjust=False).mean()
    df["KC_upper"] = df["KC_mid"] + 2 * df["ATR"]
    df["KC_lower"] = df["KC_mid"] - 2 * df["ATR"]

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # Volume ratio
    df["Vol_avg"] = df["Volume"].rolling(20).mean()
    df["Vol_ratio"] = df["Volume"] / df["Vol_avg"].replace(0, np.nan)

    # Rolling high/low
    df["High_20"] = high.rolling(20).max()
    df["Low_20"] = low.rolling(20).min()

    return df


def backtest_single_mutation_historical(
    mutation_func,
    mutation_name: str,
    all_data: dict,
    symbol_list: list[str],
) -> list[dict]:
    """
    Backtest a mutation function against historical data.

    Instead of running the mutation on live data (which only sees current bar),
    we walk through the historical bars and simulate what the mutation WOULD
    have generated at each bar, then forward-test those signals.
    """
    all_trades = []

    for symbol in symbol_list:
        df = all_data.get(symbol)
        if df is None or len(df) < 100:
            continue

        df_ind = _indicators_inline(df.copy())

        # Walk through bars 80..N-25, generating signals at each point
        # and forward-testing them over the next 25 bars
        for start_bar in range(80, len(df_ind) - MAX_HOLD_BARS, MAX_HOLD_BARS):
            # Create a "snapshot" of data up to this bar
            snapshot = {symbol: df_ind.iloc[:start_bar + 1].copy()}
            # Also add BTC + SOL for elite_dual mutation
            for anchor in ["BTCUSDT", "SOLUSDT"]:
                if anchor != symbol and anchor in all_data:
                    anchor_df = all_data[anchor]
                    if len(anchor_df) > start_bar:
                        snapshot[anchor] = anchor_df.iloc[:start_bar + 1].copy()

            try:
                signals = mutation_func(snapshot)
            except Exception:
                continue

            if not signals:
                continue

            # Forward-test each signal
            forward_df = df_ind.iloc[start_bar + 1:start_bar + 1 + MAX_HOLD_BARS]
            if len(forward_df) < 5:
                continue

            for sig in signals:
                if sig["symbol"] != symbol:
                    continue

                entry = sig["entry_price"]
                tp = sig["take_profit"]
                sl = sig["stop_loss"]
                direction = sig["signal_type"]

                exit_price = None
                exit_reason = None
                hold_bars = 0

                for j in range(len(forward_df)):
                    row = forward_df.iloc[j]
                    high = float(row["High"])
                    low = float(row["Low"])
                    close = float(row["Close"])
                    hold_bars = j + 1

                    if direction == "BUY":
                        if low <= sl:
                            exit_price = sl * (1 - SLIPPAGE_PCT)
                            exit_reason = "SL"
                            break
                        elif high >= tp:
                            exit_price = tp * (1 - SLIPPAGE_PCT)
                            exit_reason = "TP"
                            break
                    else:
                        if high >= sl:
                            exit_price = sl * (1 + SLIPPAGE_PCT)
                            exit_reason = "SL"
                            break
                        elif low <= tp:
                            exit_price = tp * (1 + SLIPPAGE_PCT)
                            exit_reason = "TP"
                            break

                if exit_price is None:
                    exit_price = float(forward_df["Close"].iloc[-1])
                    exit_reason = "TIME"

                if direction == "BUY":
                    pnl_pct = (exit_price - entry) / entry * 100
                else:
                    pnl_pct = (entry - exit_price) / entry * 100
                pnl_pct -= COMMISSION_PCT * 2 * 100

                all_trades.append({
                    "pnl_pct": round(pnl_pct, 4),
                    "exit_reason": exit_reason,
                    "direction": direction,
                    "hold_bars": hold_bars,
                    "symbol": symbol,
                    "strategy": mutation_name,
                    "category": SYMBOL_TO_CATEGORY.get(symbol, "UNKNOWN"),
                })

    return all_trades


# ══════════════════════════════════════════════════════════════════════
# Main Runner
# ══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("  ANTIGRAVITY MUTATIONS -- COMPREHENSIVE BACKTEST")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)
    print(f"  Symbols: {len(ALL_SYMBOLS)} | Categories: {len(SYMBOL_CATEGORIES)}")
    print(f"  Periods: {list(TIME_PERIODS.keys())} | Mutations: {len(COMBINED_MUTATIONS)} (V1: {len(ALL_ANTIGRAVITY_MUTATIONS)}, V2: {len(ALL_V2_MUTATIONS)})")
    print("=" * 80)

    # Print symbol universe
    for cat, syms in SYMBOL_CATEGORIES.items():
        print(f"  {cat}: {', '.join(syms)}")
    print()

    all_results = {}
    grand_trades = []

    for period_name, days_ago in TIME_PERIODS.items():
        end_time_ms = None
        if days_ago is not None:
            end_dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
            end_time_ms = int(end_dt.timestamp() * 1000)

        print(f"\n{'=' * 80}")
        print(f"  PERIOD: {period_name} {'(latest data)' if days_ago is None else f'(ending {days_ago}d ago)'}")
        print(f"{'=' * 80}")

        # Fetch data for all symbols
        period_data = {}
        for sym in ALL_SYMBOLS:
            try:
                df = fetch_klines_historical(sym, "1h", 500, end_time_ms)
                if not df.empty and len(df) >= 100:
                    period_data[sym] = df
                    print(f"    + {sym}: {len(df)} bars")
                else:
                    print(f"    - {sym}: insufficient data ({len(df) if not df.empty else 0} bars)")
            except Exception as e:
                print(f"    - {sym}: FAILED ({e})")
            time.sleep(0.12)

        if not period_data:
            print("    No data for this period, skipping")
            continue

        print(f"\n    Data fetched: {len(period_data)}/{len(ALL_SYMBOLS)} symbols")
        print()

        # Run each mutation
        for mutation_name, mutation_func in COMBINED_MUTATIONS.items():
            print(f"  -- Backtesting: {mutation_name} --")

            trades = backtest_single_mutation_historical(
                mutation_func, mutation_name, period_data,
                list(period_data.keys())
            )

            # Compute overall metrics
            metrics = compute_metrics(trades)

            # Per-category breakdown
            cat_breakdown = {}
            for cat in SYMBOL_CATEGORIES:
                cat_trades = [t for t in trades if t.get("category") == cat]
                if cat_trades:
                    cat_breakdown[cat] = compute_metrics(cat_trades)

            result_key = f"{period_name}|{mutation_name}"
            all_results[result_key] = {
                "period": period_name,
                "mutation": mutation_name,
                "metrics": metrics,
                "category_breakdown": cat_breakdown,
                "symbols_tested": len(period_data),
            }

            grand_trades.extend(trades)

            # Print summary
            m = metrics
            status = "+" if m["win_rate"] >= 50 else "~" if m["win_rate"] >= 40 else "-"
            print(f"    {status} TOTAL T:{m['total_trades']:>4} | "
                  f"WR:{m['win_rate']:>5.1f}% | "
                  f"PnL:{m['total_pnl_pct']:>+8.2f}% | "
                  f"PF:{m['profit_factor']:>5.2f} | "
                  f"DD:{m['max_drawdown_pct']:>6.2f}% | "
                  f"Sh:{m['sharpe']:>5.2f}")

            for cat, cm in cat_breakdown.items():
                cat_status = "+" if cm["win_rate"] >= 50 else "~" if cm["win_rate"] >= 40 else "-"
                cat_label = cat.replace("_", " ").title()
                print(f"      {cat_status} {cat_label:<18} "
                      f"T:{cm['total_trades']:>3} | "
                      f"WR:{cm['win_rate']:>5.1f}% | "
                      f"PnL:{cm['total_pnl_pct']:>+7.2f}% | "
                      f"PF:{cm['profit_factor']:>5.2f}")

            print()

    # ══════════════════════════════════════════════════════════════════
    # Cross-Period Consistency Analysis
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("  CROSS-PERIOD CONSISTENCY ANALYSIS")
    print("=" * 80)

    mutation_across_periods = {}
    for key, result in all_results.items():
        mname = result["mutation"]
        if mname not in mutation_across_periods:
            mutation_across_periods[mname] = []
        mutation_across_periods[mname].append(result)

    consistency_report = []

    for mname, results in mutation_across_periods.items():
        wrs = [r["metrics"]["win_rate"] for r in results if r["metrics"]["total_trades"] > 0]
        pnls = [r["metrics"]["total_pnl_pct"] for r in results if r["metrics"]["total_trades"] > 0]
        pfs = [r["metrics"]["profit_factor"] for r in results if r["metrics"]["total_trades"] > 0]
        trades = [r["metrics"]["total_trades"] for r in results]
        sharpes = [r["metrics"]["sharpe"] for r in results if r["metrics"]["total_trades"] > 0]
        dds = [r["metrics"]["max_drawdown_pct"] for r in results if r["metrics"]["total_trades"] > 0]

        if not wrs:
            continue

        total_trades = sum(trades)
        periods_profitable = sum(1 for p in pnls if p > 0)
        periods_above_50wr = sum(1 for w in wrs if w >= 50)

        report = {
            "mutation": mname,
            "periods_tested": len(results),
            "periods_profitable": periods_profitable,
            "periods_above_50wr": periods_above_50wr,
            "total_trades": total_trades,
            "avg_wr": round(np.mean(wrs), 1) if wrs else 0,
            "min_wr": round(min(wrs), 1) if wrs else 0,
            "max_wr": round(max(wrs), 1) if wrs else 0,
            "wr_std": round(np.std(wrs), 1) if len(wrs) > 1 else 0,
            "avg_pnl": round(np.mean(pnls), 2) if pnls else 0,
            "avg_pf": round(np.mean(pfs), 2) if pfs else 0,
            "avg_dd": round(np.mean(dds), 2) if dds else 0,
            "max_dd": round(max(dds), 2) if dds else 0,
            "avg_sharpe": round(np.mean(sharpes), 2) if sharpes else 0,
            "is_robust": (periods_profitable >= 2 and
                         (np.mean(wrs) >= 45 if wrs else False) and
                         total_trades >= 10),
        }
        consistency_report.append(report)

        # Determine verdict
        if report["is_robust"] and report["avg_wr"] >= 55:
            verdict = "*** VALIDATED"
        elif report["is_robust"] and report["avg_wr"] >= 50:
            verdict = "** ROBUST"
        elif report["is_robust"]:
            verdict = "* MARGINAL (borderline WR)"
        elif total_trades < 5:
            verdict = "!! INSUFFICIENT DATA (too selective)"
        else:
            verdict = "X FLUKE / UNRELIABLE"

        print(f"\n  {mname}")
        print(f"    Total trades: {total_trades}")
        print(f"    WR: {report['min_wr']:.1f}% - {report['max_wr']:.1f}% (avg {report['avg_wr']:.1f}%, std {report['wr_std']:.1f}%)")
        print(f"    Avg PnL: {report['avg_pnl']:+.2f}% | Avg PF: {report['avg_pf']:.2f} | Avg Sharpe: {report['avg_sharpe']:.2f}")
        print(f"    Avg DD: {report['avg_dd']:.2f}% | Max DD: {report['max_dd']:.2f}%")
        print(f"    Profitable periods: {periods_profitable}/{len(results)} | Periods >50% WR: {periods_above_50wr}/{len(results)}")
        print(f"    VERDICT: {verdict}")

    # ══════════════════════════════════════════════════════════════════
    # Category-Level Analysis (especially MEME vs non-MEME)
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("  CATEGORY PERFORMANCE (MEME vs NON-MEME)")
    print("=" * 80)

    for cat in SYMBOL_CATEGORIES:
        cat_trades = [t for t in grand_trades if t.get("category") == cat]
        if not cat_trades:
            print(f"\n  {cat}: No trades generated")
            continue

        cm = compute_metrics(cat_trades)
        cat_label = cat.replace("_", " ").title()

        # Per-mutation within category
        mut_trades = {}
        for t in cat_trades:
            s = t["strategy"]
            if s not in mut_trades:
                mut_trades[s] = []
            mut_trades[s].append(t)

        status = "+" if cm["win_rate"] >= 50 else "~" if cm["win_rate"] >= 40 else "-"
        print(f"\n  {status} {cat_label}")
        print(f"    T:{cm['total_trades']} | WR:{cm['win_rate']:.1f}% | "
              f"PnL:{cm['total_pnl_pct']:+.2f}% | PF:{cm['profit_factor']:.2f} | "
              f"DD:{cm['max_drawdown_pct']:.2f}% | Sh:{cm['sharpe']:.2f}")

        for mut_name, mt in mut_trades.items():
            mm = compute_metrics(mt)
            mut_status = "+" if mm["win_rate"] >= 50 else "~" if mm["win_rate"] >= 40 else "-"
            print(f"      {mut_status} {mut_name:<22} T:{mm['total_trades']:>3} WR:{mm['win_rate']:>5.1f}% PnL:{mm['total_pnl_pct']:>+7.2f}%")

    # ══════════════════════════════════════════════════════════════════
    # Per-Symbol Heatmap
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("  PER-SYMBOL PERFORMANCE")
    print("=" * 80)

    symbol_trades = {}
    for t in grand_trades:
        s = t["symbol"]
        if s not in symbol_trades:
            symbol_trades[s] = []
        symbol_trades[s].append(t)

    sorted_symbols = sorted(symbol_trades.items(),
                            key=lambda x: compute_metrics(x[1])["win_rate"],
                            reverse=True)

    for sym, trades in sorted_symbols:
        sm = compute_metrics(trades)
        cat = SYMBOL_TO_CATEGORY.get(sym, "?")
        status = "+" if sm["win_rate"] >= 50 else "~" if sm["win_rate"] >= 40 else "-"
        meme_tag = " [MEME]" if cat == "MEME_COINS" else ""
        print(f"  {status} {sym:<14} [{cat:<15}] "
              f"T:{sm['total_trades']:>3} | WR:{sm['win_rate']:>5.1f}% | "
              f"PnL:{sm['total_pnl_pct']:>+7.2f}% | PF:{sm['profit_factor']:>5.2f}{meme_tag}")

    # ══════════════════════════════════════════════════════════════════
    # Final Ranking
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("  FINAL MUTATION RANKING")
    print("=" * 80)

    ranked = sorted(consistency_report,
                    key=lambda r: (r["is_robust"], r["avg_wr"], r["avg_pf"]),
                    reverse=True)

    for i, r in enumerate(ranked, 1):
        if r["is_robust"] and r["avg_wr"] >= 55:
            tag = "***"
        elif r["is_robust"] and r["avg_wr"] >= 50:
            tag = "** "
        elif r["is_robust"]:
            tag = "*  "
        else:
            tag = "   "
        print(f"  {i}. {tag} {r['mutation']:<22} "
              f"AvgWR:{r['avg_wr']:>5.1f}% | "
              f"AvgPnL:{r['avg_pnl']:>+7.2f}% | "
              f"PF:{r['avg_pf']:>5.2f} | "
              f"DD:{r['max_dd']:>6.2f}% | "
              f"T:{r['total_trades']:>4} | "
              f"Prof:{r['periods_profitable']}/{r['periods_tested']}")

    # ══════════════════════════════════════════════════════════════════
    # Save Results
    # ══════════════════════════════════════════════════════════════════
    output_dir = PROJECT_ROOT / "genome" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON output
    json_path = output_dir / "antigravity_backtest_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbols": ALL_SYMBOLS,
            "categories": {k: v for k, v in SYMBOL_CATEGORIES.items()},
            "periods": list(TIME_PERIODS.keys()),
            "mutations": list(ALL_ANTIGRAVITY_MUTATIONS.keys()),
            "total_trades": len(grand_trades),
            "results": list(all_results.values()),
            "consistency_report": consistency_report,
            "grand_metrics": compute_metrics(grand_trades),
        }, f, indent=2, default=str)
    print(f"\n  Results saved to: {json_path}")

    # Markdown report
    md_path = output_dir / "antigravity_backtest_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Antigravity Mutations — Backtest Report\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n")
        f.write(f"**Symbols Tested:** {len(ALL_SYMBOLS)} ({len(SYMBOL_CATEGORIES)} categories)\n\n")
        f.write(f"**Periods:** {', '.join(TIME_PERIODS.keys())}\n\n")
        f.write(f"**Total Trades Simulated:** {len(grand_trades)}\n\n")

        f.write("## Mutation Rankings\n\n")
        f.write("| # | Mutation | Avg WR | Avg PnL | PF | Max DD | Trades | Verdict |\n")
        f.write("|---|---------|--------|---------|-----|--------|--------|---------|\n")
        for i, r in enumerate(ranked, 1):
            if r["is_robust"] and r["avg_wr"] >= 55:
                verdict = "VALIDATED ***"
            elif r["is_robust"] and r["avg_wr"] >= 50:
                verdict = "ROBUST **"
            elif r["is_robust"]:
                verdict = "MARGINAL *"
            elif r["total_trades"] < 5:
                verdict = "INSUFFICIENT"
            else:
                verdict = "WEAK"
            f.write(f"| {i} | {r['mutation']} | {r['avg_wr']:.1f}% | "
                    f"{r['avg_pnl']:+.2f}% | {r['avg_pf']:.2f} | "
                    f"{r['max_dd']:.2f}% | {r['total_trades']} | {verdict} |\n")

        # Category table
        f.write("\n## Category Performance\n\n")
        f.write("| Category | Trades | Win Rate | Total PnL | PF | Sharpe |\n")
        f.write("|----------|--------|----------|-----------|-----|--------|\n")
        for cat in SYMBOL_CATEGORIES:
            cat_trades = [t for t in grand_trades if t.get("category") == cat]
            if cat_trades:
                cm = compute_metrics(cat_trades)
                f.write(f"| {cat} | {cm['total_trades']} | {cm['win_rate']:.1f}% | "
                        f"{cm['total_pnl_pct']:+.2f}% | {cm['profit_factor']:.2f} | "
                        f"{cm['sharpe']:.2f} |\n")
            else:
                f.write(f"| {cat} | 0 | - | - | - | - |\n")

    print(f"  Report saved to: {md_path}")
    print("\n" + "=" * 80)
    print("  BACKTEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
