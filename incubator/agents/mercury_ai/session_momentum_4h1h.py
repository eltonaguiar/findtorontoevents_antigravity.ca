"""
SessionMomentum_4h1h — Mercury AI (Inception)
==============================================
London-open momentum with 4h uptrend + volume surge.

Entry: 4h EMA-20 > EMA-50 AND 1h close > 1h EMA-20 AND
       1h volume > 1.5x EMA-10(volume) AND hour is 08-10 UTC (London open).
Exit:  TP = entry + 1.2x ATR-14, SL = entry - 0.8x ATR-14.
Filter: Skip if candle range < 0.4x ATR-14.

Why unique: Session-time filter (London open) + higher-TF EMA + volume burst.
Targets the most liquid and directional moves at session open.

Best regime: Trending, liquid markets during London session.
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


class SessionMomentum_4h1hStrategy:
    """London-open momentum with 4h uptrend + volume surge."""
    name = "session_momentum_4h1h"
    version = "1.0.0"
    agent = "mercury_ai"

    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.ema_fast_1h = self.p.get('ema_fast_1h', 20)
        self.vol_ema_len = self.p.get('vol_ema_1h', 10)
        self.vol_factor = self.p.get('vol_factor', 1.5)
        self.atr_mult_tp = self.p.get('atr_mult_tp', 1.2)
        self.atr_mult_sl = self.p.get('atr_mult_sl', 0.8)
        self.atr_period = self.p.get('atr_period', 14)
        # 4h proxy
        self.ema_4h_fast = self.p.get('ema_4h_fast', 80)
        self.ema_4h_slow = self.p.get('ema_4h_slow', 200)
        # London session hours (UTC)
        self.session_start = self.p.get('session_start', 8)
        self.session_end = self.p.get('session_end', 10)

    def _atr(self, data, period=14):
        tr = pd.concat([
            data['high'] - data['low'],
            (data['high'] - data['close'].shift()).abs(),
            (data['low'] - data['close'].shift()).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _get_hour(self, data, idx):
        """Extract hour from timestamp column or index"""
        if 'timestamp' in data.columns:
            ts = data['timestamp'].iloc[idx]
            if hasattr(ts, 'hour'):
                return ts.hour
            return pd.Timestamp(ts).hour
        if hasattr(data.index, 'hour'):
            return data.index[idx].hour
        return idx % 24

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.ema_4h_slow, self.atr_period) + 5
        if len(data) < min_bars:
            return []

        # 1h indicators
        ema_1h = data['close'].ewm(span=self.ema_fast_1h, adjust=False).mean()
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
            price = data['close'].iloc[i]
            vol = data['volume'].iloc[i]
            atr_val = atr.iloc[i]

            if pd.isna(atr_val) or atr_val <= 0:
                continue

            # Session filter (London open)
            hour = self._get_hour(data, i)
            if not (self.session_start <= hour < self.session_end):
                continue

            # 4h uptrend
            if ema_4h_fast.iloc[i] <= ema_4h_slow.iloc[i]:
                continue

            # Price above 1h EMA
            if price <= ema_1h.iloc[i]:
                continue

            # Volume surge
            vol_ema_val = vol_ema.iloc[i]
            if pd.isna(vol_ema_val) or vol < self.vol_factor * vol_ema_val:
                continue

            # Low volatility filter
            candle_range = data['high'].iloc[i] - data['low'].iloc[i]
            if candle_range < 0.4 * atr_val:
                continue

            tp = price + atr_val * self.atr_mult_tp
            sl = price - atr_val * self.atr_mult_sl
            vol_ratio = vol / vol_ema_val if vol_ema_val > 0 else 0
            confidence = min(0.88, 0.70 + (vol_ratio - self.vol_factor) * 0.05)

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=price,
                take_profit=tp,
                stop_loss=sl,
                reason=f"London open h{hour}, 4h EMA up, vol {vol_ratio:.1f}x"
            ))

        return signals


if __name__ == "__main__":
    np.random.seed(2)
    n = 300
    close = np.cumsum(np.random.randn(n) * 12) + 22000
    high = close + np.abs(np.random.randn(n) * 30)
    low = close - np.abs(np.random.randn(n) * 30)
    volume = np.abs(np.random.randn(n) * 600) + 3000

    idx = pd.date_range(start="2024-01-01", periods=n, freq="h", tz="UTC")
    df = pd.DataFrame({
        'open': close + np.random.randn(n) * 5,
        'high': high, 'low': low, 'close': close, 'volume': volume
    }, index=idx)

    strat = SessionMomentum_4h1hStrategy()
    sigs = strat.generate_signals(df)
    print(f"Generated {len(sigs)} signal(s)")
    for s in sigs[:5]:
        print(f"  {s.direction} @ {s.entry_price:.2f}  TP:{s.take_profit:.2f}  SL:{s.stop_loss:.2f}  {s.reason}")
