#!/usr/bin/env python3
"""
Strategy Reverse-Engineer Module
=================================
Takes a trader's fill history (from hyperliquid_traders.py or copy_trader_analyzer.py),
fetches 1h candle data around each entry from Binance, computes technical indicators
at entry time, classifies the trader's style, and generates a "strategy fingerprint".

Output: alpha_engine/data/trader_fingerprints.json

Stdlib only. No numpy/pandas.
"""

import json
import math
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
FINGERPRINTS_FILE = os.path.join(DATA_DIR, "trader_fingerprints.json")

# How many 1h candles to fetch around each trade entry (for indicator computation)
CANDLE_LOOKBACK = 50  # Need 50 candles for EMA/RSI/ATR calculations
RATE_LIMIT_DELAY = 0.3  # Binance rate limit spacing

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _create_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _http_get(url: str, retries: int = 2, timeout: int = 15) -> Optional[Any]:
    """GET JSON with retries and API failover awareness."""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            ctx = _create_ssl_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return json.loads(resp.read())
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, json.JSONDecodeError):
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
    return None


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Binance candle fetching (3-API failover per MEMORY.md rule)
# ---------------------------------------------------------------------------

def fetch_klines(symbol: str, interval: str, end_time_ms: int, limit: int = 50) -> List[dict]:
    """
    Fetch historical klines ending at end_time_ms.
    Returns list of dicts: {open_time, open, high, low, close, volume}.
    Uses Binance 3-mirror failover chain.
    """
    # Normalize symbol for Binance
    sym = symbol.upper().replace("-", "").replace("/", "")
    if not sym.endswith("USDT") and not sym.endswith("BUSD"):
        sym = sym.replace("USD", "USDT")
        if not sym.endswith("USDT"):
            sym += "USDT"

    apis = [
        f"https://api.binance.com/api/v3/klines?symbol={sym}&interval={interval}&endTime={end_time_ms}&limit={limit}",
        f"https://api1.binance.com/api/v3/klines?symbol={sym}&interval={interval}&endTime={end_time_ms}&limit={limit}",
        f"https://api3.binance.com/api/v3/klines?symbol={sym}&interval={interval}&endTime={end_time_ms}&limit={limit}",
    ]

    for url in apis:
        data = _http_get(url)
        if data and isinstance(data, list) and len(data) > 0:
            candles = []
            for k in data:
                candles.append({
                    "open_time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": int(k[6]),
                })
            return candles
        time.sleep(RATE_LIMIT_DELAY)

    return []


def fetch_funding_rate(symbol: str, start_time_ms: int) -> Optional[float]:
    """Fetch the funding rate closest to start_time_ms. Returns rate or None."""
    sym = symbol.upper().replace("-", "").replace("/", "")
    if not sym.endswith("USDT"):
        sym = sym.replace("USD", "USDT")
        if not sym.endswith("USDT"):
            sym += "USDT"

    apis = [
        f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}&startTime={start_time_ms - 28800000}&endTime={start_time_ms + 28800000}&limit=5",
        f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}&limit=3",
    ]

    for url in apis:
        data = _http_get(url)
        if data and isinstance(data, list) and len(data) > 0:
            # Find closest funding rate to our timestamp
            best = min(data, key=lambda x: abs(int(x.get("fundingTime", 0)) - start_time_ms))
            return _safe_float(best.get("fundingRate", 0))
        time.sleep(RATE_LIMIT_DELAY)

    return None


# ---------------------------------------------------------------------------
# Technical indicator computations (stdlib only, no numpy)
# ---------------------------------------------------------------------------

def compute_ema(values: List[float], period: int) -> List[float]:
    """Compute EMA over a list of values. Returns list of same length (NaN-padded start)."""
    if not values or period <= 0:
        return []
    ema = [0.0] * len(values)
    k = 2.0 / (period + 1)

    # SMA for the first `period` values as seed
    if len(values) < period:
        return [sum(values) / len(values)] * len(values)

    sma = sum(values[:period]) / period
    ema[period - 1] = sma
    for i in range(period, len(values)):
        ema[i] = values[i] * k + ema[i - 1] * (1 - k)
    # Fill initial values with 0 (not meaningful)
    for i in range(period - 1):
        ema[i] = ema[period - 1]
    return ema


def compute_rsi(closes: List[float], period: int = 14) -> List[float]:
    """Compute RSI using Wilder's smoothing. Returns list of same length."""
    if len(closes) < period + 1:
        return [50.0] * len(closes)

    rsi = [50.0] * len(closes)
    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    if len(gains) < period:
        return rsi

    # Initial average gain/loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    # Fill initial RSI for the seed period
    if avg_loss == 0:
        seed_rsi = 100.0
    else:
        seed_avg_gain = sum(gains[:period]) / period
        seed_avg_loss = sum(losses[:period]) / period
        if seed_avg_loss == 0:
            seed_rsi = 100.0
        else:
            seed_rsi = 100.0 - (100.0 / (1.0 + seed_avg_gain / seed_avg_loss))
    rsi[period] = seed_rsi

    return rsi


def compute_atr(candles: List[dict], period: int = 14) -> List[float]:
    """Compute ATR (Average True Range). Returns list of same length as candles."""
    if len(candles) < 2:
        return [0.0] * len(candles)

    true_ranges = [0.0]
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        true_ranges.append(tr)

    atr = [0.0] * len(candles)
    if len(true_ranges) < period + 1:
        avg = sum(true_ranges) / len(true_ranges) if true_ranges else 0
        return [avg] * len(candles)

    # Initial ATR = SMA of first `period` TRs
    atr[period] = sum(true_ranges[1:period + 1]) / period
    for i in range(period + 1, len(true_ranges)):
        atr[i] = (atr[i - 1] * (period - 1) + true_ranges[i]) / period

    # Fill early values
    for i in range(period):
        atr[i] = atr[period]

    return atr


# ---------------------------------------------------------------------------
# Per-trade indicator snapshot
# ---------------------------------------------------------------------------

def compute_entry_indicators(candles: List[dict], entry_candle_idx: int,
                             funding_rate: Optional[float] = None) -> Dict[str, Any]:
    """
    Given candles and the index of the entry candle, compute all indicators
    at the moment of entry.
    """
    if not candles or entry_candle_idx < 0 or entry_candle_idx >= len(candles):
        return {}

    closes = [c["close"] for c in candles]
    volumes = [c["volume"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    idx = entry_candle_idx

    # RSI(14)
    rsi_values = compute_rsi(closes, 14)
    rsi_at_entry = round(rsi_values[idx], 2)

    # EMA(9) and EMA(21)
    ema9 = compute_ema(closes, 9)
    ema21 = compute_ema(closes, 21)
    ema9_at_entry = ema9[idx]
    ema21_at_entry = ema21[idx]
    price_at_entry = closes[idx]

    ema_position = "above" if ema9_at_entry > ema21_at_entry else "below"

    # Check for recent crossover (within last 3 candles)
    crossover_recent = False
    for j in range(max(0, idx - 3), idx):
        if j > 0 and ema9[j - 1] <= ema21[j - 1] and ema9[j] > ema21[j]:
            crossover_recent = True  # Bullish crossover
            break
        if j > 0 and ema9[j - 1] >= ema21[j - 1] and ema9[j] < ema21[j]:
            crossover_recent = True  # Bearish crossover
            break

    # Volume ratio (entry candle vs 20-candle average)
    vol_window_start = max(0, idx - 20)
    avg_vol_20 = sum(volumes[vol_window_start:idx]) / max(1, idx - vol_window_start) if idx > vol_window_start else volumes[idx]
    volume_ratio = round(volumes[idx] / avg_vol_20, 2) if avg_vol_20 > 0 else 1.0

    # Price position vs 24h high/low (24 candles on 1h timeframe)
    lookback_24h = max(0, idx - 24)
    high_24h = max(highs[lookback_24h:idx + 1])
    low_24h = min(lows[lookback_24h:idx + 1])
    range_24h = high_24h - low_24h
    if range_24h > 0:
        price_position_24h = round((price_at_entry - low_24h) / range_24h, 3)
    else:
        price_position_24h = 0.5

    # Is it a breakout? (price within 2% of 24h high)
    is_breakout = price_at_entry >= high_24h * 0.98

    # Is it a dip? (price within 5% of 24h low)
    is_dip = price_at_entry <= low_24h * 1.05

    # ATR(14)
    atr_values = compute_atr(candles, 14)
    atr_at_entry = round(atr_values[idx], 6)

    # Candle color at entry
    entry_candle = candles[idx]
    candle_green = entry_candle["close"] > entry_candle["open"]

    # Previous candle momentum (was the last candle a big green move?)
    if idx > 0:
        prev = candles[idx - 1]
        prev_body_pct = (prev["close"] - prev["open"]) / prev["open"] * 100 if prev["open"] > 0 else 0
    else:
        prev_body_pct = 0

    result = {
        "rsi_14": rsi_at_entry,
        "ema9": round(ema9_at_entry, 6),
        "ema21": round(ema21_at_entry, 6),
        "ema_position": ema_position,
        "ema_crossover_recent": crossover_recent,
        "volume_ratio_vs_20avg": volume_ratio,
        "price_position_24h": price_position_24h,
        "is_breakout": is_breakout,
        "is_dip": is_dip,
        "atr_14": atr_at_entry,
        "entry_candle_green": candle_green,
        "prev_candle_body_pct": round(prev_body_pct, 2),
        "high_24h": round(high_24h, 6),
        "low_24h": round(low_24h, 6),
    }

    if funding_rate is not None:
        result["funding_rate"] = round(funding_rate, 6)

    return result


# ---------------------------------------------------------------------------
# Style classification
# ---------------------------------------------------------------------------

def classify_style(indicator_snapshots: List[Dict[str, Any]]) -> str:
    """
    Classify trading style based on aggregated indicator snapshots across trades.

    Styles:
      - "breakout_scalper": entries cluster near 24h highs with volume spikes
      - "mean_reversion": entries near support with oversold RSI
      - "momentum": entries follow large green candles
      - "funding_arb": entries correlate with extreme funding rates
      - "dip_buyer": entries on red candles during uptrends
      - "mixed": no dominant pattern
    """
    if not indicator_snapshots:
        return "mixed"

    n = len(indicator_snapshots)

    # Count patterns
    breakout_count = 0
    mean_reversion_count = 0
    momentum_count = 0
    funding_arb_count = 0
    dip_buyer_count = 0

    for snap in indicator_snapshots:
        rsi = snap.get("rsi_14", 50)
        vol_ratio = snap.get("volume_ratio_vs_20avg", 1.0)
        pos_24h = snap.get("price_position_24h", 0.5)
        is_breakout = snap.get("is_breakout", False)
        is_dip = snap.get("is_dip", False)
        candle_green = snap.get("entry_candle_green", True)
        prev_body_pct = snap.get("prev_candle_body_pct", 0)
        ema_pos = snap.get("ema_position", "above")
        funding = snap.get("funding_rate", None)

        # Breakout scalper: near 24h high + volume spike
        if (is_breakout or pos_24h > 0.85) and vol_ratio > 1.5:
            breakout_count += 1

        # Mean reversion: low price position + oversold RSI
        if (is_dip or pos_24h < 0.25) and rsi < 35:
            mean_reversion_count += 1

        # Momentum: following large green candles
        if candle_green and prev_body_pct > 1.0 and vol_ratio > 1.2:
            momentum_count += 1

        # Funding arb: extreme funding rates
        if funding is not None and abs(funding) > 0.001:
            funding_arb_count += 1

        # Dip buyer: red candle + uptrend (EMA9 > EMA21)
        if not candle_green and ema_pos == "above" and pos_24h < 0.4:
            dip_buyer_count += 1

    # Pick dominant style (needs at least 30% of trades to qualify)
    threshold = max(2, n * 0.3)

    scores = {
        "breakout_scalper": breakout_count,
        "mean_reversion": mean_reversion_count,
        "momentum": momentum_count,
        "funding_arb": funding_arb_count,
        "dip_buyer": dip_buyer_count,
    }

    best_style = max(scores, key=scores.get)
    if scores[best_style] >= threshold:
        return best_style

    # Secondary check: if no strong dominant, pick highest above 20%
    secondary_threshold = max(1, n * 0.2)
    if scores[best_style] >= secondary_threshold:
        return best_style

    return "mixed"


# ---------------------------------------------------------------------------
# Fingerprint generator
# ---------------------------------------------------------------------------

def generate_fingerprint(
    trader_id: str,
    fills: List[dict],
    positions: Optional[List[dict]] = None,
    trader_stats: Optional[dict] = None,
    fetch_candles: bool = True,
    max_trades_to_analyze: int = 30,
) -> Dict[str, Any]:
    """
    Generate a complete strategy fingerprint for a single trader.

    Args:
        trader_id: Wallet address or unique code
        fills: List of fill dicts from hyperliquid_traders.fetch_fills() or OKX history
        positions: Current open positions (optional, for leverage info)
        trader_stats: Pre-computed stats from analyze_trader() (optional)
        fetch_candles: Whether to actually fetch Binance candles (False for dry run)
        max_trades_to_analyze: Cap on how many trades to fetch candles for
    """
    if not fills:
        return {"trader": trader_id, "error": "no_fills", "style": "unknown"}

    # Determine source format and normalize fills
    normalized_fills = _normalize_fills(fills)

    # Sort by time descending, take most recent
    normalized_fills.sort(key=lambda x: x["time_ms"], reverse=True)
    fills_to_analyze = normalized_fills[:max_trades_to_analyze]

    # Fetch candle data and compute indicators for each trade
    indicator_snapshots = []
    candle_cache = {}  # (symbol, hour_bucket) -> candles, to avoid duplicate fetches

    for fill in fills_to_analyze:
        coin = fill["coin"]
        entry_time_ms = fill["time_ms"]

        if entry_time_ms <= 0 or not coin:
            continue

        if not fetch_candles:
            # Dry run: skip candle fetching
            continue

        # Cache key: symbol + rounded to 4h bucket
        bucket = entry_time_ms // (4 * 3600000)
        cache_key = (coin, bucket)

        if cache_key in candle_cache:
            candles = candle_cache[cache_key]
        else:
            candles = fetch_klines(coin, "1h", entry_time_ms, limit=CANDLE_LOOKBACK)
            candle_cache[cache_key] = candles
            time.sleep(RATE_LIMIT_DELAY)

        if not candles:
            continue

        # Find the candle closest to entry time
        entry_candle_idx = _find_closest_candle(candles, entry_time_ms)
        if entry_candle_idx < 0:
            continue

        # Fetch funding rate (best effort)
        funding = fetch_funding_rate(coin, entry_time_ms)

        indicators = compute_entry_indicators(candles, entry_candle_idx, funding)
        if indicators:
            indicators["coin"] = coin
            indicators["side"] = fill.get("side", "")
            indicators["time_ms"] = entry_time_ms
            indicator_snapshots.append(indicators)

    # Classify style
    style = classify_style(indicator_snapshots)

    # Compute aggregated stats
    fingerprint = _build_fingerprint(trader_id, normalized_fills, indicator_snapshots,
                                     style, positions, trader_stats)

    return fingerprint


def _normalize_fills(fills: List[dict]) -> List[dict]:
    """Normalize fills from either Hyperliquid or OKX format."""
    normalized = []
    for f in fills:
        # Hyperliquid format
        if "coin" in f and "time_ms" in f:
            normalized.append({
                "coin": f.get("coin", ""),
                "price": _safe_float(f.get("price", f.get("px", 0))),
                "size": _safe_float(f.get("size", f.get("sz", 0))),
                "side": f.get("side", ""),
                "time_ms": int(_safe_float(f.get("time_ms", f.get("time", 0)))),
                "closed_pnl": _safe_float(f.get("closed_pnl", f.get("closedPnl", 0))),
            })
        # OKX format
        elif "instId" in f:
            inst_id = f.get("instId", "")
            coin = inst_id.replace("-SWAP", "").split("-")[0] if inst_id else ""
            open_time = int(_safe_float(f.get("openTime", 0)))
            normalized.append({
                "coin": coin,
                "price": _safe_float(f.get("openAvgPx", 0)),
                "size": _safe_float(f.get("subPos", f.get("sz", 0))),
                "side": f.get("posSide", "").upper(),
                "time_ms": open_time,
                "closed_pnl": _safe_float(f.get("pnl", 0)),
            })
        # Generic format (entry_price + timestamp)
        elif "entry_price" in f:
            ts = f.get("timestamp", f.get("opened_at", ""))
            time_ms = 0
            if isinstance(ts, (int, float)):
                time_ms = int(ts)
            elif isinstance(ts, str) and ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    time_ms = int(dt.timestamp() * 1000)
                except (ValueError, OSError):
                    pass
            normalized.append({
                "coin": f.get("coin", f.get("symbol", "")).replace("USDT", "").replace("-USD", ""),
                "price": _safe_float(f.get("entry_price", 0)),
                "size": _safe_float(f.get("size", 1)),
                "side": f.get("direction", f.get("side", "")).upper(),
                "time_ms": time_ms,
                "closed_pnl": _safe_float(f.get("closed_pnl", f.get("pnl", 0))),
            })

    return normalized


def _find_closest_candle(candles: List[dict], target_ms: int) -> int:
    """Find index of candle whose time range contains or is closest to target_ms."""
    best_idx = -1
    best_dist = float("inf")

    for i, c in enumerate(candles):
        ot = c["open_time"]
        ct = c.get("close_time", ot + 3600000)

        # If target is within this candle's range, perfect match
        if ot <= target_ms <= ct:
            return i

        dist = min(abs(target_ms - ot), abs(target_ms - ct))
        if dist < best_dist:
            best_dist = dist
            best_idx = i

    return best_idx


def _build_fingerprint(
    trader_id: str,
    fills: List[dict],
    indicator_snapshots: List[Dict[str, Any]],
    style: str,
    positions: Optional[List[dict]],
    trader_stats: Optional[dict],
) -> Dict[str, Any]:
    """Assemble the final fingerprint JSON."""

    # Basic fill stats
    total_trades = len(fills)
    wins = sum(1 for f in fills if f["closed_pnl"] > 0)
    losses = sum(1 for f in fills if f["closed_pnl"] < 0)
    total_pnl = sum(f["closed_pnl"] for f in fills)

    # Long/short ratio
    long_count = sum(1 for f in fills if f["side"].upper() in ("B", "BUY", "LONG"))
    short_count = sum(1 for f in fills if f["side"].upper() in ("A", "SELL", "SHORT"))
    total_dir = long_count + short_count
    long_ratio = round(long_count / total_dir, 3) if total_dir > 0 else 0.5

    # Top coins
    coin_counts = defaultdict(int)
    for f in fills:
        if f["coin"]:
            coin_counts[f["coin"]] += 1
    top_coins = [c[0] for c in sorted(coin_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

    # Entry hour distribution
    entry_hour_dist = defaultdict(int)
    for f in fills:
        if f["time_ms"] > 0:
            try:
                dt = datetime.fromtimestamp(f["time_ms"] / 1000.0, tz=timezone.utc)
                entry_hour_dist[f"{dt.hour:02d}"] += 1
            except (OSError, ValueError):
                pass

    # Average hold hours (estimate from consecutive fills on same coin)
    hold_hours = _estimate_hold_hours(fills)
    avg_hold_hours = round(sum(hold_hours) / len(hold_hours), 1) if hold_hours else 0

    # Leverage (from positions or stats)
    avg_leverage = 0
    if positions:
        levs = [_safe_float(p.get("leverage", 0)) for p in positions if _safe_float(p.get("leverage", 0)) > 0]
        avg_leverage = round(sum(levs) / len(levs), 1) if levs else 0
    if avg_leverage == 0 and trader_stats:
        avg_leverage = _safe_float(trader_stats.get("avg_leverage", 0))

    # Indicator averages (from snapshots)
    avg_rsi = 50.0
    avg_volume_ratio = 1.0
    avg_atr = 0.0
    avg_price_position = 0.5
    breakout_pct = 0.0
    dip_pct = 0.0

    if indicator_snapshots:
        n = len(indicator_snapshots)
        avg_rsi = round(sum(s.get("rsi_14", 50) for s in indicator_snapshots) / n, 1)
        avg_volume_ratio = round(sum(s.get("volume_ratio_vs_20avg", 1) for s in indicator_snapshots) / n, 2)
        avg_atr = round(sum(s.get("atr_14", 0) for s in indicator_snapshots) / n, 6)
        avg_price_position = round(sum(s.get("price_position_24h", 0.5) for s in indicator_snapshots) / n, 3)
        breakout_pct = round(sum(1 for s in indicator_snapshots if s.get("is_breakout", False)) / n, 3)
        dip_pct = round(sum(1 for s in indicator_snapshots if s.get("is_dip", False)) / n, 3)

    # Funding rate stats
    funding_rates = [s["funding_rate"] for s in indicator_snapshots if "funding_rate" in s]
    avg_funding = round(sum(funding_rates) / len(funding_rates), 6) if funding_rates else None

    fingerprint = {
        "trader": trader_id,
        "style": style,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "total_fills_analyzed": total_trades,
        "indicator_snapshots_computed": len(indicator_snapshots),

        # Trade stats
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / (wins + losses), 3) if (wins + losses) > 0 else 0,
        "total_pnl": round(total_pnl, 2),
        "avg_hold_hours": avg_hold_hours,
        "preferred_leverage": avg_leverage,
        "long_ratio": long_ratio,
        "top_coins": top_coins,

        # Entry patterns
        "entry_hour_distribution": dict(entry_hour_dist),
        "avg_rsi_at_entry": avg_rsi,
        "avg_volume_ratio": avg_volume_ratio,
        "avg_atr_at_entry": avg_atr,
        "avg_price_position_24h": avg_price_position,
        "breakout_entry_pct": breakout_pct,
        "dip_entry_pct": dip_pct,

        # Funding
        "avg_funding_rate_at_entry": avg_funding,

        # Style evidence
        "style_evidence": _style_evidence(indicator_snapshots, style),
    }

    return fingerprint


def _estimate_hold_hours(fills: List[dict]) -> List[float]:
    """Estimate hold durations by pairing open/close fills on same coin."""
    holds = []
    # Group by coin
    by_coin = defaultdict(list)
    for f in fills:
        if f["coin"] and f["time_ms"] > 0:
            by_coin[f["coin"]].append(f)

    for coin, coin_fills in by_coin.items():
        sorted_fills = sorted(coin_fills, key=lambda x: x["time_ms"])
        # Pair consecutive fills as open/close
        i = 0
        while i < len(sorted_fills) - 1:
            t1 = sorted_fills[i]["time_ms"]
            t2 = sorted_fills[i + 1]["time_ms"]
            if t2 > t1:
                hours = (t2 - t1) / (1000 * 3600)
                if 0 < hours < 720:  # Sanity: less than 30 days
                    holds.append(hours)
            i += 2  # Skip in pairs

    return holds


def _style_evidence(snapshots: List[Dict[str, Any]], style: str) -> Dict[str, Any]:
    """Return evidence summary for the classified style."""
    if not snapshots:
        return {"note": "no indicator data available"}

    n = len(snapshots)
    evidence = {
        "sample_size": n,
        "breakout_entries": sum(1 for s in snapshots if s.get("is_breakout", False)),
        "dip_entries": sum(1 for s in snapshots if s.get("is_dip", False)),
        "oversold_entries": sum(1 for s in snapshots if s.get("rsi_14", 50) < 30),
        "overbought_entries": sum(1 for s in snapshots if s.get("rsi_14", 50) > 70),
        "high_volume_entries": sum(1 for s in snapshots if s.get("volume_ratio_vs_20avg", 1) > 2.0),
        "ema_bullish_entries": sum(1 for s in snapshots if s.get("ema_position") == "above"),
        "green_candle_entries": sum(1 for s in snapshots if s.get("entry_candle_green", False)),
    }

    if style == "breakout_scalper":
        evidence["key_signal"] = "Entries near 24h highs with above-average volume"
    elif style == "mean_reversion":
        evidence["key_signal"] = "Entries near support with oversold RSI"
    elif style == "momentum":
        evidence["key_signal"] = "Entries following large green candles with volume"
    elif style == "funding_arb":
        evidence["key_signal"] = "Entries correlated with extreme funding rates"
    elif style == "dip_buyer":
        evidence["key_signal"] = "Entries on red candles during uptrends (EMA9 > EMA21)"
    else:
        evidence["key_signal"] = "No single dominant pattern detected"

    return evidence


# ---------------------------------------------------------------------------
# Batch analysis: process all traders from hyperliquid/okx data
# ---------------------------------------------------------------------------

def analyze_all_traders(fetch_candles: bool = True) -> List[Dict[str, Any]]:
    """
    Load trader data from hyperliquid_traders.json and/or copy_trader_patterns.json,
    reverse-engineer each trader's strategy, and save fingerprints.
    """
    fingerprints = []

    # 1. Try Hyperliquid traders
    hl_file = os.path.join(DATA_DIR, "hyperliquid_traders.json")
    if os.path.exists(hl_file):
        try:
            with open(hl_file, "r", encoding="utf-8") as f:
                hl_data = json.load(f)

            for trader in hl_data.get("top_traders", []):
                addr = trader.get("address", "")
                if not addr:
                    continue

                # We need fills -- fetch live if we have the address
                # But if the saved data doesn't have fills, we need the full address
                # For now, use the positions and stats from saved data
                stats = trader.get("stats", {})
                positions = trader.get("positions", [])

                # Build pseudo-fills from positions (limited, but available without API call)
                fills = _positions_to_pseudo_fills(positions, addr)

                if fills:
                    print(f"[reverse-engineer] Analyzing Hyperliquid trader {addr[:12]}... ({len(fills)} fills)")
                    fp = generate_fingerprint(
                        trader_id=addr,
                        fills=fills,
                        positions=positions,
                        trader_stats=stats,
                        fetch_candles=fetch_candles,
                        max_trades_to_analyze=20,
                    )
                    fp["source"] = "hyperliquid"
                    fp["display_name"] = trader.get("display_name", addr[:12])
                    fingerprints.append(fp)

        except (json.JSONDecodeError, OSError) as e:
            print(f"[reverse-engineer] Error reading {hl_file}: {e}")

    # 2. Try OKX copy traders
    ct_file = os.path.join(DATA_DIR, "copy_trader_patterns.json")
    if os.path.exists(ct_file):
        try:
            with open(ct_file, "r", encoding="utf-8") as f:
                ct_data = json.load(f)

            for trader in ct_data.get("trader_patterns", []):
                code = trader.get("uniqueCode", "")
                if not code:
                    continue

                patterns = trader.get("patterns", {})
                positions = trader.get("current_positions", [])

                # Build pseudo-fills from positions
                fills = _okx_positions_to_fills(positions, patterns)

                if fills:
                    print(f"[reverse-engineer] Analyzing OKX trader {trader.get('nickName', code)}... ({len(fills)} fills)")
                    fp = generate_fingerprint(
                        trader_id=code,
                        fills=fills,
                        positions=None,
                        trader_stats={
                            "avg_leverage": patterns.get("avg_leverage", 0),
                        },
                        fetch_candles=fetch_candles,
                        max_trades_to_analyze=20,
                    )
                    fp["source"] = "okx"
                    fp["display_name"] = trader.get("nickName", code)
                    fingerprints.append(fp)

        except (json.JSONDecodeError, OSError) as e:
            print(f"[reverse-engineer] Error reading {ct_file}: {e}")

    # Save all fingerprints
    if fingerprints:
        os.makedirs(DATA_DIR, exist_ok=True)
        output = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_traders": len(fingerprints),
            "fingerprints": fingerprints,
        }
        with open(FINGERPRINTS_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)
        print(f"[reverse-engineer] Saved {len(fingerprints)} fingerprints to {FINGERPRINTS_FILE}")

    return fingerprints


def _positions_to_pseudo_fills(positions: List[dict], trader_addr: str) -> List[dict]:
    """Convert Hyperliquid open positions to pseudo-fills for analysis."""
    fills = []
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    for pos in positions:
        coin = pos.get("coin", "")
        entry_px = _safe_float(pos.get("entry_price", 0))
        direction = pos.get("direction", "LONG")

        if coin and entry_px > 0:
            # Estimate entry time: assume positions are recent (within 24h)
            # This is a rough heuristic; real fills would be better
            fills.append({
                "coin": coin,
                "price": entry_px,
                "size": _safe_float(pos.get("size", 1)),
                "side": "B" if direction == "LONG" else "A",
                "time_ms": now_ms - 3600000 * 4,  # Assume 4h ago
                "closed_pnl": 0,
            })

    return fills


def _okx_positions_to_fills(positions: List[dict], patterns: dict) -> List[dict]:
    """Convert OKX current positions to pseudo-fills."""
    fills = []
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    for pos in positions:
        inst_id = pos.get("instId", "")
        coin = inst_id.replace("-SWAP", "").split("-")[0] if inst_id else ""
        entry_px = _safe_float(pos.get("openAvgPx", 0))
        side = pos.get("posSide", "").upper()

        if coin and entry_px > 0:
            fills.append({
                "coin": coin,
                "price": entry_px,
                "size": 1,
                "side": side if side else "LONG",
                "time_ms": now_ms - 3600000 * 4,
                "closed_pnl": 0,
            })

    return fills


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """Run the strategy reverse-engineer as a standalone script."""
    import argparse

    parser = argparse.ArgumentParser(description="Strategy Reverse-Engineer")
    parser.add_argument("--no-candles", action="store_true",
                        help="Skip candle fetching (dry run / syntax check)")
    parser.add_argument("--trader", type=str, default=None,
                        help="Analyze a single trader by address/code")
    args = parser.parse_args()

    fetch = not args.no_candles

    if args.trader:
        # Try to load fills for this specific trader
        # Check Hyperliquid data first
        hl_file = os.path.join(DATA_DIR, "hyperliquid_traders.json")
        fills = []
        positions = []
        stats = {}

        if os.path.exists(hl_file):
            with open(hl_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for t in data.get("top_traders", []):
                if args.trader.lower() in t.get("address", "").lower():
                    positions = t.get("positions", [])
                    stats = t.get("stats", {})
                    fills = _positions_to_pseudo_fills(positions, args.trader)
                    break

        if not fills:
            print(f"No data found for trader {args.trader}")
            return

        fp = generate_fingerprint(args.trader, fills, positions, stats,
                                  fetch_candles=fetch)
        print(json.dumps(fp, indent=2, default=str))
    else:
        fingerprints = analyze_all_traders(fetch_candles=fetch)
        print(f"\nAnalyzed {len(fingerprints)} traders")
        for fp in fingerprints:
            style = fp.get("style", "unknown")
            name = fp.get("display_name", fp.get("trader", "?")[:12])
            coins = ", ".join(fp.get("top_coins", [])[:3])
            rsi = fp.get("avg_rsi_at_entry", 0)
            vol = fp.get("avg_volume_ratio", 0)
            print(f"  {name:20s} | style={style:20s} | RSI={rsi:5.1f} | vol_ratio={vol:.2f} | coins={coins}")


if __name__ == "__main__":
    main()
