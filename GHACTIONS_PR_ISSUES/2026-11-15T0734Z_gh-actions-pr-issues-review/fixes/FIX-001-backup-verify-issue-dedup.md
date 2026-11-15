# FIX-001 — backup-verify issue deduplication

**File:** `.github/workflows/backup-verify.yml`
**Severity:** P0
**Status:** Proposed (not yet applied)

## What was broken
`backup-verify.yml` runs monthly on the 15th at 06:00 UTC. On every failure it opens a brand-new GitHub issue titled `[backup-verify] Restore check FAILED — <date>` with labels `backup-verify, automated`. There is no deduplication against existing open issues, so each monthly failure spawns a new issue.

**Evidence:** 5 new `backup-verify` issues opened today 2026-11-15 alone (#780, #781, #782, #783, #787 between 06:03–07:34 UTC). Monthly cadence shows 8–9 issues per month going back to 2026-06.

## What to change
Add a deduplication step before "Open failure issue":
1. Use `gh issue list --state open --label backup-verify --search "Restore check FAILED — $(date -u +%Y-%m-%d)"` (or `github-script` with `github.rest.issues.listForRepo`) to check for an existing open issue for today.
2. If one exists, post a comment with the new failure details + run URL instead of creating a new issue.
3. If none exists, create the issue as today.
4. On success (`success()`), optionally close any open today-dated `backup-verify` issue with a resolution comment.

## How to verify
- Run `gh issue list --state open --label backup-verify --search "Restore check FAILED — 2026-11-15"` and confirm only one issue per date exists after the fix.
- Trigger the workflow via `workflow_dispatch` and confirm no duplicate issue is created when one already exists for the date.
- Confirm `py_compile` smoke test still passes on the key modules listed in the workflow.

## Related
Open issue spam: #780–#787 (2026-11-15), #721–#728 (2026-10-15), #686–#694 (2026-09-15).