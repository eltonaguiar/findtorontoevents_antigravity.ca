"""Parabolic Stop Reversal - #69. Buys when simplified parabolic SAR flips from above to below price."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class ParabolicStopReversalStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.af_start=self.p.get('af_start',0.02);self.af_max=self.p.get('af_max',0.20)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.5);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.atr_period+20: return []
        # Simplified: use EMA as SAR proxy
        ema_fast=data['close'].ewm(span=5).mean();ema_slow=data['close'].ewm(span=20).mean()
        atr=self._atr(data);cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        # SAR flip: price was below both EMAs, now above both
        prev_below=data['close'].iloc[-3]<ema_fast.iloc[-3] and data['close'].iloc[-3]<ema_slow.iloc[-3]
        now_above=cp>ema_fast.iloc[-1] and cp>ema_slow.iloc[-1]
        if prev_below and now_above:
            return [Signal(symbol,"BUY",0.79,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"Parabolic flip UP")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(ParabolicStopReversalStrategy().generate_signals(d))}")
