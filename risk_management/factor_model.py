"""
Macro Factor Model with Ridge Regression + Kalman Filter
========================================================
Implements a cross-asset macro-alpha strategy:
1. Ridge regression on macro factors to predict returns
2. Kalman filter for adaptive coefficient updating
3. Residual alpha extraction for long-short basket construction
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import joblib

from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

try:
    from pykalman import KalmanFilter
    KALMAN_AVAILABLE = True
except ImportError:
    KALMAN_AVAILABLE = False
    logging.warning("pykalman not available, using simplified update")

try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class FactorExposure:
    """Container for factor exposure results."""
    symbol: str
    predicted_return: float
    actual_return: float
    residual_alpha: float
    factor_betas: Dict[str, float]
    r_squared: float
    timestamp: datetime


@dataclass
class LongShortBasket:
    """Container for long-short portfolio."""
    longs: List[Tuple[str, float]]  # (symbol, weight)
    shorts: List[Tuple[str, float]]
    neutralization: str  # 'market', 'dollar', 'beta'
    target_volatility: float
    expected_return: float
    timestamp: datetime


class MacroFactorModel:
    """
    Ridge regression + Kalman filter factor model.
    
    Factors:
        - btc_dominance: Bitcoin market cap dominance
        - total_market_cap: Total crypto market capitalization
        - defi_tvl: Total value locked in DeFi
        - google_trends: Search interest for crypto terms
        - active_addresses: On-chain activity
        - fear_greed: Fear & Greed index
    """
    
    DEFAULT_FACTORS = [
        'btc_dominance',
        'total_market_cap_usd',
        'defi_tvl',
        'market_cap_change_24h',
        'fear_greed_index'
    ]
    
    def __init__(
        self,
        alpha: float = 1.0,  # Ridge regularization
        kalman_observation_cov: float = 0.1,
        kalman_transition_cov: float = 0.01,
        lookback_window: int = 720  # 30 days of hourly data
    ):
        self.alpha = alpha
        self.kalman_obs_cov = kalman_observation_cov
        self.kalman_trans_cov = kalman_transition_cov
        self.lookback_window = lookback_window
        
        self.ridge: Optional[Ridge] = None
        self.scaler = StandardScaler()
        self.kalman: Optional[KalmanFilter] = None
        self.coefficients: Optional[np.ndarray] = None
        self.factor_names: List[str] = []
        self._is_fitted = False
    
    def _prepare_features(
        self,
        macro_df: pd.DataFrame,
        factor_cols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Prepare and normalize macro features.
        """
        if factor_cols is None:
            factor_cols = [c for c in self.DEFAULT_FACTORS if c in macro_df.columns]
        
        self.factor_names = factor_cols
        
        features = macro_df[factor_cols].copy()
        
        # Forward fill missing values
        features = features.fillna(method='ffill')
        
        # Log transform for market cap (non-stationary)
        if 'total_market_cap_usd' in features.columns:
            features['total_market_cap_usd'] = np.log(features['total_market_cap_usd'])
        
        if 'defi_tvl' in features.columns:
            features['defi_tvl'] = np.log1p(features['defi_tvl'])
        
        # Normalize to z-scores (rolling)
        for col in features.columns:
            roll_mean = features[col].rolling(168).mean()  # 1 week for hourly
            roll_std = features[col].rolling(168).std()
            features[col] = (features[col] - roll_mean) / (roll_std + 1e-10)
        
        return features.dropna()
    
    def fit_initial(
        self,
        macro_df: pd.DataFrame,
        returns_df: pd.DataFrame,
        factor_cols: Optional[List[str]] = None
    ):
        """
        Fit initial Ridge regression on historical data.
        
        Args:
            macro_df: Macro factors DataFrame (hourly index)
            returns_df: Asset returns DataFrame (same index as macro_df)
            factor_cols: Specific factor columns to use
        """
        X = self._prepare_features(macro_df, factor_cols)
        
        # Align with returns
        aligned_returns = returns_df.reindex(X.index)
        
        # Store feature means/stds for prediction
        self.feature_means = X.mean()
        self.feature_stds = X.std()
        
        # Fit Ridge for each asset
        self.ridge_models = {}
        self.asset_r_squared = {}
        
        for symbol in returns_df.columns:
            y = aligned_returns[symbol].dropna()
            X_aligned = X.loc[y.index]
            
            if len(y) < 100:
                continue
            
            # Fit Ridge
            model = Ridge(alpha=self.alpha, fit_intercept=True)
            model.fit(X_aligned, y)
            
            # Compute R-squared
            y_pred = model.predict(X_aligned)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            self.ridge_models[symbol] = model
            self.asset_r_squared[symbol] = r2
        
        # Initialize Kalman filter for coefficient tracking
        if KALMAN_AVAILABLE:
            n_factors = len(self.factor_names)
            
            self.kalman = KalmanFilter(
                n_dim_obs=1,
                n_dim_state=n_factors,
                transition_matrices=np.eye(n_factors),
                observation_matrices=np.zeros((1, n_factors)),  # Will set dynamically
                initial_state_mean=np.zeros(n_factors),
                initial_state_covariance=np.eye(n_factors) * 0.1,
                observation_covariance=self.kalman_obs_cov,
                transition_covariance=np.eye(n_factors) * self.kalman_trans_cov
            )
        
        self._is_fitted = True
        logger.info(
            f"Factor model fitted on {len(X)} samples, "
            f"{len(self.ridge_models)} assets, factors: {self.factor_names}"
        )
    
    def update(
        self,
        macro_df: pd.DataFrame,
        returns_df: pd.DataFrame
    ):
        """
        Update model with new observations using Kalman filter.
        """
        if not self._is_fitted:
            raise RuntimeError("Model not fitted. Call fit_initial() first.")
        
        X = self._prepare_features(macro_df)
        X_aligned = X.values
        
        # Update each asset's coefficients via Kalman filter
        for symbol, model in self.ridge_models.items():
            y = returns_df[symbol].reindex(X.index).values
            
            # Skip if too many NaNs
            valid_mask = ~np.isnan(y)
            if valid_mask.sum() < 10:
                continue
            
            X_valid = X_aligned[valid_mask]
            y_valid = y[valid_mask]
            
            if KALMAN_AVAILABLE and self.kalman is not None:
                # Kalman update
                current_coef = model.coef_
                
                for xi, yi in zip(X_valid, y_valid):
                    # Observation matrix is the feature vector
                    observation_matrix = xi.reshape(1, -1)
                    
                    # Update
                    filtered_state, _ = self.kalman.filter_update(
                        filtered_state_mean=current_coef,
                        filtered_state_covariance=np.eye(len(current_coef)) * 0.01,
                        observation=yi,
                        observation_matrix=observation_matrix
                    )
                    current_coef = filtered_state
                
                # Update model coefficients
                model.coef_ = current_coef
            else:
                # Fallback: Exponential weighted update
                # Blend old coefficients with new ridge fit
                if len(X_valid) >= 24:
                    new_model = Ridge(alpha=self.alpha)
                    new_model.fit(X_valid, y_valid)
                    
                    # Blend coefficients (70% new, 30% old)
                    model.coef_ = 0.7 * new_model.coef_ + 0.3 * model.coef_
                    model.intercept_ = 0.7 * new_model.intercept_ + 0.3 * model.intercept_
    
    def predict(
        self,
        macro_df: pd.DataFrame,
        symbol: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Predict returns for all assets or specific symbol.
        """
        if not self._is_fitted:
            raise RuntimeError("Model not fitted")
        
        X = self._prepare_features(macro_df)
        
        if X.empty:
            return {}
        
        latest_features = X.iloc[-1:].values
        
        predictions = {}
        assets = [symbol] if symbol else list(self.ridge_models.keys())
        
        for sym in assets:
            if sym not in self.ridge_models:
                continue
            
            model = self.ridge_models[sym]
            pred = model.predict(latest_features)[0]
            predictions[sym] = pred
        
        return predictions
    
    def compute_residual_alpha(
        self,
        macro_df: pd.DataFrame,
        returns_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compute residual alpha (actual - predicted) for all assets.
        
        Returns DataFrame with columns:
            - actual_return
            - predicted_return
            - residual_alpha
            - abs_alpha
        """
        X = self._prepare_features(macro_df)
        
        results = []
        for symbol, model in self.ridge_models.items():
            if symbol not in returns_df.columns:
                continue
            
            actual = returns_df[symbol].reindex(X.index)
            predicted = model.predict(X.values)
            
            df = pd.DataFrame({
                'symbol': symbol,
                'actual_return': actual,
                'predicted_return': predicted,
            }, index=X.index)
            
            df['residual_alpha'] = df['actual_return'] - df['predicted_return']
            df['abs_alpha'] = df['residual_alpha'].abs()
            
            results.append(df)
        
        if not results:
            return pd.DataFrame()
        
        return pd.concat(results)
    
    def build_long_short_basket(
        self,
        macro_df: pd.DataFrame,
        returns_df: pd.DataFrame,
        n_positions: int = 5,
        target_volatility: float = 0.12,  # 12% annualized
        use_risk_parity: bool = True
    ) -> LongShortBasket:
        """
        Build market-neutral long-short basket based on residual alphas.
        """
        alpha_df = self.compute_residual_alpha(macro_df, returns_df)
        
        if alpha_df.empty:
            return LongShortBasket([], [], 'none', 0.0, 0.0, datetime.utcnow())
        
        # Get latest alphas for each symbol
        latest = alpha_df.groupby('symbol').last()
        
        # Sort by residual alpha
        sorted_alphas = latest.sort_values('residual_alpha', ascending=False)
        
        # Select top/bottom
        longs = sorted_alphas.head(n_positions)
        shorts = sorted_alphas.tail(n_positions)
        
        # Compute position sizes
        if use_risk_parity and CVXPY_AVAILABLE:
            # Risk parity optimization
            long_weights = self._risk_parity_weights(longs, returns_df)
            short_weights = self._risk_parity_weights(shorts, returns_df)
        else:
            # Equal weights
            long_weights = {sym: 1.0 / n_positions for sym in longs.index}
            short_weights = {sym: 1.0 / n_positions for sym in shorts.index}
        
        # Normalize to target volatility
        vol_scale = self._compute_volatility_scale(
            list(long_weights.keys()) + list(short_weights.keys()),
            returns_df,
            target_volatility
        )
        
        long_positions = [(sym, w * vol_scale) for sym, w in long_weights.items()]
        short_positions = [(sym, -w * vol_scale) for sym, w in short_weights.items()]
        
        # Expected return
        expected_ret = (
            sum(longs['residual_alpha'] * pd.Series(long_weights)) -
            sum(shorts['residual_alpha'] * pd.Series(short_weights))
        )
        
        return LongShortBasket(
            longs=long_positions,
            shorts=short_positions,
            neutralization='market',
            target_volatility=target_volatility,
            expected_return=expected_ret,
            timestamp=datetime.utcnow()
        )
    
    def _risk_parity_weights(
        self,
        alpha_subset: pd.DataFrame,
        returns_df: pd.DataFrame,
        lookback: int = 168  # 1 week of hourly
    ) -> Dict[str, float]:
        """
        Compute inverse-volatility weights.
        """
        symbols = alpha_subset.index.tolist()
        recent_returns = returns_df[symbols].tail(lookback)
        
        # Annualized volatility
        vols = recent_returns.std() * np.sqrt(365 * 24)
        
        # Inverse volatility weights
        inv_vols = 1.0 / (vols + 1e-10)
        weights = inv_vols / inv_vols.sum()
        
        return weights.to_dict()
    
    def _compute_volatility_scale(
        self,
        symbols: List[str],
        returns_df: pd.DataFrame,
        target_vol: float,
        lookback: int = 168
    ) -> float:
        """
        Compute scaling factor to achieve target portfolio volatility.
        """
        available = [s for s in symbols if s in returns_df.columns]
        if not available:
            return 1.0
        
        recent = returns_df[available].tail(lookback)
        port_vol = recent.mean(axis=1).std() * np.sqrt(365 * 24)
        
        if port_vol < 1e-10:
            return 1.0
        
        return target_vol / port_vol
    
    def save(self, path: Path):
        """Save model to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        joblib.dump({
            'ridge_models': self.ridge_models,
            'asset_r_squared': self.asset_r_squared,
            'factor_names': self.factor_names,
            'scaler': self.scaler,
            'alpha': self.alpha,
            'is_fitted': self._is_fitted
        }, path / 'factor_model.joblib')
        
        logger.info(f"Factor model saved to {path}")
    
    def load(self, path: Path):
        """Load model from disk."""
        path = Path(path)
        model_path = path / 'factor_model.joblib'
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")
        
        data = joblib.load(model_path)
        
        self.ridge_models = data['ridge_models']
        self.asset_r_squared = data['asset_r_squared']
        self.factor_names = data['factor_names']
        self.scaler = data['scaler']
        self.alpha = data['alpha']
        self._is_fitted = data['is_fitted']
        
        logger.info(f"Factor model loaded from {path}")


def train_factor_model(
    macro_data: pd.DataFrame,
    returns_data: pd.DataFrame,
    model_path: Path = Path("models/factor_model")
) -> MacroFactorModel:
    """
    Train and save factor model.
    """
    model = MacroFactorModel()
    model.fit_initial(macro_data, returns_data)
    model.save(model_path)
    return model


def load_factor_model(
    model_path: Path = Path("models/factor_model")
) -> MacroFactorModel:
    """
    Load trained factor model.
    """
    model = MacroFactorModel()
    model.load(model_path)
    return model
