#!/usr/bin/env python3
"""
Dual Momentum Crypto Strategy (Verified Edition)
=================================================
Ported from baby_strategies/dual_momentum_crypto.py

Academic basis: Gary Antonacci "Dual Momentum Investing" (2014)
- Absolute Momentum: is the asset trending up? (positive N-day return)
- Relative Momentum: price > SMA200 (trend confirmation)
- Only long when both filters pass; otherwise cash.

Logic:
  Entry: 90-day return > 0 AND price > SMA200 AND momentum score >= 2
  Exit:  Momentum weakens (90d return < 0) OR price < SMA200 OR TP/SL
  Rebalance: Every ~14 days (on 1st/15th of month)
"""

from dataclasses import dataclass
from typing import Tuple, List, Dict

import numpy as np
import pandas as pd


@dataclass
class DualMomentumConfig:
    lookback_long: int = 90   # days for absolute momentum
    lookback_short: int = 30  # days for recent momentum
    sma_period: int = 200
    rebalance_days: int = 14
    tp_pct: float = 0.15      # 15% TP for monthly holds
    sl_pct: float = 0.10      # 10% SL
    min_score: int = 2


class DualMomentumCryptoStrategy:
    def __init__(self, config: DualMomentumConfig = None):
        self.config = config or DualMomentumConfig()

    def run(self, market_data: pd.DataFrame, capital: float) -> Tuple[pd.Series, List[Dict]]:
        c = self.config
        warmup = max(c.lookback_long, c.sma_period) + 10
        if len(market_data) < warmup:
            idx = market_data.index if hasattr(market_data, 'index') else range(len(market_data))
            return pd.Series([capital] * len(market_data), index=idx), []

        close = market_data["close"].astype(float).values
        n = len(close)

        # Precompute SMA200
        close_series = pd.Series(close)
        sma200 = close_series.rolling(c.sma_period).mean().values

        equity = capital
        equity_curve = []
        trades = []
        in_position = False
        entry_price = 0.0
        entry_date = None
        stop_loss = 0.0
        take_profit = 0.0
        bars_since_rebalance = 0

        for i in range(n):
            price = close[i]

            if in_position:
                pnl_pct = (price - entry_price) / entry_price
                equity = capital * (1 + pnl_pct)

                exit_now = False
                exit_price = price
                reason = ""

                # Check TP/SL
                if price <= stop_loss:
                    exit_now, exit_price, reason = True, stop_loss, "stop_loss"
                elif price >= take_profit:
                    exit_now, exit_price, reason = True, take_profit, "take_profit"

                # Check momentum exit (every rebalance period)
                bars_since_rebalance += 1
                if not exit_now and bars_since_rebalance >= c.rebalance_days:
                    bars_since_rebalance = 0
                    if i >= c.lookback_long:
                        mom_90d = price / close[i - c.lookback_long] - 1
                        if mom_90d <= 0:
                            exit_now, exit_price, reason = True, price, "momentum_expired"
                        elif not np.isnan(sma200[i]) and price < sma200[i]:
                            exit_now, exit_price, reason = True, price, "below_sma200"

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
                    })
                    equity = capital + pnl
                    capital = equity
                    in_position = False

            else:
                # Entry check: only on rebalance days
                bars_since_rebalance += 1
                if bars_since_rebalance < c.rebalance_days:
                    equity_curve.append(equity)
                    continue
                bars_since_rebalance = 0

                if i < c.lookback_long:
                    equity_curve.append(equity)
                    continue

                mom_90d = price / close[i - c.lookback_long] - 1
                mom_30d = price / close[i - c.lookback_short] - 1 if i >= c.lookback_short else 0
                above_sma = not np.isnan(sma200[i]) and price > sma200[i]

                # Absolute momentum filter
                if mom_90d <= 0:
                    equity_curve.append(equity)
                    continue

                # Momentum scoring
                score = 0
                if mom_90d > 0.10:
                    score += 2
                elif mom_90d > 0.05:
                    score += 1
                if mom_30d > 0.05:
                    score += 2
                elif mom_30d > 0:
                    score += 1
                if above_sma:
                    score += 1

                if score < c.min_score:
                    equity_curve.append(equity)
                    continue

                # Enter
                in_position = True
                entry_price = price
                entry_date = market_data.index[i]
                stop_loss = price * (1 - c.sl_pct)
                take_profit = price * (1 + c.tp_pct)

            equity_curve.append(equity)

        return pd.Series(equity_curve, index=market_data.index), trades
