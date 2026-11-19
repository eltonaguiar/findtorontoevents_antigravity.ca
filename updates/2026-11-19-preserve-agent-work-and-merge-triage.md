# Preserve agent work + merge triage (2026-11-19)

## What was broken

Agents share one clone with many linked worktrees. Two failure modes were live today:

1. **Branch switching strands uncommitted work.** During this session the primary
   worktree's HEAD changed under a running command — from `fix/sleeve-implausible-pf-2026-11-19`
   to `feat/audit3-p0-p1-correctness` — and 21 dirty paths stopped being visible. A
   subsequent `git checkout -b ... origin/main` **aborted** with "please move or remove
   them before you switch branches" because of other agents' untracked files, so a
   five-file commit landed on the wrong branch. Nothing was lost, but only by luck.
2. **Stale long-lived branches invite reverts.** `feat/audit3-p0-p1-correctness` (PR #965)
   is 1,555 commits behind `origin/main` and still carries three mechanisms main has
   since implemented better. Resolving its 15 conflicted files "keep my side" would
   silently delete `global_trial_count`, `provenance_id`, and `alpha_gate_report`.

## What changed

**New: `tools/preserve_agent_work.sh`.** Snapshots a worktree's modified + untracked
files onto a `backup/<label>-<stamp>` branch.

- Builds the snapshot through a **temporary `GIT_INDEX_FILE`**, so the source
  worktree's real index, HEAD, and current branch are never written. `git add -A` runs
  against the throwaway index only.
- Commits with `git commit-tree` (parent = the worktree's HEAD) and points a new ref at
  it. The snapshot is a *backup*, explicitly not a merge candidate.
- `--all` sweeps every registered worktree; `--push` sends to origin; without `--push`
  everything stays local and costs nothing.
- **Refuses to push a snapshot matching a secret pattern** (password assignments,
  `AUDIT_DB_PASS = '...'`, GitHub/Slack/Anthropic tokens, private-key headers, DSNs with
  inline credentials). It prints matching *paths*, never values. This directly guards
  against repeating the `b5f42b39ec1` plaintext-DB-password incident.
- Size guard (`--max-mb`, default 200) prevents a runaway data snapshot; `--allow-large`
  overrides.

**New: `reports/MERGE_TRIAGE_2026-11-19.md`.** Per-branch verdicts (GO / REPLAY / SPLIT
/ HOLD / BACKUP) with the mechanism-count evidence table, a corrected PR #965 resolution
plan, a merge order, and an explicit statement that branch owners execute their own
merges per `AGENTS.md`.

**Also settled:** kilo's volume-context A/B vote was already answered by main —
`04e4862e7e9` landed the sidecar (option B). No vote required.

## How it was verified

- `tools/preserve_agent_work.sh --help` prints usage and exits 0.
- Ran against a worktree with known uncommitted edits: created a `backup/...` ref,
  reported the dirty-path count, and the source worktree's `git status --porcelain` and
  `git rev-parse HEAD` were **identical before and after** (proves the temp-index design
  does not touch the source).
- Ran with `--push` on a clean worktree: correctly reported `CLEAN ... nothing to
  preserve` and pushed nothing.
- Secret guard exercised with a synthetic snapshot containing a fake
  `AUDIT_DB_PASS = 'x...'` assignment: snapshot was created locally and push was
  **refused** with the path list and no value echoed.
- Branch facts in the triage report are reproducible:
  `git rev-list --count origin/main..origin/<branch>`,
  `git show origin/main:alpha_engine/audit3_tribunal.py | grep -c global_trial_count`.

## Known limitations

- The snapshot is a point-in-time copy. It does not merge, dedupe, or reconcile with
  later commits; a second run from the same tree creates a second ref.
- The secret regex is narrow on purpose. It will miss exotic credential shapes, so it is
  a guard, not a guarantee — a passing snapshot is not a certificate of cleanliness.
- `--all` includes worktrees belonging to other agents. It only ever *reads* them, but
  pushing their snapshots to origin is still a publication decision; default is local.

## Files

- `tools/preserve_agent_work.sh` (new)
- `reports/MERGE_TRIAGE_2026-11-19.md` (new)
- `updates/2026-11-19-preserve-agent-work-and-merge-triage.md` (this file)
