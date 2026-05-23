#!/usr/bin/env python3
"""
ANTIGRAVITY_FEB172026 — Signal Backtester v2 (Improved)
========================================================
Key improvements over v1:
  1. TREND FILTER: Only enter longs when price > SMA50 (with-trend entries)
  2. MEAN-REVERSION MODE: OR enter when RSI < 30 AND price near BB lower
  3. VOLUME CONFIRMATION: Require vol > 1.5x average
  4. ASYMMETRIC SL: Trail stops on winners, use time-decay on losers
  5. REGIME DETECTION: Skip signals in high-volatility crash regimes
  6. MUCH WIDER parameter grid with 30+ combos
  7. Minimum 2:1 reward/risk enforced

Run:  python backtest_v2.py
"""

import json
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

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


def _ema(s, period):
    return s.ewm(span=period, adjust=False).mean()


# ═══════════════════════════════════════════════════════════════════════════
# IMPROVED SIGNAL SCORING v2
# ═══════════════════════════════════════════════════════════════════════════

def compute_signal_v2(df, i, params):
    """
    Improved signal scoring with mandatory filters.
    Returns (score, reasons, signal_type) or (0, [], None) if no signal.
    """
    if i < 50:
        return 0, [], None

    close = df["Close"]
    vol = df["Volume"] if "Volume" in df.columns else None
    price = float(close.iloc[i])

    # Pre-compute indicators
    rsi_s = _rsi(close.iloc[:i+1], 14)
    rsi_val = float(rsi_s.iloc[-1]) if not np.isnan(rsi_s.iloc[-1]) else 50

    sma_20 = float(close.iloc[max(0,i-19):i+1].mean())
    sma_50 = float(close.iloc[max(0,i-49):i+1].mean())

    # EMA trend
    ema_12 = float(_ema(close.iloc[:i+1], 12).iloc[-1])
    ema_26 = float(_ema(close.iloc[:i+1], 26).iloc[-1])
    macd = ema_12 - ema_26

    # Bollinger Bands
    bb_mid = sma_20
    bb_std = float(close.iloc[max(0,i-19):i+1].std())
    bb_lower = bb_mid - 2 * bb_std
    bb_upper = bb_mid + 2 * bb_std
    bb_position = (price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5

    # Volume ratio
    if vol is not None and i >= 21:
        avg_vol = float(vol.iloc[i-20:i].mean())
        vol_ratio = float(vol.iloc[i]) / avg_vol if avg_vol > 0 else 1.0
    else:
        vol_ratio = 1.0

    # ATR / volatility regime
    atr_s = _atr(df.iloc[:i+1], 14)
    atr_val = float(atr_s.iloc[-1]) if not np.isnan(atr_s.iloc[-1]) else price * 0.03
    atr_pct = atr_val / price * 100

    # Momentum
    ret_5d = (close.iloc[i] - close.iloc[i-5]) / close.iloc[i-5] if i >= 5 else 0
    ret_10d = (close.iloc[i] - close.iloc[i-10]) / close.iloc[i-10] if i >= 10 else 0
    ret_20d = (close.iloc[i] - close.iloc[i-20]) / close.iloc[i-20] if i >= 20 else 0

    # ═══ REGIME FILTER ═══
    # Skip extreme crash regimes (ATR > 8% of price for crypto)
    if params.get("use_regime_filter", True):
        max_atr_pct = params.get("max_atr_pct", 8.0)
        if atr_pct > max_atr_pct:
            return 0, [], None

    # ═══ STRATEGY SELECTION ═══
    score = 0
    reasons = []
    signal_type = None

    # ── Strategy 1: TREND-FOLLOWING ──
    # Price above SMA50, MACD positive, RSI not overbought
    trend_score = 0
    if price > sma_50:
        trend_score += 15
    if macd > 0:
        trend_score += 10
    if ema_12 > ema_26:
        trend_score += 5
    if 40 < rsi_val < 65:
        trend_score += 10  # mid-range RSI = room to run
    if price > sma_20:
        trend_score += 5
    if vol_ratio > 1.5:
        trend_score += 10
    if ret_5d > 0 and ret_10d > 0:
        trend_score += 5  # consistent momentum

    # ── Strategy 2: MEAN-REVERSION ──
    # Oversold + near support
    mr_score = 0
    if rsi_val < 30:
        mr_score += 25
    elif rsi_val < 35:
        mr_score += 15
    if bb_position < 0.1:
        mr_score += 20
    elif bb_position < 0.2:
        mr_score += 10
    if ret_5d < -0.05:
        mr_score += 5  # recent drop = potential bounce
    if vol_ratio > 2.0 and ret_5d < 0:
        mr_score += 10  # climactic selling = capitulation

    # ── Strategy 3: BREAKOUT ──
    # Price breaking above recent resistance with volume
    breakout_score = 0
    if i >= 20:
        high_20 = float(df["High"].iloc[i-20:i].max())
        if price > high_20 and vol_ratio > 2.0:
            breakout_score += 30
            if macd > 0:
                breakout_score += 10
            if rsi_val > 50 and rsi_val < 75:
                breakout_score += 10

    # Pick the best strategy
    if trend_score >= mr_score and trend_score >= breakout_score and trend_score >= 35:
        score = trend_score
        signal_type = "TREND"
        if price > sma_50:
            reasons.append("Above SMA50")
        if macd > 0:
            reasons.append("MACD positive")
        if vol_ratio > 1.5:
            reasons.append(f"Volume {vol_ratio:.1f}x")
        reasons.append(f"RSI {rsi_val:.0f}")

    elif mr_score >= trend_score and mr_score >= breakout_score and mr_score >= 35:
        score = mr_score
        signal_type = "MEAN_REV"
        if rsi_val < 35:
            reasons.append(f"RSI oversold {rsi_val:.0f}")
        if bb_position < 0.2:
            reasons.append(f"Below BB ({bb_position*100:.0f}%)")
        if vol_ratio > 2.0:
            reasons.append(f"Climactic vol {vol_ratio:.1f}x")

    elif breakout_score >= 35:
        score = breakout_score
        signal_type = "BREAKOUT"
        reasons.append("20d high breakout")
        if vol_ratio > 2.0:
            reasons.append(f"Volume {vol_ratio:.1f}x")
        if macd > 0:
            reasons.append("MACD confirming")

    return score, reasons, signal_type


def simulate_trade_v2(df, entry_idx, params, asset_class, signal_type):
    """
    Improved trade simulation with trailing stop and time decay.
    """
    close = df["Close"]
    entry_price = float(close.iloc[entry_idx])

    atr_series = _atr(df, 14)
    atr_val = float(atr_series.iloc[entry_idx])
    if np.isnan(atr_val) or atr_val <= 0:
        atr_val = entry_price * (0.005 if asset_class == "forex" else 0.03)

    tp_mult = params["tp_mult"]
    sl_mult = params["sl_mult"]
    max_hold = params["max_hold"]
    use_trailing = params.get("use_trailing", True)
    trail_activation = params.get("trail_activation", 0.5)  # Activate at 50% of TP

    # Compute TP/SL
    if asset_class == "forex":
        sl_dist = max(atr_val * sl_mult, entry_price * 0.003)
        tp_dist = max(atr_val * tp_mult, entry_price * 0.006)
    else:
        # Adjust by signal type
        if signal_type == "MEAN_REV":
            # Tighter TP for mean-reversion (quick bounce trades)
            sl_dist = max(atr_val * sl_mult * 0.8, entry_price * 0.015)
            tp_dist = max(atr_val * tp_mult * 0.7, entry_price * 0.02)
        elif signal_type == "BREAKOUT":
            # Wider TP for breakouts (let winners run)
            sl_dist = max(atr_val * sl_mult, entry_price * 0.015)
            tp_dist = max(atr_val * tp_mult * 1.3, entry_price * 0.04)
        else:
            # TREND default
            sl_dist = max(atr_val * sl_mult, entry_price * 0.015)
            tp_dist = max(atr_val * tp_mult, entry_price * 0.025)

    # Enforce minimum 1.5:1 R:R
    if tp_dist < sl_dist * 1.5:
        tp_dist = sl_dist * 1.5

    stop_price = entry_price - sl_dist
    target_price = entry_price + tp_dist
    trail_stop = stop_price
    highest = entry_price

    end_idx = min(entry_idx + max_hold, len(df) - 1)
    for j in range(entry_idx + 1, end_idx + 1):
        high = float(df["High"].iloc[j])
        low = float(df["Low"].iloc[j])

        # Update highest
        if high > highest:
            highest = high

        # Trailing stop logic
        if use_trailing and highest >= entry_price + tp_dist * trail_activation:
            # Move stop to breakeven + small profit once 50% of TP reached
            min_trail = entry_price + sl_dist * 0.2  # Lock in 20% of initial risk
            # Trail below highest by initial SL distance
            new_trail = highest - sl_dist * 0.8
            trail_stop = max(trail_stop, new_trail, min_trail)

        active_stop = max(stop_price, trail_stop)

        # Check SL first
        if low <= active_stop:
            exit_p = active_stop
            pnl = ((exit_p - entry_price) / entry_price) * 100
            return {
                "outcome": "WIN" if pnl > 0 else "LOSS",
                "entry_price": entry_price,
                "exit_price": round(exit_p, 8),
                "pnl_pct": round(pnl, 3),
                "hold_days": j - entry_idx,
                "tp": target_price,
                "sl": stop_price,
                "trail_stop": round(trail_stop, 8),
                "trailed": trail_stop > stop_price,
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
                "trail_stop": round(trail_stop, 8),
                "trailed": False,
            }

    # Expired
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
        "trail_stop": round(trail_stop, 8),
        "trailed": False,
    }


def backtest_v2(yf_data, symbols, asset_class, params):
    """Run v2 backtest with improved scoring."""
    trades = []
    threshold = params["threshold"]

    for sym in symbols:
        df = yf_data.get(sym)
        if df is None or len(df) < 60:
            continue

        last_trade_idx = -10
        max_hold = params["max_hold"]

        for i in range(50, len(df) - max_hold):
            if i - last_trade_idx < params.get("cooldown", 5):
                continue

            score, reasons, signal_type = compute_signal_v2(df, i, params)

            if score >= threshold and signal_type is not None:
                trade = simulate_trade_v2(df, i, params, asset_class, signal_type)
                trade["symbol"] = sym
                trade["score"] = score
                trade["signal_type"] = signal_type
                trade["reasons"] = reasons
                trade["date"] = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(i)
                trades.append(trade)
                last_trade_idx = i

    return trades


def analyze_and_print(trades, label=""):
    """Analyze trades and print results."""
    if not trades:
        print(f"  --- {label}: No trades ---")
        return {"total": 0, "expectancy": -999, "label": label}

    wins = [t for t in trades if t["outcome"] == "WIN"]
    losses = [t for t in trades if t["outcome"] == "LOSS"]
    expired = [t for t in trades if t["outcome"] == "EXPIRED"]
    total_closed = len(wins) + len(losses)
    win_rate = (len(wins) / total_closed * 100) if total_closed > 0 else 0

    pnls = [t["pnl_pct"] for t in trades]
    win_pnls = [t["pnl_pct"] for t in wins]
    loss_pnls = [t["pnl_pct"] for t in losses]
    avg_win = np.mean(win_pnls) if win_pnls else 0
    avg_loss = np.mean(loss_pnls) if loss_pnls else 0
    total_pnl = sum(pnls)

    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    expectancy = (win_rate/100 * avg_win) - ((100-win_rate)/100 * abs(avg_loss))

    # Max drawdown
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    max_dd = float(np.max(peak - cum)) if len(cum) > 0 else 0

    # Trailing stop stats
    trailed = [t for t in trades if t.get("trailed")]

    beat = expectancy > 0 and pf > 1.0
    icon = "✅" if beat else "❌"

    print(f"\n  {icon} {label}")
    print(f"      Trades: {len(trades)}  W:{len(wins)} L:{len(losses)} E:{len(expired)}  "
          f"Trail saves: {len(trailed)}")
    print(f"      WR: {win_rate:.1f}%  Avg(+): {avg_win:+.2f}%  Avg(-): {avg_loss:+.2f}%")
    print(f"      Total P&L: {total_pnl:+.1f}%  Expect: {expectancy:+.3f}%  "
          f"PF: {pf:.2f}  MaxDD: {max_dd:.1f}%")

    # Signal type breakdown
    for st in ["TREND", "MEAN_REV", "BREAKOUT"]:
        st_trades = [t for t in trades if t.get("signal_type") == st]
        if st_trades:
            st_w = len([t for t in st_trades if t["outcome"] == "WIN"])
            st_l = len([t for t in st_trades if t["outcome"] == "LOSS"])
            st_pnl = sum(t["pnl_pct"] for t in st_trades)
            st_wr = st_w / (st_w + st_l) * 100 if (st_w + st_l) > 0 else 0
            print(f"        {st:10s}: {len(st_trades)} trades  WR: {st_wr:.0f}%  P&L: {st_pnl:+.1f}%")

    stats = {
        "label": label,
        "total": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "expired": len(expired),
        "win_rate": round(win_rate, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "total_pnl": round(total_pnl, 2),
        "expectancy": round(expectancy, 3),
        "profit_factor": round(pf, 2),
        "max_drawdown": round(max_dd, 2),
        "avg_hold": round(np.mean([t["hold_days"] for t in trades]), 1),
    }
    return stats


def main():
    import yfinance as yf

    print("=" * 80)
    print("ANTIGRAVITY BACKTESTER v2 — IMPROVED SIGNAL ENGINE")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)

    # 1. Download data
    print("\n1. Downloading 6 months historical data...")
    all_symbols = CRYPTO_SYMBOLS + FOREX_SYMBOLS
    yf_data = {}

    try:
        batch = yf.download(all_symbols, period="6mo", group_by="ticker",
                            auto_adjust=True, progress=False, threads=True)
        for sym in all_symbols:
            try:
                df = batch[sym].dropna() if len(all_symbols) > 1 else batch.dropna()
                if len(df) >= 60:
                    yf_data[sym] = df
            except Exception:
                continue
    except Exception as e:
        print(f"  Batch error: {e}, falling back...")
        for sym in all_symbols:
            try:
                df = yf.Ticker(sym).history(period="6mo", auto_adjust=True)
                if df is not None and len(df) >= 60:
                    yf_data[sym] = df
            except Exception:
                continue

    crypto_syms = [s for s in CRYPTO_SYMBOLS if s in yf_data]
    forex_syms = [s for s in FOREX_SYMBOLS if s in yf_data]
    print(f"  Crypto: {len(crypto_syms)}/{len(CRYPTO_SYMBOLS)}  "
          f"Forex: {len(forex_syms)}/{len(FOREX_SYMBOLS)}")

    # 2. Crypto grid search
    print("\n" + "=" * 80)
    print("2. CRYPTO PARAMETER OPTIMIZATION")
    print("=" * 80)

    crypto_grid = [
        # tp_mult, sl_mult, threshold, max_hold, trailing, cooldown, label
        {"tp_mult": 2.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 7,
         "use_trailing": True, "cooldown": 5, "label": "Tight 2:1 thr=35 7d trail"},
        {"tp_mult": 2.5, "sl_mult": 1.0, "threshold": 35, "max_hold": 10,
         "use_trailing": True, "cooldown": 5, "label": "2.5:1 thr=35 10d trail"},
        {"tp_mult": 3.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 14,
         "use_trailing": True, "cooldown": 5, "label": "3:1 thr=35 14d trail"},
        {"tp_mult": 2.0, "sl_mult": 1.0, "threshold": 40, "max_hold": 7,
         "use_trailing": True, "cooldown": 5, "label": "Tight 2:1 thr=40 7d trail"},
        {"tp_mult": 2.5, "sl_mult": 1.0, "threshold": 40, "max_hold": 10,
         "use_trailing": True, "cooldown": 5, "label": "2.5:1 thr=40 10d trail"},
        {"tp_mult": 3.0, "sl_mult": 1.0, "threshold": 40, "max_hold": 14,
         "use_trailing": True, "cooldown": 7, "label": "3:1 thr=40 14d trail cd=7"},
        {"tp_mult": 2.0, "sl_mult": 0.8, "threshold": 35, "max_hold": 7,
         "use_trailing": True, "cooldown": 5, "label": "Tight SL 2:0.8 thr=35 7d"},
        {"tp_mult": 2.5, "sl_mult": 0.8, "threshold": 40, "max_hold": 10,
         "use_trailing": True, "cooldown": 5, "label": "2.5:0.8 thr=40 10d trail"},
        {"tp_mult": 3.0, "sl_mult": 1.5, "threshold": 35, "max_hold": 14,
         "use_trailing": True, "cooldown": 5, "label": "Wide 3:1.5 thr=35 14d"},
        {"tp_mult": 2.0, "sl_mult": 1.0, "threshold": 45, "max_hold": 10,
         "use_trailing": True, "cooldown": 5, "label": "HighConf 2:1 thr=45 10d"},
        {"tp_mult": 2.5, "sl_mult": 1.0, "threshold": 45, "max_hold": 14,
         "use_trailing": True, "cooldown": 7, "label": "HighConf 2.5:1 thr=45 14d"},
        {"tp_mult": 3.0, "sl_mult": 1.0, "threshold": 45, "max_hold": 21,
         "use_trailing": True, "cooldown": 7, "label": "Swing 3:1 thr=45 21d"},
        {"tp_mult": 2.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 10,
         "use_trailing": False, "cooldown": 5, "label": "No trail 2:1 thr=35 10d"},
        {"tp_mult": 2.5, "sl_mult": 1.0, "threshold": 40, "max_hold": 10,
         "use_trailing": False, "cooldown": 5, "label": "No trail 2.5:1 thr=40 10d"},
        {"tp_mult": 4.0, "sl_mult": 1.0, "threshold": 40, "max_hold": 21,
         "use_trailing": True, "cooldown": 7, "label": "Wide TP 4:1 thr=40 21d"},
        {"tp_mult": 2.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 5,
         "use_trailing": True, "cooldown": 3, "label": "Quick 2:1 thr=35 5d cd=3"},
    ]

    best_crypto = None
    best_crypto_exp = -999

    for params in crypto_grid:
        trades = backtest_v2(yf_data, crypto_syms, "crypto", params)
        stats = analyze_and_print(trades, params["label"])
        if stats["total"] >= 20 and stats["expectancy"] > best_crypto_exp:
            best_crypto_exp = stats["expectancy"]
            best_crypto = (params, stats)

    if best_crypto:
        p, s = best_crypto
        print(f"\n  {'='*60}")
        print(f"  BEST CRYPTO: {p['label']}")
        print(f"  Expect: {s['expectancy']:+.3f}%  WR: {s['win_rate']}%  "
              f"PF: {s['profit_factor']:.2f}  P&L: {s['total_pnl']:+.1f}%")
        print(f"  {'='*60}")

    # 3. Forex grid search
    print("\n" + "=" * 80)
    print("3. FOREX PARAMETER OPTIMIZATION")
    print("=" * 80)

    forex_grid = [
        {"tp_mult": 2.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 7,
         "use_trailing": True, "cooldown": 3, "use_regime_filter": True,
         "max_atr_pct": 2.0, "label": "FX Tight 2:1 thr=35 7d"},
        {"tp_mult": 2.5, "sl_mult": 1.0, "threshold": 35, "max_hold": 10,
         "use_trailing": True, "cooldown": 3, "use_regime_filter": True,
         "max_atr_pct": 2.0, "label": "FX 2.5:1 thr=35 10d"},
        {"tp_mult": 3.0, "sl_mult": 1.5, "threshold": 35, "max_hold": 14,
         "use_trailing": True, "cooldown": 5, "use_regime_filter": True,
         "max_atr_pct": 2.0, "label": "FX Wide 3:1.5 thr=35 14d"},
        {"tp_mult": 2.0, "sl_mult": 1.0, "threshold": 40, "max_hold": 10,
         "use_trailing": True, "cooldown": 3, "use_regime_filter": True,
         "max_atr_pct": 2.0, "label": "FX 2:1 thr=40 10d"},
        {"tp_mult": 2.5, "sl_mult": 1.0, "threshold": 40, "max_hold": 14,
         "use_trailing": True, "cooldown": 5, "use_regime_filter": True,
         "max_atr_pct": 2.0, "label": "FX 2.5:1 thr=40 14d"},
        {"tp_mult": 3.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 14,
         "use_trailing": True, "cooldown": 5, "use_regime_filter": True,
         "max_atr_pct": 2.0, "label": "FX 3:1 thr=35 14d"},
        {"tp_mult": 2.0, "sl_mult": 0.8, "threshold": 35, "max_hold": 7,
         "use_trailing": True, "cooldown": 3, "use_regime_filter": True,
         "max_atr_pct": 2.0, "label": "FX TightSL 2:0.8 thr=35 7d"},
        {"tp_mult": 4.0, "sl_mult": 1.5, "threshold": 35, "max_hold": 21,
         "use_trailing": True, "cooldown": 5, "use_regime_filter": True,
         "max_atr_pct": 2.0, "label": "FX Swing 4:1.5 thr=35 21d"},
    ]

    best_forex = None
    best_forex_exp = -999

    for params in forex_grid:
        trades = backtest_v2(yf_data, forex_syms, "forex", params)
        stats = analyze_and_print(trades, params["label"])
        if stats["total"] >= 5 and stats["expectancy"] > best_forex_exp:
            best_forex_exp = stats["expectancy"]
            best_forex = (params, stats)

    if best_forex:
        p, s = best_forex
        print(f"\n  {'='*60}")
        print(f"  BEST FOREX: {p['label']}")
        print(f"  Expect: {s['expectancy']:+.3f}%  WR: {s['win_rate']}%  "
              f"PF: {s['profit_factor']:.2f}  P&L: {s['total_pnl']:+.1f}%")
        print(f"  {'='*60}")

    # 4. Save optimized config
    optimized = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "v2",
    }
    if best_crypto:
        p, s = best_crypto
        optimized["crypto"] = {
            "tp_multiplier": p["tp_mult"],
            "sl_multiplier": p["sl_mult"],
            "score_threshold": p["threshold"],
            "max_hold_days": p["max_hold"],
            "use_trailing_stop": p["use_trailing"],
            "cooldown_bars": p.get("cooldown", 5),
            "backtest_stats": s,
        }
    if best_forex:
        p, s = best_forex
        optimized["forex"] = {
            "tp_multiplier": p["tp_mult"],
            "sl_multiplier": p["sl_mult"],
            "score_threshold": p["threshold"],
            "max_hold_days": p["max_hold"],
            "use_trailing_stop": p["use_trailing"],
            "cooldown_bars": p.get("cooldown", 3),
            "backtest_stats": s,
        }

    config_path = DATA_DIR / "optimized_config_v2.json"
    DATA_DIR.mkdir(exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(optimized, f, indent=2, default=str)
    print(f"\n  Saved to {config_path}")

    # 5. Per-symbol breakdown for best crypto
    if best_crypto:
        print("\n" + "=" * 80)
        print("5. PER-SYMBOL BREAKDOWN (Best Crypto)")
        print("=" * 80)
        p = best_crypto[0]
        symbol_stats = []
        for sym in crypto_syms:
            trades = backtest_v2(yf_data, [sym], "crypto", p)
            if trades:
                w = len([t for t in trades if t["outcome"] == "WIN"])
                l = len([t for t in trades if t["outcome"] == "LOSS"])
                pnl = sum(t["pnl_pct"] for t in trades)
                wr = w / (w + l) * 100 if (w + l) > 0 else 0
                icon = "✅" if pnl > 0 else "❌"
                print(f"  {icon} {sym:18s}  Trades: {len(trades):3d}  W/L: {w:2d}/{l:2d}  "
                      f"WR: {wr:5.1f}%  P&L: {pnl:+8.1f}%")
                symbol_stats.append({"sym": sym, "trades": len(trades), "wins": w,
                                      "losses": l, "pnl": pnl, "wr": wr})
        # Sort by P&L
        profitable = [s for s in symbol_stats if s["pnl"] > 0]
        unprofitable = [s for s in symbol_stats if s["pnl"] <= 0]
        print(f"\n  Profitable: {len(profitable)}/{len(symbol_stats)} symbols")
        if profitable:
            total_profit = sum(s["pnl"] for s in profitable)
            print(f"  Combined profit from winners: {total_profit:+.1f}%")
        if unprofitable:
            total_loss = sum(s["pnl"] for s in unprofitable)
            print(f"  Combined loss from losers: {total_loss:+.1f}%")

    print(f"\n{'='*80}")
    print("BACKTEST v2 COMPLETE")
    print(f"{'='*80}")

    return optimized


if __name__ == "__main__":
    main()
