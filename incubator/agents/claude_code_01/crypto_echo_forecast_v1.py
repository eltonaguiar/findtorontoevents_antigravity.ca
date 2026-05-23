"""Echo Forecast Strategy — Pattern correlation-based price forecasting.

Inspired by LuxAlgo's Echo Forecast indicator. Uses sliding-window correlation
to find the most similar historical pattern to the current price window, then
projects forward using the subsequent price action of that best-matching window.

Core idea: If recent N bars look very similar to a past N-bar window, the bars
that followed that past window may predict what happens next.

Methodology:
  1. Build correlation matrix of current window vs all historical windows
  2. Find the best-matching window (highest Pearson r)
  3. Use the K bars that followed the best match as a forecast
  4. Combine via cumulative / mean / linear-regression construction
  5. Generate BUY/SELL if forecast shows sufficient directional move
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    symbol: str
    direction: str      # "BUY" or "SELL"
    confidence: float   # 0.0 to 1.0
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class EchoForecastStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        # Window size for pattern matching (bars to compare)
        self.window_size = self.params.get('window_size', 50)
        # How many bars ahead to forecast
        self.forecast_horizon = self.params.get('forecast_horizon', 12)
        # Minimum correlation to consider a match valid
        self.min_correlation = self.params.get('min_correlation', 0.80)
        # Forecast move threshold (% of ATR) to trigger signal
        self.signal_threshold_atr = self.params.get('signal_threshold_atr', 0.5)
        # TP/SL multipliers
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)
        # ATR period
        self.atr_period = self.params.get('atr_period', 14)
        # Minimum bars needed
        self.min_bars = self.params.get('min_bars', 150)
        # Number of top matches to ensemble (like LuxAlgo's mean construction)
        self.top_k = self.params.get('top_k', 3)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data['close'].values.astype(float)
        n = len(close)
        w = self.window_size
        h = self.forecast_horizon

        # Need at least window + forecast_horizon + some history
        if n < w + h + 50:
            return []

        # Current window = last w bars
        current_window = close[n - w: n]

        # Normalize current window (z-score)
        cw_mean = np.mean(current_window)
        cw_std = np.std(current_window)
        if cw_std < 1e-10:
            return []
        cw_norm = (current_window - cw_mean) / cw_std

        # Search historical windows for best correlation matches
        # Search space: from index w to (n - w - h) so the forecast horizon exists
        search_end = n - w - h
        if search_end < w:
            return []

        correlations = []
        for i in range(w, search_end):
            hist_window = close[i: i + w]
            hw_std = np.std(hist_window)
            if hw_std < 1e-10:
                continue
            hw_norm = (hist_window - np.mean(hist_window)) / hw_std
            # Pearson correlation
            r = np.corrcoef(cw_norm, hw_norm)[0, 1]
            if not np.isnan(r):
                correlations.append((r, i))

        if not correlations:
            return []

        # Sort by correlation descending, take top_k
        correlations.sort(key=lambda x: x[0], reverse=True)
        top_matches = correlations[:self.top_k]

        best_corr = top_matches[0][0]
        if best_corr < self.min_correlation:
            return []

        # Build forecast from top_k matches
        # For each match, get the h bars that followed the matched window
        forecasts = []
        for corr, idx in top_matches:
            # The forecast starts at idx + w (right after the matched window)
            forecast_start = idx + w
            forecast_end = forecast_start + h
            if forecast_end > n:
                continue

            # Get % change series relative to last bar of matched window
            anchor_price = close[forecast_start - 1]
            if anchor_price <= 0:
                continue
            pct_changes = (close[forecast_start: forecast_end] - anchor_price) / anchor_price
            forecasts.append((corr, pct_changes))

        if not forecasts:
            return []

        # Weighted average forecast (weighted by correlation)
        total_weight = sum(c for c, _ in forecasts)
        if total_weight < 1e-10:
            return []

        weighted_forecast = np.zeros(h)
        for corr, pct_chg in forecasts:
            weight = corr / total_weight
            length = min(len(pct_chg), h)
            weighted_forecast[:length] += weight * pct_chg[:length]

        # Calculate forecast direction and magnitude
        # Use the mean of the forecast as the expected move (most stable)
        forecast_mean = np.mean(weighted_forecast)
        # Also check endpoint and peak
        forecast_end_pct = weighted_forecast[-1]
        forecast_peak = weighted_forecast[np.argmax(np.abs(weighted_forecast))]
        # Use mean — it's the most representative of overall forecast trajectory
        forecast_pct = forecast_mean

        # Current price and ATR
        current_price = close[-1]
        atr = self._atr(data, self.atr_period)
        current_atr = atr.iloc[-1]

        if current_atr <= 0 or current_price <= 0:
            return []

        # Threshold: forecast must exceed signal_threshold_atr * ATR as % of price
        threshold_pct = (self.signal_threshold_atr * current_atr) / current_price

        # Check if forecast is strong enough
        signals = []

        # Confidence based on correlation strength and forecast consistency
        # Check if all top matches agree on direction
        direction_agreement = sum(1 for _, fc in forecasts if np.mean(fc) > 0) / len(forecasts)

        if forecast_pct > threshold_pct:
            # Bullish forecast
            if direction_agreement < 0.6:
                return []  # Not enough agreement
            confidence = min(0.95, 0.5 + best_corr * 0.3 + direction_agreement * 0.2)
            tp = round(current_price + current_atr * self.tp_atr_mult, 2)
            sl = round(current_price - current_atr * self.sl_atr_mult, 2)
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=tp,
                stop_loss=sl,
                reason=(
                    f"Echo Forecast BUY: best corr {best_corr:.3f} "
                    f"({len(forecasts)} matches), forecast +{forecast_pct*100:.2f}% "
                    f"over {h} bars, {direction_agreement*100:.0f}% directional agreement"
                )
            ))

        elif forecast_pct < -threshold_pct:
            # Bearish forecast
            if direction_agreement > 0.4:
                return []  # Not enough bearish agreement
            confidence = min(0.95, 0.5 + best_corr * 0.3 + (1 - direction_agreement) * 0.2)
            tp = round(current_price - current_atr * self.tp_atr_mult, 2)
            sl = round(current_price + current_atr * self.sl_atr_mult, 2)
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=tp,
                stop_loss=sl,
                reason=(
                    f"Echo Forecast SELL: best corr {best_corr:.3f} "
                    f"({len(forecasts)} matches), forecast {forecast_pct*100:.2f}% "
                    f"over {h} bars, {(1-direction_agreement)*100:.0f}% bearish agreement"
                )
            ))

        return signals

    def _atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        tr = pd.concat([
            data['high'] - data['low'],
            (data['high'] - data['close'].shift()).abs(),
            (data['low'] - data['close'].shift()).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()
