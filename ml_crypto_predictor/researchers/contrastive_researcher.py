"""
ContrastiveResearcher — Self-Supervised Representation Learning
===============================================================

Specializes in contrastive and self-supervised learning for crypto:
  - SimCLR / SimSiam for representation learning
  - Time Series Contrastive Learning (TS-TCC)
  - Multi-view contrastive learning (price + volume + orderbook)
  - Momentum contrast (MoCo) for memory bank
  - Barlow Twins for redundancy reduction
  - BYOL for bootstrapping

Academic foundations:
  - "A Simple Framework for Contrastive Learning" (Chen et al., 2020)
  - "TS-TCC: Self-Supervised Learning for Time Series" (Eldele et al., 2021)
  - "Barlow Twins: Self-Supervised Learning via Redundancy Reduction" (Zbontar et al., 2021)
  - "Momentum Contrast for Unsupervised Visual Representation Learning" (He et al., 2020)

Key research questions:
  1. Can contrastive learning extract meaningful representations from crypto price series?
  2. Which augmentation strategies work best for financial time series?
  3. Does multi-view contrastive learning improve over single-view?
  4. Can pretrained representations transfer across pairs/timeframes?
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


class ContrastiveResearcher(Researcher):
    """
    Researcher specializing in contrastive and self-supervised learning.
    
    Investigates whether contrastive pretraining can learn robust
    representations from crypto time series without labels.
    """
    
    researcher_id = "contrastive"
    name = "Contrastive Learning Researcher"
    specialization = "Self-supervised learning (SimCLR, MoCo, Barlow Twins)"
    literature = [
        "SimCLR: A Simple Framework for Contrastive Learning (Chen et al., 2020)",
        "TS-TCC: Self-Supervised Learning for Time Series (Eldele et al., 2021)",
        "Barlow Twins: Redundancy Reduction (Zbontar et al., 2021)",
        "Momentum Contrast (He et al., 2020)",
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_dir = Path(config.get("base_dir", "ml_crypto_predictor")) if config else Path("ml_crypto_predictor")
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "models" / "contrastive"
        self.results_dir = self.base_dir / "results" / "research" / "contrastive"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def formulate_questions(self) -> List[ResearchQuestion]:
        """Define research questions for contrastive learning."""
        return [
            ResearchQuestion(
                id="cl_001",
                title="SimCLR for Crypto: Which Augmentations Work Best?",
                description="Test different augmentation strategies for contrastive learning "
                          "on crypto time series: 1) jittering, 2) scaling, 3) time warping, "
                          "4) window slicing, 5) frequency masking. Financial data has unique "
                          "properties (non-stationarity, heavy tails) — standard vision augmentations "
                          "may not transfer.",
                hypothesis="Combination of jittering + window slicing + time warping will work best. "
                          "Frequency masking may hurt because spectral properties are meaningful. "
                          "Expected: pretrained encoder + linear probe should achieve AUC > 0.60 "
                          "with only 10% labeled data.",
                methodology="1. Prepare unlabeled 1h data for BTC, ETH, SOL (10000+ samples)\n"
                          "2. Define augmentation pipeline (test combinations)\n"
                          "3. Pretrain encoder using SimCLR NT-Xent loss\n"
                          "4. Freeze encoder, train linear classifier on 10% labeled data\n"
                          "5. Compare with training from scratch on same 10%\n"
                          "6. Measure AUC, precision, recall",
                success_criteria={
                    "contrastive_better_than_scratch": True,
                    "auc_improvement": 0.05,
                    "best_augmentation_combination": ["jitter", "window_slice", "time_warp"],
                },
                priority=1,
            ),
            ResearchQuestion(
                id="cl_002",
                title="Multi-View Contrastive Learning: Price + Volume + Orderbook",
                description="Use multi-view contrastive learning where each view is a different "
                          "market aspect: 1) price series, 2) volume series, 3) orderbook imbalance. "
                          "Learn representations that are consistent across views but capture "
                          "view-specific information.",
                hypothesis="Multi-view contrastive learning will outperform single-view because "
                          "different market aspects provide complementary signals. The model will "
                          "learn representations that capture price-volume relationships, "
                          "volume-orderbook dynamics, etc.",
                methodology="1. Build three views per sample:\n"
                          "   - View 1: normalized price returns (last 60 bars)\n"
                          "   - View 2: normalized volume with VWAP\n"
                          "   - View 3: orderbook imbalance (bid/ask pressure)\n"
                          "2. Use multi-view contrastive loss (InfoNCE cross-view)\n"
                          "3. Pretrain encoder, evaluate on downstream prediction\n"
                          "4. Ablate: remove each view to measure contribution\n"
                          "5. Visualize learned representations (t-SNE)",
                success_criteria={
                    "multiview_better_than_single": True,
                    "all_views_contribute": True,
                    "improvement_over_single_view": 0.03,
                },
                priority=2,
                dependencies=["cl_001"],
            ),
            ResearchQuestion(
                id="cl_003",
                title="Transfer Learning: Can Representations Transfer Across Pairs?",
                description="Pretrain contrastive encoder on BTC, then fine-tune on SOL, "
                          "DOGE, etc. with minimal labeled data. Test if representations "
                          "learned on major coin transfer to altcoins/meme coins.",
                hypothesis="Pretrained representations on BTC will transfer well to other "
                          "large-cap coins (ETH, SOL) with minimal fine-tuning (AUC improvement "
                          "3-5% with only 5% labeled data). Transfer to meme coins (DOGE, SHIB) "
                          "will be weaker but still positive.",
                methodology="1. Pretrain encoder on BTC unlabeled data (SimCLR)\n"
                          "2. For each target coin, fine-tune with 5%, 10%, 50% labeled data\n"
                          "3. Compare against training from scratch on same data\n"
                          "4. Measure transfer gain (fine-tune - scratch)\n"
                          "5. Analyze which layers transfer best",
                success_criteria={
                    "transfer_works": True,
                    "btc_to_eth_sol_improvement": 0.03,
                    "btc_to_meme_improvement": 0.01,
                    "few_shot_benefit": True,
                },
                priority=2,
                dependencies=["cl_001"],
            ),
            ResearchQuestion(
                id="cl_004",
                title="Barlow Twins for Redundancy Reduction in Crypto Features",
                description="Use Barlow Twins to learn representations where feature dimensions "
                          "are decorrelated. This should produce more robust embeddings that "
                          "capture independent factors of variation (momentum, volatility, trend).",
                hypothesis="Barlow Twins will produce more disentangled representations than "
                          "SimCLR, leading to better downstream performance when data is limited. "
                          "The off-diagonal cross-correlation loss will force features to specialize.",
                methodology="1. Implement Barlow Twins with projection head\n"
                          "2. Train on unlabeled crypto data (same as cl_001)\n"
                          "3. Compare representations with SimCLR (visualize correlation matrix)\n"
                          "4. Linear probe evaluation on downstream task\n"
                          "5. Measure feature correlation (should be near zero off-diagonal)",
                success_criteria={
                    "barlow_better_than_simclr": True,
                    "features_decorrelated": True,  # Off-diagonal ~ 0
                    "downstream_improvement": 0.02,
                },
                priority=3,
                dependencies=["cl_001"],
            ),
            ResearchQuestion(
                id="cl_005",
                title="Contrastive Learning for Regime-Aware Representations",
                description="Can contrastive learning automatically separate data from different "
                          "regimes (bull/bear/volatile) into distinct clusters? Use the learned "
                          "representations to improve regime classification accuracy.",
                hypothesis="Contrastive pretraining will create representations where regimes "
                          "are more separable than raw features. This will improve regime detection "
                          "accuracy by 10-15% when using simple clustering (k-means).",
                methodology="1. Pretrain with SimCLR on all data (unlabeled)\n"
                          "2. Extract embeddings for regime detector training data\n"
                          "3. Train k-means on embeddings vs raw features\n"
                          "4. Compare clustering quality (silhouette score)\n"
                          "5. Use embeddings as features for regime classification\n"
                          "6. Measure accuracy improvement",
                success_criteria={
                    "embeddings_more_separable": True,
                    "silhouette_improvement": 0.1,
                    "regime_classification_improvement": 0.1,
                },
                priority=2,
                dependencies=["cl_001"],
            ),
        ]
    
    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        """Prepare data for contrastive learning."""
        from ml_crypto_predictor.enhanced_models.data_fetcher import fetch_klines
        from ml_crypto_predictor.enhanced_models.feature_engine import build_features
        
        pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        timeframe = "1h"
        
        sequences = []
        
        for pair in pairs:
            df = fetch_klines(pair, "1h", 2000)
            if df.empty or len(df) < 500:
                continue
            
            features = build_features(df)
            features.dropna(inplace=True)
            
            # Create sliding windows (sequences)
            seq_len = 60
            for i in range(len(features) - seq_len):
                seq = features.iloc[i:i+seq_len].values
                sequences.append(seq)
        
        sequences = np.array(sequences, dtype=np.float32)
        
        return {
            "sequences": sequences,
            "n_samples": len(sequences),
            "seq_len": sequences.shape[1] if len(sequences) > 0 else 0,
            "n_features": sequences.shape[2] if len(sequences) > 0 else 0,
            "timeframe": timeframe,
        }
    
    def conduct_experiment(self, question: ResearchQuestion,
                          data: Dict[str, Any]) -> ResearchResult:
        """Run contrastive learning experiments."""
        if not HAS_TORCH:
            return ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings="PyTorch not available. Cannot run contrastive experiments.",
                metrics={},
                confidence=0.0,
                reproducible=False,
                limitations=["PyTorch dependency missing"],
            )
        
        if data.get("n_samples", 0) < 100:
            return ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings="Insufficient data for contrastive learning",
                metrics={},
                confidence=0.0,
            )
        
        if question.id == "cl_001":
            result = self._run_simclr_augmentations(question, data)
        elif question.id == "cl_002":
            result = self._run_multiview_contrastive(question, data)
        elif question.id == "cl_003":
            result = self._run_transfer_learning(question, data)
        elif question.id == "cl_004":
            result = self._run_barlow_twins(question, data)
        elif question.id == "cl_005":
            result = self._run_regime_aware(question, data)
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
    
    def _run_simclr_augmentations(self, question: ResearchQuestion,
                                 data: Dict[str, Any]) -> ResearchResult:
        """Test augmentation strategies for SimCLR."""
        sequences = data["sequences"]
        n_samples = len(sequences)
        
        findings = []
        findings.append(f"Dataset: {n_samples} sequences of length {data['seq_len']}")
        
        # Define augmentation strategies
        augmentations = {
            "jitter": self._augment_jitter,
            "scale": self._augment_scale,
            "warp": self._augment_time_warp,
            "slice": self._augment_window_slice,
            "mask": self._augment_freq_mask,
        }
        
        # For now, just demonstrate framework
        findings.append("Augmentation strategies defined:")
        for name, func in augmentations.items():
            findings.append(f"  - {name}: {func.__doc__.strip() if func.__doc__ else 'No description'}")
        
        # In full implementation:
        # 1. For each augmentation combo, train SimCLR encoder
        # 2. Linear probe evaluation
        # 3. Compare AUC scores
        
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="SimCLR augmentation experiment setup complete\n" + "\n".join(findings),
            metrics={"n_samples": n_samples, "n_augmentations": len(augmentations)},
            confidence=0.5,
            reproducible=True,
            limitations=["Full training not implemented yet"],
            recommendations={"next": "Implement SimCLR training loop with NT-Xent loss"},
        )
    
    def _augment_jitter(self, x: np.ndarray, sigma: float = 0.1) -> np.ndarray:
        """Add Gaussian noise."""
        return x + np.random.normal(0, sigma, x.shape)
    
    def _augment_scale(self, x: np.ndarray, scale_range: tuple = (0.9, 1.1)) -> np.ndarray:
        """Random scaling."""
        scale = np.random.uniform(*scale_range)
        return x * scale
    
    def _augment_time_warp(self, x: np.ndarray, knots: int = 4) -> np.ndarray:
        """Time warping (stretch/compress segments)."""
        # Simplified: random small time shift
        shift = np.random.randint(-3, 4)
        if shift > 0:
            return np.roll(x, shift, axis=0)
        elif shift < 0:
            return np.roll(x, shift, axis=0)
        return x
    
    def _augment_window_slice(self, x: np.ndarray, slice_ratio: float = 0.9) -> np.ndarray:
        """Window slicing (take random subsequence)."""
        seq_len = len(x)
        slice_len = int(seq_len * slice_ratio)
        start = np.random.randint(0, seq_len - slice_len + 1)
        sliced = x[start:start + slice_len]
        # Resize back to original length (repeat or pad)
        if len(sliced) < seq_len:
            # Repeat to fill
            repeat_times = int(np.ceil(seq_len / len(sliced)))
            sliced = np.tile(sliced, (repeat_times, 1))[:seq_len]
        return sliced
    
    def _augment_freq_mask(self, x: np.ndarray, mask_ratio: float = 0.1) -> np.ndarray:
        """Frequency domain masking (Fourier-based)."""
        # Apply FFT, mask some frequencies, inverse FFT
        from scipy.fft import fft, ifft
        x_fft = fft(x, axis=0)
        mask = np.random.random(x.shape) > mask_ratio
        x_fft_masked = x_fft * mask
        return np.real(ifft(x_fft_masked, axis=0))
    
    def _run_multiview_contrastive(self, question: ResearchQuestion,
                                  data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Multi-view contrastive experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_transfer_learning(self, question: ResearchQuestion,
                              data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Transfer learning experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_barlow_twins(self, question: ResearchQuestion,
                         data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Barlow Twins experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_regime_aware(self, question: ResearchQuestion,
                         data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Regime-aware contrastive experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        """Validate contrastive learning results."""
        validation = {
            "confidence": 0.6,
            "reproducible": True,
            "limitations": [],
        }
        
        # Check if metrics are reasonable
        if result.metrics:
            n_samples = result.metrics.get("n_samples", 0)
            if n_samples < 1000:
                validation["limitations"].append("Small dataset may limit contrastive learning effectiveness")
                validation["confidence"] *= 0.8
        
        return validation
