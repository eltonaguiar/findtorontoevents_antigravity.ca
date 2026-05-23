"""
Institutional vector signal suite — 20 distinct rule engines on OHLCV.

Each function takes a DataFrame with columns: Open, High, Low, Close, Volume
(index = DatetimeIndex). Returns a 0/1 Series (long intent) **same index as Close**.

Callers MUST .shift(1) before trading to avoid same-bar lookahead; the matrix
runner does this uniformly.

No fabricated performance — combine with institutional_matrix_runner.py + real data.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np
import pandas as pd


def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0.0)
    down = (-d).clip(lower=0.0)
    ma_u = up.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    ma_d = down.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = ma_u / ma_d.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(h: pd.Series, l: pd.Series, c: pd.Series, n: int = 14) -> pd.Series:
    pc = c.shift(1)
    tr = pd.concat(
        [
            (h - l).abs(),
            (h - pc).abs(),
            (l - pc).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(span=n, adjust=False).mean()


def _macd_hist(close: pd.Series) -> pd.Series:
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    macd = ema12 - ema26
    sig = _ema(macd, 9)
    return macd - sig


def _stoch_k(h: pd.Series, l: pd.Series, c: pd.Series, n: int = 14) -> pd.Series:
    ll = l.rolling(n, min_periods=n).min()
    hh = h.rolling(n, min_periods=n).max()
    return 100.0 * (c - ll) / (hh - ll).replace(0, np.nan)


def _vwap_approx(h: pd.Series, l: pd.Series, c: pd.Series, v: pd.Series) -> pd.Series:
    tp = (h + l + c) / 3.0
    return (tp * v).cumsum() / v.cumsum().replace(0, np.nan)


def _zscore(s: pd.Series, w: int) -> pd.Series:
    m = s.rolling(w, min_periods=w).mean()
    sd = s.rolling(w, min_periods=w).std()
    return (s - m) / sd.replace(0, np.nan)


# ---------------------------------------------------------------------------
# 20 strategies — long-only binary signals
# ---------------------------------------------------------------------------


def iv_dual_ma_cross(o: pd.DataFrame) -> pd.Series:
    c = o["Close"]
    fast = _ema(c, 12)
    slow = _ema(c, 26)
    return ((fast > slow) & (fast.shift(1) <= slow.shift(1))).astype(int)


def iv_triple_ema_stack(o: pd.DataFrame) -> pd.Series:
    c = o["Close"]
    e8, e21, e55 = _ema(c, 8), _ema(c, 21), _ema(c, 55)
    return ((e8 > e21) & (e21 > e55) & (c > e21)).astype(int)


def iv_rsi2_oversold_uptrend(o: pd.DataFrame) -> pd.Series:
    c = o["Close"]
    r2 = _rsi(c, 2)
    ma200 = c.rolling(200, min_periods=50).mean()
    return ((c > ma200) & (r2 < 10)).astype(int)


def iv_rsi14_pullback(o: pd.DataFrame) -> pd.Series:
    c = o["Close"]
    r = _rsi(c, 14)
    ma50 = c.rolling(50, min_periods=30).mean()
    return ((c > ma50) & (r < 38) & (r > r.shift(1))).astype(int)


def iv_macd_hist_turn_up(o: pd.DataFrame) -> pd.Series:
    c = o["Close"]
    h = _macd_hist(c)
    return ((h > 0) & (h > h.shift(1)) & (h.shift(1) <= h.shift(2))).astype(int)


def iv_bb_squeeze_breakout(o: pd.DataFrame) -> pd.Series:
    c = o["Close"]
    mid = c.rolling(20, min_periods=20).mean()
    sd = c.rolling(20, min_periods=20).std()
    upper = mid + 2 * sd
    width = (upper - (mid - 2 * sd)) / mid.replace(0, np.nan)
    pct = width.rolling(60, min_periods=20).rank(pct=True)
    return ((pct < 0.25) & (c > upper) & (c.shift(1) <= upper.shift(1))).astype(int)


def iv_donchian_breakout_20(o: pd.DataFrame) -> pd.Series:
    h, c = o["High"], o["Close"]
    hh = h.rolling(20, min_periods=20).max()
    return (c >= hh).astype(int)


def iv_atr_expansion_long(o: pd.DataFrame) -> pd.Series:
    h, l, c = o["High"], o["Low"], o["Close"]
    atrv = _atr(h, l, c, 14)
    c_ma = c.rolling(20, min_periods=20).mean()
    return ((c > c.shift(1) + 0.5 * atrv) & (c > c_ma)).astype(int)


def iv_volume_breakout_trend(o: pd.DataFrame) -> pd.Series:
    c, v = o["Close"], o["Volume"].replace(0, np.nan)
    vma = v.rolling(20, min_periods=10).mean()
    ema20 = _ema(c, 20)
    return ((v > 1.8 * vma) & (c > ema20) & (c > c.shift(1))).astype(int)


def iv_keltner_squeeze_pop(o: pd.DataFrame) -> pd.Series:
    h, l, c = o["High"], o["Low"], o["Close"]
    ema = _ema(c, 20)
    atrv = _atr(h, l, c, 10)
    upper, lower = ema + 1.5 * atrv, ema - 1.5 * atrv
    width = (upper - lower) / ema.replace(0, np.nan)
    tight = width < width.rolling(60, min_periods=20).quantile(0.3)
    return (tight & (c > upper)).astype(int)


def iv_stoch_cross_oversold(o: pd.DataFrame) -> pd.Series:
    h, l, c = o["High"], o["Low"], o["Close"]
    k = _stoch_k(h, l, c, 14)
    d = k.rolling(3, min_periods=3).mean()
    return ((k < 25) & (k > d) & (k.shift(1) <= d.shift(1))).astype(int)


def iv_williams_r_bounce(o: pd.DataFrame) -> pd.Series:
    h, l, c = o["High"], o["Low"], o["Close"]
    ll14 = l.rolling(14, min_periods=14).min()
    hh14 = h.rolling(14, min_periods=14).max()
    wr = -100 * (hh14 - c) / (hh14 - ll14).replace(0, np.nan)
    return ((wr < -75) & (wr > wr.shift(1))).astype(int)


def iv_cci_oversold_cross(o: pd.DataFrame) -> pd.Series:
    h, l, c = o["High"], o["Low"], o["Close"]
    tp = (h + l + c) / 3.0
    sma = tp.rolling(20, min_periods=20).mean()
    md = (tp - sma).abs().rolling(20, min_periods=20).mean()
    cci = (tp - sma) / (0.015 * md.replace(0, np.nan))
    return ((cci < -100) & (cci > cci.shift(1))).astype(int)


def iv_roc_acceleration(o: pd.DataFrame) -> pd.Series:
    c = o["Close"]
    r10 = c.pct_change(10)
    r5 = c.pct_change(5)
    return ((r10 > 0) & (r5 > r10 * 0.6) & (c > _ema(c, 50))).astype(int)


def iv_ema20_pullback_reclaim(o: pd.DataFrame) -> pd.Series:
    c = o["Close"]
    e20, e50 = _ema(c, 20), _ema(c, 50)
    touched = ((c.rolling(3).min() <= e20 * 1.01) & (c.rolling(3).min() >= e20 * 0.98)).astype(
        bool
    )
    touch_prev = touched.shift(1)
    touch_prev = touch_prev.where(touch_prev.notna(), False).astype(bool)
    return ((c > e50) & touch_prev & (c > e20)).astype(int)


def iv_vwap_momentum(o: pd.DataFrame) -> pd.Series:
    h, l, c, v = o["High"], o["Low"], o["Close"], o["Volume"].replace(0, np.nan)
    vw = _vwap_approx(h, l, c, v)
    return ((c > vw * 1.002) & (c > _ema(c, 20)) & (v > v.rolling(10).mean())).astype(int)


def iv_inside_bar_breakout(o: pd.DataFrame) -> pd.Series:
    h, l, c = o["High"], o["Low"], o["Close"]
    inside = (h.shift(1) < h.shift(2)) & (l.shift(1) > l.shift(2))
    return (inside & (c > h.shift(1))).astype(int)


def iv_gap_hold_long(o: pd.DataFrame) -> pd.Series:
    o_, h, c = o["Open"], o["High"], o["Close"]
    gap = o_ > h.shift(1)
    return (gap & (c > o_) & (c > _ema(c, 20))).astype(int)


def iv_higher_low_micro(o: pd.DataFrame) -> pd.Series:
    l, c = o["Low"], o["Close"]
    hl = l.shift(1) > l.shift(2)
    hh = c > c.shift(1)
    return (hl & hh & (c > _ema(c, 30))).astype(int)


def iv_volatility_pulse(o: pd.DataFrame) -> pd.Series:
    h, l, c = o["High"], o["Low"], o["Close"]
    atrv = _atr(h, l, c, 14)
    ap = atrv / c.replace(0, np.nan)
    z = _zscore(ap, 60)
    return ((z > 1.0) & (c.pct_change(1) > 0) & (c > _ema(c, 10))).astype(int)


INSTITUTIONAL_VECTOR_STRATEGIES: Dict[str, Callable[[pd.DataFrame], pd.Series]] = {
    "iv_dual_ma_cross": iv_dual_ma_cross,
    "iv_triple_ema_stack": iv_triple_ema_stack,
    "iv_rsi2_oversold_uptrend": iv_rsi2_oversold_uptrend,
    "iv_rsi14_pullback": iv_rsi14_pullback,
    "iv_macd_hist_turn_up": iv_macd_hist_turn_up,
    "iv_bb_squeeze_breakout": iv_bb_squeeze_breakout,
    "iv_donchian_breakout_20": iv_donchian_breakout_20,
    "iv_atr_expansion_long": iv_atr_expansion_long,
    "iv_volume_breakout_trend": iv_volume_breakout_trend,
    "iv_keltner_squeeze_pop": iv_keltner_squeeze_pop,
    "iv_stoch_cross_oversold": iv_stoch_cross_oversold,
    "iv_williams_r_bounce": iv_williams_r_bounce,
    "iv_cci_oversold_cross": iv_cci_oversold_cross,
    "iv_roc_acceleration": iv_roc_acceleration,
    "iv_ema20_pullback_reclaim": iv_ema20_pullback_reclaim,
    "iv_vwap_momentum": iv_vwap_momentum,
    "iv_inside_bar_breakout": iv_inside_bar_breakout,
    "iv_gap_hold_long": iv_gap_hold_long,
    "iv_higher_low_micro": iv_higher_low_micro,
    "iv_volatility_pulse": iv_volatility_pulse,
}

assert len(INSTITUTIONAL_VECTOR_STRATEGIES) == 20
