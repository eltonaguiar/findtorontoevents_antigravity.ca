#!/usr/bin/env python3
"""
Fast Regime Detector -- Sub-minute microstructure regime ensemble.
=================================================================
Replaces the slow 30-min regime cycle with a 3-signal microstructure ensemble
that refreshes every 5 minutes. Designed for crypto where 30 min is fatal.

Signals:
  1. Funding rate   -- overleveraged longs/shorts via Binance fapi
  2. Futures premium -- perp vs spot basis (contango/backwardation)
  3. Price momentum  -- EMA(5) vs EMA(20) on 1h candles

Regimes: STRONG_BULL, BULL, CHOPPY, BEAR, STRONG_BEAR

Cross-AI consensus (6/6): sub-minute regime detection is critical.
KIMI recommendation: microstructure ensemble (funding + premium + book pressure).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_log = logging.getLogger("alpha_engine.fast_regime")

# ---------------------------------------------------------------------------
# Config imports (with failover URLs)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from config import DATA_DIR
except ImportError:
    DATA_DIR = Path(__file__).resolve().parent / "data"

# Shared API failover (Binance -> Bybit -> CoinGecko -> KuCoin -> CryptoCompare)
try:
    from api_failover import (
        fetch_klines as _failover_fetch_klines,
        fetch_price as _failover_fetch_price,
        fetch_funding_rate as _failover_fetch_funding,
    )
except ImportError:
    from alpha_engine.api_failover import (
        fetch_klines as _failover_fetch_klines,
        fetch_price as _failover_fetch_price,
        fetch_funding_rate as _failover_fetch_funding,
    )

# Keep these for backward compatibility with existing code in this file
FAPI_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
SPOT_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
BYBIT_BASE = "https://api.bybit.com"

# ---------------------------------------------------------------------------
# Cache -- 5 minute TTL (not 30 min!)
# ---------------------------------------------------------------------------
CACHE_TTL_SECONDS = 300  # 5 minutes

_regime_cache: dict[str, dict] = {}  # symbol -> {regime_dict, timestamp}

# ---------------------------------------------------------------------------
# HTTP helper with failover (requests-based, handles 451 geo-block)
# ---------------------------------------------------------------------------
HTTP_TIMEOUT = 8


def _fetch_json(url: str, timeout: int = HTTP_TIMEOUT) -> dict | list | None:
    """Fetch JSON from a single URL, returning None on any failure."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            if code == 451:
                _log.debug("Geo-blocked (451): %s", url)
                return None
            return json.loads(resp.read())
    except Exception as e:
        _log.debug("Fetch failed %s: %s", url, e)
        return None


def _fetch_with_failover(path: str, bases: list[str], timeout: int = HTTP_TIMEOUT) -> dict | list | None:
    """Try path across multiple base URLs, return first success."""
    for base in bases:
        result = _fetch_json(f"{base}{path}", timeout=timeout)
        if result is not None:
            return result
    return None


# ---------------------------------------------------------------------------
# Signal 1: Funding Rate
# ---------------------------------------------------------------------------
def _fetch_funding_rate(symbol: str = "BTCUSDT") -> dict:
    """Fetch current funding rate from Binance fapi with full failover.

    Returns: {value: float, signal: str, raw: float}
    Signal: BULLISH (negative funding = shorts overleveraged),
            BEARISH (positive funding = longs overleveraged),
            NEUTRAL (near zero)
    """
    result = {"value": 0.0, "signal": "NEUTRAL", "raw": 0.0, "source": "none"}

    # 1. Try Binance fapi (4 mirrors)
    data = _fetch_with_failover(
        f"/fapi/v1/premiumIndex?symbol={symbol}", FAPI_BASES
    )
    if data and isinstance(data, dict) and "lastFundingRate" in data:
        rate = float(data["lastFundingRate"])
        result["raw"] = rate
        result["value"] = rate * 100  # Convert to percentage
        result["source"] = "binance_fapi"
        if rate > 0.0001:  # > 0.01%
            result["signal"] = "BEARISH"  # Longs overleveraged
        elif rate < -0.0001:  # < -0.01%
            result["signal"] = "BULLISH"  # Shorts overleveraged
        else:
            result["signal"] = "NEUTRAL"
        return result

    # 2. Bybit fallback
    try:
        bybit_data = _fetch_json(
            f"{BYBIT_BASE}/v5/market/tickers?category=linear&symbol={symbol}"
        )
        if bybit_data and bybit_data.get("retCode") == 0:
            tickers = bybit_data.get("result", {}).get("list", [])
            if tickers:
                rate_str = tickers[0].get("fundingRate", "0")
                rate = float(rate_str)
                result["raw"] = rate
                result["value"] = rate * 100
                result["source"] = "bybit"
                if rate > 0.0001:
                    result["signal"] = "BEARISH"
                elif rate < -0.0001:
                    result["signal"] = "BULLISH"
                return result
    except Exception as e:
        _log.debug("Bybit funding fallback failed: %s", e)

    # 3. CoinGecko fallback (no direct funding, use sentiment proxy)
    _log.warning("All funding rate sources failed for %s", symbol)
    return result


# ---------------------------------------------------------------------------
# Signal 2: Futures Premium (basis)
# ---------------------------------------------------------------------------
def _fetch_futures_premium(symbol: str = "BTCUSDT") -> dict:
    """Compare perpetual mark price vs spot price to get basis.

    Returns: {value_pct: float, signal: str, perp_price: float, spot_price: float}
    Premium > 0.3% = BULLISH (traders paying premium for longs)
    Discount < -0.3% = BEARISH (backwardation)
    """
    result = {
        "value_pct": 0.0, "signal": "NEUTRAL",
        "perp_price": 0.0, "spot_price": 0.0, "source": "none",
    }

    # Fetch perpetual mark price from fapi
    perp_data = _fetch_with_failover(
        f"/fapi/v1/premiumIndex?symbol={symbol}", FAPI_BASES
    )
    perp_price = None
    if perp_data and isinstance(perp_data, dict):
        try:
            perp_price = float(perp_data.get("markPrice", 0))
        except (ValueError, TypeError):
            pass

    # Fetch spot price
    spot_data = _fetch_with_failover(
        f"/api/v3/ticker/price?symbol={symbol}", SPOT_BASES
    )
    spot_price = None
    if spot_data and isinstance(spot_data, dict):
        try:
            spot_price = float(spot_data.get("price", 0))
        except (ValueError, TypeError):
            pass

    # Bybit fallback for perp price
    if perp_price is None or perp_price == 0:
        try:
            bybit_data = _fetch_json(
                f"{BYBIT_BASE}/v5/market/tickers?category=linear&symbol={symbol}"
            )
            if bybit_data and bybit_data.get("retCode") == 0:
                tickers = bybit_data.get("result", {}).get("list", [])
                if tickers:
                    perp_price = float(tickers[0].get("markPrice", 0))
                    result["source"] = "bybit_perp"
        except Exception:
            pass

    # CoinGecko fallback for spot price
    if spot_price is None or spot_price == 0:
        _cg_ids = {
            "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum",
            "SOLUSDT": "solana", "BNBUSDT": "binancecoin",
        }
        cg_id = _cg_ids.get(symbol)
        if cg_id:
            cg_data = _fetch_json(
                f"{COINGECKO_BASE}/simple/price?ids={cg_id}&vs_currencies=usd"
            )
            if cg_data and cg_id in cg_data:
                spot_price = float(cg_data[cg_id].get("usd", 0))
                result["source"] = "coingecko_spot"

    if perp_price and spot_price and spot_price > 0:
        premium_pct = (perp_price - spot_price) / spot_price * 100
        result["value_pct"] = round(premium_pct, 4)
        result["perp_price"] = perp_price
        result["spot_price"] = spot_price
        if result["source"] == "none":
            result["source"] = "binance"

        if premium_pct > 0.3:
            result["signal"] = "BULLISH"
        elif premium_pct < -0.3:
            result["signal"] = "BEARISH"
        else:
            result["signal"] = "NEUTRAL"
    else:
        _log.warning("Cannot compute futures premium for %s (perp=%s, spot=%s)",
                      symbol, perp_price, spot_price)

    return result


# ---------------------------------------------------------------------------
# Signal 3: Price Momentum (EMA crossover on 1h candles)
# ---------------------------------------------------------------------------
def _compute_ema(prices: list[float], period: int) -> list[float]:
    """Compute EMA series from price list."""
    if not prices or period <= 0:
        return []
    k = 2.0 / (period + 1)
    ema = [prices[0]]
    for i in range(1, len(prices)):
        ema.append(prices[i] * k + ema[-1] * (1 - k))
    return ema


def _fetch_price_momentum(symbol: str = "BTCUSDT") -> dict:
    """Fetch last 20 1-hour candles and compute EMA(5) vs EMA(20) momentum.

    Returns: {signal: str, ema5: float, ema20: float, slope: float}
    EMA5 > EMA20 and rising = TRENDING_UP / BULLISH
    EMA5 < EMA20 and falling = TRENDING_DOWN / BEARISH
    Flat/crossed = RANGING / NEUTRAL
    """
    result = {
        "signal": "NEUTRAL", "ema5": 0.0, "ema20": 0.0,
        "slope": 0.0, "source": "none",
    }

    # Fetch 1h klines (need 20 candles)
    kline_data = _fetch_with_failover(
        f"/api/v3/klines?symbol={symbol}&interval=1h&limit=25", SPOT_BASES
    )

    if not kline_data or not isinstance(kline_data, list) or len(kline_data) < 20:
        # Bybit fallback
        try:
            bybit_data = _fetch_json(
                f"{BYBIT_BASE}/v5/market/kline?category=linear&symbol={symbol}"
                f"&interval=60&limit=25"
            )
            if bybit_data and bybit_data.get("retCode") == 0:
                raw = bybit_data.get("result", {}).get("list", [])
                # Bybit returns newest first; reverse and extract close price (index 4)
                kline_data = [[r[0], r[1], r[2], r[3], r[4]] for r in reversed(raw)]
                result["source"] = "bybit"
        except Exception:
            pass

    if not kline_data or len(kline_data) < 20:
        _log.warning("Insufficient kline data for momentum: %s", symbol)
        return result

    # Extract close prices (index 4 for Binance klines)
    try:
        closes = [float(c[4]) for c in kline_data[-25:]]
    except (IndexError, ValueError, TypeError):
        _log.warning("Bad kline format for %s", symbol)
        return result

    if len(closes) < 20:
        return result

    ema5 = _compute_ema(closes, 5)
    ema20 = _compute_ema(closes, 20)

    current_ema5 = ema5[-1]
    current_ema20 = ema20[-1]
    prev_ema5 = ema5[-3] if len(ema5) >= 3 else ema5[-1]

    # Slope of EMA5 over last 3 periods (normalized)
    slope = (current_ema5 - prev_ema5) / prev_ema5 * 100 if prev_ema5 else 0

    result["ema5"] = round(current_ema5, 2)
    result["ema20"] = round(current_ema20, 2)
    result["slope"] = round(slope, 4)
    if result["source"] == "none":
        result["source"] = "binance"

    if current_ema5 > current_ema20 and slope > 0.05:
        result["signal"] = "BULLISH"
    elif current_ema5 < current_ema20 and slope < -0.05:
        result["signal"] = "BEARISH"
    else:
        result["signal"] = "NEUTRAL"

    return result


# ---------------------------------------------------------------------------
# Ensemble: Combine 3 signals into regime
# ---------------------------------------------------------------------------
_SIGNAL_TO_SCORE = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}


# ---------------------------------------------------------------------------
# Fear & Greed Override: align regime with extreme sentiment
# ---------------------------------------------------------------------------
def _fetch_fear_greed_value() -> int | None:
    """Fetch current Fear & Greed index value (0-100). Returns None on failure."""
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.alternative.me/fng/?limit=1",
            headers={"User-Agent": "AlphaEngine/2.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        if data and isinstance(data.get("data"), list) and data["data"]:
            return int(data["data"][0]["value"])
    except Exception as e:
        _log.debug("Fear & Greed fetch failed: %s", e)
    return None


def apply_fgi_override(regime: str, fgi: int | None) -> tuple[str, str | None]:
    """Override regime when Fear & Greed is at extremes.

    Prevents dangerous misalignment where price regime says NEUTRAL/RANGING
    but sentiment is at extremes (e.g., FGI=11 Extreme Fear).

    Returns: (adjusted_regime, override_reason or None)

    Thresholds:
      FGI < 15 (Extreme Fear)  -> force BEAR regardless of price regime
      FGI > 85 (Extreme Greed) -> force BULL regardless of price regime
      FGI 15-25 -> if regime is neutral/choppy/ranging, downgrade to BEAR
      FGI 75-85 -> if regime is neutral/choppy/ranging, upgrade to BULL
    """
    if fgi is None:
        return regime, None

    neutral_regimes = {"CHOPPY", "RANGING", "NEUTRAL"}

    if fgi < 15:
        if regime not in ("BEAR", "STRONG_BEAR"):
            return "BEAR", f"FGI override: {fgi} (Extreme Fear) forced {regime}->BEAR"
    elif fgi > 85:
        if regime not in ("BULL", "STRONG_BULL"):
            return "BULL", f"FGI override: {fgi} (Extreme Greed) forced {regime}->BULL"
    elif fgi < 25 and regime in neutral_regimes:
        return "BEAR", f"FGI override: {fgi} (Fear) downgraded {regime}->BEAR"
    elif fgi > 75 and regime in neutral_regimes:
        return "BULL", f"FGI override: {fgi} (Greed) upgraded {regime}->BULL"

    return regime, None


def _combine_signals(funding: dict, premium: dict, momentum: dict) -> dict:
    """Combine 3 microstructure signals into a single regime classification.

    Scoring:
      +3 = STRONG_BULL (all bullish)
      +2 = BULL (2/3 bullish)
       0,+1,-1 = CHOPPY (mixed)
      -2 = BEAR (2/3 bearish)
      -3 = STRONG_BEAR (all bearish)
    """
    scores = {
        "funding": _SIGNAL_TO_SCORE.get(funding.get("signal", "NEUTRAL"), 0),
        "premium": _SIGNAL_TO_SCORE.get(premium.get("signal", "NEUTRAL"), 0),
        "momentum": _SIGNAL_TO_SCORE.get(momentum.get("signal", "NEUTRAL"), 0),
    }
    total = sum(scores.values())

    if total >= 3:
        regime = "STRONG_BULL"
        confidence = 0.95
    elif total == 2:
        regime = "BULL"
        confidence = 0.75
    elif total == -2:
        regime = "BEAR"
        confidence = 0.75
    elif total <= -3:
        regime = "STRONG_BEAR"
        confidence = 0.95
    elif total == 1:
        regime = "CHOPPY"
        confidence = 0.50
    elif total == -1:
        regime = "CHOPPY"
        confidence = 0.50
    else:
        regime = "RANGING"
        confidence = 0.60

    return {
        "regime": regime,
        "confidence": confidence,
        "score": total,
        "component_scores": scores,
    }


# ---------------------------------------------------------------------------
# Main API: get_fast_regime() and get_regime_for_symbol()
# ---------------------------------------------------------------------------
def get_fast_regime(symbol: str = "BTCUSDT", force_refresh: bool = False) -> dict:
    """Get fast microstructure regime for a symbol.

    Returns dict with:
        regime: str (STRONG_BULL, BULL, CHOPPY, RANGING, BEAR, STRONG_BEAR)
        confidence: float (0-1)
        components: dict with funding, premium, momentum details
        timestamp: ISO timestamp
        cache_age_seconds: how old the cached result is
        score: int (-3 to +3)
    """
    now = time.time()

    # Check cache (5 min TTL)
    if not force_refresh and symbol in _regime_cache:
        cached = _regime_cache[symbol]
        age = now - cached["_fetched_at"]
        if age < CACHE_TTL_SECONDS:
            result = dict(cached)
            result["cache_age_seconds"] = round(age, 1)
            result["cached"] = True
            return result

    # Fetch all 3 signals
    t0 = time.time()
    funding = _fetch_funding_rate(symbol)
    premium = _fetch_futures_premium(symbol)
    momentum = _fetch_price_momentum(symbol)
    fetch_time = time.time() - t0

    # Combine into regime
    ensemble = _combine_signals(funding, premium, momentum)

    # Apply Fear & Greed override for crypto symbols
    fgi_value = None
    fgi_override_reason = None
    if symbol.endswith("USDT"):
        fgi_value = _fetch_fear_greed_value()
        if fgi_value is not None:
            adjusted_regime, fgi_override_reason = apply_fgi_override(
                ensemble["regime"], fgi_value
            )
            if fgi_override_reason:
                _log.info("FGI override applied: %s", fgi_override_reason)
                print(f"  [FAST REGIME] {fgi_override_reason}")
                ensemble["regime"] = adjusted_regime
                ensemble["confidence"] = max(ensemble["confidence"], 0.70)

    result = {
        "regime": ensemble["regime"],
        "confidence": ensemble["confidence"],
        "score": ensemble["score"],
        "components": {
            "funding": funding,
            "premium": premium,
            "momentum": momentum,
        },
        "component_scores": ensemble["component_scores"],
        "fgi": fgi_value,
        "fgi_override": fgi_override_reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "fetch_time_ms": round(fetch_time * 1000, 1),
        "cache_age_seconds": 0,
        "cached": False,
        "_fetched_at": now,
    }

    # Update cache
    _regime_cache[symbol] = result

    # Persist to disk for other modules
    _persist_regime(result)

    print(f"  [FAST REGIME] {symbol}: {ensemble['regime']} "
          f"(score={ensemble['score']}, conf={ensemble['confidence']:.0%}) "
          f"funding={funding['signal']} premium={premium['signal']} "
          f"momentum={momentum['signal']} "
          f"fgi={fgi_value or '?'} [{fetch_time*1000:.0f}ms]")

    return result


def get_regime_for_symbol(symbol: str = "BTCUSDT") -> str:
    """Simple string regime for a symbol. Uses BTC as default reference.

    Returns: one of STRONG_BULL, BULL, CHOPPY, RANGING, BEAR, STRONG_BEAR
    """
    # For crypto symbols, use BTC regime as the reference unless symbol-specific
    # data is already cached
    if symbol in _regime_cache:
        cached = _regime_cache[symbol]
        age = time.time() - cached["_fetched_at"]
        if age < CACHE_TTL_SECONDS:
            return cached["regime"]

    # Try symbol-specific first for major coins
    _MAJOR_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"}
    if symbol in _MAJOR_SYMBOLS:
        result = get_fast_regime(symbol)
        return result["regime"]

    # Default: use BTC regime as market proxy
    result = get_fast_regime("BTCUSDT")
    return result["regime"]


# ---------------------------------------------------------------------------
# Persistence: save regime to disk for cross-module access
# ---------------------------------------------------------------------------
def _persist_regime(result: dict) -> None:
    """Save regime result to data/fast_regime.json for other modules."""
    try:
        path = DATA_DIR / "fast_regime.json"
        # Build a clean dict (no internal cache keys)
        clean = {k: v for k, v in result.items() if not k.startswith("_")}
        with open(path, "w") as f:
            json.dump(clean, f, indent=2)
    except Exception as e:
        _log.debug("Could not persist fast regime: %s", e)


def load_cached_regime() -> dict | None:
    """Load the last persisted regime from disk (for modules that import us)."""
    try:
        path = DATA_DIR / "fast_regime.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            # Check staleness
            ts = data.get("timestamp", "")
            if ts:
                from datetime import datetime as _dt
                fetched = _dt.fromisoformat(ts.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - fetched).total_seconds()
                data["cache_age_seconds"] = round(age, 1)
                if age > CACHE_TTL_SECONDS * 2:  # 10 min = stale warning
                    data["stale"] = True
            return data
    except Exception as e:
        _log.debug("Could not load cached regime: %s", e)
    return None


# ---------------------------------------------------------------------------
# Strategy routing helper
# ---------------------------------------------------------------------------
# Maps regime to which strategy types are allowed/blocked
REGIME_STRATEGY_ROUTING = {
    "STRONG_BULL": {
        "allow": ["trend_following", "momentum", "breakout", "mean_reversion"],
        "block": [],
    },
    "BULL": {
        "allow": ["trend_following", "momentum", "breakout", "mean_reversion"],
        "block": [],
    },
    "CHOPPY": {
        "allow": ["mean_reversion", "range", "scalp", "funding_carry"],
        "block": ["trend_following", "breakout"],
    },
    "RANGING": {
        "allow": ["mean_reversion", "range", "scalp", "funding_carry", "statistical"],
        "block": ["trend_following", "breakout", "momentum"],
    },
    "BEAR": {
        "allow": ["mean_reversion", "short", "hedge", "funding_carry"],
        "block": ["momentum", "breakout"],
    },
    "STRONG_BEAR": {
        "allow": ["short", "hedge", "funding_carry"],
        "block": ["momentum", "breakout", "trend_following"],
    },
}

# Map strategy names to types for routing
_STRATEGY_TYPE_MAP = {
    # Trend following
    "ema_crossover": "trend_following",
    "macd_divergence": "trend_following",
    "trend_following": "trend_following",
    "multi_timeframe_ema_stack": "trend_following",
    "supertrend": "trend_following",
    # Momentum
    "rsi_oversold_bounce": "momentum",
    "momentum": "momentum",
    "cross_sectional_momentum": "momentum",
    "relative_strength": "momentum",
    # Breakout
    "breakout": "breakout",
    "range_breakout": "breakout",
    "session_breakout": "breakout",
    "atr_volatility_breakout": "breakout",
    "break_of_structure": "breakout",
    # Mean reversion
    "mean_reversion": "mean_reversion",
    "bollinger_mean_reversion": "mean_reversion",
    "rsi_capitulation": "mean_reversion",
    "swing_failure_pattern": "mean_reversion",
    # Carry / funding
    "funding_rate_carry": "funding_carry",
    "funding_carry": "funding_carry",
    "funding_rate_arbitrage": "funding_carry",
    "oi_funding_squeeze": "funding_carry",
    # Short
    "short_squeeze": "short",
    "liquidation_cascade": "short",
    # Quant Stack (Mercury 2)
    "kama_atr_trend": "trend_following",
    "kama_regime_adaptive": "trend_following",
    "kama_mean_reversion": "mean_reversion",
}


def is_strategy_allowed(strategy_name: str, regime: str) -> bool:
    """Check if a strategy is allowed in the current regime.

    Returns True if allowed (or if strategy/regime not in routing table).
    Conservative: unknown strategies are always allowed.
    """
    routing = REGIME_STRATEGY_ROUTING.get(regime)
    if not routing:
        return True

    strategy_type = _STRATEGY_TYPE_MAP.get(strategy_name)
    if not strategy_type:
        return True  # Unknown strategy type = always allowed

    blocked = routing.get("block", [])
    return strategy_type not in blocked


# ---------------------------------------------------------------------------
# Encode regime as numeric for ML features
# ---------------------------------------------------------------------------
_REGIME_ENCODING = {
    "STRONG_BULL": 2,
    "BULL": 1,
    "CHOPPY": 0,
    "RANGING": 0,
    "BEAR": -1,
    "STRONG_BEAR": -2,
}


def regime_to_numeric(regime: str) -> int:
    """Convert regime string to numeric encoding for ML models."""
    return _REGIME_ENCODING.get(regime, 0)


# ---------------------------------------------------------------------------
# CLI: run standalone for testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("FAST REGIME DETECTOR -- Microstructure Ensemble")
    print("=" * 60)

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    for sym in symbols:
        result = get_fast_regime(sym, force_refresh=True)
        print(f"\n{sym}:")
        print(f"  Regime: {result['regime']} (confidence: {result['confidence']:.0%})")
        print(f"  Score: {result['score']}")
        print(f"  Funding: {result['components']['funding']['signal']} "
              f"({result['components']['funding']['value']:.4f}%)")
        print(f"  Premium: {result['components']['premium']['signal']} "
              f"({result['components']['premium']['value_pct']:.4f}%)")
        print(f"  Momentum: {result['components']['momentum']['signal']} "
              f"(slope={result['components']['momentum']['slope']:.4f})")
        print(f"  Fetch time: {result['fetch_time_ms']:.0f}ms")
