#!/usr/bin/env python3
"""
Spike MACD Divergence v1 — MACD Histogram Divergence Strategy (Incubator)
=========================================================================

Created by: google_antigravity
Date: 2026-03-13

Resurrected from alpha_engine/spike_predictor.py where it was killed after
only 3 trades — statistically meaningless. ML audit recommends 30-trade
patience in the incubator before any elimination decision.

Research Sources:
- Appel, Gerald (1979) "The Moving Average Convergence Divergence Method"
- Elder, Alexander (1993) "Trading for a Living" — Triple Screen method
- Twitter trader @TraderSimon — MACD histogram turning at key levels

Strategy Logic:
1. Fetches 4H OHLCV klines from Binance public API (no key needed)
2. Computes MACD (12, 26, 9) and RSI(14)
3. Detects two signal types:
   a) Histogram Turn: MACD histogram turning up while still negative (bullish)
      or turning down while still positive (bearish), confirmed by RSI
   b) Classic Divergence: Price makes new low but MACD histogram makes
      higher low (bullish), or price makes new high but MACD histogram
      makes lower high (bearish)
4. Entry on the bar after divergence confirmation
5. ATR-based TP/SL (TP=2x ATR, SL=1x ATR)

Original alpha_engine performance: 100% WR on forex (but only 3 trades total).
Needs 30+ trades for statistical significance — hence incubator placement.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ENAUSDT", "JUPUSDT", "WIFUSDT", "STXUSDT", "RENDERUSDT", "NEARUSDT"]

from api_helpers import fetch_klines as _fetch_klines_fallback

# Analysis parameters
KLINE_INTERVAL = "4h"
KLINE_LIMIT = 200       # ~33 days of 4H data
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
RSI_PERIOD = 14
ATR_PERIOD = 14
DIVERGENCE_LOOKBACK = 20  # bars to look back for swing highs/lows

# Risk parameters
TP_ATR_MULT = 2.0
SL_ATR_MULT = 1.0

# RSI thresholds for histogram turn confirmation
RSI_BULLISH_THRESHOLD = 45
RSI_BEARISH_THRESHOLD = 55


@dataclass
class Candle:
    """OHLCV candle."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Signal:
    """Trading signal — matches battleground format."""
    symbol: str
    direction: str       # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    strategy: str = "spike_macd_divergence_v1"
    timeframe: str = "4h"
    metadata: dict = field(default_factory=dict)


class SpikeMacdDivergenceStrategy:
    """
    MACD Histogram Divergence — detects momentum divergences between
    price action and MACD histogram for early reversal entries.

    Two signal modes:
    1. Histogram Turn: 3-bar histogram pattern (turning while same sign)
       + RSI confirmation. This is the original spike_predictor logic.
    2. Classic Divergence: Price swing low/high vs MACD histogram swing
       low/high divergence over a configurable lookback window.

    Reference:
        Appel (1979), Elder (1993), @TraderSimon
    """

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.symbols = p.get("symbols", SYMBOLS)
        self.interval = p.get("interval", KLINE_INTERVAL)
        self.limit = p.get("kline_limit", KLINE_LIMIT)
        self.macd_fast = p.get("macd_fast", MACD_FAST)
        self.macd_slow = p.get("macd_slow", MACD_SLOW)
        self.macd_signal = p.get("macd_signal", MACD_SIGNAL)
        self.rsi_period = p.get("rsi_period", RSI_PERIOD)
        self.atr_period = p.get("atr_period", ATR_PERIOD)
        self.divergence_lookback = p.get("divergence_lookback", DIVERGENCE_LOOKBACK)
        self.tp_mult = p.get("tp_atr_mult", TP_ATR_MULT)
        self.sl_mult = p.get("sl_atr_mult", SL_ATR_MULT)
        self._timeout = p.get("request_timeout", 10)

    # ── Public API ───────────────────────────────────────────────────

    def generate_signals(self, data=None, symbol: str = None) -> List[Signal]:
        """Scan all symbols for MACD divergence signals."""
        if requests is None:
            logger.error("requests library not available")
            return []

        targets = [symbol] if symbol else self.symbols
        all_signals: List[Signal] = []

        for sym in targets:
            try:
                sigs = self._analyze_symbol(sym)
                all_signals.extend(sigs)
            except Exception as e:
                logger.warning("Error analyzing %s: %s", sym, e)

        return all_signals

    # ── Core Analysis ────────────────────────────────────────────────

    def _analyze_symbol(self, symbol: str) -> List[Signal]:
        """Run MACD divergence analysis for one symbol."""

        candles = self._fetch_klines(symbol)
        if not candles or len(candles) < self.macd_slow + self.macd_signal + 10:
            logger.warning("%s: insufficient data (%d candles)",
                           symbol, len(candles) if candles else 0)
            return []

        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]

        # Compute indicators
        macd_line, signal_line, histogram = self._calc_macd(closes)
        rsi_values = self._calc_rsi(closes)
        atr_val = self._calc_atr(candles)

        if atr_val == 0 or not histogram or not rsi_values:
            return []

        current_price = closes[-1]
        current_rsi = rsi_values[-1]
        signals: List[Signal] = []

        # ── Mode 1: Histogram Turn (original spike_predictor logic) ──
        if len(histogram) >= 3:
            h0 = histogram[-1]
            h1 = histogram[-2]
            h2 = histogram[-3]

            # Bullish: histogram negative and turning up
            if h2 < h1 < h0 < 0 and current_rsi < RSI_BULLISH_THRESHOLD:
                entry = current_price
                tp = round(entry + atr_val * self.tp_mult, 2)
                sl = round(entry - atr_val * self.sl_mult, 2)

                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=0.57,
                    entry_price=round(entry, 2),
                    take_profit=tp,
                    stop_loss=sl,
                    reason=(
                        f"MACD histogram bullish turn (h={h0:.4f}>{h1:.4f}>{h2:.4f}, "
                        f"all <0), RSI={current_rsi:.0f}"
                    ),
                    metadata={
                        "signal_mode": "histogram_turn",
                        "histogram": [round(h2, 6), round(h1, 6), round(h0, 6)],
                        "rsi": round(current_rsi, 2),
                        "atr": round(atr_val, 2),
                        "current_price": current_price,
                    },
                ))

            # Bearish: histogram positive and turning down
            elif h2 > h1 > h0 > 0 and current_rsi > RSI_BEARISH_THRESHOLD:
                entry = current_price
                tp = round(entry - atr_val * self.tp_mult, 2)
                sl = round(entry + atr_val * self.sl_mult, 2)

                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=0.57,
                    entry_price=round(entry, 2),
                    take_profit=tp,
                    stop_loss=sl,
                    reason=(
                        f"MACD histogram bearish turn (h={h0:.4f}<{h1:.4f}<{h2:.4f}, "
                        f"all >0), RSI={current_rsi:.0f}"
                    ),
                    metadata={
                        "signal_mode": "histogram_turn",
                        "histogram": [round(h2, 6), round(h1, 6), round(h0, 6)],
                        "rsi": round(current_rsi, 2),
                        "atr": round(atr_val, 2),
                        "current_price": current_price,
                    },
                ))

        # ── Mode 2: Classic Price-Histogram Divergence ───────────────
        # Only check if Mode 1 didn't fire (avoid duplicate signals)
        if not signals and len(histogram) >= self.divergence_lookback:
            n = self.divergence_lookback
            price_window = closes[-n:]
            hist_window = histogram[-n:]

            div_signal = self._detect_divergence(price_window, hist_window)

            if div_signal == "bullish" and current_rsi < 50:
                entry = current_price
                tp = round(entry + atr_val * self.tp_mult, 2)
                sl = round(entry - atr_val * self.sl_mult, 2)

                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=0.60,
                    entry_price=round(entry, 2),
                    take_profit=tp,
                    stop_loss=sl,
                    reason=(
                        f"Bullish MACD divergence: price lower low but histogram "
                        f"higher low over {n} bars, RSI={current_rsi:.0f}"
                    ),
                    metadata={
                        "signal_mode": "classic_divergence",
                        "divergence_type": "bullish",
                        "lookback": n,
                        "rsi": round(current_rsi, 2),
                        "atr": round(atr_val, 2),
                        "current_price": current_price,
                    },
                ))

            elif div_signal == "bearish" and current_rsi > 50:
                entry = current_price
                tp = round(entry - atr_val * self.tp_mult, 2)
                sl = round(entry + atr_val * self.sl_mult, 2)

                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=0.60,
                    entry_price=round(entry, 2),
                    take_profit=tp,
                    stop_loss=sl,
                    reason=(
                        f"Bearish MACD divergence: price higher high but histogram "
                        f"lower high over {n} bars, RSI={current_rsi:.0f}"
                    ),
                    metadata={
                        "signal_mode": "classic_divergence",
                        "divergence_type": "bearish",
                        "lookback": n,
                        "rsi": round(current_rsi, 2),
                        "atr": round(atr_val, 2),
                        "current_price": current_price,
                    },
                ))

        return signals

    # ── Divergence Detection ─────────────────────────────────────────

    def _detect_divergence(
        self, prices: List[float], histogram: List[float]
    ) -> Optional[str]:
        """
        Detect classic divergence between price and MACD histogram.

        Bullish divergence: price makes lower low, histogram makes higher low
        Bearish divergence: price makes higher high, histogram makes lower high

        Uses the two most recent swing points within the window.
        """
        n = len(prices)
        if n < 5:
            return None

        # Find swing lows (local minima) in the price window
        swing_lows = []
        for i in range(2, n - 2):
            if prices[i] <= prices[i-1] and prices[i] <= prices[i-2] \
               and prices[i] <= prices[i+1] and prices[i] <= prices[i+2]:
                swing_lows.append(i)

        # Find swing highs (local maxima) in the price window
        swing_highs = []
        for i in range(2, n - 2):
            if prices[i] >= prices[i-1] and prices[i] >= prices[i-2] \
               and prices[i] >= prices[i+1] and prices[i] >= prices[i+2]:
                swing_highs.append(i)

        # Check bullish divergence: need at least 2 swing lows
        if len(swing_lows) >= 2:
            prev_low_idx = swing_lows[-2]
            curr_low_idx = swing_lows[-1]

            price_lower_low = prices[curr_low_idx] < prices[prev_low_idx]
            hist_higher_low = histogram[curr_low_idx] > histogram[prev_low_idx]

            # Both histogram values should be negative for a meaningful
            # bullish divergence
            if (price_lower_low and hist_higher_low
                    and histogram[curr_low_idx] < 0
                    and histogram[prev_low_idx] < 0):
                # Confirm: current bar is near the recent swing low
                # (within 2 bars of the last swing low)
                if n - 1 - curr_low_idx <= 3:
                    return "bullish"

        # Check bearish divergence: need at least 2 swing highs
        if len(swing_highs) >= 2:
            prev_high_idx = swing_highs[-2]
            curr_high_idx = swing_highs[-1]

            price_higher_high = prices[curr_high_idx] > prices[prev_high_idx]
            hist_lower_high = histogram[curr_high_idx] < histogram[prev_high_idx]

            # Both histogram values should be positive for a meaningful
            # bearish divergence
            if (price_higher_high and hist_lower_high
                    and histogram[curr_high_idx] > 0
                    and histogram[prev_high_idx] > 0):
                if n - 1 - curr_high_idx <= 3:
                    return "bearish"

        return None

    # ── Technical Indicators ─────────────────────────────────────────

    def _calc_macd(
        self, closes: List[float]
    ) -> tuple[List[float], List[float], List[float]]:
        """
        Calculate MACD line, signal line, and histogram.
        Returns lists aligned to the end of the closes array.
        """
        fast_ema = self._ema(closes, self.macd_fast)
        slow_ema = self._ema(closes, self.macd_slow)

        # MACD line = fast EMA - slow EMA (aligned to shorter array)
        offset = len(fast_ema) - len(slow_ema)
        macd_line = [
            fast_ema[offset + i] - slow_ema[i]
            for i in range(len(slow_ema))
        ]

        # Signal line = EMA of MACD line
        signal_line = self._ema(macd_line, self.macd_signal)

        # Histogram = MACD - Signal
        sig_offset = len(macd_line) - len(signal_line)
        histogram = [
            macd_line[sig_offset + i] - signal_line[i]
            for i in range(len(signal_line))
        ]

        return macd_line, signal_line, histogram

    def _ema(self, data: List[float], period: int) -> List[float]:
        """Exponential Moving Average."""
        if len(data) < period:
            return []

        multiplier = 2.0 / (period + 1)
        ema_values = [statistics.mean(data[:period])]

        for i in range(period, len(data)):
            val = (data[i] - ema_values[-1]) * multiplier + ema_values[-1]
            ema_values.append(val)

        return ema_values

    def _calc_rsi(self, closes: List[float], period: int = None) -> List[float]:
        """Relative Strength Index."""
        period = period or self.rsi_period
        if len(closes) < period + 1:
            return []

        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]

        gains = [max(d, 0) for d in deltas[:period]]
        losses = [max(-d, 0) for d in deltas[:period]]

        avg_gain = statistics.mean(gains) if gains else 0
        avg_loss = statistics.mean(losses) if losses else 0

        rsi_values = []
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100.0 - 100.0 / (1.0 + rs))

        for i in range(period, len(deltas)):
            gain = max(deltas[i], 0)
            loss = max(-deltas[i], 0)
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

            if avg_loss == 0:
                rsi_values.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(100.0 - 100.0 / (1.0 + rs))

        return rsi_values

    def _calc_atr(self, candles: List[Candle], period: int = None) -> float:
        """Average True Range for risk management."""
        period = period or self.atr_period
        if len(candles) < period + 1:
            return candles[-1].high - candles[-1].low if candles else 0

        true_ranges = []
        for i in range(1, len(candles)):
            high_low = candles[i].high - candles[i].low
            high_close = abs(candles[i].high - candles[i-1].close)
            low_close = abs(candles[i].low - candles[i-1].close)
            true_ranges.append(max(high_low, high_close, low_close))

        if len(true_ranges) < period:
            return statistics.mean(true_ranges)

        return statistics.mean(true_ranges[-period:])

    # ── Binance API ──────────────────────────────────────────────────

    def _fetch_klines(self, symbol: str) -> Optional[List[Candle]]:
        """Fetch OHLCV klines with geo-restriction fallback."""
        data = _fetch_klines_fallback(symbol, self.interval, self.limit, self._timeout)
        if not data:
            return None
        return [
            Candle(
                timestamp=int(k[0]),
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
            )
            for k in data
        ]


# ── Standalone Runner ────────────────────────────────────────────────

def main():
    """Run the MACD Divergence scanner and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    strategy = SpikeMacdDivergenceStrategy()
    signals = strategy.generate_signals()

    print(f"\n{'='*75}")
    print(f"  SPIKE MACD DIVERGENCE v1 (INCUBATOR)")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Ref: Appel (1979), Elder (1993)")
    print(f"{'='*75}")

    if not signals:
        print("\n  No signals generated.")
    else:
        for sig in signals:
            m = sig.metadata
            print(f"\n  {sig.symbol}")
            print(f"  {'─'*50}")
            print(f"  Direction:   {sig.direction}")
            print(f"  Mode:        {m.get('signal_mode', 'unknown')}")
            print(f"  Entry:       ${sig.entry_price:,.2f}")
            print(f"  TP:          ${sig.take_profit:,.2f}  |  SL: ${sig.stop_loss:,.2f}")
            print(f"  Confidence:  {sig.confidence:.1%}")
            print(f"  RSI:         {m.get('rsi', 'N/A')}")
            print(f"  Reason:      {sig.reason}")

    print(f"\n{'='*75}")
    print(f"  Scanned {len(strategy.symbols)} symbols, generated {len(signals)} signals")
    print(f"{'='*75}\n")

    return [
        {
            "symbol": s.symbol,
            "direction": s.direction,
            "strategy": s.strategy,
            "confidence": s.confidence,
            "entry_price": s.entry_price,
            "take_profit": s.take_profit,
            "stop_loss": s.stop_loss,
            "timeframe": s.timeframe,
            "reason": s.reason,
            "metadata": s.metadata,
        }
        for s in signals
    ]


if __name__ == "__main__":
    main()
