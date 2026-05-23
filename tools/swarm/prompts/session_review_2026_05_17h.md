# Session Review — 2026-05-17 Round 8

## Context
Quant/systems review. Continuation of the 2026-05-17 session (rounds 1-7 previously reviewed). Session shipped M-041 through M-047 gates, weekly filter, CRYPTO T1 cert, FOREX copytrader bypass, C5 resolver fix. This round covers the mutation analysis work done after round 7.

## Session Deliverables (this round)

### 1. Matrix Symbol Gates Updated (SHIPPED — commit 2f25fe1d25)
- `alpha_engine/data/matrix_symbol_gates.json` updated with fresh three-axis mutation analysis data
- **New cta_replicator blocks**: NG=F (0% WR, n=24), CL=F (19% WR, n=47) — explains COMMODITY 7d PF=0.64 drag
- **New multi_asset_copytrader blocks**: 9 JPY-crosses + metals (EURJPY=X 1.95%/n=154, GBPJPY=X 10.3%/n=87, CADJPY=X 9.76%/n=41, AUDJPY=X 3.57%/n=84, HG=F 0%/n=33, SI=F 2.22%/n=45, NZDUSD=X 15.3%/n=59, KC=F 4.55%/n=22, USDJPY=X 3.01%/n=133)
- **Remaining mac passing**: EURGBP=X 70.8%/n=48, GBPUSD=X 66.7%/n=30, CT=F 57.1%/n=175 (strengthens FOREX_COPYTRADER_ENABLE case)
- **quan_engine**: added LTCUSDT 23.6%/n=89 + RENDERUSDT 30.8%/n=240
- 94/94 quality_gates tests pass; 9/9 new gate unit tests pass

### 2. ig_contrarian_sentiment LONG Direction — PENDING APPROVAL
- Axis 1 (direction flip): SHORT 61.4% WR (n=57) vs LONG 16.8% WR (n=197) — 45pp spread
- Proposed: add `("ig_contrarian_sentiment", "LONG")` to `BLOCKED_ASSET_STRATEGY_PAIRS`
- Not yet added — per CLAUDE.md requires explicit user approval
- Report: `reports/mutation_investigation_2026_05_17.md`

### 3. PRs Merged Since Round 7
- **PR #1127**: net-pnl PF (C2) + exclude BLOCKED_SOURCE_SYSTEMS from aggregate (C3) — ✅ MERGED
- **PR #1131**: ETF+Bond scanner failover (yfinance absent in CI) — ✅ MERGED

### 4. Still Open PRs
- **PR #1130**: gap-aware TP/SL fill — C1 Path A (OHLC-based fill)
- **PR #1132**: C1 Paths B/C + D2 systems[] dedup — `aggregated_picks` builder pointed at deduped_closed

### 5. Known External Blockers (unchanged)
- MySQL stale row DELETE (655k rows) — needs PA console
- UEPS_ENABLE_PEAD=1 — needs PA console

## Swarm Questions

1. **ig_contrarian_sentiment LONG block**: Is the evidence sufficient to add to BLOCKED_ASSET_STRATEGY_PAIRS? n=197 LONG at WR=16.8% is the Axis 1 direction-flip per protocol. What additional validation is needed before user approval?

2. **multi_asset_copytrader after symbol blocks**: The JPY-cross blocks should dramatically improve multi_asset_copytrader's apparent WR (from 21.7% overall to ~60%+ on remaining symbols). Should FOREX_COPYTRADER_ENABLE=1 be promoted to default ON now that the worst symbols are blocked? (Currently waiting for n≥30 per-source, but n=17 was for ALL multi_asset_copytrader FOREX, including the now-blocked JPY-crosses.)

3. **cta_replicator after CL=F/NG=F blocks**: cta_replicator USDJPY=X is 70.5% WR (n=112) — T1-grade. Should cta_replicator be reclassified as a FOREX winner (previously classified as a drag in COMMODITY)?

4. **Axis 4 (threshold-normalization)**: multi_asset_copytrader, rapid_fire, quan_engine all flagged as Axis 4 candidates. After symbol blocks are in place, is there any immediately actionable Axis 4 work (ATR-normalized entry thresholds)? Or wait for 30d post-block forward data?

5. **Secondary direction-flip candidates**: forex_rsi2_mean_reversion LONG 7.4% WR (n=108) is catastrophic. cta_cross_asset_tsmom LONG 29.8% (n=84) is below floor. Should these be investigated at the same level as ig_contrarian_sentiment, or wait for n thresholds?

## Format
```json
{
  "verdict": "DONE | MOSTLY_DONE | NEEDS_WORK",
  "ig_contrarian_long_approval": "APPROVE | NEEDS_MORE_DATA | DEFER",
  "forex_copytrader_gate_recommendation": "PROMOTE_DEFAULT_ON | KEEP_N30_THRESHOLD | PAPER_ONLY",
  "cta_replicator_reclassification": "FOREX_WINNER | KEEP_WATCHING | NO_CHANGE",
  "axis4_recommendation": "DO_NOW | WAIT_30D | SKIP",
  "direction_flip_queue": ["systems worth investigating next"],
  "remaining_code_actionable": ["item1"],
  "summary": "one paragraph"
}
```
