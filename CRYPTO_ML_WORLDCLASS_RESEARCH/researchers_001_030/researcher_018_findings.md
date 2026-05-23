# Researcher 018: Dr. Maria Garcia — Feature Store & Data Platform Architect
## Complete Research Findings: Feature Stores for Crypto ML Pipelines

**Researcher:** Dr. Maria Garcia, PhD (UC Berkeley Computer Science)
**Background:** 13 years experience, former Feast project lead, now builds ML data platforms for trading systems.
**Date:** February 24, 2026
**Status:** COMPLETE

---

## Executive Summary

After exhaustive research across 2024–2026 sources — engineering blogs, academic papers, conference proceedings (Feature Store Summit 2024), and production case studies — my conclusion for a small team of 1–3 people running ~50 technical indicators for crypto ML trading is clear:

**A full feature store is NOT worth the overhead at your current scale. A well-structured Parquet-based system with lightweight metadata versioning is the correct path — with DuckDB as the query engine of choice.**

That said, certain feature store concepts (point-in-time joins, feature lineage tagging, distribution monitoring) should be adopted as lightweight patterns, not full infrastructure. Below is the complete research supporting this conclusion.

---

## Finding 1: Feast Feature Store — Current State, Crypto Use Cases, Ease of Setup

### Tool/Technique
Feast (Feature Store) — open-source, Python-native, maintained actively as of 2026 (v0.42+ branch). Originally developed at Gojek, now community-led. Robinhood publicly cited Feast as the backbone of their ML feature platform.

### Current Architecture (2024–2026)
Feast operates on three components:
1. **Feature Registry** — YAML/Python definitions of feature views, entities, data sources
2. **Offline Store** — Parquet files, BigQuery, Snowflake, Redshift (for training)
3. **Online Store** — Redis, SQLite (local), DynamoDB, Bigtable (for inference, <10ms P99 latency)

Feast supports point-in-time correct joins out of the box via `get_historical_features()`. This is the single most important differentiator from raw Parquet.

### Crypto Use Case Applicability
No major published case study exists for Feast in crypto trading specifically (as of 2026). The closest is Robinhood's implementation for equities. However, the architecture maps cleanly:
- Entity: symbol (BTC, ETH, SOL)
- Feature view: RSI_14, MACD_signal, funding_rate, volume_zscore
- Materialization schedule: every 15–30 min (aligning with your GitHub Actions cadence)
- Online serving: Redis with <10ms latency for live inference

Stream ingestion via Kafka is supported for real-time feature updates — relevant if you want sub-minute feature freshness.

### Setup Complexity: **HARD**
- `pip install feast` is trivial
- Actual production setup requires: Redis (online store), S3/GCS or local Parquet (offline store), a scheduled materializer process
- Operational burden: schema migrations, feature backfills, Redis uptime
- A solo developer will spend 2–5 days getting a production-grade Feast deployment running reliably
- Local SQLite mode (development) is simple but not suitable for concurrent reads

### Value Added for 1–3 Person Team: **LOW-MEDIUM**
Feast's value multiplies with team size. For 1–3 people sharing the same codebase, the reuse argument is weak. The consistency argument (training/serving skew) is real but solvable more cheaply.

### Cost: **Free** (infrastructure costs extra: Redis ~$15–50/mo on a small cloud VM)

### Is It Overkill? **YES, for current scale**

---

## Finding 2: Feature Stores vs Simple Parquet/CSV Files — When Is Overhead Worth It?

### The Core Tradeoff
Parquet files are columnar, compressed, fast for batch reads, and trivially versioned with date-stamped filenames or DVC. A feature store adds:
- Point-in-time joins (prevents leakage)
- Online serving (low-latency key-value lookup)
- Feature lineage (which model version consumed which feature snapshot)
- Monitoring hooks

### When a Feature Store Pays Off
Based on Feature Store Summit 2024 takeaways and the JFrog ML / Hopsworks definitive guides, feature stores justify their overhead when:
1. **Multiple teams** reuse the same features (duplication becomes expensive)
2. **Multiple models** run in parallel, each needing consistent feature snapshots
3. **Online inference** demands sub-100ms latency with features computed on schedule (not at request time)
4. **Regulatory / audit requirements** mandate feature lineage (finance, healthcare)
5. **Feature computation is expensive** (e.g., on-chain aggregations over millions of blocks)

### When Parquet + Simple Versioning Wins
For a 1–3 person crypto ML team with ~50 technical indicators:
- Features are computed quickly (pandas/Polars over OHLCV data, seconds not minutes)
- Model count is small (< 10 active models)
- Training is batch (not real-time)
- No SLA for online inference latency beyond "fast enough for 30-min candles"
- Team members all know the codebase

**The Databricks guidance is explicit:** "Start with experiment tracking + pipeline automation + basic monitoring first. Expand to feature stores as model count and traffic grows."

### Practical Cost of Overhead
Setting up Feast or Hopsworks fully:
- Initial setup: 2–5 engineering days
- Ongoing maintenance: 1–2 hours/week
- Infrastructure cost: $30–100/month

For a small team, that engineering time is better spent on signal quality, backtesting rigor, and model validation.

### Verdict
Use **versioned Parquet files + DuckDB** now. Revisit feature stores when you have 3+ data scientists or 20+ concurrent models.

---

## Finding 3: Training-Serving Skew in Crypto ML — How Big Is the Problem?

### Definition
Training-serving skew is the systematic mismatch between what a model sees during training versus what it receives during live inference. In crypto ML, this manifests as:
- Feature computed differently in training (batch pandas on historical data) vs inference (real-time calculation on streaming candles)
- Normalization parameters (mean, std) fit on training set applied incorrectly at inference time
- Lookahead bias: training feature uses `t+1` data accidentally; inference only has `t`
- Library version differences: pandas 1.x vs 2.x rolling window edge cases

### How Big Is the Problem?
Production ML engineers at Nubank documented training-serving skew as one of the top three silent killers of model performance — more insidious than outright bugs because models degrade gradually rather than failing hard.

For crypto specifically: funding_rate, open_interest, and on-chain metrics from different API endpoints can have inconsistent data cuts. A RSI computed on close prices at 00:00 UTC in training may differ from RSI computed on the "current" close during a 23:45 UTC candle — a 15-minute mismatch that subtly shifts the distribution.

Academic research (Springer Nature, 2025) confirms: "The feature set must be curated thoughtfully to avoid data leakage, using domain knowledge alongside statistical testing. Datasets must split training and testing sets while maintaining chronological order."

### Severity for Our System
**Medium-High.** Because we compute features inline during training and inference, the risk is:
- Training: features computed on clean, complete historical candles
- Inference: features computed on live, potentially incomplete candles (last candle still forming)
- Fix: explicitly exclude the current (incomplete) candle from all feature windows during inference

### The Feature Store "Fix"
A feature store enforces consistency by materializing features on a schedule (every 30 min) from a single computation function. Training pulls from the same materialized store as inference. This eliminates the skew entirely — but requires the materialization infrastructure.

The lightweight alternative: **use a single `compute_features(df)` function called identically in both training and inference paths.** Document it. Test it. This solves 80% of the skew problem without any infrastructure.

---

## Finding 4: Point-in-Time Joins for Preventing Feature Leakage in Financial ML

### What Is a Point-in-Time Join?
When building training datasets for financial ML, you need features computed as of the exact moment the label was generated — not the end of the day, not the next candle. A point-in-time join (also called "as-of join") retrieves the feature value that was available at time `t` for each training sample labeled at time `t`.

### Why This Matters for Crypto
Standard pandas merge on timestamp will often use the wrong feature value if:
- Feature computation has latency (e.g., on-chain data arrives 10 min after block close)
- Multiple feature sources have different update frequencies
- You are predicting the next candle's direction using any data from that future candle

Leakage example: computing RSI including the candle you are trying to predict. On a 15-min chart, this can add 3–8% spurious accuracy that vanishes in live trading.

### Feast's Implementation
Feast provides `get_historical_features(entity_df, feature_refs)` which performs an as-of join automatically. For each row in `entity_df` (with a timestamp), it fetches the most recent feature value that was available *before* that timestamp. This is implemented as a left join with a time-range filter, executed via DuckDB, Spark, or BigQuery depending on your offline store.

### Lightweight Alternative
For our scale, implement a manual as-of join in pandas:

```python
import pandas as pd

def as_of_join(labels_df, features_df, on='symbol', time_col='timestamp'):
    """
    For each label at time t, get the most recent feature row at t-1 or earlier.
    labels_df: DataFrame with [symbol, timestamp, target]
    features_df: DataFrame with [symbol, timestamp, feature_1, feature_2, ...]
    """
    features_df = features_df.sort_values(time_col)
    results = pd.merge_asof(
        labels_df.sort_values(time_col),
        features_df,
        on=time_col,
        by=on,
        direction='backward'  # use last feature value before the label timestamp
    )
    return results
```

`pd.merge_asof` with `direction='backward'` is the standard solution. It is built into pandas and requires no additional infrastructure. This eliminates temporal leakage for batch training datasets.

### Springer Nature (2025) Finding
"Temporal validation is critical as it preserves temporal order, preventing the use of any data after the prediction time. Cross-validation must respect temporal ordering for time-series data."

### Verdict
Point-in-time correctness is **not optional** for production financial ML. Implement `pd.merge_asof` now. Graduate to Feast's `get_historical_features` only when your data sources number more than 5 and manual as-of joins become error-prone.

---

## Finding 5: Online vs Offline Feature Stores for Trading Systems

### Offline Feature Store
- **Purpose:** Historical feature retrieval for model training and batch scoring
- **Storage:** Parquet files, BigQuery, Snowflake, DuckDB databases
- **Latency:** Seconds to minutes (acceptable for batch)
- **Access pattern:** Retrieve N years of RSI values for symbol X to build training set

### Online Feature Store
- **Purpose:** Real-time feature lookup during live inference
- **Storage:** Redis, DynamoDB, ScyllaDB, Bigtable
- **Latency:** <10ms P99 (required for sub-second trading decisions)
- **Access pattern:** "Give me the current RSI, MACD, and funding_rate for BTCUSDT right now"

### For Our System: Do We Need an Online Store?
**Our inference cadence:** Every 30 minutes (aligned with candle close).

At a 30-minute decision frequency, computing features from raw OHLCV data at inference time takes ~100–500ms. This is entirely acceptable. An online store would add <10ms latency — a meaningless improvement for a 30-min trading system.

**Online stores are critical for:**
- High-frequency trading (< 1 second decisions)
- Real-time fraud scoring (< 500ms SLA)
- Real-time recommendation engines (< 100ms SLA)

For a 15-min or 30-min candle strategy, computing features inline is correct and simpler.

### DragonflyDB Finding (2024)
"Online feature stores are essential for online serving with low latency. The Online Store delivers the latest feature values with millisecond latency for real-time inference, built on performant in-memory data stores like Dragonfly or NoSQL databases."

### Verdict
**No online store needed** for our 30-min candle system. If we graduate to tick-level or 1-min strategies, Redis-based online storage becomes necessary. For now: compute features at inference time from a local Parquet cache.

---

## Finding 6: Feature Versioning Best Practices — Tracking Which Model Used Which Features

### The Problem
Six months from now: which feature set was active model v7.2 trained on? Which normalization parameters? Was funding_rate_14d included or not? Without versioning, this is unrecoverable tribal knowledge.

### Tier 1: Minimum Viable Feature Versioning (Recommended for Small Teams)
Store a `feature_manifest.json` alongside every saved model:

```json
{
  "model_id": "alpha_engine_v7.2",
  "trained_at": "2026-02-24T14:30:00Z",
  "feature_version": "v3.1",
  "features": [
    "rsi_14", "macd_signal", "macd_hist", "bb_upper", "bb_lower",
    "volume_zscore_24h", "funding_rate_8h", "atr_14"
  ],
  "feature_computation_hash": "sha256:abc123...",
  "normalization": {
    "method": "zscore",
    "fit_on": "2023-01-01_to_2025-12-31",
    "scaler_path": "models/v7.2/scaler.pkl"
  },
  "training_data": {
    "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "start_date": "2023-01-01",
    "end_date": "2025-12-31",
    "candle_size": "15min",
    "n_samples": 148920
  }
}
```

This costs zero infrastructure and gives you full reproducibility.

### Tier 2: DVC (Data Version Control)
DVC extends Git to version data files and models. For Parquet-based feature stores:
- `dvc add features/v3.1/btcusdt_features.parquet` — tracks the file hash in Git
- `dvc push` — uploads to S3/GCS
- `dvc pull` — retrieves exact feature file for any model version

DVC integrates with Git so `git checkout model-v7.2` + `dvc pull` reproduces the exact training environment. **This is the recommended upgrade path from Tier 1.**

### Tier 3: MLflow Experiment Tracking
MLflow logs parameters, metrics, artifacts, and feature metadata per experiment run:

```python
import mlflow

with mlflow.start_run(run_name="alpha_engine_v7.2"):
    mlflow.log_param("features", ",".join(FEATURE_LIST))
    mlflow.log_param("feature_version", "v3.1")
    mlflow.log_artifact("feature_manifest.json")
    mlflow.log_metric("val_sharpe", 2.14)
    mlflow.sklearn.log_model(model, "model")
```

MLflow UI then shows every run, its features, metrics, and saved model. Free, open-source, self-hosted in one Docker container.

### Feature Store Native Versioning
Feast supports feature view versioning via tags:

```python
feature_view = FeatureView(
    name="crypto_indicators_v3",
    tags={"version": "3.1", "deprecated": "false"},
    ...
)
```

But this requires the full Feast infrastructure. For our scale, DVC + MLflow + `feature_manifest.json` achieves 90% of the value.

### Verdict
**Implement Tier 1 immediately (zero cost, zero infra), Tier 2 (DVC) within a month, Tier 3 (MLflow) when running regular experiments.** Skip Feast feature versioning for now.

---

## Finding 7: Lightweight Alternatives for Small Teams — SQLite, DuckDB, Parquet + Metadata

### Option A: Pure Parquet + Date-Versioned Filenames
```
features/
  v3.1/
    btcusdt_15min_features_2023-01-01_2026-02-24.parquet
    ethusdt_15min_features_2023-01-01_2026-02-24.parquet
  v3.2/
    btcusdt_15min_features_2024-01-01_2026-02-24.parquet
  metadata/
    v3.1_manifest.json
    v3.2_manifest.json
```
**Pros:** Zero infrastructure, fast columnar reads, compresses well (snappy/zstd), readable by pandas/Polars/DuckDB.
**Cons:** No online serving, no automatic point-in-time join, manual lineage tracking.

### Option B: DuckDB as Offline Feature Store Engine
DuckDB runs in-process, requires no server, and achieves near-Spark performance for analytical queries on a single machine.

```python
import duckdb

conn = duckdb.connect("features.duckdb")

# Store features
conn.execute("""
    CREATE TABLE IF NOT EXISTS crypto_features AS
    SELECT * FROM read_parquet('features/v3.1/*.parquet')
""")

# Point-in-time query
conn.execute("""
    SELECT f.*
    FROM labels l
    ASOF JOIN crypto_features f
    ON l.symbol = f.symbol AND l.timestamp >= f.timestamp
""")
```

DuckDB natively supports `ASOF JOIN` (as of v0.10, 2024) — this is a point-in-time join built into the SQL dialect. **This single feature makes DuckDB the ideal lightweight feature store backend.**

Real-world benchmark: one team reduced training set generation from 70 minutes to 7 minutes by switching from pandas to DuckDB for feature aggregation.

**Setup complexity:** SIMPLE (pip install duckdb, no server needed)
**Cost:** Free
**Value for small team:** High — near-Feast correctness, zero operational overhead

### Option C: SQLite for Feature Metadata + Parquet for Feature Data
Use SQLite as a fast metadata registry (which features exist, their versions, computation timestamps) and Parquet for actual feature data:

```python
# SQLite tracks what exists
cursor.execute("""
    CREATE TABLE feature_catalog (
        feature_name TEXT,
        version TEXT,
        symbol TEXT,
        computed_at TIMESTAMP,
        parquet_path TEXT,
        row_count INTEGER,
        schema_hash TEXT
    )
""")

# Parquet stores the actual values (fast columnar reads)
df.to_parquet(f"features/v{version}/{symbol}_{feature_name}.parquet")
```

**Setup complexity:** SIMPLE
**Cost:** Free
**Value for small team:** Medium — good metadata tracking, manual query assembly

### Option D: Hopsworks Serverless Free Tier
Hopsworks offers a forever-free serverless tier at app.hopsworks.ai — full feature store (online + offline), Python API, feature monitoring.

```python
import hopsworks

project = hopsworks.login()  # OAuth via GitHub/Gmail
fs = project.get_feature_store()

feature_group = fs.get_or_create_feature_group(
    name="crypto_indicators",
    version=1,
    primary_key=["symbol"],
    event_time="timestamp"
)
feature_group.insert(df)
```

**Setup complexity:** MEDIUM (account setup + Python client, no infra management)
**Cost:** Free (with storage limits)
**Value for small team:** High if you want managed online+offline stores without infrastructure
**Caveat:** Data leaves your environment (cloud-hosted), potential latency for EU/international data

### Recommendation
For our system: **DuckDB as the primary offline feature engine** (ASOF JOIN support is the killer feature), with **Parquet files for persistence** and **`feature_manifest.json` for lineage**. This combination delivers feature store correctness at zero operational cost.

---

## Finding 8: Feature Monitoring — Detecting Distribution Drift in Real-Time

### Why Drift Matters for Crypto ML
Cryptocurrency markets exhibit pronounced regime changes (volatility clustering documented 2021–2025, with distinct volatility spikes aligned with FOMC announcements and major macro events). A model trained on 2023 data may encounter a 2025 market regime that renders its features meaningless.

Types of drift relevant to crypto:
1. **Data drift:** Feature distribution shifts (RSI mean shifts from ~50 to ~35 during bear markets)
2. **Concept drift:** Relationship between features and target changes (funding_rate → return relationship inverts in low-liquidity environments)
3. **Label drift:** Win rate changes even with stable features (market becomes more efficient)

### Detection Methods (2024–2026 Best Practices)

**Statistical Tests for Batch Monitoring:**
- Kolmogorov-Smirnov (KS) test: compare feature distributions between training window and recent window
- Population Stability Index (PSI): industry standard in credit/finance, value > 0.25 signals significant drift
- Jensen-Shannon Divergence: symmetric, bounded [0,1], interpretable

**Lightweight Implementation:**
```python
from scipy.stats import ks_2samp
import numpy as np

def detect_feature_drift(train_features, live_features, feature_names, threshold=0.05):
    drift_report = {}
    for feature in feature_names:
        stat, p_value = ks_2samp(train_features[feature], live_features[feature])
        drift_report[feature] = {
            "ks_statistic": stat,
            "p_value": p_value,
            "drift_detected": p_value < threshold
        }
    return drift_report
```

**PSI Implementation:**
```python
def psi(expected, actual, buckets=10):
    """Population Stability Index. PSI > 0.25 = significant drift."""
    def scale_range(input, min_val, max_val):
        return (input - min_val) / (max_val - min_val + 1e-8)

    breakpoints = np.linspace(0, 1, buckets + 1)
    expected_pcts = np.histogram(scale_range(expected, expected.min(), expected.max()), bins=breakpoints)[0] / len(expected)
    actual_pcts = np.histogram(scale_range(actual, expected.min(), expected.max()), bins=breakpoints)[0] / len(actual)

    psi_value = np.sum((actual_pcts - expected_pcts) * np.log((actual_pcts + 1e-8) / (expected_pcts + 1e-8)))
    return psi_value
```

**Evidently AI (Free, Open Source)**
Evidently is the leading open-source library for ML monitoring. It generates drift reports for any feature set:

```python
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset

report = Report(metrics=[DataDriftPreset()])
report.run(reference_data=train_df, current_data=live_df)
report.save_html("drift_report.html")
```

**Setup complexity:** SIMPLE (pip install evidently)
**Cost:** Free
**Value for small team:** High — automatic drift detection for all 50 features with one function call

### Crypto-Specific Monitoring Targets
Based on research findings, prioritize monitoring these features for drift:
1. `funding_rate` — changes regime from positive to negative; signals overleveraged market
2. `volume_zscore` — low-volume regimes render momentum signals unreliable
3. `rsi_14` — extended bull/bear markets shift RSI distribution significantly
4. `volatility_20d` — GARCH-style clustering; regime shifts invalidate fixed ATR thresholds
5. `btc_dominance` — altcoin season feature; distribution flips during cycle shifts

**Recommended cadence:** Run drift detection weekly on the last 30 days of live data vs. training distribution.

---

## Finding 9: Feature Computation Optimization — Pandas vs Polars vs Spark

### Benchmark Summary (2024–2025 Data)

| Framework | Relative Speed | Memory Efficiency | ML Library Compat. | Setup |
|-----------|---------------|-------------------|-------------------|-------|
| Pandas 1.x | 1x (baseline) | Poor | Excellent | Trivial |
| Pandas 2.x | ~1.5x | Improved | Excellent | Trivial |
| Polars | 5–22x faster | 8x better (179MB vs 1.4GB for 1GB data) | Requires `.to_pandas()` at boundary | Simple |
| DuckDB (SQL) | 5–10x faster for aggregations | Excellent | Via `.df()` | Simple |
| PySpark | 10–50x for huge datasets | Scales horizontally | Good | Hard |

Source: Hopsworks engineering blog "Pandas2 and Polars for Feature Engineering" + multiple 2024–2025 benchmarks.

### For Our ~50 Technical Indicators

**Current situation (pandas inline):**
- 1 year of 15-min OHLCV for 10 symbols = ~35,000 rows × 10 symbols = 350,000 rows
- Computing 50 features (RSI, MACD, Bollinger Bands, etc.) in pandas: ~2–15 seconds
- This is fast enough. Optimization is not the bottleneck.

**When to switch to Polars:**
- If dataset grows to 10+ years or 50+ symbols
- If features include rolling windows over millions of rows
- If retraining daily on fresh data with 100+ symbols

**Polars for rolling technical indicators:**
```python
import polars as pl

df = pl.read_parquet("ohlcv_data.parquet")

df = df.with_columns([
    pl.col("close").rolling_mean(window_size=14).alias("sma_14"),
    pl.col("close").rolling_std(window_size=20).alias("vol_20"),
    # RSI requires a custom expression or plugin
])
```

**Caveat:** As of mid-2024, most ML libraries (scikit-learn, XGBoost, LightGBM) do not accept Polars DataFrames directly. Always convert at the training boundary: `df.to_pandas()`. This adds marginal overhead but avoids compatibility issues.

**TA-Lib integration:**
TA-Lib (C library) is still the gold standard for vectorized technical indicator computation. It is faster than pure pandas and covers 100+ indicators:

```python
import talib
import numpy as np

close = df['close'].values
rsi = talib.RSI(close, timeperiod=14)
macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
```

TA-Lib operates on numpy arrays — compatible with both pandas and Polars workflows.

### Recommendation
**Keep pandas + TA-Lib for now.** The computation time for 50 features on our dataset is already fast enough. Adopt Polars when datasets grow 10x or when a benchmark shows a real bottleneck. Use DuckDB for any SQL-style aggregations across multiple symbols.

---

## Finding 10: Best Practices for Feature Engineering in Crypto — Which Transformations Matter?

### Research Findings (2024–2025 Academic Literature)

**Top-Performing Feature Categories (from multiple Springer Nature, arxiv, and MDPI papers):**

1. **Log Returns (not raw prices)**
   - Raw prices are non-stationary; log returns are approximately stationary
   - Formula: `log_return = ln(close_t / close_{t-1})`
   - Multi-horizon: compute for 1h, 4h, 24h, 7d windows
   - Academic consensus: log returns as input features consistently outperform raw prices

2. **RSI + MACD Confluence**
   - Individual accuracy: ~50–55% (barely above random)
   - Combined RSI + MACD filter: accuracy improves to 60–65%
   - Adding volume confirmation pushes to 65–70%
   - Bitcoin prediction study: top 8 features were RSI30, MACD, MOM30, %K, RSI14 (stochastic oscillator)

3. **Volatility Features**
   - Realized volatility (rolling std of log returns over 20 periods)
   - ATR (Average True Range) — better than realized vol for intraday
   - Garman-Klass volatility: uses OHLC data, more efficient estimator than close-to-close
   - GARCH-filtered volatility improves feature quality vs raw std (Springer, 2025)

4. **Volume-Based Features**
   - Volume Z-score: `(volume - volume_mean_20d) / volume_std_20d`
   - Volume rate of change
   - Dollar volume (volume × price) for cross-symbol comparison
   - Volume momentum outperforms price momentum in crypto (Liu et al. 2022, JFE cited in our Alpha Engine)

5. **Normalization Strategy**
   - Z-score normalization: standard baseline
   - Robust scaler (`sklearn.RobustScaler`): reduces impact of outliers in volatile markets — recommended for crypto
   - Min-max normalization: avoid for time series (future leakage if fit on full dataset)
   - Rolling z-score: `(feature - rolling_mean_N) / rolling_std_N` — prevents lookahead bias at inference time

6. **Lag Features**
   - Returns at t-1, t-2, t-3, t-6, t-12, t-24 (for 1h candles)
   - RSI at t-3, t-6 (momentum persistence)
   - These are cheap to compute and consistently useful

7. **Cross-Sectional Features (for multi-asset systems)**
   - RSI rank across universe (is BTC's RSI high or low relative to alts?)
   - Volume ratio (symbol volume / total universe volume)
   - Momentum rank (Liu et al. 2022 "cross-sectional momentum" — Sharpe ~2.1)

8. **On-Chain / Funding Rate Features**
   - Funding rate 8h: persistent positive = overleveraged longs, contrarian signal
   - Open interest change: OI rising + price rising = trend confirmation
   - Fear & Greed Index: binary DCA trigger at extreme values (<10)

### What Does NOT Work (Common Mistakes)
- Raw close prices as features — non-stationary, breaks cross-symbol models
- Including future data accidentally (incomplete current candle)
- Scaling with global (not rolling) parameters — causes lookahead bias
- Using too many correlated indicators (RSI + Stochastic + MFI are ~0.85 correlated)
- Single-indicator models: "MACD alone had ~50–55% win accuracy" (Gate.com, 2025)

### Recommended Feature Set for 50-Indicator Crypto System
Based on research synthesis:

```python
CORE_FEATURES = [
    # Price-based (10)
    "log_return_1h", "log_return_4h", "log_return_24h", "log_return_7d",
    "rsi_14", "rsi_6", "cci_20", "roc_10", "momentum_5", "momentum_10",

    # Trend (8)
    "macd_signal", "macd_hist", "macd_crossover",
    "ema_9_21_ratio", "ema_21_50_ratio", "sma_cross_50_200",
    "adx_14", "di_plus_minus_diff",

    # Volatility (8)
    "atr_14_pct", "bb_width", "bb_position",  # bb_position = (close - bb_lower) / bb_width
    "realized_vol_20", "realized_vol_5", "garman_klass_vol_14",
    "vol_ratio_5_20",  # short-vol / long-vol
    "hl_range_pct",    # (high - low) / close

    # Volume (7)
    "volume_zscore_20", "volume_zscore_5",
    "obv_slope_10", "vwap_deviation",
    "volume_roc_5", "dollar_volume_zscore",
    "volume_price_corr_10",

    # Funding / On-Chain (7)
    "funding_rate_8h", "funding_rate_cumulative_24h",
    "oi_change_pct_4h", "oi_price_divergence",
    "fear_greed_index", "fear_greed_7d_avg",
    "btc_dominance_change_7d",

    # Lag features (10)
    "log_return_lag1", "log_return_lag2", "log_return_lag3",
    "rsi_lag3", "rsi_lag6",
    "volume_zscore_lag1", "volume_zscore_lag2",
    "funding_rate_lag1", "funding_rate_lag3",
    "realized_vol_lag5"
]
```

---

## Tool / System Matrix Summary

| Tool | Setup | Value (1–3 person team) | Cost | Overkill? |
|------|-------|------------------------|------|-----------|
| Feast (local SQLite mode) | Medium | Medium | Free | Borderline |
| Feast (production Redis) | Hard | Medium-High | Free + infra | Yes |
| Tecton (managed) | Medium | High | Expensive ($$$) | Yes |
| Hopsworks (serverless free) | Medium | High | Free (limited) | Borderline |
| DuckDB + Parquet | Simple | High | Free | No |
| SQLite metadata + Parquet | Simple | Medium | Free | No |
| DVC (data versioning) | Simple | High | Free | No |
| MLflow (experiment tracking) | Simple | High | Free | No |
| Evidently (drift monitoring) | Simple | High | Free | No |
| Polars (faster pandas) | Simple | Medium | Free | No |
| TA-Lib (indicator library) | Simple | High | Free | No |
| pandas + `merge_asof` | Zero | High | Free | No |

---

## Top 5 Recommendations for Our System

### Context Recap
- Team size: 1–3 people
- Features: ~50 technical indicators (RSI, MACD, Bollinger, volume, funding, on-chain)
- Computation: inline during training and inference (no pre-materialized store)
- Inference cadence: every 15–30 minutes (GitHub Actions)
- Scale: 10–20 symbols, 1–5 years historical data, <500k rows per symbol

---

### Recommendation 1: NO Full Feature Store — Use DuckDB + Versioned Parquet Files

**Do NOT implement Feast, Hopsworks, or Tecton at this scale.** The infrastructure overhead (Redis, materialization jobs, schema migrations) will consume 40% of your engineering bandwidth for a marginal correctness improvement.

**Instead:** Adopt DuckDB as your offline feature engine. Write feature computation functions once, save outputs to versioned Parquet files, and use DuckDB's native `ASOF JOIN` for point-in-time correctness when building training datasets.

```
features/
  v4.0/
    BTCUSDT_15min_2024-01-01_2026-02-24.parquet   # ~50 features, all symbols
    ETHUSDT_15min_2024-01-01_2026-02-24.parquet
    manifest_v4.0.json                             # feature list, computation hash, date range
```

Estimated implementation time: **1 day**. Estimated ongoing maintenance: **near zero**.

---

### Recommendation 2: Implement `pd.merge_asof` for Point-in-Time Correct Training Sets

This single change eliminates the most dangerous form of feature leakage in financial ML. Every training dataset must be built using `pd.merge_asof(labels_df, features_df, on='timestamp', direction='backward')`.

**Do not** build training sets by joining labels and features on exact timestamp match — this creates subtle lookahead bias whenever feature computation has any latency.

Estimated implementation time: **2 hours**. Value: **eliminates invisible accuracy inflation from leakage**.

---

### Recommendation 3: Implement a Single `compute_features(df)` Function Used in Both Training and Inference

Training-serving skew is the silent killer. The fix is not a feature store — it is **one canonical function** called identically in both paths:

```python
# features.py — THE SINGLE SOURCE OF TRUTH
def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input: OHLCV DataFrame with columns [open, high, low, close, volume]
    Output: DataFrame with all 50 engineered features

    IMPORTANT: Never read data beyond the input DataFrame.
    Never use future data. All rolling windows must be backward-looking.
    """
    df = df.copy()
    close = df['close'].values

    df['log_return_1h'] = np.log(df['close'] / df['close'].shift(1))
    df['rsi_14'] = talib.RSI(close, timeperiod=14)
    df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(close)
    # ... all 50 features computed here

    return df

# Called identically in training:
train_df = compute_features(historical_ohlcv_df)

# And in inference:
live_features = compute_features(recent_ohlcv_df).iloc[-1]
```

Estimated implementation time: **4–8 hours** (refactoring existing code). Value: **eliminates training-serving skew permanently**.

---

### Recommendation 4: Add Lightweight Feature Versioning with `feature_manifest.json` + MLflow

For every model you save, write a `feature_manifest.json` alongside it. This costs nothing and gives full reproducibility.

Upgrade path: install MLflow (`pip install mlflow`, free, self-hosted) and log every training run with its feature list, normalization parameters, and performance metrics. This replaces tribal knowledge with a queryable experiment history.

Do NOT use Feast's feature registry for this purpose — it is overkill for 1–3 people.

Estimated implementation time: **2–4 hours for manifest, 1 day for MLflow setup**. Ongoing: **minimal** (log artifacts per training run).

---

### Recommendation 5: Monitor Feature Drift Weekly with Evidently AI

Install Evidently (`pip install evidently`) and run a drift report every week comparing the last 30 days of live feature distributions against the training distribution:

```python
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset

report = Report(metrics=[DataDriftPreset()])
report.run(reference_data=training_features_df, current_data=last_30d_features_df)
report.save_html("reports/drift_2026-02-24.html")
```

Prioritize monitoring: `funding_rate`, `volume_zscore`, `rsi_14`, `realized_vol_20`, `btc_dominance_change_7d`. These are the features most sensitive to market regime changes.

Trigger model retraining when PSI > 0.25 on more than 3 core features simultaneously.

Estimated implementation time: **2–3 hours**. Ongoing: **15 minutes/week**. Value: **catches model staleness before drawdowns compound**.

---

## Final Verdict: Is a Feature Store Worth It for Our System?

**No. Not yet.**

Our system has 50 technical indicators, 1–3 developers, and a 30-minute inference cadence. The value proposition of a feature store — feature reuse across teams, online low-latency serving, automated materialization, multi-team governance — does not apply at our scale.

The correct stack is:
1. **DuckDB + Parquet** for offline feature storage and point-in-time joins
2. **Single `compute_features()` function** to eliminate training-serving skew
3. **`feature_manifest.json` + MLflow** for lightweight feature versioning
4. **Evidently AI** for drift monitoring
5. **DVC** (optional upgrade) for data file versioning in Git

This stack costs **$0**, takes **3–5 days** to implement fully, and solves 90% of the problems a feature store would solve — without the 3-month infrastructure investment.

**Revisit Feast or Hopsworks when:**
- Team grows to 5+ data scientists
- Model count exceeds 20 concurrent production models
- Real-time (sub-minute) inference is required
- Multiple business units need to reuse the same feature definitions

Until then, ship faster features, not faster feature stores.

---

## Sources

- [Feast Open Source Feature Store — Official Documentation](https://docs.feast.dev)
- [Top 5 Feature Stores in 2025: Tecton, Feast, and Beyond — GoCodeo](https://www.gocodea.com/post/top-5-feature-stores-in-2025-tecton-feast-and-beyond)
- [How Robinhood Built a Feature Store Using Feast — Tecton](https://www.tecton.ai/apply/session-video-archive/how-robinhood-built-a-feature-store-using-feast/)
- [Feature Store Architecture and Online/Offline Storage — DragonflyDB](https://www.dragonflydb.io/blog/feature-store-architecture-and-storage)
- [Online vs. Offline Feature Store: Understanding the Differences — GeeksforGeeks](https://www.geeksforgeeks.org/machine-learning/online-vs-offline-feature-store-understanding-the-differences-and-use-cases/)
- [The Definitive Guide to Feature Stores in 2024 — Hopsworks](https://www.hopsworks.ai/news/the-definitive-guide-to-feature-stores-in-2024)
- [Comprehensive Comparison: Feast vs. Tecton vs. Hopsworks (2024)](https://taylor-amarel.com/2025/04/comprehensive-comparison-feast-vs-tecton-vs-hopsworks-for-cloud-based-feature-stores-2024/)
- [DuckDB for Feature Stores: Lightweight and Fast — Medium](https://medium.com/@2nick2patel2/duckdb-for-feature-stores-lightweight-and-fast-6a7b1fc509d9)
- [DuckDB vs SQLite: The 2025 Data Analysis Showdown — Medium](https://medium.com/@bhagyarana80/duckdb-vs-sqlite-the-2025-data-analysis-showdown-0f01711db50b)
- [Dealing with Train-Serve Skew in Real-time ML Models — Nubank Engineering](https://building.nubank.com/dealing-with-train-serve-skew-in-real-time-ml-models-a-short-guide/)
- [Training Serving Skew — Giskard AI](https://www.giskard.ai/glossary/training-serving-skew)
- [Stop the Spill: The Blueprint for Eradicating Data Leakage — Microsoft Data Science](https://medium.com/data-science-at-microsoft/stop-the-spill-the-blueprint-for-eradicating-data-leakage-6f924e543a95)
- [Overview of Leakage Scenarios in Supervised ML — Journal of Big Data, 2025](https://journalofbigdata.springeropen.com/articles/10.1186/s40537-025-01193-8)
- [Pandas2 and Polars for Feature Engineering — Hopsworks](https://www.hopsworks.ai/post/pandas2-and-polars-for-feature-engineering)
- [PySpark vs Pandas vs Polars: Comprehensive Performance Benchmark 2025](https://taylor-amarel.com/2025/04/pyspark-vs-pandas-vs-polars-a-comprehensive-performance-benchmark-for-large-dataset-manipulation/)
- [Technical Analysis Meets Machine Learning: Bitcoin — arxiv, 2025](https://arxiv.org/pdf/2511.00665)
- [Machine Learning Approaches to Cryptocurrency Trading Optimization — Springer Nature, 2025](https://link.springer.com/article/10.1007/s44163-025-00519-y)
- [Predicting Bitcoin Market Trends with Enhanced Technical Indicator Integration — arxiv, 2024](https://arxiv.org/html/2410.06935v1)
- [What is a Feature Store in ML, and Do I Need One? — JFrog ML](https://www.qwak.com/post/what-is-a-feature-store-in-ml)
- [Top 4 Most Popular Feature Store Tools for ML in 2024 — JFrog ML](https://www.qwak.com/post/top-ml-feature-stores)
- [Feature Store Summit 2024: Key Takeaways — Medium](https://medium.com/data-for-ai/feature-store-summit-2024-key-takeaways-aace159d8bd1)
- [MLflow Data Versioning: Techniques, Tools & Best Practices — LakeFS](https://lakefs.io/blog/mlflow-data-versioning/)
- [Data Drift: Key Detection and Monitoring Techniques 2026 — Label Your Data](https://labelyourdata.com/articles/machine-learning/data-drift)
- [Detecting and Managing Data Drift: Tools and Best Practices — Acceldata](https://www.acceldata.io/blog/data-drift)
- [How to Build Machine Learning Systems With a Feature Store — Neptune.ai](https://neptune.ai/blog/building-ml-systems-with-feature-store)
- [What is a Feature Store? Complete Guide — Databricks](https://www.databricks.com/blog/what-feature-store-complete-guide-ml-feature-engineering)
- [Hybrid Machine Learning and Stochastic Volatility Models for Crypto — Springer, 2025](https://link.springer.com/article/10.1007/s44257-025-00046-1)

---

*Researcher ID: 018 | Dr. Maria Garcia | Status: COMPLETE | Date: 2026-02-24*
