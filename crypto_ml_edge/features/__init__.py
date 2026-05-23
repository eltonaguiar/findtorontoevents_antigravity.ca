"""
Feature Engine — crypto_ml_edge.features
==========================================
Single source of truth for ML features.

Usage:
    from crypto_ml_edge.features import build_features

    features_df = build_features(ohlcv_df)
    features_df = build_features(ohlcv_df, funding_df=funding_df)

Standalone fracdiff usage:
    from crypto_ml_edge.features.fracdiff import frac_diff_ffd, add_fracdiff_features

    ffd_series = frac_diff_ffd(df['close'], d=0.4)
    df = add_fracdiff_features(df, 'close', d=0.4)

Guarantees:
- Exactly 17 features (within FEAT-06 budget of 10-20)
- No lookahead: all features at bar T use only data available at close of bar T
- No raw prices: all features are returns, ratios, z-scores, or bounded oscillators
- Training and inference use the identical code path (FEAT-07)
"""

from crypto_ml_edge.features.engine import build_features, FEATURE_NAMES, WARMUP_BARS
from crypto_ml_edge.features.fracdiff import frac_diff_ffd, add_fracdiff_features

__all__ = [
    "build_features",
    "FEATURE_NAMES",
    "WARMUP_BARS",
    "frac_diff_ffd",
    "add_fracdiff_features",
]
