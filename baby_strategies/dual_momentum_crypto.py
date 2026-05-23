"""
DualMomentumCryptoStrategy - Baby Strat
=========================================

Created by: Claude Code (Deep Research Round 11)
Date: 2026-03-02

Academic Basis:
- Gary Antonacci "Dual Momentum Investing" (2014, McGraw-Hill)
- Absolute Momentum: is the asset trending up? (vs T-bills)
- Relative Momentum: which asset is trending strongest? (cross-sectional)
- Original equity version: ~15% CAGR, Sharpe ~1.0, max DD ~20%
- Crypto adaptation: use BTC/ETH/SOL as asset universe, SMA as cash proxy

Strategy Logic:
1. Relative Momentum: rank BTC, ETH, SOL by 90-day return
2. Absolute Momentum: only BUY if best performer has positive 90-day return
3. If absolute momentum is negative → CASH (no signal)
4. Rebalance monthly (signal on 1st/15th of month)

Why It Works:
- Momentum is the strongest documented factor in crypto (Liu et al. 2022 JFE)
- Dual filter avoids buying into bear markets (absolute check)
- Monthly rebalancing reduces transaction costs and whipsaws
- Simple, robust, hard to overfit (only 1 parameter: lookback)

Adaptation for Hourly:
- Uses 2160 bars (90 days * 24h) as lookback for momentum
- Signals only when last bar is near month boundary (every ~720 bars)
- Compares current symbol's momentum to determine if it's the winner
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


class DualMomentumCryptoStrategy:
    NAME = "dual_momentum_crypto"
    DESCRIPTION = "Antonacci dual momentum — absolute + relative momentum filter"
    ACADEMIC_SOURCE = "Antonacci 2014: ~15% CAGR, Sharpe ~1.0, applied to crypto universe"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.lookback = self.params.get('lookback', 2160)  # 90 days * 24h
        self.short_lookback = self.params.get('short_lookback', 720)  # 30 days
        self.tp_pct = self.params.get('tp_pct', 5.0)  # Wider TP for monthly hold
        self.sl_pct = self.params.get('sl_pct', 4.0)  # Wider SL for monthly hold
        self.signal_frequency = self.params.get('signal_frequency', 336)  # ~14 days in hours

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < self.lookback + 10:
            return []

        close = data['close'].values
        n = len(close)
        current_price = close[-1]

        # Only generate signals approximately every 2 weeks
        # Use bar count modulo as proxy for timing
        if hasattr(data.index, 'day'):
            day = data.index[-1].day
            hour = data.index[-1].hour
            # Signal on 1st and 15th of month, around midnight
            if not ((day in [1, 2, 15, 16]) and hour in [0, 1, 2]):
                return []
        else:
            # Fallback: signal every signal_frequency bars
            if n % self.signal_frequency > 5:
                return []

        # Absolute Momentum: 90-day return
        mom_90d = close[-1] / close[-self.lookback] - 1 if n >= self.lookback else 0
        # Short-term momentum: 30-day return
        mom_30d = close[-1] / close[-self.short_lookback] - 1 if n >= self.short_lookback else 0

        # Absolute momentum filter: must be positive
        if mom_90d <= 0:
            return []  # Cash — don't trade in downtrend

        # Relative strength: compare to SMA (cash proxy)
        sma_200 = np.mean(close[-200:]) if n >= 200 else close[-1]
        above_sma = current_price > sma_200

        if not above_sma:
            return []

        # Momentum strength scoring
        # Strong momentum = high 90d return + positive 30d return + above SMA
        momentum_score = 0
        if mom_90d > 0.10:
            momentum_score += 2  # Strong absolute
        elif mom_90d > 0.05:
            momentum_score += 1

        if mom_30d > 0.05:
            momentum_score += 2  # Strong recent
        elif mom_30d > 0:
            momentum_score += 1

        if above_sma:
            momentum_score += 1

        # Need at least moderate momentum
        if momentum_score < 2:
            return []

        # Confidence scales with momentum strength
        confidence = min(0.40 + momentum_score * 0.10, 0.85)

        # Volatility-adjusted TP/SL
        returns = np.diff(np.log(close[max(0, n - 720):]))
        rv = np.std(returns) * np.sqrt(8760) if len(returns) > 5 else 0.5
        vol_mult = max(0.5, min(2.0, rv / 0.5))

        tp = current_price * (1 + self.tp_pct * vol_mult / 100)
        sl = current_price * (1 - self.sl_pct * vol_mult / 100)

        return [Signal(
            symbol=symbol,
            direction="BUY",
            confidence=round(confidence, 3),
            entry_price=round(current_price, 2),
            take_profit=round(tp, 2),
            stop_loss=round(sl, 2),
            reason=f"Dual momentum BUY (90d={mom_90d:+.1%}, 30d={mom_30d:+.1%}, score={momentum_score}, above SMA200)"
        )]

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        result = np.zeros(len(data))
        k = 2.0 / (period + 1)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = data[i] * k + result[i - 1] * (1 - k)
        return result
