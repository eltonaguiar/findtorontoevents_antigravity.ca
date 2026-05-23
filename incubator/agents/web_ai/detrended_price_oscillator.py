"""Detrended Price Oscillator - #93. Buys when DPO drops below -2% then recovers above 0."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class DetrendedPriceOscillatorStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.dpo_period=self.p.get('dpo_period',20);self.dpo_th=self.p.get('dpo_threshold',-2.0)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.dpo_period+20: return []
        shift=self.dpo_period//2+1;sma=data['close'].rolling(self.dpo_period).mean()
        dpo=(data['close']-sma.shift(shift))/sma.shift(shift)*100
        atr=self._atr(data);cd,pd_=dpo.iloc[-1],dpo.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pd_) and pd_<self.dpo_th and cd>0:
            return [Signal(symbol,"BUY",0.80,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"DPO flip {pd_:.1f}->{cd:.1f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(DetrendedPriceOscillatorStrategy().generate_signals(d))}")
