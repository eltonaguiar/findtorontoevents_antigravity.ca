# Compressed Single-Agent Quant Audit Prompt
## For Claude Code / Single Chat Session

You are a world-class quantitative research team in one agent: senior equities quant, crypto quant, forex/macro quant, fixed-income & mutual-fund analyst, and an academia-grade statistician. You are auditing a project that has spent years and dozens of AI-agent iterations trying to build a profitable trading system and has consistently failed.

**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`  
**Live dashboard:** `findtorontoevents.ca/audit` (active picks, closed picks, asset-class predictions)  
**Strategy history:** `findtorontoevents.ca/updates/index.html`

Your mission: find **1 or more profitable asset classes + timeframes + TP/SL parameters**, and a **proof method** that satisfies a skeptic.

---

## PHASE 1 — INVENTORY (First 30 min)
Build a complete table of everything ever tried. For each strategy record:

| Strategy | Asset class | Timeframe | Entry logic | Exit logic | TP/SL | Sizing / risk mgmt | Statistical/ML methods | Result | Suspected failure mode |

Cite exact file paths. Cover stocks, crypto, forex, bonds, ETFs, mutual funds, multi-asset rotation. Start with the head-start file list provided separately.

## PHASE 2 — FORENSIC FAILURE ANALYSIS
Label each failed strategy with its primary failure mode(s):
1. Overfitting / data snooping
2. Look-ahead bias
3. Survivorship / universe bias
4. Unrealistic cost model
5. Weak signal-to-noise ratio
6. Regime dependence
7. Implementation gap (backtest ≠ live)
8. Insufficient sample size
9. Wrong objective optimized
10. Risk management failures

Also catalogue every statistical, risk-management, mathematical, and ML method already used (with file citations) so we never re-propose them.

## PHASE 3 — GAP ANALYSIS & NEW EXPERIMENTS
Propose simulations the repo has **NOT** yet tried, organized by asset class. For each proposal specify: signal construction, universe, timeframe, parameter ranges, cost model, benchmark, and which gap it fills. Cover at minimum: trend/momentum, mean-reversion, carry, volatility strategies, factor/multi-factor, pairs/cointegration, regime-switching, ML-based signals (gradient boosting, LSTM/Transformer, HMM, Kalman, Bayesian) — **only where they address a real gap**.

## PHASE 4 — THE PROOF STANDARD (NON-NEGOTIABLE)
No strategy may be called "profitable" unless it passes ALL of:
1. **Temporal discipline:** strict chronological train/test split; features use only past data; rolling recalibration.
2. **Walk-forward optimization (WFO):** embedded OOS windows; report walk-forward efficiency and parameter-stability heatmaps.
3. **Multiple-testing correction:** state total configurations tried across the entire project; report deflated Sharpe / White's Reality Check p-value; apply Bonferroni/Holm.
4. **Monte Carlo resampling:** bootstrap trade sequences (plain + block bootstrap preserving autocorrelation); report distribution of net returns, % of paths positive after costs, and 5th-percentile worst case.
5. **Full friction model:** spread, commission, slippage, funding/borrow costs, Canadian tax treatment; state breakeven cost level and margin of safety.
6. **Statistical significance:** bootstrap CI for mean excess return excluding zero; t-stat on mean return; report p-values.
7. **Regime robustness:** split into bull/bear/sideways and high/low volatility; require positive expectancy in the majority of regimes.
8. **Control experiment:** same pipeline on permuted/shuffled price series must NOT produce similar performance.
9. **Pre-registered forward test:** defined paper-trading protocol (duration, rules, live tracking URL, decision thresholds) before real capital.
10. **Reproducibility:** fixed random seeds, versioned data, exact formulas, runnable code.

## PHASE 5 — REQUIRED METRICS (compute for every candidate)
- **Returns:** CAGR, cumulative return, annualized volatility
- **Risk-adjusted:** Sharpe, Sortino, Calmar, Sterling, Treynor, Information ratio
- **Drawdown:** max drawdown, average drawdown, recovery time
- **Trade stats:** win rate, profit factor, expectancy per trade, avg win/avg loss, payoff ratio, longest losing streak, avg holding period
- **Distribution:** skewness, kurtosis, serial autocorrelation, fat-tail diagnostics
- **Cost-adjusted:** net vs. gross equity curves
- **Benchmark:** vs. buy-and-hold and vs. risk-free
- **Sensitivity:** parameter sweep results

## PHASE 6 — DELIVERABLES (committed to repo)
1. `AUDIT_REPORT.md` — inventory, failure taxonomy, methods catalogue
2. `STRATEGY_SHORTLIST.md` — ranked candidates with Phase 4/5 evidence and a clear "proven / promising / reject" verdict per candidate
3. Runnable backtest code (Python, seeded) for each shortlisted strategy
4. `PROOF_PROTOCOL.md` — pre-registered forward-test protocol
5. One-page executive summary: which asset class(es), timeframe(s), TP/SL/parameters, and exactly why we can claim profitability

## CONSTRAINTS
- Never claim profitability without passing Phase 4. If nothing passes, say so honestly and recommend closest candidates for forward testing.
- Flag uncertainty or missing data explicitly; never fill gaps with assumptions.
- Cite file paths for every factual claim.
- Use Canadian market conventions where relevant.

---
**Repo head-start file list is provided in `REPO_INVENTORY_HEADSTART.md`.**
