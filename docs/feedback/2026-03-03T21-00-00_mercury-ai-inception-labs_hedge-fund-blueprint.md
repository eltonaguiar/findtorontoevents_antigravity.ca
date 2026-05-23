# Mercury AI / Inception Labs — Hedge Fund Blueprint Feedback
> **Received:** 2026-03-03 ~21:00 UTC
> **Source:** Mercury AI, Inception Labs
> **Context:** Review of our crypto prediction system performance + hedge-fund-grade operational blueprint
> **Saved by:** Claude Code session, auto-archived for reference

---

## 1. Performance Snapshot (as analyzed)

| System / Family | Closed picks | Win-rate (WR) | Expectancy / trade | Comments |
|-----------------|--------------|--------------|-------------------|----------|
| **Mercury-2** | 46 | **39 %** | **+0.25 %** | Edge shows up when you filter for RR >= 1.4 (WR ~ 68 %, E ~ +1.87 %). |
| **Alpha Engine** | 165 | **34 %** | **-2.45 %** | Strong **directional asymmetry** - short side works (WR ~ 65 %, E ~ +3.4 %) while long side drags (WR ~ 26 %, E ~ -3.9 %). |
| **Baby Battleground** | 128 | **65 %** | **+0.53 %** | Good "core" performer. |
| **Claws of Doom** | 25 | **56 %** | **+0.78 %** | Small sample but solid. |
| **FC-PRO (baby + claws)** | 153 | **63 %** | **+0.57 %** | The current "qualified mix". |
| **ATM Challenge - funding_carry** | 39-51 per variant | **74-95 %** | **+1.61 %** (ELITE) | By far the most frequent & profitable family. |
| **ATM Challenge - ema_crossover / bollinger_squeeze** | ~30-35 each | **45-48 %** | Near breakeven | High-frequency but no edge. |
| **KILL-LIST (smart_money_fvg, m2_liquidity_lag, etc.)** | 8-9 picks each | **0-22 %** | Large negative PnL | Toxic - should be disabled. |

### Take-aways

* The **core edge** lives in a handful of components:
  * `funding_carry` (ATM) - high-frequency, high-WR, good RR.
  * `autocorrelation_exploiter`, `hurst_regime_adaptive`, `volume_profile_value_area`, `adaptive_vr_confluence` (Alpha) - strong WR & expectancy when they fire.
* **Most Alpha strategies are dormant** (1-2 trades in 16 days) because they are overly restrictive or are being scanned on a 30-min interval while they were designed for daily/weekly time-frames.
* **Direction asymmetry** is a real problem: the long side of Alpha Engine is a net drain.
* **Consensus routing** is weak - many "master picks" come from a single system, defeating the purpose of a multi-system filter.
* **Data quality** (conflicting exit-reason fields, mixed PnL units) skews performance metrics and can hide true edge.

---

## 2. What Hedge Funds / Mutual Funds Do Differently

| Hedge-Fund Practice | Why it matters for crypto |
|---------------------|---------------------------|
| **Risk-budget first, alpha second** | Limits draw-down before you even look at the edge. |
| **Tight position sizing & draw-down caps** | Prevents a single toxic component from blowing the whole portfolio. |
| **Diversification across low-correlation "sleeves"** | Crypto markets are highly correlated; you need orthogonal signals (e.g., funding-rate-arb vs. volatility-reversion). |
| **Production gates & lifecycle management** | Strategies must pass a **minimum-sample, post-cost expectancy** test before they ever go live. |
| **Freshness SLA & signal decay monitoring** | Stale signals are dropped automatically. |
| **Multi-system consensus + hard-RR sanity checks** | A pick must be corroborated by >=2 independent systems and meet a minimum RR (e.g., 1.5) before being sent to Discord. |
| **Robust data pipelines & post-trade attribution** | Guarantees that the WR/expectancy you see is the *real* edge, not a data-bug. |
| **Separate "core" vs. "incubator" books** | Core holds only proven components (high-RR, positive expectancy). Incubator runs everything else at tiny size or paper-only, feeding the pipeline for future promotion. |

---

## 3. Pragmatic Blueprint

### 3.1 Core-Book / Incubator Split

| Book | Inclusion criteria | Typical weight |
|------|-------------------|----------------|
| **Core** | Proven components (whitelist), `funding_carry` family (only ELITE variants), any Alpha component with **RR >= 1.5** *and* **post-cost expectancy > 0**, short-only for Alpha (until long side recovers) | 70-85 % of capital |
| **Incubator** | All other components (including low-frequency Alpha, EMA-crossover, Bollinger-squeeze) | 15-30 % of capital, **paper-only** for the first 48 h, then tiny real-size (<= 0.5 % of Core) |

### 3.2 Signal-Safety Gates

| Gate | Rule | Effect |
|------|------|--------|
| **RR Gate** | Only forward a pick if `RR >= 1.5` (or 1.4 for Mercury) | Removes low-RR noise; raises expectancy. |
| **Freshness SLA** | Drop any signal older than **15 min** (or the last scan interval) | Guarantees the market still fits the trigger. |
| **Consensus Gate** | Require **>= 2 unique systems** for a "master" pick. | Cuts single-system master picks. |
| **Direction Gate** | Enforce **short-only** for Alpha strategies that have a negative long expectancy. | Stops the long-side drag. |
| **Risk-Reward Sanity** | If `RR < 1.0` -> auto-reject; if `RR >= 2.0` -> boost confidence score. | Aligns with the "high-RR" edge. |

### 3.3 Position-Sizing & Draw-Down Controls

* **Fixed fractional sizing** - 2 % of equity per Core pick, 0.5 % per Incubator pick.
* **Per-component max-DD** - stop adding exposure to a component once its draw-down > 5 % of allocated capital.
* **Portfolio-wide max-DD** - hard stop at 10 % equity loss (liquidate all positions, pause the router for 30 min).

### 3.4 Data-Quality & Attribution

1. **Normalize PnL units** - store everything in a single base currency (e.g., USDT) before aggregating.
2. **Add a "status" field** (`closed`, `canceled`, `stale`) and enforce it in `closed_picks.json`.
3. **Post-trade attribution script** - run after every market-close to recompute WR/expectancy per component.

### 3.5 Weekly PM-Style Dashboard (what to monitor)

| Metric | Frequency | Alert condition |
|--------|-----------|-----------------|
| **Component expectancy** | Weekly | < 0 % -> demote to Incubator or kill |
| **WR** | Weekly | < 30 % -> demote |
| **Max DD** | Weekly | > 5 % of component allocation -> demote |
| **Turnover** | Weekly | > 30 % of component allocation -> review |
| **Slippage drift** | Weekly | > 0.2 % per trade -> tighten RR gate |
| **Regime-decay** | Real-time | If regime flag flips -> pause component until next confirmation |

### 3.6 Code-Level Changes (quick wins)

| File | Change | Reason |
|------|--------|--------|
| `config.py` / `risk_engine.py` | Add `RR_MIN = 1.5` | Enforce the RR gate globally. |
| `fc_crypto_pro.py` | Filter through `core_whitelist.json` + consensus gate (`>=2 systems`). | Only robust signals reach Discord. |
| `auto_tuner.py` / `scanner.py` | Add short-only flag for Alpha strategies with `WR_long < 30%`. | Stops long-side drain. |
| `picks_router.py` | Split routing into `core_book` vs. `incubator_book`. | Implements Core/Incubator split. |
| `aggregator_fixed.py` | Remove raw manual sender path or force through gating logic. | Eliminates back-door. |
| `send_top_picks_now.py` | Add RR >= 1.5 sanity check. | Prevents low-RR noise. |

---

## 4. How to Keep the "Edge" Alive While Staying Safe

| Action | Why it matters | How to test |
|--------|----------------|------------|
| **Loosen thresholds on dormant Alpha strategies** (e.g., RSI-divergence from 3-sigma to 2-sigma) | Increases trade frequency for statistical validation. | Back-test last 30 days; require 10+ trades and post-cost expectancy > 0. |
| **Add "regime-aware" filter** (e.g., only fire `hurst_regime_adaptive` when Hurst > 0.6) | Prevents operating in a regime where edge disappears. | Use existing `regime_state.json` to gate; monitor weekly. |
| **Introduce "vol-adjusted position size"** (scale by `1/sigma_price`) | Reduces slippage when volatility spikes. | Simulate on last 100 trades. |
| **Run Monte-Carlo "walk-forward" on Core book only** | Realistic view of tail risk for max-DD limits. | Use `closed_picks.json`; run 10,000 paths. |
| **Create "signal-decay" metric** (retire component if no trigger > 7 days) | Guarantees no stale edges. | Add `last_trigger_ts` field; daily cron to prune. |

---

## 5. Data & Feature Foundations (Deep Dive)

| Technique | Why it matters for crypto | Typical implementation |
|-----------|--------------------------|------------------------|
| **High-frequency, clean, adjusted price series** | Crypto runs 24/7, has micro-structure quirks. | Pull tick-by-tick from multiple exchanges; apply mid-price reconstruction, trade-size weighting, exchange-level fee normalization. Store in time-series DB. |
| **Feature engineering pipelines** | Raw price alone is noisy; need signals surviving regime shifts. | Technical factors (MA, BB, RSI, MACD, ADX, volume-profile, funding-rate, OI, on-chain). Stat-arb factors (cointegration, spread z-scores, Kalman-filter hedges). Macro-sentiment (social, Google Trends, CME term-structure). Regime-detection (Hurst, GARCH, k-means). |
| **Label-generation & target design** | Ground truth must reflect true economic payoff after costs. | Forward-return over pre-specified horizon. Risk-adjusted return. Binary win/loss for classification + continuous for regression. |
| **Transaction-cost modeling (TCM)** | Crypto slippage can dwarf a 1% edge. | `TC = a + b*sqrt(size/ADV) + c*spread` per exchange. Calibrate daily. |
| **Data-quality & outlier handling** | Bad ticks, outages, flash-crashes poison models. | Rule-based filters (>10 sigma jumps, zero-volume). Imputation. Versioned data lake with SHA-256 hashes. |

---

## 6. Model-Building & Validation (Deep Dive)

### 6.1 Classical Statistical / Factor-Based

| Technique | Use-case | Safeguards |
|-----------|----------|------------|
| **Linear / Ridge / Lasso regression** | Factor model (funding-rate-arb + momentum + vol-reversion). | Time-series split CV. Shrinkage. |
| **Cointegration & Pair-Trading** | BTC-ETH, spot-futures spreads. | Johansen test on rolling windows. Kalman-filter dynamic hedge. Z-score thresholds with min holding period. |
| **GARCH / EGARCH** | Forecast conditional volatility for sizing/stops. | Rolling 500-bar window. Combine with EWMA. |
| **Markov-Regime-Switching** | Detect high-vol vs low-vol states. | BIC for regime count. Minimum 12h regime duration. |

### 6.2 ML / AI Techniques

| Technique | Value | Safety |
|-----------|-------|--------|
| **Tree ensembles (XGBoost, LightGBM, CatBoost)** | Non-linear interactions; robust to missing data. | Time-series CV. Feature-importance pruning. SHAP explainability. |
| **Deep Nets (TCN, LSTM, Transformers)** | Long-range dependencies (48h funding-rate trends). | Dropout, weight decay, early-stopping, seed ensembles. |
| **Reinforcement Learning** | Dynamic position-sizing policy. | Simulated environment with slippage. Constrained RL with DD penalty. Offline evaluation before live. |
| **Unsupervised clustering / Auto-encoders** | Detect novel regimes, anomalies. | Periodically recompute. Use cluster as gate. |
| **Bayesian hierarchical models** | Quantify parameter uncertainty for sizing. | Posterior -> Monte-Carlo DD forecasts. Probabilistic risk budgeting. |
| **Meta-learning / AutoML** | Rapid hyper-parameter search. | Min OOS Sharpe > 1.0, max DD < 5%. Model registry. |

### 6.3 Validation & Model-Risk Controls

| Control | What | How |
|---------|------|-----|
| **Walk-forward back-test** | Mimics live trading. | 30-day train, 7-day test, daily roll. Record expectancy/Sharpe/DD per roll. |
| **Monte-Carlo & Bootstrap** | Tail-risk estimation. | Block-bootstrap (preserve autocorrelation). Synthetic shock scenarios (30% BTC drop). |
| **Paper-trading period** | OOS validation. | 30 days minimum before real capital. |
| **Feature/label drift monitoring** | Detect relationship changes. | KS-distance. Auto retrain or pause on threshold breach. |
| **Explainability & audit** | Investor transparency. | SHAP snapshots per trade. Tamper-proof append-only log with hash chain. |
| **Model registry** | Reproducibility. | MLflow or Git-backed. Code + hyperparams + data hash + metrics per version. |

---

## 7. Risk-Budgeting, Governance & Monitoring (Deep Dive)

| Pillar | Technique | Outcome |
|--------|-----------|---------|
| **Capital allocation** | Risk-budgeting (fixed % of portfolio vol per sleeve). Fractional Kelly. | Predictable volatility; no single component dominates DD. |
| **Portfolio DD limits** | Hard stop at 8% from peak -> liquidate + pause 30 min. | Worst-case loss bound for investors. |
| **Diversification** | PCA on factor returns; max eigenvalue < 0.5 for core. | Reduced tail-risk, improved Sharpe. |
| **Execution controls** | Smart-order routing; TWAP/VWAP; multi-exchange. | Minimizes market impact and slippage. |
| **Operational monitoring** | SLA dashboards (latency < 200ms, freshness < 5s). Circuit-breaker on 30s feed stall. | Prevents stale-signal catastrophes. |
| **Governance (MRM)** | Model-risk committee reviews: data provenance, backtest methodology, stress-test, documentation. | Formal audit trail for regulators/investors. |
| **Transparency** | Weekly performance attribution (by factor/regime/exchange). Monthly risk-budget utilization. | Clear quantitative evidence. |
| **Compliance** | KYC/AML, transaction-level audit, privacy-by-design. | Meets mutual-fund-style legal requirements. |

---

## 8. Sample Workflow (End-to-End)

1. **Data Ingestion** (tick-level -> cleaned -> feature store)
2. **Feature Generation** (technical + on-chain + macro)
3. **Regime Detector** (Hurst + clustering) -> regime ID per bar
4. **Model Ensemble** (tree-based factor + cointegration spread + RL-policy) -> signal + confidence + RR
5. **Signal Gate** (RR >= 1.5 AND >= 2 models AND freshness < 15 min -> pass; else Incubator)
6. **Risk-Budget Allocation** (fractional Kelly, capped 2% Core)
7. **Smart-Order Router** (multi-exchange, monitor slippage)
8. **Post-Trade Attribution** (update closed_picks, recompute metrics, weekly PM dashboard)
9. **Model-Risk Review** (monthly; expectancy < 0 -> demote/kill)

---

## 9. Investor-Ready Checklist

| Item | How to prove |
|------|-------------|
| **Statistically significant edge** | OOS expectancy > 0, Sharpe > 1.0, max-DD < 5%, 30-day paper period. |
| **Robust TCM** | Published calibration report (cost vs size & exchange). |
| **Risk-budget transparency** | Allocation table + DD cap policy. |
| **Model governance** | Registry with versioned code, data hash, sign-off minutes. |
| **Explainability** | SHAP-based explanation per executed trade. |
| **Regime awareness** | Regime-heatmap + auto-pause in unknown regimes. |
| **Operational reliability** | SLA: latency < 200ms, freshness < 15 min, zero-downtime last quarter. |
| **Independent audit** | Third-party backtest replication + certification. |
| **Reporting cadence** | Weekly performance, monthly deep-dive, quarterly risk-budget review. |

---

*End of feedback archive. This document should be reviewed alongside the action items being implemented in the codebase.*
