## What was broken

Two stale GitHub Actions failures on `main` were not flaky runner issues. Both `Strategy Funnel Hourly Refresh` and `Edge stability refresh` regenerated their JSON successfully, then failed on a plain `git push` with:

- `! [rejected] main -> main (fetch first)`

That means the workflows were losing normal races against other auto-commit jobs on a busy `main`.

Separately, `Sports endpoint smoke + Playwright` is currently failing for a real production reason, not CI noise. The live endpoints under `https://findtorontoevents.ca/live-monitor/api/` are returning:

- `{"ok":false,"error":"Sports DB connection failed"}`

## What I changed

- Added `fetch-depth: 0` to the two self-updating workflows so rebases have full history available.
- Replaced the naive single `git push` in:
  - `.github/workflows/strategy-funnel-hourly.yml`
  - `.github/workflows/edge-stability-refresh.yml`
  with the repo's existing pull/rebase retry pattern:
  - commit first
  - `git pull --rebase --autostash origin main`
  - `git push origin HEAD:main`
  - retry up to 5 times with backoff

## Findings

- `Strategy Funnel Hourly Refresh`: **BROKEN workflow robustness** before this patch; rerun reproduced the same push-race failure immediately.
- `Edge stability refresh`: **BROKEN workflow robustness** before this patch; rerun reproduced the same push-race failure immediately.
- `Sports endpoint smoke + Playwright`: **ENV / production outage**, because the live sports API currently cannot reach the sports DB.
- `Mirror: findtorontoevents.ca torontoevent.net`: rerun is still/was still in progress during investigation; previous stale failure was a 50webs FTP download timeout.

## How it was verified

- Re-ran the stale workflow runs with `gh run rerun --failed` and observed both auto-commit workflows fail again on the same `fetch first` push rejection.
- Confirmed the sports smoke failure body from the rerun logs.
- Hit the live production API paths directly and confirmed the same `Sports DB connection failed` response across the affected sports endpoints.

## Next steps

1. Merge this workflow retry fix so the next scheduled refresh jobs stop failing on normal `main` contention.
2. Triage the live sports DB outage separately from CI/workflow health; the smoke test is correctly detecting a production problem.
3. Watch the mirror rerun to see whether the prior FTP timeout was transient or needs timeout/retry hardening too.
