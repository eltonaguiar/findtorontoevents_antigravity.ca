"""Volume Dry Up Breakout - #35. Buys when volume drops to 20th percentile then price makes new 10-bar high."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class VolumeDryUpBreakoutStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.vol_lb=self.p.get('vol_lookback',30);self.vol_pct_th=self.p.get('vol_pct_threshold',0.20)
        self.break_lb=self.p.get('breakout_lookback',10);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.5);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.vol_lb + self.break_lb + 10 or 'volume' not in data: return []
        vol_pct = data['volume'].rolling(self.vol_lb).rank(pct=True)
        hi = data['high'].rolling(self.break_lb).max()
        atr = self._atr(data)
        cp,ca = data['close'].iloc[-1],atr.iloc[-1]
        vp = vol_pct.iloc[-2] if not pd.isna(vol_pct.iloc[-2]) else 0.5  # Previous bar low vol
        breakout = cp > hi.iloc[-2]
        if vp < self.vol_pct_th and breakout:
            return [Signal(symbol,"BUY",0.80,round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"VolDryUp pct={vp:.2f} Break")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(VolumeDryUpBreakoutStrategy().generate_signals(d))}")
