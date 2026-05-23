"""Z-Score Mean Reversion - Baby Strat #17. Buys when price z-score (from 50-period mean) drops below -2.0."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class ZScoreMeanReversionStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.zscore_lb = self.p.get('zscore_lookback', 50)
        self.zscore_th = self.p.get('zscore_threshold', -2.0)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.zscore_lb + 10: return []
        close = data['close']
        ma = close.rolling(self.zscore_lb).mean()
        std = close.rolling(self.zscore_lb).std()
        zscore = (close - ma) / std
        atr = self._atr(data)
        cp, ca, zs = close.iloc[-1], atr.iloc[-1], zscore.iloc[-1]
        if not pd.isna(zs) and zs < self.zscore_th:
            conf = min(0.65 + abs(zs - self.zscore_th) * 0.1, 0.93)
            return [Signal(symbol, "BUY", round(conf, 2), round(cp, 2), round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2), f"Zscore={zs:.2f}")]
        return []

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__ == "__main__":
    np.random.seed(42); n=300; p=50000*np.exp(np.random.normal(-0.0005,0.025,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.005,'low':p*0.995,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(ZScoreMeanReversionStrategy().generate_signals(d))}")
