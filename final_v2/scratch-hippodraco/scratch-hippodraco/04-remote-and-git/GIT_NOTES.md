# Git / remote notes (pass 2)

- `origin` = `git@github.com:eltonaguiar/findtorontoevents_antigravity.ca.git` (observed in this worktree)
- Prior session pushed docs to: `origin/docs/scratch-hippodraco-audit-2026-11-14` (audit MD + quick-wins). Merge status to `main` should be confirmed on GitHub.
- Many peer branches/worktrees exist locally (`finpredict-*`, `flaxen-hair`, `hilarious-seer`, etc.). For “remote truth”, prefer `origin/main` + open PRs/tags; do not assume a worktree branch is published.
- Recommended commands (run locally, not embedded here as destructive ops):
  - `git fetch origin --prune`
  - `git ls-tree -r --name-only origin/main | rg 'scratch-hippodraco|finpredict-v4_2026-11-14-1555|finpredict-v2_20261114-1602'`
