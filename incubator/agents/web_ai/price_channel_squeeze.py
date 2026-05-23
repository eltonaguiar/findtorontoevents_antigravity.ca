"""Price Channel Squeeze - #27. Buys when Donchian channel width hits 10th percentile then price breaks upper."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class PriceChannelSqueezeStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.dc_period = self.p.get('dc_period', 20)
        self.pct_lb = self.p.get('pct_lookback', 60)
        self.pct_th = self.p.get('pct_threshold', 0.10)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.5); self.sl_atr = self.p.get('sl_atr', 1.3)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.pct_lb + self.dc_period + 10: return []
        dc_hi = data['high'].rolling(self.dc_period).max()
        dc_lo = data['low'].rolling(self.dc_period).min()
        width = (dc_hi - dc_lo) / dc_lo
        width_pct = width.rolling(self.pct_lb).rank(pct=True)
        atr = self._atr(data)
        cp, wp, ca = data['close'].iloc[-1], width_pct.iloc[-1], atr.iloc[-1]
        if not pd.isna(wp) and wp < self.pct_th and cp > dc_hi.iloc[-2]:
            conf = min(0.78 + (self.pct_th - wp) * 2, 0.94)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"ChanSqueeze pct={wp:.2f}")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1); return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(PriceChannelSqueezeStrategy().generate_signals(d))}")
