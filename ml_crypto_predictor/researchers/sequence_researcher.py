"""
SequenceModelResearcher — Temporal Deep Learning Architectures
==============================================================

Specializes in sequence models for time series prediction:
  - LSTM (Long Short-Term Memory)
  - GRU (Gated Recurrent Unit)
  - 1D CNN (Convolutional Neural Networks)
  - CNN-GRU Hybrids with Attention

Academic foundations:
  - "Deep Learning for Time Series Analysis" (Fawaz et al., 2019)
  - "Temporal Convolutional Networks for Stock Prediction" (Bao et al., 2020)
  - "CNN-GRU Hybrid Architecture for Cryptocurrency Prediction" (MDPI Mathematics, 2025)

Key research questions:
  1. Which sequence architecture performs best on different timeframes?
  2. How does sequence length affect prediction accuracy?
  3. Can CNN-GRU hybrids outperform pure RNNs?
  4. What is the optimal balance between model complexity and overfitting?
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pandas as pd

from .base import Researcher, ResearchQuestion, ResearchResult

# Optional torch import
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class SequenceModelResearcher(Researcher):
    """
    Researcher specializing in temporal deep learning models.
    
    Investigates LSTM, GRU, CNN, and hybrid architectures for
    cryptocurrency price prediction across multiple timeframes.
    """
    
    researcher_id = "sequence_models"
    name = "Sequence Models Researcher"
    specialization = "Temporal deep learning (LSTM, GRU, CNN, hybrids)"
    literature = [
        "Deep Learning for Time Series Analysis (Fawaz et al., 2019)",
        "CNN-GRU Hybrid for Crypto (MDPI Math, 2025)",
        "Temporal Convolutional Networks (Bao et al., 2020)",
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_dir = Path(config.get("base_dir", "ml_crypto_predicter")) if config else Path("ml_crypto_predictor")
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "models" / "sequence"
        self.results_dir = self.base_dir / "results" / "research" / "sequence"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def formulate_questions(self) -> List[ResearchQuestion]:
        """Define research questions for sequence models."""
        return [
            ResearchQuestion(
                id="seq_001",
                title="LSTM vs GRU vs CNN: Best Architecture for 1h Crypto",
                description="Compare LSTM, GRU, 1D CNN, and CNN-GRU hybrid on 1h timeframe data. "
                          "Evaluate using walk-forward validation with 70+ features. "
                          "Expected: CNN-GRU hybrid performs best due to local pattern extraction + temporal dependencies.",
                hypothesis="CNN-GRU hybrid will achieve highest AUC-ROC (>0.65) and Sharpe ratio (>2.0) "
                          "due to complementary strengths: CNN extracts local patterns, GRU captures long-term dependencies.",
                methodology="1. Prepare 1h data for BTC, ETH, SOL (1000+ candles)\n"
                          "2. Build 70+ features from feature_engine.py\n"
                          "3. Create sequences of length 30, 60, 90\n"
                          "4. Train each architecture with same hyperparameters\n"
                          "5. Walk-forward validation: train on 70%, test on 30%\n"
                          "6. Compare AUC, precision, recall, Sharpe, profit factor",
                success_criteria={
                    "min_auc_roc": 0.62,
                    "min_sharpe": 1.5,
                    "min_precision": 0.55,
                    "max_overfit_threshold": 0.05,  # train-test AUC gap
                },
                priority=1,
            ),
            ResearchQuestion(
                id="seq_002",
                title="Optimal Sequence Length for Different Timeframes",
                description="Investigate how sequence length (lookback window) affects performance "
                          "across 5m, 15m, 1h, 4h, 1d timeframes. Shorter sequences for scalping, "
                          "longer for swing/position trading.",
                hypothesis="Optimal sequence length scales with timeframe: "
                          "5m: 20-30 bars, 15m: 30-48 bars, 1h: 48-60 bars, "
                          "4h: 60-80 bars, 1d: 80-120 bars. Too long causes vanishing gradients, "
                          "too short loses long-term context.",
                methodology="For each timeframe, train sequence models with varying seq_len "
                          "(20, 30, 48, 60, 80, 100, 120). Keep model architecture constant. "
                          "Evaluate on validation set. Plot performance vs seq_len.",
                success_criteria={
                    "find_optimal_per_tf": True,
                    "max_improvement_pct": 10.0,  # seq_len optimization should improve >10%
                },
                priority=2,
                dependencies=["seq_001"],
            ),
            ResearchQuestion(
                id="seq_003",
                title="Attention Mechanisms in Sequence Models",
                description="Add self-attention to CNN-GRU hybrid and compare with standard "
                          "CNN-GRU. Does attention improve interpretability and performance? "
                          "Reference: Attention-based LSTM for stock prediction (2021).",
                hypothesis="Adding attention will improve AUC by 2-3% and provide better "
                          "interpretability via attention weights. Attention helps model focus "
                          "on important timesteps (e.g., volatility spikes, pattern completions).",
                methodology="1. Baseline: CNN-GRU without attention\n"
                          "2. Enhanced: CNN-GRU with multi-head self-attention\n"
                          "3. Compare metrics and visualize attention weights\n"
                          "4. Check if attention aligns with known market events",
                success_criteria={
                    "min_auc_improvement": 0.01,
                    "attention_interpretable": True,
                },
                priority=2,
                dependencies=["seq_001"],
            ),
            ResearchQuestion(
                id="seq_004",
                title="Sequence Models vs Traditional ML: When Does Deep Learning Win?",
                description="Compare sequence models (LSTM/GRU/CNN) against traditional ML "
                          "(XGBoost, LightGBM, Random Forest) on different market regimes. "
                          "Deep learning should excel in trending/volatile regimes, "
                          "traditional ML in range-bound markets.",
                hypothesis="Sequence models outperform traditional ML by 5-10% in trending "
                          "regimes (ADX > 25) but underperform in consolidation (ADX < 15). "
                          "Hybrid ensemble combining both will be most robust.",
                methodology="1. Train sequence models and traditional ML on same datasets\n"
                          "2. Segment test set by regime (using regime_detector.py)\n"
                          "3. Compare performance per regime\n"
                          "4. Build regime-adaptive ensemble that switches between model types",
                success_criteria={
                    "seq_advantage_in_trending": True,
                    "ml_advantage_in_consolidation": True,
                    "ensemble_improves_over_best": 0.02,  # 2% improvement
                },
                priority=1,
                dependencies=["seq_001"],
            ),
        ]
    
    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        """Prepare data for sequence model experiments."""
        from ml_crypto_predictor.enhanced_models.data_fetcher import fetch_klines
        from ml_crypto_predictor.enhanced_models.feature_engine import build_features
        from ml_crypto_predictor.enhanced_models.config import CRYPTO_PAIRS, TIMEFRAMES
        
        # Select pairs and timeframe based on question
        pairs = CRYPTO_PAIRS[:3]  # BTC, ETH, SOL for speed
        timeframe = "1h"  # Default
        
        data = {}
        
        for pair in pairs:
            tf_config = TIMEFRAMES[timeframe]
            df = fetch_klines(pair, tf_config["interval"], tf_config["limit"])
            
            if df.empty or len(df) < 300:
                continue
            
            # Build features
            features = build_features(df)
            target = self._build_target(df)
            
            # Align features and target
            aligned = features.join(target, how="inner")
            aligned.dropna(inplace=True)
            
            data[pair] = {
                "features": aligned[features.columns].values,
                "target": aligned[target.name].values,
                "feature_names": list(features.columns),
                "n_samples": len(aligned),
            }
        
        return {
            "data": data,
            "timeframe": timeframe,
            "pairs": list(data.keys()),
            "n_features": data[pairs[0]]["features"].shape[1] if data else 0,
        }
    
    def _build_target(self, df: pd.DataFrame, horizon: int = 12, 
                     tp_pct: float = 0.02, sl_pct: float = -0.01) -> pd.Series:
        """Build binary classification target (TP/SL)."""
        close = df["close"]
        target = pd.Series(0, index=close.index, dtype=int)
        
        for i in range(len(close) - horizon):
            entry = close.iloc[i]
            future = close.iloc[i+1:i+1+horizon]
            
            tp = entry * (1 + tp_pct)
            sl = entry * (1 + sl_pct)
            
            tp_hit = (future >= tp).idxmax() if (future >= tp).any() else None
            sl_hit = (future <= sl).idxmax() if (future <= sl).any() else None
            
            if tp_hit and (not sl_hit or tp_hit <= sl_hit):
                target.iloc[i] = 1
        
        return target
    
    def conduct_experiment(self, question: ResearchQuestion, 
                          data: Dict[str, Any]) -> ResearchResult:
        """Run sequence model experiments."""
        if not HAS_TORCH:
            return ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings="PyTorch not available. Cannot run deep learning experiments.",
                metrics={},
                confidence=0.0,
                reproducible=False,
                limitations=["PyTorch dependency missing"],
            )
        
        # Determine which experiment to run based on question ID
        if question.id == "seq_001":
            result = self._run_architecture_comparison(question, data)
        elif question.id == "seq_002":
            result = self._run_sequence_length_optimization(question, data)
        elif question.id == "seq_003":
            result = self._run_attention_experiment(question, data)
        elif question.id == "seq_004":
            result = self._run_vs_traditional_ml(question, data)
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
    
    def _run_architecture_comparison(self, question: ResearchQuestion, 
                                    data: Dict[str, Any]) -> ResearchResult:
        """Compare LSTM, GRU, CNN, CNN-GRU architectures."""
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        
        findings = []
        all_metrics = []
        
        for pair, pair_data in data["data"].items():
            X = pair_data["features"]
            y = pair_data["target"]
            
            # Split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.3, shuffle=False  # Time series
            )
            
            # Scale
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)
            
            # Create sequences
            seq_len = 60
            X_train_seq = self._create_sequences(X_train, seq_len)
            X_test_seq = self._create_sequences(X_test, seq_len)
            y_train_seq = y_train[seq_len-1:][:len(X_train_seq)]
            y_test_seq = y_test[seq_len-1:][:len(X_test_seq)]
            
            # Train architectures
            architectures = {
                "lstm": self._build_lstm(X_train_seq.shape[2]),
                "gru": self._build_gru(X_train_seq.shape[2]),
                "cnn": self._build_cnn1d(X_train_seq.shape[2]),
                "cnn_gru": self._build_cnn_gru(X_train_seq.shape[2]),
            }
            
            for name, model in architectures.items():
                try:
                    self._train_torch_model(model, X_train_seq, y_train_seq, epochs=30)
                    metrics = self._evaluate_torch_model(model, X_test_seq, y_test_seq)
                    metrics["pair"] = pair
                    metrics["architecture"] = name
                    all_metrics.append(metrics)
                    findings.append(f"{pair}/{name}: AUC={metrics['auc']:.3f}, Sharpe={metrics.get('sharpe', 0):.2f}")
                except Exception as e:
                    findings.append(f"{pair}/{name}: Failed - {e}")
        
        # Aggregate results
        df_metrics = pd.DataFrame(all_metrics)
        summary = df_metrics.groupby("architecture").mean().to_dict()
        
        # Find best
        best_arch = df_metrics.loc[df_metrics["auc"].idxmax()]["architecture"] if not df_metrics.empty else None
        
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings=f"Architecture comparison complete. Best: {best_arch}\n" + "\n".join(findings[:10]),
            metrics=summary,
            confidence=0.85 if best_arch else 0.0,
            reproducible=True,
            limitations=["Limited to 3 pairs", "Fixed hyperparameters"],
            recommendations={
                "best_architecture": best_arch,
                "suggested_seq_len": 60,
                "next_steps": ["Test on all 30 pairs", "Hyperparameter tuning"],
            }
        )
    
    def _create_sequences(self, X: np.ndarray, seq_len: int) -> np.ndarray:
        """Convert flat features to sequences."""
        n_samples = len(X) - seq_len + 1
        if n_samples <= 0:
            raise ValueError(f"Not enough samples for seq_len={seq_len}")
        
        sequences = np.zeros((n_samples, seq_len, X.shape[1]), dtype=np.float32)
        for i in range(n_samples):
            sequences[i] = X[i:i+seq_len]
        return sequences
    
    def _build_lstm(self, n_features: int, hidden_dim: int = 64) -> nn.Module:
        """Build LSTM model."""
        class LSTMModel(nn.Module):
            def __init__(self, input_dim, hidden_dim):
                super().__init__()
                self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers=2, 
                                   batch_first=True, dropout=0.3)
                self.fc = nn.Sequential(
                    nn.Linear(hidden_dim, 32),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(32, 2),
                )
            
            def forward(self, x):
                out, _ = self.lstm(x)
                return self.fc(out[:, -1, :])
        
        return LSTMModel(n_features, hidden_dim)
    
    def _build_gru(self, n_features: int, hidden_dim: int = 64) -> nn.Module:
        """Build GRU model."""
        class GRUModel(nn.Module):
            def __init__(self, input_dim, hidden_dim):
                super().__init__()
                self.gru = nn.GRU(input_dim, hidden_dim, num_layers=2,
                                 batch_first=True, dropout=0.3)
                self.fc = nn.Sequential(
                    nn.Linear(hidden_dim, 32),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(32, 2),
                )
            
            def forward(self, x):
                out, _ = self.gru(x)
                return self.fc(out[:, -1, :])
        
        return GRUModel(n_features, hidden_dim)
    
    def _build_cnn1d(self, n_features: int) -> nn.Module:
        """Build 1D CNN model."""
        class CNN1DModel(nn.Module):
            def __init__(self, input_dim):
                super().__init__()
                self.conv = nn.Sequential(
                    nn.Conv1d(input_dim, 64, kernel_size=3, padding=1),
                    nn.BatchNorm1d(64),
                    nn.ReLU(),
                    nn.Conv1d(64, 128, kernel_size=3, padding=1),
                    nn.BatchNorm1d(128),
                    nn.ReLU(),
                    nn.AdaptiveAvgPool1d(1),
                )
                self.fc = nn.Sequential(
                    nn.Linear(128, 64),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(64, 2),
                )
            
            def forward(self, x):
                # x: (batch, seq_len, features) -> (batch, features, seq_len)
                x = x.transpose(1, 2)
                x = self.conv(x).squeeze(-1)
                return self.fc(x)
        
        return CNN1DModel(n_features)
    
    def _build_cnn_gru(self, n_features: int, hidden_dim: int = 64) -> nn.Module:
        """Build CNN-GRU hybrid model."""
        class CNNGRUModel(nn.Module):
            def __init__(self, input_dim, hidden_dim):
                super().__init__()
                self.conv = nn.Sequential(
                    nn.Conv1d(input_dim, 64, kernel_size=3, padding=1),
                    nn.BatchNorm1d(64),
                    nn.ReLU(),
                    nn.Conv1d(64, 64, kernel_size=3, padding=1),
                    nn.BatchNorm1d(64),
                    nn.ReLU(),
                )
                self.gru = nn.GRU(64, hidden_dim, num_layers=2, batch_first=True, dropout=0.2)
                self.fc = nn.Sequential(
                    nn.Linear(hidden_dim, 32),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(32, 2),
                )
            
            def forward(self, x):
                x_conv = self.conv(x.transpose(1, 2)).transpose(1, 2)
                out, _ = self.gru(x_conv)
                return self.fc(out[:, -1, :])
        
        return CNNGRUModel(n_features, hidden_dim)
    
    def _train_torch_model(self, model: nn.Module, X: np.ndarray, y: np.ndarray,
                          epochs: int = 30, batch_size: int = 64):
        """Train PyTorch model."""
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        
        X_t = torch.tensor(X, dtype=torch.float32).to(device)
        y_t = torch.tensor(y, dtype=torch.long).to(device)
        
        dataset = TensorDataset(X_t, y_t)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        
        model.train()
        for epoch in range(epochs):
            for xb, yb in loader:
                optimizer.zero_grad()
                out = model(xb)
                loss = criterion(out, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
        
        model.eval()
    
    def _evaluate_torch_model(self, model: nn.Module, X: np.ndarray, 
                             y: np.ndarray) -> Dict[str, float]:
        """Evaluate PyTorch model."""
        device = next(model.parameters()).device
        X_t = torch.tensor(X, dtype=torch.float32).to(device)
        
        with torch.no_grad():
            out = model(X_t)
            probs = torch.softmax(out, dim=1)[:, 1].cpu().numpy()
            preds = probs >= 0.5
        
        from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score
        
        try:
            auc = roc_auc_score(y, probs)
        except:
            auc = 0.5
        
        precision = precision_score(y, preds, zero_division=0)
        recall = recall_score(y, preds, zero_division=0)
        f1 = f1_score(y, preds, zero_division=0)
        
        # Simulate backtest for Sharpe
        signals = preds
        if signals.sum() > 0:
            win_rate = (y[signals] == 1).mean() * 100
            # Simplified Sharpe (would need actual returns for real calculation)
            sharpe = (win_rate/100 - 0.5) / max(0.01, (1 - win_rate/100)) * np.sqrt(252) if win_rate > 50 else 0
        else:
            sharpe = 0
        
        return {
            "auc": round(auc, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "sharpe": round(sharpe, 2),
            "win_rate": round(win_rate if signals.sum() > 0 else 0, 2),
        }
    
    # Placeholder methods for other experiments
    def _run_sequence_length_optimization(self, question: ResearchQuestion, 
                                          data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Sequence length optimization not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_attention_experiment(self, question: ResearchQuestion,
                                 data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Attention experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_vs_traditional_ml(self, question: ResearchQuestion,
                              data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Traditional ML comparison not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        """Validate sequence model results."""
        validation = {
            "confidence": 0.7,
            "reproducible": True,
            "limitations": [],
        }
        
        # Check if metrics are reasonable
        if result.metrics:
            auc = result.metrics.get("auc", 0)
            if auc < 0.5:
                validation["limitations"].append("AUC below 0.5 indicates model no better than random")
                validation["confidence"] *= 0.5
            if auc > 0.8:
                validation["limitations"].append("Very high AUC may indicate data leakage")
                validation["confidence"] *= 0.7
        
        return validation
