"""Median Price Reversion - #82. Buys when close drops >2% below rolling median price."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class MedianPriceReversionStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.lb=self.p.get('lookback',30);self.dev_th=self.p.get('deviation_threshold',-2.0)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.lb+10: return []
        med=data['close'].rolling(self.lb).median();atr=self._atr(data)
        cp,cm,ca=data['close'].iloc[-1],med.iloc[-1],atr.iloc[-1]
        dev=(cp/cm-1)*100
        if dev<self.dev_th:
            conf=min(0.72+abs(dev)*0.03,0.91)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"MedDev={dev:.1f}%")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0005,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(MedianPriceReversionStrategy().generate_signals(d))}")
