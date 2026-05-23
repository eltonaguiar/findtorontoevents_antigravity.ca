"""Vortex Indicator Cross - #95. Buys when VI+ crosses above VI- (trend ignition)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class VortexIndicatorCrossStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.vi_period=self.p.get('vi_period',14);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.vi_period+10: return []
        vm_plus=abs(data['high']-data['low'].shift());vm_minus=abs(data['low']-data['high'].shift())
        atr=self._atr(data);tr_sum=atr*self.vi_period
        vi_p=vm_plus.rolling(self.vi_period).sum()/tr_sum
        vi_m=vm_minus.rolling(self.vi_period).sum()/tr_sum
        cvp,cvm=vi_p.iloc[-1],vi_m.iloc[-1];pvp,pvm=vi_p.iloc[-2],vi_m.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pvp) and pvp<pvm and cvp>cvm:
            return [Signal(symbol,"BUY",0.80,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Vortex+ cross")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(VortexIndicatorCrossStrategy().generate_signals(d))}")
