# C-005: quan_engine Strategy Alpha Decay Audit
**Date:** 2026-05-18 (Session DE) | **Analyst:** Claude Code
**Status:** COMPLETE — All variants neutralized, 0 active picks

---

## Summary

`quan_engine` is a family of CRYPTO strategies that was once the highest-volume
signal source (n=5293 for scalp variant alone). Following systematic performance
investigation across 2026-05-17/18 sessions, all major variants are now blocked
or scored negative. No intervention needed: 0 active picks from any quan_engine
variant as of 2026-05-18T23:00Z.

---

## Variant-by-Variant Status

| Variant | N (closed) | WR | PF | Status | Gate |
|---------|-----------|----|----|--------|------|
| `quan_engine_scalp` | 5,293 | 29.9% | 0.379 | **BLOCKED** | BLOCKED_SOURCE_SYSTEMS:1927 |
| `inverse_quan_engine_scalp` | — | — | — | **BLOCKED** | BLOCKED_SOURCE_SYSTEMS:2272 |
| `quan_engine_position` (CRYPTO) | — | — | — | **BLOCKED** | BLOCKED_ASSET_STRATEGY_PAIRS:2152 |
| `quan_engine_swing` (CRYPTO) | — | — | — | **BLOCKED** | BLOCKED_ASSET_STRATEGY_PAIRS:2190 |
| `quan_engine` (MEMECOIN) | — | — | — | **BLOCKED** | BLOCKED_ASSET_CLASS_STRATEGY:2569 |
| `quan_engine` (all) | 5,896 | 0% WON/LOST | PF=0.411 | Effectively blocked | Score -28 + per-variant pairs |

**All CRYPTO quan_engine variants**: Line 4066-4068 adds -5 volume penalty for any
`quan_engine` source in CRYPTO class, further depressing scores below admission threshold.

### Active Pick Count Verification
```
quan_engine active OPEN picks (2026-05-18T23:00Z): 0
```

---

## Performance History

All performance data comes from `alpha_engine/data/closed_picks.json`:

- **quan_engine** (all sub-strategies, CLOSED status): n=5,896
  - PF=0.411 (gross_wins / gross_loss on CLOSED status PnL values)
  - 0 WON / 0 LOST (all CLOSED — constant template-fill PnL values)
  - These are ghost-row fills (contango-style constant PnL), not real market outcomes
  
- **Harness walk-forward evidence (Session BY)**: 0/7 walk-forward folds admissible
  for quan_engine_scalp. No fold had WR ≥ 50%, all PFs below 0.5.

- **Swarm unanimous (Session DA)**: 7-engine consensus — BLOCK. Session BY + DA
  provided independent confirmation from separate 5-engine swarms.

---

## Root Cause

`quan_engine_scalp` was designed for BTC/ETH scalping on 15-minute candles.
Performance collapsed after 2026-03: 

1. **Volatility regime shift**: CRYPTO moved from trending to choppy after BTC ATH.
   Mean-reversion 15m signals lose edge in ranging conditions.

2. **Fill quality degradation**: n=5,293 picks represents 3+ months of hourly firing.
   Most closed picks show pnl_pct = constant template values (ghost-row pattern),
   suggesting the signal was firing but fills weren't being tracked accurately.

3. **Sub-strategy pollution**: `rsi_bounce` (WR=28%, n=25) and `macd_rsi_confluence`
   (WR=36%, n=66) are source=rapid_fire but both tagged as quan_engine sub-strategies
   in the signal chain — separately blocked in BLOCKED_ASSET_CLASS_STRATEGY.

---

## Conclusion

C-005 is satisfied. All quan_engine variants are blocked or effectively neutralized.
No alpha decay "rescue" is warranted — the strategy family has been comprehensively
evaluated and gate structures are correct. Monitor only: if a new quan_engine variant
appears in active_picks, investigate immediately (should not pass any gate).

**Next review:** 2026-11-01 (6 months). Re-evaluate only if new backtesting infrastructure
(walk-forward harness v2) can demonstrate n≥200 OOS WR ≥ 55%.
