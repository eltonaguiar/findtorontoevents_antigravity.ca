"""MACD-Based Price Forecasting Strategy — Percentile-based trend memory.

Inspired by LuxAlgo's MACD Based Price Forecasting indicator. Builds a
memory of price changes during MACD uptrend and downtrend phases, then
uses percentile-based forecasting (80th/50th/20th) to project likely
price targets.

Core idea: During historical MACD uptrends, how much did price typically
gain? During downtrends, how much did it lose? Use those distributions
to forecast the current phase.

Methodology:
  1. Calculate MACD (fast/slow/signal EMA)
  2. Identify uptrend (MACD > Signal) and downtrend (MACD < Signal) phases
  3. For each completed phase, record total % price change
  4. Build percentile distributions of up-phase gains and down-phase losses
  5. When a NEW phase starts, project targets using 80th/50th/20th percentiles
  6. Generate signal if current phase is young and has high projected R:R
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


class MACDPriceForecastStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        # MACD parameters
        self.fast_period = self.params.get('fast_period', 12)
        self.slow_period = self.params.get('slow_period', 26)
        self.signal_period = self.params.get('signal_period', 9)
        # Minimum completed phases to build reliable distribution
        self.min_phases = self.params.get('min_phases', 5)
        # Percentile for TP (use 50th = median expected move)
        self.tp_percentile = self.params.get('tp_percentile', 50)
        # Percentile for SL (use 20th = conservative adverse move from opposite phase)
        self.sl_percentile = self.params.get('sl_percentile', 20)
        # Max bars into a phase to still trigger (catch it early)
        self.max_phase_age = self.params.get('max_phase_age', 5)
        # Minimum projected R:R to trigger
        self.min_rr = self.params.get('min_rr', 1.5)
        # ATR for fallback SL
        self.atr_period = self.params.get('atr_period', 14)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)
        # Minimum bars
        self.min_bars = self.params.get('min_bars', 100)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.min_bars:
            return []

        close = data['close'].values.astype(float)
        n = len(close)

        # Calculate MACD
        fast_ema = self._ema(close, self.fast_period)
        slow_ema = self._ema(close, self.slow_period)
        macd_line = fast_ema - slow_ema
        signal_line = self._ema(macd_line, self.signal_period)

        # Determine trend phases: 1 = uptrend (MACD > Signal), -1 = downtrend
        trend = np.where(macd_line > signal_line, 1, -1)

        # Find phase boundaries (where trend changes)
        phase_changes = np.where(np.diff(trend) != 0)[0]

        if len(phase_changes) < self.min_phases:
            return []

        # Build distributions of price changes per phase type
        up_phase_pcts = []    # % gains during uptrend phases
        down_phase_pcts = []  # % losses during downtrend phases

        # Process completed phases
        starts = [0] + list(phase_changes + 1)
        ends = list(phase_changes + 1) + [n]

        completed_phases = list(zip(starts[:-1], ends[:-1]))

        for phase_start, phase_end in completed_phases:
            if phase_end <= phase_start or phase_start >= n or phase_end > n:
                continue
            phase_trend = trend[phase_start]
            start_price = close[phase_start]
            end_price = close[phase_end - 1]  # last bar of phase
            if start_price <= 0:
                continue
            pct_change = (end_price - start_price) / start_price

            if phase_trend == 1:
                up_phase_pcts.append(pct_change)
            else:
                down_phase_pcts.append(pct_change)

        # Need enough data for meaningful percentiles
        if len(up_phase_pcts) < 4 or len(down_phase_pcts) < 4:
            return []

        up_phase_pcts = np.array(up_phase_pcts)
        down_phase_pcts = np.array(down_phase_pcts)

        # Current phase info
        current_phase_start = starts[-1]
        current_phase_trend = trend[-1]
        current_phase_age = n - current_phase_start  # bars into current phase

        # Only signal early in a phase
        if current_phase_age > self.max_phase_age:
            return []

        # Must be a fresh phase transition
        if current_phase_age < 1:
            return []

        current_price = close[-1]
        phase_start_price = close[current_phase_start]
        if current_price <= 0 or phase_start_price <= 0:
            return []

        # Calculate ATR for fallback
        atr = self._atr_from_data(data, self.atr_period)
        current_atr = atr[-1] if len(atr) > 0 else current_price * 0.02

        signals = []

        if current_phase_trend == 1:
            # Uptrend phase started — project bullish targets
            # TP from historical up-phase gains
            tp_pct = np.percentile(up_phase_pcts, self.tp_percentile)
            # SL from historical down-phase losses (how bad if wrong)
            sl_pct = np.percentile(down_phase_pcts, self.sl_percentile)

            if tp_pct <= 0:
                return []  # Median up-phase was negative? Skip

            tp_price = round(phase_start_price * (1 + tp_pct), 2)
            # SL: use conservative adverse move
            sl_price_hist = round(phase_start_price * (1 + sl_pct), 2)
            sl_price_atr = round(current_price - current_atr * self.sl_atr_mult, 2)
            # Use whichever SL is tighter (less loss)
            sl_price = max(sl_price_hist, sl_price_atr)

            # Ensure TP > current price > SL
            if tp_price <= current_price or sl_price >= current_price:
                return []

            # R:R check
            reward = tp_price - current_price
            risk = current_price - sl_price
            if risk <= 0:
                return []
            rr = reward / risk

            if rr < self.min_rr:
                return []

            # Confidence: based on historical consistency
            # What % of up-phases were actually positive?
            win_pct = np.mean(up_phase_pcts > 0)
            # How strong was median vs variance?
            median_move = np.median(up_phase_pcts)
            std_move = np.std(up_phase_pcts)
            consistency = median_move / (std_move + 1e-10)

            confidence = min(0.90, 0.4 + win_pct * 0.3 + min(consistency, 1.0) * 0.2)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=tp_price,
                stop_loss=sl_price,
                reason=(
                    f"MACD Forecast BUY: new uptrend phase (age {current_phase_age}), "
                    f"median up-phase +{median_move*100:.1f}%, "
                    f"P{self.tp_percentile} target +{tp_pct*100:.1f}%, "
                    f"R:R {rr:.1f}, {win_pct*100:.0f}% of up-phases profitable, "
                    f"{len(up_phase_pcts)} historical phases"
                )
            ))

        elif current_phase_trend == -1:
            # Downtrend phase started — project bearish targets
            # TP from historical down-phase losses (we're shorting)
            tp_pct = np.percentile(down_phase_pcts, 100 - self.tp_percentile)
            # SL from historical up-phase gains (how bad if wrong)
            sl_pct = np.percentile(up_phase_pcts, 100 - self.sl_percentile)

            if tp_pct >= 0:
                return []  # Median down-phase was positive? Skip

            tp_price = round(phase_start_price * (1 + tp_pct), 2)
            # SL: use conservative adverse move up
            sl_price_hist = round(phase_start_price * (1 + sl_pct), 2)
            sl_price_atr = round(current_price + current_atr * self.sl_atr_mult, 2)
            # Use whichever SL is tighter
            sl_price = min(sl_price_hist, sl_price_atr)

            # Ensure TP < current price < SL
            if tp_price >= current_price or sl_price <= current_price:
                return []

            # R:R check
            reward = current_price - tp_price
            risk = sl_price - current_price
            if risk <= 0:
                return []
            rr = reward / risk

            if rr < self.min_rr:
                return []

            # Confidence
            win_pct = np.mean(down_phase_pcts < 0)
            median_move = abs(np.median(down_phase_pcts))
            std_move = np.std(down_phase_pcts)
            consistency = median_move / (std_move + 1e-10)

            confidence = min(0.90, 0.4 + win_pct * 0.3 + min(consistency, 1.0) * 0.2)

            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 2),
                take_profit=tp_price,
                stop_loss=sl_price,
                reason=(
                    f"MACD Forecast SELL: new downtrend phase (age {current_phase_age}), "
                    f"median down-phase {np.median(down_phase_pcts)*100:.1f}%, "
                    f"P{100-self.tp_percentile} target {tp_pct*100:.1f}%, "
                    f"R:R {rr:.1f}, {win_pct*100:.0f}% of down-phases negative, "
                    f"{len(down_phase_pcts)} historical phases"
                )
            ))

        return signals

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA using pandas for accuracy."""
        series = pd.Series(data)
        return series.ewm(span=period, adjust=False).mean().values

    def _atr_from_data(self, data: pd.DataFrame, period: int) -> np.ndarray:
        tr = pd.concat([
            data['high'] - data['low'],
            (data['high'] - data['close'].shift()).abs(),
            (data['low'] - data['close'].shift()).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean().values
