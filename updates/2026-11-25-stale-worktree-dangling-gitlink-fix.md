# Stale worktree / dangling gitlink cleanup — 2026-11-25

## What was broken

`git worktree list` showed only the main worktree, so at first glance there were no stale
worktrees. The real problem was a **committed submodule-style gitlink** at:

```
.qwen/worktrees/audit-pick-funnel-analysis-2026-05-31
```

Facts established before touching anything:

| Check | Result |
|---|---|
| `git worktree list --porcelain` | 1 worktree only (main) |
| `.git/worktrees/` metadata dir | does not exist |
| `git ls-files -s .qwen` | one entry with mode `160000` → gitlink, not a real directory |
| `.gitmodules` | **does not exist** |
| `git config --get-regexp '^submodule\.'` | **empty** |
| on-disk contents | **empty directory** (0 files, 0 bytes) |
| pointed-to commit `a3486de3…` | **not in the object DB** (`fatal: bad object`) |

So the entry was doubly broken: a recorded submodule with no URL, pointing at a commit
that does not exist in this repository. Nothing was recoverable from it — the worktree's
contents (referenced in `reports/peer_claude-OWNERSHIP_QWEN_PENDING_WORK_2026-05-31.md`)
were already gone.

### Why it mattered

Because the gitlink had no matching `.gitmodules` URL, every `git submodule foreach --recursive`
call failed with exit 128:

```
fatal: No url found for submodule path '.qwen/worktrees/audit-pick-funnel-analysis-2026-05-31' in .gitmodules
```

GitHub Actions runs `submodule foreach` in its **post-job cleanup** step, so this surfaced as
red/failing CI across unrelated workflows. `reports/gha_actions_summary.json` records it on at
least: `execute-challenge`, the ML gatekeeper `train` jobs, `Gitleaks secret scan`, and `refresh`.

## What was changed

1. `git rm --cached .qwen/worktrees/audit-pick-funnel-analysis-2026-05-31`
   — removed the dangling gitlink from the index. The path held no files, so no content was lost.
2. `rmdir .qwen/worktrees/audit-pick-funnel-analysis-2026-05-31`
   — removed the leftover empty directory. The parent `.qwen/worktrees/` is kept because tooling
   (e.g. `.claude/skills/win-to-linux-path/`) resolves worktree-scoped paths through it.
3. `.gitignore` — appended a guard so a worktree scratch dir can never be committed as a gitlink again:

```gitignore
# --- Tool worktree scratch dirs (must never be committed; a gitlink here breaks CI submodule traversal) ---
.qwen/worktrees/
.claude/worktrees/
```

Existing CRLF line endings in `.gitignore` were preserved (appended via `printf '\r\n'`).

## How it was verified

```
gitlink count in index ......... 0   (was 1)
git ls-files -s .qwen ........... only .qwen/settings.json remains
git submodule foreach --recursive 'echo traversal-ok'
    → exits 0, no "No url found" fatal (was exit 128)
git worktree list ............... main worktree only
git status --short .............. M .gitignore
                                  D  .qwen/worktrees/audit-pick-funnel-analysis-2026-05-31
```

The `foreach` check is the meaningful one: it reproduces the exact command the GitHub Actions
post-job cleanup runs, and it passes now.

## Notes / follow-ups

- Changes are left **uncommitted** on branch `qwen/audit-deep-dive-fix` (a branch shared with
  other agents). Committing or pushing needs an explicit OK, per the "Only Push Your Own Changes"
  rule.
- Historical reports under `reports/` and `June42026_claude_opus_4_7.MD` still *reference* the
  deleted worktree path. Those are frozen historical records and were intentionally left untouched.
- No other worktrees were found on disk (no nested `.git` dirs, no `.qwen/tmp`, no sibling clones).
