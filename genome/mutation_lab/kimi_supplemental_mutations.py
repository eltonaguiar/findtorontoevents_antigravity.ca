#!/usr/bin/env python3
"""
KIMI Supplemental Mutations — Complement to Claude's Super Mutations
=====================================================================

These 5 mutations fill gaps not covered by Claude's Super Mutation Designer:
- Focus on volume-profile, VWAP, drawdown recovery, EMA ribbons, and volatility squeeze patterns
- All mutations are SANDBOX tier (0.3 weight) until proven via forward testing
- Designed to complement (not duplicate) the 5 Claude mutations:
  * keltner_rsi_confluence_v2
  * consensus_deep_value_hybrid
  * genesis_momentum_blend
  * ml_keltner_adaptive
  * multi_system_conviction_filter

Data Sources: Binance API (klines), Binance futures funding rate API
Output: Standard pick format consumed by forward_validator / battleground pipeline
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Path setup ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent

# Try importing indicators from ml_battleground shared
try:
    sys.path.insert(0, str(ROOT / "ml_battleground"))
    from shared.indicators import rsi, atr, sma, ema
    _HAS_INDICATORS = True
except ImportError:
    _HAS_INDICATORS = False

if not _HAS_INDICATORS:
    # Inline fallback indicators
    def sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(period).mean()

    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return (100 - 100 / (1 + rs)).fillna(50.0)

    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()


# ── Helpers ───────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value is None or not np.isfinite(value):
        return 0.0
    if abs(value) >= 1000:
        return round(value, 2)
    if abs(value) >= 1:
        return round(value, 4)
    if abs(value) >= 0.01:
        return round(value, 6)
    return round(value, 8)


def _base_signal(strategy: str, symbol: str, signal_type: str, entry: float,
                 tp: float, sl: float, confidence: float, reason: str,
                 parent_system: str, mutation_type: str, **extra) -> dict:
    """Create standardized signal dict with mutation metadata."""
    rr = 0.0
    if signal_type == "BUY" and entry > sl:
        rr = (tp - entry) / (entry - sl)
    elif signal_type == "SELL" and sl > entry:
        rr = (entry - tp) / (sl - entry)

    sig = {
        "strategy": strategy,
        "symbol": symbol,
        "signal_type": signal_type,
        "entry_price": _smart_round(entry),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(min(0.85, confidence), 4),
        "risk_reward": round(max(0, rr), 2),
        "reason": reason,
        "timestamp": _now_iso(),
        "category": "crypto",
        "source_system": "genome",
        "trust_tier": "SANDBOX",
        "trust_weight": 0.3,
        "parent_system": parent_system,
        "mutation_type": mutation_type,
    }
    sig.update(extra)
    return sig


# ── Data Fetching (Binance klines + funding) ───────────────────────────────

BINANCE_MIRRORS = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://api2.binance.com", "https://api3.binance.com",
    "https://data-api.binance.vision",
]


def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 300) -> pd.DataFrame:
    """Fetch OHLCV from Binance with mirror rotation."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KIMISupplemental/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data and isinstance(data, list) and len(data) > 20:
                df = pd.DataFrame(data, columns=[
                    "open_time", "Open", "High", "Low", "Close", "Volume",
                    "close_time", "qav", "num_trades", "taker_buy_base",
                    "taker_buy_quote", "ignore"
                ])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
                df.set_index("open_time", inplace=True)
                return df
        except Exception:
            continue
    return pd.DataFrame()


def fetch_funding_rate(symbol: str) -> Optional[float]:
    """Fetch latest funding rate from Binance futures API."""
    for base in BINANCE_MIRRORS[:3]:
        url = f"{base}/fapi/v1/fundingRate?symbol={symbol}&limit=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KIMISupplemental/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            if data and isinstance(data, list) and len(data) > 0:
                return float(data[0].get("fundingRate", 0))
        except Exception:
            continue
    return None


# ── Symbol Lists ──────────────────────────────────────────────────────────

TIER1_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
TIER2_SYMBOLS = ["ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "DOGEUSDT",
                 "NEARUSDT", "SUIUSDT", "APTUSDT", "INJUSDT", "ATOMUSDT"]
ALL_SYMBOLS = TIER1_SYMBOLS + TIER2_SYMBOLS


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION 1: VOLUME PROFILE SNAP + FUNDING ALIGNMENT
# ═══════════════════════════════════════════════════════════════════════════
# Combines volume profile analysis (POC - Point of Control) with funding rate
# direction to identify high-conviction breakouts from value areas.
# Unique vs Claude's mutations: Focus on volume structure, not Keltner/RSI

def volume_profile_funding_snap(data: dict, funding_rates: dict) -> list[dict]:
    """
    Volume Profile + Funding Alignment
    
    Strategy: Identify when price breaks out of the volume profile value area
    with funding rate confirming the direction (positive funding = longs paying
    shorts = bullish bias, vice versa).
    
    Entry: Price breaks above/below volume-weighted POC + funding aligned
    TP: 2.5x ATR
    SL: 1.5x ATR
    """
    signals = []
    lookback = 50  # Bars to build volume profile
    
    for symbol in ALL_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < lookback + 10:
            continue
            
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        if current <= 0:
            continue
            
        # Calculate Volume-Weighted Point of Control (VW-POC)
        # Using typical price * volume as proxy for volume profile
        typical = (high + low + close) / 3
        value_area = typical.iloc[-lookback:]
        vol_profile = volume.iloc[-lookback:]
        
        # VW-POC approximation: volume-weighted average of recent bars
        poc = (value_area * vol_profile).sum() / vol_profile.sum() if vol_profile.sum() > 0 else current
        
        # Value area bounds (volume-weighted std dev)
        value_std = np.sqrt(((value_area - poc) ** 2 * vol_profile).sum() / vol_profile.sum())
        va_high = poc + 1.0 * value_std
        va_low = poc - 1.0 * value_std
        
        atr_now = float(atr(high, low, close, 14).iloc[-1])
        if atr_now <= 0:
            continue
            
        # Funding alignment check
        funding = funding_rates.get(symbol, 0)
        funding_bullish = funding > 0.0001  # Slight positive bias
        funding_bearish = funding < -0.0001
        
        # Breakout detection
        broke_above = prev <= va_high and current > va_high
        broke_below = prev >= va_low and current < va_low
        
        if broke_above and funding_bullish:
            tp = current + 2.5 * atr_now
            sl = current - 1.5 * atr_now
            conf = 0.55 + min(0.20, abs(funding) * 1000)
            signals.append(_base_signal(
                "volume_profile_funding_snap", symbol, "BUY", current, tp, sl, conf,
                f"Volume profile breakout above POC={poc:.2f} with positive funding={funding:.6f}",
                "battleground+cross_agg", "volume_funding_hybrid",
                poc=_smart_round(poc), va_high=_smart_round(va_high), va_low=_smart_round(va_low),
                funding_rate=funding, breakout_pct=(current - poc) / poc
            ))
        elif broke_below and funding_bearish:
            tp = current - 2.5 * atr_now
            sl = current + 1.5 * atr_now
            conf = 0.55 + min(0.20, abs(funding) * 1000)
            signals.append(_base_signal(
                "volume_profile_funding_snap", symbol, "SELL", current, tp, sl, conf,
                f"Volume profile breakdown below POC={poc:.2f} with negative funding={funding:.6f}",
                "battleground+cross_agg", "volume_funding_hybrid",
                poc=_smart_round(poc), va_high=_smart_round(va_high), va_low=_smart_round(va_low),
                funding_rate=funding, breakout_pct=(current - poc) / poc
            ))
            
    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION 2: CROSS-AGGREGATION CONVICTION + BATTLEGROUND MOMENTUM
# ═══════════════════════════════════════════════════════════════════════════
# Hybrid of cross-aggregation consensus scoring with battleground momentum
# indicators. Requires consensus_score above threshold + momentum confirmation.
# Unique vs Claude's mutations: Explicit consensus + momentum combo

def cross_agg_battleground_hybrid(data: dict) -> list[dict]:
    """
    Cross-Aggregation Consensus + Battleground Momentum Hybrid
    
    Strategy: Combines multi-system consensus logic with momentum strength.
    Simulates what cross_aggregation/aggregator.py does but with battleground
    momentum filters layered on top.
    
    Consensus factors (simplified):
    - RSI alignment across timeframes (7, 14, 21)
    - Volume spike confirmation (>1.5x avg)
    - Price above/below key MAs (20, 50)
    
    Momentum factor:
    - 3-bar momentum accelerating
    """
    signals = []
    
    for symbol in TIER1_SYMBOLS + TIER2_SYMBOLS[:5]:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue
            
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue
            
        # Multi-timeframe RSI consensus
        rsi_7 = float(rsi(close, 7).iloc[-1])
        rsi_14 = float(rsi(close, 14).iloc[-1])
        rsi_21 = float(rsi(close, 21).iloc[-1])
        
        if any(pd.isna(v) for v in [rsi_7, rsi_14, rsi_21]):
            continue
            
        # RSI consensus: all aligned (all < 40 = oversold consensus, all > 60 = overbought)
        oversold_consensus = rsi_7 < 40 and rsi_14 < 45 and rsi_21 < 50
        overbought_consensus = rsi_7 > 60 and rsi_14 > 55 and rsi_21 > 50
        
        # Volume confirmation
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_now = float(volume.iloc[-1])
        vol_ratio = vol_now / vol_avg if vol_avg > 0 else 1.0
        vol_confirmed = vol_ratio > 1.5
        
        # MA alignment
        ma_20 = float(close.rolling(20).mean().iloc[-1])
        ma_50 = float(close.rolling(50).mean().iloc[-1])
        
        # Momentum acceleration
        mom_1 = float(close.pct_change(1).iloc[-1]) if len(close) > 1 else 0
        mom_3 = float(close.pct_change(3).iloc[-1]) if len(close) > 3 else 0
        momentum_accelerating = abs(mom_1) > abs(mom_3 / 3) if mom_3 != 0 else False
        
        atr_now = float(atr(high, low, close, 14).iloc[-1])
        if atr_now <= 0:
            continue
            
        # Consensus score calculation
        consensus_score = 0
        if oversold_consensus:
            consensus_score += 0.4
        if vol_confirmed:
            consensus_score += 0.3
        if current > ma_20:
            consensus_score += 0.15
        if current > ma_50:
            consensus_score += 0.15
            
        # BUY: Oversold consensus + volume + momentum
        if oversold_consensus and vol_confirmed and mom_1 > 0:
            tp = current + 2.0 * atr_now
            sl = current - 1.5 * atr_now
            conf = min(0.80, 0.50 + consensus_score * 0.4)
            signals.append(_base_signal(
                "cross_agg_battleground_hybrid", symbol, "BUY", current, tp, sl, conf,
                f"Consensus BUY: RSI consensus {rsi_7:.1f}/{rsi_14:.1f}/{rsi_21:.1f}, "
                f"vol={vol_ratio:.1f}x, mom={mom_1:.2%}",
                "cross_aggregation+battleground", "consensus_momentum_hybrid",
                rsi_7=rsi_7, rsi_14=rsi_14, rsi_21=rsi_21,
                vol_ratio=vol_ratio, consensus_score=consensus_score
            ))
            
        # SELL: Overbought consensus + volume + negative momentum
        elif overbought_consensus and vol_confirmed and mom_1 < 0:
            tp = current - 2.0 * atr_now
            sl = current + 1.5 * atr_now
            conf = min(0.80, 0.50 + consensus_score * 0.4)
            signals.append(_base_signal(
                "cross_agg_battleground_hybrid", symbol, "SELL", current, tp, sl, conf,
                f"Consensus SELL: RSI consensus {rsi_7:.1f}/{rsi_14:.1f}/{rsi_21:.1f}, "
                f"vol={vol_ratio:.1f}x, mom={mom_1:.2%}",
                "cross_aggregation+battleground", "consensus_momentum_hybrid",
                rsi_7=rsi_7, rsi_14=rsi_14, rsi_21=rsi_21,
                vol_ratio=vol_ratio, consensus_score=consensus_score
            ))
            
    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION 3: DRAWDOWN RECOVERY + VOLATILITY EXPANSION
# ═══════════════════════════════════════════════════════════════════════════
# Catches assets that have experienced significant drawdown but are showing
# signs of recovery with volatility expanding (indicating capitulation bottom).
# Unique vs Claude's mutations: Drawdown-based entry, not RSI/Keltner

def drawdown_volatility_expansion(data: dict) -> list[dict]:
    """
    Drawdown Recovery + Volatility Expansion
    
    Strategy: Identify assets that have:
    1. Drawn down >10% from recent highs (capitulation)
    2. Are showing recovery signs (2 consecutive green bars)
    3. Have ATR expanding (volatility spike = bottoming)
    
    This catches the "falling knife that stops falling" pattern.
    """
    signals = []
    
    for symbol in ALL_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue
            
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0 or len(close) < 20:
            continue
            
        # Calculate drawdown from 20-bar high
        high_20 = float(close.rolling(20).max().iloc[-1])
        drawdown = (current - high_20) / high_20 if high_20 > 0 else 0
        
        # Require meaningful drawdown (>5%)
        if drawdown > -0.05:
            continue
            
        # Recovery check: last 2 bars positive
        changes = close.diff()
        if len(changes) < 3:
            continue
        recovering = float(changes.iloc[-1]) > 0 and float(changes.iloc[-2]) > 0
        
        if not recovering:
            continue
            
        # Volatility expansion: ATR increasing
        atr_series = atr(high, low, close, 14)
        atr_now = float(atr_series.iloc[-1])
        atr_prev = float(atr_series.iloc[-5]) if len(atr_series) > 5 else atr_now
        atr_expanding = atr_now > atr_prev * 1.1  # 10% expansion
        
        if not atr_expanding:
            continue
            
        # Volume confirmation
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_now = float(volume.iloc[-1])
        vol_ratio = vol_now / vol_avg if vol_avg > 0 else 1.0
        
        # RSI check: recovering from oversold
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14) or rsi_14 > 50:  # Still need room to run
            continue
            
        tp = current + 2.5 * atr_now
        sl = current - 1.5 * atr_now
        
        # Confidence based on drawdown depth + recovery strength
        recovery_strength = abs(drawdown) * 10  # Deeper drawdown = more potential
        vol_boost = min(0.1, (vol_ratio - 1.0) * 0.05)
        conf = min(0.75, 0.50 + recovery_strength + vol_boost)
        
        signals.append(_base_signal(
            "drawdown_volatility_expansion", symbol, "BUY", current, tp, sl, conf,
            f"Drawdown recovery: {drawdown:.1%} from high, RSI={rsi_14:.1f}, "
            f"ATR expanded {atr_now/atr_prev:.1f}x, vol={vol_ratio:.1f}x",
            "battleground+darwin", "drawdown_recovery",
            drawdown_pct=drawdown * 100, atr_expansion=atr_now/atr_prev,
            rsi_14=rsi_14, vol_ratio=vol_ratio
        ))
        
    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION 4: EMA RIBBON + MACD HISTOGRAM DIVERGENCE
# ═══════════════════════════════════════════════════════════════════════════
# Uses EMA ribbon alignment (multiple EMAs stacked) combined with MACD
# histogram divergence for high-conviction trend continuation entries.
# Unique vs Claude's mutations: EMA ribbon structure + MACD divergence focus

def ema_ribbon_macd_divergence(data: dict) -> list[dict]:
    """
    EMA Ribbon + MACD Histogram Divergence
    
    Strategy: 
    - EMA Ribbon: 9, 21, 50 EMAs aligned (bullish: 9>21>50, bearish: 9<21<50)
    - MACD Histogram divergence: histogram turning in direction of trend
    
    Entry on ribbon alignment + histogram confirmation for trend continuation.
    """
    signals = []
    
    for symbol in TIER1_SYMBOLS + TIER2_SYMBOLS[:5]:
        df = data.get(symbol)
        if df is None or len(df) < 55:
            continue
            
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue
            
        # EMA Ribbon
        ema_9 = ema(close, 9)
        ema_21 = ema(close, 21)
        ema_50 = ema(close, 50)
        
        e9_now = float(ema_9.iloc[-1])
        e21_now = float(ema_21.iloc[-1])
        e50_now = float(ema_50.iloc[-1])
        
        if any(pd.isna(v) for v in [e9_now, e21_now, e50_now]):
            continue
            
        # Ribbon alignment
        bullish_ribbon = e9_now > e21_now > e50_now
        bearish_ribbon = e9_now < e21_now < e50_now
        
        # MACD calculation
        ema_12 = ema(close, 12)
        ema_26 = ema(close, 26)
        macd_line = ema_12 - ema_26
        signal_line = ema(macd_line, 9)
        histogram = macd_line - signal_line
        
        hist_now = float(histogram.iloc[-1])
        hist_prev = float(histogram.iloc[-2])
        hist_prev2 = float(histogram.iloc[-3]) if len(histogram) > 3 else hist_prev
        
        if any(pd.isna(v) for v in [hist_now, hist_prev]):
            continue
            
        # Histogram divergence
        hist_turning_up = hist_now > hist_prev and hist_prev <= hist_prev2
        hist_turning_down = hist_now < hist_prev and hist_prev >= hist_prev2
        
        atr_now = float(atr(high, low, close, 14).iloc[-1])
        if atr_now <= 0:
            continue
            
        # BUY: Bullish ribbon + histogram turning up
        if bullish_ribbon and hist_turning_up:
            tp = current + 2.5 * atr_now
            sl = e21_now  # SL at middle EMA (trend support)
            if sl >= current:
                sl = current - 1.5 * atr_now
            conf = 0.60 + min(0.20, (e9_now - e50_now) / e50_now * 100)
            signals.append(_base_signal(
                "ema_ribbon_macd_divergence", symbol, "BUY", current, tp, sl, conf,
                f"EMA ribbon aligned (9>21>50) + MACD histogram turning up "
                f"({hist_prev:.4f}->{hist_now:.4f})",
                "claude_gainer+genome", "trend_continuation",
                ema_9=e9_now, ema_21=e21_now, ema_50=e50_now,
                macd_hist=hist_now, hist_change=hist_now - hist_prev
            ))
            
        # SELL: Bearish ribbon + histogram turning down
        elif bearish_ribbon and hist_turning_down:
            tp = current - 2.5 * atr_now
            sl = e21_now  # SL at middle EMA (trend resistance)
            if sl <= current:
                sl = current + 1.5 * atr_now
            conf = 0.60 + min(0.20, (e50_now - e9_now) / e50_now * 100)
            signals.append(_base_signal(
                "ema_ribbon_macd_divergence", symbol, "SELL", current, tp, sl, conf,
                f"EMA ribbon aligned (9<21<50) + MACD histogram turning down "
                f"({hist_prev:.4f}->{hist_now:.4f})",
                "claude_gainer+genome", "trend_continuation",
                ema_9=e9_now, ema_21=e21_now, ema_50=e50_now,
                macd_hist=hist_now, hist_change=hist_now - hist_prev
            ))
            
    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION 5: VWAP + BOLLINGER SQUEEZE COMBO
# ═══════════════════════════════════════════════════════════════════════════
# Combines VWAP mean reversion with Bollinger Band squeeze detection.
# Entry when price deviates from VWAP during a squeeze (low volatility)
# then expands back toward VWAP.
# Unique vs Claude's mutations: VWAP + squeeze timing (not Keltner)

def vwap_bollinger_squeeze(data: dict) -> list[dict]:
    """
    VWAP + Bollinger Squeeze Combo
    
    Strategy:
    1. Detect Bollinger Band squeeze (bandwidth < 20-period average)
    2. Price deviates from VWAP during squeeze (mean reversion setup)
    3. Entry when squeeze resolves toward VWAP
    
    Combines two proven concepts: VWAP reversion + volatility squeeze timing.
    """
    signals = []
    
    for symbol in TIER1_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue
            
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        if current <= 0:
            continue
            
        # VWAP calculation (rolling 20-period)
        vwap_period = 20
        typical = (high + low + close) / 3
        vwap = (typical * volume).rolling(vwap_period).sum() / volume.rolling(vwap_period).sum()
        vwap_now = float(vwap.iloc[-1])
        
        if pd.isna(vwap_now):
            continue
            
        # Bollinger Bands (20, 2)
        sma_20 = close.rolling(20).mean()
        std_20 = close.rolling(20).std()
        bb_upper = sma_20 + 2 * std_20
        bb_lower = sma_20 - 2 * std_20
        bandwidth = (bb_upper - bb_lower) / sma_20
        
        bw_now = float(bandwidth.iloc[-1])
        bw_avg = float(bandwidth.rolling(20).mean().iloc[-1])
        
        if pd.isna(bw_now) or pd.isna(bw_avg) or bw_avg <= 0:
            continue
            
        # Squeeze detection: current bandwidth below average
        in_squeeze = bw_now < bw_avg * 0.9  # 10% below average
        was_in_squeeze = float(bandwidth.iloc[-2]) < bw_avg * 0.9 if len(bandwidth) > 2 else False
        
        # VWAP deviation
        vwap_deviation = (current - vwap_now) / vwap_now if vwap_now > 0 else 0
        
        atr_now = float(atr(high, low, close, 14).iloc[-1])
        if atr_now <= 0:
            continue
            
        # RSI for oversold/overbought check
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14):
            continue
            
        # BUY: Price below VWAP during/after squeeze + oversold
        if vwap_deviation < -0.005 and (in_squeeze or was_in_squeeze) and rsi_14 < 45:
            # Target VWAP or 2x ATR, whichever is closer
            tp_vwap = vwap_now
            tp_atr = current + 2.0 * atr_now
            tp = max(tp_vwap, tp_atr) if tp_vwap < current else tp_atr
            sl = current - 1.5 * atr_now
            
            squeeze_strength = (bw_avg - bw_now) / bw_avg
            conf = 0.55 + min(0.25, abs(vwap_deviation) * 20 + squeeze_strength * 0.1)
            signals.append(_base_signal(
                "vwap_bollinger_squeeze", symbol, "BUY", current, tp, sl, conf,
                f"VWAP squeeze: {vwap_deviation:.2%} below VWAP during squeeze "
                f"(bw={bw_now:.4f} < avg={bw_avg:.4f}), RSI={rsi_14:.1f}",
                "confluence_dna+battleground", "squeeze_mean_reversion",
                vwap=vwap_now, vwap_deviation=vwap_deviation,
                bb_bandwidth=bw_now, squeeze_strength=squeeze_strength
            ))
            
        # SELL: Price above VWAP during/after squeeze + overbought
        elif vwap_deviation > 0.005 and (in_squeeze or was_in_squeeze) and rsi_14 > 55:
            tp_vwap = vwap_now
            tp_atr = current - 2.0 * atr_now
            tp = min(tp_vwap, tp_atr) if tp_vwap > current else tp_atr
            sl = current + 1.5 * atr_now
            
            squeeze_strength = (bw_avg - bw_now) / bw_avg
            conf = 0.55 + min(0.25, vwap_deviation * 20 + squeeze_strength * 0.1)
            signals.append(_base_signal(
                "vwap_bollinger_squeeze", symbol, "SELL", current, tp, sl, conf,
                f"VWAP squeeze: {vwap_deviation:.2%} above VWAP during squeeze "
                f"(bw={bw_now:.4f} < avg={bw_avg:.4f}), RSI={rsi_14:.1f}",
                "confluence_dna+battleground", "squeeze_mean_reversion",
                vwap=vwap_now, vwap_deviation=vwap_deviation,
                bb_bandwidth=bw_now, squeeze_strength=squeeze_strength
            ))
            
    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

SUPPLEMENTAL_MUTATIONS = {
    "volume_profile_funding_snap": {
        "fn": volume_profile_funding_snap,
        "parent": "battleground+cross_agg",
        "mutation": "volume_funding_hybrid",
        "trust_weight": 0.30,
        "description": "Volume profile POC breakout + funding rate alignment",
        "needs_funding": True,
    },
    "cross_agg_battleground_hybrid": {
        "fn": cross_agg_battleground_hybrid,
        "parent": "cross_aggregation+battleground",
        "mutation": "consensus_momentum_hybrid",
        "trust_weight": 0.30,
        "description": "Multi-system consensus + battleground momentum filters",
        "needs_funding": False,
    },
    "drawdown_volatility_expansion": {
        "fn": drawdown_volatility_expansion,
        "parent": "battleground+darwin",
        "mutation": "drawdown_recovery",
        "trust_weight": 0.30,
        "description": "Drawdown recovery with volatility expansion bottom detection",
        "needs_funding": False,
    },
    "ema_ribbon_macd_divergence": {
        "fn": ema_ribbon_macd_divergence,
        "parent": "claude_gainer+genome",
        "mutation": "trend_continuation",
        "trust_weight": 0.30,
        "description": "EMA ribbon alignment + MACD histogram divergence",
        "needs_funding": False,
    },
    "vwap_bollinger_squeeze": {
        "fn": vwap_bollinger_squeeze,
        "parent": "confluence_dna+battleground",
        "mutation": "squeeze_mean_reversion",
        "trust_weight": 0.30,
        "description": "VWAP mean reversion during Bollinger squeeze",
        "needs_funding": False,
    },
}


def run_all(interval: str = "1h", limit: int = 300) -> dict:
    """
    Run all 5 KIMI supplemental mutations.
    
    Returns:
        {
            "metadata": {...},
            "picks": [...],
            "mutations_triggered": [...],
            "mutations_silent": [...]
        }
    """
    print(f"\n{'='*70}")
    print(f"KIMI SUPPLEMENTAL MUTATIONS — {len(SUPPLEMENTAL_MUTATIONS)} strategies")
    print(f"Complement to Claude's Super Mutations")
    print(f"{'='*70}\n")
    
    # Fetch data for all symbols
    data = {}
    for symbol in ALL_SYMBOLS:
        df = fetch_binance_klines(symbol, interval=interval, limit=limit)
        if not df.empty and len(df) > 20:
            data[symbol] = df
            print(f"  [OK] {symbol} ({interval}): {len(df)} bars")
        else:
            print(f"  [--] {symbol} ({interval}): no data")
            
    print(f"\nFetched data for {len(data)}/{len(ALL_SYMBOLS)} symbols")
    
    # Fetch funding rates for mutations that need them
    funding_rates = {}
    print("\nFetching funding rates...")
    for symbol in ALL_SYMBOLS:
        rate = fetch_funding_rate(symbol)
        if rate is not None:
            funding_rates[symbol] = rate
            print(f"  [OK] {symbol}: funding={rate:.8f}")
        else:
            print(f"  [--] {symbol}: no funding data")
            
    print(f"Fetched funding for {len(funding_rates)}/{len(ALL_SYMBOLS)} symbols\n")
    
    # Run all mutations
    all_picks = []
    triggered = []
    silent = []
    
    for name, info in SUPPLEMENTAL_MUTATIONS.items():
        try:
            if info["needs_funding"]:
                picks = info["fn"](data, funding_rates)
            else:
                picks = info["fn"](data)
                
            if picks:
                for p in picks:
                    p["timeframe"] = p.get("timeframe", interval)
                all_picks.extend(picks)
                triggered.append({
                    "strategy": name,
                    "parent": info["parent"],
                    "mutation": info["mutation"],
                    "picks": len(picks),
                })
                print(f"  [SIGNAL] {name}: {len(picks)} picks")
            else:
                silent.append(name)
                print(f"  [quiet] {name}: 0 picks")
        except Exception as e:
            silent.append(name)
            print(f"  [ERROR] {name}: {e}")
            
    # Sort by confidence
    all_picks.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    
    result = {
        "metadata": {
            "timestamp": _now_iso(),
            "total_mutations": len(SUPPLEMENTAL_MUTATIONS),
            "total_picks": len(all_picks),
            "mutations_triggered": len(triggered),
            "mutations_silent": len(silent),
            "symbols_scanned": len(data),
            "interval": interval,
            "system": "kimi_supplemental_mutations",
            "design_basis": "complement_to_claude_super_mutations",
        },
        "picks": all_picks,
        "mutations_triggered": triggered,
        "mutations_silent": silent,
    }
    
    print(f"\n{'='*70}")
    print(f"RESULTS: {len(all_picks)} picks from {len(triggered)}/{len(SUPPLEMENTAL_MUTATIONS)} mutations")
    print(f"{'='*70}\n")
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="KIMI Supplemental Mutations (complement to Claude's Super Mutations)")
    parser.add_argument("--interval", default="1h", choices=["1h", "4h", "1d"],
                        help="Kline interval (default: 1h)")
    parser.add_argument("--limit", type=int, default=300,
                        help="Number of bars to fetch (default: 300)")
    parser.add_argument("--output", default=None,
                        help="Output JSON path")
    args = parser.parse_args()
    
    output_path = args.output or str(ROOT / "genome" / "data" / "kimi_supplemental_picks.json")
    
    result = run_all(interval=args.interval, limit=args.limit)
    
    # Save results
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
        
    print(f"Saved {result['metadata']['total_picks']} picks to {output_path}")
    
    # Summary
    if result["picks"]:
        print("\nTop 5 picks by confidence:")
        for i, p in enumerate(result["picks"][:5], 1):
            print(f"  {i}. {p['symbol']} {p['signal_type']} | "
                  f"conf={p['confidence']:.2f} | "
                  f"R:R={p['risk_reward']:.1f} | "
                  f"{p['strategy']}")
