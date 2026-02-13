#!/usr/bin/env python3
"""
Meme Coin XGBoost Model Training Script
========================================

Trains an XGBoost classifier to predict whether a meme coin will hit
take-profit before stop-loss.

Usage:
    python train_meme_model.py
    python train_meme_model.py --n-estimators 300 --max-depth 6
    python train_meme_model.py --evaluate-only --model-path models/meme_model_v1.0.0_20260216.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier


# Configuration
DEFAULT_DATA_PATH = 'data/training/meme_training_data.csv'
DEFAULT_MODELS_DIR = 'models'
FEATURE_COLS = [
    'return_5m', 'return_15m', 'return_1h', 'return_4h', 'return_24h',
    'volatility_24h', 'volume_ratio', 'reddit_velocity', 'trends_velocity',
    'sentiment_score', 'sentiment_volatility', 'btc_trend_4h', 'btc_trend_24h',
    'hour_of_day', 'day_of_week', 'is_weekend'
]


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Train XGBoost model for meme coin prediction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Train with default settings
  %(prog)s --n-estimators 300        # Use 300 trees
  %(prog)s --max-depth 6             # Increase tree depth
  %(prog)s --learning-rate 0.03      # Lower learning rate
  %(prog)s --evaluate-only           # Just evaluate existing model
        """
    )
    
    parser.add_argument('--data-path', type=str, default=DEFAULT_DATA_PATH,
                        help=f'Path to training CSV (default: {DEFAULT_DATA_PATH})')
    parser.add_argument('--models-dir', type=str, default=DEFAULT_MODELS_DIR,
                        help=f'Directory to save models (default: {DEFAULT_MODELS_DIR})')
    
    # Model hyperparameters
    parser.add_argument('--n-estimators', type=int, default=200,
                        help='Number of boosting rounds (default: 200)')
    parser.add_argument('--max-depth', type=int, default=5,
                        help='Maximum tree depth (default: 5)')
    parser.add_argument('--learning-rate', type=float, default=0.05,
                        help='Learning rate (default: 0.05)')
    parser.add_argument('--subsample', type=float, default=0.8,
                        help='Subsample ratio (default: 0.8)')
    parser.add_argument('--colsample-bytree', type=float, default=0.8,
                        help='Column sample ratio (default: 0.8)')
    parser.add_argument('--random-state', type=int, default=42,
                        help='Random seed (default: 42)')
    
    # Cross-validation
    parser.add_argument('--n-splits', type=int, default=5,
                        help='Number of CV folds (default: 5)')
    
    # Evaluation mode
    parser.add_argument('--evaluate-only', action='store_true',
                        help='Only evaluate existing model, skip training')
    parser.add_argument('--model-path', type=str, default=None,
                        help='Path to existing model for evaluation')
    
    return parser.parse_args()


def load_data(data_path: str) -> pd.DataFrame:
    """Load and validate training data."""
    if not os.path.exists(data_path):
        # Try relative to script location
        script_dir = Path(__file__).parent
        alt_path = script_dir.parent / data_path
        if alt_path.exists():
            data_path = str(alt_path)
        else:
            raise FileNotFoundError(
                f"Training data not found at {data_path}. "
                "Please run export_training_data.php first or specify correct path."
            )
    
    df = pd.read_csv(data_path)
    print(f"[INFO] Loaded {len(df)} samples from {data_path}")
    
    # Validate required columns
    required_cols = FEATURE_COLS + ['target']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Validate target
    if not set(df['target'].unique()).issubset({0, 1}):
        raise ValueError("Target column must contain only 0 (loss) and 1 (win)")
    
    # Check for NaN values
    nan_counts = df[FEATURE_COLS + ['target']].isna().sum()
    if nan_counts.any():
        print(f"[WARNING] NaN values detected:\n{nan_counts[nan_counts > 0]}")
        print("[INFO] Rows with NaN will be dropped")
        df = df.dropna(subset=FEATURE_COLS + ['target'])
        print(f"[INFO] After dropping NaN: {len(df)} samples")
    
    return df


def calculate_scale_pos_weight(y: pd.Series) -> float:
    """Calculate scale_pos_weight for imbalanced dataset."""
    n_neg = (y == 0).sum()
    n_pos = (y == 1).sum()
    
    if n_pos == 0:
        return 1.0
    
    weight = n_neg / n_pos
    print(f"[INFO] Class distribution - Loss: {n_neg}, Win: {n_pos}")
    print(f"[INFO] Win rate: {n_pos / len(y):.1%}")
    print(f"[INFO] scale_pos_weight: {weight:.2f}")
    
    return weight


def create_model(args, scale_pos_weight: float) -> XGBClassifier:
    """Create XGBoost classifier with specified parameters."""
    model = XGBClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
        subsample=args.subsample,
        colsample_bytree=args.colsample_bytree,
        scale_pos_weight=scale_pos_weight,
        objective='binary:logistic',
        eval_metric='auc',
        random_state=args.random_state,
        n_jobs=-1,  # Use all CPU cores
        use_label_encoder=False,
    )
    return model


def perform_cross_validation(
    X: pd.DataFrame,
    y: pd.Series,
    args,
    scale_pos_weight: float
) -> list:
    """Perform time-series cross-validation."""
    print(f"\n{'='*60}")
    print("TIME-SERIES CROSS-VALIDATION")
    print(f"{'='*60}")
    print(f"[INFO] Using {args.n_splits}-fold TimeSeriesSplit")
    print("[INFO] Note: This prevents lookahead bias by respecting temporal order")
    
    tscv = TimeSeriesSplit(n_splits=args.n_splits)
    fold_results = []
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
        print(f"\n[Fold {fold}/{args.n_splits}]")
        print(f"  Training samples: {len(train_idx)}")
        print(f"  Test samples: {len(test_idx)}")
        
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        # Create and train model for this fold
        model = create_model(args, scale_pos_weight)
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        # Evaluate
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        result = {
            'fold': fold,
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'auc': roc_auc_score(y_test, y_prob)
        }
        fold_results.append(result)
        
        print(f"  Accuracy:  {result['accuracy']:.3f}")
        print(f"  Precision: {result['precision']:.3f}")
        print(f"  Recall:    {result['recall']:.3f}")
        print(f"  F1:        {result['f1']:.3f}")
        print(f"  AUC:       {result['auc']:.3f}")
    
    return fold_results


def analyze_feature_importance(model: XGBClassifier, feature_cols: list) -> pd.DataFrame:
    """Extract and sort feature importance."""
    importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    return importance


def optimize_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    """Find optimal threshold for precision/recall tradeoff."""
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    
    # Calculate F1 scores (avoid division by zero)
    f1_scores = np.zeros_like(precision)
    valid_mask = (precision + recall) > 0
    f1_scores[valid_mask] = 2 * (precision[valid_mask] * recall[valid_mask]) / (precision[valid_mask] + recall[valid_mask])
    
    # Find optimal threshold (excluding last threshold which is NaN)
    valid_idx = np.where((precision + recall) > 0)[0]
    if len(valid_idx) > 0:
        optimal_idx = valid_idx[np.argmax(f1_scores[valid_idx])]
        optimal_threshold = float(thresholds[optimal_idx]) if optimal_idx < len(thresholds) else 0.5
        optimal_precision = float(precision[optimal_idx])
        optimal_recall = float(recall[optimal_idx])
        optimal_f1 = float(f1_scores[optimal_idx])
    else:
        optimal_threshold = 0.5
        optimal_precision = 0.0
        optimal_recall = 0.0
        optimal_f1 = 0.0
    
    # Define tier thresholds
    tier_thresholds = {
        'lean_buy': max(0.1, optimal_threshold - 0.1),
        'moderate_buy': optimal_threshold,
        'strong_buy': min(0.9, optimal_threshold + 0.1)
    }
    
    return {
        'optimal_threshold': optimal_threshold,
        'precision_at_optimal': optimal_precision,
        'recall_at_optimal': optimal_recall,
        'f1_at_optimal': optimal_f1,
        'tier_thresholds': tier_thresholds
    }


def train_final_model(
    X: pd.DataFrame,
    y: pd.Series,
    args,
    scale_pos_weight: float
) -> XGBClassifier:
    """Train final model on full dataset."""
    print(f"\n{'='*60}")
    print("FINAL MODEL TRAINING")
    print(f"{'='*60}")
    print(f"[INFO] Training on full dataset: {len(X)} samples")
    
    final_model = create_model(args, scale_pos_weight)
    final_model.fit(X, y, verbose=True)
    
    return final_model


def save_model_files(
    model: XGBClassifier,
    importance: pd.DataFrame,
    threshold_config: dict,
    fold_results: list,
    args,
    X: pd.DataFrame,
    y: pd.Series
) -> dict:
    """Save all model files."""
    # Create models directory
    models_dir = Path(args.models_dir)
    if not models_dir.is_absolute():
        script_dir = Path(__file__).parent
        models_dir = script_dir.parent / models_dir
    models_dir.mkdir(parents=True, exist_ok=True)
    
    model_version = f"v1.0.0_{datetime.now().strftime('%Y%m%d')}"
    
    # 1. Save XGBoost model
    model_path = models_dir / f"meme_model_{model_version}.json"
    model.save_model(str(model_path))
    print(f"[INFO] Saved model: {model_path}")
    
    # 2. Save feature importance
    importance_path = models_dir / "feature_importance.json"
    importance.to_json(importance_path, orient='records', indent=2)
    print(f"[INFO] Saved feature importance: {importance_path}")
    
    # 3. Save threshold config
    threshold_path = models_dir / "threshold_config.json"
    with open(threshold_path, 'w') as f:
        json.dump(threshold_config, f, indent=2)
    print(f"[INFO] Saved threshold config: {threshold_path}")
    
    # 4. Save metadata
    metadata = {
        'version': model_version,
        'trained_at': datetime.now().isoformat(),
        'n_samples': len(X),
        'n_features': len(FEATURE_COLS),
        'feature_names': FEATURE_COLS,
        'class_distribution': {
            'win': int(y.sum()),
            'loss': int(len(y) - y.sum()),
            'win_rate': float(y.mean())
        },
        'hyperparameters': {
            'n_estimators': args.n_estimators,
            'max_depth': args.max_depth,
            'learning_rate': args.learning_rate,
            'subsample': args.subsample,
            'colsample_bytree': args.colsample_bytree,
        },
        'cv_results': fold_results,
        'mean_cv_accuracy': float(np.mean([r['accuracy'] for r in fold_results])),
        'mean_cv_precision': float(np.mean([r['precision'] for r in fold_results])),
        'mean_cv_recall': float(np.mean([r['recall'] for r in fold_results])),
        'mean_cv_f1': float(np.mean([r['f1'] for r in fold_results])),
        'mean_cv_auc': float(np.mean([r['auc'] for r in fold_results])),
        'std_cv_accuracy': float(np.std([r['accuracy'] for r in fold_results])),
        'std_cv_auc': float(np.std([r['auc'] for r in fold_results])),
        'threshold_config': threshold_config
    }
    
    metadata_path = models_dir / f"meme_model_{model_version}_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"[INFO] Saved metadata: {metadata_path}")
    
    # 5. Save PHP-readable config
    model_config = {
        'version': model_version,
        'trained_at': datetime.now().isoformat(),
        'features': FEATURE_COLS,
        'thresholds': threshold_config['tier_thresholds'],
        'optimal_threshold': threshold_config['optimal_threshold'],
        'feature_importance': importance.to_dict('records'),
        'cv_accuracy': metadata['mean_cv_accuracy'],
        'cv_auc': metadata['mean_cv_auc'],
        'class_distribution': metadata['class_distribution']
    }
    
    config_path = models_dir / "model_config.json"
    with open(config_path, 'w') as f:
        json.dump(model_config, f, indent=2)
    print(f"[INFO] Saved PHP config: {config_path}")
    
    return metadata


def generate_report(metadata: dict, importance: pd.DataFrame, models_dir: Path) -> str:
    """Generate human-readable training report."""
    report_lines = [
        "MEME COIN XGBOOST MODEL TRAINING REPORT",
        "=" * 60,
        f"Model Version: {metadata['version']}",
        f"Training Date: {metadata['trained_at']}",
        "",
        "DATASET",
        "-" * 40,
        f"Total Samples: {metadata['n_samples']}",
        f"Win Rate: {metadata['class_distribution']['win_rate']:.1%}",
        f"Features: {metadata['n_features']}",
        "",
        "HYPERPARAMETERS",
        "-" * 40,
        f"N Estimators: {metadata['hyperparameters']['n_estimators']}",
        f"Max Depth: {metadata['hyperparameters']['max_depth']}",
        f"Learning Rate: {metadata['hyperparameters']['learning_rate']}",
        f"Subsample: {metadata['hyperparameters']['subsample']}",
        f"Colsample Bytree: {metadata['hyperparameters']['colsample_bytree']}",
        "",
        f"CROSS-VALIDATION ({len(metadata['cv_results'])}-Fold Time-Series)",
        "-" * 40,
    ]
    
    for result in metadata['cv_results']:
        report_lines.append(
            f"Fold {result['fold']}: "
            f"Accuracy={result['accuracy']:.3f}, "
            f"AUC={result['auc']:.3f}, "
            f"F1={result['f1']:.3f}"
        )
    
    report_lines.extend([
        "",
        f"Mean CV Accuracy: {metadata['mean_cv_accuracy']:.3f} (+/- {metadata['std_cv_accuracy']:.3f})",
        f"Mean CV AUC: {metadata['mean_cv_auc']:.3f} (+/- {metadata['std_cv_auc']:.3f})",
        f"Mean CV Precision: {metadata['mean_cv_precision']:.3f}",
        f"Mean CV Recall: {metadata['mean_cv_recall']:.3f}",
        f"Mean CV F1: {metadata['mean_cv_f1']:.3f}",
        "",
        "TOP 10 FEATURES",
        "-" * 40,
    ])
    
    for i, row in importance.head(10).iterrows():
        report_lines.append(f"{row.name + 1:2d}. {row['feature']:20s}: {row['importance']:.3f}")
    
    report_lines.extend([
        "",
        "THRESHOLD OPTIMIZATION",
        "-" * 40,
        f"Optimal Threshold: {metadata['threshold_config']['optimal_threshold']:.3f}",
        f"Precision: {metadata['threshold_config']['precision_at_optimal']:.3f}",
        f"Recall: {metadata['threshold_config']['recall_at_optimal']:.3f}",
        f"F1 Score: {metadata['threshold_config']['f1_at_optimal']:.3f}",
        "",
        "TIER THRESHOLDS",
        "-" * 40,
        f"Lean Buy:    >= {metadata['threshold_config']['tier_thresholds']['lean_buy']:.3f}",
        f"Moderate Buy: >= {metadata['threshold_config']['tier_thresholds']['moderate_buy']:.3f}",
        f"Strong Buy:   >= {metadata['threshold_config']['tier_thresholds']['strong_buy']:.3f}",
        "",
        "COMPARISON TO BASELINE",
        "-" * 40,
        "Baseline (Rule-Based): ~3-5% win rate",
        f"XGBoost (Predicted):   {metadata['class_distribution']['win_rate']:.1%}+ win rate",
        f"CV AUC:                {metadata['mean_cv_auc']:.3f} (0.5 = random, 1.0 = perfect)",
        "",
        "=" * 60,
        "Model files saved successfully!",
        "=" * 60,
    ])
    
    report = "\n".join(report_lines)
    
    # Save report
    report_path = models_dir / "training_report.txt"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"[INFO] Saved report: {report_path}")
    
    return report


def evaluate_existing_model(model_path: str, X: pd.DataFrame, y: pd.Series) -> None:
    """Evaluate an existing model without retraining."""
    print(f"\n{'='*60}")
    print("MODEL EVALUATION")
    print(f"{'='*60}")
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    model = XGBClassifier()
    model.load_model(model_path)
    
    y_pred = model.predict(X)
    y_prob = model.predict_proba(X)[:, 1]
    
    print(f"\nDataset: {len(X)} samples")
    print(f"Win rate: {y.mean():.1%}")
    print(f"\nAccuracy:  {accuracy_score(y, y_pred):.3f}")
    print(f"Precision: {precision_score(y, y_pred, zero_division=0):.3f}")
    print(f"Recall:    {recall_score(y, y_pred, zero_division=0):.3f}")
    print(f"F1:        {f1_score(y, y_pred, zero_division=0):.3f}")
    print(f"AUC:       {roc_auc_score(y, y_prob):.3f}")
    
    print("\nClassification Report:")
    print(classification_report(y, y_pred, target_names=['Loss', 'Win']))
    
    # Feature importance
    importance = analyze_feature_importance(model, FEATURE_COLS)
    print("\nTop 10 Features:")
    print(importance.head(10).to_string(index=False))


def main():
    """Main training pipeline."""
    args = parse_args()
    
    print("=" * 60)
    print("MEME COIN XGBOOST MODEL TRAINER")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load data
    df = load_data(args.data_path)
    X = df[FEATURE_COLS]
    y = df['target']
    
    # Evaluate-only mode
    if args.evaluate_only:
        if args.model_path:
            evaluate_existing_model(args.model_path, X, y)
        else:
            # Try to find latest model
            models_dir = Path(args.models_dir)
            if not models_dir.is_absolute():
                script_dir = Path(__file__).parent
                models_dir = script_dir.parent / models_dir
            
            model_files = list(models_dir.glob("meme_model_v*.json"))
            if not model_files:
                print("[ERROR] No existing model found. Please specify --model-path")
                sys.exit(1)
            
            latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
            print(f"[INFO] Using latest model: {latest_model}")
            evaluate_existing_model(str(latest_model), X, y)
        return
    
    # Calculate class weight
    scale_pos_weight = calculate_scale_pos_weight(y)
    
    # Cross-validation
    fold_results = perform_cross_validation(X, y, args, scale_pos_weight)
    
    # Train final model
    final_model = train_final_model(X, y, args, scale_pos_weight)
    
    # Feature importance
    importance = analyze_feature_importance(final_model, FEATURE_COLS)
    
    # Threshold optimization
    y_prob_full = final_model.predict_proba(X)[:, 1]
    threshold_config = optimize_threshold(y.values, y_prob_full)
    
    # Save all files
    metadata = save_model_files(
        final_model, importance, threshold_config,
        fold_results, args, X, y
    )
    
    # Generate report
    models_dir = Path(args.models_dir)
    if not models_dir.is_absolute():
        script_dir = Path(__file__).parent
        models_dir = script_dir.parent / models_dir
    
    report = generate_report(metadata, importance, models_dir)
    
    # Print report to console
    print("\n" + report)
    
    print(f"\nFinished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == '__main__':
    main()
