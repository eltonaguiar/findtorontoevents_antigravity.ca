# The liveness guard resolved only `origin/main` — and CI has no `origin/main`

**Date:** 2026-11-22 · **Files:** `tools/verify_live_claim.py`, `tests/test_verify_live_claim.py`

## What was broken

`verify_live_claim.py` answered "is this feature live?" with
`git cat-file -e origin/main:<path>`. On a developer machine that ref exists. In CI
(`actions/checkout` fetches the **detached merge ref**, not remote branches) it does
not, so the tool reported a merged feature as `ABSENT on origin/main` — the very
false statement the tool exists to prevent, pointing the other way. It showed up as
`tests/test_verify_live_claim.py::test_path_on_ref_detects_a_merged_file FAILED` in
run 44999508284 once #1048 let the suite run.

## What changed

- `resolve_ref()` tries the given ref, then `refs/remotes/origin/main`, then a local
  `main`, returning the name and commit SHA that actually exist.
- `path_on_ref()` uses the resolved name, and when **nothing** resolves it fails with
  `cannot resolve … the claim is NOT verified` instead of guessing a tree. Unverifiable
  is never treated as verified.
- `VERIFY_LIVE_REF` env override; `--ref` still works as before.
- Tests build their fixtures in a throwaway `git init` repo with `refs/remotes/origin/main`
  set via `update-ref`, plus a case that deletes that ref to reproduce the CI shape and
  a case asserting an unresolvable ref refuses. No test borrows this clone's refs.

## Verification

- `py_compile` OK
- `python3 -m pytest tests/test_verify_live_claim.py -q` — **7 passed** (was 5)
- Live use unchanged: `--path tools/forward_book.py` present; a bogus path still exits 1
  with `REFUSING` on stderr.
