#!/usr/bin/env python3
"""
Bollinger Band Squeeze Breakout Strategy (Verified Edition)
============================================================
Ported from baby_strategies/bb_squeeze_breakout.py

Logic:
  Detects periods of low volatility (BB squeeze) followed by breakouts.
  Entry: Price breaks out of BB after squeeze, confirmed by volume spike.
  Exit: ATR-based TP/SL or re-entry into bands.
  Direction: Both LONG and SHORT.
"""

from dataclasses import dataclass
from typing import Tuple, List, Dict

import numpy as np
import pandas as pd


@dataclass
class BBSqueezeConfig:
    bb_period: int = 20
    bb_std: float = 2.0
    squeeze_threshold: float = 0.8
    volume_period: int = 20
    volume_mult: float = 1.5
    atr_period: int = 14
    tp_atr_mult: float = 3.0
    sl_atr_mult: float = 1.5
    max_hold: int = 30


class BBSqueezeBreakoutStrategy:
    def __init__(self, config: BBSqueezeConfig = None):
        self.config = config or BBSqueezeConfig()

    def run(self, market_data: pd.DataFrame, capital: float) -> Tuple[pd.Series, List[Dict]]:
        c = self.config
        warmup = max(c.bb_period, c.volume_period, c.atr_period) + 10
        if len(market_data) < warmup:
            idx = market_data.index if hasattr(market_data, 'index') else range(len(market_data))
            return pd.Series([capital] * len(market_data), index=idx), []

        close = market_data["close"].astype(float)
        high = market_data["high"].astype(float)
        low = market_data["low"].astype(float)
        volume = market_data["volume"].astype(float)

        # Indicators
        sma = close.rolling(c.bb_period).mean()
        std = close.rolling(c.bb_period).std()
        bb_upper = sma + c.bb_std * std
        bb_lower = sma - c.bb_std * std
        bb_width = (bb_upper - bb_lower) / sma
        bb_width_ma = bb_width.rolling(c.bb_period).mean()
        vol_ma = volume.rolling(c.volume_period).mean()

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
        direction = ""
        stop_loss = 0.0
        take_profit = 0.0
        bars_held = 0
        band_ref = 0.0  # for re-entry exit

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
                    elif price < band_ref and bars_held > 3:
                        exit_now, exit_price, reason = True, price, "re_enter_bands"
                else:
                    if price >= stop_loss:
                        exit_now, exit_price, reason = True, stop_loss, "stop_loss"
                    elif price <= take_profit:
                        exit_now, exit_price, reason = True, take_profit, "take_profit"
                    elif price > band_ref and bars_held > 3:
                        exit_now, exit_price, reason = True, price, "re_enter_bands"

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
                # Entry check: squeeze + volume spike + breakout
                if (i >= 1
                        and not np.isnan(bb_width.iloc[i])
                        and not np.isnan(bb_width_ma.iloc[i])
                        and not np.isnan(vol_ma.iloc[i])
                        and not np.isnan(atr.iloc[i])):

                    is_squeeze = float(bb_width.iloc[i]) < float(bb_width_ma.iloc[i]) * c.squeeze_threshold
                    vol_spike = float(volume.iloc[i]) > float(vol_ma.iloc[i]) * c.volume_mult
                    atr_val = float(atr.iloc[i])

                    if is_squeeze and vol_spike and atr_val > 0:
                        prev_price = float(close.iloc[i - 1])
                        ub = float(bb_upper.iloc[i])
                        lb = float(bb_lower.iloc[i])

                        # Bullish breakout
                        if prev_price <= ub and price > ub:
                            in_position = True
                            entry_price = price
                            entry_date = market_data.index[i]
                            direction = "LONG"
                            stop_loss = ub - atr_val * c.sl_atr_mult
                            take_profit = price + atr_val * c.tp_atr_mult
                            band_ref = ub
                            bars_held = 0

                        # Bearish breakout
                        elif prev_price >= lb and price < lb:
                            in_position = True
                            entry_price = price
                            entry_date = market_data.index[i]
                            direction = "SHORT"
                            stop_loss = lb + atr_val * c.sl_atr_mult
                            take_profit = price - atr_val * c.tp_atr_mult
                            band_ref = lb
                            bars_held = 0

            equity_curve.append(equity)

        return pd.Series(equity_curve, index=market_data.index), trades
