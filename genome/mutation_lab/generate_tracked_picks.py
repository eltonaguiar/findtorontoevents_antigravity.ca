#!/usr/bin/env python3
"""
Generate Tracked Live Picks for Forward-Testing
================================================
Runs our best-performing mutation strategies against CURRENT market data
and outputs picks with full tracking metadata (entry, TP, SL, timestamp)
for self-validation in future runs.

Strategies used (only those that passed or showed edge):
  1. cross_agg_battleground_hybrid (KIMI) — PASSED quality gates
  2. genesis_momentum_blend (Claude) — MARGINAL but +20.90% PnL
  3. Best tournament patterns: MACD-RSI confluence, EMA momentum

Output: JSON with picks + markdown summary for CHATWITHIT.md
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "ml_battleground"))

# ---------------------------------------------------------------------------
# Symbol universe — focused on most predictable from tournament data
# ---------------------------------------------------------------------------
SYMBOLS = [
    # Tier 1 Majors
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    # Tier 2 Large (high predictability from tournament)
    "AVAXUSDT", "LINKUSDT", "NEARUSDT", "SUIUSDT", "APTUSDT",
    # Tournament top predictability
    "JUPUSDT", "INJUSDT", "FETUSDT", "TAOUSDT", "SEIUSDT",
    # Mid-cap with edge
    "DOGEUSDT", "ARBUSDT", "OPUSDT", "TIAUSDT", "FILUSDT",
    "LTCUSDT",
]

BINANCE_BASE = "https://api.binance.com"


def fetch_klines(pair: str, interval: str = "1h", limit: int = 300) -> pd.DataFrame | None:
    try:
        resp = requests.get(
            f"{BINANCE_BASE}/api/v3/klines",
            params={"symbol": pair, "interval": interval, "limit": limit},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        df = pd.DataFrame(data, columns=[
            "timestamp", "Open", "High", "Low", "Close", "Volume",
            "close_time", "quote_vol", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore",
        ])
        df = df[["timestamp", "Open", "High", "Low", "Close", "Volume"]].copy()
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        df.dropna(inplace=True)
        return df
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Indicator helpers
# ---------------------------------------------------------------------------
def sma(s, p):
    return s.rolling(p).mean()

def ema(s, p):
    return s.ewm(span=p, adjust=False).mean()

def rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)

def atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def macd(close, fast=12, slow=26, signal=9):
    ema_f = ema(close, fast)
    ema_s = ema(close, slow)
    macd_line = ema_f - ema_s
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def bollinger_bands(close, period=20, std_mult=2.0):
    mid = sma(close, period)
    std = close.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    width = (upper - lower) / mid
    pctb = (close - lower) / (upper - lower)
    return upper, mid, lower, width, pctb

def adx(high, low, close, period=14):
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_val = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr_val)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr_val)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx_val = dx.ewm(span=period, adjust=False).mean()
    return adx_val, plus_di, minus_di

def supertrend(high, low, close, period=10, multiplier=3.0):
    atr_val = atr(high, low, close, period)
    hl2 = (high + low) / 2
    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val
    st = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(1, index=close.index)
    for i in range(1, len(close)):
        if close.iloc[i] > upper_band.iloc[i - 1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]
        st.iloc[i] = lower_band.iloc[i] if direction.iloc[i] == 1 else upper_band.iloc[i]
    return direction


# ---------------------------------------------------------------------------
# Strategy 1: Cross-Agg Battleground Hybrid (KIMI — PASSED quality gates)
# Multi-system RSI consensus + volume + momentum
# ---------------------------------------------------------------------------
def strategy_cross_agg_hybrid(df, symbol):
    if len(df) < 60:
        return None
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]

    rsi7 = rsi(close, 7)
    rsi14 = rsi(close, 14)
    rsi21 = rsi(close, 21)
    atr14 = atr(high, low, close, 14)
    vol_sma = sma(vol, 20)
    ema9 = ema(close, 9)
    ema21 = ema(close, 21)

    last = -1
    r7, r14, r21 = rsi7.iloc[last], rsi14.iloc[last], rsi21.iloc[last]
    v_ratio = vol.iloc[last] / vol_sma.iloc[last] if vol_sma.iloc[last] > 0 else 0
    price = close.iloc[last]
    atr_val = atr14.iloc[last]

    if pd.isna(atr_val) or atr_val <= 0:
        return None

    # Multi-RSI consensus: all three in oversold zone
    rsi_aligned = r7 < 40 and r14 < 45 and r21 < 50
    # Volume confirmation
    vol_spike = v_ratio > 1.2
    # Momentum turning: EMA9 crossing above EMA21
    momentum = ema9.iloc[last] > ema21.iloc[last] and ema9.iloc[-2] <= ema21.iloc[-2]
    # Recovery signal: RSI7 turning up from oversold
    rsi_turning = r7 > rsi7.iloc[-2] and r7 < 45

    score = 0
    if rsi_aligned:
        score += 0.30
    if vol_spike:
        score += 0.20
    if momentum:
        score += 0.25
    if rsi_turning:
        score += 0.15
    if price > ema(close, 50).iloc[last]:
        score += 0.10

    if score < 0.45:
        return None

    confidence = min(0.90, 0.50 + score * 0.5)
    tp = round(price + 2.0 * atr_val, 8)
    sl = round(price - 1.5 * atr_val, 8)
    rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0

    return {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": round(price, 8),
        "take_profit": tp,
        "stop_loss": sl,
        "risk_reward": round(rr, 2),
        "confidence": round(confidence, 4),
        "strategy": "cross_agg_battleground_hybrid",
        "source": "KIMI_mutation",
        "reason": f"RSI consensus ({r7:.0f}/{r14:.0f}/{r21:.0f}) + vol {v_ratio:.1f}x + momentum",
    }


# ---------------------------------------------------------------------------
# Strategy 2: Genesis Momentum Blend (Claude — +20.90% PnL)
# GENESIS-style multi-indicator scoring + supertrend + ADX
# ---------------------------------------------------------------------------
def strategy_genesis_momentum(df, symbol):
    if len(df) < 60:
        return None
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]

    rsi14 = rsi(close, 14)
    macd_line, sig_line, hist = macd(close)
    atr14 = atr(high, low, close, 14)
    adx_val, plus_di, minus_di = adx(high, low, close, 14)
    st_dir = supertrend(high, low, close, 10, 3.0)
    ema9 = ema(close, 9)
    ema21 = ema(close, 21)
    ema50 = ema(close, 50)
    vol_sma = sma(vol, 20)

    last = -1
    price = close.iloc[last]
    atr_val = atr14.iloc[last]

    if pd.isna(atr_val) or atr_val <= 0:
        return None

    # GENESIS scoring system
    score = 0

    # Supertrend bullish
    if st_dir.iloc[last] == 1:
        score += 2

    # ADX trending (> 20) with plus_di leading
    if adx_val.iloc[last] > 20 and plus_di.iloc[last] > minus_di.iloc[last]:
        score += 2

    # EMA stack aligned (9 > 21 > 50)
    if ema9.iloc[last] > ema21.iloc[last] > ema50.iloc[last]:
        score += 2

    # MACD histogram positive and rising
    if hist.iloc[last] > 0:
        score += 1
    if hist.iloc[last] > hist.iloc[-2]:
        score += 1

    # RSI in bullish zone (40-70)
    r = rsi14.iloc[last]
    if 40 < r < 70:
        score += 1

    # Volume above average
    v_ratio = vol.iloc[last] / vol_sma.iloc[last] if vol_sma.iloc[last] > 0 else 0
    if v_ratio > 1.0:
        score += 1

    # Need at least 6/10 to signal
    if score < 6:
        return None

    confidence = min(0.90, 0.45 + score * 0.05)
    tp = round(price + 2.0 * atr_val, 8)
    sl = round(price - 1.5 * atr_val, 8)
    rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0

    return {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": round(price, 8),
        "take_profit": tp,
        "stop_loss": sl,
        "risk_reward": round(rr, 2),
        "confidence": round(confidence, 4),
        "strategy": "genesis_momentum_blend",
        "source": "Claude_super_mutation",
        "reason": f"Genesis score {score}/10: ST={'bull' if st_dir.iloc[last]==1 else 'bear'} ADX={adx_val.iloc[last]:.0f} RSI={r:.0f} MACD={'+'if hist.iloc[last]>0 else '-'}",
    }


# ---------------------------------------------------------------------------
# Strategy 3: MACD-RSI Confluence (Tournament winner — 85%+ WR on alts)
# ---------------------------------------------------------------------------
def strategy_macd_rsi_confluence(df, symbol):
    if len(df) < 60:
        return None
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    rsi14 = rsi(close, 14)
    macd_line, sig_line, hist = macd(close)
    atr14 = atr(high, low, close, 14)
    ema50 = ema(close, 50)

    last = -1
    price = close.iloc[last]
    atr_val = atr14.iloc[last]
    r = rsi14.iloc[last]

    if pd.isna(atr_val) or atr_val <= 0:
        return None

    # MACD histogram positive AND rising
    macd_bull = hist.iloc[last] > 0 and hist.iloc[last] > hist.iloc[-2]

    # RSI in recovery zone (35-55) — not overbought, not deeply oversold
    rsi_recovery = 35 < r < 55

    # MACD crossover (histogram just turned positive)
    macd_crossover = hist.iloc[-2] < 0 and hist.iloc[last] > 0

    # Price above 50 EMA (trend filter)
    above_trend = price > ema50.iloc[last]

    if not (macd_bull and rsi_recovery and above_trend):
        return None

    confidence = 0.60
    if macd_crossover:
        confidence += 0.15
    if r < 45:
        confidence += 0.10
    confidence = min(0.90, confidence)

    tp = round(price + 2.5 * atr_val, 8)
    sl = round(price - 1.2 * atr_val, 8)
    rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0

    return {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": round(price, 8),
        "take_profit": tp,
        "stop_loss": sl,
        "risk_reward": round(rr, 2),
        "confidence": round(confidence, 4),
        "strategy": "macd_rsi_confluence",
        "source": "Tournament_winner",
        "reason": f"MACD hist {hist.iloc[last]:.4f} (rising) + RSI {r:.0f} recovery + trend aligned",
    }


# ---------------------------------------------------------------------------
# Strategy 4: EMA Momentum with Volume (Tournament — 5.77 Sharpe on AVAX)
# ---------------------------------------------------------------------------
def strategy_ema_momentum_vol(df, symbol):
    if len(df) < 60:
        return None
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]

    ema9 = ema(close, 9)
    ema21 = ema(close, 21)
    ema50 = ema(close, 50)
    atr14 = atr(high, low, close, 14)
    vol_sma = sma(vol, 20)
    rsi14 = rsi(close, 14)

    last = -1
    price = close.iloc[last]
    atr_val = atr14.iloc[last]

    if pd.isna(atr_val) or atr_val <= 0:
        return None

    # Full EMA stack aligned: 9 > 21 > 50
    ema_aligned = ema9.iloc[last] > ema21.iloc[last] > ema50.iloc[last]

    # EMA9 just crossed above EMA21 (momentum ignition)
    ema_cross = ema9.iloc[-2] <= ema21.iloc[-2] and ema9.iloc[last] > ema21.iloc[last]

    # Volume spike
    v_ratio = vol.iloc[last] / vol_sma.iloc[last] if vol_sma.iloc[last] > 0 else 0
    vol_confirm = v_ratio > 1.3

    # RSI not overbought
    r = rsi14.iloc[last]
    rsi_ok = r < 70

    if not (ema_aligned and rsi_ok):
        return None

    confidence = 0.55
    if ema_cross:
        confidence += 0.20
    if vol_confirm:
        confidence += 0.10
    if r < 55:
        confidence += 0.05
    confidence = min(0.90, confidence)

    if confidence < 0.55:
        return None

    tp = round(price + 2.0 * atr_val, 8)
    sl = round(price - 1.5 * atr_val, 8)
    rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0

    return {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": round(price, 8),
        "take_profit": tp,
        "stop_loss": sl,
        "risk_reward": round(rr, 2),
        "confidence": round(confidence, 4),
        "strategy": "ema_momentum_volume",
        "source": "Tournament_winner",
        "reason": f"EMA stack aligned (9>{ema9.iloc[last]:.2f} > 21>{ema21.iloc[last]:.2f} > 50) vol={v_ratio:.1f}x RSI={r:.0f}",
    }


# ---------------------------------------------------------------------------
# Strategy 5: Bollinger Squeeze Breakout (mean-reversion in low vol)
# ---------------------------------------------------------------------------
def strategy_bb_squeeze_breakout(df, symbol):
    if len(df) < 60:
        return None
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]

    upper, mid, lower, width, pctb = bollinger_bands(close, 20, 2.0)
    atr14 = atr(high, low, close, 14)
    rsi14 = rsi(close, 14)
    vol_sma = sma(vol, 20)

    last = -1
    price = close.iloc[last]
    atr_val = atr14.iloc[last]
    w = width.iloc[last]
    pb = pctb.iloc[last]

    if pd.isna(atr_val) or atr_val <= 0 or pd.isna(w):
        return None

    # Bollinger squeeze: width in bottom 20% of recent range
    width_20 = width.rolling(50).quantile(0.2).iloc[last]
    is_squeeze = w < width_20 if not pd.isna(width_20) else w < 0.03

    # Price breaking above mid band after squeeze
    breaking_up = price > mid.iloc[last] and close.iloc[-2] <= mid.iloc[-2]

    # RSI confirming (not oversold)
    r = rsi14.iloc[last]
    rsi_ok = r > 40 and r < 65

    if not (is_squeeze and breaking_up and rsi_ok):
        return None

    v_ratio = vol.iloc[last] / vol_sma.iloc[last] if vol_sma.iloc[last] > 0 else 0
    confidence = 0.60
    if v_ratio > 1.3:
        confidence += 0.10
    if r < 55:
        confidence += 0.05
    confidence = min(0.90, confidence)

    tp = round(price + 2.5 * atr_val, 8)
    sl = round(price - 1.0 * atr_val, 8)
    rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0

    return {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": round(price, 8),
        "take_profit": tp,
        "stop_loss": sl,
        "risk_reward": round(rr, 2),
        "confidence": round(confidence, 4),
        "strategy": "bb_squeeze_breakout",
        "source": "Tournament_pattern",
        "reason": f"BB squeeze (width={w:.4f}) + breakout above mid + RSI={r:.0f}",
    }


# ---------------------------------------------------------------------------
# Main: Run all strategies, collect picks, output JSON + markdown
# ---------------------------------------------------------------------------
STRATEGIES = [
    ("cross_agg_battleground_hybrid", strategy_cross_agg_hybrid),
    ("genesis_momentum_blend", strategy_genesis_momentum),
    ("macd_rsi_confluence", strategy_macd_rsi_confluence),
    ("ema_momentum_volume", strategy_ema_momentum_vol),
    ("bb_squeeze_breakout", strategy_bb_squeeze_breakout),
]


def main():
    now = datetime.now(timezone.utc)
    print(f"{'='*70}")
    print(f"  TRACKED LIVE PICKS GENERATOR")
    print(f"  {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  {len(SYMBOLS)} symbols x {len(STRATEGIES)} strategies")
    print(f"{'='*70}\n")

    # Fetch data
    data = {}
    for sym in SYMBOLS:
        df = fetch_klines(sym, "1h", 300)
        if df is not None and len(df) >= 60:
            data[sym] = df
            print(f"  [OK] {sym}: {len(df)} bars, last={df['Close'].iloc[-1]:.4f}")
        else:
            print(f"  [--] {sym}: no data")
        time.sleep(0.15)

    print(f"\nFetched {len(data)}/{len(SYMBOLS)} symbols\n")

    # Run strategies
    all_picks = []
    for strat_name, strat_fn in STRATEGIES:
        picks_count = 0
        for sym, df in data.items():
            pick = strat_fn(df, sym)
            if pick:
                pick["timestamp"] = now.isoformat()
                pick["status"] = "ACTIVE"
                pick["outcome"] = "PENDING"
                pick["pnl_pct"] = 0.0
                all_picks.append(pick)
                picks_count += 1
                print(f"  [SIGNAL] {strat_name} -> {sym} {pick['direction']} @ {pick['entry_price']:.4f} "
                      f"TP={pick['take_profit']:.4f} SL={pick['stop_loss']:.4f} conf={pick['confidence']:.2f}")
        if picks_count == 0:
            print(f"  [quiet] {strat_name}: no signals")

    # Sort by confidence
    all_picks.sort(key=lambda p: p["confidence"], reverse=True)

    print(f"\n{'='*70}")
    print(f"  TOTAL: {len(all_picks)} picks from {len(STRATEGIES)} strategies")
    print(f"{'='*70}\n")

    # Save JSON
    output = {
        "generated_at": now.isoformat(),
        "num_picks": len(all_picks),
        "symbols_scanned": len(data),
        "strategies_run": len(STRATEGIES),
        "picks": all_picks,
    }

    json_path = PROJECT_ROOT / "genome" / "data" / "tracked_live_picks.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"Saved {len(all_picks)} picks to {json_path}")

    # Generate markdown for CHATWITHIT.md
    md_lines = []
    md_lines.append(f"### Live Picks for Forward-Testing ({now.strftime('%Y-%m-%d %H:%M UTC')})")
    md_lines.append("")
    md_lines.append(f"**Strategies:** {', '.join(s[0] for s in STRATEGIES)}")
    md_lines.append(f"**Symbols scanned:** {len(data)} | **Picks generated:** {len(all_picks)}")
    md_lines.append("")

    if all_picks:
        md_lines.append("| # | Symbol | Dir | Entry | TP | SL | R:R | Conf | Strategy | Reason |")
        md_lines.append("|---|--------|-----|-------|----|----|-----|------|----------|--------|")
        for i, p in enumerate(all_picks, 1):
            ep = p["entry_price"]
            dec = 6 if ep < 1 else (4 if ep < 100 else 2)
            md_lines.append(
                f"| {i} | {p['symbol']} | {p['direction']} | "
                f"{p['entry_price']:.{dec}f} | {p['take_profit']:.{dec}f} | {p['stop_loss']:.{dec}f} | "
                f"{p['risk_reward']:.1f} | {p['confidence']:.0%} | "
                f"`{p['strategy']}` | {p['reason'][:60]} |"
            )
    else:
        md_lines.append("**No picks generated** — market conditions don't meet any strategy's entry criteria. This is expected and means filters are working correctly.")

    md_lines.append("")
    md_lines.append("**Forward-test rules:** Check these picks in 24h. If price hit TP → WIN. If price hit SL → LOSS. If neither → TIMEOUT (exit at 24h close).")
    md_lines.append(f"**Validation file:** `genome/data/tracked_live_picks.json`")

    md_text = "\n".join(md_lines)

    md_path = PROJECT_ROOT / "genome" / "data" / "tracked_picks_chatwithit_entry.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"Saved CHATWITHIT entry to {md_path}")

    # Print the markdown (handle Windows encoding)
    print(f"\n--- CHATWITHIT.md Entry ---\n")
    print(md_text.encode("ascii", errors="replace").decode("ascii"))

    return all_picks


if __name__ == "__main__":
    main()
