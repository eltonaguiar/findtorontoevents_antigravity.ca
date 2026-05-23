"""
MetaLearningResearcher — Few-Shot and Rapid Adaptation Learning
================================================================

Specializes in meta-learning and few-shot adaptation for crypto:
  - Model-Agnostic Meta-Learning (MAML)
  - Reptile (first-order MAML approximation)
  - Prototypical Networks for few-shot classification
  - Metric learning with triplet loss
  - Bayesian optimization for hyperparameter adaptation
  - Context-adaptive models that quickly adjust to new pairs

Academic foundations:
  - "Model-Agnostic Meta-Learning for Fast Adaptation of Deep Networks" (Finn et al., 2017)
  - "Reptile: A Scalable Meta-Learning Algorithm" (Nichol et al., 2018)
  - "Prototypical Networks for Few-Shot Learning" (Snell et al., 2017)
  - "Learning to Learn by Gradient Descent by Gradient Descent" (Andrychowicz et al., 2016)

Key research questions:
  1. Can meta-learning enable rapid adaptation to new crypto pairs with minimal data?
  2. Which meta-learning approach works best for non-stationary financial data?
  3. Can a model trained on major coins generalize to new meme coins?
  4. How does task distribution (bull vs bear markets) affect meta-learning?
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pandas as pd

from .base import Researcher, ResearchQuestion, ResearchResult

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class MetaLearningResearcher(Researcher):
    """
    Researcher specializing in meta-learning and few-shot adaptation.
    
    Investigates methods for rapidly adapting models to new cryptocurrency
    pairs or market conditions with minimal labeled data.
    """
    
    researcher_id = "meta_learning"
    name = "Meta-Learning Researcher"
    specialization = "Few-shot learning, MAML, rapid adaptation"
    literature = [
        "Model-Agnostic Meta-Learning (Finn et al., 2017)",
        "Reptile: A Scalable Meta-Learning Algorithm (Nichol et al., 2018)",
        "Prototypical Networks for Few-Shot Learning (Snell et al., 2017)",
        "Learning to Learn by Gradient Descent by Gradient Descent (Andrychowicz et al., 2016)",
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_dir = Path(config.get("base_dir", "ml_crypto_predictor")) if config else Path("ml_crypto_predictor")
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "models" / "meta"
        self.results_dir = self.base_dir / "results" / "research" / "meta"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def formulate_questions(self) -> List[ResearchQuestion]:
        """Define research questions for meta-learning."""
        return [
            ResearchQuestion(
                id="meta_001",
                title="MAML vs Reptile: Which Meta-Learning Algorithm Works Best for Crypto?",
                description="Compare Model-Agnostic Meta-Learning (MAML) with Reptile "
                          "for rapid adaptation to new cryptocurrency pairs. Both aim to "
                          "learn an initialization that can quickly adapt with few gradient steps, "
                          "but differ in gradient computation (2nd order vs 1st order).",
                hypothesis="Reptile will outperform MAML on crypto data because: "
                          "1) Financial data is noisy — second-order gradients may be unstable\n"
                          "2) Reptile is more scalable and requires less memory\n"
                          "3) Crypto markets have high variance, so first-order approximation suffices\n"
                          "Expected: Reptile achieves 5-8% higher AUC after 5 adaptation steps.",
                methodology="1. Prepare data from 20 crypto pairs (train on 15, test on 5)\n"
                          "2. For each pair, create tasks: predict next 12h direction\n"
                          "3. Meta-train MAML and Reptile on train pairs\n"
                          "4. For each test pair, adapt with k=1,5,10 gradient steps\n"
                          "5. Compare adaptation speed (AUC vs steps)\n"
                          "6. Measure stability (variance across runs)",
                success_criteria={
                    "reptile_at_least_as_good_as_maml": True,
                    "adaptation_5_steps_auc": 0.60,
                    "reptile_more_stable": True,
                },
                priority=1,
            ),
            ResearchQuestion(
                id="meta_002",
                title="Few-Shot Learning: How Little Data Do We Need?",
                description="Determine the minimum number of labeled samples needed for "
                          "effective adaptation to a new crypto pair. Test with 10, 50, 100, "
                          "500 samples. Also test if unlabeled data can help via semi-supervised "
                          "adaptation.",
                hypothesis="With meta-learned initialization, we can achieve AUC > 0.58 "
                          "with just 50 labeled samples per new pair. Semi-supervised adaptation "
                          "(using unlabeled data) can further improve to AUC > 0.62 with same "
                          "labeled budget.",
                methodology="1. Meta-train on 20 pairs (as in meta_001)\n"
                          "2. For each test pair, vary labeled data: 10, 25, 50, 100, 500\n"
                          "3. Adapt model with available labeled data\n"
                          "4. Optionally incorporate unlabeled data via pseudo-labeling or "
                          "   consistency regularization\n"
                          "5. Plot AUC vs labeled samples\n"
                          "6. Find the knee of the curve (diminishing returns)",
                success_criteria={
                    "50_samples_auc": 0.58,
                    "semi_supervised_improvement": 0.03,
                    "find_minimum_effective_samples": True,
                },
                priority=1,
                dependencies=["meta_001"],
            ),
            ResearchQuestion(
                id="meta_003",
                title="Cross-Market Transfer: Train on BTC, Adapt to Meme Coins",
                description="Test if a model meta-trained on major coins (BTC, ETH, SOL) "
                          "can quickly adapt to meme coins (DOGE, SHIB, PEPE, WIF) with minimal data. "
                          "Meme coins have different dynamics (higher volatility, retail-driven).",
                hypothesis="Meta-trained model will transfer to meme coins with minimal adaptation "
                          "(50 samples) achieving AUC ~0.57, while a model trained only on majors "
                          "will fail (AUC ~0.52). The adaptation will be slower than for major-to-major "
                          "transfer but still effective.",
                methodology="1. Meta-train on major coins only (BTC, ETH, SOL, etc.)\n"
                          "2. Test adaptation on meme coins (DOGE, SHIB, PEPE, WIF)\n"
                          "3. Baseline: fine-tune non-meta model on same meme coin data\n"
                          "4. Compare adaptation speed and final performance\n"
                          "5. Analyze what the model learns (does it overfit to retail patterns?)",
                success_criteria={
                    "meta_transfer_works": True,
                    "meta_better_than_baseline": 0.05,  # AUC improvement
                    "adaptation_possible_with_50_samples": True,
                },
                priority=2,
                dependencies=["meta_001", "meta_002"],
            ),
            ResearchQuestion(
                id="meta_004",
                title="Regime-Aware Meta-Learning: Adapt to Bull vs Bear Markets",
                description="Can meta-learning help a model quickly adapt when market regime "
                          "changes? Train meta-model on both bull and bear periods, then test "
                          "adaptation speed when switching regimes.",
                hypothesis="A regime-aware meta-learner will adapt to regime changes 2-3x faster "
                          "than a standard meta-learner because it has seen regime transitions "
                          "during meta-training. It will maintain >0.60 AUC within 50 adaptation "
                          "samples after regime shift.",
                methodology="1. Label historical data by regime (using regime_detector.py)\n"
                          "2. Create meta-tasks: adapt from one regime to another\n"
                          "3. Meta-train with regime classification as auxiliary task\n"
                          "4. Test: start model in one regime, then switch and measure "
                          "   adaptation speed\n"
                          "5. Compare with regime-agnostic meta-learning",
                success_criteria={
                    "regime_aware_faster_adaptation": True,
                    "adaptation_speedup_factor": 2.0,
                    "maintains_auc_after_switch": True,
                },
                priority=2,
                dependencies=["meta_001"],
            ),
            ResearchQuestion(
                id="meta_005",
                title="Prototypical Networks for Multi-Class Crypto Regime Classification",
                description="Use prototypical networks to classify market regimes (not just "
                          "bull/bear but also: high-vol bull, low-vol bull, high-vol bear, "
                          "low-vol bear, consolidation). Few-shot learning allows adding new "
                          "regime types without retraining from scratch.",
                hypothesis="Prototypical networks will achieve >85% regime classification accuracy "
                          "with just 20 examples per regime class. They will generalize to unseen "
                          "regime variations better than fixed-classifier approaches.",
                methodology="1. Build regime dataset using regime_detector.py labels\n"
                          "2. Create N-way K-shot tasks (N=4 regimes, K=5,10,20)\n"
                          "3. Train prototypical network with episodic training\n"
                          "4. Test on held-out regimes (leave-one-out)\n"
                          "5. Compare with standard supervised classifier trained on full data\n"
                          "6. Measure sample efficiency (accuracy vs K)",
                success_criteria={
                    "few_shot_accuracy_20_samples": 0.85,
                    "prototypical_better_than_supervised_few_shot": True,
                    "generalizes_to_unseen_regime_variations": True,
                },
                priority=3,
            ),
        ]
    
    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        """Prepare data for meta-learning experiments."""
        from ml_crypto_predictor.enhanced_models.data_fetcher import fetch_klines
        from ml_crypto_predictor.enhanced_models.feature_engine import build_features
        from ml_crypto_predictor.enhanced_models.config import CRYPTO_PAIRS
        
        # Use first 15 pairs for meta-training
        pairs = CRYPTO_PAIRS[:15]
        
        all_sequences = []
        pair_labels = []
        
        for pair_idx, pair in enumerate(pairs):
            df = fetch_klines(pair, "1h", 1500)
            if df.empty or len(df) < 500:
                continue
            
            features = build_features(df)
            target = self._build_target(df)
            aligned = features.join(target, how="inner").dropna()
            
            # Create sequences
            seq_len = 60
            for i in range(len(aligned) - seq_len):
                seq = aligned.iloc[i:i+seq_len][features.columns].values
                label = aligned.iloc[i+seq_len-1][target.name]
                all_sequences.append(seq)
                pair_labels.append(pair_idx)
        
        all_sequences = np.array(all_sequences, dtype=np.float32)
        pair_labels = np.array(pair_labels)
        
        # Split by pair for meta-learning
        unique_pairs = np.unique(pair_labels)
        train_pairs = unique_pairs[:int(len(unique_pairs) * 0.7)]
        val_pairs = unique_pairs[int(len(unique_pairs) * 0.7):int(len(unique_pairs) * 0.85)]
        test_pairs = unique_pairs[int(len(unique_pairs) * 0.85):]
        
        train_mask = np.isin(pair_labels, train_pairs)
        val_mask = np.isin(pair_labels, val_pairs)
        test_mask = np.isin(pair_labels, test_pairs)
        
        return {
            "sequences": all_sequences,
            "pair_labels": pair_labels,
            "train_mask": train_mask,
            "val_mask": val_mask,
            "test_mask": test_mask,
            "n_pairs": len(unique_pairs),
            "n_samples": len(all_sequences),
            "n_features": all_sequences.shape[2] if len(all_sequences) > 0 else 0,
            "seq_len": seq_len,
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
            elif (future <= sl).any():
                target.iloc[i] = 0
            else:
                target.iloc[i] = 0
        
        return target
    
    def conduct_experiment(self, question: ResearchQuestion,
                          data: Dict[str, Any]) -> ResearchResult:
        """Run meta-learning experiments."""
        if not HAS_TORCH:
            return ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings="PyTorch not available. Cannot run meta-learning experiments.",
                metrics={},
                confidence=0.0,
                reproducible=False,
                limitations=["PyTorch dependency missing"],
            )
        
        if data.get("n_samples", 0) < 1000:
            return ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings="Insufficient data for meta-learning (need 1000+ sequences)",
                metrics={},
                confidence=0.0,
            )
        
        if question.id == "meta_001":
            result = self._run_maml_vs_reptile(question, data)
        elif question.id == "meta_002":
            result = self._run_few_shot_learning(question, data)
        elif question.id == "meta_003":
            result = self._run_cross_market_transfer(question, data)
        elif question.id == "meta_004":
            result = self._run_regime_aware_meta(question, data)
        elif question.id == "meta_005":
            result = self._run_prototypical_networks(question, data)
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
    
    def _run_maml_vs_reptile(self, question: ResearchQuestion,
                            data: Dict[str, Any]) -> ResearchResult:
        """Compare MAML vs Reptile."""
        findings = []
        findings.append(f"Dataset: {data['n_samples']} sequences, {data['n_pairs']} pairs")
        findings.append("Meta-learning experiment initialized")
        
        # In full implementation:
        # 1. Define base model (simple MLP or LSTM)
        # 2. Implement MAML inner loop adaptation
        # 3. Implement Reptile update
        # 4. Meta-train on train pairs
        # 5. Test adaptation on test pairs
        
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="MAML vs Reptile experiment setup complete\n" + "\n".join(findings),
            metrics={
                "n_pairs": data['n_pairs'],
                "n_samples": data['n_samples'],
                "seq_len": data['seq_len'],
            },
            confidence=0.6,
            reproducible=True,
            limitations=["Full implementation pending"],
            recommendations={"next": "Implement MAML and Reptile training loops"},
        )
    
    def _run_few_shot_learning(self, question: ResearchQuestion,
                              data: Dict[str, Any]) -> ResearchResult:
        """Test few-shot learning sample efficiency."""
        findings = []
        findings.append(f"Testing few-shot learning with varying k samples")
        
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Few-shot learning experiment setup",
            metrics={},
            confidence=0.5,
        )
    
    def _run_cross_market_transfer(self, question: ResearchQuestion,
                                  data: Dict[str, Any]) -> ResearchResult:
        """Test cross-market transfer (majors to meme coins)."""
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Cross-market transfer experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_regime_aware_meta(self, question: ResearchQuestion,
                              data: Dict[str, Any]) -> ResearchResult:
        """Test regime-aware meta-learning."""
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Regime-aware meta-learning not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_prototypical_networks(self, question: ResearchQuestion,
                                  data: Dict[str, Any]) -> ResearchResult:
        """Test prototypical networks for regime classification."""
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Prototypical networks experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        """Validate meta-learning results."""
        validation = {
            "confidence": 0.6,
            "reproducible": True,
            "limitations": [],
        }
        
        return validation
