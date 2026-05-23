"""
ALPHA_ENGINE -- Entry Timing Optimizer
========================================
Computes entry quality labels for ML training and real-time entry timing scores.

Three main functions:
  1. compute_entry_quality(closed_pick) -- post-hoc label for how good the entry was
  2. compute_optimal_sl_from_winners(closed_picks, ...) -- MAE analysis for SL placement
  3. compute_entry_timing_score(symbol, data, signal) -- real-time scoring (0-1)

Used by:
  - ml_ranker.py: entry quality labels enrich training data
  - forward_validator.py: entry timing score adjusts elite_score at pick creation
"""

from __future__ import annotations

import json
import logging
import math
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# -- API endpoints with 3+ fallback chain (per MEMORY.md rule) --------

_BINANCE_KLINE_BASES = [
    "https://api.binance.com/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
    "https://api2.binance.com/api/v3/klines",
]

_COINGECKO_BASE = "https://api.coingecko.com/api/v3"

_CG_ID_MAP = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "BNBUSDT": "binancecoin",
    "SOLUSDT": "solana", "ADAUSDT": "cardano", "DOGEUSDT": "dogecoin",
    "XRPUSDT": "ripple", "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot",
    "LINKUSDT": "chainlink", "MATICUSDT": "matic-network", "LTCUSDT": "litecoin",
    "ATOMUSDT": "cosmos", "NEARUSDT": "near", "ARBUSDT": "arbitrum",
    "OPUSDT": "optimism", "APTUSDT": "aptos", "SUIUSDT": "sui",
}


# -- Data fetching -----------------------------------------------------

def _fetch_json(url: str, timeout: int = 10) -> Optional[list | dict]:
    """Fetch JSON with basic error handling."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEntryOptimizer/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug(f"Fetch failed for {url}: {e}")
        return None


def _fetch_short_klines(symbol: str, interval: str = "15m", limit: int = 16) -> Optional[list]:
    """
    Fetch short-term OHLCV klines with Binance 3-mirror fallback + CoinGecko.
    Returns list of [open, high, low, close, volume] floats.
    """
    for base in _BINANCE_KLINE_BASES:
        url = f"{base}?symbol={symbol}&interval={interval}&limit={limit}"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) >= 4:
            return [
                [float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])]
                for k in data
            ]

    # CoinGecko fallback (1-day granularity, limited but better than nothing)
    cg_id = _CG_ID_MAP.get(symbol.upper())
    if cg_id:
        url = f"{_COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days=1"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) >= 4:
            return [
                [float(k[1]), float(k[2]), float(k[3]), float(k[4]), 0.0]
                for k in data
            ]

    logger.debug(f"All API sources failed for {symbol} {interval}")
    return None


# -- Task 1: Entry Quality Labels for Training ------------------------

def compute_entry_quality(closed_pick: dict) -> dict:
    """For a closed trade, compute how good the entry was.

    For LONG: compare entry_price to the minimum price in the first N bars after entry.
    entry_edge = (entry_price - min_price_after) / entry_price * 100
    Positive = entered too high (bad), Negative = entered below dip (good)

    For SHORT: compare entry to max price after entry.
    entry_edge = (max_price_after - entry_price) / entry_price * 100
    Positive = entered too low (bad), Negative = entered above peak (good)

    Returns dict with:
      - entry_edge_pct: float (positive=bad, negative=good)
      - entry_quality: str ("excellent", "good", "fair", "poor")
      - mae_pct: float (max adverse excursion as %)
      - mfe_pct: float (max favorable excursion as %)
    """
    result = {
        "entry_edge_pct": 0.0,
        "entry_quality": "unknown",
        "mae_pct": 0.0,
        "mfe_pct": 0.0,
    }

    entry = float(closed_pick.get("entry_price", 0) or 0)
    if entry <= 0:
        return result

    direction = (closed_pick.get("direction") or closed_pick.get("signal_type") or "").upper()
    mae = float(closed_pick.get("mae", 0) or 0)
    mfe = float(closed_pick.get("mfe", 0) or 0)

    result["mae_pct"] = abs(mae) * 100
    result["mfe_pct"] = abs(mfe) * 100

    if direction in ("BUY", "LONG"):
        # For longs: MAE tells us the worst drawdown from entry
        # entry_edge = how much we entered above the subsequent low
        # mae is typically negative for longs (price went below entry)
        entry_edge = abs(mae) * 100  # positive = entered too high
        result["entry_edge_pct"] = entry_edge
    elif direction in ("SELL", "SHORT"):
        # For shorts: MFE tells us the best move from entry (price went down)
        # but MAE tells us price went up (bad for shorts)
        entry_edge = abs(mae) * 100  # positive = entered too low
        result["entry_edge_pct"] = entry_edge
    else:
        return result

    # Classify entry quality based on edge percentage
    if entry_edge <= 0.5:
        result["entry_quality"] = "excellent"  # entered within 0.5% of optimal
    elif entry_edge <= 1.5:
        result["entry_quality"] = "good"       # within 1.5%
    elif entry_edge <= 3.0:
        result["entry_quality"] = "fair"       # within 3%
    else:
        result["entry_quality"] = "poor"       # more than 3% from optimal

    return result


def compute_optimal_sl_from_winners(closed_picks: list[dict],
                                     symbol: Optional[str] = None,
                                     strategy: Optional[str] = None) -> dict:
    """Analyze MAE of winning trades to find where SL should be.

    The idea: if winners had a max adverse excursion (MAE) of X%, then
    setting SL tighter than X% would have stopped out winners unnecessarily.
    Setting SL at percentile(MAE, 95) of winners captures 95% of winning trades.

    Args:
        closed_picks: list of closed pick dicts
        symbol: optional filter by symbol
        strategy: optional filter by strategy

    Returns:
        {
            "optimal_sl_pct": float,  # recommended SL distance as %
            "mae_p50": float,         # median MAE of winners
            "mae_p75": float,         # 75th percentile MAE
            "mae_p95": float,         # 95th percentile MAE
            "n_winners": int,         # number of winning trades analyzed
            "n_losers": int,          # number of losing trades
            "current_avg_sl_pct": float,  # current average SL distance
        }
    """
    result = {
        "optimal_sl_pct": 3.0,  # default
        "mae_p50": 0.0,
        "mae_p75": 0.0,
        "mae_p95": 0.0,
        "n_winners": 0,
        "n_losers": 0,
        "current_avg_sl_pct": 0.0,
    }

    # Filter picks
    filtered = closed_picks
    if symbol:
        filtered = [p for p in filtered if p.get("symbol") == symbol]
    if strategy:
        filtered = [p for p in filtered if p.get("strategy") == strategy]

    if not filtered:
        return result

    # Separate winners and losers
    winners = [p for p in filtered if p.get("status") == "WON"
               or (p.get("status") == "TIME_EXPIRY" and float(p.get("pnl_pct", 0) or 0) > 0)]
    losers = [p for p in filtered if p.get("status") == "LOST"
              or (p.get("status") == "TIME_EXPIRY" and float(p.get("pnl_pct", 0) or 0) <= 0)]

    result["n_winners"] = len(winners)
    result["n_losers"] = len(losers)

    # Compute current average SL distance
    sl_dists = []
    for p in filtered:
        entry = float(p.get("entry_price", 0) or 0)
        sl = float(p.get("stop_loss", 0) or 0)
        if entry > 0 and sl > 0:
            sl_dists.append(abs(entry - sl) / entry * 100)
    if sl_dists:
        result["current_avg_sl_pct"] = round(sum(sl_dists) / len(sl_dists), 3)

    # Analyze MAE of winners
    if len(winners) < 5:
        return result

    winner_maes = []
    for p in winners:
        mae = float(p.get("mae", 0) or 0)
        winner_maes.append(abs(mae) * 100)  # convert to percentage

    winner_maes.sort()
    n = len(winner_maes)

    result["mae_p50"] = round(winner_maes[n // 2], 3)
    result["mae_p75"] = round(winner_maes[int(n * 0.75)], 3)
    result["mae_p95"] = round(winner_maes[min(int(n * 0.95), n - 1)], 3)

    # Optimal SL = 95th percentile MAE of winners + small buffer (10%)
    result["optimal_sl_pct"] = round(result["mae_p95"] * 1.10, 3)

    return result


# -- Task 1c: Real-Time Entry Timing Score -----------------------------

def compute_entry_timing_score(symbol: str, data: Optional[dict] = None,
                                signal: Optional[dict] = None) -> float:
    """Score whether NOW is a good time to enter based on:
    - Relative position in last 4h range (0=bottom, 1=top)
    - Volume trend (increasing = confirming, decreasing = fading)
    - RSI micro-divergence on 5min equivalent
    - Distance from VWAP

    Args:
        symbol: Trading pair (e.g. "BTCUSDT")
        data: Optional pre-fetched OHLCV data dict with keys:
              'closes', 'highs', 'lows', 'volumes'
              If None, fetches live 15m candles.
        signal: Optional signal dict for direction context

    Returns:
        float 0-1 where 1 = excellent entry timing, 0 = terrible
    """
    scores = []  # collect component scores, average at end

    direction = "LONG"
    if signal:
        d = (signal.get("direction") or signal.get("signal_type") or "").upper()
        if d in ("SELL", "SHORT"):
            direction = "SHORT"

    # Get price data
    closes = None
    highs = None
    lows = None
    volumes = None

    if data and isinstance(data, dict):
        closes = data.get("closes")
        highs = data.get("highs")
        lows = data.get("lows")
        volumes = data.get("volumes")

    if not closes:
        # Fetch live 15m candles (16 bars = 4 hours)
        klines = _fetch_short_klines(symbol, interval="15m", limit=16)
        if klines and len(klines) >= 4:
            closes = [k[3] for k in klines]
            highs = [k[1] for k in klines]
            lows = [k[2] for k in klines]
            volumes = [k[4] for k in klines]

    if not closes or len(closes) < 4:
        return 0.5  # neutral when no data

    # --- Component 1: Position in 4h range (weight: 30%) ---
    range_high = max(highs) if highs else max(closes)
    range_low = min(lows) if lows else min(closes)
    current = closes[-1]
    range_span = range_high - range_low

    if range_span > 0:
        position_in_range = (current - range_low) / range_span  # 0=bottom, 1=top
    else:
        position_in_range = 0.5

    # For LONG: lower in range = better entry; for SHORT: higher = better
    if direction == "LONG":
        range_score = 1.0 - position_in_range  # 0 at top, 1 at bottom
    else:
        range_score = position_in_range  # 1 at top, 0 at bottom
    scores.append(("range", range_score, 0.30))

    # --- Component 2: Volume trend (weight: 25%) ---
    if volumes and len(volumes) >= 4:
        recent_vol = volumes[-4:]
        # Check if volume is increasing (confirming) or decreasing (fading)
        vol_trend = 0.0
        for i in range(1, len(recent_vol)):
            if recent_vol[i - 1] > 0:
                vol_trend += (recent_vol[i] - recent_vol[i - 1]) / recent_vol[i - 1]
        vol_trend /= max(len(recent_vol) - 1, 1)

        # Increasing volume on entry = good (0.5 to 1.0 based on trend strength)
        vol_score = 0.5 + min(max(vol_trend * 2.0, -0.5), 0.5)
        scores.append(("volume", vol_score, 0.25))
    else:
        scores.append(("volume", 0.5, 0.25))

    # --- Component 3: RSI micro (5-bar RSI on the 15m data) (weight: 25%) ---
    if len(closes) >= 6:
        rsi_val = _compute_rsi(closes, period=5)
        if direction == "LONG":
            # For longs: RSI < 30 = oversold = great entry, RSI > 70 = overbought = bad
            if rsi_val < 30:
                rsi_score = 1.0
            elif rsi_val < 45:
                rsi_score = 0.7
            elif rsi_val < 55:
                rsi_score = 0.5
            elif rsi_val < 70:
                rsi_score = 0.3
            else:
                rsi_score = 0.1
        else:
            # For shorts: RSI > 70 = overbought = great entry
            if rsi_val > 70:
                rsi_score = 1.0
            elif rsi_val > 55:
                rsi_score = 0.7
            elif rsi_val > 45:
                rsi_score = 0.5
            elif rsi_val > 30:
                rsi_score = 0.3
            else:
                rsi_score = 0.1
        scores.append(("rsi_micro", rsi_score, 0.25))
    else:
        scores.append(("rsi_micro", 0.5, 0.25))

    # --- Component 4: Distance from VWAP (weight: 20%) ---
    if volumes and len(volumes) == len(closes) and len(closes) >= 4:
        vwap = _compute_vwap(closes, volumes)
        if vwap > 0 and current > 0:
            vwap_dist = (current - vwap) / vwap  # positive = above VWAP

            if direction == "LONG":
                # For longs: below VWAP = good entry (mean reversion toward VWAP)
                if vwap_dist < -0.005:
                    vwap_score = 0.9  # well below VWAP
                elif vwap_dist < 0:
                    vwap_score = 0.7  # slightly below VWAP
                elif vwap_dist < 0.005:
                    vwap_score = 0.5  # at VWAP
                else:
                    vwap_score = 0.2  # above VWAP
            else:
                # For shorts: above VWAP = good entry
                if vwap_dist > 0.005:
                    vwap_score = 0.9
                elif vwap_dist > 0:
                    vwap_score = 0.7
                elif vwap_dist > -0.005:
                    vwap_score = 0.5
                else:
                    vwap_score = 0.2
            scores.append(("vwap", vwap_score, 0.20))
        else:
            scores.append(("vwap", 0.5, 0.20))
    else:
        scores.append(("vwap", 0.5, 0.20))

    # Weighted average
    total_weight = sum(w for _, _, w in scores)
    if total_weight <= 0:
        return 0.5

    timing_score = sum(s * w for _, s, w in scores) / total_weight
    return round(max(0.0, min(1.0, timing_score)), 3)


# -- Helper: Simple RSI calculation ------------------------------------

def _compute_rsi(closes: list, period: int = 5) -> float:
    """Compute RSI from a list of close prices. Returns 0-100."""
    if len(closes) < period + 1:
        return 50.0

    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        if change >= 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))

    if len(gains) < period:
        return 50.0

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# -- Helper: VWAP calculation -----------------------------------------

def _compute_vwap(closes: list, volumes: list) -> float:
    """Compute Volume-Weighted Average Price from closes and volumes."""
    if not closes or not volumes or len(closes) != len(volumes):
        return 0.0

    cum_pv = 0.0
    cum_vol = 0.0
    for price, vol in zip(closes, volumes):
        cum_pv += price * vol
        cum_vol += vol

    if cum_vol <= 0:
        return sum(closes) / len(closes) if closes else 0.0
    return cum_pv / cum_vol


# -- Task 2: Regime Interaction Features -------------------------------

def compute_regime_interactions(features_dict: dict, regime: int) -> dict:
    """Create interaction features between regime and base signals.

    Args:
        features_dict: dict of base feature name -> value
        regime: 0=low_vol/choppy, 1=medium/mean_reverting, 2=high_vol/trending

    Returns:
        dict of interaction feature name -> value
    """
    interactions = {}
    regime_val = regime  # 0=low_vol, 1=medium, 2=high_vol

    # RSI behaves differently in different regimes
    # In high-vol regimes, RSI extremes are more meaningful
    interactions["rsi_x_regime"] = features_dict.get("rsi_14", 50) * regime_val

    # Volume ratio matters more in low vol (regime 0)
    # When market is quiet, volume spikes are more significant
    interactions["vol_ratio_x_regime"] = features_dict.get("volume_ratio", 1) * (3 - regime_val)

    # Momentum is more reliable in trending (high vol) regimes
    interactions["momentum_x_regime"] = features_dict.get("momentum_7d", 0) * regime_val

    # BB position + regime (mean reversion works in low vol)
    interactions["bb_x_regime"] = features_dict.get("bb_position", 0.5) * (1 if regime_val == 0 else 0.5)

    # Hour interactions -- time-of-day effects differ by regime
    interactions["hour_x_regime"] = features_dict.get("hour_sin", 0) * regime_val

    # ATR interaction -- volatility proxy significance varies by regime
    interactions["atr_x_regime"] = features_dict.get("atr_at_entry", 0) * regime_val

    # Direction x regime -- counter-trend trades penalized more in trending regimes
    direction_val = features_dict.get("direction_market_alignment", 0)
    interactions["direction_x_regime"] = direction_val * regime_val

    return interactions


# -- Standalone test ---------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("ALPHA ENGINE -- Entry Optimizer v1.0")
    print("=" * 60)

    # Test entry quality
    test_pick = {
        "entry_price": 100.0,
        "direction": "LONG",
        "mae": -0.02,   # 2% drawdown
        "mfe": 0.05,    # 5% max gain
        "status": "WON",
    }
    quality = compute_entry_quality(test_pick)
    print(f"\nEntry quality test: {quality}")

    # Test regime interactions
    test_features = {
        "rsi_14": 45,
        "volume_ratio": 2.5,
        "momentum_7d": 0.03,
        "bb_position": 0.3,
        "hour_sin": 0.7,
        "atr_at_entry": 0.015,
        "direction_market_alignment": 1,
    }
    for regime in (0, 1, 2):
        interactions = compute_regime_interactions(test_features, regime)
        print(f"\nRegime {regime} interactions: {interactions}")

    # Test entry timing (live API call)
    print("\nEntry timing score (BTCUSDT LONG):")
    score = compute_entry_timing_score("BTCUSDT", signal={"direction": "LONG"})
    print(f"  Score: {score}")

    print("\nDone.")
