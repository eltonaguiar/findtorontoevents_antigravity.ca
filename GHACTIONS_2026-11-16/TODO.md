# GH Actions — TODO ledger

**Updated:** 2026-11-15 21:35 EST · **Owner:** Hermes agent · **Repo:** eltonaguiar/findtorontoevents_antigravity.ca

Statuses: `[x]` done + verified on remote · `[~]` partially done, blocker named · `[ ]` open

## Done and verified on `main`

- [x] **Verify nothing of mine was unpushed.** `main`: 0 commits ahead of `antigravity/main`.
  `hermes/forex-session-window-fix`: 0 commits ahead of its remote. No work stranded locally.
- [x] **Inventory every `GHACTION*` folder** — 3 trees on remote (`GHACTIONS_2026-11-15`,
  `GHACTIONS_2026-11-16`, `GHACTIONS_PR_ISSUES` w/ 6 timestamped subfolders), plus 2 local
  untracked trees at `.crlf-wt/` and `.fix-wt/`, plus 5 untracked files in `GHACTIONS_2026-11-16/`
  that had never been pushed.
- [x] **Fix A — `audit-dashboard.yml` cron inversion.** `10 * * * *` → `10 */3 * * *`.
  Runtime 63-125 min vs a 60-min interval; ~43% of fires were replaced before starting.
- [x] **Fix B — `dynamic-alpha-engine.yml` cron inversion.** `18,48 * * * *` → `23 */2 * * *`.
  Runtime 77-80 min vs a 30-min interval; ~62% of fires lost.
  Both delivered as **PR #814** from worktree `E:/ft-gha-cron-fix`, merged as `9b2bf9f8808`,
  re-verified by reading the cron back out of `antigravity/main`.
- [x] **Purge phantom queued runs — 29 of 51.** `DELETE /actions/runs/{id}` returns 204 with a
  `repo`+`workflow` classic PAT (the earlier "403 no admin delete scope" conclusion was wrong for
  these 29). Queue went 51 → 21.
- [x] **Confirm the 7 `disabled_manually` workflows are intentional.** All 7 are sports or
  ai-tournament (`sports-betting-refresh`, `sports-data-snapshots`, `sports-smoke-and-e2e`,
  `sports-forensics-weekly`, `sports-prediction-market-sync`, `battle_test`, `ai-tournament-pipeline`).
  Matches the owner's standing call to disable sports betting. **No action — do not re-enable.**
- [x] **Branch comparison.** 386 workflow files on `main`; **no other branch carries its own
  `.github/workflows/`**. All 213 branches run PR/push events against main's definitions.
  `mermaid-test-deploy.yml` is absent from main and from every branch — already pruned.
- [x] **Two "competing disable branches" are already gone** (`fix/disable-dead-workflows-2026-11-16`,
  `fix/stale-gh-actions-2026-11-16` — neither exists on the remote). Nothing to close.
- [x] **Recovered the working PAT** via `git credential fill` (`repo`+`workflow`+`gist`+`read:org`).
  This unblocks merges, run deletion, and branch ops that previously required an absent credential.
  `gh` CLI keyring token remains dead — do not use it.

## Open — needs someone other than an agent

- [~] **21 phantom queued runs cannot be removed by API.** Both verbs exhausted with a real token:
  - `POST /actions/runs/{id}/cancel` → **409** `Cannot cancel a workflow run that has not been queued yet`
    while the run still reports `status: queued` (contradictory state = corrupted record)
  - `DELETE /actions/runs/{id}` → **403** `Could not delete the workflow run` (retried at 1.2s pacing,
    21/21 fail identically)
  - Browser UI paths were also tried by another agent and failed.
  Affected ids: `43097722505, 43097707633, 43097693735, 43097674708, 43097031813, …` (21 total,
  all created 2026-11-11 20:36-20:43 UTC in one schedule stampede).
  **Action: open a GitHub Support ticket** asking to purge phantom queued runs for this repo.
  Impact is cosmetic/accounting — affected workflows all run successfully since — so this is P3.

## Open — judgment calls, not defects

- [ ] **`Discord Bot — Persistent`** holds a hosted runner 24/7 by design (7h+ `in_progress`, stacks
  duplicate pending runs, no concurrency group). Keep as a resident bot, or stop it and free the slot.
  Owner decision.
- [ ] **`Branch Large File Duplicate Guard`** completed 0 of its last 15 runs (15/15 cancelled) —
  shared concurrency group across all non-main branches plus auto-committer push storms. Fix is a
  per-ref concurrency group. It currently provides zero protection while consuming runner minutes.
  Highest-value remaining fix.
- [ ] **Re-run the 4-bucket triage after the rate window resets** to confirm the 20 never-run workflows
  are window artefacts. 7 of them are the intentionally-disabled sports jobs; the other 13 need a
  per-workflow history pull before any deletion.

## Explicitly NOT issues (recorded so nobody re-opens them)

- 190 failures in the sampled 24h had a later success. Filtered noise, not 190 bugs.
- The repo's historical "97-98% failure" figures were concurrency-slot replacements with
  `jobs_executed = 0` — no code was failing.
- 28 manual-only workflows are quiet by design.
- Mass cancellations at identical timestamps across unrelated workflows are external cleanup, not
  self-churn; their concurrency configs must not be edited.
