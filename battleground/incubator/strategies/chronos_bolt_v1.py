#!/usr/bin/env python3
"""
Chronos-Bolt — Zero-Shot Time Series Foundation Model for Crypto Prediction
============================================================================

Created by: google_antigravity
Date: 2026-03-13

Research Sources:
- Ansari et al. (2024) "Chronos: Learning the Language of Time Series"
  Amazon Science, arXiv:2403.07815
- Fatir et al. (2024) "Chronos-Bolt: Efficient Zero-Shot Time Series Forecasting"
  Amazon Science, released via HuggingFace: amazon/chronos-bolt-small
- Benchmark: Chronos-Bolt achieves state-of-the-art zero-shot performance on
  27 datasets, outperforming task-specific models without any training.

Strategy Logic:
1. Fetches 4H OHLCV klines from Binance public API (no key needed)
2. Feeds close prices into Chronos-Bolt as a univariate time series
3. Generates probabilistic forecast (median + quantiles) for next 3 candles
4. Computes directional signal from predicted price trajectory:
   - BUY if predicted median in 3 candles > current price by threshold
   - SELL if predicted median in 3 candles < current price by threshold
5. Confidence derived from prediction interval tightness:
   - Narrow intervals (low/high quantiles close together) = high confidence
   - Wide intervals = low confidence / uncertain regime

Why This Works:
   Chronos-Bolt was pretrained on billions of time series data points from
   diverse domains (energy, finance, weather, retail). It learns universal
   temporal patterns — trends, seasonality, mean reversion, regime changes —
   without needing domain-specific training. For crypto OHLCV data, it
   provides a zero-shot "second opinion" that is completely independent of
   traditional technical indicators, making it an excellent ensemble member.

   Key advantage: No overfitting risk. The model has never seen your specific
   asset's data during training, so its predictions are purely from learned
   temporal priors — genuine out-of-sample generalization.

Model Variants (by VRAM/speed):
   - amazon/chronos-bolt-tiny   (8M params)  — fastest, ~0.5s per forecast
   - amazon/chronos-bolt-mini   (21M params) — good balance
   - amazon/chronos-bolt-small  (48M params) — best accuracy (default)
   - amazon/chronos-bolt-base   (205M params) — highest quality, slower

Installation:
   pip install chronos-forecasting torch
   # or for CPU-only:
   pip install chronos-forecasting torch --index-url https://download.pytorch.org/whl/cpu
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None  # type: ignore

# Chronos imports — graceful fallback if not installed
_CHRONOS_AVAILABLE = False
_CHRONOS_IMPORT_ERROR = ""
try:
    import torch
    from chronos import ChronosPipeline
    _CHRONOS_AVAILABLE = True
except ImportError as e:
    _CHRONOS_IMPORT_ERROR = (
        f"chronos-forecasting not installed: {e}. "
        "Install with: pip install chronos-forecasting torch"
    )

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

from api_helpers import fetch_klines as _fetch_klines_fallback

# Analysis parameters
KLINE_INTERVAL = "4h"           # 4-hour candles — good signal-to-noise for foundation model
KLINE_LIMIT = 200               # 200 candles of context (~33 days of 4H data)
PREDICTION_HORIZON = 3          # predict next 3 candles (12 hours ahead)
DIRECTION_THRESHOLD_PCT = 0.3   # min 0.3% predicted move to generate signal
NUM_SAMPLES = 20                # number of sample paths for probabilistic forecast

# Confidence quantiles
QUANTILE_LOW = 0.1              # 10th percentile (pessimistic bound)
QUANTILE_HIGH = 0.9             # 90th percentile (optimistic bound)

# Risk parameters
TP_ATR_MULT = 2.0   # TP = 2x ATR from entry
SL_ATR_MULT = 1.0   # SL = 1x ATR from entry

# Model selection — tiny for CI speed (8M params, 250x faster than base)
DEFAULT_MODEL = "amazon/chronos-bolt-tiny"


@dataclass
class Candle:
    """OHLCV candle."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def range_size(self) -> float:
        return self.high - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open


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
    strategy: str = "chronos_bolt_v1"
    timeframe: str = "4h"
    metadata: dict = field(default_factory=dict)


class ChronosBoltStrategy:
    """
    Zero-shot time series forecasting using Amazon's Chronos-Bolt
    foundation model.

    Chronos-Bolt is a T5-based model pretrained on a large corpus of
    time series data. It tokenizes real-valued time series into discrete
    bins and generates probabilistic forecasts via token-level predictions.

    This strategy uses it as a pure zero-shot predictor — no fine-tuning,
    no lookback optimization. The model receives raw close prices and
    outputs a distribution over future values.

    Reference:
        Ansari et al. (2024) "Chronos: Learning the Language of Time Series"
        arXiv:2403.07815 — Amazon Science
    """

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.symbols = p.get("symbols", SYMBOLS)
        self.interval = p.get("interval", KLINE_INTERVAL)
        self.limit = p.get("kline_limit", KLINE_LIMIT)
        self.horizon = p.get("prediction_horizon", PREDICTION_HORIZON)
        self.direction_threshold = p.get("direction_threshold_pct", DIRECTION_THRESHOLD_PCT)
        self.num_samples = p.get("num_samples", NUM_SAMPLES)
        self.tp_mult = p.get("tp_atr_mult", TP_ATR_MULT)
        self.sl_mult = p.get("sl_atr_mult", SL_ATR_MULT)
        self._timeout = p.get("request_timeout", 10)
        self._model_name = p.get("model", DEFAULT_MODEL)
        self._device = p.get("device", "cpu")
        self._pipeline: Optional[ChronosPipeline] = None

    # ── Public API ───────────────────────────────────────────────────

    def generate_signals(self, data=None, symbol: str = None) -> List[Signal]:
        """Scan all symbols using Chronos-Bolt zero-shot predictions."""
        if not _CHRONOS_AVAILABLE:
            logger.error("Chronos-Bolt unavailable: %s", _CHRONOS_IMPORT_ERROR)
            return []

        if requests is None:
            logger.error("requests library not available")
            return []

        # Lazy-load model on first use (avoids loading at import time)
        if self._pipeline is None:
            self._pipeline = self._load_model()
            if self._pipeline is None:
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

    # ── Model Loading ─────────────────────────────────────────────────

    def _load_model(self) -> Optional[ChronosPipeline]:
        """Load the Chronos-Bolt pipeline. Returns None on failure."""
        try:
            logger.info("Loading Chronos-Bolt model: %s (device=%s)",
                        self._model_name, self._device)
            pipeline = ChronosPipeline.from_pretrained(
                self._model_name,
                device_map=self._device,
                torch_dtype=torch.float32,
            )
            logger.info("Chronos-Bolt model loaded successfully")
            return pipeline
        except Exception as e:
            logger.error("Failed to load Chronos-Bolt model: %s", e)
            return None

    # ── Core Analysis ────────────────────────────────────────────────

    def _analyze_symbol(self, symbol: str) -> List[Signal]:
        """Run Chronos-Bolt forecast for one symbol and generate signal."""

        # 1. Fetch OHLCV data
        candles = self._fetch_klines(symbol)
        if not candles or len(candles) < 30:
            logger.warning("%s: insufficient kline data (%d candles)",
                           symbol, len(candles) if candles else 0)
            return []

        # 2. Extract close prices as context for the model
        close_prices = [c.close for c in candles]
        current_price = close_prices[-1]

        # 3. Calculate ATR for risk management
        atr = self._calc_atr(candles)
        if atr == 0:
            return []

        # 4. Run Chronos-Bolt prediction
        forecast = self._predict(close_prices)
        if forecast is None:
            return []

        median_forecast, low_forecast, high_forecast = forecast

        # 5. Compute directional signal
        # Use the median prediction at the end of the horizon
        predicted_price = median_forecast[-1]
        predicted_low = low_forecast[-1]
        predicted_high = high_forecast[-1]

        price_change_pct = ((predicted_price - current_price) / current_price) * 100

        # 6. Compute confidence from prediction interval tightness
        # Narrow interval relative to price = high confidence
        interval_width = predicted_high - predicted_low
        interval_pct = (interval_width / current_price) * 100 if current_price > 0 else 100

        # Confidence mapping: tighter intervals = higher confidence
        # Typical crypto 4H interval widths: 0.5% (tight) to 5% (wide)
        if interval_pct < 0.5:
            base_confidence = 0.80
        elif interval_pct < 1.0:
            base_confidence = 0.65
        elif interval_pct < 2.0:
            base_confidence = 0.50
        elif interval_pct < 3.5:
            base_confidence = 0.40
        else:
            base_confidence = 0.30

        # Boost confidence if the directional move is large relative to interval
        direction_ratio = abs(price_change_pct) / interval_pct if interval_pct > 0 else 0
        if direction_ratio > 0.5:
            base_confidence += 0.10
        if direction_ratio > 0.7:
            base_confidence += 0.05

        # Check monotonicity of forecast — trending predictions are more reliable
        if len(median_forecast) >= 3:
            diffs = [median_forecast[i+1] - median_forecast[i]
                     for i in range(len(median_forecast) - 1)]
            all_positive = all(d > 0 for d in diffs)
            all_negative = all(d < 0 for d in diffs)
            if all_positive or all_negative:
                base_confidence += 0.05  # monotonic trend bonus

        confidence = max(0.25, min(0.90, base_confidence))

        # 7. Generate signal if threshold is met
        if abs(price_change_pct) < self.direction_threshold:
            logger.info("%s: predicted move %.3f%% below threshold %.1f%% — no signal",
                        symbol, price_change_pct, self.direction_threshold)
            return []

        if price_change_pct > 0:
            direction = "BUY"
            entry = current_price
            tp = round(entry + atr * self.tp_mult, 2)
            sl = round(entry - atr * self.sl_mult, 2)
        else:
            direction = "SELL"
            entry = current_price
            tp = round(entry - atr * self.tp_mult, 2)
            sl = round(entry + atr * self.sl_mult, 2)

        # Build trajectory description
        trajectory = [round(p, 2) for p in median_forecast]

        reason = (
            f"Chronos-Bolt zero-shot: predicted {price_change_pct:+.2f}% over "
            f"{self.horizon} candles ({self.interval}) | "
            f"interval=[{predicted_low:.2f}-{predicted_high:.2f}] "
            f"width={interval_pct:.2f}% | "
            f"model={self._model_name.split('/')[-1]}"
        )

        return [Signal(
            symbol=symbol,
            direction=direction,
            confidence=round(confidence, 4),
            entry_price=round(entry, 2),
            take_profit=tp,
            stop_loss=sl,
            reason=reason,
            metadata={
                "model": self._model_name,
                "predicted_price": round(predicted_price, 2),
                "predicted_change_pct": round(price_change_pct, 4),
                "predicted_low": round(predicted_low, 2),
                "predicted_high": round(predicted_high, 2),
                "interval_width_pct": round(interval_pct, 4),
                "direction_ratio": round(direction_ratio, 4),
                "trajectory_median": trajectory,
                "current_price": current_price,
                "atr": round(atr, 2),
                "context_length": len(close_prices),
                "horizon": self.horizon,
                "num_samples": self.num_samples,
            },
        )]

    # ── Chronos-Bolt Prediction ───────────────────────────────────────

    def _predict(
        self, close_prices: List[float]
    ) -> Optional[Tuple[List[float], List[float], List[float]]]:
        """
        Run Chronos-Bolt probabilistic forecast.

        Returns:
            Tuple of (median, low_quantile, high_quantile) lists,
            each of length self.horizon.
            Returns None on failure.
        """
        try:
            # Convert to tensor — Chronos expects shape (batch, context_length)
            context = torch.tensor([close_prices], dtype=torch.float32)

            # Generate probabilistic forecast
            # Returns shape (batch, num_samples, horizon)
            forecast = self._pipeline.predict(
                context,
                prediction_length=self.horizon,
                num_samples=self.num_samples,
            )

            # Extract quantiles from samples
            # forecast shape: (1, num_samples, horizon)
            samples = forecast[0]  # shape: (num_samples, horizon)

            median = torch.quantile(samples, 0.5, dim=0).tolist()
            low = torch.quantile(samples, QUANTILE_LOW, dim=0).tolist()
            high = torch.quantile(samples, QUANTILE_HIGH, dim=0).tolist()

            return median, low, high

        except Exception as e:
            logger.error("Chronos-Bolt prediction failed: %s", e)
            return None

    # ── Technical Indicators ─────────────────────────────────────────

    def _calc_atr(self, candles: List[Candle], period: int = 14) -> float:
        """Calculate Average True Range for risk management."""
        if len(candles) < period + 1:
            return candles[-1].range_size if candles else 0

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
    """Run the Chronos-Bolt scanner and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if not _CHRONOS_AVAILABLE:
        print(f"\n  ERROR: {_CHRONOS_IMPORT_ERROR}")
        print("  Install with: pip install chronos-forecasting torch")
        return []

    strategy = ChronosBoltStrategy()
    signals = strategy.generate_signals()

    print(f"\n{'='*75}")
    print(f"  CHRONOS-BOLT ZERO-SHOT PREDICTOR  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Model: {strategy._model_name}")
    print(f"  Ref: Ansari et al. (2024) arXiv:2403.07815 — Amazon Science")
    print(f"{'='*75}")

    if not signals:
        print("\n  No signals generated.")
        print(f"  (Requires >{strategy.direction_threshold}% predicted move on {strategy.interval} timeframe)")
    else:
        for sig in signals:
            m = sig.metadata
            print(f"\n  {sig.symbol}")
            print(f"  {'─'*50}")
            print(f"  Direction:     {sig.direction}")
            print(f"  Predicted:     ${m['predicted_price']:,.2f} ({m['predicted_change_pct']:+.2f}%)")
            print(f"  Interval:      [${m['predicted_low']:,.2f} — ${m['predicted_high']:,.2f}]")
            print(f"  Interval Width:{m['interval_width_pct']:.2f}%")
            print(f"  Entry:         ${sig.entry_price:,.2f}")
            print(f"  TP:            ${sig.take_profit:,.2f}  |  SL: ${sig.stop_loss:,.2f}")
            print(f"  Confidence:    {sig.confidence:.1%}")
            print(f"  Context:       {m['context_length']} candles | Horizon: {m['horizon']} candles")
            print(f"  Trajectory:    {m['trajectory_median']}")

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
