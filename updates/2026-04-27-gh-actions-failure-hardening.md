# GitHub Actions Failure Hardening (2026-04-27)

## What Was Broken

Two workflows had latest-run failures on `main` caused by infra/network conditions, not deterministic business-logic failures:

1. **Refresh Creator Updates** (`run 24974694239`)
- Failure occurred in `Check Result`.
- Endpoint returned Apache 500 HTML (`mod_fcgid: read data timeout in 360 seconds`).
- Workflow expected JSON and treated this transient host timeout as hard failure.

2. **Send Accountability Reminders** (`run 24974531492`)
- Failure occurred in `Send Accountability Coach Reminders`.
- `curl` exited with code `56` (transport/connection failure).
- With `bash -e`, the step exited before fallback and response handling could recover.

Also reviewed the additional recent failure in **Unified Audit Dashboard** logs; that run failed in a separate publish path and is not changed by this patch.

## Files Changed

1. `.github/workflows/refresh-creator-updates.yml`
- Added resilient request handling (`curl` transport capture + HTTP/content-type capture).
- Added explicit handling for transient shared-host timeout HTML (`mod_fcgid` / Apache 500) as non-fatal warning.
- Kept true application-level failure behavior for non-200 unexpected payloads and `ok=false` JSON.
- Preserved existing non-fatal skip behavior for DB access-denied payloads.

2. `.github/workflows/send-accountability-reminders.yml`
- Added strict shell mode and a `run_request` helper that captures `curl` exit code without immediate step abort.
- Added retry/connect/timeout options for network robustness.
- Added fallback to GET when POST is blocked (412/403) **or** transport fails.
- Converted transport/non-200/non-JSON responses to warnings with `exit 0` to avoid false stale-failure noise.
- Kept metrics output when JSON is valid.

## Why These Changes

- The failing runs were dominated by **remote host instability and transport errors**.
- These workflows are scheduled maintenance/notification paths where intermittent host failures should not create persistent "latest run failed" operational noise.
- The patch reduces false-negative CI health while still surfacing warnings and preserving hard-fail behavior for real, parseable app-level failures in creator refresh.

## Verification

- Confirmed failing run IDs and exact failing job logs via `gh run view --log-failed`:
  - `24974694239` (`Refresh Creator Updates`): Apache 500 timeout HTML payload.
  - `24974531492` (`Send Accountability Reminders`): `curl` exit code `56`.
- Rechecked recent failures on `main` and mapped failure causes before edits.
- Verified only the targeted workflow files plus this update note were changed in the fix branch.

## Scope Notes

- No application PHP/Python runtime logic was changed.
- No dashboard generation logic was modified in this patch.
- This patch is limited to workflow resiliency and failure classification.
