#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Multi-Signal Confluence Strategy
=================================================
4-layer confluence system requiring 3+ independent technical signals to agree
before entering a trade. Hypothesis: requiring multiple independent signals
produces much higher WR than any single strategy alone.

Layer 1: Mean Reversion (RSI oversold/overbought + Bollinger Band extremes)
Layer 2: Volume Accumulation (OBV trend + volume spike > 1.5x average)
Layer 3: Momentum / EMA Stack (EMA 9/21/50 alignment + ATR expansion)
Layer 4: MACD Confirmation (histogram direction + momentum)

Entry Rules:
  - 3 of 4 layers agree = standard entry (confidence 0.72)
  - 4 of 4 layers agree = high-conviction entry (confidence 0.85)
  - 2 or fewer = no trade

A/B Test Variants:
  - CONFLUENCE_3OF4: 3+ layers required (more trades, slightly lower WR)
  - CONFLUENCE_4OF4: all 4 required (fewer trades, higher WR expected)
  - CONFLUENCE_WEIGHTED: weighted sum > 0.7 (historical IC weights)

Parameters:
  - Timeframe: 4H candles (100 bars)
  - Symbols: top 20 by 24h volume from Binance
  - TP: 1.5x ATR, SL: 1.0x ATR (R:R >= 1.5 by construction)
  - Max hold: 7 days (3-7 day holds = best WR from winner analysis)
  - Trailing stop: activate at +1x ATR, trail at 0.75x ATR

Data source: api_failover.fetch_klines (Binance -> Bybit -> KuCoin -> CoinGecko -> CryptoCompare)
All indicators computed from raw candles (no external indicator library).

References:
  - Wilder (1978): RSI
  - Bollinger (2001): Bollinger Bands
  - Granville (1963): On-Balance Volume
  - Appel (1979): MACD
  - Kaufman (1998): multi-factor confluence validation
  - Elder (2002): Triple Screen confirmation methodology
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Ensure local imports work when running standalone
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_failover import fetch_klines, fetch_ticker_24h

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Top 20 symbols by typical 24h volume
TOP_20_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
    "LTCUSDT", "TRXUSDT", "ETCUSDT", "SUIUSDT", "TAOUSDT",
    "DOTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "APTUSDT",
]

# Layer weights for CONFLUENCE_WEIGHTED variant (historical IC approximation)
# Mean reversion and volume have slightly higher information coefficients
LAYER_WEIGHTS = {
    "mean_reversion": 0.28,
    "volume_accumulation": 0.26,
    "momentum_ema": 0.24,
    "macd_confirmation": 0.22,
}
WEIGHTED_THRESHOLD = 0.70  # Weighted sum must exceed this

# Trailing stop parameters
TRAIL_ACTIVATE_ATR = 1.0   # Activate trailing stop after +1x ATR profit
TRAIL_DISTANCE_ATR = 0.75  # Trail at 0.75x ATR behind price

# Max hold period
MAX_HOLD_DAYS = 7


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(v: float) -> float:
    """Round to appropriate precision based on magnitude."""
    if v == 0:
        return 0.0
    av = abs(v)
    if av >= 100:
        return round(v, 2)
    if av >= 1:
        return round(v, 4)
    if av >= 0.01:
        return round(v, 6)
    return round(v, 10)


def _klines_to_df(klines: list) -> Optional[pd.DataFrame]:
    """Convert Binance-format klines to DataFrame with OHLCV columns."""
    if not klines or len(klines) < 50:
        return None
    try:
        rows = []
        for k in klines:
            rows.append({
                "Open": float(k[1]),
                "High": float(k[2]),
                "Low": float(k[3]),
                "Close": float(k[4]),
                "Volume": float(k[5]),
            })
        df = pd.DataFrame(rows)
        if len(df) < 50:
            return None
        return df
    except (IndexError, ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Technical indicator computations (from raw candles, no external library)
# ---------------------------------------------------------------------------

def _compute_rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Compute RSI from close prices array. Returns array of same length (NaN padded)."""
    n = len(close)
    rsi_arr = np.full(n, np.nan)
    if n <= period:
        return rsi_arr

    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Seed with SMA
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        rsi_arr[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_arr[period] = 100.0 - (100.0 / (1.0 + rs))

    # Wilder smoothing
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_arr[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_arr[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    return rsi_arr


def _compute_bollinger(close: np.ndarray, period: int = 20, num_std: float = 2.0):
    """Compute Bollinger Bands. Returns (middle, upper, lower) arrays."""
    n = len(close)
    middle = np.full(n, np.nan)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)

    for i in range(period - 1, n):
        window = close[i - period + 1: i + 1]
        m = np.mean(window)
        s = np.std(window, ddof=0)
        middle[i] = m
        upper[i] = m + num_std * s
        lower[i] = m - num_std * s

    return middle, upper, lower


def _compute_obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """Compute On-Balance Volume (Granville 1963)."""
    n = len(close)
    obv = np.zeros(n)
    for i in range(1, n):
        if close[i] > close[i - 1]:
            obv[i] = obv[i - 1] + volume[i]
        elif close[i] < close[i - 1]:
            obv[i] = obv[i - 1] - volume[i]
        else:
            obv[i] = obv[i - 1]
    return obv


def _compute_ema(data: np.ndarray, period: int) -> np.ndarray:
    """Compute EMA from numpy array."""
    n = len(data)
    ema_arr = np.full(n, np.nan)
    if n < period:
        return ema_arr

    # Seed with SMA
    ema_arr[period - 1] = np.mean(data[:period])
    multiplier = 2.0 / (period + 1)

    for i in range(period, n):
        ema_arr[i] = (data[i] - ema_arr[i - 1]) * multiplier + ema_arr[i - 1]

    return ema_arr


def _compute_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                 period: int = 14) -> np.ndarray:
    """Compute Average True Range (Wilder 1978)."""
    n = len(close)
    atr_arr = np.full(n, np.nan)
    if n < period + 1:
        return atr_arr

    # True Range
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))

    # Wilder smoothing
    atr_arr[period] = np.mean(tr[1: period + 1])
    for i in range(period + 1, n):
        atr_arr[i] = (atr_arr[i - 1] * (period - 1) + tr[i]) / period

    return atr_arr


def _compute_macd(close: np.ndarray, fast: int = 12, slow: int = 26,
                  signal: int = 9):
    """Compute MACD line, signal line, and histogram."""
    ema_fast = _compute_ema(close, fast)
    ema_slow = _compute_ema(close, slow)
    macd_line = ema_fast - ema_slow

    # Signal line: EMA of MACD line
    # Need to handle NaN: find first valid index
    valid_idx = slow - 1  # first index where both EMAs are valid
    n = len(close)
    signal_line = np.full(n, np.nan)
    histogram = np.full(n, np.nan)

    if n <= valid_idx + signal:
        return macd_line, signal_line, histogram

    # Compute signal line as EMA of MACD (starting from valid_idx)
    macd_valid = macd_line[valid_idx:]
    sig = _compute_ema(macd_valid, signal)
    signal_line[valid_idx:] = sig

    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def _compute_sma(data: np.ndarray, period: int) -> np.ndarray:
    """Compute Simple Moving Average."""
    n = len(data)
    sma_arr = np.full(n, np.nan)
    for i in range(period - 1, n):
        sma_arr[i] = np.mean(data[i - period + 1: i + 1])
    return sma_arr


# ---------------------------------------------------------------------------
# Layer scoring functions
# ---------------------------------------------------------------------------

def _score_layer1_mean_reversion(close: np.ndarray, high: np.ndarray,
                                  low: np.ndarray) -> tuple[int, str]:
    """Layer 1: Mean Reversion Signal.

    BUY if RSI(14) < 35 OR price below lower Bollinger Band.
    SELL if RSI(14) > 65 OR price above upper Bollinger Band.

    Returns (direction_score, reason) where:
      +1 = BUY signal, -1 = SELL signal, 0 = neutral
    """
    rsi_vals = _compute_rsi(close, 14)
    _, bb_upper, bb_lower = _compute_bollinger(close, 20, 2.0)

    rsi_now = rsi_vals[-1]
    price_now = close[-1]
    bb_up = bb_upper[-1]
    bb_lo = bb_lower[-1]

    if np.isnan(rsi_now) or np.isnan(bb_up) or np.isnan(bb_lo):
        return 0, "insufficient_data"

    buy_signals = []
    sell_signals = []

    if rsi_now < 35:
        buy_signals.append(f"RSI={rsi_now:.1f}<35")
    if rsi_now > 65:
        sell_signals.append(f"RSI={rsi_now:.1f}>65")
    if price_now < bb_lo:
        buy_signals.append(f"price<BB_lower({bb_lo:.2f})")
    if price_now > bb_up:
        sell_signals.append(f"price>BB_upper({bb_up:.2f})")

    if buy_signals:
        return 1, "L1_MeanRev: " + ", ".join(buy_signals)
    if sell_signals:
        return -1, "L1_MeanRev: " + ", ".join(sell_signals)
    return 0, "L1_neutral"


def _score_layer2_volume_accumulation(close: np.ndarray,
                                       volume: np.ndarray) -> tuple[int, str]:
    """Layer 2: Volume Accumulation Signal.

    BUY if OBV trending up for 3+ bars AND volume > 1.5x 20-bar average.
    SELL if OBV trending down for 3+ bars AND volume > 1.5x 20-bar average.

    Returns (direction_score, reason).
    """
    if len(close) < 25 or len(volume) < 25:
        return 0, "insufficient_data"

    obv = _compute_obv(close, volume)

    # Check OBV trend over last 3 bars
    obv_rising = all(obv[-i] > obv[-i - 1] for i in range(1, 4))
    obv_falling = all(obv[-i] < obv[-i - 1] for i in range(1, 4))

    # Volume spike: current bar > 1.5x 20-bar average
    vol_avg_20 = np.mean(volume[-21:-1]) if len(volume) > 21 else np.mean(volume[-20:])
    vol_now = volume[-1]
    vol_spike = vol_now > 1.5 * vol_avg_20 if vol_avg_20 > 0 else False

    if obv_rising and vol_spike:
        ratio = vol_now / vol_avg_20 if vol_avg_20 > 0 else 0
        return 1, f"L2_Volume: OBV_up_3bars, vol={ratio:.1f}x_avg"
    if obv_falling and vol_spike:
        ratio = vol_now / vol_avg_20 if vol_avg_20 > 0 else 0
        return -1, f"L2_Volume: OBV_down_3bars, vol={ratio:.1f}x_avg"
    return 0, "L2_neutral"


def _score_layer3_momentum_ema(close: np.ndarray, high: np.ndarray,
                                low: np.ndarray) -> tuple[int, str]:
    """Layer 3: Momentum / EMA Stack Signal.

    BUY if EMA(9) > EMA(21) > EMA(50) AND ATR > 20-bar ATR average.
    SELL if EMA(9) < EMA(21) < EMA(50) AND ATR > 20-bar ATR average.

    Returns (direction_score, reason).
    """
    if len(close) < 55:
        return 0, "insufficient_data"

    ema9 = _compute_ema(close, 9)
    ema21 = _compute_ema(close, 21)
    ema50 = _compute_ema(close, 50)
    atr_vals = _compute_atr(high, low, close, 14)

    e9 = ema9[-1]
    e21 = ema21[-1]
    e50 = ema50[-1]
    atr_now = atr_vals[-1]

    if any(np.isnan(x) for x in [e9, e21, e50, atr_now]):
        return 0, "insufficient_data"

    # ATR expansion check: current ATR > 20-bar ATR average
    atr_recent = atr_vals[-20:]
    atr_avg = np.nanmean(atr_recent)
    atr_expanding = atr_now > atr_avg if not np.isnan(atr_avg) else False

    if not atr_expanding:
        return 0, "L3_ATR_not_expanding"

    # Bullish stack
    if e9 > e21 > e50:
        return 1, f"L3_Momentum: EMA9({e9:.2f})>EMA21({e21:.2f})>EMA50({e50:.2f}), ATR_expanding"
    # Bearish stack
    if e9 < e21 < e50:
        return -1, f"L3_Momentum: EMA9({e9:.2f})<EMA21({e21:.2f})<EMA50({e50:.2f}), ATR_expanding"

    return 0, "L3_no_stack"


def _score_layer4_macd(close: np.ndarray) -> tuple[int, str]:
    """Layer 4: MACD Confirmation.

    BUY if MACD histogram positive AND rising (current > previous).
    SELL if MACD histogram negative AND falling (current < previous).

    Returns (direction_score, reason).
    """
    if len(close) < 35:
        return 0, "insufficient_data"

    _, _, histogram = _compute_macd(close, 12, 26, 9)

    hist_now = histogram[-1]
    hist_prev = histogram[-2]

    if np.isnan(hist_now) or np.isnan(hist_prev):
        return 0, "insufficient_data"

    # BUY: histogram positive and rising
    if hist_now > 0 and hist_now > hist_prev:
        return 1, f"L4_MACD: hist={hist_now:.4f}_rising"
    # SELL: histogram negative and falling
    if hist_now < 0 and hist_now < hist_prev:
        return -1, f"L4_MACD: hist={hist_now:.4f}_falling"

    return 0, "L4_neutral"


# ---------------------------------------------------------------------------
# Confluence aggregation
# ---------------------------------------------------------------------------

def _evaluate_confluence(close: np.ndarray, high: np.ndarray,
                          low: np.ndarray, volume: np.ndarray) -> dict:
    """Evaluate all 4 layers and return confluence result.

    Returns dict with:
      direction: "BUY" | "SELL" | None
      layers_fired: int (0-4)
      layer_details: dict per layer
      buy_count / sell_count: how many layers agree
      weighted_score: IC-weighted sum for WEIGHTED variant
    """
    l1_score, l1_reason = _score_layer1_mean_reversion(close, high, low)
    l2_score, l2_reason = _score_layer2_volume_accumulation(close, volume)
    l3_score, l3_reason = _score_layer3_momentum_ema(close, high, low)
    l4_score, l4_reason = _score_layer4_macd(close)

    scores = {
        "mean_reversion": l1_score,
        "volume_accumulation": l2_score,
        "momentum_ema": l3_score,
        "macd_confirmation": l4_score,
    }

    reasons = {
        "mean_reversion": l1_reason,
        "volume_accumulation": l2_reason,
        "momentum_ema": l3_reason,
        "macd_confirmation": l4_reason,
    }

    # Count BUY (+1) and SELL (-1) agreements
    buy_count = sum(1 for v in scores.values() if v == 1)
    sell_count = sum(1 for v in scores.values() if v == -1)

    # Weighted score: directional
    weighted_buy = sum(LAYER_WEIGHTS[k] for k, v in scores.items() if v == 1)
    weighted_sell = sum(LAYER_WEIGHTS[k] for k, v in scores.items() if v == -1)

    # Determine dominant direction
    if buy_count >= sell_count and buy_count > 0:
        direction = "BUY"
        layers_fired = buy_count
        weighted_score = weighted_buy
    elif sell_count > buy_count:
        direction = "SELL"
        layers_fired = sell_count
        weighted_score = weighted_sell
    else:
        direction = None
        layers_fired = 0
        weighted_score = 0.0

    return {
        "direction": direction,
        "layers_fired": layers_fired,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "weighted_score": weighted_score,
        "layer_scores": scores,
        "layer_reasons": reasons,
    }


# ---------------------------------------------------------------------------
# Pick builder
# ---------------------------------------------------------------------------

def _make_confluence_pick(symbol: str, direction: str, close: np.ndarray,
                           high: np.ndarray, low: np.ndarray,
                           layers_fired: int, layer_scores: dict,
                           layer_reasons: dict, weighted_score: float,
                           strategy_name: str) -> Optional[dict]:
    """Build a standard pick with ATR-based TP/SL and confluence metadata."""
    atr_vals = _compute_atr(high, low, close, 14)
    current_atr = atr_vals[-1]
    price = close[-1]

    if np.isnan(current_atr) or current_atr <= 0 or price <= 0:
        return None

    # Confidence: 3 of 4 = 0.72, 4 of 4 = 0.85
    if layers_fired >= 4:
        confidence = 0.85
    elif layers_fired >= 3:
        confidence = 0.72
    else:
        return None  # Should not reach here

    # ATR-based TP/SL: TP = 1.5x ATR, SL = 1.0x ATR (R:R = 1.5)
    if direction == "BUY":
        entry = _smart_round(price)
        tp = _smart_round(price + 1.5 * current_atr)
        sl = _smart_round(price - 1.0 * current_atr)
    else:  # SELL
        entry = _smart_round(price)
        tp = _smart_round(price - 1.5 * current_atr)
        sl = _smart_round(price + 1.0 * current_atr)

    # Build fired layers list for transparency
    fired_layers = []
    for layer_name, score in layer_scores.items():
        if (direction == "BUY" and score == 1) or (direction == "SELL" and score == -1):
            fired_layers.append(layer_name)

    reason_parts = []
    for layer_name in fired_layers:
        reason_parts.append(layer_reasons.get(layer_name, layer_name))

    return {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "confidence": round(confidence, 3),
        "strategy": strategy_name,
        "asset_class": "crypto",
        "timestamp": _now_iso(),
        "reason": f"{layers_fired}/4 layers fired: " + "; ".join(reason_parts),
        # Extra confluence metadata
        "confluence_layers_fired": layers_fired,
        "confluence_layer_scores": layer_scores,
        "confluence_weighted_score": round(weighted_score, 4),
        "confluence_fired_layers": fired_layers,
        "atr": _smart_round(current_atr),
        "trailing_stop": {
            "activate_at_atr": TRAIL_ACTIVATE_ATR,
            "trail_distance_atr": TRAIL_DISTANCE_ATR,
        },
        "max_hold_days": MAX_HOLD_DAYS,
    }


# ---------------------------------------------------------------------------
# Fetch top 20 symbols by 24h volume (dynamic)
# ---------------------------------------------------------------------------

def _get_top20_by_volume() -> list[str]:
    """Try to get top 20 USDT pairs by 24h volume from Binance.
    Falls back to hardcoded TOP_20_SYMBOLS on failure."""
    try:
        import urllib.request
        import urllib.error
        from api_failover import BINANCE_SPOT_BASES

        for base in BINANCE_SPOT_BASES[:3]:
            try:
                url = f"{base}/api/v3/ticker/24hr"
                req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read())
                if not data:
                    continue

                # Filter USDT pairs, sort by quoteVolume descending
                usdt_pairs = []
                for t in data:
                    sym = t.get("symbol", "")
                    if sym.endswith("USDT") and not sym.endswith("DOWNUSDT") and not sym.endswith("UPUSDT"):
                        try:
                            vol = float(t.get("quoteVolume", 0))
                            usdt_pairs.append((sym, vol))
                        except (ValueError, TypeError):
                            continue

                usdt_pairs.sort(key=lambda x: x[1], reverse=True)
                top20 = [p[0] for p in usdt_pairs[:20]]
                if len(top20) >= 10:
                    return top20
            except Exception:
                continue
    except Exception:
        pass

    return TOP_20_SYMBOLS


# ---------------------------------------------------------------------------
# Strategy functions (scanner-compatible: func(data, context) -> list[dict])
# ---------------------------------------------------------------------------

def confluence_3of4(data: dict, context: dict = None) -> list[dict]:
    """CONFLUENCE_3OF4: fire when 3+ of 4 layers agree on direction.

    More trades, slightly lower expected WR than 4of4.
    """
    return _run_confluence(data, context, min_layers=3,
                           strategy_name="confluence_3of4",
                           use_weighted=False)


def confluence_4of4(data: dict, context: dict = None) -> list[dict]:
    """CONFLUENCE_4OF4: fire only when ALL 4 layers agree.

    Fewer trades, highest expected WR.
    """
    return _run_confluence(data, context, min_layers=4,
                           strategy_name="confluence_4of4",
                           use_weighted=False)


def confluence_weighted(data: dict, context: dict = None) -> list[dict]:
    """CONFLUENCE_WEIGHTED: weight each layer by historical IC,
    require weighted sum > 0.70.

    Balanced: layers with higher information coefficient count more.
    """
    return _run_confluence(data, context, min_layers=3,
                           strategy_name="confluence_weighted",
                           use_weighted=True)


def _run_confluence(data: dict, context: dict = None,
                    min_layers: int = 3, strategy_name: str = "confluence",
                    use_weighted: bool = False) -> list[dict]:
    """Core confluence engine shared by all 3 variants.

    1. Fetches 4H candles for top 20 symbols (via api_failover)
    2. Evaluates all 4 layers per symbol
    3. Generates picks where enough layers agree
    """
    signals = []

    # Get dynamic top 20 symbols by volume
    top_symbols = _get_top20_by_volume()

    for symbol in top_symbols:
        try:
            # Fetch 100x 4H candles via api_failover (full failover chain)
            klines = fetch_klines(symbol, interval="4h", limit=100)
            df = _klines_to_df(klines)
            if df is None:
                continue

            close = df["Close"].values.astype(float)
            high = df["High"].values.astype(float)
            low = df["Low"].values.astype(float)
            volume = df["Volume"].values.astype(float)

            if len(close) < 55:
                continue

            # Evaluate all 4 layers
            result = _evaluate_confluence(close, high, low, volume)

            direction = result["direction"]
            layers_fired = result["layers_fired"]
            weighted_score = result["weighted_score"]

            if direction is None:
                continue

            # Apply variant-specific entry filter
            if use_weighted:
                # WEIGHTED variant: require weighted_score > threshold
                if weighted_score < WEIGHTED_THRESHOLD:
                    continue
                # Also require at least 3 raw layers for safety
                if layers_fired < 3:
                    continue
            else:
                # Standard variants: require min_layers
                if layers_fired < min_layers:
                    continue

            pick = _make_confluence_pick(
                symbol=symbol,
                direction=direction,
                close=close,
                high=high,
                low=low,
                layers_fired=layers_fired,
                layer_scores=result["layer_scores"],
                layer_reasons=result["layer_reasons"],
                weighted_score=weighted_score,
                strategy_name=strategy_name,
            )

            if pick:
                signals.append(pick)

        except Exception as e:
            logger.debug("%s error on %s: %s", strategy_name, symbol, e)
            continue

    return signals


# ---------------------------------------------------------------------------
# Strategy registry (matches alpha_engine convention)
# ---------------------------------------------------------------------------

CONFLUENCE_STRATEGIES = {
    "confluence_3of4": confluence_3of4,
    "confluence_4of4": confluence_4of4,
    "confluence_weighted": confluence_weighted,
}


# ---------------------------------------------------------------------------
# Standalone test mode
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    print("=" * 70)
    print("  MULTI-SIGNAL CONFLUENCE -- Standalone Test")
    print("=" * 70)
    print()

    for variant_name, func in CONFLUENCE_STRATEGIES.items():
        print(f"\n--- Testing {variant_name} ---")
        t0 = time.time()
        try:
            picks = func({}, None)
            elapsed = time.time() - t0
            print(f"  {len(picks)} picks in {elapsed:.1f}s")
            for p in picks:
                print(f"    {p['symbol']} {p['direction']} "
                      f"entry={p['entry']} tp={p['tp']} sl={p['sl']} "
                      f"conf={p['confidence']} layers={p['confluence_layers_fired']}/4")
                print(f"      {p['reason']}")
        except Exception as e:
            print(f"  ERROR: {e}")

    print("\n" + "=" * 70)
    print("  Test complete.")
    print("=" * 70)
