# 2026-06-03 - CI test portability and PR #340 drift fix

## What was broken

The CI investigation turned up three failing tests in the local reproduction of
the repo's main pytest command:

1. Two tests spawned `python` directly in `subprocess.run(...)`, which fails in
   environments where only `python3` is on `PATH`.
2. The PR-triage regression test still asserted that PR `#340` must remain
   closed and unmerged, but the live GitHub PR `#340` is now a later docs-only
   PR that was intentionally merged.

## What changed

- Replaced hard-coded `"python"` subprocess invocations with `sys.executable`
  in:
  - `tests/test_deep_dive_verification_2026_05_14.py`
  - `tests/test_supplemental_prework_audit_2026_05_14.py`
- Narrowed `TestClosedPRsStayClosed` to the still-valid blocked PR `#363`.
- Updated `docs/PR_TRIAGE_2026_04_25_MERGE_SUCCESS_TESTS.md` so the test
  contract matches current GitHub truth.

## Why this is the right fix

`sys.executable` is already the repo's dominant pattern for subprocess-based
Python tests and makes these tests interpreter-agnostic without changing the
tools they exercise.

For the PR-triage suite, the purpose is to guard live invariants, not preserve
an outdated assumption forever. Keeping `#340` in the closed-not-merged list now
creates a permanent false red.

## Verification

Ran the affected subset:

```bash
python3 -m pytest \
  tests/test_deep_dive_verification_2026_05_14.py \
  tests/test_supplemental_prework_audit_2026_05_14.py \
  tests/test_pr_triage_2026_04_25_merge_success.py -v
```

Result after the fix: the targeted failures are removed.
