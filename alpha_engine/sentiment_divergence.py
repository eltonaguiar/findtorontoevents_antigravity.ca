"""
ALPHA_ENGINE -- Sentiment-Price Divergence Detector
===================================================
Detects divergences between price trend and sentiment trend.

BULLISH divergence: price making lower lows, sentiment making higher lows
BEARISH divergence: price making higher highs, sentiment making lower highs

Research: Bouri et al. (2022) -- sentiment divergences precede 60-70% of major
crypto reversals. Baker & Wurgler (2006) -- investor sentiment predicts cross-
section of returns, especially at extremes.

Data sources:
  - Fear & Greed Index (alternative.me) -- primary sentiment
  - LunarCrush Galaxy Score (CoinGecko composite) -- confirmation
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    from lunarcrush_signal import get_lunarcrush_score, _get_fear_greed
except ImportError:
    get_lunarcrush_score = None
    _get_fear_greed = None

try:
    from cryptopanic_feargreed import fetch_fear_greed
except ImportError:
    fetch_fear_greed = None


def _slope(values: list[float]) -> float:
    """Compute OLS slope of values over their indices."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den > 0 else 0.0


def _std(values: list[float]) -> float:
    """Standard deviation of values."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return math.sqrt(var) if var > 0 else 0.0


def _get_fg_history() -> list[float]:
    """Get last 7 days of Fear & Greed values."""
    if fetch_fear_greed is not None:
        fg = fetch_fear_greed()
        history = fg.get("history", [])
        return [h.get("value", 50) for h in history[:7]]
    if _get_fear_greed is not None:
        return [_get_fear_greed()]
    return [50.0]


def sentiment_price_divergence(data: dict, context: dict | None = None) -> list[dict]:
    """
    Detect sentiment-price divergences for crypto symbols.

    Compares 7-day price slope vs 7-day sentiment slope.
    Signal fires when slopes diverge by >1 std dev of recent price moves.
    """
    signals = []
    LOOKBACK = 7

    fg_values = _get_fg_history()
    fg_slope = _slope(fg_values) if len(fg_values) >= 3 else 0.0

    symbols = [s for s in data.keys() if s.endswith("-USD")]

    for symbol in symbols:
        try:
            df = data[symbol]
            if df is None or len(df) < 14:
                continue

            closes = [float(v) for v in df["Close"].iloc[-LOOKBACK:]]
            if len(closes) < LOOKBACK or closes[-1] <= 0:
                continue

            price_slope = _slope(closes)
            price_std = _std(closes)
            if price_std == 0:
                continue

            # Normalize slopes to comparable scale
            norm_price = price_slope / price_std
            norm_sent = fg_slope / max(_std(fg_values), 1.0)

            # Galaxy score as confirmation (optional)
            galaxy_conf = 0.0
            galaxy_val = None
            if get_lunarcrush_score is not None:
                lc = get_lunarcrush_score(symbol)
                if lc:
                    galaxy_val = lc["galaxy_score"]
                    # Galaxy > 50 while price falling = bullish confirmation
                    if galaxy_val > 50 and norm_price < 0:
                        galaxy_conf = 0.10
                    # Galaxy < 50 while price rising = bearish confirmation
                    elif galaxy_val < 50 and norm_price > 0:
                        galaxy_conf = 0.10

            divergence = norm_sent - norm_price
            abs_div = abs(divergence)

            # Need divergence > 1 std dev to trigger
            if abs_div < 1.0:
                continue

            price = closes[-1]
            atr_proxy = price_std * 1.5  # rough ATR proxy from close std

            if divergence > 1.0 and norm_price < 0 and norm_sent > 0:
                # BULLISH: price falling, sentiment rising
                direction = "LONG"
                signal_type = "BUY"
                tp = round(price + atr_proxy * 2.5, 2) if price > 1 else round(price + atr_proxy * 2.5, 8)
                sl = round(price - atr_proxy * 1.2, 2) if price > 1 else round(price - atr_proxy * 1.2, 8)
                label = "BULLISH divergence"

            elif divergence < -1.0 and norm_price > 0 and norm_sent < 0:
                # BEARISH: price rising, sentiment falling
                direction = "SHORT"
                signal_type = "SELL"
                tp = round(price - atr_proxy * 2.5, 2) if price > 1 else round(price - atr_proxy * 2.5, 8)
                sl = round(price + atr_proxy * 1.2, 2) if price > 1 else round(price + atr_proxy * 1.2, 8)
                label = "BEARISH divergence"
            else:
                continue

            # Confidence: magnitude normalized to 0-1, capped at 0.80
            confidence = min(0.80, 0.45 + (abs_div - 1.0) * 0.15 + galaxy_conf)

            rr = abs(tp - price) / abs(sl - price) if abs(sl - price) > 0 else 2.0

            fg_now = fg_values[0] if fg_values else 50
            galaxy_str = f", Galaxy={galaxy_val:.0f}" if galaxy_val else ""

            signals.append({
                "strategy": "sentiment_price_divergence",
                "symbol": symbol,
                "category": "crypto",
                "signal_type": signal_type,
                "direction": direction,
                "entry_price": round(price, 2) if price > 1 else round(price, 8),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"{label}: 7d price slope={norm_price:+.2f} vs "
                    f"sentiment slope={norm_sent:+.2f} (div={abs_div:.2f}σ). "
                    f"F&G={fg_now}{galaxy_str}. "
                    f"Bouri et al. (2022): precedes 60-70% of reversals."
                ),
                "timeframe": "1d",
                "extra": {
                    "divergence_sigma": round(abs_div, 2),
                    "price_slope_norm": round(norm_price, 3),
                    "sentiment_slope_norm": round(norm_sent, 3),
                    "fear_greed": fg_now,
                    "galaxy_score": galaxy_val,
                    "reference": "Bouri et al. (2022), Baker & Wurgler (2006)",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        except Exception as e:
            logger.debug("sentiment_divergence %s: %s", symbol, e)
            continue

    return signals


DIVERGENCE_STRATEGIES: dict[str, callable] = {
    "sentiment_price_divergence": sentiment_price_divergence,
}
