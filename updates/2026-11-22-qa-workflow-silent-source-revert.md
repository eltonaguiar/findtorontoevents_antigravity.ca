# A `[skip ci]` QA commit was silently reverting source files — including the CI fix itself

**Date:** 2026-11-22 · **Files:** `.github/workflows/qa-market-validation.yml`, `tools/audit2_forward_summary.py`, `tests/test_qa_workflow_does_not_revert_sources.py`

## What was broken

Between 07:41 and 08:05 UTC on 2026-11-22, `merge_gate` existed on main and then
did not. #1048 added it at 07:41:51; the bot commit
`41f7bb9d5fa chore(qa): market validation snapshot [skip ci]` (08:00:17 UTC)
removed it again. Every PR that ran CI in that window failed at **collection**:

```
ImportError: cannot import name 'merge_gate' from 'tools.audit2_forward_summary'
```

Its `--stat` was the tell: one "QA snapshot" commit also carried a 27,361-line
deletion in `alpha_engine/data/closed_picks.json` and 4,245 changed lines in
`alpha_engine/data/active_picks.json`. A job that writes one artifact had
republished the whole tree.

## Root cause

`qa-market-validation.yml` retries its push like this:

```yaml
timeout 180 git fetch -q --depth=1 origin main || true
git reset --soft FETCH_HEAD || true
git add "$A"
git commit -q -m "chore(qa): market validation snapshot [skip ci]"
```

`actions/checkout` here is `fetch-depth: 1`, and the job is triggered by an
hourly cron, so its tree is minutes old while main keeps moving. On a rejected
push, `git reset --soft FETCH_HEAD` moves **HEAD only**. The index still holds
every file as of the run's start, so the following `git commit` publishes that
stale index over the new tip — reverting every source file that changed in
between. That is why a data job deleted a function from `tools/`.

## What changed

- `git reset --soft FETCH_HEAD` → `git reset FETCH_HEAD` (mixed). The index
  matches the new tip, the artifact stays in the worktree, and the existing
  `git add "$A"` re-stages just that file. Comment records why `--soft` is unsafe.
- `tools/audit2_forward_summary.py` restored from `25a3ea8bf8b` (#1048's tree).
- New guard `tests/test_qa_workflow_does_not_revert_sources.py`: fails if the
  workflow reintroduces `git reset --soft`, or widens staging to `git add -A`
  / `git add .`. Verified it **fails against the old workflow** and passes after.

## Verification

- `pytest tests/test_qa_workflow_does_not_revert_sources.py tests/test_audit2_forward_summary.py tests/test_verify_live_claim.py -q` — **12 passed**
- Re-ran the guard with the old workflow restored — **1 failed** (it catches the bug it was written for)
- `py_compile tools/audit2_forward_summary.py` — OK

## Why this matters beyond CI

This is the silent-file-revert hazard in `AGENTS.md`: an automated `[skip ci]`
commit can undo a merged fix while every dashboard and scheduler stays green.
Any future "it's fixed on main" claim needs the file check in
`tools/verify_live_claim.py`, not the merge timestamp.
