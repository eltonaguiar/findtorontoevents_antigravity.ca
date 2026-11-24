#!/usr/bin/env python3
"""
Tournament EMA Momentum Breakout — Mega Mutation Tournament Winner #2
======================================================================

Created by: google_antigravity
Date: 2026-03-13

Research Source:
- Mega Mutation Tournament (33,000 backtests across 1,000 mutations × 33 symbols)
- Tournament ID: 43ca60a694d1
- Key finding: EMA momentum breakouts were the second-dominant mutation family,
  particularly effective on high-volatility altcoins with volume confirmation.

Strategy Logic:
1. Fetches 4H OHLCV klines from Binance public API (via api_helpers fallback chain)
2. Computes EMA(9) and EMA(21)
3. Computes 20-period average volume for confirmation
4. BUY: EMA9 > EMA21 AND close > EMA21 AND volume > 1.2× avg_volume
5. SELL: EMA9 < EMA21 AND close < EMA21 AND volume > 1.2× avg_volume
6. Confidence derived from EMA separation percentage + volume ratio
7. TP/SL based on ATR(14) — 2.0× / 1.2× (wider R:R for momentum trades)

Target Symbols (tournament momentum performers):
- AVAXUSDT  (max_fitness: 0.845 in RENDERUSDT cluster)
- RENDERUSDT (max_fitness: 0.845 — highest single mutation score)
- WIFUSDT   (robust_count: 208, consistency: 3.239)
- STXUSDT   (max_fitness: 0.828, consistency: 3.045)
- ENAUSDT   (avg_fitness: 0.534, top-10 avg: 0.826)

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
SYMBOLS = ["AVAXUSDT", "RENDERUSDT", "WIFUSDT", "STXUSDT", "ENAUSDT"]

KLINE_INTERVAL = "4h"
KLINE_LIMIT = 200  # ~33 days of 4H candles

# EMA parameters
EMA_FAST = 9
EMA_SLOW = 21

# Volume confirmation
VOLUME_AVG_PERIOD = 20
VOLUME_THRESHOLD = 1.2  # require 1.2× average volume

# Risk parameters (wider for momentum — from tournament R:R analysis)
TP_ATR_MULT = 2.0
SL_ATR_MULT = 1.2


@dataclass
class Candle:
    """OHLCV candle."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class TournamentEmaMomentumStrategy:
    """
    EMA Momentum Breakout strategy derived from Mega Mutation Tournament results.

    The tournament's 33,000 backtests showed EMA crossover + volume confirmation
    as the second-strongest mutation family. Wider TP/SL ratios (2.0/1.2) let
    winners run on momentum-driven altcoins.
    """

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.symbols = p.get("symbols", SYMBOLS)
        self.interval = p.get("interval", KLINE_INTERVAL)
        self.limit = p.get("kline_limit", KLINE_LIMIT)
        self.ema_fast = p.get("ema_fast", EMA_FAST)
        self.ema_slow = p.get("ema_slow", EMA_SLOW)
        self.vol_avg_period = p.get("volume_avg_period", VOLUME_AVG_PERIOD)
        self.vol_threshold = p.get("volume_threshold", VOLUME_THRESHOLD)
        self.tp_mult = p.get("tp_atr_mult", TP_ATR_MULT)
        self.sl_mult = p.get("sl_atr_mult", SL_ATR_MULT)
        self._timeout = p.get("request_timeout", 10)

    # ── Public API ───────────────────────────────────────────────────

    def generate_signals(self, data=None, symbol: str = None) -> List[dict]:
        """Scan symbols using EMA momentum breakout from tournament DNA."""
        if np is None:
            logger.error("numpy not installed — tournament_ema_momentum requires numpy")
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
        """Run EMA momentum breakout analysis for one symbol."""

        candles = self._fetch_klines(symbol)
        min_bars = self.ema_slow + self.vol_avg_period + 2
        if not candles or len(candles) < min_bars:
            logger.warning("%s: insufficient data (%d candles, need %d)",
                           symbol, len(candles) if candles else 0, min_bars)
            return []

        closes = np.array([c.close for c in candles], dtype=np.float64)
        volumes = np.array([c.volume for c in candles], dtype=np.float64)
        current_price = closes[-1]
        current_volume = volumes[-1]

        # ATR for risk management
        atr = self._calc_atr(candles)
        if atr == 0:
            return []

        # ── EMA Calculation ───────────────────────────────────────
        ema_fast = self._ema(closes, self.ema_fast)
        ema_slow = self._ema(closes, self.ema_slow)

        current_ema_fast = ema_fast[-1]
        current_ema_slow = ema_slow[-1]

        # ── Volume Confirmation ───────────────────────────────────
        avg_volume = np.mean(volumes[-self.vol_avg_period:])
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0.0
        volume_confirmed = volume_ratio >= self.vol_threshold

        # ── EMA Crossover Detection ──────────────────────────────
        prev_ema_fast = ema_fast[-2]
        prev_ema_slow = ema_slow[-2]
        bullish_cross = prev_ema_fast <= prev_ema_slow and current_ema_fast > current_ema_slow
        bearish_cross = prev_ema_fast >= prev_ema_slow and current_ema_fast < current_ema_slow

        # ── Signal Generation ─────────────────────────────────────
        direction = None
        if current_ema_fast > current_ema_slow and current_price > current_ema_slow and volume_confirmed:
            direction = "BUY"
        elif current_ema_fast < current_ema_slow and current_price < current_ema_slow and volume_confirmed:
            direction = "SELL"

        if direction is None:
            logger.info(
                "%s: no EMA momentum signal (EMA9=%s EMA21, price %s EMA21, vol_ratio=%.2f)",
                symbol,
                ">" if current_ema_fast > current_ema_slow else "<",
                ">" if current_price > current_ema_slow else "<",
                volume_ratio,
            )
            return []

        # Only signal on fresh crossovers or strong continuation
        ema_separation_pct = abs(current_ema_fast - current_ema_slow) / current_ema_slow * 100
        is_fresh_cross = bullish_cross or bearish_cross

        # Skip if EMAs have been separated too long without a fresh cross
        # (avoids late entries in established trends)
        if not is_fresh_cross and ema_separation_pct > 3.0:
            logger.info("%s: EMA separation %.2f%% too wide for non-crossover entry",
                        symbol, ema_separation_pct)
            return []

        # ── Confidence Calculation ────────────────────────────────
        # Fresh crossovers get a boost; volume ratio adds confidence
        cross_bonus = 0.15 if is_fresh_cross else 0.0
        ema_sep_score = min(ema_separation_pct / 2.0, 1.0)  # normalize separation
        vol_score = min((volume_ratio - 1.0) / 1.0, 1.0)  # how much above average
        confidence = 0.30 + cross_bonus + 0.25 * ema_sep_score + 0.20 * vol_score
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
            f"Tournament EMA Momentum: EMA({self.ema_fast}) {'>' if direction == 'BUY' else '<'} "
            f"EMA({self.ema_slow}) {'+ fresh crossover ' if is_fresh_cross else ''}"
            f"+ volume {volume_ratio:.1f}× avg (threshold: {self.vol_threshold}×) | "
            f"EMA separation: {ema_separation_pct:.2f}% | "
            f"Source: Mega Mutation Tournament (33k backtests, family #2)"
        )

        return [{
            "symbol": symbol,
            "direction": direction,
            "confidence": round(confidence, 4),
            "entry": round(entry, 2),
            "tp": tp,
            "sl": sl,
            "timeframe": "4h",
            "strategy_name": "tournament_ema_momentum_v1",
            "reason": reason,
            "metadata": {
                "ema_fast": round(current_ema_fast, 2),
                "ema_slow": round(current_ema_slow, 2),
                "ema_separation_pct": round(ema_separation_pct, 4),
                "is_fresh_cross": is_fresh_cross,
                "volume_ratio": round(volume_ratio, 4),
                "avg_volume": round(avg_volume, 2),
                "current_volume": round(current_volume, 2),
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
    """Run the Tournament EMA Momentum scanner and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if np is None:
        print("\n  ERROR: numpy not installed. Install with: pip install numpy")
        return []

    strategy = TournamentEmaMomentumStrategy()
    signals = strategy.generate_signals()

    print(f"\n{'=' * 75}")
    print(f"  TOURNAMENT EMA MOMENTUM v1  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Source: Mega Mutation Tournament (33,000 backtests)")
    print(f"  EMA({strategy.ema_fast}/{strategy.ema_slow}) crossover + volume confirmation")
    print(f"{'=' * 75}")

    if not signals:
        print(f"\n  No signals generated (need EMA cross + vol > {VOLUME_THRESHOLD}× avg)")
    else:
        for sig in signals:
            m = sig["metadata"]
            print(f"\n  {sig['symbol']}")
            print(f"  {'─' * 50}")
            print(f"  Direction:     {sig['direction']}")
            print(f"  Entry:         ${sig['entry']:,.2f}")
            print(f"  TP:            ${sig['tp']:,.2f}  |  SL: ${sig['sl']:,.2f}")
            print(f"  Confidence:    {sig['confidence']:.1%}")
            print(f"  EMA9:          ${m['ema_fast']:,.2f}  |  EMA21: ${m['ema_slow']:,.2f}")
            print(f"  Separation:    {m['ema_separation_pct']:.2f}%")
            print(f"  Fresh Cross:   {'YES' if m['is_fresh_cross'] else 'NO'}")
            print(f"  Volume Ratio:  {m['volume_ratio']:.2f}×")
            print(f"  ATR:           ${m['atr']:,.2f}")

    print(f"\n{'=' * 75}")
    print(f"  Scanned {len(strategy.symbols)} symbols, generated {len(signals)} signals")
    print(f"{'=' * 75}\n")

    return signals


if __name__ == "__main__":
    main()
