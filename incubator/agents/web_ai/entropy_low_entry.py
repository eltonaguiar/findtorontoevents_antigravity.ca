"""Entropy Low Entry - #56. Buys when Shannon entropy of returns drops below 1.5 (predictable regime)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class EntropyLowEntryStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.ent_lb=self.p.get('entropy_lookback',30);self.ent_th=self.p.get('entropy_threshold',1.5)
        self.ema_period=self.p.get('ema_period',20);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def _entropy(self, series):
        s=series.dropna();bins=np.histogram(s,bins=10)[0];p=bins/bins.sum();p=p[p>0]
        return -np.sum(p*np.log2(p))
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.ent_lb + 20: return []
        ret=data['close'].pct_change().dropna()
        if len(ret)<self.ent_lb: return []
        ent=self._entropy(ret.iloc[-self.ent_lb:])
        ema=data['close'].ewm(span=self.ema_period).mean();atr=self._atr(data)
        cp,ce,ca=data['close'].iloc[-1],ema.iloc[-1],atr.iloc[-1]
        if ent<self.ent_th and cp>ce:
            conf=min(0.7+(self.ent_th-ent)*0.3,0.91)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Entropy={ent:.2f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(EntropyLowEntryStrategy().generate_signals(d))}")
