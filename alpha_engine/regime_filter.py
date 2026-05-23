"""
ALPHA_ENGINE -- Regime Filter: ADX + BB + Hurst + Choppiness
=============================================================
Classifies current market regime for any symbol as:
  TRENDING       -- ADX>25, Hurst>0.55, low choppiness  → breakout strategies
  CHOPPY         -- ADX<20, Hurst~0.5, high choppiness  → mean-reversion only
  MEAN_REVERTING -- Hurst<0.45, contracting BB           → RSI bounce strategies

Key finding driving this:
  - Quick trades (<1h) have 14.6% WR -- choppy regime kills them
  - Trades held >3 days have 53.3% WR -- trending regime rewards patience
  - 62% of LONGs lose in current choppy conditions

Usage:
  from alpha_engine.regime_filter import get_regime, should_enter
  regime = get_regime("BTCUSDT")
  if should_enter("BTCUSDT", "breakout"):
      # place the trade
"""
from __future__ import annotations

import json
import logging
import math
import sys
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

# -- API endpoints with 3+ fallback chain ------------------------------

_BINANCE_KLINE_BASES = [
    "https://api.binance.com/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
    "https://api2.binance.com/api/v3/klines",
]

_COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# -- Regime constants --------------------------------------------------

REGIME_TRENDING = "TRENDING"
REGIME_CHOPPY = "CHOPPY"
REGIME_MEAN_REVERTING = "MEAN_REVERTING"

# Strategy type → compatible regimes
_STRATEGY_REGIME_MAP = {
    "breakout":       {REGIME_TRENDING},
    "momentum":       {REGIME_TRENDING},
    "trend_follow":   {REGIME_TRENDING},
    "mean_reversion": {REGIME_CHOPPY, REGIME_MEAN_REVERTING},
    "rsi_bounce":     {REGIME_MEAN_REVERTING, REGIME_CHOPPY},
    "scalp":          {REGIME_CHOPPY},            # only in tight ranges
    "swing":          {REGIME_TRENDING, REGIME_MEAN_REVERTING},
    "carry":          {REGIME_TRENDING, REGIME_CHOPPY, REGIME_MEAN_REVERTING},  # always OK
}


# -- Data fetching -----------------------------------------------------

def _fetch_json(url: str, timeout: int = 10) -> Optional[list | dict]:
    """Fetch JSON with basic error handling."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaRegimeFilter/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug(f"Fetch failed for {url}: {e}")
        return None


def _fetch_klines(symbol: str, interval: str = "4h", limit: int = 50) -> Optional[list]:
    """
    Fetch OHLCV klines with Binance 3-mirror fallback + CoinGecko fallback.
    Returns list of [open, high, low, close, volume] floats.
    """
    # Try Binance mirrors
    for base in _BINANCE_KLINE_BASES:
        url = f"{base}?symbol={symbol}&interval={interval}&limit={limit}"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 10:
            # Binance klines: [openTime, open, high, low, close, volume, ...]
            return [
                [float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])]
                for k in data
            ]

    # CoinGecko fallback -- map symbol and interval to CG params
    cg_id = _symbol_to_coingecko(symbol)
    if cg_id:
        # CoinGecko market_chart: days param approximation
        days_map = {"15m": 1, "1h": 2, "4h": 10, "1d": 50}
        days = days_map.get(interval, 10)
        url = f"{_COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 10:
            # CG OHLC: [timestamp, open, high, low, close]
            return [
                [float(k[1]), float(k[2]), float(k[3]), float(k[4]), 0.0]
                for k in data
            ]

    logger.warning(f"All API sources failed for {symbol} {interval}")
    return None


def _symbol_to_coingecko(symbol: str) -> Optional[str]:
    """Map Binance symbol to CoinGecko ID for common coins."""
    mapping = {
        "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "BNBUSDT": "binancecoin",
        "SOLUSDT": "solana", "ADAUSDT": "cardano", "DOGEUSDT": "dogecoin",
        "XRPUSDT": "ripple", "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot",
        "LINKUSDT": "chainlink", "MATICUSDT": "matic-network", "LTCUSDT": "litecoin",
        "ATOMUSDT": "cosmos", "NEARUSDT": "near", "ARBUSDT": "arbitrum",
        "OPUSDT": "optimism", "APTUSDT": "aptos", "SUIUSDT": "sui",
    }
    return mapping.get(symbol.upper())


# -- Technical Indicators (pure numpy-free math) ----------------------

def _true_range(highs: list, lows: list, closes: list) -> list:
    """Compute True Range series."""
    tr = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))
    return tr


def _wilder_smooth(values: list, period: int) -> list:
    """Wilder's smoothing (exponential with alpha = 1/period)."""
    if len(values) < period:
        return []
    result = [sum(values[:period]) / period]
    for i in range(period, len(values)):
        result.append((result[-1] * (period - 1) + values[i]) / period)
    return result


def compute_adx(highs: list, lows: list, closes: list, period: int = 14) -> float:
    """
    Compute ADX (Average Directional Index).
    >25 = trending, <20 = choppy.
    Returns last ADX value or 20.0 (neutral) on failure.
    """
    if len(highs) < period * 2 + 1:
        return 20.0

    # +DM and -DM
    plus_dm = []
    minus_dm = []
    for i in range(1, len(highs)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if (up > down and up > 0) else 0.0)
        minus_dm.append(down if (down > up and down > 0) else 0.0)

    tr = _true_range(highs[1:], lows[1:], closes[1:])

    # Wilder smooth all three
    smooth_tr = _wilder_smooth(tr, period)
    smooth_plus = _wilder_smooth(plus_dm, period)
    smooth_minus = _wilder_smooth(minus_dm, period)

    if not smooth_tr or not smooth_plus or not smooth_minus:
        return 20.0

    n = min(len(smooth_tr), len(smooth_plus), len(smooth_minus))

    # +DI and -DI
    dx_values = []
    for i in range(n):
        if smooth_tr[i] == 0:
            continue
        plus_di = 100 * smooth_plus[i] / smooth_tr[i]
        minus_di = 100 * smooth_minus[i] / smooth_tr[i]
        di_sum = plus_di + minus_di
        if di_sum > 0:
            dx_values.append(100 * abs(plus_di - minus_di) / di_sum)

    if len(dx_values) < period:
        return 20.0

    # ADX = Wilder smooth of DX
    adx_smooth = _wilder_smooth(dx_values, period)
    return adx_smooth[-1] if adx_smooth else 20.0


def compute_bb_width(closes: list, period: int = 20) -> tuple[float, float]:
    """
    Compute Bollinger Band Width (current and average).
    Returns (current_width, avg_width).
    Expanding if current > avg, contracting if current < avg.
    """
    if len(closes) < period + 5:
        return (0.05, 0.05)

    widths = []
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1: i + 1]
        sma = sum(window) / period
        if sma == 0:
            continue
        variance = sum((x - sma) ** 2 for x in window) / period
        std = math.sqrt(variance)
        width = (4 * std) / sma  # 2 std bands each side, normalized
        widths.append(width)

    if not widths:
        return (0.05, 0.05)

    current = widths[-1]
    avg = sum(widths) / len(widths)
    return (current, avg)


def compute_hurst(closes: list, max_lag: int = 20) -> float:
    """
    Simplified Hurst exponent via R/S (Rescaled Range) method.
    >0.55 = trending (persistent), <0.45 = mean-reverting, 0.45-0.55 = random walk.
    """
    if len(closes) < max_lag * 2:
        return 0.50  # neutral

    # Compute log returns
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0 and closes[i] > 0:
            returns.append(math.log(closes[i] / closes[i - 1]))
        else:
            returns.append(0.0)

    if len(returns) < max_lag * 2:
        return 0.50

    # R/S analysis for various lag sizes
    rs_log = []
    lag_log = []

    for lag in range(10, max_lag + 1):
        rs_values = []
        for start in range(0, len(returns) - lag, lag):
            chunk = returns[start: start + lag]
            mean_c = sum(chunk) / lag
            # Cumulative deviations
            cumdev = []
            running = 0.0
            for r in chunk:
                running += (r - mean_c)
                cumdev.append(running)
            R = max(cumdev) - min(cumdev)
            S = math.sqrt(sum((r - mean_c) ** 2 for r in chunk) / lag)
            if S > 0:
                rs_values.append(R / S)

        if rs_values:
            avg_rs = sum(rs_values) / len(rs_values)
            if avg_rs > 0:
                rs_log.append(math.log(avg_rs))
                lag_log.append(math.log(lag))

    if len(rs_log) < 3:
        return 0.50

    # Linear regression: log(R/S) = H * log(n) + c
    n = len(rs_log)
    sum_x = sum(lag_log)
    sum_y = sum(rs_log)
    sum_xy = sum(x * y for x, y in zip(lag_log, rs_log))
    sum_xx = sum(x * x for x in lag_log)

    denom = n * sum_xx - sum_x * sum_x
    if abs(denom) < 1e-12:
        return 0.50

    H = (n * sum_xy - sum_x * sum_y) / denom
    return max(0.0, min(1.0, H))


def compute_choppiness(highs: list, lows: list, closes: list, period: int = 14) -> float:
    """
    Choppiness Index (0-100). High values (>60) = choppy, low (<40) = trending.
    CI = 100 * LOG10(SUM(ATR,n) / (highest_high - lowest_low)) / LOG10(n)
    """
    if len(highs) < period + 1:
        return 50.0

    tr = _true_range(highs, lows, closes)
    recent_tr = tr[-period:]
    recent_highs = highs[-period:]
    recent_lows = lows[-period:]

    atr_sum = sum(recent_tr)
    hh = max(recent_highs)
    ll = min(recent_lows)
    hl_range = hh - ll

    if hl_range <= 0 or atr_sum <= 0:
        return 50.0

    try:
        ci = 100.0 * math.log10(atr_sum / hl_range) / math.log10(period)
    except (ValueError, ZeroDivisionError):
        return 50.0

    return max(0.0, min(100.0, ci))


# -- Regime Classification ---------------------------------------------

def get_regime(symbol: str = "BTCUSDT") -> dict:
    """
    Classify current market regime for a symbol.

    Returns:
        {
            "symbol": str,
            "regime": "TRENDING" | "CHOPPY" | "MEAN_REVERTING",
            "confidence": float (0-1),
            "adx": float,
            "bb_width": float,
            "bb_expanding": bool,
            "hurst": float,
            "choppiness": float,
            "recommended_strategies": list[str],
            "avoid_strategies": list[str],
        }
    """
    result = {
        "symbol": symbol,
        "regime": REGIME_CHOPPY,  # safe default
        "confidence": 0.3,
        "adx": 20.0,
        "bb_width": 0.05,
        "bb_expanding": False,
        "hurst": 0.50,
        "choppiness": 50.0,
        "recommended_strategies": ["mean_reversion", "rsi_bounce"],
        "avoid_strategies": ["breakout", "momentum"],
    }

    klines = _fetch_klines(symbol, interval="4h", limit=55)
    if not klines or len(klines) < 30:
        logger.warning(f"Insufficient data for {symbol}, returning neutral CHOPPY")
        return result

    opens = [k[0] for k in klines]
    highs = [k[1] for k in klines]
    lows = [k[2] for k in klines]
    closes = [k[3] for k in klines]
    volumes = [k[4] for k in klines]

    # Compute indicators
    adx = compute_adx(highs, lows, closes, period=14)
    bb_current, bb_avg = compute_bb_width(closes, period=20)
    hurst = compute_hurst(closes, max_lag=20)
    chop = compute_choppiness(highs, lows, closes, period=14)

    result["adx"] = round(adx, 2)
    result["bb_width"] = round(bb_current, 4)
    result["bb_expanding"] = bb_current > bb_avg * 1.1
    result["hurst"] = round(hurst, 3)
    result["choppiness"] = round(chop, 2)

    # Score each regime hypothesis (0-1)
    trending_score = 0.0
    choppy_score = 0.0
    mr_score = 0.0

    # ADX contribution (weight: 30%)
    if adx > 30:
        trending_score += 0.30
    elif adx > 25:
        trending_score += 0.20
        mr_score += 0.05
    elif adx < 18:
        choppy_score += 0.25
        mr_score += 0.10
    elif adx < 22:
        choppy_score += 0.15
        mr_score += 0.10
    else:
        trending_score += 0.10
        choppy_score += 0.10
        mr_score += 0.10

    # Hurst contribution (weight: 30%)
    if hurst > 0.60:
        trending_score += 0.30
    elif hurst > 0.55:
        trending_score += 0.20
    elif hurst < 0.40:
        mr_score += 0.30
    elif hurst < 0.45:
        mr_score += 0.20
        choppy_score += 0.05
    else:
        # Random walk zone (0.45-0.55)
        choppy_score += 0.15
        trending_score += 0.05
        mr_score += 0.05

    # BB Width contribution (weight: 20%)
    if bb_current > bb_avg * 1.3:
        trending_score += 0.20  # expansion = breakout
    elif bb_current < bb_avg * 0.7:
        choppy_score += 0.10
        mr_score += 0.10       # squeeze = mean reversion potential
    else:
        choppy_score += 0.10
        trending_score += 0.05

    # Choppiness contribution (weight: 20%)
    if chop > 65:
        choppy_score += 0.20
    elif chop > 55:
        choppy_score += 0.12
        mr_score += 0.05
    elif chop < 35:
        trending_score += 0.20
    elif chop < 45:
        trending_score += 0.12
    else:
        choppy_score += 0.08
        trending_score += 0.05
        mr_score += 0.05

    # Determine regime
    scores = {
        REGIME_TRENDING: trending_score,
        REGIME_CHOPPY: choppy_score,
        REGIME_MEAN_REVERTING: mr_score,
    }
    regime = max(scores, key=scores.get)
    confidence = scores[regime] / max(sum(scores.values()), 0.01)

    result["regime"] = regime
    result["confidence"] = round(confidence, 2)

    # Set strategy recommendations
    if regime == REGIME_TRENDING:
        result["recommended_strategies"] = ["breakout", "momentum", "trend_follow", "swing"]
        result["avoid_strategies"] = ["scalp", "mean_reversion"]
    elif regime == REGIME_CHOPPY:
        result["recommended_strategies"] = ["mean_reversion", "rsi_bounce", "scalp", "carry"]
        result["avoid_strategies"] = ["breakout", "momentum", "trend_follow"]
    else:  # MEAN_REVERTING
        result["recommended_strategies"] = ["mean_reversion", "rsi_bounce", "swing"]
        result["avoid_strategies"] = ["breakout", "momentum"]

    return result


def should_enter(symbol: str, strategy_type: str) -> bool:
    """
    Gate function: should we enter a trade given the current regime?

    Args:
        symbol: Trading pair (e.g. "BTCUSDT")
        strategy_type: One of "breakout", "momentum", "mean_reversion",
                       "rsi_bounce", "scalp", "swing", "trend_follow", "carry"

    Returns:
        True if the strategy type is compatible with the current regime.
    """
    strategy_type = strategy_type.lower().strip()

    # If strategy type not mapped, allow by default (don't block unknown strategies)
    if strategy_type not in _STRATEGY_REGIME_MAP:
        logger.debug(f"Unknown strategy type '{strategy_type}', allowing by default")
        return True

    regime = get_regime(symbol)
    compatible = _STRATEGY_REGIME_MAP[strategy_type]

    allowed = regime["regime"] in compatible
    if not allowed:
        logger.info(
            f"REGIME GATE: Blocking {strategy_type} on {symbol} -- "
            f"regime={regime['regime']} (confidence={regime['confidence']}), "
            f"compatible regimes={compatible}"
        )
    return allowed


# -- Standalone execution ----------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]

    print("=" * 70)
    print("ALPHA ENGINE -- Regime Filter v1.0")
    print("=" * 70)

    for sym in symbols:
        r = get_regime(sym)
        print(f"\n{'-' * 50}")
        print(f"  {r['symbol']:12s}  REGIME: {r['regime']}")
        print(f"  {'':12s}  Confidence: {r['confidence']:.0%}")
        print(f"  {'':12s}  ADX={r['adx']:.1f}  Hurst={r['hurst']:.3f}  "
              f"Choppiness={r['choppiness']:.1f}  BB={r['bb_width']:.4f} "
              f"({'expanding' if r['bb_expanding'] else 'contracting'})")
        print(f"  {'':12s}  Recommended: {', '.join(r['recommended_strategies'])}")
        print(f"  {'':12s}  Avoid: {', '.join(r['avoid_strategies'])}")

    print(f"\n{'-' * 50}")
    print("\nGating examples:")
    for stype in ["breakout", "mean_reversion", "momentum", "rsi_bounce"]:
        ok = should_enter("BTCUSDT", stype)
        print(f"  should_enter('BTCUSDT', '{stype}') = {ok}")

    print("\nDone.")
