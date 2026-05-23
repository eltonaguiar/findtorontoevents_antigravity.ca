"""OBV Divergence - #54. Buys when price makes lower low but OBV makes higher low."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str
class OBVDivergenceStrategy:
    def __init__(self, p=None):
        self.p=p or {};self.div_lb=self.p.get('div_lookback',15);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.2);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol="BTCUSDT") -> List[Signal]:
        if len(data) < self.div_lb + 10 or 'volume' not in data: return []
        direction=np.sign(data['close'].diff());obv=(direction*data['volume']).cumsum()
        atr=self._atr(data);cp,ca=data['close'].iloc[-1],atr.iloc[-1]
        p_now=data['close'].iloc[-1];p_prev=data['close'].iloc[-1-self.div_lb]
        o_now=obv.iloc[-1];o_prev=obv.iloc[-1-self.div_lb]
        if p_now<p_prev and o_now>o_prev:
            return [Signal(symbol,"BUY",0.82,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),"OBV bullish div")]
        return []
    def _atr(self,d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)});print(f"Signals: {len(OBVDivergenceStrategy().generate_signals(d))}")
