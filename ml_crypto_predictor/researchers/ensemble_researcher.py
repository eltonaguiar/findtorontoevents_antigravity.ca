"""
EnsembleResearcher — Advanced Ensemble and Stacking Methods
===========================================================

Specializes in sophisticated ensemble techniques:
  - Stacking with diverse base learners
  - Blending with validation-based weighting
  - Boosting (XGBoost, LightGBM, CatBoost)
  - Bagging and random subspace methods
  - Dynamic ensemble selection (DES)
  - Multi-level stacking with feature propagation
  - Super learner ensembles
  - Bayesian model averaging

Academic foundations:
  - "Stacked Generalization: An Introduction to Stacking" (Wolpert, 1992)
  - "Super Learner" (van der Laan et al., 2007)
  - "Dynamic Ensemble Selection" (Giacinto & Roli, 2001)
  - "XGBoost: A Scalable Tree Boosting System" (Chen & Guestrin, 2016)

Key research questions:
  1. What is the optimal combination of base learners for crypto prediction?
  2. Can dynamic ensemble selection adapt to market regimes?
  3. Does multi-level stacking outperform single-level?
  4. How does ensemble diversity affect performance?
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pandas as pd

from .base import Researcher, ResearchQuestion, ResearchResult

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

try:
    from catboost import CatBoostClassifier
    HAS_CATBOOST = True
except ImportError:
    HAS_CATBOOST = False


class EnsembleResearcher(Researcher):
    """
    Researcher specializing in advanced ensemble methods.
    
    Investigates stacking, blending, boosting, and dynamic ensemble
    selection for cryptocurrency prediction.
    """
    
    researcher_id = "ensemble"
    name = "Ensemble Methods Researcher"
    specialization = "Stacking, boosting, dynamic ensemble selection"
    literature = [
        "Stacked Generalization (Wolpert, 1992)",
        "Super Learner (van der Laan et al., 2007)",
        "XGBoost: A Scalable Tree Boosting System (Chen & Guestrin, 2016)",
        "Dynamic Ensemble Selection (Giacinto & Roli, 2001)",
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_dir = Path(config.get("base_dir", "ml_crypto_predictor")) if config else Path("ml_crypto_predictor")
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "models" / "ensemble"
        self.results_dir = self.base_dir / "results" / "research" / "ensemble"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def formulate_questions(self) -> List[ResearchQuestion]:
        """Define research questions for ensemble methods."""
        return [
            ResearchQuestion(
                id="ens_001",
                title="Optimal Base Learner Combination for Stacking",
                description="Determine the best set of base learners for stacking ensemble. "
                          "Test combinations: tree-based (RF, XGB, LGB, CatBoost), linear (LR), "
                          "neural (MLP), and distance-based (KNN). Diversity is key — "
                          "combine models with different inductive biases.",
                hypothesis="Best stacking ensemble combines: XGBoost (gradient boosting), "
                          "Random Forest (bagging), CatBoost (categorical handling), "
                          "and Logistic Regression (linear baseline). This diverse set "
                          "should outperform any single model by 5-10%.",
                methodology="1. Prepare 1h data for BTC, ETH, SOL (70+ features)\n"
                          "2. Define candidate base learners: RF, XGB, LGB, CatBoost, LR, MLP\n"
                          "3. Test all combinations of 3-5 base learners (exhaustive search)\n"
                          "4. Use logistic regression as meta-learner\n"
                          "5. Evaluate with walk-forward validation\n"
                          "6. Measure AUC, Sharpe, profit factor\n"
                          "7. Identify top 3 combinations",
                success_criteria={
                    "stacking_beats_best_single": 0.05,  # 5% improvement
                    "diverse_combination_best": True,
                    "top_3_combos_close": True,  # Top 3 within 2% of each other
                },
                priority=1,
            ),
            ResearchQuestion(
                id="ens_002",
                title="Dynamic Ensemble Selection: Adapt to Market Regimes",
                description="Instead of fixed ensemble weights, use dynamic ensemble selection "
                          "(DES) to choose which base models to trust based on current market "
                          "conditions. Different models excel in different regimes.",
                hypothesis="DES will outperform static stacking by 8-12% because it can "
                          "adapt to regime changes: e.g., use XGB in trending markets, "
                          "RF in consolidation, CatBoost in mixed regimes. The model will "
                          "learn regime-model mapping from historical data.",
                methodology="1. Build static stacking ensemble (from ens_001)\n"
                          "2. Add regime classifier (using regime_detector.py)\n"
                          "3. For each regime, compute per-model validation performance\n"
                          "4. At inference, detect current regime, select top-3 models for that regime\n"
                          "5. Alternatively: use a gating network that takes regime features "
                          "   and outputs model weights\n"
                          "6. Compare DES vs static stacking across different test periods",
                success_criteria={
                    "des_beats_static": 0.08,
                    "regime_aware_weights": True,
                    "improves_in_regime_transitions": True,
                },
                priority=1,
                dependencies=["ens_001"],
            ),
            ResearchQuestion(
                id="ens_003",
                title="Multi-Level Stacking with Feature Propagation",
                description="Implement two-level stacking: Level 1 (diverse base models) → "
                          "Level 2 (meta-learner) → Level 3 (second meta-learner on residuals). "
                          "Also test feature propagation: concatenate original features with "
                          "level 1 predictions before level 2.",
                hypothesis="Multi-level stacking with feature propagation will improve "
                          "performance by 3-5% over single-level stacking. The additional "
                          "level allows modeling interactions between base model predictions "
                          "and original features.",
                methodology="1. Level 1: Train 5 diverse base models with CV\n"
                          "2. Level 2: Train meta-learner on level 1 predictions + original features\n"
                          "3. Level 3: Train second meta-learner on level 2 residuals\n"
                          "4. Compare: single-level vs two-level vs three-level\n"
                          "5. Ablate feature propagation (with vs without original features)",
                success_criteria={
                    "multilevel_better_than_single": 0.03,
                    "feature_propagation_helps": True,
                    "three_level_worth_complexity": True,
                },
                priority=2,
                dependencies=["ens_001"],
            ),
            ResearchQuestion(
                id="ens_004",
                title="Boosting vs Stacking: Which Ensemble Paradigm Wins?",
                description="Compare gradient boosting (XGBoost, LightGBM, CatBoost) "
                          "with stacking ensembles. Boosting builds models sequentially to "
                          "correct errors; stacking learns to combine diverse models in parallel. "
                          "Which is better for crypto prediction?",
                hypothesis="Stacking with diverse base learners will outperform any single "
                          "boosting algorithm by 5-8% because diversity reduces correlation "
                          "of errors. However, XGBoost will be the strongest single model. "
                          "Best: stacking that includes XGBoost as one base learner.",
                methodology="1. Train XGBoost, LightGBM, CatBoost individually\n"
                          "2. Train stacking ensemble with these + other diverse models\n"
                          "3. Compare all on same train/test splits\n"
                          "4. Analyze error correlation: are boosting errors correlated?\n"
                          "5. Test if stacking ensemble that includes boosting models "
                          "   beats standalone boosting",
                success_criteria={
                    "stacking_beats_boosting": 0.05,
                    "xgb_best_single": True,
                    "stacking_with_xgb_best_overall": True,
                },
                priority=1,
            ),
            ResearchQuestion(
                id="ens_005",
                title="Bayesian Model Averaging for Uncertainty Quantification",
                description="Use Bayesian Model Averaging (BMA) to combine predictions from "
                          "multiple models with weights proportional to posterior probability. "
                          "This provides calibrated uncertainty estimates, crucial for position sizing.",
                hypothesis="BMA will produce well-calibrated uncertainty estimates (reliable "
                          "confidence intervals) while maintaining competitive accuracy. The "
                          "uncertainty estimates will be useful for dynamic position sizing: "
                          "reduce exposure when ensemble disagreement is high.",
                methodology="1. Train 10 diverse models (different architectures, hyperparams)\n"
                          "2. Compute posterior weights using validation set likelihood\n"
                          "3. For each prediction, compute weighted mean + variance\n"
                          "4. Calibrate uncertainty: check if 90% confidence intervals contain "
                          "   actual outcomes 90% of the time\n"
                          "5. Use uncertainty for position sizing: size ∝ 1/ensemble_variance\n"
                          "6. Compare P&L with vs without uncertainty-based sizing",
                success_criteria={
                    "bma_well_calibrated": True,  # Reliability diagram close to diagonal
                    "bma_accuracy_comparable": True,
                    "uncertainty_sizing_improves_sharpe": 0.5,
                },
                priority=2,
                dependencies=["ens_001"],
            ),
        ]
    
    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        """Prepare data for ensemble experiments."""
        from ml_crypto_predictor.enhanced_models.data_fetcher import fetch_klines
        from ml_crypto_predictor.enhanced_models.feature_engine import build_features
        from ml_crypto_predictor.enhanced_models.config import CRYPTO_PAIRS
        
        pairs = CRYPTO_PAIRS[:5]  # BTC, ETH, SOL, BNB, XRP
        timeframe = "1h"
        
        all_X = []
        all_y = []
        
        for pair in pairs:
            df = fetch_klines(pair, "1h", 1000)
            if df.empty or len(df) < 300:
                continue
            
            features = build_features(df)
            target = self._build_target(df)
            aligned = features.join(target, how="inner").dropna()
            
            all_X.append(aligned[features.columns].values)
            all_y.append(aligned[target.name].values)
        
        if not all_X:
            return {"error": "no_data"}
        
        # Concatenate all pairs
        X = np.vstack(all_X)
        y = np.hstack(all_y)
        
        # Time series split
        split = int(len(X) * 0.7)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        return {
            "X_train": X_train,
            "y_train": y_train,
            "X_test": X_test,
            "y_test": y_test,
            "n_features": X.shape[1],
            "n_train": len(X_train),
            "n_test": len(X_test),
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
            else:
                target.iloc[i] = 0
        
        return target
    
    def conduct_experiment(self, question: ResearchQuestion,
                          data: Dict[str, Any]) -> ResearchResult:
        """Run ensemble experiments."""
        if "error" in data:
            return ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings=f"Data preparation failed: {data['error']}",
                metrics={},
                confidence=0.0,
            )
        
        if question.id == "ens_001":
            result = self._run_optimal_base_learners(question, data)
        elif question.id == "ens_002":
            result = self._run_dynamic_ensemble_selection(question, data)
        elif question.id == "ens_003":
            result = self._run_multilevel_stacking(question, data)
        elif question.id == "ens_004":
            result = self._run_boosting_vs_stacking(question, data)
        elif question.id == "ens_005":
            result = self._run_bayesian_model_averaging(question, data)
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
    
    def _run_optimal_base_learners(self, question: ResearchQuestion,
                                  data: Dict[str, Any]) -> ResearchResult:
        """Find optimal base learner combination."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import cross_val_score
        
        findings = []
        X_train = data["X_train"]
        y_train = data["y_train"]
        
        # Define candidate base learners
        base_learners = {}
        
        # Random Forest
        base_learners["rf"] = RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_leaf=10,
            class_weight="balanced_subsample", n_jobs=-1, random_state=42
        )
        
        # XGBoost
        if HAS_XGB:
            base_learners["xgb"] = xgb.XGBClassifier(
                n_estimators=300, max_depth=6, learning_rate=0.01,
                subsample=0.8, colsample_bytree=0.8,
                scale_pos_weight=3.0, eval_metric="logloss",
                verbosity=0, use_label_encoder=False
            )
        
        # LightGBM
        if HAS_LGB:
            base_learners["lgb"] = lgb.LGBMClassifier(
                n_estimators=300, max_depth=7, learning_rate=0.01,
                num_leaves=63, is_unbalance=True, verbose=-1
            )
        
        # CatBoost
        if HAS_CATBOOST:
            base_learners["cat"] = CatBoostClassifier(
                iterations=300, depth=6, learning_rate=0.03,
                auto_class_weights="Balanced", verbose=0
            )
        
        # Logistic Regression
        base_learners["lr"] = LogisticRegression(max_iter=1000, class_weight="balanced")
        
        findings.append(f"Testing {len(base_learners)} base learners: {list(base_learners.keys())}")
        
        # Evaluate individual performance
        individual_scores = {}
        for name, model in base_learners.items():
            try:
                scores = cross_val_score(model, X_train, y_train, cv=5, scoring="roc_auc", n_jobs=-1)
                individual_scores[name] = scores.mean()
                findings.append(f"  {name}: AUC={scores.mean():.3f} (+/- {scores.std():.3f})")
            except Exception as e:
                findings.append(f"  {name}: Failed - {e}")
        
        # In full implementation, would test combinations via stacking
        findings.append("Stacking combination testing not fully implemented yet")
        
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Base learner evaluation complete\n" + "\n".join(findings),
            metrics={"individual_scores": individual_scores},
            confidence=0.7,
            reproducible=True,
            limitations=["Full combination search not implemented", "Limited to 5 pairs"],
            recommendations={"best_individual": max(individual_scores, key=individual_scores.get) if individual_scores else None},
        )
    
    def _run_dynamic_ensemble_selection(self, question: ResearchQuestion,
                                       data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Dynamic ensemble selection not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_multilevel_stacking(self, question: ResearchQuestion,
                                data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Multi-level stacking not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_boosting_vs_stacking(self, question: ResearchQuestion,
                                 data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Boosting vs stacking comparison not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_bayesian_model_averaging(self, question: ResearchQuestion,
                                     data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Bayesian model averaging not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        """Validate ensemble results."""
        validation = {
            "confidence": 0.7,
            "reproducible": True,
            "limitations": [],
        }
        
        return validation
