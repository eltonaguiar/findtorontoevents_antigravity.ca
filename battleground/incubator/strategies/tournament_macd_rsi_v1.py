#!/usr/bin/env python3
"""
Tournament MACD+RSI Confluence — Mega Mutation Tournament Winner #1
====================================================================

Created by: google_antigravity
Date: 2026-03-13

Research Source:
- Mega Mutation Tournament (33,000 backtests across 1,000 mutations × 33 symbols)
- Tournament ID: 43ca60a694d1
- Key finding: MACD+RSI confluence mutations dominated the fitness leaderboard,
  with the top-5 symbols averaging 0.77+ fitness scores.

Strategy Logic:
1. Fetches 4H OHLCV klines from Binance public API (via api_helpers fallback chain)
2. Computes MACD(12, 26, 9) — line, signal, histogram
3. Computes RSI(14)
4. BUY: MACD line crosses above signal AND 35 < RSI < 65 (momentum confirmed, not overbought)
5. SELL: MACD line crosses below signal AND 35 < RSI < 65 (momentum confirmed, not oversold)
6. Confidence derived from MACD histogram magnitude + RSI distance from extremes
7. TP/SL based on ATR(14) — 1.5× / 1.0× from tournament's optimal R:R cluster

Target Symbols (top tournament performers by fitness):
- JUPUSDT  (avg_fitness: 0.541, max: 0.838)
- ENAUSDT  (avg_fitness: 0.534, max: 0.829)
- NEARUSDT (avg_fitness: 0.405, max: 0.829)
- AVAXUSDT (top-10 robust performer)
- RENDERUSDT (max_fitness: 0.845 — highest single mutation score)

Dependencies: numpy, requests (no external TA library needed)
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from api_helpers import fetch_klines as _fetch_klines_fallback

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
SYMBOLS = ["JUPUSDT", "ENAUSDT", "NEARUSDT", "AVAXUSDT", "RENDERUSDT"]

KLINE_INTERVAL = "4h"
KLINE_LIMIT = 200  # ~33 days of 4H candles

# MACD parameters (standard)
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# RSI parameters
RSI_PERIOD = 14
RSI_UPPER = 65  # not overbought threshold
RSI_LOWER = 35  # not oversold threshold

# Risk parameters (from tournament's optimal R:R cluster)
TP_ATR_MULT = 1.5
SL_ATR_MULT = 1.0


@dataclass
class Candle:
    """OHLCV candle."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class TournamentMacdRsiStrategy:
    """
    MACD+RSI Confluence strategy derived from Mega Mutation Tournament results.

    The tournament's 33,000 backtests revealed that MACD crossover + RSI
    confirmation (avoiding overbought/oversold entries) was the dominant
    mutation family, with the highest average fitness across top-5 symbols.
    """

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.symbols = p.get("symbols", SYMBOLS)
        self.interval = p.get("interval", KLINE_INTERVAL)
        self.limit = p.get("kline_limit", KLINE_LIMIT)
        self.macd_fast = p.get("macd_fast", MACD_FAST)
        self.macd_slow = p.get("macd_slow", MACD_SLOW)
        self.macd_signal_period = p.get("macd_signal", MACD_SIGNAL)
        self.rsi_period = p.get("rsi_period", RSI_PERIOD)
        self.rsi_upper = p.get("rsi_upper", RSI_UPPER)
        self.rsi_lower = p.get("rsi_lower", RSI_LOWER)
        self.tp_mult = p.get("tp_atr_mult", TP_ATR_MULT)
        self.sl_mult = p.get("sl_atr_mult", SL_ATR_MULT)
        self._timeout = p.get("request_timeout", 10)

    # ── Public API ───────────────────────────────────────────────────

    def generate_signals(self, data=None, symbol: str = None) -> List[dict]:
        """Scan symbols using MACD+RSI confluence from tournament DNA."""
        if np is None:
            logger.error("numpy not installed — tournament_macd_rsi requires numpy")
            return []
        if requests is None:
            logger.error("requests library not available")
            return []

        targets = [symbol] if symbol else self.symbols
        all_signals: List[dict] = []

        for sym in targets:
            try:
                sigs = self._analyze_symbol(sym)
                all_signals.extend(sigs)
            except Exception as e:
                logger.warning("Error analyzing %s: %s", sym, e)

        return all_signals

    # ── Core Analysis ────────────────────────────────────────────────

    def _analyze_symbol(self, symbol: str) -> List[dict]:
        """Run MACD+RSI confluence analysis for one symbol."""

        candles = self._fetch_klines(symbol)
        min_bars = self.macd_slow + self.macd_signal_period + 2
        if not candles or len(candles) < min_bars:
            logger.warning("%s: insufficient data (%d candles, need %d)",
                           symbol, len(candles) if candles else 0, min_bars)
            return []

        closes = np.array([c.close for c in candles], dtype=np.float64)
        current_price = closes[-1]

        # ATR for risk management
        atr = self._calc_atr(candles)
        if atr == 0:
            return []

        # ── MACD Calculation ──────────────────────────────────────
        ema_fast = self._ema(closes, self.macd_fast)
        ema_slow = self._ema(closes, self.macd_slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, self.macd_signal_period)
        histogram = macd_line - signal_line

        # ── RSI Calculation ───────────────────────────────────────
        rsi = self._calc_rsi(closes, self.rsi_period)
        if rsi is None:
            return []

        current_rsi = rsi[-1]
        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        current_histogram = histogram[-1]
        prev_macd = macd_line[-2]
        prev_signal = signal_line[-2]

        # ── Crossover Detection ───────────────────────────────────
        bullish_cross = prev_macd <= prev_signal and current_macd > current_signal
        bearish_cross = prev_macd >= prev_signal and current_macd < current_signal

        # ── Signal Generation ─────────────────────────────────────
        direction = None
        if bullish_cross and self.rsi_lower < current_rsi < self.rsi_upper:
            direction = "BUY"
        elif bearish_cross and self.rsi_lower < current_rsi < self.rsi_upper:
            direction = "SELL"

        if direction is None:
            logger.info("%s: no MACD+RSI confluence (RSI=%.1f, cross=%s/%s)",
                        symbol, current_rsi,
                        "bull" if bullish_cross else "-",
                        "bear" if bearish_cross else "-")
            return []

        # ── Confidence Calculation ────────────────────────────────
        # Based on histogram magnitude (stronger = more confident) and
        # RSI distance from extremes (mid-range = more room to run)
        hist_strength = min(abs(current_histogram) / (atr * 0.01), 1.0)
        rsi_mid_distance = 1.0 - abs(current_rsi - 50.0) / 50.0  # 1.0 at RSI=50, 0 at extremes
        confidence = 0.30 + 0.40 * hist_strength + 0.20 * rsi_mid_distance
        confidence = max(0.25, min(0.85, confidence))

        # ── TP/SL ────────────────────────────────────────────────
        entry = current_price
        if direction == "BUY":
            tp = round(entry + atr * self.tp_mult, 2)
            sl = round(entry - atr * self.sl_mult, 2)
        else:
            tp = round(entry - atr * self.tp_mult, 2)
            sl = round(entry + atr * self.sl_mult, 2)

        reason = (
            f"Tournament MACD+RSI: {'bullish' if direction == 'BUY' else 'bearish'} MACD crossover "
            f"+ RSI({self.rsi_period})={current_rsi:.1f} in momentum zone [{self.rsi_lower}-{self.rsi_upper}] | "
            f"MACD histogram={current_histogram:.6f} | "
            f"Source: Mega Mutation Tournament (33k backtests, fitness leader family #1)"
        )

        return [{
            "symbol": symbol,
            "direction": direction,
            "confidence": round(confidence, 4),
            "entry": round(entry, 2),
            "tp": tp,
            "sl": sl,
            "timeframe": "4h",
            "strategy_name": "tournament_macd_rsi_v1",
            "reason": reason,
            "metadata": {
                "macd_line": round(current_macd, 6),
                "macd_signal": round(current_signal, 6),
                "macd_histogram": round(current_histogram, 6),
                "rsi": round(current_rsi, 2),
                "crossover": "bullish" if bullish_cross else "bearish",
                "hist_strength": round(hist_strength, 4),
                "rsi_mid_distance": round(rsi_mid_distance, 4),
                "current_price": current_price,
                "atr": round(atr, 2),
                "tournament_id": "43ca60a694d1",
            },
        }]

    # ── Technical Indicators ─────────────────────────────────────────

    @staticmethod
    def _ema(data: "np.ndarray", period: int) -> "np.ndarray":
        """Exponential Moving Average using numpy."""
        alpha = 2.0 / (period + 1)
        result = np.empty_like(data)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
        return result

    @staticmethod
    def _calc_rsi(closes: "np.ndarray", period: int = 14) -> Optional["np.ndarray"]:
        """Relative Strength Index using Wilder's smoothing."""
        if len(closes) < period + 1:
            return None

        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        rsi_values = np.empty(len(closes))
        rsi_values[:period] = 50.0  # placeholder for initial bars

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                rsi_values[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i + 1] = 100.0 - (100.0 / (1.0 + rs))

        # Fill the period-th index
        if avg_loss == 0:
            rsi_values[period] = 100.0
        else:
            rs = np.mean(gains[:period]) / np.mean(losses[:period]) if np.mean(losses[:period]) > 0 else 100.0
            rsi_values[period] = 100.0 - (100.0 / (1.0 + rs)) if isinstance(rs, float) else 100.0

        return rsi_values

    def _calc_atr(self, candles: List[Candle], period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(candles) < period + 1:
            return candles[-1].high - candles[-1].low if candles else 0

        true_ranges = []
        for i in range(1, len(candles)):
            high_low = candles[i].high - candles[i].low
            high_close = abs(candles[i].high - candles[i - 1].close)
            low_close = abs(candles[i].low - candles[i - 1].close)
            true_ranges.append(max(high_low, high_close, low_close))

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
    """Run the Tournament MACD+RSI scanner and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if np is None:
        print("\n  ERROR: numpy not installed. Install with: pip install numpy")
        return []

    strategy = TournamentMacdRsiStrategy()
    signals = strategy.generate_signals()

    print(f"\n{'=' * 75}")
    print(f"  TOURNAMENT MACD+RSI v1  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Source: Mega Mutation Tournament (33,000 backtests)")
    print(f"  MACD({strategy.macd_fast}/{strategy.macd_slow}/{strategy.macd_signal_period})"
          f" + RSI({strategy.rsi_period}) confluence")
    print(f"{'=' * 75}")

    if not signals:
        print(f"\n  No signals generated (need MACD crossover + RSI in [{RSI_LOWER}-{RSI_UPPER}])")
    else:
        for sig in signals:
            m = sig["metadata"]
            print(f"\n  {sig['symbol']}")
            print(f"  {'─' * 50}")
            print(f"  Direction:     {sig['direction']}")
            print(f"  Entry:         ${sig['entry']:,.2f}")
            print(f"  TP:            ${sig['tp']:,.2f}  |  SL: ${sig['sl']:,.2f}")
            print(f"  Confidence:    {sig['confidence']:.1%}")
            print(f"  RSI:           {m['rsi']:.1f}")
            print(f"  MACD:          {m['macd_line']:.6f} (signal: {m['macd_signal']:.6f})")
            print(f"  Histogram:     {m['macd_histogram']:.6f}")
            print(f"  Crossover:     {m['crossover']}")
            print(f"  ATR:           ${m['atr']:,.2f}")

    print(f"\n{'=' * 75}")
    print(f"  Scanned {len(strategy.symbols)} symbols, generated {len(signals)} signals")
    print(f"{'=' * 75}\n")

    return signals


if __name__ == "__main__":
    main()
