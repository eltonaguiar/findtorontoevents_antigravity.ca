# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-26T08:40:45.658749+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-18T08:40:45.658749+00:00 → 2026-11-26T08:40:45.658749+00:00 (1000 runs scanned, truncated=False; 391 workflows)
- **API budget:** 137/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Ops - Authorize gx10 key on the laptop | fix/verification-origin-main-fetch | 2026-11-26T08:40:13Z | 0.01 | failure | NEVER (prune candidate if dormant) |
| Ops - Authorize gx10 key on the laptop | main | 2026-11-26T08:39:51Z | 0.02 | failure | NEVER (prune candidate if dormant) |
| Verification Tests | fix/verification-origin-main-fetch | 2026-11-26T08:37:23Z | 0.06 | failure | NEVER (prune candidate if dormant) |
| masking-policy-lint | fix/fx-cost-overlap-safe-push | 2026-11-26T08:33:53Z | 0.11 | failure | NEVER (prune candidate if dormant) |
| Outcome Resolver  Validate Unresolved Picks | main | 2026-11-26T08:33:30Z | 0.12 | failure | NEVER (prune candidate if dormant) |
| Clear Channel Command | main | 2026-11-26T08:31:15Z | 0.16 | failure | NEVER (prune candidate if dormant) |
| Verification Tests | main | 2026-11-26T08:30:39Z | 0.17 | failure | NEVER (prune candidate if dormant) |
| Fast Stocks Competition  High Frequency Scanner | main | 2026-11-26T08:30:23Z | 0.17 | failure | NEVER (prune candidate if dormant) |
| Deploy Strategy Bundle | main | 2026-11-26T08:30:25Z | 0.17 | failure | NEVER (prune candidate if dormant) |
| Closed Picks Command | main | 2026-11-26T08:30:25Z | 0.17 | failure | NEVER (prune candidate if dormant) |

_(+29 more in JSON)_

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (25 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Verification Tests @ fix/verification-origin-main-fetch — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Outcome Resolver  Validate Unresolved Picks @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Verification Tests @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Edge stability refresh @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- DB Sync: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00

- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: Forward-Test New Strategies Tracker → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 10
  - run 43097018427 ALPHA ENGINE - Dynamic Runner (Cloud or Local) queued 2026-11-11T20:36:11Z (age 348.08h) — uncancelable ⇒ GitHub Support batch
  - run 43097022273 UEPS Pick Runner queued 2026-11-11T20:36:13Z (age 348.08h) — uncancelable ⇒ GitHub Support batch
  - run 43097024915 Claude Code Gainer ML Tracker queued 2026-11-11T20:36:14Z (age 348.08h) — uncancelable ⇒ GitHub Support batch
  - run 43097026953 Baby Strat Real Forward Monitor queued 2026-11-11T20:36:16Z (age 348.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097029325 Signal Integrator - Isolated Source Aggregator queued 2026-11-11T20:36:17Z (age 348.07h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 2
  - Discord Bot  Persistent — 5.29h running (p90 n/a)
  - Walk-Forward Backtest (Weekly) — 2.57h running (p90 0.15h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 3
  - Baby Strat Real Forward Monitor — run 45769038199 killed at 2420.0s mid-step `?` — timeout problem, not churn
  - Weekly Real-Money Filter — run 45769044156 killed at 918.0s mid-step `?` — timeout problem, not churn
  - Weekly Real-Money Filter — run 45771048459 killed at 918.0s mid-step `?` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 74 cancelled run(s) examined (30 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 3 · eviction-shaped: 19 · stack-kill: 1 · pr-close: 0 · external: 51
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 1 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (51) — the true R7 signal, investigate:
    - run 45766993833 Equities & Stocks Agent — cancelled at 2026-11-26T06:21:07Z (branch verify/self-hosted-routing)
    - run 45766952013 ALPHA  Verify Predictions — cancelled at 2026-11-26T06:24:41Z (branch verify/self-hosted-routing)
    - run 45766969003 BESTIEJOB page QA — cancelled at 2026-11-26T06:42:42Z (branch verify/self-hosted-routing)
    - run 45767000780 Forward-Test New Strategies Tracker — cancelled at 2026-11-26T06:48:54Z (branch verify/self-hosted-routing)
    - run 45771036073 Forward-Test New Strategies Tracker — cancelled at 2026-11-26T06:53:21Z (branch verify/self-hosted-routing)
    - run 45767041212 provenance-verify — cancelled at 2026-11-26T06:56:29Z (branch verify/self-hosted-routing)
    - run 45766981331 Conviction Picks Ultra-Selective Discord Alert — cancelled at 2026-11-26T06:57:07Z (branch verify/self-hosted-routing)
    - run 45767595625 ALPHA ENGINE - Incubator Strategies — cancelled at 2026-11-26T07:03:37Z (branch verify/self-hosted-routing)
    - run 45766978235 Buy Now Analysis & Tracking — cancelled at 2026-11-26T07:06:59Z (branch verify/self-hosted-routing)
    - run 45766723978 Data Pipeline Reliability Test — cancelled at 2026-11-26T07:08:38Z (branch verify/self-hosted-routing)
    - _(+31 more in JSON)_
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 2.8 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 1.1 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.0 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 5 (29 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - strategy_performance.json no-regression guard [unknown] — stale by cadence: silent 183d as unknown (threshold 60d)
  - AI Tournament Pipeline — Daily Picks + DB Ingest [daily] — stale by cadence: silent 175d as daily (threshold 30d)
  - Real-Time Battle Test - Eliminate Losers, Optimize Winners [hourly] — stale by cadence: silent 166d as hourly (threshold 30d)
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**8** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **511** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
