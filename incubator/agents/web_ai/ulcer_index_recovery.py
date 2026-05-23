"""Ulcer Index Recovery - #98. Buys when Ulcer Index (drawdown pain) peaks then drops 50%."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class UlcerIndexRecoveryStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.ui_period=self.p.get('ui_period',14);self.peak_lb=self.p.get('peak_lookback',10)
        self.recovery_th=self.p.get('recovery_threshold',0.50);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.ui_period+self.peak_lb+10: return []
        rolling_max=data['close'].rolling(self.ui_period).max()
        pct_dd=((data['close']-rolling_max)/rolling_max*100)**2
        ui=np.sqrt(pct_dd.rolling(self.ui_period).mean())
        ui_peak=ui.rolling(self.peak_lb).max();atr=self._atr(data)
        cu,up=ui.iloc[-1],ui_peak.iloc[-1];cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(up) and up>0 and cu/up<self.recovery_th and cu<up:
            conf=min(0.72+(1-cu/up)*0.2,0.91)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Ulcer recovery={cu/up:.2f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0002,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(UlcerIndexRecoveryStrategy().generate_signals(d))}")
