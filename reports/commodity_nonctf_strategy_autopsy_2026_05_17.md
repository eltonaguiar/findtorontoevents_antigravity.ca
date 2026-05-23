# COMMODITY Non-CT=F Strategy Autopsy — 2026-05-17

## Summary

Three-axis autopsy (symbol split) on COMMODITY strategies reveals that the strategies
`cta_replicator`, `multi_asset_copytrader`, and `multi_asset_cot` have dramatically
different performance on CT=F (cotton) vs all other commodity symbols.

**Recommendation: Block these 3 strategies for non-CT=F COMMODITY symbols.**
(Requires user approval per CLAUDE.md before implementation.)

## Data (from closed_picks.json, 2026-05-17T19:00Z)

### CT=F (Cotton Futures) — strategies with edge:

| Strategy | n | WR | avg_pnl |
|----------|---|----|---------|
| multi_asset_copytrader | 116 | 84% | +3.63% |
| multi_asset_cot | 114 | 87% | +3.80% |

### Non-CT=F — strategies WITHOUT edge:

| Strategy | Symbol | n | WR | avg_pnl |
|----------|--------|---|----|---------|
| cta_replicator | CL=F (Oil) | 47 | 19% | -1.47% |
| cta_replicator | NG=F (Gas) | 24 | 0% | -3.00% |
| cta_replicator | ZC=F (Corn) | 8 | 0% | -3.78% |
| multi_asset_cot | various | 17 | 29% | -1.51% |
| multi_asset_copytrader | various | 15 | 0% | -2.62% |
| combined_confidence_strategy | various | 6 | 0% | -3.34% |

### Aggregate Impact

| Subset | n | WR | PF |
|--------|---|----|----|
| CT=F only | 231 | 85.7% | 7.84 |
| Non-CT=F only | 123 | 12.2% | 0.23 |
| All COMMODITY (current) | 354 | 60.2% | 2.28 |
| If blocked for non-CT=F | 239 | 82.8% | 6.67 |

## Root Cause

`cta_replicator`, `multi_asset_copytrader`, and `multi_asset_cot` appear to use
cotton-specific COT positioning signals that work for CT=F (where speculators are
contrarian predictors) but have no predictive value for energy/grain commodities
(CL=F, NG=F, ZC=F, ZS=F) where the COT structure differs.

The DSR analysis (cot_step7_friction_adjusted_mc.json, 2026-05-17) already shows
friction-adjusted DSR=0.0 on CT=F. The non-CT=F picks have even lower raw SR.

## Relationship to Concentration Cap

If these 3 strategies are blocked for non-CT=F:
- Remaining picks: n=239, CT=F share = 231/239 = 96.7%
- This makes concentration WORSE (97% vs 65%)
- The concentration cap raise is STILL needed to pass money_ready_verdict()

So the two actions are complementary, not alternatives:
1. Block 3 strategies for non-CT=F (removes losing picks, PF 2.28→6.67)
2. Raise concentration cap to ≥0.97 (or e.g. 0.85 allows CT=F through)

## Escalation Ladder (STRATEGY_INVESTIGATION_BEFORE_KILL.md)

This autopsy satisfies Stage 1 (observe: done) and the three-axis investigation
required before Stage 4 (Block). Cross-asset check: these strategies work for CT=F
but not for other COMMODITY symbols — this is a valid per-symbol block, not a
full strategy kill.

**These are NOT soft kills** — the strategies remain active for CT=F. Only the
non-CT=F instances are blocked.

## Actions Required (both need explicit user approval)

1. Add to BLOCKED_ASSET_STRATEGY_PAIRS (per-symbol would need a new gate):
   - `('COMMODITY', 'cta_replicator')` for symbols ≠ CT=F
   - `('COMMODITY', 'multi_asset_copytrader')` for symbols ≠ CT=F
   - `('COMMODITY', 'multi_asset_cot')` for symbols ≠ CT=F

   Note: Current BLOCKED_ASSET_STRATEGY_PAIRS is class-level, not symbol-level.
   A symbol-level block would need either:
   (a) A new per-symbol block structure in quality_gates.py
   (b) Adding CT=F-whitelist logic in these strategies directly
   (c) Blocking the full strategy pair (kills CT=F picks too — NOT recommended)

2. Raise `CONCENTRATION_CAP_BY_CLASS = {"COMMODITY": 0.97}` (or 0.85 as previously
   discussed — 0.85 still needed even if non-CT=F blocks are applied).

## Alternative: Simpler Full Class Block

If adding per-symbol block logic is too complex, consider blocking the full
`('COMMODITY', 'cta_replicator')` pair — but this would also kill the n=0 CT=F
picks from cta_replicator (cta_replicator has 0 CT=F resolved picks — all CT=F
from multi_asset_cot and multi_asset_copytrader). So blocking cta_replicator
fully for COMMODITY is safe and removes 83 losing picks without affecting CT=F.

**Simpler approach:**
- Block `('COMMODITY', 'cta_replicator')` fully (83 losing non-CT=F picks, 0 CT=F picks)
- Block `('COMMODITY', 'multi_asset_copytrader')` for non-CT=F symbols only (15 losing picks, 116 CT=F winners)
- Block `('COMMODITY', 'multi_asset_cot')` for non-CT=F symbols only (17 losing picks, 114 CT=F winners)

## Generated

2026-05-17T19:05Z — Session BB
