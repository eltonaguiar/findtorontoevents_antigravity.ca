"""
crypto_donchian_retest_voltarget_kellycap_v1
=============================================

Breakout-retest continuation with volatility targeting and Kelly-capped
confidence for smoother risk-adjusted behavior.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class CryptoDonchianRetestVoltargetKellycapStrategy:
    """Donchian breakout retest with risk scaling and Kelly confidence cap."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.donchian_window = self.p.get("donchian_window", 20)
        self.retest_tolerance = self.p.get("retest_tolerance", 0.003)
        self.vol_window = self.p.get("vol_window", 48)
        self.target_vol = self.p.get("target_vol", 0.018)
        self.atr_period = self.p.get("atr_period", 14)
        self.tp_atr = self.p.get("tp_atr", 2.4)
        self.sl_atr = self.p.get("sl_atr", 1.4)
        self.edge_window = self.p.get("edge_window", 80)
        self.kelly_cap = self.p.get("kelly_cap", 0.25)

    def generate_signals(
        self,
        data: pd.DataFrame,
        account_balance: float,
        symbol: str = "BTCUSDT",
    ) -> List[Signal]:
        min_len = max(self.donchian_window, self.edge_window, self.vol_window) + 12
        if data is None or len(data) < min_len:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        upper = high.shift(1).rolling(self.donchian_window).max()
        lower = low.shift(1).rolling(self.donchian_window).min()
        atr = self._atr(data, self.atr_period)

        curr_price = float(close.iloc[-1])
        curr_atr = float(atr.iloc[-1])
        if np.isnan(curr_atr) or curr_atr <= 0:
            return []

        prev_close = float(close.iloc[-2])
        prev_upper = float(upper.iloc[-2]) if not np.isnan(upper.iloc[-2]) else np.nan
        prev_lower = float(lower.iloc[-2]) if not np.isnan(lower.iloc[-2]) else np.nan
        curr_upper = float(upper.iloc[-1]) if not np.isnan(upper.iloc[-1]) else np.nan
        curr_lower = float(lower.iloc[-1]) if not np.isnan(lower.iloc[-1]) else np.nan

        breakout_up = not np.isnan(prev_upper) and prev_close > prev_upper
        breakout_down = not np.isnan(prev_lower) and prev_close < prev_lower
        retest_up = breakout_up and not np.isnan(curr_upper) and float(low.iloc[-1]) <= curr_upper * (1 + self.retest_tolerance) and curr_price >= curr_upper
        retest_down = breakout_down and not np.isnan(curr_lower) and float(high.iloc[-1]) >= curr_lower * (1 - self.retest_tolerance) and curr_price <= curr_lower

        # Vol targeting multiplier for exit distances.
        realized_vol = close.pct_change().rolling(self.vol_window).std(ddof=0).iloc[-1]
        if np.isnan(realized_vol) or realized_vol <= 0:
            vol_scale = 1.0
        else:
            vol_scale = float(np.clip(self.target_vol / realized_vol, 0.6, 1.8))

        kelly_f = self._kelly_fraction(close.pct_change().dropna().tail(self.edge_window))
        kelly_f = float(np.clip(kelly_f, 0.0, self.kelly_cap))

        # Keep account_balance in signature for runner compatibility and future sizing.
        _ = float(account_balance) if account_balance is not None else 0.0

        signals: List[Signal] = []
        if retest_up:
            confidence = min(0.95, 0.55 + kelly_f * 1.2 + min((vol_scale - 1.0) * 0.2, 0.12))
            tp_mult = self.tp_atr * vol_scale
            sl_mult = self.sl_atr / max(vol_scale, 0.7)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(curr_price, 2),
                    take_profit=round(curr_price + curr_atr * tp_mult, 2),
                    stop_loss=round(curr_price - curr_atr * sl_mult, 2),
                    reason=f"DonchianRetestUP volScale={vol_scale:.2f} kelly={kelly_f:.2f}",
                )
            )
        elif retest_down:
            confidence = min(0.95, 0.55 + kelly_f * 1.2 + min((vol_scale - 1.0) * 0.2, 0.12))
            tp_mult = self.tp_atr * vol_scale
            sl_mult = self.sl_atr / max(vol_scale, 0.7)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(curr_price, 2),
                    take_profit=round(curr_price - curr_atr * tp_mult, 2),
                    stop_loss=round(curr_price + curr_atr * sl_mult, 2),
                    reason=f"DonchianRetestDN volScale={vol_scale:.2f} kelly={kelly_f:.2f}",
                )
            )
        return signals

    @staticmethod
    def _kelly_fraction(rets: pd.Series) -> float:
        if rets is None or len(rets) < 20:
            return 0.05
        wins = rets[rets > 0]
        losses = -rets[rets < 0]
        if len(wins) < 5 or len(losses) < 5:
            return 0.05
        p = len(wins) / len(rets)
        avg_win = wins.mean()
        avg_loss = losses.mean()
        if avg_loss <= 0:
            return 0.05
        b = avg_win / avg_loss
        if b <= 0:
            return 0.05
        q = 1 - p
        return float((b * p - q) / b)

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        tr = pd.concat(
            [(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()

