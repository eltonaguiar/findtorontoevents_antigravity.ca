#!/usr/bin/env python3
"""
DLinear Baseline — Simple Linear Decomposition for Time Series Prediction
==========================================================================

Created by: google_antigravity
Date: 2026-03-13

Research Source:
- Zeng et al. (2023) "Are Transformers Effective for Time Series Forecasting?"
  AAAI 2023, arXiv:2205.13504
- Key finding: A single linear layer (DLinear) often matches or beats complex
  Transformer models (FEDformer, Autoformer, Informer) on short-horizon
  forecasting benchmarks, at a fraction of the compute cost.

Strategy Logic:
1. Fetches 4H OHLCV klines from Binance public API (no key needed)
2. Decomposes close prices into Trend (SMA) + Residual (Seasonal) components
3. Fits separate linear regressions on each component (pure numpy, no PyTorch)
4. Predicts next close = predicted_trend + predicted_residual
5. BUY if predicted price > current by threshold; SELL if below
6. Confidence derived from R-squared of both linear fits

Why This Works:
   DLinear's insight is that most time series forecasting power comes from
   capturing the trend and seasonal decomposition — not from attention
   mechanisms. By fitting independent linear projections on trend and
   residual components, we get a fast, interpretable baseline that is
   surprisingly competitive.

   As a battleground incubator strategy, this serves as the "beat this"
   baseline. Any strategy that can't outperform DLinear on walk-forward
   testing shouldn't be promoted to production.

Dependencies: numpy, requests (no PyTorch needed)
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

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ENAUSDT", "JUPUSDT", "WIFUSDT", "STXUSDT", "RENDERUSDT"]

from api_helpers import fetch_klines as _fetch_klines_fallback

KLINE_INTERVAL = "4h"
KLINE_LIMIT = 200               # 200 candles context (~33 days)
SMA_WINDOW = 25                 # trend decomposition window
LOOKBACK = 50                   # how many bars to fit the linear models on
DIRECTION_THRESHOLD_PCT = 0.3   # min predicted move to signal

# Risk parameters
TP_ATR_MULT = 1.5   # TP = 1.5x ATR
SL_ATR_MULT = 1.0   # SL = 1x ATR


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
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    strategy: str = "dlinear_baseline_v1"
    timeframe: str = "4h"
    metadata: dict = field(default_factory=dict)


def _linear_regression(y: "np.ndarray"):
    """
    Ordinary least-squares fit: y = a*x + b.
    Returns (slope, intercept, r_squared).
    """
    n = len(y)
    x = np.arange(n, dtype=np.float64)
    x_mean = x.mean()
    y_mean = y.mean()
    ss_xy = np.sum((x - x_mean) * (y - y_mean))
    ss_xx = np.sum((x - x_mean) ** 2)
    if ss_xx == 0:
        return 0.0, float(y_mean), 0.0
    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    r_sq = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    return float(slope), float(intercept), float(max(0.0, r_sq))


class DLinearBaselineStrategy:
    """
    DLinear decomposition baseline (Zeng et al., AAAI 2023).

    Decomposes price into trend (SMA) and residual, fits independent
    linear regressions on each, and sums the projections to forecast
    the next bar's close price.
    """

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.symbols = p.get("symbols", SYMBOLS)
        self.interval = p.get("interval", KLINE_INTERVAL)
        self.limit = p.get("kline_limit", KLINE_LIMIT)
        self.sma_window = p.get("sma_window", SMA_WINDOW)
        self.lookback = p.get("lookback", LOOKBACK)
        self.direction_threshold = p.get("direction_threshold_pct", DIRECTION_THRESHOLD_PCT)
        self.tp_mult = p.get("tp_atr_mult", TP_ATR_MULT)
        self.sl_mult = p.get("sl_atr_mult", SL_ATR_MULT)
        self._timeout = p.get("request_timeout", 10)

    # ── Public API ───────────────────────────────────────────────────

    def generate_signals(self, data=None, symbol: str = None) -> List[dict]:
        """Scan symbols using DLinear decomposition forecast."""
        if np is None:
            logger.error("numpy not installed — DLinear requires numpy")
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
        """Run DLinear forecast for one symbol."""

        candles = self._fetch_klines(symbol)
        if not candles or len(candles) < self.sma_window + self.lookback:
            logger.warning("%s: insufficient data (%d candles, need %d)",
                           symbol, len(candles) if candles else 0,
                           self.sma_window + self.lookback)
            return []

        closes = np.array([c.close for c in candles], dtype=np.float64)
        current_price = closes[-1]

        # ATR for risk management
        atr = self._calc_atr(candles)
        if atr == 0:
            return []

        # ── DLinear Decomposition ────────────────────────────────
        # Trend component: SMA over the window
        # We compute SMA for the last (lookback) bars
        # Each trend[i] = mean(closes[i-sma_window+1 : i+1])
        trend = np.convolve(closes, np.ones(self.sma_window) / self.sma_window, mode='valid')
        # trend length = len(closes) - sma_window + 1
        # We want the last `lookback` values of trend
        if len(trend) < self.lookback:
            logger.warning("%s: not enough trend data", symbol)
            return []

        trend_segment = trend[-self.lookback:]

        # Residual = close - trend (aligned to the same indices)
        # The trend array is offset by (sma_window - 1) from the start
        # So the closes aligned to trend_segment are:
        aligned_closes = closes[-(self.lookback):]
        # But trend[-self.lookback:] corresponds to closes at indices
        # [len(closes)-self.lookback : len(closes)] only if trend is long enough.
        # Since trend has len(closes)-sma_window+1 elements, and trend[-lookback:]
        # gives the last lookback elements, the aligned closes are:
        offset = len(closes) - (len(trend))  # = sma_window - 1
        trend_end_idx = len(closes)
        trend_start_idx = trend_end_idx - self.lookback
        close_for_residual = closes[trend_start_idx:trend_end_idx]

        residual_segment = close_for_residual - trend_segment

        # ── Linear Regressions ───────────────────────────────────
        trend_slope, trend_intercept, trend_r2 = _linear_regression(trend_segment)
        resid_slope, resid_intercept, resid_r2 = _linear_regression(residual_segment)

        # Predict next bar (index = lookback, one step ahead)
        next_idx = self.lookback  # next point beyond the fitted range
        predicted_trend = trend_slope * next_idx + trend_intercept
        predicted_residual = resid_slope * next_idx + resid_intercept
        predicted_price = predicted_trend + predicted_residual

        price_change_pct = ((predicted_price - current_price) / current_price) * 100

        # ── Confidence from R-squared ────────────────────────────
        # Weighted average: trend R² matters more (weight 0.7) than residual R² (0.3)
        combined_r2 = 0.7 * trend_r2 + 0.3 * resid_r2
        # Map R² [0,1] to confidence [0.25, 0.85]
        confidence = 0.25 + combined_r2 * 0.60
        confidence = max(0.25, min(0.85, confidence))

        # ── Signal Generation ────────────────────────────────────
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

        reason = (
            f"DLinear decomposition: predicted {price_change_pct:+.2f}% next {self.interval} bar | "
            f"trend R²={trend_r2:.3f}, residual R²={resid_r2:.3f} | "
            f"SMA({self.sma_window}) decomposition, {self.lookback}-bar fit | "
            f"Ref: Zeng et al. AAAI 2023"
        )

        return [{
            "symbol": symbol,
            "direction": direction,
            "confidence": round(confidence, 4),
            "entry": round(entry, 2),
            "tp": tp,
            "sl": sl,
            "timeframe": "4h",
            "strategy_name": "dlinear_baseline_v1",
            "reason": reason,
            "metadata": {
                "predicted_price": round(predicted_price, 2),
                "predicted_change_pct": round(price_change_pct, 4),
                "trend_slope": round(trend_slope, 6),
                "trend_r2": round(trend_r2, 4),
                "residual_slope": round(resid_slope, 6),
                "residual_r2": round(resid_r2, 4),
                "combined_r2": round(combined_r2, 4),
                "sma_window": self.sma_window,
                "lookback": self.lookback,
                "current_price": current_price,
                "atr": round(atr, 2),
            },
        }]

    # ── Technical Indicators ─────────────────────────────────────────

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
    """Run the DLinear baseline scanner and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if np is None:
        print("\n  ERROR: numpy not installed. Install with: pip install numpy")
        return []

    strategy = DLinearBaselineStrategy()
    signals = strategy.generate_signals()

    print(f"\n{'=' * 75}")
    print(f"  DLINEAR BASELINE  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Ref: Zeng et al. (2023) AAAI — arXiv:2205.13504")
    print(f"  SMA({strategy.sma_window}) decomposition, {strategy.lookback}-bar linear fit")
    print(f"{'=' * 75}")

    if not signals:
        print(f"\n  No signals generated (threshold: {strategy.direction_threshold}%)")
    else:
        for sig in signals:
            m = sig["metadata"]
            print(f"\n  {sig['symbol']}")
            print(f"  {'─' * 50}")
            print(f"  Direction:     {sig['direction']}")
            print(f"  Predicted:     ${m['predicted_price']:,.2f} ({m['predicted_change_pct']:+.2f}%)")
            print(f"  Entry:         ${sig['entry']:,.2f}")
            print(f"  TP:            ${sig['tp']:,.2f}  |  SL: ${sig['sl']:,.2f}")
            print(f"  Confidence:    {sig['confidence']:.1%}")
            print(f"  Trend R²:      {m['trend_r2']:.4f}  |  Residual R²: {m['residual_r2']:.4f}")
            print(f"  ATR:           ${m['atr']:,.2f}")

    print(f"\n{'=' * 75}")
    print(f"  Scanned {len(strategy.symbols)} symbols, generated {len(signals)} signals")
    print(f"{'=' * 75}\n")

    return signals


if __name__ == "__main__":
    main()
