"""
MultiTF_VolumeBreakout — Mercury AI (Inception)
================================================
1h breakout with 4h EMA trend filter + volume surge confirmation.

Entry: 4h EMA-20 > EMA-50 (uptrend) AND 1h close > 1h EMA-20 AND 1h volume > 2x EMA-20 of volume.
Exit:  TP = entry + 1.5x ATR-14, SL = entry - 1x ATR-14.
Filter: Skip if 1h candle range < 0.5x ATR-14 (low volatility).

Why unique: Combines higher-timeframe EMA trend with strict volume-burst condition,
avoiding price-only breakouts that fire on low-volume noise.

Best regime: Trending, moderately volatile markets.
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class MultiTF_VolumeBreakoutStrategy:
    """1h breakout with 4h EMA trend + volume surge."""
    name = "multitf_volume_breakout"
    version = "1.0.0"
    agent = "mercury_ai"

    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.ema_fast = self.p.get('ema_fast', 20)
        self.ema_slow = self.p.get('ema_slow', 50)
        self.vol_mult = self.p.get('vol_mult', 2.0)
        self.atr_mult_tp = self.p.get('atr_mult_tp', 1.5)
        self.atr_mult_sl = self.p.get('atr_mult_sl', 1.0)
        self.atr_period = self.p.get('atr_period', 14)
        # 4h EMA proxy: use 4x the span on 1h data
        self.ema_4h_fast = self.p.get('ema_4h_fast', 80)   # 20 * 4
        self.ema_4h_slow = self.p.get('ema_4h_slow', 200)  # 50 * 4

    def _atr(self, data, period=14):
        tr = pd.concat([
            data['high'] - data['low'],
            (data['high'] - data['close'].shift()).abs(),
            (data['low'] - data['close'].shift()).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.ema_4h_slow, self.atr_period) + 5
        if len(data) < min_bars:
            return []

        # 1h indicators
        ema_fast = data['close'].ewm(span=self.ema_fast, adjust=False).mean()
        vol_ema = data['volume'].ewm(span=self.ema_fast, adjust=False).mean()
        atr = self._atr(data, self.atr_period)

        # 4h trend proxy: longer EMAs on 1h data (span * 4)
        # If ema_4h column provided externally, use it; otherwise compute proxy
        if 'ema_4h' in data.columns:
            ema_4h_fast_vals = data['ema_4h']
            ema_4h_slow_vals = data['close'].ewm(span=self.ema_4h_slow, adjust=False).mean()
        else:
            ema_4h_fast_vals = data['close'].ewm(span=self.ema_4h_fast, adjust=False).mean()
            ema_4h_slow_vals = data['close'].ewm(span=self.ema_4h_slow, adjust=False).mean()

        signals = []
        # Scan last 20 bars for signals (not just the last bar)
        scan_start = max(min_bars, len(data) - 20)
        for i in range(scan_start, len(data)):
            price = data['close'].iloc[i]
            vol = data['volume'].iloc[i]
            atr_val = atr.iloc[i]
            if pd.isna(atr_val) or atr_val <= 0:
                continue

            # 4h uptrend: fast EMA > slow EMA
            if ema_4h_fast_vals.iloc[i] <= ema_4h_slow_vals.iloc[i]:
                continue

            # Price above 1h EMA
            if price <= ema_fast.iloc[i]:
                continue

            # Volume surge
            if pd.isna(vol_ema.iloc[i]) or vol < self.vol_mult * vol_ema.iloc[i]:
                continue

            # Low volatility filter
            candle_range = data['high'].iloc[i] - data['low'].iloc[i]
            if candle_range < 0.5 * atr_val:
                continue

            tp = price + atr_val * self.atr_mult_tp
            sl = price - atr_val * self.atr_mult_sl
            vol_ratio = vol / vol_ema.iloc[i] if vol_ema.iloc[i] > 0 else 0
            confidence = min(0.90, 0.70 + (vol_ratio - self.vol_mult) * 0.05)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=price,
                take_profit=tp,
                stop_loss=sl,
                reason=f"4h EMA trend up, 1h breakout, vol {vol_ratio:.1f}x avg"
            ))

        return signals


if __name__ == "__main__":
    np.random.seed(0)
    n = 300
    close = np.cumsum(np.random.randn(n) * 20) + 20000
    high = close + np.abs(np.random.randn(n) * 50)
    low = close - np.abs(np.random.randn(n) * 50)
    volume = np.abs(np.random.randn(n) * 1000) + 5000

    df = pd.DataFrame({
        'open': close + np.random.randn(n) * 5,
        'high': high, 'low': low, 'close': close, 'volume': volume
    })

    strat = MultiTF_VolumeBreakoutStrategy()
    sigs = strat.generate_signals(df)
    print(f"Generated {len(sigs)} signal(s)")
    for s in sigs[:5]:
        print(f"  {s.direction} @ {s.entry_price:.2f}  TP:{s.take_profit:.2f}  SL:{s.stop_loss:.2f}  {s.reason}")
