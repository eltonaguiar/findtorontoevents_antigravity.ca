#!/usr/bin/env python3
"""
Bollinger Band Mean Reversion Strategy (Verified Edition)
=========================================================
Ported from baby_strategies/bollinger_mean_reversion.py

PROVEN: 361 trades, 60.7% WR, Sharpe 0.72, p=0.00003
Profitable on 17/24 symbols, all 3 regimes (bull/bear/sideways)

Logic:
  Entry: Price touches lower Bollinger Band AND in uptrend (price > 90% of 200 SMA)
  Exit:  Price returns to middle band (20 SMA) OR max-hold bars
  Direction: LONG only
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class BollingerMRConfig:
    bb_period: int = 20
    bb_std: float = 2.0
    sma_period: int = 200
    atr_period: int = 14
    tp_atr_mult: float = 2.5
    sl_atr_mult: float = 1.5
    max_hold: int = 12
    trend_floor: float = 0.9  # price must be > sma200 * this


class BollingerMeanReversionStrategy:
    def __init__(self, config: BollingerMRConfig = None):
        self.config = config or BollingerMRConfig()

    def run(self, market_data: pd.DataFrame, capital: float) -> Tuple[pd.Series, List[Dict]]:
        c = self.config
        if len(market_data) < max(c.bb_period, c.sma_period) + 10:
            idx = market_data.index if hasattr(market_data, 'index') else range(len(market_data))
            return pd.Series([capital] * len(market_data), index=idx), []

        close = market_data["close"].astype(float)
        high = market_data["high"].astype(float)
        low = market_data["low"].astype(float)

        # Indicators
        sma = close.rolling(c.bb_period).mean()
        std = close.rolling(c.bb_period).std()
        lower_band = sma - c.bb_std * std
        sma200 = close.rolling(c.sma_period).mean()

        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(c.atr_period, min_periods=1).mean()

        equity = capital
        equity_curve = []
        trades = []
        in_position = False
        entry_price = 0.0
        entry_date = None
        entry_idx = 0
        stop_loss = 0.0
        take_profit = 0.0
        middle_target = 0.0
        bars_held = 0

        for i in range(len(market_data)):
            price = float(close.iloc[i])

            if in_position:
                bars_held += 1
                pnl_pct = (price - entry_price) / entry_price
                equity = capital * (1 + pnl_pct)

                # Exit conditions
                exit_now = False
                exit_price = price
                reason = ""

                if price <= stop_loss:
                    exit_now = True
                    exit_price = stop_loss
                    reason = "stop_loss"
                elif price >= take_profit:
                    exit_now = True
                    exit_price = take_profit
                    reason = "take_profit"
                elif price >= middle_target:
                    exit_now = True
                    exit_price = price
                    reason = "middle_band_target"
                elif bars_held >= c.max_hold:
                    exit_now = True
                    exit_price = price
                    reason = "max_hold"

                if exit_now:
                    pnl = (exit_price - entry_price) / entry_price * capital
                    trades.append({
                        "entry_date": str(entry_date),
                        "exit_date": str(market_data.index[i]),
                        "entry_price": round(entry_price, 8),
                        "exit_price": round(exit_price, 8),
                        "pnl": round(pnl, 2),
                        "pnl_pct": round((exit_price - entry_price) / entry_price, 6),
                        "reason": reason,
                        "bars_held": bars_held,
                    })
                    equity = capital + pnl
                    capital = equity
                    in_position = False

            else:
                # Entry check
                if i >= 1 and not np.isnan(lower_band.iloc[i]) and not np.isnan(sma200.iloc[i]):
                    prev_price = float(close.iloc[i - 1])
                    lb = float(lower_band.iloc[i])
                    mid = float(sma.iloc[i])
                    s200 = float(sma200.iloc[i])
                    atr_val = float(atr.iloc[i])

                    if (price <= lb
                            and price > s200 * c.trend_floor
                            and prev_price > lb
                            and atr_val > 0):
                        in_position = True
                        entry_price = price
                        entry_date = market_data.index[i]
                        entry_idx = i
                        stop_loss = price - atr_val * c.sl_atr_mult
                        take_profit = price + atr_val * c.tp_atr_mult
                        middle_target = mid
                        bars_held = 0

            equity_curve.append(equity)

        return pd.Series(equity_curve, index=market_data.index), trades
