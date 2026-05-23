"""Price Acceleration Gate - #60. Buys when 2nd derivative of price (acceleration) turns positive from negative."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class PriceAccelerationGateStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.vel_period=self.p.get('vel_period',5);self.accel_period=self.p.get('accel_period',3)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.2);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.vel_period + self.accel_period + 20: return []
        vel=data['close'].diff(self.vel_period);accel=vel.diff(self.accel_period)
        atr=self._atr(data);ca_now,pa=accel.iloc[-1],accel.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pa) and pa<0 and ca_now>0:
            conf=min(0.72+ca_now/(abs(ca_now)+abs(pa))*0.2,0.90)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"PriceAccel flip+")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(PriceAccelerationGateStrategy().generate_signals(d))}")
