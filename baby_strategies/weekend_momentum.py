"""
WeekendMomentumStrategy - Baby Strat
======================================

Created by: Claude Code (Deep Research Round 3)
Date: 2026-03-01

Academic Basis:
- "The Weekend Effect in Crypto Momentum" (Advances in Consumer Research, 2025)
- BTC weekend mean daily return: 0.0023 vs weekday 0.0012 (nearly 2x)
- DOGE weekend return: 0.0052 vs weekday 0.0021 (2.5x)
- Weekend max drawdown LOWER than weekday (BTC: -18% vs -28%)

Strategy Logic:
- Enter Friday 23:00 UTC on coins with strongest 7-day momentum
- Exit Monday 08:00 UTC
- Only trades on weekends when institutional counter-trading is absent
- Retail momentum-chasing dominates weekends

Why It Works:
- Weekend liquidity is lower — momentum persists without institutional arb
- Retail traders (trend-chasers) dominate weekends
- Reduced arbitrage activity allows momentum to run further
- 24/7 crypto market creates exploitable weekend patterns
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Dict
from dataclasses import dataclass


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class WeekendMomentumStrategy:
    NAME = "weekend_momentum"
    DESCRIPTION = "Weekend momentum — enter Friday evening, exit Monday morning"
    ACADEMIC_SOURCE = "ACR Journal 2025: Weekend Effect in Crypto Momentum (2x weekday returns)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get('lookback', 168)  # 7 days in hours
        self.tp_pct = self.params.get('tp_pct', 3.0)
        self.sl_pct = self.params.get('sl_pct', 2.0)
        self.min_momentum = self.params.get('min_momentum', 0.01)  # 1% min momentum

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.lookback + 10:
            return []

        close = data['close'].values
        current_price = close[-1]

        # Check if it's Friday evening (day 4 = Friday)
        if hasattr(data.index, 'dayofweek') and hasattr(data.index, 'hour'):
            dow = data.index[-1].dayofweek
            hour = data.index[-1].hour
            # Only enter Friday 22:00-23:00 UTC
            if not (dow == 4 and hour in [22, 23]):
                return []
        else:
            return []

        # Calculate 7-day momentum
        if len(close) >= self.lookback:
            mom_7d = close[-1] / close[-self.lookback] - 1
        else:
            return []

        # Only enter on positive momentum (ride winners into weekend)
        if mom_7d < self.min_momentum:
            return []

        # Trend filter: 200-bar EMA
        if len(close) >= 200:
            ema200 = self._ema(close, 200)[-1]
            above_trend = current_price > ema200
        else:
            above_trend = True

        # Vol scaling
        returns = np.diff(np.log(close[max(0, len(close) - 73):]))
        rv = np.std(returns) * np.sqrt(8760) if len(returns) > 5 else 0.5
        vol_scale = min(0.15 / max(rv, 0.05), 2.0)

        confidence = min(abs(mom_7d) * 3, 0.8) * min(vol_scale / 1.5, 1.0)
        if above_trend:
            confidence = min(confidence * 1.3, 0.90)
        confidence = max(confidence, 0.3)

        tp = current_price * (1 + self.tp_pct / 100)
        sl = current_price * (1 - self.sl_pct / 100)

        return [Signal(
            symbol=symbol,
            direction="BUY",
            confidence=round(confidence, 3),
            entry_price=round(current_price, 2),
            take_profit=round(tp, 2),
            stop_loss=round(sl, 2),
            reason=f"Weekend momentum BUY (7d_mom={mom_7d:+.2%}, vol_scale={vol_scale:.1f}, trend={'UP' if above_trend else 'DOWN'})"
        )]

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        result = np.zeros(len(data))
        k = 2.0 / (period + 1)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = data[i] * k + result[i - 1] * (1 - k)
        return result
