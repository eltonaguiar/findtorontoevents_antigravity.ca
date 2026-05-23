"""Kurtosis Regime - #46. Buys when return kurtosis > 5 (fat tails = extreme move) + positive momentum."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class KurtosisRegimeStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.kurt_lb=self.p.get('kurt_lookback',30);self.kurt_th=self.p.get('kurt_threshold',5.0)
        self.mom_period=self.p.get('mom_period',5);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.kurt_lb + 20: return []
        ret=data['close'].pct_change();kurt=ret.rolling(self.kurt_lb).kurt()
        mom=data['close'].pct_change(self.mom_period)
        atr=self._atr(data);ck,cm=kurt.iloc[-1],mom.iloc[-1]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(ck) and ck>self.kurt_th and cm>0:
            conf=min(0.7+(ck-self.kurt_th)*0.02,0.90)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Kurt={ck:.1f} Mom+")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(KurtosisRegimeStrategy().generate_signals(d))}")
