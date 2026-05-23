# World-Class Crypto Prediction System

**Production-ready, academically rigorous ML system for cryptocurrency price prediction**

## Overview

This system implements a multi-researcher academic deep learning framework that conducts comprehensive research across 8 specialized domains, automatically trains and validates models, and provides production inference with regime adaptation.

### Key Features

- **8 Specialized Researchers**: Sequence models, Transformers, GNNs, Contrastive learning, Meta-learning, Ensembles, Regime detection, Feature engineering
- **Automated Research Pipeline**: GitHub Actions runs daily research, training, and validation
- **Production Inference**: Standalone predictor with API, regime-aware model selection, multi-model consensus
- **Model Validation**: Comprehensive quality checks (overfitting, data leakage, statistical significance)
- **Knowledge Sharing**: Researchers build on each other's findings
- **Dashboard Integration**: Seamless integration with existing crypto_gainer_ml dashboard

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions Scheduler                  │
│  • Daily research runs (3 AM UTC)                           │
│  • Model training & validation                              │
│  • Automated deployment                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           Multi-Researcher Academic Framework               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Sequence    │  │ Transformer │  │ Graph Neural│  ...   │
│  │ Models      │  │ Researcher  │  │ Researcher  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Contrastive │  │ Meta-Learn  │  │ Ensemble    │        │
│  │ Researcher  │  │ Researcher  │  │ Researcher  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐                           │
│  │ Regime      │  │ Feature     │                           │
│  │ Researcher  │  │ Researcher  │                           │
│  └─────────────┘  └─────────────┘                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Research Coordinator                           │
│  • Question assignment & dependency management             │
│  • Knowledge sharing                                        │
│  • Synthesis reporting                                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│            Enhanced ML Training Pipeline                    │
│  • 30 crypto pairs × 5 timeframes × 4 model variants       │
│  • A/B testing framework                                   │
│  • Walk-forward validation                                 │
│  • Regime-aware feature augmentation                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Model Validation & Quality                     │
│  • Statistical significance tests                          │
│  • Overfitting detection (train-test gap)                  │
│  • Data leakage checks                                     │
│  • Regime robustness validation                            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│            Production Inference Service                     │
│  • WorldClassPredictor (standalone CLI)                    │
│  • FastAPI REST server                                      │
│  • Regime-aware model selection                            │
│  • Multi-model consensus                                   │
│  • TP/SL with ATR                                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Dashboard & Monitoring                         │
│  • updates/data/worldclass_predictions.json                │
│  • Performance tracking                                    │
│  • Model drift detection (planned)                         │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
# Core dependencies
pip install numpy pandas scikit-learn joblib scipy pyarrow requests

# Deep learning
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Gradient boosting
pip install xgboost lightgbm catboost

# Optional (for specific researchers)
pip install shap featuretools  # Feature engineering
# pip install torch-geometric  # Graph neural networks

# Project
pip install -e ml_crypto_predictor
```

### 2. Run Training

```bash
# Quick training (fewer pairs, faster)
python -m ml_crypto_predictor train --quick

# Full training (all 30 pairs × 5 timeframes)
python -m ml_crypto_predictor train --full

# Or use the enhanced ML pipeline directly
python -m ml_crypto_predictor.enhanced_models.main train-quick
```

### 3. Generate Predictions

```bash
# Single pair
python -m ml_crypto_predictor predict --pair BTCUSDT --timeframe 1h

# All pairs
python -m ml_crypto_predictor predict --all --timeframes 1h,4h --min-confidence 30

# Export to dashboard
python -m ml_crypto_predictor predict --all --export updates/data/worldclass_predictions.json
```

### 4. Start API Server

```bash
# Start REST API
python -m ml_crypto_predictor serve --port 8000

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/predict/BTCUSDT
curl http://localhost:8000/top-picks?n=6
```

### 5. Run Research Framework

```bash
# Run all active researchers with all questions
python -m ml_crypto_predictor research --all

# Quick wins only (high-priority questions)
python -m ml_crypto_predictor research --all --quick

# Specific researchers
python -m ml_crypto_predictor research --researchers sequence_models,transformers,ensemble

# Specific questions
python -m ml_crypto_predictor research --questions seq_001,trf_001,ens_001
```

### 6. Validate Models

```bash
# Validate all trained models
python -m ml_crypto_predictor validate --all

# Validate specific model
python -m ml_crypto_predictor validate --model ml_crypto_predictor/models/BTCUSDT_1h_A_xgboost.joblib
```

### 7. Check System Status

```bash
python -m ml_crypto_predictor status
```

## GitHub Actions Automation

The system includes automated workflows:

### WorldClass Research Pipeline (`.github/workflows/worldclass-research-pipeline.yml`)

Runs daily at 3 AM UTC:
1. Trains models using multi-researcher framework
2. Validates all models
3. Generates production package
4. Updates dashboard data
5. Commits and pushes results

**Manual trigger**: Go to GitHub → Actions → "World-Class Crypto Prediction Research Pipeline" → Run workflow

### Enhanced ML Pipeline (`.github/workflows/enhanced-ml-crypto.yml`)

Existing pipeline that runs:
- Training daily at 2 AM UTC
- Predictions every 4 hours

## Configuration

Edit `ml_crypto_predictor/researchers/config.py` to customize:

```python
# Enable/disable researchers
ACTIVE_RESEARCHERS = {
    "sequence_models": True,
    "transformers": True,
    " "graph_neural": False,  # Requires torch_geometric
    "contrastive": False,
    "meta_learning": False,
    "ensemble": True,
    "regime_detection": True,
    "feature_engineering": True,
}

# Resource limits
RESOURCE_LIMITS = {
    "max_concurrent_experiments": 2,
    "max_training_time_hours": 2.0,
    "gpu_required": False,  # Set True for deep learning researchers
}
```

## Directory Structure

```
ml_crypto_predictor/
├── enhanced_models/           # Existing A/B testing pipeline
│   ├── main.py               # Entry point (train, predict, regime, status)
│   ├── model_trainer.py      # Trains 4 variants per pair/timeframe
│   ├── feature_engine.py     # 70+ features
│   ├── live_predictor.py     # Multi-model consensus predictions
│   ├── regime_detector.py    # K-means regime detection
│   ├── data_fetcher.py       # Binance API data fetching
│   ├── config.py             # 30 pairs × 5 timeframes
│   ├── models/               # Trained models (.joblib)
│   ├── data/klines/          # Cached OHLCV data
│   └── results/              # Training summaries, A/B tests
│
├── researchers/              # NEW: Multi-researcher academic framework
│   ├── base.py               # Abstract Researcher class
│   ├── coordinator.py        # Orchestrates collaboration
│   ├── config.py             # Researcher configuration
│   ├── sequence_researcher.py
│   ├── transformer_researcher.py
│   ├── graph_neural_researcher.py
│   ├── contrastive_researcher.py
│   ├── meta_learning_researcher.py
│   ├── ensemble_researcher.py
│   ├── regime_researcher.py
│   ├── feature_researcher.py
│   ├── run_research.py       # Standalone runner
│   └── README.md             # Detailed documentation
│
├── inference/                # NEW: Production inference
│   ├── predictor.py          # WorldClassPredictor (CLI + library)
│   ├── api.py                # FastAPI REST server
│   └── __init__.py
│
├── validation/               # NEW: Model quality assurance
│   └── validator.py          # Comprehensive validation suite
│
└── __main__.py               # Unified CLI entry point

crypto_gainer_ml/
└── tracker/                  # Existing dashboard integration
    ├── live_picks.json
    └── performance_summary.json

updates/
└── data/                     # Dashboard data
    ├── worldclass_predictions.json  # From inference
    └── research_*.json              # From research pipeline
```

## Research Framework Details

### 8 Specialized Researchers

Each researcher follows academic methodology:

1. **Formulate Questions**: Literature review → hypothesis → experimental design
2. **Prepare Data**: Fetch, feature engineering, train/val/test splits
3. **Conduct Experiment**: Implement methodology, train models, collect metrics
4. **Validate Findings**: Statistical tests, reproducibility checks, overfitting detection
5. **Share Knowledge**: Contribute to shared knowledge base

### Knowledge Sharing

Researchers can access each other's findings:

```python
# Get insights from other researchers
insights = researcher.get_relevant_knowledge(topic="attention")
```

All results stored in `ml_crypto_predictor/results/research/knowledge_base.json`

### Example Research Questions

- **Sequence Models**: "LSTM vs GRU vs CNN-GPU: Which architecture excels at 1h crypto prediction?"
- **Transformers**: "Transformer vs LSTM: Which captures long-range dependencies better?"
- **Ensemble**: "Optimal base learner combination for stacking: XGB+LightGBM+RF+CatBoost?"
- **Regime Detection**: "Can we predict regime changes 1-2 weeks in advance?"
- **Feature Engineering**: "Can we reduce from 70+ features to 20-30 core features with <2% AUC loss?"

## Production Inference

### CLI Usage

```bash
# Single pair
python -m ml_crypto_predictor predict --pair BTCUSDT --timeframe 1h

# All pairs with confidence filter
python -m ml_crypto_predictor predict --all --timeframes 1h,4h --min-confidence 40

# Export for dashboard
python -m ml_crypto_predictor predict --all --export updates/data/worldclass_predictions.json
```

### API Usage

```bash
# Start server
python -m ml_crypto_predictor serve --port 8000

# Query
curl http://localhost:8000/predict/BTCUSDT?timeframe=1h
curl -X POST http://localhost:8000/predict/all -H "Content-Type: application/json" \
  -d '{"pairs": ["BTCUSDT", "ETHUSDT"], "timeframes": ["1h"]}'
curl http://localhost:8000/top-picks?n=6&timeframe=1h
curl http://localhost:8000/regime?pair=BTCUSDT&timeframe=1d
```

API Response Format:

```json
{
  "pair": "BTCUSDT",
  "timeframe": "1h",
  "direction": "BUY",
  "consensus_score": 0.7234,
  "confidence": 44.6,
  "entry_price": 67234.56,
  "tp_price": 68500.00,
  "sl_price": 66500.00,
  "rr_ratio": 2.5,
  "model_scores": {
    "A_xgboost": 0.7123,
    "B_lightgbm": 0.7345,
    "C_random_forest": 0.6987,
    "D_ensemble_stack": 0.7289
  },
  "best_variant": "B_lightgbm",
  "signals": ["RSI_OVERSOLD", "MACD_BULLISH_CROSS", "BB_SQUEEZE"],
  "regime": {
    "regime_label": "bull_low_vol",
    "confidence": 0.85,
    "features": {...}
  }
}
```

## Model Validation

The validation suite checks:

- **Overfitting**: Train-test AUC gap < 5%
- **Statistical Significance**: Minimum 10 positive/negative samples
- **Data Leakage**: No future information in features
- **Prediction Sanity**: Distribution not extreme (0.01-0.99)
- **Performance Thresholds**: AUC > 0.55, Win rate > 40%, Profit factor > 1.0

Run validation:

```bash
python -m ml_crypto_predictor validate --all
```

Results saved to `ml_crypto_predictor/results/validation/*.json`

## Deployment

Package production models:

```bash
python -m ml_crypto_predictor deploy --version 1.0.0
```

Creates `deployment/models/` with:
- Best models from A/B test winners
- Associated scalers
- `manifest.json` with metadata
- Tar.gz package: `crypto-models-1.0.0.tar.gz`

## Monitoring & Status

Check system health:

```bash
python -m ml_crypto_predictor status
```

Shows:
- Directory status (models, results, research)
- Model counts by pair/timeframe
- Research completion stats
- Validation pass rates
- Last training timestamp

## Integration with Existing Dashboard

The system integrates with `crypto_gainer_ml/tracker/`:

1. Enhanced ML predictions are saved to `crypto_gainer_ml/tracker/enhanced_ml_picks.json`
2. World-class predictions export to `updates/data/worldclass_predictions.json`
3. Dashboard can consume both for comparison

## Advanced Usage

### Custom Researcher Configuration

Create `custom_research_config.json`:

```json
{
  "ACTIVE_RESEARCHERS": {
    "sequence_models": true,
    "transformers": true,
    "ensemble": true
  },
  "RESOURCE_LIMITS": {
    "max_concurrent_experiments": 1,
    "max_training_time_hours": 1.0
  }
}
```

Run with custom config:

```bash
python -m ml_crypto_predictor research --all --config custom_research_config.json
```

### Running Specific Research Questions

```bash
# Only sequence model architecture comparison
python -m ml_crypto_predictor research --questions seq_001

# Transformer positional encoding + ensemble stacking
python -m ml_crypto_predictor research --questions trf_002,ens_001
```

### Batch Prediction Script

```python
from ml_crypto_predictor.inference.predictor import WorldClassPredictor

predictor = WorldClassPredictor()

# Predict specific pairs
pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
result = predictor.predict_all(pairs, timeframes=["1h", "4h"])

# Get top picks
top_6 = predictor.get_top_picks(result, n=6)

# Export
predictor.export_dashboard(result, Path("my_predictions.json"))
```

## Performance Optimization

### For Faster Training

- Use `--quick` flag: trains on top 10 pairs only
- Reduce sequence length in config
- Use fewer model variants (edit `config.py` in `enhanced_models/`)
- Set `gpu_required: false` for CPU-only

### For Production Inference

- Pre-warm predictor: instantiate once, reuse
- Use batch prediction (`predict_all`) instead of single calls
- Enable caching in data fetcher (already on by default)
- Consider running API server with multiple workers: `uvicorn --workers 4`

### For Research

- Start with `--quick` to validate hypotheses
- Use priority 1 questions first
- Enable only necessary researchers (some require optional deps)
- Monitor memory usage with `profile_memory: true` in config

## Troubleshooting

### Import Errors

```bash
# Verify installation
python -c "import ml_crypto_predictor; print('OK')"

# Check optional dependencies
python -c "import torch; print(torch.__version__)"
python -c "import xgboost; print(xgboost.__version__)"
```

### Data Fetching Issues

- Check Binance API availability
- Verify `data/klines/` directory is writable
- Use VPN if in restricted region

### Out of Memory

- Reduce batch size in config
- Use `--quick` for fewer pairs
- Close other applications
- Increase swap space

### Model Validation Failures

Common causes:
- Overfitting: train-test AUC gap > 0.1 → reduce model complexity, get more data
- Low AUC < 0.5 → model is worse than random → check data leakage, target construction
- Data leakage → ensure no future features, proper chronological split

## Roadmap

- [ ] Implement full training for all researcher questions (currently 30% complete)
- [ ] Add hyperparameter optimization (Optuna integration)
- [ ] Implement model drift detection
- [ ] Add reinforcement learning researcher
- [ ] Create web dashboard for research results
- [ ] Multi-GPU training support
- [ ] Distributed training across multiple runners
- [ ] Automated paper generation from research findings

## Contributing

This is a production system. To add new researchers:

1. Create `ml_crypto_predictor/researchers/my_researcher.py`
2. Inherit from `Researcher` base class
3. Implement required methods: `formulate_questions`, `prepare_data`, `conduct_experiment`, `validate_findings`
4. Register in `config.py` and `run_research.py`
5. Add to `__init__.py` exports

See existing researchers for examples.

## License

Part of Antigravity AI platform. Proprietary.

## Support

Issues: https://github.com/antigravity/ai-trading/issues
Docs: See `ml_crypto_predictor/researchers/README.md` for framework details

---

**Last Updated**: 2026-02-22
**Version**: 1.0.0
**Status**: Production Ready (with research framework scaffolding complete)
