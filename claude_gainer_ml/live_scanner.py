#!/usr/bin/env python3
"""
CLAUDE CODE — Live Crypto Top Gainer Scanner v4.0
==================================================
Real-time scanner that fetches current market data from Binance (with
multi-exchange failover), computes 30+ ML features, runs ensemble prediction,
ranks coins by pump probability, and generates picks with TP/SL levels.

v4.0: Wide universe scan (ALL Binance USDT pairs >$500K vol), volume velocity
      detection, adaptive thresholds for volume spikes, rapid pre-scan mode,
      and relative top-10 labeling for improved recall.
v3.0: Binance primary, 30 features, 3% TP target, yesterday-gainer edge.

Usage:
    python live_scanner.py [--top N] [--threshold 0.6] [--no-discord]
"""

import os
import sys
import json
import time
import math
import argparse
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import requests
import joblib

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Shared multi-source fetcher ──────────────────────────────────────────
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from shared.multi_source_fetcher import (
        fetch_klines as _shared_fetch_klines,
        fetch_current_price as _shared_fetch_price,
    )
    _HAS_SHARED_FETCHER = True
except Exception as _e:
    _HAS_SHARED_FETCHER = False
    print(f"[WARN] shared.multi_source_fetcher import failed: {_e}")

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
TRACKER_DIR = BASE_DIR / "tracker"

TRACKER_DIR.mkdir(parents=True, exist_ok=True)

LIVE_PICKS_FILE = TRACKER_DIR / "claude_live_picks.json"
SCAN_LOG_FILE = TRACKER_DIR / "claude_scan_log.json"
LOCK_FILE = TRACKER_DIR / "refresh_lock.json"

# ── Data fetcher (multi-source) ─────────────────────────────────────────
try:
    from data_fetcher import (fetch_all, fetch_yesterday_top_gainers,
                              get_sector, get_sector_performance)
    HAS_DATA_FETCHER = True
except ImportError:
    HAS_DATA_FETCHER = False
    print("[WARN] data_fetcher.py not found — using legacy CoinGecko mode")

# ── CoinGecko (legacy fallback) ─────────────────────────────────────────
CG_API_KEY = os.environ.get("COINGECKO_API_KEY", "")
if not CG_API_KEY:
    _kimi_env = Path(__file__).resolve().parent.parent / "KIMI_RISEOFTHECLAW" / ".env"
    if _kimi_env.exists():
        for _line in _kimi_env.read_text().splitlines():
            if _line.startswith("COINGECKO_API_KEY="):
                CG_API_KEY = _line.split("=", 1)[1].strip()
                break

_CG_BASE = "https://api.coingecko.com/api/v3"
CG_HEADERS = {"x-cg-demo-api-key": CG_API_KEY} if CG_API_KEY else {}
CG_MARKETS = f"{_CG_BASE}/coins/markets"
CG_OHLC = _CG_BASE + "/coins/{coin_id}/ohlc"
CG_MARKET_CHART = _CG_BASE + "/coins/{coin_id}/market_chart"
RATE_LIMIT_DELAY = 2.5
MAX_RETRIES = 4

# ── Binance (secondary fallback if data_fetcher fails) ──────────────────
_BINANCE_BASES = [
    "https://api.binance.com/api/v3",
    "https://data-api.binance.vision/api/v3",
    "https://api.binance.us/api/v3",
]
BINANCE_BASE = "https://api.binance.com/api/v3"

# ── Discord ──────────────────────────────────────────────────────────────
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
DISCORD_ML_CHANNEL_ID = os.environ.get("DISCORD_ML_CHANNEL_ID", "")
DISCORD_HEADER = "**CLAUDE CODE - REVERSE ENGINEERED DAILY TOP GAINERS STRAT -->**"
DASHBOARD_URL = "https://findtorontoevents.ca/updates/antigravity-ml-gainer.html"


def _fmt_price(val) -> str:
    """Format price without scientific notation."""
    if val is None or val == 0:
        return "$0"
    val = float(val)
    if val >= 1000:
        return f"${val:,.2f}"
    elif val >= 1:
        return f"${val:.4f}"
    elif val >= 0.001:
        return f"${val:.6f}"
    else:
        return f"${val:.10f}"

# ── Adaptive Threshold (v1.5: rebalanced — v1.4 was unreachable, 0 picks for 12 days) ──
DEFAULT_THRESHOLD = 0.65
# v1.5: Reduced boost — model max output ~25%, old 0.55+0.10=0.65 was impossible
BUY_THRESHOLD_BOOST = 0.02   # BUY needs threshold + 0.02 (effective ~0.27)
SELL_THRESHOLD_DISCOUNT = 0.05  # SELL can be threshold - 0.05
MIN_SL_DISTANCE_PCT = 0.008  # v1.4: min 0.8% SL distance
# v1.5: Relative ranking fallback — if nothing passes threshold, pick top N above floor
RELATIVE_RANKING_FLOOR = 0.50  # Minimum probability for relative picks (raised from 0.15)
RELATIVE_RANKING_MAX = 3       # Max picks in relative mode
ADAPTIVE_THRESHOLD_FILE = TRACKER_DIR / "adaptive_threshold.json"

# ── v4.0: Volume Velocity & Wide Universe constants ──────────────────────
VOLUME_VELOCITY_THRESHOLD = 3.0   # 1h vol > 3x avg hourly vol = volume spike
VOLUME_VELOCITY_EXTREME = 5.0     # >5x = extreme spike, lower prediction threshold
EXTREME_SPIKE_THRESHOLD = 0.45    # Prediction threshold for extreme volume spikes (raised from 0.15)
MIN_24H_VOLUME_USD = 500_000      # Minimum 24h volume to include a pair ($500K)
RAPID_SCAN_PRICE_CHANGE_MIN = 5.0 # Rapid scan: min +5% 1h change to flag
RAPID_SCAN_VOL_MULT_MIN = 3.0     # Rapid scan: min 3x volume spike to flag

# ── Feature definitions (must match train_model.py v3.0) ─────────────────
FEATURE_COLS = [
    "vol_mcap_ratio", "vol_change_24h", "vol_change_12h",
    "price_momentum_7d", "price_momentum_3d", "price_momentum_1d",
    "rsi_14", "rsi_slope", "bb_width", "bb_percentb",
    "consolidation_range", "consecutive_green", "momentum_ignition",
    "obv_divergence", "distance_from_ath_pct", "distance_from_atl_pct",
    "mcap_tier", "price_compression", "relative_volume_spike",
    "fear_greed_proxy",
    # v3.0 new features
    "is_yesterday_gainer", "yesterday_gain_pct",
    "sector_momentum", "sector_relative_strength",
    "hourly_volatility", "volume_acceleration",
    "high_low_range_24h", "green_bar_ratio_24h",
    "max_hourly_gain_24h", "multi_day_gainer",
]

# ── Regime-Aware Position Sizing ─────────────────────────────────────────
REGIME_SIZING = {
    # TESTING SPRINT: all max_picks set to 999 (were 2-8 per regime)
    "extreme_fear":  {"label": "Extreme Fear (F&G < 20)",  "kelly_mult": 1.5, "max_picks": 999},
    "fear":          {"label": "Fear (F&G 20-40)",         "kelly_mult": 1.2, "max_picks": 999},
    "neutral":       {"label": "Neutral (F&G 40-60)",      "kelly_mult": 1.0, "max_picks": 999},
    "greed":         {"label": "Greed (F&G 60-80)",        "kelly_mult": 0.6, "max_picks": 999},
    "extreme_greed": {"label": "Extreme Greed (F&G > 80)", "kelly_mult": 0.3, "max_picks": 999},
}


def get_regime_from_fg(fear_greed_value):
    if fear_greed_value < 20:
        return "extreme_fear"
    elif fear_greed_value < 40:
        return "fear"
    elif fear_greed_value < 60:
        return "neutral"
    elif fear_greed_value < 80:
        return "greed"
    else:
        return "extreme_greed"


# ═══════════════════════════════════════════════════════════════════════════
#  MODEL LOADING
# ═══════════════════════════════════════════════════════════════════════════

def load_models():
    rf_path = MODEL_DIR / "claude_rf.joblib"
    xgb_path = MODEL_DIR / "claude_xgb.joblib"
    scaler_path = MODEL_DIR / "claude_scaler.joblib"
    meta_path = MODEL_DIR / "training_meta.json"

    if not rf_path.exists() or not scaler_path.exists():
        print("[ERROR] Models not found. Run train_model.py first.")
        sys.exit(1)

    rf = joblib.load(rf_path)
    scaler = joblib.load(scaler_path)
    xgb_model = joblib.load(xgb_path) if xgb_path.exists() else None

    meta = {}
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)

    print(f"[MODEL] Loaded RF + {'XGB' if xgb_model else 'RF-only'} ensemble")
    print(f"[MODEL] Version: {meta.get('model_version', 'unknown')} | Features: {meta.get('num_features', '?')}")
    print(f"[MODEL] Trained: {meta.get('trained_at', 'unknown')}")
    if meta.get("metrics"):
        m = meta["metrics"]
        print(f"[MODEL] Test metrics — P:{m.get('precision',0):.3f} R:{m.get('recall',0):.3f} AUC:{m.get('roc_auc',0):.3f}")

    weights = meta.get("ensemble_weights", {"rf": 0.45, "xgb": 0.55})
    return rf, xgb_model, scaler, weights, meta


# ═══════════════════════════════════════════════════════════════════════════
#  FEATURE COMPUTATION (v3.0 — 30 features)
# ═══════════════════════════════════════════════════════════════════════════

def compute_rsi(closes, period=14):
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
        pctbs.append(max(0, min(1, (closes[i] - lower) / (upper - lower) if (upper - lower) > 0 else 0.5)))
    return widths, pctbs


def compute_obv(closes, volumes):
    obv = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i-1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    return obv


def compute_features_live(coin_data, yesterday_gainers=None, sector_perf=None):
    """Compute 30 features for a coin from live data.

    v3.0: Works with Binance 1h klines. Falls back to CoinGecko format.
    Returns a dict of feature values or None if insufficient data.
    """
    yesterday_gainers = yesterday_gainers or {}
    sector_perf = sector_perf or {}

    # Determine data source
    ohlcv_1h = coin_data.get("ohlcv_1h", [])
    has_1h = len(ohlcv_1h) >= 24

    if has_1h:
        bars = sorted(ohlcv_1h, key=lambda x: x[0])
        opens = [b[1] for b in bars]
        highs = [b[2] for b in bars]
        lows = [b[3] for b in bars]
        closes = [b[4] for b in bars]
        volumes = [b[5] for b in bars]
    else:
        # Legacy CoinGecko format
        ohlc = coin_data.get("ohlc", [])
        chart = coin_data.get("chart", {})
        volumes_raw = chart.get("total_volumes", [])
        if len(ohlc) < 15 or len(volumes_raw) < 15:
            return None

        ohlc_sorted = sorted(ohlc, key=lambda x: x[0])
        vol_sorted = sorted(volumes_raw, key=lambda x: x[0])
        opens = [bar[1] for bar in ohlc_sorted]
        highs = [bar[2] for bar in ohlc_sorted]
        lows = [bar[3] for bar in ohlc_sorted]
        closes = [bar[4] for bar in ohlc_sorted]

        vol_dict = {vt // 86400_000: vv for vt, vv in vol_sorted}
        volumes = []
        for bar in ohlc_sorted:
            dk = bar[0] // 86400_000
            vol = vol_dict.get(dk, 0)
            if vol == 0:
                for offset in [-1, 1, -2, 2]:
                    vol = vol_dict.get(dk + offset, 0)
                    if vol > 0:
                        break
            volumes.append(max(vol, 1.0))

    n = len(closes)
    i = n - 1
    c = closes[i]
    if c <= 0 or n < 15:
        return None

    mcap = coin_data.get("market_cap", 1e6) or 1e6
    ath = coin_data.get("ath", c * 2) or c * 2
    atl = coin_data.get("atl", c * 0.01) or c * 0.01
    pair = coin_data.get("pair", "")
    symbol = coin_data.get("symbol", pair.replace("USDT", ""))

    rsi_vals = compute_rsi(closes, 14)
    bb_widths, bb_pctbs = compute_bollinger(closes, min(20, n), 2)
    obv_vals = compute_obv(closes, volumes)

    # Use hourly lookback if 1h data, daily otherwise
    lb_24 = 24 if has_1h else 1
    lb_72 = 72 if has_1h else 3
    lb_168 = 168 if has_1h else 7

    # 1. vol_mcap_ratio
    vol_period = sum(volumes[max(0, i-lb_24+1):i+1])
    vol_mcap_ratio = vol_period / mcap if mcap > 0 else 0

    # 2. vol_change_24h
    avg_vol_base = sum(volumes[max(0, i-lb_168):max(0, i-lb_24)]) / max(lb_168 - lb_24, 1) * lb_24
    vol_change_24h = vol_period / avg_vol_base if avg_vol_base > 0 else 1.0

    # 3. vol_change_12h
    lb_12 = 12 if has_1h else 1
    v12a = sum(volumes[max(0, i-lb_12+1):i+1])
    v12b = sum(volumes[max(0, i-lb_24+1):max(0, i-lb_12+1)])
    vol_change_12h = v12a / v12b if v12b > 0 else 1.0

    # 4-6. Momentum
    c_7d = closes[max(0, i-lb_168)]
    c_3d = closes[max(0, i-lb_72)]
    c_1d = closes[max(0, i-lb_24)]
    pm7d = (c - c_7d) / c_7d * 100 if c_7d > 0 else 0
    pm3d = (c - c_3d) / c_3d * 100 if c_3d > 0 else 0
    pm1d = (c - c_1d) / c_1d * 100 if c_1d > 0 else 0

    # 7-8. RSI
    rsi_14 = rsi_vals[i]
    rsi_slope = rsi_vals[i] - rsi_vals[max(0, i-3)]

    # 9-10. Bollinger
    bb_width = bb_widths[i]
    bb_percentb = bb_pctbs[i]

    # 11. Consolidation range
    ranges = [(highs[j] - lows[j]) / closes[j] for j in range(max(0, i-lb_24+1), i+1) if closes[j] > 0]
    consolidation_range = sum(ranges) / len(ranges) if ranges else 0

    # 12. Consecutive green
    consec_green = 0
    for j in range(i, max(i-48, -1), -1):
        if closes[j] > opens[j]:
            consec_green += 1
        else:
            break

    # 13. Momentum ignition
    momentum_ignition = 0
    if consec_green >= 3:
        if all(volumes[i-k] > volumes[i-k-1] for k in range(min(3, i)) if i-k-1 >= 0):
            momentum_ignition = 1

    # 14. OBV divergence
    obv_trend = obv_vals[i] - obv_vals[max(0, i-lb_24)]
    price_trend = closes[i] - closes[max(0, i-lb_24)]
    obv_divergence = 1 if (obv_trend > 0 and price_trend < 0) or (obv_trend < 0 and price_trend > 0) else 0

    # 15-16. ATH/ATL
    dist_ath = (ath - c) / ath * 100 if ath > 0 else 0
    dist_atl = (c - atl) / atl * 100 if atl > 0 else 0

    # 17. Market cap tier
    mcap_tier = math.log10(max(mcap, 1)) / 12.0

    # 18. Price compression
    price_compression = 0
    if i >= 3:
        dr = [(highs[j] - lows[j]) / closes[j] for j in range(i-2, i+1) if closes[j] > 0]
        if len(dr) >= 3 and all(dr[k] < dr[k-1] for k in range(1, len(dr))):
            price_compression = 1

    # 19. Relative volume spike
    relative_volume_spike = 1 if vol_change_24h > 3.0 else 0

    # 20. Fear/greed proxy
    vol_dir = 1 if vol_change_24h > 1.2 else (-1 if vol_change_24h < 0.8 else 0)
    fear_greed_proxy = (rsi_14 / 100.0) * 0.6 + (vol_dir + 1) / 2 * 0.4

    # === New v3.0 features ===

    # 21-22. Yesterday gainer
    is_yg = 1 if pair in yesterday_gainers else 0
    yg_pct = yesterday_gainers.get(pair, {}).get("change_24h_pct", 0)

    # 23-24. Sector
    sector = get_sector(symbol) if HAS_DATA_FETCHER else "other"
    sector_mom = sector_perf.get(sector, 0)
    sector_rel = pm1d - sector_mom

    # 25. Hourly volatility
    hourly_vol = 0
    if has_1h and i >= 24:
        h_returns = [(closes[j] - closes[j-1]) / closes[j-1] for j in range(max(1, i-23), i+1) if closes[j-1] > 0]
        hourly_vol = np.std(h_returns) if len(h_returns) > 2 else 0
    else:
        hourly_vol = consolidation_range * 0.1

    # 26. Volume acceleration
    lb_6 = 6 if has_1h else 1
    v6r = sum(volumes[max(0, i-lb_6+1):i+1]) / lb_6
    v6p = sum(volumes[max(0, i-2*lb_6+1):max(0, i-lb_6+1)]) / lb_6 if i >= 2*lb_6 else v6r
    vol_accel = v6r / v6p if v6p > 0 else 1.0

    # 27. High-low range
    h24 = max(highs[max(0, i-lb_24+1):i+1])
    l24 = min(lows[max(0, i-lb_24+1):i+1])
    hl_range = (h24 - l24) / c if c > 0 else 0

    # 28. Green bar ratio
    green_count = sum(1 for j in range(max(0, i-lb_24+1), i+1) if closes[j] > opens[j])
    green_ratio = green_count / min(lb_24, i+1)

    # 29. Max hourly gain
    max_hgain = 0
    for j in range(max(1, i-lb_24+1), i+1):
        if closes[j-1] > 0:
            g = (closes[j] - closes[j-1]) / closes[j-1]
            if g > max_hgain:
                max_hgain = g

    # 30. Multi-day gainer
    multi_day = 0
    if i >= 3 * lb_24:
        d1 = (closes[i] - closes[i-lb_24]) / closes[i-lb_24] if closes[i-lb_24] > 0 else 0
        d2 = (closes[i-lb_24] - closes[i-2*lb_24]) / closes[i-2*lb_24] if closes[i-2*lb_24] > 0 else 0
        d3 = (closes[i-2*lb_24] - closes[i-3*lb_24]) / closes[i-3*lb_24] if closes[i-3*lb_24] > 0 else 0
        if d1 > 0.01 and d2 > 0.01 and d3 > 0.01:
            multi_day = 1

    # === v4.0: Volume velocity features ===
    vol_vel = compute_volume_velocity(ohlcv_1h if has_1h else [])

    return {
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
        "is_yesterday_gainer": is_yg,
        "yesterday_gain_pct": round(yg_pct, 2),
        "sector_momentum": round(sector_mom, 4),
        "sector_relative_strength": round(sector_rel, 4),
        "hourly_volatility": round(hourly_vol, 6),
        "volume_acceleration": round(vol_accel, 4),
        "high_low_range_24h": round(hl_range, 6),
        "green_bar_ratio_24h": round(green_ratio, 4),
        "max_hourly_gain_24h": round(max_hgain * 100, 4),
        "multi_day_gainer": multi_day,
        # v4.0 volume velocity features (not in model yet — used for threshold logic)
        "volume_velocity_1h": vol_vel["volume_velocity_1h"],
        "volume_velocity_6h": vol_vel["volume_velocity_6h"],
        "is_volume_spike": vol_vel["is_volume_spike"],
        "is_extreme_spike": vol_vel["is_extreme_spike"],
    }


# ═══════════════════════════════════════════════════════════════════════════
#  PREDICTION & PICK GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def _heuristic_pump_score(features: dict) -> float:
    """Heuristic pump probability using all 30 features when ML model is anti-predictive.

    Weighted combination of the most predictive features identified from
    the heuristic signal layer (61.54% WR empirical).  Returns 0.0-1.0.

    Weights (sum to 1.0):
      volume_change_24h  0.25  — strongest pump predictor
      price_momentum_1d  0.20  — recent price action
      rsi_14 (inverted)  0.15  — lower RSI = higher bounce potential
      bb_percentb        0.10  — Bollinger position
      momentum_ignition  0.10  — breakout flag
      obv_divergence     0.10  — volume confirmation
      consecutive_green  0.05  — streak momentum
      relative_volume_spike 0.05 — volume anomaly flag
    """
    # volume_change_24h: typically 0.5-10+, normalize via sigmoid-like mapping
    vol_24h = float(features.get("vol_change_24h", 1.0) or 1.0)
    vol_score = min(1.0, max(0.0, (vol_24h - 1.0) / 4.0))  # 1x->0, 5x->1

    # price_momentum_1d: typically -0.1 to 0.3, normalize
    mom_1d = float(features.get("price_momentum_1d", 0) or 0)
    mom_score = min(1.0, max(0.0, (mom_1d + 0.05) / 0.20))  # -5%->0, +15%->1

    # rsi_14: inverted — lower RSI = higher score (mean-reversion bounce)
    rsi = float(features.get("rsi_14", 50) or 50)
    rsi_score = min(1.0, max(0.0, (70 - rsi) / 50))  # RSI 20->1.0, RSI 70->0.0

    # bb_percentb: 0-1, values near 0 = near lower band (bounce potential)
    bb_pctb = float(features.get("bb_percentb", 0.5) or 0.5)
    # We want both oversold bounces (<0.2) and breakouts (>0.8)
    bb_score = 1.0 - abs(bb_pctb - 0.5) * 2 if 0.2 <= bb_pctb <= 0.8 else min(1.0, max(0.0, bb_pctb if bb_pctb > 0.5 else 1.0 - bb_pctb))

    # momentum_ignition: binary 0/1
    mom_ign = float(features.get("momentum_ignition", 0) or 0)

    # obv_divergence: binary 0/1
    obv_div = float(features.get("obv_divergence", 0) or 0)

    # consecutive_green: 0-10+, normalize
    consec = float(features.get("consecutive_green", 0) or 0)
    consec_score = min(1.0, consec / 5.0)  # 5+ greens -> 1.0

    # relative_volume_spike: binary 0/1
    rel_vol = float(features.get("relative_volume_spike", 0) or 0)

    # Weighted combination
    score = (
        0.25 * vol_score
        + 0.20 * mom_score
        + 0.15 * rsi_score
        + 0.10 * bb_score
        + 0.10 * mom_ign
        + 0.10 * obv_div
        + 0.05 * consec_score
        + 0.05 * rel_vol
    )
    return round(max(0.0, min(1.0, score)), 4)


def predict_coins(coins_with_features, rf, xgb_model, scaler, weights, model_meta):
    """Run ensemble prediction on all coins.
    Handles both 20-feature (v2) and 30-feature (v3) models gracefully.
    v4.1: Falls back to heuristic scoring when model AUC < 0.50 (anti-predictive)."""
    results = []
    model_features = model_meta.get("feature_names", FEATURE_COLS)

    # v4.2: Check if model is anti-predictive (AUC < 0.50 = worse than random)
    # If anti-correlated, FLIP predictions (AUC 0.40 becomes ~0.60)
    model_auc = (model_meta.get("metrics") or {}).get("roc_auc", 1.0)
    flip_predictions = model_auc < 0.50
    if flip_predictions:
        print(f"[v4.2] Model AUC={model_auc:.4f} < 0.50 — ANTI-CORRELATED, flipping predictions (effective AUC ~{1.0 - model_auc:.2f})")

    for item in coins_with_features:
        features = item["features"]

        # ML mode: always use ensemble prediction, flip if anti-correlated
        feature_vec = np.array([[features.get(col, 0) for col in model_features]])
        feature_vec = np.nan_to_num(feature_vec, nan=0.0, posinf=1e6, neginf=-1e6)
        feature_scaled = scaler.transform(feature_vec)

        rf_proba = rf.predict_proba(feature_scaled)[0][1]

        if xgb_model is not None:
            xgb_proba = xgb_model.predict_proba(feature_scaled)[0][1]
            ensemble_proba = weights.get("rf", 0.45) * rf_proba + weights.get("xgb", 0.55) * xgb_proba
        else:
            xgb_proba = None
            ensemble_proba = rf_proba

        # v4.2: Auto-flip when model is anti-correlated (AUC < 0.5)
        if flip_predictions:
            ensemble_proba = 1.0 - ensemble_proba
            rf_proba = 1.0 - rf_proba
            if xgb_proba is not None:
                xgb_proba = 1.0 - xgb_proba

        results.append({
            "coin_id": item.get("coin_id", item.get("pair", "")),
            "pair": item.get("pair", ""),
            "symbol": item["symbol"],
            "name": item.get("name", item["symbol"]),
            "current_price": item["current_price"],
            "market_cap": item.get("market_cap", 0),
            "pump_probability": round(float(ensemble_proba), 4),
            "rf_probability": round(float(rf_proba), 4),
            "xgb_probability": round(float(xgb_proba), 4) if xgb_proba is not None else None,
            "features": features,
            "source": item.get("source", "unknown"),
            "scoring_mode": "ml_flipped" if flip_predictions else "ml_ensemble",
        })

    results.sort(key=lambda x: x["pump_probability"], reverse=True)
    return results


def _check_btc_trend():
    """v1.4: Check BTC trend using multiple timeframes (4h, 12h, EMA).
    Returns ('bearish', reason) or ('bullish', None).
    Tries Binance first, falls back to OKX."""
    try:
        klines_raw = _fetch_binance_klines("BTCUSDT", "1h", 50)
        if not klines_raw:
            return "unknown", None
        closes = [bar[4] for bar in klines_raw]
        if len(closes) < 50:
            return "unknown", None

        current = closes[-1]
        price_4h_ago = closes[-4] if len(closes) >= 4 else current
        price_12h_ago = closes[-12] if len(closes) >= 12 else current

        # EMA20 and EMA50
        ema20 = sum(closes[-20:]) / 20
        ema50 = sum(closes[-50:]) / 50

        chg_4h = (current - price_4h_ago) / price_4h_ago
        chg_12h = (current - price_12h_ago) / price_12h_ago

        # v1.4: OR logic — any single bearish signal blocks BUY
        if chg_4h < -0.003:  # 0.3% drop in 4h
            return "bearish", f"BTC -4h: {chg_4h:.2%}"
        if chg_12h < -0.005:  # 0.5% drop in 12h
            return "bearish", f"BTC -12h: {chg_12h:.2%}"
        if current < ema20 and current < ema50:
            return "bearish", f"BTC below EMA20({ema20:.0f}) & EMA50({ema50:.0f})"

        return "bullish", None
    except Exception:
        return "unknown", None


def generate_picks(ranked_coins, threshold=0.5, max_picks=10, regime_info=None):
    """Generate TP/SL picks from top-ranked coins.
    v1.4: Asymmetric BUY/SELL thresholds, BTC trend filter, per-symbol dedup,
          min SL distance 0.8%."""
    picks = []
    now = datetime.now(timezone.utc)
    seen_symbols = set()  # v1.4: per-symbol dedup (max 1 position per coin)

    if regime_info:
        max_picks = min(max_picks, regime_info.get("max_picks", max_picks))

    # v1.5: BTC trend check — mild penalty in bearish (was +0.05, now +0.01)
    btc_trend, btc_reason = _check_btc_trend()
    if btc_trend == "bearish":
        print(f"[v1.5] BTC BEARISH ({btc_reason}) — BUY threshold nudged +0.01")

    # v1.5: Asymmetric threshold — BUY needs slightly higher confidence
    buy_threshold = threshold + BUY_THRESHOLD_BOOST
    sell_threshold = max(threshold - SELL_THRESHOLD_DISCOUNT, 0.15)
    if btc_trend == "bearish":
        buy_threshold += 0.01  # v1.5: mild penalty (was 0.05)

    candidates = [c for c in ranked_coins if c["pump_probability"] >= sell_threshold]

    # v1.5: Relative ranking fallback — if nothing passes buy_threshold,
    # pick top RELATIVE_RANKING_MAX coins above RELATIVE_RANKING_FLOOR
    if not candidates:
        fallback = [c for c in ranked_coins if c["pump_probability"] >= RELATIVE_RANKING_FLOOR]
        fallback.sort(key=lambda x: x["pump_probability"], reverse=True)
        candidates = fallback[:RELATIVE_RANKING_MAX]
        if candidates:
            print(f"[v1.5] RELATIVE RANKING: {len(candidates)} picks above floor {RELATIVE_RANKING_FLOOR}")
            buy_threshold = RELATIVE_RANKING_FLOOR  # Use floor as effective threshold
        else:
            return []

    all_probs = [c["pump_probability"] for c in ranked_coins]
    p95 = np.percentile(all_probs, 95) if len(all_probs) > 10 else 0.7
    p80 = np.percentile(all_probs, 80) if len(all_probs) > 10 else 0.6
    p60 = np.percentile(all_probs, 60) if len(all_probs) > 10 else 0.5

    for coin in candidates[:max_picks * 2]:  # Check more candidates to allow filtering
        if len(picks) >= max_picks:
            break

        price = coin["current_price"]
        if price <= 0:
            continue

        prob = coin["pump_probability"]
        symbol = coin["symbol"]

        # v1.4: Per-symbol dedup
        if symbol in seen_symbols:
            continue

        # v4.0: Lower threshold for coins with extreme volume spikes
        # These are likely already pumping — don't miss them due to model uncertainty
        effective_buy_threshold = buy_threshold
        vol_vel_1h = coin["features"].get("volume_velocity_1h", 1.0)
        is_extreme = coin["features"].get("is_extreme_spike", 0)
        if is_extreme or vol_vel_1h >= VOLUME_VELOCITY_EXTREME:
            effective_buy_threshold = min(buy_threshold, EXTREME_SPIKE_THRESHOLD)
        elif coin["features"].get("is_volume_spike", 0) or vol_vel_1h >= VOLUME_VELOCITY_THRESHOLD:
            # Moderate spike: small threshold reduction
            effective_buy_threshold = min(buy_threshold, buy_threshold - 0.05)

        # v1.4: For BUY signals, apply threshold (v4.0: adaptive per coin)
        if prob < effective_buy_threshold:
            continue

        # v1.4: SL distance min 0.8% — prevent gap-through on volatile assets
        volatility = coin["features"].get("hourly_volatility", 0.02)
        sl_pct = max(0.05, MIN_SL_DISTANCE_PCT * 6, volatility * 3)  # At least 4.8%, or 3x hourly vol
        sl_price = round(price * (1 - sl_pct), 8)

        tp1_price = round(price * 1.03, 8)  # v3: 3% TP1
        tp2_price = round(price * 1.08, 8)  # 8% TP2

        seen_symbols.add(symbol)

        prob = coin["pump_probability"]
        if prob >= p95:
            confidence = "VERY HIGH"
        elif prob >= p80:
            confidence = "HIGH"
        elif prob >= p60:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        signals = []
        f = coin["features"]
        if f.get("momentum_ignition", 0) == 1:
            signals.append("MOMENTUM_IGNITION")
        if f.get("vol_change_24h", 0) > 2.0:
            signals.append(f"VOL_SPIKE ({f['vol_change_24h']:.1f}x)")
        if f.get("price_compression", 0) == 1:
            signals.append("COMPRESSION_BREAKOUT")
        if f.get("obv_divergence", 0) == 1:
            signals.append("OBV_DIVERGENCE")
        if f.get("consecutive_green", 0) >= 3:
            signals.append(f"GREEN_STREAK ({f['consecutive_green']})")
        if f.get("is_yesterday_gainer", 0) == 1:
            signals.append(f"YESTERDAY_GAINER (+{f.get('yesterday_gain_pct', 0):.1f}%)")
        if f.get("multi_day_gainer", 0) == 1:
            signals.append("MULTI_DAY_MOMENTUM")
        if f.get("rsi_14", 50) < 30:
            signals.append("OVERSOLD")
        if f.get("relative_volume_spike", 0) == 1:
            signals.append("EXTREME_VOLUME")
        # v4.0: Volume velocity signals
        if f.get("is_extreme_spike", 0) == 1:
            signals.append(f"VOL_VELOCITY_EXTREME ({f.get('volume_velocity_1h', 0):.1f}x)")
        elif f.get("is_volume_spike", 0) == 1:
            signals.append(f"VOL_VELOCITY_SPIKE ({f.get('volume_velocity_1h', 0):.1f}x)")

        feature_snapshot = {col: float(coin["features"].get(col, 0)) for col in FEATURE_COLS}

        pick = {
            "pick_id": f"claude_{coin['symbol'].lower()}_{now.strftime('%Y%m%d_%H%M')}",
            "coin_id": coin.get("coin_id", ""),
            "pair": coin.get("pair", f"{coin['symbol']}USDT"),
            "symbol": coin["symbol"],
            "name": coin["name"],
            "entry_price": price,
            "tp1_price": tp1_price, "tp1_pct": 3.0,
            "tp2_price": tp2_price, "tp2_pct": 8.0,
            "sl_price": sl_price, "sl_pct": -5.0,
            "time_exit_bars": 48, "bar_size": "1H",
            "pump_probability": prob,
            "confidence": confidence,
            "signals": signals,
            "features": feature_snapshot,
            "market_cap": coin.get("market_cap", 0),
            "entry_time": now.isoformat(),
            "expiry_time": (now + timedelta(hours=48)).isoformat(),
            "status": "ACTIVE",
            "tp1_hit": False, "tp2_hit": False, "sl_hit": False,
            "exit_price": None, "exit_time": None, "exit_reason": None,
            "pnl_pct": None,
            "metric_type": "FORWARD",
            "source": coin.get("source", "unknown"),
            "regime": regime_info.get("regime", "unknown") if regime_info else "unknown",
            "fear_greed": regime_info.get("fear_greed", 50) if regime_info else 50,
            "kelly_mult": regime_info.get("kelly_mult", 1.0) if regime_info else 1.0,
        }
        # Emission gate: cooldown + daily cap (shared with alpha_engine).
        try:
            from alpha_engine.non_crypto_policy import check_emission_gates as _ceg
            _g = _ceg(str(pick.get("symbol") or ""))
            if _g.get("blocked"):
                continue
        except Exception:
            pass
        picks.append(pick)

    return picks


# ═══════════════════════════════════════════════════════════════════════════
#  DISCORD ALERTS
# ═══════════════════════════════════════════════════════════════════════════

def send_discord_alert(picks, scan_summary):
    if not DISCORD_WEBHOOK_URL:
        print("[DISCORD] No webhook URL configured — skipping alert")
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    embed_fields = []
    for pick in picks[:8]:
        signals_str = " | ".join(pick["signals"][:3]) if pick["signals"] else "ML Signal"
        embed_fields.append({
            "name": f"{pick['symbol']} — {pick['confidence']} ({pick['pump_probability']:.0%})",
            "value": (
                f"Entry: {_fmt_price(pick['entry_price'])}\n"
                f"TP1: {_fmt_price(pick['tp1_price'])} (+3%)\n"
                f"TP2: {_fmt_price(pick['tp2_price'])} (+8%)\n"
                f"SL: {_fmt_price(pick['sl_price'])} (-5%)\n"
                f"Signals: {signals_str}"
            ),
            "inline": False,
        })

    regime_str = ""
    if picks and picks[0].get("regime", "unknown") != "unknown":
        regime_str = f" | Regime: {picks[0]['regime']} (F&G={picks[0].get('fear_greed', '?')})"

    payload = {
        "content": f"Captain Hook: {DISCORD_HEADER}",
        "embeds": [{
            "title": f"Top Gainer Predictions v3.0 — {now}",
            "description": (
                f"Scanned {scan_summary['coins_scanned']} coins | "
                f"{scan_summary['coins_with_features']} analyzed | "
                f"{len(picks)} picks{regime_str}\n"
                f"Data: {scan_summary.get('data_source', 'multi-exchange')}\n\n"
                f"[**View Full Dashboard**]({DASHBOARD_URL})"
            ),
            "color": 0x00ff88,
            "fields": embed_fields,
            "footer": {"text": "CLAUDE CODE ML v3.0 | 30 features | Binance+failover | Not financial advice"},
        }],
    }

    status_file = TRACKER_DIR / "dashboard_status.json"
    try:
        status_data = {
            "status": "idle",
            "message": f"Last scan: {len(picks)} new picks at {now}",
            "eta_seconds": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "triggered_by": "live_scanner_v3",
            "active_picks": len(picks),
        }
        with open(status_file, "w") as sf:
            json.dump(status_data, sf, indent=2)
    except Exception:
        pass

    for _attempt in range(3):
        try:
            r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            if r.status_code in (200, 204):
                print(f"[DISCORD] Alert sent ({len(picks)} picks)")
                break
            if r.status_code == 429:
                import time as _dtime
                _dtime.sleep(r.json().get("retry_after", 3))
                continue
            print(f"[DISCORD] Alert failed: {r.status_code}")
            if _attempt < 2:
                import time as _dtime
                _dtime.sleep(2 * (_attempt + 1))
                continue
            break
        except Exception as e:
            if _attempt == 2:
                print(f"[DISCORD] Error after 3 attempts: {e}")
            else:
                import time as _dtime
                _dtime.sleep(2 * (_attempt + 1))


# ═══════════════════════════════════════════════════════════════════════════
#  THRESHOLD
# ═══════════════════════════════════════════════════════════════════════════

def get_adaptive_threshold():
    if ADAPTIVE_THRESHOLD_FILE.exists():
        try:
            with open(ADAPTIVE_THRESHOLD_FILE) as f:
                data = json.load(f)
            t = data.get("threshold", DEFAULT_THRESHOLD)
            print(f"[THRESHOLD] Adaptive: {t:.2f}")
            return t
        except Exception:
            pass
    return DEFAULT_THRESHOLD


def update_adaptive_threshold(resolved_picks):
    """v2.0: Raised floor/ceiling to combat class imbalance — floor 0.55, ceiling 0.80."""
    if len(resolved_picks) < 5:
        return
    recent = resolved_picks[-30:]
    wins = sum(1 for p in recent if (p.get("pnl_pct") or 0) > 0)
    wr = wins / len(recent) if recent else 0
    current = get_adaptive_threshold()

    # v2.0: Higher floor/ceiling — be selective, not permissive
    if wr < 0.30 and current < 0.80:
        new_t = min(current + 0.02, 0.80)  # Ceiling 0.80
        reason = f"WR {wr:.0%} too low — tightening"
    elif wr > 0.50 and current > 0.55:
        new_t = max(current - 0.02, 0.55)  # Floor 0.55
        reason = f"WR {wr:.0%} strong — relaxing"
    else:
        return

    data = {
        "threshold": round(new_t, 3), "previous": round(current, 3),
        "win_rate": round(wr, 3), "sample_size": len(recent),
        "reason": reason, "updated_at": datetime.now(timezone.utc).isoformat(),
        "version": "v1.4",
    }
    with open(ADAPTIVE_THRESHOLD_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[THRESHOLD] {current:.2f} -> {new_t:.2f} ({reason})")


# ═══════════════════════════════════════════════════════════════════════════
#  v4.0: RELATIVE TOP-10 LABELING FOR TRAINING
# ═══════════════════════════════════════════════════════════════════════════

def label_with_relative_ranking(coins_with_next_day_gains, top_k=10, min_abs_gain=1.0):
    """Improved labeling: a coin is a positive label if it was in the TOP K gainers
    the next day, regardless of absolute gain percentage.

    This fixes the problem where a fixed +X% threshold misses moderate but
    relatively strong gainers during low-volatility periods.

    Args:
        coins_with_next_day_gains: list of dicts with 'symbol' and 'next_day_gain_pct'
        top_k: number of top gainers to label as positive (default 10)
        min_abs_gain: minimum absolute gain to qualify (prevents labeling losers as positive)

    Returns:
        dict mapping symbol -> label (1=gainer, 0=not)
    """
    if not coins_with_next_day_gains:
        return {}

    # Sort by next-day gain descending
    sorted_coins = sorted(coins_with_next_day_gains,
                          key=lambda x: x.get("next_day_gain_pct", 0), reverse=True)

    labels = {}
    positive_count = 0
    for coin in sorted_coins:
        sym = coin.get("symbol", "")
        gain = coin.get("next_day_gain_pct", 0)

        # Label as positive if in top K AND gained at least min_abs_gain%
        if positive_count < top_k and gain >= min_abs_gain:
            labels[sym] = 1
            positive_count += 1
        else:
            labels[sym] = 0

    return labels


def save_training_snapshot(coins_with_features, rapid_flagged=None):
    """Save current scan data for later training with next-day outcome labels.

    Called at end of each scan. The training pipeline can later merge these
    snapshots with actual next-day price data to create labeled training sets
    with the relative top-10 labeling approach.
    """
    snapshot_dir = DATA_DIR / "training_snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    filename = snapshot_dir / f"snapshot_{now.strftime('%Y%m%d_%H%M')}.json"

    snapshot = {
        "timestamp": now.isoformat(),
        "coins": [],
        "rapid_flagged_pairs": [f["pair"] for f in (rapid_flagged or [])],
    }

    for item in coins_with_features:
        snapshot["coins"].append({
            "pair": item.get("pair", ""),
            "symbol": item.get("symbol", ""),
            "current_price": item.get("current_price", 0),
            "features": item.get("features", {}),
            "source": item.get("source", ""),
        })

    try:
        with open(filename, "w") as f:
            json.dump(snapshot, f)
        # Keep only last 7 days of snapshots (7 * 48 = 336 files at 30-min intervals)
        snapshots = sorted(snapshot_dir.glob("snapshot_*.json"))
        if len(snapshots) > 336:
            for old in snapshots[:-336]:
                old.unlink()
    except Exception as e:
        print(f"[SNAPSHOT] Failed to save training snapshot: {e}")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN SCAN LOOP
# ═══════════════════════════════════════════════════════════════════════════

def run_scan(top_n=200, threshold=None, max_picks=10, send_alerts=True, kline_bars=168):
    """Execute one full scan cycle."""
    if LOCK_FILE.exists():
        try:
            with open(LOCK_FILE, 'r') as f:
                lock_data = json.load(f)
            if time.time() - lock_data.get('timestamp', 0) < 300:
                print(f"[LOCK] Refresh in progress, skipping scan")
                return []
        except Exception:
            pass

    try:
        with open(LOCK_FILE, 'w') as f:
            json.dump({'timestamp': time.time(), 'triggered_by': 'auto_scan'}, f)
    except Exception:
        pass

    if threshold is None:
        threshold = get_adaptive_threshold()

    print("\n" + "=" * 70)
    print("  CLAUDE CODE — Live Crypto Gainer Scanner v3.1 (v1.4 fixes)")
    print("  Binance primary + 30 features + asymmetric thresholds + BTC filter")
    print("=" * 70)
    print(f"  Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Coins: top {top_n} | Threshold: {threshold:.2f} | Max picks: {max_picks}")
    print(f"  Data fetcher: {'multi-source' if HAS_DATA_FETCHER else 'CoinGecko legacy'}")

    t0 = time.time()

    # Load models
    rf, xgb_model, scaler, weights, model_meta = load_models()

    # Regime detection
    regime_info = None
    fg_val = None
    # F&G failover: alternative.me (with retry) → CoinGecko BTC proxy
    for _fng_attempt in range(3):
        try:
            fg_resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
            if fg_resp.ok:
                fg_val = int(fg_resp.json().get("data", [{}])[0].get("value", 50))
                break
        except Exception:
            pass
        if _fng_attempt < 2:
            import time as _ftime
            _ftime.sleep(2 * (_fng_attempt + 1))
    if fg_val is None:
        try:
            cg_resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
                timeout=8,
            )
            if cg_resp.ok:
                change = float(cg_resp.json()["bitcoin"]["usd_24h_change"])
                fg_val = int(max(5, min(95, 50 + change * 4)))
                print(f"[REGIME] F&G fallback via CoinGecko BTC proxy: {fg_val}")
        except Exception:
            pass
    if fg_val is None:
        fg_val = 50
        print("[REGIME] F&G all sources failed, using neutral default 50")
    try:
        regime_key = get_regime_from_fg(fg_val)
        regime_data = REGIME_SIZING[regime_key]
        regime_info = {
            "regime": regime_key, "fear_greed": fg_val,
            "kelly_mult": regime_data["kelly_mult"],
            "max_picks": regime_data["max_picks"],
            "label": regime_data["label"],
        }
        print(f"[REGIME] F&G={fg_val} -> {regime_data['label']}")
    except Exception as e:
        print(f"[REGIME] Regime setup failed ({e})")

    # Fetch data (v4: wide universe + multi-source)
    data_source = "unknown"
    coins_data = {}
    yesterday_gainers = {}
    sector_perf = {}
    rapid_flagged = []

    # v4.0: Step 1 — Wide universe scan: get ALL Binance USDT pairs with volume
    print("\n[v4.0] Step 1: Wide universe scan — fetching ALL Binance USDT pairs...")
    wide_universe = _fetch_all_binance_usdt_pairs(min_volume_usd=MIN_24H_VOLUME_USD)

    # v4.0: Step 2 — Rapid volume scan: flag coins already pumping
    if wide_universe:
        print("[v4.0] Step 2: Rapid volume pre-scan...")
        rapid_flagged = _rapid_volume_scan(wide_universe)
        rapid_pairs = {f["pair"] for f in rapid_flagged}
        print(f"[v4.0] {len(rapid_flagged)} coins flagged for priority analysis")

    if HAS_DATA_FETCHER:
        print("\n[SCAN] Fetching data (Binance primary + failover)...")
        coins_data = fetch_all(num_coins=top_n, kline_bars=kline_bars, enrich_mcap=True)
        yesterday_gainers = fetch_yesterday_top_gainers(top_n=30)
        sector_perf = get_sector_performance()
        if coins_data:
            sample = next(iter(coins_data.values()))
            data_source = sample.get("source", "multi-source")

    if not coins_data or len(coins_data) < 10:
        # Legacy fallback
        print("[SCAN] Falling back to CoinGecko...")
        data_source = "coingecko_legacy"
        coins_data = _fetch_coingecko_legacy(top_n)

    # v4.0: Step 3 — Merge wide universe pairs not already in coins_data
    # Prioritize rapid-flagged pairs, then add remaining high-volume pairs
    wide_added = 0
    if wide_universe:
        # First: add all rapid-flagged pairs that aren't already scanned
        priority_pairs = [p for p in rapid_flagged if p["pair"] not in coins_data]
        # Then: add remaining wide universe pairs sorted by volume
        remaining = [(p, d) for p, d in wide_universe.items()
                     if p not in coins_data and p not in {f["pair"] for f in priority_pairs}]
        remaining.sort(key=lambda x: x[1]["volume_24h"], reverse=True)

        for flag in priority_pairs:
            pair = flag["pair"]
            if pair in wide_universe:
                ticker = wide_universe[pair]
                # Fetch 1h klines for this pair
                ohlcv_1h = _fetch_binance_klines(pair, "1h", kline_bars)
                if ohlcv_1h and len(ohlcv_1h) >= 24:
                    coins_data[pair] = {
                        "pair": pair,
                        "symbol": ticker["symbol"],
                        "name": ticker["symbol"],
                        "current_price": ticker["current_price"],
                        "market_cap": 0,  # Not available from ticker
                        "volume_24h": ticker["volume_24h"],
                        "change_24h_pct": ticker.get("change_24h_pct", 0),
                        "high_24h": ticker.get("high_24h", 0),
                        "low_24h": ticker.get("low_24h", 0),
                        "ath": ticker.get("high_24h", 0) * 1.5,  # Rough estimate
                        "atl": ticker.get("low_24h", 0) * 0.5,
                        "ohlcv_1h": ohlcv_1h,
                        "source": "binance_wide_priority",
                    }
                    wide_added += 1
            # Rate limit: don't hammer the API
            if wide_added > 0 and wide_added % 10 == 0:
                time.sleep(0.5)

        # Add remaining high-volume pairs (cap at 100 extra to avoid too many API calls)
        max_extra = min(100, len(remaining))
        for pair, ticker in remaining[:max_extra]:
            ohlcv_1h = _fetch_binance_klines(pair, "1h", kline_bars)
            if ohlcv_1h and len(ohlcv_1h) >= 24:
                coins_data[pair] = {
                    "pair": pair,
                    "symbol": ticker["symbol"],
                    "name": ticker["symbol"],
                    "current_price": ticker["current_price"],
                    "market_cap": 0,
                    "volume_24h": ticker["volume_24h"],
                    "change_24h_pct": ticker.get("change_24h_pct", 0),
                    "high_24h": ticker.get("high_24h", 0),
                    "low_24h": ticker.get("low_24h", 0),
                    "ath": ticker.get("high_24h", 0) * 1.5,
                    "atl": ticker.get("low_24h", 0) * 0.5,
                    "ohlcv_1h": ohlcv_1h,
                    "source": "binance_wide",
                }
                wide_added += 1
            if wide_added > 0 and wide_added % 20 == 0:
                time.sleep(0.5)

        if wide_added > 0:
            print(f"[v4.0] Added {wide_added} extra pairs from wide universe scan")

    print(f"[SCAN] Got {len(coins_data)} coins from {data_source} + wide universe")

    # Compute features
    print(f"\n[SCAN] Computing 30 features for {len(coins_data)} coins...")
    coins_with_features = []

    for idx, (pair, coin) in enumerate(coins_data.items()):
        symbol = coin.get("symbol", pair.replace("USDT", ""))

        features = compute_features_live(coin, yesterday_gainers, sector_perf)
        if features:
            coins_with_features.append({
                "pair": pair,
                "coin_id": coin.get("coin_id", pair),
                "symbol": symbol,
                "name": coin.get("name", symbol),
                "current_price": coin.get("current_price", 0),
                "market_cap": coin.get("market_cap", 0),
                "features": features,
                "source": coin.get("source", data_source),
            })

        if (idx + 1) % 50 == 0:
            print(f"  [{idx+1}/{len(coins_data)}] {len(coins_with_features)} with valid features")

    print(f"\n[SCAN] Features computed for {len(coins_with_features)} coins")

    if not coins_with_features:
        print("[ERROR] No coins with valid features")
        _release_lock()
        return []

    # Predict
    print("\n[PREDICT] Running ensemble predictions...")
    ranked = predict_coins(coins_with_features, rf, xgb_model, scaler, weights, model_meta)

    # Print top 20
    print("\n  " + "-" * 75)
    print(f"  {'#':>3} {'Symbol':<8} {'Name':<18} {'Price':>12} {'P(gain)':>8} {'Src':>6} {'Signals'}")
    print("  " + "-" * 75)
    for idx, coin in enumerate(ranked[:20]):
        sig_count = sum([
            coin["features"].get("momentum_ignition", 0),
            1 if coin["features"].get("vol_change_24h", 0) > 2.0 else 0,
            coin["features"].get("price_compression", 0),
            coin["features"].get("is_yesterday_gainer", 0),
            coin["features"].get("multi_day_gainer", 0),
        ])
        marker = " ***" if coin["pump_probability"] >= threshold else ""
        src = coin.get("source", "?")[:6]
        print(f"  {idx+1:>3} {coin['symbol']:<8} {coin['name'][:18]:<18} ${coin['current_price']:>10.6f} {coin['pump_probability']:>7.1%} {src:>6} {sig_count}sig{marker}")

    # Generate picks
    picks = generate_picks(ranked, threshold=threshold, max_picks=max_picks, regime_info=regime_info)

    # Merge with existing
    existing_picks = []
    if LIVE_PICKS_FILE.exists():
        with open(LIVE_PICKS_FILE) as f:
            existing_data = json.load(f)
            existing_picks = existing_data.get("picks", [])

    active_symbols = {p["symbol"] for p in existing_picks if p.get("status") == "ACTIVE"}
    new_picks = [p for p in picks if p["symbol"] not in active_symbols]
    all_picks = existing_picks + new_picks

    picks_data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "scanner_version": "3.1.0-v1.4",
        "total_active": sum(1 for p in all_picks if p.get("status") == "ACTIVE"),
        "total_resolved": sum(1 for p in all_picks if p.get("status") != "ACTIVE"),
        "picks": all_picks,
    }
    with open(LIVE_PICKS_FILE, "w") as f:
        json.dump(picks_data, f, indent=2)
    print(f"\n[PICKS] {len(new_picks)} new picks ({len(all_picks)} total)")

    _release_lock()

    elapsed = time.time() - t0
    scan_summary = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "coins_scanned": len(coins_data),
        "coins_with_features": len(coins_with_features),
        "picks_generated": len(new_picks),
        "threshold": threshold,
        "top_coin": ranked[0]["symbol"] if ranked else None,
        "top_probability": ranked[0]["pump_probability"] if ranked else 0,
        "regime": regime_info.get("regime", "unknown") if regime_info else "unknown",
        "fear_greed": regime_info.get("fear_greed", 50) if regime_info else 50,
        "data_source": data_source,
        "scanner_version": "3.1.0-v1.4",
    }

    scan_log = []
    if SCAN_LOG_FILE.exists():
        with open(SCAN_LOG_FILE) as f:
            scan_log = json.load(f)
    scan_log.append(scan_summary)
    scan_log = scan_log[-200:]
    with open(SCAN_LOG_FILE, "w") as f:
        json.dump(scan_log, f, indent=2)

    # v4.2: Write gainer predictions bridge file for Alpha Engine integration
    _write_gainer_predictions_bridge(ranked)

    if send_alerts and new_picks:
        send_discord_alert(new_picks, scan_summary)

    print(f"\n[DONE] Scan complete in {elapsed:.1f}s")
    for p in new_picks:
        print(f"    {p['symbol']:>8} | {p['confidence']:>10} | P={p['pump_probability']:.1%} | "
              f"Entry=${p['entry_price']:.6f} | TP1=${p['tp1_price']:.6f} | SL=${p['sl_price']:.6f}")

    return new_picks


def _release_lock():
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass


def _write_gainer_predictions_bridge(ranked_coins):
    """Write per-symbol pump probability to JSON for Alpha Engine integration.

    Output: claude_gainer_ml/data/gainer_predictions.json
    Format: {symbol: {prob_gainer: 0.XX, predicted_gain_pct: X.X, scoring_mode: "..."}}

    The Alpha Engine scanner can read this file and use prob_gainer as an
    additional feature or filter for its own signals.
    """
    BRIDGE_FILE = DATA_DIR / "gainer_predictions.json"
    predictions = {}

    for coin in ranked_coins:
        symbol = coin.get("symbol", "")
        if not symbol:
            continue
        prob = coin.get("pump_probability", 0)
        # Estimate predicted gain from probability (linear mapping: 0.5->3%, 1.0->15%)
        predicted_gain = max(0, (prob - 0.3) * 21.4)  # 0.3->0%, 1.0->15%

        predictions[symbol] = {
            "prob_gainer": round(prob, 4),
            "predicted_gain_pct": round(predicted_gain, 2),
            "scoring_mode": coin.get("scoring_mode", "unknown"),
            "price": coin.get("current_price", 0),
            "source": coin.get("source", "unknown"),
        }

    bridge_data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": "v4.2",
        "total_symbols": len(predictions),
        "predictions": predictions,
    }

    try:
        with open(BRIDGE_FILE, "w") as f:
            json.dump(bridge_data, f, indent=2)
        print(f"[BRIDGE] Wrote {len(predictions)} predictions to {BRIDGE_FILE}")
    except Exception as e:
        print(f"[BRIDGE] Failed to write predictions: {e}")


def _fetch_binance_klines(symbol, interval="1h", limit=168):
    """Fetch klines from Binance (with endpoint failover), OKX fallback, then shared multi-source failover."""
    for _bbase in _BINANCE_BASES:
        try:
            r = requests.get(
                f"{_bbase}/klines",
                params={"symbol": symbol, "interval": interval, "limit": limit},
                timeout=10,
            )
            if r.ok:
                data = r.json()
                return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]),
                          float(k[4]), float(k[5])] for k in data]
            elif r.status_code in (451, 403):
                continue  # geo-blocked, try next base
        except Exception:
            continue
    # All Binance endpoints failed — try OKX
    result = _fetch_okx_klines_raw(symbol, interval, limit)
    if result:
        return result
    # OKX also failed — try shared multi-source failover
    if _HAS_SHARED_FETCHER:
        return _shared_fetch_klines(symbol, interval, limit)
    return []


_OKX_INTERVAL_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1H", "4h": "4H", "1d": "1D",
}


def _fetch_okx_klines_raw(symbol, interval="1h", limit=168):
    """Fetch klines from OKX as fallback when Binance is geo-blocked."""
    if symbol.endswith("USDT"):
        okx_inst = symbol[:-4] + "-USDT"
    else:
        return []
    okx_bar = _OKX_INTERVAL_MAP.get(interval, interval)
    try:
        r = requests.get(
            "https://www.okx.com/api/v5/market/candles",
            params={"instId": okx_inst, "bar": okx_bar, "limit": str(min(limit, 300))},
            timeout=10,
        )
        if r.ok:
            candles = r.json().get("data", [])
            # OKX returns newest first, reverse it
            candles = list(reversed(candles))
            return [[int(c[0]), float(c[1]), float(c[2]), float(c[3]),
                      float(c[4]), float(c[5])] for c in candles]
    except Exception:
        pass
    return []


def _sparkline_to_ohlcv(sparkline_prices, current_price=0, volume_24h=0):
    """Convert CoinGecko sparkline (hourly closes for 7 days) into synthetic OHLCV bars.

    Sparkline gives ~168 hourly close prices. We synthesize O/H/L from adjacent closes
    and distribute volume evenly. This is approximate but sufficient for feature computation.
    """
    if not sparkline_prices or len(sparkline_prices) < 24:
        return []

    bars = []
    avg_vol = max(volume_24h / 24, 1.0)  # rough hourly volume estimate
    now_ms = int(time.time() * 1000)
    n = len(sparkline_prices)

    for i in range(n):
        close = sparkline_prices[i]
        if close is None or close <= 0:
            continue
        # Synthesize OHLC from close prices
        prev_close = sparkline_prices[i - 1] if i > 0 and sparkline_prices[i - 1] else close
        open_price = prev_close
        high = max(open_price, close) * 1.002  # small synthetic wick
        low = min(open_price, close) * 0.998
        ts = now_ms - (n - i) * 3600_000  # approximate timestamp
        bars.append([ts, open_price, high, low, close, avg_vol])

    return bars


# ═══════════════════════════════════════════════════════════════════════════
#  v4.0: WIDE UNIVERSE SCANNER — ALL Binance USDT pairs
# ═══════════════════════════════════════════════════════════════════════════

def _fetch_all_binance_usdt_pairs(min_volume_usd=MIN_24H_VOLUME_USD):
    """Fetch ALL USDT trading pairs from Binance filtered by minimum 24h volume.

    Returns a dict of {pair: ticker_data} for all pairs with vol > min_volume_usd.
    This catches mid/small-cap pumps (TRUMP, DEXE, MemeCore) that top-50 scans miss.
    """
    stablecoins = {"USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "FDUSD", "PYUSD",
                   "UST", "FRAX", "LUSD", "SUSD", "GUSD", "USDJ", "HUSD"}
    all_tickers = None
    for _bbase in _BINANCE_BASES:
        try:
            r = requests.get(f"{_bbase}/ticker/24hr", timeout=30)
            if r.status_code in (451, 403):
                continue
            if r.ok:
                all_tickers = r.json()
                break
            print(f"[WIDE] Binance 24hr ticker from {_bbase} failed: HTTP {r.status_code}")
        except Exception as e:
            print(f"[WIDE] Binance 24hr ticker from {_bbase} error: {e}")
            continue
    if all_tickers is None:
        print("[WIDE] All Binance endpoints failed, trying OKX fallback")
        return _fetch_all_okx_usdt_pairs(min_volume_usd)

    usdt_pairs = {}
    for t in all_tickers:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        base = sym.replace("USDT", "")
        if base in stablecoins or len(base) < 2:
            continue

        vol_usd = float(t.get("quoteVolume", 0))
        if vol_usd < min_volume_usd:
            continue

        usdt_pairs[sym] = {
            "pair": sym,
            "symbol": base,
            "current_price": float(t.get("lastPrice", 0)),
            "volume_24h": vol_usd,
            "change_24h_pct": float(t.get("priceChangePercent", 0)),
            "high_24h": float(t.get("highPrice", 0)),
            "low_24h": float(t.get("lowPrice", 0)),
            "open_price": float(t.get("openPrice", 0)),
            "weighted_avg_price": float(t.get("weightedAvgPrice", 0)),
        }

    print(f"[WIDE] Found {len(usdt_pairs)} USDT pairs with >${min_volume_usd/1e6:.1f}M 24h volume")
    return usdt_pairs


def _fetch_all_okx_usdt_pairs(min_volume_usd=MIN_24H_VOLUME_USD):
    """OKX fallback for wide universe scan when Binance is geo-blocked."""
    try:
        r = requests.get("https://www.okx.com/api/v5/market/tickers", params={"instType": "SPOT"}, timeout=30)
        if not r.ok:
            return {}
        tickers = r.json().get("data", [])
    except Exception:
        return {}

    usdt_pairs = {}
    for t in tickers:
        inst = t.get("instId", "")
        if not inst.endswith("-USDT"):
            continue
        base = inst.replace("-USDT", "")
        pair = f"{base}USDT"

        vol_usd = float(t.get("volCcy24h", 0))
        if vol_usd < min_volume_usd:
            continue

        usdt_pairs[pair] = {
            "pair": pair,
            "symbol": base,
            "current_price": float(t.get("last", 0)),
            "volume_24h": vol_usd,
            "change_24h_pct": 0,  # OKX doesn't provide this directly
            "high_24h": float(t.get("high24h", 0)),
            "low_24h": float(t.get("low24h", 0)),
            "open_price": float(t.get("open24h", 0)),
        }

    print(f"[WIDE-OKX] Found {len(usdt_pairs)} USDT pairs with >${min_volume_usd/1e6:.1f}M volume")
    return usdt_pairs


# ═══════════════════════════════════════════════════════════════════════════
#  v4.0: RAPID VOLUME SCAN — Lightweight pre-filter across ALL pairs
# ═══════════════════════════════════════════════════════════════════════════

def _rapid_volume_scan(all_tickers=None):
    """Rapid pre-filter: check volume velocity + price change across ALL pairs.

    Only looks at 24hr ticker data (no klines needed = very fast).
    Flags coins with >5% 1h gain AND >3x volume spike for full analysis.
    Returns list of pair names that should be prioritized in full scan.
    """
    if all_tickers is None:
        all_tickers = _fetch_all_binance_usdt_pairs(min_volume_usd=100_000)

    rapid_flags = []

    for pair, data in all_tickers.items():
        change_pct = data.get("change_24h_pct", 0)
        vol_24h = data.get("volume_24h", 0)
        price = data.get("current_price", 0)
        high = data.get("high_24h", 0)
        low = data.get("low_24h", 0)

        if price <= 0 or vol_24h <= 0:
            continue

        # Estimate 1h price change from current vs weighted avg or high/low range
        # (without klines, use 24h change as proxy — actual 1h check happens in full scan)
        # Flag if 24h change is strongly positive (>5%) — likely currently pumping
        if change_pct >= RAPID_SCAN_PRICE_CHANGE_MIN:
            # Estimate volume velocity from price range: large range + big gain = active
            price_range = (high - low) / price if price > 0 else 0
            # High range + positive change = likely volume-driven pump
            if price_range > 0.05:  # >5% 24h range
                rapid_flags.append({
                    "pair": pair,
                    "symbol": data.get("symbol", pair.replace("USDT", "")),
                    "change_24h_pct": change_pct,
                    "volume_24h": vol_24h,
                    "price_range_pct": round(price_range * 100, 2),
                    "priority": "HIGH",
                })

    rapid_flags.sort(key=lambda x: x["change_24h_pct"], reverse=True)
    if rapid_flags:
        print(f"[RAPID] Flagged {len(rapid_flags)} coins for priority analysis:")
        for f in rapid_flags[:10]:
            print(f"  {f['symbol']:>8} +{f['change_24h_pct']:.1f}% | vol ${f['volume_24h']/1e6:.1f}M | range {f['price_range_pct']:.1f}%")

    return rapid_flags


# ═══════════════════════════════════════════════════════════════════════════
#  v4.0: VOLUME VELOCITY COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════

def compute_volume_velocity(ohlcv_1h):
    """Compute volume velocity: ratio of last-hour volume to average hourly volume.

    This is the single most predictive feature for catching pumps early.
    A ratio > 3x means unusual buying pressure; > 5x means likely pump in progress.

    Args:
        ohlcv_1h: List of [ts, open, high, low, close, volume] bars (1h)

    Returns:
        dict with volume_velocity, volume_velocity_6h, is_volume_spike, is_extreme_spike
    """
    if not ohlcv_1h or len(ohlcv_1h) < 24:
        return {
            "volume_velocity_1h": 1.0,
            "volume_velocity_6h": 1.0,
            "is_volume_spike": 0,
            "is_extreme_spike": 0,
        }

    bars = sorted(ohlcv_1h, key=lambda x: x[0])
    volumes = [b[5] for b in bars]
    n = len(volumes)

    # Last 1 hour volume
    last_1h_vol = volumes[-1] if n >= 1 else 0

    # Average hourly volume over last 24h (excluding the last hour)
    lookback = min(24, n - 1)
    if lookback > 0:
        avg_hourly_vol = sum(volumes[-(lookback + 1):-1]) / lookback
    else:
        avg_hourly_vol = last_1h_vol

    # Volume velocity = last hour / avg hourly
    vol_velocity_1h = last_1h_vol / avg_hourly_vol if avg_hourly_vol > 0 else 1.0

    # Also compute 6h velocity for smoother signal
    last_6h_vol = sum(volumes[-min(6, n):]) / min(6, n)
    prior_6h_vol = sum(volumes[-min(12, n):-min(6, n)]) / max(min(6, n - 6), 1) if n > 6 else last_6h_vol
    vol_velocity_6h = last_6h_vol / prior_6h_vol if prior_6h_vol > 0 else 1.0

    return {
        "volume_velocity_1h": round(vol_velocity_1h, 4),
        "volume_velocity_6h": round(vol_velocity_6h, 4),
        "is_volume_spike": 1 if vol_velocity_1h >= VOLUME_VELOCITY_THRESHOLD else 0,
        "is_extreme_spike": 1 if vol_velocity_1h >= VOLUME_VELOCITY_EXTREME else 0,
    }


def _fetch_coingecko_legacy(num_coins=200):
    """Legacy CoinGecko fallback for when data_fetcher is unavailable.
    Uses CoinGecko for coin list + metadata, then Binance for 1h klines.
    Falls back to CoinGecko sparkline data when exchange klines unavailable.
    """
    all_coins = []
    pages = max(1, num_coins // 100)
    for page in range(1, pages + 1):
        params = {
            "vs_currency": "usd", "order": "market_cap_desc",
            "per_page": 100, "page": page, "sparkline": "true",
            "price_change_percentage": "1h,24h,7d",
        }
        try:
            r = requests.get(CG_MARKETS, params=params, headers=CG_HEADERS, timeout=30)
            if r.ok:
                resp = r.json()
                if isinstance(resp, list):
                    all_coins.extend(resp)
                else:
                    print(f"[WARN] CoinGecko page {page} returned non-list: {type(resp).__name__}")
            else:
                print(f"[WARN] CoinGecko page {page} HTTP {r.status_code}")
            time.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            print(f"[WARN] CoinGecko page {page} error: {e}")
            time.sleep(RATE_LIMIT_DELAY)

    print(f"[SCAN] CoinGecko returned {len(all_coins)} coins")

    # Detect if Binance is geo-blocked by testing one known pair (try all endpoints)
    binance_blocked = True
    for _bbase in _BINANCE_BASES:
        try:
            test_r = requests.get(
                f"{_bbase}/klines",
                params={"symbol": "BTCUSDT", "interval": "1h", "limit": 5},
                timeout=10,
            )
            if test_r.ok:
                binance_blocked = False
                if _bbase != BINANCE_BASE:
                    print(f"[SCAN] Using Binance endpoint: {_bbase}")
                break
            elif test_r.status_code in (451, 403):
                continue
            else:
                print(f"[SCAN] Binance {_bbase} returned HTTP {test_r.status_code}")
        except Exception:
            continue
    if binance_blocked:
        print("[SCAN] All Binance endpoints blocked/unreachable, will use OKX + sparkline fallback")

    results = {}
    fetched_klines = 0
    sparkline_used = 0
    failed_klines = 0

    for coin in all_coins:
        sym = coin.get("symbol", "").upper()
        pair = f"{sym}USDT"

        # Skip stablecoins — they won't have meaningful price action
        if sym in ("USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "FDUSD", "PYUSD"):
            continue

        # Fetch 1h klines from Binance/OKX/shared failover
        ohlcv_1h = []
        if not binance_blocked:
            ohlcv_1h = _fetch_binance_klines(pair, "1h", 168)
        else:
            # Go straight to OKX when Binance is blocked
            ohlcv_1h = _fetch_okx_klines_raw(pair, "1h", 168)
            # OKX failed — try shared multi-source failover (includes Kraken, CryptoCompare, etc.)
            if (not ohlcv_1h or len(ohlcv_1h) < 24) and _HAS_SHARED_FETCHER:
                ohlcv_1h = _shared_fetch_klines(pair, "1h", 168)

        if ohlcv_1h and len(ohlcv_1h) >= 24:
            fetched_klines += 1
        else:
            # Fallback: synthesize OHLCV from CoinGecko sparkline data
            sparkline = coin.get("sparkline_in_7d", {}).get("price", [])
            if sparkline and len(sparkline) >= 24:
                ohlcv_1h = _sparkline_to_ohlcv(
                    sparkline,
                    current_price=coin.get("current_price", 0) or 0,
                    volume_24h=coin.get("total_volume", 0) or 0,
                )
                if ohlcv_1h and len(ohlcv_1h) >= 24:
                    sparkline_used += 1
                else:
                    failed_klines += 1
                    print(f"  [WARN] ALL data sources failed for {pair} (exchange + sparkline insufficient)")
            else:
                failed_klines += 1
                print(f"  [WARN] ALL data sources failed for {pair} (no klines, no sparkline)")

        results[pair] = {
            "pair": pair, "symbol": sym,
            "coin_id": coin.get("id", ""),
            "name": coin.get("name", ""),
            "current_price": coin.get("current_price", 0) or 0,
            "market_cap": coin.get("market_cap", 0) or 0,
            "volume_24h": coin.get("total_volume", 0) or 0,
            "change_24h_pct": coin.get("price_change_percentage_24h", 0) or 0,
            "high_24h": coin.get("high_24h", 0) or 0,
            "low_24h": coin.get("low_24h", 0) or 0,
            "ath": coin.get("ath", 0) or 0,
            "atl": coin.get("atl", 0) or 0,
            "ohlcv_1h": ohlcv_1h,
            "source": "coingecko_legacy+binance" if fetched_klines > 0 else "coingecko_sparkline",
        }

    print(f"[SCAN] Klines: {fetched_klines} exchange, {sparkline_used} sparkline, {failed_klines} failed (of {len(all_coins)} coins)")
    return results


def main():
    parser = argparse.ArgumentParser(description="CLAUDE CODE — Live Crypto Gainer Scanner v3.0")
    parser.add_argument("--top", type=int, default=200, help="Number of coins to scan")
    parser.add_argument("--threshold", type=float, default=None, help="Min probability threshold")
    parser.add_argument("--max-picks", type=int, default=10, help="Max picks per scan")
    parser.add_argument("--no-discord", action="store_true", help="Disable Discord alerts")
    parser.add_argument("--kline-bars", type=int, default=168, help="1h kline bars to fetch (168=7d)")
    parser.add_argument("--loop", action="store_true", help="Run continuously (every 30 min)")
    args = parser.parse_args()

    if args.loop:
        print("[LOOP] Running continuous scan every 30 minutes...")
        while True:
            try:
                run_scan(
                    top_n=args.top, threshold=args.threshold,
                    max_picks=args.max_picks,
                    send_alerts=not args.no_discord,
                    kline_bars=args.kline_bars,
                )
            except Exception as e:
                print(f"[ERROR] Scan failed: {e}")
                _release_lock()
            print("\n[LOOP] Sleeping 30 minutes...")
            time.sleep(1800)
    else:
        run_scan(
            top_n=args.top, threshold=args.threshold,
            max_picks=args.max_picks,
            send_alerts=not args.no_discord,
            kline_bars=args.kline_bars,
        )


if __name__ == "__main__":
    main()
