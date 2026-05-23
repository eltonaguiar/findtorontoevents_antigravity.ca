"""EMA Slope Divergence - Baby Strat #13. Buys when fast EMA slope turns positive while slow EMA slope is still negative (divergence = reversal)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class EMASlopeDivergenceStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.fast = self.p.get('ema_fast', 10)
        self.slow = self.p.get('ema_slow', 30)
        self.slope_lb = self.p.get('slope_lookback', 5)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.3)
        self.sl_atr = self.p.get('sl_atr', 1.4)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.slow + self.slope_lb + 10: return []
        ema_f = data['close'].ewm(span=self.fast).mean()
        ema_s = data['close'].ewm(span=self.slow).mean()
        slope_f = ema_f.diff(self.slope_lb) / self.slope_lb
        slope_s = ema_s.diff(self.slope_lb) / self.slope_lb
        atr = self._atr(data)
        sf, ss, cp, ca = slope_f.iloc[-1], slope_s.iloc[-1], data['close'].iloc[-1], atr.iloc[-1]
        if sf > 0 and ss < 0:
            conf = min(0.65 + abs(sf) / (abs(sf) + abs(ss)) * 0.3, 0.91)
            return [Signal(symbol, "BUY", round(conf, 2), round(cp, 2), round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2), f"FastSlope={sf:.1f} SlowSlope={ss:.1f}")]
        return []

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__ == "__main__":
    np.random.seed(42); n=300; p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.005,'low':p*0.995,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(EMASlopeDivergenceStrategy().generate_signals(d))}")
