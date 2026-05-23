"""
Crypto Kalman Trend Residual Reversion Strategy
================================================

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

class CryptoKalmanTrendResidualReversionStrategy:
    def __init__(self, params: Optional[dict] = None):
        p=params or {}
        self.q=p.get('q',1e-5)
        self.r=p.get('r',0.01)
        self.z_entry=p.get('z_entry',1.7)
        self.atr_period=p.get('atr_period',14)
        self.tp_atr_mult=p.get('tp_atr_mult',1.9)
        self.sl_atr_mult=p.get('sl_atr_mult',1.3)

    def generate_signals(self, data: pd.DataFrame, symbol: str='BTCUSDT') -> List[Signal]:
        if len(data)<40: return []
        trend=self._kalman(data['close'].values)
        resid=(data['close'].values-trend)
        z=(resid[-1]-resid.mean())/(resid.std()+1e-9)
        atr=self._atr(data).iloc[-1]; px=data['close'].iloc[-1]
        if pd.isna(atr) or atr<=0: return []
        if z < -self.z_entry:
            return [Signal(symbol,'BUY',0.72,round(px,2),round(px+atr*self.tp_atr_mult,2),round(px-atr*self.sl_atr_mult,2),f'Kalman residual z={z:.2f} mean-revert long')]
        if z > self.z_entry:
            return [Signal(symbol,'SELL',0.72,round(px,2),round(px-atr*self.tp_atr_mult,2),round(px+atr*self.sl_atr_mult,2),f'Kalman residual z={z:.2f} mean-revert short')]
        return []

    def _kalman(self, y):
        n=len(y); x=np.zeros(n); p=1.0
        x[0]=y[0]
        for t in range(1,n):
            # predict
            x_pred=x[t-1]; p_pred=p+self.q
            # update
            k=p_pred/(p_pred+self.r)
            x[t]=x_pred+k*(y[t]-x_pred)
            p=(1-k)*p_pred
        return x

    def _atr(self, df):
        tr=pd.concat([(df['high']-df['low']),(df['high']-df['close'].shift()).abs(),(df['low']-df['close'].shift()).abs()],axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__=='__main__':
    np.random.seed(4); n=260; rets=np.random.normal(0.0001,0.02,n); px=51000*np.exp(np.cumsum(rets))
    df=pd.DataFrame({'open':px,'high':px*1.01,'low':px*0.99,'close':px,'volume':np.random.uniform(100,1400,n)})
    print(CryptoKalmanTrendResidualReversionStrategy().generate_signals(df))
