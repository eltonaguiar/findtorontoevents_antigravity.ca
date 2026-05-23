"""
VerifiedSupertrendAiStrategy - Baby Strat
==========================================

Created by: Claude AI
Date: 2026-03-04

Source: TradeSearcher, 154 trades, PF 1.94, 46% WR, +2091% over 10 years

Strategy Logic:
- SuperTrend: ATR(10) * 3.0 multiplier with flip detection
- ADX(14) > 20 as regime filter (only trade in trending markets)
- Volume > 20-bar SMA (participation confirmation)
- Entry on SuperTrend flip from bearish to bullish (BUY) or bullish to bearish (SELL)
- TP: +15% / SL: -6% (2.5:1 R:R)

Why it works:
- SuperTrend adapts to volatility via ATR, avoiding whipsaws in calm markets
- ADX filter eliminates choppy range-bound periods where trend strategies bleed
- Volume confirmation ensures institutional participation behind the move
- 2.5:1 reward-to-risk compensates for 46% WR through asymmetric payoff
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


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 10) -> pd.Series:
    """Average True Range."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def calc_supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
                    atr_period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    """SuperTrend indicator returning upper band, lower band, and direction."""
    atr = calc_atr(high, low, close, atr_period)
    hl2 = (high + low) / 2
    upper_basic = hl2 + multiplier * atr
    lower_basic = hl2 - multiplier * atr

    upper_band = upper_basic.copy()
    lower_band = lower_basic.copy()
    direction = pd.Series(1, index=close.index)  # 1 = bullish, -1 = bearish

    for i in range(1, len(close)):
        if not np.isnan(lower_basic.iloc[i]):
            if lower_basic.iloc[i] > lower_band.iloc[i - 1] or close.iloc[i - 1] < lower_band.iloc[i - 1]:
                lower_band.iloc[i] = lower_basic.iloc[i]
            else:
                lower_band.iloc[i] = lower_band.iloc[i - 1]

        if not np.isnan(upper_basic.iloc[i]):
            if upper_basic.iloc[i] < upper_band.iloc[i - 1] or close.iloc[i - 1] > upper_band.iloc[i - 1]:
                upper_band.iloc[i] = upper_basic.iloc[i]
            else:
                upper_band.iloc[i] = upper_band.iloc[i - 1]

        if close.iloc[i] > upper_band.iloc[i]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

    return pd.DataFrame({"upper": upper_band, "lower": lower_band, "direction": direction})


def calc_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index."""
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr = calc_atr(high, low, close, period)
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.rolling(period).mean()


class VerifiedSupertrendAiStrategy:
    NAME = "Verified SuperTrend AI"
    DESCRIPTION = "Regime-adaptive SuperTrend with ADX filter. PF 1.94, 46% WR, +2091% (TradeSearcher)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.atr_period = self.params.get("atr_period", 10)
        self.multiplier = self.params.get("multiplier", 3.0)
        self.adx_period = self.params.get("adx_period", 14)
        self.adx_threshold = self.params.get("adx_threshold", 20)
        self.vol_period = self.params.get("vol_period", 20)
        self.tp_pct = self.params.get("tp_pct", 0.15)
        self.sl_pct = self.params.get("sl_pct", 0.06)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.atr_period, self.adx_period, self.vol_period) + 20
        if len(data) < min_bars:
            return []

        high = data["high"].astype(float)
        low = data["low"].astype(float)
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)

        st = calc_supertrend(high, low, close, self.atr_period, self.multiplier)
        adx = calc_adx(high, low, close, self.adx_period)
        vol_sma = volume.rolling(self.vol_period).mean()

        current_price = float(close.iloc[-1])
        current_dir = int(st["direction"].iloc[-1])
        prev_dir = int(st["direction"].iloc[-2])
        current_adx = float(adx.iloc[-1])
        current_vol = float(volume.iloc[-1])
        current_vol_sma = float(vol_sma.iloc[-1])

        if np.isnan(current_adx) or np.isnan(current_vol_sma):
            return []

        signals = []
        flip_detected = current_dir != prev_dir
        adx_ok = current_adx > self.adx_threshold
        vol_ok = current_vol > current_vol_sma

        if flip_detected and adx_ok and vol_ok:
            if current_dir == 1:
                confidence = min(0.4 + (current_adx - self.adx_threshold) / 100, 0.90)
                tp = current_price * (1 + self.tp_pct)
                sl = current_price * (1 - self.sl_pct)
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"SuperTrend flip BULLISH: ADX={current_adx:.1f}, vol ratio={current_vol/current_vol_sma:.2f}x",
                ))
            elif current_dir == -1:
                confidence = min(0.4 + (current_adx - self.adx_threshold) / 100, 0.90)
                tp = current_price * (1 - self.tp_pct)
                sl = current_price * (1 + self.sl_pct)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"SuperTrend flip BEARISH: ADX={current_adx:.1f}, vol ratio={current_vol/current_vol_sma:.2f}x",
                ))

        return signals


if __name__ == "__main__":
    np.random.seed(42)
    n = 300
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))

    test_data = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.001, n)),
        "high": prices * (1 + abs(np.random.normal(0, 0.01, n))),
        "low": prices * (1 - abs(np.random.normal(0, 0.01, n))),
        "close": prices,
        "volume": np.random.uniform(100, 1000, n),
    })

    strategy = VerifiedSupertrendAiStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
