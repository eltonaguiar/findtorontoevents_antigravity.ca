#!/usr/bin/env python3
"""
XGBoost Training Pipeline for Meme Coin Price Prediction
Predicts whether a coin will hit take-profit before stop-loss within 24 hours

Usage:
    python train_model.py --symbol DOGE --days 90
    python train_model.py --all-symbols --days 90
    python train_model.py --retrain --model-version v1.1.0
"""

import json
import argparse
import warnings
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import numpy as np
import pandas as pd

# Suppress warnings
warnings.filterwarnings('ignore')

try:
    import xgboost as xgb
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        roc_auc_score, classification_report, confusion_matrix
    )
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: ML libraries not available: {e}")
    print("Install with: pip install xgboost scikit-learn pandas numpy")
    SKLEARN_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════

FEATURES = [
    'return_5m', 'return_15m', 'return_1h', 'return_4h', 'return_24h',
    'volatility_24h', 'volume_ratio', 'reddit_velocity', 'trends_velocity',
    'sentiment_correlation', 'btc_trend_4h', 'btc_trend_24h',
    'hour', 'day_of_week', 'is_weekend'
]

TARGET = 'hit_tp_before_sl'

MODEL_CONFIG = {
    'n_estimators': 200,
    'max_depth': 5,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'objective': 'binary:logistic',
    'eval_metric': 'auc',
    'random_state': 42,
    'n_jobs': -1,
    'early_stopping_rounds': 20
}

CROSS_VAL_CONFIG = {
    'n_splits': 5,
    'test_size': 0.2
}


# ═══════════════════════════════════════════════════════════════════════
#  Data Loading
# ═══════════════════════════════════════════════════════════════════════

def load_historical_data(symbol: str, days: int = 90, data_dir: str = './data/') -> pd.DataFrame:
    """
    Load historical features and labels for training
    
    In production, this would:
    1. Query the PHP API for historical features
    2. Load from database
    3. Load from CSV files
    """
    # Try to load from CSV first
    csv_path = f"{data_dir}training_data_{symbol.lower()}.csv"
    
    try:
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} samples from {csv_path}")
        return df
    except FileNotFoundError:
        print(f"No local data found for {symbol}, generating synthetic training data...")
        return generate_synthetic_data(symbol, days)


def generate_synthetic_data(symbol: str, days: int = 90) -> pd.DataFrame:
    """
    Generate synthetic training data for demonstration
    In production, replace with actual historical data loading
    """
    np.random.seed(42)
    n_samples = days * 10  # Assume ~10 signals per day
    
    data = []
    for i in range(n_samples):
        # Generate realistic feature distributions
        sample = {
            'return_5m': np.random.normal(0.1, 2.0),
            'return_15m': np.random.normal(0.3, 3.5),
            'return_1h': np.random.normal(0.8, 5.0),
            'return_4h': np.random.normal(2.5, 8.0),
            'return_24h': np.random.normal(5.0, 15.0),
            'volatility_24h': np.random.uniform(0.01, 0.15),
            'volume_ratio': np.random.lognormal(0, 0.5),
            'reddit_velocity': np.random.exponential(20),
            'trends_velocity': np.random.lognormal(0, 0.3),
            'sentiment_correlation': np.random.beta(2, 2),
            'btc_trend_4h': np.random.normal(0.2, 1.5),
            'btc_trend_24h': np.random.normal(0.5, 3.0),
            'hour': np.random.randint(0, 24),
            'day_of_week': np.random.randint(0, 7),
            'is_weekend': np.random.choice([0, 1], p=[0.71, 0.29])
        }
        
        # Generate target based on feature relationships (simulated)
        # Higher returns + positive sentiment + low volatility = more likely to hit TP
        win_probability = (
            0.3 * (sample['return_1h'] > 2) +
            0.2 * (sample['reddit_velocity'] > 15) +
            0.2 * (sample['trends_velocity'] > 1.2) +
            0.15 * (sample['btc_trend_4h'] > 0) +
            0.15 * (sample['volatility_24h'] < 0.08)
        )
        
        sample[TARGET] = 1 if np.random.random() < win_probability else 0
        sample['symbol'] = symbol
        sample['timestamp'] = datetime.now() - timedelta(hours=i)
        
        data.append(sample)
    
    df = pd.DataFrame(data)
    print(f"Generated {len(df)} synthetic samples for {symbol}")
    return df


def load_training_data(symbols: List[str], days: int = 90) -> pd.DataFrame:
    """Load and combine training data for multiple symbols"""
    dfs = []
    for symbol in symbols:
        df = load_historical_data(symbol, days)
        if df is not None and len(df) > 0:
            dfs.append(df)
    
    if not dfs:
        raise ValueError("No training data available")
    
    combined = pd.concat(dfs, ignore_index=True)
    print(f"Total training samples: {len(combined)}")
    return combined


# ═══════════════════════════════════════════════════════════════════════
#  Feature Engineering
# ═══════════════════════════════════════════════════════════════════════

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Additional feature engineering beyond base features
    """
    df = df.copy()
    
    # Interaction features
    df['momentum_x_sentiment'] = df['return_1h'] * df['reddit_velocity'] / 100
    df['vol_x_volume'] = df['volatility_24h'] * df['volume_ratio']
    
    # Trend strength
    df['trend_consistency'] = (
        (df['return_5m'] > 0).astype(int) +
        (df['return_15m'] > 0).astype(int) +
        (df['return_1h'] > 0).astype(int)
    ) / 3.0
    
    # Market context
    df['btc_aligned'] = ((df['return_1h'] > 0) == (df['btc_trend_4h'] > 0)).astype(int)
    
    # Time-based features
    df['is_night_us'] = ((df['hour'] >= 0) & (df['hour'] < 6)).astype(int)
    df['is_morning_us'] = ((df['hour'] >= 13) & (df['hour'] < 16)).astype(int)
    
    # Sentiment momentum
    df['sentiment_momentum'] = df['reddit_velocity'] * df['sentiment_correlation']
    
    return df


def prepare_features(df: pd.DataFrame, feature_cols: List[str] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prepare feature matrix and target vector
    """
    if feature_cols is None:
        feature_cols = FEATURES
    
    # Select only available features
    available_features = [f for f in feature_cols if f in df.columns]
    
    if len(available_features) != len(feature_cols):
        missing = set(feature_cols) - set(available_features)
        print(f"Warning: Missing features: {missing}")
    
    X = df[available_features].fillna(0).values
    y = df[TARGET].values if TARGET in df.columns else None
    
    return X, y, available_features


# ═══════════════════════════════════════════════════════════════════════
#  Model Training
# ═══════════════════════════════════════════════════════════════════════

def time_series_cross_validation(X: np.ndarray, y: np.ndarray, n_splits: int = 5) -> Dict:
    """
    Perform time-series cross-validation to avoid lookahead bias
    """
    if not SKLEARN_AVAILABLE:
        raise RuntimeError("scikit-learn not available")
    
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    cv_scores = {
        'accuracy': [],
        'precision': [],
        'recall': [],
        'f1': [],
        'auc': []
    }
    
    fold_results = []
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        print(f"Training fold {fold + 1}/{n_splits}...")
        
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        # Check class balance
        train_pos_rate = y_train.mean()
        val_pos_rate = y_val.mean()
        print(f"  Train positive rate: {train_pos_rate:.2%}, Val: {val_pos_rate:.2%}")
        
        # Calculate scale_pos_weight for imbalanced data
        scale_pos_weight = len(y_train[y_train == 0]) / max(1, len(y_train[y_train == 1]))
        
        # Train model
        model = xgb.XGBClassifier(**{**MODEL_CONFIG, 'scale_pos_weight': scale_pos_weight})
        
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        # Predictions
        y_pred = model.predict(X_val)
        y_prob = model.predict_proba(X_val)[:, 1]
        
        # Metrics
        scores = {
            'accuracy': accuracy_score(y_val, y_pred),
            'precision': precision_score(y_val, y_pred, zero_division=0),
            'recall': recall_score(y_val, y_pred, zero_division=0),
            'f1': f1_score(y_val, y_pred, zero_division=0),
            'auc': roc_auc_score(y_val, y_prob)
        }
        
        for key, value in scores.items():
            cv_scores[key].append(value)
        
        fold_results.append({
            'fold': fold + 1,
            'train_size': len(train_idx),
            'val_size': len(val_idx),
            'scores': scores
        })
        
        print(f"  Accuracy: {scores['accuracy']:.3f}, AUC: {scores['auc']:.3f}")
    
    # Average scores
    avg_scores = {key: np.mean(values) for key, values in cv_scores.items()}
    std_scores = {key: np.std(values) for key, values in cv_scores.items()}
    
    return {
        'avg_scores': avg_scores,
        'std_scores': std_scores,
        'fold_results': fold_results
    }


def train_final_model(X: np.ndarray, y: np.ndarray, feature_names: List[str]) -> xgb.XGBClassifier:
    """
    Train final model on all available data
    """
    if not SKLEARN_AVAILABLE:
        raise RuntimeError("scikit-learn not available")
    
    print("\nTraining final model on all data...")
    
    # Handle class imbalance
    scale_pos_weight = len(y[y == 0]) / max(1, len(y[y == 1]))
    print(f"Scale pos weight: {scale_pos_weight:.2f}")
    
    model = xgb.XGBClassifier(**{**MODEL_CONFIG, 'scale_pos_weight': scale_pos_weight})
    
    model.fit(X, y, verbose=False)
    
    # Feature importance
    importance = model.feature_importances_
    feature_importance = sorted(
        zip(feature_names, importance),
        key=lambda x: x[1],
        reverse=True
    )
    
    print("\nFeature Importance:")
    for feature, imp in feature_importance:
        print(f"  {feature}: {imp:.4f}")
    
    return model, feature_importance


def save_model(model: xgb.XGBClassifier, feature_importance: List, 
               version: str, metrics: Dict, model_dir: str = './models/'):
    """
    Save trained model and metadata
    """
    import os
    os.makedirs(model_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_name = f"meme_xgb_{version}_{timestamp}"
    
    # Save model
    model_path = f"{model_dir}{model_name}.json"
    model.save_model(model_path)
    
    # Save metadata
    metadata = {
        'model_name': model_name,
        'version': version,
        'timestamp': timestamp,
        'feature_importance': feature_importance,
        'cv_metrics': metrics,
        'model_config': MODEL_CONFIG,
        'features_used': FEATURES
    }
    
    metadata_path = f"{model_dir}{model_name}_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)
    
    print(f"\nModel saved to: {model_path}")
    print(f"Metadata saved to: {metadata_path}")
    
    # Update latest symlink (or file)
    latest_file = f"{model_dir}latest_model.txt"
    with open(latest_file, 'w') as f:
        f.write(model_name)
    
    return model_name


# ═══════════════════════════════════════════════════════════════════════
#  Model Evaluation
# ═══════════════════════════════════════════════════════════════════════

def evaluate_model(model: xgb.XGBClassifier, X: np.ndarray, y: np.ndarray) -> Dict:
    """
    Comprehensive model evaluation
    """
    y_pred = model.predict(X)
    y_prob = model.predict_proba(X)[:, 1]
    
    # Classification report
    report = classification_report(y, y_pred, output_dict=True, zero_division=0)
    
    # Confusion matrix
    cm = confusion_matrix(y, y_pred)
    
    # ROC-AUC
    auc = roc_auc_score(y, y_prob)
    
    # Calibration analysis
    prob_bins = np.linspace(0, 1, 11)
    calibration = []
    
    for i in range(len(prob_bins) - 1):
        mask = (y_prob >= prob_bins[i]) & (y_prob < prob_bins[i + 1])
        if mask.sum() > 0:
            actual_rate = y[mask].mean()
            predicted_rate = y_prob[mask].mean()
            calibration.append({
                'bin': f"{prob_bins[i]:.1f}-{prob_bins[i+1]:.1f}",
                'predicted': predicted_rate,
                'actual': actual_rate,
                'count': int(mask.sum())
            })
    
    return {
        'classification_report': report,
        'confusion_matrix': cm.tolist(),
        'roc_auc': auc,
        'calibration': calibration
    }


def generate_report(cv_results: Dict, evaluation: Dict, model_name: str) -> str:
    """
    Generate training report
    """
    report = []
    report.append("=" * 60)
    report.append("MEME COIN XGBOOST MODEL TRAINING REPORT")
    report.append("=" * 60)
    report.append(f"Model: {model_name}")
    report.append(f"Generated: {datetime.now().isoformat()}")
    report.append("")
    
    report.append("CROSS-VALIDATION RESULTS")
    report.append("-" * 40)
    for metric, value in cv_results['avg_scores'].items():
        std = cv_results['std_scores'][metric]
        report.append(f"  {metric.upper()}: {value:.4f} (+/- {std:.4f})")
    report.append("")
    
    report.append("EVALUATION METRICS")
    report.append("-" * 40)
    report.append(f"  ROC-AUC: {evaluation['roc_auc']:.4f}")
    report.append("")
    
    report.append("CONFUSION MATRIX")
    report.append("-" * 40)
    cm = evaluation['confusion_matrix']
    report.append(f"  TN: {cm[0][0]}, FP: {cm[0][1]}")
    report.append(f"  FN: {cm[1][0]}, TP: {cm[1][1]}")
    report.append("")
    
    report.append("PERFORMANCE BY CLASS")
    report.append("-" * 40)
    for cls, metrics in evaluation['classification_report'].items():
        if isinstance(metrics, dict):
            report.append(f"  Class {cls}:")
            report.append(f"    Precision: {metrics.get('precision', 0):.3f}")
            report.append(f"    Recall: {metrics.get('recall', 0):.3f}")
            report.append(f"    F1: {metrics.get('f1-score', 0):.3f}")
    report.append("")
    
    report.append("=" * 60)
    
    return "\n".join(report)


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Train XGBoost model for meme coin prediction')
    parser.add_argument('--symbol', type=str, help='Train for specific symbol (e.g., DOGE)')
    parser.add_argument('--symbols', type=str, help='Comma-separated list of symbols')
    parser.add_argument('--all-symbols', action='store_true', help='Train on all available symbols')
    parser.add_argument('--days', type=int, default=90, help='Days of historical data to use')
    parser.add_argument('--model-version', type=str, default='v1.0.0', help='Model version string')
    parser.add_argument('--retrain', action='store_true', help='Retrain existing model')
    parser.add_argument('--output-dir', type=str, default='./models/', help='Output directory')
    parser.add_argument('--data-dir', type=str, default='./data/', help='Data directory')
    
    args = parser.parse_args()
    
    if not SKLEARN_AVAILABLE:
        print("Error: Required ML libraries not installed")
        print("Run: pip install xgboost scikit-learn pandas numpy")
        return 1
    
    # Determine symbols to train on
    if args.symbol:
        symbols = [args.symbol]
    elif args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
    else:
        symbols = ['DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK']  # Default meme coins
    
    print(f"Training model for symbols: {symbols}")
    print(f"Using {args.days} days of historical data")
    
    try:
        # Load data
        df = load_training_data(symbols, args.days)
        
        # Feature engineering
        df = engineer_features(df)
        
        # Prepare features
        X, y, feature_names = prepare_features(df)
        
        print(f"\nFeature matrix shape: {X.shape}")
        print(f"Target distribution: {np.bincount(y)}")
        
        # Cross-validation
        print("\nPerforming time-series cross-validation...")
        cv_results = time_series_cross_validation(X, y, n_splits=CROSS_VAL_CONFIG['n_splits'])
        
        print("\nCross-Validation Summary:")
        for metric, value in cv_results['avg_scores'].items():
            std = cv_results['std_scores'][metric]
            print(f"  {metric.upper()}: {value:.4f} (+/- {std:.4f})")
        
        # Train final model
        model, feature_importance = train_final_model(X, y, feature_names)
        
        # Evaluate
        evaluation = evaluate_model(model, X, y)
        
        # Save model
        model_name = save_model(
            model, feature_importance, 
            args.model_version, cv_results, 
            model_dir=args.output_dir
        )
        
        # Generate and save report
        report = generate_report(cv_results, evaluation, model_name)
        report_path = f"{args.output_dir}{model_name}_report.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\nReport saved to: {report_path}")
        
        # Check performance target
        if cv_results['avg_scores']['accuracy'] >= 0.70:
            print("\n✓ Target accuracy (70%+) achieved!")
        else:
            print(f"\n⚠ Target accuracy (70%+) not achieved. Current: {cv_results['avg_scores']['accuracy']:.1%}")
        
        return 0
        
    except Exception as e:
        print(f"\nError during training: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
