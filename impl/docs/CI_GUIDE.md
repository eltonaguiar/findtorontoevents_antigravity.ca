# CI Guide (impl)

This folder contains lightweight CI automation for `impl/`:

- `impl/.github/workflows/ci.yml` - GitHub Actions workflow
- `impl/scripts/ci_local.sh` - local CI runner
- `impl/scripts/pre_commit_hook.sh` - pre-commit wrapper

## What CI runs

1. Python syntax checks:
   - `alpha_engine/stat_tests.py`
   - `alpha_engine/policy_eval.py`
2. Unit tests:
   - `tests/test_stat_tests.py`

## Run locally

From repo root:

```bash
bash impl/scripts/ci_local.sh
```

Or from `impl/`:

```bash
bash scripts/ci_local.sh
```

## Install as a git pre-commit hook

From repo root:

```bash
cp impl/scripts/pre_commit_hook.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Now each commit runs the same checks as local CI.

## Notes

- CI intentionally stays minimal for speed and reliability.
- If more tests are added under `impl/tests`, extend `ci_local.sh` and `ci.yml` together.
