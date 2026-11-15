# Methods catalogue — what exists, where, and whether it ever gated a decision

Counts are **files matching the signature** from the 2026-11-15 scan (25,000-file cap,
200 KB/file, `WIRED_IN`/`archive`/`worktrees` excluded). They measure *mentions*, not quality;
the "gates a decision?" column is the one that matters.

## Statistical machinery

| Method | Files | Implementation | Gates a live decision? |
|---|---:|---|---|
| Deflated Sharpe / PSR | 756 | `alpha_engine/deflated_sharpe.py`, `probabilistic_sharpe_engine.py`, `alpha_engine/rigorous_backtest_harness.py` | **yes** — EAGLE-6 reads `tools/deflated_sharpe_results.json` (27 of 52 strategies in the noise set) |
| PBO / CSCV | 324 | **not on main**; exists only in `.claude/worktrees/cluster-a-fix-2026-06-21/tools/pbo_cscv.py` | no |
| White's Reality Check / SPA | 315 | same — worktree only; reports on main | no |
| Multiple-testing correction (BH/Bonferroni) | 315 | `strategy-funnel-hourly.yml:86` exposes `survived_bonferroni` | yes, in the funnel report |
| Walk-forward | 1,853 | `alpha_engine/walkforward_validator.py` | partially |
| CPCV / purged CV | 348 | `rigorous_backtest_harness.py` | no |
| Bootstrap / Monte Carlo / permutation | 1,021 | `probabilistic_sharpe_engine.py` (10k sims), `alpha_engine/validation/monte_carlo.py` | no |
| Significance / Wilson / CI | 3,777 | `tools/pick_excess.py`, `wilson_lower()` in `forward_tracker.py` | yes (forward ledger) |

Read the first row against the second: DSR is wired, PBO and Reality Check are not. The
strongest anti-overfitting gates are the ones missing from the live path.

## ML

| Family | Files | Notes |
|---|---:|---|
| Tree ensembles (RF/XGB/LGBM/CatBoost) | 938 | the workhorse; `ml_battleground/`, `mercury2/`, `crypto_signal_engine/` |
| Time series (ARIMA/GARCH/cointegration) | 782 | `alpha_engine/cointegration_pairs.py`, `arch` in requirements |
| State space (HMM/Kalman/Bayesian) | 700 | `regime_terminal/` (hmmlearn), `baby_strategies/kalman_mean_reversion.py` |
| Classical (SVM/PCA/clustering) | 281 | `alpha_engine/pca_factor_model.py` |
| Deep (LSTM/transformer) | 149 | mostly notebooks/prose; no live gate found |
| RL | 105 | experiments only |

## Backtest / execution / data

| Family | Files | Notes |
|---|---:|---|
| Backtest framework (vectorbt/backtrader/zipline/QC) | **51** | almost all bespoke loops; no single engine |
| Parameter sweep (grid/optuna/hyperopt) | 98 | low, given 3,000+ configurations claimed |
| Costs (slippage/commission/spread/funding) | 6,098 | mentioned constantly, modelled rarely (`alpha_engine/transaction_costs.py`) |
| Paper / forward test | 2,107 | `state/forward_test/`, `tools/forward_tracker.py` |
| Live execution | 2,061 | mostly API keys and order builders, not verified fills |
| Market data (yfinance/ccxt/OHLCV) | 3,548 | `requirements.txt`: yfinance, pandas-datareader, fredapi |
| Alternative data (on-chain/COT/OI/sentiment) | 4,336 | `copy_trader_intel/`, `alpha_engine/funding_rate_arb.py` |
| Regime | **8,609** | the most-mentioned concept in the repo |

## Dependencies actually installed (`requirements.txt`, 16 entries)

pandas, numpy, requests, python-dotenv, pyarrow, scikit-learn, scipy, arch, fredapi,
pandas-datareader, yfinance, pymysql, mysql-connector-python, redis, beautifulsoup4, PyYAML

`package.json`: 3 deps, 3 devDeps.

**Nothing exotic is missing.** The gap is not libraries; `vectorbt`/`backtrader` are absent, and
that absence matches the 51-file framework count — there was never a single engine to hold the
others to one set of fill and cost assumptions.

## Consequences for new work

1. Use `alpha_engine/rigorous_backtest_harness.py` (purged k-fold + DSR + PBO hooks) rather
   than a new loop. It is the closest thing to a standard engine on main.
2. If PBO or Reality Check is needed, **port it back from the worktree first** — citing a
   number from code that is not on the main path is not reproducible.
3. Any new cost model must beat `alpha_engine/transaction_costs.py`, not a fresh assumption.
4. Regime conditioning is already mentioned in 8,609 files; a new regime feature is not novel.
   A *regime-split report on the closed ledger* is, and is cheap.
