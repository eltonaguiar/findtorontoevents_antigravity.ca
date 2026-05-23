"""
Superior Crypto Strategy — Multi-Pair, Multi-Timeframe Backtester
=================================================================
Faithfully translates the Nexus Alpha Pine Script logic to Python.
Tests across BTC, ETH, SOL, AVAX on 1H, 4H, 1D timeframes.
Produces a performance matrix with win rate, profit factor, Sharpe,
max drawdown, and comparison vs buy-and-hold.

Requirements: pip install pandas numpy yfinance
"""

import os
import sys
import warnings
from datetime import datetime, timedelta
from itertools import product

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system(f"{sys.executable} -m pip install yfinance -q")
    import yfinance as yf


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

PAIRS = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "AVAX": "AVAX-USD",
    "BNB": "BNB-USD",
    "ADA": "ADA-USD",
    "DOT": "DOT-USD",
    "MATIC": "MATIC-USD",
}

TIMEFRAMES = {
    "1H": "1h",
    "4H": "1h",   # download 1h and resample
    "1D": "1d",
}

LOOKBACK_DAYS = 365 * 2  # 2 years
INITIAL_CAPITAL = 10000
COMMISSION_PCT = 0.1 / 100
POSITION_SIZE_PCT = 0.20


# ═══════════════════════════════════════════════════════════════════════════════
# INDICATOR FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def sma(series, period):
    return series.rolling(period).mean()

def stdev(series, period):
    return series.rolling(period).std()

def atr(df, period):
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def rsi(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)

def kama(series, length=9, fast_len=2, slow_len=30):
    fastest = 2.0 / (fast_len + 1)
    slowest = 2.0 / (slow_len + 1)
    result = pd.Series(index=series.index, dtype=float)
    result.iloc[:length] = np.nan
    if len(series) <= length:
        return result
    result.iloc[length] = series.iloc[length]
    for i in range(length + 1, len(series)):
        change_val = abs(series.iloc[i] - series.iloc[i - length])
        vol_sum = sum(abs(series.iloc[j] - series.iloc[j - 1]) for j in range(i - length + 1, i + 1))
        er = change_val / vol_sum if vol_sum != 0 else 0
        sc = (er * (fastest - slowest) + slowest) ** 2
        result.iloc[i] = result.iloc[i - 1] + sc * (series.iloc[i] - result.iloc[i - 1])
    return result

def hma(series, length=16):
    half_wma = series.rolling(length // 2).apply(
        lambda x: np.average(x, weights=range(1, len(x) + 1)), raw=True)
    full_wma = series.rolling(length).apply(
        lambda x: np.average(x, weights=range(1, len(x) + 1)), raw=True)
    raw = 2 * half_wma - full_wma
    sqrt_len = max(int(np.sqrt(length)), 1)
    return raw.rolling(sqrt_len).apply(
        lambda x: np.average(x, weights=range(1, len(x) + 1)), raw=True)

def supertrend(df, factor=3.0, atr_period=10):
    atr_val = atr(df, atr_period)
    hl2 = (df["High"] + df["Low"]) / 2
    upper = hl2 + factor * atr_val
    lower = hl2 - factor * atr_val

    st_dir = pd.Series(1, index=df.index, dtype=int)
    final_upper = upper.copy()
    final_lower = lower.copy()

    for i in range(1, len(df)):
        if lower.iloc[i] > final_lower.iloc[i - 1]:
            final_lower.iloc[i] = lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]

        if upper.iloc[i] < final_upper.iloc[i - 1]:
            final_upper.iloc[i] = upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        if st_dir.iloc[i - 1] == -1:
            if df["Close"].iloc[i] > final_upper.iloc[i - 1]:
                st_dir.iloc[i] = 1
            else:
                st_dir.iloc[i] = -1
        else:
            if df["Close"].iloc[i] < final_lower.iloc[i - 1]:
                st_dir.iloc[i] = -1
            else:
                st_dir.iloc[i] = 1

    return st_dir

def stochastic_rsi(close_series, rsi_period=14, stoch_period=14, k_smooth=3):
    rsi_val = rsi(close_series, rsi_period)
    stoch_k = ((rsi_val - rsi_val.rolling(stoch_period).min()) /
               (rsi_val.rolling(stoch_period).max() - rsi_val.rolling(stoch_period).min()).replace(0, np.nan)) * 100
    stoch_d = stoch_k.rolling(k_smooth).mean()
    return stoch_k, stoch_d

def adx(df, period=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0)
    minus_dm = np.where((down > up) & (down > 0), down, 0)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr_val = tr.ewm(alpha=1/period, min_periods=period).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/period, min_periods=period).mean() / atr_val
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/period, min_periods=period).mean() / atr_val
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_val = dx.ewm(alpha=1/period, min_periods=period).mean()
    return adx_val, plus_di, minus_di

def hurst_exponent(series, length=50):
    result = pd.Series(index=series.index, dtype=float)
    for i in range(length, len(series)):
        window = series.iloc[i - length:i]
        max_rs = window.max() - window.min()
        std_dev = window.std()
        if std_dev > 0 and max_rs > 0:
            rs = max_rs / std_dev
            h_est = 0.5 + (np.log(rs) / np.log(length) - 0.5) * 0.3
            result.iloc[i] = max(0.1, min(0.9, h_est))
        else:
            result.iloc[i] = 0.5
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

def compute_signals(df):
    """Compute all Nexus Alpha signals for a DataFrame with OHLCV columns."""
    c = df["Close"]
    h = df["High"]
    lo = df["Low"]
    v = df["Volume"]

    # Core indicators
    df["atr14"] = atr(df, 14)
    df["atr50"] = atr(df, 50)
    df["ema200"] = ema(c, 200)
    df["sma50"] = sma(c, 50)
    df["vol_sma20"] = sma(v, 20)
    df["rel_vol"] = v / df["vol_sma20"].replace(0, np.nan)
    df["atr_pct"] = (df["atr14"] / c * 100).clip(lower=0.01)

    df["kama_fast"] = kama(c, 9)
    df["kama_slow"] = kama(c, 21)
    df["hma"] = hma(c, 16)
    df["rsi2"] = rsi(c, 2)
    df["rsi14"] = rsi(c, 14)
    stk, std = stochastic_rsi(c)
    df["stoch_k"] = stk
    df["stoch_d"] = std

    macd_line = ema(c, 12) - ema(c, 26)
    signal_line = ema(macd_line, 9)
    df["macd_hist"] = macd_line - signal_line
    df["macd_line"] = macd_line
    df["signal_line"] = signal_line

    df["bb_basis"] = sma(c, 20)
    df["bb_std"] = stdev(c, 20)
    df["bb_upper"] = df["bb_basis"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_basis"] - 2 * df["bb_std"]
    bb_width = df["bb_upper"] - df["bb_lower"]
    df["pctB"] = (c - df["bb_lower"]) / bb_width.replace(0, np.nan)

    df["st_dir"] = supertrend(df)
    df["adx_val"], _, _ = adx(df)
    df["hurst"] = hurst_exponent(c)

    df["z_mean"] = sma(c, 50)
    df["z_std"] = stdev(c, 50)
    df["z_score"] = (c - df["z_mean"]) / df["z_std"].replace(0, np.nan)

    # OBV
    obv_delta = np.where(c > c.shift(1), v, np.where(c < c.shift(1), -v, 0))
    df["obv"] = pd.Series(obv_delta, index=df.index).cumsum()
    df["obv_sma"] = sma(df["obv"], 20)

    # TTM Squeeze
    kc_range = 1.5 * atr(df, 20)
    kc_upper = df["bb_basis"] + kc_range
    kc_lower = df["bb_basis"] - kc_range
    df["sqz_on"] = (df["bb_lower"] > kc_lower) & (df["bb_upper"] < kc_upper)
    df["sqz_fired"] = (~df["sqz_on"]) & df["sqz_on"].shift(1)
    ttm_avg = (h.rolling(20).max() + lo.rolling(20).min()) / 2
    ttm_mid = (ttm_avg + sma(c, 20)) / 2
    df["ttm_mom"] = c - ttm_mid

    # Donchian
    df["donch_high"] = h.rolling(20).max()
    df["donch_low"] = lo.rolling(20).min()

    # Ichimoku
    df["tenkan"] = (h.rolling(9).max() + lo.rolling(9).min()) / 2
    df["kijun"] = (h.rolling(26).max() + lo.rolling(26).min()) / 2
    df["spanA"] = ((df["tenkan"] + df["kijun"]) / 2).shift(26)
    df["spanB"] = ((h.rolling(52).max() + lo.rolling(52).min()) / 2).shift(26)
    df["cloud_top"] = pd.concat([df["spanA"], df["spanB"]], axis=1).max(axis=1)
    df["cloud_bot"] = pd.concat([df["spanA"], df["spanB"]], axis=1).min(axis=1)

    # Market structure (simplified: use rolling 20-bar swing)
    df["swing_hi"] = h.rolling(20).max().shift(1)
    df["swing_lo"] = lo.rolling(20).min().shift(1)

    # ═════════════════════════════════════════════════════════════════════════
    # REGIME DETECTION
    # ═════════════════════════════════════════════════════════════════════════
    regime = pd.Series("NORMAL", index=df.index)
    regime[(df["hurst"] > 0.55) & (df["adx_val"] > 25)] = "TRENDING"
    regime[(df["hurst"] < 0.45) & (df["adx_val"] < 20)] = "RANGING"
    vol_ratio = df["atr14"] / df["atr50"].replace(0, np.nan)
    vol_pctile = vol_ratio.rolling(100).rank(pct=True) * 100
    regime[vol_pctile > 80] = "VOLATILE"
    df["regime"] = regime

    # ═════════════════════════════════════════════════════════════════════════
    # MODULE 1: TREND FOLLOWER
    # ═════════════════════════════════════════════════════════════════════════
    kama_bull = df["kama_fast"] > df["kama_slow"]
    kama_bear = df["kama_fast"] < df["kama_slow"]
    st_bull = df["st_dir"] > 0
    st_bear = df["st_dir"] < 0
    above_ema200 = c > df["ema200"]
    below_ema200 = c < df["ema200"]
    ichi_bull = (c > df["cloud_top"]) & (df["tenkan"] > df["kijun"])
    ichi_bear = (c < df["cloud_bot"]) & (df["tenkan"] < df["kijun"])

    m1_bull = kama_bull.astype(float) * 0.25 + st_bull.astype(float) * 0.20 + above_ema200.astype(float) * 0.15 + ichi_bull.astype(float) * 0.15
    m1_bear = kama_bear.astype(float) * 0.25 + st_bear.astype(float) * 0.20 + below_ema200.astype(float) * 0.15 + ichi_bear.astype(float) * 0.15
    df["m1_conf"] = m1_bull - m1_bear

    # ═════════════════════════════════════════════════════════════════════════
    # MODULE 2: MEAN REVERSION
    # ═════════════════════════════════════════════════════════════════════════
    rsi2_bull = (df["rsi2"] < 10) & above_ema200
    rsi2_bear = (df["rsi2"] > 90) & below_ema200
    zs_bull = (df["z_score"] < -2.0) & (df["adx_val"] < 25)
    zs_bear = (df["z_score"] > 2.0) & (df["adx_val"] < 25)
    stoch_bull = (df["stoch_k"] < 20) & (df["stoch_k"] > df["stoch_d"]) & (df["stoch_k"].shift(1) <= df["stoch_d"].shift(1))
    stoch_bear = (df["stoch_k"] > 80) & (df["stoch_k"] < df["stoch_d"]) & (df["stoch_k"].shift(1) >= df["stoch_d"].shift(1))
    bb_bull = (df["pctB"] < 0) & (c > c.shift(1))
    bb_bear = (df["pctB"] > 1) & (c < c.shift(1))

    m2_bull = rsi2_bull.astype(float) * 0.30 + zs_bull.astype(float) * 0.25 + stoch_bull.astype(float) * 0.25 + bb_bull.astype(float) * 0.20
    m2_bear = rsi2_bear.astype(float) * 0.30 + zs_bear.astype(float) * 0.25 + stoch_bear.astype(float) * 0.25 + bb_bear.astype(float) * 0.20
    df["m2_conf"] = m2_bull - m2_bear

    # ═════════════════════════════════════════════════════════════════════════
    # MODULE 3: MOMENTUM / BREAKOUT
    # ═════════════════════════════════════════════════════════════════════════
    vol_spike_bull = (v > df["vol_sma20"] * 2) & (c > df["Open"]) & (c > c.shift(1))
    vol_spike_bear = (v > df["vol_sma20"] * 2) & (c < df["Open"]) & (c < c.shift(1))
    ttm_bull = df["sqz_fired"] & (df["ttm_mom"] > 0) & (df["ttm_mom"] > df["ttm_mom"].shift(1))
    ttm_bear = df["sqz_fired"] & (df["ttm_mom"] < 0) & (df["ttm_mom"] < df["ttm_mom"].shift(1))
    macd_bull = (df["macd_hist"] > 0) & (df["macd_hist"] > df["macd_hist"].shift(1)) & (df["macd_line"] > df["signal_line"])
    macd_bear = (df["macd_hist"] < 0) & (df["macd_hist"] < df["macd_hist"].shift(1)) & (df["macd_line"] < df["signal_line"])
    donch_bull = (h >= df["donch_high"]) & (c > c.shift(1))
    donch_bear = (lo <= df["donch_low"]) & (c < c.shift(1))

    m3_bull = vol_spike_bull.astype(float) * 0.30 + ttm_bull.astype(float) * 0.25 + macd_bull.astype(float) * 0.25 + donch_bull.astype(float) * 0.20
    m3_bear = vol_spike_bear.astype(float) * 0.30 + ttm_bear.astype(float) * 0.25 + macd_bear.astype(float) * 0.25 + donch_bear.astype(float) * 0.20
    df["m3_conf"] = m3_bull - m3_bear

    # ═════════════════════════════════════════════════════════════════════════
    # MODULE 4: SMART MONEY / ORDER FLOW
    # ═════════════════════════════════════════════════════════════════════════
    sfp_bull = (lo < df["swing_lo"]) & (c > df["swing_lo"]) & (c > df["Open"])
    sfp_bear = (h > df["swing_hi"]) & (c < df["swing_hi"]) & (c < df["Open"])

    cvd_range = h - lo
    cvd_buy = np.where(cvd_range > 0, v * (c - lo) / cvd_range, v * 0.5)
    cvd_sell = np.where(cvd_range > 0, v * (h - c) / cvd_range, v * 0.5)
    cvd_delta = pd.Series(cvd_buy - cvd_sell, index=df.index)
    cvd = cvd_delta.cumsum()
    cvd_sma = sma(cvd, 20)
    cvd_div_bull = (c < c.shift(5)) & (cvd > cvd_sma)
    cvd_div_bear = (c > c.shift(5)) & (cvd < cvd_sma)

    obv_div_bull = (c < c.shift(5)) & (df["obv"] > df["obv_sma"]) & (df["obv"] > df["obv"].shift(5))
    obv_div_bear = (c > c.shift(5)) & (df["obv"] < df["obv_sma"]) & (df["obv"] < df["obv"].shift(5))

    bar_rng = h - lo
    abs_rel_range = bar_rng / df["atr14"].replace(0, np.nan)
    abs_vol_ratio = v / df["vol_sma20"].replace(0, np.nan)
    abs_score = abs_vol_ratio / abs_rel_range.replace(0, np.nan)
    abs_bull = (abs_score > 4.0) & (c > (h + lo) / 2) & (c > df["Open"])
    abs_bear = (abs_score > 4.0) & (c < (h + lo) / 2) & (c < df["Open"])

    m4_bull = sfp_bull.astype(float) * 0.25 + cvd_div_bull.astype(float) * 0.20 + obv_div_bull.astype(float) * 0.20 + abs_bull.astype(float) * 0.20
    m4_bear = sfp_bear.astype(float) * 0.25 + cvd_div_bear.astype(float) * 0.20 + obv_div_bear.astype(float) * 0.20 + abs_bear.astype(float) * 0.20
    df["m4_conf"] = m4_bull - m4_bear

    # ═════════════════════════════════════════════════════════════════════════
    # META-LEARNER WEIGHTS + SIGNAL SYNTHESIS
    # ═════════════════════════════════════════════════════════════════════════
    w1 = np.where(regime == "TRENDING", 0.40, np.where(regime == "RANGING", 0.15, np.where(regime == "VOLATILE", 0.15, 0.25)))
    w2 = np.where(regime == "TRENDING", 0.10, np.where(regime == "RANGING", 0.40, np.where(regime == "VOLATILE", 0.25, 0.25)))
    w3 = np.where(regime == "TRENDING", 0.30, np.where(regime == "RANGING", 0.20, np.where(regime == "VOLATILE", 0.25, 0.25)))
    w4 = np.where(regime == "TRENDING", 0.20, np.where(regime == "RANGING", 0.25, np.where(regime == "VOLATILE", 0.35, 0.25)))

    composite = w1 * df["m1_conf"] + w2 * df["m2_conf"] + w3 * df["m3_conf"] + w4 * df["m4_conf"]
    df["composite"] = composite

    modules_long = ((df["m1_conf"] > 0.10).astype(int) + (df["m2_conf"] > 0.10).astype(int) +
                    (df["m3_conf"] > 0.10).astype(int) + (df["m4_conf"] > 0.10).astype(int))
    modules_short = ((df["m1_conf"] < -0.10).astype(int) + (df["m2_conf"] < -0.10).astype(int) +
                     (df["m3_conf"] < -0.10).astype(int) + (df["m4_conf"] < -0.10).astype(int))

    vol_ok = df["rel_vol"] > 1.0
    base_thresh = 0.28

    # Adaptive threshold: mild penalty for unclear regime, bonus for Fib confluence
    regime_conf = (df["hurst"] - 0.5).abs() * 2
    thresh = pd.Series(base_thresh, index=df.index)
    thresh[regime == "NORMAL"] = base_thresh + 0.04
    thresh[regime_conf < 0.3] = thresh[regime_conf < 0.3] + 0.03

    # Counter-trend penalty (additive, not multiplicative)
    counter_long = (composite > 0) & below_ema200
    counter_short = (composite < 0) & above_ema200
    thresh[counter_long | counter_short] = thresh[counter_long | counter_short] + 0.03

    # Fibonacci bonus
    fib_range_val = df["swing_hi"] - df["swing_lo"]
    fib_382 = df["swing_hi"] - fib_range_val * 0.382
    fib_500 = df["swing_hi"] - fib_range_val * 0.500
    fib_618 = df["swing_hi"] - fib_range_val * 0.618
    near_fib = (fib_range_val > 0) & (
        ((c - fib_382).abs() < df["atr14"] * 0.5) |
        ((c - fib_500).abs() < df["atr14"] * 0.5) |
        ((c - fib_618).abs() < df["atr14"] * 0.5))
    thresh[near_fib] = thresh[near_fib] - 0.03

    # Momentum sanity — don't enter into freefall or melt-up
    roc10 = (c - c.shift(10)) / c.shift(10) * 100
    mom_ok_long = (df["rsi14"] > 25) & (roc10 > -15)
    mom_ok_short = (df["rsi14"] < 75) & (roc10 < 15)

    df["signal"] = 0
    long_cond = (composite > thresh) & (modules_long >= 2) & vol_ok & mom_ok_long
    short_cond = (composite < -thresh) & (modules_short >= 2) & vol_ok & mom_ok_short

    # Cooldown: at least 3 bars between signals to avoid overtrading
    long_trigger = long_cond & ~long_cond.shift(1).fillna(False)
    short_trigger = short_cond & ~short_cond.shift(1).fillna(False)

    # Apply cooldown
    var_last_signal_bar = pd.Series(-100, index=df.index, dtype=int)
    for i in range(len(df)):
        if i > 0:
            var_last_signal_bar.iloc[i] = var_last_signal_bar.iloc[i - 1]
        if long_trigger.iloc[i] and (i - var_last_signal_bar.iloc[i]) >= 5:
            df.iloc[i, df.columns.get_loc("signal")] = 1
            var_last_signal_bar.iloc[i] = i
        elif short_trigger.iloc[i] and (i - var_last_signal_bar.iloc[i]) >= 5:
            df.iloc[i, df.columns.get_loc("signal")] = -1
            var_last_signal_bar.iloc[i] = i

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# BACKTESTER ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def backtest(df, initial_capital=INITIAL_CAPITAL, commission=COMMISSION_PCT, position_pct=POSITION_SIZE_PCT,
             tp_mult=2.0, sl_mult=1.0, max_hold=25, grace_bars=3):
    """Backtest with TP/SL, equity curve filter, and grace period."""
    equity = initial_capital
    position = 0
    entry_price = 0.0
    entry_atr_pct = 1.0
    bars_held = 0
    equity_peak = initial_capital

    trades = []
    equity_curve = []

    for i in range(len(df)):
        row = df.iloc[i]
        price = row["Close"]
        high_price = row["High"]
        low_price = row["Low"]
        sig = row["signal"]
        atr_pct_val = row["atr_pct"] if not np.isnan(row["atr_pct"]) else 1.0

        tp_pct = max(2.0, min(entry_atr_pct * tp_mult, 12.0))
        sl_pct = max(0.8, min(entry_atr_pct * sl_mult, 5.0))

        if position != 0:
            bars_held += 1

            # Intrabar TP/SL check using High/Low
            if position == 1:
                pnl_high = (high_price / entry_price - 1) * 100
                pnl_low = (low_price / entry_price - 1) * 100
                hit_tp = pnl_high >= tp_pct
                hit_sl = pnl_low <= -sl_pct and bars_held >= grace_bars
            else:
                pnl_high = (1 - low_price / entry_price) * 100
                pnl_low = (1 - high_price / entry_price) * 100
                hit_tp = pnl_high >= tp_pct
                hit_sl = pnl_low <= -sl_pct and bars_held >= grace_bars

            pnl_pct = (price / entry_price - 1) * position * 100
            hit_timeout = bars_held >= max_hold

            if hit_tp or hit_sl or hit_timeout:
                if hit_tp:
                    final_pnl = tp_pct
                elif hit_sl:
                    final_pnl = -sl_pct
                else:
                    final_pnl = pnl_pct

                trade_pnl = equity * position_pct * (final_pnl / 100) - equity * position_pct * commission * 2
                equity += trade_pnl
                reason = "TP" if hit_tp else "SL" if hit_sl else "TIMEOUT"
                trades.append({
                    "entry_price": entry_price,
                    "exit_price": price,
                    "direction": "long" if position == 1 else "short",
                    "pnl_pct": final_pnl,
                    "pnl_usd": trade_pnl,
                    "bars_held": bars_held,
                    "exit_reason": reason,
                })
                position = 0
                bars_held = 0

        if position == 0 and sig != 0:
            size_mult = 1.0 if equity >= equity_peak * 0.95 else 0.5
            position = int(sig)
            entry_price = price
            entry_atr_pct = atr_pct_val
            equity -= equity * position_pct * size_mult * commission

        equity_peak = max(equity_peak, equity)
        equity_curve.append(equity)

    if position != 0 and len(df) > 0:
        price = df.iloc[-1]["Close"]
        pnl_pct = (price / entry_price - 1) * position * 100
        trade_pnl = equity * position_pct * (pnl_pct / 100)
        equity += trade_pnl
        trades.append({
            "entry_price": entry_price, "exit_price": price,
            "direction": "long" if position == 1 else "short",
            "pnl_pct": pnl_pct, "pnl_usd": trade_pnl,
            "bars_held": bars_held, "exit_reason": "EOD",
        })

    return trades, equity_curve, equity


# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE METRICS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_metrics(trades, equity_curve, initial_capital=INITIAL_CAPITAL):
    if not trades:
        return {
            "trades": 0, "win_rate": 0, "profit_factor": 0,
            "sharpe": 0, "max_dd": 0, "total_return": 0,
            "avg_win": 0, "avg_loss": 0, "best": 0, "worst": 0,
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.001

    eq = pd.Series(equity_curve)
    peak = eq.cummax()
    drawdown = (eq - peak) / peak * 100
    max_dd = drawdown.min() if len(drawdown) > 0 else 0

    returns = eq.pct_change().dropna()
    sharpe = (returns.mean() / returns.std() * np.sqrt(252 * 24)) if returns.std() > 0 and len(returns) > 1 else 0

    return {
        "trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "profit_factor": gross_profit / gross_loss,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "total_return": (equity_curve[-1] / initial_capital - 1) * 100 if equity_curve else 0,
        "avg_win": np.mean(wins) if wins else 0,
        "avg_loss": np.mean(losses) if losses else 0,
        "best": max(pnls) if pnls else 0,
        "worst": min(pnls) if pnls else 0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DATA DOWNLOAD + RESAMPLE
# ═══════════════════════════════════════════════════════════════════════════════

def download_data(symbol, tf_key, lookback_days=LOOKBACK_DAYS):
    end = datetime.now()
    start = end - timedelta(days=lookback_days)

    yf_interval = TIMEFRAMES[tf_key]

    if tf_key == "4H":
        max_days = min(lookback_days, 729)
        start = end - timedelta(days=max_days)
        data = yf.download(symbol, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
                           interval="1h", progress=False)
        if data.empty:
            return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.resample("4h").agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum"
        }).dropna()
    elif tf_key == "1H":
        max_days = min(lookback_days, 729)
        start = end - timedelta(days=max_days)
        data = yf.download(symbol, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
                           interval="1h", progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
    else:
        data = yf.download(symbol, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
                           interval=yf_interval, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

    return data.dropna()


# ═══════════════════════════════════════════════════════════════════════════════
# COMPARISON: BUY-AND-HOLD
# ═══════════════════════════════════════════════════════════════════════════════

def buy_and_hold_return(df, initial_capital=INITIAL_CAPITAL):
    if len(df) < 2:
        return 0
    return (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN: MATRIX RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_matrix():
    print("=" * 90)
    print("  SUPERIOR CRYPTO STRATEGY — NEXUS ALPHA BACKTESTER")
    print("  Multi-Pair × Multi-Timeframe Performance Matrix")
    print("=" * 90)
    print()

    results = []
    pairs_to_test = list(PAIRS.keys())[:6]
    tfs_to_test = list(TIMEFRAMES.keys())

    for pair_name in pairs_to_test:
        symbol = PAIRS[pair_name]
        for tf_key in tfs_to_test:
            print(f"  Testing {pair_name} on {tf_key}...", end=" ", flush=True)
            try:
                df = download_data(symbol, tf_key)
                if df.empty or len(df) < 200:
                    print("SKIP (insufficient data)")
                    continue

                df = compute_signals(df)

                # Timeframe-specific TP/SL: wider TP on higher TFs
                if tf_key == "1H":
                    tp_m, sl_m, mh = 1.8, 0.9, 20
                elif tf_key == "4H":
                    tp_m, sl_m, mh = 2.2, 1.0, 25
                else:
                    tp_m, sl_m, mh = 2.8, 1.0, 15

                trades, eq_curve, final_eq = backtest(df, tp_mult=tp_m, sl_mult=sl_m, max_hold=mh)
                metrics = calculate_metrics(trades, eq_curve)
                bnh = buy_and_hold_return(df)

                metrics["pair"] = pair_name
                metrics["timeframe"] = tf_key
                metrics["buy_hold"] = bnh
                metrics["alpha"] = metrics["total_return"] - bnh
                results.append(metrics)

                # Exit reason counts
                tp_count = sum(1 for t in trades if t["exit_reason"] == "TP")
                sl_count = sum(1 for t in trades if t["exit_reason"] == "SL")
                to_count = sum(1 for t in trades if t["exit_reason"] == "TIMEOUT")

                status = "PROFIT" if metrics["total_return"] > 0 else "LOSS"
                print(f"{status} | {metrics['trades']} trades (TP:{tp_count} SL:{sl_count} TO:{to_count}) | WR: {metrics['win_rate']:.1f}% | "
                      f"Return: {metrics['total_return']:.1f}% | BnH: {bnh:.1f}% | "
                      f"Alpha: {metrics['alpha']:.1f}%")

            except Exception as e:
                print(f"ERROR: {e}")
                continue

    if not results:
        print("\nNo results to display.")
        return

    # Summary table
    print()
    print("=" * 90)
    print("  PERFORMANCE SUMMARY")
    print("=" * 90)
    print()

    header = f"{'Pair':<8} {'TF':<5} {'Trades':<8} {'WR%':<8} {'PF':<8} {'Sharpe':<8} {'Return%':<10} {'MaxDD%':<9} {'BnH%':<9} {'Alpha%':<9}"
    print(header)
    print("-" * len(header))

    for r in results:
        print(f"{r['pair']:<8} {r['timeframe']:<5} {r['trades']:<8} "
              f"{r['win_rate']:<8.1f} {r['profit_factor']:<8.2f} {r['sharpe']:<8.2f} "
              f"{r['total_return']:<10.1f} {r['max_dd']:<9.1f} "
              f"{r['buy_hold']:<9.1f} {r['alpha']:<9.1f}")

    # Aggregate stats
    print()
    print("-" * len(header))
    avg_wr = np.mean([r["win_rate"] for r in results])
    avg_pf = np.mean([r["profit_factor"] for r in results if r["profit_factor"] > 0 and r["profit_factor"] < 1000])
    avg_sharpe = np.mean([r["sharpe"] for r in results])
    avg_return = np.mean([r["total_return"] for r in results])
    avg_dd = np.mean([r["max_dd"] for r in results])
    avg_alpha = np.mean([r["alpha"] for r in results])
    profitable = sum(1 for r in results if r["total_return"] > 0)
    print(f"{'AVG':<8} {'ALL':<5} {sum(r['trades'] for r in results):<8} "
          f"{avg_wr:<8.1f} {avg_pf:<8.2f} {avg_sharpe:<8.2f} "
          f"{avg_return:<10.1f} {avg_dd:<9.1f} {'—':<9} {avg_alpha:<9.1f}")
    print(f"\nProfitable: {profitable}/{len(results)} pair-timeframe combinations")
    print(f"Average alpha over buy-and-hold: {avg_alpha:.1f}%")

    # Per-timeframe summary
    print()
    print("Per-Timeframe Summary:")
    for tf in tfs_to_test:
        tf_results = [r for r in results if r["timeframe"] == tf and r["trades"] > 0]
        if tf_results:
            tf_wr = np.mean([r["win_rate"] for r in tf_results])
            tf_pf = np.mean([r["profit_factor"] for r in tf_results if r["profit_factor"] < 1000])
            tf_ret = np.mean([r["total_return"] for r in tf_results])
            tf_alpha = np.mean([r["alpha"] for r in tf_results])
            tf_profit = sum(1 for r in tf_results if r["total_return"] > 0)
            print(f"  {tf}: WR={tf_wr:.1f}%, PF={tf_pf:.2f}, Ret={tf_ret:.1f}%, Alpha={tf_alpha:.1f}%, "
                  f"Profitable={tf_profit}/{len(tf_results)}")
    print()


if __name__ == "__main__":
    run_matrix()
