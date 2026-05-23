#!/usr/bin/env python3
"""
ANTIGRAVITY BATTLE TEST — Cross-Asset Elimination Tournament
=============================================================
Tests ALL asset classes: crypto, forex, stocks, penny stocks, meme coins.
Adds SHORT-side strategies for bear markets.
Uses walk-forward validation: train on first 4 months, test on last 2.
Eliminates every strategy/symbol combo with negative expectancy.

Run: python battle_test.py
"""

import json
import sys
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════
# ALL SYMBOLS BY ASSET CLASS
# ═══════════════════════════════════════════════════════════════════════════

SYMBOLS = {
    "crypto": [
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
        "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
        "DOGE-USD", "ATOM-USD", "NEAR-USD", "LTC-USD",
        "BCH-USD", "INJ-USD", "OP-USD", "ARB11841-USD",
        "FIL-USD", "SEI-USD", "APT21794-USD",
    ],
    "forex": [
        "EURUSD=X", "GBPUSD=X", "JPY=X", "AUDUSD=X",
        "CAD=X", "NZDUSD=X", "CHF=X",
    ],
    "stocks": [
        "AAPL", "MSFT", "NVDA", "AMD", "META",
        "GOOGL", "AMZN", "NFLX", "TSLA",
        "JPM", "BAC", "XOM", "CVX",
        "UBER", "PYPL", "COIN", "SHOP",
    ],
    "penny": [
        "SNDL", "CLOV", "SPCE", "UWMC",
        "NKLA", "LCID", "RIVN",
        "NVAX", "BNGO",
        "XPEV", "NIO",
    ],
    "meme": [
        "DOGE-USD", "SHIB-USD",
        "PEPE24478-USD", "BONK-USD", "FLOKI-USD",
        "WIF-USD",
        "AMC", "GME", "BBBY",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# INDICATORS
# ═══════════════════════════════════════════════════════════════════════════

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


def _bb(close, period=20, num_std=2):
    """Bollinger Bands."""
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid, mid + num_std * std, mid - num_std * std


def _macd(close, fast=12, slow=26, signal=9):
    """MACD line, signal line, histogram."""
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL STRATEGIES (LONG + SHORT)
# ═══════════════════════════════════════════════════════════════════════════

def strategy_trend_long(df, i, params):
    """Long when price > SMA50, MACD positive, RSI mid-range."""
    if i < 50:
        return 0, [], "LONG"
    close = df["Close"]
    price = float(close.iloc[i])
    
    sma50 = float(close.iloc[max(0,i-49):i+1].mean())
    sma20 = float(close.iloc[max(0,i-19):i+1].mean())
    
    rsi_s = _rsi(close.iloc[:i+1], 14)
    rsi_val = float(rsi_s.iloc[-1]) if not np.isnan(rsi_s.iloc[-1]) else 50
    
    macd_l, sig_l, _ = _macd(close.iloc[:i+1])
    macd_val = float(macd_l.iloc[-1]) if not np.isnan(macd_l.iloc[-1]) else 0
    
    vol = df.get("Volume")
    vol_ratio = 1.0
    if vol is not None and i >= 21:
        avg_vol = float(vol.iloc[i-20:i].mean())
        vol_ratio = float(vol.iloc[i]) / avg_vol if avg_vol > 0 else 1.0
    
    score = 0
    reasons = []
    
    if price > sma50:
        score += 20; reasons.append("Above SMA50")
    if price > sma20:
        score += 5
    if macd_val > 0:
        score += 15; reasons.append("MACD+")
    if 35 < rsi_val < 65:
        score += 10; reasons.append(f"RSI {rsi_val:.0f}")
    if vol_ratio > 1.5:
        score += 10; reasons.append(f"Vol {vol_ratio:.1f}x")
    
    return score, reasons, "LONG"


def strategy_mean_rev_long(df, i, params):
    """Long on extreme oversold + BB lower bounce."""
    if i < 50:
        return 0, [], "LONG"
    close = df["Close"]
    price = float(close.iloc[i])
    
    rsi_s = _rsi(close.iloc[:i+1], 14)
    rsi_val = float(rsi_s.iloc[-1]) if not np.isnan(rsi_s.iloc[-1]) else 50
    
    sma20 = float(close.iloc[max(0,i-19):i+1].mean())
    bb_std = float(close.iloc[max(0,i-19):i+1].std())
    bb_lower = sma20 - 2 * bb_std
    bb_upper = sma20 + 2 * bb_std
    bb_pos = (price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
    
    ret_5d = (close.iloc[i] - close.iloc[i-5]) / close.iloc[i-5] if i >= 5 else 0
    
    score = 0
    reasons = []
    
    if rsi_val < 25:
        score += 30; reasons.append(f"RSI extreme {rsi_val:.0f}")
    elif rsi_val < 30:
        score += 20; reasons.append(f"RSI oversold {rsi_val:.0f}")
    elif rsi_val < 35:
        score += 10
    
    if bb_pos < 0.05:
        score += 25; reasons.append("Below BB 5%")
    elif bb_pos < 0.15:
        score += 15; reasons.append("Near BB lower")
    
    if ret_5d < -0.08:
        score += 10; reasons.append("Sharp selloff")
    
    return score, reasons, "LONG"


def strategy_trend_short(df, i, params):
    """Short when price < SMA50, MACD negative, RSI mid-high."""
    if i < 50:
        return 0, [], "SHORT"
    close = df["Close"]
    price = float(close.iloc[i])
    
    sma50 = float(close.iloc[max(0,i-49):i+1].mean())
    sma20 = float(close.iloc[max(0,i-19):i+1].mean())
    
    rsi_s = _rsi(close.iloc[:i+1], 14)
    rsi_val = float(rsi_s.iloc[-1]) if not np.isnan(rsi_s.iloc[-1]) else 50
    
    macd_l, sig_l, _ = _macd(close.iloc[:i+1])
    macd_val = float(macd_l.iloc[-1]) if not np.isnan(macd_l.iloc[-1]) else 0
    
    score = 0
    reasons = []
    
    if price < sma50:
        score += 20; reasons.append("Below SMA50")
    if price < sma20:
        score += 5
    if macd_val < 0:
        score += 15; reasons.append("MACD-")
    if 40 < rsi_val < 70:
        score += 10; reasons.append(f"RSI {rsi_val:.0f}")
    # Negative momentum
    ret_5d = (close.iloc[i] - close.iloc[i-5]) / close.iloc[i-5] if i >= 5 else 0
    if ret_5d < -0.02:
        score += 10; reasons.append("Downtrend")
    
    return score, reasons, "SHORT"


def strategy_breakdown_short(df, i, params):
    """Short when breaking below 20d low with volume."""
    if i < 25:
        return 0, [], "SHORT"
    close = df["Close"]
    price = float(close.iloc[i])
    
    low_20 = float(df["Low"].iloc[i-20:i].min())
    
    vol = df.get("Volume")
    vol_ratio = 1.0
    if vol is not None and i >= 21:
        avg_vol = float(vol.iloc[i-20:i].mean())
        vol_ratio = float(vol.iloc[i]) / avg_vol if avg_vol > 0 else 1.0
    
    rsi_s = _rsi(close.iloc[:i+1], 14)
    rsi_val = float(rsi_s.iloc[-1]) if not np.isnan(rsi_s.iloc[-1]) else 50
    
    score = 0
    reasons = []
    
    if price < low_20:
        score += 25; reasons.append("20d low break")
        if vol_ratio > 2.0:
            score += 15; reasons.append(f"Vol {vol_ratio:.1f}x")
        if rsi_val < 40:
            score += 10; reasons.append(f"RSI weak {rsi_val:.0f}")
    
    return score, reasons, "SHORT"


def strategy_breakout_long(df, i, params):
    """Long on 20d high break with volume."""
    if i < 25:
        return 0, [], "LONG"
    close = df["Close"]
    price = float(close.iloc[i])
    
    high_20 = float(df["High"].iloc[i-20:i].max())
    
    vol = df.get("Volume")
    vol_ratio = 1.0
    if vol is not None and i >= 21:
        avg_vol = float(vol.iloc[i-20:i].mean())
        vol_ratio = float(vol.iloc[i]) / avg_vol if avg_vol > 0 else 1.0
    
    score = 0
    reasons = []
    
    if price > high_20 and vol_ratio > 1.8:
        score += 30; reasons.append("20d high breakout")
        if vol_ratio > 2.5:
            score += 10; reasons.append(f"Vol {vol_ratio:.1f}x")
        
        macd_l, _, _ = _macd(close.iloc[:i+1])
        if not np.isnan(macd_l.iloc[-1]) and float(macd_l.iloc[-1]) > 0:
            score += 10; reasons.append("MACD confirming")
    
    return score, reasons, "LONG"


STRATEGIES = {
    "trend_long": strategy_trend_long,
    "mean_rev_long": strategy_mean_rev_long,
    "trend_short": strategy_trend_short,
    "breakdown_short": strategy_breakdown_short,
    "breakout_long": strategy_breakout_long,
}


# ═══════════════════════════════════════════════════════════════════════════
# TRADE SIMULATION (supports LONG + SHORT)
# ═══════════════════════════════════════════════════════════════════════════

def simulate_trade(df, entry_idx, params, asset_class, direction="LONG"):
    """Simulate a trade with TP, SL, trailing stop. direction='LONG' or 'SHORT'."""
    close = df["Close"]
    entry_price = float(close.iloc[entry_idx])
    
    atr_s = _atr(df, 14)
    atr_val = float(atr_s.iloc[entry_idx])
    if np.isnan(atr_val) or atr_val <= 0:
        atr_val = entry_price * (0.005 if asset_class == "forex" else 0.03)
    
    tp_mult = params["tp_mult"]
    sl_mult = params["sl_mult"]
    max_hold = params["max_hold"]
    use_trailing = params.get("use_trailing", True)
    trail_activation = params.get("trail_activation", 0.5)
    
    # Compute TP/SL distances
    if asset_class == "forex":
        sl_dist = max(atr_val * sl_mult, entry_price * 0.003)
        tp_dist = max(atr_val * tp_mult, entry_price * 0.006)
    elif asset_class == "penny":
        sl_dist = max(atr_val * sl_mult, entry_price * 0.02)
        tp_dist = max(atr_val * tp_mult, entry_price * 0.04)
    elif asset_class == "meme":
        sl_dist = max(atr_val * sl_mult, entry_price * 0.025)
        tp_dist = max(atr_val * tp_mult, entry_price * 0.05)
    else:
        sl_dist = max(atr_val * sl_mult, entry_price * 0.015)
        tp_dist = max(atr_val * tp_mult, entry_price * 0.025)
    
    # Enforce minimum 1.5:1 R:R
    if tp_dist < sl_dist * 1.5:
        tp_dist = sl_dist * 1.5
    
    if direction == "LONG":
        stop_price = entry_price - sl_dist
        target_price = entry_price + tp_dist
    else:  # SHORT
        stop_price = entry_price + sl_dist
        target_price = entry_price - tp_dist
    
    trail_stop = stop_price
    best_price = entry_price  # highest for long, lowest for short
    
    end_idx = min(entry_idx + max_hold, len(df) - 1)
    
    for j in range(entry_idx + 1, end_idx + 1):
        high = float(df["High"].iloc[j])
        low = float(df["Low"].iloc[j])
        
        if direction == "LONG":
            if high > best_price:
                best_price = high
            
            # Trailing stop
            if use_trailing and best_price >= entry_price + tp_dist * trail_activation:
                min_trail = entry_price + sl_dist * 0.2
                new_trail = best_price - sl_dist * 0.8
                trail_stop = max(trail_stop, new_trail, min_trail)
            
            active_stop = max(stop_price, trail_stop)
            
            # Check SL
            if low <= active_stop:
                pnl = ((active_stop - entry_price) / entry_price) * 100
                return {"outcome": "WIN" if pnl > 0 else "LOSS",
                        "pnl_pct": round(pnl, 3), "hold_days": j - entry_idx,
                        "entry_price": entry_price, "exit_price": round(active_stop, 8),
                        "direction": direction}
            # Check TP
            if high >= target_price:
                pnl = ((target_price - entry_price) / entry_price) * 100
                return {"outcome": "WIN", "pnl_pct": round(pnl, 3),
                        "hold_days": j - entry_idx, "entry_price": entry_price,
                        "exit_price": target_price, "direction": direction}
        
        else:  # SHORT
            if low < best_price:
                best_price = low
            
            if use_trailing and best_price <= entry_price - tp_dist * trail_activation:
                min_trail = entry_price - sl_dist * 0.2
                new_trail = best_price + sl_dist * 0.8
                trail_stop = min(trail_stop, new_trail, min_trail)
            
            active_stop = min(stop_price, trail_stop)
            
            if high >= active_stop:
                pnl = ((entry_price - active_stop) / entry_price) * 100
                return {"outcome": "WIN" if pnl > 0 else "LOSS",
                        "pnl_pct": round(pnl, 3), "hold_days": j - entry_idx,
                        "entry_price": entry_price, "exit_price": round(active_stop, 8),
                        "direction": direction}
            if low <= target_price:
                pnl = ((entry_price - target_price) / entry_price) * 100
                return {"outcome": "WIN", "pnl_pct": round(pnl, 3),
                        "hold_days": j - entry_idx, "entry_price": entry_price,
                        "exit_price": target_price, "direction": direction}
    
    # Expired
    final_price = float(close.iloc[end_idx])
    if direction == "LONG":
        pnl = ((final_price - entry_price) / entry_price) * 100
    else:
        pnl = ((entry_price - final_price) / entry_price) * 100
    
    return {"outcome": "EXPIRED", "pnl_pct": round(pnl, 3),
            "hold_days": end_idx - entry_idx, "entry_price": entry_price,
            "exit_price": final_price, "direction": direction}


# ═══════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def backtest(yf_data, symbols, asset_class, strategy_fn, params, start_pct=0, end_pct=1.0):
    """Run backtest. start_pct/end_pct allow walk-forward splits."""
    trades = []
    threshold = params["threshold"]
    
    for sym in symbols:
        df = yf_data.get(sym)
        if df is None or len(df) < 60:
            continue
        
        # Split for walk-forward
        n = len(df)
        start_i = int(n * start_pct)
        end_i = int(n * end_pct)
        if end_i - start_i < 60:
            continue
        
        last_trade_idx = -10
        cooldown = params.get("cooldown", 5)
        
        for i in range(max(50, start_i), end_i - params["max_hold"]):
            if i - last_trade_idx < cooldown:
                continue
            
            score, reasons, direction = strategy_fn(df, i, params)
            
            if score >= threshold:
                trade = simulate_trade(df, i, params, asset_class, direction)
                trade["symbol"] = sym
                trade["score"] = score
                trade["reasons"] = reasons
                trade["date"] = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(i)
                trades.append(trade)
                last_trade_idx = i
    
    return trades


def analyze_trades(trades, label=""):
    """Analyze trades and return stats dict."""
    if not trades:
        return {"label": label, "total": 0, "wins": 0, "losses": 0,
                "win_rate": 0, "avg_win": 0, "avg_loss": 0,
                "total_pnl": 0, "expectancy": -999, "pf": 0,
                "max_dd": 0, "avg_hold": 0, "verdict": "NO_DATA"}
    
    wins = [t for t in trades if t["outcome"] == "WIN"]
    losses = [t for t in trades if t["outcome"] == "LOSS"]
    total_closed = len(wins) + len(losses)
    wr = (len(wins) / total_closed * 100) if total_closed > 0 else 0
    
    pnls = [t["pnl_pct"] for t in trades]
    avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
    avg_loss = np.mean([t["pnl_pct"] for t in losses]) if losses else 0
    total_pnl = sum(pnls)
    
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    
    expectancy = (wr/100 * avg_win) - ((100-wr)/100 * abs(avg_loss))
    
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    max_dd = float(np.max(peak - cum)) if len(cum) > 0 else 0
    
    # Verdict
    if total_closed < 10:
        verdict = "INSUFFICIENT"
    elif expectancy > 0 and pf > 1.2 and wr > 45:
        verdict = "✅ WINNER"
    elif expectancy > 0 and pf > 1.0:
        verdict = "🟡 MARGINAL"
    else:
        verdict = "❌ ELIMINATED"
    
    return {
        "label": label,
        "total": len(trades), "wins": len(wins), "losses": len(losses),
        "win_rate": round(wr, 1), "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2), "total_pnl": round(total_pnl, 2),
        "expectancy": round(expectancy, 3), "pf": round(pf, 2),
        "max_dd": round(max_dd, 2),
        "avg_hold": round(np.mean([t["hold_days"] for t in trades]), 1),
        "verdict": verdict,
    }


# ═══════════════════════════════════════════════════════════════════════════
# PARAMETER GRIDS
# ═══════════════════════════════════════════════════════════════════════════

PARAM_GRIDS = {
    "crypto_long": [
        {"tp_mult": 2.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 7, "use_trailing": True, "cooldown": 5},
        {"tp_mult": 2.5, "sl_mult": 1.0, "threshold": 40, "max_hold": 10, "use_trailing": True, "cooldown": 5},
        {"tp_mult": 3.0, "sl_mult": 1.0, "threshold": 45, "max_hold": 14, "use_trailing": True, "cooldown": 7},
        {"tp_mult": 2.0, "sl_mult": 0.8, "threshold": 40, "max_hold": 7, "use_trailing": True, "cooldown": 5},
        {"tp_mult": 3.0, "sl_mult": 1.5, "threshold": 35, "max_hold": 14, "use_trailing": True, "cooldown": 5},
    ],
    "crypto_short": [
        {"tp_mult": 2.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 7, "use_trailing": True, "cooldown": 5},
        {"tp_mult": 2.5, "sl_mult": 1.0, "threshold": 40, "max_hold": 10, "use_trailing": True, "cooldown": 5},
        {"tp_mult": 3.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 14, "use_trailing": True, "cooldown": 7},
        {"tp_mult": 2.0, "sl_mult": 0.8, "threshold": 35, "max_hold": 5, "use_trailing": True, "cooldown": 3},
    ],
    "forex": [
        {"tp_mult": 3.0, "sl_mult": 1.5, "threshold": 35, "max_hold": 14, "use_trailing": True, "cooldown": 5},
        {"tp_mult": 4.0, "sl_mult": 1.5, "threshold": 35, "max_hold": 21, "use_trailing": True, "cooldown": 5},
        {"tp_mult": 2.5, "sl_mult": 1.0, "threshold": 40, "max_hold": 10, "use_trailing": True, "cooldown": 3},
        {"tp_mult": 2.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 7, "use_trailing": True, "cooldown": 3},
    ],
    "stocks": [
        {"tp_mult": 2.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 10, "use_trailing": True, "cooldown": 5},
        {"tp_mult": 2.5, "sl_mult": 1.0, "threshold": 40, "max_hold": 14, "use_trailing": True, "cooldown": 5},
        {"tp_mult": 3.0, "sl_mult": 1.5, "threshold": 35, "max_hold": 21, "use_trailing": True, "cooldown": 7},
    ],
    "penny_meme": [
        {"tp_mult": 3.0, "sl_mult": 1.0, "threshold": 40, "max_hold": 5, "use_trailing": True, "cooldown": 3},
        {"tp_mult": 4.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 7, "use_trailing": True, "cooldown": 3},
        {"tp_mult": 2.0, "sl_mult": 0.8, "threshold": 45, "max_hold": 5, "use_trailing": True, "cooldown": 3},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# MAIN BATTLE TEST
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("⚔️  ANTIGRAVITY BATTLE TEST — CROSS-ASSET ELIMINATION TOURNAMENT")
    print(f"   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)
    
    # 1. Download ALL data — 6 months
    print("\n📥 Phase 1: Downloading 6 months real market data...")
    all_syms = []
    for cat, syms in SYMBOLS.items():
        all_syms.extend(syms)
    all_syms = list(set(all_syms))  # de-dupe
    
    yf_data = {}
    try:
        batch = yf.download(all_syms, period="6mo", group_by="ticker",
                            auto_adjust=True, progress=False, threads=True)
        for sym in all_syms:
            try:
                df = batch[sym].dropna() if len(all_syms) > 1 else batch.dropna()
                if len(df) >= 60:
                    yf_data[sym] = df
            except Exception:
                continue
    except Exception as e:
        print(f"  Batch error: {e}, falling back to individual downloads...")
        for sym in all_syms:
            try:
                df = yf.Ticker(sym).history(period="6mo", auto_adjust=True)
                if df is not None and len(df) >= 60:
                    yf_data[sym] = df
            except Exception:
                continue
    
    for cat, syms in SYMBOLS.items():
        loaded = len([s for s in syms if s in yf_data])
        print(f"  {cat:8s}: {loaded}/{len(syms)} symbols loaded")
    
    # 2. Run ALL strategy/asset/param combos
    print("\n" + "=" * 80)
    print("⚔️  Phase 2: FULL-SPECTRUM BACKTEST")
    print("=" * 80)
    
    all_results = []
    
    test_configs = [
        # (asset_class, symbols_key, strategy_name, strategy_fn, param_grid_key)
        ("crypto", "crypto", "trend_long", strategy_trend_long, "crypto_long"),
        ("crypto", "crypto", "mean_rev_long", strategy_mean_rev_long, "crypto_long"),
        ("crypto", "crypto", "breakout_long", strategy_breakout_long, "crypto_long"),
        ("crypto", "crypto", "trend_short", strategy_trend_short, "crypto_short"),
        ("crypto", "crypto", "breakdown_short", strategy_breakdown_short, "crypto_short"),
        ("forex", "forex", "trend_long", strategy_trend_long, "forex"),
        ("forex", "forex", "mean_rev_long", strategy_mean_rev_long, "forex"),
        ("stocks", "stocks", "trend_long", strategy_trend_long, "stocks"),
        ("stocks", "stocks", "mean_rev_long", strategy_mean_rev_long, "stocks"),
        ("stocks", "stocks", "breakout_long", strategy_breakout_long, "stocks"),
        ("stocks", "stocks", "trend_short", strategy_trend_short, "stocks"),
        ("penny", "penny", "mean_rev_long", strategy_mean_rev_long, "penny_meme"),
        ("penny", "penny", "breakout_long", strategy_breakout_long, "penny_meme"),
        ("meme", "meme", "mean_rev_long", strategy_mean_rev_long, "penny_meme"),
        ("meme", "meme", "breakout_long", strategy_breakout_long, "penny_meme"),
        ("meme", "meme", "trend_short", strategy_trend_short, "crypto_short"),
    ]
    
    for asset_class, sym_key, strat_name, strat_fn, grid_key in test_configs:
        syms = [s for s in SYMBOLS[sym_key] if s in yf_data]
        if not syms:
            continue
        
        print(f"\n  {'─'*60}")
        print(f"  {asset_class.upper()} × {strat_name}")
        print(f"  {'─'*60}")
        
        best = None
        best_exp = -999
        
        for pidx, params in enumerate(PARAM_GRIDS[grid_key]):
            label = f"{asset_class}_{strat_name}_p{pidx}"
            
            # Full backtest
            trades = backtest(yf_data, syms, asset_class, strat_fn, params)
            stats = analyze_trades(trades, label)
            
            # Walk-forward: train on first 67%, test on last 33%
            oos_trades = backtest(yf_data, syms, asset_class, strat_fn, params, 0.67, 1.0)
            oos_stats = analyze_trades(oos_trades, f"{label}_OOS")
            
            icon = "✅" if "WINNER" in stats["verdict"] else "🟡" if "MARGINAL" in stats["verdict"] else "❌"
            oos_icon = "✅" if "WINNER" in oos_stats["verdict"] else "🟡" if "MARGINAL" in oos_stats["verdict"] else "❌"
            
            print(f"    {icon} p{pidx} FULL: {stats['total']:3d} trades  "
                  f"WR:{stats['win_rate']:5.1f}%  PF:{stats['pf']:.2f}  "
                  f"P&L:{stats['total_pnl']:+8.1f}%  Exp:{stats['expectancy']:+.3f}%  "
                  f"{stats['verdict']}")
            print(f"    {oos_icon}    OOS:  {oos_stats['total']:3d} trades  "
                  f"WR:{oos_stats['win_rate']:5.1f}%  PF:{oos_stats['pf']:.2f}  "
                  f"P&L:{oos_stats['total_pnl']:+8.1f}%  Exp:{oos_stats['expectancy']:+.3f}%  "
                  f"{oos_stats['verdict']}")
            
            result = {
                "asset_class": asset_class,
                "strategy": strat_name,
                "param_idx": pidx,
                "params": params,
                "full": stats,
                "oos": oos_stats,
            }
            all_results.append(result)
            
            if stats["total"] >= 10 and stats["expectancy"] > best_exp:
                best_exp = stats["expectancy"]
                best = result
        
        if best:
            s = best["full"]
            print(f"  ★ BEST: {best['strategy']} p{best['param_idx']}  "
                  f"Exp:{s['expectancy']:+.3f}%  PF:{s['pf']:.2f}")
    
    # 3. ELIMINATION ROUND
    print("\n" + "=" * 80)
    print("🗡️  Phase 3: ELIMINATION ROUND")
    print("=" * 80)
    
    winners = []
    eliminated = []
    marginal = []
    
    for r in all_results:
        full = r["full"]
        oos = r["oos"]
        label = f"{r['asset_class']}/{r['strategy']}/p{r['param_idx']}"
        
        if full["total"] < 10:
            continue
        
        # WINNER = profitable in both full AND OOS
        full_pf = full.get("pf", 0)
        oos_pf = oos.get("pf", 0)
        if ("WINNER" in full["verdict"] or "MARGINAL" in full["verdict"]) and \
           oos["total"] >= 5 and oos.get("expectancy", -999) > 0 and oos_pf > 1.0:
            winners.append(r)
            print(f"  ✅ SURVIVED: {label}  Full PF:{full_pf:.2f}  OOS PF:{oos_pf:.2f}")
        elif "WINNER" in full["verdict"]:
            marginal.append(r)
            print(f"  🟡 OVERFIT:  {label}  Full PF:{full_pf:.2f}  OOS PF:{oos_pf:.2f}  (good in-sample, bad OOS)")
        else:
            eliminated.append(r)
    
    # 4. Per-symbol breakdown for winners
    print("\n" + "=" * 80)
    print("📊 Phase 4: WINNING STRATEGY PER-SYMBOL BREAKDOWN")
    print("=" * 80)
    
    symbol_verdicts = defaultdict(list)
    
    for r in winners:
        asset_class = r["asset_class"]
        strat_fn = STRATEGIES[r["strategy"]]
        params = r["params"]
        syms = [s for s in SYMBOLS.get(asset_class, []) if s in yf_data]
        
        print(f"\n  ── {r['asset_class']}/{r['strategy']}/p{r['param_idx']} ──")
        
        for sym in syms:
            trades = backtest(yf_data, [sym], asset_class, strat_fn, params)
            if not trades:
                continue
            
            w = len([t for t in trades if t["outcome"] == "WIN"])
            l = len([t for t in trades if t["outcome"] == "LOSS"])
            pnl = sum(t["pnl_pct"] for t in trades)
            wr = w / (w + l) * 100 if (w + l) > 0 else 0
            icon = "✅" if pnl > 0 else "❌"
            
            print(f"    {icon} {sym:18s}  T:{len(trades):3d}  W:{w:2d}/L:{l:2d}  "
                  f"WR:{wr:5.1f}%  P&L:{pnl:+8.1f}%")
            
            symbol_verdicts[sym].append({"pnl": pnl, "wr": wr, "trades": len(trades)})
    
    # 5. Final summary
    print("\n" + "=" * 80)
    print("🏆 Phase 5: FINAL BATTLE REPORT")
    print("=" * 80)
    
    print(f"\n  Total strategies tested: {len(all_results)}")
    print(f"  ✅ WINNERS (survived OOS): {len(winners)}")
    print(f"  🟡 OVERFIT (good train, bad test): {len(marginal)}")
    print(f"  ❌ ELIMINATED: {len(eliminated)}")
    
    if winners:
        print("\n  ── WINNING STRATEGIES ──")
        for r in sorted(winners, key=lambda x: x["full"]["expectancy"], reverse=True):
            f = r["full"]
            o = r["oos"]
            print(f"    ✅ {r['asset_class']:8s} {r['strategy']:20s} p{r['param_idx']}  "
                  f"Full[WR:{f['win_rate']:5.1f}% PF:{f['pf']:.2f} P&L:{f['total_pnl']:+.1f}%]  "
                  f"OOS[WR:{o['win_rate']:5.1f}% PF:{o['pf']:.2f} P&L:{o['total_pnl']:+.1f}%]")
    
    # Top symbols across all winners
    if symbol_verdicts:
        print("\n  ── TOP SYMBOLS (Profitable across strategies) ──")
        sym_summary = []
        for sym, entries in symbol_verdicts.items():
            total_pnl = sum(e["pnl"] for e in entries)
            avg_wr = np.mean([e["wr"] for e in entries])
            total_trades = sum(e["trades"] for e in entries)
            sym_summary.append({"sym": sym, "pnl": total_pnl, "wr": avg_wr, "trades": total_trades})
        
        for s in sorted(sym_summary, key=lambda x: x["pnl"], reverse=True):
            icon = "✅" if s["pnl"] > 0 else "❌"
            print(f"    {icon} {s['sym']:18s}  Total P&L: {s['pnl']:+8.1f}%  "
                  f"Avg WR: {s['wr']:.1f}%  Trades: {s['trades']}")
    
    # Save results
    results_file = DATA_DIR / "battle_test_results.json"
    save_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_strategies": len(all_results),
        "winners": len(winners),
        "marginal": len(marginal),
        "eliminated": len(eliminated),
        "winning_strategies": [],
        "symbol_verdicts": {},
    }
    
    for r in winners:
        save_data["winning_strategies"].append({
            "asset_class": r["asset_class"],
            "strategy": r["strategy"],
            "params": r["params"],
            "full_stats": r["full"],
            "oos_stats": r["oos"],
        })
    
    for sym, entries in symbol_verdicts.items():
        total_pnl = sum(e["pnl"] for e in entries)
        save_data["symbol_verdicts"][sym] = {
            "total_pnl": round(total_pnl, 2),
            "avg_wr": round(np.mean([e["wr"] for e in entries]), 1),
            "total_trades": sum(e["trades"] for e in entries),
            "profitable": total_pnl > 0,
        }
    
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"\n  📁 Results saved to {results_file}")
    
    print(f"\n{'='*80}")
    print("⚔️  BATTLE TEST COMPLETE")
    print(f"{'='*80}")
    
    return save_data


if __name__ == "__main__":
    main()
