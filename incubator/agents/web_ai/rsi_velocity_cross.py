"""RSI Velocity Cross - #57. Buys when RSI rate-of-change flips from negative to positive below 40."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class RSIVelocityCrossStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.rsi_period=self.p.get('rsi_period',14);self.vel_period=self.p.get('vel_period',3)
        self.rsi_th=self.p.get('rsi_threshold',40);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.4)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.rsi_period + self.vel_period + 10: return []
        rsi=self._rsi(data['close'],self.rsi_period);rsi_vel=rsi.diff(self.vel_period)
        atr=self._atr(data);cr,cv=rsi.iloc[-1],rsi_vel.iloc[-1]
        pv=rsi_vel.iloc[-2];cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pv) and cr<self.rsi_th and pv<0 and cv>0:
            conf=min(0.72+cv*0.02,0.90)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"RSI={cr:.0f} VelFlip")]
        return []
    def _rsi(self,p,n):
        d=p.diff();g=d.where(d>0,0).rolling(n).mean();l=(-d.where(d<0,0)).rolling(n).mean();return 100-(100/(1+g/l))
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(RSIVelocityCrossStrategy().generate_signals(d))}")
