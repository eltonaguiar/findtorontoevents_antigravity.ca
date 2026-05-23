"""Elder Ray Bull Power - #90. Buys when bull power (high - 13EMA) turns positive from negative."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class ElderRayBullPowerStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.ema_period=self.p.get('ema_period',13);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.2);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.ema_period+10: return []
        ema=data['close'].ewm(span=self.ema_period).mean()
        bull=data['high']-ema;bear=data['low']-ema
        atr=self._atr(data);cb,pb=bull.iloc[-1],bull.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pb) and pb<0 and cb>0 and bear.iloc[-1]<0:
            return [Signal(symbol,"BUY",0.80,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"BullPower flip+")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(ElderRayBullPowerStrategy().generate_signals(d))}")
