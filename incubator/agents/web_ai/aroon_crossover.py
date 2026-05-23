"""Aroon Crossover - #92. Buys when Aroon Up crosses above Aroon Down from below 50."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class AroonCrossoverStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.aroon_period=self.p.get('aroon_period',25);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.aroon_period+10: return []
        hi_idx=data['high'].rolling(self.aroon_period).apply(lambda x: x.argmax(),raw=True)
        lo_idx=data['low'].rolling(self.aroon_period).apply(lambda x: x.argmin(),raw=True)
        aroon_up=hi_idx/self.aroon_period*100;aroon_dn=lo_idx/self.aroon_period*100
        atr=self._atr(data);au,ad=aroon_up.iloc[-1],aroon_dn.iloc[-1]
        pau,pad=aroon_up.iloc[-2],aroon_dn.iloc[-2]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(pau) and pau<pad and au>ad:
            return [Signal(symbol,"BUY",0.80,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Aroon cross Up={au:.0f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(AroonCrossoverStrategy().generate_signals(d))}")
