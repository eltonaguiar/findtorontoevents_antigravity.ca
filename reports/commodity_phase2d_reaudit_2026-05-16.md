# COMMODITY Phase 2-D Re-Audit — 2026-05-16

## Summary

COMMODITY dashboard stats are severely inflated by CT=F (Cotton) COT duplicate
signals. True COMMODITY performance (excluding duplicates) is sub-floor.

## Data Source
`alpha_engine/data/closed_picks.json` as of 2026-05-16T02:50Z
`audit_dashboard/data/dashboard_data.json::performance.asset_class_health.COMMODITY`
(asset_class_health: n=337, WR=62.6%, PF=2.57 — generated 2026-05-16T01:54Z)

## Findings

### CT=F COT Duplication Pattern

| Metric | Value |
|---|---|
| Total CT=F COT picks (closed) | 230 |
| All direction | SHORT (100%) |
| Unique dates | 16 |
| Avg picks/date | 14.4 |
| Picks at same entry_price (>2 dups) | 21 distinct prices |
| Worst single price | 22 picks at $83.00 |
| WR of these "picks" | 85.7% |
| PF of these "picks" | 7.80 |

The COT scanner emitted the same SHORT CT=F signal ~14x per day across 16 days.
These are NOT independent trades. One profitable SHORT trade idea (Cotton fell)
was logged 230 times.

### True COMMODITY stats (closed picks, asset_class=COMMODITY)

| Slice | n | WR% | PF | Verdict |
|---|---|---|---|---|
| All COMMODITY closed picks | 354 | 60.2% | 2.28 | Inflated |
| CT=F COT duplicates only | 230 | 85.7% | 7.80 | Artifact |
| **COMMODITY excl CT=F COT dups** | **124** | **12.9%** | **0.24** | **Sub-floor** |

### Per-symbol breakdown (all commodity futures)

| Symbol | n | WR% | COT_n | COT_WR% | Non-COT_n | Non-COT_WR% |
|---|---|---|---|---|---|---|
| CT=F | 290 | 69.0% | 230 | 85.7% | 60 | 5.0% |
| CL=F | 47 | 19.1% | 0 | — | 47 | 19.1% |
| SI=F | 47 | 2.1% | 0 | — | 47 | 2.1% |
| ZW=F | 35 | 20.0% | 19 | 26.3% | 16 | 12.5% |
| KC=F | 26 | 7.7% | 3 | 0.0% | 23 | 8.7% |
| NG=F | 26 | 3.8% | 0 | — | 26 | 3.8% |
| HG=F | 33 | 0.0% | 0 | — | 33 | 0.0% |
| ZS=F | 19 | 0.0% | 12 | 0.0% | 7 | 0.0% |
| ZC=F | 8 | 0.0% | 0 | — | 8 | 0.0% |
| GC=F | 10 | 0.0% | 0 | — | 10 | 0.0% |

**Conclusion:** The only symbol not sub-floor on its own is CT=F — and that's entirely
because 230 duplicate COT SHORT signals fired when Cotton happened to drop.

## Root Cause

`cftc_cot_commercial_signal` and `cot_positioning` scanners lack deduplication.
They emit the same signal every scan cycle (~hourly) for the same symbol/direction
without checking if a recent identical pick is already active.

## Fix Status

1. **COT-dedup guard** — `audit_trail/quality_gates.py::COT_DEDUP_WINDOW_HOURS=72`
   added 2026-05-16 (commit sha in git log). Rejects new CT=F COT picks if an
   identical pick (same system, same symbol) was emitted within 72h. This prevents
   NEW duplicates from entering.

2. **Historical data** — The 230 existing closed CT=F COT duplicates remain in
   `closed_picks.json`. They will gradually age out of dashboard_data.json as
   the dashboard refreshes and old cohorts drop out of the rolling window.

3. **COMMODITY banner** — currently says "T2 PF confirmed ✓; WR exceeds 50% ✓;
   verify MDD for full T2." The money_maker_ready report already flags "T1 NOT SAFE."
   No banner change needed; operator should read the report caveat.

## Impact on Other Symbols

- **CL=F, GC=F, SI=F, ZC=F**: No COT inflation. Real performance is terrible (WR 0-19%).
  These symbols have no viable edge from current strategies.
- **ZW=F, ZS=F**: Minor COT inflation; edge still sub-floor after removal.
- **COMMODITY as a whole**: Edge is almost entirely from CT=F COT dedup artifact.
  Once the dedup guard is active and duplicates stop, COMMODITY will show its true
  performance until cleaner, deduplicated COT signals accumulate (need n≥100 clean picks).

## Recommended Actions

| Priority | Action | Expected impact |
|---|---|---|
| P0 | Do NOT claim COMMODITY T2/T1 in any external communication | Prevents false confidence |
| P1 | Monitor COMMODITY n in dashboard after COT-dedup guard goes live (hourly refresh) | n should plateau/drop from 337 as dupes stop |
| P1 | Set up 7-day rolling clean-n metric that excludes same-system same-symbol within 72h | True edge visibility |
| P2 | Investigate COMMODITY strategies that might have real edge on commodities (not COT) | New strategy development |
| P3 | Multi-axis mutation (symbol/direction/timeframe) for CL=F, GC=F before kill | Per MUTATION_PROTOCOL |
