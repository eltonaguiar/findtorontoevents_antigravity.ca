"""
JumpDiffusionDetector - Strategy #NEW-5
========================================
UNIQUE: Detects jump events in price process using Barndorff-Nielsen-Shephard test.
Jumps = sudden moves > 4σ of local realized vol. Fade jumps or ride post-jump drift.

LONG: Negative jump detected + recovery started → fade overreaction
SHORT: Positive jump detected + reversal started → fade euphoria jump
Multi-TF: σ is relative to recent history, works on any timeframe.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class JumpDiffusionDetectorStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.rv_lb = self.p.get('rv_lookback', 30)
        self.jump_sigma = self.p.get('jump_sigma', 4.0)
        self.recovery_bars = self.p.get('recovery_bars', 2)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.rv_lb + self.recovery_bars + 10:
            return []

        ret = data['close'].pct_change()
        rv = ret.rolling(self.rv_lb).std()
        atr = self._atr(data)

        # Check for jump a few bars ago
        jump_bar = -self.recovery_bars - 1
        jump_ret = ret.iloc[jump_bar]
        local_rv = rv.iloc[jump_bar - 1]

        cp, ca = data['close'].iloc[-1], atr.iloc[-1]

        if pd.isna(jump_ret) or pd.isna(local_rv) or local_rv <= 0 or pd.isna(ca) or ca <= 0:
            return []

        jump_z = jump_ret / local_rv
        signals = []

        # Negative jump (crash) → LONG if recovering
        if jump_z < -self.jump_sigma:
            recovering = data['close'].iloc[-1] > data['close'].iloc[jump_bar]
            if recovering:
                conf = min(0.72 + abs(jump_z) * 0.02, 0.92)
                signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                    round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                    f"Jump DOWN z={jump_z:.1f}σ LONG fade"))

        # Positive jump (spike) → SHORT if reversing
        if jump_z > self.jump_sigma:
            reversing = data['close'].iloc[-1] < data['close'].iloc[jump_bar]
            if reversing:
                conf = min(0.72 + abs(jump_z) * 0.02, 0.92)
                signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                    round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                    f"Jump UP z={jump_z:.1f}σ SHORT fade"))

        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0, 0.025, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.01, 'low': p * 0.99,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(JumpDiffusionDetectorStrategy().generate_signals(d))}")
