# FOREX Recovery — multi_asset_copytrader Sub-Filter

**Date:** 2026-05-17  
**Status:** DOCUMENTED — not yet unlocked (pending carry-filter condition)  
**Source:** `alpha_engine/data/closed_picks.json` last-30 FOREX picks

---

## Finding

FOREX class-wide is HARD_DISABLED (PF=0.85 all-time, n=251). However, a rolling analysis of the last 30 FOREX closed picks reveals concentrated recovery:

| Source System | n (last 30) | WR | PF |
|---|---|---|---|
| `multi_asset_copytrader` | 17 | **64.7%** | **1.87** |
| `cta_replicator` | 12 | 33.3% | 0.75 |
| `combined_confidence_strategy` | 1 | 100% | — (n too small) |
| **Combined last-30** | **30** | **53.3%** | **1.56** |

**Recovery driver:** `multi_asset_copytrader` FOREX picks are performing at T2+ levels (PF=1.87, WR=64.7%). `cta_replicator` remains negative (PF=0.75) and is the primary drag.

Also confirmed by PR #1126 hourly audit:
- FOREX 7d PF: 0.14 → **1.60** (STRONG RECOVERY — PR #687 JPY-cross fix)
- FOREX 30d PF: 0.97 → **2.30**

---

## Unlock Condition Check

The weekly filter defined: _"Unlock condition: 30-trade rolling WR>50% AND PF>1.0 post-carry filter"_

| Condition | Status |
|---|---|
| n≥30 rolling | ✅ n=30 |
| WR>50% | ✅ 53.3% |
| PF>1.0 | ✅ PF=1.56 |
| **post-carry filter** | ❌ NOT VERIFIED — `multi_asset_copytrader` picks are not carry-filtered |

**Verdict:** Class-wide rolling unlock condition is numerically met, but the protocol requires "post-carry filter" which hasn't been verified for `multi_asset_copytrader` specifically.

---

## Recommended Path

### Option A: Targeted Source-System Unlock (preferred)
Add `FOREX_COPYTRADER_ENABLE=1` gate (default OFF) to `audit_trail/quality_gates.py`:
- Bypasses `FOREX_HARD_DISABLE` only for `source_system = 'multi_asset_copytrader'`
- Requires n≥30 for `multi_asset_copytrader` specifically (currently n=17 — needs 13 more)
- PAPER TRADE ONLY until n≥30 per-source condition met

### Option B: Class-wide partial unlock
Lift `FOREX_HARD_DISABLE` to `FOREX_SOFT_DISABLE` (blocks by default but allow `trust_score >= 9`)  
— Less targeted, higher risk of `cta_replicator` contamination

### Option C: Wait for carry-filter verification
Run `tools/research/forex_carry.py` on `multi_asset_copytrader` FOREX picks, verify carry-factor overlap.
Then grant a formal unlock.

**Decision: Option A (targeted source-system unlock) when n≥30 per-source.**

---

## Next Steps

1. Monitor `multi_asset_copytrader` FOREX picks until n≥30 (need ~13 more)
2. At n≥30: add `FOREX_COPYTRADER_ENABLE=1` gate to `quality_gates.py`
3. Check if `tools/research/forex_carry.py` carry-factor aligns with these picks
4. Review `cta_replicator` for potential block per three-axis protocol (WR=33.3%, n=12)
5. Enable `FOREX_COPYTRADER_ENABLE=1` in paper-trade mode only once n=30 confirmed

---

## cta_replicator Watch

`cta_replicator` FOREX: WR=33.3%, PF=0.75, n=12 (last 30d). Not yet at n≥20 threshold for formal block.  
**Monitor at n≥20.** If WR<40% persists → three-axis autopsy per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

---

*Produced by Claude Code (claude-sonnet-4-6) autonomous session 2026-05-17*
