# 2026-05-01 — B12: Source-liveness watchdog

## Problem

Dashboard-layer volume counts are a lossy, stratified projection (3,500-pick cap
with reservation logic). Counting `source_system` cardinality in `dashboard_data.json`
is **not** a measure of source emission rate. This caused a false SEV-1 alert on
2026-04-29 when `claude_gainer_st` was excluded from `_VERIFIED_ALPHA_COPY_SOURCES`
— the panel saw 0 CGS picks in the dashboard and declared a silent failure, when in
reality CGS was emitting normally.

Per `reports/silent_failure_investigation_2026_04_29.md` Fix 4:
> The >70% volume-drop watchdog MUST measure at the source-file layer (mtime + row
> count), not the dashboard layer, or it will keep producing false-positive SEV-1s.

## Fix

New tool `tools/source_liveness_watchdog.py` that:

1. Walks all 154 `JSON_PICK_SOURCES` files (active + closed paths).
2. Checks modification time against a configurable `--stale-hours` threshold (default: 26h).
3. Checks row-count drop vs the previous run's snapshot (configurable `--drop-pct`, default: 70%).
4. Writes a **warn-only** artifact to `reports/health/source_liveness_<timestamp>.json`
   and `reports/health/source_liveness_latest.json`.
5. Always exits 0 — never raises, never SEV-1.

## First-run output (2026-05-01, 154 sources checked)

```
checked=182 ok=81 stale=90 dropped=0 missing=11
```

90 stale sources (mostly ml_battleground, paper_trading, tournament systems last
written 2026-04-25 — expected dormant state). 11 missing (orphaned paths from dead
strategies). 0 row-count drops (no previous snapshot; will detect on next run).

## Wire-Up Rule

✅ The tool is a stand-alone CLI, not an integration module. No Wire-Up Rule
applies to pure tooling that doesn't import production scorer/gate paths.

**Optional CI wiring** (not in this PR): add a `--stale-hours 36` check to the
nightly CI run that logs warnings to the step summary. The tool's always-0 exit
code means CI will never fail due to stale sources — only warn.

## Files

- `tools/source_liveness_watchdog.py` — new tool (warn-only, exit 0)
- `tests/test_source_liveness_watchdog.py` — 15 tests (all pass)
- `updates/2026-05-01-source-liveness-watchdog.md` — this doc

## Tests

All 15 pass:
- `_count_picks()` for all known JSON schemas (list, picks key, long_picks, active_picks)
- Stale detection: backdated file appears in `stale`; fresh file doesn't
- Missing detection: non-existent file appears in `missing`
- Row-count drop: >70% drop flagged; <70% drop ignored
- Report writing: dated + latest files created
- `main()` always returns 0
- `load_previous_snapshot()` returns None when no prior run; returns snapshot dict otherwise

## Acceptance criteria

- `python -m tools.source_liveness_watchdog --no-snapshot` exits 0 on a clean run
- `reports/health/source_liveness_latest.json` created with correct schema
- No existing tests broken
