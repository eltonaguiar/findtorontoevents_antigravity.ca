"""
Approach A: Pure S/R Breakout Scanner
Detects support/resistance breakouts on BTC 4h with volume + ATR confirmation.
Target: 100-300 trades/year. No ML -- pure rules.

Run: python breakout_arena/approach_a_sr_breakout/scanner.py [--dry-run]
"""
import os
import sys
import json
import math
import argparse
import time
import requests
import numpy as np
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SYSTEM_NAME = "Approach A: S/R Breakout"
SYSTEM_ID = "approach_a"
VERSION = "1.0.0"
TIMEFRAME = "4h"
SCAN_FREQUENCY = "Every 30 minutes"
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
         "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "DOTUSDT"]
CORRELATION_PAIR = "ETHUSDT"

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
EST = timezone(timedelta(hours=-5))

_BINANCE_BASES = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]
BINANCE_BASE = "https://api.binance.com"

# Cost model: 0.10% maker + 0.05% slippage each way = 0.25% round-trip
ROUND_TRIP_COST_PCT = 0.0025

# Risk params
EQUITY_RISK_PCT = 0.02       # 2% risk per trade
STARTING_EQUITY = 10_000.0
TRAILING_ACTIVATION_PCT = 0.02   # activate trailing stop at +2%
TRAILING_DISTANCE_PCT = 0.03     # trail 3% from HWM
MAX_HOLD_HOURS = 72              # 3 days max hold — auto-expire stale picks

# Breakout filters
VOLUME_RATIO_THRESHOLD = 1.3     # volume must be 1.3x 20-bar avg (was 2.0 — too strict, BTC rarely 2x)
ATR_EXPANSION_RATIO = 0.9        # ATR(14) > 0.9x SMA(20) of ATR (was 1.2 — missed breakouts in low-vol)
RSI_BUY_RANGE = (35, 80)
RSI_SELL_RANGE = (20, 65)
FEAR_GREED_BUY_MIN = 20
FEAR_GREED_SELL_MAX = 80
MIN_RR = 1.5


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class SRLevel:
    price: float
    strength: float
    touches: int
    level_type: str       # "support" | "resistance"
    source: str           # "fractal" | "volume_profile" | "round_number"
    recency: float        # 0-1


# ---------------------------------------------------------------------------
# Data Fetching (self-contained, Binance REST)
# ---------------------------------------------------------------------------
def fetch_klines(symbol: str, interval: str = "4h", limit: int = 500) -> Optional[np.ndarray]:
    """
    Fetch OHLCV with Binance → OKX → Bybit fallback chain.
    Returns numpy array [timestamp_ms, open, high, low, close, volume] or None.
    """
    # Try Binance first
    arr = _fetch_binance(symbol, interval, limit)
    if arr is not None:
        return arr
    # Fallback: OKX
    arr = _fetch_okx(symbol, interval, limit)
    if arr is not None:
        print(f"  [INFO] {symbol} fetched from OKX fallback")
        return arr
    # Fallback: Bybit
    arr = _fetch_bybit(symbol, interval, limit)
    if arr is not None:
        print(f"  [INFO] {symbol} fetched from Bybit fallback")
        return arr
    print(f"  [ERROR] All exchanges failed for {symbol}")
    return None


def _fetch_binance(symbol: str, interval: str, limit: int) -> Optional[np.ndarray]:
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
            if not data or len(data) < 50:
                continue
            return np.array([[float(d[0]), float(d[1]), float(d[2]), float(d[3]), float(d[4]), float(d[5])] for d in data])
        except Exception:
            continue
    return None


def _fetch_okx(symbol: str, interval: str, limit: int) -> Optional[np.ndarray]:
    try:
        inst_id = symbol.replace("USDT", "-USDT")
        bar_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H", "1d": "1D"}
        bar = bar_map.get(interval, "4H")
        resp = requests.get(
            "https://www.okx.com/api/v5/market/candles",
            params={"instId": inst_id, "bar": bar, "limit": str(min(limit, 300))},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data or len(data) < 50:
            return None
        data.reverse()
        return np.array([[float(d[0]), float(d[1]), float(d[2]), float(d[3]), float(d[4]), float(d[5])] for d in data])
    except Exception:
        return None


def _fetch_bybit(symbol: str, interval: str, limit: int) -> Optional[np.ndarray]:
    try:
        interval_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D"}
        bybit_interval = interval_map.get(interval, "240")
        resp = requests.get(
            "https://api.bybit.com/v5/market/kline",
            params={"category": "spot", "symbol": symbol, "interval": bybit_interval, "limit": str(min(limit, 200))},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("result", {}).get("list", [])
        if not data or len(data) < 50:
            return None
        data.reverse()
        return np.array([[float(d[0]), float(d[1]), float(d[2]), float(d[3]), float(d[4]), float(d[5])] for d in data])
    except Exception:
        return None


def fetch_fear_greed() -> int:
    """Fetch current Fear & Greed Index (0-100) with retry. Returns 50 on failure."""
    import time as _time
    for attempt in range(3):
        try:
            resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
            resp.raise_for_status()
            return int(resp.json()["data"][0]["value"])
        except Exception:
            if attempt < 2:
                _time.sleep(2 * (attempt + 1))
    return 50


# ---------------------------------------------------------------------------
# Technical Indicators (inline, no external deps beyond numpy)
# ---------------------------------------------------------------------------
def calc_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range. Returns array same length as input (NaN-padded)."""
    n = len(closes)
    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
    atr = np.full(n, np.nan)
    if n >= period:
        atr[period - 1] = np.mean(tr[:period])
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def calc_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Wilder RSI. Returns array same length as input (NaN-padded)."""
    n = len(closes)
    rsi = np.full(n, np.nan)
    if n < period + 1:
        return rsi
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - 100.0 / (1.0 + rs)
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100.0 - 100.0 / (1.0 + rs)
    return rsi


def calc_sma(values: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average. NaN-padded."""
    n = len(values)
    out = np.full(n, np.nan)
    if n < period:
        return out
    # cumsum trick for speed
    cs = np.nancumsum(values)
    out[period - 1] = cs[period - 1] / period
    for i in range(period, n):
        out[i] = (cs[i] - cs[i - period]) / period
    return out


# ---------------------------------------------------------------------------
# S/R Detection (self-contained Williams fractal + volume profile + round numbers)
# ---------------------------------------------------------------------------
def detect_sr_levels(
    ohlcv: np.ndarray,
    current_price: Optional[float] = None,
    fractal_window: int = 5,
    cluster_tolerance: float = 0.003,
    min_touches: int = 2,
    n_volume_bins: int = 50,
    volume_lookback: int = 100,
    max_levels: int = 15,
) -> list[SRLevel]:
    """
    Detect S/R levels from OHLCV numpy array.
    ohlcv columns: [timestamp_ms, open, high, low, close, volume]
    """
    if ohlcv is None or len(ohlcv) < 50:
        return []

    highs = ohlcv[:, 2]
    lows = ohlcv[:, 3]
    closes = ohlcv[:, 4]
    volumes = ohlcv[:, 5]

    if current_price is None:
        current_price = float(closes[-1])

    levels: list[SRLevel] = []

    # 1. Williams fractal pivots
    levels.extend(_fractal_sr(highs, lows, fractal_window, cluster_tolerance, min_touches))

    # 2. Volume profile (POC, VAH, VAL)
    levels.extend(_volume_profile_sr(highs, lows, volumes, n_volume_bins, volume_lookback))

    # 3. Round number levels
    levels.extend(_round_number_sr(current_price))

    # Label support vs resistance relative to current price
    for lv in levels:
        lv.level_type = "support" if lv.price < current_price else "resistance"

    # Merge nearby
    levels = _merge_nearby(levels, cluster_tolerance)

    # Sort by strength desc
    levels.sort(key=lambda x: x.strength, reverse=True)

    return levels[:max_levels]


def _fractal_sr(
    highs: np.ndarray,
    lows: np.ndarray,
    window: int = 5,
    tolerance: float = 0.003,
    min_touches: int = 2,
) -> list[SRLevel]:
    """Williams fractal pivots clustered into S/R levels."""
    n = len(highs)
    half = window // 2
    pivots = []

    for i in range(half, n - half):
        is_high = True
        is_low = True
        for j in range(i - half, i + half + 1):
            if j == i:
                continue
            if highs[j] >= highs[i]:
                is_high = False
            if lows[j] <= lows[i]:
                is_low = False
        if is_high:
            pivots.append((i, float(highs[i]), "high"))
        if is_low:
            pivots.append((i, float(lows[i]), "low"))

    if not pivots:
        return []

    pivots.sort(key=lambda x: x[1])
    clusters: list[SRLevel] = []
    used: set[int] = set()

    for idx, (bar_i, price, _) in enumerate(pivots):
        if idx in used:
            continue
        cluster = [(bar_i, price)]
        used.add(idx)
        for jdx, (bar_j, price2, _) in enumerate(pivots):
            if jdx in used:
                continue
            if abs(price2 - price) / price <= tolerance:
                cluster.append((bar_j, price2))
                used.add(jdx)

        if len(cluster) >= min_touches:
            avg_price = np.mean([p for _, p in cluster])
            max_bar = max(c[0] for c in cluster)
            recency = max_bar / n if n > 0 else 0.5
            strength = len(cluster) * (1.0 + 0.5 * recency)
            clusters.append(SRLevel(
                price=round(float(avg_price), 2),
                strength=round(strength, 3),
                touches=len(cluster),
                level_type="support",
                source="fractal",
                recency=round(recency, 3),
            ))

    return clusters


def _volume_profile_sr(
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
    n_bins: int = 50,
    lookback: int = 100,
) -> list[SRLevel]:
    """Volume profile -> POC, VAH, VAL as S/R levels."""
    data_h = highs[-lookback:]
    data_l = lows[-lookback:]
    data_v = volumes[-lookback:]

    if len(data_h) < 20:
        return []

    price_min = float(data_l.min())
    price_max = float(data_h.max())
    if price_max <= price_min:
        return []

    bin_edges = np.linspace(price_min, price_max, n_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    profile = np.zeros(n_bins)

    for i in range(len(data_h)):
        bar_low = data_l[i]
        bar_high = data_h[i]
        bar_vol = data_v[i]
        if bar_high <= bar_low or bar_vol <= 0:
            continue
        bar_range = bar_high - bar_low
        for k in range(n_bins):
            overlap = max(0.0, min(bar_high, bin_edges[k + 1]) - max(bar_low, bin_edges[k]))
            if bar_range > 0:
                profile[k] += bar_vol * (overlap / bar_range)

    if profile.sum() == 0:
        return []

    # POC (Point of Control)
    poc_idx = int(np.argmax(profile))
    poc_price = float(bin_centers[poc_idx])

    # Value Area (70% of volume)
    total_vol = profile.sum()
    target = 0.70 * total_vol
    accumulated = profile[poc_idx]
    lo_idx = poc_idx
    hi_idx = poc_idx

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

    return [
        SRLevel(price=round(poc_price, 2), strength=5.0, touches=0,
                level_type="support", source="volume_profile", recency=0.9),
        SRLevel(price=round(val_price, 2), strength=3.5, touches=0,
                level_type="support", source="volume_profile", recency=0.9),
        SRLevel(price=round(vah_price, 2), strength=3.5, touches=0,
                level_type="resistance", source="volume_profile", recency=0.9),
    ]


def _round_number_sr(price: float) -> list[SRLevel]:
    """Psychological round-number levels near current price."""
    if price <= 0:
        return []

    magnitude = 10 ** int(math.log10(price))
    step = magnitude / 10

    levels: list[SRLevel] = []
    base = round(price / step) * step
    for offset in [-3, -2, -1, 0, 1, 2, 3]:
        level_price = base + offset * step
        if level_price <= 0:
            continue
        distance = abs(level_price - price) / price
        if distance < 0.10:
            strength = max(0.5, 2.0 - distance * 20)
            levels.append(SRLevel(
                price=round(level_price, 2),
                strength=round(strength, 3),
                touches=0,
                level_type="support",
                source="round_number",
                recency=1.0,
            ))
    return levels


def _merge_nearby(levels: list[SRLevel], tolerance: float = 0.003) -> list[SRLevel]:
    """Merge S/R levels from different sources that are very close."""
    if not levels:
        return []

    levels.sort(key=lambda x: x.price)
    merged = [levels[0]]

    for level in levels[1:]:
        prev = merged[-1]
        if prev.price > 0 and abs(level.price - prev.price) / prev.price <= tolerance:
            merged[-1] = SRLevel(
                price=round((prev.price + level.price) / 2, 2),
                strength=round(prev.strength + level.strength, 3),
                touches=prev.touches + level.touches,
                level_type=prev.level_type,
                source=f"{prev.source}+{level.source}" if level.source not in prev.source else prev.source,
                recency=max(prev.recency, level.recency),
            )
        else:
            merged.append(level)

    return merged


# ---------------------------------------------------------------------------
# Breakout Detection
# ---------------------------------------------------------------------------
def check_breakout(
    ohlcv: np.ndarray,
    sr_levels: list[SRLevel],
    fear_greed: int,
) -> list[dict]:
    """
    Check for breakout signals against each S/R level.
    Returns list of signal dicts (may be empty).
    """
    if ohlcv is None or len(ohlcv) < 30 or not sr_levels:
        return []

    closes = ohlcv[:, 4]
    highs = ohlcv[:, 2]
    lows = ohlcv[:, 3]
    volumes = ohlcv[:, 5]

    current_close = float(closes[-1])
    prev_close = float(closes[-2])

    # Volume ratio: current vs 20-bar avg
    vol_window = min(20, len(volumes) - 1)
    avg_vol = float(np.mean(volumes[-vol_window - 1:-1]))
    current_vol = float(volumes[-1])
    volume_ratio = current_vol / avg_vol if avg_vol > 0 else 0.0

    # ATR(14)
    atr_arr = calc_atr(highs, lows, closes, period=14)
    current_atr = float(atr_arr[-1]) if not np.isnan(atr_arr[-1]) else 0.0

    # ATR expansion: ATR(14) vs SMA(20) of ATR(14)
    atr_sma = calc_sma(atr_arr, 20)
    atr_sma_val = float(atr_sma[-1]) if not np.isnan(atr_sma[-1]) else current_atr
    atr_ratio = current_atr / atr_sma_val if atr_sma_val > 0 else 1.0

    # RSI(14)
    rsi_arr = calc_rsi(closes, period=14)
    current_rsi = float(rsi_arr[-1]) if not np.isnan(rsi_arr[-1]) else 50.0

    signals = []

    for level in sr_levels:
        # --- BUY breakout: close above resistance, prev was below ---
        if level.level_type == "resistance":
            if (
                current_close > level.price
                and prev_close <= level.price
                and volume_ratio >= VOLUME_RATIO_THRESHOLD
                and atr_ratio >= ATR_EXPANSION_RATIO
                and RSI_BUY_RANGE[0] <= current_rsi <= RSI_BUY_RANGE[1]
                and fear_greed >= FEAR_GREED_BUY_MIN
            ):
                # Compute TP/SL
                tp, sl, rr = _compute_tp_sl(
                    entry=current_close,
                    signal_type="BUY",
                    broken_level=level.price,
                    sr_levels=sr_levels,
                    atr=current_atr,
                )
                if rr >= MIN_RR:
                    confidence = _compute_confidence(
                        volume_ratio, atr_ratio, current_rsi, level.strength, fear_greed, "BUY"
                    )
                    signals.append(_build_signal(
                        symbol="BTCUSDT",
                        signal_type="BUY",
                        entry=current_close,
                        tp=tp,
                        sl=sl,
                        rr=rr,
                        confidence=confidence,
                        level=level,
                        volume_ratio=volume_ratio,
                        atr_ratio=atr_ratio,
                        rsi=current_rsi,
                        fear_greed=fear_greed,
                    ))

        # --- SELL breakout: close below support, prev was above ---
        elif level.level_type == "support":
            if (
                current_close < level.price
                and prev_close >= level.price
                and volume_ratio >= VOLUME_RATIO_THRESHOLD
                and atr_ratio >= ATR_EXPANSION_RATIO
                and RSI_SELL_RANGE[0] <= current_rsi <= RSI_SELL_RANGE[1]
                and fear_greed <= FEAR_GREED_SELL_MAX
            ):
                tp, sl, rr = _compute_tp_sl(
                    entry=current_close,
                    signal_type="SELL",
                    broken_level=level.price,
                    sr_levels=sr_levels,
                    atr=current_atr,
                )
                if rr >= MIN_RR:
                    confidence = _compute_confidence(
                        volume_ratio, atr_ratio, current_rsi, level.strength, fear_greed, "SELL"
                    )
                    signals.append(_build_signal(
                        symbol="BTCUSDT",
                        signal_type="SELL",
                        entry=current_close,
                        tp=tp,
                        sl=sl,
                        rr=rr,
                        confidence=confidence,
                        level=level,
                        volume_ratio=volume_ratio,
                        atr_ratio=atr_ratio,
                        rsi=current_rsi,
                        fear_greed=fear_greed,
                    ))

    return signals


def _compute_tp_sl(
    entry: float,
    signal_type: str,
    broken_level: float,
    sr_levels: list[SRLevel],
    atr: float,
) -> tuple[float, float, float]:
    """
    Compute TP, SL, and R:R ratio for a breakout signal.

    BUY: TP = next resistance above entry (or +3xATR), SL = broken level - 1xATR
    SELL: TP = next support below entry (or -3xATR), SL = broken level + 1xATR
    """
    if signal_type == "BUY":
        # TP: next resistance above entry
        resistances_above = sorted(
            [lv for lv in sr_levels if lv.level_type == "resistance" and lv.price > entry],
            key=lambda x: x.price,
        )
        tp = resistances_above[0].price if resistances_above else entry + 3.0 * atr

        # SL: broken resistance (now support) minus 1x ATR buffer
        sl = broken_level - 1.0 * atr

        risk = entry - sl
        reward = tp - entry
    else:
        # TP: next support below entry
        supports_below = sorted(
            [lv for lv in sr_levels if lv.level_type == "support" and lv.price < entry],
            key=lambda x: x.price,
            reverse=True,
        )
        tp = supports_below[0].price if supports_below else entry - 3.0 * atr

        # SL: broken support (now resistance) plus 1x ATR buffer
        sl = broken_level + 1.0 * atr

        risk = sl - entry
        reward = entry - tp

    rr = reward / risk if risk > 0 else 0.0
    return round(tp, 2), round(sl, 2), round(rr, 2)


def _compute_confidence(
    volume_ratio: float,
    atr_ratio: float,
    rsi: float,
    level_strength: float,
    fear_greed: int,
    signal_type: str,
) -> float:
    """Compute a 0-1 confidence score based on breakout quality."""
    score = 0.0
    # Volume strength (0-0.3)
    score += min(0.3, (volume_ratio - 1.5) * 0.1)
    # ATR expansion (0-0.2)
    score += min(0.2, (atr_ratio - 1.0) * 0.2)
    # S/R level strength (0-0.25)
    score += min(0.25, level_strength * 0.05)
    # RSI favorability (0-0.15)
    if signal_type == "BUY":
        rsi_score = 0.15 if 45 <= rsi <= 65 else 0.08
    else:
        rsi_score = 0.15 if 35 <= rsi <= 55 else 0.08
    score += rsi_score
    # Fear & Greed alignment (0-0.1)
    if signal_type == "BUY" and fear_greed >= 30:
        score += 0.1
    elif signal_type == "SELL" and fear_greed <= 70:
        score += 0.1

    return round(max(0.1, min(1.0, score)), 2)


def _build_signal(
    symbol: str,
    signal_type: str,
    entry: float,
    tp: float,
    sl: float,
    rr: float,
    confidence: float,
    level: SRLevel,
    volume_ratio: float,
    atr_ratio: float,
    rsi: float,
    fear_greed: int,
) -> dict:
    """Build a standardized signal dict."""
    now = datetime.now(timezone.utc)
    now_est = now.astimezone(EST)

    direction = "above resistance" if signal_type == "BUY" else "below support"
    reason = (
        f"BTC broke {direction} at ${level.price:,.0f} "
        f"(strength={level.strength:.1f}, touches={level.touches}) "
        f"with {volume_ratio:.1f}x volume, ATR expanding {atr_ratio:.2f}x, "
        f"RSI={rsi:.1f}, F&G={fear_greed}"
    )

    return {
        "symbol": symbol,
        "signal_type": signal_type,
        "entry_price": entry,
        "take_profit": tp,
        "stop_loss": sl,
        "risk_reward": rr,
        "confidence": confidence,
        "strategy": "sr_breakout",
        "breakout_level": level.price,
        "breakout_level_type": level.level_type,
        "breakout_level_strength": level.strength,
        "volume_ratio": round(volume_ratio, 2),
        "atr_ratio": round(atr_ratio, 2),
        "rsi_value": round(rsi, 1),
        "fear_greed": fear_greed,
        "timestamp": now.isoformat(),
        "timestamp_est": now_est.strftime("%Y-%m-%d %H:%M EST"),
        "system": SYSTEM_ID,
        "pick_reason": reason,
        # Tracking fields (populated during position management)
        "hwm": entry,
        "trailing_active": False,
    }


# ---------------------------------------------------------------------------
# Position Tracking & Management
# ---------------------------------------------------------------------------
def load_json(filepath: str, default=None):
    """Load JSON file, return default on any error."""
    if default is None:
        default = []
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Failed to load {filepath}: {e}")
    return default


def save_json(filepath: str, data):
    """Save data to JSON file, creating directories as needed."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def manage_positions(active_picks: list[dict], closed_picks: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Check TP/SL/trailing stop for all active picks.
    Returns updated (active, closed) lists.
    """
    if not active_picks:
        return active_picks, closed_picks

    # Fetch current BTC price
    current_price = _fetch_current_price("BTCUSDT")
    if current_price <= 0:
        print("  [WARN] Could not fetch current price, skipping position management")
        return active_picks, closed_picks

    still_active = []
    newly_closed = []

    for pick in active_picks:
        entry = pick["entry_price"]
        tp = pick["take_profit"]
        sl = pick["stop_loss"]
        sig_type = pick["signal_type"]
        hwm = pick.get("hwm", entry)
        trailing_active = pick.get("trailing_active", False)

        # Update HWM
        if sig_type == "BUY":
            hwm = max(hwm, current_price)
        else:
            hwm = min(hwm, current_price)
        pick["hwm"] = hwm

        # Max-hold expiry — auto-close stale picks
        opened_at = pick.get("timestamp")
        if opened_at:
            try:
                age_hours = (datetime.now(timezone.utc) - datetime.fromisoformat(opened_at)).total_seconds() / 3600
                if age_hours > MAX_HOLD_HOURS:
                    if sig_type == "BUY":
                        raw_pnl_pct = (current_price - entry) / entry
                    else:
                        raw_pnl_pct = (entry - current_price) / entry
                    net_pnl_pct = raw_pnl_pct - ROUND_TRIP_COST_PCT

                    pick["exit_price"] = current_price
                    pick["exit_reason"] = f"Expired ({int(age_hours)}h)"
                    pick["exit_timestamp"] = datetime.now(timezone.utc).isoformat()
                    pick["exit_timestamp_est"] = datetime.now(timezone.utc).astimezone(EST).strftime("%Y-%m-%d %H:%M EST")
                    pick["pnl_pct"] = round(net_pnl_pct * 100, 2)
                    pick["pnl_net"] = round(net_pnl_pct * 100, 2)
                    pick["result"] = "WIN" if net_pnl_pct > 0 else "LOSS"

                    newly_closed.append(pick)
                    print(f"  [EXPIRED] {pick['symbol']} {sig_type} after {int(age_hours)}h | "
                          f"PnL: {pick['pnl_pct']:+.2f}% | Entry: ${entry:,.0f} Exit: ${current_price:,.0f}")
                    continue
            except (ValueError, TypeError):
                pass

        # Check trailing stop activation
        if sig_type == "BUY":
            pnl_pct = (current_price - entry) / entry
            if pnl_pct >= TRAILING_ACTIVATION_PCT:
                trailing_active = True
                pick["trailing_active"] = True
                trailing_sl = hwm * (1 - TRAILING_DISTANCE_PCT)
                # Use the higher of original SL and trailing SL
                effective_sl = max(sl, trailing_sl)
            else:
                effective_sl = sl
        else:
            pnl_pct = (entry - current_price) / entry
            if pnl_pct >= TRAILING_ACTIVATION_PCT:
                trailing_active = True
                pick["trailing_active"] = True
                trailing_sl = hwm * (1 + TRAILING_DISTANCE_PCT)
                effective_sl = min(sl, trailing_sl)
            else:
                effective_sl = sl

        # Check exit conditions
        closed = False
        exit_reason = ""

        if sig_type == "BUY":
            if current_price >= tp:
                exit_reason = "TP hit"
                closed = True
            elif current_price <= effective_sl:
                exit_reason = "Trailing SL hit" if trailing_active else "SL hit"
                closed = True
        else:  # SELL
            if current_price <= tp:
                exit_reason = "TP hit"
                closed = True
            elif current_price >= effective_sl:
                exit_reason = "Trailing SL hit" if trailing_active else "SL hit"
                closed = True

        if closed:
            # Calculate PnL
            if sig_type == "BUY":
                raw_pnl_pct = (current_price - entry) / entry
            else:
                raw_pnl_pct = (entry - current_price) / entry
            net_pnl_pct = raw_pnl_pct - ROUND_TRIP_COST_PCT

            pick["exit_price"] = current_price
            pick["exit_reason"] = exit_reason
            pick["exit_timestamp"] = datetime.now(timezone.utc).isoformat()
            pick["exit_timestamp_est"] = datetime.now(timezone.utc).astimezone(EST).strftime("%Y-%m-%d %H:%M EST")
            pick["pnl_pct"] = round(net_pnl_pct * 100, 2)
            pick["pnl_net"] = round(net_pnl_pct * 100, 2)
            pick["result"] = "WIN" if net_pnl_pct > 0 else "LOSS"

            newly_closed.append(pick)
            print(f"  [CLOSE] {pick['symbol']} {sig_type} -> {exit_reason} | "
                  f"PnL: {pick['pnl_pct']:+.2f}% | Entry: ${entry:,.0f} Exit: ${current_price:,.0f}")
        else:
            still_active.append(pick)

    closed_picks.extend(newly_closed)
    return still_active, closed_picks


def _fetch_current_price(symbol: str) -> float:
    """Fetch current ticker price from Binance."""
    try:
        resp = requests.get(
            f"{BINANCE_BASE}/api/v3/ticker/price",
            params={"symbol": symbol},
            timeout=5,
        )
        resp.raise_for_status()
        return float(resp.json()["price"])
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Stats & Equity Curve
# ---------------------------------------------------------------------------
def compute_stats(closed_picks: list[dict], equity_curve: list[dict]) -> dict:
    """Compute trading performance statistics."""
    if not closed_picks:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "avg_win_pct": 0.0,
            "avg_loss_pct": 0.0,
            "profit_factor": 0.0,
            "expectancy_pct": 0.0,
            "sharpe": 0.0,
            "max_drawdown_pct": 0.0,
            "total_pnl_pct": 0.0,
        }

    wins = [p for p in closed_picks if p.get("result") == "WIN"]
    losses = [p for p in closed_picks if p.get("result") == "LOSS"]

    win_pnls = [float(p.get("pnl_pct", 0) or 0) for p in wins]
    loss_pnls = [float(p.get("pnl_pct", 0) or 0) for p in losses]

    avg_win = np.mean(win_pnls) if win_pnls else 0.0
    avg_loss = abs(np.mean(loss_pnls)) if loss_pnls else 0.0

    total_wins = sum(win_pnls)
    total_losses = abs(sum(loss_pnls))
    profit_factor = total_wins / total_losses if total_losses > 0 else float("inf") if total_wins > 0 else 0.0

    all_pnls = [float(p.get("pnl_pct", 0) or 0) for p in closed_picks]
    expectancy = np.mean(all_pnls) if all_pnls else 0.0

    # Sharpe (annualized, assuming ~6 trades per day on 4h tf is wrong; use per-trade)
    # For low-frequency: annualize by sqrt(trades_per_year)
    trades_per_year = max(len(closed_picks), 1)  # rough estimate
    std_pnl = np.std(all_pnls) if len(all_pnls) > 1 else 1.0
    sharpe = (expectancy / std_pnl) * math.sqrt(min(trades_per_year, 300)) if std_pnl > 0 else 0.0

    # Max drawdown from equity curve
    max_dd = 0.0
    if equity_curve:
        equities = [e.get("equity", STARTING_EQUITY) for e in equity_curve]
        peak = equities[0]
        for eq in equities:
            peak = max(peak, eq)
            dd = (peak - eq) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

    return {
        "trades": len(closed_picks),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(closed_picks), 3) if closed_picks else 0.0,
        "avg_win_pct": round(float(avg_win), 2),
        "avg_loss_pct": round(float(avg_loss), 2),
        "profit_factor": round(float(profit_factor), 2) if profit_factor != float("inf") else 999.0,
        "expectancy_pct": round(float(expectancy), 2),
        "sharpe": round(float(sharpe), 2),
        "max_drawdown_pct": round(float(max_dd * 100), 2),
        "total_pnl_pct": round(float(sum(all_pnls)), 2),
    }


def update_equity_curve(equity_curve: list[dict], closed_picks: list[dict]) -> list[dict]:
    """
    Rebuild equity curve from closed picks.
    Each entry: {"timestamp": ISO, "equity": float, "trade": symbol}
    """
    equity = STARTING_EQUITY
    curve = [{"timestamp": "start", "equity": equity, "trade": "initial"}]

    # Sort closed by exit timestamp
    sorted_closed = sorted(closed_picks, key=lambda p: p.get("exit_timestamp", ""))

    for pick in sorted_closed:
        pnl_pct = pick.get("pnl_pct", 0) / 100.0
        # Position size is 2% equity risk
        risk_amount = equity * EQUITY_RISK_PCT
        rr = pick.get("risk_reward", 1.5)
        if pick.get("result") == "WIN":
            pnl_dollar = risk_amount * rr * (1 - ROUND_TRIP_COST_PCT)
        else:
            pnl_dollar = -risk_amount * (1 + ROUND_TRIP_COST_PCT)
        equity += pnl_dollar
        equity = max(equity, 0)

        curve.append({
            "timestamp": pick.get("exit_timestamp", ""),
            "equity": round(equity, 2),
            "trade": pick.get("symbol", ""),
        })

    return curve


# ---------------------------------------------------------------------------
# Dashboard JSON Builder
# ---------------------------------------------------------------------------
def build_dashboard(
    active_picks: list[dict],
    closed_picks: list[dict],
    equity_curve: list[dict],
    sr_levels: list[SRLevel],
    market_context: dict,
) -> dict:
    """Build the full dashboard JSON payload."""
    now = datetime.now(timezone.utc)
    now_est = now.astimezone(EST)

    stats = compute_stats(closed_picks, equity_curve)

    # Recent closed (last 20)
    recent_closed = sorted(
        closed_picks, key=lambda p: p.get("exit_timestamp", ""), reverse=True
    )[:20]

    # Clean picks for JSON (remove internal tracking fields)
    def clean_pick(p: dict) -> dict:
        exclude = {"hwm", "trailing_active"}
        return {k: v for k, v in p.items() if k not in exclude}

    # S/R levels as dicts
    sr_dicts = [
        {
            "price": lv.price,
            "type": lv.level_type,
            "strength": lv.strength,
            "source": lv.source,
            "touches": lv.touches,
        }
        for lv in sr_levels
    ]

    return {
        "system": SYSTEM_NAME,
        "system_id": SYSTEM_ID,
        "version": VERSION,
        "updated": now.isoformat(),
        "updated_est": now_est.strftime("%Y-%m-%d %H:%M EST"),
        "timeframe": TIMEFRAME,
        "pairs": PAIRS,
        "scan_frequency": SCAN_FREQUENCY,
        "active_picks": [clean_pick(p) for p in active_picks],
        "stats": stats,
        "equity_curve": equity_curve,
        "total_closed": len(closed_picks),
        "recent_closed": [clean_pick(p) for p in recent_closed],
        "sr_levels": sr_dicts,
        "market_context": market_context,
    }


# ---------------------------------------------------------------------------
# Duplicate Detection
# ---------------------------------------------------------------------------
def is_duplicate_signal(signal: dict, active_picks: list[dict]) -> bool:
    """Prevent duplicate signals for the same symbol + direction."""
    for pick in active_picks:
        if pick["symbol"] == signal["symbol"] and pick["signal_type"] == signal["signal_type"]:
            return True
    return False


# ---------------------------------------------------------------------------
# Main Scanner
# ---------------------------------------------------------------------------
def scan(dry_run: bool = False):
    """Main scan cycle."""
    now = datetime.now(timezone.utc)
    print(f"\n{'='*60}")
    print(f"[Approach A] S/R Breakout Scanner v{VERSION}")
    print(f"[Approach A] Scan started at {now.isoformat()}")
    print(f"[Approach A] Timeframe: {TIMEFRAME} | Pairs: {', '.join(PAIRS)}")
    if dry_run:
        print(f"[Approach A] ** DRY RUN -- signals will NOT be persisted **")
    print(f"{'='*60}\n")

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Load existing state
    active_file = os.path.join(DATA_DIR, "active_picks.json")
    closed_file = os.path.join(DATA_DIR, "closed_picks.json")
    equity_file = os.path.join(DATA_DIR, "equity_curve.json")

    active_picks = load_json(active_file, [])
    closed_picks = load_json(closed_file, [])
    equity_curve = load_json(equity_file, [])

    print(f"[Approach A] Loaded state: {len(active_picks)} active, {len(closed_picks)} closed")

    # --- Step 1: Manage existing positions ---
    print(f"\n--- Position Management ---")
    active_picks, closed_picks = manage_positions(active_picks, closed_picks)
    print(f"  Active after management: {len(active_picks)}")

    # --- Step 2: Fetch market data ---
    print(f"\n--- Fetching Market Data ---")
    btc_data = fetch_klines("BTCUSDT", TIMEFRAME, 500)
    if btc_data is None:
        print("  [FATAL] Could not fetch BTCUSDT data. Aborting scan.")
        # Still save state and write dashboard with what we have
        _finalize(active_picks, closed_picks, equity_curve, [], {}, dry_run)
        return

    current_price = float(btc_data[-1, 4])
    print(f"  BTCUSDT current price: ${current_price:,.2f}")
    print(f"  Candles loaded: {len(btc_data)}")

    # Fetch ETH for correlation context (optional, non-blocking)
    eth_data = fetch_klines("ETHUSDT", TIMEFRAME, 100)
    if eth_data is not None:
        eth_price = float(eth_data[-1, 4])
        print(f"  ETHUSDT current price: ${eth_price:,.2f}")
    else:
        print(f"  ETHUSDT: fetch failed (non-critical)")

    # Fetch Fear & Greed
    fear_greed = fetch_fear_greed()
    print(f"  Fear & Greed Index: {fear_greed}")

    # --- Step 3: Detect S/R levels ---
    print(f"\n--- S/R Level Detection ---")
    sr_levels = detect_sr_levels(btc_data, current_price)
    print(f"  Found {len(sr_levels)} S/R levels:")

    supports = [lv for lv in sr_levels if lv.level_type == "support"]
    resistances = [lv for lv in sr_levels if lv.level_type == "resistance"]

    for lv in sorted(resistances, key=lambda x: x.price):
        print(f"    R  ${lv.price:>10,.2f}  str={lv.strength:<6.2f}  touches={lv.touches}  src={lv.source}")
    print(f"    -- ${current_price:>10,.2f}  << CURRENT PRICE >>")
    for lv in sorted(supports, key=lambda x: x.price, reverse=True):
        print(f"    S  ${lv.price:>10,.2f}  str={lv.strength:<6.2f}  touches={lv.touches}  src={lv.source}")

    # --- Step 4: Compute indicators for context ---
    closes = btc_data[:, 4]
    highs = btc_data[:, 2]
    lows = btc_data[:, 3]
    volumes = btc_data[:, 5]

    atr_arr = calc_atr(highs, lows, closes, 14)
    current_atr = float(atr_arr[-1]) if not np.isnan(atr_arr[-1]) else 0.0
    atr_sma = calc_sma(atr_arr, 20)
    atr_sma_val = float(atr_sma[-1]) if not np.isnan(atr_sma[-1]) else current_atr
    atr_ratio = current_atr / atr_sma_val if atr_sma_val > 0 else 1.0

    vol_avg = float(np.mean(volumes[-21:-1])) if len(volumes) > 21 else float(np.mean(volumes))
    vol_ratio = float(volumes[-1]) / vol_avg if vol_avg > 0 else 1.0

    rsi_arr = calc_rsi(closes, 14)
    current_rsi = float(rsi_arr[-1]) if not np.isnan(rsi_arr[-1]) else 50.0

    market_context = {
        "fear_greed": fear_greed,
        "btc_price": round(current_price, 2),
        "btc_atr": round(current_atr, 2),
        "btc_atr_ratio": round(atr_ratio, 3),
        "volume_ratio": round(vol_ratio, 2),
        "rsi_14": round(current_rsi, 1),
    }

    print(f"\n--- Market Context ---")
    print(f"  ATR(14): ${current_atr:,.2f} | ATR ratio: {atr_ratio:.3f}x (need >={ATR_EXPANSION_RATIO}x)")
    print(f"  Volume ratio: {vol_ratio:.2f}x (need >={VOLUME_RATIO_THRESHOLD}x)")
    print(f"  RSI(14): {current_rsi:.1f}")
    print(f"  Fear & Greed: {fear_greed}")

    # --- Step 5: Check for breakout signals ---
    print(f"\n--- Breakout Detection ---")
    signals = check_breakout(btc_data, sr_levels, fear_greed)

    if not signals:
        print(f"  No breakout signals detected.")
        conditions = []
        if vol_ratio < VOLUME_RATIO_THRESHOLD:
            conditions.append(f"volume {vol_ratio:.1f}x < {VOLUME_RATIO_THRESHOLD}x threshold")
        if atr_ratio < ATR_EXPANSION_RATIO:
            conditions.append(f"ATR ratio {atr_ratio:.2f}x < {ATR_EXPANSION_RATIO}x threshold")
        if not (RSI_BUY_RANGE[0] <= current_rsi <= RSI_BUY_RANGE[1]):
            conditions.append(f"RSI {current_rsi:.1f} outside buy range {RSI_BUY_RANGE}")
        if conditions:
            print(f"  Reasons: {'; '.join(conditions)}")
    else:
        print(f"  Found {len(signals)} potential breakout signal(s)!")

    # --- Step 6: Add new signals (if not duplicates) ---
    new_count = 0
    for sig in signals:
        if is_duplicate_signal(sig, active_picks):
            print(f"  [SKIP] Duplicate: {sig['symbol']} {sig['signal_type']} already active")
            continue

        print(f"\n  [SIGNAL] {sig['signal_type']} {sig['symbol']}")
        print(f"    Entry:  ${sig['entry_price']:,.2f}")
        print(f"    TP:     ${sig['take_profit']:,.2f}")
        print(f"    SL:     ${sig['stop_loss']:,.2f}")
        print(f"    R:R:    {sig['risk_reward']:.2f}")
        print(f"    Conf:   {sig['confidence']:.0%}")
        print(f"    Level:  ${sig['breakout_level']:,.2f} ({sig['breakout_level_type']}, "
              f"str={sig['breakout_level_strength']:.1f})")
        print(f"    Reason: {sig['pick_reason']}")

        if not dry_run:
            active_picks.append(sig)
            new_count += 1

    if new_count > 0:
        print(f"\n  Added {new_count} new signal(s) to active picks")

    # --- Finalize ---
    _finalize(active_picks, closed_picks, equity_curve, sr_levels, market_context, dry_run)


def _finalize(
    active_picks: list[dict],
    closed_picks: list[dict],
    equity_curve: list[dict],
    sr_levels: list[SRLevel],
    market_context: dict,
    dry_run: bool,
):
    """Save state and write dashboard JSON."""
    # Update equity curve
    equity_curve = update_equity_curve(equity_curve, closed_picks)

    if not dry_run:
        active_file = os.path.join(DATA_DIR, "active_picks.json")
        closed_file = os.path.join(DATA_DIR, "closed_picks.json")
        equity_file = os.path.join(DATA_DIR, "equity_curve.json")
        dashboard_file = os.path.join(DATA_DIR, "dashboard.json")

        try:
            from alpha_engine.feed_hygiene import sanitize_active_picks
        except ImportError:
            sanitize_active_picks = lambda picks, label="": picks
        active_picks = sanitize_active_picks(active_picks, "breakout_arena_a")

        save_json(active_file, active_picks)
        save_json(closed_file, closed_picks)
        save_json(equity_file, equity_curve)

        # Build and save dashboard
        dashboard = build_dashboard(active_picks, closed_picks, equity_curve, sr_levels, market_context)
        save_json(dashboard_file, dashboard)

        print(f"\n--- State Saved ---")
        print(f"  Active picks: {len(active_picks)}")
        print(f"  Total closed: {len(closed_picks)}")
        print(f"  Dashboard: {dashboard_file}")
    else:
        print(f"\n--- Dry Run Complete (nothing saved) ---")
        print(f"  Would have {len(active_picks)} active picks")

    stats = compute_stats(closed_picks, equity_curve)
    if stats["trades"] > 0:
        print(f"\n--- Performance ---")
        print(f"  Trades: {stats['trades']} | W/L: {stats['wins']}/{stats['losses']} | "
              f"WR: {stats['win_rate']:.1%}")
        print(f"  PF: {stats['profit_factor']:.2f} | Sharpe: {stats['sharpe']:.2f} | "
              f"Max DD: {stats['max_drawdown_pct']:.1f}%")
        print(f"  Total PnL: {stats['total_pnl_pct']:+.2f}% | "
              f"Expectancy: {stats['expectancy_pct']:+.2f}%/trade")

    print(f"\n[Approach A] Scan complete.\n")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Approach A: Pure S/R Breakout Scanner")
    parser.add_argument("--dry-run", action="store_true", help="Show signals without persisting")
    args = parser.parse_args()

    scan(dry_run=args.dry_run)
