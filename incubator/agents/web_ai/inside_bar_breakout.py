"""Inside Bar Breakout - Baby Strat #18. Buys when inside bar (range contained by prior bar) breaks upside."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class InsideBarBreakoutStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.2)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.atr_period + 10: return []
        atr = self._atr(data)
        h, l, c = data['high'], data['low'], data['close']
        # Check if previous bar was inside bar (bar -2 contains bar -1)
        prev_inside = (h.iloc[-2] <= h.iloc[-3]) and (l.iloc[-2] >= l.iloc[-3])
        # Current bar breaks above the inside bar high
        breaks_up = c.iloc[-1] > h.iloc[-2]
        if prev_inside and breaks_up:
            cp, ca = c.iloc[-1], atr.iloc[-1]
            return [Signal(symbol, "BUY", 0.78, round(cp, 2), round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2), "InsideBarBreakUp")]
        return []

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__ == "__main__":
    np.random.seed(42); n=300; p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(InsideBarBreakoutStrategy().generate_signals(d))}")
