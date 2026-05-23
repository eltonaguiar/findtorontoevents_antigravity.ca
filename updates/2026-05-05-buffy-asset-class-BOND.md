# BOND Asset Class Audit — Buffy
**Agent:** Buffy (Codebuff) | **Date:** 2026-05-05  
**Class Status:** THIN (WR 55.6% | PF 1.72 | n=18 | +3.41% cum PnL)

---

## Health Summary

BOND has only 18 closed trades — not statistically meaningful. WR 55.6% and PF 1.72 are directionally positive but the sample is too small to draw conclusions. Any single trade can swing WR by ±5.5pp.

## Performance

| Strategy | WR | n | PnL |
|----------|-----|---|-----|
| multi_asset_copytrader | 57.1% | 7 | +? |
| kimi_riseoftheclaw | 44.4% | 9 | +? |

## Specific Fixes

1. **NO CAPITAL ALLOCATION** — 18 trades is insufficient. Minimum 50 closed before any allocation.
2. **Keep CANDIDATE tier** — score floor at 35 is appropriate for low-vol bond strategies.
3. **Build pipeline** — bond strategies exist (bond_yield_momentum, bond_duration_rotation, bond_mean_reversion, bond_credit_spread) but aren't generating picks. Investigate why.
4. **Don't kill anything** — too few trades to identify losers. Let it run.

## Risk

Minimal — n=18 means BOND can't hurt the portfolio even if WR is actually worse than it looks. The real risk is allocating capital before the sample is meaningful.
