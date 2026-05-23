"""
ML-Based Risk Predictor

Predicts portfolio risk events before they occur:
- Drawdown prediction
- Correlation breakdown detection  
- Volatility regime changes
- Position concentration risk
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RiskPrediction:
    """Risk prediction result container."""
    risk_type: str
    probability: float
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    time_horizon: str  # IMMEDIATE, SHORT_TERM, MEDIUM_TERM
    description: str
    recommended_action: str
    confidence: float


class MLRiskPredictor:
    """
    Machine Learning risk prediction system.
    
    Predicts various risk events to enable proactive risk management.
    """
    
    def __init__(self, model_dir: str = "risk_management/models"):
        """Initialize ML risk predictor."""
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Individual risk models
        self.drawdown_model = None
        self.correlation_model = None
        self.volatility_model = None
        
        self.feature_columns = None
        self.is_trained = False
        
        logger.info("ML Risk Predictor initialized")
    
    def prepare_training_data(self, portfolio_history: pd.DataFrame,
                             market_data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare training data from portfolio and market history.
        
        Args:
            portfolio_history: DataFrame with portfolio returns, positions, etc.
            market_data: DataFrame with market prices, volatility, etc.
            
        Returns:
            Feature-engineered DataFrame
        """
        # Merge portfolio and market data
        df = portfolio_history.merge(market_data, left_index=True, 
                                     right_index=True, how='inner')
        
        # Rolling window features
        windows = [5, 10, 20, 50]
        
        for window in windows:
            # Return-based features
            df[f'return_{window}d_mean'] = df['portfolio_return'].rolling(window).mean()
            df[f'return_{window}d_std'] = df['portfolio_return'].rolling(window).std()
            df[f'return_{window}d_max'] = df['portfolio_return'].rolling(window).max()
            df[f'return_{window}d_min'] = df['portfolio_return'].rolling(window).min()
            
            # Drawdown features
            df[f'drawdown_{window}d'] = (
                df['portfolio_value'] / df['portfolio_value'].rolling(window).max() - 1
            )
            
            # Volatility features
            if 'volatility' in df.columns:
                df[f'vol_{window}d_mean'] = df['volatility'].rolling(window).mean()
                df[f'vol_{window}d_trend'] = (
                    df['volatility'] / df[f'vol_{window}d_mean'] - 1
                )
            
            # Correlation features (if multiple positions)
            if 'correlation_avg' in df.columns:
                df[f'corr_{window}d_mean'] = df['correlation_avg'].rolling(window).mean()
                df[f'corr_{window}d_change'] = df['correlation_avg'].diff(window)
        
        # Position concentration
        df['max_position_pct'] = df['max_position_size'] / df['portfolio_value']
        df['position_herfindahl'] = df['position_concentration']
        
        # Trend features
        df['portfolio_sma_ratio'] = (
            df['portfolio_value'] / df['portfolio_value'].rolling(20).mean()
        )
        
        # Momentum
        df['momentum_10d'] = df['portfolio_return'].rolling(10).apply(
            lambda x: (x + 1).prod() - 1
        )
        df['momentum_20d'] = df['portfolio_return'].rolling(20).apply(
            lambda x: (x + 1).prod() - 1
        )
        
        self.feature_columns = [c for c in df.columns if any(
            x in c for x in ['return_', 'drawdown_', 'vol_', 'corr_', 'position_', 
                           'momentum_', 'sma_ratio', 'herfindahl']
        )]
        
        return df.dropna()
    
    def train(self, portfolio_history: pd.DataFrame, 
              market_data: pd.DataFrame) -> bool:
        """
        Train all risk prediction models.
        
        Args:
            portfolio_history: Historical portfolio data
            market_data: Historical market data
            
        Returns:
            True if training successful
        """
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            # Prepare features
            df = self.prepare_training_data(portfolio_history, market_data)

            if len(df) < 100:
                logger.warning(f"Insufficient data: {len(df)} samples")
                return False

            X = df[self.feature_columns]

            # Train drawdown prediction model
            # Target: Will drawdown exceed -5% in next 5 days?
            df['future_drawdown'] = df['drawdown_5d'].shift(-5)
            y_drawdown = (df['future_drawdown'] < -0.05).astype(int).fillna(0)

            # Temporal split: train on earlier data, test on later (no data leakage)
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y_drawdown.iloc[:split_idx], y_drawdown.iloc[split_idx:]
            
            self.drawdown_model = GradientBoostingClassifier(
                n_estimators=100, max_depth=4, random_state=42
            )
            self.drawdown_model.fit(X_train, y_train)
            
            dd_score = self.drawdown_model.score(X_test, y_test)
            logger.info(f"Drawdown model accuracy: {dd_score:.3f}")
            
            # Train correlation breakdown model
            if 'correlation_avg' in df.columns:
                df['future_corr'] = df['correlation_avg'].shift(-5)
                y_corr = (df['future_corr'] > 0.8).astype(int).fillna(0)
                
                self.correlation_model = GradientBoostingClassifier(
                    n_estimators=100, max_depth=4, random_state=43
                )
                self.correlation_model.fit(X, y_corr)
                logger.info("Correlation model trained")
            
            # Train volatility expansion model
            if 'volatility' in df.columns:
                df['future_vol'] = df['volatility'].shift(-3)
                y_vol = (df['future_vol'] > df['volatility'].quantile(0.9)).astype(int).fillna(0)
                
                self.volatility_model = GradientBoostingClassifier(
                    n_estimators=100, max_depth=4, random_state=44
                )
                self.volatility_model.fit(X, y_vol)
                logger.info("Volatility model trained")
            
            self.is_trained = True
            self._save_models()
            
            return True
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False
    
    def predict_risks(self, current_state: Dict) -> List[RiskPrediction]:
        """
        Predict risks based on current portfolio state.
        
        Args:
            current_state: Dictionary with current portfolio metrics
            
        Returns:
            List of RiskPrediction objects
        """
        if not self.is_trained:
            self.load_models()
        
        if not self.is_trained:
            return []
        
        risks = []
        
        try:
            # Prepare feature vector
            X = self._prepare_current_features(current_state)
            
            # Predict drawdown risk
            if self.drawdown_model:
                prob_dd = self.drawdown_model.predict_proba(X)[0, 1]
                
                if prob_dd > 0.7:
                    risks.append(RiskPrediction(
                        risk_type='DRAWDOWN',
                        probability=float(prob_dd),
                        severity='CRITICAL',
                        time_horizon='SHORT_TERM',
                        description='High probability of >5% drawdown in next 5 days',
                        recommended_action='Reduce position sizes by 50%, add hedges',
                        confidence=float(prob_dd)
                    ))
                elif prob_dd > 0.5:
                    risks.append(RiskPrediction(
                        risk_type='DRAWDOWN',
                        probability=float(prob_dd),
                        severity='HIGH',
                        time_horizon='MEDIUM_TERM',
                        description='Moderate drawdown risk detected',
                        recommended_action='Tighten stops, monitor closely',
                        confidence=float(prob_dd)
                    ))
            
            # Predict correlation breakdown
            if self.correlation_model:
                prob_corr = self.correlation_model.predict_proba(X)[0, 1]
                
                if prob_corr > 0.6:
                    risks.append(RiskPrediction(
                        risk_type='CORRELATION_BREAKDOWN',
                        probability=float(prob_corr),
                        severity='HIGH',
                        time_horizon='IMMEDIATE',
                        description='Positions may become highly correlated',
                        recommended_action='Reduce correlated positions, add uncorrelated assets',
                        confidence=float(prob_corr)
                    ))
            
            # Predict volatility expansion
            if self.volatility_model:
                prob_vol = self.volatility_model.predict_proba(X)[0, 1]
                
                if prob_vol > 0.7:
                    risks.append(RiskPrediction(
                        risk_type='VOLATILITY_EXPANSION',
                        probability=float(prob_vol),
                        severity='MEDIUM',
                        time_horizon='SHORT_TERM',
                        description='Volatility likely to increase significantly',
                        recommended_action='Reduce position sizes, widen stops',
                        confidence=float(prob_vol)
                    ))
            
            # Always check position concentration (rule-based)
            max_pos = current_state.get('max_position_pct', 0)
            if max_pos > 0.25:
                risks.append(RiskPrediction(
                    risk_type='CONCENTRATION',
                    probability=1.0,
                    severity='HIGH' if max_pos > 0.4 else 'MEDIUM',
                    time_horizon='IMMEDIATE',
                    description=f'High position concentration: {max_pos:.1%} in single asset',
                    recommended_action='Reduce largest position to <20%',
                    confidence=0.95
                ))
            
            return sorted(risks, key=lambda r: r.probability * 
                         {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}[r.severity],
                         reverse=True)
            
        except Exception as e:
            logger.error(f"Risk prediction failed: {e}")
            return []
    
    def _prepare_current_features(self, state: Dict) -> pd.DataFrame:
        """Prepare feature vector from current state."""
        features = {}
        
        # Map state to feature columns
        for col in self.feature_columns:
            # Extract base metric and window from column name
            if '_' in col:
                base = col.split('_')[0]
                features[col] = state.get(col, state.get(base, 0))
            else:
                features[col] = state.get(col, 0)
        
        return pd.DataFrame([features])
    
    def get_risk_summary(self, current_state: Dict) -> Dict:
        """Get comprehensive risk summary."""
        predictions = self.predict_risks(current_state)
        
        total_risk_score = sum(
            p.probability * {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}[p.severity]
            for p in predictions
        ) / 4  # Normalize to 0-1
        
        return {
            'risk_score': min(total_risk_score, 1.0),
            'risk_level': self._get_risk_level(total_risk_score),
            'active_risks': len(predictions),
            'predictions': [
                {
                    'type': p.risk_type,
                    'probability': p.probability,
                    'severity': p.severity,
                    'action': p.recommended_action
                }
                for p in predictions
            ],
            'should_halt': any(p.severity == 'CRITICAL' for p in predictions),
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_risk_level(self, score: float) -> str:
        """Convert risk score to level."""
        if score > 0.8:
            return 'EXTREME'
        elif score > 0.6:
            return 'HIGH'
        elif score > 0.4:
            return 'ELEVATED'
        elif score > 0.2:
            return 'MODERATE'
        else:
            return 'LOW'
    
    def _save_models(self):
        """Save trained models."""
        try:
            import joblib
            
            if self.drawdown_model:
                joblib.dump(self.drawdown_model, self.model_dir / "drawdown_model.pkl")
            if self.correlation_model:
                joblib.dump(self.correlation_model, self.model_dir / "correlation_model.pkl")
            if self.volatility_model:
                joblib.dump(self.volatility_model, self.model_dir / "volatility_model.pkl")
            
            metadata = {
                'trained_at': datetime.now().isoformat(),
                'feature_columns': self.feature_columns,
                'is_trained': self.is_trained
            }
            
            with open(self.model_dir / "risk_model_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info("Risk models saved")
            
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
    
    def load_models(self) -> bool:
        """Load trained models."""
        try:
            import joblib
            
            dd_path = self.model_dir / "drawdown_model.pkl"
            if dd_path.exists():
                self.drawdown_model = joblib.load(dd_path)
            
            corr_path = self.model_dir / "correlation_model.pkl"
            if corr_path.exists():
                self.correlation_model = joblib.load(corr_path)
            
            vol_path = self.model_dir / "volatility_model.pkl"
            if vol_path.exists():
                self.volatility_model = joblib.load(vol_path)
            
            meta_path = self.model_dir / "risk_model_metadata.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    metadata = json.load(f)
                    self.feature_columns = metadata.get('feature_columns')
                    self.is_trained = metadata.get('is_trained', False)
            
            logger.info("Risk models loaded")
            return self.is_trained
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            return False


class EnhancedCircuitBreaker:
    """
    Enhanced circuit breaker using ML risk predictions.
    
    Combines rule-based and ML-based risk detection.
    """
    
    def __init__(self, ml_predictor: Optional[MLRiskPredictor] = None):
        """Initialize enhanced circuit breaker."""
        self.ml_predictor = ml_predictor or MLRiskPredictor()
        self.rule_breaker = None  # Will integrate with existing circuit_breaker_system.py
        
    def check_risk_status(self, portfolio_state: Dict) -> Dict:
        """
        Check portfolio risk status using both rules and ML.
        
        Args:
            portfolio_state: Current portfolio state
            
        Returns:
            Risk status dictionary
        """
        # Get ML risk summary
        ml_risk = self.ml_predictor.get_risk_summary(portfolio_state)
        
        # Combine with rule-based checks
        # (Integration with existing circuit_breaker_system.py)
        
        status = {
            'trading_allowed': not ml_risk['should_halt'],
            'risk_score': ml_risk['risk_score'],
            'risk_level': ml_risk['risk_level'],
            'ml_predictions': ml_risk['predictions'],
            'recommended_actions': [p['action'] for p in ml_risk['predictions']],
            'timestamp': datetime.now().isoformat()
        }
        
        return status


def test_risk_predictor():
    """Test ML risk predictor."""
    print("Testing ML Risk Predictor...")
    
    # Create synthetic training data
    dates = pd.date_range(start='2025-01-01', periods=200, freq='D')
    
    portfolio_history = pd.DataFrame({
        'portfolio_return': np.random.normal(0.001, 0.02, 200),
        'portfolio_value': 100000 * (1 + np.random.normal(0.001, 0.02, 200)).cumprod(),
        'max_position_size': 20000 + np.random.randint(-5000, 5000, 200),
        'position_concentration': np.random.uniform(0.1, 0.3, 200)
    }, index=dates)
    
    market_data = pd.DataFrame({
        'volatility': np.random.uniform(0.1, 0.4, 200),
        'correlation_avg': np.random.uniform(0.3, 0.7, 200)
    }, index=dates)
    
    # Train model
    predictor = MLRiskPredictor()
    success = predictor.train(portfolio_history, market_data)
    
    if success:
        print("Model trained successfully!")
        
        # Test prediction
        current_state = {
            'portfolio_return': -0.03,
            'drawdown_5d': -0.04,
            'volatility': 0.35,
            'correlation_avg': 0.75,
            'max_position_pct': 0.35,
            'momentum_10d': -0.05
        }
        
        risks = predictor.predict_risks(current_state)
        print(f"\nPredicted risks: {len(risks)}")
        for risk in risks:
            print(f"  - {risk.risk_type}: {risk.severity} ({risk.probability:.1%})")
            print(f"    Action: {risk.recommended_action}")
    
    print("\nTest complete!")


if __name__ == "__main__":
    test_risk_predictor()
