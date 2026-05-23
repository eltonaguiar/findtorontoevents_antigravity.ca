# CI Guide

## Overview

The CI pipeline runs on every push and pull request to `main`. It consists of three stages:

1. **Config Lint** — Validates all JSON config files are parseable.
2. **Unit Tests** — Runs the full test suite via `pytest`.
3. **Integration Test** — Executes a backtest dry run (only runs after lint + unit tests pass).

## Running CI Locally

Use the local CI script from the repo root:

```bash
bash scripts/ci_local.sh
```

This runs config linting and unit tests — the same checks GitHub Actions will run.

## Pre-Commit Hook

To run CI checks automatically before every commit, install the pre-commit hook:

```bash
ln -sf ../../scripts/pre_commit_hook.sh .git/hooks/pre-commit
```

Now every `git commit` will trigger `ci_local.sh` first. If any check fails, the commit is aborted.

## What Gets Checked

| Stage | What | Command |
|-------|------|---------|
| Config Lint | JSON validity | `python -c "import json; json.load(open('config/...'))"` |
| Unit Tests | All tests | `python -m pytest tests/ -v --tb=short` |
| Integration | Backtest sanity | `python impl/alpha_engine/policy_backtest.py --dry-run` |

## Adding a New Config File

If you add a new JSON config file, add a corresponding lint line to:

- `.github/workflows/ci.yml` (under the `lint-config` job)
- `scripts/ci_local.sh`

Keep them in sync.
