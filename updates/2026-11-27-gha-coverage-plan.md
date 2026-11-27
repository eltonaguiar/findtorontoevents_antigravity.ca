# 2026-11-27 — Workflow coverage: what exists, what is broken, who fixes what

Owner of this plan: buffy-laptop @ elton2026. Coordinates claimed on COMS in
`notes/work-claim-buffy-gha-20261127`, with one `registry/jobs/...` row per workflow.

Another agent is active on this repo from windows-desktop (seat
`hermes-deepseek-flash-psc`). Their claims are listed and excluded below.

## Method — five steps, each with an artefact

1. **Inventory from git, not the UI.** `git/trees/main?recursive=1`, filter
   `.github/workflows/*.yml|*.yaml`. Result: **398 workflow files on main**. The web UI paginates
   and hides disabled workflows, so it cannot be used for a count.
2. **Run history from the runs API, paged to a date cutoff.** `actions/runs?per_page=100`, page
   until `created_at` crosses 7 days back. **9,000 runs** in the window.
   A first attempt capped at 40 pages and silently mislabelled 31 workflows as "never ran" that had
   in fact run within hours. The cap was removed and each of the 43 candidates was then re-checked
   through `actions/workflows/<file>/runs`, which is how the 31 were caught. Any coverage number
   produced under a page cap is wrong, and this document's numbers are post-fix.
3. **Bucket every workflow by rule, not by eyeball.**

   | bucket | rule | count |
   |---|---|---|
   | green | last run `success` | 375 |
   | red, but green earlier in window | has ≥1 success, last run not green | 17 |
   | chronic red | ≥2 runs, **zero** successes | 5 |
   | single failure | exactly 1 run, failed | 1 |

   375 + 17 + 5 + 1 = **398**, which is the file count. That equality is the coverage check: if the
   buckets do not sum to the inventory, the scan missed workflows.
4. **Set arithmetic, because "has runs" and "exists" are different sets.** 386 of the 398 files
   produced a run in the window; **12 are silent**. Separately, 12 paths appear in run history but
   **not** on main — the three workflows deleted in `33ed1604`, seven `ops-*` one-shots from the
   deleted `verify/self-hosted-routing` branch, and GitHub's built-in `pages-build-deployment`.
   Those are history, not backlog.
5. **Diagnose at step level.** `actions/jobs/{id}` for the failing step name, then
   `actions/jobs/{id}/logs` for the first real error. Annotations and the run summary are not
   evidence — the `db-freshness-guardian` case below is exactly why.

## Branches

- **main** — 398 workflow files, the whole surface above. All fixes land here.
- **gh-pages** — **zero** workflow files. `contents/.github/workflows?ref=gh-pages` returns 404; the
  branch root holds only the static site (`index.html`, `live_picks.json`, `bestiejob/`,
  `battleground/`, `backtest_dashboard.py`, …). Nothing there can fail and nothing needs migrating.
  Workflows only *write* to it, so the risk on gh-pages is collision, and that is already handled:
  both Pages deployers share concurrency group `github-pages` since `c1f13c62`.

## Who fixes what

### Mine (claimed, COMS job rows published)

| # | workflow | evidence | plan |
|---|---|---|---|
| 1 | `2hour_challenge.yml` | 8 runs, **8 cancelled**, 0 successes; sibling `real_2hour_challenge.yml` green | find why every run is killed at ~30 min; the 150 m timeout already exists, so the cancel source is elsewhere |
| 2 | `db-sync-to-mirror.yml` | 9 runs, 8 failures | read the failing step log, then fix or retire |
| 3 | `clear-channel-command.yml` | 5 runs, 4 failures | same |
| 4 | `gha-quality-framework.yml` | 3 runs, 2 ok, last failed | route its push through `.github/scripts/safe_push.sh`, one clean dispatch |
| 5 | `sign-coherence-gate.yml` | 4 runs, 2 ok, last red; daily cron nobody reads | diagnose step, then fix or mute with a reason |
| 6 | `verification-tests.yml` | 11 runs, only 3 ok | flaky vs broken: separate the two by failing step |
| 7 | `forward-observations-ingest.yml` | 5 runs, 3 ok, last red | diagnose |
| 8 | `audit-dashboard.yml` | green now; hyro step was dying on a numpy/pandas ABI mismatch | port only the wheel pin + import probe from PR #1181 — **not** that PR's `1000_TODOS.*` |
| 9 | `forward-ledger-sync.yml` | **never run** since merge | `workflow_dispatch` with `dry_run=true` and report the output |
| 10 | `weekly-filter.yml` | 4 runs, 2 ok, last cancelled | confirm whether the cancel is correct (superseded) or a bug |

### Not mine — windows-desktop, do not touch

`alpha-engine-daily-picks.yml`, `branch-large-file-dup-guard.yml`, `dna_strategy_pipeline.yml`.
All three carry "claimed by hermes-deepseek-flash-psc: fixed and green". Independently confirmed:
`branch-large-file-dup-guard` run `45907366474` succeeded in 975 s.

### Deletion candidates, not fixes

Silent for 166–183 days, no schedule and no caller: `ai-tournament-pipeline.yml` (175 d),
`battle_test.yml` (167 d), `strategy-performance-no-regression.yml` (183 d). The four `ops-*`
workflows that still appear in history are gone from main with the routing branch and need nothing.

## What "fixed" means here

A workflow is only fixed when its **own** run concludes `success` after the change — dispatched
where possible, otherwise the next scheduled run. Two exceptions that must be stated explicitly
rather than counted as wins:

- **Gates that detect bad data.** `db-freshness-guardian` now fails on purpose: run `45914784673`
  logs `overall=RED` and the strict verdict exits non-zero because the backtests DB is genuinely
  stale. Before PR #1188 it reported `success` while doing that. A red here means the gate works.
- **Persistent jobs.** `discord-bot` runs a 355-minute budget (`timeout-minutes: 355`,
  `cancel-in-progress: false`); a long `in_progress` is the design, not a stall.

## Known limits of this plan

- The 7-day window cannot see a workflow that is broken on a monthly schedule; silent §4 covers
  those, and three of the twelve have been silent for ~6 months.
- Bucket counts were taken at 2026-11-27T00:10Z and main takes commits every 1–2 minutes.
- Step-level diagnosis is capped by log retention; where a log is unavailable the plan says
  "diagnose", never a guessed cause.
