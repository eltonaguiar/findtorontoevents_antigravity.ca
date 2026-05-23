"""Sortino Gate Momentum - #30. Only buys when rolling Sortino ratio > 1.0 AND pullback to 10-EMA."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class SortinoGateMomentumStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.sortino_lb = self.p.get('sortino_lookback', 30)
        self.sortino_th = self.p.get('sortino_threshold', 1.0)
        self.ema_period = self.p.get('ema_period', 10)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.5); self.sl_atr = self.p.get('sl_atr', 1.3)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.sortino_lb + 20: return []
        ret = data['close'].pct_change()
        mean_ret = ret.rolling(self.sortino_lb).mean()
        downside = ret.where(ret < 0, 0).rolling(self.sortino_lb).std()
        sortino = mean_ret / downside
        ema = data['close'].ewm(span=self.ema_period).mean()
        atr = self._atr(data)
        cs, cp, ce, ca = sortino.iloc[-1], data['close'].iloc[-1], ema.iloc[-1], atr.iloc[-1]
        near_ema = abs(cp - ce) / ca < 0.5
        if not pd.isna(cs) and cs > self.sortino_th and near_ema and cp > ce:
            conf = min(0.7 + (cs - self.sortino_th) * 0.1, 0.92)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Sortino={cs:.2f} EMA pull")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1); return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(SortinoGateMomentumStrategy().generate_signals(d))}")
