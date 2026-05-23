"""
Commodity ETF: SMA200 trend + pullback to rising 20 EMA + RSI not overbought (daily).

Per-symbol presets (USO vs metals) + optional realized-vol quantile gate for oil.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

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


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    dn = (-delta).clip(lower=0.0)
    ma_up = up.ewm(alpha=1.0 / period, adjust=False).mean()
    ma_dn = dn.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = ma_up / ma_dn.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


@dataclass(frozen=True)
class CommodityPullbackParams:
    rsi_max: float
    touch_band_atr: float
    tp_atr_mult: float
    sl_atr_mult: float
    max_hold_days: int
    max_rv20_quantile: float | None


_BASE = CommodityPullbackParams(55.0, 0.28, 2.0, 1.2, 12, None)

SYMBOL_PRESETS: dict[str, CommodityPullbackParams] = {
    "GLD": CommodityPullbackParams(55.0, 0.28, 2.0, 1.2, 12, None),
    "SLV": CommodityPullbackParams(55.0, 0.30, 2.0, 1.2, 12, 0.90),
    "DBC": CommodityPullbackParams(55.0, 0.28, 2.0, 1.2, 12, None),
    "USO": CommodityPullbackParams(52.0, 0.34, 1.75, 1.05, 10, 0.82),
}


class CommodityTrendPullbackRsiStrategy:
    NAME = "commodity_trend_pullback_rsi"

    def __init__(
        self,
        rsi_max: float | None = None,
        touch_band_atr: float | None = None,
        tp_atr_mult: float | None = None,
        sl_atr_mult: float | None = None,
        max_hold_days: int | None = None,
        max_rv20_quantile: float | None = None,
        symbol_presets: Mapping[str, CommodityPullbackParams] | None = None,
        force_global_params: bool = False,
    ):
        self._global = CommodityPullbackParams(
            rsi_max=float(rsi_max if rsi_max is not None else _BASE.rsi_max),
            touch_band_atr=float(touch_band_atr if touch_band_atr is not None else _BASE.touch_band_atr),
            tp_atr_mult=float(tp_atr_mult if tp_atr_mult is not None else _BASE.tp_atr_mult),
            sl_atr_mult=float(sl_atr_mult if sl_atr_mult is not None else _BASE.sl_atr_mult),
            max_hold_days=int(max_hold_days if max_hold_days is not None else _BASE.max_hold_days),
            max_rv20_quantile=max_rv20_quantile if max_rv20_quantile is not None else _BASE.max_rv20_quantile,
        )
        self._presets: Mapping[str, CommodityPullbackParams] = symbol_presets if symbol_presets is not None else SYMBOL_PRESETS
        self._force_global = bool(force_global_params)

    def _params_for(self, symbol: str) -> CommodityPullbackParams:
        if self._force_global:
            return self._global
        key = symbol.upper().split("-")[0].split("=")[0].strip()
        return self._presets.get(key, self._global)

    def generate_signals(self, df: pd.DataFrame, symbol: str = "DBC") -> list[dict]:
        df = _coerce(df)
        if not {"open", "high", "low", "close", "volume"}.issubset(df.columns) or len(df) < 220:
            return []

        p = self._params_for(symbol)
        close = df["close"].astype(float)
        low = df["low"].astype(float)
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema200 = close.ewm(span=200, adjust=False).mean()
        rsi14 = _rsi(close, 14)
        atr = _atr(df, 14)
        rv20 = close.pct_change().rolling(20, min_periods=20).std()

        out: list[dict] = []
        for i in range(200, len(df)):
            if pd.isna(atr.iloc[i]):
                continue
            c = float(close.iloc[i])
            a = float(atr.iloc[i])
            if a <= 0:
                continue

            if p.max_rv20_quantile is not None and i >= 252:
                w = rv20.iloc[i - 252 : i].dropna()
                if len(w) > 80 and not pd.isna(rv20.iloc[i]):
                    thr = float(w.quantile(p.max_rv20_quantile))
                    if float(rv20.iloc[i]) > thr:
                        continue

            uptrend = c > float(ema200.iloc[i]) and float(ema20.iloc[i]) > float(ema200.iloc[i])
            touched = float(low.iloc[i]) <= float(ema20.iloc[i]) + p.touch_band_atr * a
            rsi_ok = float(rsi14.iloc[i]) < p.rsi_max
            reclaim = c >= float(ema20.iloc[i])

            if uptrend and touched and rsi_ok and reclaim:
                out.append(
                    {
                        "symbol": symbol,
                        "side": "LONG",
                        "entry_price": c,
                        "take_profit": c + a * p.tp_atr_mult,
                        "stop_loss": c - a * p.sl_atr_mult,
                        "strength": 64,
                        "reason": f"Trend + EMA20 pullback + RSI [{symbol}]",
                        "strategy": self.NAME,
                        "max_hold_days": p.max_hold_days,
                        "timestamp": df.index[i],
                        "bar_index": i,
                    }
                )
        return out
