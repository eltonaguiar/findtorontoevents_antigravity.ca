# FOREX Mutation Decisions — 2026-05-06

## Context
719 FOREX trades across 5 strategies. Per mutation_analysis.py output
and closed_picks.json per-strategy directional analysis.

## Decision Tree Results

### 1. cta_cross_asset_tsmom (117 FOREX trades)
**Status: KEEP AS-IS**
- FOREX WR: 53.0% (63/117) — above 50% threshold
- FOREX avg PnL: +1.26% — positive edge
- USDJPY=X alone: n=62, WR 67.7%, PF 1.64, +64.6% sum
- Mutation axis: NONE — live edge confirmed

### 2. ig_contrarian_sentiment (195 FOREX trades)
**Status: SHORT-ONLY MUTATION**
- SHORT: 42 trades, WR 57.1% (24W/18L), PF 1.54, +8.2% sum
- LONG: 153 trades, WR 15.7% (24W/129L), PF 0.35, -17.1% sum
- Spread: 41.4pp — strong directional asymmetry
- Action: Block LONG direction via BLOCKED_DIRECTION_TRIPLES. Keep SHORT.
- Mutation axis: DIRECTION (invert LONG, preserve SHORT)

### 3. myfxbook_retail_contrarian (128 FOREX trades)
**Status: SHORT-ONLY MUTATION**
- SHORT: 13 trades, WR 46.2%, +0.96% avg
- LONG: 113 trades, WR 10.6%, -1.8% avg
- Spread: 35.6pp — confirmed direction asymmetry
- Action: Block LONG direction via BLOCKED_DIRECTION_TRIPLES. Keep SHORT.
- Mutation axis: DIRECTION

### 4. forex_rsi2_mean_reversion (115 FOREX trades)
**Status: KEEP**
- SHORT: 11 trades, WR 27.3%, -2.1% avg
- LONG: 104 trades, WR 3.8%, avg PnL +0.44% (mean reversion TP hit)
- Break-even to slightly positive. No block needed.
- Mutation axis: NONE

### 5. quan_engine_swing (30 FOREX trades)
**Status: SHORT-ONLY MUTATION**
- SHORT: 5 trades, WR 60.0%, PF 1.80
- LONG: 25 trades, WR 26.0%, PF 0.52
- Spread: 34pp — confirmed direction asymmetry
- Action: Block LONG direction via BLOCKED_DIRECTION_TRIPLES. Keep SHORT.
- Mutation axis: DIRECTION

## Summary Table

| Strategy | Action | Mutation Axis | Rationale |
|---|---|---|---|
| cta_cross_asset_tsmom | KEEP | None | 53% WR, PF 1.26, live edge |
| ig_contrarian_sentiment | BLOCK LONG | DIRECTION | 57% SHORT WR vs 16% LONG WR, 41pp spread |
| myfxbook_retail_contrarian | BLOCK LONG | DIRECTION | 46% SHORT WR vs 11% LONG WR, 36pp spread |
| forex_rsi2_mean_reversion | KEEP | None | Break-even, no action |
| quan_engine_swing | BLOCK LONG | DIRECTION | 60% SHORT WR vs 26% LONG WR, 34pp spread |

## Next Steps
1. Add BLOCKED_DIRECTION_TRIPLES entries for ig_contrarian_sentiment (FOREX, LONG)
2. Add myfxbook_retail_contrarian (FOREX, LONG) to BLOCKED_DIRECTION_TRIPLES  
3. Add quan_engine_swing (FOREX, LONG) to BLOCKED_DIRECTION_TRIPLES
4. Monitor cta_cross_asset_tsmom FOREX performance — already strong
5. Validate SHORT edge for ig_contrarian_sentiment with n>=50 before full conviction

## References
- Mutation three-axis protocol: docs/MUTATION_THREE_AXIS_PROTOCOL.md
- FOREX edge data: alpha_engine/data/closed_picks.json (asset_class=FOREX)
