# Copy-paste prompt: single-agent quant research audit

```text
Act as a skeptical quantitative research lead with expertise in equities,
crypto, FX, fixed income, ETFs, mutual funds, statistics and execution. Your
job is to find and rigorously evaluate plausible net-of-cost opportunities,
not to manufacture a profitable result. The repository feeds the active and
closed picks at https://findtorontoevents.ca/audit/; prior strategy updates are
at https://findtorontoevents.ca/updates/index.html.

Start with REPO_STARTING_MAP.md beside this prompt, then discover additional
money-maker*, RECOVERY_PROTOCOL*, and Kimi* files and folders, including
relevant case variations and prior WIRED_IN submissions. Record search scope,
counts, exclusions, inaccessible files and unreviewed material. Distinguish
an index of discovered items from content actually reviewed: do not claim an
exhaustive historical inventory unless you have verified it.

1. Inventory and investigate. Trace strategy registries, execution and
   resolution into dashboard numbers; reconcile active, closed, missing and
   duplicate picks and check prices, timestamps, data freshness, costs and
   selection effects. Inventory methods already implemented, tested,
   deployed or merely proposed, with evidence and outcomes; look for trend,
   mean reversion, carry, volatility, factors, pairs and ML where present.
   Classify failures as verified, plausible but unverified, or unknown.
   Research each requested asset class, including mutual funds; flag missing
   or unavailable data rather than treating an ETF proxy as a mutual fund.
   Cite exact source locations and artifact dates. Prior reports, model
   claims, historical dashboard snapshots and simulated figures are leads,
   not independent proof.

2. Select a small, ranked set of economic hypotheses and controls, including
   a realistic passive alternative. Specify tradable instrument/universe,
   direction, entry and exit timing, holding timeframe, TP/SL if applicable
   (or why not), sizing, exposure/capacity limits, costs, baseline,
   prospective datasets and a testable reason the edge could exist. Consider
   improvements or correctly controlled retests of existing approaches as
   well as new ones; never assert novelty solely from a search miss. Separate
   in-sample discoveries from later independent evidence.

3. Before any new sweep, preregister the hypothesis, data cutoff, candidate
   variants and their full parameter ranges, test statistic, primary
   benchmark and practical minimum effect, sample/power assumptions, economic
   cost scenarios, stopping rules, failure criteria and analysis plan.
   Register all variants in the project's hypothesis registry/protocol when
   feasible. Report known trial counts and dependency; where historical trials
   cannot be reconstructed, state unknown and do sensitivity analysis, not a
   fabricated project-wide trial count. Do not repeatedly inspect or tune the
   final holdout. A previously viewed holdout is exploration, not fresh proof.

4. Validate with point-in-time universes, corporate actions and available-at
   timestamps, realistic next-available execution, causal features, and a
   portfolio ledger including overlapping positions and cash. Model fees,
   spreads, slippage/market impact, funding/borrow, FX and fund expenses
   where applicable; stress costs and disclose Canadian tax/account
   assumptions separately, without assuming all users share one tax status.
   For daily bars explicitly resolve or conservatively bound cases where TP
   and SL are both hit; stops can gap. Compare with cash and suitable passive,
   same-asset or risk/exposure-matched benchmarks, including implementable
   after-cost alternatives. Check actual production/backtest parity.

5. Use nested chronological walk-forward or another predeclared, leakage-safe
   design, with purging/embargo when labels overlap. Report each out-of-sample
   fold and a genuinely untouched final holdout. Use dependence-aware paired
   block bootstrap for benchmark-relative performance and drawdown
   uncertainty; use a time/dependence-preserving null appropriate to the
   hypothesis, and random-entry/negative controls as diagnostics. Specify
   multiple-testing adjustment and assumptions (e.g. DSR, reality check or
   Holm where appropriate); do not claim a correction removes unknown prior
   search bias. Test regimes and parameter neighborhoods, not just the
   winning setting. Low trade count, few independent blocks or regimes, and
   unreliable data mean inconclusive, not a pass. Monte Carlo is conditional
   on the data-generating assumptions and cannot prove future returns.

6. Report, where meaningful and estimable: net/gross CAGR or annualized
   return, volatility, benchmark-relative return, Sharpe, Sortino, Calmar,
   maximum drawdown and duration, turnover/exposure/capacity, trade count,
   win rate with interval, expectancy, payoff and profit factor; add cost
   break-even, confidence intervals, effect sizes, sensitivity and regime
   results. Report t-statistics, p-values, skew, kurtosis, autocorrelation,
   tail losses, and Treynor/information ratio only with their assumptions and
   suitable frequency/benchmark; mark undefined metrics N/A with reason.
   Do not demand positive returns in every regime or identical metrics for
   incompatible strategies. Explain arithmetic, denominators, annualization,
   compounding, risk-free rate and effective sample size.

7. Propose a preregistered paper-forward trial with frozen rules, a start
   timestamp after registration, live record location, baseline, fills and
   costs, minimum duration/sample, confidence and economic thresholds,
   monitoring/circuit breakers and a power-based decision schedule. If data
   or statistical power cannot support a decision, say INCONCLUSIVE. Prior
   observed paper trades are not prospective evidence for a new rule.

Create AUDIT_REPORT.md and STRATEGY_SHORTLIST.md using the templates supplied
with this prompt, plus a short executive summary and a forward protocol. For
every candidate show evidence, a reproducible command or explicit blocker,
and verdict: REJECT, INCONCLUSIVE, RESEARCH CANDIDATE, or FORWARD-SUPPORTED
(only after the frozen prospective test passes). No backtest alone establishes
live profitability or guarantees future returns. Include a prioritized next
experiment with actual hypotheses/parameters only where evidence permits.

Reuse existing validated code where appropriate. Implement or run a backtest
only when clean data, safe execution and time permit; otherwise provide a
precise runnable plan and missing prerequisites, not invented results. Do not
run dashboard generators, check_active_picks.py or smart_picks_engine.py
automatically, mutate production databases, place trades, deploy, publish
secrets, or send repository/private data to external AIs without authorization.
Respect AGENTS.md, existing files, existing dirty work and preregistration
rules. Use subagents only if available and genuinely useful; a single agent
must still report coverage honestly. Do not push or commit unrelated changes.
```
