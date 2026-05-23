"""
Hierarchical Regime Detector — 3-level regime detection (macro → sector → micro).

Outputs probability vectors used to weight signals from different strategy types.
No sklearn/PyTorch dependency — uses numpy, scipy, requests only.

Levels:
  1. Macro  (risk_on / risk_off / transition)  — global market sentiment
  2. Sector (btc_season / alt_season / mixed)  — crypto rotation
  3. Micro  (trending_up / trending_down / ranging / volatile) — per-symbol
"""

import time
from datetime import datetime, timezone

import numpy as np

try:
    import requests
except ImportError:
    requests = None


# ═══════════════════════════════════════════════════════════════════════════════
# Cache — avoid hammering free APIs on repeated calls
# ═══════════════════════════════════════════════════════════════════════════════

_cache = {}
_CACHE_TTL = 300  # 5 minutes


def _cached_get(url, key, timeout=10):
    """GET with simple TTL cache. Returns parsed JSON or None."""
    now = time.time()
    if key in _cache and now - _cache[key]["ts"] < _CACHE_TTL:
        return _cache[key]["data"]
    if requests is None:
        return None
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        _cache[key] = {"data": data, "ts": now}
        return data
    except Exception:
        return _cache.get(key, {}).get("data")


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetchers
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_fear_greed():
    """Fetch Fear & Greed index from alternative.me (0-100)."""
    data = _cached_get(
        "https://api.alternative.me/fng/?limit=2&format=json",
        "fng",
    )
    if data and "data" in data and len(data["data"]) >= 1:
        current = int(data["data"][0]["value"])
        previous = int(data["data"][1]["value"]) if len(data["data"]) > 1 else current
        return {"current": current, "previous": previous}
    return None


def _fetch_global_crypto():
    """Fetch global crypto data from CoinGecko (dominance, market caps)."""
    data = _cached_get(
        "https://api.coingecko.com/api/v3/global",
        "cg_global",
    )
    if data and "data" in data:
        d = data["data"]
        btc_dom = d.get("market_cap_percentage", {}).get("btc", 0)
        eth_dom = d.get("market_cap_percentage", {}).get("eth", 0)
        total_mcap = d.get("total_market_cap", {}).get("usd", 0)
        mcap_change_24h = d.get("market_cap_change_percentage_24h_usd", 0)
        return {
            "btc_dominance": btc_dom,
            "eth_dominance": eth_dom,
            "total_mcap": total_mcap,
            "mcap_change_24h": mcap_change_24h,
        }
    return None


def _fetch_dxy_proxy():
    """
    Estimate DXY direction from EUR/USD via CoinGecko stablecoin data.
    Falling EUR/USD ≈ rising DXY (risk-off for crypto).
    Returns a simple direction signal based on market cap change.
    """
    # Use the global market cap change as a proxy — when crypto dumps,
    # it often correlates with DXY strength.  Not perfect, but zero
    # extra API calls.
    return None  # Handled inline via mcap_change_24h


# ═══════════════════════════════════════════════════════════════════════════════
# Level 1: Macro Regime
# ═══════════════════════════════════════════════════════════════════════════════

MACRO_STATES = ["risk_on", "risk_off", "transition"]


def detect_macro_regime():
    """
    Classify macro regime using Fear & Greed + BTC dominance trend + market cap change.

    Returns:
        dict with keys: state, confidence, features, probabilities
    """
    fng = _fetch_fear_greed()
    global_data = _fetch_global_crypto()

    # Defaults if APIs fail
    fg_value = 50
    fg_delta = 0
    mcap_change = 0.0
    btc_dom = 50.0

    if fng:
        fg_value = fng["current"]
        fg_delta = fng["current"] - fng["previous"]
    if global_data:
        mcap_change = global_data.get("mcap_change_24h", 0.0)
        btc_dom = global_data.get("btc_dominance", 50.0)

    # ── Scoring: positive = risk_on, negative = risk_off ──
    score = 0.0

    # Fear & Greed (0-100): >60 risk-on, <40 risk-off
    if fg_value >= 65:
        score += 2.0
    elif fg_value >= 55:
        score += 1.0
    elif fg_value <= 25:
        score -= 2.0
    elif fg_value <= 40:
        score -= 1.0

    # F&G trend (improving = risk-on)
    if fg_delta > 5:
        score += 0.5
    elif fg_delta < -5:
        score -= 0.5

    # Market cap change (positive = risk-on)
    if mcap_change > 3.0:
        score += 1.5
    elif mcap_change > 1.0:
        score += 0.5
    elif mcap_change < -3.0:
        score -= 1.5
    elif mcap_change < -1.0:
        score -= 0.5

    # BTC dominance rising sharply = flight to quality = risk-off for alts
    # but not necessarily risk-off for the whole market
    if btc_dom > 60:
        score -= 0.3  # slight risk-off lean when BTC dom very high

    # ── Map score → state + confidence ──
    if score >= 1.5:
        state = "risk_on"
        confidence = min(0.95, 0.6 + score * 0.07)
    elif score <= -1.5:
        state = "risk_off"
        confidence = min(0.95, 0.6 + abs(score) * 0.07)
    else:
        state = "transition"
        confidence = max(0.4, 0.7 - abs(score) * 0.1)

    # Build probability vector
    probs = _score_to_macro_probs(score)

    return {
        "state": state,
        "confidence": round(confidence, 4),
        "probabilities": probs,
        "features": {
            "fear_greed": fg_value,
            "fear_greed_delta": fg_delta,
            "mcap_change_24h": round(mcap_change, 2),
            "btc_dominance": round(btc_dom, 2),
            "raw_score": round(score, 2),
        },
    }


def _score_to_macro_probs(score):
    """Convert macro score to probability distribution over 3 states using softmax."""
    # Map score to logits: [risk_on, risk_off, transition]
    logits = np.array([score, -score, -abs(score) * 0.5 + 0.5])
    probs = _softmax(logits)
    return {
        "risk_on": round(float(probs[0]), 4),
        "risk_off": round(float(probs[1]), 4),
        "transition": round(float(probs[2]), 4),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Level 2: Sector Regime
# ═══════════════════════════════════════════════════════════════════════════════

SECTOR_STATES = ["btc_season", "alt_season", "mixed"]


def detect_sector_regime():
    """
    Classify sector rotation: BTC season vs alt season.

    BTC dominance rising → btc_season
    BTC dominance falling + alts outperforming → alt_season
    Otherwise → mixed

    Returns:
        dict with keys: state, confidence, features, probabilities
    """
    global_data = _fetch_global_crypto()

    btc_dom = 50.0
    eth_dom = 15.0
    mcap_change = 0.0

    if global_data:
        btc_dom = global_data.get("btc_dominance", 50.0)
        eth_dom = global_data.get("eth_dominance", 15.0)
        mcap_change = global_data.get("mcap_change_24h", 0.0)

    # ETH/BTC ratio proxy: higher eth_dom relative to btc_dom = alt strength
    eth_btc_ratio = eth_dom / max(btc_dom, 1.0)

    # ── Scoring: positive = btc_season, negative = alt_season ──
    score = 0.0

    # BTC dominance level
    if btc_dom > 55:
        score += 1.5
    elif btc_dom > 50:
        score += 0.5
    elif btc_dom < 40:
        score -= 2.0
    elif btc_dom < 45:
        score -= 1.0

    # ETH/BTC ratio (alt strength signal)
    if eth_btc_ratio > 0.35:
        score -= 1.0  # Alts gaining
    elif eth_btc_ratio < 0.2:
        score += 0.5  # BTC dominant

    # Market cap change direction matters for context
    # Strong positive with low BTC dom = alt rally
    if mcap_change > 2.0 and btc_dom < 48:
        score -= 0.5

    # ── Map score → state + confidence ──
    if score >= 1.0:
        state = "btc_season"
        confidence = min(0.90, 0.55 + score * 0.1)
    elif score <= -1.0:
        state = "alt_season"
        confidence = min(0.90, 0.55 + abs(score) * 0.1)
    else:
        state = "mixed"
        confidence = max(0.4, 0.65 - abs(score) * 0.1)

    probs = _score_to_sector_probs(score)

    return {
        "state": state,
        "confidence": round(confidence, 4),
        "probabilities": probs,
        "features": {
            "btc_dominance": round(btc_dom, 2),
            "eth_dominance": round(eth_dom, 2),
            "eth_btc_ratio": round(eth_btc_ratio, 4),
            "mcap_change_24h": round(mcap_change, 2),
            "raw_score": round(score, 2),
        },
    }


def _score_to_sector_probs(score):
    """Convert sector score to probability distribution."""
    logits = np.array([score, -score, -abs(score) * 0.5 + 0.5])
    probs = _softmax(logits)
    return {
        "btc_season": round(float(probs[0]), 4),
        "alt_season": round(float(probs[1]), 4),
        "mixed": round(float(probs[2]), 4),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Level 3: Micro Regime (per-symbol)
# ═══════════════════════════════════════════════════════════════════════════════

MICRO_STATES = ["trending_up", "trending_down", "ranging", "volatile"]


def detect_micro_regime(symbol, prices=None):
    """
    Per-symbol micro regime using ADX, return direction, and volatility.

    Args:
        symbol: Ticker string (for labeling; not fetched here).
        prices: list/array of recent close prices (minimum 30 values).
                If None, returns a default 'ranging' regime.

    Returns:
        dict with keys: state, confidence, features, probabilities
    """
    if prices is None or len(prices) < 20:
        return {
            "state": "ranging",
            "confidence": 0.5,
            "probabilities": {s: 0.25 for s in MICRO_STATES},
            "features": {
                "symbol": symbol,
                "adx": None,
                "recent_return": None,
                "volatility_ratio": None,
                "reason": "insufficient data",
            },
        }

    prices = np.array(prices, dtype=float)

    # ── Compute ADX ──
    adx = _compute_adx(prices, period=14)

    # ── Recent return (last 5 bars) ──
    if len(prices) >= 6:
        recent_return = (prices[-1] / prices[-6]) - 1.0
    else:
        recent_return = (prices[-1] / prices[0]) - 1.0

    # ── Volatility ratio: recent vol / average vol ──
    returns = np.diff(prices) / prices[:-1]
    if len(returns) >= 20:
        recent_vol = np.std(returns[-10:])
        avg_vol = np.std(returns[-20:])
    else:
        recent_vol = np.std(returns[-5:]) if len(returns) >= 5 else 0.01
        avg_vol = np.std(returns) if len(returns) > 0 else 0.01

    vol_ratio = recent_vol / max(avg_vol, 1e-10)

    # ── Classification logic ──
    if adx > 25 and recent_return > 0.005:
        state = "trending_up"
        confidence = min(0.95, 0.55 + (adx - 25) * 0.01 + recent_return * 2)
    elif adx > 25 and recent_return < -0.005:
        state = "trending_down"
        confidence = min(0.95, 0.55 + (adx - 25) * 0.01 + abs(recent_return) * 2)
    elif adx < 20 and vol_ratio < 1.2:
        state = "ranging"
        confidence = min(0.90, 0.55 + (20 - adx) * 0.01 + (1.2 - vol_ratio) * 0.1)
    elif vol_ratio > 1.5 or (vol_ratio > 1.2 and adx < 25):
        state = "volatile"
        confidence = min(0.90, 0.5 + (vol_ratio - 1.0) * 0.15)
    else:
        # Ambiguous — low ADX, moderate vol, small return
        if recent_return > 0.002:
            state = "trending_up"
        elif recent_return < -0.002:
            state = "trending_down"
        else:
            state = "ranging"
        confidence = 0.45

    confidence = max(0.3, min(confidence, 0.95))
    probs = _build_micro_probs(state, confidence, adx, recent_return, vol_ratio)

    return {
        "state": state,
        "confidence": round(confidence, 4),
        "probabilities": probs,
        "features": {
            "symbol": symbol,
            "adx": round(adx, 2),
            "recent_return": round(recent_return, 6),
            "volatility_ratio": round(vol_ratio, 4),
        },
    }


def _compute_adx(prices, period=14):
    """
    Compute ADX from close-only data using Wilder's smoothing.

    With only close prices we approximate:
      +DM = max(close_t - close_{t-1}, 0)
      -DM = max(close_{t-1} - close_t, 0)
      TR  = abs(close_t - close_{t-1})
    """
    n = len(prices)
    if n < period + 2:
        return 20.0  # Default neutral ADX

    diffs = np.diff(prices)
    plus_dm = np.where(diffs > 0, diffs, 0.0)
    minus_dm = np.where(diffs < 0, -diffs, 0.0)
    tr = np.abs(diffs)

    # Wilder's smoothing (EMA with alpha = 1/period)
    alpha = 1.0 / period
    smoothed_plus = np.zeros(len(diffs))
    smoothed_minus = np.zeros(len(diffs))
    smoothed_tr = np.zeros(len(diffs))

    smoothed_plus[0] = plus_dm[0]
    smoothed_minus[0] = minus_dm[0]
    smoothed_tr[0] = tr[0]

    for i in range(1, len(diffs)):
        smoothed_plus[i] = smoothed_plus[i - 1] * (1 - alpha) + plus_dm[i] * alpha
        smoothed_minus[i] = smoothed_minus[i - 1] * (1 - alpha) + minus_dm[i] * alpha
        smoothed_tr[i] = smoothed_tr[i - 1] * (1 - alpha) + tr[i] * alpha

    # Directional indicators
    plus_di = np.where(smoothed_tr > 0, 100 * smoothed_plus / smoothed_tr, 0)
    minus_di = np.where(smoothed_tr > 0, 100 * smoothed_minus / smoothed_tr, 0)

    # DX
    di_sum = plus_di + minus_di
    dx = np.where(di_sum > 0, 100 * np.abs(plus_di - minus_di) / di_sum, 0)

    # ADX = smoothed DX
    if len(dx) < period:
        return float(np.mean(dx[-5:])) if len(dx) >= 5 else 20.0

    adx_values = np.zeros(len(dx))
    adx_values[period - 1] = np.mean(dx[:period])
    for i in range(period, len(dx)):
        adx_values[i] = adx_values[i - 1] * (1 - alpha) + dx[i] * alpha

    return float(adx_values[-1])


def _build_micro_probs(state, confidence, adx, ret, vol_ratio):
    """Build probability distribution over micro states using heuristic softmax."""
    # Logits based on features
    logits = np.array([
        ret * 50 + max(adx - 20, 0) * 0.05,          # trending_up
        -ret * 50 + max(adx - 20, 0) * 0.05,          # trending_down
        max(20 - adx, 0) * 0.1 - vol_ratio * 0.3,     # ranging
        (vol_ratio - 1.0) * 1.5 - max(adx - 25, 0) * 0.05,  # volatile
    ])
    probs = _softmax(logits)
    return {
        MICRO_STATES[i]: round(float(probs[i]), 4)
        for i in range(4)
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Weight mapping: regime combination → signal type multipliers
# ═══════════════════════════════════════════════════════════════════════════════

SIGNAL_TYPES = ["trend_following", "mean_reversion", "momentum", "contrarian"]

# Base weight tables per level (additive contributions)
_MACRO_WEIGHTS = {
    "risk_on":    {"trend_following": 0.15, "mean_reversion": -0.05, "momentum": 0.15, "contrarian": -0.15},
    "risk_off":   {"trend_following": -0.15, "mean_reversion": 0.15, "momentum": -0.10, "contrarian": 0.15},
    "transition": {"trend_following": -0.05, "mean_reversion": 0.05, "momentum": -0.05, "contrarian": 0.05},
}

_SECTOR_WEIGHTS = {
    "btc_season": {"trend_following": 0.10, "mean_reversion": -0.05, "momentum": 0.10, "contrarian": -0.10},
    "alt_season": {"trend_following": 0.05, "mean_reversion": 0.05, "momentum": 0.15, "contrarian": -0.05},
    "mixed":      {"trend_following": 0.0,  "mean_reversion": 0.05, "momentum": 0.0,  "contrarian": 0.0},
}

_MICRO_WEIGHTS = {
    "trending_up":   {"trend_following": 0.20, "mean_reversion": -0.20, "momentum": 0.15, "contrarian": -0.25},
    "trending_down": {"trend_following": 0.15, "mean_reversion": -0.15, "momentum": -0.10, "contrarian": 0.10},
    "ranging":       {"trend_following": -0.25, "mean_reversion": 0.30, "momentum": -0.20, "contrarian": 0.15},
    "volatile":      {"trend_following": -0.10, "mean_reversion": -0.05, "momentum": -0.05, "contrarian": 0.20},
}


def get_regime_weights(symbol, prices=None):
    """
    Combine all three regime levels into a single weight vector for signal types.

    Base weight = 1.0 per signal type.
    Each regime level adds/subtracts based on its state, scaled by confidence.

    Returns:
        dict mapping signal type → weight multiplier (0.3 to 1.7 range, clamped)
    """
    macro = detect_macro_regime()
    sector = detect_sector_regime()
    micro = detect_micro_regime(symbol, prices)

    weights = {}
    for sig in SIGNAL_TYPES:
        w = 1.0
        # Add macro contribution (scaled by confidence)
        w += _MACRO_WEIGHTS.get(macro["state"], {}).get(sig, 0) * macro["confidence"]
        # Add sector contribution
        w += _SECTOR_WEIGHTS.get(sector["state"], {}).get(sig, 0) * sector["confidence"]
        # Add micro contribution (strongest influence — closest to the asset)
        w += _MICRO_WEIGHTS.get(micro["state"], {}).get(sig, 0) * micro["confidence"]
        # Clamp to [0.3, 1.7] — never fully zero-out or over-amplify
        w = max(0.3, min(1.7, w))
        weights[sig] = round(w, 4)

    return {
        "symbol": symbol,
        "weights": weights,
        "regime_states": {
            "macro": macro["state"],
            "sector": sector["state"],
            "micro": micro["state"],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Full analysis: all three levels + combined weights + timestamp
# ═══════════════════════════════════════════════════════════════════════════════

def full_regime_analysis(symbol, prices=None):
    """
    Complete hierarchical regime analysis for a symbol.

    Args:
        symbol: Ticker string (e.g., "BTCUSDT")
        prices: Optional list/array of recent close prices for micro regime.
                If None, micro regime defaults to 'ranging'.

    Returns:
        dict with macro, sector, micro regimes + combined weights + timestamp
    """
    macro = detect_macro_regime()
    sector = detect_sector_regime()
    micro = detect_micro_regime(symbol, prices)

    # Combined weights (same logic as get_regime_weights but reuses computed regimes)
    weights = {}
    for sig in SIGNAL_TYPES:
        w = 1.0
        w += _MACRO_WEIGHTS.get(macro["state"], {}).get(sig, 0) * macro["confidence"]
        w += _SECTOR_WEIGHTS.get(sector["state"], {}).get(sig, 0) * sector["confidence"]
        w += _MICRO_WEIGHTS.get(micro["state"], {}).get(sig, 0) * micro["confidence"]
        w = max(0.3, min(1.7, w))
        weights[sig] = round(w, 4)

    return {
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "macro": macro,
        "sector": sector,
        "micro": micro,
        "combined_weights": weights,
        "regime_summary": (
            f"Macro={macro['state']}({macro['confidence']:.0%}) "
            f"Sector={sector['state']}({sector['confidence']:.0%}) "
            f"Micro={micro['state']}({micro['confidence']:.0%})"
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════════════════════

def _softmax(logits):
    """Numerically stable softmax."""
    x = np.array(logits, dtype=float)
    x -= x.max()
    exp_x = np.exp(x)
    return exp_x / exp_x.sum()


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json
    import sys

    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"

    # Generate synthetic prices for demo if no real data
    np.random.seed(42)
    demo_prices = 50000 * np.cumprod(1 + np.random.normal(0.001, 0.02, 60))

    result = full_regime_analysis(symbol, prices=demo_prices.tolist())
    print(json.dumps(result, indent=2))
