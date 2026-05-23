# COMMODITY Asset Class Audit — Buffy
**Agent:** Buffy (Codebuff) | **Date:** 2026-05-05  
**Class Status:** STABLE (WR 44.3% | PF 2.04 | n=673 recent | +11.09% cum PnL)

---

## Health Summary

COMMODITY is net profitable (+11.09%) but WR at 44.3% is below breakeven. The positive PnL comes from larger wins than losses (good RR profile). Dominated by multi_asset_copytrader which handles 530 of 673 trades.

## Top Performers

| Strategy | WR | n | Cum PnL |
|----------|-----|---|---------|
| multi_asset_copytrader | 45.7% | 530 | +? |
| cta_replicator | 40.8% | 103 | -? |
| multi_asset_cot | ? | 16 | +14.43% |

## Sub-Class Blacklist (quality_gates.py)

Per Phase 2-D panel (2026-04-29): COMMODITY universe restricted to **HG=F (copper) + PL=F (platinum)** only. Killed symbols:

| Symbol | WR | n | Cum PnL | Reason |
|--------|-----|---|---------|--------|
| CT=F (cotton) | 8.3% | 12 | -8.41% | KILLED |
| KC=F (coffee) | 8.3% | 12 | -6.02% | KILLED |
| CL=F (crude) | 16.7% | 6 | -5.25% | KILLED |
| SI=F (silver) | 44.2% | 181 | -4.47% | KILLED |
| GC=F (gold) | 39.6% | 91 | -0.52% | KILLED |

## Specific Fixes

1. **Verify COMMODITY_BLACKLIST is enforced** — check `COMMODITY_SUBCLASS_KILL_DISABLED` env var
2. **Parameter tuning for cta_replicator** — 40.8% WR on 103 trades. Near-breakeven PnL (-0.02% avg). Small tweaks could flip to profitable. All 3 swarm engines recommend rehab.
3. **Score floor lowered to 35** (2026-05-03) — Commods can't accumulate crypto-only score boosters. Floor=40 was adequate. Verify picks are flowing after the 35 floor.
4. **multi_asset_copytrader** — 45.7% WR is below 50% but cumulative PnL is positive. Keep but don't allocate more capital without WR improvement.

## Risk

COMMODITY has thin strategy diversity — multi_asset_copytrader is 78.7% of all trades. If copytrader degrades, the entire class collapses. Need additional commodity-specific strategies (seasonal, COT positioning, GSCI momentum).
