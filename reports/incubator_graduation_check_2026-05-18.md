# Incubator Graduation Check — live forward_summary data

Bridged 189 forward-tested strategies from `incubator/forward_test.db::forward_summary` through the graduation gate (`StrategyGraduationCriteria` + `EarlyHatchCriteria`).

- **Standard-graduation passes: 0 / 189**
- Early-hatch-only passes: 0

`min_forward_days` is not evaluated (forward_summary has no start date); these are *quality-bar* passes — WR / Sharpe / MDD / PnL / trades only.

**No strategy clears the standard graduation quality bar.**

## Why strategies fail the standard bar (n)

- Insufficient trades: 189
- Sharpe too low: 189
- P&L too low: 189
- Win rate too low: 188
- P&L not positive: 188

## Verdict

No forward-tested strategy clears the graduation quality bar. The incubator currently holds no graduate-ready signal source — consistent with reports/EDGE_VERDICT_2026-05-18.md.