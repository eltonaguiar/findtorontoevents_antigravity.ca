"""Volume Spike Reversal - #26. Buys when volume is 3x average AND price reverses from low (capitulation volume)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class VolumeSpikeReversalStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.vol_mult = self.p.get('vol_multiplier', 3.0)
        self.vol_lb = self.p.get('vol_lookback', 20)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.2); self.sl_atr = self.p.get('sl_atr', 1.3)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.vol_lb + 10 or 'volume' not in data: return []
        vol_ma = data['volume'].rolling(self.vol_lb).mean()
        atr = self._atr(data)
        cv, cvm = data['volume'].iloc[-1], vol_ma.iloc[-1]
        cp, cl, ch, ca = data['close'].iloc[-1], data['low'].iloc[-1], data['high'].iloc[-1], atr.iloc[-1]
        vol_spike = cv > cvm * self.vol_mult if cvm > 0 else False
        rng = ch - cl
        close_pos = (cp - cl) / rng if rng > 0 else 0.5
        reversal = close_pos > 0.6  # Close in upper portion despite selling
        if vol_spike and reversal:
            conf = min(0.7 + (cv/cvm - self.vol_mult) * 0.05, 0.92)
            return [Signal(symbol, "BUY", round(conf,2), round(cp,2), round(cp+ca*self.tp_atr,2), round(cp-ca*self.sl_atr,2), f"Vol={cv/cvm:.1f}x Recov")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1); return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(VolumeSpikeReversalStrategy().generate_signals(d))}")
