# Incidents Fix: Signal Time Enrichment + FOREX PnL Clamp

**Date:** 2026-05-31  
**Author:** opencode  
**Source:** incidents.html review via opencode session

## Summary

Two incidents from [findtorontoevents.ca/audit/incidents.html](https://findtorontoevents.ca/audit/incidents.html) were addressed in this session.

---

## Fix 1: Smart Picks 'Signal Time' → P1 RESOLVED

**Incident:** "Smart Picks 'Signal Time' is dashboard-file age, not pick age"
- The `smart_picks_feed` picks in the dashboard payload lacked a `signal_time` field
- Template fell back to `age_hours` which was stale/uniform across all picks
- All rows appeared to have fired at the same time regardless of real signal time

**Fix applied in** `audit_trail/dashboard_generator.py:2315-2348`:
- Added `_add_signal_time()` helper that computes `signal_time = generated_at - age_hours` for each pick in `smart_picks.json`
- Enriches picks in all four categories: `picks`, `scalp_picks`, `swing_picks`, `position_picks`
- Skips picks that already have a `signal_time` field
- Gracefully handles missing `generated_at` or `age_hours`

**No DB query needed** — computed from existing file data.

---

## Fix 2: 5 FOREX rows pnl_pct < -100% → P0 IN_PROGRESS

**Incident:** "5 FOREX rows have pnl_pct < -100% (one at -106,700%)"
- Unit-clamp bug commit #876 missed 5 rows, distorting FOREX class avg PF/WR
- Baseline FOREX WR is 43.9% on n=1666 but class looked catastrophic

**Fix created** at `tools/fix_forex_pnl_clamp.py`:
- Connects to MySQL via pymysql using existing `DB_PASS_STOCKS` env var
- Reports current count, performs `UPDATE trading_picks SET pnl_pct = -100 WHERE pnl_pct < -100 AND category='FOREX'`, reports remaining
- Dry-run safe: prints affected count before UPDATE

**To execute:** `DB_PASS_STOCKS=<pw> python3 tools/fix_forex_pnl_clamp.py`

---

## Updated Seed File

`tools/audit_pick_funnel/seed_incidents_enhancements.py`:
- Incident "Smart Picks 'Signal Time'..." → `P1 RESOLVED` with updated description
- Incident "5 FOREX rows..." → `P0 IN_PROGRESS` with script reference

---

## Files Changed

| File | Change |
|------|--------|
| `audit_trail/dashboard_generator.py` | Added `_add_signal_time()` + enriched `_load_smart_picks_feed()` to add `signal_time` to every pick |
| `tools/fix_forex_pnl_clamp.py` | New tool to clamp FOREX pnl_pct < -100% to -100 |
| `tools/audit_pick_funnel/seed_incidents_enhancements.py` | Updated status fields for both incidents |
| `updates/2026-05-31-incident-fixes-signal-time-forex-clamp.md` | This document |

## Related Incidents (not addressed, noted)

- `smart_picks.json` 31 days stale (`alpha_engine/data/smart_picks.json` last modified 2026-04-30) — run `smart_picks_engine.py` manually to regenerate
- `summary_picks.json` fixture suspicion — already resolved by `tools/sync_summary_picks_json.py` (current file shows divergent per-class timestamps)
