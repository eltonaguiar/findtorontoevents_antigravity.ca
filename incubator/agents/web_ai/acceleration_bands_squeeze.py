"""Acceleration Bands Squeeze - #85. Buys on squeeze of acceleration bands (upper-lower width min)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class AccelerationBandsSqueezeStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.period=self.p.get('period',20);self.width_lb=self.p.get('width_lookback',40)
        self.pct_th=self.p.get('pct_threshold',0.15);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.5);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.width_lb+self.period+10: return []
        h,l,c=data['high'],data['low'],data['close']
        upper=h*(1+(h-l)/((h+l)/2)*0.5).rolling(self.period).mean()
        lower=l*(1-(h-l)/((h+l)/2)*0.5).rolling(self.period).mean()
        width=(upper-lower)/c;wp=width.rolling(self.width_lb).rank(pct=True)
        atr=self._atr(data);cwp,cp,ca=wp.iloc[-1],c.iloc[-1],atr.iloc[-1]
        if not pd.isna(cwp) and cwp<self.pct_th and cp>upper.iloc[-2]:
            return [Signal(symbol,"BUY",0.82,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"AccBand squeeze={cwp:.2f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(AccelerationBandsSqueezeStrategy().generate_signals(d))}")
