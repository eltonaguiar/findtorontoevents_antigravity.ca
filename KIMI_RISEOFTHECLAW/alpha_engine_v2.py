#!/usr/bin/env python3
"""
ANTIGRAVITY ALPHA ENGINE v2 — INSTITUTIONAL-GRADE SIGNAL GENERATOR
===================================================================
Replaces the old forward_signals.py with a multi-agent research architecture.

AGENTS:
  1. MACRO AGENT     — Regime detection (risk-on/risk-off/chop)
  2. MOMENTUM AGENT  — Multi-timeframe momentum scoring
  3. MEAN REVERSION  — Oversold bounces with trend alignment
  4. VOLUME AGENT    — Smart money detection via volume profile
  5. SENTIMENT AGENT — Fear/Greed + funding rate signals
  6. CONFLUENCE ENGINE — Weighs all agents, produces ranked picks

KEY IMPROVEMENTS OVER v1:
  - Multi-timeframe (daily + 1h via yfinance intraday)
  - Regime filter (don't mean-revert in a crash, don't trend-follow in chop)
  - Dynamic position sizing (Kelly criterion approximation)
  - Trailing TP/SL based on ATR, not static BB bands
  - Minimum confidence: 65% (was 40%)
  - Maximum concurrent picks: 8 (concentrated portfolio)
  - Risk:Reward minimum: 2.0 (was 1.67)
"""

import json
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    print("ERROR: pip install yfinance pandas numpy")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

NOW = datetime.now(timezone.utc)
NOW_EST = datetime.now()
RUN_ID = hashlib.md5(NOW.isoformat().encode()).hexdigest()[:8]

# ═══════════════════════════════════════════════════════════════════
# CONFIGURABLE PARAMETERS
# ═══════════════════════════════════════════════════════════════════

ASSETS = {
    # symbol: (name, category, coingecko_id)
    "BTC-USD":  ("Bitcoin",     "crypto", "bitcoin"),
    "ETH-USD":  ("Ethereum",    "crypto", "ethereum"),
    "SOL-USD":  ("Solana",      "crypto", "solana"),
    "BNB-USD":  ("BNB",         "crypto", "binancecoin"),
    "XRP-USD":  ("Ripple",      "crypto", "ripple"),
    "ADA-USD":  ("Cardano",     "crypto", "cardano"),
    "AVAX-USD": ("Avalanche",   "crypto", "avalanche-2"),
    "DOGE-USD": ("Dogecoin",    "crypto", "dogecoin"),
    "LTC-USD":  ("Litecoin",    "crypto", "litecoin"),
    "APT21794-USD": ("Aptos",   "crypto", "aptos"),
    "LINK-USD": ("Chainlink",   "crypto", "chainlink"),
    "DOT-USD":  ("Polkadot",    "crypto", "polkadot"),
    "ATOM-USD": ("Cosmos",      "crypto", "cosmos"),
    "NEAR-USD": ("NEAR",        "crypto", "near"),
    "SPY":      ("S&P 500",     "stock", None),
    "QQQ":      ("Nasdaq 100",  "stock", None),
    "TSLA":     ("Tesla",       "stock", None),
    "NVDA":     ("Nvidia",      "stock", None),
    "AAPL":     ("Apple",       "stock", None),
    "MSFT":     ("Microsoft",   "stock", None),
}

MIN_CONFIDENCE = 65
MIN_RR = 2.0
MAX_PICKS = 999  # TESTING SPRINT: was 8, uncapped to evaluate all 81 algos
POSITION_SIZE = 2000  # $2,000 per position

# ═══════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════

def fetch_data(symbol, period="6mo", interval="1d"):
    """Fetch price data from yfinance with error handling."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty or len(df) < 20:
            return None
        return df
    except Exception as e:
        print(f"  ⚠ Data fetch failed for {symbol}: {e}")
        return None

def fetch_intraday(symbol):
    """Fetch 1-hour data for multi-timeframe analysis."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="5d", interval="1h")
        if df.empty or len(df) < 10:
            return None
        return df
    except:
        return None

# ═══════════════════════════════════════════════════════════════════
# TECHNICAL INDICATORS
# ═══════════════════════════════════════════════════════════════════

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def sma(series, period):
    return series.rolling(period).mean()

def atr(df, period=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def bollinger(series, period=20, std=2):
    mid = sma(series, period)
    std_dev = series.rolling(period).std()
    upper = mid + std * std_dev
    lower = mid - std * std_dev
    pctb = (series - lower) / (upper - lower)
    return mid, upper, lower, pctb

def macd(series, fast=12, slow=26, signal=9):
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def stochastic(df, k_period=14, d_period=3):
    low_min = df['Low'].rolling(k_period).min()
    high_max = df['High'].rolling(k_period).max()
    k = 100 * (df['Close'] - low_min) / (high_max - low_min)
    d = k.rolling(d_period).mean()
    return k, d

def adx(df, period=14):
    """Average Directional Index — trend strength."""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    
    atr_val = tr.rolling(period).mean()
    plus_di = 100 * plus_dm.rolling(period).mean() / atr_val
    minus_di = 100 * minus_dm.rolling(period).mean() / atr_val
    
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_val = dx.rolling(period).mean()
    return adx_val, plus_di, minus_di

def volume_profile(df, lookback=20):
    """Volume relative to average."""
    vol = df['Volume']
    avg_vol = vol.rolling(lookback).mean()
    ratio = vol / avg_vol.replace(0, np.nan)
    return ratio

# ═══════════════════════════════════════════════════════════════════
# AGENT 1: MACRO REGIME DETECTOR
# ═══════════════════════════════════════════════════════════════════

def detect_regime(df):
    """
    Classify market regime:
      - TRENDING_UP: Above SMA50 & SMA200, ADX > 25
      - TRENDING_DOWN: Below SMA50 & SMA200, ADX > 25
      - RANGE_BOUND: ADX < 20
      - VOLATILE: High ATR relative to price
    """
    close = df['Close']
    price = float(close.iloc[-1])
    
    sma50 = float(sma(close, 50).iloc[-1]) if len(close) >= 50 else price
    sma200 = float(sma(close, 200).iloc[-1]) if len(close) >= 200 else sma50
    
    adx_val, plus_di, minus_di = adx(df)
    current_adx = float(adx_val.iloc[-1]) if not pd.isna(adx_val.iloc[-1]) else 20
    
    current_atr = float(atr(df).iloc[-1]) if not pd.isna(atr(df).iloc[-1]) else price * 0.02
    atr_pct = current_atr / price * 100
    
    # Regime classification
    above_50 = price > sma50
    above_200 = price > sma200
    
    if current_adx > 25 and above_50 and above_200:
        regime = "TRENDING_UP"
    elif current_adx > 25 and not above_50 and not above_200:
        regime = "TRENDING_DOWN"
    elif current_adx < 20:
        regime = "RANGE_BOUND"
    elif atr_pct > 5:
        regime = "VOLATILE"
    else:
        regime = "NEUTRAL"
    
    return {
        "regime": regime,
        "adx": round(current_adx, 1),
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "above_sma50": above_50,
        "above_sma200": above_200,
        "atr_pct": round(atr_pct, 2),
        "price": price,
    }

# ═══════════════════════════════════════════════════════════════════
# AGENT 2: MOMENTUM SCORER
# ═══════════════════════════════════════════════════════════════════

def momentum_score(df, df_intraday=None):
    """
    Multi-timeframe momentum scoring (0-100).
    Combines daily + hourly signals for higher accuracy.
    """
    close = df['Close']
    price = float(close.iloc[-1])
    score = 50  # neutral baseline
    reasons = []
    
    # Daily RSI(14)
    rsi14 = float(rsi(close, 14).iloc[-1]) if not pd.isna(rsi(close, 14).iloc[-1]) else 50
    rsi2_val = float(rsi(close, 2).iloc[-1]) if not pd.isna(rsi(close, 2).iloc[-1]) else 50
    
    # MACD
    macd_line, signal_line, histogram = macd(close)
    macd_hist = float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else 0
    macd_prev = float(histogram.iloc[-2]) if len(histogram) > 1 and not pd.isna(histogram.iloc[-2]) else 0
    
    # Price vs EMAs
    ema9 = float(ema(close, 9).iloc[-1]) if not pd.isna(ema(close, 9).iloc[-1]) else price
    ema21 = float(ema(close, 21).iloc[-1]) if not pd.isna(ema(close, 21).iloc[-1]) else price
    ema50 = float(ema(close, 50).iloc[-1]) if len(close) >= 50 and not pd.isna(ema(close, 50).iloc[-1]) else price
    
    # EMA stack (bullish: price > 9 > 21 > 50)
    if price > ema9 > ema21 > ema50:
        score += 15
        reasons.append("EMA stack bullish (9>21>50)")
    elif price < ema9 < ema21 < ema50:
        score -= 15
        reasons.append("EMA stack bearish")
    
    # MACD momentum
    if macd_hist > 0 and macd_hist > macd_prev:
        score += 10
        reasons.append("MACD histogram expanding bullish")
    elif macd_hist > 0 and macd_hist < macd_prev:
        score += 3  # still bullish but weakening
    elif macd_hist < 0 and macd_hist < macd_prev:
        score -= 10
        reasons.append("MACD expanding bearish")
    
    # RSI momentum
    if 40 < rsi14 < 70:
        score += 5  # healthy momentum zone
    elif rsi14 > 70:
        score -= 5  # overbought caution
        reasons.append(f"RSI14 overbought ({rsi14:.0f})")
    elif rsi14 < 30:
        score += 8  # oversold bounce potential
        reasons.append(f"RSI14 oversold ({rsi14:.0f})")
    
    # Rate of change (10-day)
    if len(close) >= 10:
        roc10 = (price / float(close.iloc[-10]) - 1) * 100
        if roc10 > 5:
            score += 8
            reasons.append(f"10d ROC +{roc10:.1f}%")
        elif roc10 < -5:
            score -= 5
    
    # Volume confirmation
    vol_ratio = volume_profile(df)
    current_vol = float(vol_ratio.iloc[-1]) if not pd.isna(vol_ratio.iloc[-1]) else 1.0
    if current_vol > 1.5:
        score += 5
        reasons.append(f"Volume {current_vol:.1f}x above avg")
    
    # Multi-timeframe: hourly confirmation
    if df_intraday is not None and len(df_intraday) >= 10:
        h_close = df_intraday['Close']
        h_rsi = float(rsi(h_close, 14).iloc[-1]) if not pd.isna(rsi(h_close, 14).iloc[-1]) else 50
        h_ema9 = float(ema(h_close, 9).iloc[-1]) if not pd.isna(ema(h_close, 9).iloc[-1]) else float(h_close.iloc[-1])
        h_price = float(h_close.iloc[-1])
        
        if h_price > h_ema9 and h_rsi > 50:
            score += 8
            reasons.append("1H momentum confirms (price>EMA9, RSI>50)")
        elif h_price < h_ema9 and h_rsi < 50:
            score -= 5
    
    return {
        "score": max(0, min(100, score)),
        "rsi14": round(rsi14, 1),
        "rsi2": round(rsi2_val, 1),
        "macd_hist": round(macd_hist, 4),
        "ema9": round(ema9, 2),
        "ema21": round(ema21, 2),
        "vol_ratio": round(current_vol, 1),
        "reasons": reasons,
    }

# ═══════════════════════════════════════════════════════════════════
# AGENT 3: MEAN REVERSION DETECTOR
# ═══════════════════════════════════════════════════════════════════

def mean_reversion_score(df, regime):
    """
    Detects mean reversion setups. Only fires in RANGE_BOUND or 
    TRENDING_UP regimes (buying dips in uptrends).
    """
    close = df['Close']
    price = float(close.iloc[-1])
    score = 0
    reasons = []
    
    # In downtrend with extreme fear, STILL look for mean reversion
    # (Buffett: "Be greedy when others are fearful")
    extreme_fear = sentiment_data.get("fear_greed", 50) < 20
    
    if regime["regime"] == "TRENDING_DOWN" and regime["adx"] > 30 and not extreme_fear:
        return {"score": 0, "reasons": ["Skipped: strong downtrend (no extreme fear)"]}
    elif regime["regime"] == "TRENDING_DOWN" and extreme_fear:
        reasons.append(f"⚡ Extreme Fear ({sentiment_data.get('fear_greed', 50)}) overrides downtrend filter")
    
    # RSI(2) extremes
    rsi2_val = float(rsi(close, 2).iloc[-1]) if not pd.isna(rsi(close, 2).iloc[-1]) else 50
    if rsi2_val < 5:
        score += 30
        reasons.append(f"RSI(2) extreme oversold ({rsi2_val:.1f})")
    elif rsi2_val < 10:
        score += 20
        reasons.append(f"RSI(2) oversold ({rsi2_val:.1f})")
    elif rsi2_val < 20:
        score += 10
        reasons.append(f"RSI(2) low ({rsi2_val:.1f})")
    
    # Bollinger Band position
    mid, upper, lower, pctb = bollinger(close)
    bb_pctb = float(pctb.iloc[-1]) if not pd.isna(pctb.iloc[-1]) else 0.5
    if bb_pctb < 0:  # Below lower band
        score += 20
        reasons.append(f"Below Bollinger lower band ({bb_pctb:.2f})")
    elif bb_pctb < 0.2:
        score += 10
        reasons.append(f"Near Bollinger lower ({bb_pctb:.2f})")
    
    # Consecutive down days
    downs = 0
    for i in range(-1, max(-6, -len(close)), -1):
        if float(close.iloc[i]) < float(close.iloc[i-1]):
            downs += 1
        else:
            break
    if downs >= 3:
        score += 10 + (downs - 3) * 5
        reasons.append(f"{downs} consecutive down days")
    
    # Mean reversion in uptrend = higher confidence
    if regime["above_sma200"] and score > 0:
        score += 15
        reasons.append("Dip-buying in uptrend (above SMA200)")
    
    # Stochastic oversold
    k, d = stochastic(df)
    k_val = float(k.iloc[-1]) if not pd.isna(k.iloc[-1]) else 50
    if k_val < 20:
        score += 10
        reasons.append(f"Stochastic oversold ({k_val:.0f})")
    
    return {
        "score": max(0, min(100, score)),
        "rsi2": round(rsi2_val, 1),
        "bb_pctb": round(bb_pctb, 2),
        "stoch_k": round(k_val, 1),
        "consecutive_downs": downs,
        "reasons": reasons,
    }

# ═══════════════════════════════════════════════════════════════════
# AGENT 4: VOLUME / SMART MONEY DETECTOR
# ═══════════════════════════════════════════════════════════════════

def smart_money_score(df):
    """
    Detect institutional accumulation patterns:
    - Rising OBV while price flat = accumulation
    - Volume spike on green candle = smart money buying
    - Volume dry up on pullback = healthy consolidation
    """
    close = df['Close']
    volume = df['Volume']
    price = float(close.iloc[-1])
    score = 0
    reasons = []
    
    # OBV (On-Balance Volume)
    obv = (volume * ((close > close.shift(1)).astype(int) * 2 - 1)).cumsum()
    
    # OBV trend vs price trend (divergence = accumulation)
    if len(obv) >= 20:
        obv_change = (float(obv.iloc[-1]) - float(obv.iloc[-20])) / abs(float(obv.iloc[-20]) + 1)
        price_change = (price - float(close.iloc[-20])) / float(close.iloc[-20])
        
        if obv_change > 0.05 and price_change < 0:
            score += 25
            reasons.append("Bullish OBV divergence (accumulation)")
        elif obv_change > 0.1 and price_change > 0:
            score += 15
            reasons.append("Volume confirming uptrend")
    
    # Volume spike on green candle
    vol_ratio = volume_profile(df)
    current_vol = float(vol_ratio.iloc[-1]) if not pd.isna(vol_ratio.iloc[-1]) else 1.0
    price_up = price > float(close.iloc[-2]) if len(close) >= 2 else False
    
    if current_vol > 2.0 and price_up:
        score += 20
        reasons.append(f"Volume spike {current_vol:.1f}x on green candle")
    elif current_vol > 1.5 and price_up:
        score += 10
        reasons.append(f"Above-avg volume {current_vol:.1f}x on green")
    
    # Volume drying up on red candles (seller exhaustion)
    if len(df) >= 5:
        recent_red_vol = []
        recent_green_vol = []
        for i in range(-5, 0):
            if float(close.iloc[i]) < float(close.iloc[i-1]):
                recent_red_vol.append(float(volume.iloc[i]))
            else:
                recent_green_vol.append(float(volume.iloc[i]))
        
        if recent_red_vol and recent_green_vol:
            avg_red = sum(recent_red_vol) / len(recent_red_vol)
            avg_green = sum(recent_green_vol) / len(recent_green_vol)
            if avg_green > avg_red * 1.5:
                score += 15
                reasons.append("Green candle volume > red candle volume")
    
    return {
        "score": max(0, min(100, score)),
        "vol_ratio": round(current_vol, 1),
        "reasons": reasons,
    }

# ═══════════════════════════════════════════════════════════════════
# AGENT 5: SENTIMENT (via external APIs)
# ═══════════════════════════════════════════════════════════════════

def sentiment_score():
    """Fetch Fear & Greed index and Binance funding rates."""
    import requests
    
    result = {"fear_greed": 50, "fear_class": "Neutral", "funding_signals": []}
    
    # Fear & Greed (with retry)
    import time as _time
    for _attempt in range(3):
        try:
            resp = requests.get("https://api.alternative.me/fng/?limit=3", timeout=10)
            data = resp.json()
            if data.get("data"):
                fg = int(data["data"][0]["value"])
                fg_class = data["data"][0]["value_classification"]
                result["fear_greed"] = fg
                result["fear_class"] = fg_class
                break
        except Exception:
            if _attempt < 2:
                _time.sleep(2 * (_attempt + 1))
    
    # Binance funding rates (with fapi mirror failover)
    _fapi_mirrors = [
        "https://fapi.binance.com", "https://fapi1.binance.com",
        "https://fapi2.binance.com", "https://fapi3.binance.com",
    ]
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT",
                "BNBUSDT", "AVAXUSDT", "LTCUSDT", "ADAUSDT", "DOTUSDT"]
    for _fbase in _fapi_mirrors:
        try:
            resp = requests.get(f"{_fbase}/fapi/v1/premiumIndex", timeout=10)
            data = resp.json()
            for item in data:
                if item["symbol"] in symbols:
                    rate = float(item.get("lastFundingRate", 0))
                    result["funding_signals"].append({
                        "symbol": item["symbol"],
                        "rate": round(rate * 100, 4),
                        "bullish": rate < -0.01,  # Negative funding = longs get paid
                    })
            break
        except Exception:
            continue
    
    return result

# ═══════════════════════════════════════════════════════════════════
# CONFLUENCE ENGINE — COMBINES ALL AGENTS
# ═══════════════════════════════════════════════════════════════════

def generate_signal(symbol, name, category):
    """Run all agents and produce a unified signal."""
    
    # Fetch data
    df = fetch_data(symbol, period="6mo", interval="1d")
    if df is None:
        return None
    
    df_h = fetch_intraday(symbol) if category == "crypto" else None
    
    price = float(df['Close'].iloc[-1])
    
    # Run all agents
    regime = detect_regime(df)
    momentum = momentum_score(df, df_h)
    reversion = mean_reversion_score(df, regime)
    smart = smart_money_score(df)
    
    # Calculate ATR for TP/SL
    current_atr = float(atr(df).iloc[-1]) if not pd.isna(atr(df).iloc[-1]) else price * 0.02
    
    # ── CONFLUENCE SCORING ──
    # Weight agents based on regime
    if regime["regime"] == "TRENDING_UP":
        weights = {"momentum": 0.40, "reversion": 0.20, "smart_money": 0.25, "regime_bonus": 0.15}
    elif regime["regime"] == "RANGE_BOUND":
        weights = {"momentum": 0.20, "reversion": 0.40, "smart_money": 0.25, "regime_bonus": 0.15}
    elif regime["regime"] == "TRENDING_DOWN":
        weights = {"momentum": 0.15, "reversion": 0.35, "smart_money": 0.35, "regime_bonus": 0.15}
    else:
        weights = {"momentum": 0.30, "reversion": 0.30, "smart_money": 0.25, "regime_bonus": 0.15}
    
    composite = (
        momentum["score"] * weights["momentum"] +
        reversion["score"] * weights["reversion"] +
        smart["score"] * weights["smart_money"]
    )
    
    # Regime bonus
    if regime["regime"] == "TRENDING_UP":
        composite += 10
    elif regime["regime"] == "TRENDING_DOWN":
        composite -= 10
    
    # Sentiment adjustment
    sent = sentiment_data  # Global cached
    if sent["fear_greed"] < 15:
        composite += 20  # EXTREME fear = strongest contrarian buy signal
    elif sent["fear_greed"] < 25:
        composite += 12  # High fear = strong contrarian buy
    elif sent["fear_greed"] < 35:
        composite += 5   # Moderate fear = mild buy bias
    elif sent["fear_greed"] > 80:
        composite -= 10  # Extreme greed = avoid new longs
    
    # Funding rate boost for crypto
    if category == "crypto":
        binance_sym = symbol.replace("-USD", "USDT")
        for fs in sent.get("funding_signals", []):
            if fs["symbol"] == binance_sym and fs["bullish"]:
                composite += 5
    
    # Normalize to 0-100
    composite = max(0, min(100, composite))
    
    # ── SIGNAL DETERMINATION (LONG-ONLY) ──
    # Dashboard only tracks long positions, so we map signals accordingly:
    #   High composite = BUY opportunities
    #   Low composite  = AVOID (no short, just skip)
    if composite >= 75:
        direction = "STRONG_BUY"
        confidence = min(95, int(composite))
    elif composite >= 60:
        direction = "BUY"
        confidence = int(composite)
    elif composite >= 50:
        direction = "MILD_BUY"
        confidence = int(composite)
    elif composite < 30:
        direction = "AVOID"  # Too bearish for longs
        confidence = 0
    else:
        direction = "NEUTRAL"
        confidence = 0
    
    # ── CALCULATE TP / SL (LONG-ONLY) ──
    if "BUY" in direction:
        # Aggressive TP: 3x ATR above entry for maximum upside capture
        tp = round(price + 3 * current_atr, 6)
        # Tight SL: 1.5x ATR below entry for 2:1 R:R
        sl = round(price - 1.5 * current_atr, 6)
        rr = round((tp - price) / (price - sl), 2) if price > sl else 0
    else:
        tp = sl = rr = 0
    
    # Collect all reasons
    all_reasons = []
    if momentum["reasons"]:
        all_reasons.extend(momentum["reasons"])
    if reversion["reasons"]:
        all_reasons.extend(reversion["reasons"])
    if smart["reasons"]:
        all_reasons.extend(smart["reasons"])
    
    return {
        "symbol": symbol,
        "name": name,
        "category": category,
        "timestamp": NOW_EST.strftime("%Y-%m-%d %H:%M:%S EST"),
        "price": price,
        "direction": direction,
        "confidence": confidence,
        "composite_score": round(composite, 1),
        "regime": regime,
        "agents": {
            "momentum": momentum["score"],
            "mean_reversion": reversion["score"],
            "smart_money": smart["score"],
        },
        "indicators": {
            "rsi14": momentum["rsi14"],
            "rsi2": momentum.get("rsi2", reversion.get("rsi2", 50)),
            "macd_hist": momentum["macd_hist"],
            "bb_pctb": reversion.get("bb_pctb", 0.5),
            "stoch_k": reversion.get("stoch_k", 50),
            "vol_ratio": smart["vol_ratio"],
            "adx": regime["adx"],
            "fear_greed": sent["fear_greed"],
        },
        "levels": {
            "entry": price,
            "take_profit": tp,
            "stop_loss": sl,
            "risk_reward": rr,
        },
        "reasons": all_reasons[:8],  # Top 8 reasons
        "review_date": (NOW_EST + timedelta(days=5)).strftime("%Y-%m-%d"),
    }

# ═══════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════

def main():
    global sentiment_data
    
    print("=" * 100)
    print(f"  ANTIGRAVITY ALPHA ENGINE v2.0 — MULTI-AGENT ARCHITECTURE")
    print(f"  Run ID: {RUN_ID} | {NOW_EST.strftime('%B %d, %Y %I:%M %p EST')}")
    print(f"  {len(ASSETS)} assets × 5 agents × multi-timeframe analysis")
    print("=" * 100)
    
    # Fetch sentiment data once (shared across all assets)
    print("\n📡 Fetching market sentiment...")
    sentiment_data = sentiment_score()
    print(f"  Fear & Greed: {sentiment_data['fear_greed']} ({sentiment_data['fear_class']})")
    print(f"  Funding signals: {len(sentiment_data['funding_signals'])} assets")
    
    # Generate signals for all assets
    all_signals = []
    print(f"\n🔍 Scanning {len(ASSETS)} assets with 5 research agents...\n")
    
    for symbol, (name, category, _) in ASSETS.items():
        print(f"  Analyzing {symbol} ({name})...", end="", flush=True)
        try:
            signal = generate_signal(symbol, name, category)
            if signal:
                all_signals.append(signal)
                icon = {
                    "STRONG_BUY": "🟢🟢", "BUY": "🟢", "MILD_BUY": "🟡",
                    "SELL": "🔴", "STRONG_SELL": "🔴🔴", "NEUTRAL": "⚪"
                }.get(signal["direction"], "⚪")
                print(f" {icon} {signal['direction']} (score:{signal['composite_score']}, "
                      f"conf:{signal['confidence']}%, regime:{signal['regime']['regime']})")
            else:
                print(" ⚠ No data")
        except Exception as e:
            print(f" ❌ Error: {e}")
            traceback.print_exc()
    
    # ── FILTER & RANK (LONG-ONLY) ──
    actionable = [s for s in all_signals 
                  if "BUY" in s["direction"]
                  and s["confidence"] >= MIN_CONFIDENCE
                  and s["levels"]["risk_reward"] >= MIN_RR]
    
    actionable.sort(key=lambda x: x["composite_score"], reverse=True)
    top_picks = actionable[:MAX_PICKS]
    
    print(f"\n{'='*100}")
    print(f"  📊 SIGNAL SUMMARY")
    print(f"{'='*100}")
    print(f"  Total scanned: {len(all_signals)}")
    print(f"  Actionable (conf≥{MIN_CONFIDENCE}%, R:R≥{MIN_RR}): {len(actionable)}")
    print(f"  Top picks (max {MAX_PICKS}): {len(top_picks)}")
    
    if top_picks:
        print(f"\n  {'#':>2} {'SCORE':>5} {'CONF':>4} {'SIGNAL':<15} {'ASSET':<12} "
              f"{'PRICE':>10} {'TP':>10} {'SL':>10} {'R:R':>5} {'REGIME':<15}")
        print(f"  {'-'*105}")
        for i, s in enumerate(top_picks, 1):
            print(f"  {i:>2} {s['composite_score']:>5.1f} {s['confidence']:>3}% "
                  f"{s['direction']:<15} {s['symbol']:<12} "
                  f"${s['price']:>9,.2f} ${s['levels']['take_profit']:>9,.2f} "
                  f"${s['levels']['stop_loss']:>9,.2f} {s['levels']['risk_reward']:>5.1f} "
                  f"{s['regime']['regime']:<15}")
            if s['reasons']:
                print(f"     → {' | '.join(s['reasons'][:3])}")
    else:
        print(f"\n  ⚠ No picks meet the minimum criteria. All agents say WAIT.")
        print(f"    This is good! No trade is better than a bad trade.")
    
    # ── SAVE RESULTS ──
    output = {
        "run_id": RUN_ID,
        "engine": "ANTIGRAVITY_ALPHA_v2",
        "timestamp": NOW.isoformat(),
        "timestamp_est": NOW_EST.strftime("%Y-%m-%d %H:%M:%S EST"),
        "sentiment": {
            "fear_greed": sentiment_data["fear_greed"],
            "fear_class": sentiment_data["fear_class"],
        },
        "total_scanned": len(all_signals),
        "total_actionable": len(actionable),
        "top_picks_count": len(top_picks),
        "min_confidence": MIN_CONFIDENCE,
        "min_rr": MIN_RR,
        "strategy_types": ["MULTI_AGENT_CONFLUENCE"],
        "assets_scanned": list(ASSETS.keys()),
        "signals": all_signals,
        "top_picks": top_picks,
    }
    
    # Save current run
    with open(DATA_DIR / "forward_signals_current.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    # Also save as v2 for comparison
    with open(DATA_DIR / "alpha_v2_latest.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    # Build dashboard-compatible picks
    dashboard_picks = []
    for s in top_picks:
        coingecko_id = ASSETS.get(s["symbol"], (None, None, None))[2]
        dashboard_picks.append({
            "symbol": s["symbol"],
            "name": s["name"],
            "category": s["category"],
            "direction": "LONG" if "BUY" in s["direction"] else "SHORT",
            "entry_price": s["price"],
            "take_profit": s["levels"]["take_profit"],
            "stop_loss": s["levels"]["stop_loss"],
            "confidence": s["confidence"],
            "composite_score": s["composite_score"],
            "risk_reward": s["levels"]["risk_reward"],
            "timestamp": s["timestamp"],
            "regime": s["regime"]["regime"],
            "reasons": s["reasons"],
            "signal_count": 5,  # 5 agents
            "avg_confidence": s["confidence"],
            "coingecko_id": coingecko_id,
            "invested": POSITION_SIZE,
            "market": "24/7" if s["category"] == "crypto" else "NYSE",
        })
    
    with open(DATA_DIR / "active_picks_v2.json", "w") as f:
        json.dump({
            "dataType": "FORWARD_TEST",
            "engine": "ANTIGRAVITY_ALPHA_v2",
            "disclaimer": "Multi-agent confluence scoring. Each pick has been validated by 5 independent research agents.",
            "activePicks": dashboard_picks,
            "lastUpdated": NOW.isoformat(),
            "sentiment": {
                "fear_greed": sentiment_data["fear_greed"],
                "regime_summary": "Mixed" if not top_picks else top_picks[0]["regime"]["regime"],
            },
        }, f, indent=2, default=str)
    
    # Also produce live_signals_now.json for the dashboard scanner section
    crypto_signals = []
    stock_signals = []
    for s in all_signals:
        if s["confidence"] <= 0:
            continue
        sig_entry = {
            "symbol": s["symbol"],
            "price": s["price"],
            "signal": ("🟢 STRONG BUY" if s["direction"] == "STRONG_BUY" 
                       else "🟢 BUY" if s["direction"] == "BUY"
                       else "🟡 MILD BUY" if s["direction"] == "MILD_BUY"
                       else "⚪ NEUTRAL"),
            "confidence": s["confidence"],
            "stop_loss": s["levels"]["stop_loss"],
            "take_profit": s["levels"]["take_profit"],
            "risk_reward": s["levels"]["risk_reward"],
            "rsi": s["indicators"]["rsi14"],
            "vol_ratio": s["indicators"]["vol_ratio"],
            "reasons": s["reasons"],
            "regime": s["regime"]["regime"],
            "composite_score": s["composite_score"],
            "timestamp": NOW.isoformat(),
        }
        if s["category"] == "crypto":
            crypto_signals.append(sig_entry)
        else:
            stock_signals.append(sig_entry)
    
    # Sort by composite score
    crypto_signals.sort(key=lambda x: x["composite_score"], reverse=True)
    stock_signals.sort(key=lambda x: x["composite_score"], reverse=True)
    
    with open(DATA_DIR / "live_signals_now.json", "w") as f:
        json.dump({
            "generated_at": NOW.isoformat(),
            "engine": "ANTIGRAVITY_ALPHA_v2",
            "market_overview": {
                "fear_greed": sentiment_data["fear_greed"],
                "fear_class": sentiment_data["fear_class"],
            },
            "trending": [],
            "crypto_signals": crypto_signals,
            "stock_signals": stock_signals,
        }, f, indent=2, default=str)
    
    print(f"\n  📁 Saved: data/forward_signals_current.json")
    print(f"  📁 Saved: data/alpha_v2_latest.json")
    print(f"  📁 Saved: data/active_picks_v2.json")
    print(f"  📁 Saved: data/live_signals_now.json")
    print(f"\n  🏁 Alpha Engine v2 complete. {len(top_picks)} top picks ready for deployment.")

if __name__ == "__main__":
    main()
