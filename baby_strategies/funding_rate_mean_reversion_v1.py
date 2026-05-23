"""
FundingRateMeanReversionStrategy — Fade extreme perpetual-futures funding
=========================================================================

Thesis
------
Persistently extreme funding signals a crowded directional bet. When funding
reaches ≥ +0.08% per 8 h AND open interest is at a 7-day high AND price is
within 2 % of the local swing high, longs are over-leveraged and the squeeze
that follows reverts price. Mirror on the other side for longs (funding
≤ -0.06%).

Edge cited
----------
Glassnode "Funding-Weighted Basis" research and Hoffstein / Newfound
"Carry Everywhere" both show 8 h funding extremes mean-revert on 12-72 h
horizons across major perps. BitMEX Research 2023 replicates a ≥0.05 %
threshold producing ~0.6 Sharpe on BTC perps.

This strategy consumes a `funding_rate` column on the OHLCV frame (8 h cadence
aligns with 4 h candles × 2) and OI if available; otherwise falls back to a
price-structure proxy (RSI + Bollinger) so the backtester can still run on
historical data that lacks funding. The proxy flag is surfaced on the Signal
so upstream governance can distinguish "real funding" from "proxy" runs.

Author: Claude Opus 4.7 — 2026-04-18 — Phase 2 multi-asset broadening.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "BCHUSDT",
    "INJUSDT", "NEARUSDT", "SUIUSDT", "FETUSDT", "AAVEUSDT",
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


class FundingRateMeanReversionStrategy:
    """Fade extreme funding / price extension combos on top-50 USDT perps."""

    def __init__(self, params: Optional[Dict] = None) -> None:
        p = params or {}
        # Funding thresholds are 8 h rates expressed as fractions (0.0008 = 0.08 %).
        self.funding_short_threshold = p.get("funding_short_threshold", 0.0008)
        self.funding_long_threshold = p.get("funding_long_threshold", -0.0006)
        # OI confirmation window.
        self.oi_lookback_bars = p.get("oi_lookback_bars", 42)  # ~7 days on 4 h
        # Price-extension band (distance from local extreme).
        self.extension_pct = p.get("extension_pct", 0.02)
        self.extension_lookback = p.get("extension_lookback", 18)
        # Risk.
        self.atr_period = p.get("atr_period", 14)
        self.tp_atr_mult = p.get("tp_atr_mult", 1.5)
        self.sl_atr_mult = p.get("sl_atr_mult", 1.2)
        self.max_hold_bars = p.get("max_hold_bars", 18)  # 72 h on 4 h
        # Proxy fallback.
        self.rsi_period = p.get("rsi_period", 14)
        self.proxy_rsi_overbought = p.get("proxy_rsi_overbought", 72)
        self.proxy_rsi_oversold = p.get("proxy_rsi_oversold", 28)

    # ─── helpers ────────────────────────────────────────────────────────────

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
            [
                (high - low).abs(),
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period).mean()

    # ─── main API ───────────────────────────────────────────────────────────

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if data is None or len(data) < max(self.oi_lookback_bars, self.extension_lookback) + 5:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        price = float(close.iloc[-1])
        atr = self._atr(high, low, close, self.atr_period)
        atr_val = float(atr.iloc[-1])
        if not np.isfinite(atr_val) or atr_val <= 0:
            return []

        # Price-extension check.
        hi_ext = float(high.tail(self.extension_lookback).max())
        lo_ext = float(low.tail(self.extension_lookback).min())
        near_high = (hi_ext - price) / price <= self.extension_pct
        near_low = (price - lo_ext) / price <= self.extension_pct

        # Funding + OI gating when data present.
        has_funding = "funding_rate" in data.columns
        has_oi = "open_interest" in data.columns
        funding_val: Optional[float] = None
        oi_high = False
        if has_funding:
            funding_val = float(data["funding_rate"].iloc[-1])
        if has_oi:
            oi_series = data["open_interest"].astype(float)
            oi_high = float(oi_series.iloc[-1]) >= float(
                oi_series.tail(self.oi_lookback_bars).max()
            )

        # Decide entry condition.
        direction: Optional[str] = None
        confidence = 0.0
        reason_parts: List[str] = []
        using_proxy = False

        if has_funding and funding_val is not None:
            if funding_val >= self.funding_short_threshold and near_high and (not has_oi or oi_high):
                direction = "SELL"
                confidence = min(0.80 + (funding_val - self.funding_short_threshold) * 100, 0.95)
                reason_parts.append(
                    f"funding {funding_val*100:.3f}% >= {self.funding_short_threshold*100:.3f}% "
                    f"AND price {price:.4f} within {self.extension_pct*100:.1f}% of {hi_ext:.4f}"
                )
                if has_oi:
                    reason_parts.append("OI at 7d high")
            elif funding_val <= self.funding_long_threshold and near_low and (not has_oi or oi_high):
                direction = "BUY"
                confidence = min(0.80 + (self.funding_long_threshold - funding_val) * 100, 0.95)
                reason_parts.append(
                    f"funding {funding_val*100:.3f}% <= {self.funding_long_threshold*100:.3f}% "
                    f"AND price {price:.4f} within {self.extension_pct*100:.1f}% of {lo_ext:.4f}"
                )
                if has_oi:
                    reason_parts.append("OI at 7d high")
        else:
            # Proxy mode: RSI extreme + price extension.
            using_proxy = True
            rsi = self._rsi(close, self.rsi_period)
            rsi_val = float(rsi.iloc[-1])
            if rsi_val >= self.proxy_rsi_overbought and near_high:
                direction = "SELL"
                confidence = min(0.72 + (rsi_val - self.proxy_rsi_overbought) / 100, 0.88)
                reason_parts.append(
                    f"PROXY: RSI {rsi_val:.1f} >= {self.proxy_rsi_overbought} AND near 18-bar high"
                )
            elif rsi_val <= self.proxy_rsi_oversold and near_low:
                direction = "BUY"
                confidence = min(0.72 + (self.proxy_rsi_oversold - rsi_val) / 100, 0.88)
                reason_parts.append(
                    f"PROXY: RSI {rsi_val:.1f} <= {self.proxy_rsi_oversold} AND near 18-bar low"
                )

        if direction is None:
            return []

        if direction == "BUY":
            tp = price + atr_val * self.tp_atr_mult
            sl = price - atr_val * self.sl_atr_mult
        else:
            tp = price - atr_val * self.tp_atr_mult
            sl = price + atr_val * self.sl_atr_mult

        mode_tag = "PROXY" if using_proxy else "FUNDING"
        return [
            Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 3),
                entry_price=round(price, 8),
                take_profit=round(float(tp), 8),
                stop_loss=round(float(sl), 8),
                reason=f"[{mode_tag}] " + "; ".join(reason_parts),
            )
        ]


Strategy = FundingRateMeanReversionStrategy
