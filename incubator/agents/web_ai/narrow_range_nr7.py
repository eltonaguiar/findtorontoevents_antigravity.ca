"""Narrow Range NR7 - #63. Buys on NR7 (narrowest range in 7 bars) breakout upside."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class NarrowRangeNR7Strategy:
    def __init__(self,p=None):
        self.p=p or {};self.nr_period=self.p.get('nr_period',7);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.5);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.nr_period+self.atr_period+5: return []
        rng=data['high']-data['low'];atr=self._atr(data)
        prev_rng=rng.iloc[-2];min_rng=rng.iloc[-self.nr_period-1:-1].min()
        is_nr7=prev_rng<=min_rng;breaks_up=data['close'].iloc[-1]>data['high'].iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if is_nr7 and breaks_up:
            return [Signal(symbol,"BUY",0.80,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"NR7 breakout")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(NarrowRangeNR7Strategy().generate_signals(d))}")
