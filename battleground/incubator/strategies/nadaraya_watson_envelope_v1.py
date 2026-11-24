#!/usr/bin/env python3
"""
Nadaraya-Watson Kernel Regression Envelope — Mean-Reversion Strategy
=====================================================================

Created by: google_antigravity
Date: 2026-03-13

Research Source:
- LuxAlgo "Nadaraya-Watson Envelope" TradingView indicator (30.3K+ likes)
- Non-parametric kernel regression for adaptive fair-price estimation
- Mathematically orthogonal to EMA/RSI/Keltner stack (kernel smoothing
  uses local weighting, not fixed look-back periods)

Core Concept:
    Nadaraya-Watson kernel regression creates an adaptive "fair price"
    curve using Gaussian-weighted local averaging. When price deviates
    significantly from this kernel estimate, it tends to revert — making
    this a MEAN-REVERSION strategy that complements trend-following systems.

Kernel Formula:
    For each bar i:
        y_hat[i] = sum(K(|i-j| / h) * close[j]) / sum(K(|i-j| / h))
    where K(u) = exp(-0.5 * u^2)   (Gaussian kernel)
    and h = bandwidth parameter (default 8)

Signal Logic (CONTRARIAN):
    - LONG when z_score < -1.0 (price below lower envelope = oversold)
      AND kernel_slope > -0.5 (kernel not in steep downtrend)
    - SHORT when z_score > 1.0 (price above upper envelope = overbought)
      AND kernel_slope < 0.5 (kernel not in steep uptrend)
    - z_score = (close - y_hat) / envelope_width

TP/SL:
    - TP = revert to kernel line (distance from price to kernel)
    - SL = 1.5 * envelope_width beyond entry
    - Minimum TP: 0.8 * ATR(14), Minimum SL: 0.5 * ATR(14)
"""

from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from api_helpers import fetch_klines as _fetch_klines_fallback
from api_helpers import fetch_current_price as _fetch_price_fallback

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ENAUSDT",
    "JUPUSDT", "WIFUSDT", "STXUSDT", "RENDERUSDT",
]

KLINE_INTERVAL = "1h"
KLINE_LIMIT = 200
BANDWIDTH = 8           # Kernel bandwidth — higher = smoother curve
ENVELOPE_MULT = 2.0     # Envelope width multiplier (like Bollinger bands)
Z_SCORE_THRESHOLD = 1.0 # Deviation threshold for signal generation
KERNEL_SLOPE_BARS = 5   # Bars for kernel slope calculation
ATR_PERIOD = 14
RSI_PERIOD = 14


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
    strategy: str = "nadaraya_watson_envelope_v1"
    timeframe: str = "1h"
    metadata: dict = field(default_factory=dict)


class NadarayaWatsonEnvelopeStrategy:
    """
    Nadaraya-Watson kernel regression envelope strategy.

    Uses non-parametric Gaussian kernel smoothing to estimate a fair-price
    curve, then generates mean-reversion signals when price deviates
    significantly from the kernel estimate.

    Based on LuxAlgo's TradingView indicator (30.3K+ likes).
    """

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.symbols = p.get("symbols", SYMBOLS)
        self.interval = p.get("interval", KLINE_INTERVAL)
        self.limit = p.get("kline_limit", KLINE_LIMIT)
        self.bandwidth = p.get("bandwidth", BANDWIDTH)
        self.envelope_mult = p.get("envelope_mult", ENVELOPE_MULT)
        self.z_threshold = p.get("z_score_threshold", Z_SCORE_THRESHOLD)
        self.slope_bars = p.get("kernel_slope_bars", KERNEL_SLOPE_BARS)
        self.atr_period = p.get("atr_period", ATR_PERIOD)
        self.rsi_period = p.get("rsi_period", RSI_PERIOD)
        self._timeout = p.get("request_timeout", 10)

    # ── Public API ───────────────────────────────────────────────────

    def generate_signals(self, data=None, symbol: str = None) -> List[Signal]:
        """Scan all symbols for Nadaraya-Watson envelope opportunities."""
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
        """Full Nadaraya-Watson analysis for one symbol."""

        # 1. Fetch OHLCV data
        raw = _fetch_klines_fallback(symbol, self.interval, self.limit, self._timeout)
        if not raw or len(raw) < 50:
            logger.warning(
                "%s: insufficient kline data (%d candles)",
                symbol, len(raw) if raw else 0,
            )
            return []

        closes = [float(k[4]) for k in raw]
        highs = [float(k[2]) for k in raw]
        lows = [float(k[3]) for k in raw]

        # 2. Fetch current price
        current_price = _fetch_price_fallback(symbol, self._timeout)
        if current_price is None or current_price <= 0:
            current_price = closes[-1]

        # 3. Calculate Nadaraya-Watson kernel regression
        y_hat = self._kernel_regression(closes)
        if y_hat is None or len(y_hat) < self.slope_bars + 1:
            logger.warning("%s: kernel regression failed", symbol)
            return []

        # 4. Calculate envelope
        residuals = [
            closes[i] - y_hat[i] for i in range(len(closes))
        ]
        residual_stdev = statistics.stdev(residuals) if len(residuals) > 1 else 0
        if residual_stdev == 0:
            logger.warning("%s: zero residual stdev — no variance", symbol)
            return []

        envelope_width = self.envelope_mult * residual_stdev
        upper_envelope = y_hat[-1] + envelope_width
        lower_envelope = y_hat[-1] - envelope_width

        # 5. Calculate z-score (normalized distance from kernel)
        z_score = (current_price - y_hat[-1]) / envelope_width

        # 6. Calculate kernel slope (trend direction of fair-price estimate)
        kernel_slope = 0.0
        if y_hat[-self.slope_bars] != 0:
            kernel_slope = (
                (y_hat[-1] - y_hat[-self.slope_bars])
                / y_hat[-self.slope_bars] * 100
            )

        # 7. Calculate RSI for confluence
        rsi = self._calc_rsi(closes)

        # 8. Calculate ATR for minimum TP/SL floors
        atr = self._calc_atr(highs, lows, closes)

        # 9. Signal logic (CONTRARIAN — mean-reversion)
        direction = None

        if z_score < -self.z_threshold and kernel_slope > -0.5:
            direction = "BUY"
        elif z_score > self.z_threshold and kernel_slope < 0.5:
            direction = "SELL"

        if direction is None:
            return []

        # 10. Calculate confidence
        confidence = 0.60  # base

        # Bonus for additional z-score deviation beyond threshold
        excess_z = abs(z_score) - self.z_threshold
        z_bonus = min(0.15, (excess_z / 0.5) * 0.05)
        confidence += z_bonus

        # RSI confluence bonus
        rsi_confirms = False
        if direction == "BUY" and rsi is not None and rsi < 30:
            confidence += 0.05
            rsi_confirms = True
        elif direction == "SELL" and rsi is not None and rsi > 70:
            confidence += 0.05
            rsi_confirms = True

        confidence = max(0.30, min(0.95, confidence))

        # 11. TP/SL calculation
        distance_to_kernel = abs(current_price - y_hat[-1])
        sl_distance = 1.5 * envelope_width

        # Apply ATR floors
        min_tp = 0.8 * atr
        min_sl = 0.5 * atr
        tp_distance = max(distance_to_kernel, min_tp)
        sl_distance = max(sl_distance, min_sl)

        if direction == "BUY":
            tp = round(current_price + tp_distance, 2)
            sl = round(current_price - sl_distance, 2)
        else:
            tp = round(current_price - tp_distance, 2)
            sl = round(current_price + sl_distance, 2)

        # 12. Build reason string
        reason_parts = [
            "NW Kernel mean-reversion:",
            "z=" + str(round(z_score, 2)),
            "kernel=" + str(round(y_hat[-1], 2)),
            "slope=" + str(round(kernel_slope, 3)) + "%",
            "env_w=" + str(round(envelope_width, 2)),
        ]
        if rsi is not None:
            reason_parts.append("RSI=" + str(round(rsi, 1)))
        if rsi_confirms:
            reason_parts.append("(RSI confirms)")
        reason = " | ".join(reason_parts)

        return [Signal(
            symbol=symbol,
            direction=direction,
            confidence=round(confidence, 4),
            entry_price=round(current_price, 2),
            take_profit=tp,
            stop_loss=sl,
            reason=reason,
            metadata={
                "kernel_value": round(y_hat[-1], 4),
                "kernel_slope_pct": round(kernel_slope, 4),
                "z_score": round(z_score, 4),
                "envelope_width": round(envelope_width, 4),
                "upper_envelope": round(upper_envelope, 4),
                "lower_envelope": round(lower_envelope, 4),
                "residual_stdev": round(residual_stdev, 4),
                "bandwidth": self.bandwidth,
                "rsi": round(rsi, 2) if rsi is not None else None,
                "rsi_confirms": rsi_confirms,
                "atr": round(atr, 4),
                "current_price": current_price,
                "distance_to_kernel": round(distance_to_kernel, 4),
            },
        )]

    # ── Kernel Regression ────────────────────────────────────────────

    def _kernel_regression(self, closes: List[float]) -> Optional[List[float]]:
        """
        Nadaraya-Watson kernel regression with Gaussian kernel.

        For each bar i:
            y_hat[i] = sum(K(|i-j| / h) * close[j]) / sum(K(|i-j| / h))
        where K(u) = exp(-0.5 * u^2)  (Gaussian kernel)
        and h = bandwidth parameter.
        """
        n = len(closes)
        if n == 0:
            return None

        h = self.bandwidth
        y_hat = []

        for i in range(n):
            weighted_sum = 0.0
            weight_total = 0.0

            for j in range(n):
                u = abs(i - j) / h
                # Gaussian kernel: K(u) = exp(-0.5 * u^2)
                kernel_weight = math.exp(-0.5 * u * u)
                weighted_sum += kernel_weight * closes[j]
                weight_total += kernel_weight

            if weight_total > 0:
                y_hat.append(weighted_sum / weight_total)
            else:
                y_hat.append(closes[i])

        return y_hat

    # ── Technical Indicators ─────────────────────────────────────────

    def _calc_rsi(self, closes: List[float]) -> Optional[float]:
        """Calculate standard 14-period RSI."""
        period = self.rsi_period
        if len(closes) < period + 1:
            return None

        deltas = [
            closes[i] - closes[i - 1]
            for i in range(1, len(closes))
        ]

        # Seed averages with first 'period' changes
        gains = [d if d > 0 else 0 for d in deltas[:period]]
        losses = [-d if d < 0 else 0 for d in deltas[:period]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        # Smoothed (Wilder's) moving average for remaining
        for d in deltas[period:]:
            gain = d if d > 0 else 0
            loss = -d if d < 0 else 0
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _calc_atr(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
    ) -> float:
        """Calculate Average True Range (14-period)."""
        period = self.atr_period
        if len(closes) < period + 1:
            # Fallback: simple range of last candle
            if highs and lows:
                return highs[-1] - lows[-1]
            return 0.0

        true_ranges = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i - 1])
            low_close = abs(lows[i] - closes[i - 1])
            true_ranges.append(max(high_low, high_close, low_close))

        if len(true_ranges) < period:
            return statistics.mean(true_ranges)

        return statistics.mean(true_ranges[-period:])


# ── Module-level scan() function ─────────────────────────────────────

def scan(params: Optional[dict] = None) -> List[dict]:
    """
    Module-level entry point for the battleground incubator framework.
    Returns a list of signal dicts.
    """
    strategy = NadarayaWatsonEnvelopeStrategy(params)
    signals = strategy.generate_signals()
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


# ── Standalone Runner ────────────────────────────────────────────────

def main():
    """Run the Nadaraya-Watson Envelope scanner and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    strategy = NadarayaWatsonEnvelopeStrategy()
    signals = strategy.generate_signals()

    header = "=" * 75
    divider = "-" * 50
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print("")
    print(header)
    print("  NADARAYA-WATSON KERNEL ENVELOPE  |  " + timestamp)
    print("  Based on: LuxAlgo TradingView indicator (30.3K likes)")
    print("  Type: MEAN-REVERSION (contrarian)")
    print(header)

    if not signals:
        print("")
        print("  No mean-reversion opportunities detected.")
        print("  (Requires z-score beyond +/-1.0 with favorable kernel slope)")
    else:
        for sig in signals:
            m = sig.metadata
            print("")
            print("  " + sig.symbol)
            print("  " + divider)
            print("  Direction:   " + sig.direction)
            print("  Z-Score:     " + str(round(m["z_score"], 3)))
            print("  Kernel:      " + str(round(m["kernel_value"], 2)))
            print("  Slope:       " + str(round(m["kernel_slope_pct"], 3)) + "%")
            lo_str = str(round(m["lower_envelope"], 2))
            hi_str = str(round(m["upper_envelope"], 2))
            print("  Envelope:    [" + lo_str + " - " + hi_str + "]")
            entry_str = "${:,.2f}".format(sig.entry_price)
            tp_str = "${:,.2f}".format(sig.take_profit)
            sl_str = "${:,.2f}".format(sig.stop_loss)
            print("  Entry:       " + entry_str)
            print("  TP:          " + tp_str + "  |  SL: " + sl_str)
            conf_str = "{:.1%}".format(sig.confidence)
            print("  Confidence:  " + conf_str)
            rsi_val = m.get("rsi")
            if rsi_val is not None:
                rsi_str = str(round(rsi_val, 1))
                confirms = " (confirms)" if m.get("rsi_confirms") else ""
                print("  RSI:         " + rsi_str + confirms)

    print("")
    print(header)
    sym_count = str(len(strategy.symbols))
    sig_count = str(len(signals))
    print("  Scanned " + sym_count + " symbols, found " + sig_count + " mean-reversion signals")
    print(header)
    print("")

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
