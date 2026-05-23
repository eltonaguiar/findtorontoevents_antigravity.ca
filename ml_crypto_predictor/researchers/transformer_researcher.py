"""
TransformerResearcher — Attention-Based Architectures
=====================================================

Specializes in Transformer and attention-based models for crypto prediction:
  - Standard Transformer (Vaswani et al., 2017)
  - Time Series Transformer (with positional encoding)
  - Informer/Autoformer (efficient attention for long sequences)
  - Temporal Fusion Transformer (TFT)
  - Multi-head self-attention with feature-wise interactions

Academic foundations:
  - "Attention Is All You Need" (Vaswani et al., 2017)
  - "Temporal Fusion Transformers for Interpretable Multi-horizon Time Series Forecasting" (Lim et al., 2021)
  - "Informer: Beyond Efficient Transformer for Long Sequence Time-Series Forecasting" (Zhou et al., 2021)
  - "Are Transformers Effective for Time Series Forecasting?" (Zeng et al., 2023)

Key research questions:
  1. Do Transformers outperform RNNs on crypto time series?
  2. What is the optimal attention mechanism (full, sparse, linear)?
  3. How does positional encoding affect temporal understanding?
  4. Can Transformers capture multi-scale patterns effectively?
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
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class TransformerResearcher(Researcher):
    """
    Researcher specializing in Transformer and attention-based architectures.
    
    Investigates various Transformer variants for cryptocurrency prediction,
    with focus on handling long sequences and multi-horizon forecasting.
    """
    
    researcher_id = "transformers"
    name = "Transformer Researcher"
    specialization = "Attention-based models (Transformer, TFT, Informer)"
    literature = [
        "Attention Is All You Need (Vaswani et al., 2017)",
        "Temporal Fusion Transformers (Lim et al., 2021)",
        "Informer: Efficient Transformer for Long Sequences (Zhou et al., 2021)",
        "Are Transformers Effective for Time Series? (Zeng et al., 2023)",
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_dir = Path(config.get("base_dir", "ml_crypto_predictor")) if config else Path("ml_crypto_predictor")
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "models" / "transformer"
        self.results_dir = self.base_dir / "results" / "research" / "transformer"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def formulate_questions(self) -> List[ResearchQuestion]:
        """Define research questions for Transformer models."""
        return [
            ResearchQuestion(
                id="trf_001",
                title="Transformer vs LSTM/GRU: Which Excels at Crypto Prediction?",
                description="Compare standard Transformer encoder against LSTM and GRU "
                          "on 1h and 4h timeframes. Use same feature set and sequence lengths. "
                          "Transformers should capture long-range dependencies better but may "
                          "overfit on noisy financial data.",
                hypothesis="Transformers will achieve higher AUC-ROC (+3-5%) than LSTMs/GRUs "
                          "on 4h timeframe (longer patterns) but may underperform on 5m scalping "
                          "due to higher noise and need for rapid inference.",
                methodology="1. Prepare 1h and 4h data for BTC, ETH, SOL\n"
                          "2. Build 70+ features from feature_engine.py\n"
                          "3. Create sequences of length 60 and 100\n"
                          "4. Train Transformer (4 layers, 8 heads, d_model=128)\n"
                          "5. Train LSTM/GRU baselines (2 layers, 64 hidden)\n"
                          "6. Compare using walk-forward validation\n"
                          "7. Measure AUC, precision, recall, Sharpe ratio",
                success_criteria={
                    "min_auc_improvement_over_lstm": 0.02,
                    "sharpe_improvement": 0.5,
                    "transformer_not_overfit": True,  # train-test gap < 0.1
                },
                priority=1,
            ),
            ResearchQuestion(
                id="trf_002",
                title="Optimal Positional Encoding for Financial Time Series",
                description="Test different positional encoding strategies: "
                          "1) Absolute (Vaswani), 2) Relative (Shaw et al.), "
                          "3) Learnable positional embeddings, 4) No encoding (rely on features). "
                          "Financial data has irregular patterns; standard sinusoidal may not be optimal.",
                hypothesis="Learnable positional embeddings will perform best because "
                          "market dynamics (session changes, day-of-week effects) are data-driven "
                          "and may not follow simple sinusoidal patterns.",
                methodology="1. Fix Transformer architecture (4 layers, 8 heads)\n"
                          "2. Train with different positional encodings on same data\n"
                          "3. Compare validation AUC and convergence speed\n"
                          "4. Visualize learned positional embeddings if learnable",
                success_criteria={
                    "learnable_better_than_sinusoidal": True,
                    "improvement_over_no_position": 0.05,
                },
                priority=2,
                dependencies=["trf_001"],
            ),
            ResearchQuestion(
                id="trf_003",
                title="Efficient Attention for Long Sequences (Informer-style)",
                description="Test Informer's ProbSparse attention vs standard full attention "
                          "on daily (1d) timeframe with 500+ candle sequences. "
                          "Standard attention is O(n²) — inefficient for long sequences. "
                          "Informer reduces to O(n log n) with probabilistic sampling.",
                hypothesis="ProbSparse attention will match full attention performance "
                          "(AUC within 1%) while being 3-5x faster and using 60% less memory. "
                          "This enables longer sequence lengths (200+ bars) on daily data.",
                methodology="1. Implement Informer's ProbSparse attention\n"
                          "2. Compare with standard multi-head attention\n"
                          "3. Test on 1d timeframe with seq_len=100, 150, 200\n"
                          "4. Measure: AUC, training time, memory usage, inference speed\n"
                          "5. Check if sparsity hurts performance on critical patterns",
                success_criteria={
                    "speedup_factor": 3.0,
                    "memory_reduction": 0.4,
                    "auc_degradation_max": 0.01,
                },
                priority=2,
                dependencies=["trf_001"],
            ),
            ResearchQuestion(
                id="trf_004",
                title="Multi-Head Attention: Optimal Number of Heads?",
                description="Investigate the effect of attention heads (2, 4, 8, 16) on "
                          "crypto prediction performance. More heads allow attending to "
                          "different representation subspaces but increase overfitting risk.",
                hypothesis="8 heads is optimal for 70+ features: enough capacity to capture "
                          "different patterns (momentum, volume, trend, volatility) without "
                          "excessive parameter growth. 16 heads will overfit on limited data.",
                methodology="1. Fix Transformer depth=4, d_model=128\n"
                          "2. Vary n_heads: 2, 4, 8, 16\n"
                          "3. Train on 1h data (BTC, ETH, SOL)\n"
                          "4. Compare validation metrics and training stability\n"
                          "5. Analyze attention patterns per head (specialization?)",
                success_criteria={
                    "find_optimal_n_heads": True,
                    "optimal_in_range": [4, 8, 12],
                    "16_heads_overfits": True,
                },
                priority=3,
                dependencies=["trf_001"],
            ),
            ResearchQuestion(
                id="trf_005",
                title="Transformer with Market Context Embeddings",
                description="Enhance Transformer by adding embeddings for: "
                          "1) Fear & Greed index, 2) Funding rates, 3) BTC dominance, "
                          "4) Time features (hour, day, session). Test if context-aware "
                          "Transformer outperforms baseline.",
                hypothesis="Adding market context embeddings will improve AUC by 2-3% "
                          "because external factors significantly impact crypto markets. "
                          "The model will learn to modulate attention based on regime.",
                methodology="1. Baseline: Transformer with only price/volume features\n"
                          "2. Enhanced: Add context embeddings (concatenated to input)\n"
                          "3. Train both on same data with regime-aware splits\n"
                          "4. Compare performance in different market regimes\n"
                          "5. Visualize attention weights with/without context",
                success_criteria={
                    "context_improves_auc": 0.02,
                    "improves_in_high_vol": True,
                },
                priority=2,
                dependencies=["trf_001"],
            ),
        ]
    
    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        """Prepare data for Transformer experiments."""
        from ml_crypto_predictor.enhanced_models.data_fetcher import fetch_klines
        from ml_crypto_predictor.enhanced_models.feature_engine import build_features
        from ml_crypto_predictor.enhanced_models.config import CRYPTO_PAIRS, TIMEFRAMES
        
        pairs = CRYPTO_PAIRS[:3]  # BTC, ETH, SOL
        timeframe = "1h"
        
        data = {}
        
        for pair in pairs:
            tf_config = TIMEFRAMES[timeframe]
            df = fetch_klines(pair, tf_config["interval"], tf_config["limit"])
            
            if df.empty or len(df) < 300:
                continue
            
            features = build_features(df)
            target = self._build_target(df)
            
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
        """Build binary classification target."""
        close = df["close"]
        target = pd.Series(0, index=close.index, dtype=int)
        
        for i in range(len(close) - horizon):
            entry = close.iloc[i]
            future = close.iloc[i+1:i+1+horizon]
            
            tp = entry * (1 + tp_pct)
            sl = entry * (1 + sl_pct)
            
            tp_hit = (future >= tp).any()
            sl_hit = (future <= sl).any()
            
            if tp_hit and (not sl_hit or (future >= tp).idxmax() <= (future <= sl).idxmax() if sl_hit else True):
                target.iloc[i] = 1
        
        return target
    
    def conduct_experiment(self, question: ResearchQuestion,
                          data: Dict[str, Any]) -> ResearchResult:
        """Run Transformer experiments."""
        if not HAS_TORCH:
            return ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings="PyTorch not available. Cannot run Transformer experiments.",
                metrics={},
                confidence=0.0,
                reproducible=False,
                limitations=["PyTorch dependency missing"],
            )
        
        if question.id == "trf_001":
            result = self._run_transformer_vs_rnn(question, data)
        elif question.id == "trf_002":
            result = self._run_positional_encoding_experiment(question, data)
        elif question.id == "trf_003":
            result = self._run_efficient_attention_experiment(question, data)
        elif question.id == "trf_004":
            result = self._run_n_heads_experiment(question, data)
        elif question.id == "trf_005":
            result = self._run_context_embedding_experiment(question, data)
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
    
    def _run_transformer_vs_rnn(self, question: ResearchQuestion,
                               data: Dict[str, Any]) -> ResearchResult:
        """Compare Transformer vs LSTM/GRU."""
        findings = []
        all_metrics = []
        
        for pair, pair_data in data["data"].items():
            X = pair_data["features"]
            y = pair_data["target"]
            
            # Simple split
            split = int(len(X) * 0.7)
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            
            # Scale
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)
            
            seq_len = 60
            X_train_seq = self._create_sequences(X_train, seq_len)
            X_test_seq = self._create_sequences(X_test, seq_len)
            y_train_seq = y_train[seq_len-1:][:len(X_train_seq)]
            y_test_seq = y_test[seq_len-1:][:len(X_test_seq)]
            
            # Models
            models = {
                "transformer": self._build_transformer(seq_len, X_train_seq.shape[2], d_model=128, n_heads=8, n_layers=4),
                "lstm": self._build_lstm(X_train_seq.shape[2]),
                "gru": self._build_gru(X_train_seq.shape[2]),
            }
            
            for name, model in models.items():
                try:
                    self._train_torch_model(model, X_train_seq, y_train_seq, epochs=20)
                    metrics = self._evaluate_torch_model(model, X_test_seq, y_test_seq)
                    metrics["pair"] = pair
                    metrics["model"] = name
                    all_metrics.append(metrics)
                    findings.append(f"{pair}/{name}: AUC={metrics['auc']:.3f}")
                except Exception as e:
                    findings.append(f"{pair}/{name}: Failed - {e}")
        
        df_metrics = pd.DataFrame(all_metrics)
        summary = df_metrics.groupby("model").mean().to_dict()
        
        # Check hypothesis: Transformer better than LSTM/GRU?
        transformer_auc = df_metrics[df_metrics["model"] == "transformer"]["auc"].mean()
        lstm_auc = df_metrics[df_metrics["model"] == "lstm"]["auc"].mean()
        improvement = transformer_auc - lstm_auc if not (pd.isna(transformer_auc) or pd.isna(lstm_auc)) else 0
        
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings=f"Transformer vs RNN comparison. Improvement: {improvement:.3f}\n" + "\n".join(findings[:10]),
            metrics=summary,
            confidence=0.8 if improvement > 0.01 else 0.5,
            reproducible=True,
            limitations=["Limited pairs", "Fixed hyperparameters"],
            recommendations={
                "transformer_better_than_lstm": improvement > 0.01,
                "best_model": df_metrics.loc[df_metrics["auc"].idxmax()]["model"] if not df_metrics.empty else None,
            }
        )
    
    def _create_sequences(self, X: np.ndarray, seq_len: int) -> np.ndarray:
        """Convert to sequences."""
        n_samples = len(X) - seq_len + 1
        if n_samples <= 0:
            raise ValueError(f"Not enough samples for seq_len={seq_len}")
        sequences = np.zeros((n_samples, seq_len, X.shape[1]), dtype=np.float32)
        for i in range(n_samples):
            sequences[i] = X[i:i+seq_len]
        return sequences
    
    def _build_transformer(self, seq_len: int, n_features: int, d_model: int = 128,
                          n_heads: int = 8, n_layers: int = 4) -> nn.Module:
        """Build standard Transformer encoder."""
        class PositionalEncoding(nn.Module):
            def __init__(self, d_model: int, max_len: int = 5000):
                super().__init__()
                pe = torch.zeros(max_len, d_model)
                position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
                div_term = torch.exp(torch.arange(0, d_model, 2).float() * 
                                   (-np.log(10000.0) / d_model))
                pe[:, 0::2] = torch.sin(position * div_term)
                pe[:, 1::2] = torch.cos(position * div_term)
                pe = pe.unsqueeze(0)  # (1, max_len, d_model)
                self.register_buffer('pe', pe)
            
            def forward(self, x: torch.Tensor) -> torch.Tensor:
                # x: (batch, seq_len, d_model)
                return x + self.pe[:, :x.size(1)]
        
        class TransformerModel(nn.Module):
            def __init__(self, seq_len, n_features, d_model, n_heads, n_layers):
                super().__init__()
                self.input_proj = nn.Linear(n_features, d_model)
                self.pos_enc = PositionalEncoding(d_model, max_len=seq_len)
                
                encoder_layer = nn.TransformerEncoderLayer(
                    d_model=d_model,
                    nhead=n_heads,
                    dim_feedforward=d_model * 4,
                    dropout=0.1,
                    activation='relu',
                    batch_first=True,
                )
                self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
                
                self.fc = nn.Sequential(
                    nn.Linear(d_model, 64),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                    nn.Linear(64, 2),
                )
            
            def forward(self, x: torch.Tensor) -> torch.Tensor:
                # x: (batch, seq_len, n_features)
                x = self.input_proj(x)
                x = self.pos_enc(x)
                x = self.transformer(x)
                # Use the output at the last timestep
                return self.fc(x[:, -1, :])
        
        return TransformerModel(seq_len, n_features, d_model, n_heads, n_layers)
    
    def _build_lstm(self, n_features: int, hidden_dim: int = 64) -> nn.Module:
        """Build LSTM."""
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
        """Build GRU."""
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
        
        signals = preds
        if signals.sum() > 0:
            win_rate = (y[signals] == 1).mean() * 100
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
    def _run_positional_encoding_experiment(self, question: ResearchQuestion,
                                           data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Positional encoding experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_efficient_attention_experiment(self, question: ResearchQuestion,
                                            data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Efficient attention experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_n_heads_experiment(self, question: ResearchQuestion,
                               data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="N-heads experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_context_embedding_experiment(self, question: ResearchQuestion,
                                          data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Context embedding experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        """Validate Transformer results."""
        validation = {
            "confidence": 0.7,
            "reproducible": True,
            "limitations": [],
        }
        
        if result.metrics:
            auc = result.metrics.get("auc", 0)
            if auc < 0.5:
                validation["limitations"].append("AUC below 0.5")
                validation["confidence"] *= 0.5
            if auc > 0.85:
                validation["limitations"].append("Very high AUC may indicate leakage")
                validation["confidence"] *= 0.7
        
        return validation
