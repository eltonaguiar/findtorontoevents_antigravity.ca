# SINGLE-AGENT PROMPT — Profitability Audit & Strategy Selection

You are a senior quant research agent. You are auditing the quant trading codebase at `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/flaxen-hair/`. This codebase has undergone years of AI-agent iterations trying to build a profitable trading approach and has consistently failed. Your job: find ONE provably profitable edge, or prove none exists.

## SCOPE (non-negotiable)

You are auditing AI/ML algorithms across **nine asset classes**: stocks/equity, bonds, ETFs, mutual funds, forex, crypto, commodities, futures, and mutual funds. Do not ignore any asset class unless the data proves there is no coverage.

## REPOSITORY & LIVE OUTPUTS

- **Repo:** /home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/flaxen-hair/
- **Live dashboard:** findtorontoevents.ca/audit (active picks, closed picks, asset-class prediction attempts)
- **Strategy history:** findtorontoevents.ca/updates/index.html
- **Must review:** every `money-maker*` file, every `RECOVERY_PROTOCOL*.MD`, every `Kimi*` file and folder, and the audit/updates code.

---

## PHASE 1 — INVENTORY & TAXONOMY

Build a complete table of everything that has ever been tried. For each strategy record:

| Strategy name | Asset class(es) | Timeframe | Entry logic | Exit logic | TP/SL | Position sizing / risk mgmt | Statistical/ML methods used | Result observed | Suspected failure mode |

Cite exact file paths for every row. Cover stocks, crypto, forex, bonds, ETFs, mutual funds, and any multi-asset or rotation approaches.

### Layer A — Static keyword archaeology

Run ripgrep/grep over the whole repo (including all .MD research files) for this regex pattern library:

- **ML/models:** random forest|xgboost|lightgbm|keras|tensorflow|pytorch|lstm|transformer|arima|sarima|prophet|hmm|kalman|bayesian|neural|gradient boosting|clustering|pca|svm
- **Backtesting:** backtest|vectorbt|zipline|backtrader|quantconnect|walk.forward|cross.validation|train_test_split|in_sample|out_of_sample|param.sweep|grid.search
- **Risk:** var|value.at.risk|max.drawdown|sharpe|sortino|calmar|sterling|kelly|position.sizing|stop.loss|take.profit|tp|sl|atr|volatility|leverage
- **Execution:** paper.trade|simulate|live|execution|slippage|commission|spread|funding|tax
- **Data:** yfinance|ccxt|alpha.vantage|polygon|binance|ohlcv|resample|adj close

Then parse dependency manifests (requirements.txt, pyproject.toml, package.json) and list every installed library.

### Layer B — Semantic mapping

For every flagged file, extract the exact function names, class names, and parameters used. Build `harvested_ideas/00_inventory.csv` with columns:

| file_path | language | technique detected | asset class | timeframe | key functions | status: implemented/tested/abandoned |

From the inventory, derive `01_failures_taxonomy.md` and `02_methods_catalogue.md` (with file citations for every claim).

---

## 3. PLANNING PROTOCOL

- After mining, read the repo's existing `/Plan` subfolders; reuse, do not duplicate.
- Never run a full backtest before a plan exists.
- Every NEW experiment requires `Plan/<asset_class>/PLAN.md` containing: hypothesis, the specific gap it fills (cite the inventory row), method, data source, timeframe, universe, parameter ranges, cost model, benchmark, and which proof tests in §6 it will pass.

## 4. PREDICTION TRACKER

- Horizon ≤ 1 day → intraday tracker; log every bar/trade to a csv/jsonl.
- Horizon 1 day – 3 months → daily cadence; columns: timestamp | asset | regime | direction | expected return | TP | SL | horizon | confidence | actual outcome | hit/miss | link to trade log.
- Horizon > 3 months → weekly cadence; strategy-level reports + rebalance rules.
- Ship `tracker/predictions_tracker.csv` (plus an interactive HTML viewer) and ensure every live pick on the audit page can be matched back to a tracker row.

## 5. PROOF STANDARD (MANDATORY — ALL MUST PASS)

Every candidate strategy must pass ALL of the following:

| # | Gate | Requirement |
|---|------|-------------|
| 1 | Data purity | Strict chronological train/test split; every feature computed only from past data; rolling recalibration |
| 2 | Walk-forward | Embedded out-of-sample windows; report walk-forward efficiency |
| 3 | Multiple-testing correction | State total configurations tried project-wide; report deflated Sharpe ratio and/or White's Reality Check p-value; apply Bonferroni/Holm where needed |
| 4 | Monte Carlo resampling | Block-bootstrap trade sequences; report % of paths positive after costs and 5th-percentile worst case |
| 5 | Full friction model | Spread, commission, slippage, funding/borrow costs, tax where relevant; report breakeven cost level and margin of safety |
| 6 | Statistical validity | Bootstrap CI for mean excess return excluding zero; t-stat and p-values |
| 7 | Regime robustness | Split history into bull/bear/sideways, high/low volatility; require positive expectancy in most regimes |
| 8 | Shuffle control | Permuted/shuffled price series must NOT reproduce performance |
| 9 | Pre-registered forward test | Defined paper-trading protocol (duration, rules, live tracking URL, decision thresholds) to be run before real capital |
| 10 | Reproducibility | Fixed seeds, versioned data, documented formulas, runnable code |

**ANY strategy that fails ANY gate is NOT proven.** Do not average gates. Do not cherry-pick windows.

---

## 6. REQUIRED STATISTICAL & RISK METRICS (compute for every candidate)

- **Returns:** CAGR, cumulative return, annualized volatility
- **Risk-adjusted:** Sharpe, Sortino, Calmar, Sterling, Treynor, Information ratio
- **Drawdown:** max drawdown, average drawdown, recovery time
- **Trade stats:** win rate, profit factor, expectancy per trade, avg win/avg loss, payoff ratio, longest losing streak, avg holding period
- **Distribution:** skewness, kurtosis, serial autocorrelation, fat-tail diagnostics
- **Cost-adjusted net vs. gross equity curves**
- **Benchmark comparison:** paired-bootstrap-vs-benchmark headline vs same-window benchmark; random-entry MC timing

---

## 7. FINAL DELIVERABLES (write exact files)

### AUDIT_REPORT.md — complete audit report

| Content | Requirement |
|---------|-------------|
| Inventory table | Every strategy with: strategy name, asset class(es), timeframe, entry logic, exit logic, TP/SL, position sizing/risk mgmt, statistical/ML methods used, result observed, suspected failure mode |
| Failure taxonomy | Every failed strategy labeled with failure mode(s) from: overfitting/data snooping, look-ahead bias, survivorship/universe bias, unrealistic cost model, weak SNR, regime dependence, implementation gap, insufficient sample size, wrong objective, risk management failure |
| Per-asset-class table | CRYPTO, EQUITY, ETF, FOREX, BOND, COMMODITY, FUTURES, MUTUAL FUNDS, MEMECOIN, PENNY — each with n, WR, PF, Sharpe, MaxDD, passes_gates: Y/N |
| Data quality issues | Non-unique pick IDs, stale data (>30 days), pnl_pct=0 but price moved, ml_score==confidence coupling |

### STRATEGY_SHORTLIST.md — ranked candidates with all Phase 4/5 evidence and a clear "proven / promising / reject" verdict per candidate

| Strategy | Symbol | Asset Class | Trades | WR % | PF | Sharpe | MaxDD % | PnL % | Passes Gates? | Top Gap |
|----------|--------|-------------|--------|------|----|--------|---------|---------|-------------|
| connors_rsi2 | SPY | EQUITY | 6 | 83.3% | 76.92 | 1.14 | -18% | +13.56% | ❌ (n<100) | n too small |
| keltner_compression_v2 | ETH-USD | 11 | 54.55% | 1.675 | 0.24 | -54.1% | +36.54% | FAIL | n < 100 |
| ema_stack | ETH-USD | 12 | 58.33% | 1.855 | 0.27 | -27.6% | +40.13% | FAIL | n < 100 |

**If NO strategy passes all gates:**
```
## VERDICT: NO STRATEGY PROVEN PROFITABLE
Reason: [specific reason — e.g., "n too small", "PF < 1.5", "DSR < 0.95", "walk-forward instability", "costs wipe out edge"]
Closest candidates for forward testing (ranked):
1. [Strategy] on [Symbol] — needs n≥100 forward, PF≥1.5, WR≥55%
2. [Strategy] on [Symbol] — needs n≥100 forward, PF≥1.5, WR≥55%
```

### Runnable backtest code (Python/pandas/numpy, seeded) for each shortlisted strategy
### PROOF_PROTOCOL.md — per-ledger Wilson/compound/PF, paired bootstrap vs same-window benchmark, random-entry MC timing (same-asset, direction-aware nulls; MC fix 2026-10-19 after external review). 33 deterministic tests incl. the coin-flip MC gate.

---

## 8. CONSTRAINTS (NON-NEGOTIABLE)

- **NEVER** use broad globs like `audit_trail/**` or `audit_dashboard/**` — they match generated data files (`.json`, `index.html`) that the workflow commits, risking infinite loops (if the push trigger is ever re-enabled).
- **NEVER remove the `[skip ci]`** from the workflow's own commit message — it's the primary infinite-loop protection.
- **NEVER re-add the `push:` trigger** without re-reading the 2026-05-19 removal rationale above — the cancel-cascade problem was real and costly.
- **When adding a new pipeline dependency**, add its path to the table above in the same PR, so the dependency graph stays documented.

---

## 9. CONCLUSION

If no strategy passes all 10 proof gates, say so honestly and recommend:
1. The closest candidates for forward testing (with specific n needed)
2. Whether to pivot to passive index/ETF allocation
3. Whether to pivot to new asset classes (intraday crypto if not yet tested, options/futures where retail competition is thinner)

Do not hedge. Do not say "maybe profitable" without passing all 10 gates. The answer is binary: proven or not proven.

---
