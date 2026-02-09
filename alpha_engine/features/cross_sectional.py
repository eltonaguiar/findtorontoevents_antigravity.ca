"""
Feature Family 2: Cross-Sectional Momentum

Rank returns vs universe, industry-relative strength.
Instead of "if RSI < 30 buy", rank the entire universe by composite factors
and pick top-K. Cross-sectional approaches generalize better.
"""
import numpy as np
import pandas as pd


def compute_cross_sectional_features(
    close: pd.DataFrame,
    volume: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Compute cross-sectional (relative) features.
    
    For each date, ranks each stock vs the universe.
    Features are in stacked (date, ticker) format.
    
    Features:
    - Return rank (percentile) at multiple horizons
    - Industry-relative strength
    - Return spread (stock return - universe median)
    - Momentum rank acceleration
    - Volume-weighted momentum rank
    """
    features = {}

    # ── Return Percentile Ranks ───────────────────────────────────────────
    for w in [5, 10, 21, 63, 126, 252]:
        ret = close.pct_change(w)
        # Cross-sectional rank (0 = worst, 1 = best)
        rank = ret.rank(axis=1, pct=True)
        features[f"cs_rank_{w}d"] = rank.stack()

    # ── Return Spread vs Universe ─────────────────────────────────────────
    for w in [21, 63]:
        ret = close.pct_change(w)
        median_ret = ret.median(axis=1)
        spread = ret.sub(median_ret, axis=0)
        features[f"cs_spread_{w}d"] = spread.stack()

    # ── Z-Score vs Universe ───────────────────────────────────────────────
    for w in [21, 63]:
        ret = close.pct_change(w)
        cs_mean = ret.mean(axis=1)
        cs_std = ret.std(axis=1)
        zscore = ret.sub(cs_mean, axis=0).div(cs_std.replace(0, np.nan), axis=0)
        features[f"cs_zscore_{w}d"] = zscore.stack()

    # ── Momentum Rank Change (acceleration of relative strength) ──────────
    for w in [21, 63]:
        ret = close.pct_change(w)
        rank = ret.rank(axis=1, pct=True)
        rank_change = rank - rank.shift(w)
        features[f"cs_rank_change_{w}d"] = rank_change.stack()

    # ── Residual Momentum (Fama-French residual proxy) ────────────────────
    # Remove market component: stock_ret - beta * market_ret
    market_ret = close.pct_change(21).mean(axis=1)  # Equal-weight market proxy
    stock_ret = close.pct_change(21)
    # Simple beta approximation
    for ticker in close.columns:
        if ticker not in stock_ret.columns:
            continue
        rolling_cov = stock_ret[ticker].rolling(252).cov(market_ret)
        rolling_var = market_ret.rolling(252).var()
        beta = rolling_cov / rolling_var.replace(0, np.nan)
        residual = stock_ret[ticker] - beta * market_ret
        features[f"cs_residual_mom_{ticker}"] = residual

    # Flatten residual momentum to stacked format
    residual_df = pd.DataFrame({k: v for k, v in features.items() if "residual" in k})
    # Remove individual ticker residual columns, will add the ranked version
    features = {k: v for k, v in features.items() if "residual" not in k}

    if not residual_df.empty:
        # Stack properly - these are already Series indexed by date
        # Re-create as wide DataFrame and stack
        residual_wide = pd.DataFrame(index=close.index)
        for k, v in list(features.items()):
            if "residual" in k:
                del features[k]
        for ticker in close.columns:
            col = f"cs_residual_mom_{ticker}"
            if col in residual_df.columns:
                residual_wide[ticker] = residual_df[col]

        if not residual_wide.empty:
            res_rank = residual_wide.rank(axis=1, pct=True)
            features["cs_residual_rank"] = res_rank.stack()

    # ── Volume-Adjusted Momentum ──────────────────────────────────────────
    if volume is not None:
        ret_21 = close.pct_change(21)
        vol_ratio = volume / volume.rolling(20).mean()
        vol_adj_mom = ret_21 * vol_ratio
        vol_adj_rank = vol_adj_mom.rank(axis=1, pct=True)
        features["cs_vol_adj_rank"] = vol_adj_rank.stack()

    # ── Sector-Relative Strength (proxy using return dispersion) ──────────
    ret_21 = close.pct_change(21)
    sector_median = ret_21.median(axis=1)
    sector_rel = ret_21.sub(sector_median, axis=0)
    sector_rel_rank = sector_rel.rank(axis=1, pct=True)
    features["cs_sector_rel_rank"] = sector_rel_rank.stack()

    result = pd.DataFrame(features)
    if isinstance(result.index, pd.MultiIndex):
        result.index.names = ["date", "ticker"]
    return result
