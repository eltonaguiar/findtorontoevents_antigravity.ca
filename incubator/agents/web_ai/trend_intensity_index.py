"""Trend Intensity Index - #52. Buys when TII (consecutive up vs down closes ratio) crosses above 60."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class TrendIntensityIndexStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.tii_lb=self.p.get('tii_lookback',20);self.tii_th=self.p.get('tii_threshold',60)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.tii_lb + 10: return []
        diff=data['close'].diff();up=(diff>0).rolling(self.tii_lb).sum();dn=(diff<0).rolling(self.tii_lb).sum()
        tii=up/(up+dn)*100;atr=self._atr(data)
        ct,pt=tii.iloc[-1],tii.iloc[-2];cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pt) and pt<self.tii_th and ct>self.tii_th:
            return [Signal(symbol,"BUY",0.80,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"TII={ct:.0f} crossed")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(TrendIntensityIndexStrategy().generate_signals(d))}")
