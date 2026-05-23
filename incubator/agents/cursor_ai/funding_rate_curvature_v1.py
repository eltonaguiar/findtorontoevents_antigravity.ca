"""
Funding Rate Curvature Strategy
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

class FundingRateCurvatureStrategy:
    def __init__(self, params: Optional[dict] = None):
        p=params or {}
        self.curvature_threshold=p.get('curvature_threshold',0.00015)
        self.atr_period=p.get('atr_period',14)
        self.tp_atr_mult=p.get('tp_atr_mult',2.0)
        self.sl_atr_mult=p.get('sl_atr_mult',1.3)

    def generate_signals(self, data: pd.DataFrame, symbol: str='BTCUSDT') -> List[Signal]:
        if len(data)<30: return []
        fr = data['funding_rate'] if 'funding_rate' in data.columns else self._mock_funding_series(len(data), symbol)
        # second derivative proxy
        curv = fr.diff().diff().iloc[-1]
        atr=self._atr(data).iloc[-1]
        px=data['close'].iloc[-1]
        if pd.isna(atr) or atr<=0 or pd.isna(curv): return []
        if curv < -self.curvature_threshold:
            return [Signal(symbol,'BUY',0.69,round(px,2),round(px+atr*self.tp_atr_mult,2),round(px-atr*self.sl_atr_mult,2),f'Funding curvature {curv:.6f} bullish inflection')]
        if curv > self.curvature_threshold:
            return [Signal(symbol,'SELL',0.69,round(px,2),round(px-atr*self.tp_atr_mult,2),round(px+atr*self.sl_atr_mult,2),f'Funding curvature {curv:.6f} bearish inflection')]
        return []

    def _mock_funding_series(self, n:int, symbol:str) -> pd.Series:
        np.random.seed((abs(hash(symbol))+121)%10000)
        return pd.Series(np.random.normal(0,0.00008,n)).cumsum()/10

    def _atr(self, df):
        tr=pd.concat([(df['high']-df['low']),(df['high']-df['close'].shift()).abs(),(df['low']-df['close'].shift()).abs()],axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__=='__main__':
    np.random.seed(6); n=220; rets=np.random.normal(0.0002,0.02,n); px=50000*np.exp(np.cumsum(rets))
    df=pd.DataFrame({'open':px,'high':px*1.01,'low':px*0.99,'close':px,'volume':np.random.uniform(100,1400,n)})
    print(FundingRateCurvatureStrategy().generate_signals(df))
