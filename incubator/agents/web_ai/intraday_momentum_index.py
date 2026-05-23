"""Intraday Momentum Index - #86. Buys when IMI (intraday momentum) < 30 for 3 bars then rises."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class IntradayMomentumIndexStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.imi_period=self.p.get('imi_period',14);self.imi_th=self.p.get('imi_threshold',30)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.4)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.imi_period+10: return []
        if 'open' in data:
            gain=(data['close']-data['open']).where(data['close']>data['open'],0)
            loss=(data['open']-data['close']).where(data['close']<data['open'],0)
        else:
            d=data['close'].diff();gain=d.where(d>0,0);loss=(-d).where(d<0,0)
        gs=gain.rolling(self.imi_period).sum();ls=loss.rolling(self.imi_period).sum()
        imi=100*gs/(gs+ls);atr=self._atr(data)
        ci,pi=imi.iloc[-1],imi.iloc[-2];cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pi) and pi<self.imi_th and ci>pi:
            conf=min(0.72+(self.imi_th-pi)*0.02,0.90)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"IMI={ci:.0f} rising")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p*0.999,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(IntradayMomentumIndexStrategy().generate_signals(d))}")
