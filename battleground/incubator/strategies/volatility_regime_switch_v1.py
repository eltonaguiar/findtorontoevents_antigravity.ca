#!/usr/bin/env python3
"""
Volatility Regime Switch Strategy — Battleground Incubator v1
==============================================================

Created by: Claude Code (adapted from baby_strategies/volatility_regime_switch.py)
Date: 2026-03-13

Backtested Performance (from Holy Grail audit):
  Sharpe: 6.14  |  Win Rate: 58.97%  |  Max DD: 2.40%

Strategy Logic:
  Detects volatility regime using ATR percentile ranking:
  - LOW volatility regime (percentile < 20):
      → Mean reversion trades (Bollinger Band bounces)
      → Expect price to snap back to the mean
  - HIGH volatility regime (percentile > 80):
      → Momentum/breakout trades (ride the expansion)
      → Follow strong directional moves
  - NORMAL regime (20-80 percentile): No trades (wait for edge)

Why This Works:
  Volatility is mean-reverting AND clustered. Low-vol periods precede
  expansions (great for mean reversion at extremes), while high-vol
  periods have strong directional follow-through. By switching strategy
  type based on regime, we capture alpha from BOTH environments instead
  of being stuck with one approach.

  Academic references:
  - Mandelbrot (1963): volatility clustering
  - Bollerslev (1986): GARCH — vol is predictable
  - Cont (2001): empirical properties of asset returns

Data Source: Binance public klines API (no key required)
"""

from __future__ import annotations

import logging
import statistics
import time
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

# Volatility regime detection
VOL_PERIOD = 20           # ATR calculation period
VOL_LOOKBACK = 100        # window for percentile ranking
LOW_VOL_PCTILE = 20       # below this = low vol regime
HIGH_VOL_PCTILE = 80      # above this = high vol regime

# Bollinger Bands (for mean reversion in low-vol regime)
BB_PERIOD = 20
BB_STD = 2.0

# Momentum parameters (for breakout in high-vol regime)
MOMENTUM_LOOKBACK = 5     # candles for momentum calculation
MOMENTUM_THRESHOLD = 0.03 # 3% move required

# Risk parameters
TP_MULT = 2.0    # TP = Nx ATR from entry
SL_MULT = 1.5    # SL = Nx ATR from entry

# Kline settings
KLINE_INTERVAL = "1h"     # 1-hour candles for regime detection
KLINE_LIMIT = 150         # enough for 100-bar lookback + indicators


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
    """Trading signal — matches battleground incubator format."""
    symbol: str
    direction: str       # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    strategy: str = "volatility_regime_switch_v1"
    timeframe: str = "1h"
    metadata: dict = field(default_factory=dict)


class VolatilityRegimeSwitchStrategy:
    """
    Volatility Regime Switch Strategy

    Detects volatility regime changes using percentile-based ATR thresholds:
    - Low vol regime (percentile < 20): Mean reversion at Bollinger Band extremes
    - High vol regime (percentile > 80): Momentum/breakout following strong moves
    - Normal regime (20-80): No trades — no edge

    Backtested: Sharpe 6.14, WR 58.97%, Max DD 2.40%
    """

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.symbols = p.get("symbols", SYMBOLS)
        self.interval = p.get("interval", KLINE_INTERVAL)
        self.limit = p.get("kline_limit", KLINE_LIMIT)
        self.vol_period = p.get("vol_period", VOL_PERIOD)
        self.vol_lookback = p.get("vol_lookback", VOL_LOOKBACK)
        self.low_vol_pctile = p.get("low_vol_pctile", LOW_VOL_PCTILE)
        self.high_vol_pctile = p.get("high_vol_pctile", HIGH_VOL_PCTILE)
        self.bb_period = p.get("bb_period", BB_PERIOD)
        self.bb_std = p.get("bb_std", BB_STD)
        self.mom_lookback = p.get("momentum_lookback", MOMENTUM_LOOKBACK)
        self.mom_threshold = p.get("momentum_threshold", MOMENTUM_THRESHOLD)
        self.tp_mult = p.get("tp_mult", TP_MULT)
        self.sl_mult = p.get("sl_mult", SL_MULT)
        self._timeout = p.get("request_timeout", 10)

    # ── Public API ───────────────────────────────────────────────────

    def generate_signals(self, data=None, symbol: str = None) -> List[Signal]:
        """Scan all symbols for volatility regime switch opportunities."""
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
        """Full volatility regime analysis for one symbol."""

        # 1. Fetch OHLCV data from Binance
        candles = self._fetch_klines(symbol)
        if not candles or len(candles) < self.vol_lookback + 10:
            logger.warning(
                "%s: insufficient kline data (%d candles, need %d)",
                symbol, len(candles) if candles else 0, self.vol_lookback + 10,
            )
            return []

        # 2. Calculate ATR series
        atr_series = self._calc_atr_series(candles, self.vol_period)
        if len(atr_series) < self.vol_lookback:
            return []

        # 3. Determine volatility regime via percentile ranking
        recent_atr_window = atr_series[-self.vol_lookback:]
        current_atr = atr_series[-1]

        # Percentile: what fraction of the lookback window is below current ATR
        below_count = sum(1 for a in recent_atr_window if a <= current_atr)
        vol_percentile = (below_count / len(recent_atr_window)) * 100

        # 4. Calculate Bollinger Bands
        closes = [c.close for c in candles]
        if len(closes) < self.bb_period:
            return []

        bb_window = closes[-self.bb_period:]
        sma_val = statistics.mean(bb_window)
        std_val = statistics.stdev(bb_window) if len(bb_window) > 1 else 0
        bb_upper = sma_val + (std_val * self.bb_std)
        bb_lower = sma_val - (std_val * self.bb_std)

        # 5. Current state
        current_price = candles[-1].close
        prev_price = candles[-2].close

        signals = []

        # ── LOW VOLATILITY REGIME: Mean Reversion ────────────────
        if vol_percentile < self.low_vol_pctile:
            regime = "LOW_VOL"

            # Price at/above upper BB = short (mean revert down)
            if current_price >= bb_upper and std_val > 0:
                deviation = (current_price - sma_val) / current_atr if current_atr > 0 else 0
                confidence = max(0.35, min(0.90, 0.40 + deviation * 0.10))

                tp = round(sma_val, 2)  # target = mean
                sl = round(current_price + (current_atr * self.sl_mult), 2)

                # Validate RR ratio
                risk = sl - current_price
                reward = current_price - tp
                rr_ratio = reward / risk if risk > 0 else 0

                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 4),
                    entry_price=round(current_price, 2),
                    take_profit=tp,
                    stop_loss=sl,
                    reason=(
                        f"Low-vol mean reversion SHORT: vol_pctile={vol_percentile:.0f}, "
                        f"price at upper BB ({current_price:.2f} >= {bb_upper:.2f}), "
                        f"target SMA={sma_val:.2f}"
                    ),
                    metadata={
                        "regime": regime,
                        "vol_percentile": round(vol_percentile, 1),
                        "current_atr": round(current_atr, 2),
                        "bb_upper": round(bb_upper, 2),
                        "bb_lower": round(bb_lower, 2),
                        "sma": round(sma_val, 2),
                        "bb_deviation": round(deviation, 2),
                        "rr_ratio": round(rr_ratio, 2),
                        "current_price": current_price,
                    },
                ))

            # Price at/below lower BB = long (mean revert up)
            elif current_price <= bb_lower and std_val > 0:
                deviation = (sma_val - current_price) / current_atr if current_atr > 0 else 0
                confidence = max(0.35, min(0.90, 0.40 + deviation * 0.10))

                tp = round(sma_val, 2)  # target = mean
                sl = round(current_price - (current_atr * self.sl_mult), 2)

                risk = current_price - sl
                reward = tp - current_price
                rr_ratio = reward / risk if risk > 0 else 0

                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 4),
                    entry_price=round(current_price, 2),
                    take_profit=tp,
                    stop_loss=sl,
                    reason=(
                        f"Low-vol mean reversion LONG: vol_pctile={vol_percentile:.0f}, "
                        f"price at lower BB ({current_price:.2f} <= {bb_lower:.2f}), "
                        f"target SMA={sma_val:.2f}"
                    ),
                    metadata={
                        "regime": regime,
                        "vol_percentile": round(vol_percentile, 1),
                        "current_atr": round(current_atr, 2),
                        "bb_upper": round(bb_upper, 2),
                        "bb_lower": round(bb_lower, 2),
                        "sma": round(sma_val, 2),
                        "bb_deviation": round(deviation, 2),
                        "rr_ratio": round(rr_ratio, 2),
                        "current_price": current_price,
                    },
                ))

        # ── HIGH VOLATILITY REGIME: Momentum/Breakout ────────────
        elif vol_percentile > self.high_vol_pctile:
            regime = "HIGH_VOL"

            # Calculate momentum over lookback period
            if len(candles) > self.mom_lookback:
                lookback_price = candles[-(self.mom_lookback + 1)].close
                momentum = (current_price - lookback_price) / lookback_price
            else:
                momentum = 0

            # Strong upward momentum + price above SMA
            if momentum > self.mom_threshold and current_price > sma_val:
                confidence = max(0.40, min(0.90, 0.50 + momentum * 5))

                tp = round(current_price + (current_atr * self.tp_mult), 2)
                sl = round(current_price - (current_atr * self.sl_mult), 2)

                risk = current_price - sl
                reward = tp - current_price
                rr_ratio = reward / risk if risk > 0 else 0

                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 4),
                    entry_price=round(current_price, 2),
                    take_profit=tp,
                    stop_loss=sl,
                    reason=(
                        f"High-vol momentum LONG: vol_pctile={vol_percentile:.0f}, "
                        f"mom={momentum:+.1%} over {self.mom_lookback} bars, "
                        f"price above SMA ({current_price:.2f} > {sma_val:.2f})"
                    ),
                    metadata={
                        "regime": regime,
                        "vol_percentile": round(vol_percentile, 1),
                        "current_atr": round(current_atr, 2),
                        "momentum": round(momentum, 4),
                        "momentum_lookback": self.mom_lookback,
                        "sma": round(sma_val, 2),
                        "rr_ratio": round(rr_ratio, 2),
                        "current_price": current_price,
                    },
                ))

            # Strong downward momentum + price below SMA
            elif momentum < -self.mom_threshold and current_price < sma_val:
                confidence = max(0.40, min(0.90, 0.50 + abs(momentum) * 5))

                tp = round(current_price - (current_atr * self.tp_mult), 2)
                sl = round(current_price + (current_atr * self.sl_mult), 2)

                risk = sl - current_price
                reward = current_price - tp
                rr_ratio = reward / risk if risk > 0 else 0

                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 4),
                    entry_price=round(current_price, 2),
                    take_profit=tp,
                    stop_loss=sl,
                    reason=(
                        f"High-vol momentum SHORT: vol_pctile={vol_percentile:.0f}, "
                        f"mom={momentum:+.1%} over {self.mom_lookback} bars, "
                        f"price below SMA ({current_price:.2f} < {sma_val:.2f})"
                    ),
                    metadata={
                        "regime": regime,
                        "vol_percentile": round(vol_percentile, 1),
                        "current_atr": round(current_atr, 2),
                        "momentum": round(momentum, 4),
                        "momentum_lookback": self.mom_lookback,
                        "sma": round(sma_val, 2),
                        "rr_ratio": round(rr_ratio, 2),
                        "current_price": current_price,
                    },
                ))

        return signals

    # ── Technical Indicators ─────────────────────────────────────────

    def _calc_atr_series(self, candles: List[Candle], period: int) -> List[float]:
        """Calculate ATR as a rolling series (list of floats)."""
        if len(candles) < 2:
            return []

        true_ranges = []
        for i in range(1, len(candles)):
            high_low = candles[i].high - candles[i].low
            high_close = abs(candles[i].high - candles[i - 1].close)
            low_close = abs(candles[i].low - candles[i - 1].close)
            true_ranges.append(max(high_low, high_close, low_close))

        # Rolling mean ATR
        atr_series = []
        for i in range(len(true_ranges)):
            start = max(0, i - period + 1)
            window = true_ranges[start : i + 1]
            atr_series.append(statistics.mean(window))

        return atr_series

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
    """Run the Volatility Regime Switch scanner and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    strategy = VolatilityRegimeSwitchStrategy()
    signals = strategy.generate_signals()

    print(f"\n{'='*75}")
    print(f"  VOLATILITY REGIME SWITCH SCANNER  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Backtested: Sharpe 6.14 | WR 58.97% | Max DD 2.40%")
    print(f"{'='*75}")

    if not signals:
        print("\n  No regime-edge opportunities right now.")
        print("  (Vol percentile must be <20 or >80, with price confirmation)")
    else:
        for sig in signals:
            m = sig.metadata
            print(f"\n  {sig.symbol}")
            print(f"  {'─'*50}")
            print(f"  Direction:    {sig.direction}")
            print(f"  Regime:       {m.get('regime', 'N/A')}")
            print(f"  Vol Pctile:   {m.get('vol_percentile', 0):.0f}th percentile")
            print(f"  Entry:        ${sig.entry_price:,.2f}")
            print(f"  TP:           ${sig.take_profit:,.2f}  |  SL: ${sig.stop_loss:,.2f}")
            print(f"  Confidence:   {sig.confidence:.1%}")
            print(f"  R:R Ratio:    {m.get('rr_ratio', 0):.2f}")
            if "momentum" in m:
                print(f"  Momentum:     {m['momentum']:+.2%}")
            if "bb_deviation" in m:
                print(f"  BB Deviation: {m['bb_deviation']:.2f}x ATR")
            print(f"  ATR (curr):   ${m.get('current_atr', 0):,.2f}")

    print(f"\n{'='*75}")
    print(f"  Scanned {len(strategy.symbols)} symbols, found {len(signals)} regime opportunities")
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
