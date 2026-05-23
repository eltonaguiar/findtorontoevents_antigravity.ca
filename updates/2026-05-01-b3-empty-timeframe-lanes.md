# B3: Freshness Watchdog `empty_timeframe_lanes` Extension
**Date:** 2026-05-01  
**PR:** feat/b3-empty-timeframe-lanes-2026-05-01  
**Risk:** LOW — additive schema field; no behavior change to existing output

## What

Extends `tools/generate_asset_class_freshness_report.py` with an `empty_timeframe_lanes`
list in the daily artifact. Each entry is `{"asset_class": str, "timeframe": str}` for
every standard lane with 0 active picks.

**Standard lanes:** CRYPTO/EQUITY/FOREX/BOND/ETF/COMMODITY × SCALP/INTRADAY/SWING/POSITION
(24 total). Empty lanes = those absent from `picks.active` in the dashboard payload.

## Why

The existing freshness report identified *stale asset classes* (no recent closed picks)
but had no visibility into *empty timeframe lanes* (no active coverage). A lane like
`EQUITY × POSITION` or `FOREX × SCALP` with zero active picks is an invisible gap —
the existing report wouldn't flag it.

This is the alerting surface for B2's "⚠ empty lane" tooltip: the freshness report
artifact can now be consumed by CI or the dashboard to surface capacity gaps.

## Changes

**`tools/generate_asset_class_freshness_report.py`** (~30 lines):
- New `_STANDARD_ASSET_CLASSES` / `_STANDARD_TIMEFRAMES` module-level constants
- New `_empty_timeframe_lanes(active_picks)` helper
- `build_report()`: reads `picks.active` from payload; adds `empty_timeframe_lanes` to output dict
- `_to_markdown()`: adds "Empty Timeframe Lanes" section

**`tests/test_asset_class_freshness_report.py`** (+12 tests):
- `TestEmptyTimeframeLanes` — 7 unit tests on the helper directly
- `TestBuildReportEmptyLanes` — 4 integration tests via `build_report()`

## Acceptance criteria

- `build_report()` output always includes `empty_timeframe_lanes` key (even on empty payload)
- Lanes covered by ≥1 active pick are excluded from the list
- Matching is case-insensitive (pick asset_class/timeframe values may be mixed case)
- Existing metrics (win_rate, profit_factor, stale_classes) unchanged

## Wire-Up Rule

**Opt-in sidecar** — `generate_asset_class_freshness_report.py` is a standalone CLI tool
(not yet called from a production scheduler).

**Wiring plan:** follow-up PR adds `python tools/generate_asset_class_freshness_report.py`
as a pre-step in `.github/workflows/audit-dashboard.yml` so the artifact is generated
before each dashboard rebuild. The `empty_timeframe_lanes` output can then be consumed
by the dashboard generator's `_build_asset_class_timeframe_grid()` (from B2 PRs #568/#574)
to add an "alert" overlay on empty cells.
