"""
OvernightSeasonalityBTCStrategy - Baby Strat
=============================================

Created by: Claude Code (Deep Research Round 3)
Date: 2026-03-01

Academic Basis:
- QuantPedia "Overnight Seasonality in Bitcoin" — Gemini exchange validation
- "Are There Seasonal Intraday or Overnight Anomalies in Bitcoin?" — peer-reviewed
- Sharpe 1.58, 33% annualized, 2-hour holding period

Strategy Logic:
- BUY BTC at 22:00 UTC, SELL at 00:00 UTC
- Exploits systematic positive drift during the 22:00-00:00 window
- When all traditional markets are closed, crypto-native participants dominate
- Low-liquidity environment creates directional drift
- Optional: only trade Thu-Fri-Sat for higher Sharpe

Why It Works:
- Market microstructure effect from trading session overlaps
- Daily candle close mechanics on UTC-based exchanges create buying pressure
- Regime-independent — driven by execution mechanics, not directional bias
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


class OvernightSeasonalityBTCStrategy:
    NAME = "overnight_seasonality_btc"
    DESCRIPTION = "Buy BTC at 22:00 UTC, sell at 00:00 UTC — overnight drift anomaly"
    ACADEMIC_SOURCE = "QuantPedia: Overnight Seasonality in Bitcoin (Sharpe 1.58)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.tp_pct = self.params.get('tp_pct', 1.0)
        self.sl_pct = self.params.get('sl_pct', 0.5)
        self.best_days = self.params.get('best_days', [3, 4, 5])  # Thu=3, Fri=4, Sat=5

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < 50:
            return []

        close = data['close'].values
        current_price = close[-1]

        # Check if we have datetime index
        if hasattr(data.index, 'hour'):
            current_hour = data.index[-1].hour
            current_dow = data.index[-1].dayofweek
        else:
            # If no datetime index, use bar position as proxy
            # Can't determine time-of-day without timestamps
            return []

        # Only signal at 22:00 UTC
        if current_hour != 22:
            return []

        # Optional: filter to best days (Thu, Fri, Sat)
        if self.best_days and current_dow not in self.best_days:
            return []

        # Simple trend filter: price above 200-bar EMA
        if len(close) >= 200:
            ema200 = self._ema(close, 200)[-1]
            trend_up = current_price > ema200
        else:
            trend_up = True

        # Vol scaling
        if len(close) > 72:
            returns = np.diff(np.log(close[-73:]))
            rv = np.std(returns) * np.sqrt(8760)
            vol_scale = min(0.15 / max(rv, 0.05), 2.0)
        else:
            vol_scale = 1.0

        confidence = 0.65 * min(vol_scale / 1.5, 1.0)
        if trend_up:
            confidence = min(confidence * 1.2, 0.90)

        tp = current_price * (1 + self.tp_pct / 100)
        sl = current_price * (1 - self.sl_pct / 100)

        day_names = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}

        return [Signal(
            symbol=symbol,
            direction="BUY",
            confidence=round(confidence, 3),
            entry_price=round(current_price, 2),
            take_profit=round(tp, 2),
            stop_loss=round(sl, 2),
            reason=f"Overnight seasonality BUY 22:00-00:00 UTC ({day_names.get(current_dow, '?')}, vol_scale={vol_scale:.1f})"
        )]

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        result = np.zeros(len(data))
        k = 2.0 / (period + 1)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = data[i] * k + result[i - 1] * (1 - k)
        return result
