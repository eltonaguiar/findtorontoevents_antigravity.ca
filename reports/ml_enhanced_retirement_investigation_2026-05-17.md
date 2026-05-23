# ml_enhanced_* Retirement Investigation — 2026-05-17

**Triggered by:** Session O swarm Q4 recommendation ("formally retire dormant ml_enhanced_* variants")  
**Conclusion:** DO NOT block. ml_enhanced_* is STILL ACTIVE under a revised naming convention.

## Finding: Two naming conventions coexist

The strategy emission monitor (149 distinct "long-named" strategies in closed_picks.json)
reported 153 DORMANT strategies, mostly `ml_enhanced_SYMBOL_TIMEFRAME_VARIANT_MODEL` variants
last emitted Feb–Apr 2026. This drove the swarm Q4 recommendation.

**However**, the active_picks.json tells a different story:

| Convention | Example | Active picks (2026-05-17) | Last emit |
|---|---|---|---|
| Short-named (new) | `ml_enhanced_DYDXUSDT` | **24** | 2026-05-17 (today) |
| Long-named (old) | `ml_enhanced_FETUSDT_1d_B_lightgbm` | 12 | 2026-05-17 (today) |
| **Total** | | **36** | 2026-05-17 |

Both naming conventions have active picks as of today. Blocking `ml_enhanced` as a
source system would kill 36 live open positions.

## Root cause of "dormancy" appearance

The emission monitor `_last_emit_date()` checks both `strategy` and `source_system` fields.
The 149 "long-named" strategy keys in closed_picks.json last emitted in Feb–Apr 2026 because:
1. The old per-symbol-per-timeframe-per-model strategy naming was deprecated
2. The new system emits under short-named keys or consolidated source_system identifiers
3. The closed_picks.json snapshot predates the naming migration — the new picks resolve
   under the new naming and won't backfill the old long-named keys in closed_picks.json

## Performance assessment

Resolved picks in closed_picks.json: **0** (no outcome=WIN/LOSS/HIT/MISS records found).  
This means:
- We cannot compute WR/PF for ml_enhanced_* from closed_picks.json alone
- The picks appear to be open/stale with missing outcome records
- Trust score range: 1–7, avg 3.3 (from trust_score backfill 2026-05-16 session N)
- 5/36 active picks pass HC gate 7 (trust_score ≥ 6)

## Recommendation

**NO ACTION on BLOCKED_SOURCE_SYSTEMS.** The "dormancy" was a naming-convention artifact.

Correct approach:
1. The old long-named strategies (149 variants) are naturally phased out as the new naming
   takes over. No block needed — they have zero active picks and zero resolved picks in the
   current snapshot.
2. Monitor short-named `ml_enhanced_*` for resolved outcome accumulation. Once n≥50 resolved
   picks under the new naming, run a full performance autopsy.
3. **Schedule:** Re-evaluate after MySQL ghost-row purge (2026-05-24) when quan_engine
   stale rows are cleared. This may also unlock ml_enhanced resolved-pick records.

## Action taken

Investigation doc written (this file). No quality_gates.py changes made.

## Mutation protocol checklist (STRATEGY_INVESTIGATION_BEFORE_KILL.md)

| Step | Status | Detail |
|---|---|---|
| Step 1 — Sample check | BLOCKED | No resolved picks in closed_picks.json |
| Step 2 — Direction autopsy | BLOCKED | No resolved picks |
| Step 3 — Confidence bucket | BLOCKED | No resolved picks |
| Step 4 — Asset class split | N/A | All CRYPTO |
| Step 5 — Winning subset n≥100 | N/A | Cannot compute without resolved picks |
| **Kill verdict** | **NOT JUSTIFIED** | Cannot block without resolved-pick evidence |
