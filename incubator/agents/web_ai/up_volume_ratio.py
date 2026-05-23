"""Up Volume Ratio - #75. Buys when up-volume/total-volume ratio exceeds 70% over 10 bars."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class UpVolumeRatioStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.lb=self.p.get('lookback',10);self.ratio_th=self.p.get('ratio_threshold',0.70)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.2);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.lb+10 or 'volume' not in data: return []
        up_mask=data['close'].diff()>0;up_vol=(data['volume']*up_mask).rolling(self.lb).sum()
        total_vol=data['volume'].rolling(self.lb).sum();ratio=up_vol/total_vol
        atr=self._atr(data);cr,cp,ca=ratio.iloc[-1],data['close'].iloc[-1],atr.iloc[-1]
        if not pd.isna(cr) and cr>self.ratio_th:
            conf=min(0.7+(cr-self.ratio_th)*1.5,0.91)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"UpVolRatio={cr:.2f}")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(UpVolumeRatioStrategy().generate_signals(d))}")
