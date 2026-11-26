# GHA cancellations were hung pushes, not concurrency churn — plus an automatic failure digest

**Date:** 2026-11-25 (23:53–00:20 UTC)
**Scope:** `eltonaguiar/findtorontoevents_antigravity.ca` GitHub Actions triage

## 1. What was asked

1. Re-run the raw-log sweep after the next `:06` Hub Data Sync firing and confirm the
   repaired gate goes green.
2. Wire `tools/gha_raw_logs.py` into a scheduled workflow that posts a failure digest,
   so triage happens automatically.
3. Run the sweep with `--include-cancelled` to decide whether the cancellations are
   concurrency churn or real lost work.

## 2. The cancellations were real lost work

`python3 tools/gha_raw_logs.py --latest-failing --include-cancelled --limit 300`
(scanned 300 runs, 111 workflows) reported two cancelled workflows:

| workflow | run | job duration | conclusion |
|---|---|---|---|
| `portfolio-tracker` | `45719700001` | 23:13:45 → 23:24:00 (**10m15s**) | cancelled |
| `realtime-challenge` | `45722095341` | 23:32:07 → 23:42:22 (**10m15s**) | cancelled |

Both durations land on the job's own `timeout-minutes: 10` plus the ~15s post-job
cleanup. Neither is concurrency churn: **both declare `cancel-in-progress: false`**, and
`realtime-challenge`'s newer run `45723933351` is a fresh schedule firing, not a
supersede.

The raw logs name the actual cause. Both commit steps used the same inline idiom:

```bash
for i in 1 2 3; do
  git push && break || { git pull --rebase --autostash; sleep 5; }
done
```

- `portfolio-tracker`, 23:14:26: `! [rejected] main -> main (fetch first)` → the bare
  `git pull --rebase --autostash` was invoked and then produced **no output for 9m32s**
  until `##[error]The operation was canceled.` at 23:23:58. Local commit `39d9bfbc`
  ("portfolio-tracker: mark to market") was created and **never pushed**.
- `realtime-challenge`, 23:32:58: same rejection, then **9m21s** of silence until the
  cancel at 23:42:19. Local commit `b146370f` ("realtime-challenge: cycle") was created
  and **never pushed**.

So the work ran, the commit succeeded, and only the push was lost — which is exactly the
failure mode documented at the top of `.github/scripts/safe_push.sh`
("Cancellation fix 2026-05-06: … git operations hung past the runner timeout, causing GHA
to kill the job AFTER all work was done"). `safe_push.sh` bounds every git call with
`timeout 90`, retries up to 8 times with backoff, deepens shallow checkouts, and resolves
data-file rebase conflicts with `-X theirs`; 209 workflow files already use it. These two
were the stragglers.

A secondary effect: a job killed at its own timeout is reported by the API as
`conclusion: cancelled`, not `failure`, so `gh run list` and the dashboard colour it as
"cancelled" and it never appears in a failure triage. That is why these went unnoticed.

## 3. Changes

### `portfolio-tracker.yml`, `realtime-challenge.yml`

- Replaced the unbounded inline `git push … git pull --rebase --autostash` retry loop with
  `bash .github/scripts/safe_push.sh`, passing `TOKEN_FOR_PUSH: ${{ secrets.GH_PAT || github.token }}`.
- Bound the commit step (`timeout-minutes: 6` / `5`) and raised the job timeout
  (15 / 12) so a stuck push fails **the step** (`failure`, with the commit still in the
  log) instead of the **job** hitting its own limit (`cancelled`, work discarded).
- `realtime-challenge.yml`: moved the caller-controlled `workflow_dispatch` `tag` input out
  of the script body into `env:` and used `"$TAG"`, so an input value can never be
  interpreted as shell source (same env-binding fix as PR #1141).

### `.github/workflows/gha-failure-digest.yml` (new)

Every 2 hours at `:37`, the workflow:

1. runs `tools/gha_raw_logs.py --latest-failing --include-cancelled --limit 300`,
2. appends the rendered digest to the run's **job summary**,
3. uploads `reports/gha_raw_logs_latest.{md,json}` plus the raw `reports/gha_logs/*.log`
   as a 14-day artifact,
4. creates **one** issue titled `[CI] GitHub Actions failure digest` and **edits it in
   place** on later runs, closing it with an "all green" comment when nothing is failing.

It deliberately exits 0 while reporting failures — a red digest would register as one more
failing workflow and bury the signal it exists to deliver. Issue posting is
`continue-on-error: true` so restricted-permission forks still get the summary and artifact.
Cancelled runs are included on purpose, precisely because in this repo a cancellation is
usually a timeout-killed job that lost work.

Permissions are least-privilege (`actions: read`, `contents: read`, `issues: write`), and
`concurrency` is `cancel-in-progress: false` so a digest is never truncated mid-report.

## 4. Verification

- `python3 -c "import yaml; …"` parses all three files; `actionlint -shellcheck=shellcheck`
  on the three files reports no findings.
- The digest's issue-matching and count shell logic was exercised locally against the real
  `reports/gha_raw_logs_latest.json` (title match + count) before committing.
- `gha-failure-digest.yml` dispatched for real after merge (run `45725255620`, on the
  merge commit): **success** in ~53s. It swept 300 runs / 111 workflows and opened issue
  **#1146** containing the Hub Data Sync entry — summary + artifact + issue path proven
  end-to-end.
- `realtime-challenge` run `45726342320` (`schedule`, 00:06:40Z, post-fix) **success** — the
  first success after two consecutive cancelled runs. `portfolio-tracker` run `45727657271`
  (`workflow_dispatch`, 00:17:20Z, post-fix) **success**.
- The `:06` Hub Data Sync scheduled confirmation is recorded in §5.

## 5. Hub Data Sync gate — live confirmation

The `:06` firing queued as run `45719481029` was still on the **pre-fix** sha `b66ad3359`
and failed the **old** gate (`##[error]hub manifest is 268.6 days stale`). The repaired
gate from PR #1141 (`ffa177e07fa9`, confirmed an ancestor of `origin/main`) replaced that
hard failure with a >180-day *warning*. The first firing after the repair is recorded below.

**Observed outcome (2026-11-26T00:27Z): the `:06` scheduled firing never ran.**

- `hub-sync` workflow id `281991676`, state `active`, cron still `6 * * * *`. No
  `schedule`-event run was enqueued for the 00:06 slot (polled every 10s from 23:59Z to
  00:27Z). `portfolio-tracker`'s 00:07 slot was skipped too.
- This is not a repo-wide schedule outage: dozens of other `schedule` runs landed between
  00:00Z and 00:17Z, including `realtime-challenge` at 00:06:40Z. Both skipped workflows are
  `active`, so this reads as a per-workflow enqueue drop by GitHub's scheduler (delays and
  drops are documented under load, and this repo carries hundreds of schedules).
- The repaired gate was nonetheless executed on post-fix code: run `45725291106`
  (`workflow_dispatch`, sha `58803925e`) **succeeded** at 2026-11-25T23:58:10Z, and the
  00:17:21Z sweep no longer lists Hub Data Sync among failures. The old gate's
  `##[error]hub manifest is 268.6 days stale` is gone — the 268-day manifest is now a
  `::warning`, as designed.
- **Still outstanding:** confirmation from an actual `schedule` firing. Next natural
  observation point is the 01:06 slot, which normally enqueues 01:11–01:14Z.
