# Machine Learning Trading System Architecture

## Complete Design Document

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [ML Architecture Overview](#ml-architecture-overview)
3. [Feature Engineering Pipeline](#feature-engineering-pipeline)
4. [Model Selection Framework](#model-selection-framework)
5. [Cross-Validation Strategies](#cross-validation-strategies)
6. [Meta-Learner Design](#meta-learner-design)
7. [StrategyArbitrator Class](#strategyarbitrator-class)
8. [ML-in-Finance Challenges](#ml-in-finance-challenges)
9. [Implementation Details](#implementation-details)
10. [Usage Examples](#usage-examples)

---

## Executive Summary

This document presents a comprehensive Machine Learning architecture for stock trading algorithms that addresses the unique challenges of financial time series prediction. The system includes:

- **Feature Engineering Pipeline**: 8 feature families with 100+ features
- **Model Selection Framework**: Tree models, linear models, and ensemble methods
- **Purged Cross-Validation**: Prevents data leakage in time series
- **Meta-Learner (StrategyArbitrator)**: Dynamically weights strategies based on regime
- **Regime Detection**: Identifies market conditions for adaptive allocation
- **Multiple Hypothesis Correction**: Controls false discovery rate
- **Ablation Testing**: Validates feature contributions

---

## ML Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ML TRADING SYSTEM ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │  Raw Data    │───▶│   Feature    │───▶│   Models     │                   │
│  │  (OHLCV)     │    │  Engineering │    │  (Multiple)  │                   │
│  └──────────────┘    └──────────────┘    └──────┬───────┘                   │
│                                                  │                          │
│                              ┌───────────────────┘                          │
│                              ▼                                              │
│                    ┌──────────────────┐                                     │
│                    │  Cross-Validate  │                                     │
│                    │  (Purged K-Fold) │                                     │
│                    └────────┬─────────┘                                     │
│                             │                                               │
│                             ▼                                               │
│                    ┌──────────────────┐                                     │
│                    │ Strategy Signals │                                     │
│                    └────────┬─────────┘                                     │
│                             │                                               │
│                             ▼                                               │
│         ┌─────────────────────────────────────┐                             │
│         │      STRATEGY ARBITRATOR            │                             │
│         │  ┌─────────────┐  ┌──────────────┐  │                             │
│         │  │   Regime    │  │   Dynamic    │  │                             │
│         │  │  Detection  │  │   Weighting  │  │                             │
│         │  └─────────────┘  └──────────────┘  │                             │
│         │  ┌─────────────┐  ┌──────────────┐  │                             │
│         │  │ Performance │  │   Silence    │  │                             │
│         │  │  Tracking   │  │ Underperform │  │                             │
│         │  └─────────────┘  └──────────────┘  │                             │
│         └──────────────────┬──────────────────┘                             │
│                            │                                                │
│                            ▼                                                │
│                  ┌─────────────────┐                                        │
│                  │ Ensemble Signal │                                        │
│                  │   + Confidence  │                                        │
│                  └─────────────────┘                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Feature Engineering Pipeline

### Feature Families

| Family | Description | Key Features | Count |
|--------|-------------|--------------|-------|
| **Trend** | Moving averages, trend strength | MA, EMA, MACD, slope | ~20 |
| **Momentum** | Rate of change, RSI | ROC, RSI, returns | ~15 |
| **Volatility** | Realized vol, ATR, Bollinger Bands | Vol_20d, ATR, BB | ~15 |
| **Volume** | Volume trends, OBV, VWAP | Volume MA, OBV, VWAP | ~10 |
| **Mean Reversion** | Z-scores from means | Z-score MA, dist from max/min | ~10 |
| **Cross-Sectional** | Rankings, percentiles | Return percentile, rank | ~8 |
| **Seasonality** | Calendar effects | Day of week, month, quarter | ~10 |
| **Regime** | Market state indicators | Trend strength, vol regime | ~8 |

### Feature Configuration

```python
class FeatureConfig:
    # Lookback windows
    trend_windows: List[int] = [5, 10, 20, 50, 200]
    momentum_windows: List[int] = [5, 10, 20, 60]
    volatility_windows: List[int] = [5, 10, 20, 60]
    volume_windows: List[int] = [5, 10, 20]
    
    # Technical parameters
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    bb_period: int = 20
    bb_std: float = 2.0
```

### Key Methods

```python
class FeatureEngineer:
    def fit(self, X: pd.DataFrame, y=None) -> 'FeatureEngineer'
    def transform(self, X: pd.DataFrame, fit_scaler: bool = False) -> pd.DataFrame
    def get_feature_importance_mask(self, X, y, threshold=0.01) -> List[bool]
```

---

## Model Selection Framework

### Supported Models

| Model Type | Use Case | Strengths |
|------------|----------|-----------|
| **LightGBM** | Default classifier | Fast, handles non-linearity |
| **XGBoost** | High-performance | Regularization, feature importance |
| **Random Forest** | Baseline/ensemble | Robust, interpretable |
| **Gradient Boosting** | Complex patterns | Sequential error correction |
| **Logistic Regression** | Linear baseline | Fast, interpretable |
| **Ridge** | Meta-learner | Stable, prevents overfitting |
| **Elastic Net** | Feature selection | L1/L2 regularization |

### Model Factory

```python
class ModelFactory:
    @staticmethod
    def create_model(
        model_type: ModelType,
        model_config: ModelConfig = None,
        task: str = "classification",
        **kwargs
    ) -> BaseMLModel
```

### Model Configuration

```python
class ModelConfig:
    model_type: ModelType = ModelType.LIGHTGBM
    prediction_horizon: int = 5  # Days ahead
    target_type: str = "direction"  # "direction", "return", "quantile"
    
    # Cross-validation
    cv_folds: int = 5
    cv_purge_gap: int = 5
    cv_embargo_pct: float = 0.02
    
    # Walk-forward
    wf_train_size: int = 252 * 2  # 2 years
    wf_test_size: int = 63  # 3 months
    wf_step_size: int = 21  # 1 month
```

---

## Cross-Validation Strategies

### 1. Purged K-Fold Cross-Validation

**Purpose**: Prevent data leakage between train and test sets in time series.

**Mechanism**:
- **Purge Gap**: Remove observations near test set boundary
- **Embargo**: Additional buffer after test set

```python
class PurgedKFold(BaseCrossValidator):
    def __init__(
        self,
        n_splits: int = 5,
        purge_gap: int = 5,        # Bars to purge
        embargo_pct: float = 0.01  # Embargo percentage
    )
```

**Visual Representation**:
```
Fold 1: [TRAIN] [PURGE] [TEST] [EMBARGO] [TRAIN]
Fold 2: [TRAIN] [EMBARGO] [TRAIN] [PURGE] [TEST] [EMBARGO] [TRAIN]
Fold 3: [TRAIN] [EMBARGO] [TRAIN] [EMBARGO] [TRAIN] [PURGE] [TEST]
```

### 2. Walk-Forward Cross-Validation

**Purpose**: Simulate real-world deployment where model is retrained periodically.

```python
class WalkForwardCV(BaseCrossValidator):
    def __init__(
        self,
        train_size: int,      # Training window size
        test_size: int,       # Test window size
        step_size: int,       # Step between windows
        purge_gap: int = 5,
        embargo_pct: float = 0.01
    )
```

**Visual Representation**:
```
Time →
[TRAIN: 2 years] [PURGE] [TEST: 3 months] [EMBARGO]
         [TRAIN: 2 years] [PURGE] [TEST: 3 months] [EMBARGO]
                  [TRAIN: 2 years] [PURGE] [TEST: 3 months]
```

### 3. Combinatorial Cross-Validation

**Purpose**: Assess backtest overfitting through multiple train/test combinations.

```python
class CombinatorialCV(BaseCrossValidator):
    def __init__(
        self,
        n_splits: int = 10,      # Total splits
        n_test_splits: int = 2,  # Test splits per combination
        purge_gap: int = 5
    )
```

---

## Meta-Learner Design

### Architecture

The meta-learner combines predictions from multiple base models using:

1. **Stacking**: Train meta-model on base model predictions
2. **Dynamic Weighting**: Adjust weights based on recent performance
3. **Regime-Aware Allocation**: Different weights for different regimes

### Meta-Learner Training

```python
def train_meta_learner(
    self,
    X: pd.DataFrame,              # Regime indicators
    y: pd.Series,                 # Target returns
    strategy_signals: pd.DataFrame  # Base model predictions
) -> None
```

### Meta-Features

```python
def _create_meta_features(
    self,
    X: pd.DataFrame,
    strategy_signals: pd.DataFrame
) -> pd.DataFrame:
    meta_features = pd.DataFrame(index=X.index)
    
    # Regime features
    meta_features['volatility_regime'] = X['vol_regime']
    meta_features['trend_strength'] = X['trend_strength_20']
    
    # Strategy signals
    for col in strategy_signals.columns:
        meta_features[f'signal_{col}'] = strategy_signals[col]
    
    # Interaction features
    for col1 in strategy_signals.columns:
        for col2 in ['vol_regime', 'trend_strength_20']:
            meta_features[f'interaction_{col1}_{col2}'] = (
                strategy_signals[col1] * X[col2]
            )
    
    return meta_features
```

---

## StrategyArbitrator Class

### Class Definition

```python
class StrategyArbitrator:
    """
    Meta-learner that arbitrates between multiple trading strategies.
    
    Key Functions:
    1. Monitor strategy performance in real-time
    2. Detect market regimes
    3. Dynamically weight strategies based on regime and performance
    4. Silence underperforming strategies
    5. Provide confidence scores for combined signals
    """
    
    def __init__(
        self,
        config: ModelConfig = None,
        regime_detector: RegimeDetector = None,
        lookback_window: int = 63,
        performance_metric: str = "sharpe"
    )
```

### Input/Output Specifications

**Input**:
```python
@dataclass
class StrategySignal:
    strategy_id: str
    timestamp: datetime
    signal: SignalType  # LONG, SHORT, NEUTRAL
    confidence: float   # 0 to 1
    expected_return: float
    volatility: float
    regime: RegimeType
    metadata: Dict[str, Any]
```

**Output**:
```python
{
    'signal': SignalType,           # Final ensemble signal
    'confidence': float,            # Overall confidence (0-1)
    'weighted_signal': float,       # Continuous signal (-1 to 1)
    'signal_strength': float,       # Absolute signal strength
    'consensus_ratio': float,       # Strategy agreement level
    'n_active_strategies': int,     # Number of active strategies
    'regime': str,                  # Current regime
    'regime_confidence': float,     # Regime detection confidence
    'strategy_breakdown': Dict      # Per-strategy details
}
```

### Key Methods

```python
# Register a strategy
def register_strategy(
    self,
    strategy_id: str,
    strategy_info: Dict = None
) -> None

# Process incoming signals
def process_signals(
    self,
    signals: List[StrategySignal],
    market_features: pd.DataFrame,
    market_returns: pd.Series
) -> Dict

# Train meta-learner
def train_meta_learner(
    self,
    X: pd.DataFrame,
    y: pd.Series,
    strategy_signals: pd.DataFrame
) -> None

# Get strategy summary
def get_strategy_summary(self) -> pd.DataFrame
```

### Dynamic Strategy Weighting Logic

```python
def _update_weights(self, regime_state: RegimeState) -> None:
    """Update strategy weights based on regime and performance."""
    
    # Calculate recent performance for each strategy
    for strategy_id, perf_df in self.strategy_performance.items():
        # Get performance score (Sharpe, return, etc.)
        score = perf_df['sharpe_ratio'].tail(self.lookback_window).mean()
        
        # Apply regime-specific multiplier
        regime_multiplier = self._get_regime_multiplier(
            strategy_id, regime_state.regime
        )
        
        regime_perf[strategy_id] = score * regime_multiplier
    
    # Convert to weights using softmax
    scores = np.array(list(regime_perf.values()))
    exp_scores = np.exp(scores - np.max(scores))
    weights = exp_scores / np.sum(exp_scores)
```

### Regime-Specific Multipliers

```python
TREND_FOLLOWING_MULTIPLIERS = {
    RegimeType.BULL_TREND: 1.5,
    RegimeType.BEAR_TREND: 1.3,
    RegimeType.TRENDING: 1.4,
    RegimeType.RANGING: 0.5,
    RegimeType.HIGH_VOLATILITY: 0.7,
    RegimeType.CRISIS: 0.3
}

MEAN_REVERSION_MULTIPLIERS = {
    RegimeType.RANGING: 1.5,
    RegimeType.LOW_VOLATILITY: 1.4,
    RegimeType.BULL_TREND: 0.6,
    RegimeType.BEAR_TREND: 0.5,
    RegimeType.TRENDING: 0.4,
    RegimeType.CRISIS: 0.2
}
```

### Confidence Scoring

```python
def _calculate_confidence(
    self,
    weighted_signal: float,
    consensus_ratio: float,
    regime_confidence: float,
    signals: List[StrategySignal]
) -> float:
    """
    Calculate overall confidence score.
    
    Components:
    - Signal strength: 40%
    - Average strategy confidence: 20%
    - Consensus ratio: 20%
    - Regime confidence: 20%
    """
    signal_confidence = min(abs(weighted_signal), 1.0)
    avg_confidence = np.mean([s.confidence for s in signals])
    
    confidence = (
        signal_confidence * 0.4 +
        avg_confidence * 0.2 +
        consensus_ratio * 0.2 +
        regime_confidence * 0.2
    )
    
    return min(confidence, 1.0)
```

---

## ML-in-Finance Challenges

### 1. Preventing Lookahead Bias

**Problem**: Using future information that wouldn't be available at prediction time.

**Solutions**:

```python
def prevent_lookahead_bias(
    df: pd.DataFrame,
    feature_cols: List[str] = None,
    strict: bool = True
) -> pd.DataFrame:
    """
    Techniques:
    1. Verify no future data in feature calculation
    2. Ensure targets are shifted properly
    3. Check for data leakage indicators
    """
    
    # Check for suspicious autocorrelation
    for col in feature_cols:
        autocorr = series.autocorr(lag=1)
        if abs(autocorr) > 0.99:
            raise ValueError(f"Potential lookahead bias in {col}")
    
    # Ensure proper target shifting
    target = returns.shift(-horizon)  # Future returns
```

**Best Practices**:
- Always use `shift()` for target creation
- Calculate features using only past data
- Use rolling windows that don't include current bar
- Validate with purged cross-validation

### 2. Handling Non-Stationarity

**Problem**: Financial time series have changing statistical properties over time.

**Solutions**:

```python
def handle_non_stationarity(
    X: pd.DataFrame,
    method: str = "difference"
) -> pd.DataFrame:
    """
    Methods:
    - difference: First difference
    - normalize: Normalize by rolling statistics
    - quantile: Convert to quantile ranks
    - neutralize: Remove common trends (PCA)
    """
    
    if method == "difference":
        X_clean = X.diff().dropna()
    
    elif method == "normalize":
        for col in X.columns:
            rolling_mean = X[col].rolling(252).mean()
            rolling_std = X[col].rolling(252).std()
            X_clean[col] = (X[col] - rolling_mean) / rolling_std
    
    elif method == "quantile":
        for col in X.columns:
            X_clean[col] = X[col].rolling(252).apply(
                lambda x: stats.percentileofscore(x, x.iloc[-1]) / 100
            )
```

### 3. Feature Importance and Ablation Testing

```python
class AblationTester:
    """
    Tests contribution of features by removing them
    and measuring performance degradation.
    """
    
    def test_feature_ablation(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        feature_groups: Dict[str, List[str]] = None,
        metric: Callable = accuracy_score
    ) -> pd.DataFrame:
        
        # Baseline performance
        baseline_scores = self._cross_val_score(X, y, metric)
        baseline_mean = np.mean(baseline_scores)
        
        # Test each feature group
        for group_name, features in feature_groups.items():
            X_ablated = X.drop(columns=features)
            ablated_scores = self._cross_val_score(X_ablated, y, metric)
            
            # Calculate importance
            importance = baseline_mean - np.mean(ablated_scores)
```

### 4. Multiple Hypothesis Correction

```python
class MultipleHypothesisCorrection:
    """
    Controls false discovery rate in feature selection
    and model comparison.
    """
    
    @staticmethod
    def benjamini_hochberg(
        p_values: np.ndarray,
        alpha: float = 0.05
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Benjamini-Hochberg FDR correction.
        
        Find largest k such that p(k) <= (k/m) * alpha
        """
        n_tests = len(p_values)
        sorted_indices = np.argsort(p_values)
        sorted_pvals = p_values[sorted_indices]
        
        thresholds = np.arange(1, n_tests + 1) / n_tests * alpha
        rejected_sorted = sorted_pvals <= thresholds
        
        k = np.max(np.where(rejected_sorted)[0]) if np.any(rejected_sorted) else -1
        
        rejected = np.zeros(n_tests, dtype=bool)
        if k >= 0:
            rejected[sorted_indices[:k+1]] = True
        
        return rejected, adjusted_pvals
```

---

## Implementation Details

### Complete Pipeline

```python
class MLPipeline:
    """
    Complete ML pipeline for financial time series.
    """
    
    def __init__(
        self,
        feature_config: FeatureConfig = None,
        model_config: ModelConfig = None
    ):
        self.feature_engineer = FeatureEngineer(feature_config)
        self.models: Dict[str, BaseMLModel] = {}
        self.ensemble: Optional[StrategyArbitrator] = None
    
    def prepare_data(
        self,
        df: pd.DataFrame,
        target_type: str = "direction",
        horizon: int = 5
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Generate features and target."""
        features = self.feature_engineer.fit_transform(df)
        
        # NO LOOKAHEAD BIAS: Shift target
        returns = df['close'].pct_change(horizon).shift(-horizon)
        target = (returns > 0).astype(int)
        
        return features, target
    
    def train_models(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_types: List[ModelType] = None
    ) -> Dict:
        """Train multiple models with CV."""
        for model_type in model_types:
            for fold, (train_idx, test_idx) in enumerate(self.cv.split(X, y)):
                model = ModelFactory.create_model(model_type, self.config, task)
                model.fit(X.iloc[train_idx], y.iloc[train_idx])
                self.models[f"{model_type.value}_fold_{fold}"] = model
    
    def create_ensemble(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> StrategyArbitrator:
        """Create ensemble with meta-learner."""
        self.ensemble = StrategyArbitrator(config=self.model_config)
        
        for model_name in self.models:
            self.ensemble.register_strategy(f"ml_model_{model_name}")
        
        return self.ensemble
```

---

## Usage Examples

### Basic Usage

```python
# 1. Initialize pipeline
from ml_trading_system_design import *

feature_config = FeatureConfig(
    trend_windows=[5, 10, 20, 50],
    momentum_windows=[5, 10, 20],
    include_seasonality=True
)

model_config = ModelConfig(
    prediction_horizon=5,
    ensemble_method="stacking"
)

pipeline = MLPipeline(feature_config, model_config)

# 2. Prepare data
X, y = pipeline.prepare_data(df, target_type="direction", horizon=5)

# 3. Create CV splitter
cv = pipeline.create_cv_splitter("walk_forward")

# 4. Train models
results = pipeline.train_models(X, y, model_types=[
    ModelType.LIGHTGBM,
    ModelType.RANDOM_FOREST,
    ModelType.RIDGE
])

# 5. Create ensemble
ensemble = pipeline.create_ensemble(X, y)

# 6. Process signals
signals = [
    StrategySignal(
        strategy_id="ml_model_lightgbm_fold_0",
        timestamp=df.index[-1],
        signal=SignalType.LONG,
        confidence=0.75,
        expected_return=0.02,
        volatility=0.15,
        regime=RegimeType.BULL_TREND
    ),
    # ... more signals
]

result = ensemble.process_signals(signals, market_features, market_returns)
```

### Advanced: Regime-Aware Allocation

```python
# Configure regime-specific multipliers
ensemble.regime_strategy_map = {
    RegimeType.BULL_TREND: {
        'trend_following': 1.5,
        'momentum': 1.4,
        'mean_reversion': 0.6
    },
    RegimeType.HIGH_VOLATILITY: {
        'trend_following': 0.7,
        'volatility': 1.5,
        'mean_reversion': 0.8
    }
}

# Process signals with regime awareness
result = ensemble.process_signals(signals, features, returns)
print(f"Regime: {result['regime']}")
print(f"Signal: {result['signal'].name}")
print(f"Confidence: {result['confidence']:.2%}")
```

### Running Ablation Study

```python
# Define feature groups
feature_groups = {
    'trend': [c for c in X.columns if 'ma_' in c or 'macd' in c],
    'momentum': [c for c in X.columns if 'momentum' in c or 'rsi' in c],
    'volatility': [c for c in X.columns if 'volatility' in c or 'atr' in c],
    'volume': [c for c in X.columns if 'volume' in c or 'obv' in c],
}

# Run ablation
ablation_results = pipeline.run_ablation_study(X, y, feature_groups)

# View results
print(ablation_results[['feature_group', 'importance', 'importance_pct']])
```

---

## Summary

This ML trading system architecture provides:

1. **Robust Feature Engineering**: 8 families of features with 100+ indicators
2. **Leakage-Preventing CV**: Purged K-Fold and Walk-Forward methods
3. **Dynamic Meta-Learning**: StrategyArbitrator adapts to market regimes
4. **Statistical Rigor**: Multiple hypothesis correction and ablation testing
5. **Production-Ready**: Clean class structure with comprehensive documentation

The system is designed to be:
- **Modular**: Each component can be used independently
- **Extensible**: Easy to add new models, features, or strategies
- **Testable**: Built-in ablation and validation frameworks
- **Robust**: Handles non-stationarity and prevents overfitting

---

## File Locations

- **Main Implementation**: `/mnt/okcomputer/output/ml_trading_system_design.py`
- **Documentation**: `/mnt/okcomputer/output/ML_TRADING_SYSTEM_DESIGN.md`
