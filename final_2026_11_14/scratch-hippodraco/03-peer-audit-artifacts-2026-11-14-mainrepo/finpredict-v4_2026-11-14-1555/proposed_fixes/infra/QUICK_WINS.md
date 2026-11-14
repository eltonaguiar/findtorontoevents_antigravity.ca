# Infrastructure Quick Wins — Prediction System
**Audit date:** 2026-11-14  
**Auditor:** DevOps / Quantitative Engineering  
**Scope:** GitHub Actions, CI/CD pipelines, MySQL sync, JSON artifact freshness, dashboard data flow

---

## 1. TOP 5 QUICK WINS (< 1 day each)

> Ranked by immediate system-wide impact. Each can be deployed independently.

---

### QW-1: Stop Alpha Engine cascading cancellations
**What to do**
- Root cause: `alpha-engine-live.yml` runs 45–60 min + 17 min MySQL sync on a 2-hour cron with `cancel-in-progress: true`. Any queue pressure or runner latency causes the in-flight run to be killed, producing the observed 9 cancelled + 1 failure pattern.
- Change `cancel-in-progress: true` → `false` (already proven for `alpha-engine-fast.yml` and `audit-dashboard.yml`).
- If queue stacking becomes a problem, widen the cron to `3 */3 * * *` (every 3 hours) or reduce the job to a delta-only validation + generation split (see Long-Term #1).
- Add a 5-minute `sleep` buffer at job start if another instance is still running (portable check via GitHub API or a lock file).

**File/location to edit**
- `.github/workflows/alpha-engine-live.yml` — `concurrency.cancel-in-progress`
- `.github/workflows/alpha-engine-daily-picks.yml` — apply same fix if it uses `cancel-in-progress: true`

**Expected impact**
- Alpha Engine completes end-to-end again, restoring the primary scanner and unblocking active-pick generation.
- Eliminates the ~24h outage loop.

**Effort estimate**
- 30 min (config change + monitoring one full cycle)

---

### QW-2: Surface silent failures from `|| non-fatal` masking
**What to do**
- `alpha-engine-live.yml` contains **58** instances of `|| echo "… failed (non-fatal)"` / `|| true`. These mask real outages (e.g., MySQL sync, Polymarket, Kalshi, price enricher) so the run stays green while subsystems die.
- Immediate fix: add a post-processing step at the end of the job that scans the step logs for the pattern `failed (non-fatal)` and emits `::error` annotations for each hit. This makes failures visible in the GHA UI without changing runtime semantics.
- Secondary fix: convert the 5 most critical steps (Universal Price Enricher, Full MySQL Sync, Trust Tier Stamper, Outcome Check, Elite Scorer) from `|| non-fatal` to `continue-on-error: false` so they fail loud.

**File/location to edit**
- `.github/workflows/alpha-engine-live.yml` — add a final step: `Surface non-fatal failures`
- `.github/workflows/audit-dashboard.yml` — apply same log-scan step

**Expected impact**
- Failures stop hiding. The next broken subsystem (API key, DB creds, rate limit) will be visible within one run instead of weeks.

**Effort estimate**
- 2–4 hours

---

### QW-3: Restart the hourly update pipeline
**What to do**
- `audit_dashboard/data/hourly_update_last_run.json` is **44.6 hours old** (`2026-11-12T19:22Z`). The `audit-hourly-update.yml` workflow exists but is producing stale artifacts.
- Check the last 3 runs of `Audit Hourly Update` in the GHA UI. Likely causes: (a) `generate_hourly_update.py` crashes silently, (b) push conflict on contended `main` aborts the commit, (c) a missing secret causes an early exit.
- Add the same freshness assert already used in `picks-now-refresh.yml` (lines 46–67): if `hourly_update_last_run.json` is >2h old after the script runs, fail the step with `::error`.
- If the push is failing, use the `safe_push.sh` retry pattern or switch to `if: always()` on the commit step so a prior script failure does not suppress the push.

**File/location to edit**
- `.github/workflows/audit-hourly-update.yml` — add freshness assert + `if: always()` on commit
- `audit_dashboard/generate_hourly_update.py` — add defensive error logging if it exits 0 without writing the marker

**Expected impact**
- Hourly update resumes; `updates/index.html` and sidecar status become current again.

**Effort estimate**
- 1–2 hours

---

### QW-4: Wire orphan pipelines into dashboard data
**What to do**
- **Copy Trader** (`copy-trader-intelligence.yml`) runs every 45 min and writes `copy_trader_intel/data/active_picks.json`, but `audit-dashboard.yml` never merges it into the dashboard payload. The merge logic exists in the copy-trader workflow (Step 3) but only writes to `alpha_engine/data/active_picks.json` — and that file is overwritten by Alpha Engine commits without preserving copy-trader rows.
- **Claude Gainer** (`alpha-gainer-capture.yml`) writes `alpha_engine/data/gainer_capture_picks.json` but no downstream consumer reads it.
- Fix: in `audit-dashboard.yml`, add two merge steps before `audit_trail/dashboard_generator.py` runs:
  1. Merge `copy_trader_intel/data/active_picks.json` into `alpha_engine/data/active_picks.json` (deduplicate by `symbol+direction+source_system`).
  2. Merge `alpha_engine/data/gainer_capture_picks.json` into the same target.
- Tag merged picks with `source_system` so the dashboard can filter them.

**File/location to edit**
- `.github/workflows/audit-dashboard.yml` — add merge steps before dashboard generation
- `audit_trail/dashboard_generator.py` — ensure `source_system` is preserved in payload

**Expected impact**
- Copy Trader and Gainer picks surface on the live dashboard for the first time, restoring two live signal streams.

**Effort estimate**
- 4–6 hours

---

### QW-5: Run the MySQL ghost-row dedup fix
**What to do**
- `evidence_db_health.json` shows **22,947 ghost rows**, mostly MEMECOIN duplicates (e.g., DOGEUSDT: 3,569 identical rows). The `mysql_dedup_fix.yml` workflow exists but is manual-only and defaults to `dry_run=true`.
- Step 1: run the workflow with `dry_run=true`, capture the report, and review the `DELETE` preview.
- Step 2: if the preview looks correct, run with `dry_run=false`.
- Step 3: add a weekly cron trigger to `.github/workflows/mysql_dedup_fix.yml` so dedup runs automatically (keep `dry_run=true` for the scheduled run; require manual dispatch for `apply`).
- Step 4: after dedup, add a `UNIQUE(symbol, direction, created_at, source_system)` index (or composite hash) to `trading_picks` to prevent re-insertion. Do this in a maintenance window.

**File/location to edit**
- `.github/workflows/mysql_dedup_fix.yml` — add weekly cron + email/alert on ghost count > 1000
- `tools/mysql_dedup_fix.py` — already exists; verify it handles MEMECOIN duplicates

**Expected impact**
- DB size drops by ~23k rows. Query performance improves. Dashboard no longer double-counts ghost picks.

**Effort estimate**
- 2–3 hours (dry-run review + apply + index addition)

---

## 2. MEDIUM FIXES (1–3 days)

---

### MF-1: Rescue TIME_EXIT limbo (4,220 picks)
**What to do**
- Only **301 / 4,820** TIME_EXIT picks have been resolved (6.2%). The `universal_pick_resolver.py` fallback exists (lines 1301–1338) but the `audit-dashboard.yml` resolver step is capped at **40 minutes** and may not reach the backlog.
- Build a one-off batch script (`tools/resolve_time_exit_backlog.py`) that:
  1. Queries all `status = 'TIME_EXIT'` picks older than N days.
  2. Fetches closing prices from Binance/yfinance/FMP.
  3. Computes PnL and writes `exit_reason = 'TIME_EXIT_RESOLVED'`.
- Increase the resolver timeout in `audit-dashboard.yml` from 40 min to 60 min, or split resolver into two jobs: crypto (fast) and non-crypto (slow).
- Add a daily staleness check: if `COUNT(*) WHERE status = 'TIME_EXIT' AND resolved_at IS NULL` grows > 500, alert.

**File/location to edit**
- `tools/resolve_time_exit_backlog.py` — new one-off batch script
- `.github/workflows/audit-dashboard.yml` — resolver timeout / split job
- `audit_trail/universal_pick_resolver.py` — ensure TIME_EXIT fallback runs for all asset classes

**Expected impact**
- Honest closed-ledger stats. Dashboard PF and WR become trustworthy.

**Effort estimate**
- 1–2 days

---

### MF-2: Repair intrabar truth resolution (`at_signal_outcomes`)
**What to do**
- `at_signal_outcomes` last resolved **2026-03-04** (254 days stale). The `db_freshness.json` signal shows `115,782 minutes stale` / `RED`.
- `universal_pick_resolver.py` has intrabar fetchers (Binance + yfinance) and `_check_tp_sl_intrabar()`, but the audit-dashboard resolver step was missing DB credentials until 2026-06-19. Verify the credentials are still valid.
- Run a **bootstrap batch** (`workflow_dispatch` with `bootstrap_intrabar: true` in `audit-dashboard.yml`) to reresolve the backlog. This bypasses the 90-day window and is idempotent.
- After bootstrap, confirm `at_signal_outcomes` receives new rows within 24 hours.
- If the bootstrap is too slow, shard by asset class and run in parallel jobs.

**File/location to edit**
- `.github/workflows/audit-dashboard.yml` — verify DB env vars in resolver step; run `bootstrap_intrabar`
- `audit_trail/universal_pick_resolver.py` — add metric logging (`n_intrabar_resolved` per run)

**Expected impact**
- Honest TP/SL hit detection. Removes the "close-only" bias that inflates PF.

**Effort estimate**
- 1–2 days

---

### MF-3: Refresh all stale JSON artifacts
**What to do**
- Multiple critical JSONs are frozen:
  - `dashboard_data.json` — 26 days stale
  - `picks_now.json` — 7 days stale
  - `picks_now_live_pnl.json` — 45 hours stale
  - `db_freshness.json` — 175 days stale (abandoned)
  - `feature_signals_latest.json` — 79.5 hours stale
  - `hyro_quan_bridge.json` — 45.8 hours stale
- Build a single `tools/stale_artifact_refresher.py` that:
  1. Checks `mtime` / `generated_at` of each artifact.
  2. Calls the correct generator script if age exceeds threshold.
  3. Writes a unified `artifact_freshness.json` report (replaces the abandoned `db_freshness.json`).
- Schedule it hourly via a new lightweight workflow `.github/workflows/artifact-freshness-guardian.yml`.
- For `db_freshness.json`: either delete it (it is misleading) or redirect consumers to the new `artifact_freshness.json`.

**File/location to edit**
- `tools/stale_artifact_refresher.py` — new
- `.github/workflows/artifact-freshness-guardian.yml` — new
- `audit_dashboard/data/db_freshness.json` — delete or replace

**Expected impact**
- All dashboard panels show current data. HyroTrader "Loading…" issue resolved.

**Effort estimate**
- 1–2 days

---

### MF-4: Make Alpha Engine MySQL sync fail-loud
**What to do**
- The Full MySQL sync step (`alpha-engine-live.yml`, lines 812–828) sets `continue-on-error: true`, then warns if it failed. Because the DB is the source of truth for the dashboard, a silent sync failure means the dashboard drifts from git state.
- Change `continue-on-error: true` → `false`.
- Add a retry loop (3×, exponential backoff) around `sync_all_picks_to_mysql.py` before giving up.
- If sync still fails after retries, skip the git commit and emit `::error` so the run is red.

**File/location to edit**
- `.github/workflows/alpha-engine-live.yml` — Full MySQL sync step
- `sync_all_picks_to_mysql.py` — add idempotency so retries are safe

**Expected impact**
- DB and git state stay in sync. Dashboard no longer shows phantom picks from prior runs.

**Effort estimate**
- 3–6 hours

---

## 3. LONG-TERM FIXES (1–2 weeks)

---

### LF-1: Delta-only MySQL sync + stop git-committing 44 MB `dashboard_data.json`
**What to do**
- `audit-dashboard.yml` commits a **44 MB** `dashboard_data.json` every hour. The git pack has grown to **~19 GB**, causing checkout hangs (documented in `audit-dashboard.yml` lines 82–92). The current workaround (`filter: blob:none`) treats the symptom.
- Stop committing generated artifacts to git:
  1. Add `audit_dashboard/data/*.json` to `.gitignore` (except template/config files).
  2. Upload `dashboard_data.json` as a GitHub Actions artifact (retention: 7 days) or to S3/R2.
  3. Change the FTP deploy step to pull from the artifact URL instead of the repo path.
  4. Switch MySQL sync to **delta-only** (INSERT/UPDATE only changed rows) so the 17-minute full sync becomes <2 minutes, eliminating the timeout/cancel pressure.

**File/location to edit**
- `.gitignore` — add generated JSON blobs
- `.github/workflows/audit-dashboard.yml` — artifact upload + FTP pull from artifact
- `sync_all_picks_to_mysql.py` — refactor to delta sync

**Expected impact**
- Repo shrinks. Checkouts become fast and reliable. Dashboard deploy time drops from ~35 min to <15 min.

**Effort estimate**
- 1 week

---

### LF-2: Build a unified infrastructure telemetry layer
**What to do**
- Replace the abandoned `db_freshness.json` with a live `infra_health.json` that aggregates:
  - GHA workflow run status (last 10 runs per critical workflow)
  - JSON artifact ages (dashboard_data, picks_now, picks_now_live_pnl, hyro_quan_bridge, feature_signals)
  - DB row counts (active, closed, ghost, TIME_EXIT limbo)
  - Resolver throughput (picks resolved per hour, intrabar vs close-only)
  - Price fetcher health (success rate, avg latency, last failure)
- Build a small FastAPI/Flask app (`tools/infra_health_api.py`) that serves `infra_health.json` and a `/health` endpoint.
- Add a lightweight status page (`audit_dashboard/infra_status.html`) that consumes it.

**File/location to edit**
- `tools/infra_health_collector.py` — new
- `tools/infra_health_api.py` — new
- `audit_dashboard/infra_status.html` — new
- `.github/workflows/infra-health-hourly.yml` — new scheduled workflow

**Expected impact**
- Single pane of glass for system health. Detect outages in minutes instead of days.

**Effort estimate**
- 1 week

---

### LF-3: Circuit breaker for Alpha Engine
**What to do**
- If the primary scanner fails N times consecutively (suggest N=3), auto-pause the cron and alert instead of burning runner minutes on guaranteed failures.
- Implement in `actions-failure-guardian.yml`:
  1. Query the GitHub API for `alpha-engine-live.yml` last 5 runs.
  2. If cancellations + failures ≥ 3, call the GitHub API to disable the workflow (`PATCH /repos/{owner}/{repo}/actions/workflows/{workflow_id}` with `state: disabled`).
  3. Post a Discord/Slack alert with a `workflow_dispatch` re-enable link.
  4. Re-enable automatically after a cooldown (e.g., 6 hours) or require manual approval.

**File/location to edit**
- `.github/workflows/actions-failure-guardian.yml` — add circuit-breaker logic
- `scripts/actions_failure_guardian.py` — extend with workflow disable/enable API calls

**Expected impact**
- Saves runner minutes. Prevents cascading failure noise. Forces human investigation on persistent outages.

**Effort estimate**
- 3–5 days

---

### LF-4: Unified orphan-pipe merger
**What to do**
- Instead of one-off wiring per pipeline (QW-4), build a `pipeline_merge_orchestrator.py` that:
  1. Reads active picks from all scanners: Alpha Engine, Gainer Capture, Copy Trader, AI Challenge, HyroTrader, Momentum Catcher.
  2. Normalizes to a common schema (`symbol`, `direction`, `entry_price`, `tp`, `sl`, `source_system`, `generated_at`, `elite_score`).
  3. Deduplicates by `(symbol, direction, source_system)` or a composite hash.
  4. Applies priority rules (e.g., Alpha Engine > Gainer > Copy Trader for same symbol).
  5. Writes `alpha_engine/data/active_picks_merged.json`.
- Change `audit-dashboard.yml` to consume `active_picks_merged.json` instead of `active_picks.json`.
- Add a validation gate: if any source is >4h stale, flag it in the dashboard but still merge the rest.

**File/location to edit**
- `tools/pipeline_merge_orchestrator.py` — new
- `.github/workflows/audit-dashboard.yml` — change input file
- `audit_trail/dashboard_generator.py` — consume merged file

**Expected impact**
- All live signal streams reach the dashboard reliably. New pipelines can be added with a single config line.

**Effort estimate**
- 1–2 weeks

---

## 4. INFRASTRUCTURE PRIORITY MATRIX

| Fix | Impact | Effort | Priority | Category |
|-----|--------|--------|----------|----------|
| **QW-1** Stop Alpha Engine cascading cancels | 🔴 Critical (restores primary scanner) | 30 min | **P0** | Quick Win |
| **QW-2** Surface `|| non-fatal` failures | 🔴 Critical (stops silent outages) | 2–4 h | **P0** | Quick Win |
| **QW-3** Restart hourly update pipeline | 🟠 High (restores status page) | 1–2 h | **P1** | Quick Win |
| **QW-4** Wire orphan pipelines into dashboard | 🟠 High (restores 2 signal streams) | 4–6 h | **P1** | Quick Win |
| **QW-5** Run MySQL ghost-row dedup | 🟠 High (cleans 23k ghost rows) | 2–3 h | **P1** | Quick Win |
| **MF-1** Rescue TIME_EXIT limbo | 🟠 High (honest closed ledger) | 1–2 d | **P1** | Medium |
| **MF-2** Repair intrabar truth resolution | 🟠 High (honest TP/SL stats) | 1–2 d | **P1** | Medium |
| **MF-3** Refresh all stale JSON artifacts | 🟡 Medium (restores all panels) | 1–2 d | **P2** | Medium |
| **MF-4** Make MySQL sync fail-loud | 🟡 Medium (prevents DB drift) | 3–6 h | **P2** | Medium |
| **LF-1** Delta sync + stop committing 44 MB JSON | 🟡 Medium (fixes repo bloat) | 1 wk | **P2** | Long-term |
| **LF-2** Unified infra telemetry layer | 🟡 Medium (observability) | 1 wk | **P2** | Long-term |
| **LF-3** Circuit breaker for Alpha Engine | 🟢 Low (cost saving + noise reduction) | 3–5 d | **P3** | Long-term |
| **LF-4** Unified orphan-pipe merger | 🟢 Low (scalability) | 1–2 wk | **P3** | Long-term |

---

## Appendix: Root-Cause Cheat Sheet

| Symptom | Likely Root Cause | Quick Fix |
|---------|-------------------|-----------|
| Alpha Engine 9/10 cancelled | `cancel-in-progress: true` + 2h cron < runtime | QW-1 |
| Dashboard 0 active picks | Alpha Engine dead + orphan pipes not merged | QW-1 + QW-4 |
| `dashboard_data.json` 26 days stale | Alpha Engine dead → no new data to merge | QW-1 + MF-3 |
| `picks_now.json` 7 days stale | `picks-now-refresh.yml` failing or push blocked | MF-3 |
| `picks_now_live_pnl.json` 45h stale | Price enricher failing silently (`|| non-fatal`) | QW-2 + MF-3 |
| `at_signal_outcomes` 254 days stale | Missing DB creds (fixed 2026-06-19) but backlog not bootstrapped | MF-2 |
| `db_freshness.json` 175 days stale | File abandoned; generator no longer runs | MF-3 (delete/replace) |
| `hourly_update_last_run.json` 44.6h stale | `audit-hourly-update.yml` failing silently | QW-3 |
| 22,947 ghost rows | MEMECOIN duplicate inserts (no UNIQUE index) | QW-5 |
| 4,220 TIME_EXIT limbo | Resolver timeout too short for backlog | MF-1 |
| Copy Trader / Gainer orphaned | Dashboard generator does not read their JSONs | QW-4 |
