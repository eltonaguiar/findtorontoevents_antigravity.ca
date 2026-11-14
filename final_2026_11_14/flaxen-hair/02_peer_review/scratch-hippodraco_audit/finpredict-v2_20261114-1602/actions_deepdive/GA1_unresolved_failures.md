# GA1 — Unresolved GitHub Actions Failure Sweep

**Verdict: FAIL — unresolved latest-run failures exist.**

Repo: `eltonaguiar/findtorontoevents_antigravity.ca` · Branch: `main`
Scan window: 2026-11-14 ~17:50Z–17:57Z (commands run against live GitHub API)
Method: `fix-gh-actions` skill (latest-run-per-workflow grouping, dual grouping by name and workflow ID, chronic-cancel rule, per-workflow-ID verification, failed-log inspection).
Source code was **not modified**.

---

## Method (what was actually run)

1. `gh run list --branch main --limit 500 --json databaseId,workflowName,workflowDatabaseId,event,status,conclusion,createdAt,updatedAt,headSha,url` → saved to `actions_deepdive/raw/GA1_runs.json` (500 runs).
2. Grouped the 500 runs **twice and independently**:
   - by `workflowName` → 152 distinct names
   - by `workflowDatabaseId` → 152 distinct IDs
   - Name↔ID mapping anomalies (same display name on multiple IDs, or one ID with multiple names): **0**. The duplicate-display-name hazard did not occur in this window.
3. Flagged every workflow whose LATEST run was `failure`, `timed_out`, `startup_failure`, `stale`, or `cancelled`.
4. Applied the chronic-cancel rule to `cancelled`: ≥4 cancels in the last 15 runs, 0 successes in that window, no success in 48h (also requires ≥5 runs). **0 chronic cancels.**
5. For each flagged workflow, verified by workflow ID: `gh api repos/.../actions/workflows/<id>/runs?branch=main&per_page=20`, then `gh run view <id> --json jobs,...` and `gh run view <id> --log-failed` (stored logs truncated to 200 lines each).
6. Verified the six known run IDs directly (view + run API for `run_attempt`/`previous_attempt_url` + newer runs of the same workflow ID).
7. Audited the guardian workflow and both guardian scripts on `main`.
8. Re-queried the latest run per flagged workflow ID at the end of the sweep to confirm nothing changed to green during analysis.

---

## Summary

| Metric | Count | Source |
|---|---|---|
| Runs scanned | 500 | `GA1_runs.json` |
| Distinct workflows by name | 152 | grouping |
| Distinct workflows by workflow ID | 152 | grouping |
| Name↔ID mapping anomalies | 0 | grouping |
| **Flagged latest-run failures** | **8** | grouping |
| — of which `failure` | 8 | grouping |
| — `timed_out` / `startup_failure` / `stale` | 0 | grouping |
| — latest run `cancelled` | 0 | grouping |
| **Chronic cancels** | **0** | chronic rule |
| Latest run non-completed (in_progress/pending) at scan | 12 | grouping |
| Guardian-reported unresolved failures (17:33:54Z) | 14 | `reports/actions_failure_guardian.json` |
| Guardian-reported chronic cancels | 0 | guardian report |
| Guardian recent runs sampled | 15 (15 success, 0 failure) | `gh run list --workflow actions-failure-guardian.yml` |

**Genuine unresolved vs auto-retried:** all 8 flagged workflows were auto-retried by the guardian (`rerun_triggered: true` in the 17:33Z guardian report) and each latest run is at `run_attempt` 2–4 — they are **auto-retried but still unresolved**. Six additional workflows were mid-rerun at scan time (latest `in_progress`); their outcome is **UNVERIFIED** (see below).

### Latest non-completed runs at scan time (12)

| Workflow | Workflow ID | Run | Status | Created |
|---|---|---|---|---|
| Polymarket Prediction Market Signals (Multi-Asset) | 281981718 | 43622741764 | in_progress | 17:44:31Z |
| Cross-System Signal Aggregator | 281981394 | 43622460469 | in_progress | 17:41:21Z |
| ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds | 281979205 | 43621895588 | pending | 17:35:02Z |
| Gainer Predictor Scanner | 281978129 | 43621517365 | in_progress | 17:30:58Z |
| ALPHA ENGINE - Dynamic Runner (Cloud or Local) | 281982350 | 43620447658 | in_progress | 17:19:13Z |
| Unified Audit Dashboard | 281988696 | 43619994221 | in_progress | 17:14:14Z |
| DNA Strategy Pipeline | 281988695 | 43614551127 | in_progress | 16:14:52Z |
| ALPHA ENGINE - Live Autonomous Scanner | 281987846 | 43614126400 | in_progress | 16:10:15Z |
| Market Beating System - Crypto & Forex Priority | 281986171 | 43613854784 | in_progress | 16:07:19Z |
| Self-Optimizing Trading Bot - Auto-Validates & Tweaks | 281984259 | 43613434000 | in_progress | 16:02:48Z |
| Signal Tracking & Validation - Beat the Market | 281984055 | 43613316905 | in_progress | 16:01:33Z |
| Autonomous Trading Bot - Runs Automatically Every 4 Hours | 281983852 | 43613272988 | in_progress | 16:01:06Z |

Of these, **DNA Strategy Pipeline, ALPHA Live Autonomous Scanner, Market Beating, Self-Optimizing, Signal Tracking, Autonomous Trading Bot** are the six reruns of failures reported by the guardian at 17:33Z. Their latest-run outcome is **UNVERIFIED** (still running when the sweep ended).

---

## Per-workflow evidence (8 flagged latest-run failures)

All eight were re-checked by workflow ID at the end of the sweep and were still the same `completed/failure` run. Logs stored truncated to ≤200 lines under `actions_deepdive/raw/GA1_log_<run>.txt`.

| Workflow (path) | Workflow ID | Latest run | Conclusion | Created (UTC) | Failing step | Root error (from failed log) | Retry state |
|---|---|---|---|---|---|---|---|
| Missed Opportunity Analyzer Hourly Self-Improvement (`.github/workflows/missed-opportunity-scan.yml`) | 281990749 | 43620744998 | failure | 17:22:20 | `Commit results` | Push rejected: `alpha_engine/data/wrong_guesses_log.json` is **100.22 MB**, exceeds GitHub's 100.00 MB limit (GH001). Previous run 43615261146 succeeded at 16:22. | attempt 2; guardian rerun requested; still failing |
| Sports endpoint smoke + Playwright (`.github/workflows/sports-smoke-and-e2e.yml`) | 281989431 | 43620352180 | failure | 17:18:10 | `Install Playwright (chromium only)` | `ERROR: Playwright does not support chromium on ubuntu26.04-x64` (Playwright 1.58.2) | attempt 2; prior attempts 3; still failing |
| CI Tests (`.github/workflows/ci-tests.yml`) | 282011873 | 43615290049 | failure | 16:22:50 | `Run all tests (gating — known-drift quarantined)` on **both** 3.11 and 3.12 | Collection error in `tests/test_combined_book_sleeves.py`: `ValueError: Invalid frequency: ME` (KeyError `'ME'` → pandas frequency unsupported) | attempt 4; still failing |
| Forward Test - Strategy Validation (`.github/workflows/forward_test.yml`) | 281985883 | 43613794351 | failure | 16:06:42 | `Install dependencies` | `pip install -r requirements.txt` builds pandas from source for **CPython 3.14**: `_PyLong_AsByteArray` expected 6 args, have 5 → `metadata-generation-failed` | attempt 4; still failing |
| Live Trading Bot - Canada Edition (FREE Data) (`.github/workflows/live_trading_canada_free.yml`) | 281985754 | 43613787653 | failure | 16:06:37 | `Install dependencies` | Same CPython 3.14 pandas build failure (`_PyLong_AsByteArray`, `metadata-generation-failed`) | attempt 4; still failing |
| Live Trading Bot - Canada Edition (`.github/workflows/live_trading_canada.yml`) | 281985660 | 43613779808 | failure | 16:06:32 | `Install dependencies` | Same CPython 3.14 pandas build failure | attempt 4; still failing |
| Live Trading Bot (`.github/workflows/live_trading.yml`) | 281985082 | 43613629628 | failure | 16:04:56 | `Install dependencies` | Same CPython 3.14 pandas build failure | attempt 4; still failing |
| Crypto Picks Dispatch (`.github/workflows/picks_dispatch.yml`) | 281984481 | 43613459896 | failure | 16:03:05 | `Install dependencies` | Same CPython 3.14 pandas build failure | attempt 4; still failing |

### Notes / caveats on the pandas cluster

- Each of the five pandas-failing workflows declares `python-version: '3.11'` in its YAML, yet the failed build artifacts are named `cpython-314` and the compiler error is the CPython 3.14 `_PyLong_AsByteArray` ABI change. The reason setup did not apply 3.11 is **UNVERIFIED** from failed-step logs alone (the `--log-failed` output begins at the failing install step). Treat "workflow pins 3.11 but install runs 3.14" as a confirmed symptom with an unconfirmed cause.
- The five workflows have been failing for many hours with `run_attempt` 4–8 across the last 20 runs each (e.g., Crypto Picks Dispatch's previous runs were attempt 7–8, all failure). This is a deterministic install failure, not a flake.

---

## Known-run verification

Every requested run was checked via `gh run view <id>` plus the run API (`run_attempt`, `previous_attempt_url`), then the same workflow ID's newer runs were inspected.

| Known run | Workflow (ID) | Current conclusion | run_attempt | Newer runs of same workflow | Status |
|---|---|---|---|---|---|
| 43609547717 | ALPHA ENGINE - Dynamic Runner (281982350) | failure | 1 | 43612197130, 43614960770, 43617643018 all **failure**; 43620447658 in_progress | **Still failing (not retried; scheduled runs keep failing)** |
| 43608586741 | ALPHA ENGINE FAST Tighter TP/SL (281979205) | failure | 1 | 43610957736 failure, 43614165537 (attempt 2) failure, 43616386010 failure; 43619471650 in_progress, 43621895588 pending | **Still failing** |
| 43605861085 | CI Tests (282011873) | failure | 4 | 43615290049 (attempt 4) **failure** | **Still failing / retried, not resolved** |
| 43609430834 | Sports endpoint smoke + Playwright (281989431) | failure | 3 | 43614883408 (attempt 3) failure, 43620352180 (attempt 2) failure | **Still failing / retried, not resolved** |
| 43603128044 | Market Beating System (281986171) | failure | 5 | 43613854784 (attempt 4) in_progress | **Still failing; retry in flight (outcome UNVERIFIED)** |
| 43602685216 | Signal Tracking & Validation (281984055) | failure | 4 | 43613316905 (attempt 4) in_progress | **Still failing; retry in flight (outcome UNVERIFIED)** |

Root errors for the two ALPHA runs (not captured by the 8-way flag because their latest run is currently `in_progress`):

- **43609547717** and **43608586741** both end with:
  `File ".../alpha_engine/scanner.py", line 2942, in rank_and_filter_signals`
  `_forex_by_sym[s["symbol"]][sig_type].append(s)`
  `KeyError: 'LONG'`
  preceded by Binance `451 Client Error` noise. The `KeyError: 'LONG'` is the terminating error (`##[error]Process completed with exit code 1`).
- **43603128044** — failed log retrieval returned 0 lines (`gh run view --log-failed` empty for attempt 5 and for newer failure 43593454374). Job step list confirms step 5 `Install dependencies` failed. Root error is **UNVERIFIED**; consistent with the CPython-3.14 pandas install failure seen in sibling workflows, but not directly evidenced.

No known run has been resolved (no success on the same workflow after the cited run).

---

## Guardian status (self-check)

Guardian workflow: `.github/workflows/actions-failure-guardian.yml`

| Item | Finding |
|---|---|
| Workflow exists on `main` | Yes (fetched via contents API, ref=main) |
| Triggers | `workflow_dispatch` + `schedule: cron '*/30 * * * *'` (every 30 min) |
| Permissions | `contents: write` |
| Invocation | `python scripts/actions_failure_guardian.py` with `GITHUB_TOKEN: ${{ secrets.GH_PAT || github.token }}` |
| Output commit | `.github/scripts/safe_commit_push.sh "Update actions failure guardian status [skip ci]" reports/actions_failure_guardian.json` |
| `scripts/actions_failure_guardian.py` on `main` | Exists — 26,693 bytes, 712 lines; contains `FAILURE_GUARD_CHRONIC_WINDOW`, `CHRONIC_MIN_CANCELLED`, `CHRONIC_MIN_RUNS`, `MIN_HOURS_NO_SUCCESS`, Discord + GITHUB_TOKEN logic |
| `.github/scripts/workflow_health_check.py` on `main` | Exists — 8,072 bytes, 233 lines; contains the same chronic-cancel tunables |
| Recent guardian runs (15 sampled) | 15/15 `success`; latest **43621702340 at 17:32:57Z** |
| Guardian report (`reports/actions_failure_guardian.json`, generated 17:33:54Z) | `runs_scanned=600`, `workflows_scanned=365`, `unresolved_failures_count=14`, `chronic_cancel_workflows_count=0`, `disabled_workflows_count=4`, `stale_workflows_count=207`, `masked_failures_count=0`; all 14 unresolved entries show `rerun_triggered=true`, `rerun_message="rerun requested (201)"` |

**Assessment:** the guardian is present, wired, scheduled, and healthy (no guardian failures). It is doing its job of requesting reruns — every one of the 8 flagged workflows shows a guardian-triggered attempt. However, the failures are deterministic (dependency build, test collection, runner/OS incompatibility, oversized file), so reruns cannot converge. The guardian is not the blocker; the root causes are.

**Guardian cross-check with this scan:** the guardian's 14 unresolved entries match this scan exactly. Eight are still `completed/failure`; six are the workflows whose latest run is now `in_progress` (reruns in flight). Guardian's 0 chronic-cancel count matches this scan's 0.

---

## UNVERIFIED markers

1. **Market Beating 43603128044 root error** — `--log-failed` returned 0 lines for attempt 5 and for the newer failure 43593454374; only the failing step (`Install dependencies`) is confirmed. Cause not directly evidenced.
2. **Six mid-rerun workflows** (DNA Strategy Pipeline, ALPHA Live Autonomous Scanner, Market Beating, Self-Optimizing, Signal Tracking, Autonomous Trading Bot) — latest run `in_progress` at sweep end; pass/fail outcome unknown.
3. **Why the declared `python-version: '3.11'` produced a `cpython-314` pandas build** in the five install-failing workflows — symptom confirmed from logs, cause not established from available failed-step output.
4. **ALPHA Dynamic current run 43620447658 / ALPHA FAST 43619471650 + 43621895588** — in progress/pending at sweep end; outcome unknown (their predecessor runs all failed).

---

## Evidence inventory (`actions_deepdive/raw/`)

| File | Contents |
|---|---|
| `GA1_runs.json` | Raw 500-run list response |
| `GA1_analysis.txt` | Grouping/flag/chronic output (name and ID groupings) |
| `GA1_latest_by_id.tsv` | Authoritative latest run per flagged workflow ID |
| `GA1_run_<run>.json` | `gh run view` job/step detail for each flagged run |
| `GA1_log_<run>.txt` | Failed logs, truncated to ≤200 lines |
| `GA1_known_<run>.json` / `GA1_known_<run>_api.json` | Known-run view + run API data |
| `GA1_knownlog_<run>.txt` | Known-run failed logs (truncated) |
| `GA1_wf_<id>_runs.json` / `GA1_wf_<id>_meta.json` | Per-workflow-ID run history + metadata |
| `GA1_wfyaml_<workflow>.json` | Workflow YAML snapshots from `main` |
| `GA1_guardian_runs.json` | Guardian workflow run list |
| `GA1_guardian_report.json` / `_api.json` | Guardian output report |
| `GA1_guardian_workflow.yml` | Guardian workflow definition |
| `GA1_guardian_script_api.json` / `GA1_healthcheck_api.json` | Guardian script contents |
