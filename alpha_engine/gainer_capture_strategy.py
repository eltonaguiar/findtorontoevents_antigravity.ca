#!/usr/bin/env python3
# ENTRY TIMING RULES (backed by data from Mar 24 investigation):
# - Sweet spot: coins up 3-8% with 2x+ volume acceleration
# - BLOCK: coins already up >15% (mean reversion zone)
# - REQUIRE: RSI(4h) < 65 (not overbought)
# - REQUIRE: price within 2% of session high (still making new highs)
"""
ALPHA ENGINE -- Gainer Capture Strategy
========================================
Three complementary strategies to catch coins at the START of their pump.

CRITICAL FIX (Mar 24 2026): Changed from chasing finished pumps (10-30% up)
to early entry (3-8% up with volume building). Previous version entered AFTER
coins already pumped 7-44%, resulting in 2W/8L from mean reversion.

Strategy 1: Early Momentum Rider
  - Find coins up 3-8% in 24h with accelerating hourly volume (>2x)
  - BLOCK coins already up >15% (mean reversion imminent)
  - Entry when RSI(4H) < 65 (not yet overbought)
  - REQUIRE: price within 2% of 24h high (still making new highs)
  - Trailing TP at 5% from high, SL at -8%

Strategy 2: Breakout Continuation
  - Find coins breaking 7-day highs within last 4 hours
  - Volume 3x+ the 7-day average
  - Entry on pullback to breakout level, TP +15% trailing, SL -5%

Strategy 3: Gainer Momentum Portfolio
  - Rank ALL Binance coins by (24h_gain * volume_ratio * momentum_score)
  - BLOCK coins already up >15% (mean reversion zone)
  - Take TOP 3, hold 24-48h max
  - Drop when hourly gain turns negative for 2 consecutive hours

A/B Testing:
  Three forward-test portfolios in data/gainer_portfolio_state.json
  Each starts at $10,000 virtual capital, max 3 positions per portfolio

Reverse Engineering:
  Reads missed_gainers_log.json and top_gainer_patterns.json to learn
  what big gainers looked like BEFORE they pumped.

Uses Binance API with full failover chain (api_failover.py).
Stdlib only -- no external dependencies beyond what scanner.py uses.
"""

from __future__ import annotations

import json
import math
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"
PORTFOLIO_STATE_FILE = DATA_DIR / "gainer_portfolio_state.json"
MISSED_GAINERS_LOG = DATA_DIR / "missed_gainers_log.json"
GAINER_PATTERNS_FILE = DATA_DIR / "top_gainer_patterns.json"
ACTIVE_PICKS_FILE = DATA_DIR / "active_picks.json"

# ---------------------------------------------------------------------------
# Binance API failover chain (NEVER single endpoint per project rules)
# Binance mirrors -> Bybit -> CoinGecko -> KuCoin -> CryptoCompare
# ---------------------------------------------------------------------------
BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

# In CI, prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    _preferred = ["https://data-api.binance.vision"]
    BINANCE_SPOT_BASES = _preferred + [u for u in BINANCE_SPOT_BASES if u not in _preferred]

BYBIT_BASE = "https://api.bybit.com"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
KUCOIN_BASE = "https://api.kucoin.com"

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT = 12
RSI_PERIOD = 14

# Strategy 1: Early Momentum Rider (FIXED Mar 24: early entry, not chasing)
EMR_MIN_GAIN_24H = 3.0        # Minimum 24h gain % (was 10% -- too late)
EMR_MAX_GAIN_24H = 8.0        # Maximum 24h gain % (was 30% -- way too late)
EMR_BLOCK_GAIN_24H = 15.0     # HARD BLOCK: coins already up >15% (mean reversion zone)
EMR_VOL_ACCEL_MIN = 2.0       # Current hour vol / previous hour vol
EMR_RSI_4H_MAX = 65.0         # RSI(4H) must be below this (was 75 -- too overbought)
EMR_NEAR_HIGH_PCT = 2.0       # Price must be within 2% of 24h high
EMR_MIN_VOLUME_USD = 2_000_000
EMR_TP_TRAIL_PCT = 5.0        # Trailing stop from high
EMR_SL_PCT = 8.0              # Wider stop for volatile movers

# Strategy 2: Breakout Continuation
BC_VOL_RATIO_MIN = 3.0        # Volume must be 3x+ 7-day average
BC_BREAKOUT_HOURS = 4          # Must have broken 7d high within last 4 hours
BC_MIN_VOLUME_USD = 3_000_000
BC_TP_TRAIL_PCT = 15.0        # Let these run -- can do 50%+
BC_SL_PCT = 5.0               # Below breakout level

# Strategy 3: Gainer Momentum Portfolio
GMP_TOP_N = 3                 # Top 3 by composite score
GMP_MAX_HOLD_HOURS = 48       # Max hold time
GMP_MIN_VOLUME_USD = 5_000_000
GMP_TP_PCT = 12.0             # Fixed TP (rebalanced anyway)
GMP_SL_PCT = 6.0              # Fixed SL

# Shared
EXCLUDE_SYMBOLS = {
    "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "DAIUSDT", "FDUSDUSDT",
    "USDPUSDT", "EURUSDT", "GBPUSDT", "AEURUSDT", "USTCUSDT",
    "WBTCUSDT", "WBETHUSDT",
    # Extended stablecoin blocklist (Mar 2026)
    "UUSDT", "USD1USDT", "USDEUSDT", "XUSDUSDT", "STABLEUSDT",
    "RLUSDUSDT", "BFUSDUSDT", "PYUSDUSDT", "GUSDUSDT", "FRAXUSDT",
}


def _is_stablecoin_by_pattern(symbol: str, price: float | None = None) -> bool:
    """Detect stablecoins by naming pattern or price heuristic."""
    if symbol in EXCLUDE_SYMBOLS:
        return True
    if symbol.endswith("USDUSDT") or symbol.endswith("USDTUSDT"):
        return True
    if price is not None and 0.99 <= price <= 1.01:
        return True
    return False
SKIP_TAGS = ("UP", "DOWN", "BEAR", "BULL")

# Portfolio A/B testing
STARTING_CAPITAL = 10_000.0
MAX_POSITIONS_PER_PORTFOLIO = 3

# ---------------------------------------------------------------------------
# SSL context
# ---------------------------------------------------------------------------
def _ssl_ctx():
    ctx = ssl.create_default_context()
    try:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    except Exception:
        ctx = ssl._create_unverified_context()
    return ctx


# ---------------------------------------------------------------------------
# HTTP helpers with full failover
# ---------------------------------------------------------------------------
def _fetch_json(url: str, timeout: int = REQUEST_TIMEOUT) -> Any:
    """Fetch JSON from URL with timeout."""
    url = urllib.parse.quote(url, safe=':/?&=#@[]!$\'()*+,;')
    ctx = _ssl_ctx()
    req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine-GainerCapture/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as e:
        return None


def _binance_get(path: str, params: str = "") -> Any:
    """Try Binance API with failover across mirror endpoints."""
    full_path = f"{path}?{params}" if params else path
    for base in BINANCE_SPOT_BASES:
        result = _fetch_json(f"{base}{full_path}")
        if result is not None:
            return result
    # Fallback: Bybit (for ticker data)
    return None


def fetch_all_tickers() -> List[Dict]:
    """Fetch ALL Binance 24h tickers with full failover chain.

    Failover: Binance mirrors -> Bybit -> CoinGecko
    """
    # 1. Binance mirrors
    tickers = _binance_get("/api/v3/ticker/24hr")
    if tickers:
        return _normalize_binance_tickers(tickers)

    # 2. Bybit fallback
    print("  [gainer_capture] Binance failed, trying Bybit...")
    data = _fetch_json(f"{BYBIT_BASE}/v5/market/tickers?category=spot")
    if data and data.get("retCode") == 0:
        result = []
        for t in data.get("result", {}).get("list", []):
            sym = t.get("symbol", "")
            if not sym.endswith("USDT"):
                continue
            try:
                pct = float(t.get("price24hPcnt", 0)) * 100
                vol = float(t.get("turnover24h", 0))
                price = float(t.get("lastPrice", 0))
                high24 = float(t.get("highPrice24h", 0))
                low24 = float(t.get("lowPrice24h", 0))
            except (ValueError, TypeError):
                continue
            result.append({
                "symbol": sym,
                "price_change_pct": round(pct, 2),
                "volume_usdt": vol,
                "last_price": price,
                "high_24h": high24,
                "low_24h": low24,
            })
        if result:
            return result

    # 3. CoinGecko fallback (limited to top 250 by market cap)
    print("  [gainer_capture] Bybit failed, trying CoinGecko...")
    cg_data = _fetch_json(
        f"{COINGECKO_BASE}/coins/markets?vs_currency=usd&order=volume_desc&per_page=250&page=1"
    )
    if cg_data:
        result = []
        for c in cg_data:
            sym = (c.get("symbol", "").upper() + "USDT")
            try:
                pct = float(c.get("price_change_percentage_24h", 0) or 0)
                vol = float(c.get("total_volume", 0) or 0)
                price = float(c.get("current_price", 0) or 0)
                high24 = float(c.get("high_24h", 0) or 0)
                low24 = float(c.get("low_24h", 0) or 0)
            except (ValueError, TypeError):
                continue
            result.append({
                "symbol": sym,
                "price_change_pct": round(pct, 2),
                "volume_usdt": vol,
                "last_price": price,
                "high_24h": high24,
                "low_24h": low24,
            })
        if result:
            return result

    # 4. KuCoin fallback
    print("  [gainer_capture] CoinGecko failed, trying KuCoin...")
    kucoin_data = _fetch_json(f"{KUCOIN_BASE}/api/v1/market/allTickers")
    if kucoin_data and kucoin_data.get("code") == "200000":
        result = []
        for t in kucoin_data.get("data", {}).get("ticker", []):
            sym_raw = t.get("symbol", "")
            if not sym_raw.endswith("-USDT"):
                continue
            sym = sym_raw.replace("-", "")
            try:
                pct = float(t.get("changeRate", 0)) * 100
                vol = float(t.get("volValue", 0))
                price = float(t.get("last", 0))
                high24 = float(t.get("high", 0))
                low24 = float(t.get("low", 0))
            except (ValueError, TypeError):
                continue
            result.append({
                "symbol": sym,
                "price_change_pct": round(pct, 2),
                "volume_usdt": vol,
                "last_price": price,
                "high_24h": high24,
                "low_24h": low24,
            })
        if result:
            return result

    print("  [gainer_capture][ERROR] All ticker sources failed")
    return []


def _normalize_binance_tickers(raw: List[Dict]) -> List[Dict]:
    """Normalize Binance ticker response to common format."""
    result = []
    for t in raw:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        if sym in EXCLUDE_SYMBOLS:
            continue
        if any(tag in sym for tag in SKIP_TAGS):
            continue
        try:
            pct = float(t.get("priceChangePercent", 0))
            vol = float(t.get("quoteVolume", 0))
            price = float(t.get("lastPrice", 0))
            high24 = float(t.get("highPrice", 0))
            low24 = float(t.get("lowPrice", 0))
        except (ValueError, TypeError):
            continue
        if price <= 0:
            continue
        result.append({
            "symbol": sym,
            "price_change_pct": round(pct, 2),
            "volume_usdt": vol,
            "last_price": price,
            "high_24h": high24,
            "low_24h": low24,
        })
    return result


# ---------------------------------------------------------------------------
# Kline fetcher with failover
# ---------------------------------------------------------------------------
def fetch_klines(symbol: str, interval: str = "1h", limit: int = 24) -> Optional[List[List]]:
    """Fetch klines from Binance with failover to Bybit.

    Returns list of [open_time, open, high, low, close, volume, ...] or None.
    """
    # Binance
    klines = _binance_get("/api/v3/klines", f"symbol={symbol}&interval={interval}&limit={limit}")
    if klines and len(klines) > 0:
        return klines

    # Bybit fallback
    interval_map = {"1h": "60", "4h": "240", "1d": "D", "15m": "15"}
    bybit_interval = interval_map.get(interval, "60")
    data = _fetch_json(
        f"{BYBIT_BASE}/v5/market/kline?category=spot&symbol={symbol}"
        f"&interval={bybit_interval}&limit={limit}"
    )
    if data and data.get("retCode") == 0:
        raw = data.get("result", {}).get("list", [])
        if raw:
            # Bybit returns [timestamp, open, high, low, close, volume, turnover] desc order
            raw.reverse()
            return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]),
                     float(k[4]), float(k[5])] for k in raw]

    return None


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------
def compute_rsi(closes: List[float], period: int = RSI_PERIOD) -> Optional[float]:
    """Compute RSI using Wilder smoothing."""
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_volume_acceleration(volumes: List[float]) -> float:
    """Ratio of latest volume to previous volume. >2.0 = accelerating."""
    if len(volumes) < 2:
        return 1.0
    prev = volumes[-2]
    if prev <= 0:
        return 1.0
    return volumes[-1] / prev


def compute_volume_ratio_vs_avg(volumes: List[float]) -> float:
    """Ratio of latest volume to average of all prior volumes."""
    if len(volumes) < 2:
        return 1.0
    prior = volumes[:-1]
    avg_prior = sum(prior) / len(prior) if prior else 1.0
    if avg_prior <= 0:
        return 1.0
    return volumes[-1] / avg_prior


def compute_momentum_score(closes: List[float]) -> float:
    """Price momentum score: weighted recent returns.
    Higher = stronger momentum. Range roughly -1 to +1.
    """
    if len(closes) < 4:
        return 0.0
    # Weight recent candles more heavily
    weights = [0.4, 0.3, 0.2, 0.1]
    returns = []
    for i in range(-1, max(-len(closes), -5), -1):
        if abs(i) < len(closes):
            prev = closes[i - 1] if abs(i - 1) < len(closes) else closes[0]
            if prev > 0:
                returns.append((closes[i] - prev) / prev)
    score = 0.0
    for i, r in enumerate(returns):
        w = weights[i] if i < len(weights) else 0.05
        score += r * w
    return score


# ---------------------------------------------------------------------------
# Reverse Engineering: Learn from past missed gainers
# ---------------------------------------------------------------------------
def analyze_missed_patterns() -> Dict:
    """Analyze missed_gainers_log.json and top_gainer_patterns.json to learn
    what big gainers looked like BEFORE they pumped.

    Returns dict with:
      - sector_clusters: which sectors pump together
      - peak_hours_utc: when do the biggest pumps start
      - avg_volume_before_pump: typical volume before pump
      - common_gain_range: typical initial gain range before bigger move
      - repeat_pumpers: symbols that pump repeatedly
    """
    analysis = {
        "sector_clusters": {},
        "peak_hours_utc": {},
        "avg_volume_before_pump": 0,
        "common_gain_range": {"min": 10, "max": 30},
        "repeat_pumpers": [],
        "total_analyzed": 0,
    }

    # Load missed gainers log
    missed = _load_json(MISSED_GAINERS_LOG, [])
    patterns = _load_json(GAINER_PATTERNS_FILE, {})

    if not missed and not patterns:
        return analysis

    # Analyze time-of-day patterns
    hour_counts: Dict[int, int] = {}
    symbol_counts: Dict[str, int] = {}
    volumes = []
    gains = []

    for entry in missed:
        ts = entry.get("timestamp", "")
        sym = entry.get("symbol", "")
        gain = entry.get("gain_24h", 0)
        vol = entry.get("volume", 0)

        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                hour = dt.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            except (ValueError, TypeError):
                pass

        if sym:
            symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
        if vol > 0:
            volumes.append(vol)
        if gain > 0:
            gains.append(gain)

    # Peak hours (top 5)
    if hour_counts:
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        analysis["peak_hours_utc"] = {str(h): c for h, c in sorted_hours[:5]}

    # Repeat pumpers (appeared 3+ times)
    analysis["repeat_pumpers"] = [
        sym for sym, cnt in symbol_counts.items() if cnt >= 3
    ]

    # Average volume and gain range
    if volumes:
        analysis["avg_volume_before_pump"] = sum(volumes) / len(volumes)
    if gains:
        sorted_gains = sorted(gains)
        p25 = sorted_gains[len(sorted_gains) // 4] if len(sorted_gains) >= 4 else sorted_gains[0]
        p75 = sorted_gains[3 * len(sorted_gains) // 4] if len(sorted_gains) >= 4 else sorted_gains[-1]
        analysis["common_gain_range"] = {"min": round(p25, 1), "max": round(p75, 1)}

    # Sector clustering from patterns
    if isinstance(patterns, dict):
        known = patterns.get("known_pump_symbols", {})
        # Group by name patterns (AI, meme, DeFi)
        ai_coins = [s for s in known if any(t in s.upper() for t in ("AI", "FET", "RENDER", "TAO", "AGIX"))]
        meme_coins = [s for s in known if any(t in s.upper() for t in ("DOGE", "SHIB", "PEPE", "BONK", "FLOKI", "WIF", "MEME"))]
        defi_coins = [s for s in known if any(t in s.upper() for t in ("UNI", "AAVE", "CAKE", "SUSHI", "CRV", "MKR"))]
        analysis["sector_clusters"] = {
            "ai": ai_coins[:10],
            "meme": meme_coins[:10],
            "defi": defi_coins[:10],
        }

    analysis["total_analyzed"] = len(missed)
    return analysis


# ---------------------------------------------------------------------------
# Strategy 1: Early Momentum Rider
# ---------------------------------------------------------------------------
def strategy_early_momentum_rider(
    tickers: List[Dict],
    existing_symbols: set = None,
) -> List[Dict]:
    """Find coins up 3-8% in 24h with accelerating volume.

    FIXED Mar 24: Catch coins at START of pump, not after.
    Entry: gain 3-8% AND hourly volume acceleration > 2x AND RSI(4H) < 65
    BLOCK: coins already up >15% (mean reversion zone)
    REQUIRE: price within 2% of 24h high (still making new highs)
    TP: Trailing 5% from high
    SL: -8% from entry
    """
    if existing_symbols is None:
        existing_symbols = set()

    # Filter candidates: 3-8% gain sweet spot, BLOCK >15%
    candidates = []
    for t in tickers:
        sym = t["symbol"]
        gain = t["price_change_pct"]
        vol = t["volume_usdt"]

        if sym in existing_symbols:
            continue
        # HARD BLOCK: coins already up >15% are in mean reversion zone
        if gain > EMR_BLOCK_GAIN_24H:
            continue
        if not (EMR_MIN_GAIN_24H <= gain <= EMR_MAX_GAIN_24H):
            continue
        if vol < EMR_MIN_VOLUME_USD:
            continue

        # "Near session high" filter: price must be within 2% of 24h high
        price = t.get("last_price", 0)
        high_24h = t.get("high_24h", 0)
        if price > 0 and high_24h > 0:
            dist_from_high_pct = ((high_24h - price) / high_24h) * 100
            if dist_from_high_pct > EMR_NEAR_HIGH_PCT:
                continue  # Price pulling back, not making new highs

        candidates.append(t)

    if not candidates:
        return []

    # Sort by gain (prefer middle of 3-8% range -- 5-6% sweet spot)
    candidates.sort(key=lambda x: -abs(x["price_change_pct"] - 5.5))

    picks = []
    for c in candidates[:8]:  # Check top 8 candidates
        sym = c["symbol"]
        price = c["last_price"]

        # Fetch 1h klines for volume acceleration
        klines_1h = fetch_klines(sym, "1h", 24)
        if not klines_1h or len(klines_1h) < 3:
            continue

        volumes_1h = [float(k[5]) for k in klines_1h]
        vol_accel = compute_volume_acceleration(volumes_1h)
        if vol_accel < EMR_VOL_ACCEL_MIN:
            continue

        # Fetch 4h klines for RSI check
        klines_4h = fetch_klines(sym, "4h", 20)
        rsi_4h = None
        if klines_4h and len(klines_4h) >= 15:
            closes_4h = [float(k[4]) for k in klines_4h]
            rsi_4h = compute_rsi(closes_4h)

        if rsi_4h is not None and rsi_4h >= EMR_RSI_4H_MAX:
            continue  # Already overbought

        # Compute confidence
        confidence = _emr_confidence(c["price_change_pct"], vol_accel, rsi_4h, c["volume_usdt"])

        tp_price = round(price * (1 + EMR_TP_TRAIL_PCT / 100), 8)
        sl_price = round(price * (1 - EMR_SL_PCT / 100), 8)

        picks.append({
            "symbol": sym,
            "signal_type": "BUY",
            "direction": "LONG",
            "strategy": "gainer_early_momentum_rider",
            "entry_price": price,
            "take_profit": tp_price,
            "stop_loss": sl_price,
            "confidence": confidence,
            "trailing_stop_pct": EMR_TP_TRAIL_PCT,
            "category": "crypto",
            "timeframe": "1h-4h",
            "rationale": (
                f"Early entry: +{c['price_change_pct']:.1f}% 24h (sweet spot), "
                f"vol accel {vol_accel:.1f}x, "
                f"RSI(4H) {rsi_4h:.0f}" if rsi_4h else f"vol accel {vol_accel:.1f}x"
            ),
            "metadata": {
                "gain_24h": c["price_change_pct"],
                "volume_accel": round(vol_accel, 2),
                "rsi_4h": round(rsi_4h, 1) if rsi_4h else None,
                "volume_usdt": c["volume_usdt"],
                "portfolio": "A",
            },
            "opened_at": datetime.now(timezone.utc).isoformat(),
        })

        time.sleep(0.3)  # Rate limit between kline fetches

    return picks


def _emr_confidence(gain_pct: float, vol_accel: float, rsi_4h: Optional[float], volume: float) -> float:
    """Confidence 0.70-0.85 based on volume strength + gain momentum."""
    score = 0.70  # Base

    # Volume acceleration bonus (0-0.05)
    if vol_accel >= 5.0:
        score += 0.05
    elif vol_accel >= 3.0:
        score += 0.03

    # Gain sweet spot bonus (4-7% is ideal for early entry -- 0-0.05)
    if 4 <= gain_pct <= 7:
        score += 0.05
    elif 3 <= gain_pct < 4:
        score += 0.02

    # RSI room bonus (lower RSI = more room to run -- 0-0.03)
    if rsi_4h is not None:
        if rsi_4h < 55:
            score += 0.03
        elif rsi_4h < 65:
            score += 0.02

    # Volume strength bonus (0-0.02)
    if volume >= 20_000_000:
        score += 0.02
    elif volume >= 10_000_000:
        score += 0.01

    return round(min(0.85, score), 2)


# ---------------------------------------------------------------------------
# Strategy 2: Breakout Continuation
# ---------------------------------------------------------------------------
def strategy_breakout_continuation(
    tickers: List[Dict],
    existing_symbols: set = None,
) -> List[Dict]:
    """Find coins breaking 7-day highs with 3x+ volume.

    Catches the 'second leg' after initial breakout.
    Entry on pullback to breakout level.
    TP: +15% trailing, SL: -5% below breakout level.
    """
    if existing_symbols is None:
        existing_symbols = set()

    # Pre-filter: positive gain, decent volume
    candidates = [
        t for t in tickers
        if t["price_change_pct"] > 0
        and t["volume_usdt"] >= BC_MIN_VOLUME_USD
        and t["symbol"] not in existing_symbols
    ]

    if not candidates:
        return []

    # Sort by volume (higher volume breakouts are more reliable)
    candidates.sort(key=lambda x: -x["volume_usdt"])

    picks = []
    for c in candidates[:12]:  # Check top 12 by volume
        sym = c["symbol"]
        price = c["last_price"]

        # Fetch 1h klines for 7-day analysis (168 hours)
        klines = fetch_klines(sym, "1h", 168)
        if not klines or len(klines) < 48:  # Need at least 2 days
            continue

        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        volumes = [float(k[5]) for k in klines]

        # Find 7-day high (excluding last 4 candles)
        if len(highs) <= BC_BREAKOUT_HOURS:
            continue
        prior_high = max(highs[:-BC_BREAKOUT_HOURS])
        recent_high = max(highs[-BC_BREAKOUT_HOURS:])

        # Check if recent candles broke above the prior 7-day high
        if recent_high <= prior_high:
            continue  # No breakout

        # Check volume ratio vs 7-day average
        avg_vol_7d = sum(volumes[:-BC_BREAKOUT_HOURS]) / max(len(volumes) - BC_BREAKOUT_HOURS, 1)
        if avg_vol_7d <= 0:
            continue
        recent_avg_vol = sum(volumes[-BC_BREAKOUT_HOURS:]) / BC_BREAKOUT_HOURS
        vol_ratio = recent_avg_vol / avg_vol_7d

        if vol_ratio < BC_VOL_RATIO_MIN:
            continue  # Volume not strong enough

        # Breakout level = prior 7-day high
        breakout_level = prior_high

        # Check if price has pulled back near breakout level (support flip)
        # Allow entry if price is within 3% above breakout level
        pullback_pct = ((price - breakout_level) / breakout_level) * 100 if breakout_level > 0 else 999
        if pullback_pct > 10:
            continue  # Already too far above breakout -- missed the entry
        if pullback_pct < -2:
            continue  # Fell back below breakout -- failed breakout

        confidence = _bc_confidence(vol_ratio, pullback_pct, c["price_change_pct"])

        tp_price = round(price * (1 + BC_TP_TRAIL_PCT / 100), 8)
        sl_price = round(breakout_level * (1 - BC_SL_PCT / 100), 8)

        picks.append({
            "symbol": sym,
            "signal_type": "BUY",
            "direction": "LONG",
            "strategy": "gainer_breakout_continuation",
            "entry_price": price,
            "take_profit": tp_price,
            "stop_loss": sl_price,
            "confidence": confidence,
            "trailing_stop_pct": BC_TP_TRAIL_PCT,
            "category": "crypto",
            "timeframe": "1h",
            "rationale": (
                f"7d breakout: prior high {breakout_level:.6g}, "
                f"vol ratio {vol_ratio:.1f}x, pullback {pullback_pct:.1f}%"
            ),
            "metadata": {
                "breakout_level": breakout_level,
                "vol_ratio_7d": round(vol_ratio, 2),
                "pullback_pct": round(pullback_pct, 2),
                "gain_24h": c["price_change_pct"],
                "volume_usdt": c["volume_usdt"],
                "portfolio": "B",
            },
            "opened_at": datetime.now(timezone.utc).isoformat(),
        })

        time.sleep(0.3)

    return picks


def _bc_confidence(vol_ratio: float, pullback_pct: float, gain_24h: float) -> float:
    """Confidence 0.70-0.85 for breakout continuation."""
    score = 0.70

    # Volume ratio bonus (0-0.05)
    if vol_ratio >= 5.0:
        score += 0.05
    elif vol_ratio >= 4.0:
        score += 0.03

    # Pullback quality (closer to breakout = better entry -- 0-0.05)
    if 0 <= pullback_pct <= 3:
        score += 0.05  # Perfect pullback to support
    elif 3 < pullback_pct <= 6:
        score += 0.03

    # Gain context (0-0.05)
    if 5 <= gain_24h <= 20:
        score += 0.05  # Moderate gain = room to run
    elif gain_24h > 20:
        score += 0.02  # Already extended

    return round(min(0.85, score), 2)


# ---------------------------------------------------------------------------
# Strategy 3: Gainer Momentum Portfolio
# ---------------------------------------------------------------------------
def strategy_momentum_portfolio(
    tickers: List[Dict],
    existing_symbols: set = None,
) -> List[Dict]:
    """Rank ALL coins by composite momentum score, take TOP 3.

    Composite = 24h_gain * volume_ratio_vs_median * price_momentum_score
    Hold 24-48h max. Drop if hourly gain negative 2 consecutive hours.
    """
    if existing_symbols is None:
        existing_symbols = set()

    # Filter: positive gain, good volume, BLOCK >15% (mean reversion zone)
    candidates = [
        t for t in tickers
        if 3.0 <= t["price_change_pct"] <= 15.0  # 3-15% gain; BLOCK >15%
        and t["volume_usdt"] >= GMP_MIN_VOLUME_USD
        and t["symbol"] not in existing_symbols
    ]

    if not candidates:
        return []

    # Compute median volume for normalization
    all_volumes = [t["volume_usdt"] for t in candidates if t["volume_usdt"] > 0]
    if not all_volumes:
        return []
    all_volumes.sort()
    median_vol = all_volumes[len(all_volumes) // 2]
    if median_vol <= 0:
        median_vol = 1.0

    # Score each candidate
    scored = []
    for c in candidates:
        gain = c["price_change_pct"]
        vol_ratio = c["volume_usdt"] / median_vol

        # Fetch short klines for price momentum
        klines = fetch_klines(c["symbol"], "1h", 6)
        if klines and len(klines) >= 3:
            closes = [float(k[4]) for k in klines]
            mom_score = compute_momentum_score(closes)
        else:
            mom_score = gain / 100.0  # Fallback: use 24h gain as proxy

        # Composite score
        composite = gain * max(vol_ratio, 0.1) * max(1.0 + mom_score * 10, 0.1)

        scored.append({
            **c,
            "composite_score": round(composite, 2),
            "vol_ratio": round(vol_ratio, 2),
            "momentum_score": round(mom_score, 4),
        })
        time.sleep(0.2)

    # Rank by composite, take top N
    scored.sort(key=lambda x: -x["composite_score"])
    top = scored[:GMP_TOP_N]

    picks = []
    for rank, c in enumerate(top, 1):
        price = c["last_price"]
        confidence = _gmp_confidence(c["composite_score"], c["vol_ratio"], rank)

        tp_price = round(price * (1 + GMP_TP_PCT / 100), 8)
        sl_price = round(price * (1 - GMP_SL_PCT / 100), 8)

        picks.append({
            "symbol": c["symbol"],
            "signal_type": "BUY",
            "direction": "LONG",
            "strategy": "gainer_momentum_portfolio",
            "entry_price": price,
            "take_profit": tp_price,
            "stop_loss": sl_price,
            "confidence": confidence,
            "category": "crypto",
            "timeframe": "1h",
            "max_hold_hours": GMP_MAX_HOLD_HOURS,
            "rationale": (
                f"Momentum rank #{rank}: composite {c['composite_score']:.1f}, "
                f"+{c['price_change_pct']:.1f}% 24h, vol ratio {c['vol_ratio']:.1f}x"
            ),
            "metadata": {
                "momentum_rank": rank,
                "composite_score": c["composite_score"],
                "gain_24h": c["price_change_pct"],
                "vol_ratio": c["vol_ratio"],
                "momentum_score": c["momentum_score"],
                "volume_usdt": c["volume_usdt"],
                "portfolio": "C",
            },
            "opened_at": datetime.now(timezone.utc).isoformat(),
        })

    return picks


def _gmp_confidence(composite: float, vol_ratio: float, rank: int) -> float:
    """Confidence for momentum portfolio. Rank 1 gets highest."""
    base = 0.80 if rank == 1 else (0.75 if rank == 2 else 0.72)

    # Composite score bonus
    if composite >= 500:
        base += 0.03
    elif composite >= 200:
        base += 0.02

    # Volume ratio bonus
    if vol_ratio >= 3.0:
        base += 0.02

    return round(min(0.85, base), 2)


# ---------------------------------------------------------------------------
# Portfolio A/B Test Management
# ---------------------------------------------------------------------------
def _load_json(path: Path, default=None) -> Any:
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    tmp.replace(path)


def _sanitize_for_json(obj):
    """Replace NaN/Infinity with None for json.dump safety."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def load_portfolio_state() -> Dict:
    """Load or initialize the 3 forward-test portfolios."""
    state = _load_json(PORTFOLIO_STATE_FILE, None)
    if state and "portfolios" in state:
        return state

    # Initialize fresh state
    now = datetime.now(timezone.utc).isoformat()
    state = {
        "created_at": now,
        "last_updated": now,
        "portfolios": {
            "A": {
                "name": "Early Momentum Rider",
                "strategy": "gainer_early_momentum_rider",
                "description": "10-30% gainers with volume acceleration",
                "starting_capital": STARTING_CAPITAL,
                "current_capital": STARTING_CAPITAL,
                "open_positions": [],
                "closed_positions": [],
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0.0,
                "max_drawdown": 0.0,
                "peak_capital": STARTING_CAPITAL,
            },
            "B": {
                "name": "Breakout Continuation",
                "strategy": "gainer_breakout_continuation",
                "description": "7-day high breakers with 3x+ volume",
                "starting_capital": STARTING_CAPITAL,
                "current_capital": STARTING_CAPITAL,
                "open_positions": [],
                "closed_positions": [],
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0.0,
                "max_drawdown": 0.0,
                "peak_capital": STARTING_CAPITAL,
            },
            "C": {
                "name": "Top 3 Momentum",
                "strategy": "gainer_momentum_portfolio",
                "description": "Pure momentum ranking top 3",
                "starting_capital": STARTING_CAPITAL,
                "current_capital": STARTING_CAPITAL,
                "open_positions": [],
                "closed_positions": [],
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0.0,
                "max_drawdown": 0.0,
                "peak_capital": STARTING_CAPITAL,
            },
        },
        "scan_history": [],
    }
    _save_json(PORTFOLIO_STATE_FILE, state)
    return state


def update_portfolio_positions(state: Dict) -> Dict:
    """Check open positions against current prices, close TP/SL hits."""
    now = datetime.now(timezone.utc)

    for port_key, port in state["portfolios"].items():
        still_open = []
        for pos in port.get("open_positions", []):
            sym = pos["symbol"]
            entry = pos["entry_price"]
            tp = pos["take_profit"]
            sl = pos["stop_loss"]
            max_hold = pos.get("max_hold_hours", 72)

            # Fetch current price
            current = _get_current_price(sym)
            if current is None:
                still_open.append(pos)
                continue

            pos["current_price"] = current
            pos["unrealized_pnl_pct"] = round(((current - entry) / entry) * 100, 2) if entry > 0 else 0

            # Check TP
            if current >= tp:
                pnl_pct = ((current - entry) / entry) * 100
                _close_position(port, pos, current, pnl_pct, "TP_HIT")
                continue

            # Check SL
            if current <= sl:
                pnl_pct = ((current - entry) / entry) * 100
                _close_position(port, pos, current, pnl_pct, "SL_HIT")
                continue

            # Check max hold time
            opened = pos.get("opened_at", "")
            if opened:
                try:
                    opened_dt = datetime.fromisoformat(opened.replace("Z", "+00:00"))
                    if (now - opened_dt).total_seconds() > max_hold * 3600:
                        pnl_pct = ((current - entry) / entry) * 100
                        _close_position(port, pos, current, pnl_pct, "MAX_HOLD")
                        continue
                except (ValueError, TypeError):
                    pass

            # Check momentum loss for portfolio C (2 consecutive negative hourly candles)
            if port_key == "C":
                klines = fetch_klines(sym, "1h", 3)
                if klines and len(klines) >= 3:
                    c1 = float(klines[-2][4]) - float(klines[-2][1])  # close - open
                    c2 = float(klines[-1][4]) - float(klines[-1][1])
                    if c1 < 0 and c2 < 0:
                        pnl_pct = ((current - entry) / entry) * 100
                        _close_position(port, pos, current, pnl_pct, "MOMENTUM_LOSS")
                        continue

            # Update trailing stop if applicable
            trailing_pct = pos.get("trailing_stop_pct")
            if trailing_pct and current > entry:
                highest = max(pos.get("highest_price", entry), current)
                pos["highest_price"] = highest
                new_sl = round(highest * (1 - trailing_pct / 100), 8)
                if new_sl > sl:
                    pos["stop_loss"] = new_sl

            still_open.append(pos)

        port["open_positions"] = still_open

    state["last_updated"] = now.isoformat()
    return state


def _close_position(port: Dict, pos: Dict, exit_price: float, pnl_pct: float, reason: str):
    """Close a position and update portfolio stats."""
    pos["exit_price"] = exit_price
    pos["pnl_pct"] = round(pnl_pct, 2)
    pos["exit_reason"] = reason
    pos["closed_at"] = datetime.now(timezone.utc).isoformat()

    # Update capital
    alloc = pos.get("allocation", port["current_capital"] / MAX_POSITIONS_PER_PORTFOLIO)
    pnl_usd = alloc * (pnl_pct / 100)
    port["current_capital"] = round(port["current_capital"] + pnl_usd, 2)
    port["total_pnl"] = round(port["total_pnl"] + pnl_usd, 2)
    port["total_trades"] += 1

    if pnl_pct > 0:
        port["wins"] += 1
    else:
        port["losses"] += 1

    # Track drawdown
    if port["current_capital"] > port["peak_capital"]:
        port["peak_capital"] = port["current_capital"]
    dd = ((port["peak_capital"] - port["current_capital"]) / port["peak_capital"]) * 100
    if dd > port["max_drawdown"]:
        port["max_drawdown"] = round(dd, 2)

    # Keep last 100 closed positions
    port.setdefault("closed_positions", []).append(pos)
    port["closed_positions"] = port["closed_positions"][-100:]


def _get_current_price(symbol: str) -> Optional[float]:
    """Fetch current price from Binance with failover."""
    for base in BINANCE_SPOT_BASES[:3]:  # Try first 3 mirrors
        data = _fetch_json(f"{base}/api/v3/ticker/price?symbol={symbol}")
        if data and "price" in data:
            try:
                return float(data["price"])
            except (ValueError, TypeError):
                continue

    # Bybit fallback
    data = _fetch_json(f"{BYBIT_BASE}/v5/market/tickers?category=spot&symbol={symbol}")
    if data and data.get("retCode") == 0:
        tickers = data.get("result", {}).get("list", [])
        if tickers:
            try:
                return float(tickers[0].get("lastPrice", 0))
            except (ValueError, TypeError):
                pass

    return None


def add_picks_to_portfolios(state: Dict, picks: List[Dict]) -> Dict:
    """Add new picks to their respective portfolios (A, B, or C)."""
    for pick in picks:
        port_key = pick.get("metadata", {}).get("portfolio")
        if not port_key or port_key not in state["portfolios"]:
            continue

        port = state["portfolios"][port_key]

        # Check position limit
        if len(port["open_positions"]) >= MAX_POSITIONS_PER_PORTFOLIO:
            continue

        # Check not already holding this symbol
        held_symbols = {p["symbol"] for p in port["open_positions"]}
        if pick["symbol"] in held_symbols:
            continue

        # Compute allocation
        available = port["current_capital"]
        alloc = min(available / MAX_POSITIONS_PER_PORTFOLIO, available * 0.4)
        if alloc < 100:  # Minimum $100 position
            continue

        pos = {
            "symbol": pick["symbol"],
            "entry_price": pick["entry_price"],
            "take_profit": pick["take_profit"],
            "stop_loss": pick["stop_loss"],
            "confidence": pick["confidence"],
            "allocation": round(alloc, 2),
            "trailing_stop_pct": pick.get("trailing_stop_pct"),
            "max_hold_hours": pick.get("max_hold_hours", 72),
            "opened_at": pick["opened_at"],
            "rationale": pick.get("rationale", ""),
            "highest_price": pick["entry_price"],
        }

        port["open_positions"].append(pos)

    return state


# ---------------------------------------------------------------------------
# Strategy dict for scanner.py integration
# ---------------------------------------------------------------------------
GAINER_CAPTURE_STRATEGIES = {
    "gainer_early_momentum_rider": {
        "name": "Gainer: Early Momentum Rider",
        "family": "gainer_capture",
        "category": "crypto",
        "signal_type": "BUY",
        "timeframe": "1h-4h",
        "description": "Coins up 3-8% with accelerating volume, RSI(4H)<65, near session high",
        "expected_wr": 0.55,
        "expected_rr": 1.6,
        "tp_pct": EMR_TP_TRAIL_PCT,
        "sl_pct": EMR_SL_PCT,
        "regime_affinity": ["trending"],
    },
    "gainer_breakout_continuation": {
        "name": "Gainer: Breakout Continuation",
        "family": "gainer_capture",
        "category": "crypto",
        "signal_type": "BUY",
        "timeframe": "1h",
        "description": "7-day high breakout with 3x+ volume, pullback entry",
        "expected_wr": 0.58,
        "expected_rr": 3.0,
        "tp_pct": BC_TP_TRAIL_PCT,
        "sl_pct": BC_SL_PCT,
        "regime_affinity": ["trending"],
    },
    "gainer_momentum_portfolio": {
        "name": "Gainer: Momentum Portfolio Top 3",
        "family": "gainer_capture",
        "category": "crypto",
        "signal_type": "BUY",
        "timeframe": "1h",
        "description": "Top 3 coins by composite momentum score (3-15% gain, blocks >15%)",
        "expected_wr": 0.52,
        "expected_rr": 2.0,
        "tp_pct": GMP_TP_PCT,
        "sl_pct": GMP_SL_PCT,
        "regime_affinity": ["trending", "transitional"],
    },
}


# ---------------------------------------------------------------------------
# Main entry point: generate_gainer_picks()
# ---------------------------------------------------------------------------
def generate_gainer_picks(
    data: Optional[Dict] = None,
    existing_symbols: Optional[set] = None,
) -> List[Dict]:
    """Run all 3 gainer capture strategies and return combined picks.

    This is the main function called by scanner.py.
    Also updates the A/B test portfolios.

    Args:
        data: Price data dict from scanner (can be None, we fetch directly).
        existing_symbols: Symbols already in active picks (to avoid dupes).

    Returns:
        List of pick dicts ready for injection into scanner's all_signals.
    """
    print("\n  [GAINER CAPTURE] Running 3 gainer strategies...")
    now = datetime.now(timezone.utc)

    if existing_symbols is None:
        existing_symbols = set()
        # Try to load from active picks
        active = _load_json(ACTIVE_PICKS_FILE, [])
        if isinstance(active, list):
            existing_symbols = {p.get("symbol", "") for p in active}

    # 1. Fetch all tickers (single API call, shared across strategies)
    tickers = fetch_all_tickers()
    if not tickers:
        print("  [GAINER CAPTURE] No tickers available, skipping")
        return []
    print(f"  [GAINER CAPTURE] Fetched {len(tickers)} USDT tickers")

    # 2. Analyze patterns from missed gainers (informational)
    patterns = analyze_missed_patterns()
    if patterns.get("total_analyzed", 0) > 0:
        print(f"  [GAINER CAPTURE] Analyzed {patterns['total_analyzed']} past missed gainers")
        if patterns.get("repeat_pumpers"):
            print(f"  [GAINER CAPTURE] Repeat pumpers: {', '.join(patterns['repeat_pumpers'][:5])}")
        if patterns.get("peak_hours_utc"):
            top_hour = max(patterns["peak_hours_utc"], key=lambda h: patterns["peak_hours_utc"][h])
            print(f"  [GAINER CAPTURE] Peak pump hour (UTC): {top_hour}:00")

    # 3. Run strategies
    all_picks = []

    # Strategy 1: Early Momentum Rider
    emr_picks = strategy_early_momentum_rider(tickers, existing_symbols)
    print(f"  [GAINER CAPTURE] Strategy 1 (Early Momentum): {len(emr_picks)} picks")
    all_picks.extend(emr_picks)

    # Strategy 2: Breakout Continuation
    bc_picks = strategy_breakout_continuation(tickers, existing_symbols)
    print(f"  [GAINER CAPTURE] Strategy 2 (Breakout Continuation): {len(bc_picks)} picks")
    all_picks.extend(bc_picks)

    # Strategy 3: Momentum Portfolio
    gmp_picks = strategy_momentum_portfolio(tickers, existing_symbols)
    print(f"  [GAINER CAPTURE] Strategy 3 (Momentum Portfolio): {len(gmp_picks)} picks")
    all_picks.extend(gmp_picks)

    print(f"  [GAINER CAPTURE] Total: {len(all_picks)} picks across 3 strategies")

    # 4. Update A/B test portfolios
    try:
        state = load_portfolio_state()
        state = update_portfolio_positions(state)
        state = add_picks_to_portfolios(state, all_picks)

        # Record scan
        scan_record = {
            "timestamp": now.isoformat(),
            "picks_generated": len(all_picks),
            "strategy_counts": {
                "early_momentum": len(emr_picks),
                "breakout_continuation": len(bc_picks),
                "momentum_portfolio": len(gmp_picks),
            },
            "pattern_analysis": {
                "repeat_pumpers_count": len(patterns.get("repeat_pumpers", [])),
                "peak_hour": patterns.get("peak_hours_utc", {}),
            },
        }
        state.setdefault("scan_history", []).append(scan_record)
        state["scan_history"] = state["scan_history"][-200:]  # Keep last 200

        _save_json(PORTFOLIO_STATE_FILE, _sanitize_for_json(state))

        # Print portfolio status
        for key, port in state["portfolios"].items():
            n_open = len(port.get("open_positions", []))
            wr = (port["wins"] / port["total_trades"] * 100) if port["total_trades"] > 0 else 0
            print(
                f"  [PORTFOLIO {key}] {port['name']}: "
                f"${port['current_capital']:.0f} ({port['total_pnl']:+.0f} PnL), "
                f"{port['total_trades']} trades ({wr:.0f}% WR), "
                f"{n_open} open"
            )
    except Exception as e:
        print(f"  [GAINER CAPTURE] Portfolio update error: {e}")

    return all_picks


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("  GAINER CAPTURE STRATEGY -- Standalone Run")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    picks = generate_gainer_picks()

    if picks:
        # Save picks to a dedicated output file
        output_path = DATA_DIR / "gainer_capture_picks.json"
        _save_json(output_path, _sanitize_for_json(picks))
        print(f"\n  Saved {len(picks)} picks to {output_path}")

        for p in picks:
            print(
                f"  {p['strategy']}: {p['symbol']} @ {p['entry_price']:.6g} "
                f"(TP {p['take_profit']:.6g} / SL {p['stop_loss']:.6g}) "
                f"conf={p['confidence']:.2f}"
            )
    else:
        print("\n  No picks generated this scan.")

    print("\n  Done.")
