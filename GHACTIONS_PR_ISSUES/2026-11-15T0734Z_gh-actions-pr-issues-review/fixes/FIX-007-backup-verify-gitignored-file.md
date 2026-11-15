# FIX-007 — backup-verify false failure on gitignored file

**File:** `.github/workflows/backup-verify.yml`
**Severity:** P0
**Status:** Applied (PR #790)

## What was broken
`backup-verify.yml` failed on **every** run with:
```
[backup-verify] FAILURES DETECTED:
  - dashboard_data.json NOT FOUND
  - Critical file missing: audit_dashboard/data/dashboard_data.json
```
`audit_dashboard/data/dashboard_data.json` is **gitignored** (`.gitignore:218`), so it can never exist in a fresh `actions/checkout`. The check was therefore guaranteed to fail, and each failure opened an issue (40+ `backup-verify` issues, bulk-closed 2026-11-15 at 07:47).

**Root cause:** the smoke script treated a *gitignored, runtime-generated* file as a required committed artifact.

## What changed
- Added a `_is_gitignored(path)` helper (`git check-ignore -q`).
- Query 1: if `dashboard_data.json` is missing **and** gitignored → `SKIP` (not a failure).
- Query 3: for each critical file, if missing **and** gitignored → `SKIP`; a missing *committed* file still FAILS as before.

This keeps the check meaningful (committed files must exist and be non-empty) while not failing on files that are generated at runtime.

## How to verify
- `yaml.safe_load` parses the workflow ✅
- Run via `workflow_dispatch`: the smoke step should print `SKIP dashboard_data.json (gitignored...)` and pass for the committed files (`recent_exits.json`, `ml_health_status.json`, `pcg5_log.json` were all OK in run 43683666944).

## Related
FIX-001 (issue dedup) stops the spam; FIX-007 fixes the *cause* of the failure. Closed-today backup-verify issues #606–#787 were symptoms.