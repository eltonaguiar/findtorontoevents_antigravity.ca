# GHA best-practices hardening (2026-11-16)

## Scope
Low-risk hardening for data-commit workflows with known push-race/timeout failure modes. Avoided broad mass edits across 200+ workflows.

## Changes
- `.github/workflows/regime-terminal.yml`: commit step runs `if: always()` with `timeout-minutes: 5`, conflict-marker guard, authenticated remote for retries, explicit failure after 3 exhausted pushes.
- `.github/workflows/audit-impact-tracker.yml`: added `if: always()`, step timeout, `TOKEN_FOR_PUSH` remote auth, conflict-marker guard, and explicit failure after 3 retries.
- `.github/workflows/ueps-pick-runner.yml`: added step timeout, conflict-marker guard, authenticated remote, retry loop with warning+exit when push fails (step remains `continue-on-error` per existing behavior).

## Best-practice checklist applied (repo-relevant)
- Least-privilege/explicit permissions (kept/verified where present), bounded timeouts, conflict-safe auto-commits, authenticated retry pushes, fail-fast/explicit outcomes, `if: always()` where diagnostics/persistence needed.
- Repo-wide gaps still present: many workflows lack `permissions`/`concurrency`/job timeouts and 212 commit workflows lack full safeguards; action pinning to SHAs not broadly adopted.

## Verification
- `python3 -c "import yaml; ..."` for modified workflows: OK.
- `python3 -m pytest tests/test_skyrocket_detector_wireup.py tests/test_ueps_workflow_yaml.py -q`: 45 passed.

## Revert
- `git revert <commit>` or restore prior commit-step blocks in modified workflow files.
