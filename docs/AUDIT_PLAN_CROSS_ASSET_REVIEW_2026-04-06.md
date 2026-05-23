# Audit plan review for cross-asset pick quality

**Date:** 2026-04-06  
**Fleet note:** `PUBLISH` to `alpha_engine_bus` may return **0** when no client is subscribed; the message can still be recorded via `bus:broadcast:log` / inbox patterns depending on your publisher.  
**Scope:** Review of the Cursor plan **audit picks edge analysis** (fleet: `audit_picks_edge_analysis` / instrumentation plan) against the current `/audit` truth layer and existing repo evidence.  
**Verdict:** The plan is worth doing, but it is an **analysis bridge**, not the fix for hedge-fund-grade consistency.

## Bottom line

The current plan is directionally correct because it closes a real visibility gap:

- closed-pick scoring evidence already exists
- active-book evidence is fragmented
- operators still do not have one reproducible report tying the current `/audit` snapshot to asset class, strategy history, and unrealized PnL

That said, the plan will not by itself solve the actual failure mode. The system does not look primarily blocked by "not enough analytics." It looks blocked by four harder issues:

1. the dashboard truth layer is still not fully trustworthy
2. the system mixes asset classes that need different ranking logic
3. toxic strategy lanes are still entering the book
4. forward promotion appears contaminated by overfit selection

## What the existing evidence already says

### 1. Cross-asset behavior is not one problem

The strongest repo evidence is in [docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md](/e:/findtorontoevents_antigravity.ca/docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md):

- Crypto: `smart_score` is useful, `elite_score` is weak for realized PnL ranking.
- Equity: `elite_score` ranks outcomes better, but the traded universe still loses money on average.
- Forex: headline score is weak and confidence is noise or inverse.

That means the path to "hedge-fund level" is not one global score tweak. The system needs asset-conditioned routing, weights, and strategy allowlists.

### 2. The plan helps with observability, not edge creation

The Cursor plan is good because it would add one missing operational report:

- same snapshot as `/audit`
- active book by asset class
- score vs unrealized PnL with sample-size guardrails
- strategy-on-book joined to closed history

That is exactly what the current workflow lacks. It should reduce self-deception around "live score looks good, therefore edge is fixed."

But analysis is not the bottleneck after that. The repo already contains enough evidence to act:

- [SCORE_PNL_EDGE_REVIEW_2026-04.md](../audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md)
- [ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md](ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md)
- [HEDGE_FUND_ENHANCEMENT_PLAN.md](../HEDGE_FUND_ENHANCEMENT_PLAN.md)

The real issue is execution discipline after the evidence is known.

### 3. "So close" is mostly a selection problem

[HEDGE_FUND_ENHANCEMENT_PLAN.md](/e:/findtorontoevents_antigravity.ca/HEDGE_FUND_ENHANCEMENT_PLAN.md) contains the most important warning:

- backtest-forward correlation reported at `-0.91`
- `78.9%` of trades hitting stop loss
- DNA mutation live win rate reported at `14.3%`

If those findings are directionally true, the system is not just under-optimized. It is promoting the wrong things. In that state, more scoring sophistication can make the dashboard look smarter while still selecting bad exposures.

### 4. Dashboard trust still matters

[KIMI_AUDIT_FINDINGS_20260405.md](KIMI_AUDIT_FINDINGS_20260405.md) shows unresolved or recently fixed integrity issues around:

- total PnL aggregation
- impossible drawdown presentation
- summary vs drill-down drift

Until those are clean, the team risks optimizing to corrupted topline metrics.

## Review of the current plan

### What is good

- Correct source of truth: `audit_dashboard/data/dashboard_data.json`
- Correct refusal to invent SQL metrics
- Correct emphasis on one reproducible snapshot
- Correct addition of active-book analysis, which is the current blind spot
- Correct Redis bus publication pattern for fleet awareness

### What is missing

- No explicit requirement to block conclusions when the dashboard integrity checks are stale or unresolved
- No hard requirement to separate asset classes in all operator-facing conclusions
- No direct tie from analysis output to gating actions for toxic strategies
- No requirement to audit strategy promotion rules against forward results before adding more features

### What is overstated

The plan can improve operator clarity. It cannot meaningfully improve pick quality on its own. Calling it a hedge-fund-quality improvement plan would be overstating it. It is an audit instrumentation plan.

## Recommended priority order

### P0

1. Finish truth-layer cleanup before trusting aggregate score stories.
2. Ship the active-book analyzer from the Cursor plan.
3. Produce one snapshot report that always splits crypto, equity, forex, commodities, and ETF separately.

### P1

1. Enforce asset-class-specific ranking logic.
2. Gate or remove structurally losing equity and forex strategy lanes.
3. Add rolling strategy expectancy and strategy-symbol expectancy as explicit ranking inputs.

### P2

1. Audit promotion logic against forward performance, not just backtest quality.
2. Make DSR, FDR, purged CV, and regime reporting promotion requirements instead of documentation items.
3. Narrow the live book until only statistically and operationally defended lanes remain.

## Concrete feedback on each asset class

### Crypto

- Best near-term opportunity.
- Keep `smart_score` central.
- Reduce dependence on `elite_score` until crypto elite components are revalidated.
- Focus on strategy-level tails and duplicate exposure control.

### Equity

- Biggest structural problem.
- Ranking may work, but the universe being traded is still bad.
- Do not solve equity with weights alone.
- Use allowlists, lane retirement, and rolling expectancy penalties.

### Forex

- Treat as experimental.
- Confidence should not be trusted as a strong signal in current form.
- Require larger closed samples and cleaner monotonicity before meaningful capital allocation.

### Commodities and ETF

- Likely under-sampled in current public evidence.
- Keep them separate in every report.
- Do not borrow crypto assumptions into these books.

## Final judgment

Approve the current plan as a necessary reporting step.

Do not confuse it with the actual alpha-repair plan.

If the goal is consistent hedge-fund-grade picks, the real sequence is:

1. trust the dashboard
2. split the problem by asset class
3. kill or quarantine toxic lanes
4. fix promotion logic
5. only then refine composite scoring

## Reference set

- [C:\Users\zerou\.cursor\plans\audit_picks_edge_analysis_dbcaff8e.plan.md](C:\Users\zerou\.cursor\plans\audit_picks_edge_analysis_dbcaff8e.plan.md)
- [docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md](/e:/findtorontoevents_antigravity.ca/docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md)
- [audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md](/e:/findtorontoevents_antigravity.ca/audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md)
- [docs/KIMI_AUDIT_FINDINGS_20260405.md](/e:/findtorontoevents_antigravity.ca/docs/KIMI_AUDIT_FINDINGS_20260405.md)
- [HEDGE_FUND_ENHANCEMENT_PLAN.md](/e:/findtorontoevents_antigravity.ca/HEDGE_FUND_ENHANCEMENT_PLAN.md)
