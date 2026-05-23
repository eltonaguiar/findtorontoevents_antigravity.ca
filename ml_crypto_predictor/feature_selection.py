"""
Feature Selection Audit - L1 Regularization for Model Improvement
===============================================================
Identifies and keeps only the top predictive features to:
- Reduce overfitting
- Improve out-of-sample win-rate
- Lower model complexity
- Speed up inference
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from sklearn.linear_model import Lasso, LassoCV
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectFromModel
import logging

logger = logging.getLogger(__name__)


def audit_feature_importance_l1(
    X: pd.DataFrame,
    y: pd.Series,
    max_features: int = 100,
    cv_folds: int = 5
) -> Dict:
    """
    Run L1-regularized feature selection audit.
    
    Uses Lasso regression with cross-validation to find optimal alpha,
    then selects features with non-zero coefficients.
    
    Args:
        X: Feature matrix
        y: Target variable (returns or direction)
        max_features: Maximum features to keep
        cv_folds: Number of CV folds for alpha selection
    
    Returns:
        Dict with selected features, coefficients, and importance scores
    """
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Use LassoCV to find optimal alpha
    lasso_cv = LassoCV(cv=cv_folds, random_state=42, max_iter=2000)
    lasso_cv.fit(X_scaled, y)
    
    # Get optimal alpha
    optimal_alpha = lasso_cv.alpha_
    logger.info(f"Optimal L1 alpha: {optimal_alpha:.6f}")
    
    # Fit final Lasso with optimal alpha
    lasso = Lasso(alpha=optimal_alpha, random_state=42, max_iter=2000)
    lasso.fit(X_scaled, y)
    
    # Get feature importance (absolute coefficients)
    importance = np.abs(lasso.coef_)
    
    # Create feature importance dataframe
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'coefficient': lasso.coef_,
        'abs_coefficient': importance,
        'selected': importance > 0
    }).sort_values('abs_coefficient', ascending=False)
    
    # Select top features (up to max_features)
    selected = feature_importance[feature_importance['selected']].head(max_features)
    
    # Log results
    n_selected = len(selected)
    n_total = len(X.columns)
    logger.info(f"Selected {n_selected}/{n_total} features ({n_selected/n_total:.1%})")
    
    # Log top 10 features
    logger.info("Top 10 features by importance:")
    for _, row in selected.head(10).iterrows():
        logger.info(f"  {row['feature']}: {row['coefficient']:.4f}")
    
    return {
        'selected_features': selected['feature'].tolist(),
        'all_features': feature_importance.to_dict('records'),
        'optimal_alpha': optimal_alpha,
        'n_selected': n_selected,
        'n_total': n_total,
        'selection_ratio': n_selected / n_total if n_total > 0 else 0,
        'scaler': scaler,
        'model': lasso
    }


def select_top_features_by_mutual_info(
    X: pd.DataFrame,
    y: pd.Series,
    n_features: int = 50
) -> List[str]:
    """
    Select features using mutual information (non-linear relationships).
    
    Good for capturing non-linear patterns that L1 might miss.
    """
    from sklearn.feature_selection import mutual_info_regression, SelectKBest
    
    selector = SelectKBest(score_func=mutual_info_regression, k=n_features)
    selector.fit(X, y)
    
    # Get selected feature names
    mask = selector.get_support()
    selected = X.columns[mask].tolist()
    
    # Get scores
    scores = selector.scores_
    feature_scores = pd.DataFrame({
        'feature': X.columns,
        'mutual_info_score': scores
    }).sort_values('mutual_info_score', ascending=False)
    
    logger.info(f"Selected {len(selected)} features by mutual information")
    
    return selected


def recursive_feature_elimination(
    X: pd.DataFrame,
    y: pd.Series,
    estimator=None,
    n_features: int = 50,
    step: float = 0.1
) -> List[str]:
    """
    Recursive Feature Elimination (RFE) for feature selection.
    
    More aggressive than L1 - iteratively removes weakest features.
    """
    from sklearn.feature_selection import RFECV
    from sklearn.ensemble import RandomForestRegressor
    
    if estimator is None:
        estimator = RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1)
    
    # Use RFECV to find optimal number of features
    selector = RFECV(
        estimator=estimator,
        step=step,
        cv=3,
        scoring='neg_mean_squared_error',
        n_jobs=-1,
        min_features_to_select=n_features
    )
    
    selector.fit(X, y)
    
    # Get selected features
    mask = selector.get_support()
    selected = X.columns[mask].tolist()
    
    logger.info(f"RFE selected {len(selected)} features (optimal via CV)")
    logger.info(f"CV scores shape: {selector.cv_results_.shape}")
    
    return selected


def compare_feature_selection_methods(
    X: pd.DataFrame,
    y: pd.Series,
    max_features: int = 100
) -> pd.DataFrame:
    """
    Compare multiple feature selection methods and return consensus.
    """
    results = {}
    
    # Method 1: L1 (Lasso)
    try:
        l1_result = audit_feature_importance_l1(X, y, max_features=max_features)
        results['l1_lasso'] = set(l1_result['selected_features'])
        logger.info(f"L1 selected {len(results['l1_lasso'])} features")
    except Exception as e:
        logger.error(f"L1 selection failed: {e}")
        results['l1_lasso'] = set()
    
    # Method 2: Mutual Information
    try:
        mi_features = select_top_features_by_mutual_info(X, y, n_features=max_features)
        results['mutual_info'] = set(mi_features)
        logger.info(f"Mutual info selected {len(results['mutual_info'])} features")
    except Exception as e:
        logger.error(f"Mutual info selection failed: {e}")
        results['mutual_info'] = set()
    
    # Method 3: RFE
    try:
        rfe_features = recursive_feature_elimination(X, y, n_features=max_features//2)
        results['rfe'] = set(rfe_features)
        logger.info(f"RFE selected {len(results['rfe'])} features")
    except Exception as e:
        logger.error(f"RFE selection failed: {e}")
        results['rfe'] = set()
    
    # Find consensus (features selected by at least 2 methods)
    from collections import Counter
    all_selected = []
    for method_features in results.values():
        all_selected.extend(list(method_features))
    
    feature_counts = Counter(all_selected)
    consensus_features = [f for f, count in feature_counts.items() if count >= 2]
    
    # If consensus is too small, use L1 result
    if len(consensus_features) < max_features // 4:
        logger.warning(f"Consensus too small ({len(consensus_features)}), using L1 result")
        consensus_features = list(results['l1_lasso'])
    
    logger.info(f"Consensus features (2+ methods): {len(consensus_features)}")
    
    # Create comparison dataframe
    comparison = pd.DataFrame({
        'feature': X.columns,
        'l1_selected': [f in results['l1_lasso'] for f in X.columns],
        'mi_selected': [f in results['mutual_info'] for f in X.columns],
        'rfe_selected': [f in results['rfe'] for f in X.columns],
        'consensus': [f in consensus_features for f in X.columns],
        'method_count': [feature_counts.get(f, 0) for f in X.columns]
    }).sort_values('method_count', ascending=False)
    
    return comparison


def apply_feature_selection_to_model(
    model_path: str,
    feature_names: List[str],
    selected_features: List[str]
) -> Dict:
    """
    Apply feature selection results to a trained model.
    
    Returns metadata about the reduction for logging.
    """
    n_original = len(feature_names)
    n_selected = len(selected_features)
    reduction = (n_original - n_selected) / n_original if n_original > 0 else 0
    
    logger.info(f"Feature reduction: {n_original} → {n_selected} ({reduction:.1%} reduction)")
    
    return {
        'n_original': n_original,
        'n_selected': n_selected,
        'reduction_pct': reduction * 100,
        'selected_features': selected_features,
        'dropped_features': list(set(feature_names) - set(selected_features))
    }


if __name__ == "__main__":
    # Example usage
    print("Feature Selection Audit Module")
    print("Use this module to audit and select the best features for your models")
    print("\nExample:")
    print("  from ml_crypto_predictor.feature_selection import audit_feature_importance_l1")
    print("  result = audit_feature_importance_l1(X_train, y_train, max_features=100)")
    print("  selected = result['selected_features']")
