#!/usr/bin/env python3
"""
VWAP Mean Reversion Strategy (Verified Edition)
================================================
Ported from baby_strategies/corr_vwap_reversion.py

Academic basis: VWAP is the institutional fair-value benchmark (+0.913 correlation
with close price). Deviations from VWAP tend to revert due to institutional
rebalancing.

Logic:
  Entry BUY:  Price < VWAP - N std devs (undervalued vs fair value)
  Entry SELL: Price > VWAP + N std devs (overvalued vs fair value)
  Exit: Price reverts to VWAP or TP/SL hit.
  Direction: Both LONG and SHORT.
"""

from dataclasses import dataclass
from typing import Tuple, List, Dict

import numpy as np
import pandas as pd


@dataclass
class VWAPReversionConfig:
    vwap_period: int = 50
    band_mult: float = 1.0
    tp_pct: float = 0.05
    sl_pct: float = 0.03
    max_hold: int = 20


class VWAPReversionStrategy:
    def __init__(self, config: VWAPReversionConfig = None):
        self.config = config or VWAPReversionConfig()

    def run(self, market_data: pd.DataFrame, capital: float) -> Tuple[pd.Series, List[Dict]]:
        c = self.config
        if len(market_data) < c.vwap_period + 10:
            idx = market_data.index if hasattr(market_data, 'index') else range(len(market_data))
            return pd.Series([capital] * len(market_data), index=idx), []

        close = market_data["close"].astype(float)
        high = market_data["high"].astype(float)
        low = market_data["low"].astype(float)
        volume = market_data["volume"].astype(float)

        # Rolling VWAP and std dev
        typical_price = (high + low + close) / 3
        tp_vol = typical_price * volume
        vwap = tp_vol.rolling(c.vwap_period).sum() / volume.rolling(c.vwap_period).sum()
        deviation = (typical_price - vwap).rolling(c.vwap_period).std()

        equity = capital
        equity_curve = []
        trades = []
        in_position = False
        entry_price = 0.0
        entry_date = None
        direction = ""
        stop_loss = 0.0
        take_profit = 0.0
        vwap_target = 0.0
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
                    elif price >= vwap_target:
                        exit_now, exit_price, reason = True, price, "vwap_target"
                else:
                    if price >= stop_loss:
                        exit_now, exit_price, reason = True, stop_loss, "stop_loss"
                    elif price <= take_profit:
                        exit_now, exit_price, reason = True, take_profit, "take_profit"
                    elif price <= vwap_target:
                        exit_now, exit_price, reason = True, price, "vwap_target"

                if bars_held >= c.max_hold:
                    exit_now, exit_price, reason = True, price, "max_hold"

                if exit_now:
                    if direction == "LONG":
                        pnl = (exit_price - entry_price) / entry_price * capital
                        pnl_pct_real = (exit_price - entry_price) / entry_price
                    else:
                        pnl = (entry_price - exit_price) / entry_price * capital
                        pnl_pct_real = (entry_price - exit_price) / entry_price

                    trades.append({
                        "entry_date": str(entry_date),
                        "exit_date": str(market_data.index[i]),
                        "entry_price": round(entry_price, 8),
                        "exit_price": round(exit_price, 8),
                        "pnl": round(pnl, 2),
                        "pnl_pct": round(pnl_pct_real, 6),
                        "direction": direction,
                        "reason": reason,
                        "bars_held": bars_held,
                    })
                    equity = capital + pnl
                    capital = equity
                    in_position = False

            else:
                # Entry check
                if (i >= 1
                        and not np.isnan(vwap.iloc[i])
                        and not np.isnan(deviation.iloc[i])):

                    vw = float(vwap.iloc[i])
                    std = float(deviation.iloc[i])

                    if std > 0:
                        lower_band = vw - c.band_mult * std
                        upper_band = vw + c.band_mult * std

                        # BUY: price below lower band
                        if price < lower_band:
                            in_position = True
                            entry_price = price
                            entry_date = market_data.index[i]
                            direction = "LONG"
                            stop_loss = price * (1 - c.sl_pct)
                            take_profit = price * (1 + c.tp_pct)
                            vwap_target = vw
                            bars_held = 0

                        # SELL: price above upper band
                        elif price > upper_band:
                            in_position = True
                            entry_price = price
                            entry_date = market_data.index[i]
                            direction = "SHORT"
                            stop_loss = price * (1 + c.sl_pct)
                            take_profit = price * (1 - c.tp_pct)
                            vwap_target = vw
                            bars_held = 0

            equity_curve.append(equity)

        return pd.Series(equity_curve, index=market_data.index), trades
