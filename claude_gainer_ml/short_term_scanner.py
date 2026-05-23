#!/usr/bin/env python3
"""
CLAUDE GAINER — Short-Term Crypto Predictor v1.0
=================================================
Extends Claude Gainer ML with 1h/4h prediction modes.
40 features (30 original + 10 from crypto_ml_edge: funding, F&G, ATR, S/R).
RF + XGBoost ensemble with self-learning feedback loop.

Usage:
    python -m claude_gainer_ml.short_term_scanner [--timeframe 1h|4h] [--pairs 20] [--resolve]
"""

import os
import sys
import json
import math
import time
import uuid
import logging
import argparse
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR.parent
MODEL_DIR = BASE_DIR / "models" / "short_term"
DATA_DIR = BASE_DIR / "data"
TRACKER_DIR = BASE_DIR / "tracker"
PICKS_FILE = TRACKER_DIR / "short_term_picks.json"
ACTIVE_PICKS_FILE = TRACKER_DIR / "short_term_active.json"
WEIGHTS_FILE = TRACKER_DIR / "st_strategy_weights.json"

for d in [MODEL_DIR, DATA_DIR, TRACKER_DIR]:
    d.mkdir(parents=True, exist_ok=True)

SOURCE_SYSTEM = "CLAUDE_GAINER_ST"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("claude_gainer_st")

# ── Timeframe Configs ────────────────────────────────────────────────────
TIMEFRAME_CONFIG = {
    "1h": {
        "interval": "1h", "bars_needed": 200,
        "tp_atr_mult": 2.5, "sl_atr_mult": 1.5,
        "max_hold_bars": 12,  # 12 hours
        "label_threshold": 0.015,  # +1.5% for label=1
        "lookback_24h": 24, "lookback_7d": 168,
    },
    "4h": {
        "interval": "4h", "bars_needed": 100,
        "tp_atr_mult": 3.5, "sl_atr_mult": 2.0,
        "max_hold_bars": 8,  # 32 hours
        "label_threshold": 0.03,  # +3.0% for label=1
        "lookback_24h": 6, "lookback_7d": 42,
    },
}

# ── Database ─────────────────────────────────────────────────────────────
DB_HOST = os.environ.get('AUDIT_DB_HOST', 'mysql.50webs.com')
DB_PORT = int(os.environ.get('AUDIT_DB_PORT', '3306'))
DB_USER = os.environ.get('AUDIT_DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.environ.get('AUDIT_DB_PASS', 'password')
DB_NAME = os.environ.get('AUDIT_DB_NAME', 'ejaguiar1_stocks')

# ── Feature Columns (40 total) ──────────────────────────────────────────
FEATURE_COLS_30 = [
    "vol_mcap_ratio", "vol_change_24h", "vol_change_12h",
    "price_momentum_7d", "price_momentum_3d", "price_momentum_1d",
    "rsi_14", "rsi_slope", "bb_width", "bb_percentb",
    "consolidation_range", "consecutive_green", "momentum_ignition",
    "obv_divergence", "distance_from_ath_pct", "distance_from_atl_pct",
    "mcap_tier", "price_compression", "relative_volume_spike",
    "fear_greed_proxy",
    "is_yesterday_gainer", "yesterday_gain_pct",
    "sector_momentum", "sector_relative_strength",
    "hourly_volatility", "volume_acceleration",
    "high_low_range_24h", "green_bar_ratio_24h",
    "max_hourly_gain_24h", "multi_day_gainer",
]

FEATURE_COLS_NEW = [
    "funding_rate", "funding_zscore", "funding_momentum",
    "fear_greed_current", "fear_greed_7d_avg", "fear_greed_momentum",
    "atr_pct", "vol_percentile", "sr_dist_high", "sr_dist_low",
]

ALL_FEATURE_COLS = FEATURE_COLS_30 + FEATURE_COLS_NEW

# ── Binance mirrors ─────────────────────────────────────────────────────
BINANCE_MIRRORS = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://api2.binance.com", "https://api3.binance.com",
    "https://data-api.binance.vision",
]
_mirror_idx = 0
_binance_blocked = False

# ── Data Fetching ────────────────────────────────────────────────────────

def _fetch_json(url, timeout=10):
    """Fetch JSON from URL with error handling."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ClaudeGainerST/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def fetch_binance_klines(symbol, interval="1h", limit=200):
    """Fetch klines from Binance with mirror rotation."""
    global _mirror_idx, _binance_blocked
    if _binance_blocked:
        return []
    for attempt in range(len(BINANCE_MIRRORS)):
        base = BINANCE_MIRRORS[(_mirror_idx + attempt) % len(BINANCE_MIRRORS)]
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 0:
            _mirror_idx = (_mirror_idx + attempt) % len(BINANCE_MIRRORS)
            return [[float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]),
                     int(k[0])] for k in data]  # [open, high, low, close, vol, timestamp]
    _binance_blocked = True
    return []


def fetch_coingecko_klines(symbol, interval="1h", limit=200):
    """CoinGecko fallback for klines."""
    coin_map = {"BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "BNBUSDT": "binancecoin",
                "SOLUSDT": "solana", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
                "DOGEUSDT": "dogecoin", "DOTUSDT": "polkadot-new",
                "AVAXUSDT": "avalanche-2", "LINKUSDT": "chainlink",
                "LTCUSDT": "litecoin", "TRXUSDT": "tron", "MATICUSDT": "matic-network",
                "ATOMUSDT": "cosmos", "NEARUSDT": "near", "UNIUSDT": "uniswap",
                "APTUSDT": "aptos", "OPUSDT": "optimism", "ARBUSDT": "arbitrum",
                "SUIUSDT": "sui",
                "ETHFIUSDT": "ether-fi", "QNTUSDT": "quant-network",
                "DEXEUSDT": "dexe", "ENJUSDT": "enjincoin",
                "THEUSDT": "thena", "PIXELUSDT": "pixels",
                "ANKRUSDT": "ankr", "HOTUSDT": "holotoken",
                "SAHARAUSDT": "sahara-ai"}
    coin_id = coin_map.get(symbol)
    if not coin_id:
        return []
    days = max(2, limit // 24) if interval == "1h" else max(7, limit // 6)
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"
    data = _fetch_json(url)
    if not data or not isinstance(data, list):
        return []
    return [[d[1], d[2], d[3], d[4], 0, d[0]] for d in data[-limit:]]


def get_klines(symbol, interval="1h", limit=200):
    """Get klines with Binance → CoinGecko fallback."""
    klines = fetch_binance_klines(symbol, interval, limit)
    if not klines:
        klines = fetch_coingecko_klines(symbol, interval, limit)
    return klines


def get_top_pairs(limit=20):
    """Get top N USDT pairs by volume from Binance."""
    data = _fetch_json("https://api.binance.com/api/v3/ticker/24hr")
    if not data:
        # Hardcoded fallback
        return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
                "LTCUSDT", "TRXUSDT", "MATICUSDT", "ATOMUSDT", "NEARUSDT",
                "UNIUSDT", "APTUSDT", "OPUSDT", "ARBUSDT", "SUIUSDT"][:limit]
    usdt = [t for t in data if t["symbol"].endswith("USDT")
            and float(t.get("quoteVolume", 0)) > 0
            and not any(x in t["symbol"] for x in ["UP", "DOWN", "BULL", "BEAR"])]
    usdt.sort(key=lambda t: float(t.get("quoteVolume", 0)), reverse=True)
    return [t["symbol"] for t in usdt[:limit]]


def fetch_funding_rate(symbol):
    """Fetch current funding rate from Binance futures."""
    url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
    data = _fetch_json(url)
    if data and "lastFundingRate" in data:
        return float(data["lastFundingRate"])
    return None


_fg_cache = {"value": None, "values_7d": None, "ts": 0}

def fetch_fear_greed():
    """Fetch Fear & Greed index with caching + CoinGecko BTC proxy fallback."""
    if time.time() - _fg_cache["ts"] < 300 and _fg_cache["value"] is not None:
        return _fg_cache["value"], _fg_cache["values_7d"]

    # Source 1: alternative.me (primary)
    url = "https://api.alternative.me/fng/?limit=7&format=json"
    data = _fetch_json(url)
    if data and "data" in data:
        values = [int(d["value"]) for d in data["data"]]
        _fg_cache["value"] = values[0]
        _fg_cache["values_7d"] = values
        _fg_cache["ts"] = time.time()
        return values[0], values

    # Source 2: CoinGecko BTC 24h change proxy (heuristic: -10%≈F&G 10, +10%≈F&G 90)
    try:
        import requests as _req
        resp = _req.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=8,
        )
        if resp.ok:
            change = float(resp.json()["bitcoin"]["usd_24h_change"])
            proxy = int(max(5, min(95, 50 + change * 4)))
            print(f"  [F&G fallback] CoinGecko BTC proxy: {proxy} (BTC 24h={change:+.1f}%)")
            _fg_cache["value"] = proxy
            _fg_cache["values_7d"] = [proxy] * 7
            _fg_cache["ts"] = time.time()
            return proxy, [proxy] * 7
    except Exception:
        pass

    return 50, [50] * 7  # neutral default


# ── Technical Indicators ─────────────────────────────────────────────────

def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return [50.0] * len(closes)
    rsi_vals = [50.0] * period
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas[:period]]
    losses = [abs(min(d, 0)) for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period, len(deltas)):
        delta = deltas[i]
        avg_gain = (avg_gain * (period - 1) + max(delta, 0)) / period
        avg_loss = (avg_loss * (period - 1) + abs(min(delta, 0))) / period
        if avg_loss == 0:
            rsi_vals.append(100.0)
        else:
            rsi_vals.append(100.0 - (100.0 / (1.0 + avg_gain / avg_loss)))
    while len(rsi_vals) < len(closes):
        rsi_vals.insert(0, 50.0)
    return rsi_vals


def compute_bollinger(closes, period=20, num_std=2):
    widths, pctbs = [], []
    for i in range(len(closes)):
        if i < period - 1:
            widths.append(0.0)
            pctbs.append(0.5)
            continue
        window = closes[i - period + 1: i + 1]
        sma = sum(window) / period
        std = (sum((x - sma) ** 2 for x in window) / period) ** 0.5
        upper = sma + num_std * std
        lower = sma - num_std * std
        widths.append((upper - lower) / sma if sma > 0 else 0)
        pctbs.append(max(0, min(1, (closes[i] - lower) / (upper - lower)
                                if (upper - lower) > 0 else 0.5)))
    return widths, pctbs


def compute_obv(closes, volumes):
    obv = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    return obv


def compute_atr(highs, lows, closes, period=14):
    """Average True Range."""
    if len(closes) < 2:
        return [0.0]
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    atr = [sum(trs[:period]) / period if len(trs) >= period else sum(trs) / max(len(trs), 1)]
    for i in range(period, len(trs)):
        atr.append((atr[-1] * (period - 1) + trs[i]) / period)
    while len(atr) < len(closes):
        atr.insert(0, atr[0] if atr else 0)
    return atr


def compute_ema(values, period):
    if not values:
        return []
    multiplier = 2 / (period + 1)
    ema = [values[0]]
    for v in values[1:]:
        ema.append(v * multiplier + ema[-1] * (1 - multiplier))
    return ema


# ── Feature Engineering (40 features) ────────────────────────────────────

def compute_features(klines, timeframe="1h", funding_rate=None, fg_current=50, fg_7d=None):
    """Compute 40 features from kline data + external signals.

    Args:
        klines: list of [open, high, low, close, volume, timestamp]
        timeframe: "1h" or "4h"
        funding_rate: current funding rate (float or None)
        fg_current: Fear & Greed index (0-100)
        fg_7d: list of 7 daily F&G values

    Returns: dict of 40 features or None if insufficient data
    """
    cfg = TIMEFRAME_CONFIG[timeframe]
    n = len(klines)
    if n < 50:
        return None

    opens = [k[0] for k in klines]
    highs = [k[1] for k in klines]
    lows = [k[2] for k in klines]
    closes = [k[3] for k in klines]
    volumes = [k[4] for k in klines]

    i = n - 1
    c = closes[i]
    if c <= 0:
        return None

    lb_24 = cfg["lookback_24h"]
    lb_7d = cfg["lookback_7d"]
    lb_12 = lb_24 // 2
    lb_72 = lb_24 * 3

    rsi_vals = compute_rsi(closes, 14)
    bb_widths, bb_pctbs = compute_bollinger(closes, min(20, n), 2)
    obv_vals = compute_obv(closes, volumes)
    atr_vals = compute_atr(highs, lows, closes, 14)

    # ── Original 30 features ──

    # 1. vol_mcap_ratio (approximate from volume)
    vol_period = sum(volumes[max(0, i - lb_24 + 1):i + 1])
    mcap_est = c * vol_period * 10  # rough estimate
    vol_mcap_ratio = vol_period / max(mcap_est, 1)

    # 2-3. Volume changes
    avg_vol_base = sum(volumes[max(0, i - lb_7d):max(0, i - lb_24)]) / max(lb_7d - lb_24, 1) * lb_24
    vol_change_24h = vol_period / avg_vol_base if avg_vol_base > 0 else 1.0
    v12a = sum(volumes[max(0, i - lb_12 + 1):i + 1])
    v12b = sum(volumes[max(0, i - lb_24 + 1):max(0, i - lb_12 + 1)])
    vol_change_12h = v12a / v12b if v12b > 0 else 1.0

    # 4-6. Momentum
    c_7d = closes[max(0, i - lb_7d)]
    c_3d = closes[max(0, i - lb_72)]
    c_1d = closes[max(0, i - lb_24)]
    pm7d = (c - c_7d) / c_7d * 100 if c_7d > 0 else 0
    pm3d = (c - c_3d) / c_3d * 100 if c_3d > 0 else 0
    pm1d = (c - c_1d) / c_1d * 100 if c_1d > 0 else 0

    # 7-8. RSI
    rsi_14 = rsi_vals[i]
    rsi_slope = rsi_vals[i] - rsi_vals[max(0, i - 3)]

    # 9-10. Bollinger
    bb_width = bb_widths[i]
    bb_percentb = bb_pctbs[i]

    # 11. Consolidation range
    ranges = [(highs[j] - lows[j]) / closes[j] for j in range(max(0, i - lb_24 + 1), i + 1) if closes[j] > 0]
    consolidation_range = sum(ranges) / len(ranges) if ranges else 0

    # 12. Consecutive green
    consec_green = 0
    for j in range(i, max(i - 48, -1), -1):
        if closes[j] > opens[j]:
            consec_green += 1
        else:
            break

    # 13. Momentum ignition
    momentum_ignition = 0
    if consec_green >= 3:
        if all(volumes[i - k] > volumes[i - k - 1] for k in range(min(3, i)) if i - k - 1 >= 0):
            momentum_ignition = 1

    # 14. OBV divergence
    obv_trend = obv_vals[i] - obv_vals[max(0, i - lb_24)]
    price_trend = closes[i] - closes[max(0, i - lb_24)]
    obv_divergence = 1 if (obv_trend > 0 and price_trend < 0) or (obv_trend < 0 and price_trend > 0) else 0

    # 15-16. ATH/ATL (use local extremes)
    local_high = max(highs[max(0, i - lb_7d):i + 1])
    local_low = min(lows[max(0, i - lb_7d):i + 1])
    dist_ath = (local_high - c) / local_high * 100 if local_high > 0 else 0
    dist_atl = (c - local_low) / local_low * 100 if local_low > 0 else 0

    # 17. Market cap tier (estimate from volume)
    mcap_tier = math.log10(max(mcap_est, 1)) / 12.0

    # 18. Price compression
    price_compression = 0
    if i >= 3:
        dr = [(highs[j] - lows[j]) / closes[j] for j in range(i - 2, i + 1) if closes[j] > 0]
        if len(dr) >= 3 and all(dr[k] < dr[k - 1] for k in range(1, len(dr))):
            price_compression = 1

    # 19. Relative volume spike
    relative_volume_spike = 1 if vol_change_24h > 3.0 else 0

    # 20. Fear/greed proxy
    vol_dir = 1 if vol_change_24h > 1.2 else (-1 if vol_change_24h < 0.8 else 0)
    fear_greed_proxy = (rsi_14 / 100.0) * 0.6 + (vol_dir + 1) / 2 * 0.4

    # 21-22. Yesterday gainer (not available in short-term mode)
    is_yesterday_gainer = 0
    yesterday_gain_pct = 0

    # 23-24. Sector (simplified)
    sector_momentum = pm1d * 0.5  # proxy
    sector_relative_strength = 0

    # 25. Hourly volatility
    h_returns = [(closes[j] - closes[j - 1]) / closes[j - 1]
                 for j in range(max(1, i - lb_24 + 1), i + 1) if closes[j - 1] > 0]
    hourly_volatility = float(np.std(h_returns)) if len(h_returns) > 2 else 0

    # 26. Volume acceleration
    lb_6 = max(1, lb_24 // 4)
    v6r = sum(volumes[max(0, i - lb_6 + 1):i + 1]) / lb_6
    v6p = sum(volumes[max(0, i - 2 * lb_6 + 1):max(0, i - lb_6 + 1)]) / lb_6 if i >= 2 * lb_6 else v6r
    volume_acceleration = v6r / v6p if v6p > 0 else 1.0

    # 27. High-low range
    h24 = max(highs[max(0, i - lb_24 + 1):i + 1])
    l24 = min(lows[max(0, i - lb_24 + 1):i + 1])
    high_low_range = (h24 - l24) / c if c > 0 else 0

    # 28. Green bar ratio
    green_count = sum(1 for j in range(max(0, i - lb_24 + 1), i + 1) if closes[j] > opens[j])
    green_bar_ratio = green_count / min(lb_24, i + 1)

    # 29. Max hourly gain
    max_hgain = 0
    for j in range(max(1, i - lb_24 + 1), i + 1):
        if closes[j - 1] > 0:
            g = (closes[j] - closes[j - 1]) / closes[j - 1]
            if g > max_hgain:
                max_hgain = g

    # 30. Multi-day gainer
    multi_day_gainer = 0
    if i >= 3 * lb_24:
        d1 = (closes[i] - closes[i - lb_24]) / closes[i - lb_24] if closes[i - lb_24] > 0 else 0
        d2 = (closes[i - lb_24] - closes[i - 2 * lb_24]) / closes[i - 2 * lb_24] if closes[i - 2 * lb_24] > 0 else 0
        d3 = (closes[i - 2 * lb_24] - closes[i - 3 * lb_24]) / closes[i - 3 * lb_24] if closes[i - 3 * lb_24] > 0 else 0
        if d1 > 0.01 and d2 > 0.01 and d3 > 0.01:
            multi_day_gainer = 1

    # ── New 10 features (from crypto_ml_edge) ──

    # 31-33. Funding rate features
    fr = funding_rate if funding_rate is not None else 0.0
    funding_zscore = 0.0  # Would need rolling history; use proxy
    funding_momentum = 0.0
    if funding_rate is not None:
        # Z-score proxy: funding rate / typical range (0.01%)
        funding_zscore = fr / 0.0001 if abs(fr) > 0 else 0
        funding_momentum = fr  # Single-point momentum proxy

    # 34-36. Fear & Greed features
    fg_7d = fg_7d or [fg_current] * 7
    fg_7d_avg = sum(fg_7d) / len(fg_7d)
    fg_momentum = fg_current - fg_7d_avg

    # 37. ATR as % of close
    atr_pct = atr_vals[i] / c * 100 if c > 0 else 0

    # 38. Volume percentile (rank in 90-bar window)
    vol_window = volumes[max(0, i - 89):i + 1]
    if len(vol_window) > 1:
        vol_percentile = sum(1 for v in vol_window if v <= volumes[i]) / len(vol_window)
    else:
        vol_percentile = 0.5

    # 39-40. Support/Resistance distance
    swing_high = max(highs[max(0, i - 20):i])
    swing_low = min(lows[max(0, i - 20):i])
    sr_dist_high = (swing_high - c) / c * 100 if c > 0 else 0
    sr_dist_low = (c - swing_low) / c * 100 if c > 0 else 0

    return {
        # Original 30
        "vol_mcap_ratio": round(vol_mcap_ratio, 6),
        "vol_change_24h": round(vol_change_24h, 4),
        "vol_change_12h": round(vol_change_12h, 4),
        "price_momentum_7d": round(pm7d, 4),
        "price_momentum_3d": round(pm3d, 4),
        "price_momentum_1d": round(pm1d, 4),
        "rsi_14": round(rsi_14, 2),
        "rsi_slope": round(rsi_slope, 2),
        "bb_width": round(bb_width, 6),
        "bb_percentb": round(bb_percentb, 4),
        "consolidation_range": round(consolidation_range, 6),
        "consecutive_green": consec_green,
        "momentum_ignition": momentum_ignition,
        "obv_divergence": obv_divergence,
        "distance_from_ath_pct": round(dist_ath, 2),
        "distance_from_atl_pct": round(min(dist_atl, 100000), 2),
        "mcap_tier": round(mcap_tier, 4),
        "price_compression": price_compression,
        "relative_volume_spike": relative_volume_spike,
        "fear_greed_proxy": round(fear_greed_proxy, 4),
        "is_yesterday_gainer": is_yesterday_gainer,
        "yesterday_gain_pct": yesterday_gain_pct,
        "sector_momentum": round(sector_momentum, 4),
        "sector_relative_strength": sector_relative_strength,
        "hourly_volatility": round(hourly_volatility, 6),
        "volume_acceleration": round(volume_acceleration, 4),
        "high_low_range_24h": round(high_low_range, 6),
        "green_bar_ratio_24h": round(green_bar_ratio, 4),
        "max_hourly_gain_24h": round(max_hgain * 100, 4),
        "multi_day_gainer": multi_day_gainer,
        # New 10
        "funding_rate": round(fr, 8),
        "funding_zscore": round(funding_zscore, 4),
        "funding_momentum": round(funding_momentum, 8),
        "fear_greed_current": fg_current,
        "fear_greed_7d_avg": round(fg_7d_avg, 2),
        "fear_greed_momentum": round(fg_momentum, 2),
        "atr_pct": round(atr_pct, 4),
        "vol_percentile": round(vol_percentile, 4),
        "sr_dist_high": round(sr_dist_high, 4),
        "sr_dist_low": round(sr_dist_low, 4),
        # Extra metadata (not features, for TP/SL calc)
        "_atr": atr_vals[i],
        "_close": c,
    }


# ── Rule-Based Signal Engine (no trained model needed) ───────────────────

def generate_signals_rule_based(features, symbol, timeframe):
    """Generate trading signals using rule-based strategies on 40 features.
    This runs immediately — no trained model required. As picks resolve,
    the self-learner trains an ML model that replaces/augments this."""
    signals = []
    f = features
    c = f["_close"]
    atr = f["_atr"]
    cfg = TIMEFRAME_CONFIG[timeframe]

    # Strategy 1: RSI Oversold + Volume Spike
    if f["rsi_14"] < 30 and f["vol_change_24h"] > 1.5:
        conf = 65 + min((30 - f["rsi_14"]) * 0.5, 10) + min(f["vol_change_24h"] * 3, 10)
        tp = c + atr * cfg["tp_atr_mult"]
        sl = c - atr * cfg["sl_atr_mult"]
        signals.append({
            "direction": "LONG", "strategy": "rsi_vol_bounce",
            "confidence": min(conf, 95),
            "reason": f"RSI {f['rsi_14']:.1f} oversold + volume {f['vol_change_24h']:.1f}x",
            "tp": tp, "sl": sl,
        })

    # Strategy 2: Momentum Ignition + Compression
    if f["momentum_ignition"] == 1 and f["price_compression"] == 1:
        conf = 70 + min(f["consecutive_green"] * 2, 10)
        tp = c + atr * cfg["tp_atr_mult"]
        sl = c - atr * cfg["sl_atr_mult"]
        signals.append({
            "direction": "LONG", "strategy": "momentum_compression",
            "confidence": min(conf, 95),
            "reason": f"Momentum ignition + price compression. {f['consecutive_green']} green bars.",
            "tp": tp, "sl": sl,
        })

    # Strategy 3: Funding Rate Reversal (from NOW.py, proven 71% WR)
    if f["funding_rate"] < -0.0001 and f["rsi_14"] < 45:
        conf = 68 + min(abs(f["funding_rate"]) * 50000, 15)
        tp = c + atr * cfg["tp_atr_mult"]
        sl = c - atr * cfg["sl_atr_mult"]
        signals.append({
            "direction": "LONG", "strategy": "funding_reversal",
            "confidence": min(conf, 95),
            "reason": f"Negative funding ({f['funding_rate']:.4%}) + RSI {f['rsi_14']:.1f}. Squeeze potential.",
            "tp": tp, "sl": sl,
        })

    # Strategy 4: Fear & Greed Extreme + RSI Bounce
    # 2026 audit: F&G < 25 fires <5% of the time; relaxed to < 30 for more coverage
    if f["fear_greed_current"] < 30 and f["rsi_14"] < 40 and f["price_momentum_1d"] < -2:
        conf = 67 + min((30 - f["fear_greed_current"]) * 0.5, 10)
        tp = c + atr * cfg["tp_atr_mult"] * 1.2  # Wider TP for contrarian
        sl = c - atr * cfg["sl_atr_mult"]
        signals.append({
            "direction": "LONG", "strategy": "fear_greed_contrarian",
            "confidence": min(conf, 95),
            "reason": f"F&G {f['fear_greed_current']} (extreme fear) + RSI {f['rsi_14']:.1f} + dip {f['price_momentum_1d']:.1f}%",
            "tp": tp, "sl": sl,
        })

    # Strategy 5: Bollinger Squeeze + Volume Acceleration
    if f["bb_width"] < 0.02 and f["bb_percentb"] > 0.8 and f["volume_acceleration"] > 1.5:
        conf = 64 + min(f["volume_acceleration"] * 5, 15)
        tp = c + atr * cfg["tp_atr_mult"]
        sl = c - atr * cfg["sl_atr_mult"]
        signals.append({
            "direction": "LONG", "strategy": "bb_squeeze_expansion",
            "confidence": min(conf, 95),
            "reason": f"BB squeeze (width {f['bb_width']:.4f}) + vol acceleration {f['volume_acceleration']:.1f}x",
            "tp": tp, "sl": sl,
        })

    # Strategy 6: Multi-Day Momentum + Volume
    if f["multi_day_gainer"] == 1 and f["vol_change_24h"] > 1.2:
        conf = 63 + min(f["price_momentum_3d"], 15)
        tp = c + atr * cfg["tp_atr_mult"]
        sl = c - atr * cfg["sl_atr_mult"]
        signals.append({
            "direction": "LONG", "strategy": "multi_day_momentum",
            "confidence": min(conf, 95),
            "reason": f"3-day positive streak + volume {f['vol_change_24h']:.1f}x. Momentum {f['price_momentum_3d']:.1f}%",
            "tp": tp, "sl": sl,
        })

    # Strategy 7: OBV Divergence + Support Bounce
    if f["obv_divergence"] == 1 and f["sr_dist_low"] < 2.0 and f["rsi_14"] < 45:
        conf = 62 + min(f["vol_percentile"] * 10, 10)
        tp = c + atr * cfg["tp_atr_mult"]
        sl = c - atr * cfg["sl_atr_mult"]
        signals.append({
            "direction": "LONG", "strategy": "obv_support_divergence",
            "confidence": min(conf, 95),
            "reason": f"OBV divergence near support ({f['sr_dist_low']:.1f}% from swing low). RSI {f['rsi_14']:.1f}.",
            "tp": tp, "sl": sl,
        })

    # Strategy 8: ATR Breakout (high volatility expansion)
    # 2026 audit: triple-AND too restrictive → relax ATR 3.0→2.5, volume 2.0→1.8
    if f["atr_pct"] > 2.5 and f["price_momentum_1d"] > 1.0 and f["vol_change_24h"] > 1.8:
        conf = 60 + min(f["atr_pct"] * 2, 15)
        tp = c + atr * cfg["tp_atr_mult"] * 1.3
        sl = c - atr * cfg["sl_atr_mult"]
        signals.append({
            "direction": "LONG", "strategy": "atr_vol_breakout",
            "confidence": min(conf, 95),
            "reason": f"ATR expansion {f['atr_pct']:.1f}% + volume {f['vol_change_24h']:.1f}x + momentum +{f['price_momentum_1d']:.1f}%",
            "tp": tp, "sl": sl,
        })

    # Strategy 9: RSI Overbought Reversal (SHORT)
    if f["rsi_14"] > 75 and f["funding_rate"] is not None and f["funding_rate"] > 0.0005:
        conf = 62 + min((f["rsi_14"] - 70) * 0.5, 10) + min(f["funding_rate"] * 10000, 10)
        tp = c - atr * cfg["tp_atr_mult"]
        sl = c + atr * cfg["sl_atr_mult"]
        signals.append({
            "direction": "SHORT", "strategy": "overbought_funding_short",
            "confidence": min(conf, 95),
            "reason": f"RSI {f['rsi_14']:.1f} overbought + positive funding ({f['funding_rate']:.4%}). Overheated.",
            "tp": tp, "sl": sl,
        })

    # Strategy 10: MACD + RSI Confluence (via momentum proxy)
    if f["price_momentum_1d"] > 0 and f["rsi_14"] > 35 and f["rsi_14"] < 60 and f["rsi_slope"] > 2:
        if f["vol_change_24h"] > 1.0 and f["sr_dist_high"] > 2:
            conf = 60 + min(f["rsi_slope"] * 2, 10) + min(f["vol_change_24h"] * 3, 10)
            tp = c + atr * cfg["tp_atr_mult"]
            sl = c - atr * cfg["sl_atr_mult"]
            signals.append({
                "direction": "LONG", "strategy": "rsi_momentum_confluence",
                "confidence": min(conf, 95),
                "reason": f"RSI recovering ({f['rsi_14']:.1f}, slope +{f['rsi_slope']:.1f}) + momentum +{f['price_momentum_1d']:.1f}%",
                "tp": tp, "sl": sl,
            })

    return signals


# ── ML Model (loads if trained, otherwise rule-based only) ───────────────

def load_ml_model(timeframe):
    """Load trained ML model for this timeframe, if available."""
    try:
        import joblib
        model_path = MODEL_DIR / f"st_{timeframe}_ensemble.joblib"
        scaler_path = MODEL_DIR / f"st_{timeframe}_scaler.joblib"
        meta_path = MODEL_DIR / f"st_{timeframe}_meta.json"
        if not model_path.exists():
            return None, None, None
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path) if scaler_path.exists() else None
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        log.info(f"ML model loaded for {timeframe}: v{meta.get('version', '?')}")
        return model, scaler, meta
    except Exception as e:
        log.debug(f"No ML model for {timeframe}: {e}")
        return None, None, None


def ml_predict(features, model, scaler, meta):
    """Run ML prediction if model is available."""
    if model is None:
        return None
    feature_names = meta.get("feature_names", ALL_FEATURE_COLS)
    vec = np.array([[features.get(col, 0) for col in feature_names]])
    vec = np.nan_to_num(vec, nan=0.0, posinf=1e6, neginf=-1e6)
    if scaler:
        vec = scaler.transform(vec)
    try:
        proba = model.predict_proba(vec)[0][1]
        return float(proba)
    except Exception:
        return None


# ── Self-Learning: Adaptive Weights ──────────────────────────────────────

_strategy_weights = {}

def load_strategy_weights():
    """Load strategy performance weights from local JSON (updated after resolution)."""
    global _strategy_weights
    if WEIGHTS_FILE.exists():
        try:
            data = json.loads(WEIGHTS_FILE.read_text())
            _strategy_weights = data
            log.info(f"Strategy weights loaded: {_strategy_weights}")
        except Exception:
            pass


def save_strategy_weights():
    """Save strategy weights to JSON."""
    WEIGHTS_FILE.write_text(json.dumps(_strategy_weights, indent=2), encoding="utf-8")


def update_strategy_weights(picks_history):
    """Update strategy weights based on resolved picks.
    Winners get boosted (up to 1.5x), losers penalized (down to 0.5x)."""
    global _strategy_weights
    MIN_PICKS = 5

    strategy_stats = {}
    for p in picks_history:
        if p.get("status") not in ("TP_HIT", "SL_HIT", "EXPIRED"):
            continue
        strat = p.get("strategy", "unknown")
        if strat not in strategy_stats:
            strategy_stats[strat] = {"wins": 0, "losses": 0, "total": 0}
        strategy_stats[strat]["total"] += 1
        if p["status"] == "TP_HIT":
            strategy_stats[strat]["wins"] += 1
        else:
            strategy_stats[strat]["losses"] += 1

    for strat, stats in strategy_stats.items():
        if stats["total"] < MIN_PICKS:
            _strategy_weights[strat] = 1.0
            continue
        wr = stats["wins"] / stats["total"]
        weight = 0.5 + wr  # Range: 0.5 (0% WR) to 1.5 (100% WR)
        _strategy_weights[strat] = round(max(0.5, min(1.5, weight)), 3)

    save_strategy_weights()
    log.info(f"Strategy weights updated: {_strategy_weights}")


# ── Database ─────────────────────────────────────────────────────────────

def get_db():
    try:
        import pymysql
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import pymysql
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                           password=DB_PASS, database=DB_NAME,
                           charset='utf8mb4', connect_timeout=15, autocommit=True)


def insert_picks_db(run_id, scan_time, picks):
    """Insert picks into now_history table with CLAUDE_GAINER_ST source."""
    try:
        conn = get_db()
        cur = conn.cursor()
        inserted = 0
        for p in picks:
            cur.execute("""
                INSERT INTO now_history (run_id, scan_time, symbol, direction, strategy,
                    entry_price, sl_price, tp_price_1_5, tp_price_2_0, sl_pct,
                    confidence, reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                f"ST_{run_id}", scan_time, p["symbol"], p["direction"],
                f"st_{p['strategy']}", p["entry_price"],
                p["sl_price"], p["tp_price"], p.get("tp_price_2", p["tp_price"]),
                round(abs(p["entry_price"] - p["sl_price"]) / p["entry_price"] * 100, 2),
                round(p["confidence"], 1),
                p["reason"][:500],
            ))
            inserted += 1
        cur.close()
        conn.close()
        return inserted
    except Exception as e:
        log.warning(f"DB insert failed: {e}")
        return 0


def resolve_pending_picks():
    """Resolve pending picks from previous scans."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, symbol, direction, entry_price, sl_price, tp_price_1_5, tp_price_2_0,
                   scan_time, strategy
            FROM now_history
            WHERE outcome_1_5 = 'PENDING' AND run_id LIKE 'ST_%'
              AND scan_time > DATE_SUB(NOW(), INTERVAL 48 HOUR)
        """)
        cols = [d[0] for d in cur.description]
        pending = [dict(zip(cols, row)) for row in cur.fetchall()]

        if not pending:
            cur.close()
            conn.close()
            return {"resolved": 0}

        resolved = tp_hits = sl_hits = expired = 0
        for pick in pending:
            symbol = pick["symbol"]
            entry = float(pick["entry_price"])
            tp = float(pick["tp_price_1_5"])
            sl = float(pick["sl_price"])
            direction = pick.get("direction", "LONG")
            scan_time = pick["scan_time"]

            # Check time-based expiry
            if isinstance(scan_time, str):
                scan_dt = datetime.fromisoformat(scan_time.replace("Z", "+00:00"))
            else:
                scan_dt = scan_time.replace(tzinfo=timezone.utc) if scan_time.tzinfo is None else scan_time
            hours_elapsed = (datetime.now(timezone.utc) - scan_dt).total_seconds() / 3600
            max_hold = 12 if "1h" in pick.get("strategy", "") else 32

            # Fetch current price
            price_data = _fetch_json(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
            if not price_data:
                continue
            current = float(price_data["price"])

            outcome = None
            pnl = 0

            if direction == "LONG":
                pnl = (current - entry) / entry * 100
                if current >= tp:
                    outcome = "TP_HIT"
                    tp_hits += 1
                elif current <= sl:
                    outcome = "SL_HIT"
                    sl_hits += 1
                elif hours_elapsed >= max_hold:
                    outcome = "EXPIRED"
                    expired += 1
            else:
                pnl = (entry - current) / entry * 100
                if current <= tp:
                    outcome = "TP_HIT"
                    tp_hits += 1
                elif current >= sl:
                    outcome = "SL_HIT"
                    sl_hits += 1
                elif hours_elapsed >= max_hold:
                    outcome = "EXPIRED"
                    expired += 1

            if outcome:
                resolved += 1
                cur.execute("""
                    UPDATE now_history SET outcome_1_5 = %s, outcome_2_0 = %s,
                        actual_pnl_pct = %s, resolved_at = NOW(),
                        peak_price = %s, trough_price = %s
                    WHERE id = %s
                """, (outcome, outcome, round(pnl, 4), current, current, pick["id"]))

        cur.close()
        conn.close()
        return {"resolved": resolved, "tp": tp_hits, "sl": sl_hits, "expired": expired}
    except Exception as e:
        log.warning(f"Resolution failed: {e}")
        return {"resolved": 0}


# ── JSON-based Resolution (no MySQL required) ────────────────────────────

CLOSED_PICKS_FILE = TRACKER_DIR / "short_term_closed.json"


def resolve_pending_picks_json():
    """Resolve PENDING picks in short_term_picks.json against live Binance prices.

    Works without MySQL — reads the JSON history file, fetches current prices
    from Binance, evaluates TP/SL/expiry, updates outcomes in-place, and appends
    newly resolved picks to short_term_closed.json for the audit dashboard.

    Returns dict with resolved/tp/sl/expired counts.
    """
    if not PICKS_FILE.exists():
        return {"resolved": 0}

    try:
        all_picks = json.loads(PICKS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning(f"[JSON resolver] Could not read picks file: {e}")
        return {"resolved": 0}

    pending = [p for p in all_picks if p.get("outcome") == "PENDING"]
    if not pending:
        return {"resolved": 0}

    log.info(f"[JSON resolver] {len(pending)} PENDING picks to evaluate")

    # Batch-fetch current prices for all unique symbols
    symbols = list(set(p["symbol"] for p in pending))
    prices = {}
    for sym in symbols:
        data = _fetch_json(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}")
        if data and "price" in data:
            prices[sym] = float(data["price"])
        else:
            # Try mirror
            for mirror in BINANCE_MIRRORS[1:]:
                data = _fetch_json(f"{mirror}/api/v3/ticker/price?symbol={sym}")
                if data and "price" in data:
                    prices[sym] = float(data["price"])
                    break

    resolved = tp_hits = sl_hits = expired_count = 0
    now = datetime.now(timezone.utc)
    newly_closed = []

    for pick in all_picks:
        if pick.get("outcome") != "PENDING":
            continue

        symbol = pick["symbol"]
        current = prices.get(symbol)
        if current is None:
            continue  # No price — leave as PENDING

        entry = float(pick.get("entry_price", 0))
        tp = float(pick.get("tp_price_1_5", 0))
        sl = float(pick.get("sl_price", 0))
        direction = pick.get("direction", "LONG")

        # Parse scan time for expiry check
        scan_str = pick.get("scan_time", "")
        try:
            scan_dt = datetime.fromisoformat(scan_str.replace(" ", "T"))
            if scan_dt.tzinfo is None:
                scan_dt = scan_dt.replace(tzinfo=timezone.utc)
        except Exception:
            scan_dt = now - timedelta(hours=999)

        hours_elapsed = (now - scan_dt).total_seconds() / 3600
        # 1h strategies expire after 12h, 4h strategies after 32h
        tf = pick.get("timeframe", "4h")
        max_hold = 12 if tf == "1h" else 32

        outcome = None
        pnl = 0.0

        if entry > 0:
            if direction == "LONG":
                pnl = (current - entry) / entry * 100
                if tp > 0 and current >= tp:
                    outcome = "TP_HIT"
                    tp_hits += 1
                elif sl > 0 and current <= sl:
                    outcome = "SL_HIT"
                    sl_hits += 1
                elif hours_elapsed >= max_hold:
                    outcome = "EXPIRED"
                    expired_count += 1
            else:  # SHORT
                pnl = (entry - current) / entry * 100
                if tp > 0 and current <= tp:
                    outcome = "TP_HIT"
                    tp_hits += 1
                elif sl > 0 and current >= sl:
                    outcome = "SL_HIT"
                    sl_hits += 1
                elif hours_elapsed >= max_hold:
                    outcome = "EXPIRED"
                    expired_count += 1

        if outcome:
            pick["outcome"] = outcome
            pick["pnl_pct"] = round(pnl, 4)
            pick["actual_pnl_pct"] = round(pnl, 4)
            pick["resolved_at"] = now.isoformat()
            pick["exit_price"] = current
            resolved += 1
            newly_closed.append({**pick})

    # Write updated picks back (outcomes now set)
    PICKS_FILE.write_text(json.dumps(all_picks, indent=2, default=str), encoding="utf-8")

    # Append newly closed picks to short_term_closed.json
    if newly_closed:
        existing_closed = []
        if CLOSED_PICKS_FILE.exists():
            try:
                existing_closed = json.loads(CLOSED_PICKS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        existing_closed.extend(newly_closed)
        existing_closed = existing_closed[-2000:]  # Keep last 2000
        CLOSED_PICKS_FILE.write_text(json.dumps(existing_closed, indent=2, default=str), encoding="utf-8")
        log.info(f"[JSON resolver] Resolved {resolved}: TP={tp_hits}, SL={sl_hits}, Expired={expired_count}")

    return {"resolved": resolved, "tp": tp_hits, "sl": sl_hits, "expired": expired_count}


# ── JSON Output ──────────────────────────────────────────────────────────

def save_picks_json(picks, run_id, scan_time):
    """Save picks to JSON files."""
    # Active picks (current scan only)
    active_data = []
    for p in picks:
        # confidence is computed on a 0-95 percent scale internally; the
        # canonical pick schema (and edge-stability harness) expect 0-1. Emit
        # /100 so closed_picks ledgers do not store percent-as-integer (#1241).
        _conf = p["confidence"]
        if _conf is not None and _conf > 1.0:
            _conf = _conf / 100.0
        active_data.append({
            "symbol": p["symbol"],
            "direction": p["direction"],
            "strategy": f"st_{p['strategy']}",
            "confidence": round(_conf, 4),
            "entry_price": p["entry_price"],
            "reason": p["reason"],
            "sl_price": p["sl_price"],
            "tp_price_1_5": p["tp_price"],
            "tp_price_2_0": p.get("tp_price_2", p["tp_price"]),
            "sl_pct": round(abs(p["entry_price"] - p["sl_price"]) / p["entry_price"] * 100, 2),
            "timeframe": p["timeframe"],
            "scan_time": scan_time,
            "source": SOURCE_SYSTEM,
        })
    ACTIVE_PICKS_FILE.write_text(json.dumps(active_data, indent=2, default=str), encoding="utf-8")

    # Append to history file
    existing = []
    if PICKS_FILE.exists():
        try:
            existing = json.loads(PICKS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    for p in active_data:
        existing.append({**p, "run_id": run_id, "outcome": "PENDING"})
    existing = existing[-500:]  # Keep last 500
    PICKS_FILE.write_text(json.dumps(existing, indent=2, default=str), encoding="utf-8")


# ── Main Scanner ─────────────────────────────────────────────────────────

def scan_symbol(symbol, timeframe, fg_current, fg_7d, ml_model=None, ml_scaler=None, ml_meta=None):
    """Scan a single symbol. Returns list of pick dicts."""
    cfg = TIMEFRAME_CONFIG[timeframe]
    klines = get_klines(symbol, cfg["interval"], cfg["bars_needed"])
    if len(klines) < 50:
        return []

    funding = fetch_funding_rate(symbol)
    features = compute_features(klines, timeframe, funding, fg_current, fg_7d)
    if features is None:
        return []

    # Get signals from rule-based engine
    signals = generate_signals_rule_based(features, symbol, timeframe)

    # If ML model available, add ML-based signal
    if ml_model is not None:
        ml_prob = ml_predict(features, ml_model, ml_scaler, ml_meta)
        if ml_prob is not None and ml_prob > 0.6:
            atr = features["_atr"]
            c = features["_close"]
            signals.append({
                "direction": "LONG",
                "strategy": "ml_ensemble",
                "confidence": min(50 + ml_prob * 50, 95),
                "reason": f"ML ensemble prediction: {ml_prob:.1%} pump probability",
                "tp": c + atr * cfg["tp_atr_mult"],
                "sl": c - atr * cfg["sl_atr_mult"],
            })

    # Convert to picks
    picks = []
    for sig in signals:
        # Apply self-learning weight
        weight = _strategy_weights.get(sig["strategy"], 1.0)
        adjusted_conf = round(min(95, max(30, sig["confidence"] * weight)), 4)

        picks.append({
            "symbol": symbol,
            "direction": sig["direction"],
            "strategy": sig["strategy"],
            "confidence": adjusted_conf,
            "entry_price": features["_close"],
            "tp_price": sig["tp"],
            "sl_price": sig["sl"],
            "reason": sig["reason"],
            "timeframe": timeframe,
            "features": {k: v for k, v in features.items() if not k.startswith("_")},
        })

    return picks


def run_scan(timeframes=None, pair_count=20):
    """Main scan entry point."""
    timeframes = timeframes or ["1h", "4h"]
    run_id = str(uuid.uuid4())[:8]
    scan_time = datetime.now(timezone.utc)
    scan_str = scan_time.strftime('%Y-%m-%d %H:%M:%S')
    t_start = time.time()

    log.info(f"{'=' * 60}")
    log.info(f"  CLAUDE GAINER SHORT-TERM — Scan {run_id}")
    log.info(f"  {scan_str} UTC | Timeframes: {timeframes}")
    log.info(f"{'=' * 60}")

    # 1. Load self-learning weights
    load_strategy_weights()

    # 2. Resolve pending picks — JSON-first (no MySQL required), then DB fallback
    log.info("Resolving pending picks (JSON)...")
    json_resolve_stats = resolve_pending_picks_json()
    if json_resolve_stats.get("resolved", 0) > 0:
        log.info(f"  JSON resolved {json_resolve_stats['resolved']}: "
                 f"TP={json_resolve_stats.get('tp', 0)}, "
                 f"SL={json_resolve_stats.get('sl', 0)}, "
                 f"Expired={json_resolve_stats.get('expired', 0)}")
    log.info("Resolving pending picks (DB)...")
    resolve_stats = resolve_pending_picks()
    if resolve_stats.get("resolved", 0) > 0:
        log.info(f"  DB resolved {resolve_stats['resolved']}: TP={resolve_stats.get('tp', 0)}, "
                 f"SL={resolve_stats.get('sl', 0)}, Expired={resolve_stats.get('expired', 0)}")

    # 3. Fetch F&G once
    fg_current, fg_7d = fetch_fear_greed()
    log.info(f"  Fear & Greed: {fg_current} (7d avg: {sum(fg_7d) / len(fg_7d):.0f})")

    # 4. Get top pairs
    pairs = get_top_pairs(pair_count)
    log.info(f"  Scanning {len(pairs)} pairs")

    # 5. Load ML models (if available)
    ml_models = {}
    for tf in timeframes:
        model, scaler, meta = load_ml_model(tf)
        if model:
            ml_models[tf] = (model, scaler, meta)
            log.info(f"  ML model active for {tf}")

    # 6. Scan all pairs across all timeframes
    all_picks = []
    t_scan = time.time()

    for tf in timeframes:
        ml_model, ml_scaler, ml_meta = ml_models.get(tf, (None, None, None))
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(scan_symbol, sym, tf, fg_current, fg_7d,
                                       ml_model, ml_scaler, ml_meta): sym
                       for sym in pairs}
            for future in as_completed(futures):
                sym = futures[future]
                try:
                    picks = future.result()
                    for p in picks:
                        all_picks.append(p)
                        log.info(f"  SIGNAL [{tf}]: {p['symbol']} {p['direction']} via {p['strategy']} "
                                 f"(conf: {p['confidence']:.0f}%)")
                except Exception as e:
                    log.debug(f"  Error {sym}: {e}")

    scan_duration = time.time() - t_scan

    # Sort by confidence
    all_picks.sort(key=lambda p: p["confidence"], reverse=True)

    # Deduplicate (max 1 pick per symbol per timeframe)
    seen = set()
    unique_picks = []
    for p in all_picks:
        key = (p["symbol"], p["timeframe"])
        if key not in seen:
            seen.add(key)
            unique_picks.append(p)
    all_picks = unique_picks

    # 7. Insert to DB
    db_ok = False
    try:
        inserted = insert_picks_db(run_id, scan_time, all_picks)
        db_ok = inserted > 0
        if inserted:
            log.info(f"  Inserted {inserted} picks to MySQL")
    except Exception as e:
        log.warning(f"  DB insert failed: {e}")

    # 8. Save JSON
    if all_picks:
        save_picks_json(all_picks, run_id, scan_str)
        log.info(f"  Saved {len(all_picks)} picks to JSON")

    # 9. Discord notification
    try:
        sys.path.insert(0, str(ROOT))
        from cross_aggregation.freshpicks_notify import send_fresh_pick
        dashboard = "https://findtorontoevents.ca/audit/"
        stats = {"total": len(all_picks), "active": len(all_picks)}
        sent = 0
        for p in all_picks[:5]:
            fp = {
                "symbol": p["symbol"], "direction": p["direction"],
                "entry_price": p["entry_price"], "tp_price": p["tp_price"],
                "sl_price": p["sl_price"], "confidence": p["confidence"] / 100,
                "strategy": f"ST-{p['strategy']}", "reason": p["reason"][:200],
            }
            if send_fresh_pick("Claude Gainer ST", fp, dashboard, stats=stats):
                sent += 1
        if sent:
            log.info(f"  Sent {sent} picks to Discord #fresh-picks")
    except Exception as e:
        log.debug(f"  Discord notify skipped: {e}")

    # 10. Summary
    total_time = time.time() - t_start
    log.info(f"\n{'=' * 60}")
    log.info(f"  SCAN COMPLETE — {len(all_picks)} picks in {total_time:.1f}s")
    log.info(f"  Scan: {scan_duration:.1f}s | Pairs: {len(pairs)} | TFs: {timeframes}")
    log.info(f"{'=' * 60}")
    if all_picks:
        log.info(f"\n  TOP PICKS:")
        for i, p in enumerate(all_picks[:10]):
            tp_pct = abs(p["tp_price"] - p["entry_price"]) / p["entry_price"] * 100
            sl_pct = abs(p["sl_price"] - p["entry_price"]) / p["entry_price"] * 100
            log.info(f"  {i + 1}. [{p['timeframe']}] {p['symbol']:12s} {p['direction']:5s} "
                     f"via {p['strategy']:25s} conf={p['confidence']:.0f}% "
                     f"TP=+{tp_pct:.1f}% SL=-{sl_pct:.1f}%")

    return all_picks


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claude Gainer Short-Term Predictor")
    parser.add_argument("--timeframe", "-t", choices=["1h", "4h", "both"], default="both",
                        help="Timeframe to scan (default: both)")
    parser.add_argument("--pairs", "-p", type=int, default=20, help="Number of pairs (default: 20)")
    parser.add_argument("--resolve", action="store_true", help="Only resolve pending picks")
    args = parser.parse_args()

    if args.resolve:
        json_stats = resolve_pending_picks_json()
        log.info(f"JSON resolution: {json_stats}")
        db_stats = resolve_pending_picks()
        log.info(f"DB resolution: {db_stats}")
    else:
        tfs = ["1h", "4h"] if args.timeframe == "both" else [args.timeframe]
        run_scan(timeframes=tfs, pair_count=args.pairs)
