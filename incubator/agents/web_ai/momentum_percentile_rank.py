"""Momentum Percentile Rank - Baby Strat #16. Buys when 20-period return percentile rank drops below 10% (extreme loser = bounce)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class MomentumPercentileRankStrategy:
    def __init__(self, p: Optional[dict] = None):
        self.p = p or {}
        self.mom_period = self.p.get('mom_period', 20)
        self.rank_lb = self.p.get('rank_lookback', 100)
        self.rank_th = self.p.get('rank_threshold', 0.10)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.rank_lb + self.mom_period + 10: return []
        ret = data['close'].pct_change(self.mom_period)
        rank = ret.rolling(self.rank_lb).rank(pct=True)
        atr = self._atr(data)
        cp, ca = data['close'].iloc[-1], atr.iloc[-1]
        rk = rank.iloc[-1] if not pd.isna(rank.iloc[-1]) else 0.5
        if rk < self.rank_th:
            conf = min(0.7 + (self.rank_th - rk) * 3, 0.92)
            return [Signal(symbol, "BUY", round(conf, 2), round(cp, 2), round(cp + ca * self.tp_atr, 2), round(cp - ca * self.sl_atr, 2), f"MomRank={rk:.2f}")]
        return []

    def _atr(self, d):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__ == "__main__":
    np.random.seed(42); n=300; p=50000*np.exp(np.random.normal(-0.0003,0.02,n).cumsum())
    d=pd.DataFrame({'open':p,'high':p*1.005,'low':p*0.995,'close':p,'volume':np.random.uniform(100,1000,n)})
    print(f"Signals: {len(MomentumPercentileRankStrategy().generate_signals(d))}")
