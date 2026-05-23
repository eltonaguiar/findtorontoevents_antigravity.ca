"""
RegimeResearcher — Market Regime Detection and Adaptation
=========================================================

Specializes in identifying and adapting to different market regimes:
  - Statistical regime detection (hidden Markov models, change point detection)
  - Machine learning regime classification (clustering, supervised)
  - Regime-aware model selection and weighting
  - Volatility regime modeling (GARCH, stochastic volatility)
  - Trend strength classification (ADX-based)
  - Liquidity regime detection
  - Cross-market regime correlation

Academic foundations:
  - "Regime Detection in Financial Markets" (Ang & Bekaert, 2002)
  - "Hidden Markov Models for Regime Detection" (Hamilton, 1989)
  - "Volatility Regime Switching" (Cai, 1994)
  - "Market Regime Identification with Machine Learning" (Bulla et al., 2011)

Key research questions:
  1. Which regime detection method is most robust for crypto?
  2. Can we predict regime changes before they happen?
  3. How should models adapt once a new regime is detected?
  4. Do regime-based position sizing and risk management improve Sharpe?
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pandas as pd

from .base import Researcher, ResearchQuestion, ResearchResult

try:
    from sklearn.mixture import GaussianMixture
    HAS_GM = True
except ImportError:
    HAS_GM = False

try:
    import hmmlearn.hmm as hmm
    HAS_HMM = True
except ImportError:
    HAS_HMM = False


class RegimeResearcher(Researcher):
    """
    Researcher specializing in market regime detection and adaptation.
    
    Investigates methods for identifying market states (bull/bear/volatile/consolidation)
    and adapting trading strategies accordingly.
    """
    
    researcher_id = "regime_detection"
    name = "Regime Detection Researcher"
    specialization = "Market regime identification and adaptation"
    literature = [
        "Regime Detection in Financial Markets (Ang & Bekaert, 2002)",
        "Hidden Markov Models for Regime Detection (Hamilton, 1989)",
        "Volatility Regime Switching (Cai, 1994)",
        "Market Regime Identification with ML (Bulla et al., 2011)",
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_dir = Path(config.get("base_dir", "ml_crypto_predictor")) if config else Path("ml_crypto_predictor")
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "models" / "regime"
        self.results_dir = self.base_dir / "results" / "research" / "regime"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def formulate_questions(self) -> List[ResearchQuestion]:
        """Define research questions for regime detection."""
        return [
            ResearchQuestion(
                id="reg_001",
                title="K-Means vs Gaussian Mixture vs HMM: Best Regime Detection?",
                description="Compare three popular regime detection methods on BTC daily data: "
                          "1) K-Means clustering (current implementation in regime_detector.py)\n"
                          "2) Gaussian Mixture Model (soft clustering, probabilistic)\n"
                          "3) Hidden Markov Model (temporal dependencies). "
                          "Label regimes using expert knowledge (bull/bear/volatile/calm).",
                hypothesis="Gaussian Mixture Model will outperform K-Means because "
                          "regimes have overlapping features and GMM handles uncertainty better. "
                          "HMM may be too complex for limited data and overfit. "
                          "Expected: GMM achieves 80%+ regime classification accuracy.",
                methodology="1. Prepare 5 years of BTC daily data (OHLCV + 70+ features)\n"
                          "2. Manually label regimes for a subset (using heuristics: price trend, "
                          "   volatility, volume) as ground truth\n"
                          "3. Train K-Means (4 clusters), GMM (4 components), HMM (4 states)\n"
                          "4. Compare cluster/state labels with ground truth\n"
                          "5. Measure: accuracy, silhouette score, regime stability\n"
                          "6. Visualize regime transitions over time",
                success_criteria={
                    "gmm_better_than_kmeans": True,
                    "regime_accuracy": 0.80,
                    "silhouette_score": 0.5,
                    "regimes_stable": True,  # Low regime switching noise
                },
                priority=1,
            ),
            ResearchQuestion(
                id="reg_002",
                title="Predicting Regime Changes: Can We Forecast Transitions?",
                description="Build a model to predict upcoming regime changes (e.g., bull → bear) "
                          "1-2 weeks in advance. Use leading indicators: volatility term structure, "
                          "volume divergence, funding rates, BTC dominance, fear & greed extremes.",
                hypothesis="We can predict regime changes with 60-70% accuracy 7-14 days in advance "
                          "using a combination of: 1) volatility term structure (VIX-like indicators), "
                          "2) volume divergence from price, 3) funding rate spikes, 4) BTC dominance "
                          "breakdown. Early warning will allow defensive positioning.",
                methodology="1. Label regime change points (transition dates)\n"
                          "2. Build features that are leading indicators:\n"
                          "   - Volatility term structure (front-month vs back-month)\n"
                          "   - Volume-price divergence (OBV vs price)\n"
                          "   - Funding rate extremes and divergence\n"
                          "   - BTC dominance trend breaks\n"
                          "   - Fear & Greed index extremes (>80 or <20)\n"
                          "3. Train binary classifier: will regime change in next 7-14 days?\n"
                          "4. Use time-series cross-validation\n"
                          "5. Measure precision, recall, F1\n"
                          "6. Analyze false positives (whipsaws) vs missed transitions",
                success_criteria={
                    "predict_7d_accuracy": 0.65,
                    "predict_14d_accuracy": 0.60,
                    "precision_over_0.6": True,
                    "recall_over_0.5": True,
                },
                priority=1,
                dependencies=["reg_001"],
            ),
            ResearchQuestion(
                id="reg_003",
                title="Regime-Aware Model Selection: Which Model per Regime?",
                description="Determine which model architecture performs best in each regime. "
                          "Test: XGBoost, LightGBM, Random Forest, LSTM, Transformer, GNN. "
                          "Hypothesis: different models excel in different regimes.",
                hypothesis="Regime-optimal model mapping:\n"
                          "- Bull low-vol: LightGBM (fast, handles trends well)\n"
                          "- Bull high-vol: Transformer (captures complex patterns)\n"
                          "- Bear low-vol: Random Forest (robust, less overfitting)\n"
                          "- Bear high-vol: GNN (captures cross-asset panic)\n"
                          "Using regime-appropriate models will improve overall performance by 10-15%.",
                methodology="1. Use regime labels from reg_001\n"
                          "2. For each regime, train all model types on regime-specific data\n"
                          "3. Compare performance per regime\n"
                          "4. Build regime→model mapping\n"
                          "5. Implement regime-aware model selector\n"
                          "6. Backtest: switch models based on detected regime\n"
                          "7. Compare with always-use-best-single-model baseline",
                success_criteria={
                    "different_models_best_per_regime": True,
                    "regime_aware_improves_overall": 0.10,
                    "mapping_stable_across_time": True,
                },
                priority=1,
                dependencies=["reg_001"],
            ),
            ResearchQuestion(
                id="reg_004",
                title="Volatility Regime Detection with GARCH and Realized Vol",
                description="Separate volatility into regimes using GARCH(1,1) forecasts and "
                          "realized volatility. Identify: low-vol (<1% daily), medium-vol (1-3%), "
                          "high-vol (>3%). Test if volatility regime predicts future returns.",
                hypothesis="High volatility regimes precede short-term reversals (mean reversion) "
                          "while low volatility regimes precede trends. This can be used for "
                          "position sizing and strategy selection. Volatility regime will be "
                          "a strong predictor of next-day return direction (correlation ~0.3).",
                methodology="1. Compute GARCH(1,1) volatility forecast for BTC 1h returns\n"
                          "2. Compute 20-day realized volatility\n"
                          "3. Classify volatility regime using thresholds or clustering\n"
                          "4. Analyze next-day returns per regime\n"
                          "5. Build predictive model: volatility regime → expected return\n"
                          "6. Use for position sizing: reduce size in high-vol regimes",
                success_criteria={
                    "volatility_regime_predictive": True,
                    "correlation_with_next_return": 0.2,
                    "regime_thresholds_stable": True,
                },
                priority=2,
            ),
            ResearchQuestion(
                id="reg_005",
                title="Liquidity Regime Detection: When to Trade?",
                description="Detect liquidity regimes using bid-ask spread, order book depth, "
                          "and market impact metrics. Avoid trading in low-liquidity regimes "
                          "(low depth, high spread) to reduce slippage and improve execution.",
                hypothesis="Liquidity regimes are predictable and have strong impact on "
                          "trading costs. Low-liquidity regimes (spread > 0.1%, depth < $1M) "
                          "should be avoided — they occur 20% of the time but cause 50% of "
                          "slippage. Liquidity detection will improve net returns by 5-8%.",
                methodology="1. Collect order book data (bid/ask, depth) from Binance API\n"
                          "2. Compute liquidity metrics: spread, depth at 0.5%, impact cost\n"
                          "3. Cluster into high/medium/low liquidity regimes\n"
                          "4. Correlate liquidity regime with execution quality\n"
                          "5. Build classifier to detect low-liquidity regime in real-time\n"
                          "6. Backtest: skip trades during low-liquidity periods\n"
                          "7. Measure improvement in net P&L after slippage",
                success_criteria={
                    "liquidity_regime_detectable": True,
                    "low_liq_avoidance_improves_net_returns": 0.05,
                    "classifier_accuracy": 0.85,
                },
                priority=2,
            ),
            ResearchQuestion(
                id="reg_006",
                title="Cross-Market Regime Correlation: Do All Coins Move Together?",
                description="Analyze regime synchronization across crypto markets. "
                          "Do all coins enter bull/bear regimes simultaneously? "
                          "Or do some coins lead/lag? Identify regime leaders and laggards.",
                hypothesis="Major coins (BTC, ETH) lead regime changes, altcoins follow with "
                          "1-3 day lag. Meme coins are most lagged and most volatile. "
                          "This lead-lag relationship can be used for pair trading and "
                          "relative value strategies.",
                methodology="1. Run regime detection on top 20 coins independently\n"
                          "2. Compute regime state time series for each coin\n"
                          "3. Calculate cross-correlation of regime states\n"
                          "4. Identify leaders (Granger causality) and laggards\n"
                          "5. Test if leading coins predict lagging coin regimes\n"
                          "6. Build trading strategy: long leader, short laggard during transitions",
                success_criteria={
                    "regime_synchronization_high": True,  # But not perfect
                    "btc_eth_lead_others": True,
                    "lead_lag_predictive": True,
                    "pair_trading_opportunities": True,
                },
                priority=3,
            ),
        ]
    
    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        """Prepare data for regime detection experiments."""
        from ml_crypto_predictor.enhanced_models.data_fetcher import fetch_klines
        from ml_crypto_predictor.enhanced_models.feature_engine import build_features
        
        # Use BTC daily data for regime detection (BTC drives market)
        df = fetch_klines("BTCUSDT", "1d", 365 * 3)  # 3 years
        
        if df.empty or len(df) < 500:
            return {"error": "insufficient_data"}
        
        features = build_features(df)
        features.dropna(inplace=True)
        
        # For now, use simple features for regime detection
        regime_features = pd.DataFrame(index=features.index)
        regime_features["return_20d"] = df["close"].pct_change(20)
        regime_features["volatility_20d"] = df["close"].pct_change().rolling(20).std() * np.sqrt(365)
        regime_features["rsi_14"] = features["rsi_14"]
        regime_features["adx_14"] = features["adx_14"]
        regime_features["volume_ratio"] = features["vol_ratio_20"]
        
        # Build simple target: next 20d return sign (for supervised regime labeling)
        target = (df["close"].pct_change(20) > 0).astype(int)
        
        return {
            "features": regime_features.values,
            "target": target.loc[regime_features.index].values,
            "feature_names": list(regime_features.columns),
            "n_samples": len(regime_features),
            "timestamps": regime_features.index,
        }
    
    def conduct_experiment(self, question: ResearchQuestion,
                          data: Dict[str, Any]) -> ResearchResult:
        """Run regime detection experiments."""
        if "error" in data:
            return ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings=f"Data preparation failed: {data['error']}",
                metrics={},
                confidence=0.0,
            )
        
        if question.id == "reg_001":
            result = self._run_comparative_regime_detection(question, data)
        elif question.id == "reg_002":
            result = self._run_regime_change_prediction(question, data)
        elif question.id == "reg_003":
            result = self._run_regime_aware_model_selection(question, data)
        elif question.id == "reg_004":
            result = self._run_volatility_regime(question, data)
        elif question.id == "reg_005":
            result = self._run_liquidity_regime(question, data)
        elif question.id == "reg_006":
            result = self._run_cross_market_regime(question, data)
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
    
    def _run_comparative_regime_detection(self, question: ResearchQuestion,
                                         data: Dict[str, Any]) -> ResearchResult:
        """Compare K-Means, GMM, HMM for regime detection."""
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import silhouette_score
        
        findings = []
        X = data["features"]
        
        # Standardize
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # K-Means
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        kmeans_labels = kmeans.fit_predict(X_scaled)
        kmeans_silhouette = silhouette_score(X_scaled, kmeans_labels)
        findings.append(f"K-Means: silhouette={kmeans_silhouette:.3f}")
        
        # GMM
        if HAS_GM:
            gmm = GaussianMixture(n_components=4, random_state=42)
            gmm_labels = gmm.fit_predict(X_scaled)
            gmm_silhouette = silhouette_score(X_scaled, gmm_labels)
            findings.append(f"GMM: silhouette={gmm_silhouette:.3f}")
        else:
            gmm_silhouette = 0
            findings.append("GMM: not available (sklearn.mixture missing)")
        
        # HMM (simplified)
        if HAS_HMM:
            try:
                hmm_model = hmm.GaussianHMM(n_components=4, covariance_type="full", n_iter=100)
                hmm_model.fit(X_scaled)
                hmm_labels = hmm_model.predict(X_scaled)
                hmm_silhouette = silhouette_score(X_scaled, hmm_labels)
                findings.append(f"HMM: silhouette={hmm_silhouette:.3f}")
            except Exception as e:
                hmm_silhouette = 0
                findings.append(f"HMM: failed - {e}")
        else:
            hmm_silhouette = 0
            findings.append("HMM: not available (hmmlearn missing)")
        
        # Determine winner
        best_method = "kmeans"
        best_score = kmeans_silhouette
        if gmm_silhouette > best_score:
            best_method = "gmm"
            best_score = gmm_silhouette
        if hmm_silhouette > best_score:
            best_method = "hmm"
            best_score = hmm_silhouette
        
        findings.append(f"Best method: {best_method} (silhouette={best_score:.3f})")
        
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Regime detection comparison complete\n" + "\n".join(findings),
            metrics={
                "kmeans_silhouette": round(kmeans_silhouette, 3),
                "gmm_silhouette": round(gmm_silhouette, 3),
                "hmm_silhouette": round(hmm_silhouette, 3),
                "best_method": best_method,
            },
            confidence=0.75,
            reproducible=True,
            limitations=["Simple features", "No ground truth labels"],
            recommendations={
                "best_regime_method": best_method,
                "next": "Validate regimes against expert labels and trading outcomes",
            }
        )
    
    def _run_regime_change_prediction(self, question: ResearchQuestion,
                                     data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Regime change prediction not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_regime_aware_model_selection(self, question: ResearchQuestion,
                                         data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Regime-aware model selection not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_volatility_regime(self, question: ResearchQuestion,
                              data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Volatility regime detection not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_liquidity_regime(self, question: ResearchQuestion,
                             data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Liquidity regime detection not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_cross_market_regime(self, question: ResearchQuestion,
                                data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Cross-market regime correlation not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        """Validate regime detection results."""
        validation = {
            "confidence": 0.7,
            "reproducible": True,
            "limitations": [],
        }
        
        # Check silhouette score
        silhouette = result.metrics.get("kmeans_silhouette", 0)
        if silhouette < 0.3:
            validation["limitations"].append("Low silhouette score indicates poor cluster separation")
            validation["confidence"] *= 0.7
        
        return validation
