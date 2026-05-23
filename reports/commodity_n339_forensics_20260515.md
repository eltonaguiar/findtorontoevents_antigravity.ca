# COMMODITY n=339 Forensics — COT Over-Emission Impact

**Date:** 2026-05-15 | **Priority:** P0 | **Source:** dashboard_data.json 2026-05-15T20:20Z

## TL;DR

The COMMODITY headline **PF=2.36, WR=60.5%, n=339** is inflated by COT over-emission artifacts.
Real post-dedup estimate: **n ≈ 218, PF unknown** (requires DB purge to verify).

## Evidence

### 1. COT Over-Emission (from `reports/cot_pipeline_audit_20260514.md`)

- Paper pilot had 101 closed picks from only **5 unique CFTC weekly releases** (20:1 emission ratio)
- After dedup to 1-pick-per-release: WR 90.1% → **40.0%**, PF 2.73 → **0.17**
- PR #941 fixed look-ahead timing (2026-05-13) — no timing bias remains
- PR #961 fixed future over-emission (2026-05-13) — go-forward is clean
- **Historical picks in DB were NOT retroactively purged**

### 2. `multi_asset_cot` System (COMMODITY-only)

```
closed = 126
wins   = 99
losses = 27
WR     = 78.6%   ← inflated by over-emitted duplicate wins
PF     = 4.34    ← inflated
```

Estimated real contribution (5 unique signals × 1 deduped pick each):
- real_n ≈ 5
- WR ≈ 40%, PF ≈ 0.17 (from dedup audit)
- Duplicate picks: **~121 out of 126 closed picks are over-emission artifacts**

### 3. COMMODITY asset_class_health Impact

```
Current (inflated):  n=339, WR=60.5%, PF=2.36
multi_asset_cot contributes: 126 resolved picks (99W + 27L)
Estimated deduped multi_asset_cot: 5 resolved picks (2W + 3L using 40% WR)
Estimated post-dedup COMMODITY: n ≈ 218, wins ≈ (205 - 97) = 108, losses ≈ (134 + 24 - 27) = 131
Post-dedup WR estimate: 108/239 ≈ 45%  ← sub-T2 WR floor (50%)
Post-dedup PF: unknown without PnL breakdown, but expect <1.5
```

**Verdict: COMMODITY does NOT qualify as Tier-2 on post-dedup data.**

## Status of Fixes

| Fix | Status | Remaining issue |
|---|---|---|
| COT look-ahead timing | ✅ Fixed PR #941 | None |
| Future over-emission | ✅ Fixed PR #961 | None for new picks |
| Historical over-emission purge | ❌ NOT DONE | n=339 headline still inflated |

## Required P0 Action

**Purge duplicate COT picks from DB** — identify picks from `multi_asset_cot` system
where `source_system = 'multi_asset_cot'` AND `cftc_report_date` is the same for multiple
picks in the same symbol+direction bucket. Keep 1 per (symbol, direction, cftc_report_date).

SQL template (requires DB access):
```sql
-- Count duplicates per COT signal
SELECT symbol, direction, cftc_report_date, COUNT(*) as n
FROM picks
WHERE source_system = 'multi_asset_cot'
GROUP BY symbol, direction, cftc_report_date
HAVING COUNT(*) > 1;
-- Expected: ~24 groups with ~5 picks each = ~96-121 duplicates
```

## What Tier-2 Claim Can Be Made Today

**CANNOT claim Tier-2 for COMMODITY.** The pre-dedup headline is an artifact.

Non-COT COMMODITY sources (estimated n≈213) need independent WR/PF calculation.
From `recent_closed` data (previous session analysis):
- `cot_positioning`: n=32, WR=59%, PF=1.46
- `cftc_cot_commercial_signal`: n=32, WR=56%, PF=1.29
- `connors_rsi2`: n=5, WR=20%, PF=0.25

These non-COT COMMODITY sources show T2-range PF (1.29-1.46) — potentially salvageable
after DB purge removes the COT artifacts that mask the real signal.

## References

- `reports/cot_pipeline_audit_20260514.md` — full over-emission timeline
- `audit_trail/quality_gates.py` — COT not in BLOCKED pairs yet (only timing fix)
- PR #941, PR #961 (COT timing + dedup)
