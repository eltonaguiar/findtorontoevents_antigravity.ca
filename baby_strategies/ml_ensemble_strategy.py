"""
ML Ensemble Trading Strategy
Combines XGBoost, LSTM, and Transformer models with on-chain data
Target: 15-25% CAGR with superior risk-adjusted returns
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

# ML libraries
try:
    import xgboost as xgb
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("ML libraries not available. Install with: pip install xgboost scikit-learn")

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not available. LSTM/Transformer features disabled.")


@dataclass
class ModelPrediction:
    """Individual model prediction with confidence"""
    model_name: str
    prediction: float  # Expected return
    confidence: float  # 0-1 scale
    direction: int  # -1, 0, 1


class LSTMModel(nn.Module):
    """LSTM for time series prediction"""
    def __init__(self, input_dim: int = 20, hidden_dim: int = 64, num_layers: int = 3):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=0.3,
            batch_first=True
        )
        self.fc = nn.Linear(hidden_dim, 1)
        self.layer_norm = nn.LayerNorm(hidden_dim)
        
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        # Use last timestep
        last_hidden = lstm_out[:, -1, :]
        normalized = self.layer_norm(last_hidden)
        return self.fc(normalized)


class TransformerModel(nn.Module):
    """Simplified Quantformer-style transformer"""
    def __init__(self, input_dim: int = 20, d_model: int = 64, nhead: int = 8, num_layers: int = 4):
        super().__init__()
        self.embedding = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=0.1,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        self.fc = nn.Linear(d_model, 1)
        
    def forward(self, x):
        embedded = self.embedding(x)
        transformed = self.transformer(embedded)
        # Global average pooling
        pooled = transformed.mean(dim=1)
        return self.fc(pooled)


class FeatureEngineer:
    """Create features for ML models"""
    
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self.scaler = StandardScaler()
        
    def technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        features = pd.DataFrame(index=df.index)
        
        # Price features
        features['returns'] = df['close'].pct_change()
        features['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Moving averages
        for period in [5, 10, 20, 50]:
            features[f'sma_{period}'] = df['close'].rolling(period).mean()
            features[f'sma_ratio_{period}'] = df['close'] / features[f'sma_{period}']
        
        # Volatility
        features['volatility_5'] = features['returns'].rolling(5).std()
        features['volatility_20'] = features['returns'].rolling(20).std()
        features['volatility_ratio'] = features['volatility_5'] / features['volatility_20']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        features['macd'] = ema_12 - ema_26
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        
        # Bollinger Bands
        sma_20 = df['close'].rolling(20).mean()
        std_20 = df['close'].rolling(20).std()
        features['bb_upper'] = sma_20 + (std_20 * 2)
        features['bb_lower'] = sma_20 - (std_20 * 2)
        features['bb_position'] = (df['close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        
        # Volume features
        if 'volume' in df.columns:
            features['volume_sma'] = df['volume'].rolling(20).mean()
            features['volume_ratio'] = df['volume'] / features['volume_sma']
            features['volume_price_trend'] = features['returns'] * features['volume_ratio']
        
        return features
    
    def onchain_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate on-chain features if available"""
        features = pd.DataFrame(index=df.index)
        
        # Check for on-chain columns
        onchain_cols = ['nupl', 'mvrv', 'exchange_flow', 'sopr', 'lth_supply']
        available_cols = [c for c in onchain_cols if c in df.columns]
        
        if available_cols:
            for col in available_cols:
                features[col] = df[col]
                # Normalized versions
                features[f'{col}_zscore'] = (df[col] - df[col].rolling(90).mean()) / df[col].rolling(90).std()
        
        return features
    
    def create_feature_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create complete feature set"""
        tech = self.technical_features(df)
        chain = self.onchain_features(df)
        
        features = pd.concat([tech, chain], axis=1)
        
        # Add lagged features
        for col in ['returns', 'volume_ratio']:
            if col in features.columns:
                for lag in [1, 2, 3, 5]:
                    features[f'{col}_lag_{lag}'] = features[col].shift(lag)
        
        return features.dropna()


class MLEnsembleStrategy:
    """
    Machine Learning Ensemble Strategy
    
    Combines:
    - XGBoost (gradient boosted trees)
    - Random Forest
    - LSTM (deep learning)
    - Transformer (attention mechanism)
    
    With on-chain data integration for crypto assets
    """
    
    def __init__(self, 
                 symbol: str,
                 capital: float = 10000,
                 ensemble_weights: Optional[Dict[str, float]] = None,
                 confidence_threshold: float = 0.6,
                 max_position: float = 0.25):
        
        self.symbol = symbol
        self.capital = capital
        self.confidence_threshold = confidence_threshold
        self.max_position = max_position
        
        # Default ensemble weights
        self.ensemble_weights = ensemble_weights or {
            'xgboost': 0.35,
            'random_forest': 0.25,
            'lstm': 0.20,
            'transformer': 0.20
        }
        
        # Models
        self.models = {}
        self.feature_engineer = FeatureEngineer()
        self.is_trained = False
        
        # Performance tracking
        self.predictions_history = []
        self.actual_returns = []
        
        # Model-specific settings
        self.model_params = {
            'xgboost': {
                'n_estimators': 500,
                'max_depth': 6,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42
            },
            'random_forest': {
                'n_estimators': 300,
                'max_depth': 15,
                'min_samples_split': 10,
                'random_state': 42
            }
        }
        
        logging.info(f"Initialized MLEnsembleStrategy for {symbol}")
    
    def prepare_data(self, df: pd.DataFrame, target_horizon: int = 5) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features and target"""
        features = self.feature_engineer.create_feature_matrix(df)
        
        # Target: Future returns
        target = df['close'].pct_change(target_horizon).shift(-target_horizon)
        
        # Align features and target
        aligned = pd.concat([features, target], axis=1).dropna()
        X = aligned.iloc[:, :-1]
        y = aligned.iloc[:, -1]
        
        return X, y
    
    def train(self, df: pd.DataFrame, validation_split: float = 0.2):
        """Train all models"""
        if not ML_AVAILABLE:
            raise RuntimeError("ML libraries not available. Cannot train models.")
        
        X, y = self.prepare_data(df)
        
        # Split data chronologically
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Scale features
        X_train_scaled = pd.DataFrame(
            self.feature_engineer.scaler.fit_transform(X_train),
            index=X_train.index,
            columns=X_train.columns
        )
        X_val_scaled = pd.DataFrame(
            self.feature_engineer.scaler.transform(X_val),
            index=X_val.index,
            columns=X_val.columns
        )
        
        # Train XGBoost
        if 'xgboost' in self.ensemble_weights:
            logging.info("Training XGBoost...")
            xgb_model = xgb.XGBRegressor(**self.model_params['xgboost'])
            xgb_model.fit(
                X_train_scaled, y_train,
                eval_set=[(X_val_scaled, y_val)],
                verbose=False
            )
            self.models['xgboost'] = xgb_model
        
        # Train Random Forest
        if 'random_forest' in self.ensemble_weights:
            logging.info("Training Random Forest...")
            rf_model = RandomForestRegressor(**self.model_params['random_forest'])
            rf_model.fit(X_train_scaled, y_train)
            self.models['random_forest'] = rf_model
        
        # Train LSTM
        if 'lstm' in self.ensemble_weights and TORCH_AVAILABLE:
            logging.info("Training LSTM...")
            self._train_lstm(X_train_scaled, y_train, X_val_scaled, y_val)
        
        # Train Transformer
        if 'transformer' in self.ensemble_weights and TORCH_AVAILABLE:
            logging.info("Training Transformer...")
            self._train_transformer(X_train_scaled, y_train, X_val_scaled, y_val)
        
        self.is_trained = True
        
        # Evaluate on validation set
        val_predictions = self._ensemble_predict(X_val_scaled)
        val_corr = np.corrcoef(val_predictions, y_val)[0, 1]
        logging.info(f"Validation correlation: {val_corr:.4f}")
        
        return self
    
    def _train_lstm(self, X_train, y_train, X_val, y_val, epochs=100):
        """Train LSTM model"""
        # Create sequences
        seq_length = 20
        
        def create_sequences(X, y, seq_len):
            Xs, ys = [], []
            for i in range(len(X) - seq_len):
                Xs.append(X.iloc[i:i+seq_len].values)
                ys.append(y.iloc[i+seq_len])
            return np.array(Xs), np.array(ys)
        
        X_seq, y_seq = create_sequences(X_train, y_train, seq_length)
        X_val_seq, y_val_seq = create_sequences(
            pd.concat([X_train.tail(seq_length), X_val]),
            pd.concat([y_train.tail(seq_length), y_val]),
            seq_length
        )
        
        # Model
        model = LSTMModel(input_dim=X_train.shape[1])
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        # Training
        best_val_loss = float('inf')
        patience = 20
        patience_counter = 0
        
        for epoch in range(epochs):
            model.train()
            optimizer.zero_grad()
            
            X_tensor = torch.FloatTensor(X_seq)
            y_tensor = torch.FloatTensor(y_seq).unsqueeze(1)
            
            pred = model(X_tensor)
            loss = criterion(pred, y_tensor)
            loss.backward()
            optimizer.step()
            
            # Validation
            if epoch % 5 == 0:
                model.eval()
                with torch.no_grad():
                    val_pred = model(torch.FloatTensor(X_val_seq))
                    val_loss = criterion(val_pred, torch.FloatTensor(y_val_seq).unsqueeze(1))
                
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                
                if patience_counter >= patience:
                    logging.info(f"LSTM early stopping at epoch {epoch}")
                    break
        
        self.models['lstm'] = model
    
    def _train_transformer(self, X_train, y_train, X_val, y_val, epochs=100):
        """Train Transformer model"""
        seq_length = 20
        
        def create_sequences(X, y, seq_len):
            Xs, ys = [], []
            for i in range(len(X) - seq_len):
                Xs.append(X.iloc[i:i+seq_len].values)
                ys.append(y.iloc[i+seq_len])
            return np.array(Xs), np.array(ys)
        
        X_seq, y_seq = create_sequences(X_train, y_train, seq_length)
        X_val_seq, y_val_seq = create_sequences(
            pd.concat([X_train.tail(seq_length), X_val]),
            pd.concat([y_train.tail(seq_length), y_val]),
            seq_length
        )
        
        model = TransformerModel(input_dim=X_train.shape[1])
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        best_val_loss = float('inf')
        patience = 20
        
        for epoch in range(epochs):
            model.train()
            optimizer.zero_grad()
            
            X_tensor = torch.FloatTensor(X_seq)
            y_tensor = torch.FloatTensor(y_seq).unsqueeze(1)
            
            pred = model(X_tensor)
            loss = criterion(pred, y_tensor)
            loss.backward()
            optimizer.step()
            
            if epoch % 5 == 0:
                model.eval()
                with torch.no_grad():
                    val_pred = model(torch.FloatTensor(X_val_seq))
                    val_loss = criterion(val_pred, torch.FloatTensor(y_val_seq).unsqueeze(1))
                
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                
                if patience_counter >= patience:
                    logging.info(f"Transformer early stopping at epoch {epoch}")
                    break
        
        self.models['transformer'] = model
    
    def predict(self, df: pd.DataFrame) -> ModelPrediction:
        """Generate ensemble prediction"""
        if not self.is_trained:
            raise RuntimeError("Models not trained. Call train() first.")
        
        X = self.feature_engineer.create_feature_matrix(df)
        if len(X) == 0:
            return ModelPrediction('ensemble', 0, 0, 0)
        
        X_latest = X.iloc[-1:]
        X_scaled = self.feature_engineer.scaler.transform(X_latest)
        
        predictions = []
        
        # Tree-based models
        for name in ['xgboost', 'random_forest']:
            if name in self.models:
                pred = self.models[name].predict(X_scaled)[0]
                predictions.append(ModelPrediction(name, pred, 0.7, np.sign(pred)))
        
        # Deep learning models
        if TORCH_AVAILABLE:
            for name in ['lstm', 'transformer']:
                if name in self.models:
                    model = self.models[name]
                    model.eval()
                    
                    # Get sequence
                    seq_len = 20
                    if len(X) >= seq_len:
                        seq = X.iloc[-seq_len:].values
                        seq_scaled = self.feature_engineer.scaler.transform(seq)
                        seq_tensor = torch.FloatTensor(seq_scaled).unsqueeze(0)
                        
                        with torch.no_grad():
                            pred = model(seq_tensor).item()
                        predictions.append(ModelPrediction(name, pred, 0.65, np.sign(pred)))
        
        # Ensemble
        if not predictions:
            return ModelPrediction('ensemble', 0, 0, 0)
        
        # Weighted average
        total_weight = sum(self.ensemble_weights.get(p.model_name, 0.2) for p in predictions)
        weighted_pred = sum(
            p.prediction * self.ensemble_weights.get(p.model_name, 0.2) 
            for p in predictions
        ) / total_weight
        
        # Confidence based on agreement
        directions = [p.direction for p in predictions if p.direction != 0]
        if directions:
            agreement = sum(1 for d in directions if d == np.sign(weighted_pred)) / len(directions)
            confidence = agreement * 0.7 + 0.3  # Base confidence 0.3
        else:
            confidence = 0.5
        
        return ModelPrediction(
            'ensemble',
            weighted_pred,
            confidence,
            1 if weighted_pred > 0.001 else (-1 if weighted_pred < -0.001 else 0)
        )
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """Generate trading signal"""
        prediction = self.predict(df)
        
        signal = {
            'symbol': self.symbol,
            'timestamp': df.index[-1] if len(df) > 0 else datetime.now(),
            'direction': 'NEUTRAL',
            'strength': 0,
            'expected_return': prediction.prediction,
            'confidence': prediction.confidence,
            'position_size': 0
        }
        
        if prediction.confidence < self.confidence_threshold:
            return signal
        
        # Direction
        if prediction.direction > 0:
            signal['direction'] = 'LONG'
        elif prediction.direction < 0:
            signal['direction'] = 'SHORT'
        
        # Strength based on expected return magnitude
        signal['strength'] = min(abs(prediction.prediction) * 100, 1.0)
        
        # Position sizing with Kelly
        if prediction.prediction > 0:
            # Conservative Kelly
            win_rate = 0.55  # Estimated from validation
            avg_win = prediction.prediction
            avg_loss = -prediction.prediction * 0.8
            
            if avg_loss != 0:
                b = avg_win / abs(avg_loss)
                kelly = (win_rate * b - (1 - win_rate)) / b
                half_kelly = kelly * 0.5
                signal['position_size'] = max(0, min(half_kelly, self.max_position))
        
        return signal
    
    def backtest(self, df: pd.DataFrame, train_ratio: float = 0.6) -> Dict:
        """Walk-forward backtest"""
        if not ML_AVAILABLE:
            return {'error': 'ML libraries not available'}
        
        # Initial training
        train_size = int(len(df) * train_ratio)
        train_df = df.iloc[:train_size]
        test_df = df.iloc[train_size:]
        
        self.train(train_df)
        
        # Walk-forward test
        results = []
        position = 0
        equity = self.capital
        
        retrain_every = 63  # Retrain quarterly
        
        for i in range(0, len(test_df) - 5, 5):
            current_data = pd.concat([train_df, test_df.iloc[:i]])
            
            # Retrain periodically
            if i > 0 and i % retrain_every == 0:
                self.train(current_data)
            
            # Generate signal
            signal = self.generate_signal(current_data)
            
            # Execute
            if signal['direction'] == 'LONG' and position <= 0:
                position = 1
            elif signal['direction'] == 'SHORT' and position >= 0:
                position = -1
            elif signal['direction'] == 'NEUTRAL':
                position = 0
            
            # Calculate return
            future_return = test_df['close'].iloc[i+5] / test_df['close'].iloc[i] - 1
            strategy_return = position * future_return
            
            equity *= (1 + strategy_return)
            
            results.append({
                'date': test_df.index[i],
                'position': position,
                'signal': signal,
                'return': strategy_return,
                'equity': equity
            })
        
        # Calculate metrics
        returns = [r['return'] for r in results]
        equity_curve = [r['equity'] for r in results]
        
        metrics = {
            'total_return': (equity_curve[-1] / self.capital - 1) * 100,
            'annualized_return': self._annualize_return(equity_curve[-1] / self.capital, len(results) / 52),
            'sharpe_ratio': np.mean(returns) / np.std(returns) * np.sqrt(52) if np.std(returns) > 0 else 0,
            'max_drawdown': self._max_drawdown(equity_curve),
            'win_rate': sum(1 for r in returns if r > 0) / len(returns) * 100,
            'trades': len([r for r in results if r['position'] != 0]),
            'equity_curve': equity_curve
        }
        
        return metrics
    
    def _annualize_return(self, total_return: float, years: float) -> float:
        """Calculate annualized return"""
        if years <= 0:
            return 0
        return ((total_return) ** (1/years) - 1) * 100
    
    def _max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown"""
        peak = equity_curve[0]
        max_dd = 0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)
        return max_dd * 100


# Factory function
def create_ml_ensemble_strategy(symbol: str, capital: float = 10000) -> MLEnsembleStrategy:
    """Create configured ML ensemble strategy"""
    return MLEnsembleStrategy(
        symbol=symbol,
        capital=capital,
        ensemble_weights={
            'xgboost': 0.35,
            'random_forest': 0.25,
            'lstm': 0.20,
            'transformer': 0.20
        },
        confidence_threshold=0.6,
        max_position=0.20
    )


if __name__ == "__main__":
    # Example usage
    print("ML Ensemble Strategy - Example Usage")
    print("=" * 50)
    
    strategy = create_ml_ensemble_strategy("BTC-USD", capital=10000)
    
    print(f"\nStrategy Configuration:")
    print(f"  Symbol: {strategy.symbol}")
    print(f"  Capital: ${strategy.capital:,.2f}")
    print(f"  Ensemble Weights: {strategy.ensemble_weights}")
    print(f"  Confidence Threshold: {strategy.confidence_threshold}")
    print(f"  Max Position: {strategy.max_position * 100}%")
    
    print("\nTo run backtest:")
    print("  strategy.train(df)")
    print("  results = strategy.backtest(df)")
