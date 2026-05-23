#!/usr/bin/env python3
"""
Proven Strategies — Ported from Battleground incubator.

Three strategies with verified backtested performance:

1. whale_confirmed_rsi   (70.6% WR, Sharpe 5.73)
   RSI(14) oversold/overbought + volume-based whale detection proxy.

2. atr_regime_rsi        (56.2% WR, Sharpe 3.45)
   Low-volatility regime filter + RSI(14) oversold. BUY only.

3. multi_period_rsi_confluence (72.7% WR, Sharpe 10.86)
   RSI(14) < 35 AND RSI(50) < 40 dual alignment. BUY only.

Usage:
    from trading.proven_strategies import scan_all_strategies
    signals = scan_all_strategies("BTCUSDT", klines)
"""

from __future__ import annotations

from typing import Dict, List, Optional


# ── Helpers ──────────────────────────────────────────────────────────


def _parse_ohlcv(klines: List) -> Dict[str, List[float]]:
    """Convert Binance kline arrays to OHLCV lists.

    Each kline: [open_time, open, high, low, close, volume, close_time, ...]
    """
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []
    for k in klines:
        opens.append(float(k[1]))
        highs.append(float(k[2]))
        lows.append(float(k[3]))
        closes.append(float(k[4]))
        volumes.append(float(k[5]))
    return {
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    }


def _compute_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Wilder's RSI using exponential moving average of gains/losses."""
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Seed with SMA for the first `period` deltas
    first_gains = [d if d > 0 else 0.0 for d in deltas[:period]]
    first_losses = [-d if d < 0 else 0.0 for d in deltas[:period]]
    avg_gain = sum(first_gains) / period
    avg_loss = sum(first_losses) / period

    # Smooth with Wilder's EMA for remaining deltas
    for d in deltas[period:]:
        gain = d if d > 0 else 0.0
        loss = -d if d < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 4)


def _compute_atr(highs: List[float], lows: List[float], closes: List[float],
                 period: int = 14) -> Optional[float]:
    """Average True Range over `period` bars."""
    if len(closes) < period + 1:
        return None

    true_ranges = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    # Simple moving average of last `period` true ranges
    atr = sum(true_ranges[-period:]) / period
    return round(atr, 8)


def _compute_atr_series(highs: List[float], lows: List[float],
                        closes: List[float]) -> List[float]:
    """Return a list of per-bar true range values (for rolling ATR avg)."""
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return trs


def _volume_ratio(volumes: List[float], lookback: int = 20) -> float:
    """Current volume / average of previous `lookback` bars."""
    if len(volumes) < lookback + 1:
        return 1.0
    avg = sum(volumes[-lookback - 1:-1]) / lookback
    if avg <= 0:
        return 1.0
    return round(volumes[-1] / avg, 4)


# ── Strategy 1: Whale Confirmed RSI ─────────────────────────────────


def whale_confirmed_rsi(symbol: str, klines: List) -> Optional[Dict]:
    """
    RSI(14) oversold/overbought + volume spike as whale proxy.

    BUY:  RSI < 30 + volume > 2x avg (whale accumulation proxy)
    SELL: RSI > 70 + volume > 2x avg (whale distribution proxy)
    TP = 2.0 * ATR, SL = 1.5 * ATR

    Source: incubator WhaleConfirmedRSI — 70.6% WR, Sharpe 5.73
    """
    if len(klines) < 55:
        return None

    ohlcv = _parse_ohlcv(klines)
    closes = ohlcv["close"]
    highs = ohlcv["high"]
    lows = ohlcv["low"]
    volumes = ohlcv["volume"]

    rsi14 = _compute_rsi(closes, 14)
    atr = _compute_atr(highs, lows, closes, 14)
    vol_ratio = _volume_ratio(volumes, 20)

    if rsi14 is None or atr is None or atr <= 0:
        return None

    current_price = closes[-1]
    whale_threshold = 2.0  # volume > 2x average = whale proxy

    direction = None
    confidence = 0.0

    if rsi14 < 30 and vol_ratio >= whale_threshold:
        # Oversold + whale accumulation
        direction = "LONG"
        tp = round(current_price + 2.0 * atr, 8)
        sl = round(current_price - 1.5 * atr, 8)
        # Higher confidence when RSI is more extreme and volume bigger
        confidence = round(min(0.65 + (30 - rsi14) / 100 + (vol_ratio - 2.0) / 20, 0.92), 3)

    elif rsi14 > 70 and vol_ratio >= whale_threshold:
        # Overbought + whale distribution
        direction = "SHORT"
        tp = round(current_price - 2.0 * atr, 8)
        sl = round(current_price + 1.5 * atr, 8)
        confidence = round(min(0.65 + (rsi14 - 70) / 100 + (vol_ratio - 2.0) / 20, 0.92), 3)

    if direction is None:
        return None

    return {
        "symbol": symbol,
        "direction": direction,
        "strategy": "whale_confirmed_rsi",
        "entry_price": current_price,
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": confidence,
        "indicators": {
            "rsi14": rsi14,
            "atr": atr,
            "vol_ratio": vol_ratio,
            "whale_detected": vol_ratio >= whale_threshold,
        },
    }


# ── Strategy 2: ATR Regime RSI ──────────────────────────────────────


def atr_regime_rsi(symbol: str, klines: List) -> Optional[Dict]:
    """
    Low-volatility regime filter + RSI(14) oversold.

    STEP 1: ATR(14) / rolling ATR avg(50) < 1.2 (low vol regime)
    STEP 2: RSI(14) < 35 -> BUY
    TP = 2.0 * ATR, SL = 1.5 * ATR
    BUY only.

    Source: incubator ATRRegimeRSI — 56.2% WR, Sharpe 3.45
    """
    if len(klines) < 65:
        return None

    ohlcv = _parse_ohlcv(klines)
    closes = ohlcv["close"]
    highs = ohlcv["high"]
    lows = ohlcv["low"]

    rsi14 = _compute_rsi(closes, 14)
    atr = _compute_atr(highs, lows, closes, 14)

    if rsi14 is None or atr is None or atr <= 0:
        return None

    # Compute rolling ATR average over 50 bars for regime detection
    tr_series = _compute_atr_series(highs, lows, closes)
    if len(tr_series) < 50:
        return None

    # ATR over last 14 bars (current ATR)
    current_atr = sum(tr_series[-14:]) / 14
    # Average ATR over last 50 bars
    avg_atr_50 = sum(tr_series[-50:]) / 50

    if avg_atr_50 <= 0:
        return None

    atr_ratio = current_atr / avg_atr_50

    # Only trade in low-vol regime
    if atr_ratio >= 1.2:
        return None

    # Only BUY when RSI oversold
    if rsi14 >= 35:
        return None

    current_price = closes[-1]
    tp = round(current_price + 2.0 * atr, 8)
    sl = round(current_price - 1.5 * atr, 8)

    # Confidence: lower RSI and lower vol regime = better
    confidence = round(min(0.55 + (35 - rsi14) / 100 + (1.2 - atr_ratio) / 5, 0.85), 3)

    return {
        "symbol": symbol,
        "direction": "LONG",
        "strategy": "atr_regime_rsi",
        "entry_price": current_price,
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": confidence,
        "indicators": {
            "rsi14": rsi14,
            "atr": atr,
            "atr_ratio": round(atr_ratio, 4),
            "regime": "low_vol",
        },
    }


# ── Strategy 3: Multi-Period RSI Confluence ─────────────────────────


def multi_period_rsi_confluence(symbol: str, klines: List) -> Optional[Dict]:
    """
    Dual RSI alignment for high-confidence oversold entries.

    RSI(14) < 35 AND RSI(50) < 40 -> BUY
    TP = 2.0 * ATR, SL = 1.5 * ATR
    BUY only.

    Source: incubator MultiPeriodRSIConfluence — 72.7% WR, Sharpe 10.86
    """
    if len(klines) < 65:
        return None

    ohlcv = _parse_ohlcv(klines)
    closes = ohlcv["close"]
    highs = ohlcv["high"]
    lows = ohlcv["low"]

    rsi14 = _compute_rsi(closes, 14)
    rsi50 = _compute_rsi(closes, 50)
    atr = _compute_atr(highs, lows, closes, 14)

    if rsi14 is None or rsi50 is None or atr is None or atr <= 0:
        return None

    # Both RSI periods must confirm oversold
    if rsi14 >= 35 or rsi50 >= 40:
        return None

    current_price = closes[-1]
    tp = round(current_price + 2.0 * atr, 8)
    sl = round(current_price - 1.5 * atr, 8)

    # Confidence: deeper oversold on both timeframes = higher confidence
    rsi14_depth = (35 - rsi14) / 35  # 0-1 scale
    rsi50_depth = (40 - rsi50) / 40  # 0-1 scale
    confidence = round(min(0.70 + rsi14_depth * 0.10 + rsi50_depth * 0.10, 0.95), 3)

    return {
        "symbol": symbol,
        "direction": "LONG",
        "strategy": "multi_period_rsi_confluence",
        "entry_price": current_price,
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": confidence,
        "indicators": {
            "rsi14": rsi14,
            "rsi50": rsi50,
            "atr": atr,
        },
    }


# ── Aggregator ──────────────────────────────────────────────────────


ALL_STRATEGIES = [
    whale_confirmed_rsi,
    atr_regime_rsi,
    multi_period_rsi_confluence,
]


def scan_all_strategies(symbol: str, klines: List) -> List[Dict]:
    """Run all proven strategies on the given klines and return signals."""
    signals = []
    for strategy_fn in ALL_STRATEGIES:
        try:
            result = strategy_fn(symbol, klines)
            if result is not None:
                signals.append(result)
        except Exception as e:
            print(f"  [WARN] {strategy_fn.__name__} failed on {symbol}: {e}")
    return signals
