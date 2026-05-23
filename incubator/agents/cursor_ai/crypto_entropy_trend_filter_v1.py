"""
Crypto Entropy Trend Filter Strategy
====================================

Created by: cursor_ai
Date: 2026-02-27
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str

class CryptoEntropyTrendFilterStrategy:
    def __init__(self, params: Optional[dict] = None):
        p=params or {}
        self.window=p.get('window',30)
        self.entropy_threshold=p.get('entropy_threshold',2.2)
        self.atr_period=p.get('atr_period',14)
        self.tp_atr_mult=p.get('tp_atr_mult',2.1)
        self.sl_atr_mult=p.get('sl_atr_mult',1.3)

    def generate_signals(self, data: pd.DataFrame, symbol: str='BTCUSDT') -> List[Signal]:
        if len(data) < self.window + 10: return []
        ent = self._entropy(data['close'].pct_change().dropna().tail(self.window))
        atr = self._atr(data).iloc[-1]
        px = data['close'].iloc[-1]
        if pd.isna(atr) or atr<=0: return []
        trend = data['close'].iloc[-1] > data['close'].rolling(20).mean().iloc[-1]
        if ent < self.entropy_threshold and trend:
            return [Signal(symbol,'BUY',0.74,round(px,2),round(px+atr*self.tp_atr_mult,2),round(px-atr*self.sl_atr_mult,2),f'Low entropy {ent:.2f} trending up')]
        if ent < self.entropy_threshold and not trend:
            return [Signal(symbol,'SELL',0.74,round(px,2),round(px-atr*self.tp_atr_mult,2),round(px+atr*self.sl_atr_mult,2),f'Low entropy {ent:.2f} trending down')]
        return []

    def _entropy(self, series: pd.Series, bins: int = 12) -> float:
        hist, _ = np.histogram(series.dropna(), bins=bins)
        p = hist / max(1, hist.sum())
        p = p[p>0]
        return float(-(p*np.log2(p)).sum())

    def _atr(self, df: pd.DataFrame) -> pd.Series:
        tr = pd.concat([(df['high']-df['low']), (df['high']-df['close'].shift()).abs(), (df['low']-df['close'].shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__ == '__main__':
    np.random.seed(1); n=260; rets=np.random.normal(0.0001,0.015,n); px=48000*np.exp(np.cumsum(rets))
    df=pd.DataFrame({'open':px,'high':px*1.01,'low':px*0.99,'close':px,'volume':np.random.uniform(100,900,n)})
    print(CryptoEntropyTrendFilterStrategy().generate_signals(df))
