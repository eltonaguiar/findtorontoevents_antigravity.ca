"""Volatility Mean Reversion - #38. Buys when realized vol drops 50%+ from its 30-bar peak (vol compression = opportunity)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class VolatilityMeanReversionStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.vol_period=self.p.get('vol_period',20);self.vol_peak_lb=self.p.get('vol_peak_lookback',30)
        self.compression_th=self.p.get('compression_threshold',0.50);self.ema_period=self.p.get('ema_period',20)
        self.atr_period=self.p.get('atr_period',14);self.tp_atr=self.p.get('tp_atr',2.0);self.sl_atr=self.p.get('sl_atr',1.5)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.vol_peak_lb + self.vol_period + 10: return []
        ret = data['close'].pct_change()
        rvol = ret.rolling(self.vol_period).std() * np.sqrt(252)
        vol_peak = rvol.rolling(self.vol_peak_lb).max()
        ema = data['close'].ewm(span=self.ema_period).mean()
        atr = self._atr(data)
        cv, vp = rvol.iloc[-1], vol_peak.iloc[-1]
        cp, ce, ca = data['close'].iloc[-1], ema.iloc[-1], atr.iloc[-1]
        ratio = cv / vp if vp > 0 else 1.0
        if ratio < self.compression_th and cp > ce:
            conf = min(0.72 + (self.compression_th - ratio) * 0.4, 0.91)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"VolCompr={ratio:.2f}")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0001,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(VolatilityMeanReversionStrategy().generate_signals(d))}")
