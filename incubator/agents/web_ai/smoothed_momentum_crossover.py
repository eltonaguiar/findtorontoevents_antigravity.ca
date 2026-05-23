"""Smoothed Momentum Crossover - #81. Buys when 5-bar EMA of momentum crosses above 0."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class SmoothedMomentumCrossoverStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.mom_period=self.p.get('mom_period',10);self.smooth=self.p.get('smooth_period',5)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.2);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.mom_period+self.smooth+10: return []
        mom=data['close'].diff(self.mom_period);smom=mom.ewm(span=self.smooth).mean()
        atr=self._atr(data);cm,pm=smom.iloc[-1],smom.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pm) and pm<0 and cm>0:
            return [Signal(symbol,"BUY",0.79,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"SmoothMom cross0")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(SmoothedMomentumCrossoverStrategy().generate_signals(d))}")
