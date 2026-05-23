"""EMA Ribbon Compression - #24. Buys when 3 EMAs (8/13/21) compress within 0.5% then price breaks above all three."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class EMARibbonCompressionStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.e1 = self.p.get('ema1', 8); self.e2 = self.p.get('ema2', 13); self.e3 = self.p.get('ema3', 21)
        self.compress_th = self.p.get('compress_threshold', 0.005)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.5); self.sl_atr = self.p.get('sl_atr', 1.3)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.e3 + 20: return []
        ema1 = data['close'].ewm(span=self.e1).mean()
        ema2 = data['close'].ewm(span=self.e2).mean()
        ema3 = data['close'].ewm(span=self.e3).mean()
        atr = self._atr(data)
        e1v,e2v,e3v = ema1.iloc[-1],ema2.iloc[-1],ema3.iloc[-1]
        spread = (max(e1v,e2v,e3v) - min(e1v,e2v,e3v)) / e2v
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        if spread < self.compress_th and cp > max(e1v,e2v,e3v):
            conf = min(0.75 + (self.compress_th - spread) * 50, 0.93)
            return [Signal(symbol, "BUY", round(conf,2), round(cp,2), round(cp+ca*self.tp_atr,2), round(cp-ca*self.sl_atr,2), f"Ribbon spread={spread:.4f}")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1); return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(EMARibbonCompressionStrategy().generate_signals(d))}")
