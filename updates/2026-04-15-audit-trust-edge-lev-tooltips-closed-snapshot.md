# Audit dashboard: TRUST / EDGE / LEV tooltips, closed-pick at-issue snapshots, init hardening

**Status:** Generator **`at_issue_*`** snapshots are implemented in code (`_snapshot_at_issue_for_recent_closed` in `audit_trail/dashboard_generator.py`, 2026-04-16). See **`updates/2026-04-16-audit-backend-at-issue-snapshot-wired.md`**.

## Issues

1. **TRUST / EDGE / LEV** column header tooltips were too shallow vs actual dashboard logic.
2. **Closed picks** showed only slim post-merge fields; users need strategy forward WR and trust **as known before** today’s leaderboard + trust enrich overwrite them.
3. **Active Picks intermittently failed**: `getVerifiedTier` / `buildVerifiedEdgeIndex` ordering in `index.html` lagged `template.html` — `_applyGlobalSportsFilter` returned early without rebuilding the index when `D.picks` was missing; `getVerifiedTier` could see a null or partial `_verifiedEdgeIndex`. External JSON fetch could surface `TypeError` (e.g. `trackCombos` / strategy key) and abort `init()`.

## Changes

### Generator (`audit_trail/dashboard_generator.py`)

- Before the main `for pick in active + recent_closed` merge, copy into optional **`at_issue_*`** fields on **`recent_closed`** when not already set: `strat_fwd_wr`, `strat_fwd_trades`, `forward_wr`, `forward_trades`, `trust_score`, `trust_tier` from the raw row.
- Immediately before `enrich_picks_with_trust_score(recent_closed)`, fill missing **`at_issue_trust_*`** from current `trust_tier` / `trust_score` so tier at least reflects pre-enrich state.
- Extended **`_CLOSED_PICK_KEEP_FIELDS`** so slim export retains `at_issue_*`.

### Dashboard UI (`audit_dashboard/template.html` + `index.html`)

- **Tooltips**: Expanded **Trust**, **EDGE** (GOLDEN / VERIFIED / TRACK thresholds aligned with `buildVerifiedEdgeIndex`), **LEV** (0–30 factor stack, not exchange margin).
- **Closed Picks** table: columns **FWD@ISS**, **N@ISS**, **Tr@ISS**, **Tier@ISS** + `colTips` / `numCols` entries.
- **index.html** synced with template: **verified edge block defined before** `_applyGlobalSportsFilter`; early exit calls **`buildVerifiedEdgeIndex()`**; **`getVerifiedTier`** uses full defensive object shape (local `{}` fallbacks for sub-maps).

### Tests

- `tests/audit_verified_edge_active_picks.spec.ts`: second test opens **Closed Picks** and asserts header text includes **FWD@ISS** and **Tr@ISS**.

## Verification

```bash
npx playwright test tests/audit_verified_edge_active_picks.spec.ts tests/audit_agv_col_tip_viewport.spec.ts --project="Desktop Chrome"
```

Regenerate `dashboard_data.json` / deploy audit HTML per usual CI so closed rows pick up `at_issue_*` from the next generator run.
