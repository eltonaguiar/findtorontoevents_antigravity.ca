"""
Session London Open Momentum Strategy
=====================================

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

class SessionLondonOpenMomentumStrategy:
    def __init__(self, params: Optional[dict] = None):
        p=params or {}
        self.start_hour=p.get('start_hour',7)
        self.end_hour=p.get('end_hour',9)
        self.vol_mult=p.get('vol_mult',1.6)
        self.atr_period=p.get('atr_period',14)
        self.tp_atr_mult=p.get('tp_atr_mult',2.0)
        self.sl_atr_mult=p.get('sl_atr_mult',1.4)

    def generate_signals(self, data: pd.DataFrame, symbol: str='BTCUSDT') -> List[Signal]:
        if len(data)<40: return []
        df=data.copy()
        if 'date' in df.columns: hours=pd.to_datetime(df['date']).dt.hour
        elif isinstance(df.index,pd.DatetimeIndex): hours=df.index.hour
        else: return []
        h=int(hours.iloc[-1])
        if not (self.start_hour <= h <= self.end_hour): return []
        vol_avg=df['volume'].rolling(20).mean().iloc[-1]
        if df['volume'].iloc[-1] <= vol_avg*self.vol_mult: return []
        atr=self._atr(df).iloc[-1]; px=df['close'].iloc[-1]
        if pd.isna(atr) or atr<=0: return []
        up = df['close'].iloc[-1] > df['close'].iloc[-5]
        if up:
            return [Signal(symbol,'BUY',0.7,round(px,2),round(px+atr*self.tp_atr_mult,2),round(px-atr*self.sl_atr_mult,2),f'London open impulse hour={h}')]
        return [Signal(symbol,'SELL',0.7,round(px,2),round(px-atr*self.tp_atr_mult,2),round(px+atr*self.sl_atr_mult,2),f'London open downside impulse hour={h}')]

    def _atr(self, df: pd.DataFrame) -> pd.Series:
        tr=pd.concat([(df['high']-df['low']), (df['high']-df['close'].shift()).abs(), (df['low']-df['close'].shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

if __name__=='__main__':
    np.random.seed(2); n=300; rets=np.random.normal(0.0001,0.02,n); px=50000*np.exp(np.cumsum(rets))
    dts=pd.date_range('2026-01-01', periods=n, freq='5min')
    df=pd.DataFrame({'date':dts,'open':px,'high':px*1.01,'low':px*0.99,'close':px,'volume':np.random.uniform(100,1200,n)})
    print(SessionLondonOpenMomentumStrategy().generate_signals(df))
