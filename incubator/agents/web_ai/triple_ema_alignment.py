"""Triple EMA Alignment - #34. Buys when 5/13/34 EMAs align bullish + price pulls back to 13-EMA."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class TripleEMAAlignmentStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.e1=self.p.get('ema1',5);self.e2=self.p.get('ema2',13);self.e3=self.p.get('ema3',34)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.e3 + 20: return []
        e1=data['close'].ewm(span=self.e1).mean();e2=data['close'].ewm(span=self.e2).mean();e3=data['close'].ewm(span=self.e3).mean()
        atr=self._atr(data);cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        aligned = e1.iloc[-1] > e2.iloc[-1] > e3.iloc[-1]
        near_e2 = abs(cp - e2.iloc[-1]) / ca < 0.5
        if aligned and near_e2 and cp > e2.iloc[-1]:
            return [Signal(symbol,"BUY",0.82,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"3EMA aligned pullback")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(TripleEMAAlignmentStrategy().generate_signals(d))}")
