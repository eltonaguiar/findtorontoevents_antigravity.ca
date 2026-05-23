# 2026-04-29 — Defense-in-depth modules (kill_list audit + auto-rollback triggers)

Two opt-in sidecar modules shipped together as defense-in-depth instrumentation,
per the 4-AI panel review at
`reports/PANEL_REVIEW_2026_04_29_OPERATION_PHENOMENAL_FOLLOWUPS.md` (items #7
and #8, both ranked quick-wins with 4/4 and 3/4 panel agreement).

Neither module changes production behavior in this PR. Both are exposed as
plain functions + CLI entry points and will be wired in follow-up PRs (see
"Wiring plan" below).

## Panel rationale

### Item #7 — kill_list SHA-256 integrity audit (4/4 panel quick-win)
PR #519 introduced a `mutation_name` fallback path during pick attribution.
The fallback can produce strings whose suffix coincidentally matches an
existing kill_list entry, allowing a banned strategy to slip past the gate
without an explicit kill-run event. A per-cycle SHA-256 of the canonical
kill_list, written to an append-only audit log, makes any silent change
detectable post-hoc.

### Item #8 — Auto-rollback trigger detector (3/4 panel quick-win)
The 2026-04-29 "Operation Phenomenal Performance" rollout in
`updates/index.html` published auto-rollback thresholds that included
`CRYPTO MDD >195%`. Panel AI #2 flagged that threshold as mathematically
impossible (MDD on a non-leveraged equity curve is bounded by ~100%; even
our pnl_pct-sum aggregation tops out near that ceiling). 3/4 panelists
concurred. We need a corrected, testable, default-off trigger detector.

## Triggers

`audit_trail/auto_rollback_triggers.py::check_rollback_conditions(...)` is a
pure function that returns triggered conditions and takes no other action.

| # | Trigger             | Threshold                | Severity   | Notes |
|---|---------------------|--------------------------|------------|-------|
| 1 | `banned_id_emit`    | any kill_list match      | critical   | Suppressed when `kill_list_metadata.auto_expired == true`. Checks both `picks.active` and `picks.active_raw`. |
| 2 | `wr_3d_below_28`    | WR < 28%, n >= 20, 3d    | high       | Per asset class. Win = `pnl_pct > 0` (canonical rule from `core_whitelist.json::kill_run_stats.normalization_rules`). |
| 3 | `mdd_breach`        | peak-to-trough MDD > 30% | critical   | Per asset class, on cumulative `sum_pnl_pct` over closed picks in the window. |

## Threshold rationale: why 30%, not 195%

- MDD on a non-leveraged book is mathematically bounded near 100%.
  The published 195% threshold could never fire — it provides zero
  protection.
- Tier 2 hedge-fund cap in `docs/PERFORMANCE_CHARTER.md` is MDD < 20%
  for an asset class we are sizing up. 30% leaves a 10pp headroom for
  noise on rolling 3d windows so we do not page on every garden-variety
  drawdown.
- Tier 1 (Renaissance grade) target is MDD < 10%. A future tightening to
  20% or 15% can ship as a one-line constant change with a test update.

## CLI examples

Audit the current kill_list (appends one line to
`audit_trail/data/kill_list_audit_log.json`):

```
python -m audit_trail.kill_list_audit
```

Inspect rollback triggers using the live dashboard data:

```
python -m audit_trail.auto_rollback_triggers
```

Override the asset class:

```python
from audit_trail.auto_rollback_triggers import check_rollback_conditions
triggers = check_rollback_conditions(asset_class="EQUITY", window_days=3)
```

Drift detection:

```python
from audit_trail.kill_list_audit import detect_unexpected_changes
drifts = detect_unexpected_changes(window_hours=24)
```

## Wiring plan (NOT YET WIRED — opt-in sidecar)

Per the Wire-Up Rule (`CLAUDE.md`), both modules are opt-in sidecars in this
PR. No production caller imports either file. Production wire-up will land in
follow-up PRs:

1. `kill_list_audit.audit_kill_list(audit_cycle_id)` — to be invoked from
   `audit_trail/dashboard_generator.py` once per cycle, immediately after the
   helper that loads `core_whitelist.json` (typically `_load_external_kill_set`
   or equivalent). Expected wire-up: 2026-05-02.
2. `auto_rollback_triggers.check_rollback_conditions()` — to be invoked from
   `alpha_engine/smart_picks_engine.py` pre-emission. Triggers will be appended
   to `audit_dashboard/data/auto_rollback_log.json` and surfaced on the
   dashboard. The actual rollback action (e.g. re-blocking a strategy in
   `strategy_blocklist`) is a separate decision and PR.
   Expected wire-up: 2026-05-05.

## Files

- `audit_trail/kill_list_audit.py`
- `audit_trail/auto_rollback_triggers.py`
- `tests/test_kill_list_audit.py`
- `tests/test_auto_rollback_triggers.py`
- `updates/2026-04-29-defense-modules.md` (this file)
