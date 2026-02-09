"""
Feature Family 3: Volatility / Risk

Realized vol, ATR, beta, downside vol, drawdown depth, kurtosis.
Essential for risk management and volatility-targeting strategies.
"""
import numpy as np
import pandas as pd


def compute_volatility_features(
    close: pd.DataFrame,
    high: pd.DataFrame = None,
    low: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Compute volatility and risk features.
    
    Features (stacked format):
    - Realized volatility (multiple windows)
    - ATR (Average True Range)
    - Beta vs market
    - Downside volatility
    - Max drawdown (rolling)
    - Kurtosis (tail risk)
    - Volatility of volatility
    - Intraday range
    - Parkinson volatility
    """
    features = {}
    returns = close.pct_change()

    # ── Realized Volatility ───────────────────────────────────────────────
    for w in [5, 10, 21, 63, 126]:
        rvol = returns.rolling(w).std() * np.sqrt(252)  # Annualized
        features[f"rvol_{w}d"] = rvol.stack()

    # ── Volatility Ratio (short vs long term) ─────────────────────────────
    rvol_21 = returns.rolling(21).std()
    rvol_63 = returns.rolling(63).std()
    rvol_ratio = rvol_21 / rvol_63.replace(0, np.nan)
    features["vol_ratio_21_63"] = rvol_ratio.stack()

    # ── Volatility Z-Score ────────────────────────────────────────────────
    vol_zscore = (rvol_21 - rvol_21.rolling(252).mean()) / rvol_21.rolling(252).std()
    features["vol_zscore"] = vol_zscore.stack()

    # ── ATR (Average True Range) ──────────────────────────────────────────
    if high is not None and low is not None:
        for w in [14, 21]:
            atr = _compute_atr(close, high, low, w)
            atr_pct = atr / close  # Normalize as % of price
            features[f"atr_{w}d_pct"] = atr_pct.stack()

    # ── Intraday Range ────────────────────────────────────────────────────
    if high is not None and low is not None:
        intraday_range = (high - low) / close
        features["intraday_range"] = intraday_range.stack()
        features["intraday_range_avg_20"] = intraday_range.rolling(20).mean().stack()

    # ── Parkinson Volatility (more efficient estimator) ───────────────────
    if high is not None and low is not None:
        log_hl = np.log(high / low)
        parkinson = np.sqrt((1 / (4 * np.log(2))) * (log_hl ** 2).rolling(21).mean()) * np.sqrt(252)
        features["parkinson_vol"] = parkinson.stack()

    # ── Beta vs Market ────────────────────────────────────────────────────
    market_ret = returns.mean(axis=1)  # Equal-weight market proxy
    for w in [63, 252]:
        betas = pd.DataFrame(index=close.index, columns=close.columns, dtype=float)
        for ticker in close.columns:
            rolling_cov = returns[ticker].rolling(w).cov(market_ret)
            rolling_var = market_ret.rolling(w).var()
            betas[ticker] = rolling_cov / rolling_var.replace(0, np.nan)
        features[f"beta_{w}d"] = betas.stack()

    # ── Downside Volatility ───────────────────────────────────────────────
    downside_ret = returns.clip(upper=0)
    for w in [21, 63]:
        downside_vol = downside_ret.rolling(w).std() * np.sqrt(252)
        features[f"downside_vol_{w}d"] = downside_vol.stack()

    # ── Upside/Downside Capture ───────────────────────────────────────────
    up_days = (market_ret > 0)
    down_days = (market_ret <= 0)
    for w in [63]:
        up_capture = pd.DataFrame(index=close.index, columns=close.columns, dtype=float)
        down_capture = pd.DataFrame(index=close.index, columns=close.columns, dtype=float)
        for ticker in close.columns:
            stock_up = returns[ticker].where(up_days).rolling(w).mean()
            market_up = market_ret.where(up_days).rolling(w).mean()
            up_capture[ticker] = stock_up / market_up.replace(0, np.nan)

            stock_down = returns[ticker].where(down_days).rolling(w).mean()
            market_down = market_ret.where(down_days).rolling(w).mean()
            down_capture[ticker] = stock_down / market_down.replace(0, np.nan)

        features[f"up_capture_{w}d"] = up_capture.stack()
        features[f"down_capture_{w}d"] = down_capture.stack()

    # ── Rolling Max Drawdown ──────────────────────────────────────────────
    for w in [63, 126, 252]:
        drawdown = _rolling_max_drawdown(close, w)
        features[f"max_dd_{w}d"] = drawdown.stack()

    # ── Kurtosis (tail risk) ──────────────────────────────────────────────
    for w in [63, 252]:
        kurt = returns.rolling(w).kurt()
        features[f"kurtosis_{w}d"] = kurt.stack()

    # ── Skewness ──────────────────────────────────────────────────────────
    for w in [63, 252]:
        skew = returns.rolling(w).skew()
        features[f"skewness_{w}d"] = skew.stack()

    # ── Volatility of Volatility ──────────────────────────────────────────
    vol_21 = returns.rolling(21).std()
    vol_of_vol = vol_21.rolling(63).std() / vol_21.rolling(63).mean().replace(0, np.nan)
    features["vol_of_vol"] = vol_of_vol.stack()

    result = pd.DataFrame(features)
    result.index.names = ["date", "ticker"]
    return result


def _compute_atr(close: pd.DataFrame, high: pd.DataFrame, low: pd.DataFrame, window: int) -> pd.DataFrame:
    """Compute Average True Range."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1) if len(close.columns) == 1 else \
        pd.DataFrame({t: pd.concat([tr1[t], tr2[t], tr3[t]], axis=1).max(axis=1) for t in close.columns})
    return true_range.rolling(window).mean()


def _rolling_max_drawdown(close: pd.DataFrame, window: int) -> pd.DataFrame:
    """Compute rolling maximum drawdown."""
    rolling_max = close.rolling(window, min_periods=1).max()
    drawdown = (close - rolling_max) / rolling_max
    return drawdown
