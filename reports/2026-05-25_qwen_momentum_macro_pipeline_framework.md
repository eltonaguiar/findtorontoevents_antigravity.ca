# Qwen — Momentum + Macro Signal Pipeline Framework, Risk-Budgeting Pitfalls, OOS Walk-Forward Validation

**Date:** 2026-05-25 (Qwen Code session)
**Type:** Methodology reference doc (not a one-off pick set)
**Linked enhancements:**
- `ENHANCEMENT_OVERALL: Adopt Qwen 7-stage momentum+macro+regime pipeline as alpha_engine reference architecture`
- `ENHANCEMENT_OVERALL: Enforce purged-k-fold + walk-forward validation as new-strategy admission gate` (kilocode/nemotron, complementary)
- `ENHANCEMENT_OVERALL: Add momentum + macro composite signal template to alpha_engine` (kilocode pseudo-code, narrower)

---

## 1. Momentum-Plus-Macro Signal Pipeline (7 stages)

| Stage | What it does | Code module |
|---|---|---|
| **0. Config** | Central tunable params: universe, look-back windows, scoring weights, risk limits, cost assumptions | `PipelineConfig` dataclass |
| **1. Data ingestion** | Clean OHLCV per symbol + macro series; forward-fill few missing bars; drop zero-volume rows | `ingest_market_data`, `ingest_macro_data` |
| **2. Feature engineering** | **Momentum:** 21/63/126-day returns, vol-scaled momentum, pull-back filter, relative strength vs SPY. **Macro:** transform raw macro into tail tags (dovish-rate, inflation-trend, credit-stress, dollar-strength, low-VIX regime), build z-score-normalized composite macro score | `compute_momentum_features`, `compute_macro_features` |
| **3. Regime detection** | HMM-like proxy: rolling Sharpe → Bear / Sideways / Bull | `detect_regime` |
| **4. Signal generation** | Per-row composite score (momentum z + regime boost + macro tailwind + cross-sectional rank) using config weights; emit LONG/SHORT + filter low-rank | `generate_signals` |
| **5. Position sizing** | Two-stage: (1) inverse-vol parity so each leg contributes equal risk, (2) capped Kelly fraction (±25% of signal) + global max-position cap | `size_positions` |
| **6. Portfolio construction** | CVaR-aware constrained optimisation (min vol) with constraints on leverage, per-asset cap, sector exposure | `construct_portfolio` |
| **7. Execution queue** | Target weights → concrete orders, slippage + cost model, priority by weight change | `queue_orders` |

**Reference flow:**

```python
cfg      = PipelineConfig(universe_symbols=[...])
prices   = ingest_market_data(cfg.universe_symbols, "2020-01-01", "2026-05-25")
macro    = ingest_macro_data("2020-01-01", "2026-05-25")
signals  = generate_signals(cfg, prices, macro)
weights  = size_positions(signals, get_vols(prices), cfg)
opt_wt   = construct_portfolio(weights, get_cov_matrix(prices), cfg)
orders   = queue_orders(opt_wt, current_holdings, latest_prices, cfg)
```

All steps deterministic, modular, swappable for more sophisticated models (true HMM, ML score, alt optimisers).

---

## 2. Risk-Budgeting Pitfalls (8 traps to avoid)

| # | Pitfall | What breaks | Fix |
|---|---|---|---|
| 1 | Assuming covariance stationarity | Shock (e.g., Mar 2020) breaks "equal-risk" allocation | Time-decayed covariances (exp-decay) + Ledoit-Wolf shrinkage; recompute often |
| 2 | Ignoring transaction-cost feedback | High-turnover signals eat the profit | Model slippage + commissions IN the optimiser; penalise turnover |
| 3 | Nominal-$ vs vol-equivalent sizing | 1 M$ gold ≠ 1 M$ BTC — hidden concentration | Express budgets as % portfolio vol; `target_weight = target_risk × portfolio_vol / asset_vol` |
| 4 | Hidden sector/country concentration | Multiple "different" US-tech stocks = single sector | Sector caps, cluster by correlation, cap risk per cluster |
| 5 | Over-fit risk-budget params | Few-month tune yields fake Sharpe that collapses | Freeze params ≥ 2 quarters; Monte-Carlo perturbation stress-test |
| 6 | Confusing ex-ante vs ex-post risk | Predicted 8% DD turns into 14% realised | Continuously compare realised vs predicted vol; widen buffers if realised > predicted |
| 7 | Pure Kelly without caps | Kelly says 23%, a few bad weeks wipe equity | Fractional Kelly (~25%) + hard max-position cap (~10%) |
| 8 | Rebalancing-induced timing risk | Large monthly rebal during flash crash moves market against you | Drift-triggered rebal (e.g., > 1.5× expected drift); VWAP / slice large orders |

---

## 3. Robust OOS Back-Testing + Walk-Forward Validation

### Step 1 — Train/test definition
- **No overlap** between train + test windows.
- Rolling **expanding window**: each fold trains on all data up to t, tests on next h days.

### Step 2 — Walk-forward implementation
1. Split timeline into n roughly-equal test intervals.
2. Per fold:
   - Build signals only from data **before** the test start.
   - Verify no look-ahead (`_assert_no_lookahead`).
   - Run strategy on test slice; collect Sharpe / WR / max-DD.

### Step 3 — Statistical significance
- 1-sample t-test on OOS Sharpe.
- Binomial test on WR > 50%.
- Max-DD threshold (e.g., < 20%).
- Bonferroni correction for multiple-strategy comparisons.

### Step 4 — Stability diagnostics
- CoV of Sharpe across folds (target < 0.5).
- Edge-decay slope from rolling 3-fold Sharpe — steep negative = over-fit.
- Regime-specific variance (bull/bear/sideways).
- Parameter sensitivity (±20% shifts).
- Permutation test (random shuffle to assess significance).

### Step 5 — Deployment gate (must-pass checklist)

| Gate | Target |
|---|---|
| OOS Sharpe ≥ 0.50 / yr | ☐ |
| Max DD < 20% | ☐ |
| Win-rate binomial p < 0.05 | ☐ |
| Sharpe CoV < 0.5 | ☐ |
| Edge-decay slope > −0.05 | ☐ |
| Permutation p < 0.10 | ☐ |
| Net Sharpe after costs > 0.30 | ☐ |
| Zero leakage flags | ☐ |
| Parameter sweep stability (< 15% PnL loss) | ☐ |
| Stress-test (e.g., Mar 2020) DD ≤ 30% | ☐ |

If any gate fails: fix underlying issue OR accept reduced sizing/position cap before going live.

---

## TL;DR

- Pipeline = raw market+macro → composite score → rank → size by risk → optimise → orders.
- Pitfalls mostly = hidden assumptions (stationary cov, ignoring costs, $-not-vol units) + over-fit.
- Walk-forward + leakage guards + statistical tests + stability diagnostics = the deployment gate.

## Action items in this repo

1. **Refactor `alpha_engine` to the 7-stage modular layout above** (ENHANCEMENT_OVERALL). Current code mixes stages — separating them allows swapping any single stage (e.g., HMM regime for the rolling-Sharpe proxy).
2. **Wire the deployment-gate checklist into CI** so no strategy promotes from shadow → probation without all 10 gates green (extends the kilocode/nemotron purged-k-fold proposal).
3. **Implement CVaR-aware portfolio constructor** as a replacement for the current rank-and-fill logic.
4. **Add turnover penalty to the optimiser** to operationalise pitfall #2.

These all land as separate ENHANCEMENT_OVERALL rows linking back to this doc.
