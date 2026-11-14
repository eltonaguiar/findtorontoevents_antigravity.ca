# GitHub Actions Deep Dive — 2026-11-14

**Audit clock:** 2026-11-14T17:50–17:57Z
**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca` (`main`)
**Method:** `fix-gh-actions` skill (latest-run-per-workflow, dual name/ID grouping, chronic-cancel rule, per-workflow-ID verification, failed-log mining) + job-level API analysis.
**Subagents:** GA1 (unresolved failures), GA2 (stale inventory), GA3 (log errors/warnings), GA4 (jobs/scheduling).
**Source changes:** none. Reports: `GA1..GA4*.md`; matrix: `GA2_workflow_matrix.csv`; raw: `raw/`.

---

## Verdict: **FAIL**

The critical audit/money path is running, the guardian is healthy, and no chronic-cancel workflow was found. But 8 workflows have an unresolved latest-run failure, 56/365 are stale, and the scheduler is structurally saturated: **35% of audit-dashboard runs are cancelled with zero jobs executed**, and key jobs wait **1.5–3.7 h** in queue.

---

## 1. Unresolved latest-run failures — **8 of 152**

Scanned 500 runs; grouped by name and by workflow ID (0 name↔ID anomalies). Latest run was `failure` for 8 workflows; 0 `timed_out`/`startup_failure`/`stale`; 0 chronic cancels. All 8 were auto-retried by the guardian and are now at `run_attempt` 2–4 — **retried but still unresolved**.

| Workflow | Path | Latest run | Failing step | Root error |
|---|---|---|---|---|
| Missed Opportunity Analyzer | `missed-opportunity-scan.yml` | 43620744998 | Commit results | `wrong_guesses_log.json` is **100.22 MB** > GitHub 100 MB limit; push rejected |
| Sports smoke + Playwright | `sports-smoke-and-e2e.yml` | 43620352180 | Install Playwright | `Playwright 1.58.2` does not support `ubuntu26.04-x64` |
| CI Tests | `ci-tests.yml` | 43615290049 | Run all tests (3.11 + 3.12) | `tests/test_combined_book_sleeves.py`: `ValueError: Invalid frequency: ME` against `pandas==2.1.4` |
| Forward Test | `forward_test.yml` | 43613794351 | Install dependencies | pandas source build on **CPython 3.14**: `_PyLong_AsByteArray` ABI mismatch |
| Live Trading Canada FREE | `live_trading_canada_free.yml` | 43613787653 | Install dependencies | same CPython 3.14 pandas failure |
| Live Trading Canada | `live_trading_canada.yml` | 43613779808 | Install dependencies | same |
| Live Trading Bot | `live_trading.yml` | 43613629628 | Install dependencies | same |
| Crypto Picks Dispatch | `picks_dispatch.yml` | 43613459896 | Install dependencies | same |

**Known-run verification:** ALPHA Dynamic 43609547717 and ALPHA FAST 43608586741 remain failing with `KeyError: 'LONG'` at `alpha_engine/scanner.py:2942`; newer scheduled runs also failed. CI/Sports are the same deterministic failures above, not flakes.

---

## 2. Log error/warning clusters (30 failures, 13:18–17:22Z)

| # | Root cause | Failed runs | Workflows | Evidence | Feeds audit |
|---|---|---:|---|---|---|
| A | `KeyError: 'LONG'` — forex map inner dict only has `BUY`/`SELL` | **15 (50%)** | ALPHA Dynamic ×8, ALPHA FAST ×7 | `scanner.py:2942`; 558 runner-min wasted | **Yes** (primary pick source) |
| B | pandas built on Python 3.14 despite `python-version: '3.11'` because `update-environment: false` | **7** | Forward Test, Live Trading ×3, Crypto Picks Dispatch, Market Beating, Signal Tracking | `_PyLong_AsByteArray` → `metadata-generation-failed`; ~715 runner-min | Indirect |
| C | Playwright 1.58.2 unsupported on `ubuntu26.04-x64` | **5** | Sports smoke | install error | No |
| D | `freq="ME"` (pandas 2.2 alias) against pinned `pandas==2.1.4` | **2** | CI Tests (3.11, 3.12) | `tests/test_combined_book_sleeves.py:17` | Indirect (CI gate) |
| E | 100.22 MB tracked JSON over GitHub limit | **1** | Missed Opportunity | `alpha_engine/data/wrong_guesses_log.json` | Indirect |

**Noise / hygiene:** 6,628 Binance `451` lines across 15 alpha runs swamp the real terminal error; 14/30 runs returned no `--log-failed` output and were recovered from the logs ZIP API; 70 workflow files use `continue-on-error: true`, and several `|| true` / bare `except` paths swallow failures before logging.

---

## 3. Stale / never-run inventory — **56 of 365**

| Bucket | Count | Notes |
|---|---:|---|
| Never run (all-time) | **20** | templates/one-offs; several stale stubs |
| >7 d | **36** | most are monthly/quarterly by design |
| **Total stale (never or >7 d)** | **56 (15.3%)** | 52 active + 4 disabled |
| Disabled but still carrying `cron:` | **4** | `ai-tournament-pipeline`, `battle_test`, `forex-agent`, `forex-smart-picks` |
| Orphaned registrations (file deleted from `main`) | **2** | `db-secret-scan.yml`, `mermaid-test-deploy.yml` |

**Critical path is fresh:** `audit-dashboard.yml` (17:14Z), `audit-hourly-update.yml` (17:21Z success), `db-freshness-guardian.yml` (17:01Z success), `cross-db-audit.yml` (06:06Z success), `pick-funnel-nightly.yml` (04:05Z success). No active recurring schedule is cadence-overdue.

**Material stale failure:** `backup-verify.yml` (monthly audit dependency) last ran 2026-10-15 and **failed**.

**Duplicate/legacy families (recommend owner review, do not auto-delete):** DB freshness legacy vs guardian; secret-scan orphan; edge-stability duplicate name; three movie-fetch variants; three meme-scanner generations; `2hour_challenge` vs unused `real_`; battleground pair; AI tournament old vs monthly; four forward-test variants; deploy/mirror pairs.

---

## 4. Job-level scheduling / concurrency — **FAIL**

| Metric | Observed |
|---|---|
| Audit-dashboard last 60 runs | 37 success, **22 cancelled**, 1 in progress |
| Cancels with **zero jobs executed** | **21 of 22 (95%) = 35% of all runs** |
| Zero-job queue wait before discard | 39–67 min (median ~59) |
| Audit job p50 / p95 | **97.2 / 111.6 min** vs 60-min cron and 115-min timeout |
| Queue p50: Signal / Market / Mirror / PEAD | **91.4 / 118.5 / 174.0 / 221.2 min** |
| Scheduled workflows | 310; **166 have no `concurrency:`** |
| Scheduled + push-to-main + no concurrency | **91** |
| Cron entries firing at `:00` | **196** (114 push to main) |
| PEAD push-retry exhaustion | **60/60 recent runs** fail in `Commit shadow log` |
| Live Spike push exhaustion | 1/60 (30.2 min burned) |
| Mirror failures | 60/60 are **FTP download timeouts**, not push |

**Structural causes:** hourly cron is shorter than the job's own p50 runtime; `dashboard-publish` is shared by 3 workflows (`audit-dashboard`, `operator-review-today`, `rsi5070-forward-snapshot`); 166 scheduled workflows lack concurrency; many push-to-main jobs fire at `:00`/`:30`.

**Guardian:** `actions-failure-guardian.yml` is healthy (15/15 recent success, latest 43621702340 at 17:32:57Z). Its 17:33:54Z report independently shows **14 unresolved, 0 chronic cancels** and requests reruns; reruns cannot fix deterministic root causes.

---

## 5. Fix plan

### P0 — do first (each ≤1 day, reversible)

| # | Fix | Exact target | Impact | Risk |
|---|---|---|---|---|
| 1 | Normalize `LONG/SHORT → BUY/SELL` before the FX map lookup | `alpha_engine/scanner.py:2937-2942` | Removes **15/30** failures, ~88/day, ~558 runner-min | Low; log normalization |
| 2 | Remove `update-environment: false` (or use `python -m pip`) so 3.11 is actually used | `forward_test.yml:33`, `live_trading.yml:29`, `live_trading_canada.yml:33`, `live_trading_canada_free.yml:43`, `picks_dispatch.yml:24`, `market_beating.yml:35`, `signal_tracking.yml:35` | Removes **7/30** failures, ~715 runner-min, ~100-min builds | Low |
| 3 | Fix CI frequency alias | `tests/test_combined_book_sleeves.py:17` (`"ME"` → `"M"`/`"MS"`) or pin pandas 2.2 | Removes **2/30**, unblocks CI gate | Low |
| 4 | Pin runner / upgrade Playwright | `sports-smoke-and-e2e.yml:53` (`ubuntu-24.04`), `:86`; `package.json:20` | Removes **5/30** | Low |
| 5 | Stop committing the 100 MB JSON | `missed-opportunity-scan.yml:43`; `.gitignore`; `git rm --cached`; rotate/LFS | Removes **1/30** | Low (history may need LFS) |
| 6 | Space audit cron to match runtime | `audit-dashboard.yml:5` `'10 * * * *'` → `'10 */2 * * *'`; `:55` timeout 115→130 | Eliminates ~21 zero-job discards/60; freshness ≤2 h | Low; slower refresh |
| 7 | Split the shared concurrency group | `operator-review-today.yml:39`, `rsi5070-forward-snapshot.yml:59` → `dashboard-publish-daily` | Removes 3-way 07:00/07:10 contention | Low |
| 8 | Fix PEAD push loop | `pead-shadow-collector.yml:82-101` | Stops 60/60 commit failures | Medium |
| 9 | Stop duplicate push runs | `signal_tracking.yml:9-14`, `market_beating.yml:9-14` remove `push:` | Removes duplicate runs in a 91-min queue | Low |

### P1 — structural

- Add `concurrency` + `timeout-minutes` to the 166 scheduled workflows lacking it; stagger `:00`/`:30` clusters.
- Add `filter: blob:none` to `signal_tracking.yml:29` / `market_beating.yml:29` checkout (15–20 min → 1–2 min).
- Fix `backup-verify.yml` (failed 30.4 d) or mark known-failing.
- Clean 4 disabled-with-cron files and 2 orphaned registrations (recommend only).
- Consolidate duplicate families after owner confirmation (do **not** mass-delete).
- Make silent failures loud: audit `continue-on-error: true` (70 files) and `|| true`.

### Validation

```bash
gh run list --branch main --limit 500 --json workflowName,conclusion,createdAt \
  --jq '[group_by(.workflowName)[]|sort_by(.createdAt)|last|select(.conclusion=="failure")]|length'
gh run view <new_run_id> --log-failed
gh api repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/<id>/jobs
```

Target after P0: unresolved latest-run failures ≤2 (only mid-rerun), 24 h failure count <20, audit zero-job cancels = 0, audit p95 < 130 min.

---

## 6. Reconciliation with the earlier Actions section

The earlier `sub/A_actions_health.md` (16:05Z) reported 4,109 runs/24 h, 24 failing workflows/24 h, 82 cancels, and an 84.5-min median. The 17:50Z deep dive refines this:
- Latest-run failures at scan time: **8 of 152** (window-sensitive; not a contradiction — the 24 h window includes resolved and retried runs).
- Audit duration: **p50 97.2 / p95 111.6 min** (supersedes the single 84.5-min median).
- Zero-job cancels: **21 of 22** in the last 60 audit runs (supersedes "9 of 24 h cancels").
- New failure clusters not in `sub/A`: Playwright `ubuntu26.04`, CI `ME` alias, 100 MB LFS limit, PEAD 60/60 push exhaustion.

`sub/A` remains correct on totals (365 workflows, 20 never-run, 36 stale >7 d, 93 alpha failures/24 h at its clock).

---

## 7. UNVERIFIED

- Why `setup-python` 3.11 does not win despite `python-version: '3.11'` (symptom confirmed; cause inferred from `update-environment: false`).
- Root cause of the 17:33:40–49Z mass failure (~20 workflows starting after a 70–90 min queue).
- PEAD 60/60 push failures for every run (3/3 sampled show the 10-attempt loop).
- Whether the guardian's 14 reruns ultimately succeed (six were mid-rerun at scan end).
- Repo-wide warning census beyond the 30 sampled failures.
