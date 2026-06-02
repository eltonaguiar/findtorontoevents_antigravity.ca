#!/usr/bin/env python3
"""Crypto Donchian breakout (20/10) for walk-forward verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class CryptoDonchianConfig:
    entry_period: int = 20
    exit_period: int = 10
    atr_period: int = 14
    atr_sl_mult: float = 2.0
    tp_pct: float = 0.12
    max_hold: int = 40


class CryptoDonchianBreakout:
    def __init__(self, config: CryptoDonchianConfig | None = None):
        self.config = config or CryptoDonchianConfig()

    def run(self, market_data: pd.DataFrame, capital: float) -> Tuple[pd.Series, List[Dict]]:
        c = self.config
        warmup = c.entry_period + c.atr_period + 5
        if len(market_data) < warmup:
            idx = market_data.index if hasattr(market_data, "index") else range(len(market_data))
            return pd.Series([capital] * len(market_data), index=idx), []

        close = market_data["close"].astype(float)
        high = market_data["high"].astype(float)
        low = market_data["low"].astype(float)

        upper = high.shift(1).rolling(c.entry_period).max()
        lower = low.shift(1).rolling(c.entry_period).min()
        exit_low = low.shift(1).rolling(c.exit_period).min()
        exit_high = high.shift(1).rolling(c.exit_period).max()
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(c.atr_period, min_periods=1).mean()

        equity = capital
        equity_curve: List[float] = []
        trades: List[Dict] = []
        in_position = False
        entry_price = 0.0
        entry_date = None
        direction = ""
        stop_loss = 0.0
        take_profit = 0.0
        bars_held = 0

        for i in range(len(market_data)):
            price = float(close.iloc[i])
            if in_position:
                bars_held += 1
                if direction == "LONG":
                    pnl_pct = (price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - price) / entry_price
                equity = capital * (1 + pnl_pct)
                exit_now = False
                exit_price = price
                reason = ""
                if direction == "LONG":
                    if price <= stop_loss:
                        exit_now, exit_price, reason = True, stop_loss, "stop_loss"
                    elif price >= take_profit:
                        exit_now, exit_price, reason = True, take_profit, "take_profit"
                    elif price < float(exit_low.iloc[i]):
                        exit_now, exit_price, reason = True, price, "donchian_exit"
                else:
                    if price >= stop_loss:
                        exit_now, exit_price, reason = True, stop_loss, "stop_loss"
                    elif price <= take_profit:
                        exit_now, exit_price, reason = True, take_profit, "take_profit"
                    elif price > float(exit_high.iloc[i]):
                        exit_now, exit_price, reason = True, price, "donchian_exit"
                if bars_held >= c.max_hold:
                    exit_now, exit_price, reason = True, price, "time_exit"
                if exit_now:
                    trades.append(
                        {
                            "entry_date": str(entry_date),
                            "exit_date": str(market_data.index[i]),
                            "entry_price": round(entry_price, 8),
                            "exit_price": round(exit_price, 8),
                            "pnl_pct": round(
                                (exit_price - entry_price) / entry_price
                                if direction == "LONG"
                                else (entry_price - exit_price) / entry_price,
                                6,
                            ),
                            "reason": reason,
                        }
                    )
                    capital = equity
                    in_position = False
            else:
                u = float(upper.iloc[i])
                l = float(lower.iloc[i])
                a = float(atr.iloc[i])
                if np.isnan(u) or np.isnan(l) or np.isnan(a):
                    equity_curve.append(equity)
                    continue
                prev = float(close.iloc[i - 1])
                if price > u and prev <= float(upper.iloc[i - 1]):
                    in_position = True
                    direction = "LONG"
                    entry_price = price
                    entry_date = market_data.index[i]
                    stop_loss = price - c.atr_sl_mult * a
                    take_profit = price * (1 + c.tp_pct)
                    bars_held = 0
                elif price < l and prev >= float(lower.iloc[i - 1]):
                    in_position = True
                    direction = "SHORT"
                    entry_price = price
                    entry_date = market_data.index[i]
                    stop_loss = price + c.atr_sl_mult * a
                    take_profit = price * (1 - c.tp_pct)
                    bars_held = 0
            equity_curve.append(equity)

        return pd.Series(equity_curve, index=market_data.index), trades