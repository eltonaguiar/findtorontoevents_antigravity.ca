"""
Automated Feature Selection System
Eliminates redundant features using multiple selection methods
"""

import pandas as pd
import numpy as np
from sklearn.feature_selection import RFE, SelectKBest, f_regression
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LassoCV
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

class FeatureSelector:
    def __init__(self, target_feature='returns', min_features=5, max_features=20):
        """
        Initialize feature selector
        
        Args:
            target_feature: The target variable for feature selection
            min_features: Minimum number of features to keep
            max_features: Maximum number of features to keep
        """
        self.target_feature = target_feature
        self.min_features = min_features
        self.max_features = max_features
        self.scaler = StandardScaler()
    
    def recursive_feature_elimination(self, X, y, n_features=None):
        """
        Recursive Feature Elimination (RFE)
        Uses Random Forest importance for feature ranking
        """
        if n_features is None:
            n_features = min(self.max_features, X.shape[1])
        
        estimator = RandomForestRegressor(n_estimators=100, random_state=42)
        rfe = RFE(estimator=estimator, n_features_to_select=n_features)
        rfe.fit(X, y)
        
        selected_features = X.columns[rfe.support_].tolist()
        rankings = pd.DataFrame({
            'feature': X.columns,
            'rfe_rank': rfe.ranking_,
            'rfe_selected': rfe.support_
        })
        
        return selected_features, rankings
    
    def boruta_selection(self, X, y):
        """
        Boruta feature selection (simplified version)
        Uses Random Forest importance with statistical testing
        """
        try:
            from boruta import BorutaPy
            
            estimator = RandomForestRegressor(n_estimators=100, random_state=42)
            boruta = BorutaPy(
                estimator=estimator, 
                n_estimators='auto',
                verbose=0,
                random_state=42
            )
            
            boruta.fit(X.values, y.values)
            
            selected_features = X.columns[boruta.support_].tolist()
            rankings = pd.DataFrame({
                'feature': X.columns,
                'boruta_selected': boruta.support_,
                'boruta_rank': boruta.ranking_
            })
            
            return selected_features, rankings
            
        except ImportError:
            print("Boruta not available, using RFE instead")
            return self.recursive_feature_elimination(X, y)
    
    def permutation_importance(self, X, y, n_repeats=10):
        """
        Permutation importance using Random Forest
        Measures feature importance by shuffling values
        """
        from sklearn.inspection import permutation_importance
        
        estimator = RandomForestRegressor(n_estimators=100, random_state=42)
        estimator.fit(X, y)
        
        result = permutation_importance(
            estimator, X, y, 
            n_repeats=n_repeats, 
            random_state=42
        )
        
        importance_df = pd.DataFrame({
            'feature': X.columns,
            'permutation_importance': result.importances_mean,
            'permutation_std': result.importances_std
        }).sort_values('permutation_importance', ascending=False)
        
        # Select top features
        top_features = importance_df.head(self.max_features)['feature'].tolist()
        
        return top_features, importance_df
    
    def lasso_feature_selection(self, X, y):
        """
        LASSO feature selection with cross-validation
        Uses L1 regularization to shrink coefficients
        """
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        lasso = LassoCV(cv=5, random_state=42, max_iter=1000)
        lasso.fit(X_scaled, y)
        
        # Get non-zero coefficients
        nonzero_features = X.columns[lasso.coef_ != 0].tolist()
        
        importance_df = pd.DataFrame({
            'feature': X.columns,
            'lasso_coef': lasso.coef_,
            'lasso_selected': lasso.coef_ != 0
        }).sort_values('lasso_coef', key=abs, ascending=False)
        
        return nonzero_features, importance_df
    
    def univariate_selection(self, X, y):
        """
        Univariate feature selection using F-tests
        """
        selector = SelectKBest(score_func=f_regression, k=self.max_features)
        selector.fit(X, y)
        
        selected_features = X.columns[selector.get_support()].tolist()
        
        scores_df = pd.DataFrame({
            'feature': X.columns,
            'f_score': selector.scores_,
            'p_value': selector.pvalues_,
            'selected': selector.get_support()
        }).sort_values('f_score', ascending=False)
        
        return selected_features, scores_df
    
    def consensus_selection(self, X, y):
        """
        Consensus feature selection using multiple methods
        Returns features selected by majority of methods
        """
        # Get selections from all methods
        methods = {}
        
        # RFE
        rfe_features, _ = self.recursive_feature_elimination(X, y)
        methods['rfe'] = set(rfe_features)
        
        # Boruta (or RFE if Boruta unavailable)
        boruta_features, _ = self.boruta_selection(X, y)
        methods['boruta'] = set(boruta_features)
        
        # Permutation importance
        perm_features, _ = self.permutation_importance(X, y)
        methods['permutation'] = set(perm_features)
        
        # LASSO
        lasso_features, _ = self.lasso_feature_selection(X, y)
        methods['lasso'] = set(lasso_features)
        
        # Univariate
        uni_features, _ = self.univariate_selection(X, y)
        methods['univariate'] = set(uni_features)
        
        # Count votes
        feature_votes = {}
        for method_name, feature_set in methods.items():
            for feature in feature_set:
                if feature not in feature_votes:
                    feature_votes[feature] = 0
                feature_votes[feature] += 1
        
        # Select features with majority vote (selected by at least 3 methods)
        consensus_features = [
            feature for feature, votes in feature_votes.items() 
            if votes >= 3
        ]
        
        # Ensure we have at least min_features
        if len(consensus_features) < self.min_features:
            # Add top features by vote count
            top_features = sorted(feature_votes.items(), key=lambda x: x[1], reverse=True)
            additional_features = [f for f, v in top_features if f not in consensus_features]
            consensus_features.extend(additional_features[:self.min_features - len(consensus_features)])
        
        # Limit to max_features
        consensus_features = consensus_features[:self.max_features]
        
        # Create voting summary
        voting_summary = pd.DataFrame({
            'feature': list(feature_votes.keys()),
            'votes': list(feature_votes.values()),
            'selected': [f in consensus_features for f in feature_votes.keys()]
        }).sort_values('votes', ascending=False)
        
        return consensus_features, voting_summary, methods
    
    def select_features(self, data):
        """
        Main feature selection method
        Returns selected features and comprehensive report
        """
        # Prepare data
        if self.target_feature not in data.columns:
            raise ValueError(f"Target feature '{self.target_feature}' not found in data")
        
        # Separate features and target
        y = data[self.target_feature]
        X = data.drop(columns=[self.target_feature])
        
        # Remove non-numeric columns
        X_numeric = X.select_dtypes(include=[np.number])
        
        print(f"Starting feature selection on {X_numeric.shape[1]} features")
        
        # Get consensus selection
        selected_features, voting_summary, methods = self.consensus_selection(X_numeric, y)
        
        print(f"Selected {len(selected_features)} features")
        
        # Create comprehensive report
        report = {
            'selected_features': selected_features,
            'voting_summary': voting_summary,
            'methods_used': list(methods.keys()),
            'original_feature_count': X_numeric.shape[1],
            'selected_feature_count': len(selected_features),
            'reduction_percent': (1 - len(selected_features) / X_numeric.shape[1]) * 100
        }
        
        return selected_features, report

def main():
    """Main entry point for orchestrator integration."""
    # Create sample data for testing
    np.random.seed(42)
    n_samples = 1000
    n_features = 30

    # Generate synthetic data with some informative features
    X = pd.DataFrame(np.random.randn(n_samples, n_features),
                     columns=[f'feature_{i}' for i in range(n_features)])

    # Create target with relationship to first 5 features
    y = (X['feature_0'] * 0.5 +
         X['feature_1'] * 0.3 +
         X['feature_2'] * 0.2 +
         X['feature_3'] * 0.1 +
         X['feature_4'] * 0.05 +
         np.random.randn(n_samples) * 0.1)

    data = X.copy()
    data['returns'] = y

    # Test feature selection
    selector = FeatureSelector()
    selected_features, report = selector.select_features(data)

    print("\n=== Feature Selection Results ===")
    print(f"Original features: {report['original_feature_count']}")
    print(f"Selected features: {report['selected_feature_count']}")
    print(f"Reduction: {report['reduction_percent']:.1f}%")
    print(f"\nSelected features: {selected_features}")

    print("\n=== Voting Summary ===")
    print(report['voting_summary'].head(10))


if __name__ == "__main__":
    main()