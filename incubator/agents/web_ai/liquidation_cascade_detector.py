"""
LiquidationCascadeDetector - Strategy #NEW-3
=============================================
UNIQUE: Detects liquidation cascades via extreme price acceleration + volume explosion.
Cascades create opportunities: fade the cascade (mean revert) or ride the follow-through.

LONG: Downward cascade detected (price accel < -3σ + vol 4x) → fade for snap-back
SHORT: Upward cascade detected (price accel > +3σ + vol 4x) → fade euphoria
Works across all timeframes — uses sigma-based thresholds.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class LiquidationCascadeDetectorStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.accel_lb = self.p.get('accel_lookback', 30)
        self.accel_sigma = self.p.get('accel_sigma', 3.0)
        self.vol_mult = self.p.get('vol_multiplier', 4.0)
        self.vol_lb = self.p.get('vol_lookback', 20)
        self.recovery_bars = self.p.get('recovery_bars', 2)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.accel_lb + 10:
            return []

        ret = data['close'].pct_change()
        accel = ret.diff()  # 2nd derivative of price
        accel_mean = accel.rolling(self.accel_lb).mean()
        accel_std = accel.rolling(self.accel_lb).std()
        accel_z = (accel - accel_mean) / accel_std

        vol_ma = data['volume'].rolling(self.vol_lb).mean() if 'volume' in data else pd.Series(1, index=data.index)
        vol_ratio = data['volume'] / vol_ma if 'volume' in data else pd.Series(1, index=data.index)

        atr = self._atr(data)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        az = accel_z.iloc[-self.recovery_bars - 1]  # Cascade bar (few bars ago)
        vr = vol_ratio.iloc[-self.recovery_bars - 1]
        recovering = data['close'].iloc[-1] > data['close'].iloc[-self.recovery_bars]

        if pd.isna(az) or pd.isna(ca) or ca <= 0:
            return []

        signals = []

        # Downward cascade → LONG (fade the liquidation)
        if az < -self.accel_sigma and vr > self.vol_mult and recovering:
            conf = min(0.72 + abs(az) * 0.03, 0.92)
            signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                f"LiqCascade DOWN az={az:.1f}σ vol={vr:.1f}x LONG fade"))

        # Upward cascade → SHORT (fade the squeeze)
        up_recovering = data['close'].iloc[-1] < data['close'].iloc[-self.recovery_bars]
        if az > self.accel_sigma and vr > self.vol_mult and up_recovering:
            conf = min(0.72 + abs(az) * 0.03, 0.92)
            signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                f"LiqCascade UP az={az:.1f}σ vol={vr:.1f}x SHORT fade"))

        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0, 0.025, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.01, 'low': p * 0.99,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(LiquidationCascadeDetectorStrategy().generate_signals(d))}")
