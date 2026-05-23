"""Avg Directional Movement - #89. Buys when +DI crosses above -DI with ADX > 20."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class AvgDirectionalMovementStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.di_period=self.p.get('di_period',14);self.adx_th=self.p.get('adx_threshold',20)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.di_period*2+10: return []
        h,l=data['high'],data['low'];up=h.diff();dn=-l.diff()
        pdm=up.where((up>dn)&(up>0),0);ndm=dn.where((dn>up)&(dn>0),0)
        atr=self._atr(data);pdi=pdm.rolling(self.di_period).mean()/atr*100
        ndi=ndm.rolling(self.di_period).mean()/atr*100
        dx=abs(pdi-ndi)/(pdi+ndi)*100;adx=dx.rolling(self.di_period).mean()
        cp_di,cn_di,pp_di,pn_di=pdi.iloc[-1],ndi.iloc[-1],pdi.iloc[-2],ndi.iloc[-2]
        cadx=adx.iloc[-1];cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(cadx) and pp_di<pn_di and cp_di>cn_di and cadx>self.adx_th:
            return [Signal(symbol,"BUY",0.82,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"+DI cross ADX={cadx:.0f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(AvgDirectionalMovementStrategy().generate_signals(d))}")
