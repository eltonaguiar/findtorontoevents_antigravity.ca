# Two green-but-frozen pipelines (2026-11-15)

Method: rather than trusting workflow conclusions, each workflow's last run was
compared against the timestamp inside the artifact it is supposed to write.
Two workflows had been succeeding for days while their published data froze.

## 1. `feature-signals-hourly` — payload frozen 4 days, job green

| | |
|---|---|
| workflow | `feature-signals-hourly.yml`, cron `25 0,8,16 * * *`, last runs all `success` |
| artifact | `audit_dashboard/data/feature_signals_latest.json` |
| live copy | `https://findtorontoevents.ca/audit/data/feature_signals_latest.json` → `generated_at 2026-11-11T08:30:23` (4 days stale) |

**Root cause** — the publish line was:

```yaml
git push || echo "::warning::push failed (concurrent commit)"
```

A bare `git push` is non-fast-forward in this storm-commit repo, so it failed on
every run and the `|| echo` swallowed it. The refresh was committed locally and
discarded when the runner was torn down. The job never reported a problem, which
is why this survived 4 days and ~12 green runs.

**Fix** — publish through the repo's existing `.github/scripts/safe_push.sh`
(fetch + rebase + ref-lock retries, and it deepens shallow checkouts itself).
`permissions: contents: write` was already present.

## 2. `hyro_pick_performance.json` — frozen 7 days, validator crashed every run

| | |
|---|---|
| producer | `tools/hyro_pick_performance_validator.py`, invoked from `audit-dashboard.yml` |
| artifact | `audit_dashboard/data/hyro_pick_performance.json` |
| live copy | `generated_at 2026-11-08T02:14:09` (7 days stale) |

**Root cause** — reproduced locally in one command:

```
File "tools/hyro_pick_performance_validator.py", line 326, in extract_signals_from_closed_picks
    if sig_dt < cutoff:
TypeError: can't compare offset-naive and offset-aware datetimes
```

DB timestamps come back tz-naive (stored as UTC) while `cutoff` is tz-aware. The
crash was masked twice over: the workflow runs
`python tools/hyro_pick_performance_validator.py ... || echo "failed (non-fatal)"`
with `continue-on-error: true`, so the hourly dashboard job stayed green while
the artifact never advanced.

**Fix** — when `sig_dt.tzinfo is None`, treat it as UTC via
`sig_dt = sig_dt.replace(tzinfo=cutoff.tzinfo)` before the comparison.

Note: the artifact IS in `audit-dashboard.yml`'s commit list
(`audit_dashboard/data/hyro_pick_performance.json`), so once the validator runs
clean the payload will publish normally — no workflow change was needed.

## Audit results (312 scheduled workflows, cron-aware)

Staleness was judged against each workflow's own cron cadence, not a flat 24h
cutoff, then the artifact cross-check decided whether a green run meant data.

**Genuinely stale / dead:**

| workflow | last run | why |
|---|---|---|
| `mysql-q001-sync.yml` | 4200h ago, **failure** | cron `0 8 24 5 *` = once a year; last attempt failed |
| `poc-picks-checkpoint.yml` | 2820h ago | crons hardcoded to 2026-07-18/20 — permanently inert |
| `forex-agent.yml`, `forex-smart-picks.yml` | 3951h / 3947h | `disabled_manually` in GitHub; last runs were `success` |
| `ai-tournament-pipeline.yml`, `battle_test.yml` | 3932h / 3728h | `disabled_manually` |

**Checked and cleared (do not flag):**

- `daily-top-picks-filter` — artifact 5.2h old vs 0.4h run is its own
  `git diff --staged --quiet && echo "no changes"` guard, not a failure.
- `edge_decay_heatmap.json` (185d) — written by a backtest tool, **not** by
  `edge-decay-check.yml` (which writes `audit_trail/data/edge_decay_report.json`).
  Historical artifact, not live data.
- `ai_tournament_leaderboard.json` — `ai-leaderboard-refresh.yml` is
  `workflow_dispatch`-only; the leaderboard is refreshed by
  `tools/ai_tournament/update_leaderboard.py` instead (artifact was 10h old).
- `audit_dashboard/data/dashboard_data.json` (26d in git) — intentionally
  gitignored; the deployed copy is fresh (`generated_at 2026-11-15T07:54`).
- Microsoft/antivirus style false positives ruled out: 0 duplicate YAML keys,
  0 workflows with missing `on:`.

## Verification

- `ast.parse` on the patched validator: ok.
- `yaml.safe_load` on the patched workflow: ok; `safe_push.sh` present, bare
  `git push ||` gone.
- Validator re-run read-only: **`TypeError: offset-naive` occurrences = 0** (was a
  hard crash on every run).

## NOT MEASURED

- Neither fix has yet been proven by a scheduled run writing fresh data: the next
  `feature-signals-hourly` tick is 16:25Z and `audit-dashboard` is hourly. Until
  then the live timestamps remain 2026-11-11 and 2026-11-08. The proof to look
  for is `generated_at` moving past those values on the live site.

## Addendum — sequencing correction

The first commit merged (#807) carried the validator fix and this document, but
its workflow edit silently aborted on a line-ending mismatch: the publish line in
`feature-signals-hourly.yml` did not match the literal string, the script exited
before writing, and the job still ran `git push`. That was caught by the
verification step (`safe_push present: False`), which means the claim above was
briefly not backed by code.

The workflow change is applied in the follow-up commit on this branch, using an
EOL-tolerant regex over the publish line, and re-verified with
`yaml.safe_load` plus string assertions. Lesson: a guard that silently `exit 1`s
inside a heredoc must be checked for by the step that follows it, not assumed.
