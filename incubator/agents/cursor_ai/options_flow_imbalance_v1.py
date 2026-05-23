"""
Options Flow Imbalance Strategy
===============================

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

class OptionsFlowImbalanceStrategy:
    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.call_put_threshold = p.get('call_put_threshold', 1.4)
        self.rsi_period = p.get('rsi_period', 14)
        self.atr_period = p.get('atr_period', 14)
        self.tp_atr_mult = p.get('tp_atr_mult', 2.3)
        self.sl_atr_mult = p.get('sl_atr_mult', 1.4)

    def generate_signals(self, data: pd.DataFrame, symbol: str = 'BTCUSDT') -> List[Signal]:
        if len(data) < 30:
            return []
        rsi = self._rsi(data['close'])
        atr = self._atr(data)
        cp_ratio = self._mock_options_cp_ratio(symbol)
        px = data['close'].iloc[-1]
        a = float(atr.iloc[-1]) if pd.notna(atr.iloc[-1]) else 0
        if a <= 0:
            return []
        out = []
        if cp_ratio > self.call_put_threshold and rsi.iloc[-1] > 52:
            out.append(Signal(symbol, 'BUY', round(min(0.92, 0.55 + (cp_ratio-1)*0.2), 3), round(px, 2), round(px + a*self.tp_atr_mult, 2), round(px - a*self.sl_atr_mult, 2), f'Call/Put {cp_ratio:.2f} bullish flow'))
        elif cp_ratio < 1/self.call_put_threshold and rsi.iloc[-1] < 48:
            out.append(Signal(symbol, 'SELL', round(min(0.92, 0.55 + (1-cp_ratio)*0.2), 3), round(px, 2), round(px - a*self.tp_atr_mult, 2), round(px + a*self.sl_atr_mult, 2), f'Call/Put {cp_ratio:.2f} bearish flow'))
        return out

    def _rsi(self, s: pd.Series) -> pd.Series:
        d = s.diff(); g = d.where(d>0,0).rolling(self.rsi_period).mean(); l = (-d.where(d<0,0)).rolling(self.rsi_period).mean()
        return 100 - (100 / (1 + g/l.replace(0,np.nan)))

    def _atr(self, df: pd.DataFrame) -> pd.Series:
        tr = pd.concat([(df['high']-df['low']), (df['high']-df['close'].shift()).abs(), (df['low']-df['close'].shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def _mock_options_cp_ratio(self, symbol: str) -> float:
        np.random.seed(abs(hash(symbol)) % 10000)
        return float(np.random.uniform(0.6, 1.8))

if __name__ == '__main__':
    np.random.seed(42)
    n=220; rets=np.random.normal(0.0002,0.02,n); px=50000*np.exp(np.cumsum(rets))
    df=pd.DataFrame({'open':px*(1+np.random.normal(0,0.001,n)),'high':px*(1+np.abs(np.random.normal(0,0.01,n))),'low':px*(1-np.abs(np.random.normal(0,0.01,n))),'close':px,'volume':np.random.uniform(200,1500,n)})
    s=OptionsFlowImbalanceStrategy(); sig=s.generate_signals(df)
    print(f'Generated {len(sig)} signals'); [print(x) for x in sig[:3]]
