# G1 — T3 fix replayed onto a clean, pushable branch

**Date:** 2026-11-23 · **Backlog:** G1 in `docs/BACKLOG_100_2026-11-23.md`
**Branch:** `ci/t3-sparse-checkout-fix` @ **`96dcc4046c1`**, cut from `origin/main` (`acca431fb89`)
**Worktree:** `/tmp/t3-clean` (isolated — the main checkout is dirty with other desks' work)
**State:** committed locally, **NOT pushed**. G2 needs an operator decision.

---

## Why a worktree and not a branch switch

The main checkout sits on `push/phase2-round-2026-11-22` with **14 modified tracked files** (`reports/PROTOCOL_V1_ACKS.md`, `reports/protocol_v1_acks.jsonl`, `reports/weekly_scorecard/*`) and **624 untracked files** — none of them mine. Switching branches in that tree would either fail or carry foreign work onto a new branch.

`git worktree add /tmp/t3-clean -b ci/t3-sparse-checkout-fix origin/main` leaves the dirty tree completely untouched. That is the only safe way to build a clean branch next to a shared working tree.

## What was replayed, and what was dropped

The original fix `5e044af5252` touched **3** files. This branch carries **2**:

| file | kept? | why |
|---|---|---|
| `.github/workflows/alpha-engine-fast.yml` | **kept** | the actual fix |
| `updates/2026-11-23-t3-sparse-checkout-root-cause.md` | **kept** | the documentation |
| `docs/TODO_LEDGER_2026-11-22.md` | **dropped** | **conflicted** on cherry-pick |

The ledger is a shared file that other desks have edited since. `git cherry-pick` reported `CONFLICT (content)` on it. Hand-resolving would mean choosing between my entries and theirs, and a branch whose entire purpose is "carries only what the fix needs" should not also carry a merged ledger. Dropped, and recorded here so nobody thinks it was forgotten.

Verified: `git diff --stat origin/main...HEAD` → **2 files changed, 120 insertions(+), 1 deletion(-)**.

## What the fix does (unchanged from the original)

The `alpha-engine-fast` workflow's `sparse-checkout` listed only `.github`, `alpha_engine`, `shared`. **`tools/` (1,705 tracked files) and `audit_trail/` (125 tracked files) were never on the runner's disk.** Two different-looking errors, one cause:

```
[PROVENANCE] skipped: No module named 'provenance_ledger'
[SHADOW]     skipped: No module named 'audit_trail'
```

Both modules exist and are tracked; `PYTHONPATH` was already correct. Three changes:

1. `sparse-checkout` **3 → 6** paths, adding `tools`, `audit_trail`, `reports/provenance`.
2. The commit step stages `reports/provenance/picks_provenance.jsonl` with `-f`.
3. A new **blocking** step, *"Provenance must not be silently skipped"*, greps the scanner log for `[PROVENANCE] skipped` and fails the job if present.

A zero-pick cycle is deliberately **not** a failure — it is a legitimate outcome, and failing on it would train people to ignore the gate.

## How it was verified

```
git worktree add /tmp/t3-clean -b ci/t3-sparse-checkout-fix origin/main
  -> HEAD acca431fb89, 46,992 files checked out

git cherry-pick -n 5e044af5252
  -> CONFLICT (content) on docs/TODO_LEDGER_2026-11-22.md   [expected, handled]

git checkout HEAD -- docs/TODO_LEDGER_2026-11-22.md ; git reset -q <that path>
git diff --cached --name-only | wc -l   ->  2

git diff --cached .github/workflows/alpha-engine-fast.yml | grep '^+'
  -> + tools / + audit_trail / + reports/provenance
  -> + "Provenance must not be silently skipped"
  -> + if grep -q '\[PROVENANCE\] skipped' "$LOG"

git diff --stat origin/main...HEAD
  -> 2 files changed, 120 insertions(+), 1 deletion(-)

git status --porcelain | wc -l   ->  0
```

## Status of T3 — still OPEN

The fix being on a clean branch does **not** close T3. T3 closes only when a run emits `n_records > 0` **and** `provenance-verify.yml` reports the chain intact. Neither has been observed.

## The four commands that would push it

```
cd /tmp/t3-clean
git push -u origin ci/t3-sparse-checkout-fix
# then open a PR into main
```

**Not run.** Pushing and opening a PR is an outward action, and the house rule is to ask first. This branch exists precisely so the operator can push it without touching the 81 foreign commits on the phase2 branch.

Zero capital sanctioned. Paper only. Not investment advice.
