# Cron collision audit against the weekly peer-claim verification job

**Date:** 2026-11-23
**Base:** `origin/main` @ `488d9ab920b322948c5640f6577ffea9e7b518f1`
**Question:** Block 28 moved `peer-claim-verification.yml` from `'23 6 * * 1'` to
`'31 6 * * 1'` to dodge `feature-stability-check.yml`, with the caveat *"If
anything else in the repo uses `'31 6 * * 1'`, it wasn't checked."* Was the move
sufficient?

**Answer: no. `stale-branch-cleanup.yml` already used `'31 6 * * 1'`.** The cron
is now `'18 6 * * 1'`.

## Method

Read-only inventory of every workflow in `.github/workflows/` (394 files at this
sha), parsed with PyYAML. The `on:` key is parsed as boolean `True` by PyYAML, so
the scripts read `d.get('on') or d.get(True) or {}` - noted here because it is the
classic gotcha that silently yields zero crons if unhandled.

## Totals

- **379 cron entries** across all workflows.
- **31 exact-duplicate cron strings** (i.e. a string used by 2+ workflows);
  336 distinct cron strings.
- Most duplicates are benign hourly-half-hour jobs (`0 * * * *`, `24 * * * *`,
  `50 * * * *`, ...) that this repo runs by design.

## The collision

`'31 6 * * 1'` was held by exactly two workflows:

| Workflow | Role |
|---|---|
| `peer-claim-verification.yml` | This job: runs branch-containment / ancestry checks, then commits a report with `[skip ci]`. |
| `stale-branch-cleanup.yml` | `contents: write`, 30-min timeout, **deletes merged branches** older than N days via `actions/github-script`. |

This is not merely runner-queue contention. The verification engine checks
`git branch -r --contains` and `git merge-base --is-ancestor` for claims that land
on non-main refs; the cleanup job can delete exactly those branches in the same
minute. A branch-containment claim could read NOT LANDED purely because the
cleanup job removed the ref first - a false negative indistinguishable from a
real one.

## Monday hour-6 occupancy

Every enumerated candidate minute in hour 6 is already taken by at least one
recurring job:

| Minute | Occupants (abbrev.) |
|---|---|
| 31 | `mutation-lab.yml` (`31 */3`), `strategy-funnel-hourly.yml` (`31 *`), `stale-branch-cleanup.yml`, (this job) |
| 33 | `alpha-engine-fast.yml`, `buy-now-analysis.yml`, `discord_status.yml`, `mega-mutation-tracker.yml`, `signal-recorder.yml`, `update-creator-news.yml` |
| 37 | `crypto-intraday-sim.yml`, `prediction-quality-tracker.yml`, `sports-smoke-and-e2e.yml` |
| 41 | `crypto-smart-picks.yml`, `forward-observations-ingest.yml`, `recommended-portfolio.yml`, `tv-paper-tpsl-watchdog.yml` |
| 47 | `decile-separation-test.yml`, `hourly-master-picks.yml`, `outcome-resolver.yml`, `strategy-forward-tester.yml`, `torontoevent-deploy-riseoftheclaw.yml` |
| 53 | `claude-gainer-ml-live.yml`, `copy-trader-intelligence.yml`, `fc-crypto-pro.yml`, `incubator-strategies.yml`, `provenance-verify.yml`, `verified-pilot-daily.yml` |
| 59 | `deploy-battleground-ftp.yml`, `sports-data-snapshots.yml`, `torontoevent-spike-scanner.yml` |

**Minute 18 is the only minute in Monday hour 6 with no scheduled job at all**, so
that is the chosen slot.

## Coarse overlap (honest framing)

In a repo this size an hourly job overlaps almost any minute by construction -
e.g. `strategy-funnel-hourly.yml` (`31 * * * *`) and `mutation-lab.yml`
(`31 */3 * * *`) also fire at 06:31. That class of overlap is expected and is
**not** a defect. The class that genuinely contends is *hourly-or-slower,
non-trivial, committing* work sharing the slot - and `stale-branch-cleanup.yml`
was exactly that. Moving to 06:18 leaves the job sharing its minute only with
whatever unrelated hourly jobs exist there, which is the same situation as every
other job in this repo.

## Verdict

Block 28's move was **insufficient** - it fixed the `feature-stability-check.yml`
collision but landed on a second, arguably worse one (a branch-deleting job). The
cron is now `'18 6 * * 1'`. `docs/VERIFICATION.md` and the `AGENTS.md` dependency
table were updated to match.
