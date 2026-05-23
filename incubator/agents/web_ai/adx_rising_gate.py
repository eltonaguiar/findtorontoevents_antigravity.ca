"""ADX Rising Gate - #55. Buys when ADX rises from <20 to >25 (trend ignition) + bullish direction."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class ADXRisingGateStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.adx_period=self.p.get('adx_period',14);self.adx_lo=self.p.get('adx_lo',20);self.adx_hi=self.p.get('adx_hi',25)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.5);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.adx_period * 2 + 10: return []
        h,l,c=data['high'],data['low'],data['close']
        # Simplified ADX proxy using directional movement
        up=h.diff();dn=-l.diff()
        pdm=up.where((up>dn)&(up>0),0);ndm=dn.where((dn>up)&(dn>0),0)
        atr=self._atr(data)
        pdi=100*(pdm.rolling(self.adx_period).mean()/atr)
        ndi=100*(ndm.rolling(self.adx_period).mean()/atr)
        dx=abs(pdi-ndi)/(pdi+ndi)*100
        adx=dx.rolling(self.adx_period).mean()
        ca_now,pa=adx.iloc[-1],adx.iloc[-3];cp,ca=c.iloc[-1],atr.iloc[-1]
        if not pd.isna(pa) and pa<self.adx_lo and ca_now>self.adx_hi and pdi.iloc[-1]>ndi.iloc[-1]:
            return [Signal(symbol,"BUY",0.83,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"ADX={ca_now:.0f} rising")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(ADXRisingGateStrategy().generate_signals(d))}")
