"""Rolling Sharpe Gate - #37. Only buys when rolling 30-bar Sharpe > 0.5 AND pullback occurs (quality momentum)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class RollingSharpeGateStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.sharpe_lb=self.p.get('sharpe_lookback',30);self.sharpe_th=self.p.get('sharpe_threshold',0.5)
        self.ema_period=self.p.get('ema_period',10);self.atr_period=self.p.get('atr_period',14)
        self.tp_atr=self.p.get('tp_atr',2.3);self.sl_atr=self.p.get('sl_atr',1.3)
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.sharpe_lb + 20: return []
        ret = data['close'].pct_change()
        sharpe = ret.rolling(self.sharpe_lb).mean() / ret.rolling(self.sharpe_lb).std() * np.sqrt(252)
        ema = data['close'].ewm(span=self.ema_period).mean()
        atr = self._atr(data)
        cs, cp, ce, ca = sharpe.iloc[-1], data['close'].iloc[-1], ema.iloc[-1], atr.iloc[-1]
        near_ema = abs(cp - ce) / ca < 0.6
        if not pd.isna(cs) and cs > self.sharpe_th and near_ema and cp > ce:
            conf = min(0.7 + (cs - self.sharpe_th) * 0.1, 0.92)
            return [Signal(symbol,"BUY",round(conf,2),round(cp,2),round(cp+ca*self.tp_atr,2),round(cp-ca*self.sl_atr,2),f"Sharpe={cs:.2f} pullback")]
        return []
    def _atr(self, d):
        tr=pd.concat([d['high']-d['low'],abs(d['high']-d['close'].shift()),abs(d['low']-d['close'].shift())],axis=1).max(axis=1);return tr.rolling(self.atr_period).mean()
if __name__=="__main__":
    np.random.seed(42);n=300;p=50000*np.exp(np.random.normal(0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.006,'low':p*0.994,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(RollingSharpeGateStrategy().generate_signals(d))}")
