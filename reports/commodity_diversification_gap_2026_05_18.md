# COMMODITY Diversification Gap — Investigation Note

**Date:** 2026-05-18  
**Analyst:** Claude Sonnet 4.6  
**Trigger:** M-002 CT=F cap enforcement revealed a diversification pipeline gap

---

## Finding

M-003/M-004 plan to "diversify scanner to include GC=F, SI=F, HG=F, ZC=F, NG=F, ZW=F" — but ALL of these are in `COMMODITY_BLACKLIST` (quality_gates.py:1606).

### COMMODITY_BLACKLIST current state (2026-05-18)

| Symbol | Reason blocked | Post-fix performance |
|--------|---------------|----------------------|
| GC=F | Phase 2-D kill (WR=39.6% pre-fix) | No resolved picks |
| SI=F | Phase 2-D kill (WR=44.2% pre-fix) | WR=0% n=1 (insufficient) |
| ZC=F | Phase 2-D kill | WR=0% n=8 |
| ZW=F | Phase 2-D kill | WR=26.3% PF=0.44 n=19 |
| NG=F | Phase 2-D kill | WR=0% n=25 |
| CL=F | Phase 2-D kill (WR=16.7% pre-fix) | Not evaluated post-fix |

### NOT in COMMODITY_BLACKLIST

| Symbol | Post-fix performance | Source |
|--------|----------------------|--------|
| CT=F | WR=81.4% PF=6.33 n=43 | multi_asset_cot |
| HG=F | No resolved picks (n=36 total, all from multi_asset_copytrader) | multi_asset_copytrader |
| PL=F | No resolved picks (n=20 total, all from multi_asset_copytrader) | multi_asset_copytrader |

---

## Impact on M-002 Cap

With M-002 (CT=F weekly cap) now enforced at 40%:
- CT=F picks are throttled when >40% of 7-day COMMODITY window
- No other COT source generates non-CT=F COMMODITY picks at scale (multi_asset_cot only covers CT=F, ZW=F, KC=F — last two are blacklisted)
- HG=F and PL=F have picks from `multi_asset_copytrader` but no resolved outcomes to evaluate edge

**Practical effect:** M-002 will slow CT=F intake; net effect on COMMODITY MONEY_READY path is to reduce signal velocity until non-CT=F signals accumulate and resolve.

---

## Verdict

M-003/M-004 items in MASTER_ACTION_PLAN should be re-evaluated as follows:

| Item | Status | Actual situation |
|------|--------|-----------------|
| M-003: Include GC=F, SI=F, HG=F, ZC=F | NOT DONE (misassessed as DONE) | All in COMMODITY_BLACKLIST; post-fix data doesn't justify unblock |
| M-004: Include CL=F, NG=F, ZW=F | NOT DONE | All in COMMODITY_BLACKLIST with catastrophic post-fix WR=0% |

**Action required:**
- Do NOT remove symbols from COMMODITY_BLACKLIST without STRATEGY_INVESTIGATION + MUTATION_THREE_AXIS_PROTOCOL
- Monitor HG=F and PL=F (from multi_asset_copytrader) — they are NOT in the blacklist and will accumulate resolved picks over time
- Once HG=F or PL=F reaches n≥30 resolved with WR≥50%, they can be promoted as the diversification path
- Re-evaluate GC=F (gold) when n≥50 post-fix resolved picks are available — gold's Phase 2-D kill was on n=91 at WR=39.6%, which may have been resolver-corrupted

**Estimated timeline:** HG=F/PL=F reaches n≥30 resolved: 4-6 weeks at current generation rate.

---

## Recommendation for COMMODITY MONEY_READY Path

1. M-002 CT=F cap enforced ✅ — reduces concentration
2. COMMODITY pipeline will slow — expected and acceptable
3. Focus CT=F on COT signal quality (M-001 stale gate ✅)
4. Allow HG=F and PL=F to accumulate resolved picks naturally
5. Review GC=F at n≥50 post-fix resolved picks for potential re-inclusion

**C-006 rapid_fire deferred** (no closed picks). **COMMODITY MONEY_READY ETA:** 2026-06-17 (30-day roadmap) — now at risk if HG=F/PL=F accumulation is slow.
