"""VWAP Deviation Snap - #43. Buys when price deviates >2 ATR below VWAP proxy then snaps back."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class VWAPDeviationSnapStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.vwap_lb=self.p.get('vwap_lookback',20);self.dev_th=self.p.get('deviation_threshold',2.0)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.4)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.vwap_lb + 10: return []
        if 'volume' in data:
            vwap=(data['close']*data['volume']).rolling(self.vwap_lb).sum()/data['volume'].rolling(self.vwap_lb).sum()
        else: vwap=data['close'].rolling(self.vwap_lb).mean()
        atr=self._atr(data);cp,cv,ca=data['close'].iloc[-1],vwap.iloc[-1],atr.iloc[-1]
        dev=(cp-cv)/ca if ca>0 else 0
        prev_dev=(data['close'].iloc[-2]-vwap.iloc[-2])/atr.iloc[-2] if atr.iloc[-2]>0 else 0
        if prev_dev < -self.dev_th and dev > prev_dev:  # Was deeply below, now recovering
            conf=min(0.7+abs(prev_dev)*0.05,0.91)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"VWAPdev={dev:.1f}ATR snap")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0005,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(VWAPDeviationSnapStrategy().generate_signals(d))}")
