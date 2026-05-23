# Researcher Profile: Dr. Emily Carter

## Persona
- **Title:** Cloud AI/ML Solutions Architect
- **Expertise:** AWS, GCP, Azure ML services for crypto trading
- **Years Experience:** 12
- **Background:** PhD Stanford CS, former AWS Solutions Architect, now designs cloud ML platforms for crypto firms.

## Research Scope
**Primary Question:** Which cloud services (AWS, GCP, Azure) are best suited for building and deploying crypto ML prediction systems at scale?

**Target Systems/Areas:**
- AWS SageMaker (training + deployment)
- Google Vertex AI
- Azure Machine Learning
- Lambda functions for serverless inference
- Cloud GPUs/TPUs for training
- Data storage (S3, BigQuery, Cosmos DB)

## Methodology
1. **Sources:** Full codebase audit of `E:\findtorontoevents_antigravity.ca`, cloud provider documentation, pricing calculators.
2. **Extraction:** Examined 107 GitHub Actions workflows, all ML training pipelines, database layers, model storage patterns, and deployment mechanisms.
3. **Analysis:** Mapped current architecture against cloud migration opportunities, identified bottlenecks and cost/benefit tradeoffs.
4. **Validation:** Cross-referenced actual model artifact counts, database sizes, and workflow execution patterns.

---

## Key Findings (REAL CODEBASE AUDIT)

### Finding 1: Compute Infrastructure Is 100% GitHub Actions (CPU-Only)

**Current State:** Every ML training and inference workload runs on `ubuntu-latest` GitHub Actions runners. There are **107 workflow files** in `.github/workflows/`, with the following ML-relevant schedules:

| Workflow | Schedule | Timeout | Purpose |
|---|---|---|---|
| `alpha-engine-live.yml` | Every 15 min | 12 min | Production scanner (100 strategies), ML accelerator, RF auto-training |
| `crypto-ml-edge.yml` | Every 30 min | 15 min | LightGBM Edge Engine + Gainer Detector |
| `ml-battleground-a.yml` | Every 15 min | 10 min | System A (XGBoost filter) scanner |
| `enhanced-ml-crypto.yml` | Daily 2AM + every 4h | 60 min | Multi-model A/B testing (30 pairs x 5 timeframes) |
| `train_crypto_models.yml` | Daily midnight | default | XGBoost ensemble + walk-forward validation |
| `ml-battleground-bootstrap.yml` | On-demand | default | Bootstrap validation for all systems |

**Critical Limitation:** All runners are 2-core, 7GB RAM, CPU-only. No GPU/TPU access. The `train_model.py` in `ml_battleground/system_c_deeplearn/` includes PyTorch GRU-Attention training that checks `torch.cuda.is_available()` but always falls back to CPU in CI. Training is constrained to small models and limited data.

**Cloud Migration Opportunity:** HIGH. Moving training to cloud GPU instances (AWS p3.2xlarge or GCP A100) would unlock:
- Larger GRU/Transformer models (currently capped at ~128 hidden, 2 layers due to CPU time limits)
- Longer training runs (currently limited to 10-60 min timeouts)
- Hyperparameter search at scale (Optuna currently limited to 20 trials in `crypto_ml_edge/trainer.py`)

### Finding 2: Zero Cloud SDK Usage -- Entirely Self-Hosted

**Current State:** A grep for `boto3`, `google-cloud`, `azure`, `amazonaws`, and `s3_` across the entire codebase returned **zero Python SDK imports**. The codebase has no cloud provider dependencies whatsoever.

The only external services used are:
- **Binance API** (spot + futures) for OHLCV data and funding rates
- **CoinGecko API** for market caps and trending data
- **Alternative.me** for Fear & Greed Index
- **yfinance** for equity/forex data
- **FTP to 50webs.com** for static site deployment (fragile; was down Feb 17-18)
- **GitHub Pages** for dashboard hosting (reliable)
- **Discord webhooks** for notifications

**Assessment:** The system is architecturally simple but fragile. FTP deployment has documented outages. There is no CDN, no load balancer, no auto-scaling.

### Finding 3: Model Storage Is Git-Committed (Anti-Pattern at Scale)

**Current State:** All trained model artifacts are committed directly to the git repository:

| Location | Format | Count | Purpose |
|---|---|---|---|
| `ml_crypto_predictor/models/` | `.pkl` | ~100+ | RandomForest, GradientBoosting, scalers (base/scalping/swing) |
| `ml_crypto_predictor/enhanced_models/models/` | `.joblib` | ~100+ | CatBoost, GRU, CNN1D, CNN-GRU, Attention-Ensemble, XGB Meta-Stacker per pair |
| `ml_crypto_predictor/production_models/` | `.pkl` | ~14 | Production-grade models |
| `claude_gainer_ml/models/` | `.joblib` | 3 | RF + XGB + scaler |
| `ml_battleground/system_c_deeplearn/models/` | `.pt` | 1 | PyTorch GRU-Attention state dict |
| `alpha_engine/data/` | `.pkl`/`.json` | varies | RF model + ML weights |
| `crypto_ml_edge/models/` | `.joblib` | varies | LightGBM pipelines with sidecar JSON metadata |

**Problems Identified:**
1. **Repository bloat:** 200+ binary model files committed to git. Each retraining cycle adds new versions without pruning old ones.
2. **No model versioning:** No MLflow, DVC, or W&B tracking. The `crypto_ml_edge/trainer.py` saves JSON sidecar files alongside `.joblib` models, which is the closest thing to metadata tracking.
3. **No model registry:** No way to compare model versions, roll back, or audit which model generated a specific prediction.
4. **Git LFS not configured:** Binary `.pkl`/`.joblib`/`.pt` files are stored as regular git objects.

**Cloud Migration Opportunity:** CRITICAL.
- **AWS S3 + MLflow** or **DVC (Data Version Control)** for model versioning
- **SageMaker Model Registry** or **Vertex AI Model Registry** for deployment lineage
- Estimated storage: ~500MB of model artifacts currently; will grow to multi-GB as more pairs/timeframes/model architectures are added

### Finding 4: Database Layer Is SQLite-Only (7 Databases, All Local)

**Current State:** The codebase uses SQLite exclusively for structured persistence:

| Database | Location | Purpose |
|---|---|---|
| `alpha_engine/data/alpha.db` | Alpha Engine | Signals, picks, strategy stats, regime snapshots |
| `crypto_data.db` | Root | General crypto data cache |
| `model_health.db` | Root | Model health monitoring |
| `ab_testing_agent/ab_testing.db` | A/B Testing | Experiment tracking |
| `ab_testing_agent/crypto_data.db` | A/B Testing | Crypto data for experiments |
| `KIMI_RISEOFTHECLAW/data/kimi_trading.db` | KIMI Scanner | Trading signals + signal tracker |
| `KIMI_RISEOFTHECLAW/data/signal_tracker.db` | KIMI Scanner | TP/SL validation |

**Database Schema (Alpha Engine -- most mature):**
- `signals` table: Raw signal log with 19 columns including ML score, regime, ATR, RSI
- `picks` table: Open/closed positions with P&L tracking, transaction costs, hold days
- `strategy_stats` table: Rolling performance metrics (Sharpe, Sortino, Kelly, max drawdown)
- `regime` table: Market regime snapshots (SPY regime, crypto regime, VIX, DXY, F&G)
- WAL journaling mode enabled for concurrent reads
- Foreign keys enforced

**Problems Identified:**
1. **SQLite is ephemeral in GitHub Actions:** Each workflow run starts fresh. The `alpha.db` is not committed; only JSON exports (`active_picks.json`, `closed_picks.json`) are persisted via git commits.
2. **No shared state between workflows:** The 107 workflows cannot share database state.
3. **No backup/disaster recovery:** SQLite files are local-only.
4. **Concurrency limitations:** SQLite cannot handle multiple concurrent writers (relevant if scaling to real-time).

**Cloud Migration Opportunity:** MEDIUM-HIGH.
- **PostgreSQL on RDS/Cloud SQL** for shared state across workflows
- **TimescaleDB** for time-series OHLCV data (currently re-fetched every run)
- **Redis** for caching frequently-accessed data (Fear & Greed, funding rates)
- The `ab_testing_agent/config.py` already has a `DATABASE_URL` pattern supporting SQLAlchemy, suggesting some cloud-readiness awareness

### Finding 5: Data Fetching Is Stateless and Redundant

**Current State:** Every GitHub Actions run re-fetches market data from scratch:
- `yfinance` for equity/forex (limited to 60-day hourly, 1-year daily)
- Binance REST API for crypto OHLCV + funding rates
- Alternative.me for Fear & Greed
- CoinGecko for market caps

**No data caching between runs.** The `crypto_ml_edge/config.py` has `CACHE_TTL_HOURS = 1.0` and `HISTORY_YEARS = 5` but this cache exists only within a single workflow execution.

**Problems Identified:**
1. **API rate limiting risk:** 107 workflows all hitting the same free APIs
2. **Wasted compute:** Fetching and computing the same features (RSI, MACD, Bollinger) repeatedly
3. **Limited history:** yfinance caps hourly data at 60 days; no long-term historical data store
4. **No feature store:** Features are computed on-the-fly every scan cycle

**Cloud Migration Opportunity:** HIGH.
- **S3/GCS data lake** for historical OHLCV storage (fetch once, use forever)
- **Feature store** (SageMaker Feature Store, Feast, or simple Parquet on S3) for pre-computed features
- **Shared cache layer** (Redis/Memcached) for API responses
- The `alpha_engine/config.py` already specifies `DATA_STORAGE_FORMAT = "parquet"` and `PARQUET_COMPRESSION = "snappy"`, indicating intent to use Parquet but it is not yet implemented

### Finding 6: No Model Serving Infrastructure

**Current State:** There is no REST API, no serverless function, and no model serving endpoint for real-time inference. All "serving" is batch-mode:
1. GitHub Actions cron triggers a Python script
2. Script loads model from local `.joblib`/`.pkl` file
3. Script generates predictions and writes to JSON files
4. JSON files are committed to git and/or deployed via FTP to static sites
5. Static HTML dashboards read JSON via fetch()

The `ab_testing_agent/` has a Flask-based API (`api.py`) and dashboard (`dashboard.py`), but it appears to be a prototype that runs locally, not deployed anywhere.

The `trading_system/k8s/manifests.yaml` contains Kubernetes deployment manifests with namespaces (`trading-prod`, `trading-data`, `trading-monitoring`) and priority classes, but this is **aspirational documentation only** -- there is no Dockerfile, no container registry, and no evidence of any Kubernetes cluster.

**Cloud Migration Opportunity:** MEDIUM (dependent on use case).
- **AWS Lambda / GCP Cloud Run** for serverless inference endpoints (sub-second latency)
- **SageMaker Endpoints / Vertex AI Endpoints** for managed model serving
- **Current batch approach works** if 15-30 minute signal latency is acceptable
- Real-time serving only needed if moving to execution (currently paper-trading only)

### Finding 7: ML Framework Diversity Creates Deployment Complexity

**Current State:** The codebase uses 6+ ML frameworks across different subsystems:

| Framework | Used In | Purpose |
|---|---|---|
| **scikit-learn** | All systems | RandomForest, GradientBoosting, StandardScaler, Pipeline |
| **XGBoost** | `train_crypto_models.yml`, ml_battleground | Gradient boosting ensemble |
| **LightGBM** | `crypto_ml_edge/trainer.py` | Primary classifier with Optuna tuning |
| **PyTorch** | `ml_battleground/system_c_deeplearn/` | GRU-Attention neural net (dual-timeframe) |
| **CatBoost** | `ml_crypto_predictor/enhanced_models/` | Per-pair CatBoost classifiers |
| **SHAP** | `crypto_ml_edge/trainer.py` | Feature importance and pruning |

**PyTorch Details (System C):**
- Architecture: Dual-timeframe GRU (128 hidden, 2 layers) + Multi-Head Self-Attention (4 heads) + 3 output heads (entry prob, TP dist, SL dist)
- Training: Walk-forward 5-fold CV, 50-bar purge gap, Adam optimizer, ReduceLROnPlateau
- Currently CPU-only in CI; model saved as `.pt` state dict

**Cloud Implication:** Multi-framework serving requires either:
- A unified container with all frameworks installed (~5GB+ image)
- Per-model microservices (more complex but cleaner)
- ONNX conversion for framework-agnostic serving

---

## Scalability Bottleneck Analysis

### Bottleneck 1: GitHub Actions Free Tier Limits
- **2,000 minutes/month** for free tier; at 107 workflows many running every 15-30 min, this is likely being exceeded
- **20 concurrent jobs** maximum
- **No GPU runners** on free/pro plans (self-hosted or GitHub-hosted large runners needed for GPU)

### Bottleneck 2: Model Training Time on CPU
- System C (GRU-Attention): Limited to small batches and short epochs due to 10-60 min workflow timeouts
- Enhanced ML Pipeline: 30 pairs x 6 model architectures = 180 models to train; currently takes up to 60 min on CPU
- Optuna hyperparameter search: Limited to 20 trials (should be 100-500 for proper optimization)

### Bottleneck 3: Data Re-Fetching
- Every run fetches data from scratch; no persistent data store
- Rate limiting risk from 100+ workflows hitting free APIs
- 60-day hourly data limit from yfinance means limited training history

### Bottleneck 4: Git Repository Size
- 200+ model artifacts (.pkl, .joblib, .pt) bloating the repo
- JSON data files committed on every 15-minute scan cycle
- No git LFS; full clone size likely multi-GB

---

## Actionable Recommendations (Prioritized)

### Phase 1: Quick Wins (Low Cost, High Impact)
- [x] **AUDITED**: Current state is 100% GitHub Actions + SQLite + git-committed models
- [ ] **Add DVC (Data Version Control)** for model versioning -- remove binary models from git, track via DVC remotes on free S3/GCS tier
- [ ] **Add git LFS** as a stopgap for any remaining binary artifacts
- [ ] **Consolidate data fetching** into a single daily workflow that caches OHLCV data as Parquet files (the config already specifies Parquet format)
- [ ] **Add GitHub Actions caching** (`actions/cache`) for pip dependencies and fetched data between runs

### Phase 2: Cloud Data Layer ($20-50/month)
- [ ] **S3 or GCS bucket** for OHLCV historical data lake (fetch once, ~10GB)
- [ ] **PostgreSQL on Supabase (free tier)** or **Neon.tech** to replace SQLite for shared state across workflows
- [ ] **Redis (Upstash free tier)** for caching API responses (Fear & Greed, funding rates, CoinGecko)
- [ ] **Simple feature store**: Pre-computed features saved as Parquet in S3, loaded by training/inference workflows

### Phase 3: Cloud Training ($50-200/month, on-demand)
- [ ] **AWS SageMaker Training Jobs** or **GCP Vertex AI Custom Training** for GPU-accelerated model training
- [ ] Recommended instance: **ml.g4dn.xlarge** (T4 GPU, $0.53/hr) or **n1-standard-4 + T4** ($0.35/hr) for PyTorch GRU-Attention
- [ ] **Spot instances** for Optuna hyperparameter search (100+ trials at ~$5-10 per full sweep)
- [ ] **MLflow on EC2/Cloud Run** for experiment tracking and model registry

### Phase 4: Cloud Serving (If Moving Beyond Paper Trading)
- [ ] **AWS Lambda + API Gateway** or **GCP Cloud Run** for serverless inference (pay-per-request)
- [ ] **SageMaker Multi-Model Endpoint** for serving 180+ models from a single endpoint
- [ ] Estimated inference cost: <$5/month for current scan-every-15-min pattern
- [ ] Only worth implementing if latency matters (sub-second signals for live execution)

### Phase 5: Full Cloud Architecture ($200-500/month)
- [ ] **Kubernetes (EKS/GKE)** -- the `trading_system/k8s/manifests.yaml` provides a starting blueprint
- [ ] **Managed Airflow** or **Prefect** to replace GitHub Actions cron for workflow orchestration
- [ ] **MLflow + Model Registry** for full ML lifecycle management
- [ ] **Prometheus + Grafana** (already in `trading_system/monitoring/`) for observability

---

## Cost Projection

| Tier | Monthly Cost | What You Get |
|---|---|---|
| Current (free) | $0 | GitHub Actions CPU, SQLite, git-committed models, FTP hosting |
| Starter Cloud | $20-50 | S3 data lake, managed PostgreSQL, Redis cache, DVC |
| Training Upgrade | $50-200 | GPU training (on-demand), MLflow, Optuna at scale |
| Full Production | $200-500 | Kubernetes, managed serving endpoints, full observability |

**Recommendation for This Project:** Phase 1 (DVC + caching) is free and should be done immediately. Phase 2 ($20-50/month) provides the highest ROI by eliminating data re-fetching and enabling shared state. Phase 3 is only needed when model complexity outgrows CPU capabilities (the GRU-Attention model is the trigger point).

---

## References
- Codebase audit: 107 GitHub Actions workflows, 7 SQLite databases, 200+ model artifacts
- `alpha_engine/database.py` -- SQLite persistence layer with WAL mode
- `alpha_engine/ml_ranker.py` -- RandomForest ML signal ranker
- `crypto_ml_edge/trainer.py` -- LightGBM + Optuna + SHAP training pipeline
- `ml_battleground/system_c_deeplearn/train_model.py` -- PyTorch GRU-Attention training
- `ml_battleground/system_c_deeplearn/model_arch.py` -- Neural network architecture
- `alpha_engine/config.py` -- Parquet storage format specified but not yet implemented
- `ab_testing_agent/config.py` -- SQLAlchemy DATABASE_URL pattern
- `trading_system/k8s/manifests.yaml` -- Aspirational Kubernetes manifests (not deployed)
- AWS SageMaker pricing: https://aws.amazon.com/sagemaker/pricing/
- GCP Vertex AI pricing: https://cloud.google.com/vertex-ai/pricing

---
*Researcher ID: 023* | *Status: Complete*
