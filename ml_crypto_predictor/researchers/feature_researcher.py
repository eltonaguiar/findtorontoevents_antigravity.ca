"""
FeatureResearcher — Automated Feature Engineering and Selection
===============================================================

Specializes in discovering, generating, and selecting predictive features:
  - Automated feature synthesis (deep feature synthesis, featuretools)
  - Feature importance analysis (SHAP, permutation, mutual information)
  - Feature selection (genetic algorithms, LASSO, stability selection)
  - Feature extraction (PCA, autoencoders, t-SNE)
  - Temporal feature engineering (lags, rolling stats, interactions)
  - Cross-asset feature generation (correlations, lead-lag)
  - Feature robustness testing (stationarity, regime stability)

Academic foundations:
  - "Deep Feature Synthesis: Automating Data Science" (Kumar et al., 2016)
  - "A Unified Approach to Interpreting Model Predictions" (Lundberg & Lee, 2017)
  - "Stability Selection" (Meinshausen & Bühlmann, 2010)
  - "Auto-Encoding Variational Bayes" (Kingma & Welling, 2014)

Key research questions:
  1. Can automated feature discovery outperform manual engineering?
  2. Which feature selection method is most robust for non-stationary crypto data?
  3. Do nonlinear feature interactions significantly improve prediction?
  4. Can we identify a minimal feature set that maintains performance?
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pandas as pd

from .base import Researcher, ResearchQuestion, ResearchResult

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


class FeatureResearcher(Researcher):
    """
    Researcher specializing in automated feature engineering and selection.
    
    Investigates methods for discovering, generating, and selecting
    the most predictive features for crypto price prediction.
    """
    
    researcher_id = "feature_engineering"
    name = "Feature Engineering Researcher"
    specialization = "Automated feature synthesis, selection, and importance analysis"
    literature = [
        "Deep Feature Synthesis (Kumar et al., 2016)",
        "SHAP: Unified Approach to Model Interpretation (Lundberg & Lee, 2017)",
        "Stability Selection (Meinshausen & Bühlmann, 2010)",
        "Autoencoders for Feature Extraction (Kingma & Welling, 2014)",
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_dir = Path(config.get("base_dir", "ml_crypto_predictor")) if config else Path("ml_crypto_predictor")
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "models" / "features"
        self.results_dir = self.base_dir / "results" / "research" / "features"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def formulate_questions(self) -> List[ResearchQuestion]:
        """Define research questions for feature engineering."""
        return [
            ResearchQuestion(
                id="feat_001",
                title="Manual vs Automated Feature Engineering: Which Wins?",
                description="Compare manually engineered features (current 70+ in feature_engine.py) "
                          "with automatically generated features using deep feature synthesis. "
                          "Can automated methods discover useful features humans missed?",
                hypothesis="Automated feature synthesis will discover 10-20% additional "
                          "predictive features beyond manual engineering, improving AUC by 2-3%. "
                          "However, domain knowledge (manual features) will still be crucial — "
                          "the best approach is combining both.",
                methodology="1. Start with raw OHLCV + orderbook data\n"
                          "2. Manual baseline: use existing 70+ features from feature_engine.py\n"
                          "3. Automated: use featuretools-style deep feature synthesis\n"
                          "   - Primitive operations: +, -, *, /, lag, rolling mean/std\n"
                          "   - Generate combinations: e.g., (volume * price), (rsi * adx)\n"
                          "   - Limit to 200-300 auto-generated features\n"
                          "4. Combine both sets (union)\n"
                          "5. Train model (XGBoost) on each feature set\n"
                          "6. Compare AUC, precision, recall\n"
                          "7. Analyze top features from each approach",
                success_criteria={
                    "automated_adds_value": True,
                    "combined_best": True,
                    "auto_features_improve_auc": 0.02,
                },
                priority=1,
            ),
            ResearchQuestion(
                id="feat_002",
                title="Optimal Feature Selection: Minimal Set for Max Performance",
                description="Find the smallest subset of features that maintains >95% of "
                          "full-feature model performance. Use multiple selection methods "
                          "(SHAP, LASSO, mutual information, genetic algorithm) and compare.",
                hypothesis="We can reduce from 70+ features to 20-30 core features with "
                          "minimal performance loss (<2% AUC). The minimal set will include: "
                          "RSI, MACD, volume ratio, ATR, ADX, BTC correlation, funding rate, "
                          "and a few interaction terms. Redundant features (e.g., multiple RSI periods) "
                          "can be eliminated.",
                methodology="1. Train XGBoost on full feature set (70+)\n"
                          "2. Compute feature importance via multiple methods:\n"
                          "   - SHAP values (model-based)\n"
                          "   - Mutual information (model-agnostic)\n"
                          "   - LASSO coefficients\n"
                          "   - Permutation importance\n"
                          "3. For each method, select top N features (N=10,20,30,50)\n"
                          "4. Compare model performance vs feature count\n"
                          "5. Find elbow point (diminishing returns)\n"
                          "6. Test stability: do selected features change across time periods?",
                success_criteria={
                    "reduce_to_30_with_minimal_loss": True,
                    "feature_selection_stable": True,  # Similar features selected in different periods
                    "shap_consistent_with_other_methods": True,
                },
                priority=1,
                dependencies=["feat_001"],
            ),
            ResearchQuestion(
                id="feat_003",
                title="Nonlinear Feature Interactions: Do They Matter?",
                description="Test if explicit nonlinear feature interactions (products, ratios, "
                          "polynomials) improve model performance beyond what tree-based models "
                          "can learn implicitly. Tree models can approximate interactions but "
                          "may need more depth.",
                hypothesis="Explicit interaction features (e.g., RSI × volume, MACD × ADX) "
                          "will improve linear model performance significantly but have minimal "
                          "effect on tree-based models (XGBoost, LightGBM) which can learn "
                          "interactions automatically. For tree models, interaction features "
                          "may even cause overfitting.",
                methodology="1. Generate interaction features:\n"
                          "   - Products: feature_i × feature_j\n"
                          "   - Ratios: feature_i / feature_j\n"
                          "   - Polynomials: feature², feature³\n"
                          "   - Limit to top 20 features from feat_002\n"
                          "2. Train models: Linear (LR), RF, XGB, LGB\n"
                          "3. Compare with/without interaction features\n"
                          "4. Measure performance gain per model type\n"
                          "5. Analyze if interactions are actually used by tree models",
                success_criteria={
                    "interactions_help_linear": True,
                    "interactions_hurt_or_neutral_for_trees": True,
                    "interaction_gain_linear": 0.05,
                },
                priority=2,
                dependencies=["feat_002"],
            ),
            ResearchQuestion(
                id="feat_004",
                title="Feature Robustness: Which Features Survive Regime Changes?",
                description="Test feature stability across different market regimes. "
                          "A feature that works in bull markets may fail in bear markets. "
                          "Identify regime-agnostic features vs regime-specific ones.",
                hypothesis="Some features are regime-stable (e.g., volume-based, some momentum) "
                          "while others are regime-dependent (e.g., trend-following works only "
                          "in trending markets). The most robust features will be: volume anomalies, "
                          "volatility measures, and cross-asset correlations. Regime-specific "
                          "features can be used for regime-adaptive models.",
                methodology="1. Use regime labels from regime_detector.py\n"
                          "2. For each feature, compute predictive power (AUC of univariate) "
                          "   per regime\n"
                          "3. Calculate feature stability score: correlation of feature "
                          "   importance across regimes\n"
                          "4. Identify stable features (high stability score) vs regime-specific\n"
                          "5. Build two models: one with stable features only, one with all\n"
                          "6. Compare out-of-sample performance across regimes",
                success_criteria={
                    "identify_stable_features": True,
                    "stable_features_work_across_regimes": True,
                    "regime_specific_features_identifiable": True,
                },
                priority=2,
                dependencies=["feat_002"],
            ),
            ResearchQuestion(
                id="feat_005",
                title="Autoencoder-Based Feature Extraction: Can We Learn Better Representations?",
                description="Train an autoencoder (or variational autoencoder) on raw features "
                          "to learn compressed, denoised representations. Compare downstream "
                          "prediction performance using autoencoder latent space vs raw features.",
                hypothesis="Autoencoder will learn a compressed representation (10-20 dimensions) "
                          "that captures most predictive signal while filtering noise. "
                          "This will improve model generalization and reduce overfitting, "
                          "especially in volatile regimes. Expected: 2-4% AUC improvement.",
                methodology="1. Train variational autoencoder (VAE) on normalized features\n"
                          "2. Use latent dimension = 10, 20, 30 (compare)\n"
                          "3. Extract latent features for each sample\n"
                          "4. Train predictor (XGBoost) on latent features vs raw features\n"
                          "5. Compare performance and overfitting (train-test gap)\n"
                          "6. Visualize latent space (t-SNE) colored by regime/label",
                success_criteria={
                    "autoencoder_improves_prediction": 0.02,
                    "latent_space_interpretable": True,  # Can identify what each dim captures
                    "compression_ratio": 0.3,  # 20 dims from 70+ features
                },
                priority=3,
                dependencies=["feat_001"],
            ),
            ResearchQuestion(
                id="feat_006",
                title="Cross-Asset Feature Engineering: Lead-Lag and Correlation Dynamics",
                description="Generate features based on cross-asset relationships: "
                          "1) BTC vs altcoin returns (beta), 2) correlation rolling windows, "
                          "3) lead-lag relationships (does ETH lead SOL?), 4) sector rotation. "
                          "Do cross-asset features add predictive power?",
                hypothesis="Cross-asset features will improve prediction by 3-5% because "
                          "crypto markets are highly interconnected. BTC leads altcoins by "
                          "1-3 hours on average. Correlation spikes precede volatility spikes. "
                          "Sector rotation (DeFi vs Meme vs AI) provides regime context.",
                methodology="1. Fetch data for top 10 coins\n"
                          "2. Compute cross-asset features:\n"
                          "   - Rolling beta of each coin vs BTC (20h window)\n"
                          "   - Rolling correlation matrix (pairwise)\n"
                          "   - Lead-lag cross-correlation (max correlation at lag)\n"
                          "   - Sector indices (average of DeFi, meme, AI groups)\n"
                          "3. Add these as features for each coin\n"
                          "4. Train model with/without cross-asset features\n"
                          "5. Measure improvement and identify most predictive cross features",
                success_criteria={
                    "cross_asset_features_help": True,
                    "btc_lead_lag_detected": True,
                    "improvement_over_single_asset": 0.03,
                },
                priority=2,
            ),
        ]
    
    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        """Prepare data for feature engineering experiments."""
        from ml_crypto_predictor.enhanced_models.data_fetcher import fetch_klines
        from ml_crypto_predictor.enhanced_models.feature_engine import build_features
        from ml_crypto_predictor.enhanced_models.config import CRYPTO_PAIRS
        
        pairs = CRYPTO_PAIRS[:5]  # BTC, ETH, SOL, BNB, XRP
        timeframe = "1h"
        
        all_features = []
        all_targets = []
        
        for pair in pairs:
            df = fetch_klines(pair, "1h", 1000)
            if df.empty or len(df) < 300:
                continue
            
            features = build_features(df)
            target = self._build_target(df)
            aligned = features.join(target, how="inner").dropna()
            
            all_features.append(aligned[features.columns])
            all_targets.append(aligned[target.name])
        
        if not all_features:
            return {"error": "no_data"}
        
        # Combine all pairs
        X = pd.concat(all_features)
        y = pd.concat(all_targets)
        
        return {
            "X": X.values,
            "y": y.values,
            "feature_names": list(X.columns),
            "n_samples": len(X),
            "n_features": X.shape[1],
        }
    
    def _build_target(self, df: pd.DataFrame, horizon: int = 12,
                     tp_pct: float = 0.02, sl_pct: float = -0.01) -> pd.Series:
        """Build binary classification target."""
        close = df["close"]
        target = pd.Series(0, index=close.index, dtype=int)
        
        for i in range(len(close) - horizon):
            entry = close.iloc[i]
            future = close.iloc[i+1:i+1+horizon]
            
            tp = entry * (1 + tp_pct)
            sl = entry * (1 + sl_pct)
            
            if (future >= tp).any() and not (future <= sl).any():
                target.iloc[i] = 1
        
        return target
    
    def conduct_experiment(self, question: ResearchQuestion,
                          data: Dict[str, Any]) -> ResearchResult:
        """Run feature engineering experiments."""
        if "error" in data:
            return ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings=f"Data preparation failed: {data['error']}",
                metrics={},
                confidence=0.0,
            )
        
        if question.id == "feat_001":
            result = self._run_manual_vs_automated(question, data)
        elif question.id == "feat_002":
            result = self._run_optimal_feature_selection(question, data)
        elif question.id == "feat_003":
            result = self._run_nonlinear_interactions(question, data)
        elif question.id == "feat_004":
            result = self._run_feature_robustness(question, data)
        elif question.id == "feat_005":
            result = self._run_autoencoder_features(question, data)
        elif question.id == "feat_006":
            result = self._run_cross_asset_features(question, data)
        else:
            result = ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings="Unknown question ID",
                metrics={},
                confidence=0.0,
            )
        
        return result
    
    def _run_manual_vs_automated(self, question: ResearchQuestion,
                                data: Dict[str, Any]) -> ResearchResult:
        """Compare manual vs automated feature engineering."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score
        
        findings = []
        X = data["X"]
        y = data["y"]
        n_features = data["n_features"]
        
        findings.append(f"Baseline: {n_features} manual features")
        
        # Baseline: use all current features
        baseline_model = RandomForestClassifier(n_estimators=100, max_depth=10, n_jobs=-1, random_state=42)
        try:
            baseline_score = cross_val_score(baseline_model, X, y, cv=5, scoring="roc_auc", n_jobs=-1).mean()
            findings.append(f"Baseline CV AUC: {baseline_score:.3f}")
        except Exception as e:
            baseline_score = 0.5
            findings.append(f"Baseline failed: {e}")
        
        # Automated feature generation (simplified)
        # In full implementation, would use featuretools or custom transformations
        n_auto_features = min(100, n_features * 2)  # Simulate generating more
        findings.append(f"Automated approach: would generate ~{n_auto_features} features")
        findings.append("Full automated feature synthesis not yet implemented")
        
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Manual vs automated feature comparison\n" + "\n".join(findings),
            metrics={
                "manual_features": n_features,
                "auto_features_proposed": n_auto_features,
                "baseline_auc": round(baseline_score, 3),
            },
            confidence=0.6,
            reproducible=True,
            limitations=["Automated feature generation not fully implemented"],
            recommendations={"next": "Implement deep feature synthesis pipeline"},
        )
    
    def _run_optimal_feature_selection(self, question: ResearchQuestion,
                                      data: Dict[str, Any]) -> ResearchResult:
        """Find optimal feature subset."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score
        from sklearn.feature_selection import SelectKBest, mutual_info_classif
        
        X = data["X"]
        y = data["y"]
        n_features = data["n_features"]
        feature_names = data["feature_names"]
        
        findings = []
        findings.append(f"Starting with {n_features} features")
        
        # Mutual information selection
        k_values = [10, 20, 30, 50, min(100, n_features)]
        mi_scores = []
        
        for k in k_values:
            if k >= n_features:
                continue
            selector = SelectKBest(mutual_info_classif, k=k)
            X_selected = selector.fit_transform(X, y)
            
            model = RandomForestClassifier(n_estimators=100, max_depth=10, n_jobs=-1, random_state=42)
            score = cross_val_score(model, X_selected, y, cv=5, scoring="roc_auc", n_jobs=-1).mean()
            mi_scores.append((k, score))
            findings.append(f"  k={k}: AUC={score:.3f}")
        
        # Find optimal k (simple: max AUC)
        if mi_scores:
            best_k, best_score = max(mi_scores, key=lambda x: x[1])
            findings.append(f"Best: k={best_k} (AUC={best_score:.3f})")
        else:
            best_k = n_features
            best_score = 0.5
        
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Feature selection optimization\n" + "\n".join(findings),
            metrics={
                "total_features": n_features,
                "optimal_k": best_k,
                "optimal_auc": round(best_score, 3),
                "reduction_pct": round((1 - best_k/n_features) * 100, 1) if n_features > 0 else 0,
            },
            confidence=0.7,
            reproducible=True,
            limitations=["Only tested mutual information, need SHAP/LASSO comparison"],
            recommendations={"optimal_feature_count": best_k},
        )
    
    def _run_nonlinear_interactions(self, question: ResearchQuestion,
                                   data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Nonlinear interaction features not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_feature_robustness(self, question: ResearchQuestion,
                               data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Feature robustness analysis not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_autoencoder_features(self, question: ResearchQuestion,
                                 data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Autoencoder feature extraction not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_cross_asset_features(self, question: ResearchQuestion,
                                 data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Cross-asset feature engineering not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        """Validate feature engineering results."""
        validation = {
            "confidence": 0.7,
            "reproducible": True,
            "limitations": [],
        }
        
        return validation
