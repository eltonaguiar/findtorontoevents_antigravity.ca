"""
Ensemble Model Stacking System
Combines multiple ML models using stacking for improved performance
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

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
        """Prepare data for stacking"""
        # Split into training and validation sets
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state
        )
        
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

def main():
    """Main entry point for orchestrator integration."""
    # Create sample data
    np.random.seed(42)
    n_samples = 1000
    n_features = 10

    X = pd.DataFrame(np.random.randn(n_samples, n_features),
                     columns=[f'feature_{i}' for i in range(n_features)])

    # Create target with some signal
    y = (X['feature_0'] * 0.3 +
         X['feature_1'] * 0.2 +
         X['feature_2'] * 0.1 +
         np.random.randn(n_samples) * 0.1)

    # Test ensemble stacking
    print("=== Ensemble Stacking Test ===")

    ensemble = EnsembleStacker()
    ensemble.fit(X, y)

    # Make predictions
    predictions = ensemble.predict(X.head(10))
    print(f"Sample predictions: {predictions[:5]}")

    # Get model weights
    weights = ensemble.get_model_weights()
    print("\n=== Model Weights ===")
    print(weights.head())

    # Test performance-weighted blending
    print("\n=== Performance-Weighted Blending Test ===")

    blender = PerformanceWeightedBlender()

    # Create sample predictions
    preds_dict = {
        'model1': y + np.random.normal(0, 0.05, len(y)),
        'model2': y + np.random.normal(0, 0.1, len(y)),
        'model3': y + np.random.normal(0, 0.02, len(y))
    }

    weights = blender.calculate_performance_weights(preds_dict, y)
    print(f"Model weights: {weights}")

    blended_preds = blender.blend_predictions(preds_dict)
    print(f"Blended predictions MSE: {mean_squared_error(y[:len(blended_preds)], blended_preds):.4f}")


if __name__ == "__main__":
    main()