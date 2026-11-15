# 01 — Workflow Health

Evidence date: 2026-11-15 ~07:30–07:40 UTC. Source: `gh run list`, `gh run view
--log`, `gh api`, and direct inspection of `.github/workflows/`.

## Run-level snapshot (last 100 runs)

| Status | Count |
|--------|-------|
| completed / success | 72 |
| completed / cancelled | 11 |
| completed / failure | 1 |
| in_progress / pending | 16 |

The single failure in the last 100 was **Sports endpoint smoke + Playwright**
(run `43689346545`). Cancellations are the sprawl symptom (concurrency groups
preempting sibling runs).

## Workflow sprawl (the systemic problem)

| Metric | Value |
|--------|-------|
| Workflow files total | 382 (363 `.yml` active + 19 `.disabled`/`.retired`/`.draft`/`.md`) |
| Active workflows | **363** |
| On a `schedule:` cron | **313** |
| Contain `push:` trigger | 40 |
| Can run `workflow_dispatch` | 357 |
| Workflows that `git push` to `main` | **236** |
| Cron firing **every minute** (`*`) | **83** |
| Cron every 2 min (`*/2`) | 28 |
| Cron every 4 min (`*/4`) | 30 |
| Cron at minute 6 | 28 |
| Duplicate workflow name | `edge stability refresh` → `edge-stability-daily.yml` + `edge-stability-refresh.yml` |

236 independent writers racing on **one** `main` branch is the root cause of:
non-fast-forward push failures, rebase loops, "cancelled" runs, and Actions
minute burn. Every new "fix" that retries a push adds to the contention.

## Confirmed-broken workflows

### 1. `backup-verify.yml` — impossible to pass, floods issues
- Checks `audit_dashboard/data/dashboard_data.json`.
- That path is **gitignored** (`.gitignore:218`), so a fresh `actions/checkout`
  never contains it → `dashboard_data.json NOT FOUND` → `sys.exit(1)` every run.
- Other critical files it checks (`recent_exits.json`, `ml_health_status.json`,
  `pcg5_log.json`) **are** tracked — only `dashboard_data.json` is absent.
- On failure it **creates a new issue unconditionally** (no lookup for an
  existing open issue). → duplicate flood.
- `actions-failure-guardian` re-runs the failure every 30 min; re-runs keep the
  same run id, which is why issues #780/#781/#782/#783/#787 all cite run
  `43683666944` and were opened at 06:03, 06:10, 06:37, 07:07, 07:34.

### 2. `sports-smoke-and-e2e.yml` — Playwright vs ubuntu 26.04
- `ubuntu-latest` now resolves to 26.04; log: `ERROR: Playwright does not
  support chromium on ubuntu26.04-x64`. Job dies at install, never runs a test.
- Root: `runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}`. The
  repo variable **`ACTIONS_RUNNER_LABEL` does not exist**, so it always falls
  back to `ubuntu-latest` (= 26.04).
- Also exposed and unfixed: **`social-prediction-tracker.yml`** and
  **`sports-betting-refresh.yml`** (both Playwright, both `ubuntu-latest`).

### 3. `qa-market-validation.yml` — no quote-chain credentials
- `alpha_engine/equity_price_failover.py` has a 7-adapter chain; adapters 2–6
  return `None` when their env var is unset. The workflow supplies **none** of
  `FINNHUB_API_KEY`, `TIINGO_API_KEY`, `TWELVE_DATA_API_KEY`,
  `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY`, so only Stooq (blocked from runner
  IPs) + yfinance (flaky) are live → `ALL 7 sources failed` for every ticker →
  gate fails every hour on infrastructure, not data.

### 4. Snapshot push loops — no rebase
- `rsi5070-forward-snapshot.yml` (10 retries) and `operator-review-today.yml`
  (5 retries) re-issue the identical `git push` after a non-fast-forward. It can
  never succeed. PR 786 adds fetch+rebase before retry.

## Healthy but noisy

- 195 docs commits and 24 WIRED_IN prompt bundles in 48h produced **zero**
  change to strategy behaviour. They also inflate `main` and slow every
  checkout in CI.
- Real code shipped under `[skip ci]` (e.g. the cost-model commit `e527b290026`)
  bypassed CI entirely.

## Recommended remediation order

1. Merge PR 786 (fixes #3, #4, and one of #2).
2. Apply `04_SUGGESTED_FIXES.md`:
   - rewrite `backup-verify.yml` to check live/published artifacts and dedup issues;
   - add an exclude-list + per-run cooldown to `actions_failure_guardian.py`;
   - pin `social-prediction-tracker.yml` and `sports-betting-refresh.yml` to
     `ubuntu-24.04`.
3. Prune cron: disable duplicate/retired scanners, stagger the 83 `* * * * *`
   jobs, and convert same-minute clusters to offset minutes.
