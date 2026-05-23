#!/usr/bin/env python3
"""
ANTIGRAVITY_FEB172026 — Signal Backtester & Optimizer
======================================================
Validates the signal generation logic against 6 months of real historical data.
Tests every crypto + forex pair, simulating entries at signal triggers and
checking if TP or SL was hit within N days.

Optimizes:
  - ATR multipliers for TP/SL
  - Signal score thresholds
  - Holding periods
  - Per-asset-class parameters

Run:  python backtest_signals.py
"""

import json
import sys
import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

# Asset lists
CRYPTO_SYMBOLS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
    "DOGE-USD", "SHIB-USD", "ATOM-USD", "NEAR-USD", "LTC-USD",
    "BCH-USD", "INJ-USD", "OP-USD", "ARB11841-USD", "SUI20947-USD",
    "PEPE-USD", "BONK-USD", "FLOKI-USD", "WIF-USD", "TIA-USD",
    "FIL-USD", "SEI-USD", "APT21794-USD",
]
FOREX_SYMBOLS = ["EURUSD=X", "GBPUSD=X", "JPY=X", "AUDUSD=X", "CAD=X", "NZDUSD=X", "CHF=X"]


def _rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(df, period=14):
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_signal_score(close, vol, i, atr_val, price):
    """Compute the signal score at bar index i using lookback data."""
    if i < 20:
        return 0, []

    score = 50
    reasons = []

    # RSI
    rsi_s = _rsi(close.iloc[:i+1], 14)
    rsi_val = float(rsi_s.iloc[-1]) if not np.isnan(rsi_s.iloc[-1]) else 50

    if rsi_val < 30:
        score += 15
        reasons.append(f"RSI oversold {rsi_val:.0f}")
    elif rsi_val < 40:
        score += 8
        reasons.append(f"RSI low {rsi_val:.0f}")
    elif rsi_val > 70:
        score -= 10

    # Bollinger Band
    bb_mid = close.iloc[max(0,i-19):i+1].mean()
    bb_std = close.iloc[max(0,i-19):i+1].std()
    bb_lower = bb_mid - 2 * bb_std
    if price < bb_lower:
        score += 12
        reasons.append("Below BB lower")

    # Volume spike
    if i >= 21:
        avg_vol = float(vol.iloc[i-20:i].mean())
        if avg_vol > 0:
            vol_ratio = float(vol.iloc[i]) / avg_vol
            if vol_ratio > 3.0:
                score += 10
                reasons.append(f"Volume {vol_ratio:.1f}x")
            elif vol_ratio > 2.0:
                score += 5
                reasons.append(f"Volume {vol_ratio:.1f}x")

    # SMA trend
    sma_20 = float(close.iloc[max(0,i-19):i+1].mean())
    sma_50 = float(close.iloc[max(0,i-49):i+1].mean()) if i >= 49 else sma_20
    if price > sma_50:
        score += 5
        reasons.append("Above SMA50")

    # Momentum acceleration (jerk)
    if i >= 3:
        d1 = close.iloc[:i+1].pct_change()
        d2 = d1.diff()
        jerk = float(d2.iloc[-1]) if not np.isnan(d2.iloc[-1]) else 0
        if jerk > 0.002:
            score += 7
            reasons.append("Momentum accelerating")

    return score, reasons


def simulate_trade(df, entry_idx, tp_mult, sl_mult, max_hold_days, asset_class):
    """Simulate a trade from entry_idx forward. Returns outcome."""
    close = df["Close"]
    entry_price = float(close.iloc[entry_idx])

    atr_series = _atr(df, 14)
    atr_val = float(atr_series.iloc[entry_idx])
    if np.isnan(atr_val) or atr_val <= 0:
        if asset_class == "forex":
            atr_val = entry_price * 0.005
        else:
            atr_val = entry_price * 0.03

    # TP/SL
    if asset_class == "forex":
        sl_dist = max(atr_val * sl_mult, entry_price * 0.003)
        tp_dist = max(atr_val * tp_mult, entry_price * 0.006)
    else:
        sl_dist = max(atr_val * sl_mult, entry_price * 0.015)
        tp_dist = max(atr_val * tp_mult, entry_price * 0.025)

    stop_price = entry_price - sl_dist
    target_price = entry_price + tp_dist

    # Walk forward
    end_idx = min(entry_idx + max_hold_days, len(df) - 1)
    for j in range(entry_idx + 1, end_idx + 1):
        high = float(df["High"].iloc[j])
        low = float(df["Low"].iloc[j])

        # Check SL first (more conservative)
        if low <= stop_price:
            pnl = ((stop_price - entry_price) / entry_price) * 100
            return {
                "outcome": "LOSS",
                "entry_price": entry_price,
                "exit_price": stop_price,
                "pnl_pct": round(pnl, 3),
                "hold_days": j - entry_idx,
                "tp": target_price,
                "sl": stop_price,
            }

        # Check TP
        if high >= target_price:
            pnl = ((target_price - entry_price) / entry_price) * 100
            return {
                "outcome": "WIN",
                "entry_price": entry_price,
                "exit_price": target_price,
                "pnl_pct": round(pnl, 3),
                "hold_days": j - entry_idx,
                "tp": target_price,
                "sl": stop_price,
            }

    # Expired — neither TP nor SL hit
    final_price = float(close.iloc[end_idx])
    pnl = ((final_price - entry_price) / entry_price) * 100
    return {
        "outcome": "EXPIRED",
        "entry_price": entry_price,
        "exit_price": final_price,
        "pnl_pct": round(pnl, 3),
        "hold_days": end_idx - entry_idx,
        "tp": target_price,
        "sl": stop_price,
    }


def backtest_params(yf_data, symbols, asset_class, tp_mult, sl_mult,
                    score_threshold, max_hold_days):
    """Run backtest with given parameters across all symbols."""
    all_trades = []

    for sym in symbols:
        df = yf_data.get(sym)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        vol = df["Volume"] if "Volume" in df.columns else pd.Series(np.zeros(len(df)))

        # Scan for signals every day from bar 30 onward
        # (need 20 bars lookback + 10 bars forward minimum)
        last_trade_idx = -10  # cooldown between signals
        for i in range(30, len(df) - max_hold_days):
            if i - last_trade_idx < 5:  # 5-bar cooldown
                continue

            price = float(close.iloc[i])
            atr_s = _atr(df, 14)
            atr_val = float(atr_s.iloc[i]) if not np.isnan(atr_s.iloc[i]) else price * 0.03

            score, reasons = compute_signal_score(close, vol, i, atr_val, price)

            if score >= score_threshold:
                trade = simulate_trade(df, i, tp_mult, sl_mult, max_hold_days, asset_class)
                trade["symbol"] = sym
                trade["score"] = score
                trade["bar_idx"] = i
                trade["date"] = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(i)
                trade["reasons"] = reasons
                all_trades.append(trade)
                last_trade_idx = i

    return all_trades


def analyze_results(trades, label=""):
    """Analyze backtest results and return stats."""
    if not trades:
        return {"total": 0, "win_rate": 0}

    wins = [t for t in trades if t["outcome"] == "WIN"]
    losses = [t for t in trades if t["outcome"] == "LOSS"]
    expired = [t for t in trades if t["outcome"] == "EXPIRED"]

    total_closed = len(wins) + len(losses)
    win_rate = (len(wins) / total_closed * 100) if total_closed > 0 else 0

    all_pnls = [t["pnl_pct"] for t in trades]
    win_pnls = [t["pnl_pct"] for t in wins]
    loss_pnls = [t["pnl_pct"] for t in losses]

    avg_win = np.mean(win_pnls) if win_pnls else 0
    avg_loss = np.mean(loss_pnls) if loss_pnls else 0
    total_pnl = sum(all_pnls)
    avg_pnl = np.mean(all_pnls) if all_pnls else 0

    # Profit factor
    gross_profit = sum(p for p in all_pnls if p > 0)
    gross_loss = abs(sum(p for p in all_pnls if p < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
    loss_rate = 100 - win_rate
    expectancy = (win_rate/100 * avg_win) - (loss_rate/100 * abs(avg_loss))

    # Max drawdown (sequential)
    cumulative = np.cumsum(all_pnls)
    peak = np.maximum.accumulate(cumulative)
    drawdown = peak - cumulative
    max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0

    avg_hold = np.mean([t["hold_days"] for t in trades]) if trades else 0

    return {
        "label": label,
        "total": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "expired": len(expired),
        "win_rate": round(win_rate, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(avg_pnl, 2),
        "profit_factor": round(profit_factor, 2),
        "expectancy": round(expectancy, 3),
        "max_drawdown": round(max_dd, 2),
        "avg_hold_days": round(avg_hold, 1),
    }


def print_results(stats):
    """Print formatted backtest results."""
    if stats["total"] == 0:
        print(f"  {stats.get('label', '?')}: No trades")
        return

    beat_market = stats["expectancy"] > 0 and stats["profit_factor"] > 1.2
    icon = "✅" if beat_market else "❌"

    print(f"\n  {icon} {stats.get('label', '')}:")
    print(f"      Trades: {stats['total']}  |  "
          f"Win: {stats['wins']}  Loss: {stats['losses']}  Exp: {stats['expired']}")
    print(f"      Win Rate: {stats['win_rate']}%  |  "
          f"Avg Win: {stats['avg_win']:+.2f}%  |  Avg Loss: {stats['avg_loss']:+.2f}%")
    print(f"      Total P&L: {stats['total_pnl']:+.2f}%  |  "
          f"Avg P&L: {stats['avg_pnl']:+.2f}%  |  Expectancy: {stats['expectancy']:+.3f}%")
    print(f"      Profit Factor: {stats['profit_factor']:.2f}  |  "
          f"Max DD: {stats['max_drawdown']:.2f}%  |  Avg Hold: {stats['avg_hold_days']:.1f}d")


def main():
    import yfinance as yf

    print("=" * 80)
    print("ANTIGRAVITY SIGNAL BACKTESTER & OPTIMIZER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)

    # 1. Download historical data
    print("\n1. Downloading 6 months of historical data...")
    all_symbols = CRYPTO_SYMBOLS + FOREX_SYMBOLS
    yf_data = {}

    try:
        batch = yf.download(all_symbols, period="6mo", group_by="ticker",
                            auto_adjust=True, progress=False, threads=True)
        for sym in all_symbols:
            try:
                if len(all_symbols) > 1:
                    df = batch[sym].dropna()
                else:
                    df = batch.dropna()
                if len(df) >= 50:
                    yf_data[sym] = df
            except Exception:
                continue
    except Exception as e:
        print(f"  Batch error: {e}")

    print(f"  Loaded {len(yf_data)} symbols with 50+ bars")

    crypto_syms = [s for s in CRYPTO_SYMBOLS if s in yf_data]
    forex_syms = [s for s in FOREX_SYMBOLS if s in yf_data]
    print(f"  Crypto: {len(crypto_syms)} symbols  |  Forex: {len(forex_syms)} symbols")

    # 2. Parameter grid search
    print("\n" + "=" * 80)
    print("2. OPTIMIZING CRYPTO PARAMETERS")
    print("=" * 80)

    # Test different TP/SL multiplier combos
    crypto_configs = [
        # (tp_mult, sl_mult, threshold, max_hold, label)
        (2.0, 1.0, 55, 10, "Conservative: TP=2.0x SL=1.0x thr=55 hold=10d"),
        (2.5, 1.5, 55, 10, "Balanced:     TP=2.5x SL=1.5x thr=55 hold=10d"),
        (3.0, 1.5, 55, 14, "Aggressive:   TP=3.0x SL=1.5x thr=55 hold=14d"),
        (2.0, 1.0, 60, 10, "High-Conf:    TP=2.0x SL=1.0x thr=60 hold=10d"),
        (2.5, 1.5, 60, 10, "High-Conf B:  TP=2.5x SL=1.5x thr=60 hold=10d"),
        (3.0, 1.5, 60, 14, "High-Conf C:  TP=3.0x SL=1.5x thr=60 hold=14d"),
        (2.0, 1.0, 65, 7,  "Elite Short:  TP=2.0x SL=1.0x thr=65 hold=7d"),
        (2.5, 1.0, 65, 10, "Elite Med:    TP=2.5x SL=1.0x thr=65 hold=10d"),
        (3.0, 2.0, 55, 14, "Wide:         TP=3.0x SL=2.0x thr=55 hold=14d"),
        (1.5, 0.75, 55, 7, "Scalper:      TP=1.5x SL=0.75 thr=55 hold=7d"),
        (2.0, 0.8, 60, 10, "Tight SL:     TP=2.0x SL=0.8x thr=60 hold=10d"),
        (3.5, 1.5, 60, 21, "Swing:        TP=3.5x SL=1.5x thr=60 hold=21d"),
    ]

    best_crypto = None
    best_crypto_expectancy = -999

    for tp_m, sl_m, thr, hold, label in crypto_configs:
        trades = backtest_params(yf_data, crypto_syms, "crypto", tp_m, sl_m, thr, hold)
        stats = analyze_results(trades, label)
        print_results(stats)
        if stats["total"] >= 10 and stats["expectancy"] > best_crypto_expectancy:
            best_crypto_expectancy = stats["expectancy"]
            best_crypto = (tp_m, sl_m, thr, hold, label, stats)

    if best_crypto:
        tp_m, sl_m, thr, hold, label, stats = best_crypto
        print(f"\n  🏆 BEST CRYPTO CONFIG: {label}")
        print(f"     Expectancy: {stats['expectancy']:+.3f}%  |  "
              f"Win Rate: {stats['win_rate']}%  |  PF: {stats['profit_factor']:.2f}")

    # 3. Forex optimization
    print("\n" + "=" * 80)
    print("3. OPTIMIZING FOREX PARAMETERS")
    print("=" * 80)

    forex_configs = [
        (2.0, 1.0, 55, 10, "Conservative: TP=2.0x SL=1.0x thr=55 hold=10d"),
        (2.5, 1.5, 55, 10, "Balanced:     TP=2.5x SL=1.5x thr=55 hold=10d"),
        (3.0, 1.5, 55, 14, "Aggressive:   TP=3.0x SL=1.5x thr=55 hold=14d"),
        (2.0, 1.0, 60, 10, "High-Conf:    TP=2.0x SL=1.0x thr=60 hold=10d"),
        (3.0, 2.0, 55, 14, "Wide:         TP=3.0x SL=2.0x thr=55 hold=14d"),
        (1.5, 0.75, 55, 5, "Scalper:      TP=1.5x SL=0.75 thr=55 hold=5d"),
        (2.0, 0.8, 60, 7,  "Tight SL:     TP=2.0x SL=0.8x thr=60 hold=7d"),
        (3.0, 1.5, 60, 14, "High-Conf A:  TP=3.0x SL=1.5x thr=60 hold=14d"),
        (2.5, 1.0, 55, 7,  "Quick:        TP=2.5x SL=1.0x thr=55 hold=7d"),
        (4.0, 2.0, 55, 21, "Swing:        TP=4.0x SL=2.0x thr=55 hold=21d"),
    ]

    best_forex = None
    best_forex_expectancy = -999

    for tp_m, sl_m, thr, hold, label in forex_configs:
        trades = backtest_params(yf_data, forex_syms, "forex", tp_m, sl_m, thr, hold)
        stats = analyze_results(trades, label)
        print_results(stats)
        if stats["total"] >= 5 and stats["expectancy"] > best_forex_expectancy:
            best_forex_expectancy = stats["expectancy"]
            best_forex = (tp_m, sl_m, thr, hold, label, stats)

    if best_forex:
        tp_m, sl_m, thr, hold, label, stats = best_forex
        print(f"\n  🏆 BEST FOREX CONFIG: {label}")
        print(f"     Expectancy: {stats['expectancy']:+.3f}%  |  "
              f"Win Rate: {stats['win_rate']}%  |  PF: {stats['profit_factor']:.2f}")

    # 4. Summary + save optimized config
    print("\n" + "=" * 80)
    print("4. FINAL OPTIMIZED CONFIGURATION")
    print("=" * 80)

    optimized = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "crypto": {
            "tp_multiplier": best_crypto[0] if best_crypto else 2.5,
            "sl_multiplier": best_crypto[1] if best_crypto else 1.5,
            "score_threshold": best_crypto[2] if best_crypto else 60,
            "max_hold_days": best_crypto[3] if best_crypto else 10,
            "backtest_stats": best_crypto[5] if best_crypto else {},
        },
        "forex": {
            "tp_multiplier": best_forex[0] if best_forex else 2.0,
            "sl_multiplier": best_forex[1] if best_forex else 1.0,
            "score_threshold": best_forex[2] if best_forex else 55,
            "max_hold_days": best_forex[3] if best_forex else 10,
            "backtest_stats": best_forex[5] if best_forex else {},
        },
    }

    if best_crypto:
        s = best_crypto[5]
        print(f"\n  CRYPTO: TP={best_crypto[0]}x ATR  SL={best_crypto[1]}x ATR  "
              f"Threshold={best_crypto[2]}  Hold={best_crypto[3]}d")
        print(f"    Win Rate: {s['win_rate']}%  |  Expectancy: {s['expectancy']:+.3f}%  |  "
              f"PF: {s['profit_factor']:.2f}  |  Total P&L: {s['total_pnl']:+.2f}%")

    if best_forex:
        s = best_forex[5]
        print(f"\n  FOREX:  TP={best_forex[0]}x ATR  SL={best_forex[1]}x ATR  "
              f"Threshold={best_forex[2]}  Hold={best_forex[3]}d")
        print(f"    Win Rate: {s['win_rate']}%  |  Expectancy: {s['expectancy']:+.3f}%  |  "
              f"PF: {s['profit_factor']:.2f}  |  Total P&L: {s['total_pnl']:+.2f}%")

    config_path = DATA_DIR / "optimized_config.json"
    DATA_DIR.mkdir(exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(optimized, f, indent=2, default=str)
    print(f"\n  Config saved to {config_path}")

    # 5. Per-symbol breakdown for best crypto config
    if best_crypto:
        print("\n" + "=" * 80)
        print("5. PER-SYMBOL BREAKDOWN (Best Crypto Config)")
        print("=" * 80)
        tp_m, sl_m, thr, hold = best_crypto[:4]
        for sym in crypto_syms:
            trades = backtest_params(yf_data, [sym], "crypto", tp_m, sl_m, thr, hold)
            if trades:
                w = len([t for t in trades if t["outcome"] == "WIN"])
                l = len([t for t in trades if t["outcome"] == "LOSS"])
                total_pnl = sum(t["pnl_pct"] for t in trades)
                wr = w / (w + l) * 100 if (w + l) > 0 else 0
                icon = "✅" if total_pnl > 0 else "❌"
                print(f"  {icon} {sym:15s}  W/L: {w}/{l}  WR: {wr:.0f}%  P&L: {total_pnl:+.1f}%")

    print(f"\n{'=' * 80}")
    print("BACKTEST COMPLETE")
    print(f"{'=' * 80}")

    return optimized


if __name__ == "__main__":
    main()
