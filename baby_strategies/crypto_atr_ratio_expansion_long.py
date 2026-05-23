"""
Crypto: short ATR / long ATR compression then expansion with upside break (daily).

Per-symbol presets (ETH vs BTC), optional ``--crypto-mode btc_only`` in
``backtest_batch_round3.py``, and volatility gates (ATR/close + RV20 quantile).
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


@dataclass(frozen=True)
class CryptoAtrRatioParams:
    ratio_max: float
    tp_atr_mult: float
    sl_atr_mult: float
    max_hold_days: int
    max_atr_over_close: float | None
    max_rv20_quantile: float | None


_BASE = CryptoAtrRatioParams(
    ratio_max=0.78,
    tp_atr_mult=2.5,
    sl_atr_mult=1.15,
    max_hold_days=10,
    max_atr_over_close=None,
    max_rv20_quantile=None,
)

SYMBOL_PRESETS: dict[str, CryptoAtrRatioParams] = {
    "BTC-USD": CryptoAtrRatioParams(
        ratio_max=0.78,
        tp_atr_mult=2.5,
        sl_atr_mult=1.15,
        max_hold_days=10,
        max_atr_over_close=0.095,
        max_rv20_quantile=0.92,
    ),
    "ETH-USD": CryptoAtrRatioParams(
        ratio_max=0.64,
        tp_atr_mult=1.85,
        sl_atr_mult=0.98,
        max_hold_days=8,
        max_atr_over_close=0.055,
        max_rv20_quantile=0.84,
    ),
    "SOL-USD": CryptoAtrRatioParams(
        ratio_max=0.74,
        tp_atr_mult=2.3,
        sl_atr_mult=1.12,
        max_hold_days=10,
        max_atr_over_close=0.085,
        max_rv20_quantile=0.90,
    ),
    "BNB-USD": CryptoAtrRatioParams(
        ratio_max=0.76,
        tp_atr_mult=2.4,
        sl_atr_mult=1.14,
        max_hold_days=10,
        max_atr_over_close=0.088,
        max_rv20_quantile=0.91,
    ),
}


class CryptoAtrRatioExpansionLongStrategy:
    NAME = "crypto_atr_ratio_expansion_long"

    def __init__(
        self,
        ratio_max: float | None = None,
        tp_atr_mult: float | None = None,
        sl_atr_mult: float | None = None,
        max_hold_days: int | None = None,
        max_atr_over_close: float | None = None,
        max_rv20_quantile: float | None = None,
        symbol_presets: Mapping[str, CryptoAtrRatioParams] | None = None,
        force_global_params: bool = False,
    ):
        self._global = CryptoAtrRatioParams(
            ratio_max=float(ratio_max if ratio_max is not None else _BASE.ratio_max),
            tp_atr_mult=float(tp_atr_mult if tp_atr_mult is not None else _BASE.tp_atr_mult),
            sl_atr_mult=float(sl_atr_mult if sl_atr_mult is not None else _BASE.sl_atr_mult),
            max_hold_days=int(max_hold_days if max_hold_days is not None else _BASE.max_hold_days),
            max_atr_over_close=max_atr_over_close if max_atr_over_close is not None else _BASE.max_atr_over_close,
            max_rv20_quantile=max_rv20_quantile if max_rv20_quantile is not None else _BASE.max_rv20_quantile,
        )
        self._presets: Mapping[str, CryptoAtrRatioParams] = symbol_presets if symbol_presets is not None else SYMBOL_PRESETS
        self._force_global = bool(force_global_params)

    def _params_for(self, symbol: str) -> CryptoAtrRatioParams:
        if self._force_global:
            return self._global
        return self._presets.get(symbol, self._global)

    def generate_signals(self, df: pd.DataFrame, symbol: str = "BTC-USD") -> list[dict]:
        df = _coerce(df)
        if not {"open", "high", "low", "close", "volume"}.issubset(df.columns) or len(df) < 220:
            return []

        p = self._params_for(symbol)
        close = df["close"].astype(float)
        high = df["high"].astype(float)
        ema50 = close.ewm(span=50, adjust=False).mean()
        atr5 = _atr(df, 5)
        atr20 = _atr(df, 20)
        atr14 = _atr(df, 14)
        rv20 = close.pct_change().rolling(20, min_periods=20).std()

        out: list[dict] = []
        for i in range(200, len(df)):
            if pd.isna(atr5.iloc[i]) or pd.isna(atr20.iloc[i]) or pd.isna(atr14.iloc[i]):
                continue
            c = float(close.iloc[i])
            a = float(atr14.iloc[i])
            if a <= 0 or float(atr20.iloc[i]) <= 0:
                continue

            if p.max_atr_over_close is not None and (a / max(c, 1e-12)) > p.max_atr_over_close:
                continue

            if p.max_rv20_quantile is not None and i >= 252:
                w = rv20.iloc[i - 252 : i].dropna()
                if len(w) > 80 and not pd.isna(rv20.iloc[i]):
                    thr = float(w.quantile(p.max_rv20_quantile))
                    if float(rv20.iloc[i]) > thr:
                        continue

            ratio = float(atr5.iloc[i]) / float(atr20.iloc[i])
            prior_high = max(float(high.iloc[i - 1]), float(high.iloc[i - 2]), float(high.iloc[i - 3]))
            compress = ratio < p.ratio_max
            trend = c > float(ema50.iloc[i])
            breakout = c > prior_high

            if compress and trend and breakout:
                out.append(
                    {
                        "symbol": symbol,
                        "side": "LONG",
                        "entry_price": c,
                        "take_profit": c + a * p.tp_atr_mult,
                        "stop_loss": c - a * p.sl_atr_mult,
                        "strength": 65,
                        "reason": f"ATR compress + EMA50 + 3d high [{symbol}]",
                        "strategy": self.NAME,
                        "max_hold_days": p.max_hold_days,
                        "timestamp": df.index[i],
                        "bar_index": i,
                    }
                )
        return out
