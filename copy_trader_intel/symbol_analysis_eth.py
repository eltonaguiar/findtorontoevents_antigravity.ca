#!/usr/bin/env python3
"""
ETH-Specific Deep Pattern Analyzer
====================================
Extracts ALL ETH trades from OKX copy traders, fetches 2-year ETH-USD hourly
OHLCV, computes 20+ technical features at each entry timestamp, trains an ML
classifier, generates 5 ETH-specific strategy variations, backtests each on
2-year data, and saves results.

Key findings driving this analyzer:
  - nightraid- (Grade A, 72.5% WR) trades 70% ETH with 47.2x avg leverage, 123h avg hold
  - Expert-Ethash-Camel (Grade B, 67.6% WR) trades 50% ETH
  - ETH shorts: 75-79% WR vs ETH longs: 59-70% WR

source_system = "ml_eth_reverser"

Outputs:
  data/eth_pattern_analysis.json   -- per-trade feature extraction + stats
  data/eth_strategy_variations.json -- 5 ETH-specific strategy variations
  data/eth_ml_picks.json           -- ML-generated current picks
"""

import sys
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

import json
import math
import time
import statistics
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

SOURCE_SYSTEM = "ml_eth_reverser"
TRADE_HISTORY_FILE = DATA_DIR / "okx_trade_history.json"
TRADER_PROFILES_FILE = DATA_DIR / "okx_trader_profiles.json"
OUTPUT_ANALYSIS = DATA_DIR / "eth_pattern_analysis.json"
OUTPUT_VARIATIONS = DATA_DIR / "eth_strategy_variations.json"
OUTPUT_ML_PICKS = DATA_DIR / "eth_ml_picks.json"

# Binance API failover chain (NEVER single endpoint -- project rule)
BINANCE_ENDPOINTS = [
    "https://data-api.binance.vision",
    "https://api.binance.us",
    "https://api.binance.com",
]
COINGECKO_ENDPOINT = "https://api.coingecko.com/api/v3"
KUCOIN_ENDPOINT = "https://api.kucoin.com"

# ─── Trader name mapping (from okx_trader_profiles.json) ────────────────────
TRADER_NAMES = {}  # populated at runtime from profiles


def _load_trader_names():
    """Load trader ID -> nickname mapping from profiles."""
    global TRADER_NAMES
    try:
        with open(TRADER_PROFILES_FILE, "r", encoding="utf-8") as f:
            profiles = json.load(f)
        for p in profiles.get("profiles", []):
            uid = p.get("uniqueCode", "")
            name = p.get("nickName", uid)
            if uid:
                TRADER_NAMES[uid] = name
    except Exception as e:
        print(f"[WARN] Could not load trader profiles: {e}")


# ─── 1. Extract ALL ETH trades ──────────────────────────────────────────────

def extract_eth_trades():
    """Extract all ETH-USDT-SWAP trades from okx_trade_history.json."""
    try:
        with open(TRADE_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Cannot read trade history: {e}")
        return []

    traders = data.get("traders", {})
    eth_trades = []

    for trader_id, trades in traders.items():
        trader_name = TRADER_NAMES.get(trader_id, trader_id[:8])
        for t in trades:
            inst = t.get("inst", "")
            if "ETH" not in inst:
                continue
            trade = {
                "trader_id": trader_id,
                "trader_name": trader_name,
                "inst": inst,
                "side": t.get("side", "").upper(),
                "leverage": t.get("leverage", 1.0),
                "margin_mode": t.get("margin_mode", "isolated"),
                "entry_price": t.get("entry_price", 0),
                "exit_price": t.get("exit_price", 0),
                "open_time": t.get("open_time", 0),
                "close_time": t.get("close_time", 0),
                "hold_hours": t.get("hold_hours", 0),
                "pnl_usd": t.get("pnl_usd", 0),
                "pnl_pct": t.get("pnl_pct", 0),
                "size": t.get("size", 0),
                "trade_id": t.get("trade_id", ""),
            }
            # Compute win/loss
            trade["is_win"] = 1 if trade["pnl_usd"] > 0 else 0
            eth_trades.append(trade)

    print(f"[ETH] Extracted {len(eth_trades)} ETH trades from {len(traders)} traders")
    return eth_trades


# ─── 2. Fetch 2-year ETH-USD hourly OHLCV ───────────────────────────────────

def _fetch_binance_klines(symbol, interval, start_ms, end_ms, limit=1000):
    """Fetch klines from Binance with 3-endpoint failover."""
    import requests
    for endpoint in BINANCE_ENDPOINTS:
        try:
            url = (f"{endpoint}/api/v3/klines?symbol={symbol}"
                   f"&interval={interval}&startTime={start_ms}"
                   f"&endTime={end_ms}&limit={limit}")
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(2)
                continue
        except Exception:
            continue
    return []


def _fetch_coingecko_fallback(days=730):
    """Fallback: CoinGecko hourly data (max 90 days per call)."""
    import requests
    all_prices = []
    try:
        # CoinGecko only gives hourly for <=90 days, so we chunk
        chunks = min(days // 90 + 1, 9)
        for i in range(chunks):
            chunk_days = min(90, days - i * 90)
            if chunk_days <= 0:
                break
            to_ts = int(time.time()) - (i * 90 * 86400)
            from_ts = to_ts - (chunk_days * 86400)
            url = (f"{COINGECKO_ENDPOINT}/coins/ethereum/market_chart/range"
                   f"?vs_currency=usd&from={from_ts}&to={to_ts}")
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                prices = data.get("prices", [])
                all_prices.extend(prices)
            time.sleep(1.5)  # CoinGecko rate limit
    except Exception as e:
        print(f"[WARN] CoinGecko fallback error: {e}")
    return all_prices


def fetch_eth_ohlcv_2y():
    """Fetch ~2 years of ETH-USDT hourly OHLCV data.

    Uses Binance klines in 1000-candle chunks (41.6 days each).
    Falls back to CoinGecko if Binance fails.
    Returns list of dicts: {ts, open, high, low, close, volume}
    """
    import requests
    symbol = "ETHUSDT"
    interval = "1h"
    now_ms = int(time.time() * 1000)
    two_years_ago_ms = now_ms - (730 * 24 * 3600 * 1000)

    all_candles = []
    cursor = two_years_ago_ms
    chunk_size_ms = 1000 * 3600 * 1000  # 1000 hours

    print("[ETH] Fetching 2-year hourly OHLCV from Binance...")
    attempts = 0
    max_attempts = 20  # ~20 chunks covers 2 years

    while cursor < now_ms and attempts < max_attempts:
        end_ms = min(cursor + chunk_size_ms, now_ms)
        klines = _fetch_binance_klines(symbol, interval, cursor, end_ms, limit=1000)
        if not klines:
            print(f"[WARN] Binance returned no data for chunk starting {cursor}. Trying next chunk.")
            cursor = end_ms
            attempts += 1
            time.sleep(0.5)
            continue

        for k in klines:
            all_candles.append({
                "ts": int(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })
        cursor = int(klines[-1][0]) + 3600000  # next hour
        attempts += 1
        time.sleep(0.3)  # rate limit

    if len(all_candles) < 100:
        print("[WARN] Binance data insufficient, trying CoinGecko fallback...")
        cg_prices = _fetch_coingecko_fallback(730)
        if cg_prices:
            all_candles = []
            for ts_ms, price in cg_prices:
                all_candles.append({
                    "ts": int(ts_ms),
                    "open": price,
                    "high": price * 1.001,
                    "low": price * 0.999,
                    "close": price,
                    "volume": 0,
                })

    # Deduplicate by timestamp
    seen_ts = set()
    unique = []
    for c in all_candles:
        if c["ts"] not in seen_ts:
            seen_ts.add(c["ts"])
            unique.append(c)
    unique.sort(key=lambda x: x["ts"])

    print(f"[ETH] Loaded {len(unique)} hourly candles ({len(unique)/24:.0f} days)")
    return unique


# ─── 3. Compute 20+ technical features ──────────────────────────────────────

def _sma(values, period):
    """Simple moving average."""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _ema(values, period):
    """Exponential moving average."""
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema_val = sum(values[:period]) / period
    for v in values[period:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val


def _rsi(closes, period=14):
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr(highs, lows, closes, period=14):
    """Average True Range."""
    if len(closes) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)
    if len(trs) < period:
        return sum(trs) / len(trs) if trs else 0
    return sum(trs[-period:]) / period


def _adx(highs, lows, closes, period=14):
    """Average Directional Index (simplified)."""
    if len(closes) < period * 2:
        return 20.0
    plus_dm = []
    minus_dm = []
    for i in range(1, len(highs)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)

    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)

    if len(trs) < period:
        return 20.0

    atr_val = sum(trs[-period:]) / period
    if atr_val == 0:
        return 20.0
    plus_di = 100 * (sum(plus_dm[-period:]) / period) / atr_val
    minus_di = 100 * (sum(minus_dm[-period:]) / period) / atr_val
    denom = plus_di + minus_di
    if denom == 0:
        return 0.0
    dx = 100 * abs(plus_di - minus_di) / denom
    return dx


def _bollinger_position(closes, period=20, num_std=2):
    """Position within Bollinger Bands (0=lower, 0.5=middle, 1=upper)."""
    if len(closes) < period:
        return 0.5
    sma = sum(closes[-period:]) / period
    std = statistics.stdev(closes[-period:]) if len(closes[-period:]) > 1 else 0
    if std == 0:
        return 0.5
    upper = sma + num_std * std
    lower = sma - num_std * std
    band_width = upper - lower
    if band_width == 0:
        return 0.5
    return max(0, min(1, (closes[-1] - lower) / band_width))


def _macd(closes, fast=12, slow=26, signal=9):
    """MACD line, signal line, histogram."""
    if len(closes) < slow + signal:
        return 0, 0, 0
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    if ema_fast is None or ema_slow is None:
        return 0, 0, 0
    macd_line = ema_fast - ema_slow
    # Simplified signal: just return the line value and direction
    return macd_line, 0, macd_line


def _volume_ratio(volumes, period=20):
    """Current volume vs average volume ratio."""
    if len(volumes) < period + 1:
        return 1.0
    avg = sum(volumes[-period - 1:-1]) / period
    if avg == 0:
        return 1.0
    return volumes[-1] / avg


def _price_change_pct(closes, period):
    """Price change over N periods."""
    if len(closes) < period + 1:
        return 0.0
    if closes[-period - 1] == 0:
        return 0.0
    return ((closes[-1] - closes[-period - 1]) / closes[-period - 1]) * 100


def _hour_of_day(ts_ms):
    """UTC hour from millisecond timestamp."""
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).hour


def _day_of_week(ts_ms):
    """Day of week (0=Monday, 6=Sunday) from millisecond timestamp."""
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).weekday()


def compute_features_at_timestamp(candles_by_ts, entry_ts_ms, lookback=200):
    """Compute 24 technical features for a given entry timestamp.

    candles_by_ts: dict mapping ts -> candle dict
    entry_ts_ms: trade entry timestamp in ms
    lookback: number of hours to look back

    Returns dict of feature_name -> value, or None if insufficient data.
    """
    # Find nearest candle timestamp (round down to hour)
    entry_hour_ts = (entry_ts_ms // 3600000) * 3600000

    # Collect candles for lookback period
    candle_list = []
    for i in range(lookback, -1, -1):
        ts = entry_hour_ts - (i * 3600000)
        if ts in candles_by_ts:
            candle_list.append(candles_by_ts[ts])

    if len(candle_list) < 50:
        return None

    closes = [c["close"] for c in candle_list]
    highs = [c["high"] for c in candle_list]
    lows = [c["low"] for c in candle_list]
    opens = [c["open"] for c in candle_list]
    volumes = [c["volume"] for c in candle_list]

    price = closes[-1]
    if price == 0:
        return None

    features = {}

    # Trend indicators
    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    sma100 = _sma(closes, 100)
    sma200 = _sma(closes, 200)
    ema9 = _ema(closes, 9)
    ema21 = _ema(closes, 21)

    features["price"] = price
    features["sma20_dist_pct"] = ((price - sma20) / sma20 * 100) if sma20 else 0
    features["sma50_dist_pct"] = ((price - sma50) / sma50 * 100) if sma50 else 0
    features["sma100_dist_pct"] = ((price - sma100) / sma100 * 100) if sma100 else 0
    features["sma200_dist_pct"] = ((price - sma200) / sma200 * 100) if sma200 else 0
    features["ema9_above_ema21"] = 1 if (ema9 and ema21 and ema9 > ema21) else 0

    # Momentum
    features["rsi_14"] = _rsi(closes, 14)
    features["rsi_7"] = _rsi(closes, 7)
    macd_line, _, macd_hist = _macd(closes)
    features["macd_line"] = macd_line
    features["macd_histogram"] = macd_hist

    # Volatility
    features["atr_14"] = _atr(highs, lows, closes, 14)
    features["atr_pct"] = (features["atr_14"] / price * 100) if price else 0
    features["bb_position"] = _bollinger_position(closes, 20, 2)
    features["adx_14"] = _adx(highs, lows, closes, 14)

    # Volume
    features["volume_ratio_20"] = _volume_ratio(volumes, 20)
    features["volume_ratio_5"] = _volume_ratio(volumes, 5)

    # Price changes (momentum at various timeframes)
    features["change_1h_pct"] = _price_change_pct(closes, 1)
    features["change_4h_pct"] = _price_change_pct(closes, 4)
    features["change_24h_pct"] = _price_change_pct(closes, 24)
    features["change_72h_pct"] = _price_change_pct(closes, 72)
    features["change_168h_pct"] = _price_change_pct(closes, 168)  # 7 days

    # Time features
    features["hour_utc"] = _hour_of_day(entry_ts_ms)
    features["day_of_week"] = _day_of_week(entry_ts_ms)
    features["is_london_ny_overlap"] = 1 if 11 <= features["hour_utc"] <= 15 else 0

    # Range position (where price sits in recent range)
    high_24 = max(highs[-24:]) if len(highs) >= 24 else max(highs)
    low_24 = min(lows[-24:]) if len(lows) >= 24 else min(lows)
    range_24 = high_24 - low_24
    features["range_position_24h"] = ((price - low_24) / range_24) if range_24 > 0 else 0.5

    # Candle pattern (last candle)
    last_body = closes[-1] - opens[-1]
    last_range = highs[-1] - lows[-1]
    features["last_candle_body_pct"] = (last_body / opens[-1] * 100) if opens[-1] else 0
    features["last_candle_wick_ratio"] = (last_range / abs(last_body)) if last_body != 0 else 1

    return features


# ─── 4. ML Classifier ───────────────────────────────────────────────────────

def train_eth_classifier(trades_with_features):
    """Train a RandomForest classifier to predict ETH trade outcomes.

    Falls back to statistical scoring if sklearn not available.
    Returns (model_or_None, feature_names, feature_importances, accuracy).
    """
    if not trades_with_features:
        return None, [], {}, 0.0

    feature_names = [
        "sma20_dist_pct", "sma50_dist_pct", "sma100_dist_pct", "sma200_dist_pct",
        "ema9_above_ema21", "rsi_14", "rsi_7", "macd_line", "macd_histogram",
        "atr_pct", "bb_position", "adx_14", "volume_ratio_20", "volume_ratio_5",
        "change_1h_pct", "change_4h_pct", "change_24h_pct", "change_72h_pct",
        "change_168h_pct", "hour_utc", "day_of_week", "is_london_ny_overlap",
        "range_position_24h", "last_candle_body_pct", "leverage",
    ]

    # Build feature matrix
    X = []
    y = []
    for t in trades_with_features:
        f = t.get("features")
        if not f:
            continue
        row = []
        for fn in feature_names:
            if fn == "leverage":
                row.append(t.get("leverage", 1.0))
            else:
                val = f.get(fn, 0)
                if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
                    row.append(0)
                else:
                    row.append(float(val))
        # Label: direction + outcome combined
        # 1 = winning short, 0 = losing trade, 2 = winning long
        side = t.get("side", "").upper()
        is_win = t.get("is_win", 0)
        if side == "SHORT" and is_win:
            y.append(1)
        elif side == "LONG" and is_win:
            y.append(2)
        else:
            y.append(0)
        X.append(row)

    if len(X) < 10:
        print(f"[ML] Only {len(X)} samples -- insufficient for training")
        return None, feature_names, {}, 0.0

    # Try sklearn RandomForest
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score
        import numpy as np

        X_arr = np.array(X, dtype=np.float64)
        y_arr = np.array(y)

        # Replace any remaining NaN/inf
        X_arr = np.nan_to_num(X_arr, nan=0, posinf=0, neginf=0)

        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_leaf=3,
            random_state=42,
            class_weight="balanced",
        )

        # Cross-validation
        n_splits = min(5, max(2, len(X) // 5))
        if n_splits >= 2:
            scores = cross_val_score(model, X_arr, y_arr, cv=n_splits, scoring="accuracy")
            accuracy = float(np.mean(scores))
        else:
            accuracy = 0.0

        # Train final model on all data
        model.fit(X_arr, y_arr)

        importances = dict(zip(feature_names, model.feature_importances_.tolist()))
        print(f"[ML] RandomForest trained: {accuracy:.1%} CV accuracy on {len(X)} samples")
        return model, feature_names, importances, accuracy

    except ImportError:
        print("[ML] sklearn not available, using statistical fallback")

    # Statistical fallback: compute feature-outcome correlations
    importances = {}
    for i, fn in enumerate(feature_names):
        vals_win = [X[j][i] for j in range(len(X)) if y[j] > 0]
        vals_lose = [X[j][i] for j in range(len(X)) if y[j] == 0]
        if vals_win and vals_lose:
            mean_diff = abs(statistics.mean(vals_win) - statistics.mean(vals_lose))
            combined_std = statistics.stdev(vals_win + vals_lose) if len(vals_win + vals_lose) > 1 else 1
            importances[fn] = mean_diff / combined_std if combined_std > 0 else 0
        else:
            importances[fn] = 0

    # Normalize importances
    total_imp = sum(importances.values())
    if total_imp > 0:
        importances = {k: v / total_imp for k, v in importances.items()}

    accuracy = sum(1 for yi in y if yi > 0) / len(y) if y else 0
    print(f"[ML] Statistical fallback: base WR = {accuracy:.1%} on {len(X)} samples")
    return None, feature_names, importances, accuracy


# ─── 5. Generate 5 ETH-specific strategy variations ─────────────────────────

def generate_eth_variations(eth_trades, analysis_stats):
    """Generate 5 ETH-specific strategy variations based on trader patterns.

    v1: SHORT-only ETH (79% WR from nightraid- data)
    v2: High-leverage momentum (47x, only when ADX>25)
    v3: Patience variant (hold winners 150h+, cut losers at 30h)
    v4: London/NY overlap only (11-15 UTC)
    v5: Scale-into-winners (start small, add to winners)
    """
    # Compute aggregate stats
    short_trades = [t for t in eth_trades if t["side"] == "SHORT"]
    long_trades = [t for t in eth_trades if t["side"] == "LONG"]
    short_wr = sum(1 for t in short_trades if t["is_win"]) / len(short_trades) if short_trades else 0
    long_wr = sum(1 for t in long_trades if t["is_win"]) / len(long_trades) if long_trades else 0

    # De-leverage PnL to get actual price move percentages
    # pnl_pct in data is already leveraged, so divide by leverage to get price move
    win_price_moves = []
    for t in eth_trades:
        if t["is_win"]:
            lev = max(t.get("leverage", 1), 1)
            win_price_moves.append(abs(t["pnl_pct"]) / lev)
    lose_price_moves = []
    for t in eth_trades:
        if not t["is_win"]:
            lev = max(t.get("leverage", 1), 1)
            lose_price_moves.append(abs(t["pnl_pct"]) / lev)

    avg_win_price_move = statistics.mean(win_price_moves) if win_price_moves else 5.0
    avg_lose_price_move = statistics.mean(lose_price_moves) if lose_price_moves else 3.0
    median_win_price_move = statistics.median(win_price_moves) if win_price_moves else 3.0
    median_lose_price_move = statistics.median(lose_price_moves) if lose_price_moves else 2.0

    # nightraid- specific stats
    nightraid_trades = [t for t in eth_trades if "nightraid" in t.get("trader_name", "").lower()]
    nightraid_shorts = [t for t in nightraid_trades if t["side"] == "SHORT"]
    nightraid_short_wr = sum(1 for t in nightraid_shorts if t["is_win"]) / len(nightraid_shorts) if nightraid_shorts else 0.79
    nightraid_avg_lev = statistics.mean([t["leverage"] for t in nightraid_trades]) if nightraid_trades else 47.2

    # Compute hour distribution for best trading hours
    hour_wins = defaultdict(int)
    hour_total = defaultdict(int)
    for t in eth_trades:
        h = _hour_of_day(t["open_time"])
        hour_total[h] += 1
        if t["is_win"]:
            hour_wins[h] += 1
    best_hours = sorted(hour_total.keys(),
                        key=lambda h: hour_wins.get(h, 0) / hour_total[h] if hour_total[h] >= 2 else 0,
                        reverse=True)[:6]

    now_str = datetime.now(timezone.utc).isoformat()

    variations = [
        {
            "variation_id": "eth_v1_short_only",
            "name": "ETH Short Specialist",
            "description": "SHORT-only ETH based on 75-79% WR short bias from nightraid- and Expert-Ethash-Camel",
            "source_system": SOURCE_SYSTEM,
            "coin": "ETHUSDT",
            "direction": "SHORT",
            "tp_pct": round(min(median_win_price_move * 0.8, 8.0), 2),
            "sl_pct": round(min(median_lose_price_move * 0.6, 4.0), 2),
            "max_hold_hours": 48,
            "leverage": 10,
            "entry_conditions": {
                "rsi_14_above": 55,
                "bb_position_above": 0.6,
                "adx_above": 15,
                "sma20_dist_pct_above": 0.5,
            },
            "entry_hours_utc": best_hours,
            "session": "ANY",
            "starting_capital": 1000,
            "status": "ACTIVE",
            "source_wr": round(short_wr, 4),
            "nightraid_short_wr": round(nightraid_short_wr, 4),
            "source_trades": len(short_trades),
            "created_at": now_str,
        },
        {
            "variation_id": "eth_v2_high_lev_momentum",
            "name": "ETH High-Leverage Momentum",
            "description": "47x leverage momentum trades like nightraid-, only when ADX>25 confirms trend strength",
            "source_system": SOURCE_SYSTEM,
            "coin": "ETHUSDT",
            "direction": "BOTH",
            "tp_pct": round(median_win_price_move * 0.4, 2),  # Tighter TP for high leverage
            "sl_pct": round(min(median_lose_price_move * 0.25, 1.0), 2),  # Very tight SL
            "max_hold_hours": 12,
            "leverage": 47,
            "entry_conditions": {
                "adx_above": 25,
                "volume_ratio_20_above": 1.3,
                "atr_pct_above": 0.8,
                "short_when_rsi_above": 65,
                "long_when_rsi_below": 35,
            },
            "entry_hours_utc": best_hours,
            "session": "HIGH_VOLATILITY",
            "starting_capital": 500,
            "status": "ACTIVE",
            "source_wr": round((short_wr + long_wr) / 2, 4),
            "nightraid_avg_leverage": round(nightraid_avg_lev, 1),
            "source_trades": len(eth_trades),
            "created_at": now_str,
        },
        {
            "variation_id": "eth_v3_patience",
            "name": "ETH Patience (Hold Winners)",
            "description": "Hold winners 150h+, cut losers at 30h -- mirrors nightraid-'s 123h avg hold pattern",
            "source_system": SOURCE_SYSTEM,
            "coin": "ETHUSDT",
            "direction": "BOTH",
            "tp_pct": round(avg_win_price_move * 1.2, 2),  # Wide TP for long holds
            "sl_pct": round(median_lose_price_move * 0.8, 2),
            "max_hold_hours": 200,
            "min_hold_winners_hours": 150,
            "max_hold_losers_hours": 30,
            "leverage": 5,
            "entry_conditions": {
                "sma50_dist_pct_range": [-3, 3],
                "rsi_14_range": [35, 65],
                "change_24h_pct_range": [-5, 5],
            },
            "entry_hours_utc": list(range(24)),
            "session": "ANY",
            "starting_capital": 1000,
            "status": "ACTIVE",
            "source_wr": round((short_wr * 0.4 + long_wr * 0.6), 4),
            "nightraid_avg_hold_hours": 123,
            "source_trades": len(eth_trades),
            "created_at": now_str,
        },
        {
            "variation_id": "eth_v4_london_ny_overlap",
            "name": "ETH London/NY Overlap",
            "description": "Trade only during 11-15 UTC (London/NY overlap) -- nightraid-'s best performing hours",
            "source_system": SOURCE_SYSTEM,
            "coin": "ETHUSDT",
            "direction": "SHORT",  # Short bias during overlap (higher WR)
            "tp_pct": round(median_win_price_move * 0.7, 2),
            "sl_pct": round(median_lose_price_move * 0.5, 2),
            "max_hold_hours": 24,
            "leverage": 15,
            "entry_conditions": {
                "hour_utc_range": [11, 15],
                "adx_above": 18,
                "volume_ratio_20_above": 1.0,
            },
            "entry_hours_utc": [11, 12, 13, 14, 15],
            "session": "LONDON_NY_OVERLAP",
            "starting_capital": 1000,
            "status": "ACTIVE",
            "source_wr": round(short_wr, 4),
            "overlap_trades": sum(1 for t in eth_trades if 11 <= _hour_of_day(t["open_time"]) <= 15),
            "source_trades": len(eth_trades),
            "created_at": now_str,
        },
        {
            "variation_id": "eth_v5_scale_into_winners",
            "name": "ETH Scale-Into-Winners",
            "description": "Start small (25% size), add 25% every time position is +1% -- nightraid- pattern yields 4x larger wins",
            "source_system": SOURCE_SYSTEM,
            "coin": "ETHUSDT",
            "direction": "BOTH",
            "tp_pct": round(avg_win_price_move * 1.0, 2),
            "sl_pct": round(median_lose_price_move * 0.6, 2),
            "max_hold_hours": 120,
            "leverage": 10,
            "scaling": {
                "initial_size_pct": 25,
                "add_at_profit_pct": [1, 2, 3],
                "add_size_pct": 25,
                "max_additions": 3,
            },
            "entry_conditions": {
                "rsi_14_range": [30, 70],
                "adx_above": 20,
                "change_4h_pct_abs_above": 0.5,
            },
            "entry_hours_utc": best_hours,
            "session": "ANY",
            "starting_capital": 2000,
            "status": "ACTIVE",
            "source_wr": round((short_wr + long_wr) / 2, 4),
            "avg_win_vs_loss_ratio": round(avg_win_price_move / avg_lose_price_move, 2) if avg_lose_price_move > 0 else 2.0,
            "source_trades": len(eth_trades),
            "created_at": now_str,
        },
    ]

    return variations


# ─── 6. Backtest each variation on 2-year data ──────────────────────────────

def _check_entry_conditions(features, conditions):
    """Check if current market features match entry conditions."""
    if not features or not conditions:
        return True

    for key, val in conditions.items():
        if key.endswith("_above"):
            feat_name = key.replace("_above", "")
            if feat_name in features and features[feat_name] < val:
                return False
        elif key.endswith("_below"):
            feat_name = key.replace("_below", "")
            if feat_name in features and features[feat_name] > val:
                return False
        elif key.endswith("_range"):
            feat_name = key.replace("_range", "")
            if feat_name in features and isinstance(val, list) and len(val) == 2:
                if features[feat_name] < val[0] or features[feat_name] > val[1]:
                    return False
        elif key == "hour_utc_range" and isinstance(val, list) and len(val) == 2:
            hour = features.get("hour_utc", 12)
            if not (val[0] <= hour <= val[1]):
                return False
        elif key == "short_when_rsi_above":
            pass  # Handled by direction logic
        elif key == "long_when_rsi_below":
            pass  # Handled by direction logic

    return True


def _determine_direction(features, variation):
    """Determine trade direction for BOTH-direction variations."""
    direction = variation.get("direction", "BOTH")
    if direction in ("SHORT", "LONG"):
        return direction

    conditions = variation.get("entry_conditions", {})
    rsi = features.get("rsi_14", 50) if features else 50

    short_rsi = conditions.get("short_when_rsi_above", 65)
    long_rsi = conditions.get("long_when_rsi_below", 35)

    if rsi > short_rsi:
        return "SHORT"
    elif rsi < long_rsi:
        return "LONG"

    # Default: follow short-term trend
    change = features.get("change_4h_pct", 0) if features else 0
    return "SHORT" if change > 0.5 else "LONG" if change < -0.5 else None


def backtest_variation(variation, candles, candles_by_ts):
    """Backtest a single variation on historical candle data.

    Simulates trades using 4-hour evaluation intervals.
    Returns backtest results dict.
    """
    name = variation["variation_id"]
    tp_pct = variation.get("tp_pct", 3.0)
    sl_pct = variation.get("sl_pct", 1.5)
    max_hold = variation.get("max_hold_hours", 48)
    leverage = variation.get("leverage", 10)
    entry_hours = set(variation.get("entry_hours_utc", range(24)))
    conditions = variation.get("entry_conditions", {})
    capital = variation.get("starting_capital", 1000)

    min_hold_winners = variation.get("min_hold_winners_hours", 0)
    max_hold_losers = variation.get("max_hold_losers_hours", max_hold)
    has_scaling = "scaling" in variation

    trades = []
    equity = capital
    peak_equity = capital
    max_drawdown = 0
    in_trade = False
    entry_price = 0
    entry_idx = 0
    trade_dir = None
    cooldown = 0

    # Use every 4th candle as potential entry (avoid overtrading)
    step = 4
    for i in range(200, len(candles) - max_hold, step):
        candle = candles[i]
        ts = candle["ts"]
        hour = _hour_of_day(ts)

        if cooldown > 0:
            cooldown -= step
            continue

        if in_trade:
            # Check exit conditions
            hours_held = (i - entry_idx)  # hours since entry
            current_price = candle["close"]

            if trade_dir == "SHORT":
                pnl_pct = ((entry_price - current_price) / entry_price) * 100 * leverage
            else:
                pnl_pct = ((current_price - entry_price) / entry_price) * 100 * leverage

            # Scale-into-winners simulation
            scale_bonus = 1.0
            if has_scaling and pnl_pct > 0:
                scaling = variation["scaling"]
                adds = sum(1 for thresh in scaling.get("add_at_profit_pct", [])
                           if pnl_pct / leverage >= thresh)
                adds = min(adds, scaling.get("max_additions", 3))
                initial = scaling.get("initial_size_pct", 25) / 100
                add_pct = scaling.get("add_size_pct", 25) / 100
                scale_bonus = initial + adds * add_pct

            # Patience variant: hold winners longer
            if min_hold_winners > 0 and pnl_pct > 0 and hours_held < min_hold_winners:
                if pnl_pct < -sl_pct:  # But still honor SL
                    pass  # Fall through to SL check
                elif hours_held < max_hold:
                    continue  # Keep holding winner

            # Exit conditions
            hit_tp = pnl_pct >= tp_pct
            hit_sl = pnl_pct <= -sl_pct
            timed_out = hours_held >= max_hold
            loser_timeout = (max_hold_losers < max_hold and pnl_pct < 0
                             and hours_held >= max_hold_losers)

            if hit_tp or hit_sl or timed_out or loser_timeout:
                final_pnl_pct = pnl_pct * scale_bonus if has_scaling else pnl_pct
                trade_pnl_usd = equity * (final_pnl_pct / 100)
                equity += trade_pnl_usd
                peak_equity = max(peak_equity, equity)
                dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
                max_drawdown = max(max_drawdown, dd)

                trades.append({
                    "direction": trade_dir,
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(current_price, 2),
                    "pnl_pct": round(final_pnl_pct, 2),
                    "pnl_usd": round(trade_pnl_usd, 2),
                    "hold_hours": hours_held,
                    "exit_reason": "TP" if hit_tp else "SL" if hit_sl else "LOSER_CUT" if loser_timeout else "TIMEOUT",
                    "is_win": 1 if trade_pnl_usd > 0 else 0,
                })

                in_trade = False
                cooldown = 4  # 4-hour cooldown between trades
                if equity <= 0:
                    break
            continue

        # Not in trade -- check entry
        if hour not in entry_hours:
            continue

        # Compute features at this candle
        features = compute_features_at_timestamp(candles_by_ts, ts, lookback=200)
        if not features:
            continue

        if not _check_entry_conditions(features, conditions):
            continue

        direction = _determine_direction(features, variation)
        if direction is None:
            continue

        # Enter trade
        in_trade = True
        entry_price = candle["close"]
        entry_idx = i
        trade_dir = direction

    # Compute stats
    if not trades:
        return {
            "variation_id": name,
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl_pct": 0,
            "max_drawdown_pct": 0,
            "sharpe_ratio": 0,
            "final_equity": capital,
            "roi_pct": 0,
        }

    wins = sum(1 for t in trades if t["is_win"])
    wr = wins / len(trades) if trades else 0
    pnl_list = [t["pnl_pct"] for t in trades]
    total_pnl = sum(pnl_list)
    avg_pnl = statistics.mean(pnl_list) if pnl_list else 0
    std_pnl = statistics.stdev(pnl_list) if len(pnl_list) > 1 else 1
    sharpe = (avg_pnl / std_pnl * math.sqrt(252)) if std_pnl > 0 else 0

    avg_win = statistics.mean([t["pnl_pct"] for t in trades if t["is_win"]]) if wins > 0 else 0
    avg_loss = statistics.mean([abs(t["pnl_pct"]) for t in trades if not t["is_win"]]) if (len(trades) - wins) > 0 else 0
    profit_factor = (avg_win * wins) / (avg_loss * (len(trades) - wins)) if avg_loss > 0 and (len(trades) - wins) > 0 else 999

    return {
        "variation_id": name,
        "name": variation.get("name", name),
        "total_trades": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "win_rate": round(wr, 4),
        "total_pnl_pct": round(total_pnl, 2),
        "avg_pnl_pct": round(avg_pnl, 2),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "final_equity": round(equity, 2),
        "roi_pct": round((equity - capital) / capital * 100, 2),
        "trades_sample": trades[:10],  # First 10 trades for inspection
    }


# ─── 7. Generate ML picks ───────────────────────────────────────────────────

def generate_ml_picks(model, feature_names, candles, candles_by_ts, variations):
    """Generate current ML-based picks using the trained model and latest data."""
    if not candles:
        return []

    latest_ts = candles[-1]["ts"]
    features = compute_features_at_timestamp(candles_by_ts, latest_ts, lookback=200)
    if not features:
        return []

    picks = []
    now_str = datetime.now(timezone.utc).isoformat()

    for var in variations:
        var_id = var["variation_id"]
        direction = var.get("direction", "BOTH")
        conditions = var.get("entry_conditions", {})

        # Check conditions but still generate picks with lower confidence if not met
        conditions_met = _check_entry_conditions(features, conditions)

        actual_dir = _determine_direction(features, var) if direction == "BOTH" else direction
        if actual_dir is None:
            # Fallback: use short bias (proven higher WR for ETH)
            actual_dir = "SHORT" if features.get("rsi_14", 50) > 45 else "LONG"

        # Confidence from ML model or feature heuristics
        confidence = 0.5
        if model is not None:
            try:
                import numpy as np
                row = []
                for fn in feature_names:
                    if fn == "leverage":
                        row.append(var.get("leverage", 10))
                    else:
                        val = features.get(fn, 0)
                        row.append(float(val) if val is not None else 0)
                X = np.array([row], dtype=np.float64)
                X = np.nan_to_num(X, nan=0, posinf=0, neginf=0)
                proba = model.predict_proba(X)[0]
                # Class 1 = winning short, class 2 = winning long
                if actual_dir == "SHORT":
                    target_class = 1
                else:
                    target_class = 2
                if target_class in list(model.classes_):
                    idx = list(model.classes_).index(target_class)
                    confidence = float(proba[idx])
                else:
                    confidence = 0.3
            except Exception:
                confidence = 0.5
        else:
            # Heuristic confidence from feature alignment
            rsi = features.get("rsi_14", 50)
            adx = features.get("adx_14", 20)
            bb = features.get("bb_position", 0.5)
            if actual_dir == "SHORT":
                confidence = min(0.9, 0.3 + (rsi - 50) / 100 + (adx - 15) / 100 + (bb - 0.5) / 2)
            else:
                confidence = min(0.9, 0.3 + (50 - rsi) / 100 + (adx - 15) / 100 + (0.5 - bb) / 2)
            confidence = max(0.1, confidence)

        # Reduce confidence if entry conditions not met
        if not conditions_met:
            confidence *= 0.6

        price = features.get("price", candles[-1]["close"])
        tp_pct = var.get("tp_pct", 3.0)
        sl_pct = var.get("sl_pct", 1.5)

        if actual_dir == "SHORT":
            target = round(price * (1 - tp_pct / 100), 2)
            stop = round(price * (1 + sl_pct / 100), 2)
        else:
            target = round(price * (1 + tp_pct / 100), 2)
            stop = round(price * (1 - sl_pct / 100), 2)

        picks.append({
            "symbol": "ETHUSDT",
            "direction": actual_dir,
            "entry_price": round(price, 2),
            "target_price": round(target, 2),
            "stop_price": round(stop, 2),
            "leverage": var.get("leverage", 10),
            "confidence": round(confidence, 4),
            "variation_id": var_id,
            "variation_name": var.get("name", var_id),
            "source_system": SOURCE_SYSTEM,
            "generated_at": now_str,
            "features_snapshot": {
                "rsi_14": round(features.get("rsi_14", 0), 2),
                "adx_14": round(features.get("adx_14", 0), 2),
                "bb_position": round(features.get("bb_position", 0), 4),
                "macd_line": round(features.get("macd_line", 0), 4),
                "change_24h_pct": round(features.get("change_24h_pct", 0), 2),
                "volume_ratio_20": round(features.get("volume_ratio_20", 0), 2),
                "atr_pct": round(features.get("atr_pct", 0), 4),
            },
            "max_hold_hours": var.get("max_hold_hours", 48),
        })

    # Sort by confidence
    picks.sort(key=lambda p: p["confidence"], reverse=True)
    return picks


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  ETH Deep Pattern Analyzer -- source_system: ml_eth_reverser")
    print("=" * 70)

    _load_trader_names()

    # Step 1: Extract ETH trades
    print("\n[1/7] Extracting ETH trades from OKX history...")
    eth_trades = extract_eth_trades()
    if not eth_trades:
        print("[ERROR] No ETH trades found. Exiting.")
        return

    # Compute per-trader stats
    trader_stats = defaultdict(lambda: {"total": 0, "wins": 0, "shorts": 0, "short_wins": 0,
                                         "longs": 0, "long_wins": 0, "leverages": [], "hold_hours": []})
    for t in eth_trades:
        name = t["trader_name"]
        ts = trader_stats[name]
        ts["total"] += 1
        ts["wins"] += t["is_win"]
        ts["leverages"].append(t["leverage"])
        ts["hold_hours"].append(t["hold_hours"])
        if t["side"] == "SHORT":
            ts["shorts"] += 1
            ts["short_wins"] += t["is_win"]
        else:
            ts["longs"] += 1
            ts["long_wins"] += t["is_win"]

    for name, ts in trader_stats.items():
        ts["wr"] = round(ts["wins"] / ts["total"], 4) if ts["total"] else 0
        ts["short_wr"] = round(ts["short_wins"] / ts["shorts"], 4) if ts["shorts"] else 0
        ts["long_wr"] = round(ts["long_wins"] / ts["longs"], 4) if ts["longs"] else 0
        ts["avg_leverage"] = round(statistics.mean(ts["leverages"]), 1) if ts["leverages"] else 0
        ts["avg_hold_hours"] = round(statistics.mean(ts["hold_hours"]), 1) if ts["hold_hours"] else 0
        # Clean up list fields for JSON
        del ts["leverages"]
        del ts["hold_hours"]

    print(f"  Trader ETH stats:")
    for name, ts in trader_stats.items():
        print(f"    {name}: {ts['total']} trades, WR={ts['wr']:.1%}, "
              f"Short WR={ts['short_wr']:.1%} ({ts['shorts']}), "
              f"Long WR={ts['long_wr']:.1%} ({ts['longs']}), "
              f"Avg Lev={ts['avg_leverage']}x")

    # Step 2: Fetch 2-year OHLCV
    print("\n[2/7] Fetching 2-year ETH-USD hourly OHLCV...")
    candles = fetch_eth_ohlcv_2y()
    if len(candles) < 500:
        print(f"[WARN] Only {len(candles)} candles retrieved -- backtest will be limited")

    candles_by_ts = {c["ts"]: c for c in candles}

    # Step 3: Compute features for each trade
    print("\n[3/7] Computing 24 technical features per trade entry...")
    trades_with_features = []
    feature_count = 0
    for t in eth_trades:
        features = compute_features_at_timestamp(candles_by_ts, t["open_time"], lookback=200)
        trade_enriched = dict(t)
        trade_enriched["features"] = features
        trades_with_features.append(trade_enriched)
        if features:
            feature_count += 1

    print(f"  Features computed for {feature_count}/{len(eth_trades)} trades")

    # Step 4: Train ML classifier
    print("\n[4/7] Training ML classifier...")
    model, feature_names, importances, accuracy = train_eth_classifier(trades_with_features)

    # Overall analysis stats
    total_short = sum(1 for t in eth_trades if t["side"] == "SHORT")
    total_long = sum(1 for t in eth_trades if t["side"] == "LONG")
    short_wins = sum(1 for t in eth_trades if t["side"] == "SHORT" and t["is_win"])
    long_wins = sum(1 for t in eth_trades if t["side"] == "LONG" and t["is_win"])

    analysis_stats = {
        "total_eth_trades": len(eth_trades),
        "total_shorts": total_short,
        "total_longs": total_long,
        "short_win_rate": round(short_wins / total_short, 4) if total_short else 0,
        "long_win_rate": round(long_wins / total_long, 4) if total_long else 0,
        "overall_win_rate": round(sum(t["is_win"] for t in eth_trades) / len(eth_trades), 4),
        "avg_pnl_pct": round(statistics.mean([t["pnl_pct"] for t in eth_trades]), 2),
        "avg_leverage": round(statistics.mean([t["leverage"] for t in eth_trades]), 1),
        "avg_hold_hours": round(statistics.mean([t["hold_hours"] for t in eth_trades]), 1),
        "ml_accuracy": round(accuracy, 4),
        "top_features": dict(sorted(importances.items(), key=lambda x: x[1], reverse=True)[:10]),
        "per_trader": dict(trader_stats),
    }

    # Save pattern analysis
    print("\n[5/7] Generating ETH strategy variations...")
    analysis_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_system": SOURCE_SYSTEM,
        "analysis": analysis_stats,
        "candle_count": len(candles),
        "candle_range": {
            "from": datetime.fromtimestamp(candles[0]["ts"] / 1000, tz=timezone.utc).isoformat() if candles else None,
            "to": datetime.fromtimestamp(candles[-1]["ts"] / 1000, tz=timezone.utc).isoformat() if candles else None,
        },
        "feature_importances": importances,
        "trades_analyzed": len(trades_with_features),
        "trades_with_features": feature_count,
    }

    try:
        with open(OUTPUT_ANALYSIS, "w", encoding="utf-8") as f:
            json.dump(analysis_output, f, indent=2, ensure_ascii=False, default=str)
        print(f"  Saved: {OUTPUT_ANALYSIS}")
    except Exception as e:
        print(f"[ERROR] Saving analysis: {e}")

    # Step 5: Generate variations
    variations = generate_eth_variations(eth_trades, analysis_stats)

    # Step 6: Backtest each variation
    print("\n[6/7] Backtesting 5 variations on 2-year data...")
    backtest_results = []
    for var in variations:
        print(f"  Backtesting {var['variation_id']}...")
        try:
            result = backtest_variation(var, candles, candles_by_ts)
            var["backtest"] = result
            backtest_results.append(result)
            print(f"    -> {result['total_trades']} trades, WR={result['win_rate']:.1%}, "
                  f"ROI={result['roi_pct']:.1f}%, Sharpe={result['sharpe_ratio']:.2f}, "
                  f"MaxDD={result['max_drawdown_pct']:.1f}%")
        except Exception as e:
            print(f"    [ERROR] Backtest failed: {e}")
            var["backtest"] = {"error": str(e)}
            backtest_results.append({"variation_id": var["variation_id"], "error": str(e)})

    # Save variations
    variations_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_system": SOURCE_SYSTEM,
        "variation_count": len(variations),
        "variations": variations,
        "backtest_summary": backtest_results,
    }

    try:
        with open(OUTPUT_VARIATIONS, "w", encoding="utf-8") as f:
            json.dump(variations_output, f, indent=2, ensure_ascii=False, default=str)
        print(f"  Saved: {OUTPUT_VARIATIONS}")
    except Exception as e:
        print(f"[ERROR] Saving variations: {e}")

    # Step 7: Generate ML picks
    print("\n[7/7] Generating ML picks from current market state...")
    try:
        picks = generate_ml_picks(model, feature_names, candles, candles_by_ts, variations)

        picks_output = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_system": SOURCE_SYSTEM,
            "model_type": "RandomForest" if model else "statistical_heuristic",
            "model_accuracy": round(accuracy, 4),
            "pick_count": len(picks),
            "picks": picks,
        }

        with open(OUTPUT_ML_PICKS, "w", encoding="utf-8") as f:
            json.dump(picks_output, f, indent=2, ensure_ascii=False, default=str)
        print(f"  Saved: {OUTPUT_ML_PICKS} ({len(picks)} picks)")
    except Exception as e:
        print(f"[ERROR] Generating ML picks: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("  ETH Analysis Complete")
    print("=" * 70)
    print(f"  ETH Trades Analyzed: {len(eth_trades)}")
    print(f"  Short WR: {analysis_stats['short_win_rate']:.1%} ({total_short} trades)")
    print(f"  Long WR: {analysis_stats['long_win_rate']:.1%} ({total_long} trades)")
    print(f"  ML Accuracy: {accuracy:.1%}")
    print(f"  Variations: {len(variations)}")
    print(f"  Candles: {len(candles)} ({len(candles)/24:.0f} days)")
    for r in backtest_results:
        if "error" not in r:
            print(f"  {r.get('name', r['variation_id'])}: "
                  f"WR={r['win_rate']:.1%}, ROI={r['roi_pct']:.1f}%, "
                  f"Sharpe={r['sharpe_ratio']:.2f}")
    print(f"\n  Outputs:")
    print(f"    {OUTPUT_ANALYSIS}")
    print(f"    {OUTPUT_VARIATIONS}")
    print(f"    {OUTPUT_ML_PICKS}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
