# Crypto Prediction Strategy Validation Plan

## Executive Summary

This plan provides a systematic, data-driven roadmap to rigorously validate our crypto prediction strategy against the \"devil's advocate\" criteria. The goal is to demonstrate a genuine, robust edge beyond survivorship bias or market beta. We leverage the existing [`alpha_engine`](alpha_engine/) codebase (e.g., [`crypto_strategies.py`](alpha_engine/crypto_strategies.py), [`elite_scorer.py`](alpha_engine/elite_scorer.py), audit tools) for execution.

**Target Timeline:** 1-2 weeks, assuming daily backtest iterations.

**Success Metrics:** All 6 criteria met → Grade upgrade.

**Key Assumptions:**
- Access to historical data via [`coinalyze_client.py`](alpha_engine/coinalyze_client.py), CoinMetrics, etc.
- ML prediction scores from [`elite_scorer.py`](alpha_engine/elite_scorer.py) or similar.
- Backtests use walk-forward optimization (WFO) or out-of-sample (OOS) periods.

## Current Baseline Assessment

**Immediate Action:** Run comprehensive audits to establish starting point.
```
cd alpha_engine && python audit_comprehensive_report.py --crypto --ml-scores
cd alpha_engine && python battle_test_rigorous.py --symbols crypto --min-trades 30
```
- Review outputs for trade counts, p-values, DD/Calmar, regime splits.
- Expected Gaps (from criteria): ML corr=0, shorts weak, regimes unbalanced.

## Criterion-by-Criterion Validation Plan

### 1. 30+ Trades Per Strategy (Sample Size)
**Goal:** Minimum viable n for edge claims.

**Steps:**
1. Extend backtest horizons: 2020-present (bull+bear+bull cycles) using [`backtest_multi_strategy.py`](alpha_engine/backtest_multi_strategy.py).
2. Dynamic universe: Top 50-100 crypto by volume/liquidity via [`dynamic_universe.py`](alpha_engine/dynamic_universe.py).
3. Tune entry thresholds conservatively: Reduce lookback if n<30, but validate via deflated Sharpe [`deflated_sharpe.py`](alpha_engine/deflated_sharpe.py).
4. **Validation Script:** Modify [`backtest_new_strategies.py`](alpha_engine/backtest_new_strategies.py) to filter `trades >= 30`.
5. **Metric:** All promoted strategies pass.

**Timeline:** Day 1.

### 2. 3+ Strategies with p<0.05 at n>30 (Statistical Significance)
**Goal:** Non-random outperformance.

**Steps:**
1. Bootstrap returns (1000 resamples) per strategy using scipy.stats.bootstrap.
2. Compute p-value vs. buy-hold benchmark (BTCUSD).
3. Ensemble: Combine 3+ winners from crypto variants (e.g., momentum, mean-reversion, ML-enhanced).
4. **New Script:** `stats_test_crypto.py`
   ```python
   from scipy.stats import bootstrap
   # ... load backtest results
   pvals = [bootstrap(trades, np.mean).pvalue for trades in strategy_returns]
   winners = [s for s, p in zip(strats, pvals) if p < 0.05 and len(trades) > 30]
   ```
5. **Target:** >=3 strategies (e.g., cyclic_momentum + ML_filter + basis_carry).

**Timeline:** Days 1-2.

### 3. Positive ML Score Correlation with Outcomes (Fix Current Zero)
**Goal:** Predictions predict PnL.

**Steps:**
1. Extract ML scores from [`elite_scorer.py`](alpha_engine/elite_scorer.py) vs. realized trade PnL.
2. Compute correlations: Spearman (rank), Pearson (linear) on holdout set.
3. If zero: 
   - Retrain features (add regime, vol, sentiment via [`binance_sentiment.py`](alpha_engine/binance_sentiment.py)).
   - Threshold optimization via [`entry_optimizer.py`](alpha_engine/entry_optimizer.py).
4. **Validation:** `corr = scipy.stats.spearmanr(ml_scores, pnls)[0] > 0.1` (p<0.05).
5. **Script:** Enhance [`compute_backtest_forward_correlation.py`](alpha_engine/compute_backtest_forward_correlation.py) for ML.

**Timeline:** Days 2-4.

### 4. Max Drawdown <30%, Calmar >1.0
**Goal:** Risk-adjusted viability.

**Steps:**
1. Compute on full OOS: Max DD (peak-to-trough), Calmar = CAGR / |Max DD|.
2. Dynamic position sizing: [`conformal_sizing.py`](alpha_engine/conformal_sizing.py) or volatility targeting.
3. Stress test: 2022 bear market subset.
4. **Script:** Integrate into [`audit_pnl.py`](alpha_engine/audit_pnl.py).
5. **Target:** DD<30%, Calmar>1.0 across portfolio.

**Timeline:** Day 3.

### 5. Profitable in Bull AND Bear Regimes
**Goal:** Regime-agnostic.

**Steps:**
1. Define regimes: BTC 200-day SMA (above=bull, below=bear) or altseason index [`altcoin_season_detector.py`](alpha_engine/altcoin_season_detector.py).
2. Split backtests: Compute Sharpe/PnL per regime.
3. Balance: Add regime filters (e.g., short-only in bear).
4. **Validation:** Positive expectancy both regimes (min Sharpe 0.5).
5. **Script:** `regime_split_backtest.py` using bocpd changepoint [`bocpd.py`](alpha_engine/bocpd.py).

**Timeline:** Days 4-5.

### 6. Profitable Short Trades (Not Just Long Crypto Beta)
**Goal:** True skill, not momentum.

**Steps:**
1. Force short generation: Invert signals or add contrarian modules [`cascade_contrarian.py`](alpha_engine/cascade_contrarian.py).
2. Filter: Shorts only on high-confidence ML bear scores.
3. Metrics: Winrate>50%, PF>1.0 for shorts.
4. **Validation:** Shorts contribute >20% total PnL positively.
5. **Script:** `short_trade_audit.py` from [`audit_trade_patterns.py`](analysis_trade_patterns.py).

**Timeline:** Days 5-6.

## Execution Roadmap

| Phase | Tasks | Tools/Scripts | Owner | Due |
|-------|-------|---------------|-------|-----|
| 0 | Baseline audits | audit_*.py | Auto | Day 0 |
| 1 | Sample size + Stats | backtest_*.py, stats_test_crypto.py | Kilo | Day 2 |
| 2 | ML Corr Fix | elite_scorer.py, compute_backtest_forward_correlation.py | ML Team | Day 4 |
| 3 | Risk + Regimes | audit_pnl.py, regime_split_backtest.py | Risk | Day 5 |
| 4 | Shorts Validation | short_trade_audit.py | Quant | Day 6 |
| 5 | Full Ensemble Test | confluence_pipeline.py | All | Day 7 |
| 6 | Report & Certify | audit_final_summary.py | Review | Day 8 |

## Monitoring & Iteration
- Daily: Run [`alpha_engine_winning_monitor.py`](alpha_engine/alpha_engine_winning_monitor.py).
- Git commits per criterion.
- If stuck: AB test variants via ab_testing_agent.

## Risks & Mitigations
- Data quality: Cross-verify with multiple sources.
- Overfitting: Mandatory WFO/OOS.
- Compute: Batch via [`batch2_runner.py`](alpha_engine/batch2_runner.py).

## Next Action
Run baseline: `python alpha_engine/audit_comprehensive_report.py --crypto`

**Upon completion:** Update [`AUDIT_REPORT_2026-03-19.md`](AUDIT_REPORT_2026-03-06.md) with proofs.