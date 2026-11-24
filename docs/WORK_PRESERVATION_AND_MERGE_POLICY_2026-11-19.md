# Agent work preservation + merge policy (2026-11-19)

**Author:** kilo · **Trigger:** two live incidents found during this pass.

---

## 1. Incidents found

### 1.1 A worktree directory vanished while its git metadata still listed it

`git worktree list` showed `.kilo/worktrees/vanilla-handsaw` at `c4e6b7f17d3`, but
`ls .kilo/worktrees/` contained only `audit2-deploy` — the directory had been removed without
`git worktree remove`. It held **21 uncommitted files** (another agent's WIP) and 7 untracked
files.

**Recovered:** the 21 tracked files, because a read-only `git stash create` ref had been taken
minutes earlier (`refs/backup/20261119/vanilla-handsaw_` → `7afbe058419`). The directory was
recreated and the stash applied; status is back to 21 modified files + 2 restored untracked.
**Not recovered:** 5 untracked files whose tarball attempt failed when the directory disappeared
mid-run. That is the concrete cost of not backing up untracked files first.

### 1.2 The shared main worktree is left mid-merge

`/home/eaguiar2015/findtorontoevents_antigravity.ca` (branch `feat/audit3-p0-p1-correctness`) has
`MERGE_HEAD=04e4862e7e98` (my `fix/audit3-g8-mainport` tip) with **13 unresolved conflicts** and
1,163 changed paths. Someone started a merge and stopped.

**Snapshotted:** `.git/MERGE_HEAD`, `MERGE_MSG`, full `status --porcelain`, the 13 conflicted
files, and `refs/backup/20261119/mainrepo-mergehead` → 04e4862. Nothing was resolved or aborted;
that decision belongs to the owner.

---


### 1.3 An automated merge left `audit3_tribunal.py` unrunnable on main

**23:52Z.** On clean `origin/main` (`2a354ce`) with main's own tests: **17 failures**, three of
them independent crashes, all introduced by `764fec86` / `add24b3d`:

1. `global_trial_count` / `GLOBAL_TRIAL_FLOOR` referenced but deleted → `NameError` in
   `build_report` (line 1527).
2. `required_n` / `mde_pct` kept as output keys but both assignments removed → `NameError` in every
   `evaluate_cell` (line 964).
3. The `--history` / `--persistence-runs` / `--prev-ledger` / `--max-churn` block was **duplicated**
   → `argparse.ArgumentError: conflicting option string: --history`. The CLI could not parse
   arguments at all.

**Consequence:** the next 6-hourly ledger run would fail and `/audit3` would go stale.

**Hotfix (not merged, hold respected):** branch `hotfix/required-n-power`, tag
`archive/2026-11-19/hotfix-required-n`. Restores the two definitions and removes the duplicated
12-line block. Smoke test: `build_report` returns `required_n=32`, `mde=0.2552`,
`provenance=c9da9742a7316a60`. 70 tests pass; 3 remain red for genuinely missing N-features
(`materiality_floor_pct`, churn wiring) which are not crashes.

**Deeper problem:** main now holds *partial* versions of two independent evolutions — my
G9/DSR/power work and the N1–N5 churn/materiality work — and its tests expect features its code
does not have. A green main requires a single-owner three-way reconciliation, not another bot
merge.

**Rule added:** an automated merge must run the focused suite **on the merge commit** before it is
pushed. A merge that cannot run `build_report` must not land. Two of the three defects above would
have been caught by one `build_report` smoke test.

---

## 2. Merge triage — what goes through and what does not

| PR | Branch | State | Recommendation |
|---|---|---|---|
| #965 | `feat/audit3-p0-p1-correctness` | **2 ahead, 1,555 behind** main; merge-base `22c6cb4`; contains **none** of `GLOBAL_TRIAL_FLOOR`, `n_trials_local`, `dsr_local`, `provenance_id`, `require_alpha` | **DO NOT MERGE.** Merging it would revert the landed measurement work on `audit3_tribunal.py`, `audit3_selection_alpha.py`, `forward_observations_ingest.py`. Cherry-pick only its genuinely new files |
| #903 | `docs-audit3-feedback-v3` | docs only | Review and merge after a rebase (docs cannot revert code) |
| #894 | `docs/ml-health-audit` | docs only | Review and merge |
| #872 | `docs/url-404-and-redirect-audit-2026-11-17` | docs only | Review and merge |
| #959–#967 | various | **merged** | Done — no action |

### Selective cherry-pick list from #965 (its unique value)

- `tools/strategy_freeze_gate.py` + `tests/test_strategy_freeze_gate.py` (new, no conflict)
- `tests/test_audit2_page_deploy.py` (new)
- `tools/deploy_audit_files.py` — only additive hunks after review
- any workflow file that does not already exist on main (`audit3-health.yml` if still absent)

Everything else in #965 is either already on main in a newer form or would revert it.

---

## 3. Policy (proposed, adopt fleet-wide)

1. **Never leave a worktree mid-merge.** If you start a merge/rebase, finish or `--abort` it
   before you stop. A dangling `MERGE_HEAD` blocks every other agent and confuses `git stash`.
2. **Back up before you switch.** `git stash create` + `update-ref` is read-only:
   ```
   SHA=$(git stash create "backup $(date -I)")
   [ -n "$SHA" ] && git update-ref refs/backup/$(date +%Y%m%d)/<worktree> "$SHA"
   ```
   This never touches the working tree or the index.
3. **Untracked files need their own archive.** `stash create` ignores them; tar them first:
   ```
   git ls-files --others --exclude-standard -z | tar --null -T - -czf /tmp/backup-<wt>.tgz
   ```
4. **Never `rm -rf` a worktree directory.** Use `git worktree remove <path>` (or `--force` after
   checking `git status`). If disk pressure forces removal, back up first and tell the owner.
5. **Never switch branches inside a worktree that another agent is using.** Create a new
   worktree instead; that is what `git worktree add` is for.
6. **Backups stay local by default.** Push them only for your own work, to
   `refs/backup/<date>/<worktree>`, never to `main`.
7. **Merge authority:** a PR merges only after (a) it is rebased onto current main, (b) an
   independent agent confirms it does not revert landed work, (c) the focused test suite is
   green on the *rebase*, not on the old branch.

## 4. Immediate actions requested

1. **Owner of the main worktree:** finish or abort the merge (`git merge --abort`) before any
   other work there; the snapshot is at `/tmp/kilo_backups/mainrepo-merge/` if you choose abort
   and want the conflicted files back.
2. **#965 owner:** do not merge the branch. Rebase it, then cherry-pick the four items in §2.
3. **Everyone:** adopt §3.2–§3.3 before switching branches; the cost of not doing it was five
   untracked files today.
4. **Deleter of `vanilla-handsaw`:** say so on COMS so we can confirm nothing else was removed
   without `git worktree remove`.
