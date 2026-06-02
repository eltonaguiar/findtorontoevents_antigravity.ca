#!/usr/bin/env python3
"""ETF sector dual momentum vs SPY (Antonacci-style) for walk-forward verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from verified_strategies.data_fetcher import fetch_ohlcv


@dataclass
class ETFDualMomentumConfig:
    lookback: int = 252
    rebalance_bars: int = 10
    sectors: Tuple[str, ...] = (
        "XLC",
        "XLE",
        "XLF",
        "XLI",
        "XLK",
        "XLP",
        "XLU",
        "XLY",
    )


class ETFDualMomentumStrategy:
    def __init__(self, config: ETFDualMomentumConfig | None = None):
        self.config = config or ETFDualMomentumConfig()

    def _load_closes(self, calendar: pd.DatetimeIndex) -> Dict[str, pd.Series]:
        out: Dict[str, pd.Series] = {}
        for sym in ("SPY",) + self.config.sectors:
            df, _ = fetch_ohlcv(sym, max(len(calendar) + self.config.lookback + 50, 400))
            if df is None or df.empty:
                continue
            s = df["close"].astype(float)
            s.index = pd.to_datetime(s.index)
            out[sym] = s.reindex(calendar, method="ffill")
        return out

    def run(self, market_data: pd.DataFrame, capital: float) -> Tuple[pd.Series, List[Dict]]:
        c = self.config
        calendar = pd.to_datetime(market_data.index)
        if len(calendar) < c.lookback + c.rebalance_bars + 5:
            return pd.Series([capital] * len(market_data), index=market_data.index), []

        closes = self._load_closes(calendar)
        if "SPY" not in closes:
            return pd.Series([capital] * len(market_data), index=market_data.index), []

        spy = closes["SPY"]
        equity = capital
        equity_curve: List[float] = []
        trades: List[Dict] = []
        held: str | None = None
        entry_price = 0.0
        entry_date = None
        bars_since_rebal = c.rebalance_bars

        for i in range(len(calendar)):
            price_spy = float(spy.iloc[i]) if not np.isnan(spy.iloc[i]) else 0.0
            bars_since_rebal += 1

            if held and held in closes:
                px = float(closes[held].iloc[i])
                if not np.isnan(px) and entry_price:
                    equity = capital * (px / entry_price)

            if bars_since_rebal >= c.rebalance_bars and i >= c.lookback:
                bars_since_rebal = 0
                spy_ret = float(spy.iloc[i] / spy.iloc[i - c.lookback] - 1.0) if spy.iloc[i - c.lookback] else 0.0
                best_sym = None
                best_ret = -1.0
                for sym in c.sectors:
                    if sym not in closes:
                        continue
                    s = closes[sym]
                    if i < c.lookback or np.isnan(s.iloc[i]) or np.isnan(s.iloc[i - c.lookback]):
                        continue
                    r = float(s.iloc[i] / s.iloc[i - c.lookback] - 1.0)
                    if r > spy_ret and r > 0 and r > best_ret:
                        best_ret = r
                        best_sym = sym
                target = best_sym

                if held and held != target:
                    exit_px = float(closes[held].iloc[i]) if held in closes else price_spy
                    if entry_price:
                        trades.append(
                            {
                                "entry_date": str(entry_date),
                                "exit_date": str(calendar[i]),
                                "entry_price": round(entry_price, 6),
                                "exit_price": round(exit_px, 6),
                                "pnl_pct": round((exit_px / entry_price - 1.0), 6),
                                "symbol": held,
                                "reason": "rebalance",
                            }
                        )
                        capital = capital * (exit_px / entry_price)
                        equity = capital
                    held = None

                if target and held != target:
                    entry_price = float(closes[target].iloc[i])
                    entry_date = calendar[i]
                    held = target

            equity_curve.append(equity)

        if held and held in closes and entry_price:
            exit_px = float(closes[held].iloc[-1])
            trades.append(
                {
                    "entry_date": str(entry_date),
                    "exit_date": str(calendar[-1]),
                    "entry_price": round(entry_price, 6),
                    "exit_price": round(exit_px, 6),
                    "pnl_pct": round((exit_px / entry_price - 1.0), 6),
                    "symbol": held,
                    "reason": "eod",
                }
            )

        return pd.Series(equity_curve, index=market_data.index), trades