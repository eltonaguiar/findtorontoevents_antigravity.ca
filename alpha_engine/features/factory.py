"""
Feature Factory - Orchestrator

Computes all 14 feature families and assembles them into a single feature matrix.
Each family is toggleable for ablation testing.
"""
import logging
from typing import Dict, List, Optional, Set

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureFactory:
    """
    Master feature factory that orchestrates all 14 factor families.
    
    Each family can be toggled on/off for ablation tests.
    Features are computed as cross-sectional (date x ticker) matrices.
    """

    def __init__(self, enabled_families: Optional[Dict[str, bool]] = None):
        from .. import config
        self.enabled = enabled_families or config.FEATURE_FAMILIES.copy()

    def compute_all(
        self,
        close: pd.DataFrame,
        high: pd.DataFrame = None,
        low: pd.DataFrame = None,
        volume: pd.DataFrame = None,
        fundamentals: pd.DataFrame = None,
        macro: pd.DataFrame = None,
        earnings_data: Dict = None,
        sentiment_data: pd.DataFrame = None,
        insider_data: pd.DataFrame = None,
    ) -> pd.DataFrame:
        """
        Compute all enabled feature families and combine into a single matrix.
        
        Args:
            close: Adjusted close prices (date x ticker)
            high: High prices (date x ticker)
            low: Low prices (date x ticker)
            volume: Volume (date x ticker)
            fundamentals: Key ratios DataFrame (ticker index)
            macro: Macro indicators DataFrame (date index)
            earnings_data: Earnings-related data dict
            sentiment_data: Sentiment scores DataFrame
            insider_data: Insider activity DataFrame
            
        Returns:
            MultiIndex DataFrame: (date, ticker) x features
        """
        all_features = {}

        if self.enabled.get("momentum"):
            logger.info("Computing momentum features...")
            from .momentum import compute_momentum_features
            all_features["mom"] = compute_momentum_features(close)

        if self.enabled.get("cross_sectional"):
            logger.info("Computing cross-sectional momentum features...")
            from .cross_sectional import compute_cross_sectional_features
            all_features["cs"] = compute_cross_sectional_features(close, volume)

        if self.enabled.get("volatility") and high is not None and low is not None:
            logger.info("Computing volatility features...")
            from .volatility import compute_volatility_features
            all_features["vol"] = compute_volatility_features(close, high, low)

        if self.enabled.get("volume") and volume is not None:
            logger.info("Computing volume features...")
            from .volume import compute_volume_features
            all_features["vlm"] = compute_volume_features(close, volume)

        if self.enabled.get("mean_reversion"):
            logger.info("Computing mean reversion features...")
            from .mean_reversion import compute_mean_reversion_features
            all_features["mr"] = compute_mean_reversion_features(close, high, low)

        if self.enabled.get("regime") and macro is not None:
            logger.info("Computing regime features...")
            from .regime import compute_regime_features
            all_features["reg"] = compute_regime_features(close, macro)

        if self.enabled.get("fundamental") and fundamentals is not None:
            logger.info("Computing fundamental features...")
            from .fundamental import compute_fundamental_features
            all_features["fund"] = compute_fundamental_features(close, fundamentals)

        if self.enabled.get("growth") and fundamentals is not None:
            logger.info("Computing growth features...")
            from .growth import compute_growth_features
            all_features["grw"] = compute_growth_features(fundamentals)

        if self.enabled.get("valuation") and fundamentals is not None:
            logger.info("Computing valuation features...")
            from .valuation import compute_valuation_features
            all_features["val"] = compute_valuation_features(close, fundamentals)

        if self.enabled.get("earnings") and earnings_data is not None:
            logger.info("Computing earnings features...")
            from .earnings_features import compute_earnings_features
            all_features["earn"] = compute_earnings_features(close, earnings_data)

        if self.enabled.get("seasonality"):
            logger.info("Computing seasonality features...")
            from .seasonality import compute_seasonality_features
            all_features["seas"] = compute_seasonality_features(close)

        if self.enabled.get("options"):
            logger.info("Computing options proxy features...")
            from .options_features import compute_options_features
            all_features["opt"] = compute_options_features(close, volume)

        if self.enabled.get("sentiment") and sentiment_data is not None:
            logger.info("Computing sentiment features...")
            from .sentiment_features import compute_sentiment_features
            all_features["sent"] = compute_sentiment_features(close, volume, sentiment_data)

        if self.enabled.get("flow") and volume is not None:
            logger.info("Computing flow features...")
            from .flow import compute_flow_features
            all_features["flow"] = compute_flow_features(close, volume)

        # Combine all feature families
        combined = self._combine_features(all_features)
        logger.info(f"Feature matrix: {combined.shape[0]} rows x {combined.shape[1]} columns")
        return combined

    def _combine_features(self, feature_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Combine feature DataFrames, handling different index types."""
        if not feature_dict:
            return pd.DataFrame()

        frames = []
        for prefix, df in feature_dict.items():
            if df is None or df.empty:
                continue
            # Prefix column names with family tag
            df = df.copy()
            df.columns = [f"{prefix}_{c}" for c in df.columns]
            frames.append(df)

        if not frames:
            return pd.DataFrame()

        # Join all frames on their index
        result = frames[0]
        for f in frames[1:]:
            result = result.join(f, how="outer")

        return result

    def get_feature_names(self) -> List[str]:
        """Get list of all feature names that would be computed."""
        names = []
        family_sizes = {
            "momentum": 30, "cross_sectional": 15, "volatility": 20,
            "volume": 15, "mean_reversion": 15, "regime": 10,
            "fundamental": 20, "growth": 10, "valuation": 12,
            "earnings": 12, "seasonality": 10, "options": 8,
            "sentiment": 8, "flow": 10,
        }
        for family, enabled in self.enabled.items():
            if enabled:
                names.append(f"[{family}: ~{family_sizes.get(family, 10)} features]")
        return names

    def ablation_test(
        self,
        close: pd.DataFrame,
        **kwargs,
    ) -> Dict[str, pd.DataFrame]:
        """
        Run ablation: compute features with each family disabled one at a time.
        Returns dict of family_name -> feature_matrix_without_that_family.
        """
        results = {}
        for family in self.enabled:
            if not self.enabled[family]:
                continue
            # Disable one family
            test_enabled = self.enabled.copy()
            test_enabled[family] = False
            factory = FeatureFactory(enabled_families=test_enabled)
            results[f"without_{family}"] = factory.compute_all(close, **kwargs)
        return results
