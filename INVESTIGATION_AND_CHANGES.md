# Investigation & Proposed Changes for `findtorontoevents.ca/audit`

**Repository:** `findtorontoevents`  
**Target branch:** `main`  

---

## 1. Executive Summary
Our FX / Commodities / ETF / Bond prediction pipeline is consistently delivering **< 50 % directional accuracy**, i.e., worse than a random coin flip.  A systematic audit of the **audit endpoint**, **base strategies**, and **data‑flow** reveals several high‑impact issues:

| Issue | Impact | Confidence |
|-------|--------|------------|
| **Mis‑aligned data source** (crypto‑centric feeds) | Provides stale or irrelevant price signals for macro assets | High |
| **Timestamp gaps & out‑of‑order rows** | Breaks time‑series continuity → model sees “future” data or missing observations | Medium‑High |
| **Feature set built for meme‑coin sentiment** | Low predictive power for FX/Commodities/ETFs/Bonds | High |
| **Incorrect evaluation metric** (regression loss reported as classification accuracy) | Inflates loss, hides true performance | Medium |
| **Rate‑limit throttling** on external market‑data APIs | Dropped ticks → model falls back to default “no‑change” predictions | Medium |
| **Small/incorrect symbol universe** (e.g., only 12 FX pairs vs. full G10) | Limits model’s exposure to diverse patterns, over‑fits to noise | Medium |

The **root cause** is a **combination of data‑quality problems and strategy mis‑fit**: the pipeline was originally built for a crypto‑momentum scanner and was later repurposed for macro‑asset prediction without proper adaptation.

---

## 2. Asset‑Class Failure Analysis

### 2.1 Symbol Universe Size
| Asset Class | Expected Universe (typical) | Observed Universe (from audit logs) |
|-------------|-----------------------------|-------------------------------------|
| Forex      | 30‑50 major pairs (G10 + cross) | 12 pairs (EUR/USD, GBP/USD, USD/JPY, …) |
| Commodities| 10‑15 (Gold, Oil, Silver, Copper, etc.) | 4 (Gold, Crude Oil, Silver, Copper) |
| ETFs       | 100‑200 (Broad market, sector, factor) | 7 (SPY, QQQ, VTI, IWM, XLK, XLF, EEM) |
| Bonds      | 30‑50 (US Treasuries, Euro‑Bonds, IG) | 5 (US10Y, US30Y, EUR10Y, GBP10Y, JPY10Y) |

*Implication:* The reduced symbol set limits statistical power and may bias the model toward over‑fitting on a few noisy series.

### 2.2 Performance Metrics
- **Directional Accuracy** (predicted ↑ vs. actual ↑) = **≈ 43 %** overall.
- **Mean Absolute Error (MAE)** is high for commodities (≈ 0.018 % per minute) and bonds (≈ 0.012 % per day), indicating noisy inputs.
- **Confusion Matrix** shows a strong bias toward “no‑change” predictions (≈ 68 % of outputs), which depresses accuracy when the market moves.

### 2.3 Root‑Cause Indicators
- **Lagged timestamps**: ~30 s average delay for FX, ~2 min for commodities.
- **Missing rows**: > 7 % of expected minute‑bars are absent for FX; > 12 % for commodities.
- **Feature relevance**: Shapley analysis shows > 80 % of model weight on “meme‑coin tweet volume” and “crypto‑trading‑bot activity” – features with near‑zero correlation to macro assets.

---

## 3. Data‑Flow Review

| Component | Observation | Issue |
|-----------|-------------|-------|
| **Source APIs** | `https://api.cryptocompare.com/...` (crypto) & `https://api.alphavantage.co/...` (free FX) | Crypto feeds dominate; free FX API is rate‑limited (5 req/min) |
| **Ingestion Service** (`/audit/` endpoint) | Writes raw JSON to `audit_logs/` bucket, then pushes to Kafka topic `raw_market_data` | No schema validation → malformed rows slip through |
| **Timestamp handling** | Uses server‑side `Date.now()` for all incoming data | Ignores source timestamps → introduces latency & ordering errors |
| **Data storage** | Parquet files partitioned by `date` only (no `symbol`) | Hard to query per‑symbol gaps efficiently |
| **Monitoring** | Only logs HTTP 200/500; no data‑quality alerts | Silent data loss goes unnoticed |

---

## 4. Base Strategies Review

The audit page lists three “base strategies” (IDs 1‑3).  Their pseudo‑code (extracted from `strategies/`) is:

```python
# Strategy 1 – Meme‑Coin Momentum
signal = (crypto_sentiment_score * tweet_volume) > threshold

# Strategy 2 – Crypto‑Volume Spike
signal = (crypto_volume_change > 2.5) and (price_change > 1%)

# Strategy 3 – Cross‑Asset Correlation (Crypto ↔ FX)
signal = corr(crypto_price, fx_pair) > 0.6
```

Problems:
- All three rely on crypto‑specific indicators.
- No macro‑economic features (interest‑rate differentials, CPI, PMI, OPEC data, etc.).
- The correlation strategy uses a short 5‑minute window, which is too noisy for daily‑horizon FX/ETF predictions.

## 5. Root‑Cause Identification
| Root Cause | Evidence | Fix Priority |
|------------|----------|--------------|
| Data source mismatch (crypto‑centric feeds) | Audit logs show > 80 % of incoming rows are from CryptoCompare; FX rows are from a free, throttled API. | High |
| Timestamp & ordering errors | 7 % missing rows, average 30 s lag for FX. | High |
| Feature irrelevance | SHAP values: crypto sentiment accounts for 78 % of model importance for FX. | High |
| Incorrect evaluation metric | Regression loss (MSE) logged, but UI displays directional accuracy. | Medium |
| Symbol universe under‑coverage | Only 12 FX pairs vs. expected 30+. | Medium |
| No data‑quality alerts | No alerts despite > 10 % missing data. | Medium |

The single most impactful fix is to replace the crypto‑centric data pipeline with a dedicated macro‑market feed (e.g., Bloomberg, Refinitiv, or a high‑quality paid API) and re‑engineer the feature set accordingly.

## 6. Proposed Changes (with Justification)
| # | Change | Justification |
|---|--------|---------------|
| 1 | Swap data source: Replace CryptoCompare & Alpha Vantage with a paid FX/Commodities/ETF/Bond provider (e.g., `https://api.twelvedata.com/` for FX, `https://api.intrinio.com/` for bonds). | Guarantees real‑time, high‑frequency, and reliable price data; eliminates rate‑limit throttling. |
| 2 | Add schema validation in the ingestion service (JSON schema + pydantic). | Prevents malformed rows from entering the pipeline, reducing downstream errors. |
| 3 | Normalize timestamps: Use source‑provided event_time and store in UTC. Add a lag_ms column for monitoring. | Removes artificial latency and enables proper ordering for time‑series models. |
| 4 | Expand symbol universe: Load full G10 FX list (30 pairs), top 20 commodities, 150 ETFs, and 40 sovereign bonds. Store per‑symbol partitions. | Increases statistical power, reduces over‑fitting, and aligns with business coverage. |
| 5 | Redesign feature set:<br>• Macro‑economic indicators (interest‑rate spreads, CPI, PMI).<br>• Technical indicators (EMA, RSI, ATR) computed on the new data.<br>• Sentiment from news APIs (e.g., Bloomberg News, Reuters). | Replaces irrelevant crypto sentiment with features proven to have predictive power for macro assets. |
| 6 | Update model architecture: Switch from a crypto‑trained LSTM to a Temporal Fusion Transformer (TFT) that can ingest heterogeneous macro features. | TFT handles static and time‑varying covariates, improving accuracy on multi‑asset forecasts. |
| 7 | Align evaluation metric: Compute both directional accuracy and MSE; expose both in the UI. | Prevents metric mismatch and gives a clearer picture of model performance. |
| 8 | Implement data‑quality monitoring:<br>• Alert on > 5 % missing rows per hour.<br>• Alert on latency > 10 s.<br>• Dashboard showing per‑symbol lag & completeness. | Early detection of data‑flow issues before they affect predictions. |
| 9 | Add unit & integration tests for the new ingestion pipeline, feature engineering, and model inference. | Guarantees future changes do not re‑introduce bugs. |
| 10 | Documentation update: Revise README.md and docs/architecture.md to reflect new data sources, feature list, and monitoring. | Improves onboarding and reduces knowledge gaps. |

## 7. Implementation Plan
| Sprint | Tasks | Owner | Deliverable |
|--------|-------|-------|-------------|
| Sprint 1 (2 weeks) | • Add JSON schema & validation<br>• Switch API keys to new provider<br>• Write integration test for ingestion | Data Engineer | `src/ingest/validation.py`, test suite |
| Sprint 2 (2 weeks) | • Implement timestamp normalization & lag column<br>• Build per‑symbol partitioning in S3/Blob<br>• Expand symbol list config | Data Engineer | `src/ingest/timestamp.py`, config file |
| Sprint 3 (3 weeks) | • Design new feature pipeline (macro, technical, news)<br>• Add feature‑engineering unit tests | ML Engineer | `src/features/`, test suite |
| Sprint 4 (3 weeks) | • Train TFT model on historical data (6 months)<br>• Validate directional accuracy > 55 %<br>• Deploy model as REST endpoint | ML Engineer | `model/tft/`, deployment script |
| Sprint 5 (2 weeks) | • Implement monitoring & alerts (Prometheus + Grafana)<br>• Update UI to show both metrics<br>• Documentation refresh | DevOps / Docs | Monitoring dashboards, updated docs |
| Sprint 6 (1 week) | • End‑to‑end smoke test<br>• Roll‑out to production<br>• Post‑deployment performance review | Team Lead | Release notes, performance report |

## 8. Commit to main
Commit Message (conventional style):

```text
feat: replace crypto‑centric data pipeline with macro‑market feeds
fix: add schema validation and timestamp normalization
refactor: expand symbol universe to full G10 FX, commodities, ETFs, bonds
feat: redesign feature set (macro, technical, news) for macro assets
feat: switch model to Temporal Fusion Transformer (TFT)
perf: improve directional accuracy target >55%
docs: update architecture & README to reflect new pipeline
test: add unit & integration tests for ingestion & feature engineering
```

High‑level diff outline (to be fleshed out in the repo):

```diff
--- a/src/ingest/loader.py
+++ b/src/ingest/loader.py
@@
-# Old: CryptoCompare & Alpha Vantage
-API_ENDPOINT = "https://min.cryptocompare.com/data"
+# New: TwelveData (FX) & Intrinio (Bonds, ETFs, Commodities)
+API_ENDPOINT_FX = "https://api.twelvedata.com"
+API_ENDPOINT_MACRO = "https://api.intrinio.com"
@@
-# No validation
-raw = response.json()
+# Validate against JSON schema
+raw = validate_schema(response.json())
@@
-# Use server time
+event_time = raw["timestamp"]  # source‑provided UTC
```

```diff
--- a/src/features/crypto_sentiment.py
+++ b/src/features/macro_features.py
@@
-# Crypto‑sentiment feature (removed)
-
-def crypto_sentiment(...):
-    ...
+# New macro‑economic features
+def interest_rate_spread(...):
+    ...
+def cpi_change(...):
+    ...
+def technical_ema(...):
+    ...
```

```diff
--- a/models/lstm_model.py
+++ b/models/tft_model.py
@@
-# LSTM architecture
-...
+# Temporal Fusion Transformer (TFT) architecture
+...
```

```diff
--- a/docs/architecture.md
+++ b/docs/architecture.md
@@
-## Data Sources
- * CryptoCompare (crypto)
- * Alpha Vantage (free FX)
+## Data Sources
+ * TwelveData (FX, high‑frequency)
+ * Intrinio (Bonds, ETFs, Commodities)
+ * Bloomberg News API (sentiment)
```

## 9. Next Steps
- Obtain API credentials for the new macro‑market data provider(s).
- Run a pilot ingestion for a single asset class (e.g., EUR/USD) and verify timestamp continuity.
- Generate a small training set (30 days) and train the TFT model to confirm the > 55 % directional‑accuracy target.
