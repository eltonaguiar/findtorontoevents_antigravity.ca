"""
Shared Feature Engine — Crypto ML Edge
========================================
Single source of truth for all model features.  Used identically by
training pipelines and live inference; there is no separate
``inference_features.py``.  Changing this file changes features everywhere.

Design contract
---------------
* ``build_features(ohlcv_df, funding_df)`` is the ONE public function.
* Returns a DataFrame of exactly ``len(FEATURE_NAMES)`` columns (20).
* Every value at row T uses *only* data available at close of bar T.
  Where there is any doubt, the bar-T value is obtained via ``.shift(1)``
  on the raw series before computing the indicator.
* No raw prices in the output — every column is a return, ratio, z-score,
  percentile, or a bounded oscillator (RSI, %B).
* ``WARMUP_BARS`` is the minimum number of bars needed before the first
  fully-valid (NaN-free) feature row.  Callers should slice ``df[WARMUP_BARS:]``
  if they need a clean matrix without ``dropna()``.

Feature budget: 10-20 per FEAT-06.  Current count: 20.

References
----------
FEAT-01  Momentum : ret_1h, ret_4h, ret_24h, ret_7d
FEAT-02  Funding  : funding_rate, funding_zscore, funding_momentum
FEAT-03  Volume   : vol_ratio_20, vol_momentum
FEAT-04  Volatility: atr_14, vol_percentile_90, gk_vol_14
FEAT-05  S/R      : sr_dist_high, sr_dist_low
FEAT-06  FracDiff : close_ffd (Lopez de Prado AFML Ch.5, d=0.4)
         Extra    : rsi_14, bb_percentb, obv_slope
FEAT-07  OI       : oi_change_pct_4h, oi_price_diverge (from coinglass.db)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional

from crypto_ml_edge.features.fracdiff import frac_diff_ffd
from crypto_ml_edge.data_fetcher import fetch_klines

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

FEATURE_NAMES: list[str] = [
    # FEAT-01: Momentum
    "ret_1h",
    "ret_4h",
    "ret_24h",
    "ret_7d",
    # FEAT-02: Funding rate
    "funding_rate",
    "funding_zscore",
    "funding_momentum",
    # FEAT-03: Volume
    "vol_ratio_20",
    "vol_momentum",
    # FEAT-04: Volatility
    "atr_14",
    "vol_percentile_90",
    "gk_vol_14",
    # Extra oscillators (stationary, well-researched)
    "rsi_14",
    # FEAT-05: Support / Resistance
    "sr_dist_high",
    "sr_dist_low",
    # Extra: mean-reversion / OBV
    "bb_percentb",
    "obv_slope",
    # Fractional differentiation — Lopez de Prado, AFML Ch.5
    "close_ffd",
    # FEAT-07: Open Interest momentum (data from coinglass.db — zero new API calls)
    "oi_change_pct_4h",
    "oi_price_diverge",
]

# Longest lookback across all features.
# 282 bars (close_ffd with d=0.4, threshold=1e-4) dominates ret_7d (168 bars).
# Callers may safely slice ``output.iloc[WARMUP_BARS:]`` for a clean matrix.
WARMUP_BARS: int = 300

# ---------------------------------------------------------------------------
# Timeframe-aware lookback multipliers for momentum features.
# Maps timeframe -> bar counts for ret_4h, ret_24h, ret_7d.
# ---------------------------------------------------------------------------
_TF_MULTIPLIERS: dict[str, dict[str, int]] = {
    "1h":  {"ret_4h": 4,  "ret_24h": 24,  "ret_7d": 168},
    "4h":  {"ret_4h": 1,  "ret_24h": 6,   "ret_7d": 42},
    "15m": {"ret_4h": 16, "ret_24h": 96,  "ret_7d": 672},
}
_TF_DEFAULT = "1h"

# ---------------------------------------------------------------------------
# Private indicator helpers
# NOTE: Every helper is written so that the output at index i depends only
# on values at indices <= i.  No shift(-n) forward fills are used.
# ---------------------------------------------------------------------------

def _sma(series: pd.Series, period: int) -> pd.Series:
    """Simple moving average — uses only past data."""
    return series.rolling(period, min_periods=period).mean()


def _ema(series: pd.Series, period: int) -> pd.Series:
    """EMA (causal, adjust=False).  No lookahead."""
    return series.ewm(span=period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Wilder RSI.

    Uses ewm(alpha=1/period) — equivalent to Wilder smoothing.
    Output is bounded [0, 100]; stationary enough for ML features.
    """
    delta = close.diff()                        # diff(1) — no lookahead
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    """
    Average True Range as a *percentage of close*.

    True range uses close.shift(1) — the previous bar's close, which is
    fully available at bar T.
    """
    prev_close = close.shift(1)                 # bar T-1, fully known at T
    tr = pd.concat(
        [high - low,
         (high - prev_close).abs(),
         (low  - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr_val = tr.rolling(period, min_periods=period).mean()
    return atr_val / (close + 1e-10)            # normalise — no raw price


def _bollinger_percentb(close: pd.Series, period: int = 20,
                        num_std: float = 2.0) -> pd.Series:
    """
    Bollinger Band %B.

    %B = (close - lower) / (upper - lower).
    Bounded roughly [0, 1]; stationary oscillator.
    """
    sma = _sma(close, period)
    std = close.rolling(period, min_periods=period).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    return (close - lower) / (upper - lower + 1e-10)


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume (raw cumulative series)."""
    direction = np.sign(close.diff())
    direction.iloc[0] = 0.0
    return (direction * volume).cumsum()


def _obv_slope(close: pd.Series, volume: pd.Series,
               slope_period: int = 10, norm_period: int = 20) -> pd.Series:
    """
    OBV slope normalised by rolling standard deviation.

    obv_slope[T] = (OBV[T] - OBV[T-slope_period]) / std(OBV, norm_period)

    This is stationary and dimensionless — safe as an ML feature.
    """
    obv = _obv(close, volume)
    slope = obv.diff(slope_period)
    norm = obv.rolling(norm_period, min_periods=norm_period).std()
    return slope / (norm + 1e-10)


def _realized_vol_percentile(close: pd.Series,
                             short_window: int = 20,
                             rank_window: int = 90) -> pd.Series:
    """
    Realised-volatility percentile (FEAT-04).

    At bar T:
      1. Compute 20-bar rolling std of log-returns  -> rv[T]  (uses T..T-19)
      2. Rank rv[T] within its trailing 90-bar window  -> percentile [0, 1]

    Both steps are purely backward-looking.
    """
    log_ret = np.log(close / close.shift(1))
    rv = log_ret.rolling(short_window, min_periods=short_window).std()
    percentile = rv.rolling(rank_window, min_periods=rank_window).apply(
        lambda x: float(pd.Series(x).rank(pct=True).iloc[-1]),
        raw=False,
    )
    return percentile


def _swing_high(high: pd.Series, lookback: int = 20) -> pd.Series:
    """Rolling max of *high* over the past ``lookback`` bars (including bar T)."""
    return high.rolling(lookback, min_periods=lookback).max()


def _swing_low(low: pd.Series, lookback: int = 20) -> pd.Series:
    """Rolling min of *low* over the past ``lookback`` bars (including bar T)."""
    return low.rolling(lookback, min_periods=lookback).min()


# ---------------------------------------------------------------------------
# OI momentum helpers (FEAT-07)
# ---------------------------------------------------------------------------

def compute_oi_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add open_interest momentum features.

    oi_change_pct_4h: % change in OI over last 4 hours
      - Rising OI + rising price = strong trend (conviction signal)
      - Rising OI + falling price = short pressure building
    oi_price_diverge: price moves without OI change = weak move (fade signal)
      - |price_change_4h| > 2% AND |oi_change_pct_4h| < 0.5% → divergence=1

    When the ``open_interest`` column is absent, both features default to 0
    so the pipeline continues unaffected.
    """
    try:
        df = df.copy()
        if "open_interest" in df.columns:
            df["oi_change_pct_4h"] = df["open_interest"].pct_change(periods=4).fillna(0)
            price_chg = df["close"].pct_change(periods=4).fillna(0)
            df["oi_price_diverge"] = (
                (price_chg.abs() > 0.02) & (df["oi_change_pct_4h"].abs() < 0.005)
            ).astype(int)
        else:
            df["oi_change_pct_4h"] = 0.0
            df["oi_price_diverge"] = 0
    except Exception:  # noqa: BLE001
        df["oi_change_pct_4h"] = 0.0
        df["oi_price_diverge"] = 0
    return df


# ---------------------------------------------------------------------------
# Garman-Klass volatility helper (FEAT-04 supplement)
# ---------------------------------------------------------------------------

def garman_klass_volatility(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Garman-Klass volatility estimator (more efficient than ATR for OHLC bars).

    GK = sqrt(0.5 * ln(H/L)^2 - (2*ln2 - 1) * ln(C/O)^2)
    Annualized by multiplying by sqrt(252*24) for hourly bars.

    Returns a Series of non-negative floats.  Values within the first
    ``window`` bars will be NaN (rolling window hasn't filled).  Guards
    against zero/negative prices with a small epsilon.
    """
    try:
        eps = 1e-10
        log_hl = (np.log((df["high"] + eps) / (df["low"] + eps))) ** 2
        log_co = (np.log((df["close"] + eps) / (df["open"] + eps))) ** 2
        gk_var = 0.5 * log_hl - (2 * np.log(2) - 1) * log_co
        # Rolling mean of instantaneous GK variance; clip negative rounding noise
        gk_var_rolled = gk_var.rolling(window, min_periods=window).mean().clip(lower=0.0)
        gk = np.sqrt(gk_var_rolled)
        return gk * np.sqrt(252 * 24)  # annualise for hourly bars
    except Exception:  # noqa: BLE001
        return pd.Series(0.0, index=df.index)


# ---------------------------------------------------------------------------
# Funding-rate helpers
# ---------------------------------------------------------------------------

def _merge_funding(ohlcv_idx: pd.DatetimeIndex,
                   funding_df: pd.DataFrame) -> pd.Series:
    """
    Align funding rates to the OHLCV index using forward-fill (nearest past).

    The funding DataFrame must have a DatetimeIndex and a ``funding_rate``
    column (or be a Series).  We use ``reindex`` + ``ffill`` so that bar T
    receives the most recently published funding rate, never a future one.
    """
    if isinstance(funding_df, pd.Series):
        fr = funding_df
    else:
        fr = funding_df["funding_rate"]

    # Reindex to OHLCV timestamps; forward-fill so each bar gets the last
    # known funding rate.  No lookahead: we never backfill.
    aligned = fr.reindex(ohlcv_idx.union(fr.index)).sort_index().ffill()
    return aligned.reindex(ohlcv_idx)


# ---------------------------------------------------------------------------
# OHLCV convenience wrapper (used by GSD Scanner workflow)
# ---------------------------------------------------------------------------

def fetch_ohlcv(symbol: str, interval: str = "1h",
                limit: int = 200) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data for a symbol via the shared data_fetcher.

    Thin wrapper around ``data_fetcher.fetch_klines`` so that workflow
    scripts can do ``from crypto_ml_edge.features.engine import fetch_ohlcv``
    and get a ready-to-use DataFrame with columns
    ``[open, high, low, close, volume]``.

    Returns ``None`` if no data is available.
    """
    try:
        df = fetch_klines(symbol, interval, limit=limit, cache=True)
        if df is None or df.empty:
            return None
        # Ensure only the standard OHLCV columns are returned
        ohlcv_cols = [c for c in ["open", "high", "low", "close", "volume"]
                      if c in df.columns]
        return df[ohlcv_cols]
    except Exception as exc:
        print(f"[WARN] fetch_ohlcv({symbol}, {interval}): {exc}")
        return None


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def build_features(
    ohlcv_df: pd.DataFrame,
    funding_df: Optional[pd.DataFrame] = None,
    timeframe: str = "1h",
) -> pd.DataFrame:
    """
    Build the canonical feature matrix for the Crypto ML Edge Engine.

    Parameters
    ----------
    ohlcv_df : pd.DataFrame
        OHLCV data with columns ``[open, high, low, close, volume]``
        and a tz-aware ``DatetimeIndex`` (UTC preferred).
        Rows must be sorted ascending by time with no duplicates.

    funding_df : pd.DataFrame or pd.Series, optional
        Perpetual-futures funding rates.  Must have a ``DatetimeIndex``
        and either a ``funding_rate`` column (DataFrame) or be a plain
        Series named ``funding_rate``.  Binance publishes every 8 hours;
        this function forward-fills to match the OHLCV frequency.
        If ``None``, funding features default to 0.0.

    Returns
    -------
    pd.DataFrame
        Shape ``(len(ohlcv_df), 17)``.  Columns match ``FEATURE_NAMES``
        exactly.  Rows within the warm-up window contain ``NaN``;
        callers should slice ``result.iloc[WARMUP_BARS:]`` or call
        ``.dropna()`` before passing to a model.

    Notes
    -----
    * Zero lookahead: bar T features depend only on bars 0..T.
    * No raw prices: every column is a return, ratio, z-score, percentile,
      or a bounded oscillator.
    * This function is deterministic given the same input — safe to call
      from both training and inference code without divergence.
    """
    if ohlcv_df.empty:
        raise ValueError("ohlcv_df is empty.")
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(ohlcv_df.columns)
    if missing:
        raise ValueError(f"ohlcv_df is missing columns: {missing}")

    o = ohlcv_df["open"]
    h = ohlcv_df["high"]
    l = ohlcv_df["low"]
    c = ohlcv_df["close"]
    v = ohlcv_df["volume"]

    feat = pd.DataFrame(index=ohlcv_df.index)

    # -- FEAT-01: Momentum (lagged returns) ------------------------------------
    # pct_change(n) at index i = (c[i] - c[i-n]) / c[i-n]
    # Uses only historical closes — no lookahead.
    # Lookback periods are timeframe-aware (1h vs 4h vs 15m).
    _mult = _TF_MULTIPLIERS.get(timeframe, _TF_MULTIPLIERS[_TF_DEFAULT])
    feat["ret_1h"]  = c.pct_change(1)
    feat["ret_4h"]  = c.pct_change(_mult["ret_4h"])
    feat["ret_24h"] = c.pct_change(_mult["ret_24h"])
    feat["ret_7d"]  = c.pct_change(_mult["ret_7d"])

    # -- FEAT-02: Funding rate -------------------------------------------------
    if funding_df is not None:
        fr_series = _merge_funding(ohlcv_df.index, funding_df)
    else:
        fr_series = pd.Series(0.0, index=ohlcv_df.index)

    feat["funding_rate"] = fr_series

    # Z-score over a 20-period rolling window (mean/std of past 20 rates)
    fr_mean = fr_series.rolling(20, min_periods=20).mean()
    fr_std  = fr_series.rolling(20, min_periods=20).std()
    feat["funding_zscore"] = (fr_series - fr_mean) / (fr_std + 1e-10)

    # Momentum: change over the past 3 observations
    feat["funding_momentum"] = fr_series.diff(3)

    # -- FEAT-03: Volume -------------------------------------------------------
    vol_sma20 = _sma(v, 20)
    feat["vol_ratio_20"] = v / (vol_sma20 + 1e-10)

    # Volume momentum: fractional change over 5 bars
    # Use shift(1) so that bar T's momentum looks at bars T-1..T-6,
    # providing one extra bar of safety against any off-by-one.
    # In practice pct_change(5) already ends at T; shift(1) is the
    # conservative choice to make the guarantee airtight.
    feat["vol_momentum"] = v.shift(1).pct_change(5)

    # -- FEAT-04: Volatility ---------------------------------------------------
    feat["atr_14"]          = _atr(h, l, c, 14)
    feat["vol_percentile_90"] = _realized_vol_percentile(c, short_window=20,
                                                          rank_window=90)

    # Garman-Klass volatility (FEAT-04 supplement) — more efficient than ATR
    try:
        feat["gk_vol_14"] = garman_klass_volatility(ohlcv_df, window=14)
    except Exception:  # noqa: BLE001
        feat["gk_vol_14"] = 0.0

    # -- RSI (bounded oscillator — stationary) ---------------------------------
    feat["rsi_14"] = _rsi(c, 14)

    # -- FEAT-05: Support / Resistance -----------------------------------------
    # Distance from bar T's close to the 20-bar swing high / low,
    # expressed as a fraction of close.  Negative = below swing high.
    swing_h = _swing_high(h, 20)
    swing_l = _swing_low(l, 20)
    feat["sr_dist_high"] = (c - swing_h) / (c + 1e-10)   # <= 0 always
    feat["sr_dist_low"]  = (c - swing_l) / (c + 1e-10)   # >= 0 always

    # -- Bollinger %B (mean-reversion signal — stationary) ---------------------
    feat["bb_percentb"] = _bollinger_percentb(c, 20)

    # -- OBV slope (normalised — stationary) -----------------------------------
    feat["obv_slope"] = _obv_slope(c, v, slope_period=10, norm_period=20)

    # -- FEAT-06: Fractional differentiation — Lopez de Prado, AFML Ch.5 ------
    # FFD with d=0.4: removes unit root while preserving ~60% of memory.
    # Standard returns (d=1) destroy memory; raw prices are non-stationary.
    # d=0.4 is the sweet spot that passes ADF while retaining predictive power.
    # Window width ~282 bars at threshold=1e-4 (about 12 days of 1h data).
    feat["close_ffd"] = frac_diff_ffd(c, d=0.4)

    # -- FEAT-07: OI momentum (from coinglass.db — zero new API calls) ---------
    # compute_oi_features expects a DataFrame with at least a ``close`` column
    # and optionally an ``open_interest`` column.  If OI is absent the function
    # zero-fills gracefully so the pipeline continues unaffected.
    try:
        _oi_input = ohlcv_df.copy()
        _oi_output = compute_oi_features(_oi_input)
        feat["oi_change_pct_4h"] = _oi_output["oi_change_pct_4h"]
        feat["oi_price_diverge"]  = _oi_output["oi_price_diverge"].astype(float)
    except Exception:  # noqa: BLE001
        feat["oi_change_pct_4h"] = 0.0
        feat["oi_price_diverge"]  = 0.0

    # -- Column order: follow FEATURE_NAMES exactly ----------------------------
    feat = feat[FEATURE_NAMES]

    return feat
