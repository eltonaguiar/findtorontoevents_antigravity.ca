#!/usr/bin/env python3
"""
COMPREHENSIVE CRYPTO STRATEGY BACKTESTER
==========================================
Tests multiple strategies across multiple crypto assets and timeframes.
Uses real daily data from yfinance (2020-2026).

Strategies tested:
1. Connors RSI-2 Mean Reversion (proven 68-78% WR on equities)
2. Keltner Compression Breakout (proven 72.9% WR on BTC in battleground)
3. Multi-Period RSI Confluence (proven 60-64% WR forward-tested)
4. Bollinger Band Mean Reversion
5. EMA Crossover Trend Following (9/21 EMA)
6. DCA on Fear & Greed Extreme (buy dips)
7. MACD Histogram Reversal
8. Supertrend
9. Volume Spike + RSI Confirmation
10. Donchian Channel Breakout (Turtle Trading)

Each strategy tested with:
- Realistic 0.1% transaction cost per side (Binance taker fee)
- No lookahead bias
- Walk-forward: Train on 2020-2023, Test on 2024-2026
- Per-symbol and aggregate stats
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ── Config ──────────────────────────────────────────────────────────────
SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "AVAX-USD", "DOGE-USD", "ADA-USD", "LINK-USD"]
START = "2020-01-01"
END = "2026-03-11"
SPLIT_DATE = "2024-01-01"  # Train vs test split
FEE_PCT = 0.001  # 0.1% per side (Binance taker)
INITIAL_CAPITAL = 10000
MAX_HOLD_DAYS = 10  # For mean-reversion strategies
TREND_MAX_HOLD = 30  # For trend-following strategies

# ── Indicators ──────────────────────────────────────────────────────────

def rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def sma(series, period):
    return series.rolling(period).mean()

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def bollinger_bands(close, period=20, std_dev=2):
    mid = sma(close, period)
    std = close.rolling(period).std()
    return mid, mid + std_dev * std, mid - std_dev * std

def keltner_channels(df, ema_period=20, atr_period=14, atr_mult=1.5):
    mid = ema(df["Close"], ema_period)
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr_val = tr.rolling(atr_period).mean()
    return mid, mid + atr_mult * atr_val, mid - atr_mult * atr_val

def atr(df, period=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def macd(close, fast=12, slow=26, signal=9):
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def donchian(df, period=20):
    upper = df["High"].rolling(period).max()
    lower = df["Low"].rolling(period).min()
    return upper, lower

def supertrend(df, period=10, multiplier=3):
    hl2 = (df["High"] + df["Low"]) / 2
    atr_val = atr(df, period)
    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val

    st = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)

    st.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(df)):
        if df["Close"].iloc[i] > upper_band.iloc[i-1]:
            direction.iloc[i] = 1
        elif df["Close"].iloc[i] < lower_band.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]

        if direction.iloc[i] == 1:
            st.iloc[i] = max(lower_band.iloc[i], st.iloc[i-1]) if direction.iloc[i-1] == 1 else lower_band.iloc[i]
        else:
            st.iloc[i] = min(upper_band.iloc[i], st.iloc[i-1]) if direction.iloc[i-1] == -1 else upper_band.iloc[i]

    return st, direction

# ── Strategy Signal Generators ──────────────────────────────────────────

def strategy_connors_rsi2(df):
    """Connors RSI-2: Buy RSI(2)<5 above 200 SMA, sell RSI(2)>65"""
    signals = []
    rsi2 = rsi(df["Close"], 2)
    sma200 = sma(df["Close"], 200)

    for i in range(201, len(df)):
        if rsi2.iloc[i] < 5 and df["Close"].iloc[i] > sma200.iloc[i]:
            signals.append({"idx": i, "direction": "LONG", "type": "entry"})
    return signals, {"exit_rsi_above": 65, "max_hold": MAX_HOLD_DAYS}

def strategy_connors_rsi2_crypto(df):
    """Connors RSI-2 adapted for crypto: RSI(2)<10 above 50 SMA (crypto trends shorter)"""
    signals = []
    rsi2 = rsi(df["Close"], 2)
    sma50 = sma(df["Close"], 50)

    for i in range(51, len(df)):
        if rsi2.iloc[i] < 10 and df["Close"].iloc[i] > sma50.iloc[i]:
            signals.append({"idx": i, "direction": "LONG", "type": "entry"})
    return signals, {"exit_rsi_above": 60, "max_hold": 7}

def strategy_keltner_compression(df):
    """Keltner Compression: Enter when BB squeezes inside Keltner then breaks out"""
    signals = []
    bb_mid, bb_upper, bb_lower = bollinger_bands(df["Close"], 20, 2)
    kc_mid, kc_upper, kc_lower = keltner_channels(df, 20, 14, 1.5)

    squeeze = (bb_lower > kc_lower) & (bb_upper < kc_upper)

    for i in range(21, len(df)):
        if i < 2:
            continue
        # Squeeze released + price breaks above Keltner upper
        if squeeze.iloc[i-1] and not squeeze.iloc[i] and df["Close"].iloc[i] > kc_upper.iloc[i]:
            signals.append({"idx": i, "direction": "LONG", "type": "entry"})
        elif squeeze.iloc[i-1] and not squeeze.iloc[i] and df["Close"].iloc[i] < kc_lower.iloc[i]:
            signals.append({"idx": i, "direction": "SHORT", "type": "entry"})
    return signals, {"atr_tp_mult": 2.0, "atr_sl_mult": 1.0, "max_hold": 15}

def strategy_multi_rsi_confluence(df):
    """Multi-period RSI confluence: RSI(2)<20 AND RSI(7)<40 AND RSI(14)<50"""
    signals = []
    rsi2 = rsi(df["Close"], 2)
    rsi7 = rsi(df["Close"], 7)
    rsi14 = rsi(df["Close"], 14)
    sma50 = sma(df["Close"], 50)

    for i in range(50, len(df)):
        if rsi2.iloc[i] < 20 and rsi7.iloc[i] < 40 and rsi14.iloc[i] < 50:
            if df["Close"].iloc[i] > sma50.iloc[i]:
                signals.append({"idx": i, "direction": "LONG", "type": "entry"})
    return signals, {"exit_rsi_above": 60, "max_hold": MAX_HOLD_DAYS}

def strategy_bollinger_mean_reversion(df):
    """Bollinger Band Mean Reversion: Buy at lower band, sell at middle"""
    signals = []
    bb_mid, bb_upper, bb_lower = bollinger_bands(df["Close"], 20, 2)
    rsi14 = rsi(df["Close"], 14)

    for i in range(21, len(df)):
        if df["Close"].iloc[i] < bb_lower.iloc[i] and rsi14.iloc[i] < 30:
            signals.append({"idx": i, "direction": "LONG", "type": "entry"})
        elif df["Close"].iloc[i] > bb_upper.iloc[i] and rsi14.iloc[i] > 70:
            signals.append({"idx": i, "direction": "SHORT", "type": "entry"})
    return signals, {"exit_at_mid": True, "max_hold": MAX_HOLD_DAYS}

def strategy_ema_crossover(df):
    """EMA 9/21 Crossover: trend following"""
    signals = []
    ema9 = ema(df["Close"], 9)
    ema21 = ema(df["Close"], 21)
    ema50 = ema(df["Close"], 50)

    for i in range(50, len(df)):
        if ema9.iloc[i] > ema21.iloc[i] and ema9.iloc[i-1] <= ema21.iloc[i-1] and df["Close"].iloc[i] > ema50.iloc[i]:
            signals.append({"idx": i, "direction": "LONG", "type": "entry"})
        elif ema9.iloc[i] < ema21.iloc[i] and ema9.iloc[i-1] >= ema21.iloc[i-1] and df["Close"].iloc[i] < ema50.iloc[i]:
            signals.append({"idx": i, "direction": "SHORT", "type": "entry"})
    return signals, {"exit_on_cross": True, "max_hold": TREND_MAX_HOLD}

def strategy_macd_reversal(df):
    """MACD Histogram Reversal: enter when histogram crosses zero"""
    signals = []
    _, _, hist = macd(df["Close"])
    sma50 = sma(df["Close"], 50)

    for i in range(50, len(df)):
        if hist.iloc[i] > 0 and hist.iloc[i-1] <= 0 and df["Close"].iloc[i] > sma50.iloc[i]:
            signals.append({"idx": i, "direction": "LONG", "type": "entry"})
        elif hist.iloc[i] < 0 and hist.iloc[i-1] >= 0 and df["Close"].iloc[i] < sma50.iloc[i]:
            signals.append({"idx": i, "direction": "SHORT", "type": "entry"})
    return signals, {"exit_on_cross": True, "max_hold": TREND_MAX_HOLD}

def strategy_supertrend_follow(df):
    """Supertrend: follow the trend direction"""
    signals = []
    st, direction = supertrend(df, 10, 3)

    for i in range(11, len(df)):
        if direction.iloc[i] == 1 and direction.iloc[i-1] == -1:
            signals.append({"idx": i, "direction": "LONG", "type": "entry"})
        elif direction.iloc[i] == -1 and direction.iloc[i-1] == 1:
            signals.append({"idx": i, "direction": "SHORT", "type": "entry"})
    return signals, {"exit_on_flip": True, "max_hold": TREND_MAX_HOLD}

def strategy_volume_spike_rsi(df):
    """Volume Spike + RSI: High volume candle with oversold RSI"""
    signals = []
    rsi14 = rsi(df["Close"], 14)
    vol_sma = sma(df["Volume"], 20)

    for i in range(21, len(df)):
        if vol_sma.iloc[i] > 0 and df["Volume"].iloc[i] > 2.5 * vol_sma.iloc[i]:
            if rsi14.iloc[i] < 35 and df["Close"].iloc[i] > df["Open"].iloc[i]:
                signals.append({"idx": i, "direction": "LONG", "type": "entry"})
            elif rsi14.iloc[i] > 65 and df["Close"].iloc[i] < df["Open"].iloc[i]:
                signals.append({"idx": i, "direction": "SHORT", "type": "entry"})
    return signals, {"atr_tp_mult": 2.0, "atr_sl_mult": 1.5, "max_hold": MAX_HOLD_DAYS}

def strategy_donchian_breakout(df):
    """Donchian Channel (Turtle Trading): Break above 20-day high = LONG"""
    signals = []
    upper, lower = donchian(df, 20)
    atr_val = atr(df, 14)

    for i in range(21, len(df)):
        if df["Close"].iloc[i] > upper.iloc[i-1] and atr_val.iloc[i] > 0:
            signals.append({"idx": i, "direction": "LONG", "type": "entry"})
        elif df["Close"].iloc[i] < lower.iloc[i-1] and atr_val.iloc[i] > 0:
            signals.append({"idx": i, "direction": "SHORT", "type": "entry"})
    return signals, {"atr_tp_mult": 3.0, "atr_sl_mult": 2.0, "max_hold": TREND_MAX_HOLD}


# ── Backtester ──────────────────────────────────────────────────────────

def backtest_strategy(df, strategy_fn, symbol, period_label="full"):
    """Run a strategy on price data, return trade list with realistic costs."""
    signals, params = strategy_fn(df)

    trades = []
    rsi2 = rsi(df["Close"], 2)
    rsi14 = rsi(df["Close"], 14)
    bb_mid, _, _ = bollinger_bands(df["Close"], 20, 2)
    ema9 = ema(df["Close"], 9)
    ema21 = ema(df["Close"], 21)
    _, _, hist = macd(df["Close"])
    _, st_dir = supertrend(df, 10, 3)
    atr_val = atr(df, 14)

    max_hold = params.get("max_hold", MAX_HOLD_DAYS)

    i = 0
    while i < len(signals):
        sig = signals[i]
        entry_idx = sig["idx"]
        entry_price = df["Close"].iloc[entry_idx]
        direction = 1 if sig["direction"] == "LONG" else -1

        # Skip if not enough room for exit
        if entry_idx + 1 >= len(df):
            i += 1
            continue

        # Simulate exit
        exit_idx = None
        exit_reason = "MAX_HOLD"

        for j in range(entry_idx + 1, min(entry_idx + max_hold + 1, len(df))):
            price = df["Close"].iloc[j]

            # ATR-based TP/SL
            if "atr_tp_mult" in params and atr_val.iloc[entry_idx] > 0:
                tp_dist = params["atr_tp_mult"] * atr_val.iloc[entry_idx]
                sl_dist = params["atr_sl_mult"] * atr_val.iloc[entry_idx]

                if direction == 1:
                    if price >= entry_price + tp_dist:
                        exit_idx = j; exit_reason = "TP"; break
                    if price <= entry_price - sl_dist:
                        exit_idx = j; exit_reason = "SL"; break
                else:
                    if price <= entry_price - tp_dist:
                        exit_idx = j; exit_reason = "TP"; break
                    if price >= entry_price + sl_dist:
                        exit_idx = j; exit_reason = "SL"; break

            # RSI-based exit
            if "exit_rsi_above" in params and direction == 1:
                if rsi2.iloc[j] > params["exit_rsi_above"]:
                    exit_idx = j; exit_reason = "RSI_EXIT"; break

            # BB mid exit
            if params.get("exit_at_mid"):
                if direction == 1 and price >= bb_mid.iloc[j]:
                    exit_idx = j; exit_reason = "BB_MID"; break
                elif direction == -1 and price <= bb_mid.iloc[j]:
                    exit_idx = j; exit_reason = "BB_MID"; break

            # EMA cross exit
            if params.get("exit_on_cross"):
                if direction == 1 and ema9.iloc[j] < ema21.iloc[j]:
                    exit_idx = j; exit_reason = "EMA_CROSS"; break
                elif direction == -1 and ema9.iloc[j] > ema21.iloc[j]:
                    exit_idx = j; exit_reason = "EMA_CROSS"; break

            # Supertrend flip exit
            if params.get("exit_on_flip"):
                if direction == 1 and st_dir.iloc[j] == -1:
                    exit_idx = j; exit_reason = "ST_FLIP"; break
                elif direction == -1 and st_dir.iloc[j] == 1:
                    exit_idx = j; exit_reason = "ST_FLIP"; break

        if exit_idx is None:
            exit_idx = min(entry_idx + max_hold, len(df) - 1)

        exit_price = df["Close"].iloc[exit_idx]

        # PnL with fees
        if direction == 1:
            raw_pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            raw_pnl_pct = (entry_price - exit_price) / entry_price * 100

        net_pnl_pct = raw_pnl_pct - (FEE_PCT * 2 * 100)  # 0.1% each side

        trades.append({
            "symbol": symbol,
            "direction": sig["direction"],
            "entry_date": str(df.index[entry_idx].date()),
            "exit_date": str(df.index[exit_idx].date()),
            "entry_price": round(entry_price, 4),
            "exit_price": round(exit_price, 4),
            "pnl_pct": round(net_pnl_pct, 4),
            "raw_pnl_pct": round(raw_pnl_pct, 4),
            "hold_days": exit_idx - entry_idx,
            "exit_reason": exit_reason,
            "period": period_label
        })

        # Skip signals that overlap with this trade
        i += 1
        while i < len(signals) and signals[i]["idx"] <= exit_idx:
            i += 1

    return trades


def analyze_trades(trades, strategy_name):
    """Compute stats from trade list."""
    if not trades:
        return None

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_pnl = sum(pnls)
    avg_pnl = np.mean(pnls)
    wr = len(wins) / len(pnls) * 100 if pnls else 0
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0
    profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float("inf")

    # Max drawdown (cumulative)
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    dd = cum - peak
    max_dd = min(dd) if len(dd) > 0 else 0

    # Sharpe (annualized, assuming ~365 trading days for crypto)
    if len(pnls) > 1:
        sharpe = (np.mean(pnls) / np.std(pnls)) * np.sqrt(365 / max(np.mean([t["hold_days"] for t in trades]), 1))
    else:
        sharpe = 0

    # Expectancy
    expectancy = (wr/100 * avg_win) + ((1 - wr/100) * avg_loss)

    # By symbol
    by_symbol = {}
    for t in trades:
        s = t["symbol"]
        if s not in by_symbol:
            by_symbol[s] = []
        by_symbol[s].append(t["pnl_pct"])

    symbol_stats = {}
    for s, pnl_list in by_symbol.items():
        sw = [p for p in pnl_list if p > 0]
        symbol_stats[s] = {
            "trades": len(pnl_list),
            "wr": round(len(sw) / len(pnl_list) * 100, 1),
            "avg_pnl": round(np.mean(pnl_list), 3),
            "total_pnl": round(sum(pnl_list), 2)
        }

    return {
        "strategy": strategy_name,
        "total_trades": len(pnls),
        "win_rate": round(wr, 1),
        "avg_pnl": round(avg_pnl, 3),
        "avg_win": round(avg_win, 3),
        "avg_loss": round(avg_loss, 3),
        "total_pnl": round(total_pnl, 2),
        "profit_factor": round(profit_factor, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_dd, 2),
        "expectancy": round(expectancy, 4),
        "avg_hold_days": round(np.mean([t["hold_days"] for t in trades]), 1),
        "by_symbol": symbol_stats
    }


# ── Main ────────────────────────────────────────────────────────────────

STRATEGIES = {
    "connors_rsi2_classic": strategy_connors_rsi2,
    "connors_rsi2_crypto": strategy_connors_rsi2_crypto,
    "keltner_compression": strategy_keltner_compression,
    "multi_rsi_confluence": strategy_multi_rsi_confluence,
    "bollinger_mean_reversion": strategy_bollinger_mean_reversion,
    "ema_9_21_crossover": strategy_ema_crossover,
    "macd_histogram_reversal": strategy_macd_reversal,
    "supertrend_follow": strategy_supertrend_follow,
    "volume_spike_rsi": strategy_volume_spike_rsi,
    "donchian_breakout": strategy_donchian_breakout,
}

def main():
    print("=" * 80)
    print("COMPREHENSIVE CRYPTO STRATEGY BACKTEST")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Period: {START} to {END}")
    print(f"Walk-forward split: Train <{SPLIT_DATE} | Test >={SPLIT_DATE}")
    print(f"Fee: {FEE_PCT*100}% per side ({FEE_PCT*2*100}% round-trip)")
    print("=" * 80)

    # Fetch data
    print("\nFetching price data...")
    data = {}
    for sym in SYMBOLS:
        try:
            df = yf.download(sym, start=START, end=END, progress=False)
            if df is not None and len(df) > 200:
                # Flatten multi-level columns if needed
                if hasattr(df.columns, 'levels') and df.columns.nlevels > 1:
                    df.columns = df.columns.get_level_values(0)
                data[sym] = df
                print(f"  {sym}: {len(df)} bars ({df.index[0].date()} to {df.index[-1].date()})")
            else:
                print(f"  {sym}: SKIPPED (insufficient data)")
        except Exception as e:
            print(f"  {sym}: ERROR - {e}")

    print(f"\nLoaded {len(data)} symbols. Running {len(STRATEGIES)} strategies...\n")

    all_results = {"in_sample": {}, "out_of_sample": {}, "full": {}}
    all_trades = {}

    for strat_name, strat_fn in STRATEGIES.items():
        print(f"-- {strat_name} --")
        is_trades = []
        oos_trades = []
        full_trades = []

        for sym, df in data.items():
            # Full period
            trades_full = backtest_strategy(df, strat_fn, sym, "full")
            full_trades.extend(trades_full)

            # In-sample (train)
            df_is = df[df.index < SPLIT_DATE]
            if len(df_is) > 200:
                trades_is = backtest_strategy(df_is, strat_fn, sym, "in_sample")
                is_trades.extend(trades_is)

            # Out-of-sample (test)
            df_oos = df[df.index >= SPLIT_DATE]
            if len(df_oos) > 50:
                trades_oos = backtest_strategy(df_oos, strat_fn, sym, "out_of_sample")
                oos_trades.extend(trades_oos)

        stats_is = analyze_trades(is_trades, strat_name)
        stats_oos = analyze_trades(oos_trades, strat_name)
        stats_full = analyze_trades(full_trades, strat_name)

        all_results["in_sample"][strat_name] = stats_is
        all_results["out_of_sample"][strat_name] = stats_oos
        all_results["full"][strat_name] = stats_full
        all_trades[strat_name] = full_trades

        if stats_oos:
            flag = "***" if stats_oos["win_rate"] >= 60 and stats_oos["profit_factor"] >= 1.3 else ""
            print(f"  OOS: {stats_oos['total_trades']:>4} trades | WR {stats_oos['win_rate']:>5.1f}% | "
                  f"Avg {stats_oos['avg_pnl']:>+7.3f}% | PF {stats_oos['profit_factor']:>5.2f} | "
                  f"Sharpe {stats_oos['sharpe']:>5.2f} | Total {stats_oos['total_pnl']:>+8.2f}% {flag}")
        else:
            print("  OOS: No trades")

        if stats_is:
            print(f"  IS:  {stats_is['total_trades']:>4} trades | WR {stats_is['win_rate']:>5.1f}% | "
                  f"Avg {stats_is['avg_pnl']:>+7.3f}% | PF {stats_is['profit_factor']:>5.2f}")
        print()

    # ── Summary Table ──
    print("\n" + "=" * 80)
    print("OUT-OF-SAMPLE RESULTS (2024-2026) — THE ONLY THING THAT MATTERS")
    print("=" * 80)

    oos_list = []
    for name, stats in all_results["out_of_sample"].items():
        if stats:
            oos_list.append(stats)

    oos_list.sort(key=lambda x: x["profit_factor"], reverse=True)

    print(f"\n{'Strategy':<30} {'Trades':>6} {'WR%':>6} {'AvgPnL':>8} {'TotalPnL':>10} {'PF':>6} {'Sharpe':>7} {'MaxDD':>8} {'AvgHold':>8}")
    print("-" * 95)

    for s in oos_list:
        flag = " <<<" if s["win_rate"] >= 58 and s["profit_factor"] >= 1.2 and s["total_trades"] >= 20 else ""
        print(f"{s['strategy']:<30} {s['total_trades']:>6} {s['win_rate']:>5.1f}% {s['avg_pnl']:>+7.3f}% "
              f"{s['total_pnl']:>+9.2f}% {s['profit_factor']:>5.2f} {s['sharpe']:>6.2f} "
              f"{s['max_drawdown']:>+7.2f}% {s['avg_hold_days']:>6.1f}d{flag}")

    # ── Walk-Forward Degradation Check ──
    print("\n" + "=" * 80)
    print("WALK-FORWARD DEGRADATION CHECK (IS vs OOS)")
    print("=" * 80)
    print(f"\n{'Strategy':<30} {'IS WR':>7} {'OOS WR':>7} {'Degrad':>8} {'IS PF':>7} {'OOS PF':>7} {'Verdict':>10}")
    print("-" * 80)

    for name in STRATEGIES:
        is_s = all_results["in_sample"].get(name)
        oos_s = all_results["out_of_sample"].get(name)
        if is_s and oos_s:
            wr_deg = oos_s["win_rate"] - is_s["win_rate"]
            if oos_s["win_rate"] >= is_s["win_rate"] * 0.85 and oos_s["profit_factor"] >= 1.1:
                verdict = "ROBUST"
            elif oos_s["win_rate"] >= is_s["win_rate"] * 0.7:
                verdict = "OKAY"
            else:
                verdict = "OVERFIT"
            print(f"{name:<30} {is_s['win_rate']:>6.1f}% {oos_s['win_rate']:>6.1f}% {wr_deg:>+7.1f}% "
                  f"{is_s['profit_factor']:>6.2f} {oos_s['profit_factor']:>6.2f} {verdict:>10}")

    # ── Per-Symbol Best Strategy ──
    print("\n" + "=" * 80)
    print("BEST STRATEGY PER SYMBOL (OOS only)")
    print("=" * 80)

    for sym in SYMBOLS:
        best = None
        for name, stats in all_results["out_of_sample"].items():
            if stats and sym in stats.get("by_symbol", {}):
                sym_data = stats["by_symbol"][sym]
                if sym_data["trades"] >= 5:
                    if best is None or sym_data["wr"] > best[1]["wr"]:
                        best = (name, sym_data)
        if best:
            print(f"  {sym:<12} -> {best[0]:<30} WR={best[1]['wr']:>5.1f}% | "
                  f"{best[1]['trades']} trades | Avg={best[1]['avg_pnl']:>+.3f}% | Total={best[1]['total_pnl']:>+.2f}%")
        else:
            print(f"  {sym:<12} -> No strategy with 5+ OOS trades")

    # ── GIC Benchmark ──
    print("\n" + "=" * 80)
    print("vs GIC BENCHMARK (4% annual = +0.011%/day)")
    print("=" * 80)

    gic_daily = 0.011
    for s in oos_list:
        if s["total_trades"] > 0:
            days_active = sum(t["hold_days"] for t in all_trades[s["strategy"]] if t["period"] == "full")
            gic_equiv = gic_daily * days_active
            beat = "BEATS GIC" if s["total_pnl"] > gic_equiv else "LOSES TO GIC"
            print(f"  {s['strategy']:<30} +{s['total_pnl']:>8.2f}% vs GIC +{gic_equiv:>6.1f}% → {beat}")

    # Save results
    output = {
        "run_date": datetime.now().isoformat(),
        "config": {
            "symbols": SYMBOLS,
            "period": f"{START} to {END}",
            "split": SPLIT_DATE,
            "fee": FEE_PCT
        },
        "out_of_sample": {k: v for k, v in all_results["out_of_sample"].items() if v},
        "in_sample": {k: v for k, v in all_results["in_sample"].items() if v},
        "full": {k: v for k, v in all_results["full"].items() if v}
    }

    out_path = Path("tmp/crypto_backtest_results.json")
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nResults saved to {out_path}")

    # ── FINAL VERDICT ──
    print("\n" + "=" * 80)
    print("FINAL VERDICT: RELIABLE CRYPTO STRATEGIES")
    print("=" * 80)

    reliable = [s for s in oos_list if s["win_rate"] >= 55 and s["profit_factor"] >= 1.1 and s["total_trades"] >= 15]

    if reliable:
        print("\nSTRATEGIES THAT PASS ALL FILTERS (WR>=55%, PF>=1.1, 15+ OOS trades):\n")
        for i, s in enumerate(reliable, 1):
            print(f"  {i}. {s['strategy']}")
            print(f"     Win Rate: {s['win_rate']}% | Profit Factor: {s['profit_factor']} | Sharpe: {s['sharpe']}")
            print(f"     Avg PnL/trade: {s['avg_pnl']:+.3f}% | Total: {s['total_pnl']:+.2f}% | Trades: {s['total_trades']}")
            print(f"     Avg Win: {s['avg_win']:+.3f}% | Avg Loss: {s['avg_loss']:+.3f}% | MaxDD: {s['max_drawdown']:+.2f}%")
            print()
    else:
        print("\nNO STRATEGY passed all filters on out-of-sample crypto data.")
        print("This is honest — crypto is hard to predict reliably.")

if __name__ == "__main__":
    main()
