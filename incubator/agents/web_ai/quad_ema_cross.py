"""Quad EMA Cross - #88. Buys when 5EMA > 10EMA > 20EMA > 50EMA (perfect alignment)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class QuadEMACrossStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.5);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<60: return []
        e5=data['close'].ewm(span=5).mean();e10=data['close'].ewm(span=10).mean()
        e20=data['close'].ewm(span=20).mean();e50=data['close'].ewm(span=50).mean()
        atr=self._atr(data);cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        aligned=e5.iloc[-1]>e10.iloc[-1]>e20.iloc[-1]>e50.iloc[-1]
        prev_not=not(e5.iloc[-3]>e10.iloc[-3]>e20.iloc[-3]>e50.iloc[-3])
        if aligned and prev_not:
            return [Signal(symbol,"BUY",0.85,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"4EMA aligned")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(QuadEMACrossStrategy().generate_signals(d))}")
