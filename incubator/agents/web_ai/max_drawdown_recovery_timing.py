"""
MaxDrawdownRecoveryTiming - Strategy #NEW-15
==============================================
UNIQUE: Monitors rolling max drawdown. Entries triggered when drawdown hits extreme
then starts recovering (drawdown shrinking). Both long and short via inverse.

LONG: Max DD exceeded -8% then recovered to -3% → worst is over
SHORT: Max "drawup" exceeded +8% then shrinks to +3% → euphoria fading
Multi-TF: Percentage-based, works on any bar size.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class MaxDrawdownRecoveryTimingStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.dd_lb = self.p.get('dd_lookback', 40)
        self.dd_extreme = self.p.get('dd_extreme', -0.08)
        self.dd_recovery = self.p.get('dd_recovery', -0.03)
        self.du_extreme = self.p.get('du_extreme', 0.08)
        self.du_recovery = self.p.get('du_recovery', 0.03)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.3)
        self.sl_atr = self.p.get('sl_atr', 1.3)

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.dd_lb + 10:
            return []
        rolling_max = data['close'].rolling(self.dd_lb).max()
        rolling_min = data['close'].rolling(self.dd_lb).min()
        dd = (data['close'] - rolling_max) / rolling_max
        du = (data['close'] - rolling_min) / rolling_min
        atr = self._atr(data)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        dd_peak = dd.iloc[-self.dd_lb//2:].min()
        dd_now = dd.iloc[-1]
        du_peak = du.iloc[-self.dd_lb//2:].max()
        du_now = du.iloc[-1]
        if pd.isna(ca) or ca <= 0:
            return []
        signals = []
        if dd_peak < self.dd_extreme and dd_now > self.dd_recovery:
            conf = min(0.72 + abs(dd_peak) * 2, 0.92)
            signals.append(Signal(symbol, "BUY", round(conf, 2), round(cp, 2),
                round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2),
                f"DD recovery {dd_peak:.1%}→{dd_now:.1%} LONG"))
        if du_peak > self.du_extreme and du_now < self.du_recovery:
            conf = min(0.72 + du_peak * 2, 0.92)
            signals.append(Signal(symbol, "SELL", round(conf, 2), round(cp, 2),
                round(cp - ca * self.tp_atr, 2), round(cp + ca * self.sl_atr, 2),
                f"DU fade {du_peak:.1%}→{du_now:.1%} SHORT"))
        return signals

if __name__ == "__main__":
    np.random.seed(42); n = 300
    p = 50000 * np.exp(np.random.normal(0, 0.025, n).cumsum())
    d = pd.DataFrame({'open': p * 0.999, 'high': p * 1.01, 'low': p * 0.99,
                       'close': p, 'volume': np.random.uniform(100, 1000, n)})
    print(f"Signals: {len(MaxDrawdownRecoveryTimingStrategy().generate_signals(d))}")
