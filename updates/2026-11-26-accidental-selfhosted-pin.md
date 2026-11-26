# A throw-away-branch pin leaked onto main (2026-11-26)

## What happened

To test workflows on the idle self-hosted ARM64 runners, `tools/gha_selfhosted_batch.py`
creates a throw-away branch from `origin/main`, rewrites `runs-on:` to
`[self-hosted, Linux, ARM64]`, dispatches, then deletes the branch. The design assumes
`main` never carries a pin.

`strategy-funnel-hourly.yml` breaks that assumption: it rebuilds data, commits it, and
pushes with `.github/scripts/safe_push.sh`, which pushes **HEAD**. Running it from the
pinned branch meant the pin travelled inside the workflow's own data commit. Main received:

```
4ca0524091fc ci(temp): run strategy-funnel-hourly.yml on the self-hosted runner
```

`git show origin/main:.github/workflows/strategy-funnel-hourly.yml` then read
`runs-on: [self-hosted, Linux, ARM64]` — an hourly production workflow pinned to a box that
other agents share, that goes offline, and whose listeners have already flapped once today.
If the runner had gone offline, that workflow would have queued forever with no failure.

## How it was caught

After the parallel runs finished, every workflow touched in the session was re-checked
against main:

```bash
git grep -l "runs-on: \[self-hosted" origin/main -- .github/workflows
```

`strategy-funnel-hourly.yml` was the only pin that appeared during this session. The other
six (`crypto-winner-scan`, `daily-miracle-scan`, `discord-bot`, `refresh-creator-updates`,
`runner-smoke-test-linux`, `runner-smoke-test`) predate it and were left alone.

## Fix

1. **Reverted the pin** (PR #1191): one line back to `runs-on: ubuntu-latest`. Merged before
   the next hourly tick.
2. **Refused by default** in `tools/gha_selfhosted_batch.py`: new `pushes_own_head()` reads
   the workflow and checks for `safe_push.sh`, `safe_commit_push.sh`, `git push` or
   `git-push`. If present, the dispatcher prints `REFUSED_PUSHES_HEAD` and skips it. A
   `--allow-push-workflow` flag exists for workflows that push an explicit branch or path
   rather than HEAD.
   Comment lines are stripped before matching, so a workflow that merely *documents*
   `safe_push.sh` (as `gha-queue-audit.yml` now does) is still dispatchable.

## How it was verified

`python3 -m pytest tests/test_gha_batch_push_guard.py tests/test_gha_log_classifier_echo.py tests/test_gha_usage_triage.py -q`
→ **18 passed**.

- `pushes_own_head()` is True for `strategy-funnel-hourly.yml` (the one that leaked) and
  False for `gha-queue-audit.yml` (read-only monitor that only mentions it in a comment).
- Dry run: `python3 tools/gha_selfhosted_batch.py -w strategy-funnel-hourly.yml` now prints
  `[refuse]` and records `REFUSED_PUSHES_HEAD` instead of dispatching.
- `origin/main:.github/workflows/strategy-funnel-hourly.yml` reads `runs-on: ubuntu-latest`
  after the revert.

## Rule for the batch protocol

Batch only workflows that are read-only with respect to git. If a workflow pushes, either
leave it on `ubuntu-latest` or give it a `runner` input (`inputs.runner`) so it can be
dispatched on `main` with `-f runner=self-hosted` and no pin at all.
