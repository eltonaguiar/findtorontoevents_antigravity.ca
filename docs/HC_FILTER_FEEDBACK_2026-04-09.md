# HC Filter Feedback - 2026-04-09

## Summary
Recent HC filter changes have made the classification **too strict** - resulting in **0 picks** getting HC tier (S/A/B).

## Recent Code Changes (Last 5 Commits)

| Commit | Change |
|--------|--------|
| 1f4fb5d98b | fix: Add forward_trades validation gate for HC tier classification |
| 1e17cd6392 | fix: HC filter now falls back to strategy_performance.json for forward_wr |
| f42f013239 | fix(hc-filter): align frontend/backend, add PROBATION blacklist, restore HF tier support |
| 95ba34d293 | fix: Extract forward_wr/forward_trades from extra_json in CSV exports |
| ca5f74c4ad | feat(audit): HC filter v3 Gate 9 correlation + ordered filter |

## Key Improvements Made

1. **CSV Export Fix**: `_deriveForwardWR` and `_deriveForwardTrades` now parse `extra_json` including nested `ml_features_at_entry` paths
2. **Fallback to strategy_performance.json**: HC filter now reads win rates from closed picks data for strategies without explicit forward_wr
3. **Forward trades validation gate**: Requires `n >= 5` trades before ANY HC tier classification
4. **Overconfidence kill**: Rejects picks with `conf > 0.90` AND `< 20` trades

## CRITICAL ISSUE: Zero HC Picks

**Current State:**
- Active picks: 111 total
- HC tier (S/A/B): **0 picks** (0%)
- Non-HC picks: 111 (100%)

**Root Cause Analysis:**

The validation gate added at line 720 requires `n >= min_n (5)` forward_trades BEFORE any tier classification. However:

1. **Most active picks come from copy traders** - they have `forward_wr` but not from `strategy_performance.json`
2. **ML-enhanced strategies** - have excellent track records (e.g., 80.8% WR) but the fallback isn't being triggered properly
3. **min_n = 5** may be too high for some edge strategies that prove themselves quickly

**Strategy Distribution in Active Picks:**
- clone_hl_copy_lb_None: 23 picks (copy trader)
- clone_hl_copy_Auros_66M: 11 picks
- clone_hl_copy_PensionFund_24M: 9 picks
- cta_cross_asset_tsmom: 6 picks
- ml_enhanced_RENDERUSDT_1h_D: 1 pick (80.8% WR)
- ml_enhanced_FETUSDT_1d_B: 1 pick (80.8% WR)

## Recommendations

1. **Lower min_n threshold** to 3 for proven strategies (those with WR > 60% in strategy_performance)
2. **Add copy trader bypass** - copy traders with positive forward_wr should pass without requiring 5 trades
3. **Add tier-specific min_n**: S tier = 10, A tier = 5, B tier = 3
4. **Debug the fallback** - verify strategy_performance.json is being loaded correctly

## Action Items

- [ ] Investigate why strategy_performance fallback isn't populating HC tiers
- [ ] Add logging to trace why picks are being rejected at the gate
- [ ] Consider relaxing min_n for strategies with >60% WR
- [ ] Add copy trader special handling

---
*Generated: 2026-04-09*