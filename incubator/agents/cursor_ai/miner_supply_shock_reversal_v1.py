"""
Miner Supply Shock Reversal Strategy
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

class MinerSupplyShockReversalStrategy:
    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.flow_threshold = p.get('flow_threshold', 1.8)
        self.rsi_period = p.get('rsi_period', 14)
        self.atr_period = p.get('atr_period', 14)
        self.tp_atr_mult = p.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = p.get('sl_atr_mult', 1.4)

    def generate_signals(self, data: pd.DataFrame, symbol: str='BTCUSDT') -> List[Signal]:
        if len(data) < 40:
            return []
        rsi = self._rsi(data['close']).iloc[-1]
        atr = self._atr(data).iloc[-1]
        px = data['close'].iloc[-1]
        if pd.isna(atr) or atr<=0:
            return []
        miner_flow = self._mock_miner_flow(symbol)
        out=[]
        if miner_flow > self.flow_threshold and rsi < 38:
            out.append(Signal(symbol,'BUY',0.72,round(px,2),round(px+atr*self.tp_atr_mult,2),round(px-atr*self.sl_atr_mult,2),f'Miner sell shock {miner_flow:.2f} with oversold RSI {rsi:.1f}'))
        elif miner_flow < -self.flow_threshold and rsi > 62:
            out.append(Signal(symbol,'SELL',0.72,round(px,2),round(px-atr*self.tp_atr_mult,2),round(px+atr*self.sl_atr_mult,2),f'Miner buy shock {miner_flow:.2f} with overbought RSI {rsi:.1f}'))
        return out

    def _rsi(self, s: pd.Series) -> pd.Series:
        d=s.diff(); g=d.where(d>0,0).rolling(self.rsi_period).mean(); l=(-d.where(d<0,0)).rolling(self.rsi_period).mean()
        return 100-(100/(1+g/l.replace(0,np.nan)))

    def _atr(self, df: pd.DataFrame) -> pd.Series:
        tr=pd.concat([(df['high']-df['low']),(df['high']-df['close'].shift()).abs(),(df['low']-df['close'].shift()).abs()],axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def _mock_miner_flow(self, symbol: str) -> float:
        np.random.seed((abs(hash(symbol))+11) % 10000)
        return float(np.random.normal(0, 2.0))

if __name__ == '__main__':
    np.random.seed(19); n=220; rets=np.random.normal(0.0002,0.02,n); px=50000*np.exp(np.cumsum(rets))
    df=pd.DataFrame({'open':px*(1+np.random.normal(0,0.001,n)),'high':px*(1+np.abs(np.random.normal(0,0.01,n))),'low':px*(1-np.abs(np.random.normal(0,0.01,n))),'close':px,'volume':np.random.uniform(100,1300,n)})
    s=MinerSupplyShockReversalStrategy(); print(s.generate_signals(df))
