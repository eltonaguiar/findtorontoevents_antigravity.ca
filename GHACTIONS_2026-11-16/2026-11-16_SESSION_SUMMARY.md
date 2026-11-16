# GH Actions session summary — 2026-11-16

## What shipped (all merged to main, all reversible + documented)
| PR | Change | Why |
|---|---|---|
| #811 | finpredict emitter download hardening; ALPHA **job** timeout 60→90 | emitter crashed on transient GLD download; ALPHA runs >60m were being killed (reported as "cancelled") |
| #813 | ALPHA **"Commit results" step** timeout 5→15m | the step capped at 5m but its retry loop runs ~12m → step timed out mid-retry, turning a non-fatal push failure into a RED job |
| #815 | disable duplicate ROOCODE torontoevent backtest/deploy | byte-identical true-duplicate (same scripts + FTP target), 15-min cron, no concurrency → 2× load + FTP race |
| #816 | APPROACH playbook (best practices, 4-bucket model, timeout-wave backlog, detection rules) | the requested design doc |
| #817 | ALPHA cancellation/flapping root-cause analysis | 9/15 flapper explained |

Earlier: #812 `on: {}` was invalid syntax (spurious "No event triggers" failures 01:51–01:54Z); a peer
converted them to `.disabled` (`3d1aa94ba5e`). Lesson recorded: **never `on: {}` — rename to `.disabled`.**

## Empirically confirmed
- Run `43788456858` (01:49Z, **pre-fix** config) failed with exactly
  `The action 'Commit results' has timed out after 5 minutes` at 02:58:25Z → validates PR #813.
- Runs created **before** the 02:39Z merge (01:49, 02:25) use the old 5m step cap and will repeat it;
  the first run created **after 02:39Z** uses 15m (verify via scheduled check).

## Deeper constraint found (do NOT "just deepen the fetch")
ALPHA's push-retry loop fails `git pull --rebase` repeatedly during push contention because the
checkout is `fetch-depth: 1` (no merge base to the new main tip). The obvious fix (deepen fetch)
is **unsafe here**: a workflow comment records that `git fetch --unshallow` blew up disk because
`.git` is ~37 GB. The existing shallow + `-X theirs` + non-fatal-warning design is intentional.
Consequence for **/audit**: on push-failure cycles, `alpha_engine/data/` (which feeds
`quality_gates.py`, `universal_pick_resolver.py`, `regime_filter.py`) self-heals next cycle — so
alpha freshness is best-effort, not guaranteed. This is a known tradeoff, not a regression.

## Current health
- 0 repo-wide failures after 01:55Z (subagent stale/flapping recheck) except the two pre-fix ALPHA
  runs (01:49, and likely 02:25).
- Only flapper: `dynamic-alpha-engine` (now addressed by #811 + #813).
- `regime-terminal` 2/15, `multi-asset-scanner` 1/15, `audit-dashboard` 1/15 — all healthy.
- `gainer-predictor`, `copy-trader-intelligence`, `signal-engine`, `baby-strat`, `meme-scanner` 0/15.

## Open follow-ups
1. Verify first post-02:39Z ALPHA run (scheduled check) — success, or worst case `cancelled` at 90m,
   never a 5m step timeout.
2. If ALPHA still flaps: change cron `18,48 * * * *` → `18 */2 * * *` (runtime < interval, no overlap).
3. Timeout-wave rollout for the 79 no-timeout workflows (see APPROACH.md §6) — canary, never below p95.
4. Branch/subagent-B audit + job-state/subagent-A findings → fold in when they return.
