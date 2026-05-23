"""
DEX Liquidity Imbalance Strategy
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

class DexLiquidityImbalanceStrategy:
    def __init__(self, params: Optional[dict] = None):
        p=params or {}
        self.imbalance_threshold=p.get('imbalance_threshold',1.35)
        self.atr_period=p.get('atr_period',14)
        self.tp_atr_mult=p.get('tp_atr_mult',2.4)
        self.sl_atr_mult=p.get('sl_atr_mult',1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str='BTCUSDT') -> List[Signal]:
        if len(data)<30: return []
        atr=self._atr(data).iloc[-1]; px=data['close'].iloc[-1]
        if pd.isna(atr) or atr<=0: return []
        imbalance=self._mock_pool_imbalance(symbol)
        if imbalance>self.imbalance_threshold:
            return [Signal(symbol,'BUY',0.73,round(px,2),round(px+atr*self.tp_atr_mult,2),round(px-atr*self.sl_atr_mult,2),f'DEX buy-side imbalance {imbalance:.2f}')]
        if imbalance<1/self.imbalance_threshold:
            return [Signal(symbol,'SELL',0.73,round(px,2),round(px-atr*self.tp_atr_mult,2),round(px+atr*self.sl_atr_mult,2),f'DEX sell-side imbalance {imbalance:.2f}')]
        return []

    def _atr(self, df: pd.DataFrame) -> pd.Series:
        tr=pd.concat([(df['high']-df['low']),(df['high']-df['close'].shift()).abs(),(df['low']-df['close'].shift()).abs()],axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def _mock_pool_imbalance(self, symbol:str)->float:
        np.random.seed((abs(hash(symbol))+31)%10000)
        return float(np.random.uniform(0.6,1.8))

if __name__=='__main__':
    np.random.seed(3); n=240; rets=np.random.normal(0.0001,0.018,n); px=52000*np.exp(np.cumsum(rets))
    df=pd.DataFrame({'open':px,'high':px*1.01,'low':px*0.99,'close':px,'volume':np.random.uniform(120,1300,n)})
    print(DexLiquidityImbalanceStrategy().generate_signals(df))
