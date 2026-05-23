"""Pivot Point Bounce - #39. Buys when price touches classic pivot support (yesterday H+L+C/3 - range) and bounces."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class PivotPointBounceStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.atr_period + 10: return []
        atr = self._atr(data)
        # Classic pivot: (H+L+C)/3 of previous bar
        ph, pl, pc = data['high'].iloc[-2], data['low'].iloc[-2], data['close'].iloc[-2]
        pivot = (ph + pl + pc) / 3
        s1 = 2 * pivot - ph  # Support 1
        cp, cl, ca = data['close'].iloc[-1], data['low'].iloc[-1], atr.iloc[-1]
        # Price touched S1 (low near or below) but closed above
        touched_s1 = cl <= s1 * 1.002
        bounced = cp > s1 and cp > cl
        if touched_s1 and bounced:
            return [Signal(symbol,"BUY",0.78,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"PivotS1={s1:.0f} bounce")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(PivotPointBounceStrategy().generate_signals(d))}")
