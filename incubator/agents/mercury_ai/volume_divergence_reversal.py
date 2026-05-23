"""
VolumeDivergence_Reversal — Mercury AI (Inception)
===================================================
1h reversal when volume drops while price falls in a 4h downtrend.

Entry: 4h EMA-20 < EMA-50 (downtrend) AND 1h close < prev close AND
       1h volume < 0.7x vol EMA-20 AND price makes new 1h low.
Exit:  TP = entry + 1.0x ATR-14, SL = entry - 1.5x ATR-14.
Filter: Skip if candle range < 0.3x ATR-14.

Why unique: Volume-price divergence + higher-TF bearish EMA targets
short-term rebounds that breakout-only strategies miss.

Best regime: Bearish, moderately volatile markets.
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


class VolumeDivergence_ReversalStrategy:
    """1h reversal when volume drops while price falls in a 4h downtrend."""
    name = "volume_divergence_reversal"
    version = "1.0.0"
    agent = "mercury_ai"

    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.ema_fast = self.p.get('ema_fast', 20)
        self.ema_slow = self.p.get('ema_slow', 50)
        self.vol_ema_len = self.p.get('vol_ema', 20)
        self.vol_factor = self.p.get('vol_factor', 0.7)
        self.atr_mult_tp = self.p.get('atr_mult_tp', 1.0)
        self.atr_mult_sl = self.p.get('atr_mult_sl', 1.5)
        self.atr_period = self.p.get('atr_period', 14)
        # 4h EMA proxy on 1h data
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

        # Indicators
        vol_ema = data['volume'].ewm(span=self.vol_ema_len, adjust=False).mean()
        atr = self._atr(data, self.atr_period)

        # 4h trend proxy
        if 'ema_4h' in data.columns:
            ema_4h_fast = data['ema_4h']
            ema_4h_slow = data['close'].ewm(span=self.ema_4h_slow, adjust=False).mean()
        else:
            ema_4h_fast = data['close'].ewm(span=self.ema_4h_fast, adjust=False).mean()
            ema_4h_slow = data['close'].ewm(span=self.ema_4h_slow, adjust=False).mean()

        signals = []
        scan_start = max(min_bars, len(data) - 20)
        for i in range(scan_start, len(data)):
            if i < 2:
                continue

            price = data['close'].iloc[i]
            prev_price = data['close'].iloc[i - 1]
            vol = data['volume'].iloc[i]
            atr_val = atr.iloc[i]
            low_now = data['low'].iloc[i]
            low_prev = data['low'].iloc[i - 1]
            high_now = data['high'].iloc[i]

            if pd.isna(atr_val) or atr_val <= 0:
                continue

            # 4h downtrend: fast EMA < slow EMA
            if ema_4h_fast.iloc[i] >= ema_4h_slow.iloc[i]:
                continue

            # Price must be falling
            if price >= prev_price:
                continue

            # Volume must be low (divergence)
            vol_ema_val = vol_ema.iloc[i]
            if pd.isna(vol_ema_val) or vol >= self.vol_factor * vol_ema_val:
                continue

            # New lower low
            if low_now >= low_prev:
                continue

            # Filter tiny candles
            if (high_now - low_now) < 0.3 * atr_val:
                continue

            tp = price + atr_val * self.atr_mult_tp
            sl = price - atr_val * self.atr_mult_sl
            vol_ratio = vol / vol_ema_val if vol_ema_val > 0 else 0
            confidence = min(0.85, 0.65 + (self.vol_factor - vol_ratio) * 0.3)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=price,
                take_profit=tp,
                stop_loss=sl,
                reason=f"Vol divergence {vol_ratio:.2f}x EMA, 4h downtrend, new low"
            ))

        return signals


if __name__ == "__main__":
    np.random.seed(1)
    n = 300
    close = np.cumsum(np.random.randn(n) * 15) + 21000
    high = close + np.abs(np.random.randn(n) * 50)
    low = close - np.abs(np.random.randn(n) * 50)
    volume = np.abs(np.random.randn(n) * 800) + 4000

    df = pd.DataFrame({
        'open': close + np.random.randn(n) * 5,
        'high': high, 'low': low, 'close': close, 'volume': volume
    })

    strat = VolumeDivergence_ReversalStrategy()
    sigs = strat.generate_signals(df)
    print(f"Generated {len(sigs)} signal(s)")
    for s in sigs[:5]:
        print(f"  {s.direction} @ {s.entry_price:.2f}  TP:{s.take_profit:.2f}  SL:{s.stop_loss:.2f}  {s.reason}")
