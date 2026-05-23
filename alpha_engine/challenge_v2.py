#!/usr/bin/env python3
"""
ALPHA ENGINE -- 2-HOUR CHALLENGE V2
====================================
Uses 5-minute intraday data for real-time scalping.
All timestamps in EST. Restartable rounds.
Proven scalping strategies with tight TP/SL.

Usage:
  python challenge_v2.py start          # Start a new round
  python challenge_v2.py check          # Check current round
  python challenge_v2.py restart        # Abandon current, start fresh
  python challenge_v2.py history        # Show all rounds
"""

import json
import sys
import os
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import yfinance as yf

# EST timezone
EST = timezone(timedelta(hours=-5))

DATA_DIR = Path(__file__).resolve().parent / "data"
CHALLENGE_FILE = DATA_DIR / "challenge_v2.json"
HISTORY_FILE = DATA_DIR / "challenge_v2_history.json"

# Focus on the most liquid, volatile assets for 2hr scalping
SCALP_SYMBOLS = {
    # Crypto (24/7, high volatility)
    "BTC-USD":  {"cat": "crypto", "name": "Bitcoin"},
    "ETH-USD":  {"cat": "crypto", "name": "Ethereum"},
    "SOL-USD":  {"cat": "crypto", "name": "Solana"},
    "DOGE-USD": {"cat": "crypto", "name": "Dogecoin"},
    "XRP-USD":  {"cat": "crypto", "name": "XRP"},
    "AVAX-USD": {"cat": "crypto", "name": "Avalanche"},
    "LINK-USD": {"cat": "crypto", "name": "Chainlink"},
    "ADA-USD":  {"cat": "crypto", "name": "Cardano"},
    # Forex (high liquidity)
    "EURUSD=X": {"cat": "forex", "name": "EUR/USD"},
    "GBPUSD=X": {"cat": "forex", "name": "GBP/USD"},
    "USDJPY=X": {"cat": "forex", "name": "USD/JPY"},
    "AUDUSD=X": {"cat": "forex", "name": "AUD/USD"},
    "USDCAD=X": {"cat": "forex", "name": "USD/CAD"},
    "GBPJPY=X": {"cat": "forex", "name": "GBP/JPY"},
}


def now_est():
    return datetime.now(EST)


def est_str(dt=None):
    if dt is None:
        dt = now_est()
    return dt.strftime("%Y-%m-%d %I:%M:%S %p EST")


def fetch_intraday(symbols, interval="5m", period="1d"):
    """Fetch 5-minute intraday candles."""
    tickers = " ".join(symbols)
    raw = yf.download(tickers, period=period, interval=interval,
                      group_by="ticker", auto_adjust=True,
                      threads=True, progress=False)
    data = {}
    for sym in symbols:
        try:
            if len(symbols) == 1:
                df = raw.copy()
            else:
                df = raw[sym].copy() if sym in raw.columns.get_level_values(0) else None
            if df is not None and not df.empty:
                df = df.dropna(subset=["Close"])
                if len(df) >= 10:
                    data[sym] = df
        except Exception:
            continue
    return data


# =============================================================================
# SCALPING STRATEGIES (5-minute candles, tight TP/SL)
# =============================================================================

def strat_ema_crossover(df, sym, meta):
    """EMA 9/21 crossover with RSI filter. Classic scalp."""
    close = df["Close"]
    if len(close) < 30:
        return None
    ema9 = close.ewm(span=9).mean()
    ema21 = close.ewm(span=21).mean()
    rsi = compute_rsi(close, 14)
    price = float(close.iloc[-1])
    atr = compute_atr(df, 14)

    # Bullish crossover: EMA9 crosses above EMA21, RSI > 50
    if (ema9.iloc[-1] > ema21.iloc[-1] and
        ema9.iloc[-2] <= ema21.iloc[-2] and
        rsi > 50 and rsi < 75):
        tp = price + atr * 1.5
        sl = price - atr * 1.0
        return make_pick(sym, meta, "BUY", price, tp, sl, atr, "ema_crossover_9_21",
                         f"EMA9 crossed above EMA21, RSI={rsi:.0f}")

    # Bearish crossover
    if (ema9.iloc[-1] < ema21.iloc[-1] and
        ema9.iloc[-2] >= ema21.iloc[-2] and
        rsi < 50 and rsi > 25):
        tp = price - atr * 1.5
        sl = price + atr * 1.0
        return make_pick(sym, meta, "SELL", price, tp, sl, atr, "ema_crossover_9_21",
                         f"EMA9 crossed below EMA21, RSI={rsi:.0f}")
    return None


def strat_rsi_extreme(df, sym, meta):
    """RSI oversold bounce / overbought rejection on 5min."""
    close = df["Close"]
    if len(close) < 20:
        return None
    rsi = compute_rsi(close, 14)
    price = float(close.iloc[-1])
    atr = compute_atr(df, 14)

    # Oversold bounce (RSI was <25, now rising back above 30)
    rsi_prev = compute_rsi(close.iloc[:-1], 14)
    if rsi > 30 and rsi < 45 and rsi_prev < 30:
        tp = price + atr * 2.0
        sl = price - atr * 1.0
        return make_pick(sym, meta, "BUY", price, tp, sl, atr, "rsi_extreme_bounce",
                         f"RSI bounced from {rsi_prev:.0f} to {rsi:.0f}")

    # Overbought rejection
    if rsi < 70 and rsi > 55 and rsi_prev > 70:
        tp = price - atr * 2.0
        sl = price + atr * 1.0
        return make_pick(sym, meta, "SELL", price, tp, sl, atr, "rsi_extreme_bounce",
                         f"RSI rejected from {rsi_prev:.0f} to {rsi:.0f}")
    return None


def strat_bollinger_squeeze(df, sym, meta):
    """Bollinger Band squeeze breakout -- volatility expansion play."""
    close = df["Close"]
    if len(close) < 25:
        return None
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20
    bandwidth = (upper - lower) / sma20

    price = float(close.iloc[-1])
    atr = compute_atr(df, 14)

    # Squeeze: bandwidth is at 20-bar low, then breakout
    bw_now = float(bandwidth.iloc[-1])
    bw_min = float(bandwidth.iloc[-20:].min())

    if bw_now <= bw_min * 1.05:  # Currently in squeeze
        # Check breakout direction
        if price > float(upper.iloc[-1]):
            tp = price + atr * 2.0
            sl = price - atr * 1.0
            return make_pick(sym, meta, "BUY", price, tp, sl, atr, "bb_squeeze_breakout",
                             f"BB squeeze breakout UP, BW={bw_now:.4f}")
        elif price < float(lower.iloc[-1]):
            tp = price - atr * 2.0
            sl = price + atr * 1.0
            return make_pick(sym, meta, "SELL", price, tp, sl, atr, "bb_squeeze_breakout",
                             f"BB squeeze breakout DOWN, BW={bw_now:.4f}")
    return None


def strat_momentum_burst(df, sym, meta):
    """3 consecutive same-direction candles with increasing volume."""
    close = df["Close"]
    vol = df["Volume"]
    if len(close) < 5 or vol.iloc[-1] == 0:
        return None
    price = float(close.iloc[-1])
    atr = compute_atr(df, 14)

    # 3 green candles with increasing volume
    c1 = float(close.iloc[-3]) > float(df["Open"].iloc[-3])
    c2 = float(close.iloc[-2]) > float(df["Open"].iloc[-2])
    c3 = float(close.iloc[-1]) > float(df["Open"].iloc[-1])
    v_inc = float(vol.iloc[-1]) > float(vol.iloc[-2]) > float(vol.iloc[-3])

    if c1 and c2 and c3 and v_inc:
        tp = price + atr * 1.5
        sl = price - atr * 0.8
        return make_pick(sym, meta, "BUY", price, tp, sl, atr, "momentum_burst",
                         "3 green candles + increasing volume")

    # 3 red candles with increasing volume
    r1 = float(close.iloc[-3]) < float(df["Open"].iloc[-3])
    r2 = float(close.iloc[-2]) < float(df["Open"].iloc[-2])
    r3 = float(close.iloc[-1]) < float(df["Open"].iloc[-1])

    if r1 and r2 and r3 and v_inc:
        tp = price - atr * 1.5
        sl = price + atr * 0.8
        return make_pick(sym, meta, "SELL", price, tp, sl, atr, "momentum_burst",
                         "3 red candles + increasing volume")
    return None


def strat_vwap_bounce(df, sym, meta):
    """VWAP bounce -- price touches VWAP and bounces."""
    close = df["Close"]
    vol = df["Volume"]
    high = df["High"]
    low = df["Low"]
    if len(close) < 15 or vol.sum() == 0:
        return None

    price = float(close.iloc[-1])
    atr = compute_atr(df, 14)
    typical = (high + low + close) / 3
    vwap = (typical * vol).cumsum() / vol.cumsum()
    vwap_val = float(vwap.iloc[-1])

    # Price near VWAP (within 0.3 ATR) and bouncing up
    dist = abs(price - vwap_val)
    if dist < atr * 0.3:
        # Check if price is starting to move away from VWAP
        if price > vwap_val and float(close.iloc[-2]) <= float(vwap.iloc[-2]):
            tp = price + atr * 1.5
            sl = price - atr * 0.8
            return make_pick(sym, meta, "BUY", price, tp, sl, atr, "vwap_bounce",
                             f"Price bounced off VWAP ({vwap_val:.6g})")
        elif price < vwap_val and float(close.iloc[-2]) >= float(vwap.iloc[-2]):
            tp = price - atr * 1.5
            sl = price + atr * 0.8
            return make_pick(sym, meta, "SELL", price, tp, sl, atr, "vwap_bounce",
                             f"Price rejected from VWAP ({vwap_val:.6g})")
    return None


def strat_macd_divergence(df, sym, meta):
    """MACD histogram divergence -- fast reversal signal."""
    close = df["Close"]
    if len(close) < 30:
        return None
    price = float(close.iloc[-1])
    atr = compute_atr(df, 14)

    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    hist = macd - signal

    # Bullish: histogram crosses from negative to positive
    if float(hist.iloc[-1]) > 0 and float(hist.iloc[-2]) <= 0:
        tp = price + atr * 1.5
        sl = price - atr * 1.0
        return make_pick(sym, meta, "BUY", price, tp, sl, atr, "macd_crossover",
                         "MACD histogram crossed bullish")

    # Bearish: histogram crosses from positive to negative
    if float(hist.iloc[-1]) < 0 and float(hist.iloc[-2]) >= 0:
        tp = price - atr * 1.5
        sl = price + atr * 1.0
        return make_pick(sym, meta, "SELL", price, tp, sl, atr, "macd_crossover",
                         "MACD histogram crossed bearish")
    return None


def strat_price_channel(df, sym, meta):
    """Donchian channel breakout -- trend following."""
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    if len(close) < 20:
        return None
    price = float(close.iloc[-1])
    atr = compute_atr(df, 14)

    high_20 = float(high.iloc[-20:].max())
    low_20 = float(low.iloc[-20:].min())
    mid = (high_20 + low_20) / 2

    # Breakout above 20-bar high
    if price >= high_20 and float(close.iloc[-2]) < high_20:
        tp = price + atr * 2.0
        sl = mid
        return make_pick(sym, meta, "BUY", price, tp, sl, atr, "donchian_breakout",
                         f"Broke 20-bar high ({high_20:.6g})")

    # Breakdown below 20-bar low
    if price <= low_20 and float(close.iloc[-2]) > low_20:
        tp = price - atr * 2.0
        sl = mid
        return make_pick(sym, meta, "SELL", price, tp, sl, atr, "donchian_breakout",
                         f"Broke 20-bar low ({low_20:.6g})")
    return None


def strat_mean_reversion(df, sym, meta):
    """Z-score mean reversion -- fades extreme moves."""
    close = df["Close"]
    if len(close) < 25:
        return None
    price = float(close.iloc[-1])
    atr = compute_atr(df, 14)

    mean = float(close.rolling(20).mean().iloc[-1])
    std = float(close.rolling(20).std().iloc[-1])
    if std == 0:
        return None
    zscore = (price - mean) / std

    # Extremely stretched -- fade it
    if zscore < -2.0:
        tp = price + atr * 1.5
        sl = price - atr * 1.0
        return make_pick(sym, meta, "BUY", price, tp, sl, atr, "zscore_mean_reversion",
                         f"Z-score={zscore:.2f}, price stretched below mean")
    if zscore > 2.0:
        tp = price - atr * 1.5
        sl = price + atr * 1.0
        return make_pick(sym, meta, "SELL", price, tp, sl, atr, "zscore_mean_reversion",
                         f"Z-score={zscore:.2f}, price stretched above mean")
    return None


# =============================================================================
# HELPERS
# =============================================================================

def compute_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def compute_atr(df, period=14):
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr_val = float(tr.rolling(period).mean().iloc[-1])
    if atr_val == 0:
        atr_val = float(close.iloc[-1]) * 0.005
    return atr_val


def make_pick(sym, meta, signal_type, price, tp, sl, atr, strategy, reason):
    rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0
    return {
        "symbol": sym,
        "name": meta["name"],
        "category": meta["cat"],
        "signal_type": signal_type,
        "entry_price": round(price, 8),
        "take_profit": round(tp, 8),
        "stop_loss": round(sl, 8),
        "atr": round(atr, 8),
        "risk_reward": round(rr, 2),
        "strategy": strategy,
        "reason": reason,
        "entry_time_est": est_str(),
        "entry_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


ALL_STRATEGIES = [
    strat_ema_crossover,
    strat_rsi_extreme,
    strat_bollinger_squeeze,
    strat_momentum_burst,
    strat_vwap_bounce,
    strat_macd_divergence,
    strat_price_channel,
    strat_mean_reversion,
]


def start_round():
    """Start a new challenge round."""
    t = now_est()
    print("\n" + "=" * 80)
    print("  ALPHA ENGINE -- 2-HOUR CHALLENGE V2")
    print(f"  Round Start: {est_str(t)}")
    print(f"  Round End:   {est_str(t + timedelta(hours=2))}")
    print("=" * 80)

    # Determine round number
    history = load_history()
    round_num = len(history) + 1
    print(f"\n  Round #{round_num}")

    print(f"\n[1/3] Fetching 5-minute intraday data for {len(SCALP_SYMBOLS)} symbols...")
    symbols = list(SCALP_SYMBOLS.keys())
    data = fetch_intraday(symbols, interval="5m", period="5d")
    print(f"  Got data for {len(data)}/{len(symbols)} symbols")

    print(f"\n[2/3] Running {len(ALL_STRATEGIES)} scalping strategies...")
    all_picks = []
    for strat_fn in ALL_STRATEGIES:
        for sym, meta in SCALP_SYMBOLS.items():
            if sym not in data:
                continue
            try:
                pick = strat_fn(data[sym], sym, meta)
                if pick:
                    all_picks.append(pick)
                    print(f"  [{pick['strategy']}] {pick['signal_type']} {sym} @ {pick['entry_price']:.8g} "
                          f"TP={pick['take_profit']:.8g} SL={pick['stop_loss']:.8g} "
                          f"R:R={pick['risk_reward']:.1f}x -- {pick['reason']}")
            except Exception as e:
                pass

    print(f"\n  Total picks: {len(all_picks)}")
    if not all_picks:
        print("  WARNING: No signals generated! Market may be flat.")
        print("  Trying with 15m candles for more history...")
        data15 = fetch_intraday(symbols, interval="15m", period="5d")
        for strat_fn in ALL_STRATEGIES:
            for sym, meta in SCALP_SYMBOLS.items():
                if sym not in data15:
                    continue
                try:
                    pick = strat_fn(data15[sym], sym, meta)
                    if pick:
                        pick["timeframe"] = "15m"
                        all_picks.append(pick)
                        print(f"  [15m] [{pick['strategy']}] {pick['signal_type']} {sym} @ {pick['entry_price']:.8g}")
                except Exception:
                    pass
        print(f"  Total picks after 15m fallback: {len(all_picks)}")

    # Also try 1h for broader signals
    if len(all_picks) < 5:
        print("  Also trying 1h candles for broader signals...")
        data1h = fetch_intraday(symbols, interval="1h", period="5d")
        for strat_fn in ALL_STRATEGIES:
            for sym, meta in SCALP_SYMBOLS.items():
                if sym not in data1h:
                    continue
                try:
                    pick = strat_fn(data1h[sym], sym, meta)
                    if pick:
                        pick["timeframe"] = "1h"
                        all_picks.append(pick)
                        print(f"  [1h] [{pick['strategy']}] {pick['signal_type']} {sym} @ {pick['entry_price']:.8g}")
                except Exception:
                    pass
        print(f"  Total picks after 1h fallback: {len(all_picks)}")

    print(f"\n[3/3] Saving round data...")

    # De-duplicate: only keep one pick per (symbol, strategy, signal_type)
    seen = set()
    unique_picks = []
    for p in all_picks:
        key = (p["symbol"], p["strategy"], p["signal_type"])
        if key not in seen:
            seen.add(key)
            unique_picks.append(p)
    all_picks = unique_picks

    challenge = {
        "round": round_num,
        "start_time_est": est_str(t),
        "end_time_est": est_str(t + timedelta(hours=2)),
        "start_utc": datetime.now(timezone.utc).isoformat(),
        "total_picks": len(all_picks),
        "strategies_used": list(set(p["strategy"] for p in all_picks)),
        "symbols_covered": list(set(p["symbol"] for p in all_picks)),
        "picks": all_picks,
        "checks": [],
        "status": "ACTIVE",
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHALLENGE_FILE, "w") as f:
        json.dump(challenge, f, indent=2, default=str)

    # Print summary
    print(f"\n" + "=" * 80)
    print(f"  ROUND #{round_num} -- {len(all_picks)} PICKS LOCKED IN")
    print(f"  {est_str(t)}")
    print(f"=" * 80)
    by_cat = defaultdict(list)
    for p in all_picks:
        by_cat[p["category"]].append(p)
    for cat in sorted(by_cat.keys()):
        picks = by_cat[cat]
        print(f"\n  [{cat.upper()}] ({len(picks)} picks)")
        for p in picks:
            print(f"    {p['signal_type']:>4s} {p['symbol']:>12s} @ {p['entry_price']:>12.8g} "
                  f"TP={p['take_profit']:>12.8g} SL={p['stop_loss']:>12.8g} "
                  f"R:R={p['risk_reward']:.1f}x [{p['strategy']}]")

    by_strat = defaultdict(int)
    for p in all_picks:
        by_strat[p["strategy"]] += 1
    print(f"\n  By Strategy:")
    for s in sorted(by_strat.keys()):
        print(f"    {s:30s}: {by_strat[s]} picks")

    print(f"\n  Check results: python challenge_v2.py check")
    print(f"  Round ends: {est_str(t + timedelta(hours=2))}")
    print("=" * 80)
    return challenge


def check_round():
    """Check current round against live prices."""
    if not CHALLENGE_FILE.exists():
        print("No active round. Run 'start' first.")
        return None

    with open(CHALLENGE_FILE) as f:
        challenge = json.load(f)

    picks = challenge["picks"]
    if not picks:
        print("No picks in current round.")
        return None

    start_str = challenge.get("start_time_est", "?")
    start_utc = challenge.get("start_utc", datetime.now(timezone.utc).isoformat())
    try:
        start_dt = datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
    except Exception:
        start_dt = datetime.now(timezone.utc)
    elapsed_min = (datetime.now(timezone.utc) - start_dt).total_seconds() / 60

    t = now_est()
    print("\n" + "=" * 80)
    print(f"  CHALLENGE V2 -- ROUND #{challenge.get('round', '?')} CHECK")
    print(f"  Started: {start_str}")
    print(f"  Now:     {est_str(t)}")
    print(f"  Elapsed: {elapsed_min:.0f} minutes")
    print("=" * 80)

    # Fetch current intraday prices
    unique_syms = list(set(p["symbol"] for p in picks))
    print(f"\n  Fetching real-time prices for {len(unique_syms)} symbols...")

    current_prices = {}
    period_highs = {}
    period_lows = {}

    for interval, period in [("5m", "1d"), ("15m", "5d"), ("1d", "5d")]:
        try:
            raw = yf.download(" ".join(unique_syms), period=period, interval=interval,
                              group_by="ticker", auto_adjust=True,
                              threads=True, progress=False)
            if raw is not None and not raw.empty:
                for sym in unique_syms:
                    if sym in current_prices:
                        continue
                    try:
                        if len(unique_syms) == 1:
                            df = raw
                        else:
                            df = raw[sym] if sym in raw.columns.get_level_values(0) else None
                        if df is not None and not df.empty:
                            df = df.dropna(subset=["Close"])
                            if len(df) > 0:
                                current_prices[sym] = float(df["Close"].iloc[-1])
                                period_highs[sym] = float(df["High"].max())
                                period_lows[sym] = float(df["Low"].min())
                    except Exception:
                        continue
            if len(current_prices) >= len(unique_syms) * 0.8:
                print(f"  Got {len(current_prices)}/{len(unique_syms)} prices via {interval}")
                break
        except Exception:
            continue

    # Score each pick
    results = []
    for p in picks:
        sym = p["symbol"]
        entry = p["entry_price"]
        tp = p["take_profit"]
        sl = p["stop_loss"]
        sig = p["signal_type"]
        current = current_prices.get(sym)
        day_high = period_highs.get(sym, current)
        day_low = period_lows.get(sym, current)

        if current is None or entry <= 0:
            results.append({**p, "current_price": None, "pnl_pct": 0,
                            "pnl_dollar": 0, "status": "NO_DATA",
                            "check_time_est": est_str()})
            continue

        status = "OPEN"
        exit_price = current

        if sig == "BUY":
            if tp and day_high >= tp:
                status = "TP_HIT"
                exit_price = tp
            elif sl and day_low <= sl:
                status = "SL_HIT"
                exit_price = sl
            pnl = (exit_price - entry) / entry
        else:
            if tp and day_low <= tp:
                status = "TP_HIT"
                exit_price = tp
            elif sl and day_high >= sl:
                status = "SL_HIT"
                exit_price = sl
            pnl = (entry - exit_price) / entry

        results.append({
            **p,
            "current_price": round(current, 8),
            "day_high": round(day_high, 8),
            "day_low": round(day_low, 8),
            "exit_price": round(exit_price, 8),
            "pnl_pct": round(pnl * 100, 4),
            "pnl_dollar": round(pnl * 2000, 2),  # $2000 per position
            "status": status,
            "check_time_est": est_str(),
        })

    # Strategy leaderboard
    by_strat = defaultdict(list)
    for r in results:
        by_strat[r["strategy"]].append(r)

    strat_scores = []
    for strat, sr in by_strat.items():
        valid = [r for r in sr if r["status"] != "NO_DATA"]
        if not valid:
            continue
        pnls = [r["pnl_pct"] for r in valid]
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p <= 0)
        total_pnl = sum(r["pnl_dollar"] for r in valid)
        tp_hits = sum(1 for r in valid if r["status"] == "TP_HIT")
        sl_hits = sum(1 for r in valid if r["status"] == "SL_HIT")
        still_open = sum(1 for r in valid if r["status"] == "OPEN")
        avg_pnl = np.mean(pnls) if pnls else 0
        wr = wins / len(valid) * 100 if valid else 0

        strat_scores.append({
            "strategy": strat,
            "picks": len(valid),
            "winning": wins,
            "losing": losses,
            "tp_hits": tp_hits,
            "sl_hits": sl_hits,
            "open": still_open,
            "win_rate": round(wr, 1),
            "avg_pnl_pct": round(avg_pnl, 4),
            "total_pnl_dollar": round(total_pnl, 2),
        })

    strat_scores.sort(key=lambda x: x["total_pnl_dollar"], reverse=True)

    # Print leaderboard
    print(f"\n  STRATEGY LEADERBOARD ({elapsed_min:.0f} min into round):")
    print(f"  {'#':>3s} {'Strategy':>30s} {'Picks':>5s} {'W':>3s} {'L':>3s} "
          f"{'WR%':>5s} {'TP':>3s} {'SL':>3s} {'AvgPnL%':>8s} {'Total P&L':>11s}")
    print(f"  {'-'*3} {'-'*30} {'-'*5} {'-'*3} {'-'*3} "
          f"{'-'*5} {'-'*3} {'-'*3} {'-'*8} {'-'*11}")

    for i, s in enumerate(strat_scores, 1):
        medal = {1: " [1ST]", 2: " [2ND]", 3: " [3RD]"}.get(i, "")
        color = "+" if s["total_pnl_dollar"] >= 0 else ""
        print(f"  {i:>3d} {s['strategy']:>30s} {s['picks']:>4d} {s['winning']:>3d} {s['losing']:>3d} "
              f"{s['win_rate']:>4.0f}% {s['tp_hits']:>3d} {s['sl_hits']:>3d} "
              f"{s['avg_pnl_pct']:>+7.3f}% ${s['total_pnl_dollar']:>+9.2f}{medal}")

    # Overall stats
    all_pnl = sum(s["total_pnl_dollar"] for s in strat_scores)
    all_picks_n = sum(s["picks"] for s in strat_scores)
    all_wins = sum(s["winning"] for s in strat_scores)
    all_losses = sum(s["losing"] for s in strat_scores)
    wr = all_wins / all_picks_n * 100 if all_picks_n > 0 else 0

    print(f"\n  OVERALL: {all_picks_n} picks | {all_wins}W/{all_losses}L ({wr:.1f}% WR) | "
          f"P&L: ${all_pnl:+,.2f}")

    # Asset class breakdown
    print(f"\n  ASSET CLASS:")
    by_cat = defaultdict(lambda: {"pnl": 0, "n": 0, "w": 0})
    for r in results:
        if r["status"] == "NO_DATA":
            continue
        cat = r.get("category", "?")
        by_cat[cat]["n"] += 1
        by_cat[cat]["pnl"] += r.get("pnl_dollar", 0)
        if r.get("pnl_pct", 0) > 0:
            by_cat[cat]["w"] += 1
    for cat in sorted(by_cat.keys()):
        d = by_cat[cat]
        wr_val = d["w"] / d["n"] * 100 if d["n"] > 0 else 0
        print(f"    {cat:>10s}: {d['n']:>3d} picks, {wr_val:>5.1f}% WR, ${d['pnl']:>+10.2f}")

    # Top winners and losers
    sorted_results = sorted(results, key=lambda x: x.get("pnl_pct", 0), reverse=True)
    top_w = [r for r in sorted_results if r.get("pnl_pct", 0) > 0][:5]
    top_l = [r for r in sorted_results if r.get("pnl_pct", 0) < 0][-5:]

    if top_w:
        print(f"\n  TOP WINNERS:")
        for r in top_w:
            print(f"    {r['signal_type']:>4s} {r['name']:>12s} ({r['symbol']}) "
                  f"{r['pnl_pct']:>+7.3f}% ${r['pnl_dollar']:>+8.2f} "
                  f"[{r['strategy']}] {r['status']}")

    if top_l:
        print(f"\n  TOP LOSERS:")
        for r in top_l:
            print(f"    {r['signal_type']:>4s} {r['name']:>12s} ({r['symbol']}) "
                  f"{r['pnl_pct']:>+7.3f}% ${r['pnl_dollar']:>+8.2f} "
                  f"[{r['strategy']}] {r['status']}")

    # Save check
    check_entry = {
        "check_time_est": est_str(),
        "elapsed_minutes": round(elapsed_min, 1),
        "total_pnl": round(all_pnl, 2),
        "win_rate": round(wr, 1),
        "picks_detail": results,
        "strategy_scores": strat_scores,
    }
    challenge["checks"].append(check_entry)
    with open(CHALLENGE_FILE, "w") as f:
        json.dump(challenge, f, indent=2, default=str)

    # Winner
    if strat_scores and strat_scores[0]["total_pnl_dollar"] > 0:
        w = strat_scores[0]
        print(f"\n  CURRENT LEADER: {w['strategy']}")
        print(f"    {w['picks']} picks, {w['winning']}W/{w['losing']}L, "
              f"{w['win_rate']:.0f}% WR, ${w['total_pnl_dollar']:+,.2f}")
    elif strat_scores:
        print(f"\n  NO CLEAR WINNER YET -- all strategies underwater or flat")

    # Verdict at 2hrs+
    if elapsed_min >= 115:
        print(f"\n  {'='*60}")
        print(f"  FINAL VERDICT -- ROUND #{challenge.get('round', '?')}")
        print(f"  {'='*60}")
        winners = [s for s in strat_scores if s["total_pnl_dollar"] > 0]
        losers = [s for s in strat_scores if s["total_pnl_dollar"] <= 0]
        if winners:
            print(f"  WINNING STRATEGIES ({len(winners)}):")
            for s in winners:
                print(f"    {s['strategy']:>30s}: ${s['total_pnl_dollar']:+,.2f} "
                      f"({s['win_rate']:.0f}% WR)")
        if losers:
            print(f"  LOSING STRATEGIES ({len(losers)}):")
            for s in losers:
                print(f"    {s['strategy']:>30s}: ${s['total_pnl_dollar']:+,.2f} "
                      f"({s['win_rate']:.0f}% WR)")
        print(f"\n  OVERALL P&L: ${all_pnl:+,.2f}")
        if all_pnl > 0:
            print(f"  VERDICT: PROFITABLE ROUND!")
        else:
            print(f"  VERDICT: LOSING ROUND -- consider restarting with 'restart'")

        challenge["status"] = "COMPLETED"
        challenge["final_pnl"] = round(all_pnl, 2)
        challenge["final_wr"] = round(wr, 1)
        with open(CHALLENGE_FILE, "w") as f:
            json.dump(challenge, f, indent=2, default=str)
        save_to_history(challenge)

    print("=" * 80)
    return strat_scores


def restart_round():
    """Archive current round and start fresh."""
    if CHALLENGE_FILE.exists():
        with open(CHALLENGE_FILE) as f:
            old = json.load(f)
        old["status"] = "ABANDONED"
        save_to_history(old)
        print(f"  Archived round #{old.get('round', '?')} (ABANDONED)")

    return start_round()


def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []


def save_to_history(challenge):
    history = load_history()
    summary = {
        "round": challenge.get("round"),
        "start": challenge.get("start_time_est"),
        "end": est_str(),
        "status": challenge.get("status"),
        "total_picks": challenge.get("total_picks", 0),
        "final_pnl": challenge.get("final_pnl", 0),
        "final_wr": challenge.get("final_wr", 0),
        "strategies": challenge.get("strategies_used", []),
    }
    history.append(summary)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def show_history():
    history = load_history()
    if not history:
        print("No challenge history yet.")
        return
    print(f"\n  CHALLENGE HISTORY ({len(history)} rounds)")
    print(f"  {'#':>3s} {'Start':>25s} {'Status':>10s} {'Picks':>5s} {'P&L':>10s} {'WR%':>5s}")
    print(f"  {'-'*3} {'-'*25} {'-'*10} {'-'*5} {'-'*10} {'-'*5}")
    for h in history:
        print(f"  {h.get('round', '?'):>3} {h.get('start', '?'):>25s} "
              f"{h.get('status', '?'):>10s} {h.get('total_picks', 0):>5d} "
              f"${h.get('final_pnl', 0):>+9.2f} {h.get('final_wr', 0):>4.1f}%")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python challenge_v2.py [start|check|restart|history]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "start":
        start_round()
    elif cmd == "check":
        check_round()
    elif cmd == "restart":
        restart_round()
    elif cmd == "history":
        show_history()
    else:
        print(f"Unknown: {cmd}")
