# pypbo Audit — Full Usage Inventory (2026-04-20)

## 1. Mercury's Error

Mercury's workflow described `pypbo` as **"Python Portfolio Bayesian Optimisation"**, recommending it to wrap the pipeline in a Bayesian optimiser that maximises Sharpe/Sortino/Calmar. **This is wrong.** The acronym is **P**robability of **B**acktest **O**verfitting. The real library is [`esvhd/pypbo`](https://github.com/esvhd/pypbo), a Python implementation of the Bailey, Borwein, Lopez de Prado, Zhu framework for *detecting* overfitting and *deflating* inflated Sharpe ratios — it does not optimise anything. It is a **validation / haircut layer**, not a hyperparameter search loop.

(The collision Mercury may have tripped on: there is a second unrelated `bobmoretti/pypbo` that packages Bohemia Interactive PBO game files — also not a Bayesian optimiser.)

## 2. Full Function Inventory (esvhd/pypbo)

Top-level `pypbo` package:

| Callable | Purpose |
|---|---|
| `pypbo.pbo(rtns_df, S, metric_func, threshold, n_jobs, plot, verbose, hist)` | PBO via CSCV (Combinatorial Symmetric Cross-Validation). Returns PBO probability, performance-degradation slope, prob. of loss OOS, stochastic-dominance plots. |
| `pypbo.psr(sharpe, T, skew, kurt, sr_benchmark=0)` | Probabilistic Sharpe Ratio — P(true SR > benchmark) given sample length, skew, kurtosis. |
| `pypbo.dsr(sharpe, T, skew, kurt, N_trials, var_trials_sr)` | Deflated Sharpe Ratio — PSR deflated for multiple testing across `N_trials`. |
| `pypbo.minTRL(sharpe, skew, kurt, sr_benchmark, prob)` | Minimum Track Record Length — observations needed for SR significance. |
| `pypbo.minBTL(N_trials, prob, alpha)` | Minimum Backtest Length — years needed before best-of-N SR is trustworthy. |

`pypbo.perf` submodule:

| Callable | Purpose |
|---|---|
| `perf.sharpe_iid(returns, bench, factor, log)` | Annualised IID Sharpe. |
| `perf.sharpe_non_iid(returns, bench, factor, q)` | Autocorrelation-adjusted Sharpe (Lo 2002). |
| `perf.sortino_iid` / `sortino_non_iid` | Sortino variants. |
| `perf.omega(returns, target)` | Omega ratio. |
| `perf.annualized_pct_return`, `annualized_log_return` | Return helpers used as `metric_func` for `pbo()`. |
| `perf.stochastic_dominance` helpers (FSD / SSD tests) | Rank-ordering strategies under dominance criteria. |

That is the complete public surface — there is no optimiser, no sampler, no acquisition function.

## 3. How We Apply Each — Concrete Repo Data Paths

Working dir: `c:\findtorontoevents_antigravity.ca`.

| Function | Input in this repo | Decision it supports | Asset classes |
|---|---|---|---|
| `pbo()` | Matrix of per-mutation daily returns from `alpha_engine/run_massive_mutations.py` and `alpha_engine/data/expansion_promotion_ranked.json`; closed-pick pnl series from `alpha_engine/data/closed_picks.archive.jsonl` pivoted per strategy. | Kill/ship gate for a whole *family* of mutations before any promotion. Wire into `alpha_engine/validation/promotion_gate.py`. | ALL (CRYPTO, EQUITY, ETF, FOREX, COMMODITY, BOND) |
| `psr()` | Per-strategy closed-pick return series (`closed_picks_fast.json`, `battle_test_picks.json`). | "Is this single strategy's Sharpe real?" — replace the naive Sharpe gate in `alpha_engine/validation/sharpe_metrics.py` and `cross_aggregation/dsr_gate.py`. | ALL |
| `dsr()` | Same returns + `N_trials` from `tools/experiment_log.py` (count of mutations/feeds tested this cycle). | Ship / paper-flag / reject at the *portfolio discovery* level. Primary input to `tools/deflated_sharpe_per_feed.py` and `alpha_engine/dsr_pick_filter.py` (currently uses a custom DSR — swap for reference impl). | ALL |
| `minTRL()` | Each feed's observed skew/kurt (compute in `tools/deflated_sharpe.py`). | "How many more closed picks before this feed earns a verdict?" — feeds tagged *insufficient-history* in `updates/` instead of falsely shipped. | High-turnover (CRYPTO, FOREX) benefit most; BOND rarely clears. |
| `minBTL()` | `S` = number of mutations in a sweep (read from `alpha_engine/MASSIVE_MUTATION_PLAN.md` runs). | Sanity check before any mutation cycle: if BTL > available history, abort sweep. Add to `alpha_engine/run_massive_mutations.py` preflight. | ALL — critical for EQUITY/ETF where daily bars are sparse. |
| `perf.sharpe_non_iid` | Overlapping-return series (our pick holds overlap by design). | Replace naive Sharpe everywhere we currently assume IID. | CRYPTO 24/7 especially. |
| `perf.stochastic_dominance` | Pairwise strategy returns. | Rank competing feeds without relying on a single metric — input to `alpha_engine/incubator/ranker.py`. | ALL |

## 4. What Mercury Actually Wanted — Correct Library

If we want **Bayesian hyperparameter optimisation of strategy params** (lookback, threshold, stop multiple, etc.), use:

- **[Optuna](https://optuna.org/)** — TPE/GP samplers, pruning, distributed, persistent storage. Best fit: wraps `alpha_engine/vectorized_backtest.py` with `study.optimize(objective)` where objective returns PSR (not raw Sharpe).
- **scikit-optimize (`skopt`)** — GP-based, smaller API, fine for ≤20 params.
- **Hyperopt** — older TPE, lower activity.

**Correct pattern:** Optuna searches params → each trial's returns fed into `pypbo.psr`/`pypbo.dsr` as the *objective* → after the study, run `pypbo.pbo` across all trial equity curves to confirm the winner isn't an artifact. The two libraries are complements, not substitutes.

## 5. PBO vs DSR Decision Matrix

| Question | Use | Why |
|---|---|---|
| "Is the *best* of N backtested strategies genuinely OOS-robust?" | **PBO** | CSCV directly estimates P(best IS → below-median OOS). |
| "Does this *one* strategy's Sharpe survive multiple-testing haircut?" | **DSR** | Closed-form deflation by `N_trials`, skew, kurt. |
| "Do we have enough history to judge at all?" | **minTRL / minBTL** | Length-only prerequisites. |
| "Is Sharpe even significant ignoring selection bias?" | **PSR** | Single-strategy, no trial count. |

Rule of thumb we should adopt: **PSR ≥ 0.95 AND DSR ≥ 0.95 AND PBO ≤ 0.5** before `promote_strategy.py` flips a feed to `SHIP`. Paper-flag if any one fails; reject if two fail.

## 6. Related Libraries Mercury Missed

- **[rubenbriones/Probabilistic-Sharpe-Ratio](https://github.com/rubenbriones/Probabilistic-Sharpe-Ratio)** — Lopez de Prado reference PSR/DSR (known small bug in Python version; R is cleaner). Use as cross-check oracle.
- **`mlfinlab.backtest_statistics`** (pre-license-change fork, e.g. Hudson & Thames mirrors) — PSR, DSR, **Haircut Sharpe** (Harvey & Liu), **Profit Hurdle**, CSCV. Haircut Sharpe is a valuable addition we don't yet run.
- **`pyfolio-reloaded`** — tearsheets with PSR baked in.
- **`quantstats`** — not statistically rigorous but useful for per-pick diagnostics.
- **`arch`** (Sheppard) — bootstrap + MCS (Model Confidence Set) for picking a set of non-dominated strategies; better than single-metric ranking.
- **`SPA` / Reality Check / Hansen's SPA test** (in `arch`) — formal multiple-testing on Sharpe across strategies.
- **AlphaSharpe (2025 arXiv)** — LLM-evolved risk-adjusted metrics; experimental, worth tracking.

Net: keep our `alpha_engine/deflated_sharpe.py` custom impl, but add `pypbo` as a dependency and adopt `pbo()` + `minBTL()` which we currently do not run. Pair with Optuna for the actual hyperparameter search Mercury was gesturing at.
