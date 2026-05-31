# DB Health Harness — `harness_healthy` Gate (Contract Change)

**Date:** 2026-05-31
**Author:** Claude (operator-item #2 follow-up from PR #221)
**Status:** DRAFT — open PR, operator review required

## Problem

`tools/db_health_check.py` (overall block, prior to this change) computed
`any_red` and `checks_failed` independently:

```python
"checks_failed": sum(1 for c in results["checks"].values()
                     if not c["ok"] or not c.get("data", {}).get("threshold_pass", True)),
"any_red": any(c.get("data", {}).get("tier") == "red"
               for c in results["checks"].values() if c["ok"]),
```

The `any_red` aggregate **excludes errored checks** (`if c["ok"]`). A run where
every check throws an exception emits `any_red=false`, the dashboard banner
stays green, and downstream consumers infer the DB is healthy when in fact the
harness produced no signal at all.

Exit code follows `any_red`, so CI also passes a fully-broken harness.

## Fix (bounded)

Adds two derived flags to `results["overall"]`. No existing field is removed
or renamed — purely additive contract extension.

| Field | Type | Semantics |
|---|---|---|
| `harness_healthy` | `bool` | `True` iff `checks_failed == 0`. False means at least one check errored or failed threshold. |
| `banner_should_show` | `bool` | `any_red OR NOT harness_healthy`. Used by dashboards to decide whether to render any banner at all. |

`any_red` keeps its existing definition (red-tier among successfully-run
checks) so the hard DATA INTEGRITY banner does not change behavior on a
healthy harness.

CI exit code is unchanged (`exit 1 if any_red`) in this PR to keep blast
radius small; a follow-up PR can opt the workflow into `exit 1 if not
harness_healthy` once we observe field behavior.

## Dashboard side (`audit_dashboard/dashboard_enhancements.js`)

A second, soft-warning banner is added below the existing hard banner block:

- If `any_red` → hard red DATA INTEGRITY FAILURE banner (unchanged).
- Else if `harness_healthy === false` → new amber **DB HEALTH HARNESS DEGRADED**
  banner stating that `any_red` may be falsely-green by exclusion.
- Else → no banner (existing behavior).

The two banners are mutually exclusive (an `else if`), so a red-tier verdict
on a healthy harness still surfaces as red (no doubling up).

## Why open PR (not admin-merge)

This is a **contract change to `db_health.json`** (additive but consumed by
the live dashboard) plus a JS change to the user-facing banner. Per the
operator rules, anything touching dashboard JS or the health-check contract
opens a PR rather than admin-merging.

## Compatibility

- Old consumers reading `any_red` / `checks_failed` / `checks_passed`:
  unchanged.
- New consumers can opt into `harness_healthy` and `banner_should_show`.
- JSON shape is a strict superset.

## Files changed

- `tools/db_health_check.py` (overall dict) — additive
- `audit_dashboard/dashboard_enhancements.js` (banner block) — additive
  `else if` branch
- `reports/peer_claude-harness-healthy-draft_2026-05-31.md` — this doc

## Follow-ups

1. Once observed in production for ~24h, optionally change exit code to
   `exit 1 if banner_should_show` so CI catches errored harness runs.
2. Add a unit test that injects a forced-error check and asserts
   `harness_healthy == False` while `any_red == False`.
