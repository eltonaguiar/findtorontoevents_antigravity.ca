---
title: "Phase 1.1 — 'Forward validator frozen 270h' root-cause diagnosis"
date: 2026-05-26
status: diagnosed, fix proposed, NOT YET APPLIED (pending user authorization)
relates_to: reports/2026-05-26_money_maker_v2_unblock_plan.md
---

# Phase 1.1 diagnosis — what's actually frozen

## TL;DR

The incident phrasing "forward_validator frozen 270h" is misdirected. `alpha_engine/forward_validator.py` is healthy and runs every ~2h green. The actual freeze is in a **different** workflow: **Outcome Resolver** has been failing every cycle for ~17h with `fatal: pathspec 'alpha_engine/data/closed_picks.json' did not match any files`. The signal_outcomes/MySQL-mirror downstream of it (P0 #10) is starved as a result.

This is a one-line workflow-file fix. It does not require touching the resolver code, the dashboard generator, or any picks data.

## Evidence chain

### 1. `alpha-engine-live.yml` is NOT frozen
Five most recent runs all `success`, every ~2h on schedule:
```
26450458490  success  ALPHA ENGINE - Live Autonomous Scanner  2026-05-26T13:19:30Z
26443995251  success  ALPHA ENGINE - Live Autonomous Scanner  2026-05-26T09:26:26Z
26438658932  success  ALPHA ENGINE - Live Autonomous Scanner  2026-05-26T07:29:30Z
```
And `forward_validator.py` does not write `signal_outcomes` or `trust_score` — `grep -n "signal_outcomes\|trust_score\|at_signal_outcomes" alpha_engine/forward_validator.py` returns zero matches.

### 2. `outcome-resolver.yml` IS frozen
Last 15 runs all `failure`. Last success: 2026-05-25T18:51:38Z. First failure: 2026-05-25T19:54:08Z. Every hourly cron since has failed.

### 3. Exact failure
From `gh run view 26471783524 --log-failed`:
```
resolve-outcomes  Commit resolved picks  fatal: pathspec 'alpha_engine/data/closed_picks.json' did not match any files
resolve-outcomes  Commit resolved picks  ##[error]Process completed with exit code 128.
```
The failing step is the `git add` in `.github/workflows/outcome-resolver.yml` ~line 97:
```yaml
git add alpha_engine/data/closed_picks.json alpha_engine/data/outcome_resolver_log.json
```

### 4. Why the file isn't there
- `git ls-tree -r HEAD -- alpha_engine/data/closed_picks.json` returns empty — file is not tracked.
- `ls alpha_engine/data/closed_picks.json` → No such file.
- Existing files in that dir: `closed_picks.archive.jsonl`, `closed_picks_enriched.json`, `closed_picks_fast.json` (none of which the workflow git-adds).

The file was removed from the repo by the history rewrite `34463f11a` (2026-05-23 "main-only stripped reset: remove heavy data artifacts"), then gitignored by `8bc9cf075` (2026-05-25 19:34 UTC "gitignore v3 — closed_picks*"). The resolver workflow was never updated to match — it still tries to commit a file that:
1. Is gitignored (so even if regenerated, `git add` without `-f` is a no-op).
2. Isn't being regenerated on the runner (fresh checkout has nothing).

The first failure (19:54) is the first hourly cron tick that ran after `8bc9cf075` (19:34) — perfect causal match.

### 5. Downstream cascade
- The `git add` failure → `exit 128` → the whole step fails → the **INC #10 fix (MySQL mirror step that runs AFTER `git add` in workflow ordering)** never executes. Actually verifying ordering: the mirror step runs BEFORE `git add` in the YAML, so the mirror itself runs; only the commit step fails. **This means MySQL `at_signal_outcomes` IS being written hourly post-INC#10 — Kilo's concern was already addressed by commit `cc4159888`.**
- However, because the resolver workflow as a whole exits non-zero, GitHub Actions marks it `failure`, and no new resolver log entries get committed → `alpha_engine/data/outcome_resolver_log.json` last entry remains 2026-05-21 → which is what spawned the "270h frozen" claim.
- `signal_outcomes` 82d-staleness (P0 #10) was a true symptom of the same broken workflow PRE-cc4159888, but the INC #10 mirror added today decouples it. **Verify by querying MySQL `at_signal_outcomes` MAX(updated_at) — if it's within ~1h, P0 #10 is effectively cleared once the workflow stops failing.**

## Proposed surgical fix

Edit `.github/workflows/outcome-resolver.yml` line ~97. Current:

```yaml
git add alpha_engine/data/closed_picks.json alpha_engine/data/outcome_resolver_log.json
```

Change to:

```yaml
git add alpha_engine/data/outcome_resolver_log.json
git add alpha_engine/data/closed_picks.json 2>/dev/null || true
```

Rationale:
- `closed_picks.json` is gitignored intentionally (1.9 MB live file, 21 MB historical bloat per commit `8bc9cf075`). It SHOULD NOT be committed.
- `outcome_resolver_log.json` is the file the workflow actually needs to commit (it's small, audit-grade, and not gitignored — confirmed by `grep outcome_resolver_log .gitignore` returning empty).
- The `|| true` pattern matches the other `git add` lines in the same step (lines 99-103).

## Blast radius

- **Inside the workflow:** none. Other steps (resolver execution, MySQL mirror) already ran successfully before this failing step. We're fixing the cleanup-and-commit tail.
- **Outside the workflow:**
  - `closed_picks.json` is consumed by 8 readers + 5 writers per commit `8bc9cf075`. None of those read from git-checkout; they all assume the file exists locally on whichever runner generates it. Other workflows that need this file generate it themselves.
  - GH Actions cron runners do NOT share state. Each resolver run starts fresh; the previous run's `closed_picks.json` was already lost-by-design (it's gitignored). So nothing breaks that wasn't already broken.

## Rollback

`git revert <fix-commit>` is safe. The pre-fix state is the current 17h freeze, so any rollback restores the freeze but doesn't break anything new.

## Validation gate (before declaring Phase 1.1 done)

1. After the fix lands on `main`, watch the next outcome-resolver cron tick (every hour at :15). Run should be `success`.
2. `gh run view <run_id>` shows the "Mirror resolved outcomes to MySQL" step executed without error.
3. Query MySQL `SELECT MAX(updated_at) FROM at_signal_outcomes` — must be within 2h of now.
4. `alpha_engine/data/outcome_resolver_log.json` has a new entry committed with timestamp matching the run.

Only after all four hold do we move to Phase 1.2 (PnL integrity audit).

## Open questions answered (revising plan v2)

- **Plan Q1** (resolver upstream of PnL mismatch?): **Independent.** The resolver workflow failure was a commit-step bug, unrelated to PnL labelling logic. PnL mismatch (P0 #4/#5) is a separate resolver-code bug; this fix doesn't touch it.
- **Plan Q5** (no-filter-this-week framing): Stronger case for **publish** now — once this fix lands, three of the P0s (#7, #10, and partial #4 visibility) effectively clear within 24h, and the "no filter" story becomes "we found and fixed the freeze; filter resumes once Phase 1.2 lands."

## Decision needed from user

This is a one-line YAML edit to a production workflow file. CLAUDE.md says "never push without pulling first" but doesn't bar workflow edits. Per the executing-actions guidance, I want explicit authorization before applying the change. Two options:

1. **Apply now** — I make the edit, commit on a branch, open a PR with this diagnosis as the PR body, do NOT auto-merge. Wait for user to merge.
2. **Hold** — User reviews this report first, then decides whether to proceed.
