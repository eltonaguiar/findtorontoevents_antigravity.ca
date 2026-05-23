"""
VWAPRSIInstitutionalStrategy - Baby Strat
==========================================

Created by: Antigravity AI
Date: 2026-03-16

Category: INTRADAY MEAN REVERSION
Best for: Day trading BTC/ETH — catching bounces at institutional VWAP levels

Source: Hybrid #2 from Kimi Agent Proven Strategies (VWAP-RSI Institutional
Confluence), adapted to the baby_strategies Signal pattern.

Strategy Logic:
  - VWAP with 1σ/2σ standard deviation bands
  - Triple RSI confluence: RSI(14), RSI(21), RSI(50)
  - LONG: Price returns to VWAP in uptrend + RSI(14)<40 + RSI(21)>50 + RSI(50)>55 + Volume
  - SHORT: Price returns to VWAP in downtrend + RSI(14)>60 + RSI(21)<50 + RSI(50)<45 + Volume
  - TP: 2σ VWAP band | SL: 1σ VWAP band (opposite side)

Why it works:
  - VWAP is the institutional "fair value" benchmark
  - Triple RSI across timeframes filters false mean-reversion entries
  - Short-term RSI gives oversold/overbought signal
  - Medium & long-term RSI confirm the broader trend hasn't reversed
  - Volume spike at VWAP confirms institutional participation

Expected: WR 65-72%, PF 1.7-2.1
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


NAME = "vwap_rsi_institutional"
DESCRIPTION = "VWAP + Triple RSI(14/21/50) institutional confluence mean reversion"

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]


def _rsi(close: pd.Series, period: int) -> pd.Series:
    """Compute RSI using exponential moving average."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - 100 / (1 + rs)


def _vwap_with_bands(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
    std_period: int = 20
):
    """
    Compute cumulative VWAP with standard deviation bands.

    Returns (vwap, upper_1σ, lower_1σ, upper_2σ, lower_2σ)
    """
    typical_price = (high + low + close) / 3
    cum_tp_vol = (typical_price * volume).cumsum()
    cum_vol = volume.cumsum()
    vwap = cum_tp_vol / cum_vol.replace(0, 1e-10)

    # Rolling std of typical price for bands
    std = typical_price.rolling(std_period, min_periods=5).std()

    upper_1 = vwap + std
    lower_1 = vwap - std
    upper_2 = vwap + std * 2
    lower_2 = vwap - std * 2

    return vwap, upper_1, lower_1, upper_2, lower_2


class VWAPRSIInstitutionalStrategy:

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_short = self.params.get("rsi_short", 14)
        self.rsi_medium = self.params.get("rsi_medium", 21)
        self.rsi_long = self.params.get("rsi_long", 50)
        self.std_period = self.params.get("std_period", 20)
        self.volume_ma = self.params.get("volume_ma", 20)
        # RSI thresholds
        self.rsi_short_oversold = self.params.get("rsi_short_oversold", 40)
        self.rsi_short_overbought = self.params.get("rsi_short_overbought", 60)
        self.rsi_med_bull = self.params.get("rsi_med_bull", 50)
        self.rsi_med_bear = self.params.get("rsi_med_bear", 50)
        self.rsi_long_bull = self.params.get("rsi_long_bull", 55)
        self.rsi_long_bear = self.params.get("rsi_long_bear", 45)
        # VWAP proximity threshold (within 0.5% of VWAP)
        self.vwap_proximity = self.params.get("vwap_proximity", 0.005)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        min_bars = max(self.rsi_long, self.std_period, self.volume_ma) + 10
        if len(data) < min_bars:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        # VWAP and bands
        vwap, upper_1, lower_1, upper_2, lower_2 = _vwap_with_bands(
            high, low, close, volume, self.std_period
        )

        # Triple RSI
        rsi_14 = _rsi(close, self.rsi_short)
        rsi_21 = _rsi(close, self.rsi_medium)
        rsi_50 = _rsi(close, self.rsi_long)

        # Volume MA
        vol_ma = volume.rolling(self.volume_ma).mean()

        # Current values
        i = len(close) - 1
        price = float(close.iloc[i])
        cur_vwap = float(vwap.iloc[i])
        cur_rsi14 = float(rsi_14.iloc[i])
        cur_rsi21 = float(rsi_21.iloc[i])
        cur_rsi50 = float(rsi_50.iloc[i])
        cur_vol = float(volume.iloc[i])
        cur_vol_ma = float(vol_ma.iloc[i])
        cur_upper1 = float(upper_1.iloc[i])
        cur_lower1 = float(lower_1.iloc[i])
        cur_upper2 = float(upper_2.iloc[i])
        cur_lower2 = float(lower_2.iloc[i])

        if any(np.isnan(x) for x in [cur_vwap, cur_rsi14, cur_rsi21, cur_rsi50, cur_vol_ma]):
            return []

        signals = []

        # Price near VWAP
        near_vwap = abs(price - cur_vwap) / cur_vwap < self.vwap_proximity

        # Volume confirmation
        vol_confirmed = cur_vol > cur_vol_ma

        # Trend: use EMA(50) of close as trend filter
        ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[i])
        uptrend = price > ema50
        downtrend = price < ema50

        # === LONG SIGNAL ===
        if (
            near_vwap
            and uptrend
            and cur_rsi14 < self.rsi_short_oversold   # Short-term oversold
            and cur_rsi21 > self.rsi_med_bull            # Medium-term bullish
            and cur_rsi50 > self.rsi_long_bull           # Long-term bullish
            and vol_confirmed
        ):
            # TP at 2σ upper band, SL at 1σ lower band
            tp = cur_upper2
            sl = cur_lower1

            # Ensure valid TP/SL
            if tp > price and sl < price:
                # Confidence from RSI depth + volume strength
                rsi_depth = (self.rsi_short_oversold - cur_rsi14) / self.rsi_short_oversold
                vol_strength = min((cur_vol / cur_vol_ma - 1) * 0.5, 0.2)
                trend_strength = min((cur_rsi50 - 50) / 50, 0.15)
                confidence = min(0.55 + rsi_depth * 0.2 + vol_strength + trend_strength, 0.92)

                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(
                        f"VWAP-RSI institutional LONG: price {price:.2f} near VWAP {cur_vwap:.2f}, "
                        f"RSI(14)={cur_rsi14:.1f}<{self.rsi_short_oversold}, "
                        f"RSI(21)={cur_rsi21:.1f}>{self.rsi_med_bull}, "
                        f"RSI(50)={cur_rsi50:.1f}>{self.rsi_long_bull}, "
                        f"vol={cur_vol:.0f}>{cur_vol_ma:.0f}"
                    ),
                ))

        # === SHORT SIGNAL ===
        if (
            near_vwap
            and downtrend
            and cur_rsi14 > self.rsi_short_overbought   # Short-term overbought
            and cur_rsi21 < self.rsi_med_bear              # Medium-term bearish
            and cur_rsi50 < self.rsi_long_bear             # Long-term bearish
            and vol_confirmed
        ):
            tp = cur_lower2
            sl = cur_upper1

            if tp < price and sl > price:
                rsi_depth = (cur_rsi14 - self.rsi_short_overbought) / (100 - self.rsi_short_overbought)
                vol_strength = min((cur_vol / cur_vol_ma - 1) * 0.5, 0.2)
                trend_strength = min((50 - cur_rsi50) / 50, 0.15)
                confidence = min(0.55 + rsi_depth * 0.2 + vol_strength + trend_strength, 0.92)

                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(
                        f"VWAP-RSI institutional SHORT: price {price:.2f} near VWAP {cur_vwap:.2f}, "
                        f"RSI(14)={cur_rsi14:.1f}>{self.rsi_short_overbought}, "
                        f"RSI(21)={cur_rsi21:.1f}<{self.rsi_med_bear}, "
                        f"RSI(50)={cur_rsi50:.1f}<{self.rsi_long_bear}, "
                        f"vol={cur_vol:.0f}>{cur_vol_ma:.0f}"
                    ),
                ))

        return signals


# ── CLI Test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Strategy: {NAME}")
    print(f"Description: {DESCRIPTION}")
    print(f"Symbols: {SYMBOLS}")
    print()

    # Synthetic test: trending up data with a pullback to VWAP
    np.random.seed(42)
    n = 300
    # Create an uptrend with mean-reverting pullbacks
    trend = np.linspace(50000, 55000, n)
    noise = np.random.normal(0, 100, n)
    pullbacks = np.sin(np.linspace(0, 15 * np.pi, n)) * 500
    prices = trend + noise + pullbacks

    test_data = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.001, n)),
        "high": prices * (1 + abs(np.random.normal(0, 0.005, n))),
        "low": prices * (1 - abs(np.random.normal(0, 0.005, n))),
        "close": prices,
        "volume": np.random.uniform(100, 2000, n),
    })

    strategy = VWAPRSIInstitutionalStrategy()
    sigs = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(sigs)} signals from {len(test_data)} bars")
    for sig in sigs[:5]:
        print(f"\n  {sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")

    # Verify: no crashes on empty data
    empty = pd.DataFrame({"open": [], "high": [], "low": [], "close": [], "volume": []})
    assert strategy.generate_signals(empty) == [], "Should return empty on empty data"
    print("\n✅ All self-tests passed!")
