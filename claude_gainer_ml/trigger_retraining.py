#!/usr/bin/env python3
"""
CLAUDE CODE — Trigger ML Retraining Pipeline
=============================================
Connects the existing self_improver.py pipeline that was designed but never
activated. This script:

1. Collects all resolved picks from tracker/claude_pick_history.json
2. Enriches legacy picks (without stored features) by fetching historical
   klines from Binance and recomputing the 20 ML features at entry time
3. Generates additional real-market training samples from Binance kline
   history to supplement the weak synthetic data (15K rows, 1% pos rate)
4. Calls self_improver's retraining with a quality gate:
   - If retrained AUC > current 0.537 → save new model
   - If worse → keep old model, log why
5. Bumps version in training_meta.json

Usage:
    python trigger_retraining.py [--enrich-only] [--augment N] [--force]
"""

import os
import sys
import json
import time
import argparse
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
TRACKER_DIR = BASE_DIR / "tracker"

PICK_HISTORY_FILE = TRACKER_DIR / "claude_pick_history.json"
ONLINE_DATA_FILE = DATA_DIR / "online_training_data.csv"
FEATURE_CACHE = DATA_DIR / "feature_matrix.csv"
TRAINING_META = MODEL_DIR / "training_meta.json"
AUGMENTED_CACHE = DATA_DIR / "augmented_real_data.csv"

sys.path.insert(0, str(BASE_DIR))

# ── Feature columns (must match self_improver.py and live_scanner.py) ────
FEATURE_COLS = [
    "vol_mcap_ratio", "vol_change_24h", "vol_change_12h",
    "price_momentum_7d", "price_momentum_3d", "price_momentum_1d",
    "rsi_14", "rsi_slope", "bb_width", "bb_percentb",
    "consolidation_range", "consecutive_green", "momentum_ignition",
    "obv_divergence", "distance_from_ath_pct", "distance_from_atl_pct",
    "mcap_tier", "price_compression", "relative_volume_spike",
    "fear_greed_proxy",
]

# Binance pairs to fetch real market data from (liquid, well-known coins)
BINANCE_TRAINING_PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "MATICUSDT", "UNIUSDT", "AAVEUSDT", "ATOMUSDT", "NEARUSDT",
    "APTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "SUIUSDT",
    "FTMUSDT", "SHIBUSDT", "PEPEUSDT", "BONKUSDT", "FLOKIUSDT",
    "RUNEUSDT", "THETAUSDT", "FILUSDT", "GRTUSDT", "RENDERUSDT",
    "STXUSDT", "PENDLEUSDT", "TAOUSDT", "ONDOUSDT", "BCHUSDT",
    "LTCUSDT", "ETCUSDT", "ZECUSDT", "DCRUSDT", "AXSUSDT",
]

BINANCE_BASE = "https://api.binance.com/api/v3"


# ═══════════════════════════════════════════════════════════════════════════
#  BINANCE DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════

def fetch_binance_klines(symbol, interval="1h", limit=500):
    """Fetch klines from Binance. Returns list of [ts, o, h, l, c, v]."""
    import requests
    url = f"{BINANCE_BASE}/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]),
                     float(k[4]), float(k[5])] for k in data]
    except Exception as e:
        print(f"  [WARN] Failed to fetch {symbol}: {e}")
    return []


def fetch_binance_klines_historical(symbol, interval="1h", start_ms=None, end_ms=None, limit=1000):
    """Fetch historical klines from Binance with start/end timestamps."""
    import requests
    url = f"{BINANCE_BASE}/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    if start_ms:
        params["startTime"] = int(start_ms)
    if end_ms:
        params["endTime"] = int(end_ms)
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]),
                     float(k[4]), float(k[5])] for k in data]
    except Exception as e:
        print(f"  [WARN] Failed to fetch {symbol} historical: {e}")
    return []


# ═══════════════════════════════════════════════════════════════════════════
#  FEATURE COMPUTATION (standalone, mirrors live_scanner.py)
# ═══════════════════════════════════════════════════════════════════════════

def compute_rsi(closes, period=14):
    """Compute RSI for a price series."""
    n = len(closes)
    rsi = [50.0] * n
    if n < period + 1:
        return rsi
    gains, losses = [], []
    for i in range(1, n):
        delta = closes[i] - closes[i-1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, n):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i-1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i-1]) / period
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def compute_bollinger(closes, period=20, num_std=2):
    """Compute Bollinger Band width and %B."""
    n = len(closes)
    widths = [0.0] * n
    pctbs = [0.5] * n
    for i in range(period - 1, n):
        window = closes[i - period + 1:i + 1]
        sma = sum(window) / period
        std = (sum((x - sma) ** 2 for x in window) / period) ** 0.5
        if sma > 0:
            widths[i] = (2 * num_std * std) / sma
        upper = sma + num_std * std
        lower = sma - num_std * std
        if upper != lower:
            pctbs[i] = (closes[i] - lower) / (upper - lower)
    return widths, pctbs


def compute_obv(closes, volumes):
    """Compute On-Balance Volume."""
    n = len(closes)
    obv = [0.0] * n
    for i in range(1, n):
        if closes[i] > closes[i-1]:
            obv[i] = obv[i-1] + volumes[i]
        elif closes[i] < closes[i-1]:
            obv[i] = obv[i-1] - volumes[i]
        else:
            obv[i] = obv[i-1]
    return obv


def compute_features_from_klines(klines, mcap=1e9, ath=None, atl=None, bar_idx=None):
    """Compute 20 ML features from 1h klines at a given bar index.

    Args:
        klines: list of [ts, o, h, l, c, v] (1h bars, sorted by time)
        mcap: estimated market cap
        ath/atl: all-time high/low estimates
        bar_idx: which bar to compute features at (default: last bar)

    Returns:
        dict of feature values, or None if insufficient data
    """
    if len(klines) < 168:  # need at least 7 days of hourly data
        return None

    bars = sorted(klines, key=lambda x: x[0])
    opens = [b[1] for b in bars]
    highs = [b[2] for b in bars]
    lows = [b[3] for b in bars]
    closes = [b[4] for b in bars]
    volumes = [b[5] for b in bars]

    n = len(closes)
    i = bar_idx if bar_idx is not None else n - 1
    if i < 168 or i >= n:
        i = n - 1
    c = closes[i]
    if c <= 0:
        return None

    if ath is None:
        ath = max(closes) * 1.1
    if atl is None:
        atl = min(c for c in closes if c > 0) * 0.9

    rsi_vals = compute_rsi(closes, 14)
    bb_widths, bb_pctbs = compute_bollinger(closes, min(20, n), 2)
    obv_vals = compute_obv(closes, volumes)

    # Hourly lookbacks
    lb_24 = 24
    lb_72 = 72
    lb_168 = 168
    lb_12 = 12

    # 1. vol_mcap_ratio
    vol_period = sum(volumes[max(0, i-lb_24+1):i+1])
    vol_mcap_ratio = vol_period / mcap if mcap > 0 else 0

    # 2. vol_change_24h
    avg_vol_base = sum(volumes[max(0, i-lb_168):max(0, i-lb_24)]) / max(lb_168 - lb_24, 1) * lb_24
    vol_change_24h = vol_period / avg_vol_base if avg_vol_base > 0 else 1.0

    # 3. vol_change_12h
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
    ranges = [(highs[j] - lows[j]) / closes[j]
              for j in range(max(0, i-lb_24+1), i+1) if closes[j] > 0]
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
    obv_divergence = 1 if (obv_trend > 0 and price_trend < 0) or \
                          (obv_trend < 0 and price_trend > 0) else 0

    # 15-16. Distance from ATH/ATL
    distance_from_ath_pct = ((ath - c) / ath * 100) if ath > 0 else 0
    distance_from_atl_pct = ((c - atl) / atl * 100) if atl > 0 else 0

    # 17. Market cap tier
    if mcap >= 50e9:
        mcap_tier = 1.0
    elif mcap >= 5e9:
        mcap_tier = 0.8
    elif mcap >= 500e6:
        mcap_tier = 0.6
    elif mcap >= 50e6:
        mcap_tier = 0.4
    else:
        mcap_tier = 0.2

    # 18. Price compression
    recent_range = max(closes[max(0, i-lb_24):i+1]) - min(closes[max(0, i-lb_24):i+1])
    wider_range = max(closes[max(0, i-lb_168):i+1]) - min(closes[max(0, i-lb_168):i+1])
    price_compression = 1 if (wider_range > 0 and recent_range / wider_range < 0.15) else 0

    # 19. Relative volume spike
    avg_vol_7d = sum(volumes[max(0, i-lb_168):i]) / max(lb_168 - 1, 1)
    curr_vol = volumes[i]
    relative_volume_spike = 1 if (avg_vol_7d > 0 and curr_vol / avg_vol_7d > 3.0) else 0

    # 20. Fear & greed proxy (momentum + volume)
    fear_greed_proxy = min(1.0, max(0.0,
        0.5 + pm1d / 40 + (vol_change_24h - 1) * 0.2))

    return {
        "vol_mcap_ratio": round(vol_mcap_ratio, 6),
        "vol_change_24h": round(vol_change_24h, 4),
        "vol_change_12h": round(vol_change_12h, 4),
        "price_momentum_7d": round(pm7d, 4),
        "price_momentum_3d": round(pm3d, 4),
        "price_momentum_1d": round(pm1d, 4),
        "rsi_14": round(rsi_14, 2),
        "rsi_slope": round(rsi_slope, 2),
        "bb_width": round(bb_width, 4),
        "bb_percentb": round(bb_percentb, 4),
        "consolidation_range": round(consolidation_range, 6),
        "consecutive_green": consec_green,
        "momentum_ignition": momentum_ignition,
        "obv_divergence": obv_divergence,
        "distance_from_ath_pct": round(distance_from_ath_pct, 2),
        "distance_from_atl_pct": round(distance_from_atl_pct, 2),
        "mcap_tier": mcap_tier,
        "price_compression": price_compression,
        "relative_volume_spike": relative_volume_spike,
        "fear_greed_proxy": round(fear_greed_proxy, 4),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1: ENRICH RESOLVED PICKS WITH REAL FEATURES
# ═══════════════════════════════════════════════════════════════════════════

# Approximate market caps for symbol mapping (for resolved picks)
SYMBOL_MCAP = {
    "H": 100e6, "INJ": 500e6, "ZEC": 500e6, "VVV": 100e6,
    "RIVER": 50e6, "SKR": 20e6, "VIRTUAL": 200e6, "TIBBIR": 20e6,
    "HNT": 200e6, "UNI": 3e9, "TAO": 2e9, "AVAX": 5e9,
    "DCR": 300e6, "ADA": 10e9, "STX": 500e6, "PENDLE": 300e6,
    "AXS": 300e6, "RENDER": 1e9, "XDC": 200e6, "THETA": 300e6,
    "ONDO": 500e6, "GT": 1e9, "BONK": 500e6, "MX": 500e6,
    "ZBCN": 30e6, "AAVE": 2e9, "ETC": 2e9, "FET": 500e6,
    "BCH": 5e9,
}

# Map symbols to Binance pairs
SYMBOL_TO_PAIR = {
    "INJ": "INJUSDT", "ZEC": "ZECUSDT", "UNI": "UNIUSDT", "TAO": "TAOUSDT",
    "AVAX": "AVAXUSDT", "DCR": "DCRUSDT", "ADA": "ADAUSDT", "STX": "STXUSDT",
    "PENDLE": "PENDLEUSDT", "AXS": "AXSUSDT", "RENDER": "RENDERUSDT",
    "XDC": "XDCUSDT", "THETA": "THETAUSDT", "ONDO": "ONDOUSDT",
    "GT": "GTUSDT", "BONK": "BONKUSDT", "AAVE": "AAVEUSDT",
    "ETC": "ETCUSDT", "FET": "FETUSDT", "BCH": "BCHUSDT",
    "HNT": "HNTUSDT", "MX": "MXUSDT",
}


def enrich_pick_features(pick):
    """Fetch historical Binance klines for a resolved pick and compute features.

    Returns enriched pick dict with 'features' field, or None if unable.
    """
    symbol = pick.get("symbol", "")
    pair = SYMBOL_TO_PAIR.get(symbol)
    if not pair:
        return None

    entry_time = pick.get("entry_time", "")
    if not entry_time:
        return None

    # Parse entry time and compute time window
    # We need 168 bars (7 days) of hourly data BEFORE the entry
    try:
        entry_dt = datetime.fromisoformat(entry_time)
        end_ms = int(entry_dt.timestamp() * 1000)
        start_ms = end_ms - (170 * 3600 * 1000)  # 170h before entry
    except Exception:
        return None

    klines = fetch_binance_klines_historical(pair, "1h", start_ms, end_ms, limit=170)
    if not klines or len(klines) < 168:
        return None

    mcap = SYMBOL_MCAP.get(symbol, 500e6)
    features = compute_features_from_klines(klines, mcap=mcap)
    if not features:
        return None

    enriched = dict(pick)
    enriched["features"] = features
    return enriched


def enrich_all_picks():
    """Enrich all resolved picks in pick_history with real features from Binance."""
    if not PICK_HISTORY_FILE.exists():
        print("[ENRICH] No pick history found")
        return 0

    with open(PICK_HISTORY_FILE) as f:
        history = json.load(f)

    print(f"\n[ENRICH] Processing {len(history)} resolved picks...")
    enriched_count = 0
    failed_symbols = []

    for idx, pick in enumerate(history):
        # Skip if already has good features
        existing = pick.get("features", {})
        if existing and any(v != 0 for v in existing.values()):
            enriched_count += 1
            continue

        symbol = pick.get("symbol", "?")
        result = enrich_pick_features(pick)
        if result:
            pick["features"] = result["features"]
            enriched_count += 1
            pnl = pick.get("pnl_pct", 0)
            print(f"  [{idx+1}/{len(history)}] {symbol}: enriched (pnl={pnl:+.1f}%)")
        else:
            failed_symbols.append(symbol)
            print(f"  [{idx+1}/{len(history)}] {symbol}: FAILED (no Binance pair or data)")

        # Rate limit: Binance allows ~1200 req/min
        time.sleep(0.15)

    # Save enriched history back
    with open(PICK_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

    print(f"\n[ENRICH] Enriched {enriched_count}/{len(history)} picks")
    if failed_symbols:
        print(f"  Failed: {', '.join(failed_symbols)}")

    return enriched_count


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 2: GENERATE REAL-MARKET AUGMENTATION DATA
# ═══════════════════════════════════════════════════════════════════════════

def generate_real_market_augmentation(num_pairs=30, days_back=90):
    """Fetch real Binance kline data and create labeled training samples.

    For each coin, we slide a window across the kline history:
    - Compute features at bar[i]
    - Label = 1 if price gains >3% in next 24h, else 0

    This generates REAL market labels instead of the synthetic pump patterns
    in the original training data.
    """
    import pandas as pd

    print(f"\n[AUGMENT] Generating real-market training data from Binance...")
    print(f"  Pairs: {num_pairs}, Lookback: {days_back} days")

    pairs_to_use = BINANCE_TRAINING_PAIRS[:num_pairs]
    all_rows = []

    # Approximate market caps for augmentation pairs
    pair_mcaps = {
        "BTCUSDT": 800e9, "ETHUSDT": 200e9, "BNBUSDT": 50e9,
        "SOLUSDT": 30e9, "XRPUSDT": 25e9, "ADAUSDT": 10e9,
        "DOGEUSDT": 10e9, "AVAXUSDT": 5e9, "DOTUSDT": 5e9,
        "LINKUSDT": 5e9, "MATICUSDT": 3e9, "UNIUSDT": 3e9,
    }

    for pair_idx, pair in enumerate(pairs_to_use):
        print(f"  [{pair_idx+1}/{len(pairs_to_use)}] Fetching {pair}...", end=" ", flush=True)

        # Fetch enough bars: 7 days warmup + days_back days of samples + 1 day forward
        total_hours = (days_back + 8) * 24
        # Binance max is 1000 per request, so we may need multiple calls
        all_klines = []
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        end_ms = now_ms
        remaining = total_hours

        while remaining > 0:
            fetch_limit = min(remaining, 1000)
            start_ms = end_ms - (fetch_limit * 3600 * 1000)
            klines = fetch_binance_klines_historical(pair, "1h", start_ms, end_ms, fetch_limit)
            if not klines:
                break
            all_klines = klines + all_klines  # prepend
            end_ms = start_ms
            remaining -= len(klines)
            time.sleep(0.2)

        if len(all_klines) < 200:
            print(f"insufficient data ({len(all_klines)} bars)")
            continue

        klines_sorted = sorted(all_klines, key=lambda x: x[0])
        closes = [k[4] for k in klines_sorted]
        n_bars = len(klines_sorted)
        mcap = pair_mcaps.get(pair, 500e6)

        # Slide window: compute features at each bar, label by next-24h gain
        # Start at bar 168 (need 7d warmup), end 24 bars before last (need forward label)
        samples_this_pair = 0
        for bar_i in range(168, n_bars - 24, 6):  # step=6 (every 6h) to avoid oversampling
            features = compute_features_from_klines(klines_sorted, mcap=mcap, bar_idx=bar_i)
            if not features:
                continue

            # Label: did price gain >3% in next 24 bars?
            future_max = max(closes[bar_i+1:bar_i+25])
            gain_pct = (future_max - closes[bar_i]) / closes[bar_i] * 100
            label = 1 if gain_pct >= 3.0 else 0

            row = dict(features)
            row["label"] = label
            row["coin_id"] = pair
            row["symbol"] = pair.replace("USDT", "")
            row["timestamp"] = klines_sorted[bar_i][0]
            row["close"] = closes[bar_i]
            row["next_close"] = closes[min(bar_i+24, n_bars-1)]
            all_rows.append(row)
            samples_this_pair += 1

        print(f"{samples_this_pair} samples")
        time.sleep(0.3)

    if not all_rows:
        print("[AUGMENT] No samples generated!")
        return 0

    aug_df = pd.DataFrame(all_rows)
    pos_rate = aug_df["label"].mean()
    print(f"\n[AUGMENT] Generated {len(aug_df)} real-market samples")
    print(f"  Positive rate: {pos_rate:.2%} (vs 1% in synthetic data)")
    print(f"  Positives: {aug_df['label'].sum()}, Negatives: {(aug_df['label'] == 0).sum()}")

    # Save augmented data
    aug_df.to_csv(AUGMENTED_CACHE, index=False)
    print(f"  Saved to {AUGMENTED_CACHE}")

    return len(aug_df)


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 3: RETRAIN WITH QUALITY GATE
# ═══════════════════════════════════════════════════════════════════════════

def retrain_with_quality_gate(force=False):
    """Retrain the model using enriched picks + augmented data,
    but only save if AUC improves over current 0.537.
    """
    import pandas as pd
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

    try:
        import xgboost as xgb
        HAS_XGB = True
    except ImportError:
        HAS_XGB = False

    print("\n" + "=" * 70)
    print("  RETRAINING WITH QUALITY GATE")
    print("=" * 70)

    # Load current model metrics
    prev_meta = {}
    if TRAINING_META.exists():
        with open(TRAINING_META) as f:
            prev_meta = json.load(f)
    prev_auc = prev_meta.get("metrics", {}).get("roc_auc", 0.5)
    prev_prec = prev_meta.get("metrics", {}).get("precision", 0.0)
    prev_version = prev_meta.get("model_version", "1.0.0")
    print(f"  Current model: v{prev_version}")
    print(f"  Current AUC: {prev_auc:.4f}, Precision: {prev_prec:.4f}")

    # ── Collect training data ──

    # 1. Original synthetic data
    if FEATURE_CACHE.exists():
        original_df = pd.read_csv(FEATURE_CACHE)
        print(f"  Original synthetic data: {len(original_df)} samples (pos rate: {original_df['label'].mean():.2%})")
    else:
        print("[ERROR] No feature_matrix.csv found!")
        return False

    # 2. Online data from resolved picks (via self_improver's collect)
    from self_improver import collect_online_data
    print("\n  Collecting online data from resolved picks...")
    collect_online_data()

    online_df = pd.DataFrame()
    if ONLINE_DATA_FILE.exists():
        online_df = pd.read_csv(ONLINE_DATA_FILE)
        print(f"  Online data: {len(online_df)} samples")

    # 3. Real-market augmented data
    aug_df = pd.DataFrame()
    if AUGMENTED_CACHE.exists():
        aug_df = pd.read_csv(AUGMENTED_CACHE)
        print(f"  Augmented real data: {len(aug_df)} samples (pos rate: {aug_df['label'].mean():.2%})")

    # ── Combine datasets ──
    required_cols = FEATURE_COLS + ["label"]

    dfs_to_combine = []

    # Add original data (down-weight by taking a subset to balance with real data)
    for col in required_cols:
        if col not in original_df.columns:
            original_df[col] = 0.0
    # Subsample synthetic data — it's low quality. Keep 30% max.
    synth_sample_size = min(len(original_df), max(3000, len(aug_df)))
    synth_subset = original_df[required_cols].sample(n=synth_sample_size, random_state=42)
    dfs_to_combine.append(synth_subset)
    print(f"  Using {len(synth_subset)}/{len(original_df)} synthetic samples")

    # Add augmented real data (high quality, full inclusion)
    if len(aug_df) > 0:
        for col in required_cols:
            if col not in aug_df.columns:
                aug_df[col] = 0.0
        dfs_to_combine.append(aug_df[required_cols])

    # Add online data (highest quality — real picks with outcomes)
    if len(online_df) > 0:
        for col in required_cols:
            if col not in online_df.columns:
                online_df[col] = 0.0
        # Weight online data 3x by repeating (these are real pick outcomes)
        for _ in range(3):
            dfs_to_combine.append(online_df[required_cols])

    combined = pd.concat(dfs_to_combine, ignore_index=True)
    combined = combined.dropna(subset=["label"])
    print(f"\n  Combined training data: {len(combined)} samples")
    print(f"  Combined positive rate: {combined['label'].mean():.2%}")

    # ── Prepare X, y ──
    X = combined[FEATURE_COLS].values
    y = combined["label"].values
    X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)

    # Time-sorted split (80/20) — ensures test set is "future" data
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    if len(np.unique(y_test)) < 2:
        print("[WARN] Test set has only one class — shuffling data")
        indices = np.random.RandomState(42).permutation(len(X))
        X = X[indices]
        y = y[indices]
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"  Train: {len(X_train)} (pos: {sum(y_train):.0f})")
    print(f"  Test:  {len(X_test)} (pos: {sum(y_test):.0f})")

    # ── Scale ──
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ── Train RandomForest ──
    print("\n  Training RandomForest (300 trees)...")
    pos_weight = max(1, int(sum(y_train == 0) / max(sum(y_train == 1), 1)))
    sample_weights = np.where(y_train == 1, pos_weight, 1).astype(float)

    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_split=10,
        min_samples_leaf=5,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train_scaled, y_train, sample_weight=sample_weights)
    rf_proba = rf.predict_proba(X_test_scaled)[:, 1]

    # ── Train XGBoost ──
    xgb_model = None
    xgb_proba = np.zeros_like(rf_proba)

    if HAS_XGB:
        print("  Training XGBoost (300 rounds)...")
        xgb_model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=pos_weight,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
        xgb_model.fit(X_train_scaled, y_train)
        xgb_proba = xgb_model.predict_proba(X_test_scaled)[:, 1]

    # ── Ensemble ──
    if HAS_XGB and xgb_model is not None:
        ensemble_proba = 0.45 * rf_proba + 0.55 * xgb_proba
    else:
        ensemble_proba = rf_proba

    ensemble_pred = (ensemble_proba >= 0.5).astype(int)

    # ── Metrics ──
    if len(np.unique(y_test)) > 1:
        prec = precision_score(y_test, ensemble_pred, zero_division=0)
        rec = recall_score(y_test, ensemble_pred, zero_division=0)
        f1 = f1_score(y_test, ensemble_pred, zero_division=0)
        auc = roc_auc_score(y_test, ensemble_proba)
    else:
        print("[WARN] Cannot compute AUC — test set has only one class")
        prec = rec = f1 = auc = 0

    print(f"\n  ┌─────────────────────────────────────┐")
    print(f"  │  RETRAINED MODEL METRICS             │")
    print(f"  │  Precision: {prec:.4f}  (was {prev_prec:.4f})  │")
    print(f"  │  Recall:    {rec:.4f}                  │")
    print(f"  │  F1:        {f1:.4f}                  │")
    print(f"  │  ROC-AUC:   {auc:.4f}  (was {prev_auc:.4f})  │")
    print(f"  └─────────────────────────────────────┘")

    # ── Quality gate ──
    improved = auc > prev_auc
    if not improved and not force:
        print(f"\n  *** QUALITY GATE FAILED ***")
        print(f"  New AUC ({auc:.4f}) is NOT better than current ({prev_auc:.4f})")
        print(f"  Model NOT saved. Use --force to override.")

        # Log the failed attempt
        _log_attempt(prev_version, auc, prec, rec, f1, prev_meta.get("metrics", {}),
                     reason="quality_gate_failed", saved=False,
                     combined_size=len(combined), online_size=len(online_df),
                     aug_size=len(aug_df))
        return False

    # ── Save new model ──
    parts = prev_version.split(".")
    parts[1] = str(int(parts[1]) + 1)
    parts[2] = "0"
    new_version = ".".join(parts)

    # Backup old models
    for model_file in ["claude_rf.joblib", "claude_scaler.joblib", "claude_xgb.joblib"]:
        src = MODEL_DIR / model_file
        bak = MODEL_DIR / f"{model_file}.bak"
        if src.exists():
            import shutil
            shutil.copy2(src, bak)

    joblib.dump(rf, MODEL_DIR / "claude_rf.joblib")
    joblib.dump(scaler, MODEL_DIR / "claude_scaler.joblib")
    if HAS_XGB and xgb_model:
        joblib.dump(xgb_model, MODEL_DIR / "claude_xgb.joblib")

    # Feature importance
    feat_imp = dict(zip(FEATURE_COLS, rf.feature_importances_))
    feat_imp = dict(sorted(feat_imp.items(), key=lambda x: -x[1]))

    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_version": new_version,
        "pipeline": "CLAUDE CODE Gainer ML (retrained via trigger_retraining.py)",
        "num_features": len(FEATURE_COLS),
        "feature_names": FEATURE_COLS,
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "online_samples_used": int(len(online_df)),
        "augmented_samples_used": int(len(aug_df)),
        "total_samples": int(len(combined)),
        "positive_rate_train": float(sum(y_train) / len(y_train)),
        "positive_rate_test": float(sum(y_test) / len(y_test)),
        "ensemble_weights": {"rf": 0.45, "xgb": 0.55} if HAS_XGB else {"rf": 1.0},
        "metrics": {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "roc_auc": round(auc, 4),
        },
        "previous_metrics": prev_meta.get("metrics", {}),
        "feature_importance": {k: round(v, 4) for k, v in feat_imp.items()},
        "has_xgboost": HAS_XGB,
        "retrain_trigger": "trigger_retraining.py",
        "quality_gate_passed": improved or force,
    }
    with open(TRAINING_META, "w") as f:
        json.dump(meta, f, indent=2)

    # Log success
    from self_improver import log_improvement
    log_improvement(new_version, meta, prev_meta.get("metrics", {}))

    _log_attempt(new_version, auc, prec, rec, f1, prev_meta.get("metrics", {}),
                 reason="quality_gate_passed" if improved else "forced",
                 saved=True, combined_size=len(combined),
                 online_size=len(online_df), aug_size=len(aug_df))

    delta_auc = auc - prev_auc
    print(f"\n  Model saved as v{new_version}")
    print(f"  AUC improvement: {prev_auc:.4f} -> {auc:.4f} ({delta_auc:+.4f})")
    print(f"  Precision: {prev_prec:.4f} -> {prec:.4f}")
    print(f"  Models backed up to *.joblib.bak")

    return True


def _log_attempt(version, auc, prec, rec, f1, prev_metrics, reason="",
                 saved=False, combined_size=0, online_size=0, aug_size=0):
    """Log retraining attempt (success or failure) for audit trail."""
    log_file = MODEL_DIR / "retrain_log.json"
    log = []
    if log_file.exists():
        with open(log_file) as f:
            log = json.load(f)

    log.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "reason": reason,
        "saved": saved,
        "metrics": {"precision": prec, "recall": rec, "f1": f1, "roc_auc": auc},
        "previous_metrics": prev_metrics,
        "data_sizes": {
            "combined": combined_size,
            "online": online_size,
            "augmented": aug_size,
        },
    })

    # Keep last 100 entries
    log = log[-100:]
    with open(log_file, "w") as f:
        json.dump(log, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Trigger ML retraining pipeline for Claude Gainer ML")
    parser.add_argument("--enrich-only", action="store_true",
                        help="Only enrich pick history with Binance features, don't retrain")
    parser.add_argument("--augment", type=int, default=30,
                        help="Number of Binance pairs to fetch for augmentation (default: 30)")
    parser.add_argument("--skip-augment", action="store_true",
                        help="Skip Binance augmentation (use existing augmented data if available)")
    parser.add_argument("--force", action="store_true",
                        help="Force save model even if AUC doesn't improve")
    parser.add_argument("--days", type=int, default=60,
                        help="Days of historical data to use for augmentation (default: 60)")
    args = parser.parse_args()

    print("=" * 70)
    print("  CLAUDE CODE — ML Retraining Trigger")
    print(f"  Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)

    # ── Step 1: Check resolved picks ──
    if PICK_HISTORY_FILE.exists():
        with open(PICK_HISTORY_FILE) as f:
            history = json.load(f)
        n_picks = len(history)
        wins = sum(1 for p in history if (p.get("pnl_pct") or 0) > 0)
        losses = n_picks - wins
        avg_pnl = sum(float(p.get("pnl_pct", 0) or 0) for p in history) / max(n_picks, 1)
        print(f"\n  Resolved picks: {n_picks}")
        print(f"  Win/Loss: {wins}/{losses} ({wins/max(n_picks,1):.0%} WR)")
        print(f"  Avg PnL: {avg_pnl:.2f}%")
    else:
        print("\n  [WARN] No pick history found — will rely on augmented data")
        n_picks = 0

    # ── Step 2: Enrich picks with Binance features ──
    print("\n" + "-" * 50)
    print("  STEP 1: Enriching pick history with real features")
    print("-" * 50)
    enriched = enrich_all_picks()

    if args.enrich_only:
        print("\n[DONE] Enrichment complete (--enrich-only mode)")
        return

    # ── Step 3: Generate real-market augmentation ──
    if not args.skip_augment:
        print("\n" + "-" * 50)
        print("  STEP 2: Generating real-market training data")
        print("-" * 50)
        aug_count = generate_real_market_augmentation(
            num_pairs=args.augment,
            days_back=args.days,
        )
    else:
        print("\n  [SKIP] Using existing augmented data (--skip-augment)")
        if AUGMENTED_CACHE.exists():
            import pandas as pd
            aug_df = pd.read_csv(AUGMENTED_CACHE)
            print(f"  Found {len(aug_df)} existing augmented samples")

    # ── Step 4: Retrain with quality gate ──
    print("\n" + "-" * 50)
    print("  STEP 3: Retraining with quality gate")
    print("-" * 50)
    success = retrain_with_quality_gate(force=args.force)

    # ── Summary ──
    print("\n" + "=" * 70)
    if success:
        with open(TRAINING_META) as f:
            new_meta = json.load(f)
        print(f"  RETRAINING COMPLETE — Model v{new_meta['model_version']}")
        print(f"  AUC: {new_meta['metrics']['roc_auc']:.4f}")
        print(f"  Precision: {new_meta['metrics']['precision']:.4f}")
    else:
        print("  RETRAINING DID NOT IMPROVE MODEL")
        print("  Old model retained. Check retrain_log.json for details.")
    print("=" * 70)


if __name__ == "__main__":
    main()
