"""True Range Percentile - #80. Buys when TR is in lowest 10th percentile (extreme quiet) + bullish bar."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class TrueRangePercentileStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.tr_lb=self.p.get('tr_lookback',60);self.pct_th=self.p.get('pct_threshold',0.10)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.5);self.sl_atr=self.p.get('sl_atr',1.2)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.tr_lb+10: return []
        h,l,c=data['high'],data['low'],data['close']
        tr=pd.concat([h-l,abs(h-c.shift()),abs(l-c.shift())],axis=1).max(axis=1)
        tr_pct=tr.rolling(self.tr_lb).rank(pct=True)
        atr=self._atr(data);tp=tr_pct.iloc[-1];cp,ca=c.iloc[-1],atr.iloc[-1]
        bullish=cp>c.iloc[-2]
        if not pd.isna(tp) and tp<self.pct_th and bullish:
            conf=min(0.78+(self.pct_th-tp)*3,0.93)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"TR pct={tp:.2f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(TrueRangePercentileStrategy().generate_signals(d))}")
