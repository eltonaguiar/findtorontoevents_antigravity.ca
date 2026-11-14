# Execution Roadmap — Final v4

**Worktree:** flaxen-hair_2026-11-14T2200 | **Source:** final_v3 focus decision (confirmed)

## 90-Day Plan

| Weeks | Work | Decision Point |
|-------|------|----------------|
| **Week 1** | EQUITY 24-month benchmark test vs SPY total return; route `kimi_riseoftheclaw` through intrabar resolver; kill crypto SWING emission | EQUITY alpha vs beta |
| **Weeks 2–3** | Exit-semantics fix (B4); per-class cost gate in CI; freshness gates (B9) | Can we trust the numbers? |
| **Weeks 4–8** | CRYPTO POSITION forward test (frozen rules, n≥100); commodity momentum-vs-contrarian as new pre-registered trial | Does crypto have signal after fix? |
| **Weeks 9–13** | Review forward data against gates; publish trial count | Scale or wind down |

## Go / No-Go Criteria

### GO (Promote to Live Capital)
- [ ] n ≥ 100 forward picks
- [ ] WR ≥ 55%
- [ ] PF ≥ 1.5
- [ ] pf_drift < 30%
- [ ] All 6 gates passing (finpredict-v4 scoring framework)
- [ ] 3+ months of clean forward performance

### NO-GO (Stay in Paper or Halt)
- [ ] n < 100 forward picks
- [ ] WR < 55%
- [ ] PF < 1.5
- [ ] Any gate failing
- [ ] DSR < 0.95
- [ ] Regime filter fails (bear market)

## Emergency Stop Conditions

| Condition | Action |
|-----------|--------|
| Any gate fails for 2 consecutive weeks | Halt all live trading |
| Drawdown exceeds −20% monthly cap | Halt all trading for month |
| 3 consecutive losing sessions | Halt for session, review regime |
| Data staleness > T-1 day | No new picks until refreshed |
| Exchange counterparty risk | Reduce exposure, diversify venues |

## Risk Management Rules

| Rule | Specification |
|------|---------------|
| Position sizing | Max 2% risk per trade |
| Kelly Criterion | 0.25×–0.5× full Kelly for proven edges |
| Daily loss cap | −5% |
| Monthly loss cap | −20% |
| Correlation limit | Max 1 position per correlated group |
| Regime filter | BTC > 200-EMA (crypto); SPY > 200-SMA (equity) |
| Stop loss | Technical-level (swing low/high), not fixed percentage |
| Losing streak | 3 losses → stop session |

## Statistical Gates (finpredict-v4 6-Gate Pipeline)

| Gate | Requirement |
|------|-------------|
| Gate 0: Data Quality | n ≥ 30, complete trade log, no missing prices |
| Gate 1: Statistical Significance | Bootstrap 95% CI: PF_lower > 1.0, Sharpe_lower > 0 |
| Gate 2: Walk-Forward | ≥ 60% profitable folds, mean OOS PF > 1.2 |
| Gate 3: Gross Profitability | PF > 1.5, Sharpe > 1.0, WR > 50%, Sortino > 1.5 |
| Gate 4: Money-Ready (Net) | Net PF > 1.2, Net Sharpe > 0.5, Net WR > 45%, DSR > 0.95 |
| Gate 5: Direction Validation | If directional, both sides pass Gate 4 |

## Definition of Success at Day 90

**Not "profitable."** One class with a pre-registered, benchmark-relative result and a known trial count — the first point at which "is this profitable?" becomes answerable.

## What NOT to Do in Next 90 Days

| Tempting | Why Not |
|----------|---------|
| Tune commodity COT until it passes | Failed all 4 pre-registered checks; re-fitting = false positives |
| Add mutual funds as a class | Equity risk premium, not signal; 3–6 months, Sharpe 0.2–0.5 expected, no intraday measurement |
| Mine more strategies | 170 ledgers already sampled; 4 pass at 95% vs 8.5 by chance |
| Fix FOREX 16pp gap with entries | Structural problem; entry timing won't close it |
| Turn on more emitting systems | Sizing disabled everywhere for a reason; emission is the loss source |
