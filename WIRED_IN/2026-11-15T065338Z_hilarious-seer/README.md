# Master Document: Quant Audit Prompts, Proof Standards & Failure Diagnosis
## Consolidated reference for the Antigravity trading system audit

**Date:** 2026-11-15
**Worktree:** hilarious-seer
**Location:** `WIRED_IN/2026-11-15T065338Z_hilarious-seer/`

---

## Table of Contents
1. [Original Request](#original-request)
2. [Enhanced Prompt (World-Class Quant Team)](#enhanced-prompt-world-class-quant-team)
3. [Self-Engineering Prompt](#self-engineering-prompt)
4. [Failure Signature Analysis](#failure-signature-analysis)
5. [Negative Result Diagnosis Template](#negative-result-diagnosis-template)
6. [Follow-Up Q&A](#follow-up-qa)

---

## Original Request

> Based on this info, get us some prompts to help a github repo for prediction of various financial investment asset classes like stocks/crypto/forex/bonds/etfs/commodities/mutual funds etc.
>
> You have a repo https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/ that was being worked on for basically years with tons of AI agents, lots of .MD of research, strategies for stocks/crypto/forex/bonds/ETFS/mutual funds,.... and yet the dashboard output isn't profitable. The repo feeds into findtorontoevents.ca/audit where we have active picks, closed picks and an attempt at predictions for asset classes.
>
> review money-maker* files and RECOVERY_PROTOCOL*.MD and all Kimi* files and folders, where we had Kimi Agent Swarm research and review our project over time,
>
> We also had findtorontoevents.ca/updates/index.html where we talked about our strategies we tried.
>
> But overall, just give us some strategies to go through the repo, algorithms and find us 1 or more profitable asset classes, and timeframes, and TP/SL or other trading parameters, and a method to prove beyond a shadow of a doubt its profitable.
>
> Like if we hired the world's leading Quants or a stock expert, then a crypto expert, mutual fund expert etc. Despite trying so many strategies, we still were met with failure.
>
> What statistical measures should we consider to use. Use subagents and scan our repo for statistical and risk management methods/ mathematical functions/ machine learning algorithms and determine, what we've already tried, and determine room for other simulations we can adjust.

---

## Enhanced Prompt (World-Class Quant Team)

```text
You are a world-class quantitative research team: a senior equities quant, a crypto quant, a forex/macro quant, a fixed-income & mutual-fund analyst, and an academia-grade statistician. You are auditing a project that has spent years and dozens of AI-agent iterations trying to build a profitable trading system and has consistently failed.

REPOSITORY & LIVE OUTPUTS
- Repo: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/
- Live dashboard: findtorontoevents.ca/audit (active picks, closed picks, asset-class prediction attempts)
- Strategy history page: findtorontoevents.ca/updates/index.html
- Must review: every `money-maker*` file, every `RECOVERY_PROTOCOL*.MD`, every `Kimi*` file and folder, and the audit/updates code.

PHASE 1 — INVENTORY & TAXONOMY
Build a complete table of everything that has ever been tried. For each strategy record:
| Strategy name | Asset class(es) | Timeframe | Entry logic | Exit logic | TP/SL | Position sizing / risk mgmt | Statistical/ML methods used | Result observed | Suspected failure mode |
Cite exact file paths for every row. Cover stocks, crypto, forex, bonds, ETFs, mutual funds, and any multi-asset or rotation approaches.

PHASE 2 — FORENSIC FAILURE ANALYSIS
For each failed strategy, label its failure mode(s) from this taxonomy:
1. Overfitting / data snooping (too many parameter trials, too few trades)
2. Look-ahead bias (future data leaked into signals)
3. Survivorship / universe bias
4. Unrealistic cost model (ignoring spread, slippage, commissions, funding)
5. Weak signal-to-noise ratio (edge too small vs. volatility)
6. Regime dependence (worked in bull market only)
7. Implementation gap (backtest logic differs from live execution)
8. Insufficient sample size (statistically inconclusive)
9. Wrong objective optimized (e.g., raw return instead of risk-adjusted)
10. Risk management failures (no stop discipline, over-leverage, concentration)

Also produce a verbatim catalogue of the statistical, risk-management, mathematical, and machine-learning methods already used in the repo (with file citations), so we never propose something already tried.

PHASE 3 — GAP ANALYSIS & NEW EXPERIMENTS
Propose simulations the repo has NOT yet tried, organized by asset class. For each proposal specify: signal construction, universe, timeframe, parameter ranges, cost model, benchmark, and precisely which gap it fills. Cover at least: trend/momentum, mean-reversion, carry, volatility strategies, factor/multi-factor, pairs/cointegration, regime-switching, and ML-based signals (e.g., gradient boosting, LSTM/Transformer, HMM, Kalman filters, Bayesian methods) — only where they address a real gap.

PHASE 4 — THE PROOF STANDARD (NON-NEGOTIABLE)
No strategy may be called "profitable" or recommended unless it passes ALL of:
1. Temporal discipline: strict chronological train/test split; every feature computed using only past data; rolling recalibration.
2. Walk-forward optimization (WFO) with embedded out-of-sample windows; report walk-forward efficiency and parameter-stability heatmaps.
3. Multiple-testing correction: state the total number of configurations tried across the entire project; report the deflated Sharpe ratio and/or White's Reality Check p-value; apply Bonferroni/Holm where needed.
4. Monte Carlo resampling: bootstrap trade sequences (plain and block bootstrap preserving autocorrelation); report distribution of net returns, % of paths positive after costs, and the 5th-percentile worst case.
5. Full friction model: spread, commission, slippage, funding/borrow costs, and Canadian tax treatment where relevant; then state the breakeven cost level and margin of safety.
6. Statistical significance: bootstrap confidence interval for mean excess return excluding zero; t-stat on mean daily/weekly return; report p-values.
7. Regime robustness: split history into bull/bear/sideways and high/low volatility; require positive expectancy in the majority of regimes, not just on average.
8. Control experiment: the same pipeline run on permuted/shuffled price series must NOT produce similar performance.
9. Pre-registered forward test: a defined paper-trading protocol (duration, rules, live tracking URL, decision thresholds) to be run before real capital.
10. Reproducibility: fixed random seeds, versioned data, exact formulas documented, runnable code.

PHASE 5 — REQUIRED STATISTICAL & RISK METRICS (compute for every candidate)
- Returns: CAGR, cumulative return, annualized volatility
- Risk-adjusted: Sharpe, Sortino, Calmar, Sterling, Treynor, Information ratio
- Drawdown: max drawdown, average drawdown, recovery time
- Trade stats: win rate, profit factor, expectancy per trade, avg win/avg loss, payoff ratio, longest losing streak, avg holding period
- Distribution: skewness, kurtosis, serial autocorrelation, fat-tail diagnostics
- Cost-adjusted net vs. gross equity curves
- Benchmark comparison vs. buy-and-hold of the asset and vs. risk-free
- Parameter sensitivity across the full sweep

PHASE 6 — DELIVERABLES (exact files, committed to the repo)
1. `AUDIT_REPORT.md` — inventory table, failure taxonomy, catalogue of methods already tried
2. `STRATEGY_SHORTLIST.md` — ranked candidates with all Phase 4/5 evidence and a clear "proven / promising / reject" verdict per candidate
3. Runnable backtest code (Python/pandas/numpy, seeded) for each shortlisted strategy
4. `PROOF_PROTOCOL.md` — the pre-registered forward-test protocol
5. A one-page executive summary answering: which asset class(es), which timeframe(s), which TP/SL and other parameters, and exactly why we can now claim it is profitable.

CONSTRAINTS
- Never claim profitability without passing Phase 4. If nothing passes, say so honestly and recommend the closest candidates for forward testing.
- Flag any uncertainty or missing data explicitly; do not fill gaps with assumptions.
- Cite file paths for every factual claim about the repo.
- Use Canadian market conventions (currency, taxes, trading hours) where relevant.
```

---

## Self-Engineering Prompt

```text
You are a senior quant research contractor who is also responsible for project governance.
You will engineer your own execution plan, execute it, and store every artifact in the
repository exactly as specified below. Work autonomously, but make every decision auditable.

## 1. Workspace protocol (NON-NEGOTIABLE)
- Create your output folder: WIRED_IN/<UTC-timestamp>_<unique-id>/
  - Timestamp format: YYYY-MM-DD_HHmm UTC, e.g. 2026-11-15_0700
  - unique-id = your worktree/branch name or a short random suffix (e.g. x7k9)
- Folder layout inside it:
  - Summary.MD — LIVING DOCUMENT: created FIRST with your plan, updated at the end of
    every phase, finalized last. It must let a reader reconstruct exactly what you did.
  - harvested_ideas/ — raw mining output:
      - 00_inventory.csv
      - 01_failures_taxonomy.md
      - 02_methods_catalogue.md
      - one .md per asset class (stocks, crypto, forex, bonds, etfs, mutual_funds,
        multi_asset)
  - Plan/ — mirrors the repo's existing /Plan structure; one subfolder per asset class,
    each containing PLAN.md BEFORE any code is written
  - experiments/ — code + parameters per simulation
  - tracker/ — prediction tracker (see §5)
  - proof/ — walk-forward outputs, Monte Carlo results, significance tests, equity curves

## 2. Repo-mining algorithm (run FIRST, before any strategy work)
Layer A — Static keyword archaeology: run ripgrep/grep over the whole repo (including
all .MD research files) for this regex pattern library:
- ML/models: random forest|xgboost|lightgbm|keras|tensorflow|pytorch|lstm|transformer|
  arima|sarima|prophet|hmm|kalman|bayesian|neural|gradient boosting|clustering|pca|svm
- Backtesting: backtest|vectorbt|zipline|backtrader|quantconnect|walk.forward|
  cross.validation|train_test_split|in_sample|out_of_sample|param.sweep|grid.search
- Risk: var|value.at.risk|max.drawdown|sharpe|sortino|calmar|sterling|kelly|
  position.sizing|stop.loss|take.profit|tp|sl|atr|volatility|leverage
- Execution: paper.trade|simulate|live|execution|slippage|commission|spread|funding|tax
- Data: yfinance|ccxt|alpha.vantage|polygon|binance|ohlcv|resample|adj close
Then parse dependency manifests (requirements.txt, pyproject.toml, package.json) and list
every installed library.
Layer B — Semantic mapping: for every flagged file, extract the exact function names,
class names, and parameters used. Build harvested_ideas/00_inventory.csv with columns:
[file_path | language | technique detected | asset class | timeframe | key functions |
status: implemented/tested/abandoned].
From the inventory, derive 01_failures_taxonomy.md and 02_methods_catalogue.md (with file
citations for every claim).

## 3. Planning protocol
- After mining, read the repo's existing /Plan subfolders; reuse, do not duplicate.
- Never run a full backtest before a plan exists.
- Every NEW experiment requires Plan/<asset_class>/PLAN.md containing: hypothesis, the
  specific gap it fills (cite the inventory row), method, data source, timeframe, universe,
  parameter ranges, cost model, benchmark, and which proof tests in §6 it will pass.

## 4. Prediction tracker (scale to your prediction timeframe)
- Horizon ≤ 1 day → intraday tracker; log every bar/trade to a csv/jsonl.
- Horizon 1 day – 3 months → daily cadence; columns: timestamp | asset | regime |
  direction | expected return | TP | SL | horizon | confidence | actual outcome |
  hit/miss | link to trade log.
- Horizon > 3 months → weekly cadence; strategy-level reports + rebalance rules.
- Ship tracker/predictions_tracker.csv (plus an interactive HTML viewer) and ensure every
  live pick on the audit page can be matched back to a tracker row.

## 5. Git & remote protocol
- Work on a branch/worktree named after your unique id; commit after each phase; push to
  the remote frequently (origin).
- Cherry-pick salvageable changes into the main branch only when they pass review.
- Never rewrite public history. Verify with git status / git log before every push.
- If git fails (auth/network), save everything locally anyway and record the blocker in
  Summary.MD.

## 6. Proof standard (mandatory for every candidate)
Pass ALL of: (1) strict chronological train/test split, features computed only from past
data; (2) walk-forward optimization with embedded OOS windows, report walk-forward
efficiency; (3) multiple-testing correction — state total configurations tried project-wide,
report deflated Sharpe ratio and/or White's Reality Check p-value; (4) block-bootstrap
Monte Carlo of trade sequences — report % of paths positive after costs and 5th-percentile
worst case; (5) full friction model (spread, commission, slippage, funding, tax) plus the
breakeven cost level and margin of safety; (6) bootstrap CI for mean excess return excluding
zero, t-stat and p-values; (7) regime-split results (bull/bear/sideways, high/low vol) —
positive expectancy in most regimes, not just on average; (8) shuffle control: permuted
prices must not reproduce performance; (9) pre-registered paper-trading protocol with
duration, rules, and decision thresholds; (10) reproducibility: fixed seeds, versioned
data, documented formulas, runnable code.

## 7. Final deliverables
- Update Summary.MD: what was done, inventory highlights, ranked candidates with explicit
  verdicts (proven / promising / reject), recommended asset class(es) + timeframe(s) +
  TP/SL + parameters, the statistical evidence, and exact reproduction commands.
- Push everything to the remote. If nothing passes §6, say so honestly and recommend the
  closest candidates for forward testing.
```

---

## Failure Signature Analysis

### How to Interpret Results When No Strategy Passes

**1. Read the failure signature, not the failure**

The proof standard is a ladder. Which rung each strategy fell off tells you what kind of problem you have:

| Failed at | What it means | What it points to |
|-----------|---------------|-------------------|
| Significance tests (CI includes zero, low t-stat) | The signal is indistinguishable from noise | No real edge in that signal class; don't chase variants of it |
| Friction model (edge dies after costs) | The edge exists but is too small to harvest | Lower turnover, maker orders, different instrument (futures vs. ETF), or accept it's untradeable |
| Walk-forward stability (parameters drift) | Classic overfitting / regime dependence | The "edge" was curve-fit; move to simpler, lower-parameter signals |
| Shuffle control (shuffled data also performs) | Your pipeline has a leak (look-ahead bias, bug) | This is the best possible failure — it's a code bug, not the market |
| Monte Carlo (some paths positive, but wide spread / many negative) | Too few trades to conclude anything | More data, longer history, or lower frequency so sample size grows |
| Regime split (wins only in bull markets) | Conditional edge | Trade it only in that regime — or stop pretending it's unconditional |

**2. What NOT to do**

- Don't lower the bar to let something through. That's how the previous years of failure happened. The proof standard is the single most valuable thing you now own — protect it.
- Don't re-run failed candidates with tweaked parameters until one passes. That converts your proof standard into a search engine for false positives. Any parameter change after seeing results is a new hypothesis that must re-enter the full pre-registered pipeline.
- Don't cherry-pick the best-looking walk-forward window and call it validation.
- Don't conclude "our AI agents are bad." The agents built a rigorous negative result, which is rare and extremely useful.

**3. Legitimate next moves, depending on the signature**

- Everything fails at significance: the markets/asset classes/timeframes you tested are genuinely efficient at that cost level. Stop re-testing them. The mandate was "find at least one profitable asset class" — so pivot: new asset class (e.g., intraday crypto if you haven't, or options/futures where retail competition is thinner), or a genuinely different signal family (carry, volatility, cross-sectional rather than directional).
- Edge dies at costs: this is a harvesting problem, not a signal problem. Test a low-turnover version (weekly instead of daily, basket instead of single names), and explicitly model maker-taker rebates. This is also where you learn your real cost per trade.
- Everything fails but with low variance / near-misses: consider portfolio-level construction — 5–8 weakly positive, uncorrelated signals can produce a statistically significant combined result even when each alone is sub-significant. But you must cascade the multiple-testing correction across the combination (deflated Sharpe on the combined strategy), and re-enter it as a fresh pre-registered candidate.
- Failures are regime-conditional: narrow the mandate. A strategy that's provably positive in high-volatility regimes only is legitimate — if you pre-register "trade only in regime X, stand aside otherwise" before seeing the data that defines X.

**4. When the honest answer is "no edge exists here"**

If after the full sweep the conclusion is genuinely negative, that itself is a deliverable:

- Publish the negative result in Summary.MD. Include the total number of configurations tried, the deflated Sharpe threshold, and the proof that the failure is not due to bugs. This protects you from repeating it — and it's the exact evidence a serious investor would want to see before trusting you with capital.
- Stop. Sunk cost is the real enemy. "Years of attempts" is the strongest reason to take a clean sweep seriously, not to keep going.
- Reconsider the business premise. If no directional edge survives, the profitable alternative may be passive: the audit dashboard could pivot to a disciplined allocation/index strategy (which has a measurable, provable expected outcome) rather than active picks. That's still a legitimate product — and it can pass a proof standard, because its benchmark is explicit.

**5. Near-miss definition**

A near-miss is: passes all of temporal discipline, shuffling, walk-forward, and frictions, but fails significance or Monte Carlo due to sample size. That's a candidate worth re-testing with more data (or a longer forward-test window) — not a candidate to deploy. By contrast, a candidate that fails shuffling or walk-forward is dead, permanently.

---

## Negative Result Diagnosis Template

```markdown
# Negative Result Diagnosis — Candidate Failure Classification

**Date:** YYYY-MM-DD
**Audit ID:** [link to parent audit report]
**Decision owner:** [name]

---

## 1. Decision Rule (pre-registered)

A candidate is **dead** if it fails: shuffle control, walk-forward stability, or temporal discipline.
A candidate is **near-miss** if it passes temporal discipline, shuffle control, walk-forward, and friction model, but fails significance or Monte Carlo due to sample size.
A candidate is **actionable** if it passes all ten proof steps.

Only actionable candidates advance. Near-misses may be re-tested with more data. Dead candidates are archived and may not be re-run with tweaked parameters.

---

## 2. Candidate Classification Matrix

| ID | Candidate | Assets | Timeframe | Proven Steps / 10 | Failed At | Verdict | Root Cause (hypothesis) | Recommended Pivot | Next Action |
|----|-----------|--------|-----------|-------------------|-----------|---------|--------------------------|-------------------|-------------|
| ... | ... | ... | ... | e.g. 6/10 | #4 friction | Actionable | Edge exists but costs eat it | Lower turnover, maker orders | Paper trade 90 days |

*Proven Steps reference §6 of the proof protocol (1=temporal, 2=WFO, 3=multiple testing, 4=MC, 5=friction, 6=significance, 7=regime, 8=shuffle, 9=forward test, 10=reproducibility).*

---

## 3. Failure-Signature → Pivot Map (auto-classification rules)

| Failed Hurdle | Interpretation | Actionable Pivot | Reject If |
|---|---|---|---|
| Significance (CI includes zero, low t-stat) | Signal indistinguishable from noise | Pivot to a *different signal family* (carry/volatility/cross-sectional) — not a parameter tweak | Any variant of this signal class tested >3 times |
| Friction model (edge dies post-cost) | Edge exists but too small to harvest | Lower turnover (weekly vs. daily), basket sizing, maker orders, different instrument (futures vs. ETF) | Cost margin < 2× breakeven after 3 cost-model refinements |
| Walk-forward stability (params drift) | Classic overfitting / regime dependence | Simplify signal, cut parameters by ≥50%, re-enter as fresh hypothesis | Same signal family fails WFO twice |
| Shuffle control (shuffled data also profits) | Pipeline leak / bug | Debug code — this is the *best* failure; fix and re-test | Leak not fixed within 2 sprint cycles |
| Monte Carlo (wide spread, many negative paths) | Too few trades to conclude | Extend history or lower frequency so N trades grows | Still < 60 trades after data extension |
| Regime split (wins only in bull markets) | Conditional edge | Trade only in that regime with a pre-registered regime trigger, stand aside otherwise | No regime trigger that is deterministic & auditable |

---

## 4. Near-Miss Register

Candidates that failed only on sample size:

| ID | Candidate | Trades in backtest | Missing data | Recommended fix | Horizon of paper test |
|----|-----------|--------------------|--------------|------------------|------------------------|
| ... | ... | e.g. 23 / 60+ | e.g. no pre-2015 crypto data | Backtest on 2× history + weekly cadence | 6 months live |

**Rule:** near-misses are *not* deployed. They may only be re-tested by extending data or lengthening the forward test — never by parameter hunting.

---

## 5. Portfolio-Level Combination (if all single signals fail but show low-variance near-misses)

- Pool 5–8 weakly positive, pair-wise uncorrelated signals (ρ < 0.3)
- Equal-risk-parity or volatility-weighted sizing
- **Must** cascade multiple-testing correction across the combination (deflated Sharpe on the *combined* strategy)
- Re-enter as a fresh pre-registered candidate in §2

---

## 6. Final Verdict Section (fill in exactly one)

**[ ] Proven edge found** — candidate(s): ______. Recommend forward test per `PROOF_PROTOCOL.md`.

**[ ] Near-miss only** — candidate(s): ______. Recommend data extension + longer paper test.

**[ ] No edge — clean negative result.** Published total configurations tried: _____. Deflated Sharpe threshold: ____. Proof that failures are not code bugs: ______. Sunk cost cut-off confirmed. Recommend pivot to passive allocation or new asset class/signal family.

---

## 7. Sign-off

| Role | Name | Date |
|------|------|------|
| Lead Quant | | |
| Statistician | | |
| Governance | | |
```

---

## Follow-Up Q&A

### Q1: Near-misses failing only on sample size — extend backtest or longer paper test?

Do both, in this order:

1. Extend the backtest window first — but only if the failure is genuinely a count problem (too few trades), not a structure problem. Extend with additional history (e.g., pre-2015 crypto, longer equity history), or lower the frequency (daily → weekly, which grows N trades while reducing turnover). Document the extended N.
2. If extended backtest still falls short, move to a longer pre-registered paper-trading test — because a live paper test adds real trades to the sample, which is exactly what the Monte Carlo significance test is missing.
3. Never re-run the backtest with tweaked parameters to chase significance. Any parameter change after seeing results is a new hypothesis that must re-enter the full pipeline from §2.

**Decision threshold:** a near-miss is worth paper-trading if it passes temporal discipline, shuffle control, walk-forward, and frictions, and the only gap is N trades < 60. If any of those four fail, it is dead regardless of sample size.

### Q2: Pivot the dashboard to passive allocation while keeping a measurable proof?

Yes — and this can pass a proof standard more cleanly than any active strategy, because the benchmark is explicit:

1. Redesign the audit as an allocation engine: instead of active picks, the dashboard recommends a static or rule-based blend (e.g., 60% bond ETF / 30% equity ETF / 10% cash, or a volatility-targeted multi-asset portfolio) with quarterly rebalance.
2. Pre-register the rule and the benchmark: every allocation decision is a deterministic function of observable, lagged data (e.g., "when 10y yield > 4%, shift 10% into short bonds"). The benchmark is an explicit buy-and-hold multi-asset index.
3. Proof standard applies identically: run the same walk-forward, friction, Monte Carlo, and shuffle-control tests on the allocation strategy. The edge is not directionality — it's documented, rule-based risk management and rebalance discipline.
4. Publish the negative result of the active sweep separately (use the template above) so investors see the active side was rigorously killed, not quietly abandoned. This actually increases trust: a product that says "we tested 87 active strategies, zero passed; here is our provable passive alternative" is far more credible than one that just keeps showing active picks.

**The key shift:** the claim changes from "we beat the market directionally" to "we provide a measurable, rule-based allocation with a defined, defensible expected outcome." Both are legitimate products, but the passive one can be proven with confidence — which is exactly what your audit page currently lacks.

---

## Related Files in This WIRED_IN Folder

- `MASTER_PROMPT.md` — merged self-engineering + proof standard prompt
- `QUANT_AUDIT_PROMPT.md` — compressed single-agent prompt for Claude Code
- `REPO_INVENTORY_HEADSTART.md` — curated file/folder list to accelerate Phase 1 inventory
- `AUDIT_REPORT_TEMPLATE.md` — structured template for forensic audit report
- `STRATEGY_SHORTLIST_TEMPLATE.md` — structured template for ranked strategy shortlist
- `NEGATIVE_RESULT_DIAGNOSIS_TEMPLATE.md` — failure classification matrix and decision tree

---

*Generated by hilarious-seer worktree, 2026-11-15*
