"""
Rotational Trend Momentum Strategy — Catching Crypto Trends
============================================================

Source: Zarattini et al. (2025), "Catching Crypto Trends: A Rotational
        Momentum Approach to Cryptocurrency Portfolio Construction."
        Documented Sharpe ratio of 1.5+ across multi-year backtests.

Strategy Logic:
  The core insight is a composite TREND SCORE built from multiple
  momentum timeframes, combined with a volatility regime filter and
  a "cash signal" mechanism. In bear regimes (all momentum negative
  AND price below 50-EMA), the strategy goes FLAT — holding stablecoins
  instead of forcing a trade. This dramatically improves risk-adjusted
  returns by avoiding sustained drawdowns.

  Composite Trend Score:
    - 7-day return  (fast momentum):  weight 0.35
    - 14-day return (medium momentum): weight 0.30
    - 30-day return (slow momentum):   weight 0.20
    - Price position vs 50-EMA:        weight 0.15

  Volatility Regime Detection:
    - 20-day realized vol vs 60-day avg vol
    - High-vol regime (>1.5x): penalize confidence by 30%
    - Low-vol regime  (<0.7x): boost confidence by 15%

  Entry Rules:
    - BUY  if composite trend score > +0.2
    - SELL if composite trend score < -0.3 (asymmetric to bias long)
    - NO SIGNAL (cash) if all momentum windows negative AND price < EMA(50)

  TP/SL (ATR-based, trend-following = wider targets):
    - TP = entry + 2.5 * ATR(14)   [3.0 * ATR in low-vol regime]
    - SL = entry - 1.5 * ATR(14)

  Volume Filter:
    - Current volume must exceed 0.8x of 20-day average volume

Expected Performance:
  - Sharpe ratio: 1.5+ (documented in paper)
  - The cash-signal mechanism is the key alpha: avoiding bear regime
    drawdowns lifts Sharpe from ~0.8 (always-invested) to 1.5+
  - Best on: BTC, ETH, SOL and other liquid large-cap crypto
  - Timeframe: Daily bars (paper uses daily rebalancing)

References:
  - Zarattini, C. et al. (2025). "Catching Crypto Trends: A Rotational
    Momentum Approach to Cryptocurrency Portfolio Construction."
  - Moskowitz, T., Ooi, Y.H., Pedersen, L.H. (2012). "Time Series
    Momentum." Journal of Financial Economics, 104(2), 228-250.
  - Jegadeesh, N. & Titman, S. (1993). "Returns to Buying Winners and
    Selling Losers." Journal of Finance, 48(1), 65-91.
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


class RotationalMomentumStrategy:
    """
    Rotational Trend Momentum strategy adapted from Zarattini et al. (2025).

    Computes a weighted composite trend score from multi-timeframe momentum,
    applies volatility regime detection, and uses a cash-signal filter to
    stay flat during bear regimes. Designed for per-symbol scanning.
    """

    def __init__(
        self,
        lookback_fast: int = 7,
        lookback_mid: int = 14,
        lookback_slow: int = 30,
        ema_trend: int = 50,
        vol_short: int = 20,
        vol_long: int = 60,
        vol_high_mult: float = 1.5,
        vol_low_mult: float = 0.7,
        buy_threshold: float = 0.2,
        sell_threshold: float = -0.3,
        volume_avg_period: int = 20,
        volume_min_ratio: float = 0.8,
        atr_period: int = 14,
        tp_atr_mult: float = 2.5,
        sl_atr_mult: float = 1.5,
    ):
        self.lookback_fast = lookback_fast
        self.lookback_mid = lookback_mid
        self.lookback_slow = lookback_slow
        self.ema_trend = ema_trend
        self.vol_short = vol_short
        self.vol_long = vol_long
        self.vol_high_mult = vol_high_mult
        self.vol_low_mult = vol_low_mult
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.volume_avg_period = volume_avg_period
        self.volume_min_ratio = volume_min_ratio
        self.atr_period = atr_period
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult

        # Weights for the composite trend score
        self.weight_fast = 0.35
        self.weight_mid = 0.30
        self.weight_slow = 0.20
        self.weight_ema = 0.15

    def _compute_atr(self, df: pd.DataFrame) -> pd.Series:
        """Compute Average True Range over self.atr_period."""
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)

        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)

        return tr.rolling(window=self.atr_period, min_periods=1).mean()

    def _compute_ema(self, series: pd.Series, span: int) -> pd.Series:
        """Compute Exponential Moving Average."""
        return series.ewm(span=span, adjust=False).mean()

    def _compute_returns(self, close: pd.Series, period: int) -> pd.Series:
        """Compute simple returns over a lookback period."""
        return close.pct_change(periods=period)

    def _compute_realized_vol(self, close: pd.Series, window: int) -> pd.Series:
        """Compute realized volatility as rolling std of log returns."""
        log_returns = np.log(close / close.shift(1))
        return log_returns.rolling(window=window, min_periods=1).std()

    def _normalize_return(self, ret: float) -> float:
        """
        Normalize a return value to roughly [-1, 1] range using tanh.
        This prevents any single momentum window from dominating the score.
        """
        return float(np.tanh(ret * 10))

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Generate trading signals from OHLCV data.

        Parameters
        ----------
        data : pd.DataFrame
            Must contain columns: 'open', 'high', 'low', 'close', 'volume'.
            Rows should be sorted by time ascending (oldest first).
        symbol : str
            Trading pair symbol, e.g. "BTCUSDT".

        Returns
        -------
        List[Signal]
            Zero or one Signal. Empty list means "stay in cash" (no trade).
        """
        signals: List[Signal] = []

        # Minimum data requirement
        min_rows = max(
            self.lookback_slow, self.ema_trend, self.vol_long, self.atr_period
        ) + 5
        if len(data) < min_rows:
            return signals

        close = data["close"]
        volume = data["volume"]

        # --- 1. Composite Trend Score ---
        ret_fast = self._compute_returns(close, self.lookback_fast)
        ret_mid = self._compute_returns(close, self.lookback_mid)
        ret_slow = self._compute_returns(close, self.lookback_slow)
        ema_50 = self._compute_ema(close, self.ema_trend)

        latest_close = float(close.iloc[-1])
        latest_ema = float(ema_50.iloc[-1])

        r_fast = self._normalize_return(float(ret_fast.iloc[-1]))
        r_mid = self._normalize_return(float(ret_mid.iloc[-1]))
        r_slow = self._normalize_return(float(ret_slow.iloc[-1]))

        # EMA position score: +1 if above EMA, -1 if below, scaled by distance
        ema_distance = (latest_close - latest_ema) / latest_ema if latest_ema != 0 else 0.0
        ema_score = float(np.tanh(ema_distance * 10))

        composite_score = (
            self.weight_fast * r_fast
            + self.weight_mid * r_mid
            + self.weight_slow * r_slow
            + self.weight_ema * ema_score
        )

        # --- 2. Volatility Regime Detection ---
        vol_short_series = self._compute_realized_vol(close, self.vol_short)
        vol_long_series = self._compute_realized_vol(close, self.vol_long)

        vol_short_now = float(vol_short_series.iloc[-1])
        vol_long_now = float(vol_long_series.iloc[-1])

        vol_ratio = vol_short_now / vol_long_now if vol_long_now > 0 else 1.0

        is_high_vol = vol_ratio > self.vol_high_mult
        is_low_vol = vol_ratio < self.vol_low_mult

        # --- 3. Cash Signal Filter ---
        # If ALL momentum signals are negative AND price < EMA(50), stay flat
        all_momentum_negative = (r_fast < 0) and (r_mid < 0) and (r_slow < 0)
        below_ema = latest_close < latest_ema

        if all_momentum_negative and below_ema:
            # Cash signal — the key innovation from Zarattini et al.
            return signals

        # --- 4. Volume Confirmation ---
        avg_volume = volume.rolling(window=self.volume_avg_period, min_periods=1).mean()
        latest_volume = float(volume.iloc[-1])
        latest_avg_volume = float(avg_volume.iloc[-1])

        if latest_avg_volume > 0 and latest_volume < self.volume_min_ratio * latest_avg_volume:
            # Dead market — skip
            return signals

        # --- 5. Direction Decision ---
        direction: Optional[str] = None

        if composite_score > self.buy_threshold:
            direction = "BUY"
        elif composite_score < self.sell_threshold:
            direction = "SELL"
        else:
            # Score in neutral zone — no signal
            return signals

        # --- 6. Confidence Calculation ---
        if direction == "BUY":
            raw_confidence = min((composite_score - self.buy_threshold) / 0.8, 1.0)
        else:
            raw_confidence = min((abs(composite_score) - abs(self.sell_threshold)) / 0.7, 1.0)

        # Clamp to [0.1, 1.0] base range
        confidence = max(0.1, min(raw_confidence, 1.0))

        # Apply volatility regime adjustment
        if is_high_vol:
            confidence *= 0.70  # 30% penalty
        elif is_low_vol:
            confidence *= 1.15  # 15% bonus

        confidence = round(max(0.05, min(confidence, 1.0)), 4)

        # --- 7. TP/SL via ATR ---
        atr_series = self._compute_atr(data)
        atr_now = float(atr_series.iloc[-1])

        tp_mult = self.tp_atr_mult
        if is_low_vol:
            tp_mult = 3.0  # Widen target in calm regime

        if direction == "BUY":
            take_profit = round(latest_close + tp_mult * atr_now, 8)
            stop_loss = round(latest_close - self.sl_atr_mult * atr_now, 8)
        else:
            take_profit = round(latest_close - tp_mult * atr_now, 8)
            stop_loss = round(latest_close + self.sl_atr_mult * atr_now, 8)

        # --- 8. Build Reason String ---
        regime = "HIGH-VOL" if is_high_vol else ("LOW-VOL" if is_low_vol else "NORMAL-VOL")
        reason = (
            f"Rotational Momentum (Zarattini 2025): composite={composite_score:+.3f} "
            f"[fast={r_fast:+.2f} mid={r_mid:+.2f} slow={r_slow:+.2f} ema={ema_score:+.2f}] "
            f"| regime={regime} vol_ratio={vol_ratio:.2f} "
            f"| vol_confirm={latest_volume/latest_avg_volume:.2f}x avg"
        )

        signals.append(Signal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            entry_price=round(latest_close, 8),
            take_profit=take_profit,
            stop_loss=stop_loss,
            reason=reason,
        ))

        return signals


# ---------------------------------------------------------------------------
# Convenience: quick smoke test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(42)

    # Generate synthetic daily OHLCV data (100 bars)
    n = 100
    dates = pd.date_range("2025-01-01", periods=n, freq="D")
    base_price = 60000.0
    returns = np.random.normal(0.002, 0.025, n)
    close_prices = base_price * np.cumprod(1 + returns)

    df = pd.DataFrame({
        "open": close_prices * (1 + np.random.uniform(-0.005, 0.005, n)),
        "high": close_prices * (1 + np.random.uniform(0.001, 0.02, n)),
        "low": close_prices * (1 - np.random.uniform(0.001, 0.02, n)),
        "close": close_prices,
        "volume": np.random.uniform(1000, 5000, n),
    }, index=dates)

    strategy = RotationalMomentumStrategy()
    result = strategy.generate_signals(df, symbol="BTCUSDT")

    if result:
        sig = result[0]
        print(f"Signal: {sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence}")
        print(f"  Entry:      {sig.entry_price:.2f}")
        print(f"  TP:         {sig.take_profit:.2f}")
        print(f"  SL:         {sig.stop_loss:.2f}")
        print(f"  Reason:     {sig.reason}")
    else:
        print("No signal (cash regime or neutral zone)")
