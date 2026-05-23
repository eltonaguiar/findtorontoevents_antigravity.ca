"""Momentum Stall Reversal - #36. Buys when strong downward momentum stalls (ROC approaches zero from negative)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class MomentumStallReversalStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.roc_period=self.p.get('roc_period',10);self.stall_th=self.p.get('stall_threshold',0.5)
        self.min_prior_drop=self.p.get('min_prior_drop',-3.0);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.4)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.roc_period + 20: return []
        roc = data['close'].pct_change(self.roc_period) * 100
        atr = self._atr(data)
        cr, pr = roc.iloc[-1], roc.iloc[-3]
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        # Prior strong drop, now stalling near zero
        if not pd.isna(pr) and pr < self.min_prior_drop and abs(cr) < self.stall_th and cr > pr:
            conf = min(0.7 + abs(pr) * 0.02, 0.90)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"ROCstall cur={cr:.1f} prior={pr:.1f}")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0005,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(MomentumStallReversalStrategy().generate_signals(d))}")
