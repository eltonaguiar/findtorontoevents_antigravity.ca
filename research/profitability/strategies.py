"""Candidate strategy implementations (v1 registry).

Every function returns target weights indexed like the close panel; execution and costs are
handled by backtest.portfolio_returns (signal at close t -> position from t+1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def buy_hold(close: pd.DataFrame) -> pd.DataFrame:
    """Equal-weight, daily-rebalanced, only currently available symbols."""
    avail = close.notna().astype(float)
    return avail.div(avail.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)


def fixed_mix(close: pd.DataFrame, mix: dict[str, float]) -> pd.DataFrame:
    w = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    for sym, wt in mix.items():
        if sym in w.columns:
            w[sym] = wt
    return w


def tsmom(close: pd.DataFrame, lookback: int = 200) -> pd.DataFrame:
    """Long when close > trailing SMA, else flat. One column per asset."""
    sma = close.rolling(lookback, min_periods=lookback).mean()
    return (close > sma).astype(float).where(close.notna(), 0.0)


def vol_scaled_tsmom(close: pd.DataFrame, lookback: int = 200, vol_window: int = 20,
                     target_vol: float = 0.40, cap: float = 1.5) -> pd.DataFrame:
    """Long/flat trend scaled by target/realized vol, capped. Long-only in v1."""
    trend = (close > close.rolling(lookback, min_periods=lookback).mean()).astype(float)
    realized = close.pct_change().rolling(vol_window, min_periods=vol_window).std() * np.sqrt(365)
    scale = (target_vol / realized).clip(upper=cap).fillna(0.0)
    return (trend * scale).clip(lower=0.0, upper=cap).where(close.notna(), 0.0)


def xs_momentum(close: pd.DataFrame, lookback: int = 28, top: int = 3,
                min_history: int = 180, freq: str = "W-FRI") -> pd.DataFrame:
    """Weekly cross-sectional momentum: equal-weight top-N by trailing return."""
    idx = close.index
    periods = idx.to_period(freq)
    rebal = pd.Series(idx, index=idx).groupby(periods).max()
    rows: dict[pd.Timestamp, pd.Series] = {}
    hist_count = close.notna().cumsum()
    for d in rebal:
        if d not in close.index:
            continue
        cur = pd.Series(0.0, index=close.columns)
        if len(close.loc[:d]) >= min_history:
            mom = (close.loc[d] / close.shift(lookback).loc[d] - 1.0)
            valid = mom.dropna()
            valid = valid[hist_count.loc[d].reindex(valid.index) >= min_history]
            if len(valid) >= top:
                sel = valid.nlargest(top).index
                cur[sel] = 1.0 / top
        rows[d] = cur
    if not rows:
        return pd.DataFrame(0.0, index=idx, columns=close.columns)
    w = pd.DataFrame(rows).T.reindex(idx).ffill().fillna(0.0)
    return w


def rsi(series: pd.Series, n: int = 2) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0.0).ewm(alpha=1.0 / n, adjust=False).mean()
    down = (-delta.clip(upper=0.0)).ewm(alpha=1.0 / n, adjust=False).mean()
    rs = up / down.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    out = out.where(~((down <= 0) & (up > 0)), 100.0)
    out = out.where(~((up <= 0) & (down > 0)), 0.0)
    return out.fillna(50.0)


def rsi2(close: pd.DataFrame, entry: float = 10.0, exit_level: float = 50.0,
         max_hold: int = 5, min_history: int = 30) -> pd.DataFrame:
    """Long when RSI(2) < entry; exit when RSI(2) > exit or max_hold days."""
    out = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    for col in close.columns:
        s = close[col]
        r = rsi(s, 2)
        holding = False
        held = 0
        for i in range(len(s)):
            if not np.isfinite(s.iloc[i]) or i < min_history:
                out.iloc[i, out.columns.get_loc(col)] = 0.0
                continue
            if not holding:
                if np.isfinite(r.iloc[i]) and r.iloc[i] < entry:
                    holding = True
                    held = 0
            else:
                held += 1
                if (np.isfinite(r.iloc[i]) and r.iloc[i] > exit_level) or held >= max_hold:
                    holding = False
            out.iloc[i, out.columns.get_loc(col)] = 1.0 if holding else 0.0
    active = out.sum(axis=1)
    return out.div(active.replace(0.0, np.nan), axis=0).fillna(0.0)


def dual_momentum(close: pd.DataFrame, risk: list[str], cash: str = "BIL",
                  lookback: int = 252) -> pd.DataFrame:
    """Monthly: hold the best risk asset if its 12m return beats cash, else cash."""
    idx = close.index
    periods = idx.to_period("M")
    rebal = pd.Series(idx, index=idx).groupby(periods).max()
    rows: dict[pd.Timestamp, pd.Series] = {}
    for d in rebal:
        if d not in close.index:
            continue
        cur = pd.Series(0.0, index=close.columns)
        hist = close.loc[:d]
        if len(hist) > lookback:
            base = hist.iloc[-lookback - 1]
            mom = (close.loc[d] / base - 1.0).dropna()
            risk_mom = mom.reindex([s for s in risk if s in mom.index]).dropna()
            cash_mom = mom.get(cash, np.nan)
            if len(risk_mom):
                best = risk_mom.idxmax()
                if np.isfinite(cash_mom) and risk_mom[best] > cash_mom:
                    cur[best] = 1.0
                elif cash in cur.index:
                    cur[cash] = 1.0
                else:
                    cur[best] = 1.0
        rows[d] = cur
    if not rows:
        return pd.DataFrame(0.0, index=idx, columns=close.columns)
    return pd.DataFrame(rows).T.reindex(idx).ffill().fillna(0.0)


def _with_cash(risk: pd.DataFrame, cash_ret: pd.Series) -> pd.DataFrame:
    """Scale risk weights to <=1 and put the remainder in CASH."""
    s = risk.sum(axis=1)
    scale = pd.Series(1.0, index=risk.index)
    over = s > 1.0
    scale[over] = 1.0 / s[over]
    risk = risk.mul(scale, axis=0)
    out = risk.copy()
    out["CASH"] = (1.0 - risk.sum(axis=1)).clip(lower=0.0)
    return out


def rsi2_cash(close: pd.DataFrame, cash_ret: pd.Series, entry: float = 10.0,
              exit_level: float = 50.0, max_hold: int = 5) -> pd.DataFrame:
    return _with_cash(rsi2(close, entry, exit_level, max_hold), cash_ret)


def rsi2_trend_cash(close: pd.DataFrame, cash_ret: pd.Series, trend_lookback: int = 200,
                    entry: float = 10.0, exit_level: float = 50.0, max_hold: int = 5) -> pd.DataFrame:
    trend = (close > close.rolling(trend_lookback, min_periods=trend_lookback).mean()).astype(float)
    risk = rsi2(close, entry, exit_level, max_hold) * trend
    return _with_cash(risk, cash_ret)


def sector_momentum_cash(close: pd.DataFrame, cash_ret: pd.Series, lookback: int = 252,
                         top: int = 3) -> pd.DataFrame:
    risk = xs_momentum(close, lookback=lookback, top=top, min_history=lookback, freq="M")
    return _with_cash(risk, cash_ret)
