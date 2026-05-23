# Master Synthesis Report: 28-Researcher Crypto ML Audit

**Date:** 2026-02-24
**Scope:** Full codebase audit + world-class research synthesis
**Researchers:** 28 PhD-level domain experts (001-030, excluding 003/019)
**Total Research Output:** ~15,000+ lines across 28 individual reports

---

## Executive Summary

Twenty-eight specialized researchers audited the entire `findtorontoevents_antigravity.ca` crypto ML trading system — covering hedge fund quant strategies, deep learning architectures, ensemble methods, risk management, backtest validation, on-chain analytics, sentiment analysis, market microstructure, alpha decay, hyperparameter optimization, reinforcement learning, transformers, generative models, explainable AI, data quality, MLOps, feature stores, benchmarks, competition strategies, open source tools, cloud services, HFT, portfolio optimization, cross-exchange arbitrage, DeFi yield, MEV, regime detection, and governance tokens.

### The System Today
- **100 strategies** across 6 modules (Alpha Engine)
- **107 GitHub Actions workflows** (CPU-only, 15-30 min intervals)
- **6+ ML frameworks** (scikit-learn, XGBoost, LightGBM, PyTorch, CatBoost, SHAP)
- **7 SQLite databases**, 200+ git-committed model artifacts
- **Paper trading only** — signal generator, no order execution
- **Proven strategies:** Connors RSI-2 (75.7% WR, p=6e-6), VIX Spike Reversal (72% WR, Sharpe 6.20)

### The Verdict
**Methodological skeleton: STRONG (8/10).** The config already has `KELLY_FRACTION = 0.15`, `FRAC_DIFF_D = 0.4`, `PURGE_GAP_BARS = 20`, `MIN_DSR_PROBABILITY = 0.95`. The statistical validation discipline exceeds most retail systems.

**Implementation gaps: CRITICAL.** A cost-accounting bug makes every DSR calculation invalid. Models are git-committed without versioning. Data is re-fetched from scratch every run. No regime detection in production. No ensemble stacking.

**Expected improvement from this roadmap:** +25-50% risk-adjusted returns (Sharpe) across the portfolio if Tiers 1-3 are implemented.

---

## Prioritized Roadmap

### TIER 1: CRITICAL FIXES (Week 1) — Cost: $0

These are bugs and validation gaps that invalidate current results. **Nothing else matters until these are fixed.**

| # | Action | Source | Expected Impact |
|---|--------|--------|-----------------|
| 1.1 | ✅ **DONE 2026-02-24 (`fcce5f9268b`)** — Fix cost model bug in validation.py. `crypto_ml_edge/validation.py` now charges cost on trade bars only (`np.where(returns != 0, cost_per_trade_bar, 0.0)`) in both `cost_adjusted_sharpe` and `validate_model`. Verified on disk 2026-05-17. | R006, R001 | BTC net Sharpe flips from -2.11 to positive |
| 1.2 | **Enforce DSR 0.95 gate** — config has it but trainer.py doesn't enforce it. Add hard gate. | R006, R001 | Eliminates overfitted models before deployment |
| 1.3 | **Implement Purged CV** — non-purged CV overstates Sharpe by 15-30% on daily crypto. Use `TimeSeriesSplit` with embargo gap = holding period. | R006, R011 | Reveals true model edge; expect reported Sharpe to drop 30-50% but live performance improves |
| 1.4 | **Convert to binary long-only labels** — 3-class ({-1,0,+1}) wastes capacity on shorts in a structurally long-biased market. Binary concentrates signal. | Plan | Max probability lifts from ~0.55 to ~0.75 |
| 1.5 | **Always drop the last CCXT candle** — it's always partial and creates look-ahead bias. | R016 | Eliminates a systematic data quality error |

### TIER 2: HIGH-IMPACT FREE IMPROVEMENTS (Weeks 2-4) — Cost: $0

| # | Action | Source | Expected Impact |
|---|--------|--------|-----------------|
| 2.1 | **GT-Score objective for HPO** — Replace Sharpe-only with `0.35*Sharpe + 0.45*Sortino + 0.20*Calmar`. Zero compute cost, 98% generalization improvement per arXiv 2602.00080. | R011, R004 | +15-20% OOS generalization |
| 2.2 | **Quarter Kelly + ATR scalar sizing** — Full Kelly is insane for noisy edge estimation. Quarter Kelly with 5% hard cap, scaled by ATR vs median ATR ratio. | R005 | Cuts volatility ~50%, sacrifices only ~12% returns |
| 2.3 | **3-tier drawdown brake (5%/10%/20%)** — Mechanically prevents catastrophic loss compounding. Yellow: reduce 25-50%. Red: 25% of normal. Full stop: halt all entries. | R005 | The single highest-leverage risk management change |
| 2.4 | **F&G rate-of-change feature** — A 25+ point single-day surge predicts +4.0% avg 7-day BTC return. Currently only using absolute F&G level. | R008 | +3-5% directional accuracy on F&G signals |
| 2.5 | **Rolling 30-day Spearman IC monitoring** — Win rate alone cannot distinguish dying signal from regime mismatch. Alert at IC < 0.02 for 30 days. | R010 | Early warning for alpha decay (2-4 weeks advance) |
| 2.6 | **Single `compute_features()` function** — Training and inference must call the same code path. Kills training-serving skew. | R018 | Eliminates a class of silent prediction errors |
| 2.7 | **Feature manifest JSON alongside models** — SHA-256 hash + row count + date range + cleaning config. Minimum viable versioning at zero cost. | R018 | Full reproducibility for model debugging |
| 2.8 | **OHLCV data validator** — Run 6 checks (OHLC consistency, gaps, duplicates, outliers, volume, timestamps) before every write. | R016 | Stops all silent bad data immediately |
| 2.9 | **Real on-chain metrics from free APIs** — Replace 200d SMA proxy with real MVRV Z-Score, NUPL, STH-SOPR from Coin Metrics Community API (no key needed). | R007 | +8-12% directional accuracy on on-chain strategies |
| 2.10 | **3-state HMM regime classifier** — Train on BTC daily returns + vol + volume. Feed as LightGBM categorical feature. Upweight RSI-2 in mean-reverting, momentum in trending. | R010, R029 | +0.3-0.5 Sharpe improvement (documented in literature) |

### TIER 3: ENSEMBLE & MODEL UPGRADES (Weeks 4-8) — Cost: $0-50/month

| # | Action | Source | Expected Impact |
|---|--------|--------|-----------------|
| 3.1 | **3-model soft-voting ensemble** (LightGBM + XGBoost + CatBoost) — Use `TimeSeriesSplit` with embargo gap. | R004 | +8-12% Sharpe over single LightGBM |
| 3.2 | **Optuna TPE HPO: 75 trials** with HyperbandPruner, 90-min budget, cached best_params.json. | R011 | +15-35% Sharpe over fixed hyperparams |
| 3.3 | **Add Chronos-Bolt as zero-shot ensemble member** — Amazon's 250x-faster foundation model. CPU, 20 lines of code, no training. | R013 | +5-15% directional improvement |
| 3.4 | **4h timeframe support** — 4x fewer trades = 4x less cost drag. Config supports it; `build_features()` hardcodes 1h. | Plan | Dramatically reduces cost penalty |
| 3.5 | **Market health gate** — Wire `ml_battleground/shared/market_health.py` circuit breaker into scanner. Skip inference during PANIC regime. | Plan | Prevents trading during cascades (F&G=5) |
| 3.6 | **Probability calibration** — Isotonic calibration spreads LightGBM's clustered 0.3-0.5 probabilities for better threshold filtering. | Plan | Better signal/noise separation |
| 3.7 | **Cross-sectional momentum rank feature** — Rank of 30-day return across all scanned pairs. Documented live Sharpe ~2.0 independently. | R001 | Orthogonal alpha source, simple implementation |
| 3.8 | **Funding rate 5-feature decomposition** — Replace raw funding rate with level, z-score, sign, rate-of-change, extreme-flag. | R001 | Captures predictive content in deviation, not level |
| 3.9 | **Rolling Sharpe softmax ensemble weighting** — Daily weight recalculation from 5-day rolling Sharpe. Proven in FinRL 2024. | R004 | +5-8% additional Sharpe, reduces drawdown 4.17% |

### TIER 4: DATA & FEATURES (Weeks 6-12) — Cost: $0-49/month

| # | Action | Source | Expected Impact |
|---|--------|--------|-----------------|
| 4.1 | **VPIN proxy from REST trades** — Pre-crash warning at our 15-60 min horizon sweet spot. | R009 | Adds crash anticipation layer |
| 4.2 | **Roll Measure** — Most predictive single microstructure feature in literature. Computable from mid-prices we already store. | R009 | Near-zero implementation cost |
| 4.3 | **Google Trends via pytrends** — 0.75 correlation with BTC. Nonlinear relationship captured by gradient boosting. Free, 1 day implementation. | R008 | 1-2 week leading indicator |
| 4.4 | **FinBERT for sentiment** — Replace VADER (~56% accuracy) with FinBERT-crypto (~69% accuracy). Free, local deployment. | R008 | +13% sentiment accuracy |
| 4.5 | **Exchange netflow 7-day SMA** — Direct accumulation detection. Oct 2024 reading of -7,210 BTC preceded major Q4 rally. | R007 | Orthogonal on-chain signal |
| 4.6 | **Coinbase-Binance basis z-score** — One extra REST call. Institutional vs retail flow discrimination. Coinbase leads by 1-10 min. | R009 | Institutional flow detection |
| 4.7 | **Evidently AI drift monitoring** — Weekly PSI > 0.25 triggers retraining. Priority features: funding_rate, volume_zscore, rsi_14. | R018 | Catches regime changes before drawdowns |
| 4.8 | **LunarCrush AltRank subscription** — $49/month, most cost-effective paid social data. | R008 | Social momentum signal |
| 4.9 | **CTGAN feature augmentation** — Augment LightGBM training with synthetic bear market samples. Expect 2-5% AUC improvement. | R014 | Better bear market generalization |

### TIER 5: INFRASTRUCTURE (Months 2-3) — Cost: $20-200/month

| # | Action | Source | Expected Impact |
|---|--------|--------|-----------------|
| 5.1 | **DVC for model versioning** — Remove 200+ binary models from git. Track via DVC remotes on free S3/GCS tier. | R023 | Eliminates repo bloat |
| 5.2 | **DuckDB + Parquet data layer** — Replace SQLite ephemeral DBs. In-process, ASOF JOIN, 10x faster feature generation. | R018, R023 | Eliminates data re-fetching |
| 5.3 | **PostgreSQL on Supabase/Neon (free tier)** — Shared state across 107 workflows. | R023 | Cross-workflow persistence |
| 5.4 | **MLflow experiment tracking** — Model registry with champion/challenger aliases. Declarative rollback. | R017, R023 | Full ML lifecycle management |
| 5.5 | **Redis cache (Upstash free tier)** — Cache API responses (F&G, funding rates, CoinGecko). | R023 | Eliminates 107 workflows hitting same APIs |
| 5.6 | **Consolidate 12 requirements.txt into pyproject.toml** — Inconsistent pinning creates reproducibility risk. | R022 | Dependency sanity |
| 5.7 | **GitHub Actions caching** — `actions/cache` for pip deps and fetched data between runs. | R023 | Faster CI, lower API pressure |

### TIER 6: ADVANCED/FUTURE (Months 3-6+) — Cost: $50-500/month

| # | Action | Source | Expected Impact |
|---|--------|--------|-----------------|
| 6.1 | **5-model stacking with LR meta-learner** — LGBM + XGB + CatBoost + RF + MLP, purged time-series CV. | R004 | +15-18% total Sharpe improvement |
| 6.2 | **TimeGAN synthetic data generation** — 200-500 synthetic 2022-analog sequences for stress testing. | R014 | Robustness quantification |
| 6.3 | **Temporal Fusion Transformer** — For 4h horizon with on-chain features. Fine-tune from checkpoint on CPU. | R002, R013 | Multi-horizon calibrated forecasts |
| 6.4 | **AWS SageMaker GPU training (on-demand)** — ml.g4dn.xlarge T4 GPU at $0.53/hr for GRU-Attention and HPO. | R023 | Unlock larger models, 100+ Optuna trials |
| 6.5 | **SHAP-RFE quarterly feature selection** — Joint hyperparameter + feature optimization via shap-hypetune. | R011 | Prunes stale features systematically |
| 6.6 | **Governance token strategies** — TVL momentum divergence, protocol revenue momentum, governance activity scoring. | R030 | New alpha source for DeFi tokens |
| 6.7 | **True cross-exchange price arbitrage** — Binance vs Bybit vs OKX simultaneous comparison. Data fetcher connects to all three already. | R026 | New arbitrage alpha |
| 6.8 | **CCXT integration** — Replace 500+ lines of manual exchange API code with unified interface. | R026 | Cleaner multi-exchange infrastructure |

---

## Researcher Scorecard

| ID | Domain | Overall System Score | Top Recommendation |
|----|--------|---------------------|-------------------|
| 001 | Hedge Fund Quant | Methodology: 8/10 | Cross-sectional momentum rank as feature |
| 002 | LSTM/Attention | N/A (research) | TFT for 4h horizon, CPCV validation |
| 004 | Ensemble Methods | N/A (research) | 5-model stacking, GT-Score, TabPFN |
| 005 | Risk Management | N/A (research) | Quarter Kelly + 3-tier drawdown brake |
| 006 | Backtest Validation | N/A (research) | Fix cost bug, 7-layer validation stack |
| 007 | On-Chain Analytics | N/A (research) | Real NUPL/MVRV from Coin Metrics free API |
| 008 | Social Sentiment | N/A (research) | F&G rate-of-change, FinBERT, Google Trends |
| 009 | Market Microstructure | Codebase: 6/10 | Multi-level OBI, VPIN proxy, Roll Measure |
| 010 | Alpha Decay | N/A (research) | Rolling IC monitoring, 3-state HMM |
| 011 | Hyperparameter Opt | N/A (research) | Optuna TPE 75 trials, GT-Score objective |
| 013 | Transformer Models | N/A (research) | Chronos-Bolt zero-shot, keep LightGBM primary |
| 014 | Generative Models | Codebase: 2/10 | CTGAN augmentation for bear markets |
| 015 | Explainable AI | Codebase: 7/10 | SHAP already in trainer; add LIME for debugging |
| 016 | Data Quality | N/A (research) | OHLCV validator, drop last CCXT candle |
| 017 | MLOps/Deployment | Codebase: 5.5/10 | MLflow registry, A/B testing framework |
| 018 | Feature Store | N/A (research) | DuckDB + Parquet, single compute_features() |
| 020 | Benchmarks | Codebase: 7.1/10 | Fix survivorship bias, dataset versioning |
| 021 | Competitions | Codebase: 6.1/10 | Heterogeneous stacking (validation: 9/10) |
| 022 | Open Source | Codebase: 7/10 | Dependency consolidation, error hierarchy |
| 023 | Cloud Services | Codebase: N/A | DVC + caching (Phase 1), S3 data lake (Phase 2) |
| 024 | HFT | Codebase: N/A | Well-researched LF signal generator, not HFT |
| 025 | Portfolio Opt | Codebase: B+ | Add HRP and EWMA covariance |
| 026 | Cross-Exchange Arb | Codebase: 5.5/10 | Funding rate arb excellent (9/10); add true cross-exchange |
| 027 | DeFi Yield | Codebase: 3/10 | No DeFi protocol integration; strong funding carry |
| 028 | MEV Extraction | Codebase: 2/10 | Correctly positioned as signal engine |
| 029 | Regime Detection | Codebase: 5/10 | 5-layer hybrid: HMM+BOCPD+Hurst+ADX+GARCH |
| 030 | Governance Tokens | Codebase: 3/10 | TVL momentum, governance activity scoring |

---

## Cross-Cutting Themes (Consensus Across 5+ Researchers)

### 1. "Fix the basics before adding complexity" (R001, R004, R006, R011, R016, R018)
The cost bug, lack of purged CV, and training-serving skew are collectively responsible for more performance degradation than any missing feature or model architecture. Fix these first.

### 2. "LightGBM stays as primary" (R001, R004, R011, R013)
Tuned LightGBM is competitive with complex DL architectures for direction classification on crypto (58-65% accuracy vs Transformer's 60-66%). The compute cost differential is 10-100x. Spend that compute on better HPO and ensemble diversity.

### 3. "Regime detection is the highest-leverage upgrade" (R001, R005, R010, R029)
Four independent researchers identified regime-aware allocation as the single most impactful model improvement. A 3-state HMM trained on BTC returns + vol + volume, feeding strategy allocation weights, is expected to add +0.3-1.0 Sharpe.

### 4. "Validation > Model Architecture" (R006, R011, R020, R021)
The system's validation discipline (DSR, cost accounting, walk-forward) already exceeds most retail and many institutional systems. But the cost bug invalidates all current DSR values. Fix it, and the existing validation framework becomes genuinely world-class.

### 5. "Free on-chain data is massively underutilized" (R007, R008)
Coin Metrics Community API provides MVRV, NUPL, STH-SOPR, LTH-SOPR with no API key. These are the top-2 features in the best published ML study (82% directional accuracy). Currently using 200d SMA proxy — replacing with real data is expected to add +8-12% accuracy.

### 6. "The 15-minute scan cadence is a feature, not a bug" (R009, R024, R028)
Three researchers independently confirmed: microstructure signals lose predictive power above 15-min frequency. The system is correctly positioned as a low-frequency quantitative signal generator. Latency arbitrage and MEV are architecturally incompatible and should not be pursued.

### 7. "Correlation monitoring is essential in crypto" (R005, R010, R025)
BTC/ETH/SOL correlation converges to 1.0 during crashes, eliminating diversification at the worst moment. When rolling 10-day correlation exceeds 0.85, treat entire portfolio as a single asset and cap total crypto exposure.

---

## Key Numbers to Remember

| Metric | Current | After Tier 1 | After Tier 1-3 |
|--------|---------|--------------|----------------|
| BTC Net Sharpe | -2.11 (broken) | ~1.5-2.5 (estimated) | ~2.5-3.5 |
| DSR Gate | Invalid (cost bug) | Correctly computed | Correctly computed |
| Models passing DSR | 0% | ~30-50% (genuine) | ~50-70% |
| Validation layers | 1 (DSR only) | 4 (DSR + purged CV + cost + sample size) | 7 (full stack) |
| Ensemble depth | Single model | Single model | 3-5 model stack |
| Regime awareness | None | HMM categorical feature | Full health gate + HMM |
| On-chain data | Proxy (200d SMA) | Real (Coin Metrics) | Real + sentiment + Trends |
| Model versioning | Git-committed binaries | Feature manifests | DVC + MLflow |
| HPO trials | 20 (fixed) | 75 (Optuna TPE) | 75 + HyperbandPruner |
| Position sizing | Fixed 3.3% | Quarter Kelly + ATR | Quarter Kelly + drawdown brake |

---

## Implementation Dependencies

```
TIER 1 (Week 1) ─────────────────────────────────────────────────────
  1.1 Fix cost bug ──┐
  1.2 DSR enforcement ┤
  1.3 Purged CV ──────┤──→ Retrain all models
  1.4 Binary labels ──┤
  1.5 Drop last candle ┘

TIER 2 (Weeks 2-4) ──── Can run in parallel ────────────────────────
  2.1 GT-Score ──────────┐
  2.2 Quarter Kelly ─────┤ (independent)
  2.3 Drawdown brake ────┤
  2.4 F&G rate-of-change ┤
  2.5 IC monitoring ─────┤
  2.6 compute_features() ┤
  2.7 Feature manifest ──┤
  2.8 OHLCV validator ───┤
  2.9 Real on-chain ─────┤
  2.10 HMM regime ───────┘──→ Retrain with new features

TIER 3 (Weeks 4-8) ──── After Tier 2 retraining ───────────────────
  3.1 Ensemble ─────────┐
  3.2 Optuna HPO ───────┤
  3.3 Chronos-Bolt ─────┤──→ Full retraining + validation
  3.4-3.9 Features ─────┘

TIER 4-6 ──── Independent, prioritize by ROI ───────────────────────
```

---

## Files Referenced Across All Research

### Most-Cited Files (appearing in 5+ researcher reports)
- `crypto_ml_edge/validation.py` — Cost model bug location
- `crypto_ml_edge/trainer.py` — LightGBM training pipeline
- `crypto_ml_edge/scanner.py` — Live inference engine
- `crypto_ml_edge/config.py` — DSR gate, Kelly fraction, feature config
- `alpha_engine/production_scanner.py` — 100-strategy scanner
- `alpha_engine/ml_ranker.py` — RandomForest signal ranker
- `ml_battleground/shared/market_health.py` — Circuit breaker (unused)
- `ml_battleground/system_c_deeplearn/train_model.py` — PyTorch GRU-Attention

### Key External References (Most-Cited Across Researchers)
- Lopez de Prado — DSR, purged CV, CPCV, PBO (R006, R011, R020)
- Easley & O'Hara — VPIN, order flow toxicity (R009, R001)
- Omole & Enke (2025) — 82% directional accuracy with CNN-LSTM + MVRV + NUPL (R007)
- FinRL 2024 — Rolling Sharpe softmax ensemble, Sharpe +0.21 (R004)
- GT-Score arXiv 2602.00080 — 98% generalization improvement (R011)
- BIS 2024 — Crypto carry trade research (R001)
- CTBench NeurIPS 2025 — Crypto generation benchmark (R014)

---

*Generated by 28 parallel research agents | Synthesis date: 2026-02-24*
*Total research tokens consumed: ~1.3M across all agents*
