"""Price Rate Disparity - #87. Buys when disparity index (close vs EMA) drops below -3%."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class PriceRateDisparityStrategy:
    def __init__(self,p=None):
        self.p=p or {};self.ema_period=self.p.get('ema_period',25);self.disp_th=self.p.get('disparity_threshold',-3.0)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data)<self.ema_period+10: return []
        ema=data['close'].ewm(span=self.ema_period).mean();disp=(data['close']/ema-1)*100
        atr=self._atr(data);cd,cp,ca=disp.iloc[-1],data['close'].iloc[-1],atr.iloc[-1]
        if cd<self.disp_th:
            conf=min(0.72+abs(cd)*0.02,0.91)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Disparity={cd:.1f}%")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0005,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(PriceRateDisparityStrategy().generate_signals(d))}")
