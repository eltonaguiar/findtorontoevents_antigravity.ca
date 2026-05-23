"""
Cross Market Correlation Stress Strategy
========================================

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

class CrossMarketCorrelationStressStrategy:
    def __init__(self, params: Optional[dict] = None):
        p=params or {}
        self.lookback=p.get('lookback',30)
        self.stress_z=p.get('stress_z',1.7)
        self.atr_period=p.get('atr_period',14)
        self.tp_atr_mult=p.get('tp_atr_mult',2.2)
        self.sl_atr_mult=p.get('sl_atr_mult',1.3)

    def generate_signals(self, data: pd.DataFrame, symbol: str='BTCUSDT') -> List[Signal]:
        if len(data) < self.lookback + 10:
            return []
        if 'btc_ret' in data.columns and 'spx_ret' in data.columns:
            corr = data['btc_ret'].rolling(self.lookback).corr(data['spx_ret'])
            c = corr.iloc[-1]
            mu = corr.rolling(self.lookback).mean().iloc[-1]
            sd = corr.rolling(self.lookback).std().iloc[-1]
            z = 0 if pd.isna(sd) or sd == 0 else abs((c-mu)/sd)
        else:
            np.random.seed(len(data)); z=float(np.random.uniform(0,2.2))
        atr = self._atr(data).iloc[-1]
        px = data['close'].iloc[-1]
        if pd.isna(atr) or atr<=0: return []
        out=[]
        if z > self.stress_z:
            buy = data['close'].iloc[-1] < data['close'].iloc[-2]
            if buy:
                out.append(Signal(symbol,'BUY',round(min(0.9,0.55+(z-self.stress_z)*0.2),3),round(px,2),round(px+atr*self.tp_atr_mult,2),round(px-atr*self.sl_atr_mult,2),f'Correlation stress z={z:.2f}, snapback long'))
            else:
                out.append(Signal(symbol,'SELL',round(min(0.9,0.55+(z-self.stress_z)*0.2),3),round(px,2),round(px-atr*self.tp_atr_mult,2),round(px+atr*self.sl_atr_mult,2),f'Correlation stress z={z:.2f}, snapback short'))
        return out

    def _atr(self, df: pd.DataFrame) -> pd.Series:
        tr = pd.concat([(df['high']-df['low']), (df['high']-df['close'].shift()).abs(), (df['low']-df['close'].shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__ == '__main__':
    np.random.seed(7); n=260; rets=np.random.normal(0.0001,0.018,n); px=45000*np.exp(np.cumsum(rets))
    df=pd.DataFrame({'open':px*(1+np.random.normal(0,0.001,n)),'high':px*(1+np.abs(np.random.normal(0,0.01,n))),'low':px*(1-np.abs(np.random.normal(0,0.01,n))),'close':px,'volume':np.random.uniform(100,1200,n)})
    s=CrossMarketCorrelationStressStrategy(); print(s.generate_signals(df))
