"""EMA Crossover Pullback - #64. Buys after 10/30 EMA golden cross + first pullback to 10-EMA."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class EMACrossoverPullbackStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.fast=self.p.get('ema_fast',10);self.slow=self.p.get('ema_slow',30)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.slow+20: return []
        ef=data['close'].ewm(span=self.fast).mean();es=data['close'].ewm(span=self.slow).mean()
        atr=self._atr(data);cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        crossed_recently=ef.iloc[-5]<=es.iloc[-5] and ef.iloc[-1]>es.iloc[-1]
        near_fast=abs(cp-ef.iloc[-1])/ca<0.4 if ca>0 else False
        if crossed_recently and near_fast and cp>ef.iloc[-1]:
            return [Signal(symbol,"BUY",0.81,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"EMAx pullback")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(EMACrossoverPullbackStrategy().generate_signals(d))}")
