"""Hurst Exponent Gate - #32. Only trades when rolling Hurst < 0.4 (mean-reverting regime) + RSI oversold."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class HurstExponentGateStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.hurst_lb = self.p.get('hurst_lookback', 50)
        self.hurst_th = self.p.get('hurst_threshold', 0.4)
        self.rsi_period = self.p.get('rsi_period', 14); self.rsi_th = self.p.get('rsi_threshold', 35)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0); self.sl_atr = self.p.get('sl_atr', 1.5)
    def _hurst(self, series, n):
        if len(series) < n: return 0.5
        s = series.iloc[-n:].values
        lags = range(2, min(20, n//2))
        tau = [np.std(np.subtract(s[lag:], s[:-lag])) for lag in lags]
        if min(tau) <= 0: return 0.5
        reg = np.polyfit(np.log(list(lags)), np.log(tau), 1)
        return reg[0]
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.hurst_lb + 20: return []
        h = self._hurst(data['close'], self.hurst_lb)
        rsi = self._rsi(data['close'], self.rsi_period)
        atr = self._atr(data)
        cr, cp, ca = rsi.iloc[-1], data['close'].iloc[-1], atr.iloc[-1]
        if h < self.hurst_th and cr < self.rsi_th:
            conf = min(0.7 + (self.hurst_th - h) * 0.5, 0.92)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Hurst={h:.2f} RSI={cr:.0f}")]
        return []
    def _rsi(self, p, n):
        d=p.diff();g=d.where(d>0,0).rolling(n).mean();l=(-d.where(d<0,0)).rolling(n).mean();return 100-(100/(1+g/l))
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(-0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(HurstExponentGateStrategy().generate_signals(d))}")
