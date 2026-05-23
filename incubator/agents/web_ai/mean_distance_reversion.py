"""Mean Distance Reversion - #41. Buys when price deviation from 50-EMA exceeds -2x ATR (rubber-band snap back)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class MeanDistanceReversionStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.ema_period=self.p.get('ema_period',50);self.dev_mult=self.p.get('deviation_mult',2.0)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.ema_period + 20: return []
        ema = data['close'].ewm(span=self.ema_period).mean()
        atr = self._atr(data)
        cp, ce, ca = data['close'].iloc[-1], ema.iloc[-1], atr.iloc[-1]
        deviation = (cp - ce) / ca if ca > 0 else 0
        if deviation < -self.dev_mult:
            conf = min(0.7 + abs(deviation - self.dev_mult) * 0.1, 0.93)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"EMAdev={deviation:.1f}xATR")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0005,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(MeanDistanceReversionStrategy().generate_signals(d))}")
