# Regime Terminal workflow commit hardening (2026-11-16)

## What was broken
- `.github/workflows/regime-terminal.yml` commit step could run 15 minutes, did not run with `if: always()`, lacked conflict-marker guard, did not authenticate remote for retry pushes, and could exit without failing after exhausted retries.

## What changed
- Set commit step to `if: always()` with `timeout-minutes: 5`.
- Added `bash .github/scripts/assert_no_conflict_markers.sh` before commit.
- Set authenticated `origin` remote using `TOKEN_FOR_PUSH` before push retries.
- Made retry loop fail explicitly after 3 attempts.

## Verification
- `python3 -m pytest tests/test_skyrocket_detector_wireup.py tests/test_ueps_workflow_yaml.py -q` → 45 passed (on `origin/main`-based branch).
- YAML/workflow behavior change only; runtime impact limited to `regime-terminal` data-commit reliability.

## Revert
- `git revert <commit>` or restore previous commit-step block in `.github/workflows/regime-terminal.yml`.
