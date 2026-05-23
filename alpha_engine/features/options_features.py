"""
Feature Family 12: Options / Positioning

IV rank, skew, gamma exposure proxies, unusual options volume.
When premium options data is unavailable, we compute proxies from price/volume.
"""
import numpy as np
import pandas as pd


def compute_options_features(
    close: pd.DataFrame,
    volume: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Compute options-derived and positioning features.
    
    Without live options chain data, we compute proxies:
    - IV rank proxy (from realized vol percentile)
    - Implied vol premium proxy
    - Put/call ratio proxies from volume patterns
    - Unusual volume as options activity proxy
    - Gamma squeeze risk proxy
    
    With options data available (future plug-in):
    - IV rank from actual IV
    - Put/call ratio
    - Skew (OTM put vol vs ATM vol)
    - Gamma exposure
    """
    features = {}
    returns = close.pct_change()

    # ── IV Rank Proxy (realized vol percentile) ───────────────────────────
    # IV rank = current IV percentile over past year
    # Proxy: use realized vol percentile as stand-in
    rvol_21 = returns.rolling(21).std() * np.sqrt(252)
    for w in [252]:
        iv_rank_proxy = rvol_21.rolling(w).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x.dropna()) > 20 else np.nan,
            raw=False,
        )
        features[f"iv_rank_proxy"] = iv_rank_proxy.stack()

    # ── Implied Vol Premium Proxy ─────────────────────────────────────────
    # IV typically trades above realized vol. When gap is large → expensive options
    # Proxy: compare short-term vol to long-term vol
    rvol_5 = returns.rolling(5).std() * np.sqrt(252)
    rvol_63 = returns.rolling(63).std() * np.sqrt(252)
    iv_premium_proxy = rvol_5 / rvol_63.replace(0, np.nan) - 1
    features["iv_premium_proxy"] = iv_premium_proxy.stack()

    # ── Vol Term Structure Proxy ──────────────────────────────────────────
    # Contango (short vol < long vol) vs backwardation
    vol_term = rvol_21 / rvol_63.replace(0, np.nan)
    features["vol_term_structure"] = vol_term.stack()
    features["vol_backwardation"] = (vol_term > 1.0).astype(float).stack()

    # ── Unusual Volume as Options Activity Proxy ──────────────────────────
    if volume is not None:
        vol_avg_20 = volume.rolling(20).mean()
        vol_ratio = volume / vol_avg_20.replace(0, np.nan)
        unusual = (vol_ratio > 2.0).astype(float)  # 2x average = unusual
        features["unusual_volume"] = unusual.stack()
        features["volume_ratio"] = vol_ratio.stack()

        # Unusual volume + positive return = bullish call activity proxy
        unusual_bull = unusual * (returns > 0).astype(float)
        unusual_bear = unusual * (returns < 0).astype(float)
        features["unusual_vol_bull"] = unusual_bull.stack()
        features["unusual_vol_bear"] = unusual_bear.stack()

    # ── Gamma Squeeze Risk Proxy ──────────────────────────────────────────
    # High volume + rapid price increase + low float = gamma squeeze risk
    if volume is not None:
        ret_5 = close.pct_change(5)
        vol_surge = volume / volume.rolling(20).mean().replace(0, np.nan)
        # Gamma risk = rapid move up + high volume
        gamma_proxy = ret_5.clip(0, None) * vol_surge
        features["gamma_squeeze_proxy"] = gamma_proxy.stack()

    # ── Volatility Smile Proxy ────────────────────────────────────────────
    # Skew proxy: asymmetry in returns (left tail heavier = more put demand)
    skew_20 = returns.rolling(20).skew()
    features["return_skew_20d"] = skew_20.stack()

    # Negative skew = heavier left tail = more put protection buying
    features["put_demand_proxy"] = (-skew_20).clip(0, None).stack()

    result = pd.DataFrame(features)
    result.index.names = ["date", "ticker"]
    return result
