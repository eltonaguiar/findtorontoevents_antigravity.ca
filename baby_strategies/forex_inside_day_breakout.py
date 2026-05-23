"""
Forex (daily): inside day (range inside prior day) then breakout in trend direction.

Trend: 50 EMA > 200 EMA for longs only in this template.
"""

from __future__ import annotations

import pandas as pd


def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [str(c[0]).lower() for c in out.columns]
    else:
        out.columns = [str(c).lower() for c in out.columns]
    return out


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    c = df["close"].astype(float)
    tr = pd.concat([(h - l), (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


class ForexInsideDayBreakoutStrategy:
    NAME = "forex_inside_day_breakout"

    def __init__(
        self,
        tp_atr_mult: float = 2.0,
        sl_atr_mult: float = 1.0,
        max_hold_days: int = 8,
    ):
        self.tp_atr_mult = float(tp_atr_mult)
        self.sl_atr_mult = float(sl_atr_mult)
        self.max_hold_days = int(max_hold_days)

    def generate_signals(self, df: pd.DataFrame, symbol: str = "EURUSD=X") -> list[dict]:
        df = _coerce(df)
        if not {"open", "high", "low", "close", "volume"}.issubset(df.columns) or len(df) < 220:
            return []

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        ema50 = close.ewm(span=50, adjust=False).mean()
        ema200 = close.ewm(span=200, adjust=False).mean()
        atr = _atr(df, 14)
        out: list[dict] = []

        for i in range(200, len(df)):
            if pd.isna(atr.iloc[i]):
                continue
            c = float(close.iloc[i])
            a = float(atr.iloc[i])
            if a <= 0:
                continue

            h1 = float(high.iloc[i - 1])
            l1 = float(low.iloc[i - 1])
            h2 = float(high.iloc[i - 2])
            l2 = float(low.iloc[i - 2])

            inside = h1 <= h2 and l1 >= l2
            bull_trend = float(ema50.iloc[i]) > float(ema200.iloc[i])
            break_up = c > h1

            if inside and bull_trend and break_up:
                out.append(
                    {
                        "symbol": symbol,
                        "side": "LONG",
                        "entry_price": c,
                        "take_profit": c + a * self.tp_atr_mult,
                        "stop_loss": c - a * self.sl_atr_mult,
                        "strength": 61,
                        "reason": "Inside day + upside break in bullish EMA alignment",
                        "strategy": self.NAME,
                        "max_hold_days": self.max_hold_days,
                        "timestamp": df.index[i],
                        "bar_index": i,
                    }
                )
        return out
