"""
Crypto Hurst Volatility Expansion Breakout - Baby Strat #3
===========================================================

Created by: codex_gpt5
Date: 2026-02-26

Strategy Logic:
- Entry when: Hurst exponent indicates persistent trend regime,
  price breaks a 20-bar range, and volume expansion confirms participation.
- Exit when: Take profit (2.4x ATR) or stop loss (1.4x ATR)
- Risk management: ATR-based exits and confidence scaled by trend persistence,
  volatility expansion, and breakout quality.

Unique Value Proposition:
This strategy targets an underexplored white-space area: regime-aware momentum.
Unlike basic breakouts, it requires a statistically persistent market regime
(Hurst > threshold) plus volatility and volume expansion, reducing low-quality
range-break fakeouts.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str
    direction: str  # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class CryptoHurstVolExpansionBreakoutStrategy:
    """
    Regime-aware breakout strategy using Hurst + volatility + volume confirmation.

    Core idea:
    - Trade breakouts only when market behavior is persistent (Hurst high)
    - Require volatility expansion to avoid dead-market signals
    - Require volume expansion to confirm participation
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}

        # Keep parameter count intentionally small to avoid overfitting.
        self.hurst_window = self.params.get("hurst_window", 100)
        self.breakout_window = self.params.get("breakout_window", 20)
        self.vol_short_window = self.params.get("vol_short_window", 10)
        self.vol_long_window = self.params.get("vol_long_window", 40)
        self.hurst_trend_threshold = self.params.get("hurst_trend_threshold", 0.58)
        self.vol_expansion_threshold = self.params.get("vol_expansion_threshold", 1.15)
        self.volume_z_threshold = self.params.get("volume_z_threshold", 1.0)

        self.atr_period = self.params.get("atr_period", 14)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 2.4)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.4)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        min_bars = max(
            self.hurst_window,
            self.breakout_window,
            self.vol_long_window,
            self.atr_period,
        ) + 10
        if len(data) < min_bars:
            return []

        close = data["close"]
        high = data["high"]
        low = data["low"]
        volume = data["volume"]

        hurst = self._rolling_hurst(close, self.hurst_window)
        atr = self._calculate_atr(data, self.atr_period)

        returns = close.pct_change()
        realized_vol_short = returns.rolling(self.vol_short_window).std()
        realized_vol_long = returns.rolling(self.vol_long_window).std()
        vol_ratio = realized_vol_short / (realized_vol_long + 1e-12)

        volume_ma = volume.rolling(self.breakout_window).mean()
        volume_std = volume.rolling(self.breakout_window).std()
        volume_z = (volume - volume_ma) / (volume_std + 1e-12)

        prev_range_high = high.rolling(self.breakout_window).max().shift(1)
        prev_range_low = low.rolling(self.breakout_window).min().shift(1)

        current_price = close.iloc[-1]
        current_hurst = hurst.iloc[-1]
        current_atr = atr.iloc[-1]
        current_vol_ratio = vol_ratio.iloc[-1]
        current_volume_z = volume_z.iloc[-1]
        range_high = prev_range_high.iloc[-1]
        range_low = prev_range_low.iloc[-1]

        if any(pd.isna(v) for v in [
            current_hurst,
            current_atr,
            current_vol_ratio,
            current_volume_z,
            range_high,
            range_low,
        ]):
            return []

        trend_regime = current_hurst > self.hurst_trend_threshold
        vol_expanding = current_vol_ratio > self.vol_expansion_threshold
        volume_confirmed = current_volume_z > self.volume_z_threshold

        signals: List[Signal] = []

        if trend_regime and vol_expanding and volume_confirmed and current_price > range_high:
            confidence = self._compute_confidence(
                hurst_value=current_hurst,
                vol_ratio=current_vol_ratio,
                volume_zscore=current_volume_z,
                threshold_hurst=self.hurst_trend_threshold,
                threshold_vol=self.vol_expansion_threshold,
            )
            signals.append(self._build_signal(
                symbol=symbol,
                direction="BUY",
                entry_price=current_price,
                atr_value=current_atr,
                confidence=confidence,
                reason=(
                    f"Trend-regime breakout: Hurst={current_hurst:.2f}, "
                    f"vol_ratio={current_vol_ratio:.2f}, volume_z={current_volume_z:.2f}, "
                    f"price>{range_high:.2f}"
                ),
            ))

        elif trend_regime and vol_expanding and volume_confirmed and current_price < range_low:
            confidence = self._compute_confidence(
                hurst_value=current_hurst,
                vol_ratio=current_vol_ratio,
                volume_zscore=current_volume_z,
                threshold_hurst=self.hurst_trend_threshold,
                threshold_vol=self.vol_expansion_threshold,
            )
            signals.append(self._build_signal(
                symbol=symbol,
                direction="SELL",
                entry_price=current_price,
                atr_value=current_atr,
                confidence=confidence,
                reason=(
                    f"Trend-regime downside breakout: Hurst={current_hurst:.2f}, "
                    f"vol_ratio={current_vol_ratio:.2f}, volume_z={current_volume_z:.2f}, "
                    f"price<{range_low:.2f}"
                ),
            ))

        return signals

    def _build_signal(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        atr_value: float,
        confidence: float,
        reason: str,
    ) -> Signal:
        if direction == "BUY":
            tp = entry_price + atr_value * self.tp_atr_mult
            sl = entry_price - atr_value * self.sl_atr_mult
        else:
            tp = entry_price - atr_value * self.tp_atr_mult
            sl = entry_price + atr_value * self.sl_atr_mult

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=round(confidence, 3),
            entry_price=round(entry_price, 2),
            take_profit=round(tp, 2),
            stop_loss=round(sl, 2),
            reason=reason,
        )

    def _compute_confidence(
        self,
        hurst_value: float,
        vol_ratio: float,
        volume_zscore: float,
        threshold_hurst: float,
        threshold_vol: float,
    ) -> float:
        hurst_score = min(max((hurst_value - threshold_hurst) / 0.25, 0.0), 1.0)
        vol_score = min(max((vol_ratio - threshold_vol) / 0.75, 0.0), 1.0)
        volume_score = min(max((volume_zscore - self.volume_z_threshold) / 2.0, 0.0), 1.0)

        confidence = 0.45 * hurst_score + 0.35 * vol_score + 0.20 * volume_score
        return min(max(confidence, 0.1), 0.95)

    def _rolling_hurst(self, prices: pd.Series, window: int) -> pd.Series:
        return prices.rolling(window=window).apply(self._hurst_exponent, raw=False)

    @staticmethod
    def _hurst_exponent(series: pd.Series) -> float:
        x = np.asarray(series)
        if len(x) < 20:
            return np.nan

        lags = np.arange(2, 20)
        tau = []
        for lag in lags:
            diff = x[lag:] - x[:-lag]
            std_val = np.std(diff)
            tau.append(std_val if std_val > 0 else 1e-8)

        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        hurst = poly[0]
        return float(np.clip(hurst, 0.0, 1.0))

    @staticmethod
    def _calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]

        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        return tr.rolling(window=period, min_periods=1).mean()


if __name__ == "__main__":
    np.random.seed(42)
    n = 320

    # Synthetic series with alternating regimes to trigger both signal sides.
    regime = np.where(np.arange(n) < n // 2, 0.0012, -0.0010)
    noise = np.random.normal(0.0, 0.018, n)
    returns = regime + noise

    prices = 50000 * np.exp(np.cumsum(returns))

    test_data = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.0015, n)),
        "high": prices * (1 + np.abs(np.random.normal(0, 0.012, n))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.012, n))),
        "close": prices,
        "volume": np.random.lognormal(mean=6.5, sigma=0.55, size=n),
    })

    strategy = CryptoHurstVolExpansionBreakoutStrategy({
        "hurst_trend_threshold": 0.40,
        "vol_expansion_threshold": 0.80,
        "volume_z_threshold": -0.50,
    })
    all_signals = []

    start = 120
    for i in range(start, len(test_data)):
        window = test_data.iloc[: i + 1]
        sigs = strategy.generate_signals(window, symbol="BTCUSDT")
        for sig in sigs:
            all_signals.append((i, sig))

    print("=== Crypto Hurst Volatility Expansion Breakout ===")
    print(f"Scanned {len(test_data) - start} windows")
    print(f"Total signals: {len(all_signals)}")

    buys = [s for _, s in all_signals if s.direction == "BUY"]
    sells = [s for _, s in all_signals if s.direction == "SELL"]
    print(f"BUY: {len(buys)} | SELL: {len(sells)}")

    for bar_idx, sig in all_signals[:5]:
        print(f"\nBar {bar_idx}: {sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
