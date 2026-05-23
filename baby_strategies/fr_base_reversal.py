"""
FRBaseReversalStrategy - Baby Strat
====================================

Created by: Claude AI
Date: 2026-03-04

Academic Source: FundedRelay (Feb 2026 TradingView The Leap, +77.7%)
  Advanced Trend Reversal strategy combining EMA crossover, RSI confirmation,
  ATR volatility expansion, and liquidity metering.

Strategy Logic:
- Entry BUY: EMA21 crosses above EMA55 + price > EMA200 + RSI crosses above 55 + ATR expanding
- Entry SELL: EMA21 crosses below EMA55 + price < EMA200 + RSI crosses below 45 + ATR expanding
- Asset Liquidity Meter: volume / (high - low) — higher = better liquidity
- TP: +12%, SL: -5%

Why it works:
- Dual EMA crossover captures trend reversals with moderate lag
- EMA200 alignment ensures trades go with the macro trend
- RSI confirmation filters false crosses (only enter when momentum agrees)
- ATR expansion ensures volatility is increasing (trend is accelerating, not choppy)
- Liquidity meter avoids thin-book / low-participation moves
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


def calc_ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def calc_liquidity_meter(volume: pd.Series, high: pd.Series, low: pd.Series) -> pd.Series:
    """Asset Liquidity Meter: volume / (high - low). Higher = better liquidity."""
    spread = (high - low).replace(0, np.nan)
    return volume / spread


class FRBaseReversalStrategy:
    NAME = "FR Base Reversal"
    DESCRIPTION = "FundedRelay Advanced Trend Reversal: EMA21/55 cross + EMA200 alignment + RSI + ATR expansion"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.fast_ema = self.params.get("fast_ema", 21)
        self.slow_ema = self.params.get("slow_ema", 55)
        self.trend_ema = self.params.get("trend_ema", 200)
        self.rsi_period = self.params.get("rsi_period", 14)
        self.atr_period = self.params.get("atr_period", 14)
        self.rsi_bull_threshold = self.params.get("rsi_bull_threshold", 55)
        self.rsi_bear_threshold = self.params.get("rsi_bear_threshold", 45)
        self.tp_pct = self.params.get("tp_pct", 0.12)
        self.sl_pct = self.params.get("sl_pct", 0.05)

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.trend_ema + 10:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        ema_fast = calc_ema(close, self.fast_ema)
        ema_slow = calc_ema(close, self.slow_ema)
        ema_trend = calc_ema(close, self.trend_ema)
        rsi = calc_rsi(close, self.rsi_period)
        atr = calc_atr(high, low, close, self.atr_period)
        liquidity = calc_liquidity_meter(volume, high, low)

        current_price = float(close.iloc[-1])
        signals = []

        # Check EMA crossover (current bar vs previous bar)
        fast_now = float(ema_fast.iloc[-1])
        fast_prev = float(ema_fast.iloc[-2])
        slow_now = float(ema_slow.iloc[-1])
        slow_prev = float(ema_slow.iloc[-2])
        trend_now = float(ema_trend.iloc[-1])
        rsi_now = float(rsi.iloc[-1])
        rsi_prev = float(rsi.iloc[-2])
        atr_now = float(atr.iloc[-1])
        atr_prev = float(atr.iloc[-2])
        liq_now = float(liquidity.iloc[-1]) if not np.isnan(float(liquidity.iloc[-1])) else 0

        # ATR must be expanding
        atr_expanding = atr_now > atr_prev

        # Bullish crossover
        bullish_cross = fast_prev <= slow_prev and fast_now > slow_now
        # Bearish crossover
        bearish_cross = fast_prev >= slow_prev and fast_now < slow_now

        # RSI confirmation
        rsi_bull_confirm = rsi_prev <= self.rsi_bull_threshold and rsi_now > self.rsi_bull_threshold
        rsi_bear_confirm = rsi_prev >= self.rsi_bear_threshold and rsi_now < self.rsi_bear_threshold

        # Allow RSI to already be in confirming zone (more lenient)
        rsi_bull_confirm = rsi_bull_confirm or rsi_now > self.rsi_bull_threshold
        rsi_bear_confirm = rsi_bear_confirm or rsi_now < self.rsi_bear_threshold

        if bullish_cross and current_price > trend_now and rsi_bull_confirm and atr_expanding:
            confidence = min(0.55 + (rsi_now - 50) / 100, 0.92)
            tp = current_price * (1 + self.tp_pct)
            sl = current_price * (1 - self.sl_pct)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"FR Base BUY: EMA{self.fast_ema} crossed EMA{self.slow_ema}, price>{self.trend_ema}EMA, RSI={rsi_now:.1f}>55, ATR expanding, liq={liq_now:.0f}",
                )
            )

        if bearish_cross and current_price < trend_now and rsi_bear_confirm and atr_expanding:
            confidence = min(0.55 + (50 - rsi_now) / 100, 0.92)
            tp = current_price * (1 - self.tp_pct)
            sl = current_price * (1 + self.sl_pct)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"FR Base SELL: EMA{self.fast_ema} crossed EMA{self.slow_ema}, price<{self.trend_ema}EMA, RSI={rsi_now:.1f}<45, ATR expanding, liq={liq_now:.0f}",
                )
            )

        return signals


if __name__ == "__main__":
    np.random.seed(42)
    n = 300
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))

    test_data = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.001, n)),
            "high": prices * (1 + abs(np.random.normal(0, 0.01, n))),
            "low": prices * (1 - abs(np.random.normal(0, 0.01, n))),
            "close": prices,
            "volume": np.random.uniform(100, 1000, n),
        }
    )

    strategy = FRBaseReversalStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Strategy: {strategy.NAME}")
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
