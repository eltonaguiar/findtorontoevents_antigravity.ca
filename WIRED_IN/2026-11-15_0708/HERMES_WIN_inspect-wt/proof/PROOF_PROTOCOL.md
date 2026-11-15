# PROOF PROTOCOL.md — Mandatory Non-Negotiable Standard

No strategy may be called "profitable" or recommended unless it passes ALL of the following 10 steps. Any single failure = DEAD or NEAR-MISS (see `03_negative_result_diagnosis.md` for exact classification rules).

---

## Step 1 — Strict Chronological Train/Test Split
- **Requirement:** Features must be computed using ONLY past data. The train window closes at a fixed timestamp; the test window begins immediately after. No peeking at future data to compute any feature, indicator, or signal value.
- **Gate outcome:** Fail → CANDIDATE DEAD (same as shuffle control failure). This is the most common failure (F2, F28, F29).
- **Audit requirement:** Document train/test split dates, all feature lookback windows, and the fixed cutoff timestamp.

## Step 2 — Walk-Forward Optimisation (WFO) with Embedded OOS Windows
- **Requirement:** Walk-forward windows of exactly 4 years training / 1 year testing (minimum). Train window rebalances, optimises parameters, then freezes. Report walk-forward efficiency: `(sum of test-period PF) / (sum of train-period PF)`.
- **Parameter stability heatmap:** Plot efficiency across consecutive windows; windows with >20% efficiency drop flag as unstable.
- **Gate outcome:** Fail → CANDIDATE DEAD (overfitting / regime dependence). Examples: F4, F7, F14, F22.
- **Audit requirement:** Efficiency heatmap, parameter values per window, stability verdict.

## Step 3 — Multiple-Testing Correction (Project-Wide)
- **Requirement:** State the total number of distinct configurations tried across the entire project. Compute deflated Sharpe ratio and/or White's Reality Check p-value; apply Bonferroni or Holm correction.
- **Gate outcome:** Fail → CANDIDATE DEAD. The project-wide trial count (currently ~1,307 backtest files) makes uncorrected Sharpe meaningless.
- **Audit requirement:** Total config count, deflated Sharpe, WC p-value, correction applied.

## Step 4 — Monte Carlo Resampling of Trade Sequences
- **Requirement:** Block bootstrap (arch>=7.0.0: MovingBlockBootstrap, StationaryBootstrap) of trade sequences, preserving autocorrelation. Report: % of paths positive after costs, 5th-percentile worst-case net return.
- **Gate outcome:** Fail → NEAR-MISS if all other steps pass; otherwise DEAD. If % positive < 50%, edge is not tradeable.
- **Audit requirement:** Number of bootstrap paths, % positive, 5th percentile, cost model applied.

## Step 5 — Full Friction Model
- **Requirement:** Spread (maker/taker), commission, slippage, funding/borrow costs, and Canadian tax treatment where relevant. Then state the breakeven cost level and margin of safety.
- **Gate outcome:** Fail → NEAR-MISS if all other steps pass; otherwise DEAD. If edge dies after costs, it's not tradeable at current cost level.
- **Audit requirement:** Full cost breakdown, breakeven cost, margin of safety.

## Step 6 — Statistical Significance
- **Requirement:** Bootstrap confidence interval for mean excess return excluding zero; t-stat on mean daily/weekly return; report p-values.
- **Gate outcome:** Fail → NEAR-MISS if all other steps pass; otherwise DEAD. CI including zero = no measurable edge.
- **Audit requirement:** CI lower bound, t-stat, p-value, cost-adjusted.

## Step 7 — Regime Robustness
- **Requirement:** Split history into bull/bear/sideways and high/low volatility regimes. Require positive expectancy in the majority of regimes, not just on average across all regimes.
- **Gate outcome:** Fail → NEAR-MISS if all other steps pass; otherwise DEAD. A strategy that only works in bull markets is conditional, not unconditional.
- **Audit requirement:** Regime labels, PF/Sharpe per regime, majority-vote verdict.

## Step 8 — Control Experiment (Shuffle)
- **Requirement:** The same pipeline run on permuted/shuffled price series must NOT produce similar performance. If shuffled data also profits, the pipeline has a leak (look-ahead bias, bug).
- **Gate outcome:** Fail → CANDIDATE DEAD (same as shuffle control failure). This is the "best possible failure" — it's a code bug, not a market fact.
- **Audit requirement:** Shuffled series results, comparison verdict.

## Step 9 — Pre-registered Forward Test (Paper Trading)
- **Requirement:** A defined paper-trading protocol with: duration (minimum 6 months), exact rules, live tracking URL, decision thresholds (e.g., "buy if signal > 0.6 and cost-adjusted PF > 1.15 after 30 trades"), and real-time PnL tracking.
- **Gate outcome:** Fail → NEAR-MISS if all other steps pass; otherwise DEAD. No live protocol = not deployable.
- **Audit requirement:** Protocol document, tracking URL, trade log, 6-month summary.

## Step 10 — Reproducibility
- **Requirement:** Fixed random seeds, versioned data, exact formulas documented, runnable code. Another researcher must be able to clone the repo, reproduce the backtest, and get the same numerical results within floating-point tolerance.
- **Gate outcome:** Fail → CANDIDATE DEAD. If another researcher cannot reproduce it, the result is not scientifically valid.
- **Audit requirement:** Seeds, data versions, formula docs, reproduction test results.

---

## THE PROOF STANDARD IN PRACTICE

| Failed at | What it means | Action |
|-----------|---------------|--------|
| Significance (CI includes zero, low t-stat) | Signal indistinguishable from noise | Pivot to a *different signal family* — not a parameter tweak |
| Friction model (edge dies post-cost) | Edge exists but too small to harvest | Lower turnover, basket sizing, maker orders, different instrument |
| Walk-forward stability (params drift) | Classic overfitting / regime dependence | Simplify signal, cut params ≥50%, re-enter as fresh hypothesis |
| Shuffle control (shuffled data also profits) | Pipeline leak / bug | Debug code — this is the *best* possible failure; fix and re-test |
| Monte Carlo (wide spread, many negative paths) | Too few trades to conclude | Extend history or lower frequency so N trades grows |
| Regime split (wins only in bull markets) | Conditional edge | Trade only in that regime with a pre-registered trigger, stand aside otherwise |

**A candidate that passes ALL 10 steps is ACTIONABLE.** A candidate that fails only the friction model or Monte Carlo due to sample size is a NEAR-MISS — worth re-testing with more data or longer paper-trading, but NOT for deployment. All others are DEAD.

--- 

*Never claim profitability without passing the full proof standard. If nothing passes, say so honestly and recommend the closest candidates for forward testing.*