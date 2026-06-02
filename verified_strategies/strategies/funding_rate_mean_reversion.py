#!/usr/bin/env python3
"""
Funding Rate Mean Reversion Strategy (Verified Edition)
========================================================
Ported from baby_strategies/funding_rate_mean_reversion_v1.py

Thesis: Persistently extreme funding rates signal crowded directional bets.
When funding reaches extremes AND price is near local extremes, the crowded
trade unwinds and price reverts.

When funding data is unavailable, falls back to RSI + Bollinger proxy:
  - SELL: RSI(14) >= 72 AND price near 18-bar high
  - BUY:  RSI(14) <= 28 AND price near 18-bar low

Exit: ATR-based TP/SL or max hold bars.
"""

from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional

import numpy as np
import pandas as pd


@dataclass
class FundingRateMRConfig:
    funding_short_threshold: float = 0.0008   # 0.08% per 8h
    funding_long_threshold: float = -0.0006   # -0.06% per 8h
    extension_pct: float = 0.02
    extension_lookback: int = 18
    atr_period: int = 14
    tp_atr_mult: float = 1.5
    sl_atr_mult: float = 1.2
    max_hold: int = 18
    # Proxy fallback (RSI + Bollinger)
    rsi_period: int = 14
    proxy_rsi_overbought: float = 72.0
    proxy_rsi_oversold: float = 28.0


class FundingRateMeanReversionStrategy:
    def __init__(self, config: FundingRateMRConfig = None):
        self.config = config or FundingRateMRConfig()

    @staticmethod
    def _rsi(close: pd.Series, period: int) -> pd.Series:
        delta = close.diff()
        up = delta.clip(lower=0).rolling(period).mean()
        down = (-delta.clip(upper=0)).rolling(period).mean()
        rs = up / down.replace(0, np.nan)
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        prev_close = close.shift(1)
        tr = pd.concat(
            [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period).mean()

    def run(self, market_data: pd.DataFrame, capital: float) -> Tuple[pd.Series, List[Dict]]:
        c = self.config
        warmup = max(c.extension_lookback, c.atr_period, c.rsi_period) + 10
        if len(market_data) < warmup:
            idx = market_data.index if hasattr(market_data, 'index') else range(len(market_data))
            return pd.Series([capital] * len(market_data), index=idx), []

        close = market_data["close"].astype(float)
        high = market_data["high"].astype(float)
        low = market_data["low"].astype(float)

        # Indicators
        atr = self._atr(high, low, close, c.atr_period)
        rsi = self._rsi(close, c.rsi_period)
        has_funding = "funding_rate" in market_data.columns

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
                else:
                    if price >= stop_loss:
                        exit_now, exit_price, reason = True, stop_loss, "stop_loss"
                    elif price <= take_profit:
                        exit_now, exit_price, reason = True, take_profit, "take_profit"

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
                if i < c.extension_lookback or np.isnan(atr.iloc[i]):
                    equity_curve.append(equity)
                    continue

                atr_val = float(atr.iloc[i])
                if atr_val <= 0:
                    equity_curve.append(equity)
                    continue

                # Price extension
                hi_ext = float(high.iloc[max(0, i - c.extension_lookback):i + 1].max())
                lo_ext = float(low.iloc[max(0, i - c.extension_lookback):i + 1].min())
                near_high = (hi_ext - price) / price <= c.extension_pct if price > 0 else False
                near_low = (price - lo_ext) / price <= c.extension_pct if price > 0 else False

                entry_dir = None

                # Funding mode
                if has_funding:
                    fr = float(market_data["funding_rate"].iloc[i])
                    if fr >= c.funding_short_threshold and near_high:
                        entry_dir = "SHORT"
                    elif fr <= c.funding_long_threshold and near_low:
                        entry_dir = "LONG"
                else:
                    # Proxy mode: RSI
                    rsi_val = float(rsi.iloc[i]) if not np.isnan(rsi.iloc[i]) else 50
                    if rsi_val >= c.proxy_rsi_overbought and near_high:
                        entry_dir = "SHORT"
                    elif rsi_val <= c.proxy_rsi_oversold and near_low:
                        entry_dir = "LONG"

                if entry_dir:
                    in_position = True
                    entry_price = price
                    entry_date = market_data.index[i]
                    direction = entry_dir
                    if entry_dir == "LONG":
                        stop_loss = price - atr_val * c.sl_atr_mult
                        take_profit = price + atr_val * c.tp_atr_mult
                    else:
                        stop_loss = price + atr_val * c.sl_atr_mult
                        take_profit = price - atr_val * c.tp_atr_mult
                    bars_held = 0

            equity_curve.append(equity)

        return pd.Series(equity_curve, index=market_data.index), trades
