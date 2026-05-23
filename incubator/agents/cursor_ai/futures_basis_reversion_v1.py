"""
Futures Basis Reversion Strategy
================================

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

class FuturesBasisReversionStrategy:
    def __init__(self, params: Optional[dict] = None):
        p=params or {}
        self.basis_z=p.get('basis_z',1.8)
        self.atr_period=p.get('atr_period',14)
        self.tp_atr_mult=p.get('tp_atr_mult',1.8)
        self.sl_atr_mult=p.get('sl_atr_mult',1.2)

    def generate_signals(self, data: pd.DataFrame, symbol: str='BTCUSDT') -> List[Signal]:
        if len(data)<40: return []
        px=data['close'].iloc[-1]
        basis=self._mock_basis(symbol)
        atr=self._atr(data).iloc[-1]
        if pd.isna(atr) or atr<=0: return []
        if basis > self.basis_z:
            return [Signal(symbol,'SELL',0.71,round(px,2),round(px-atr*self.tp_atr_mult,2),round(px+atr*self.sl_atr_mult,2),f'Positive basis z={basis:.2f} mean reversion short')]
        if basis < -self.basis_z:
            return [Signal(symbol,'BUY',0.71,round(px,2),round(px+atr*self.tp_atr_mult,2),round(px-atr*self.sl_atr_mult,2),f'Negative basis z={basis:.2f} mean reversion long')]
        return []

    def _mock_basis(self, symbol:str)->float:
        np.random.seed((abs(hash(symbol))+77)%10000)
        return float(np.random.normal(0,2.2))

    def _atr(self, df):
        tr=pd.concat([(df['high']-df['low']),(df['high']-df['close'].shift()).abs(),(df['low']-df['close'].shift()).abs()],axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__=='__main__':
    np.random.seed(5); n=220; rets=np.random.normal(0.0002,0.02,n); px=50000*np.exp(np.cumsum(rets))
    df=pd.DataFrame({'open':px,'high':px*1.01,'low':px*0.99,'close':px,'volume':np.random.uniform(100,1400,n)})
    print(FuturesBasisReversionStrategy().generate_signals(df))
