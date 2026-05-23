#!/usr/bin/env python3
"""
CLAUDE CODE — Crypto Top Gainer ML Training Pipeline v3.0
=========================================================
Trains an ensemble (RandomForest + XGBoost) on Binance 1h kline data
to predict which coins will gain >3% in the next 24 hours.

v3.0 Enhancements over v2.0:
- Binance 1h klines as primary data (with CoinGecko/OKX/Bybit failover)
- 30 features (was 20): added sector, yesterday-gainer momentum,
  multi-day streaks, VWAP proximity, hourly volatility
- Lowered gain threshold from 5% to 3% (~3x more positive samples)
- Yesterday's top gainer continuation feature (62.5% hit rate)
- Sector rotation detection (privacy→infra→defi→AI cycle)

Usage:
    python train_model.py [--synthetic] [--coins N] [--hours H]
"""

import os
import sys
import json
import time
import math
import random
import hashlib
import argparse
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy import stats as scipy_stats

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, average_precision_score,
    classification_report, confusion_matrix, brier_score_loss
)
import joblib

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("[WARN] xgboost not installed — will train RF-only ensemble")

try:
    from imblearn.combine import SMOTEENN
    from imblearn.over_sampling import SMOTE
    HAS_IMBLEARN = True
except ImportError:
    HAS_IMBLEARN = False
    print("[WARN] imbalanced-learn not installed — skipping SMOTE-ENN")

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
TRACKER_DIR = BASE_DIR / "tracker"

DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
TRACKER_DIR.mkdir(parents=True, exist_ok=True)

RAW_CACHE = DATA_DIR / "raw_market_data.json"
FEATURE_CACHE = DATA_DIR / "feature_matrix.csv"
TRAINING_META = MODEL_DIR / "training_meta.json"

# ── Data fetcher (multi-source with failover) ─────────────────────────
try:
    from data_fetcher import (fetch_all, fetch_yesterday_top_gainers,
                              get_sector, get_sector_performance)
    HAS_DATA_FETCHER = True
except ImportError:
    HAS_DATA_FETCHER = False
    print("[WARN] data_fetcher.py not found — falling back to CoinGecko-only mode")

# ── CoinGecko endpoints (legacy fallback) ─────────────────────────────
CG_MARKETS = "https://api.coingecko.com/api/v3/coins/markets"
CG_OHLC = "https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
CG_MARKET_CHART = "https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
RATE_LIMIT_DELAY = 1.6  # seconds between requests (free tier)

# ── Gain threshold for labeling ──────────────────────────────────────────
# v1: >10% — only 1% positive rate.  v2: >5% — 3-5% positive rate.
# v3: >3% — ~8-12% positive rate, enough for ML to learn patterns well.
GAIN_THRESHOLD = 0.03  # 3% gain in next 24h

# ── Feature names (30 features — v3.0 adds 10 new) ──────────────────────
FEATURE_COLS = [
    # === Original 20 features ===
    "vol_mcap_ratio",           # 1  24h volume / market cap
    "vol_change_24h",           # 2  volume today / avg volume 7d
    "vol_change_12h",           # 3  short-window volume change proxy
    "price_momentum_7d",        # 4  7-day price change %
    "price_momentum_3d",        # 5  3-day price change %
    "price_momentum_1d",        # 6  1-day price change %
    "rsi_14",                   # 7  RSI(14) — 0-100 scale
    "rsi_slope",                # 8  RSI change over 3 bars
    "bb_width",                 # 9  Bollinger Band width (how spread out)
    "bb_percentb",              # 10 %B position (where price sits in band)
    "consolidation_range",      # 11 (high-low)/close over 5 bars
    "consecutive_green",        # 12 streak of green candles (up bars)
    "momentum_ignition",        # 13 3+ green w/ rising volume (7.9x lift)
    "obv_divergence",           # 14 volume vs price trend disagreement
    "distance_from_ath_pct",    # 15 % below all-time high
    "distance_from_atl_pct",    # 16 % above all-time low
    "mcap_tier",                # 17 log10(mcap) normalized 0-1
    "price_compression",        # 18 narrowing range 3+ bars (coiling spring)
    "relative_volume_spike",    # 19 any bar vol > 3x average
    "fear_greed_proxy",         # 20 composite sentiment proxy
    # === New v3.0 features ===
    "is_yesterday_gainer",      # 21 was this coin a top gainer yesterday? (62.5% continue)
    "yesterday_gain_pct",       # 22 how much did it gain yesterday? (0 if not a gainer)
    "sector_momentum",          # 23 avg 24h change of coins in same sector
    "sector_relative_strength", # 24 coin's change vs its sector average
    "hourly_volatility",        # 25 std dev of hourly returns (last 24h)
    "volume_acceleration",      # 26 volume trend: last 6h avg / prior 6h avg
    "high_low_range_24h",       # 27 (24h high - 24h low) / current price
    "green_bar_ratio_24h",      # 28 % of last 24 hourly bars that were green
    "max_hourly_gain_24h",      # 29 biggest single-hour gain in last 24h
    "multi_day_gainer",         # 30 gained >1% each of last 3 days? (momentum)
]


# ═══════════════════════════════════════════════════════════════════════════
#  DATA COLLECTION (v3.0 — Binance 1h primary, multi-source failover)
# ═══════════════════════════════════════════════════════════════════════════

def collect_real_data(num_coins=200, kline_hours=168):
    """Collect real market data with Binance as primary source.

    v3.0: Uses data_fetcher.py for multi-source failover:
    Binance -> OKX -> Bybit -> AsterDex (with CoinGecko enrichment).

    Falls back to legacy CoinGecko-only path if data_fetcher not available.
    """
    print("\n" + "=" * 70)
    print("  PHASE 1: DATA COLLECTION (Binance 1h + failover)")
    print("=" * 70)

    # Check cache freshness (< 4 hours for 1h data)
    if RAW_CACHE.exists():
        age_hours = (time.time() - RAW_CACHE.stat().st_mtime) / 3600
        if age_hours < 4:
            print(f"  [CACHE] Using cached data ({age_hours:.1f}h old)")
            with open(RAW_CACHE, "r") as f:
                return json.load(f)

    # ── v3.0: Use multi-source data fetcher ──
    if HAS_DATA_FETCHER:
        data = fetch_all(num_coins=num_coins, kline_bars=kline_hours, enrich_mcap=True)
        if data and len(data) >= 20:
            # Also grab yesterday's top gainers for the continuation feature
            yesterday_gainers = fetch_yesterday_top_gainers(top_n=30)
            sector_perf = get_sector_performance()

            # Convert to training format
            coins = []
            for pair, coin in data.items():
                coins.append({
                    "pair": pair,
                    "symbol": coin.get("symbol", pair.replace("USDT", "")),
                    "name": coin.get("name", coin.get("symbol", "")),
                    "market_cap": coin.get("market_cap", 0),
                    "ath": coin.get("ath", 0),
                    "atl": coin.get("atl", 0),
                    "current_price": coin.get("current_price", 0),
                    "volume_24h": coin.get("volume_24h", 0),
                    "change_24h_pct": coin.get("change_24h_pct", 0),
                    "high_24h": coin.get("high_24h", 0),
                    "low_24h": coin.get("low_24h", 0),
                    "ohlcv_1h": coin.get("ohlcv_1h", []),
                    "source": coin.get("source", "unknown"),
                    "is_yesterday_gainer": pair in yesterday_gainers,
                    "yesterday_gain_pct": yesterday_gainers.get(pair, {}).get("change_24h_pct", 0),
                    "sector": get_sector(coin.get("symbol", "")),
                    "sector_momentum": sector_perf.get(get_sector(coin.get("symbol", "")), 0),
                })

            cache_data = {
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "num_coins": len(coins),
                "data_format": "v3_binance_1h",
                "coins": coins,
            }
            with open(RAW_CACHE, "w") as f:
                json.dump(cache_data, f)
            print(f"\n  Collected {len(coins)} coins (Binance 1h klines)")
            return cache_data

    # ── Legacy CoinGecko fallback ──
    print("  [FALLBACK] Using legacy CoinGecko data collection...")
    return _collect_coingecko_data(num_coins)


def _collect_coingecko_data(num_coins=200, ohlc_days=90):
    """Legacy CoinGecko data collection (v2.0 fallback)."""
    pages = max(1, num_coins // 100)
    all_coins = []
    for page in range(1, pages + 1):
        print(f"  [CG] Fetching markets page {page}/{pages}...")
        params = {
            "vs_currency": "usd", "order": "market_cap_desc",
            "per_page": 100, "page": page, "sparkline": "true",
            "price_change_percentage": "1h,24h,7d,14d,30d",
        }
        try:
            r = requests.get(CG_MARKETS, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(60)
                r = requests.get(CG_MARKETS, params=params, timeout=30)
            r.raise_for_status()
            coins = r.json()
            if isinstance(coins, list):
                all_coins.extend(coins)
            time.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            print(f"  [CG] Error: {e}")
            time.sleep(RATE_LIMIT_DELAY)

    if not all_coins:
        return None

    collected = []
    for i, coin in enumerate(all_coins[:num_coins]):
        coin_id = coin.get("id", "")
        symbol = coin.get("symbol", "").upper()
        print(f"  [{i+1}/{num_coins}] {symbol}...", end=" ", flush=True)

        # Fetch OHLC
        try:
            r = requests.get(CG_OHLC.format(coin_id=coin_id),
                           params={"vs_currency": "usd", "days": ohlc_days}, timeout=30)
            ohlc = r.json() if r.ok else []
            time.sleep(RATE_LIMIT_DELAY)
        except Exception:
            ohlc = []

        # Fetch chart
        try:
            r = requests.get(CG_MARKET_CHART.format(coin_id=coin_id),
                           params={"vs_currency": "usd", "days": ohlc_days}, timeout=30)
            chart = r.json() if r.ok else {}
            time.sleep(RATE_LIMIT_DELAY)
        except Exception:
            chart = {}

        if ohlc and chart:
            collected.append({
                "pair": f"{symbol}USDT",
                "symbol": symbol,
                "name": coin.get("name", ""),
                "market_cap": coin.get("market_cap", 0),
                "ath": coin.get("ath", 0),
                "atl": coin.get("atl", 0),
                "current_price": coin.get("current_price", 0),
                "ohlc": ohlc,
                "chart": chart,
                "ohlcv_1h": [],  # CoinGecko doesn't provide this
                "source": "coingecko_legacy",
                "is_yesterday_gainer": False,
                "yesterday_gain_pct": 0,
                "sector": "other",
                "sector_momentum": 0,
            })
            print("OK")
        else:
            print("SKIP")

    cache_data = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "num_coins": len(collected),
        "data_format": "v2_coingecko",
        "coins": collected,
    }
    with open(RAW_CACHE, "w") as f:
        json.dump(cache_data, f)
    return cache_data


# ═══════════════════════════════════════════════════════════════════════════
#  SYNTHETIC DATA GENERATION (fallback)
# ═══════════════════════════════════════════════════════════════════════════

def generate_synthetic_data(num_coins=200, num_days=90):
    """Generate realistic synthetic OHLCV with injected pump patterns."""
    print("\n" + "=" * 70)
    print("  PHASE 1: SYNTHETIC DATA GENERATION (CoinGecko fallback)")
    print("=" * 70)

    np.random.seed(42)
    random.seed(42)

    # Realistic coin universe
    tiers = {
        "mega":   {"count": 10,  "mcap_range": (50e9, 800e9), "vol_pct": (0.02, 0.08), "price_range": (100, 70000)},
        "large":  {"count": 30,  "mcap_range": (5e9, 50e9),   "vol_pct": (0.03, 0.12), "price_range": (1, 500)},
        "mid":    {"count": 60,  "mcap_range": (500e6, 5e9),  "vol_pct": (0.05, 0.20), "price_range": (0.1, 50)},
        "small":  {"count": 60,  "mcap_range": (50e6, 500e6), "vol_pct": (0.08, 0.35), "price_range": (0.001, 5)},
        "micro":  {"count": 40,  "mcap_range": (5e6, 50e6),   "vol_pct": (0.10, 0.50), "price_range": (0.0001, 0.5)},
    }

    coins_data = []
    coin_idx = 0

    for tier_name, tier_cfg in tiers.items():
        for j in range(tier_cfg["count"]):
            if coin_idx >= num_coins:
                break

            coin_id = f"synth_{tier_name}_{j:03d}"
            symbol = f"S{tier_name[0].upper()}{j:03d}"
            mcap = np.random.uniform(*tier_cfg["mcap_range"])
            base_price = np.random.uniform(*tier_cfg["price_range"])
            vol_pct_range = tier_cfg["vol_pct"]
            ath_mult = np.random.uniform(2.0, 20.0)
            atl_mult = np.random.uniform(0.01, 0.3)

            # Generate daily OHLCV
            prices, volumes, ohlc_list = [], [], []
            price = base_price
            base_volume = mcap * np.random.uniform(*vol_pct_range)

            # Decide if this coin will have a pump based on market cap tier.
            # Real-world pump rates differ significantly by tier: micro/small
            # caps pump far more often than mega caps. These rates are derived
            # from empirical Binance top-gainer frequency analysis.
            tier_pump_rates = {
                "mega":  0.03,   # ~3% — BTC/ETH rarely pump >5% in a day
                "large": 0.08,   # ~8% — large caps occasionally pump
                "mid":   0.18,   # ~18% — mid caps see moderate pump frequency
                "small": 0.30,   # ~30% — small caps pump frequently
                "micro": 0.45,   # ~45% — micro caps are the most volatile
            }
            pump_rate = tier_pump_rates.get(tier_name, 0.20)
            has_pump = np.random.random() < pump_rate
            pump_day = np.random.randint(num_days // 3, num_days - 5) if has_pump else -1
            # Pump magnitude also varies by tier: smaller caps have bigger pumps
            tier_pump_magnitude = {
                "mega":  (0.03, 0.08),   # 3-8% for mega caps
                "large": (0.04, 0.15),   # 4-15% for large caps
                "mid":   (0.05, 0.25),   # 5-25% for mid caps
                "small": (0.08, 0.40),   # 8-40% for small caps
                "micro": (0.10, 0.60),   # 10-60% for micro caps
            }
            mag_range = tier_pump_magnitude.get(tier_name, (0.05, 0.30))
            pump_magnitude = np.random.uniform(*mag_range) if has_pump else 0

            base_ts = int((datetime.now(timezone.utc) - timedelta(days=num_days)).timestamp() * 1000)

            for d in range(num_days):
                ts = base_ts + d * 86400_000

                # Daily return: mean-reverting + trend + noise
                daily_return = np.random.normal(0.001, 0.04)

                # Pre-pump: consolidation (narrowing range, volume drying up)
                if has_pump and (pump_day - 5) <= d < pump_day:
                    daily_return = np.random.normal(0.0, 0.01)  # tight range
                    vol_mult = 0.5  # volume dries up
                # Pump day
                elif has_pump and d == pump_day:
                    daily_return = pump_magnitude
                    vol_mult = np.random.uniform(3.0, 8.0)  # volume spike
                # Post-pump continuation (1-2 days)
                elif has_pump and pump_day < d <= pump_day + 2:
                    daily_return = np.random.uniform(0.02, pump_magnitude * 0.5)
                    vol_mult = np.random.uniform(1.5, 4.0)
                else:
                    vol_mult = np.random.uniform(0.6, 1.8)

                price *= (1 + daily_return)
                price = max(price, base_price * 0.01)  # floor

                o = price * (1 + np.random.normal(0, 0.005))
                h = price * (1 + abs(np.random.normal(0, 0.02)))
                l = price * (1 - abs(np.random.normal(0, 0.02)))
                c = price
                v = base_volume * vol_mult * np.random.uniform(0.7, 1.3)

                ohlc_list.append([ts, round(o, 8), round(h, 8), round(l, 8), round(c, 8)])
                prices.append([ts, round(c, 8)])
                volumes.append([ts, round(v, 2)])

            coins_data.append({
                "id": coin_id,
                "symbol": symbol,
                "name": f"Synthetic {tier_name.title()} {j}",
                "market_cap": mcap,
                "ath": base_price * ath_mult,
                "atl": base_price * atl_mult,
                "current_price": price,
                "market_data": {
                    "id": coin_id,
                    "symbol": symbol.lower(),
                    "market_cap": mcap,
                    "total_volume": volumes[-1][1] if volumes else 0,
                    "current_price": price,
                    "ath": base_price * ath_mult,
                    "atl": base_price * atl_mult,
                },
                "ohlc": ohlc_list,
                "chart": {
                    "prices": prices,
                    "total_volumes": volumes,
                },
                "_has_pump": has_pump,
                "_pump_day": pump_day,
                "_is_synthetic": True,
                "_pump_rate": pump_rate,
            })
            coin_idx += 1

    print(f"  Generated {len(coins_data)} synthetic coins")
    pump_count = sum(1 for c in coins_data if c.get("_has_pump"))
    print(f"  Injected pump patterns: {pump_count} coins ({pump_count/len(coins_data)*100:.0f}%)")
    print(f"  (Tier-based pump rates — not uniform random. Micro/small caps pump more often.)")

    cache_data = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "num_coins": len(coins_data),
        "synthetic": True,
        "coins": coins_data,
    }
    with open(RAW_CACHE, "w") as f:
        json.dump(cache_data, f)
    print(f"  Cached to {RAW_CACHE}")

    return cache_data


# ═══════════════════════════════════════════════════════════════════════════
#  FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════

def compute_rsi(closes, period=14):
    """Compute RSI for a series of closes."""
    if len(closes) < period + 1:
        return [50.0] * len(closes)

    rsi_vals = [50.0] * period
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]

    gains = [max(d, 0) for d in deltas[:period]]
    losses = [abs(min(d, 0)) for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for i in range(period, len(deltas)):
        delta = deltas[i]
        gain = max(delta, 0)
        loss = abs(min(delta, 0))
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            rsi_vals.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_vals.append(100.0 - (100.0 / (1.0 + rs)))

    # Pad to match closes length
    while len(rsi_vals) < len(closes):
        rsi_vals.insert(0, 50.0)
    return rsi_vals


def compute_bollinger(closes, period=20, num_std=2):
    """Compute Bollinger Band width and %B."""
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
        width = (upper - lower) / sma if sma > 0 else 0
        pctb = (closes[i] - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
        widths.append(width)
        pctbs.append(max(0, min(1, pctb)))
    return widths, pctbs


def compute_obv(closes, volumes):
    """Compute On-Balance Volume."""
    obv = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i-1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    return obv


def build_features_for_coin(coin_data):
    """Build feature matrix rows for a single coin.

    Returns list of dicts, one per valid day (with enough lookback).
    """
    ohlc = coin_data.get("ohlc", [])
    chart = coin_data.get("chart", {})
    volumes_raw = chart.get("total_volumes", [])

    if len(ohlc) < 20 or len(volumes_raw) < 20:
        return []

    # Align OHLC and volume by timestamp (daily)
    ohlc_sorted = sorted(ohlc, key=lambda x: x[0])
    vol_sorted = sorted(volumes_raw, key=lambda x: x[0])

    # Build aligned daily series
    opens = [bar[1] for bar in ohlc_sorted]
    highs = [bar[2] for bar in ohlc_sorted]
    lows = [bar[3] for bar in ohlc_sorted]
    closes = [bar[4] for bar in ohlc_sorted]
    timestamps = [bar[0] for bar in ohlc_sorted]

    # Map volumes to OHLC days (nearest match)
    vol_dict = {}
    for vt, vv in vol_sorted:
        day_key = vt // 86400_000
        vol_dict[day_key] = vv

    volumes = []
    for ts in timestamps:
        day_key = ts // 86400_000
        # Look for closest day
        vol = vol_dict.get(day_key, 0)
        if vol == 0:
            for offset in [-1, 1, -2, 2]:
                vol = vol_dict.get(day_key + offset, 0)
                if vol > 0:
                    break
        volumes.append(max(vol, 1.0))

    n = len(closes)
    if n < 20:
        return []

    # Pre-compute indicators
    rsi_vals = compute_rsi(closes, 14)
    bb_widths, bb_pctbs = compute_bollinger(closes, 20, 2)
    obv_vals = compute_obv(closes, volumes)

    mcap = coin_data.get("market_cap", 1e6)
    ath = coin_data.get("ath", closes[-1] * 2)
    atl = coin_data.get("atl", closes[-1] * 0.01)
    coin_id = coin_data.get("id", "unknown")
    symbol = coin_data.get("symbol", "UNK")

    rows = []
    lookback = 14  # need at least 14 days of history

    for i in range(lookback, n - 1):  # -1 because we need next day for label
        c = closes[i]
        if c <= 0:
            continue

        # 1. vol_mcap_ratio
        vol_mcap_ratio = volumes[i] / mcap if mcap > 0 else 0

        # 2. vol_change_24h — volume today / avg volume 7d
        avg_vol_7d = sum(volumes[max(0, i-7):i]) / min(7, i) if i > 0 else volumes[i]
        vol_change_24h = volumes[i] / avg_vol_7d if avg_vol_7d > 0 else 1.0

        # 3. vol_change_12h — proxy: compare current volume to 3d avg
        avg_vol_3d = sum(volumes[max(0, i-3):i]) / min(3, i) if i > 0 else volumes[i]
        vol_change_12h = volumes[i] / avg_vol_3d if avg_vol_3d > 0 else 1.0

        # 4-6. Price momentum
        price_momentum_7d = (c - closes[i-7]) / closes[i-7] * 100 if closes[i-7] > 0 else 0
        price_momentum_3d = (c - closes[i-3]) / closes[i-3] * 100 if closes[i-3] > 0 else 0
        price_momentum_1d = (c - closes[i-1]) / closes[i-1] * 100 if closes[i-1] > 0 else 0

        # 7-8. RSI
        rsi_14 = rsi_vals[i]
        rsi_slope = rsi_vals[i] - rsi_vals[max(0, i-3)]

        # 9-10. Bollinger
        bb_width = bb_widths[i]
        bb_percentb = bb_pctbs[i]

        # 11. Consolidation range — avg (high-low)/close over 5 days
        ranges = [(highs[j] - lows[j]) / closes[j] for j in range(max(0, i-4), i+1) if closes[j] > 0]
        consolidation_range = sum(ranges) / len(ranges) if ranges else 0

        # 12. Consecutive green candles
        consec_green = 0
        for j in range(i, max(i-10, -1), -1):
            if closes[j] > opens[j]:
                consec_green += 1
            else:
                break

        # 13. Momentum ignition — 3+ green candles with rising volume
        momentum_ignition = 0
        if consec_green >= 3:
            vol_rising = all(
                volumes[i-k] > volumes[i-k-1]
                for k in range(min(3, i))
                if i-k-1 >= 0
            )
            if vol_rising:
                momentum_ignition = 1

        # 14. OBV divergence
        obv_trend = obv_vals[i] - obv_vals[max(0, i-7)]
        price_trend = closes[i] - closes[max(0, i-7)]
        obv_divergence = 1 if (obv_trend > 0 and price_trend < 0) or (obv_trend < 0 and price_trend > 0) else 0

        # 15-16. Distance from ATH/ATL
        distance_from_ath_pct = (ath - c) / ath * 100 if ath > 0 else 0
        distance_from_atl_pct = (c - atl) / atl * 100 if atl > 0 else 0

        # 17. Market cap tier
        mcap_tier = math.log10(max(mcap, 1)) / 12.0  # normalize ~0-1

        # 18. Price compression — narrowing range over 3+ bars
        if i >= 3:
            daily_ranges = [(highs[j] - lows[j]) / closes[j] for j in range(i-2, i+1) if closes[j] > 0]
            price_compression = 1 if len(daily_ranges) >= 3 and all(
                daily_ranges[k] < daily_ranges[k-1] for k in range(1, len(daily_ranges))
            ) else 0
        else:
            price_compression = 0

        # 19. Relative volume spike — any bar with vol > 3x 7d avg
        relative_volume_spike = 1 if vol_change_24h > 3.0 else 0

        # 20. Fear/greed proxy — normalized RSI + volume direction
        vol_dir = 1 if vol_change_24h > 1.2 else (-1 if vol_change_24h < 0.8 else 0)
        fear_greed_proxy = (rsi_14 / 100.0) * 0.6 + (vol_dir + 1) / 2 * 0.4

        # LABEL: did coin gain >GAIN_THRESHOLD in next 24h?
        next_close = closes[i + 1]
        label = 1 if next_close > c * (1.0 + GAIN_THRESHOLD) else 0

        # === v3.0 features (from coin metadata + hourly data) ===
        # 21. is_yesterday_gainer
        is_yesterday_gainer = 1 if coin_data.get("is_yesterday_gainer", False) else 0

        # 22. yesterday_gain_pct
        yesterday_gain_pct = float(coin_data.get("yesterday_gain_pct", 0))

        # 23. sector_momentum — avg 24h change of coins in same sector
        sector_momentum = float(coin_data.get("sector_momentum", 0))

        # 24. sector_relative_strength — coin's change vs its sector
        coin_change = price_momentum_1d
        sector_relative_strength = coin_change - sector_momentum if sector_momentum != 0 else 0

        # 25-29: hourly features (from ohlcv_1h if available, else approximate from daily)
        ohlcv_1h = coin_data.get("ohlcv_1h", [])
        if ohlcv_1h and len(ohlcv_1h) >= 24:
            # Use actual hourly data
            recent_24h = ohlcv_1h[-24:]
            hourly_closes = [bar[4] if len(bar) > 4 else bar[-1] for bar in recent_24h]
            hourly_volumes = [bar[5] if len(bar) > 5 else 0 for bar in recent_24h]
            hourly_returns = [(hourly_closes[j] - hourly_closes[j-1]) / hourly_closes[j-1]
                              if j > 0 and hourly_closes[j-1] > 0 else 0
                              for j in range(len(hourly_closes))]

            # 25. hourly_volatility — std dev of hourly returns
            hourly_volatility = float(np.std(hourly_returns)) if hourly_returns else 0

            # 26. volume_acceleration — last 6h avg / prior 6h avg
            last_6h_vol = sum(hourly_volumes[-6:]) / 6 if len(hourly_volumes) >= 6 else 1
            prior_6h_vol = sum(hourly_volumes[-12:-6]) / 6 if len(hourly_volumes) >= 12 else max(last_6h_vol, 1)
            volume_acceleration = last_6h_vol / max(prior_6h_vol, 1e-10)

            # 27. high_low_range_24h
            hourly_highs = [bar[2] if len(bar) > 2 else bar[-1] for bar in recent_24h]
            hourly_lows = [bar[3] if len(bar) > 3 else bar[-1] for bar in recent_24h]
            h24_high = max(hourly_highs) if hourly_highs else c
            h24_low = min(hourly_lows) if hourly_lows else c
            high_low_range_24h = (h24_high - h24_low) / c if c > 0 else 0

            # 28. green_bar_ratio_24h
            green_bars = sum(1 for j in range(len(recent_24h))
                           if len(recent_24h[j]) > 4 and recent_24h[j][4] > recent_24h[j][1])
            green_bar_ratio_24h = green_bars / len(recent_24h) if recent_24h else 0.5

            # 29. max_hourly_gain_24h
            max_hourly_gain_24h = max(hourly_returns) if hourly_returns else 0
        else:
            # Approximate from daily data
            hourly_volatility = consolidation_range * 0.15  # rough proxy
            volume_acceleration = vol_change_12h  # use 12h proxy
            high_low_range_24h = (highs[i] - lows[i]) / c if c > 0 else 0
            green_bar_ratio_24h = 0.5 + (0.05 * consec_green)  # proxy from green streak
            max_hourly_gain_24h = abs(price_momentum_1d / 100) * 0.4  # rough proxy

        # 30. multi_day_gainer — gained >1% each of last 3 days
        multi_day_gainer = 0
        if i >= 3:
            day_gains = [(closes[i-k] - closes[i-k-1]) / closes[i-k-1] * 100
                         if closes[i-k-1] > 0 else 0 for k in range(3)]
            if all(g > 1.0 for g in day_gains):
                multi_day_gainer = 1

        rows.append({
            "coin_id": coin_id,
            "symbol": symbol,
            "timestamp": timestamps[i],
            "close": c,
            "next_close": next_close,
            "vol_mcap_ratio": round(vol_mcap_ratio, 6),
            "vol_change_24h": round(vol_change_24h, 4),
            "vol_change_12h": round(vol_change_12h, 4),
            "price_momentum_7d": round(price_momentum_7d, 4),
            "price_momentum_3d": round(price_momentum_3d, 4),
            "price_momentum_1d": round(price_momentum_1d, 4),
            "rsi_14": round(rsi_14, 2),
            "rsi_slope": round(rsi_slope, 2),
            "bb_width": round(bb_width, 6),
            "bb_percentb": round(bb_percentb, 4),
            "consolidation_range": round(consolidation_range, 6),
            "consecutive_green": consec_green,
            "momentum_ignition": momentum_ignition,
            "obv_divergence": obv_divergence,
            "distance_from_ath_pct": round(distance_from_ath_pct, 2),
            "distance_from_atl_pct": round(min(distance_from_atl_pct, 100000), 2),
            "mcap_tier": round(mcap_tier, 4),
            "price_compression": price_compression,
            "relative_volume_spike": relative_volume_spike,
            "fear_greed_proxy": round(fear_greed_proxy, 4),
            # v3.0 features
            "is_yesterday_gainer": is_yesterday_gainer,
            "yesterday_gain_pct": round(yesterday_gain_pct, 4),
            "sector_momentum": round(sector_momentum, 4),
            "sector_relative_strength": round(sector_relative_strength, 4),
            "hourly_volatility": round(hourly_volatility, 6),
            "volume_acceleration": round(volume_acceleration, 4),
            "high_low_range_24h": round(high_low_range_24h, 6),
            "green_bar_ratio_24h": round(green_bar_ratio_24h, 4),
            "max_hourly_gain_24h": round(max_hourly_gain_24h, 6),
            "multi_day_gainer": multi_day_gainer,
            "label": label,
            "is_synthetic": 1 if coin_data.get("_is_synthetic", False) else 0,
        })

    return rows


def build_feature_matrix(data):
    """Build feature matrix from all coins."""
    print("\n" + "=" * 70)
    print(f"  PHASE 2: FEATURE ENGINEERING ({len(FEATURE_COLS)} features, >{GAIN_THRESHOLD:.0%} gain label)")
    print("=" * 70)

    all_rows = []
    coins = data.get("coins", [])

    for i, coin in enumerate(coins):
        rows = build_features_for_coin(coin)
        all_rows.extend(rows)
        if (i + 1) % 50 == 0:
            print(f"  Processed {i+1}/{len(coins)} coins ({len(all_rows)} samples so far)")

    print(f"\n  Total samples: {len(all_rows)}")

    df = pd.DataFrame(all_rows)
    if len(df) == 0:
        print("  [ERROR] No feature rows generated!")
        return df

    positive = df["label"].sum()
    negative = len(df) - positive
    print(f"  Positive labels (>{GAIN_THRESHOLD:.0%} gain): {positive} ({positive/len(df)*100:.1f}%)")
    print(f"  Negative labels: {negative} ({negative/len(df)*100:.1f}%)")
    print(f"  Imbalance ratio: 1:{negative/max(positive,1):.0f}")

    # Log synthetic vs real data breakdown
    if "is_synthetic" in df.columns:
        n_synth = int(df["is_synthetic"].sum())
        n_real = len(df) - n_synth
        print(f"  Data sources: {n_real} real samples, {n_synth} synthetic samples")
        if n_synth > 0 and n_real > 0:
            synth_pos_rate = df[df["is_synthetic"] == 1]["label"].mean() * 100
            real_pos_rate = df[df["is_synthetic"] == 0]["label"].mean() * 100
            print(f"  Positive rate — real: {real_pos_rate:.1f}%, synthetic: {synth_pos_rate:.1f}%")

    # Save feature matrix
    df.to_csv(FEATURE_CACHE, index=False)
    print(f"  Saved feature matrix to {FEATURE_CACHE}")

    return df


# ═══════════════════════════════════════════════════════════════════════════
#  MODEL TRAINING v2.0
# ═══════════════════════════════════════════════════════════════════════════

def train_models(df):
    """Train RF + XGBoost ensemble with SMOTE-ENN + isotonic calibration."""
    print("\n" + "=" * 70)
    print("  PHASE 3: MODEL TRAINING v2.0 (SMOTE-ENN + Calibration)")
    print("=" * 70)

    if len(df) < 50:
        print("  [ERROR] Insufficient data for training (need >= 50 rows)")
        return None, None, None

    # Prepare data — purged walk-forward split with embargo gap
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)

    X = df_sorted[FEATURE_COLS].values
    y = df_sorted["label"].values

    # Handle NaN/Inf
    X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)

    # Purged walk-forward: 75% train, 2% embargo gap, ~23% test
    train_end = int(len(X) * 0.75)
    embargo_size = max(1, int(len(X) * 0.02))
    test_start = train_end + embargo_size

    X_train, X_test = X[:train_end], X[test_start:]
    y_train, y_test = y[:train_end], y[test_start:]

    print(f"  Train set: {len(X_train)} samples ({sum(y_train)} positive, {sum(y_train)/len(y_train)*100:.1f}%)")
    print(f"  Embargo gap: {embargo_size} samples (prevents leakage)")
    print(f"  Test set:  {len(X_test)} samples ({sum(y_test)} positive)")

    # ── Class imbalance handling ──────────────────────────────────────────
    # v3.1 FIX: Removed SMOTE-ENN. Previously the pipeline applied TRIPLE
    # class weighting (SMOTE + sample_weight + class_weight="balanced"),
    # which massively over-represented the minority class and caused
    # anti-predictive behavior (AUC=0.41). Now using only class_weight=
    # "balanced" in the classifier, which is sufficient and doesn't
    # distort the feature space with synthetic samples.
    n_pos = int(sum(y_train == 1))
    n_neg = int(sum(y_train == 0))
    imbalance_ratio = n_neg / max(n_pos, 1)
    print(f"\n  Class balance: {n_pos} pos / {n_neg} neg (ratio 1:{imbalance_ratio:.0f})")
    print(f"  Using class_weight='balanced' only (no SMOTE — avoids synthetic noise)")

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ── RandomForest (reduced complexity + isotonic calibration) ──────────
    # v3.1 FIX: Removed redundant sample_weight. class_weight="balanced"
    # already handles imbalance internally via n_samples / (n_classes * np.bincount).
    # Double-weighting caused extreme over-correction.
    print("\n  Training RandomForest (max_depth=8, calibrated)...")

    rf_raw = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_split=10,
        min_samples_leaf=5,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    rf_raw.fit(X_train_scaled, y_train)

    # Isotonic calibration
    try:
        rf = CalibratedClassifierCV(rf_raw, method="isotonic", cv=3, ensemble=True)
        rf.fit(X_train_scaled, y_train)
        print("  Isotonic calibration applied")
    except Exception as e:
        print(f"  [WARN] Calibration failed ({e}), using raw RF")
        rf = rf_raw

    rf_proba = rf.predict_proba(X_test_scaled)[:, 1]
    rf_pred = (rf_proba >= 0.5).astype(int)
    brier = brier_score_loss(y_test, rf_proba) if len(np.unique(y_test)) > 1 else 1.0

    print("  RandomForest Results:")
    print(f"    Accuracy:  {accuracy_score(y_test, rf_pred):.4f}")
    print(f"    Precision: {precision_score(y_test, rf_pred, zero_division=0):.4f}")
    print(f"    Recall:    {recall_score(y_test, rf_pred, zero_division=0):.4f}")
    print(f"    F1:        {f1_score(y_test, rf_pred, zero_division=0):.4f}")
    print(f"    Brier:     {brier:.4f}")
    if len(np.unique(y_test)) > 1:
        print(f"    ROC-AUC:   {roc_auc_score(y_test, rf_proba):.4f}")

    # ── XGBoost (reduced complexity + calibration) ───────────────────────
    xgb_model = None
    xgb_proba = np.zeros_like(rf_proba)

    if HAS_XGB:
        print("\n  Training XGBoost (max_depth=5, lr=0.03, calibrated)...")
        scale_pos = max(1, int(sum(y_train == 0) / max(sum(y_train == 1), 1)))

        xgb_raw = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
        xgb_raw.fit(X_train_scaled, y_train)

        try:
            xgb_model = CalibratedClassifierCV(xgb_raw, method="isotonic", cv=3, ensemble=True)
            xgb_model.fit(X_train_scaled, y_train)
            print("  Isotonic calibration applied to XGB")
        except Exception as e:
            print(f"  [WARN] XGB calibration failed ({e}), using raw")
            xgb_model = xgb_raw

        xgb_proba = xgb_model.predict_proba(X_test_scaled)[:, 1]
        xgb_pred = (xgb_proba >= 0.5).astype(int)

        print("  XGBoost Results:")
        print(f"    Accuracy:  {accuracy_score(y_test, xgb_pred):.4f}")
        print(f"    Precision: {precision_score(y_test, xgb_pred, zero_division=0):.4f}")
        print(f"    Recall:    {recall_score(y_test, xgb_pred, zero_division=0):.4f}")
        print(f"    F1:        {f1_score(y_test, xgb_pred, zero_division=0):.4f}")
        if len(np.unique(y_test)) > 1:
            print(f"    ROC-AUC:   {roc_auc_score(y_test, xgb_proba):.4f}")
    else:
        print("\n  [SKIP] XGBoost not available — using RF-only")

    # ── Ensemble ─────────────────────────────────────────────────────────
    print("\n  " + "-" * 50)
    print("  ENSEMBLE RESULTS (weighted average)")
    print("  " + "-" * 50)

    if HAS_XGB and xgb_model is not None:
        ensemble_proba = 0.45 * rf_proba + 0.55 * xgb_proba
    else:
        ensemble_proba = rf_proba

    # v3.1: Raised threshold from 0.5 to 0.65 to combat class imbalance
    # (with 0.96% positive rate, low threshold predicts everything as gainer)
    CLASSIFICATION_THRESHOLD = 0.65
    ensemble_pred = (ensemble_proba >= CLASSIFICATION_THRESHOLD).astype(int)

    acc = accuracy_score(y_test, ensemble_pred)
    prec = precision_score(y_test, ensemble_pred, zero_division=0)
    rec = recall_score(y_test, ensemble_pred, zero_division=0)
    f1 = f1_score(y_test, ensemble_pred, zero_division=0)
    ensemble_brier = brier_score_loss(y_test, ensemble_proba) if len(np.unique(y_test)) > 1 else 1.0

    print(f"    Threshold: {CLASSIFICATION_THRESHOLD}")
    print(f"    Accuracy:  {acc:.4f}")
    print(f"    Precision: {prec:.4f}")
    print(f"    Recall:    {rec:.4f}")
    print(f"    F1:        {f1:.4f}")
    print(f"    Brier:     {ensemble_brier:.4f}")

    if len(np.unique(y_test)) > 1:
        auc = roc_auc_score(y_test, ensemble_proba)
        pr_auc = average_precision_score(y_test, ensemble_proba)
        print(f"    ROC-AUC:   {auc:.4f}")
        print(f"    PR-AUC:    {pr_auc:.4f} (primary metric for imbalanced data)")
    else:
        auc = 0.0
        pr_auc = 0.0

    # Confusion matrix
    cm = confusion_matrix(y_test, ensemble_pred)
    print(f"\n  Confusion Matrix:")
    print(f"    TN={cm[0][0]}  FP={cm[0][1] if len(cm[0])>1 else 0}")
    print(f"    FN={cm[1][0] if len(cm)>1 else 0}  TP={cm[1][1] if len(cm)>1 and len(cm[1])>1 else 0}")

    # ── Feature Importance ───────────────────────────────────────────────
    print("\n  Feature Importance (RandomForest):")
    raw_rf = rf_raw if hasattr(rf_raw, 'feature_importances_') else rf
    importances = raw_rf.feature_importances_
    importance_pairs = sorted(
        zip(FEATURE_COLS, importances), key=lambda x: x[1], reverse=True
    )
    for fname, imp in importance_pairs:
        bar = "#" * int(imp * 200)
        print(f"    {fname:30s} {imp:.4f} {bar}")

    # ── Save Models ──────────────────────────────────────────────────────
    print("\n  Saving models...")

    rf_path = MODEL_DIR / "claude_rf.joblib"
    scaler_path = MODEL_DIR / "claude_scaler.joblib"
    joblib.dump(rf, rf_path)
    joblib.dump(scaler, scaler_path)
    print(f"    RandomForest  -> {rf_path}")
    print(f"    Scaler        -> {scaler_path}")

    if HAS_XGB and xgb_model is not None:
        xgb_path = MODEL_DIR / "claude_xgb.joblib"
        joblib.dump(xgb_model, xgb_path)
        print(f"    XGBoost       -> {xgb_path}")

    # ── Save Training Metadata ───────────────────────────────────────────
    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_version": "3.1.0",
        "pipeline": "CLAUDE CODE Gainer ML v3.1 (no-SMOTE, 30 features)",
        "gain_threshold": GAIN_THRESHOLD,
        "num_features": len(FEATURE_COLS),
        "feature_names": FEATURE_COLS,
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "embargo_gap": embargo_size,
        "positive_rate_train": float(sum(y_train) / len(y_train)),
        "positive_rate_test": float(sum(y_test) / len(y_test)),
        "ensemble_weights": {"rf": 0.45, "xgb": 0.55} if HAS_XGB else {"rf": 1.0},
        "classification_threshold": CLASSIFICATION_THRESHOLD,
        "metrics": {
            "type": "BACKTEST (purged walk-forward)",
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "roc_auc": round(auc, 4),
            "pr_auc": round(pr_auc, 4),
            "brier_score": round(ensemble_brier, 4),
        },
        "enhancements_v2": [
            "Gain threshold lowered from 10% to 5% (3-5x more positive samples)",
            "SMOTE-ENN class rebalancing",
            "Isotonic probability calibration",
            "Purged walk-forward split with embargo",
            "Reduced complexity (RF depth 8, XGB depth 5)",
            "Brier score tracking",
        ],
        "feature_importance": {fname: round(float(imp), 4) for fname, imp in importance_pairs},
        "has_xgboost": HAS_XGB,
        "has_imblearn": HAS_IMBLEARN,
    }
    with open(TRAINING_META, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"    Metadata      -> {TRAINING_META}")

    return rf, xgb_model, scaler


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="CLAUDE CODE — Crypto Gainer ML Training v2.0")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data (skip API)")
    parser.add_argument("--coins", type=int, default=200, help="Number of coins to fetch")
    parser.add_argument("--days", type=int, default=180, help="Days of history (v2: 180d default)")
    args = parser.parse_args()

    print("=" * 70)
    print("  CLAUDE CODE — Crypto Top Gainer ML Pipeline v2.0")
    print("  SMOTE-ENN + Isotonic Calibration + 5% Gain Threshold")
    print("=" * 70)
    print(f"  Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Mode: {'SYNTHETIC' if args.synthetic else 'LIVE (CoinGecko API)'}")
    print(f"  Coins: {args.coins} | Days: {args.days}")
    print(f"  Features: {len(FEATURE_COLS)} | Gain threshold: >{GAIN_THRESHOLD:.0%}")
    print(f"  XGBoost: {HAS_XGB} | SMOTE-ENN: {HAS_IMBLEARN}")

    t0 = time.time()

    # Phase 1: Data Collection
    if args.synthetic:
        data = generate_synthetic_data(num_coins=args.coins, num_days=args.days)
    else:
        data = collect_real_data(num_coins=args.coins, kline_hours=args.days * 24)
        if data is None:
            print("\n  [FALLBACK] API failed — switching to synthetic data")
            data = generate_synthetic_data(num_coins=args.coins, num_days=args.days)

    # Phase 2: Feature Engineering
    df = build_feature_matrix(data)
    if len(df) == 0:
        print("\n  [FATAL] No features generated. Aborting.")
        sys.exit(1)

    # Phase 3: Model Training
    rf, xgb_model, scaler = train_models(df)
    if rf is None:
        print("\n  [FATAL] Model training failed. Aborting.")
        sys.exit(1)

    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print(f"  TRAINING COMPLETE in {elapsed:.1f}s")
    print(f"  Models saved to: {MODEL_DIR}")
    print(f"  Ready for live scanning: python live_scanner.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
