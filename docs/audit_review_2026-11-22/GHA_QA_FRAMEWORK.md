# GHA quality framework

Design of `tools/gha_quality_framework.py`. It is a static, offline companion to the runtime
auditor `tools/gha_health_audit.py` (R1-R12). A rule described here exists because its test
passes (`--self-test`), and nothing here is delegated to an AI.

## Why a second auditor

R1-R12 answers "what is broken now" from run history: failed-no-success, flapping, queue hogs,
cancel churn. It cannot see that a workflow file is structurally fragile, e.g. two workflows write
the same artifact, or a gate step swallows its own failure. Those are visible in the YAML,
deterministically, with no token. The measured motivation is the `/audit`-lags-`/audit3`
duplicate-producer class of bug [SRC: plan section 0].

## Layer A - Inventory and metadata

For every file in `.github/workflows/*.yml|*.yaml` the tool records:

| Field | How |
|---|---|
| triggers | `on:` as string, list, or mapping (YAML 1.1 makes bare `on` a bool, handled) |
| cron entries | every `schedule[].cron` |
| permissions | whether a `permissions:` block exists, and its value |
| concurrency | the group |
| secrets | every `secrets.NAME` in step `env`, `with`, and `run` |
| actions | every `uses:` with its pin |
| continue-on-error | count |
| `|| true` / `|| :` | count |
| gate steps | steps whose label names a gate and is not a deploy/commit step |
| silent gate steps | gate steps with continue-on-error or `|| true` |
| timeouts | per-job `timeout-minutes` |
| push steps | `git push`/`git commit` steps, and whether `[skip ci]` is present |
| artifacts | produced (`> file`, `git add file`) and consumed (`cat`, `jq`, `open(...)`, `< file`) |

A workflow that fails to parse is still inventoried, with `parse_error` set (fail-closed).

## Layer B - Static rules

Q1-Q10 are defined with severity and rationale in `GHA_QA_RULE_CATALOG.md`.

## Layer C - Runtime signals

Optional. `--runtime-report GHACTIONS_LIVE/gha_health.json` merges R1-R12's R1 rows: any workflow
flagged broken-now loses 10 points and is marked in the report. Absent file means no runtime
signals and the tool still runs (`--no-runtime` forces this).

## Layer D - Scoring and budget

Per workflow, start at 100 and subtract the weight of each finding attributed to it:

| Signal | Weight |
|---|---|
| parse error | 30 |
| Q7 silent-failure | 25 |
| Q5 duplicate-producer | 15 |
| Q8 missing-timeout | 10 |
| Q3 write-all-default | 10 |
| Q2 unpinned-action | 5 |
| Q4 self-push-without-skip-ci | 5 |
| Q1 cron-stampede | 5 |
| Q6 orphan-artifact | 3 |
| Q9 secret-sprawl | 3 |
| Q10 dead-schedule | 3 |
| broken now (runtime) | 10 |

The repo aggregate is the mean of per-workflow scores. Budget: the tool makes zero network calls,
reads at most one runtime JSON, and parses each workflow once, so it cannot become a queue hog.

## Layer E - Gate and report

- `--check` exits non-zero on any blocking (P0/P1) finding.
- `--check --baseline <file>` exits non-zero only on blocking findings **not** in the baseline.
  This is what lets the gate be enforced today without 103 pre-existing violations blocking every
  PR. `--write-baseline <file>` records the current set.
- `--dry-run` prints the report and writes nothing.
- The runner `gha-quality-framework.yml` starts dispatch-only, has its own concurrency group, a
  staggered cron minute (:13, never :00), and commits its report with `[skip ci]`.

## Advisory vs blocking

| Rule | Severity | Gate |
|---|---|---|
| Q5 duplicate-producer | P0 | blocking |
| Q7 silent-failure | P0 | blocking |
| Q2 unpinned-action | P1 | blocking |
| Q3 write-all-default | P1 | blocking |
| Q8 missing-timeout | P1 | blocking |
| Q1 cron-stampede | P2 | advisory |
| Q4 self-push-without-skip-ci | P2 | advisory |
| Q6 orphan-artifact | P2 | advisory |
| Q9 secret-sprawl | P2 | advisory |
| Q10 dead-schedule | P2 | advisory |

Rationale: P0/P1 are correctness hazards that are cheap to fix locally. P2s are either
noisy heuristics (Q1 needs contention context the file does not have) or repo-wide policy
questions (Q6/Q9/Q10 need an owner decision), so they warn and score but do not block.

## Measured first run

Over 375 workflow files: 1 parse error, aggregate 94.4/100, 103 blocking violations:
Q2 10, Q3 28, Q5 21, Q7 40, Q8 4 [SRC: GHACTIONS_LIVE/gha_quality.md].
