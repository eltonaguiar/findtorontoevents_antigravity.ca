# Raw Actions logs are fetchable programmatically — `tools/gha_raw_logs.py`

**Date:** 2026-11-25
**Trigger:** asked whether the "View raw logs" link (a signed Azure blob URL) can be read and repeated
across the latest run of every workflow.

## Answer: yes, and the signed URL is not needed

The UI's "View raw logs" is a redirect to a short-lived Azure blob:

```
https://productionresultssa16.blob.core.windows.net/actions-results/<run>/workflow-job-run-<job>/logs/job/job-logs.txt
  ?se=2026-11-25T23:50:23Z&sig=...&st=2026-11-25T23:40:18Z&sp=r&...
```

Note `st`/`se`: the signature was valid for **~10 minutes**. Copying those links around is fragile.
The stable endpoint is the one that 302s to them, and it works with the authenticated session:

```bash
gh api /repos/{owner}/{repo}/actions/jobs/{job_id}/logs   # -> plain-text job log
```

Proven on the job that prompted this (`.../runs/45722879024/job/139585294128`): 31,303 bytes,
365 lines — byte-identical to the blob behind the pasted signed URL.

## The tool

`tools/gha_raw_logs.py` — three modes:

```bash
# one job, accepts the full web URL
python3 tools/gha_raw_logs.py --job https://github.com/o/r/actions/runs/1/job/2

# every job in one run
python3 tools/gha_raw_logs.py --run 45714932707

# latest COMPLETED run of every workflow seen recently; fetch logs for the failing ones
python3 tools/gha_raw_logs.py --latest-failing --limit 300
```

Writes raw logs to `reports/gha_logs/<run>-<job>-<slug>.log` (gitignored — they are large and
regenerable) and a summary to `reports/gha_raw_logs_latest.{json,md}`.

Cost: one paginated `gh run list`, then 1 job-list + 1 log call per failing job. A sweep with one
failing workflow is ~4 calls; the whole 300-run sweep was well under 20.

## Two accuracy bugs found and fixed while building it

**1. The log embeds the step's own script.** Matching `::error::` blindly reported *source code*
as the failure:

```
cause: echo "::error::signal_recorder/export_hub_combos.py is missing — hub data cannot refresh"
```

That is the literal text of the heredoc, printed into the log, not an event. Fix: `##[error]`
(runner annotation) is authoritative and checked first; bare `::error::` only counts on a line that
does not look like source (`SOURCE_LINE_RE` rejects `echo "::error::`, `print(f"::error::`, comments).
Correct output for the same job is now:

```
cause: ##[error]hub manifest is 268.6 days stale
```

**2. "Latest run" was wrong for workflows still running.** Deduping to the newest run per workflow
made a workflow with an in-progress run look healthy, hiding the failure of the run before it. The
tool now tracks the newest run *and* the newest **completed** run per workflow, reports the completed
one, and annotates when a newer run is still in progress.

**Cause vs outcome.** The first authoritative error is usually the root cause; the last is how the job
ended. Both are reported:

```
cause:   ##[error]B/OVERLAY: snapshot present but payload EMPTY (fetcher returned nothing ...)
outcome: ##[error]The action 'Commit results' has timed out after 30 minutes.
```

## First sweep (2026-11-25T23:44Z, 300 runs → 115 workflows)

| Latest completed conclusion | Count |
|---|---|
| success | 107 |
| cancelled | 2 |
| skipped | 1 |
| in progress (newest run) | 4 |
| **failure** | **1** |

The single failure was `Hub Data Sync` run `45719481029` on `b66ad3359` — the run that predates the
gate repair merged as `ffa177e07fa9` (PR #1141). Its next scheduled fire (`:06`) is the live test of
that fix.

Two earlier failures had already recovered: `CI Tests` failed at 23:05 and 23:33 but succeeded at
23:32:51 and had a newer run in flight, so it is not counted as unrecovered.

## Notes

- `--include-cancelled` opts into cancelled runs (mostly concurrency cancellation, not defects).
- Values in logs are already secret-masked by the runner; the tool stores logs locally under
  `reports/gha_logs/` and does not print them wholesale.
- The raw log of a *successful* job is still fetchable, which is how the pasted
  `Prediction Quality Tracker` link was confirmed green (it contained no error lines at all).
