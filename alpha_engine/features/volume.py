"""
Feature Family 4: Volume / Liquidity

Dollar volume, volume shocks, illiquidity (Amihud), spread proxy.
Critical for ensuring we only trade names with sufficient capacity.
"""
import numpy as np
import pandas as pd


def compute_volume_features(
    close: pd.DataFrame,
    volume: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute volume and liquidity features.
    
    Features (stacked format):
    - Dollar volume and its rank
    - Volume ratio (vs moving average)
    - Volume shock (sudden spike)
    - Amihud illiquidity ratio
    - VWAP distance proxy
    - On-Balance Volume (OBV) trend
    - Volume-price divergence
    - Turnover rate proxy
    """
    features = {}
    returns = close.pct_change()
    dollar_volume = close * volume

    # ── Dollar Volume ─────────────────────────────────────────────────────
    for w in [5, 20]:
        avg_dvol = dollar_volume.rolling(w).mean()
        features[f"dollar_vol_{w}d"] = np.log1p(avg_dvol).stack()

    # ── Dollar Volume Rank (cross-sectional) ──────────────────────────────
    dvol_20 = dollar_volume.rolling(20).mean()
    features["dollar_vol_rank"] = dvol_20.rank(axis=1, pct=True).stack()

    # ── Volume Ratio (current vs average) ─────────────────────────────────
    for w in [5, 20, 50]:
        vol_avg = volume.rolling(w).mean()
        vol_ratio = volume / vol_avg.replace(0, np.nan)
        features[f"vol_ratio_{w}d"] = vol_ratio.stack()

    # ── Volume Shock (z-score of volume) ──────────────────────────────────
    vol_mean = volume.rolling(50).mean()
    vol_std = volume.rolling(50).std()
    vol_zscore = (volume - vol_mean) / vol_std.replace(0, np.nan)
    features["vol_shock"] = vol_zscore.stack()

    # ── Amihud Illiquidity Ratio ──────────────────────────────────────────
    # Higher = more illiquid = harder to trade
    abs_ret = returns.abs()
    amihud_daily = abs_ret / dollar_volume.replace(0, np.nan)
    for w in [21, 63]:
        features[f"amihud_{w}d"] = amihud_daily.rolling(w).mean().stack()

    # ── Spread Proxy (high-low range / close) ─────────────────────────────
    # Without tick data, we approximate spread from price range
    # Lower liquidity stocks tend to have wider ranges
    # (This is a rough proxy; real spread data is better)

    # ── On-Balance Volume (OBV) Trend ─────────────────────────────────────
    obv = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    for ticker in close.columns:
        sign = np.sign(returns[ticker]).fillna(0)
        obv[ticker] = (sign * volume[ticker]).cumsum()

    # OBV trend (slope of OBV normalized)
    for w in [10, 20]:
        obv_ma = obv.rolling(w).mean()
        obv_slope = obv_ma.pct_change(5)
        features[f"obv_slope_{w}d"] = obv_slope.stack()

    # ── Volume-Price Divergence ───────────────────────────────────────────
    # Price up + volume down = weak rally
    # Price down + volume up = panic selling
    price_dir = np.sign(returns.rolling(5).mean())
    vol_dir = np.sign(volume.rolling(5).mean() - volume.rolling(20).mean())
    divergence = price_dir * vol_dir  # -1 = divergence, +1 = confirmation
    features["vol_price_div"] = divergence.stack()

    # ── Accumulation/Distribution Proxy ───────────────────────────────────
    # CLV (Close Location Value) * Volume
    # If we have high/low, use (close-low - (high-close)) / (high-low) * volume
    # Otherwise, use return sign * volume as proxy
    for w in [10, 20]:
        ad = (returns.clip(-0.1, 0.1) * volume).rolling(w).sum()
        ad_norm = ad / dollar_volume.rolling(w).sum().replace(0, np.nan)
        features[f"acc_dist_{w}d"] = ad_norm.stack()

    # ── Relative Volume (vs sector) ───────────────────────────────────────
    universe_avg_vol = volume.mean(axis=1)
    rel_vol = volume.div(universe_avg_vol, axis=0)
    features["rel_volume"] = rel_vol.stack()

    result = pd.DataFrame(features)
    result.index.names = ["date", "ticker"]
    return result
