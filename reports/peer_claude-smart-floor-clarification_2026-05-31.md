# Peer Report — Smart-Floor Wording Mismatch on /audit/pick_funnel.html

**Author:** Claude (worktree wf_860213bb-35d-3)
**Date:** 2026-05-31
**Severity:** P2 / OPEN
**Surface:** `audit_dashboard/pick_funnel.html`
**Generator:** `tools/audit_pick_funnel/extract_funnel.py`
**Snapshot:** `audit_dashboard/data/pick_funnel_90d.json::smart_picks_db_stats`

## TL;DR

A blackbox peer noted: live DB query for **FOREX @ `elite_score ≥ 60` + `confidence ≥ 0.60`** returns only **7 smart-decisive picks**, but the page's snapshot table shows **48 decisive @ 39.58% WR**. Root cause: the page wording in two spots claims the Smart filter is **"elite≥60"** universally, but the extractor uses a **per-class `SMART_FLOOR_BY_CLASS`** dict where FOREX = **40**, not 60. So FOREX picks scoring 40-59 (n=41) flow into the table but would never satisfy the peer's elite≥60 query.

## Actual per-class floors

Source: `tools/audit_pick_funnel/extract_funnel.py:41-44` (FROZEN 2026-05-20, mirrors `audit_trail/quality_gates.py`):

| Class      | smart_floor |
|------------|-------------|
| CRYPTO     | 60          |
| EQUITY     | 60          |
| PENNY      | 60          |
| MEME       | 60          |
| BOND       | 60          |
| INDEX      | 55          |
| ETF        | 55          |
| FUTURES    | 45          |
| FOREX      | **40**      |
| COMMODITY  | **30**      |

`PROVEN_MIN_CONF = 0.60` is universal.

## Snapshot confirms

`audit_dashboard/data/pick_funnel_90d.json::smart_picks_db_stats.FOREX`:
```json
{"n": 48, "wins": 19, "losses": 29, "decisive": 48, "wr_pct": 39.58,
 "pf": 0.803, "smart_floor": 40, "top_source": "multi_asset_copytrader",
 "top_source_share": 0.5833, "caveats": ["wr_below_50pct"]}
```
So the per-row JSON IS honest — every row carries its actual `smart_floor`. The mismatch is **page-text only**, not data.

## Page-text mismatches (fixed in this PR)

1. **Line 305** (ELI5 block):
   - Before: "restricted to elite_score≥60 & confidence≥0.60"
   - After: "restricted to `elite_score ≥ per-class floor` & `confidence ≥ 0.60`" + explicit floor table.

2. **Line 371** (table header):
   - Before: "Dashboard — Smart filter (elite≥60 & conf≥0.60)"
   - After: "Dashboard — Smart filter (elite≥per-class floor & conf≥0.60)" + hover tooltip with the floors.

Already-honest spots (no change): lines 161, 568, 582 already say "elite_score ≥ per-class floor".

## Why option (a) over (b)

- (a) Disclose per-class floors in the page wording — **chosen**.
- (b) Force the extractor to floor=60 universally — would drop FOREX/COMMODITY/FUTURES/INDEX/ETF picks from the Smart Picks cohort, which **changes production semantics** (nav surface counts, money_ready_verdict) without a strategy-level decision. That's a separate P1 conversation, not a docs fix.

The per-class floors mirror the live gate in `audit_trail/quality_gates.py:_smart_floor_score` — so the page should describe what the gate actually does, not pretend it's a uniform 60.

## Recommended follow-ups (not in this PR)

1. **P2:** Add the per-class floor column to the rendered smart_picks_db_stats table (`renderSmartPicksDbStats` in pick_funnel.html ~line 950) so every row visibly shows its floor.
2. **P1 (open question):** Is FOREX floor=40 the right business choice given FOREX is currently FAIL+sub-T2? A peer agent should run mutation analysis (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`) on FOREX@40 vs FOREX@60 cohorts before any uniform-60 push.
3. **P3:** Cross-link `SMART_FLOOR_BY_CLASS` between `extract_funnel.py` and `quality_gates.py` so the two cannot drift.

## FINDING_OVERALL

```
severity: P2
status: OPEN
title: pick_funnel.html wording claimed "elite≥60" but extractor uses per-class floors (FOREX=40, COMMODITY=30, FUTURES=45, INDEX/ETF=55, rest=60)
surface: audit_dashboard/pick_funnel.html
evidence:
  - tools/audit_pick_funnel/extract_funnel.py:41-44 (SMART_FLOOR_BY_CLASS)
  - audit_dashboard/data/pick_funnel_90d.json::smart_picks_db_stats.FOREX.smart_floor == 40
  - peer blackbox: live FOREX @ elite≥60 + conf≥0.60 returns n=7; page shows n=48
remediation: docs-only edit to two strings (lines 305, 371) — done in this PR
followups: render smart_floor column per row; revisit whether FOREX=40 is correct
```
