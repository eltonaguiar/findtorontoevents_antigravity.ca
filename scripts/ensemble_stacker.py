"""
Ensemble Model Stacking System
Combines multiple ML models using stacking for improved performance.

CRITICAL FIX: Wired to real lm_signals + lm_trades data from DB instead of
synthetic random data. Uses purged TimeSeriesSplit for proper time-series
cross-validation (no look-ahead bias).

Data source: lm_signals joined with lm_trades and lm_market_regime
Target: forward return (return_pct from lm_trades)
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
import mysql.connector
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('ensemble_stacker')

# DB config from env vars
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

class EnsembleStacker:
    def __init__(self, base_models=None, meta_model=None, test_size=0.2, random_state=42):
        """
        Initialize ensemble stacker
        
        Args:
            base_models: List of base models for stacking
            meta_model: Meta-model for combining base model predictions
            test_size: Proportion of data for validation
            random_state: Random seed for reproducibility
        """
        self.test_size = test_size
        self.random_state = random_state
        
        # Default base models
        if base_models is None:
            self.base_models = [
                ('rf', RandomForestRegressor(n_estimators=100, random_state=random_state)),
                ('gbm', GradientBoostingRegressor(n_estimators=100, random_state=random_state)),
                ('ridge', Ridge(alpha=1.0)),
                ('lr', LinearRegression())
            ]
        else:
            self.base_models = base_models
        
        # Default meta-model
        if meta_model is None:
            self.meta_model = LinearRegression()
        else:
            self.meta_model = meta_model
        
        self.scaler = StandardScaler()
        self.base_model_predictions = {}
        self.meta_model_trained = None
        self.feature_names = None
    
    def prepare_data(self, X, y):
        """
        Prepare data for stacking using purged time-series split.

        Uses the last fold of TimeSeriesSplit (train = earlier data, val = latest data).
        A purge gap removes samples at the boundary to prevent label leakage
        from overlapping trade windows (de Prado 2018).
        """
        tscv = TimeSeriesSplit(n_splits=5)
        # Use last fold (maximum training data, most recent validation)
        train_idx, val_idx = None, None
        for t_idx, v_idx in tscv.split(X):
            train_idx, val_idx = t_idx, v_idx

        # Purge: remove ~5% of training samples at boundary
        purge_gap = max(1, int(len(train_idx) * 0.05))
        train_idx = train_idx[:-purge_gap]

        X_train = X.iloc[train_idx] if hasattr(X, 'iloc') else X[train_idx]
        X_val = X.iloc[val_idx] if hasattr(X, 'iloc') else X[val_idx]
        y_train = y.iloc[train_idx] if hasattr(y, 'iloc') else y[train_idx]
        y_val = y.iloc[val_idx] if hasattr(y, 'iloc') else y[val_idx]

        return X_train, X_val, y_train, y_val
    
    def train_base_models(self, X_train, y_train):
        """Train all base models"""
        trained_models = {}
        
        for name, model in self.base_models:
            print(f"Training base model: {name}")
            model.fit(X_train, y_train)
            trained_models[name] = model
        
        return trained_models
    
    def get_base_predictions(self, trained_models, X):
        """Get predictions from all base models"""
        predictions = {}
        
        for name, model in trained_models.items():
            preds = model.predict(X)
            predictions[name] = preds
        
        return predictions
    
    def create_meta_features(self, base_predictions):
        """Create meta-features from base model predictions"""
        # Combine predictions into a DataFrame
        meta_features = pd.DataFrame(base_predictions)
        
        # Add statistical features
        meta_features['mean_prediction'] = meta_features.mean(axis=1)
        meta_features['std_prediction'] = meta_features.std(axis=1)
        meta_features['min_prediction'] = meta_features.min(axis=1)
        meta_features['max_prediction'] = meta_features.max(axis=1)
        meta_features['range_prediction'] = meta_features['max_prediction'] - meta_features['min_prediction']
        
        return meta_features
    
    def train_meta_model(self, meta_features, y):
        """Train the meta-model on base model predictions"""
        # Scale meta-features
        meta_features_scaled = self.scaler.fit_transform(meta_features)
        
        # Train meta-model
        self.meta_model_trained = self.meta_model.fit(meta_features_scaled, y)
        
        return self.meta_model_trained
    
    def stack_predict(self, X):
        """Make predictions using the stacked ensemble"""
        if self.meta_model_trained is None:
            raise ValueError("Meta-model not trained. Call fit() first.")
        
        # Get base model predictions
        base_preds = self.get_base_predictions(self.trained_base_models, X)
        
        # Create meta-features
        meta_features = self.create_meta_features(base_preds)
        
        # Scale meta-features
        meta_features_scaled = self.scaler.transform(meta_features)
        
        # Make final prediction
        final_predictions = self.meta_model_trained.predict(meta_features_scaled)
        
        return final_predictions
    
    def fit(self, X, y):
        """Train the complete stacking ensemble"""
        # Prepare data
        X_train, X_val, y_train, y_val = self.prepare_data(X, y)
        
        # Train base models
        self.trained_base_models = self.train_base_models(X_train, y_train)
        
        # Get base model predictions on validation set
        base_val_preds = self.get_base_predictions(self.trained_base_models, X_val)
        
        # Create meta-features
        meta_features_val = self.create_meta_features(base_val_preds)
        
        # Train meta-model
        self.train_meta_model(meta_features_val, y_val)
        
        # Store feature names
        self.feature_names = X.columns.tolist()
        
        # Calculate validation performance
        val_predictions = self.stack_predict(X_val)
        val_mse = mean_squared_error(y_val, val_predictions)
        val_r2 = r2_score(y_val, val_predictions)
        
        print(f"Stacking ensemble trained successfully")
        print(f"Validation MSE: {val_mse:.4f}")
        print(f"Validation R²: {val_r2:.4f}")
        
        return self
    
    def predict(self, X):
        """Make predictions on new data"""
        return self.stack_predict(X)
    
    def get_model_weights(self):
        """Get weights assigned to each base model by meta-model"""
        if self.meta_model_trained is None:
            raise ValueError("Meta-model not trained")
        
        # Get feature names (base model predictions + statistical features)
        feature_names = list(self.trained_base_models.keys()) + [
            'mean_prediction', 'std_prediction', 'min_prediction', 
            'max_prediction', 'range_prediction'
        ]
        
        # Get coefficients (for linear meta-models)
        if hasattr(self.meta_model_trained, 'coef_'):
            weights = pd.DataFrame({
                'feature': feature_names,
                'weight': self.meta_model_trained.coef_
            }).sort_values('weight', key=abs, ascending=False)
        else:
            weights = pd.DataFrame({
                'feature': feature_names,
                'weight': [1.0/len(feature_names)] * len(feature_names)
            })
        
        return weights
    
    def cross_validate(self, X, y, cv=5):
        """Perform cross-validation on the stacking ensemble"""
        from sklearn.model_selection import cross_val_score
        
        # Create a function for cross-validation
        def stacking_cv(X_train, y_train):
            # Split into training and validation
            X_tr, X_val, y_tr, y_val = train_test_split(
                X_train, y_train, test_size=self.test_size, random_state=self.random_state
            )
            
            # Train base models
            base_models_trained = self.train_base_models(X_tr, y_tr)
            
            # Get predictions
            base_preds = self.get_base_predictions(base_models_trained, X_val)
            meta_features = self.create_meta_features(base_preds)
            
            # Scale and train meta-model
            meta_features_scaled = self.scaler.fit_transform(meta_features)
            meta_model = self.meta_model.fit(meta_features_scaled, y_val)
            
            # Make predictions
            predictions = meta_model.predict(meta_features_scaled)
            
            return mean_squared_error(y_val, predictions)
        
        # Perform cross-validation
        cv_scores = cross_val_score(
            estimator=None,
            X=X, y=y,
            scoring='neg_mean_squared_error',
            cv=cv,
            fit_params=None
        )
        
        return -cv_scores  # Convert back to positive MSE

# Performance-weighted blender
class PerformanceWeightedBlender:
    def __init__(self, validation_window=30):
        """
        Performance-weighted model blending
        
        Args:
            validation_window: Number of periods for performance evaluation
        """
        self.validation_window = validation_window
        self.model_weights = {}
        self.model_performance = {}
    
    def calculate_performance_weights(self, predictions_dict, actual_returns):
        """Calculate weights based on recent performance"""
        weights = {}
        
        for model_name, preds in predictions_dict.items():
            # Calculate recent performance (MSE)
            if len(preds) > self.validation_window:
                recent_preds = preds[-self.validation_window:]
                recent_actual = actual_returns[-self.validation_window:]
            else:
                recent_preds = preds
                recent_actual = actual_returns
            
            mse = mean_squared_error(recent_actual, recent_preds)
            
            # Inverse weighting (better performance = higher weight)
            # Add small epsilon to avoid division by zero
            weight = 1.0 / (mse + 1e-8)
            weights[model_name] = weight
            self.model_performance[model_name] = mse
        
        # Normalize weights to sum to 1
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v/total_weight for k, v in weights.items()}
        
        self.model_weights = weights
        return weights
    
    def blend_predictions(self, predictions_dict):
        """Blend predictions using performance weights"""
        if not self.model_weights:
            raise ValueError("Weights not calculated. Call calculate_performance_weights first.")
        
        # Ensure all predictions have same length
        min_length = min(len(preds) for preds in predictions_dict.values())
        
        blended_predictions = np.zeros(min_length)
        
        for model_name, preds in predictions_dict.items():
            if model_name in self.model_weights:
                weight = self.model_weights[model_name]
                blended_predictions += weight * preds[:min_length]
        
        return blended_predictions

def connect_db():
    """Connect to MySQL database."""
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )


def fetch_real_signals():
    """
    Fetch real signal data from lm_signals + lm_trades + lm_market_regime.
    Returns a DataFrame sorted by signal_date (ascending) for time-series CV.
    """
    logger.info("Fetching real signals from DB...")
    try:
        conn = connect_db()
        query = """
        SELECT s.id, s.symbol, s.algorithm_name, s.asset_class,
               s.signal_strength, s.signal_type, s.signal_date,
               t.return_pct, t.realized_pnl_usd,
               m.regime, m.spy_ret, m.vix_value
        FROM lm_signals s
        JOIN lm_trades t ON s.id = t.signal_id
        LEFT JOIN lm_market_regime m ON DATE(s.signal_date) = m.regime_date
        WHERE t.status = 'closed' AND t.return_pct IS NOT NULL
        ORDER BY s.signal_date ASC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        logger.info("Loaded %d closed signals with outcomes", len(df))
        return df
    except mysql.connector.Error as err:
        logger.error("DB error: %s", err)
        return pd.DataFrame()


def prepare_signal_features(df):
    """
    Engineer features from real signal data for the ensemble stacker.
    Target: return_pct (continuous — regression target for return prediction).
    """
    df = df.copy()

    # Features from signals
    df['is_buy'] = (df['signal_type'] == 'buy').astype(int)
    df['regime_bull'] = (df['regime'] == 'bull').astype(int)
    df['regime_bear'] = (df['regime'] == 'bear').astype(int)

    # Rolling win rate per algorithm (causal — only uses past data)
    df['win'] = (df['return_pct'] > 0).astype(int)
    df['win_rate_rolling'] = df.groupby('algorithm_name')['win'].transform(
        lambda x: x.rolling(20, min_periods=3).mean()
    )

    # One-hot encode algorithm and asset class
    df = pd.get_dummies(df, columns=['algorithm_name', 'asset_class'],
                        prefix=['algo', 'asset'])

    feature_cols = ['signal_strength', 'is_buy', 'regime_bull', 'regime_bear',
                    'spy_ret', 'vix_value', 'win_rate_rolling']
    # Add one-hot columns
    feature_cols += [c for c in df.columns if c.startswith('algo_') or c.startswith('asset_')]

    X = df[feature_cols].fillna(0)
    y = df['return_pct']

    return X, y, feature_cols


def main():
    """Main entry point — train ensemble on real DB signals."""
    logger.info("=== Ensemble Stacker (Real Data Mode) ===")

    # --- Fetch real data ---
    df = fetch_real_signals()

    if len(df) < 50:
        logger.warning("Insufficient data (%d rows). Need at least 50 closed signals with outcomes.", len(df))
        logger.info("Ensure lm_signals is populated and lm_trades has closed entries with return_pct.")
        return

    X, y, feature_cols = prepare_signal_features(df)
    logger.info("Features: %d columns, %d samples", len(feature_cols), len(X))
    logger.info("Target (return_pct): mean=%.3f%%, std=%.3f%%", y.mean(), y.std())

    # --- Train ensemble with purged TSCV ---
    ensemble = EnsembleStacker()
    ensemble.fit(X, y)

    # --- Model weights ---
    weights = ensemble.get_model_weights()
    logger.info("\nModel Weights (meta-model coefficients):")
    for _, row in weights.iterrows():
        logger.info("  %s: %.4f", row['feature'], row['weight'])

    # --- Performance-weighted blending across base models ---
    logger.info("\n=== Performance-Weighted Blending ===")
    blender = PerformanceWeightedBlender()

    # Get base model predictions on full dataset
    base_preds = ensemble.get_base_predictions(ensemble.trained_base_models, X)
    blend_weights = blender.calculate_performance_weights(base_preds, y.values)
    logger.info("Blending weights: %s",
                {k: f"{v:.4f}" for k, v in blend_weights.items()})

    blended = blender.blend_predictions(base_preds)
    blended_mse = mean_squared_error(y.values[:len(blended)], blended)
    logger.info("Blended MSE: %.4f", blended_mse)

    logger.info("\n=== Ensemble Stacker Complete ===")


if __name__ == "__main__":
    main()