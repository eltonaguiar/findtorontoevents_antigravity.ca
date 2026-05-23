"""
Equity: two consecutive down closes + RSI oversold bounce (daily).

Inspired by short-term reversal / Connors-style setups (research; not optimized).
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


def _rsi(close: pd.Series, period: int = 2) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    dn = (-delta).clip(lower=0.0)
    ma_up = up.ewm(alpha=1.0 / period, adjust=False).mean()
    ma_dn = dn.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = ma_up / ma_dn.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


class EquityTwoDayRsiReversalStrategy:
    NAME = "equity_two_day_rsi_reversal"

    def __init__(
        self,
        rsi2_max: float = 25.0,
        tp_atr_mult: float = 1.8,
        sl_atr_mult: float = 1.0,
        max_hold_days: int = 5,
    ):
        self.rsi2_max = float(rsi2_max)
        self.tp_atr_mult = float(tp_atr_mult)
        self.sl_atr_mult = float(sl_atr_mult)
        self.max_hold_days = int(max_hold_days)

    def generate_signals(self, df: pd.DataFrame, symbol: str = "SPY") -> list[dict]:
        df = _coerce(df)
        if not {"open", "high", "low", "close", "volume"}.issubset(df.columns) or len(df) < 220:
            return []

        close = df["close"].astype(float)
        ema200 = close.ewm(span=200, adjust=False).mean()
        rsi2 = _rsi(close, 2)
        atr = _atr(df, 14)
        out: list[dict] = []

        for i in range(200, len(df)):
            if pd.isna(atr.iloc[i]) or pd.isna(rsi2.iloc[i]):
                continue
            c0 = float(close.iloc[i])
            c1 = float(close.iloc[i - 1])
            c2 = float(close.iloc[i - 2])
            a = float(atr.iloc[i])
            if a <= 0:
                continue

            two_red = c0 < c1 < c2
            oversold = float(rsi2.iloc[i]) < self.rsi2_max
            trend_ok = c0 > float(ema200.iloc[i])

            if two_red and oversold and trend_ok:
                out.append(
                    {
                        "symbol": symbol,
                        "side": "LONG",
                        "entry_price": c0,
                        "take_profit": c0 + a * self.tp_atr_mult,
                        "stop_loss": c0 - a * self.sl_atr_mult,
                        "strength": 62,
                        "reason": "2 down days + RSI(2) extreme in long-term uptrend",
                        "strategy": self.NAME,
                        "max_hold_days": self.max_hold_days,
                        "timestamp": df.index[i],
                        "bar_index": i,
                    }
                )
        return out
