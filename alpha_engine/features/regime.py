"""
Feature Family 6: Regime

Volatility regime, correlation regime, rate regime, trend regime.
Most systems fail here — they don't adapt to changing market conditions.
"""
import numpy as np
import pandas as pd


def compute_regime_features(
    close: pd.DataFrame,
    macro: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute regime-aware features.
    
    Features (stacked):
    - Volatility regime indicators
    - Correlation regime
    - Rate regime
    - Trend regime
    - Cross-asset regime signals
    - Regime transition indicators
    """
    features = {}
    returns = close.pct_change()

    # ── Volatility Regime ─────────────────────────────────────────────────
    if "VIX" in macro.columns:
        vix = macro["VIX"].reindex(close.index, method="ffill")
        for ticker in close.columns:
            features[f"vix_level_{ticker}"] = vix

        # VIX percentile over 1 year
        vix_pct = vix.rolling(252).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
        for ticker in close.columns:
            features[f"vix_percentile_{ticker}"] = vix_pct

        # VIX term structure slope proxy (change in VIX)
        vix_slope = vix.diff(5) / vix.shift(5)
        for ticker in close.columns:
            features[f"vix_slope_{ticker}"] = vix_slope

    # Realized vol regime (market-wide)
    market_ret = returns.mean(axis=1)
    realized_vol = market_ret.rolling(21).std() * np.sqrt(252)
    vol_regime_score = (realized_vol - realized_vol.rolling(252).mean()) / realized_vol.rolling(252).std().replace(0, np.nan)
    for ticker in close.columns:
        features[f"vol_regime_{ticker}"] = vol_regime_score

    # ── Correlation Regime ────────────────────────────────────────────────
    # When correlations spike, diversification fails → risk-off signal
    rolling_corr_avg = _rolling_avg_correlation(returns, window=63)
    for ticker in close.columns:
        features[f"corr_regime_{ticker}"] = rolling_corr_avg

    # Correlation percentile
    corr_pct = rolling_corr_avg.rolling(252).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
    )
    for ticker in close.columns:
        features[f"corr_percentile_{ticker}"] = corr_pct

    # ── Rate Regime ───────────────────────────────────────────────────────
    if "TNX" in macro.columns:
        tnx = macro["TNX"].reindex(close.index, method="ffill")
        tnx_change = tnx.diff(21)
        tnx_sma50 = tnx.rolling(50).mean()
        tnx_dist = (tnx - tnx_sma50) / tnx_sma50

        for ticker in close.columns:
            features[f"rate_level_{ticker}"] = tnx
            features[f"rate_change_21d_{ticker}"] = tnx_change
            features[f"rate_dist_sma50_{ticker}"] = tnx_dist

    # ── Dollar Regime (DXY) ───────────────────────────────────────────────
    if "DXY" in macro.columns:
        dxy = macro["DXY"].reindex(close.index, method="ffill")
        dxy_sma50 = dxy.rolling(50).mean()
        dxy_dist = (dxy - dxy_sma50) / dxy_sma50

        for ticker in close.columns:
            features[f"dxy_dist_{ticker}"] = dxy_dist
            # Strong dollar = bad for tech/growth, good for value
            features[f"dxy_strong_{ticker}"] = (dxy_dist > 0.02).astype(float)

    # ── Trend Regime (market-level) ───────────────────────────────────────
    if "SPY" in macro.columns:
        spy = macro["SPY"].reindex(close.index, method="ffill")
        spy_sma50 = spy.rolling(50).mean()
        spy_sma200 = spy.rolling(200).mean()

        trend_score = pd.Series(0.0, index=close.index)
        trend_score += (spy > spy_sma50).astype(float)
        trend_score += (spy > spy_sma200).astype(float)
        trend_score += (spy_sma50 > spy_sma200).astype(float)
        trend_score = trend_score / 3.0  # Normalize to [0, 1]

        for ticker in close.columns:
            features[f"market_trend_{ticker}"] = trend_score

    # ── Regime Transition Detection ───────────────────────────────────────
    # Detect when regime is changing (increased uncertainty)
    if "VIX" in macro.columns:
        vix = macro["VIX"].reindex(close.index, method="ffill")
        vix_accel = vix.diff().diff()  # Second derivative
        for ticker in close.columns:
            features[f"regime_transition_{ticker}"] = vix_accel.abs()

    # Convert to stacked format
    feature_df = pd.DataFrame(features, index=close.index)

    # Reshape: group by ticker
    stacked_features = {}
    base_feature_names = set()
    for col in feature_df.columns:
        # Extract feature name and ticker
        parts = col.rsplit("_", 1)
        if len(parts) == 2 and parts[1] in close.columns:
            base_feature_names.add(parts[0])

    if base_feature_names:
        stacked_dict = {}
        for feat_name in base_feature_names:
            wide = pd.DataFrame(index=close.index)
            for ticker in close.columns:
                col = f"{feat_name}_{ticker}"
                if col in feature_df.columns:
                    wide[ticker] = feature_df[col]
            stacked_dict[feat_name] = wide.stack()

        result = pd.DataFrame(stacked_dict)
        result.index.names = ["date", "ticker"]
        return result

    return pd.DataFrame()


def _rolling_avg_correlation(returns: pd.DataFrame, window: int = 63) -> pd.Series:
    """
    Compute rolling average pairwise correlation.
    High average correlation = high systemic risk.
    """
    n_stocks = min(returns.shape[1], 20)  # Limit for speed
    subset = returns.iloc[:, :n_stocks]

    avg_corrs = []
    for i in range(len(returns)):
        if i < window:
            avg_corrs.append(np.nan)
            continue
        window_data = subset.iloc[i - window:i]
        corr_matrix = window_data.corr()
        # Average of upper triangle (exclude diagonal)
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
        avg_corr = corr_matrix.values[mask].mean()
        avg_corrs.append(avg_corr)

    return pd.Series(avg_corrs, index=returns.index, name="avg_correlation")
