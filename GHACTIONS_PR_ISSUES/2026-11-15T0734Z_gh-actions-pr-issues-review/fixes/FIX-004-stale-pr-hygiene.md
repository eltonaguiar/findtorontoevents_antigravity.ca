# FIX-004 — Stale pull request hygiene

**Scope:** GitHub Pull Requests (all open)
**Severity:** P2
**Status:** Proposed (not yet applied)

## What was broken
36 open PRs, of which 34 are stale (dating from 2026-06-24 back to 2026-10-04, plus 2 from today 2026-11-15). Stale PRs clutter the review queue and obscure the active wired-in CI fixes (#785, #786). None of the stale PRs show recent activity or linked successful CI runs.

## What to change
1. Keep the two newest PRs active:
   - #786 `fix(ci): restore QA price validation, snapshot pushes, and sports smoke` (`wired-in/buffy-gh-actions-fix-2026-11-15`)
   - #785 `Restore audit page script tags lost on main + tracker horizon fix` (`wired-in/buffy-2026-11-15-final`)
2. Close (or rebase-and-reopen) the 34 stale PRs, prioritizing:
   - #761 FTP credential rotation (2026-10-23) — related to FIX-002
   - #751 GHA health monitor (2026-10-22)
   - #749 resolver batch-close root cause (2026-10-20)
   - #744 forward_validator blacklist (2026-10-20)
   - #713 backup-verify false failures + issue spam (2026-10-04) — related to FIX-001
   - #711 stale tag defects (2026-10-04)
3. Add a stale-PR label/auto-close policy so PRs inactive >60 days are flagged.

## How to verify
- `gh pr list --state open` confirms only #785 and #786 remain as active wired-in CI fixes.
- Stale PRs closed with a note referencing this review.
- Confirm #713 (backup-verify issue spam) is addressed by FIX-001 before closing.

## Related
FIX-001 (backup-verify dedup), FIX-002 (FTP cert verification).