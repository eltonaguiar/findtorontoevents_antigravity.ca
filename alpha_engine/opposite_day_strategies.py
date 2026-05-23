"""
ALPHA_ENGINE -- Opposite Day Derived Strategies
================================================
5 strategies derived from the Opposite Day paper-trade experiment.

Empirical observation: flipping crowd consensus picks showed 8/8 short
positions profitable within 1 hour. Analysis identified key factors:
(1) bearish macro regime, (2) overbought technicals, (3) tight TP/SL,
(4) cluster overbought conditions, (5) crowd sentiment extremes.

Each strategy codifies one of these edges.

Strategy 1: overbought_reversal_short -- RSI>70 + bearish candle reversal
Strategy 2: macro_regime_short_filter -- Short only when BTC < 30d SMA
Strategy 3: crowd_contrarian_timer   -- Fade 5+ crowd consensus, 4h hold
Strategy 4: cluster_short_momentum   -- 6+/10 cryptos overbought → short all
Strategy 5: news_sentiment_contrarian -- F&G extremes contrarian
"""

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from config import CRYPTO_SYMBOLS
from indicators import rsi, sma, atr, bollinger_bands, macd, volume_ratio

log = logging.getLogger(__name__)

# -- Shared helpers (match crypto_strategies.py interface) ------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    return CRYPTO_SYMBOLS.get(symbol, {}).get("cat", "crypto")


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


# Top 10 crypto for cluster strategies
TOP_10_CRYPTO = [
    "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD",
    "DOGE-USD", "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
]

# Predictions data path
PREDICTIONS_PATH = Path(__file__).parent.parent / "predictions" / "data" / "active_predictions.json"


# =========================================================================
# STRATEGY 1: Overbought Reversal Short
# =========================================================================
# Short overbought assets with bearish candle confirmation.
# Edge: RSI > 70 + price above SMA(20) + bearish candle = reversal imminent.
# Tight TP/SL mimics the Opposite Day distances that produced 8/8 wins.
#
# References:
# - Wilder (1978): RSI > 70 = overbought
# - Bollinger (2001): price above upper band = extended
# - Opposite Day experiment (2026-03-04): tight TP/SL captures quick reversals

def overbought_reversal_short(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Short overbought assets when RSI>70, above SMA(20), bearish candle."""
    signals = []

    for symbol, info in CRYPTO_SYMBOLS.items():
        if info.get("cat") != "crypto":
            continue
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        opn = df["Open"]

        rsi_val = float(rsi(close, 14).iloc[-1])
        sma_20 = float(sma(close, 20).iloc[-1])
        price = float(close.iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])

        # Entry: RSI > 70 AND price > SMA(20) AND bearish candle
        if rsi_val <= 70 or price <= sma_20:
            continue
        if float(close.iloc[-1]) >= float(opn.iloc[-1]):
            continue  # Not a bearish candle

        # TP/SL: tight, ATR-based (SHORT direction)
        tp = _smart_round(price - atr_val * 1.5)
        sl = _smart_round(price + atr_val * 1.0)

        # Confidence: base 0.65, boost for extra confirmation
        confidence = 0.65
        bb = bollinger_bands(close, 20, 2.0)
        if price > float(bb["upper"].iloc[-1]):
            confidence += 0.1  # Above BB upper band
        vol = volume_ratio(df["Volume"], 20)
        if float(vol.iloc[-1]) < 0.8:
            confidence += 0.1  # Declining volume on push = exhaustion
        confidence = min(confidence, 0.90)

        rr = abs(price - tp) / abs(sl - price) if abs(sl - price) > 0 else 0

        signals.append({
            "strategy": "overbought_reversal_short",
            "symbol": symbol,
            "category": _get_category(symbol),
            "signal_type": "SELL",
            "direction": "SHORT",
            "entry_price": _smart_round(price),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(confidence, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Overbought reversal: RSI={rsi_val:.0f}>70, "
                f"price {price:.2f} > SMA20 {sma_20:.2f}, bearish candle"
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "atr_at_entry": round(atr_val, 4),
            "volume_ratio": round(float(vol.iloc[-1]), 2),
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# STRATEGY 2: Macro Regime Short Filter
# =========================================================================
# Only short when BTC is in a bearish regime (below 30-day SMA).
# Edge: When the dominant trend is bearish, filtered shorts cluster as
# winners -- exactly what the Opposite Day experiment showed.
#
# References:
# - Mebane Faber (2007): 10-month SMA trend filter
# - Opposite Day analysis: "market was down-trend for 2-3 days"

def macro_regime_short_filter(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Short top crypto when BTC is below its 30-day SMA (bearish regime)."""
    signals = []

    # Check BTC regime first
    btc_df = data.get("BTC-USD")
    if btc_df is None or len(btc_df) < 50:
        return signals

    btc_close = btc_df["Close"]
    btc_price = float(btc_close.iloc[-1])
    btc_sma30 = float(sma(btc_close, 30).iloc[-1])
    btc_sma50 = float(sma(btc_close, 50).iloc[-1])

    # Gate: BTC must be below 30d SMA (bearish regime)
    if btc_price >= btc_sma30:
        return signals

    for symbol in TOP_10_CRYPTO:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        price = float(close.iloc[-1])

        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val <= 60:
            continue  # Only short when RSI is elevated

        # MACD bearish crossover check
        macd_data = macd(close, 12, 26, 9)
        macd_line = macd_data["macd"]
        sig_line = macd_data["signal"]
        if float(macd_line.iloc[-1]) >= float(sig_line.iloc[-1]):
            continue  # MACD not bearish

        atr_val = float(atr(high, low, close, 14).iloc[-1])
        # Use category defaults: -8% SL, +8% TP (conservative for regime play)
        tp = _smart_round(price * 0.92)  # 8% below
        sl = _smart_round(price * 1.08)  # 8% above

        confidence = 0.70
        if btc_price < btc_sma50:
            confidence += 0.10  # Deeper bearish confirmation

        rr = abs(price - tp) / abs(sl - price) if abs(sl - price) > 0 else 0

        signals.append({
            "strategy": "macro_regime_short_filter",
            "symbol": symbol,
            "category": _get_category(symbol),
            "signal_type": "SELL",
            "direction": "SHORT",
            "entry_price": _smart_round(price),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(confidence, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Bearish regime: BTC {btc_price:.0f} < SMA30 {btc_sma30:.0f}, "
                f"{symbol} RSI={rsi_val:.0f}>60, MACD bearish cross"
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "atr_at_entry": round(atr_val, 4),
            "timestamp": _now_iso(),
            "extra": {
                "btc_price": round(btc_price, 2),
                "btc_sma30": round(btc_sma30, 2),
                "btc_below_sma50": btc_price < btc_sma50,
            },
        })

    return signals


# =========================================================================
# STRATEGY 3: Crowd Contrarian Timer
# =========================================================================
# Fade crowd consensus when 5+ predictors agree on same direction.
# Edge: Opposite Day showed that flipping crowd picks went from red to
# green at ~1 hour mark. This is a quick scalp (2% TP, 3% SL, 4h hold).
#
# Reads: predictions/data/active_predictions.json
# When 5+ predictors all say LONG on same symbol → go SHORT (and vice versa)

def crowd_contrarian_timer(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Fade crowd consensus when 5+ predictors agree on same symbol."""
    signals = []

    if not PREDICTIONS_PATH.is_file():
        return signals

    try:
        predictions = json.loads(PREDICTIONS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return signals

    if not isinstance(predictions, list):
        return signals

    # Count consensus per symbol+direction
    consensus: dict[str, Counter] = {}
    for p in predictions:
        sym = p.get("symbol", "")
        direction = p.get("direction", "").upper()
        if not sym or direction not in ("LONG", "SHORT"):
            continue
        if sym not in consensus:
            consensus[sym] = Counter()
        consensus[sym][direction] += 1

    for sym, counts in consensus.items():
        for direction, count in counts.items():
            if count < 5:
                continue

            # Exclude SUI (insufficient data)
            if "SUI" in sym.upper():
                continue

            # Find the corresponding yfinance symbol in data
            yf_sym = None
            for s in data:
                if sym.replace("USDT", "-USD").upper() == s.upper() or sym.upper() in s.upper():
                    yf_sym = s
                    break
            if yf_sym is None:
                # Try direct match
                for s in data:
                    base = sym.replace("USDT", "").replace("USD", "").replace("-", "")
                    if base in s.replace("-", "").replace("USD", ""):
                        yf_sym = s
                        break
            if yf_sym is None:
                continue

            df = data.get(yf_sym)
            if df is None or len(df) < 5:
                continue

            price = float(df["Close"].iloc[-1])

            # Opposite direction
            opp_dir = "SHORT" if direction == "LONG" else "LONG"
            opp_signal = "SELL" if direction == "LONG" else "BUY"

            # Quick scalp: 2% TP, 3% SL
            if opp_dir == "SHORT":
                tp = _smart_round(price * 0.98)
                sl = _smart_round(price * 1.03)
            else:
                tp = _smart_round(price * 1.02)
                sl = _smart_round(price * 0.97)

            # Confidence scales with consensus strength
            confidence = min(0.60 + 0.05 * (count - 5), 0.90)

            rr = abs(price - tp) / abs(sl - price) if abs(sl - price) > 0 else 0

            signals.append({
                "strategy": "crowd_contrarian_timer",
                "symbol": yf_sym,
                "category": _get_category(yf_sym),
                "signal_type": opp_signal,
                "direction": opp_dir,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Crowd contrarian: {count} predictors agree {direction} on {sym}, "
                    f"fading to {opp_dir} (4h scalp)"
                ),
                "timeframe": "4h",
                "timestamp": _now_iso(),
                "extra": {
                    "crowd_direction": direction,
                    "crowd_count": count,
                    "auto_expire_hours": 4,
                },
            })

    return signals


# =========================================================================
# STRATEGY 4: Cluster Short Momentum
# =========================================================================
# When 6+ of top 10 cryptos have RSI > 65 simultaneously, short all of them.
# Edge: Opposite Day screenshot showed all 8 positions profitable at once.
# This systematizes the "everything is overbought" pattern.
#
# References:
# - Breadth indicators (McClellan 1969): market breadth extremes predict reversals
# - Opposite Day (2026-03-04): 8/8 simultaneous shorts profitable

def cluster_short_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Short all overbought cryptos when 6+ of top 10 have RSI > 65."""
    signals = []

    # Calculate RSI for each top-10 asset
    overbought = []
    for symbol in TOP_10_CRYPTO:
        df = data.get(symbol)
        if df is None or len(df) < 20:
            continue
        rsi_val = float(rsi(df["Close"], 14).iloc[-1])
        if rsi_val > 65:
            overbought.append((symbol, rsi_val, df))

    # Gate: need 6+ overbought
    if len(overbought) < 6:
        return signals

    # Confidence scales with breadth
    base_confidence = min(0.65 + 0.03 * (len(overbought) - 6), 0.85)

    for symbol, rsi_val, df in overbought:
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        price = float(close.iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])

        tp = _smart_round(price - atr_val * 1.5)
        sl = _smart_round(price + atr_val * 1.0)
        rr = abs(price - tp) / abs(sl - price) if abs(sl - price) > 0 else 0

        signals.append({
            "strategy": "cluster_short_momentum",
            "symbol": symbol,
            "category": _get_category(symbol),
            "signal_type": "SELL",
            "direction": "SHORT",
            "entry_price": _smart_round(price),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(base_confidence, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Cluster overbought: {len(overbought)}/10 assets RSI>65, "
                f"{symbol} RSI={rsi_val:.0f}"
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "atr_at_entry": round(atr_val, 4),
            "timestamp": _now_iso(),
            "extra": {
                "overbought_count": len(overbought),
                "overbought_symbols": [s for s, _, _ in overbought],
            },
        })

    return signals


# =========================================================================
# STRATEGY 5: News Sentiment Contrarian
# =========================================================================
# Use Fear & Greed Index as a contrarian signal.
# Edge: When F&G > 75 (extreme greed), short overbought assets.
# When F&G < 25 (extreme fear), long oversold assets.
#
# References:
# - Alternative.me F&G index
# - Opposite Day analysis: "macro-news drag" + "negative sentiment amplifies downside"
# - Existing fear_greed_extreme_dca strategy (onchain_strategies.py)

def news_sentiment_contrarian(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Contrarian trades on Fear & Greed extremes."""
    signals = []

    # Fetch Fear & Greed Index (with retry)
    import time as _time
    fng_value = None
    for _attempt in range(3):
        try:
            resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
            resp.raise_for_status()
            fng_data = resp.json().get("data", [])
            if fng_data:
                fng_value = int(fng_data[0]["value"])
                break
        except Exception as exc:
            if _attempt == 2:
                log.warning("F&G fetch failed after 3 attempts: %s", exc)
            else:
                _time.sleep(2 * (_attempt + 1))
    if fng_value is None:
        return signals

    # Only act on extremes
    if 25 <= fng_value <= 75:
        return signals

    is_greed = fng_value > 75
    top_symbols = TOP_10_CRYPTO[:5]

    for symbol in top_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 20:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        price = float(close.iloc[-1])
        rsi_val = float(rsi(close, 14).iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])

        if is_greed and rsi_val > 60:
            # Extreme greed + overbought → SHORT
            tp = _smart_round(price - atr_val * 1.5)
            sl = _smart_round(price + atr_val * 1.0)
            signal_type = "SELL"
            direction = "SHORT"
            reason = f"Contrarian: F&G={fng_value} (extreme greed), {symbol} RSI={rsi_val:.0f}>60 → SHORT"
        elif not is_greed and rsi_val < 40:
            # Extreme fear + oversold → LONG
            tp = _smart_round(price + atr_val * 1.5)
            sl = _smart_round(price - atr_val * 1.0)
            signal_type = "BUY"
            direction = "LONG"
            reason = f"Contrarian: F&G={fng_value} (extreme fear), {symbol} RSI={rsi_val:.0f}<40 → LONG"
        else:
            continue

        # Confidence scales with extremity
        extremity = abs(fng_value - 50) / 50  # 0-1 scale
        confidence = min(0.60 + extremity * 0.25, 0.85)

        rr = abs(price - tp) / abs(sl - price) if abs(sl - price) > 0 else 0

        signals.append({
            "strategy": "news_sentiment_contrarian",
            "symbol": symbol,
            "category": _get_category(symbol),
            "signal_type": signal_type,
            "direction": direction,
            "entry_price": _smart_round(price),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(confidence, 2),
            "risk_reward": round(rr, 2),
            "reason": reason,
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "atr_at_entry": round(atr_val, 4),
            "timestamp": _now_iso(),
            "extra": {
                "fear_greed_value": fng_value,
                "fear_greed_label": "Extreme Greed" if is_greed else "Extreme Fear",
            },
        })

    return signals


# -- Registry --------------------------------------------------------

OPPOSITE_DAY_STRATEGIES = {
    "overbought_reversal_short": overbought_reversal_short,
    "macro_regime_short_filter": macro_regime_short_filter,
    "crowd_contrarian_timer": crowd_contrarian_timer,
    "cluster_short_momentum": cluster_short_momentum,
    "news_sentiment_contrarian": news_sentiment_contrarian,
}
