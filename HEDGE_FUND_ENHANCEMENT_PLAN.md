# Hedge Fund Enhancement Plan — Crypto Prediction System

**Date:** 2026-04-06 (v3 — Edge Addendum + Backtesting + Non-Crypto deep analysis)  
**Source:** Analysis of findtorontoevents.ca/audit vs institutional-grade standards  
**Review:** Mercury AI (2026-04-06) — all recommendations incorporated  
**Edge Analysis:** See `EDGE_ADDENDUM.md` for full diagnosis of why Smart Picks lack consistent TP/SL edge  
**Goal:** Elevate crypto predictions to hedge fund level quality and trust **with consistent forward-proven edge**

---

## Executive Summary

The current system has a strong foundation: 5-agent ensemble, ML scoring (ml_score Spearman rho +0.33), Smart Picks multi-factor scoring, walk-forward validation, and 1,927 closed picks with decile analysis. The biggest gaps are in **statistical rigor** (multiple testing correction), **tail risk management**, and **operational infrastructure** (database, monitoring, kill switches). Mercury AI's review added concrete implementation details, quick wins, and refined priorities throughout.

**Critical new finding (v3):** Backtest-forward correlation is **-0.91** — the system is optimized to select overfit strategies. 78.9% of trades hit SL. The DNA mutation system produces 14.3% WR live. See `EDGE_ADDENDUM.md` for the full diagnosis and 7-action fix plan. The hedge fund enhancements below are necessary but **insufficient without fixing the edge problem first**.

### Repo alignment (since 2026-04-06 draft)

Partial coverage already exists; the items below are **not** a substitute for Harvey-Liu / DSR / TimescaleDB, but they narrow the gap until those land.

| Plan theme | In-repo today |
|------------|----------------|
| Tail risk (§2) | `tools/hedge_fund_portfolio_risk_snapshot.py` → `alpha_engine/data/hedge_fund_risk_snapshot.json` (historical VaR/CVaR on closed crypto `pnl_pct`). Re-run after major closes updates. |
| Kill switches (§5) | `audit_trail/quality_gates.py`: AUTO_KILL / SYMBOL_PAUSE / SOURCE_PROBATION penalties + **4-tier portfolio DD** (5/10/15/20%). Redis bus: `tools/dd_alert.py` when shipped. Reconcile wording with live code on each deploy. |
| Non-crypto / cross-asset quality | `audit_trail/non_crypto_strategy_set.py` (tiered boosts for consensus, COT, RSI2 lanes), futures feed wired in `dashboard_generator.py`, `STOCK` parity in gates. |
| Prediction markets (§7) | Polymarket/Kalshi/consensus agents + fallbacks; wallet-copy JSON can be sparse — see `docs/AUDIT_SMART_VA_NONCRYPTO_RESEARCH_2026-04-06.md`. |
| API reliability (§5) | `alpha_engine/api_failover.py` (multi-endpoint chains). |

---

## Current Capabilities (What We Have)

- **ML Models:** XGBoost, LightGBM, LSTM with stacking meta-learner
- **Ensemble:** 5 AI agents (Claude Opus, Antigravity, Grok, KIMI, Mercury) competing independently
- **Smart Picks:** 6-dimension scoring (Direction x Regime, Elite Score, Freshness, TP Upside, HTF Alignment, MTF Gate)
- **Quality Gates:** R:R ≥ 1.2, TP remaining ≥ 10%, Age ≤ 48h, 14 banned systems
- **Validation:** Walk-forward, binomial p-value, decile analysis, overconfidence detection
- **Strategy Universe:** 156+ strategies across crypto/equity/forex/commodity/futures/ETF
- **Infrastructure:** GitHub Actions, JSON data feeds, Binance CCXT, static HTML dashboards

---

## Gap Analysis & Enhancements

### 1. Statistical Rigor & Validation

| Gap | Current | Hedge Fund Standard | Priority | Mercury Additions |
|-----|---------|-------------------|----------|-------------------|
| Multiple testing correction | Not applied | Harvey-Liu: adjust Sharpe for # strategies tried | **CRITICAL** | Also implement **Benjamini-Hochberg FDR control** on binomial p-values for transparent false-discovery-rate view |
| Deflated Sharpe Ratio | Not computed | DSR corrects for model selection across 156+ strategies | **CRITICAL** | **Automate in backtest pipeline**, store alongside raw Sharpe in validation table. Flag DSR < 0.5 for manual review |
| Purged cross-validation | Basic walk-forward | Gap between train/test windows to prevent leakage | HIGH | Adopt **Purged K-Fold with 1-2 week embargo** (asset-liquidity-dependent). Eliminates look-ahead bias in high-freq crypto |
| Statistical significance | Binomial p-value for WR only | Sharpe significance (Lo 2002), Diebold-Mariano | HIGH | **Stub:** `tools/lo_sharpe_significance_stub.py` → `tools/data/lo_sharpe_significance_report.json` (moment-based SR variance, pooled `pnl_pct`; **Diebold–Mariano** still open) |
| Regime-segmented backtests | Global metrics only | Per-regime Sharpe (bull/bear/sideways/crisis) | HIGH | Use existing HMM to label each day. Compute per-regime **Sharpe, Sortino, and Calmar ratios**. Add **heat-map** to dashboard |
| Overfitting audit trail | Informal | Document # strategies tried, params explored, rejections | MEDIUM | Create **Git-tracked experiment log** (JSON/SQLite): model type, hyperparams, feature set, data version, backtest window, metrics |

**Actions:**
1. Implement Harvey-Liu multiple testing adjustment across all 156+ strategies
2. Compute Deflated Sharpe Ratio for every strategy and the ensemble; **automate in pipeline, store in validation table, flag DSR < 0.5**
3. Add **Purged K-Fold with configurable embargo (1-2 weeks)** for every new model version
4. Run Sharpe significance tests (Lo 2002 formula) on all live strategies
5. Segment all backtests by regime (HMM states) and report per-regime **Sharpe, Sortino, Calmar** — dashboard heat-map
6. **Add Benjamini-Hochberg FDR control** to binomial p-value table *(Mercury quick win)*
7. **Create Git-tracked experiment log** for reproducibility audit trail

---

### 2. Risk Management

| Gap | Current | Hedge Fund Standard | Priority | Mercury Additions |
|-----|---------|-------------------|----------|-------------------|
| Position sizing | Fractional Kelly (0.25) | Kelly + CVaR constraints + volatility scaling | HIGH | **Dynamic Kelly**: `w = Kelly × (target_CVaR / current_CVaR)` — caps exposure when tail risk spikes |
| Correlation monitoring | Static max_corr: 0.7 | Dynamic correlation matrix, rolling, regime-aware | HIGH | **Rolling 30d/90d correlation matrix** → risk-parity optimizer. Alert when any pair > 0.85 for > 5 days |
| Drawdown management | 20% halt cap | Tiered circuit breakers (5%/10%/15%/20%) | HIGH | **Four-tier scheme**: 5% → reduce 25%; 10% → halve; 15% → pause entries; 20% → full shutdown. **Slack/Teams alerts** at each tier |
| Tail risk | **Partial:** historical VaR/CVaR snapshot | CVaR/VaR at 95%/99% per live position + portfolio-weighted ES | **CRITICAL** | Add **Expected Shortfall at 99.5%** and **MDD over 30-day rolling windows**. Store in time-series table |
| Concentration limits | Per-symbol only | Per-strategy, per-asset-class, per-regime | MEDIUM | — |
| Leverage controls | "1x" filter | Dynamic leverage based on volatility regime | MEDIUM | — |
| Scenario analysis | None | Stress test: -30% BTC crash, exchange failure, liquidity crisis | HIGH | **Scenario engine** with 3 stress vectors: (1) 30% BTC crash, (2) 24h exchange outage (zero liquidity), (3) sudden stablecoin regulatory ban. Produce "stress-loss" report |

**Actions:**
1. Implement tiered drawdown circuit breakers with auto-deleveraging **+ Slack alerts at each tier**
2. Add rolling correlation matrix (30d/90d) for portfolio construction **+ correlation heat-map alert**
3. Compute CVaR at 95%/99% for every active pick and portfolio **+ ES at 99.5% + 30-day rolling MDD**
4. Build scenario stress tests with **3 defined stress vectors** and stress-loss reporting
5. **Dynamic Kelly**: `Kelly × (target_CVaR / current_CVaR)` for position sizing

---

### 3. Execution & Transaction Cost Analysis (TCA)

| Gap | Current | Hedge Fund Standard | Priority | Mercury Additions |
|-----|---------|-------------------|----------|-------------------|
| Slippage modeling | Assumed 0.05% | Actual fill data, market impact model | **CRITICAL** | Capture real-time fills from Binance. Compute `slippage = (fill_price − signal_price) / signal_price`. Fit **Kyle's lambda** for market impact vs trade size / 24h volume |
| Transaction costs | 0.1% fee assumed | Full TCA: spread, impact, timing, opportunity cost | HIGH | — |
| Execution quality | Not tracked | Fill rate, partial fills, latency, rejection rate | HIGH | Track **fill rate, partial-fill freq, avg latency, rejection reasons**. **Grafana panel** with thresholds (latency > 500ms alert) |
| Order book analysis | Limited | Depth-of-market, liquidity scoring per symbol | MEDIUM | **Liquidity Score** = (top-5 bid+ask size) / avg 24h volume. Cap position size at 2% of score-weighted liquidity |
| Smart routing | Single exchange (Binance) | Multi-exchange best execution, arbitrage detection | MEDIUM | Multi-exchange router across **Binance, Kraken, Bybit, OKX** — best price-adjusted-for-fees + lowest slippage |

**Actions:**
1. Log actual fill prices vs signal prices; compute realized slippage per symbol **+ Kyle's lambda impact model**
2. Build market impact model for position sizing constraints
3. Implement **multi-exchange smart routing** (Binance, Kraken, Bybit, OKX) with fee optimization
4. Track execution quality metrics: fill rate, average latency, rejection rate **+ Grafana dashboard**
5. **Liquidity Score** per symbol for position-size capping

---

### 4. ML Pipeline & Model Governance

| Gap | Current | Hedge Fund Standard | Priority | Mercury Additions |
|-----|---------|-------------------|----------|-------------------|
| Feature importance | Mentioned but not systematic | SHAP values per prediction, drift detection | HIGH | **Deploy SHAP for every model**, store top-10 features/day. **Auto-drift alert** when SHAP distribution shifts > 20% from baseline |
| Concept drift | Manual monitoring | Automated: ADWIN, Page-Hinkley, KS-test on residuals | **CRITICAL** | **ADWIN on residuals + weekly KS test on feature distributions**. Auto-trigger retraining on drift (don't wait for 24h) |
| Model versioning | Informal | MLflow/DVC: track every version, hyperparams, data | HIGH | **MLflow with central model registry**. Enforce: every model must be registered with validation score (DSR, Sharpe, CVaR) before promotion to production |
| A/B testing | 5-AI battle informal | Controlled experiment with statistical significance | MEDIUM | — |
| Auto-retraining | "Full refresh every 24h" | **Trigger-based** retraining on drift detection | MEDIUM | Tie to ADWIN/KS drift detection — immediate retrain, not scheduled |
| Prediction calibration | Not checked | Brier score, reliability diagrams, Platt scaling | HIGH | **Brier Score + reliability diagrams** per agent. If calibration error > 0.02, apply **Platt scaling or isotonic regression** before ensemble |
| Ensemble weighting | Equal or manual | Optimal weights via stacking, Bayesian model averaging | MEDIUM | **Bayesian Model Averaging (BMA)**: weight ∝ posterior probability given recent performance. Update weights **weekly** |

**Actions:**
1. Implement SHAP-based feature importance dashboard **with 20% drift alert + weekly email digest** *(Mercury quick win)*
2. Add concept drift detection (**ADWIN on residuals + weekly KS test**); **auto-trigger retraining**
3. Version all models with **MLflow central registry**; track data → features → model → prediction lineage
4. Compute **Brier score and reliability diagrams**; Platt/isotonic scaling if calibration error > 0.02
5. **Bayesian Model Averaging** for ensemble weights, updated weekly

---

### 5. Operations & Infrastructure

| Gap | Current | Hedge Fund Standard | Priority | Mercury Additions |
|-----|---------|-------------------|----------|-------------------|
| Database | JSON files on disk | PostgreSQL/TimescaleDB for time-series | HIGH | **TimescaleDB hypertables** for raw market data, model predictions, and trade logs (separate tables) |
| Monitoring/alerting | HTML dashboard, manual | Grafana/Datadog: latency, errors, model health, P&L | HIGH | **Prometheus + Grafana**. Alerts: model latency > 5s, data-feed gaps > 2min, kill-switch activation, CVaR spikes |
| Kill switches | 20% DD halt only | Multi-level: per-strategy, per-symbol, portfolio-wide | **CRITICAL** | **Hierarchical micro-service**: per-asset signal → per-strategy → portfolio-wide → exchange-wide. **Immutable append-only log** for all actions |
| Disaster recovery | GitHub repo backup | Hot standby, automated failover, data replication | MEDIUM | **Hot standby replica** in different AZ/cloud. **pgBackRest** for continuous WAL archiving. Quarterly failover tests |
| Audit trail | audit_trail/ module exists | Full signal → order → fill → P&L chain | HIGH | **Immutable event store** (Kafka with log-compaction). Cryptographic hash chain linking events for tamper-evidence |
| API reliability | api_failover.py exists | Circuit breakers, rate limiting, multi-provider fallback | MEDIUM | — |
| Secrets management | Not visible | Vault/KMS for API keys, encrypted at rest | HIGH | **HashiCorp Vault** (or cloud-native). Auto-rotate keys every 30 days. Least-privilege IAM per service |

**Actions:**
1. Migrate from JSON files to **TimescaleDB hypertables** (market data, predictions, trade logs)
2. Implement multi-level kill switches (**hierarchical micro-service with immutable append-only log**)
3. Build **Prometheus + Grafana** monitoring with specific alert thresholds
4. Full signal-to-P&L audit chain **with cryptographic hash chain (tamper-evident)**
5. Implement **HashiCorp Vault** for secrets with 30-day auto-rotation
6. **Hot standby + pgBackRest WAL archiving** + quarterly failover tests

---

### 6. Compliance & Reporting

| Gap | Current | Hedge Fund Standard | Priority | Mercury Additions |
|-----|---------|-------------------|----------|-------------------|
| Performance reporting | Dashboard only | GIPS-compliant returns, monthly fact sheets | MEDIUM | **GIPS fact sheets**: time-weighted returns, money-weighted returns, attribution by asset class/strategy/regime |
| Risk reporting | Decile analysis | Daily VaR/CVaR, stress test results, factor exposures | HIGH | **Daily risk bulletin**: VaR (95% & 99%), CVaR, stress-test outcomes, concentration limits, **risk-budget chart** (allocated vs used) |
| Trade reconstruction | Partial (audit_trail) | Full audit: who/what/when/why for every trade | HIGH | **One-click trade-replay** via immutable event store — reconstruct order book state at time of each trade |
| Data quality | data_quality_audit.py exists | Automated: completeness, timeliness, accuracy checks | MEDIUM | — |
| Regulatory readiness | None | SOC 2 controls, data retention, access logging | LOW → **MEDIUM** | Start **SOC 2 controls now**: RBAC access logs, **7-year data retention** for trade logs, quarterly external security assessments |

**Actions:**
1. Generate monthly **GIPS-compliant fact sheets** with multi-dimensional attribution
2. **Daily risk bulletin**: VaR/CVaR, stress tests, concentration, risk-budget chart
3. **One-click trade-replay** from immutable event store
4. Begin **SOC 2 prep**: RBAC, 7-year retention, quarterly security assessments

---

### 7. Alpha Generation & Signal Quality

| Gap | Current | Hedge Fund Standard | Priority | Mercury Additions |
|-----|---------|-------------------|----------|-------------------|
| On-chain signals | Not integrated | Exchange flows, whale alerts, NVT, MVRV | HIGH | **Glassnode + CryptoQuant**: exchange inflows/outflows, whale wallets (≥ 10k BTC), NVT, MVRV. Normalize to 0-1 score as features |
| Sentiment analysis | Fear & Greed index only | NLP on Twitter/Reddit/Telegram, prediction markets | MEDIUM | **BERT-based NLP pipeline** for topic-specific sentiment (e.g., "Ethereum scaling", "Regulation"). Combine with Polymarket/Kalshi odds |
| Macro regime | HMM regime detection | Fed policy, DXY, yields, cross-asset correlation | MEDIUM | **Expand HMM with macro**: DXY, Fed Funds Rate, VIX, total crypto market cap → richer states (e.g., "risk-on crypto-bull") |
| Alternative data | None | Funding rates, open interest, options flow, social volume | HIGH | Add **funding rate, open interest, options IV, Telegram/Discord social volume**. L1 regularization feature selection |
| Alpha decay monitoring | Strategy momentum tracked | Rolling Sharpe degradation, half-life estimation | HIGH | **Rolling 30-day Sharpe** per strategy. If Sharpe drops > 2σ below historical mean for **3 consecutive periods** → auto de-risk |
| Cross-asset signals | BTC lead-lag only | Granger causality across full universe | MEDIUM | **Weekly Granger-causality matrix** across major crypto pairs, BTC, ETH, gold, USD. Use significant links as features |

**Actions:**
1. Integrate **Glassnode + CryptoQuant** for on-chain data (exchange flows, whale, NVT, MVRV)
2. Add funding rate, open interest, options IV as signal features **+ L1 regularization selection**
3. Implement **rolling 30-day Sharpe** with **2σ / 3-consecutive-period de-risk trigger**
4. Build **weekly Granger-causality matrix** across crypto + macro universe
5. **BERT sentiment pipeline** for Twitter/Reddit + prediction market odds layer
6. **Expand HMM** with DXY, Fed rate, VIX, total crypto market cap

---

## Top 10 Critical Enhancements (Mercury-Refined)

| # | Enhancement | Impact | Effort |
|---|------------|--------|--------|
| 1 | Harvey-Liu + DSR + Benjamini-Hochberg FDR | Validates entire system's statistical credibility | Medium |
| 2 | Tail risk (CVaR/VaR/ES at 99.5%) + 30-day rolling MDD | Prevents catastrophic losses | Medium — v0 shipped |
| 3 | Multi-level kill switches (hierarchical micro-service) | Operational safety | Low |
| 4 | Concept drift (ADWIN + KS) + auto-retraining | Prevents silent model degradation | Medium |
| 5 | Real-time TCA + Kyle's lambda + multi-exchange routing | Accurate P&L attribution | Medium |
| 6 | Regime-segmented reporting (Sharpe/Sortino/Calmar heat-map) | Capital allocation to best regimes | Low |
| 7 | TimescaleDB hypertables | Scalability and real-time analytics | High |
| 8 | On-chain (Glassnode/CryptoQuant) + derivatives signals | New alpha sources | Medium |
| 9 | Purged K-Fold cross-validation (1-2 week embargo) | Out-of-sample validity | Low |
| 10 | Immutable audit chain (Kafka + cryptographic hash) | Institutional trust and compliance | Medium |

---

## Quick Wins (≤ 2 weeks — Mercury)

| # | Quick Win | File/Tool |
|---|-----------|-----------|
| 1 | Add **Benjamini-Hochberg FDR** to existing binomial p-value table | `statistical_validator.py` |
| 2 | **30-day rolling CVaR** calculation → dashboard surface | `tools/hedge_fund_portfolio_risk_snapshot.py` |
| 3 | **Slack alert** for any strategy exceeding 5% drawdown | New: `tools/dd_alert.py` |
| 4 | **Log actual fill prices** in new fills table; first-order slippage stats | `alpha_engine/data/fills.json` → TimescaleDB |
| 5 | **SHAP importance notebook** for top model + weekly email digest | New: `notebooks/shap_weekly.ipynb` |

---

## Implementation Roadmap (Mercury Suggested)

### Phase 1 — Foundation (Weeks 1-4)
- Harvey-Liu + DSR pipeline on existing backtests
- Benjamini-Hochberg FDR on walk-forward p-values
- Purged K-Fold cross-validation framework
- Git-tracked experiment log
- 30-day rolling CVaR + Slack drawdown alerts (quick wins)

### Phase 2 — Risk Hardening (Weeks 5-8)
- Four-tier circuit breakers with Slack alerts
- Dynamic Kelly position sizing
- Rolling correlation matrix + heat-map alerts
- Scenario engine (3 stress vectors)
- SHAP drift detection + auto-retrain trigger

### Phase 3 — Infrastructure (Weeks 9-14)
- TimescaleDB migration (hypertables)
- Prometheus + Grafana monitoring
- Hierarchical kill-switch micro-service
- HashiCorp Vault secrets management
- Immutable event store (Kafka)

### Phase 4 — Alpha Expansion (Weeks 15-20)
- Glassnode + CryptoQuant on-chain integration
- BERT sentiment pipeline
- Expanded HMM (macro indicators)
- Granger causality matrix
- Bayesian Model Averaging for ensemble

### Phase 5 — Compliance (Weeks 21-24)
- GIPS-compliant fact sheets
- Daily risk bulletin
- Trade-replay system
- SOC 2 preparation
- Hot standby + disaster recovery

---

## Pilot Implementation (Mercury Suggested)

Choose **BTC-Momentum** strategy and run the full pipeline:
1. Harvey-Liu adjusted Sharpe
2. Deflated Sharpe Ratio
3. CVaR at 95% / 99%
4. Purged K-Fold validation
5. Regime-segmented performance heat-map

Produce a "proof-of-concept" report for investment committee review before scaling to all 156+ strategies.

---

## §8. Edge Generation — Finding Consistent TP/SL Profit

**Full analysis:** `EDGE_ADDENDUM.md` — read this for the complete diagnosis.

### The Core Problem

| Metric | Value | Meaning |
|--------|-------|---------|
| Backtest-Forward correlation | **-0.91** | Higher backtest WR = worse forward performance |
| SL hit rate | **78.9%** | Direction correct but SL too tight for noise |
| elite_score power | **ρ = +0.012** | Noise — 21/25 components non-predictive |
| DNA mutation live WR | **14.3%** | Combining good strategies makes them worse |
| Walk-forward survivors | **1 of 260** (0.4%) | 96.5% insufficient or failing OOS |

### 7 Actions to Consistent Edge

| # | Action | Impact |
|---|--------|--------|
| 1 | Kill 150+ unvalidated strategies, keep walk-forward survivors | Remove noise |
| 2 | ATR-based dynamic TP/SL (7 weeks overdue) | Fix 78.9% SL hit rate |
| 3 | Deploy structural edges: Funding Arb (A), ETF Decay (77% WR), Connors RSI-2 (p=6e-6) | 3-4 Grade A edges |
| 4 | Fix forward validation gate (broken 7 weeks) | Prevent overfit deployment |
| 5 | Regime-gate strategy selection | Route to best strategy per regime |
| 6 | Symbol tier hard filter (Tier 1/2 only) | Remove micro-cap losers |
| 7 | Embrace mean-reversion identity | Coherent system design |

### Non-Crypto Verdict

| Asset | WR | PnL | Action |
|-------|-----|-----|--------|
| CRYPTO | 42.8% | +3,818% | KEEP |
| EQUITY | 31.8% | -617% | KILL Alpha Factors; KEEP Connors RSI-2 (75.7%) + VIX Reversal (72%) |
| FOREX | 30.1% | -41% | KILL momentum; KEEP Bollinger bounce (65.3% OOS) |
| COMMODITY | 47.7% | -10% | KEEP COT, fix data |
| ETF | 75% (filtered) | +2% | KEEP Leveraged ETF Decay Shorts |
| FUTURES | 0% | -1.35% | KEEP futures_momentum |

### Backtesting Fix

```
1. Real data only (no synthetic seed=42)
2. Walk-forward with 1-2 week embargo
3. Anti-overfit 8-check suite (ALL pass)
4. DSR > 0.5 (corrects for 635 strategies)
5. Min 100 OOS trades (ML: 1,000+)
6. Realistic costs: 0.25% round-trip
```

---

## References

- Bailey & Lopez de Prado (2014): "The Deflated Sharpe Ratio"
- Harvey & Liu (2015): "Backtesting"
- Lo (2002): "The Statistics of Sharpe Ratios"
- Bailey et al. (2014): "Pseudo-Mathematics and Financial Charlatanism"
- Benjamini & Hochberg (1995): "Controlling the False Discovery Rate"
- Kyle (1985): "Continuous Auctions and Insider Trading" (Kyle's lambda)
- Fireblocks: Institutional crypto infrastructure standards
- Hyla Fund: Liquid alpha framework for systematic crypto strategies
- Mercury AI Review (2026-04-06): Enhancement plan feedback

---

## Tooling index (this repo)

| Artifact | Role |
|----------|------|
| `tools/hedge_fund_portfolio_risk_snapshot.py` | Regenerate tail snapshot from `closed_picks.json` |
| `alpha_engine/data/hedge_fund_risk_snapshot.json` | Output consumed by humans / future dashboard wiring |
| `audit_trail/non_crypto_strategy_set.py` | Non-crypto strategy tier boosts (audit scoring) |
| `audit_trail/quality_gates.py` | Active / Smart gates, penalties, kill alignment |
| `statistical_validator.py` | Binomial p-value testing (see also `tools/fdr_control.py` for BH-FDR) |
| `tools/fdr_control.py` | §1 **Benjamini–Hochberg FDR** on strategy win rates vs H0=50% → `tools/data/fdr_results.json` (DSR cross-ref optional) |
| `walk_forward_validator.py` | Walk-forward validation (upgrade to Purged K-Fold) |
| `tools/purged_kfold.py` | Purged K-Fold + embargo (landed 2026-04-02) |
| `tools/scenario_stress_test.py` | Three-vector stress engine (BTC crash / outage / stablecoin) |
| `tools/experiment_log.py` | Append-only **experiment_log.jsonl** (Git audit trail §1) |
| `tools/schemas/experiment_entry.schema.json` | JSON Schema for each log line |
| `tools/data/experiment_log.jsonl` | Created on first `experiment_log.py log` (git-tracked once present) |
| `tools/kyle_lambda_tca.py` | §3 v0: cross-sectional Kyle λ + round-trip TCA stats → `tools/kyle_lambda_results.json` |
| `tools/shap_drift_monitor.py` | §4 stub: drift vs `tools/data/ml_composite_baseline.json` → `tools/data/shap_drift_report.json` |
| `tools/schemas/shap_importance_snapshot.schema.json` | Snapshot format for SHAP or proxy importances |
| `tools/concept_drift_ks_stub.py` | §4 stub: two-sample **KS** on `pnl_pct` time windows + **ADWIN-lite** variance ratio → `tools/data/concept_drift_report.json` |
| `tools/brier_reliability_stub.py` | §4 stub: **Brier** + **ECE** (equal-width bins) from `confidence` vs win(`pnl_pct`) → `tools/data/brier_calibration_report.json` |
| `tools/liquidity_score_stub.py` | §3 stub: top-5 book depth vs 24h base volume + spread → `tools/data/liquidity_snapshot.json` |
| `tools/bma_ensemble_weights_stub.py` | §4 BMA-lite: Beta(1,1) win-rate × √n weights by `source_system` or `strategy` → `tools/data/bma_weights_report.json` (re-run weekly) |
| `tools/alpha_decay_rolling_sharpe.py` | §7 stub: rolling Sharpe (30d calendar or 30-trade fallback) → 2σ / 3-period decay flags → `tools/data/alpha_decay_report.json` |
| `tools/multi_exchange_router_stub.py` | §3 stub: Binance/Kraken/Bybit/OKX public tickers → fee-adjusted best buy/sell venue → `tools/data/multi_exchange_router_report.json` |
| `tools/tail_risk_es995_mdd_stub.py` | §2 stub: empirical **ES 99.5%** (worst 0.5% mean PnL) + **30d rolling MDD** on cumulative `pnl_pct` path → `tools/data/tail_risk_es995_mdd_report.json` |
| `tools/rolling_correlation_matrix_stub.py` | §2 stub: daily sum `pnl_pct` per symbol → Pearson **30d / 90d** corr; flags **|ρ| ≥ 0.85** → `tools/data/rolling_correlation_report.json` |
| `tools/page_hinkley_drift_stub.py` | §4 stub: **Page–Hinkley** mean-shift on **daily mean `pnl_pct`** (warm-up vs monitor) → `tools/data/page_hinkley_drift_report.json` |
| `tools/daily_risk_bulletin_stub.py` | §6 stub: one JSON **daily risk bulletin** — headline + VaR/CVaR + actives + satellites (CVaR, corr, stress, drift, **BH-FDR**, **BTC regime perf**) → `tools/data/daily_risk_bulletin.json` |
| `tools/data/fdr_results.json` | BH-FDR output (regenerate via `python tools/fdr_control.py`) |
| `tools/regime_performance_btc_stub.py` | §1 stub: **BTC daily** regime labels (Binance klines) × closed `pnl_pct` → per-regime Sharpe/Sortino/Calmar-like → `tools/data/regime_performance_btc_report.json` |
| `tools/lo_sharpe_significance_stub.py` | §1 stub: **Lo / DSR-block** variance of Sharpe on closed `pnl_pct` (``(mean/std)·√T``), z vs benchmark, two-sided normal **p**, **PSR** → `tools/data/lo_sharpe_significance_report.json` (numpy-only; no scipy import) |
| `tools/promote_strategy.py` | **Strategy promotion workflow**: DSR + FDR + forward WR >= 40% + >= 30 trades gate. Only path to anti-overfit registry / Smart Picks. Usage: `python tools/promote_strategy.py <name>`, `--list`, `--audit` |
| `alpha_engine/anti_overfit_gate.py` | Anti-overfit registry gate (fail-closed). `get_registry_stats()` + `audit_active_picks_against_registry()` used in CI workflow |

---

## Multi-agent coordination (Redis bus)

**Channel:** `python C:/Users/zerou/redis-bus/agent_bus.py broadcast <agent_id> "<message>"`  
**Master doc:** this file — claim work with `CLAIMING: §X — <item>` on the bus to avoid duplicate effort.

### Check-ins (append newest at top)

| UTC date | Agent | Status |
|----------|--------|--------|
| 2026-04-06 | **cursor-composer** | **DONE:** §1 **Lo-style Sharpe significance stub** — `tools/lo_sharpe_significance_stub.py`: closed `recent_closed` **pnl_pct** → **SR** = (mean/std)·√T; skew/kurt via **mean(z³), mean(z⁴)**; variance matches **statistical_validator** DSR term; **z**, two-sided normal **p**, **PSR** vs ``--benchmark-sharpe``. **numpy + math only** (scipy import stalls on some Windows hosts). Sample: **T=3500**, SR≈**−1.58**, **p_two≈0** (reject H0: SR=0 at 5%). Output `tools/data/lo_sharpe_significance_report.json`. **CLI:** ``--min-trades``, ``--crypto-only``, ``--redis-alert``. **NEXT:** per-strategy series; Diebold–Mariano vs benchmark model; bootstrap when fat tails (high z⁴). |
| 2026-04-02 | **cursor-composer** | **DONE:** §6 **Daily bulletin — FDR + regime satellites** — `tools/daily_risk_bulletin_stub.py` now ingests ``tools/data/fdr_results.json`` (**bh_fdr**: counts + sample strategy lists) and ``tools/data/regime_performance_btc_report.json`` (**regime_performance_btc**: sharpe_like_by_regime + assignment counts). Re-run ``fdr_control.py`` / ``regime_performance_btc_stub.py`` before bulletin for fresh data. **NEXT:** HTML/email; risk-budget fields. |
| 2026-04-02 | **cursor-composer** | **DONE:** §1 **Regime-segmented performance (BTC labels) stub** — `tools/regime_performance_btc_stub.py`: public **Binance** BTCUSDT **1d** klines → close-to-close return → **BULL / SIDEWAYS / BEAR / CRISIS** thresholds; maps each **closed** pick (UTC day) to regime; **Sharpe-like**, **Sortino-like**, **Calmar-like** on ``pnl_pct`` per regime (≥``--min-trades``). Sample: **3190** picks assigned, all four regimes (SIDEWAYS best mean PnL in snapshot). Output `tools/data/regime_performance_btc_report.json`. **CLI:** `--crypto-only`, `--klines-limit`, `--redis-alert`. **NEXT:** native HMM regime on pick when field populated; dashboard heat-map. |
| 2026-04-02 | **cursor-composer** | **DONE:** §1 **Benjamini–Hochberg FDR** — upgraded `tools/fdr_control.py`: argparse ``--dashboard``, ``--out`` (default ``tools/data/fdr_results.json``), ``--min-trades``, ``--alpha``, ``--h0-wr``, ``--dsr-json``, ``--redis-alert``; UTC ``generated_at_utc``; DSR survivor cross-ref unchanged. Sample: **56** strategies (≥10 trades), **10** FDR-significant, **3** pass FDR+DSR. Legacy ``tools/fdr_results.json`` removed — use **tools/data/** path. **NEXT:** dashboard tile; HTML bulletin. |
| 2026-04-02 | **cursor-composer** | **DONE:** §6 **Daily risk bulletin stub** — `tools/daily_risk_bulletin_stub.py`: pulls **dashboard** `summary` + **closed** VaR/CVaR 95/99 + cumulative DD on `pnl_pct`; **active** concentration (top symbols); optional passthrough from `tail_risk_es995_mdd`, `rolling_cvar_results`, `rolling_correlation`, `stress_test_results`, `concept_drift` (null if missing). Output `tools/data/daily_risk_bulletin.json`. **CLI:** `--crypto-only`, `--top-symbols`, `--redis-alert`. **NEXT:** HTML/email digest; risk-budget vs used when portfolio weights exist. |
| 2026-04-02 | **cursor-composer** | **DONE:** §4 **Page–Hinkley drift stub** — `tools/page_hinkley_drift_stub.py`: **daily mean `pnl_pct`** from `recent_closed` (UTC day); warm-up prefix → reference **μ** and **pstdev**; **δ** and **h** scaled from warm-up σ; standard cumulative PH for **upward** mean shift and mirrored run for **downward**. Sample: **32** trading days, **upward_drift_alert=true** (monitor-only; proxy series). Output `tools/data/page_hinkley_drift_report.json`. **CLI:** `--warmup-ratio`, `--delta-scale`, `--h-scale`, `--crypto-only`, `--redis-alert`. **NEXT:** run on true residuals; multi-series per strategy. |
| 2026-04-02 | **cursor-composer** | **DONE:** §2 **Rolling correlation matrix stub** — `tools/rolling_correlation_matrix_stub.py`: **daily** aggregate `pnl_pct` per **symbol** from `recent_closed`; **Pearson** correlation on last **30** and **90** calendar days (no-trade days **0**); top **N** symbols by activity; flags pairs **|ρ| ≥ 0.85** (Mercury concentration hint). Sample: **35** symbols, **6** high pairs (30d and 90d in one run). Output `tools/data/rolling_correlation_report.json`. **CLI:** `--top-symbols`, `--corr-threshold`, `--min-nonzero-days`, `--crypto-only`, `--redis-alert`. **NEXT:** volume-weighted returns; 5-day persistence alert; risk-parity weights. |
| 2026-04-02 | **cursor-composer** | **DONE:** §2 **ES 99.5% + rolling 30d MDD stub** — `tools/tail_risk_es995_mdd_stub.py`: `recent_closed` with timestamps; per **30 calendar days** (daily step): **ES 99.5%** = mean of worst **0.5%** of trade `pnl_pct` in window; **MDD** = max peak-to-trough on **time-ordered cumulative** `pnl_pct` (percentage points). Sample: **~3190** picks, **15** rolling windows, all-time ES99.5 **≈ −18.9%** (tail mean). Output `tools/data/tail_risk_es995_mdd_report.json`. **CLI:** `--crypto-only`, `--window-days`, `--redis-alert`. **NEXT:** dollar-equity MDD when balances exist; wire rolling series to dashboard. |
| 2026-04-02 | **cursor-composer** | **DONE:** §3 **Multi-exchange router stub** — `tools/multi_exchange_router_stub.py`: parallel public **bookTicker/ticker** from **Binance, Kraken, Bybit, OKX**; configurable **taker fee** assumptions; **effective_buy** / **effective_sell** ranking; **cross_venue_dispersion_pct** (min ask vs max bid). Symbols from dashboard **active** `*USDT` (``--max-symbols``). Output `tools/data/multi_exchange_router_report.json`. **CLI:** `--pause-ms`, `--redis-alert`. **NEXT:** depth at size, transfer latency, real fee tiers; wire into execution sim. |
| 2026-04-02 | **cursor-composer** | **DONE:** §7 **Alpha decay (rolling Sharpe) stub** — `tools/alpha_decay_rolling_sharpe.py`: closed picks with `closed_at` + `pnl_pct`; per **strategy** rolling Sharpe = mean/std×√n; primary **30 calendar days** / step 7d; if span less than window, **30 trades / step 7** (fits `recent_closed` short spans). **3 consecutive** rolling points below **hist_mean − 2σ** → `decay_flagged_strategies`. Sample run: **11** tracked, **2** flagged (monitor-only). Output `tools/data/alpha_decay_report.json`. **CLI:** `--min-total-trades`, `--window-trades`, `--crypto-only`, `--redis-alert`. **NEXT:** tie to auto de-risk / position caps; economic significance filter. |
| 2026-04-02 | **cursor-composer** | **DONE:** §4 **BMA-lite ensemble weights** — `tools/bma_ensemble_weights_stub.py`: `recent_closed` grouped by **`source_system`** (or `--groupby strategy`); **p̂ = Beta(1,1)** on wins/(wins+losses); **raw_weight = p̂ × √n**; normalized **weight** + **entropy** / **effective # sources**. Sample: **23** buckets (min 15 trades), **H≈2.82**, **n_eff≈16.8**, top weight **claude_gainer_st ≈ 0.21**. Output `tools/data/bma_weights_report.json`. **CLI:** `--min-trades`, `--top`, `--redis-alert`. **NEXT:** marginal likelihood / stacking when models export scores; wire weights into ensemble if product wants. |
| 2026-04-06 | **cursor-composer** | **DONE:** §3 **Liquidity score stub** — `tools/liquidity_score_stub.py`: USDT symbols from dashboard **active** → `api_failover` **order book** (top 5) + **24h ticker**; **liquidity_ratio** = (Σ bid qty + Σ ask qty) / `volume`; **spread_pct**. Output `tools/data/liquidity_snapshot.json`. **CLI:** `--max-symbols`, `--spread-alert-pct`, `--ratio-floor`, `--redis-alert`. **NEXT:** notional-weighted depth; 2% position cap vs score; multi-exchange. |
| 2026-04-06 | **cursor-composer** | **DONE:** §4 **Brier + reliability (ECE) stub** — `tools/brier_reliability_stub.py`: closed picks with `confidence`≥floor → outcome **y=1[pnl_pct>0]**; **Brier**, **ECE** (10 equal-width prob bins), **Brier skill** vs constant p̂=win_rate. Sample: **n≈2968**, **Brier≈0.29**, **ECE≈0.19** → **calibration_alert** at default thresholds (tighten to Mercury 0.02 ECE when probs are true model outputs). **CLI:** `--min-confidence`, `--ece-alert`, `--brier-alert`, `--redis-alert`. |
| 2026-04-06 | **cursor-composer** | **DONE:** §4 **concept drift KS + ADWIN-lite** — `tools/concept_drift_ks_stub.py`: time-ordered `recent_closed` → two-sample **Kolmogorov–Smirnov** on **pnl_pct** (early vs late window) + variance ratio first/last quartile. Sample run: **n≈3193**, **D≈0.11** vs crit **≈0.048** → **KS drift alert**; variance ratio also flagged — **monitor / consider retrain** (pnl is outcome proxy, not model residual). Output `tools/data/concept_drift_report.json`. **NEXT:** export true residuals; wire to GHA; fills slippage. |
| 2026-04-06 | **cursor-composer** | **DONE:** §4 **SHAP drift stub** — `tools/shap_drift_monitor.py` compares normalized mean `ml_composite_breakdown` (active/closed pools) to `tools/data/ml_composite_baseline.json`; metrics **l1_half**, **max_abs_delta**, cosine sim; default alert **>0.20**. Schema `tools/schemas/shap_importance_snapshot.schema.json`. **CLI:** `--init-baseline`, `--redis-alert`. Swap in real SHAP JSON same schema when models export it. **NEXT:** fills-based slippage, ADWIN/KS stub, or wire monitor into GHA post-dashboard. |
| 2026-04-06 | **cursor-composer** | **DONE:** §3 **Kyle λ / TCA v0** — `tools/kyle_lambda_tca.py` reads `picks.recent_closed`, cross-sectional OLS `r_s ~ α + λ·Q_s` (symbol flow imbalance vs mean signed return). Latest run: **85** symbols (n≥8), **λ≈2.80**, R²≈0.0048, mean signed ret **~22.4%** (data artifact / selection — monitor only). Output `tools/kyle_lambda_results.json`; `--log-experiment` → `experiment_log.jsonl`. **NEXT:** §4 SHAP drift stub or fills-based slippage when `fills.json` exists. |
| 2026-04-02 | **cursor-composer** | **DONE:** §1 Git experiment log — `tools/experiment_log.py` + `tools/schemas/experiment_entry.schema.json` + `tools/data/` (append JSONL). CLI: `python tools/experiment_log.py log|tail`. **Verified:** `dsr_pick_filter` wired; `smart_picks` DSR → `smart_score`, `quality_gates` DSR → dashboard `score` (separate scalars). **NEXT:** claim §3 Kyle/TCA or §4 SHAP stub on bus before coding. |
| 2026-04-02 | claude-paper-tv | Broadcast: Kilocode P0 + Mercury quick wins + 4–8 parallel subagents (FDR, rolling CVaR, DD alert, stress, regime perf, purged kfold, DSR filter, Kelly, funding, correlation). See bus archive for full UNCLAIMED list. |

### Handoff notes for implementers

- After **DSR filter** merges: ensure `get_dsr_survivors()` failure mode is fail-open (empty set = no extra penalty) so production never blanks the feed on missing JSON.
- **Non-crypto** path: `asset_class` quarantine set must stay in sync with `_NON_CRYPTO_AC` in `quality_gates.py` (explicit set, not `!= CRYPTO`).
