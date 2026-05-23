"""Fractal Breakout - #97. Buys when price breaks above a Williams fractal high (5-bar pattern)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class FractalBreakoutStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.5);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.atr_period+10: return []
        h=data['high'];atr=self._atr(data)
        # Find last fractal high: bar where high > both neighbors (2 each side)
        fractal_hi=None
        for i in range(4,min(20,len(h)-1)):
            if h.iloc[-i]>h.iloc[-i-1] and h.iloc[-i]>h.iloc[-i-2] and h.iloc[-i]>h.iloc[-i+1] and h.iloc[-i]>h.iloc[-i+2]:
                fractal_hi=h.iloc[-i];break
        if fractal_hi is None: return []
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if cp>fractal_hi:
            return [Signal(symbol,"BUY",0.81,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Fractal break>{fractal_hi:.0f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(FractalBreakoutStrategy().generate_signals(d))}")
