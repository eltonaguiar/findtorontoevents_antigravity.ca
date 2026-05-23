"""Close Location Value - #40. Buys when CLV (close-low)/(high-low) accumulates negative for 5+ bars then flips positive."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class CloseLocationValueStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.clv_lb=self.p.get('clv_lookback',5);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.4)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.clv_lb + self.atr_period + 10: return []
        rng = data['high'] - data['low']
        clv = ((data['close'] - data['low']) - (data['high'] - data['close'])) / rng.replace(0, np.nan)
        clv = clv.fillna(0)
        clv_ma = clv.rolling(self.clv_lb).mean()
        atr = self._atr(data)
        cc, pc = clv_ma.iloc[-1], clv_ma.iloc[-2]
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        if not pd.isna(pc) and pc < -0.3 and cc > 0:
            conf = min(0.7 + abs(pc) * 0.3, 0.90)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"CLV flip {pc:.2f}->{cc:.2f}")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.008,'low':p*0.992,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(CloseLocationValueStrategy().generate_signals(d))}")
