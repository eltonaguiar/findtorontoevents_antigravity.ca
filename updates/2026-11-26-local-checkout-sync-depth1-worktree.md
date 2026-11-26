# Local checkout synced to `main` (depth-1 fetch + worktree)

**Date:** 2026-11-26
**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca` (local `C:\findtorontoevents_antigravity.ca`)

## Problem

The working checkout was ~62 workflow files behind `main`, and four files needed
for offline gate runs did not exist locally at all:

- `tools/provenance_ledger.py`
- `tools/provenance_resolver.py`
- `tools/pick_data_quality_gate.py`
- `.github/workflows/pick-data-quality-gate.yml`, `.github/workflows/ci.yml`,
  `.github/workflows/tribunal-runtime-gate.yml`

A plain `git fetch origin main` timed out (>240 s) — the repo is ~3.7 GiB of git
objects and the network here is slow.

## What was done

```
git -c http.postBuffer=524288000 fetch --depth=1 --no-tags origin main
  -> origin/main = 3f69e44f573  ("System F Claws of Doom: sync 2026-11-26 01:37 UTC")

git worktree add --detach tmp/main_tree origin/main
  -> 48,717 files checked out, HEAD 3f69e44f573, 404 entries in .github/workflows
```

`tmp/` is gitignored, so the worktree does not pollute the index or the repo.

## Result

| | before | after (`tmp/main_tree`) |
|---|---|---|
| workflow files (`*.yml`/`*.yaml`) | 337 | **383** |
| files present on main but missing locally | 63 | — |
| `tools/provenance_ledger.py` | absent | present |
| `tools/provenance_resolver.py` | absent | present |
| `tools/pick_data_quality_gate.py` | absent | present |

The three gates that had been unverifiable now run locally and pass:

```
python tools/provenance_ledger.py --selftest    -> ALL SELFTESTS PASSED   exit 0
python tools/provenance_resolver.py --selftest  -> ALL RESOLVER SELFTESTS PASSED  exit 0
python tools/pick_data_quality_gate.py          -> PASS — pick-data-quality gate (500 rows)  exit 0
```

## Caveats

1. **The repo is now a shallow-fetch hybrid.** `.git/shallow` contains
   `3f69e44f573` (main) and `12b0e523a0` (PR #1116 head). History traversal stops
   at those commits for those refs; the feature branch's own history is intact.
   Undo with `git fetch --unshallow origin` (slow, same reason the original fetch
   timed out).
2. **`db_freshness_check` and `cross_db_consistency` still cannot run locally** —
   no `dbpasses.txt` / MySQL credentials in this environment. Those two gates need
   a machine with DB access.
3. **15 workflow files exist locally but not on `main`** (e.g.
   `ai-leaderboard-refresh.yml`, `cross-db-consistency.yml`, `db-freshness-check.yml`,
   `daily-price-refresh.yml`, `mysql-q001-sync.yml`, plus four `*.yml.retired`
   files). These are stale local leftovers, not files deleted from main in this
   session — `main` uses differently-named replacements for several of them. They
   are not a reason to re-sync; they simply should not be committed back.
4. The worktree shows one modified file (`.claude/skills/thingstocheck-June2026/SKILL.md`)
   immediately after checkout — a CRLF/attributes artifact on this Windows box, not
   an edit. Don't "fix" it.

## Do not

Do **not** run `git checkout origin/main -- .` or `git reset --hard` in the main
tree to "sync". That would silently revert the uncommitted work on
`fix/gha-silent-ml-noops-and-worktree-gitlink` and is exactly the failure mode
recorded in `updates/2026-11-25-stale-worktree-dangling-gitlink-fix.md`. Use the
`tmp/main_tree` worktree for anything that needs current `main`.
