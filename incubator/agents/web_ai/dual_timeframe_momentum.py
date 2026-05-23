"""Dual Timeframe Momentum - #47. Buys when both 5-bar and 20-bar ROC are positive (short+medium alignment)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class DualTimeframeMomentumStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.fast_roc=self.p.get('fast_roc',5);self.slow_roc=self.p.get('slow_roc',20)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.slow_roc + 10: return []
        roc_f=data['close'].pct_change(self.fast_roc)*100;roc_s=data['close'].pct_change(self.slow_roc)*100
        atr=self._atr(data);rf,rs=roc_f.iloc[-1],roc_s.iloc[-1]
        cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(rs) and rf>0 and rs>0 and rf>rs:  # Fast > Slow = accelerating
            conf=min(0.7+rf*0.02,0.90)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"ROC5={rf:.1f} ROC20={rs:.1f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(DualTimeframeMomentumStrategy().generate_signals(d))}")
