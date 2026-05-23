"""
Approach C: Spike Reverse-Engineering Scanner
Identifies pre-spike patterns across top crypto assets and enters when
current conditions match historical spike archetypes.

Core concept: Analyze what happens BEFORE big moves (>3% in 4h). Build a
pattern library of pre-spike conditions. In real-time, match current market state
against spike archetypes. Enter when pattern similarity is high.

v2.0 adds:
  - Top 20 liquid altcoins (ETH, SOL, XRP, etc.)
  - Meme coin rapid-scan tier (TRUMP, PEPE, BONK, etc.) with wider params
  - CoinGecko trending integration for confidence boost
  - ATR-based SL (2x ATR), mid-TP trailing stop, wider tolerances

Target: 50-150 high-conviction trades/year across all assets.

Run: python breakout_arena/approach_c_spike_reverse/scanner.py [--dry-run]
"""

import argparse
import json
import math
import os
import sys
import time
import requests
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCANNER_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCANNER_DIR, "data")

ACTIVE_PICKS_PATH = os.path.join(DATA_DIR, "active_picks.json")
CLOSED_PICKS_PATH = os.path.join(DATA_DIR, "closed_picks.json")
DASHBOARD_PATH = os.path.join(DATA_DIR, "dashboard.json")
SPIKE_HISTORY_PATH = os.path.join(DATA_DIR, "spike_history.json")

SYSTEM_NAME = "approach_c_spike_reverse"
VERSION = "2.0.0"
EST = timezone(timedelta(hours=-5))

# ---------------------------------------------------------------------------
# Asset tiers
# ---------------------------------------------------------------------------

# Tier 1: Large caps — original BTC + top 20 liquid pairs
TIER1_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "MATICUSDT",
    "NEARUSDT", "SUIUSDT", "APTUSDT", "OPUSDT", "ARBUSDT",
    "INJUSDT", "TIAUSDT", "SEIUSDT", "FETUSDT", "RENDERUSDT",
    "TAOUSDT",
]

# Tier 2: Meme coins — higher volatility, different parameters
MEME_SYMBOLS = [
    "TRUMPUSDT", "DEXEUSDT", "BONKUSDT", "PEPEUSDT", "WIFUSDT",
    "FLOKIUSDT", "SHIBUSDT",
]

ALL_SYMBOLS = TIER1_SYMBOLS + MEME_SYMBOLS

# Per-tier configuration
TIER1_CONFIG = {
    "spike_threshold_pct": 3.0,
    "kline_interval": "4h",
    "kline_limit": 500,
    "min_volume_ratio": 1.2,
    "sl_atr_multiplier": 2.0,      # v2: was 1.5, widened to reduce stop-outs
    "tp_magnitude_scale": 0.90,
    "trail_activate_pct": 3.0,
    "trail_from_hwm_pct": 4.0,
    "max_hold_hours": 48,
    "round_trip_cost_pct": 0.25,
}

MEME_CONFIG = {
    "spike_threshold_pct": 5.0,     # memes move bigger — need higher bar
    "kline_interval": "2h",         # shorter lookback for fast movers
    "kline_limit": 500,
    "min_volume_ratio": 5.0,        # require 5x avg volume for meme confirmation
    "sl_atr_multiplier": 2.5,       # wider SL for meme volatility
    "tp_magnitude_scale": 0.80,     # slightly more conservative TP
    "trail_activate_pct": 5.0,      # activate trailing later (memes whipsaw)
    "trail_from_hwm_pct": 6.0,      # wider trail for meme volatility
    "max_hold_hours": 24,           # shorter hold — memes fade fast
    "round_trip_cost_pct": 0.30,    # higher cost (wider spreads on memes)
}

def _get_tier_config(symbol: str) -> dict:
    """Return the appropriate config for a symbol's tier."""
    if symbol in MEME_SYMBOLS:
        return MEME_CONFIG
    return TIER1_CONFIG

def _get_tier_name(symbol: str) -> str:
    """Return tier label for logging."""
    if symbol in MEME_SYMBOLS:
        return "MEME"
    return "TIER1"

# ---------------------------------------------------------------------------
# Cost model
# ---------------------------------------------------------------------------
ROUND_TRIP_COST_PCT = 0.25  # default; overridden per-tier in pick creation

# ---------------------------------------------------------------------------
# Risk management constants
# ---------------------------------------------------------------------------
MAX_CONCURRENT = 999        # TESTING SPRINT: was 2, uncapped to evaluate spike picks
MAX_DRAWDOWN = 0.20         # 20% circuit breaker
STARTING_EQUITY = 10_000.0
MIN_RR = 2.0                # higher bar -- we wait for big moves
TRAIL_ACTIVATE_PCT = 3.0    # default; overridden per-tier
TRAIL_FROM_HWM_PCT = 4.0    # default; overridden per-tier
MAX_HOLD_HOURS = 48         # default; overridden per-tier

# ---------------------------------------------------------------------------
# Spike detection thresholds
# ---------------------------------------------------------------------------
SPIKE_THRESHOLD_PCT = 3.0   # default; overridden per-tier
PRE_SPIKE_LOOKBACK = 20     # bars before spike to extract pattern
ARCHETYPE_MATCH_THRESHOLD = 0.60   # minimum score to consider
SIGNAL_MATCH_THRESHOLD = 0.65      # minimum to generate signal
MIN_VOLUME_RATIO = 1.2             # default; overridden per-tier

# ---------------------------------------------------------------------------
# Binance REST helpers
# ---------------------------------------------------------------------------
_BINANCE_BASES = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]
BINANCE_BASE = "https://api.binance.com"
BINANCE_FAPI = "https://fapi.binance.com"


def _fetch_klines(symbol: str, interval: str, limit: int = 500) -> Optional[pd.DataFrame]:
    """Fetch OHLCV from Binance (with endpoint failover) + OKX/Bybit fallback."""
    # Binance (try all endpoints)
    for base in _BINANCE_BASES:
        try:
            resp = requests.get(
                f"{base}/api/v3/klines",
                params={"symbol": symbol, "interval": interval, "limit": limit},
                timeout=10,
            )
            if resp.status_code in (451, 403):
                continue  # geo-blocked, try next
            resp.raise_for_status()
            data = resp.json()
            if data:
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
                if len(df) >= 50:
                    return df
        except Exception:
            continue

    # OKX fallback
    try:
        inst_id = symbol.replace("USDT", "-USDT")
        bar_map = {"1h": "1H", "4h": "4H", "1d": "1D"}
        bar = bar_map.get(interval, "4H")
        resp = requests.get(
            f"https://www.okx.com/api/v5/market/candles",
            params={"instId": inst_id, "bar": bar, "limit": str(min(limit, 300))},
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json().get("data", [])
        if rows:
            rows.reverse()
            df = pd.DataFrame(rows, columns=[
                "timestamp", "Open", "High", "Low", "Close", "Volume",
                "vol_ccy", "vol_ccy_quote", "confirm",
            ])
            df = df[["timestamp", "Open", "High", "Low", "Close", "Volume"]].copy()
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            df.dropna(inplace=True)
            if len(df) >= 50:
                return df
    except Exception:
        pass

    return None


def _fetch_fear_greed() -> int:
    """Current Fear & Greed index (0-100) with retry."""
    import time as _time
    for attempt in range(3):
        try:
            resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
            return int(resp.json()["data"][0]["value"])
        except Exception:
            if attempt < 2:
                _time.sleep(2 * (attempt + 1))
    return 50


def _fetch_funding_rate(symbol: str = "BTCUSDT") -> float:
    """Current Binance futures funding rate."""
    try:
        resp = requests.get(
            f"{BINANCE_FAPI}/fapi/v1/premiumIndex",
            params={"symbol": symbol},
            timeout=10,
        )
        resp.raise_for_status()
        return float(resp.json().get("lastFundingRate", 0))
    except Exception:
        return 0.0


def _fetch_live_price(symbol: str = "BTCUSDT", retries: int = 3) -> Optional[dict]:
    """Live price + 24h high/low. Multi-exchange fallback with retry to prevent stale picks."""
    import time as _time

    for attempt in range(retries):
        if attempt > 0:
            wait = 2 ** attempt  # exponential backoff: 2s, 4s
            print(f"  [RETRY] Attempt {attempt + 1}/{retries} for {symbol} (waiting {wait}s)")
            _time.sleep(wait)

        # Attempt 1: Binance ticker
        try:
            resp = requests.get(
                f"{BINANCE_BASE}/api/v3/ticker/24hr",
                params={"symbol": symbol},
                timeout=15,
            )
            resp.raise_for_status()
            d = resp.json()
            return {
                "price": float(d["lastPrice"]),
                "high": float(d["highPrice"]),
                "low": float(d["lowPrice"]),
            }
        except Exception as e:
            print(f"  [WARN] Binance ticker failed for {symbol}: {e}")

        # Attempt 2: OKX ticker
        try:
            inst_id = symbol.replace("USDT", "-USDT")
            resp = requests.get(
                "https://www.okx.com/api/v5/market/ticker",
                params={"instId": inst_id},
                timeout=15,
            )
            resp.raise_for_status()
            d = resp.json().get("data", [{}])[0]
            return {
                "price": float(d["last"]),
                "high": float(d["high24h"]),
                "low": float(d["low24h"]),
            }
        except Exception as e:
            print(f"  [WARN] OKX ticker failed for {symbol}: {e}")

        # Attempt 3: Extract from OHLCV (most reliable fallback)
        try:
            df = _fetch_klines(symbol, "1h", limit=5)
            if df is not None and len(df) > 0:
                return {
                    "price": float(df["Close"].iloc[-1]),
                    "high": float(df["High"].iloc[-1]),
                    "low": float(df["Low"].iloc[-1]),
                }
        except Exception as e:
            print(f"  [WARN] OHLCV fallback failed for {symbol}: {e}")

    print(f"  [ERROR] ALL price sources failed for {symbol} after {retries} attempts — picks will be stale")
    return None


# ---------------------------------------------------------------------------
# Indicators (inline, no external dependency)
# ---------------------------------------------------------------------------

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period).mean()


# ---------------------------------------------------------------------------
# S/R Detection  (Williams Fractal + Volume Profile)
# ---------------------------------------------------------------------------

@dataclass
class SRLevel:
    price: float
    strength: float
    touches: int
    level_type: str      # "support" | "resistance"
    source: str          # "fractal" | "volume_profile" | "round_number"


def _detect_sr_levels(df: pd.DataFrame, max_levels: int = 10) -> list[SRLevel]:
    """Detect support/resistance via Williams fractal + volume profile + round numbers."""
    current_price = float(df["Close"].iloc[-1])
    levels: list[SRLevel] = []

    # --- Williams fractal pivots ---
    high_vals = df["High"].values
    low_vals = df["Low"].values
    n = len(df)
    half = 2  # fractal window half

    pivots: list[tuple[int, float, str]] = []
    for i in range(half, n - half):
        is_high = all(high_vals[i] > high_vals[j] for j in range(i - half, i + half + 1) if j != i)
        is_low = all(low_vals[i] < low_vals[j] for j in range(i - half, i + half + 1) if j != i)
        if is_high:
            pivots.append((i, float(high_vals[i]), "high"))
        if is_low:
            pivots.append((i, float(low_vals[i]), "low"))

    # Cluster pivots within 0.3% tolerance
    tolerance = 0.003
    pivots.sort(key=lambda x: x[1])
    used: set[int] = set()
    for idx, (bar_i, price, ptype) in enumerate(pivots):
        if idx in used:
            continue
        cluster = [(bar_i, price)]
        used.add(idx)
        for jdx, (bar_j, price2, _) in enumerate(pivots):
            if jdx in used:
                continue
            if abs(price2 - price) / max(price, 1e-10) <= tolerance:
                cluster.append((bar_j, price2))
                used.add(jdx)
        if len(cluster) >= 2:
            avg_price = np.mean([p for _, p in cluster])
            max_bar = max(c[0] for c in cluster)
            recency = max_bar / n if n > 0 else 0.5
            strength = len(cluster) * (1.0 + 0.5 * recency)
            ltype = "support" if avg_price < current_price else "resistance"
            levels.append(SRLevel(
                price=round(avg_price, 2),
                strength=strength,
                touches=len(cluster),
                level_type=ltype,
                source="fractal",
            ))

    # --- Volume profile (POC, VAH, VAL) ---
    lookback = min(100, len(df))
    data_slice = df.tail(lookback)
    if len(data_slice) >= 20:
        price_min = float(data_slice["Low"].min())
        price_max = float(data_slice["High"].max())
        if price_max > price_min:
            n_bins = 50
            bin_edges = np.linspace(price_min, price_max, n_bins + 1)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            profile = np.zeros(n_bins)
            for _, row in data_slice.iterrows():
                bar_low, bar_high, bar_vol = float(row["Low"]), float(row["High"]), float(row["Volume"])
                if bar_high <= bar_low or bar_vol <= 0:
                    continue
                for k in range(n_bins):
                    overlap = max(0, min(bar_high, bin_edges[k + 1]) - max(bar_low, bin_edges[k]))
                    profile[k] += bar_vol * (overlap / (bar_high - bar_low))
            if profile.sum() > 0:
                poc_idx = int(np.argmax(profile))
                poc_price = float(bin_centers[poc_idx])
                # Value area (70%)
                total_vol = profile.sum()
                target = 0.70 * total_vol
                accumulated = profile[poc_idx]
                lo_idx = hi_idx = poc_idx
                while accumulated < target and (lo_idx > 0 or hi_idx < n_bins - 1):
                    expand_lo = profile[lo_idx - 1] if lo_idx > 0 else 0
                    expand_hi = profile[hi_idx + 1] if hi_idx < n_bins - 1 else 0
                    if expand_lo >= expand_hi and lo_idx > 0:
                        lo_idx -= 1
                        accumulated += profile[lo_idx]
                    elif hi_idx < n_bins - 1:
                        hi_idx += 1
                        accumulated += profile[hi_idx]
                    else:
                        break
                val_price = float(bin_centers[lo_idx])
                vah_price = float(bin_centers[hi_idx])
                for vp_price in [poc_price, val_price, vah_price]:
                    ltype = "support" if vp_price < current_price else "resistance"
                    levels.append(SRLevel(
                        price=round(vp_price, 2), strength=4.0, touches=0,
                        level_type=ltype, source="volume_profile",
                    ))

    # --- Round numbers ---
    magnitude = 10 ** int(np.log10(max(current_price, 1)))
    step = magnitude / 10 if current_price < magnitude * 5 else magnitude / 5
    if step < 1:
        step = 1
    base = round(current_price / step) * step
    for offset in [-3, -2, -1, 0, 1, 2, 3]:
        rn = base + offset * step
        if rn > 0 and abs(rn - current_price) / current_price < 0.10:
            ltype = "support" if rn < current_price else "resistance"
            levels.append(SRLevel(
                price=round(rn, 2), strength=1.5, touches=0,
                level_type=ltype, source="round_number",
            ))

    # Merge nearby, sort by strength
    levels.sort(key=lambda x: x.price)
    merged: list[SRLevel] = []
    for lv in levels:
        if merged and abs(lv.price - merged[-1].price) / max(merged[-1].price, 1e-10) <= tolerance:
            prev = merged[-1]
            merged[-1] = SRLevel(
                price=round((prev.price + lv.price) / 2, 2),
                strength=prev.strength + lv.strength,
                touches=prev.touches + lv.touches,
                level_type=prev.level_type,
                source=f"{prev.source}+{lv.source}",
            )
        else:
            merged.append(lv)
    merged.sort(key=lambda x: x.strength, reverse=True)
    return merged[:max_levels]


def _nearest_sr_distance(levels: list[SRLevel], price: float, atr_val: float) -> float:
    """Distance to nearest S/R level normalized by ATR. Lower = closer."""
    if not levels or atr_val <= 0:
        return 5.0  # far away default
    distances = [abs(lv.price - price) / atr_val for lv in levels]
    return min(distances)


# ---------------------------------------------------------------------------
# Pre-Spike Pattern Extraction (8 features)
# ---------------------------------------------------------------------------

@dataclass
class PreSpikePattern:
    """8-feature snapshot of conditions before a spike."""
    volatility_compression: float    # ATR at bar / ATR 20 bars before
    volume_buildup: float            # avg vol last 5 / avg vol bars 20-10
    price_range_squeeze: float       # (HH - LL of last 10) / ATR
    trend_momentum: float            # (EMA9 - EMA21) / price
    rsi_position: float              # RSI(14)
    sr_proximity: float              # distance to nearest S/R / ATR
    funding_rate: float              # current funding rate
    candle_pattern: float            # avg(body/range) of last 3 candles


def _extract_pattern(
    df: pd.DataFrame,
    bar_index: int,
    sr_levels: list[SRLevel],
    funding_rate: float = 0.0,
) -> Optional[PreSpikePattern]:
    """Extract 8-feature pattern from the 20 bars before bar_index."""
    if bar_index < PRE_SPIKE_LOOKBACK + 14:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    atr_series = _atr(high, low, close, 14)
    atr_at_bar = float(atr_series.iloc[bar_index]) if not pd.isna(atr_series.iloc[bar_index]) else 0
    atr_20_before = float(atr_series.iloc[bar_index - PRE_SPIKE_LOOKBACK]) if not pd.isna(atr_series.iloc[bar_index - PRE_SPIKE_LOOKBACK]) else 0

    # 1. Volatility compression
    vol_compression = atr_at_bar / atr_20_before if atr_20_before > 0 else 1.0

    # 2. Volume buildup: avg vol last 5 bars / avg vol bars 20-10 before
    vol_last_5 = float(volume.iloc[bar_index - 5:bar_index].mean())
    vol_20_10 = float(volume.iloc[bar_index - PRE_SPIKE_LOOKBACK:bar_index - 10].mean())
    volume_buildup = vol_last_5 / vol_20_10 if vol_20_10 > 0 else 1.0

    # 3. Price range squeeze: (HH - LL of last 10) / ATR
    hh = float(high.iloc[bar_index - 10:bar_index].max())
    ll = float(low.iloc[bar_index - 10:bar_index].min())
    range_squeeze = (hh - ll) / atr_at_bar if atr_at_bar > 0 else 3.0

    # 4. Trend momentum: (EMA9 - EMA21) / price
    ema9 = _ema(close, 9)
    ema21 = _ema(close, 21)
    price_at_bar = float(close.iloc[bar_index])
    trend_mom = (float(ema9.iloc[bar_index]) - float(ema21.iloc[bar_index])) / price_at_bar if price_at_bar > 0 else 0

    # 5. RSI position
    rsi_series = _rsi(close, 14)
    rsi_val = float(rsi_series.iloc[bar_index]) if not pd.isna(rsi_series.iloc[bar_index]) else 50.0

    # 6. S/R proximity
    sr_prox = _nearest_sr_distance(sr_levels, price_at_bar, atr_at_bar)

    # 7. Funding rate (passed in)
    fr = funding_rate

    # 8. Candle pattern: avg(|body| / range) of last 3 candles
    bodies = []
    for k in range(bar_index - 3, bar_index):
        if k < 0:
            continue
        body = abs(float(close.iloc[k]) - float(df["Open"].iloc[k]))
        rng = float(high.iloc[k]) - float(low.iloc[k])
        bodies.append(body / rng if rng > 0 else 0.5)
    candle_pat = np.mean(bodies) if bodies else 0.5

    return PreSpikePattern(
        volatility_compression=round(vol_compression, 4),
        volume_buildup=round(volume_buildup, 4),
        price_range_squeeze=round(range_squeeze, 4),
        trend_momentum=round(trend_mom, 6),
        rsi_position=round(rsi_val, 2),
        sr_proximity=round(sr_prox, 4),
        funding_rate=round(fr, 6),
        candle_pattern=round(candle_pat, 4),
    )


# ---------------------------------------------------------------------------
# Spike Detection (Historical)
# ---------------------------------------------------------------------------

@dataclass
class DetectedSpike:
    bar_index: int
    timestamp: str
    direction: str          # "BULL" | "BEAR"
    magnitude_pct: float
    pattern: Optional[PreSpikePattern]


def find_historical_spikes(
    df_4h: pd.DataFrame,
    sr_levels: list[SRLevel],
    funding_rate: float = 0.0,
    threshold_pct: float = SPIKE_THRESHOLD_PCT,
) -> list[DetectedSpike]:
    """Find bars where price moved >threshold% in one 4h candle."""
    spikes: list[DetectedSpike] = []
    opens = df_4h["Open"].values
    closes = df_4h["Close"].values
    n = len(df_4h)

    for i in range(PRE_SPIKE_LOOKBACK + 14, n):
        move_pct = (closes[i] - opens[i]) / opens[i] * 100
        if abs(move_pct) >= threshold_pct:
            pattern = _extract_pattern(df_4h, i, sr_levels, funding_rate)
            ts = str(df_4h.index[i]) if hasattr(df_4h.index[i], 'isoformat') else str(df_4h.index[i])
            spikes.append(DetectedSpike(
                bar_index=i,
                timestamp=ts,
                direction="BULL" if move_pct > 0 else "BEAR",
                magnitude_pct=round(move_pct, 2),
                pattern=pattern,
            ))
    return spikes


# ---------------------------------------------------------------------------
# Spike Archetypes
# ---------------------------------------------------------------------------

@dataclass
class Archetype:
    name: str
    description: str
    # Ideal ranges for each feature: (ideal_value, tolerance)
    ideal_volatility_compression: tuple[float, float]
    ideal_volume_buildup: tuple[float, float]
    ideal_price_range_squeeze: tuple[float, float]
    ideal_trend_momentum: tuple[float, float]   # absolute value
    ideal_rsi_position: tuple[float, float]
    ideal_sr_proximity: tuple[float, float]
    ideal_funding_rate: tuple[float, float]
    ideal_candle_pattern: tuple[float, float]
    avg_magnitude: float   # typical spike size in %
    direction_rule: str    # "trend" | "reversal" | "breakout"


# The four spike archetypes
ARCHETYPES = [
    Archetype(
        name="Squeeze Breakout",
        description="Price compresses in tight range then explodes. Direction from trend momentum.",
        ideal_volatility_compression=(0.65, 0.20),   # low ATR ratio = compressed
        ideal_volume_buildup=(1.4, 0.40),             # rising volume into squeeze
        ideal_price_range_squeeze=(1.2, 0.50),        # tight range
        ideal_trend_momentum=(0.01, 0.015),           # mild trend bias
        ideal_rsi_position=(50.0, 15.0),              # middle RSI, not exhausted
        ideal_sr_proximity=(0.8, 0.50),               # somewhat close to S/R
        ideal_funding_rate=(0.0, 0.03),               # neutral funding
        ideal_candle_pattern=(0.3, 0.20),             # small bodies (dojis/indecision)
        avg_magnitude=4.5,
        direction_rule="trend",
    ),
    Archetype(
        name="Momentum Continuation",
        description="Strong trend accelerates further with rising volume.",
        ideal_volatility_compression=(1.0, 0.30),     # normal ATR
        ideal_volume_buildup=(1.6, 0.50),             # strongly rising volume
        ideal_price_range_squeeze=(2.5, 1.00),        # expanding range
        ideal_trend_momentum=(0.025, 0.015),          # strong momentum
        ideal_rsi_position=(55.0, 12.0),              # 43-67 range, not overbought
        ideal_sr_proximity=(1.5, 1.00),               # further from S/R
        ideal_funding_rate=(0.01, 0.03),              # mild positive funding (bullish)
        ideal_candle_pattern=(0.6, 0.20),             # strong bodies
        avg_magnitude=5.0,
        direction_rule="trend",
    ),
    Archetype(
        name="Capitulation Reversal",
        description="Exhaustion move reverses violently. Panic volume + extreme RSI + extreme funding.",
        ideal_volatility_compression=(1.3, 0.40),     # elevated volatility
        ideal_volume_buildup=(2.2, 0.80),             # panic volume (very high)
        ideal_price_range_squeeze=(3.0, 1.50),        # wide range before
        ideal_trend_momentum=(0.03, 0.020),           # strong prior move
        ideal_rsi_position=(22.0, 10.0),              # extreme RSI (<32 or mapped)
        ideal_sr_proximity=(0.4, 0.30),               # very close to S/R (bouncing off)
        ideal_funding_rate=(0.06, 0.04),              # extreme funding
        ideal_candle_pattern=(0.7, 0.20),             # big bodies (panic candles)
        avg_magnitude=6.0,
        direction_rule="reversal",
    ),
    Archetype(
        name="S/R Cascade",
        description="Price breaks through major S/R, triggering stop-hunts and liquidation cascades.",
        ideal_volatility_compression=(0.80, 0.25),    # slightly compressed
        ideal_volume_buildup=(1.6, 0.50),             # building volume
        ideal_price_range_squeeze=(1.5, 0.60),        # moderate range
        ideal_trend_momentum=(0.015, 0.015),          # moderate momentum
        ideal_rsi_position=(50.0, 18.0),              # neutral RSI
        ideal_sr_proximity=(0.3, 0.20),               # very close to major S/R
        ideal_funding_rate=(0.02, 0.03),              # moderate funding
        ideal_candle_pattern=(0.5, 0.20),             # mixed candle types
        avg_magnitude=5.5,
        direction_rule="breakout",
    ),
]


# ---------------------------------------------------------------------------
# Similarity Scoring
# ---------------------------------------------------------------------------

def _gaussian_similarity(value: float, ideal: float, tolerance: float) -> float:
    """Gaussian similarity: 1.0 at ideal, falls off with distance."""
    if tolerance <= 0:
        return 1.0 if value == ideal else 0.0
    return math.exp(-0.5 * ((value - ideal) / tolerance) ** 2)


def compute_similarity(pattern: PreSpikePattern, archetype: Archetype) -> float:
    """Score current conditions against an archetype (0-1). Averages 8 gaussian similarities."""
    scores = [
        _gaussian_similarity(pattern.volatility_compression, *archetype.ideal_volatility_compression),
        _gaussian_similarity(pattern.volume_buildup, *archetype.ideal_volume_buildup),
        _gaussian_similarity(pattern.price_range_squeeze, *archetype.ideal_price_range_squeeze),
        _gaussian_similarity(abs(pattern.trend_momentum), *archetype.ideal_trend_momentum),
        # For RSI: capitulation archetype uses extreme RSI, map appropriately
        _gaussian_similarity(pattern.rsi_position, *archetype.ideal_rsi_position),
        _gaussian_similarity(pattern.sr_proximity, *archetype.ideal_sr_proximity),
        _gaussian_similarity(abs(pattern.funding_rate * 100), *archetype.ideal_funding_rate),  # funding in % terms
        _gaussian_similarity(pattern.candle_pattern, *archetype.ideal_candle_pattern),
    ]
    return round(float(np.mean(scores)), 4)


def determine_direction(pattern: PreSpikePattern, archetype: Archetype) -> str:
    """Determine expected spike direction given current pattern and archetype."""
    if archetype.direction_rule == "reversal":
        # Capitulation reversal: if RSI < 30 then bounce up, if > 70 bounce down
        if pattern.rsi_position < 35:
            return "BUY"
        elif pattern.rsi_position > 65:
            return "SELL"
        # Use funding: extreme positive -> reverse down, extreme negative -> reverse up
        if pattern.funding_rate > 0.0003:
            return "SELL"
        elif pattern.funding_rate < -0.0003:
            return "BUY"
        return "BUY"  # default: bounce up from exhaustion

    elif archetype.direction_rule == "trend":
        # Follow the trend momentum direction
        return "BUY" if pattern.trend_momentum > 0 else "SELL"

    elif archetype.direction_rule == "breakout":
        # Breakout direction from trend + S/R context
        return "BUY" if pattern.trend_momentum > 0 else "SELL"

    return "BUY"


def match_current_to_archetypes(current_pattern: PreSpikePattern) -> list[dict]:
    """Score current conditions against each archetype. Return sorted matches above threshold."""
    matches = []
    for archetype in ARCHETYPES:
        score = compute_similarity(current_pattern, archetype)
        if score > ARCHETYPE_MATCH_THRESHOLD:
            matches.append({
                "archetype": archetype.name,
                "score": score,
                "expected_direction": determine_direction(current_pattern, archetype),
                "expected_magnitude": archetype.avg_magnitude,
                "direction_rule": archetype.direction_rule,
            })
    return sorted(matches, key=lambda x: x["score"], reverse=True)


# ---------------------------------------------------------------------------
# Signal Validation
# ---------------------------------------------------------------------------

def _validate_signal(
    matches: list[dict],
    current_pattern: PreSpikePattern,
    ema9: float,
    ema50: float,
    volume_ratio: float,
) -> Optional[dict]:
    """
    Only generate a signal when:
    1. At least one archetype matches with score > 0.65
    2. Expected direction aligns with current trend (EMA9 vs EMA50)
    3. Volume is above average (> 1.2x)
    4. No conflicting archetypes (bull + bear matching simultaneously)
    """
    if not matches:
        return None

    top = matches[0]
    if top["score"] < SIGNAL_MATCH_THRESHOLD:
        return None

    # Check volume
    if volume_ratio < MIN_VOLUME_RATIO:
        return None

    # Check trend alignment
    current_trend = "BUY" if ema9 > ema50 else "SELL"
    expected_dir = top["expected_direction"]

    # For capitulation reversal, we EXPECT counter-trend, so skip alignment check
    if top["direction_rule"] != "reversal":
        if expected_dir != current_trend:
            return None

    # Check for conflicting archetypes
    if len(matches) >= 2:
        directions = set(m["expected_direction"] for m in matches if m["score"] > SIGNAL_MATCH_THRESHOLD)
        if len(directions) > 1:
            return None  # conflicting signals

    return top


# ---------------------------------------------------------------------------
# TP/SL Calculation
# ---------------------------------------------------------------------------

def _compute_tp_sl(
    entry: float,
    direction: str,
    atr_val: float,
    expected_magnitude: float,
    sr_levels: list[SRLevel],
    tier_config: Optional[dict] = None,
) -> tuple[float, float, str]:
    """
    TP: based on archetype's average spike magnitude.
    SL: 2.0x ATR (v2: widened from 1.5x to reduce premature stop-outs).
    Min 2.0:1 R:R.
    """
    cfg = tier_config or TIER1_CONFIG
    tp_scale = cfg.get("tp_magnitude_scale", 0.90)
    sl_mult = cfg.get("sl_atr_multiplier", 2.0)

    # TP from expected magnitude
    tp_pct = expected_magnitude * tp_scale / 100.0

    # SL at ATR multiplier (v2: default 2.0x, memes 2.5x)
    sl_dist = sl_mult * atr_val

    if direction == "BUY":
        tp = entry * (1 + tp_pct)
        sl = entry - sl_dist

        # Check S/R: if a strong support is closer than 1.5 ATR, use it
        supports = [lv for lv in sr_levels if lv.level_type == "support" and lv.price < entry]
        if supports:
            best_support = max(supports, key=lambda x: x.strength)
            sr_sl = best_support.price * 0.998
            if sr_sl > sl and (entry - sr_sl) < 2.0 * atr_val:
                sl = sr_sl

        # Enforce min R:R
        risk = entry - sl
        reward = tp - entry
        if risk > 0 and reward / risk < MIN_RR:
            tp = entry + MIN_RR * risk
        method = "spike_archetype"
    else:
        tp = entry * (1 - tp_pct)
        sl = entry + sl_dist

        resistances = [lv for lv in sr_levels if lv.level_type == "resistance" and lv.price > entry]
        if resistances:
            best_res = max(resistances, key=lambda x: x.strength)
            sr_sl = best_res.price * 1.002
            if sr_sl < sl and (sr_sl - entry) < 2.0 * atr_val:
                sl = sr_sl

        risk = sl - entry
        reward = entry - tp
        if risk > 0 and reward / risk < MIN_RR:
            tp = entry - MIN_RR * risk
        method = "spike_archetype"

    return round(tp, 2), round(sl, 2), method


# ---------------------------------------------------------------------------
# Position / Pick Management
# ---------------------------------------------------------------------------

def _load_json(path: str) -> list:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def _save_json(data, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _load_active() -> list[dict]:
    return _load_json(ACTIVE_PICKS_PATH)


def _load_closed() -> list[dict]:
    return _load_json(CLOSED_PICKS_PATH)


def _save_active(picks: list[dict]):
    try:
        from alpha_engine.feed_hygiene import sanitize_active_picks
    except ImportError:
        sanitize_active_picks = lambda p, label="": p
    picks = sanitize_active_picks(picks, "breakout_arena_c")
    _save_json(picks, ACTIVE_PICKS_PATH)


def _save_closed_append(newly_closed: list[dict]):
    existing = _load_closed()
    existing.extend(newly_closed)
    _save_json(existing, CLOSED_PICKS_PATH)


def _record_pnl(pick: dict):
    """Calculate and record PnL on a closed pick."""
    entry = pick["entry_price"]
    exit_price = pick["exit_price"]
    signal = pick.get("signal_type", "BUY")
    if signal == "BUY":
        gross_pnl = (exit_price - entry) / entry * 100
    else:
        gross_pnl = (entry - exit_price) / entry * 100
    pick["gross_pnl_pct"] = round(gross_pnl, 4)
    pick["net_pnl_pct"] = round(gross_pnl - ROUND_TRIP_COST_PCT, 4)
    pick["cost_pct"] = ROUND_TRIP_COST_PCT


def validate_active_picks(active: list[dict]) -> tuple[list[dict], list[dict]]:
    """Check active picks against live prices. Returns (still_active, newly_closed).
    v2: per-symbol price fetch + per-tier trailing parameters + mid-TP trailing lock."""
    if not active:
        return [], []

    now = datetime.now(timezone.utc)
    still_active = []
    newly_closed = []

    # Cache prices per symbol to avoid redundant API calls
    price_cache: dict[str, Optional[dict]] = {}

    for pick in active:
        symbol = pick.get("symbol", "BTCUSDT")
        entry = pick["entry_price"]
        tp = pick["take_profit"]
        sl = pick["stop_loss"]
        signal = pick.get("signal_type", "BUY")
        opened_at = datetime.fromisoformat(pick["timestamp"])

        # Fetch price (cached per symbol)
        if symbol not in price_cache:
            price_cache[symbol] = _fetch_live_price(symbol)
        price_data = price_cache[symbol]
        if not price_data:
            print(f"  [ERROR] Could not fetch live price for {symbol} — keeping pick active")
            still_active.append(pick)
            continue

        current = price_data["price"]

        # Per-tier config
        cfg = _get_tier_config(symbol)
        trail_activate = cfg.get("trail_activate_pct", TRAIL_ACTIVATE_PCT)
        trail_from_hwm = cfg.get("trail_from_hwm_pct", TRAIL_FROM_HWM_PCT)
        max_hold = cfg.get("max_hold_hours", MAX_HOLD_HOURS)

        # High-water mark
        if signal == "BUY":
            hwm = max(pick.get("hwm", entry), current)
        else:
            hwm = min(pick.get("hwm", entry), current)
        pick["hwm"] = hwm

        # Expiry
        hours_held = (now - opened_at).total_seconds() / 3600
        if hours_held > max_hold:
            pick["exit_price"] = current
            pick["exit_reason"] = "expiry"
            pick["closed_at"] = now.isoformat()
            _record_pnl(pick)
            newly_closed.append(pick)
            continue

        # --- v2: Mid-TP trailing stop ---
        # When price reaches 50% of TP distance, move SL to breakeven + 0.5%
        if signal == "BUY":
            tp_dist = tp - entry
            progress = (current - entry) / tp_dist if tp_dist > 0 else 0
            if progress >= 0.50 and not pick.get("mid_tp_locked"):
                breakeven_sl = entry * 1.005  # lock in 0.5% profit
                if breakeven_sl > sl:
                    sl = breakeven_sl
                    pick["stop_loss"] = round(sl, 2)
                    pick["mid_tp_locked"] = True
        else:
            tp_dist = entry - tp
            progress = (entry - current) / tp_dist if tp_dist > 0 else 0
            if progress >= 0.50 and not pick.get("mid_tp_locked"):
                breakeven_sl = entry * 0.995
                if breakeven_sl < sl:
                    sl = breakeven_sl
                    pick["stop_loss"] = round(sl, 2)
                    pick["mid_tp_locked"] = True

        # Trailing stop (activates after trail_activate_pct gain from entry)
        if signal == "BUY":
            unrealized_pct = (hwm - entry) / entry * 100
            if unrealized_pct > trail_activate:
                trail_level = hwm * (1 - trail_from_hwm / 100)
                if trail_level > sl:
                    sl = trail_level
                    pick["stop_loss"] = round(sl, 2)
                    pick["trailing_active"] = True
        else:
            unrealized_pct = (entry - hwm) / entry * 100
            if unrealized_pct > trail_activate:
                trail_level = hwm * (1 + trail_from_hwm / 100)
                if trail_level < sl:
                    sl = trail_level
                    pick["stop_loss"] = round(sl, 2)
                    pick["trailing_active"] = True

        # SL check (0.3% buffer)
        SL_BUFFER = 0.003
        if signal == "BUY":
            sl_hit = current <= sl * (1 + SL_BUFFER)
        else:
            sl_hit = current >= sl * (1 - SL_BUFFER)
        if sl_hit:
            pick["exit_price"] = current
            pick["exit_reason"] = "trailing_stop" if pick.get("trailing_active") else "stop_loss"
            pick["closed_at"] = now.isoformat()
            _record_pnl(pick)
            newly_closed.append(pick)
            continue

        # TP check
        if signal == "BUY":
            tp_hit = current >= tp * (1 - SL_BUFFER)
        else:
            tp_hit = current <= tp * (1 + SL_BUFFER)
        if tp_hit:
            pick["exit_price"] = current
            pick["exit_reason"] = "take_profit"
            pick["closed_at"] = now.isoformat()
            _record_pnl(pick)
            newly_closed.append(pick)
            continue

        # Update unrealized
        pick["current_price"] = current
        if signal == "BUY":
            pick["unrealized_pnl_pct"] = round((current - entry) / entry * 100, 4)
        else:
            pick["unrealized_pnl_pct"] = round((entry - current) / entry * 100, 4)
        still_active.append(pick)

    return still_active, newly_closed


# ---------------------------------------------------------------------------
# Equity / Stats
# ---------------------------------------------------------------------------

def _compute_stats(closed: list[dict]) -> dict:
    """Compute stats from closed picks."""
    if not closed:
        return {
            "trades": 0, "wins": 0, "losses": 0, "win_rate": 0,
            "sharpe": 0, "max_dd": 0, "total_pnl_pct": 0,
            "equity_curve": [STARTING_EQUITY],
        }
    pnls = [p.get("net_pnl_pct", 0) for p in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    equity = [STARTING_EQUITY]
    for pnl in pnls:
        equity.append(equity[-1] * (1 + pnl / 100))

    # Max drawdown
    peak = equity[0]
    max_dd = 0
    for e in equity:
        peak = max(peak, e)
        dd = (peak - e) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    # Sharpe (annualized, ~100 trades/year target)
    arr = np.array(pnls)
    if len(arr) >= 2 and np.std(arr) > 0:
        sharpe = float(np.mean(arr) / np.std(arr) * np.sqrt(100))
    else:
        sharpe = 0.0

    return {
        "trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(closed) if closed else 0,
        "avg_win_pct": round(float(np.mean(wins)), 4) if wins else 0,
        "avg_loss_pct": round(float(np.mean(losses)), 4) if losses else 0,
        "total_pnl_pct": round(sum(pnls), 4),
        "sharpe": round(sharpe, 2),
        "max_dd": round(max_dd, 4),
        "equity_curve": equity,
    }


def _calculate_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve or len(equity_curve) < 2:
        return 0.0
    peak = max(equity_curve)
    current = equity_curve[-1]
    if peak <= 0:
        return 0.0
    return (peak - current) / peak


# ---------------------------------------------------------------------------
# Spike History Persistence
# ---------------------------------------------------------------------------

def _load_spike_history() -> list[dict]:
    return _load_json(SPIKE_HISTORY_PATH)


def _save_spike_history(spikes: list[dict]):
    _save_json(spikes, SPIKE_HISTORY_PATH)


def _merge_spike_history(existing: list[dict], new_spikes: list[DetectedSpike]) -> list[dict]:
    """Merge new spikes into existing history, avoiding duplicates by timestamp."""
    existing_ts = {s.get("timestamp", "") for s in existing}
    for sp in new_spikes:
        if sp.timestamp not in existing_ts:
            entry = {
                "timestamp": sp.timestamp,
                "direction": sp.direction,
                "magnitude_pct": sp.magnitude_pct,
                "pattern": asdict(sp.pattern) if sp.pattern else None,
            }
            existing.append(entry)
    # Keep last 200 spikes
    return existing[-200:]


# ---------------------------------------------------------------------------
# Dashboard Output
# ---------------------------------------------------------------------------

def _write_dashboard(
    active: list[dict],
    closed: list[dict],
    stats: dict,
    current_pattern: Optional[PreSpikePattern],
    archetype_analysis: list[dict],
    spike_history_recent: list[dict],
):
    """Write dashboard.json for frontend consumption."""
    now = datetime.now(timezone.utc)
    dashboard = {
        "system": "Spike Reverse-Engineering",
        "version": VERSION,
        "updated": now.isoformat(),
        "updated_est": now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST"),
        "active_picks": active,
        "stats": {k: v for k, v in stats.items() if k != "equity_curve"},
        "equity_curve": stats.get("equity_curve", []),
        "total_closed": len(closed),
        "recent_closed": closed[-20:] if closed else [],
        "current_pattern": asdict(current_pattern) if current_pattern else None,
        "archetype_analysis": archetype_analysis,
        "spike_history": spike_history_recent[-5:],
    }
    _save_json(dashboard, DASHBOARD_PATH)


# ---------------------------------------------------------------------------
# Main Scan
# ---------------------------------------------------------------------------

def scan(dry_run: bool = False):
    """Main scan cycle for Approach C: Spike Reverse-Engineering."""
    now = datetime.now(timezone.utc)
    print(f"[Approach C - Spike Reverse-Engineering] Scan started at {now.isoformat()}")
    print(f"  Version: {VERSION}")
    print(f"  Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    print()

    # -----------------------------------------------------------------------
    # 1. Load existing state and validate active picks
    # -----------------------------------------------------------------------
    active = _load_active()
    closed = _load_closed()
    print(f"  Loaded: {len(active)} active, {len(closed)} closed")

    active, newly_closed = validate_active_picks(active)
    if newly_closed:
        print(f"  Closed {len(newly_closed)} picks: "
              f"{[p.get('exit_reason', '?') for p in newly_closed]}")
        closed.extend(newly_closed)

    stats = _compute_stats(closed)
    equity_curve = stats.get("equity_curve", [STARTING_EQUITY])
    dd = _calculate_drawdown(equity_curve)
    print(f"  Stats: WR={stats.get('win_rate', 0):.1%} | "
          f"Sharpe={stats.get('sharpe', 0):.2f} | DD={dd:.1%}")

    # Risk check
    can_trade = len(active) < MAX_CONCURRENT and dd < MAX_DRAWDOWN
    if not can_trade:
        reason = "max drawdown" if dd >= MAX_DRAWDOWN else "max concurrent positions"
        print(f"  Cannot open new trades: {reason}")

    # -----------------------------------------------------------------------
    # 2. Fetch market data
    # -----------------------------------------------------------------------
    print("\n  Fetching data...")
    df_4h = _fetch_klines("BTCUSDT", "4h", 500)
    df_1h = _fetch_klines("BTCUSDT", "1h", 500)
    fear_greed = _fetch_fear_greed()
    funding_rate = _fetch_funding_rate("BTCUSDT")

    if df_4h is None or len(df_4h) < 100:
        print("  ERROR: Could not fetch sufficient 4h data. Aborting.")
        if not dry_run:
            _save_active(active)
            if newly_closed:
                _save_closed_append(newly_closed)
        return

    print(f"  4h candles: {len(df_4h)} | 1h candles: {len(df_1h) if df_1h is not None else 0}")
    print(f"  Fear & Greed: {fear_greed} | Funding Rate: {funding_rate:.6f}")
    print(f"  BTC price: ${float(df_4h['Close'].iloc[-1]):,.0f}")

    # -----------------------------------------------------------------------
    # 3. Detect S/R levels
    # -----------------------------------------------------------------------
    sr_levels = _detect_sr_levels(df_4h)
    print(f"\n  S/R Levels: {len(sr_levels)}")
    for lv in sr_levels[:5]:
        print(f"    ${lv.price:,.0f} ({lv.level_type}, str={lv.strength:.1f}, src={lv.source})")

    # -----------------------------------------------------------------------
    # 4. Find historical spikes
    # -----------------------------------------------------------------------
    spikes = find_historical_spikes(df_4h, sr_levels, funding_rate)
    print(f"\n  Historical spikes detected: {len(spikes)} (threshold: {SPIKE_THRESHOLD_PCT}%)")
    for sp in spikes[-5:]:
        print(f"    {sp.timestamp}: {sp.direction} {sp.magnitude_pct:+.1f}%")

    # Persist spike history
    spike_history = _load_spike_history()
    spike_history = _merge_spike_history(spike_history, spikes)
    if not dry_run:
        _save_spike_history(spike_history)
    print(f"  Spike history total: {len(spike_history)}")

    # -----------------------------------------------------------------------
    # 5. Extract current pattern
    # -----------------------------------------------------------------------
    current_bar = len(df_4h) - 1
    current_pattern = _extract_pattern(df_4h, current_bar, sr_levels, funding_rate)
    if current_pattern is None:
        print("\n  ERROR: Could not extract current pattern. Not enough data.")
        if not dry_run:
            _save_active(active)
            if newly_closed:
                _save_closed_append(newly_closed)
        return

    print(f"\n  Current Pattern:")
    print(f"    volatility_compression: {current_pattern.volatility_compression:.4f}")
    print(f"    volume_buildup:         {current_pattern.volume_buildup:.4f}")
    print(f"    price_range_squeeze:    {current_pattern.price_range_squeeze:.4f}")
    print(f"    trend_momentum:         {current_pattern.trend_momentum:.6f}")
    print(f"    rsi_position:           {current_pattern.rsi_position:.2f}")
    print(f"    sr_proximity:           {current_pattern.sr_proximity:.4f}")
    print(f"    funding_rate:           {current_pattern.funding_rate:.6f}")
    print(f"    candle_pattern:         {current_pattern.candle_pattern:.4f}")

    # -----------------------------------------------------------------------
    # 6. Match against archetypes
    # -----------------------------------------------------------------------
    archetype_analysis = []
    for arch in ARCHETYPES:
        score = compute_similarity(current_pattern, arch)
        direction = determine_direction(current_pattern, arch)
        archetype_analysis.append({
            "archetype": arch.name,
            "score": score,
            "expected_direction": direction,
            "expected_magnitude": arch.avg_magnitude,
            "threshold": SIGNAL_MATCH_THRESHOLD,
        })

    print(f"\n  Archetype Matching:")
    for aa in archetype_analysis:
        marker = " <<< MATCH" if aa["score"] >= SIGNAL_MATCH_THRESHOLD else ""
        print(f"    {aa['archetype']:25s}: {aa['score']:.4f} "
              f"({aa['expected_direction']}, ~{aa['expected_magnitude']:.1f}%){marker}")

    matches = match_current_to_archetypes(current_pattern)

    # -----------------------------------------------------------------------
    # 7. Signal generation
    # -----------------------------------------------------------------------
    signal = None
    if can_trade and matches:
        close_vals = df_4h["Close"]
        ema9_val = float(_ema(close_vals, 9).iloc[-1])
        ema50_val = float(_ema(close_vals, 50).iloc[-1])
        vol_recent = float(df_4h["Volume"].iloc[-5:].mean())
        vol_avg = float(df_4h["Volume"].iloc[-50:].mean())
        volume_ratio = vol_recent / vol_avg if vol_avg > 0 else 0

        signal = _validate_signal(matches, current_pattern, ema9_val, ema50_val, volume_ratio)

    # F&G guard: block SELL during extreme fear (contrarian bounce likely), block BUY during extreme greed
    if signal and fear_greed is not None:
        direction = signal.get("expected_direction", "")
        if direction == "SELL" and fear_greed < 20:
            print(f"\n  [F&G GUARD] Blocking SELL signal: F&G={fear_greed} < 20 (extreme fear = bounce likely)")
            signal = None
        elif direction == "BUY" and fear_greed > 85:
            print(f"\n  [F&G GUARD] Blocking BUY signal: F&G={fear_greed} > 85 (extreme greed = correction likely)")
            signal = None

    if signal:
        entry_price = float(df_4h["Close"].iloc[-1])
        atr_val = float(_atr(df_4h["High"], df_4h["Low"], df_4h["Close"], 14).iloc[-1])

        tp, sl, method = _compute_tp_sl(
            entry_price, signal["expected_direction"],
            atr_val, signal["expected_magnitude"], sr_levels,
        )

        # Calculate R:R
        if signal["expected_direction"] == "BUY":
            risk = entry_price - sl
            reward = tp - entry_price
        else:
            risk = sl - entry_price
            reward = entry_price - tp
        rr = reward / risk if risk > 0 else 0

        new_pick = {
            "symbol": "BTCUSDT",
            "signal_type": signal["expected_direction"],
            "entry_price": entry_price,
            "take_profit": tp,
            "stop_loss": sl,
            "risk_reward": round(rr, 2),
            "confidence": round(signal["score"], 4),
            "archetype_match": signal["archetype"],
            "archetype_score": signal["score"],
            "expected_magnitude_pct": signal["expected_magnitude"],
            "tp_sl_method": method,
            "timestamp": now.isoformat(),
            "timestamp_est": now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST"),
            "system": SYSTEM_NAME,
            "version": VERSION,
            "fear_greed": fear_greed,
            "funding_rate": funding_rate,
            "current_price": entry_price,
            "unrealized_pnl_pct": 0.0,
            "pick_reason": (
                f"Spike archetype: {signal['archetype']} "
                f"(score={signal['score']:.2f}, mag={signal['expected_magnitude']:.1f}%) "
                f"| R:R {rr:.1f} | F&G={fear_greed} | Funding={funding_rate:.4f}"
            ),
        }

        print(f"\n  *** SIGNAL GENERATED ***")
        print(f"    Direction: {signal['expected_direction']}")
        print(f"    Archetype: {signal['archetype']} (score: {signal['score']:.4f})")
        print(f"    Entry: ${entry_price:,.0f}")
        print(f"    TP: ${tp:,.0f} | SL: ${sl:,.0f}")
        print(f"    R:R: {rr:.1f}")
        print(f"    Expected magnitude: {signal['expected_magnitude']:.1f}%")

        if not dry_run:
            # Cooldown: don't open same archetype+direction within 8 hours
            cooldown_hours = 8
            duplicate = False
            for existing in active:
                if (existing.get("archetype_match") == signal["archetype"]
                        and existing.get("signal_type") == signal["expected_direction"]):
                    duplicate = True
                    break
            if not duplicate:
                # Also check recently closed picks (within cooldown window)
                for closed_pick in closed[-5:]:
                    closed_at = closed_pick.get("closed_at", "")
                    if closed_at:
                        try:
                            closed_time = datetime.fromisoformat(closed_at)
                            if (now - closed_time).total_seconds() < cooldown_hours * 3600:
                                if (closed_pick.get("archetype_match") == signal["archetype"]
                                        and closed_pick.get("signal_type") == signal["expected_direction"]):
                                    duplicate = True
                                    break
                        except (ValueError, TypeError):
                            pass
            if duplicate:
                print(f"    --> COOLDOWN: Same archetype+direction already active or recently closed")
            else:
                active.append(new_pick)
                print(f"    --> Pick added to active positions")
        else:
            print(f"    --> DRY RUN: pick NOT saved")
    else:
        if not can_trade:
            print(f"\n  No signal generated (risk limit reached)")
        elif not matches:
            print(f"\n  No signal generated (no archetype matches above threshold)")
        else:
            print(f"\n  No signal generated (validation failed)")

    # -----------------------------------------------------------------------
    # 8. Save state and write dashboard
    # -----------------------------------------------------------------------
    if not dry_run:
        _save_active(active)
        if newly_closed:
            _save_closed_append(newly_closed)

    stats = _compute_stats(_load_closed() if not dry_run else closed)
    _write_dashboard(
        active, closed, stats,
        current_pattern, archetype_analysis,
        spike_history[-5:],
    )

    print(f"\n  Active: {len(active)} | Closed: {len(closed)} | "
          f"Spikes in history: {len(spike_history)}")
    print(f"  Dashboard written to: {DASHBOARD_PATH}")
    print(f"\n[Approach C] Scan complete.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Approach C: Spike Reverse-Engineering Scanner",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run analysis without saving picks or modifying state",
    )
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    scan(dry_run=args.dry_run)
