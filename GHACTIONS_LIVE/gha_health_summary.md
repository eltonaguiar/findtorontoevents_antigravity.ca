# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-26T12:42:56.123452+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-18T12:42:56.123452+00:00 → 2026-11-26T12:42:56.123452+00:00 (1000 runs scanned, truncated=False; 394 workflows)
- **API budget:** 107/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Deploy Competition to Live Site | main | 2026-11-26T12:38:07Z | 0.08 | failure | yes |
| Picks-Now Live PnL (hourly) | main | 2026-11-26T12:37:08Z | 0.1 | failure | yes |
| Mirror: findtorontoevents.ca  torontoevent.net | main | 2026-11-26T12:34:32Z | 0.14 | failure | NEVER (prune candidate if dormant) |
| GHCOPILOT prospective paper monitor | main | 2026-11-26T12:32:32Z | 0.17 | failure | yes |
| Send Accountability Reminders | main | 2026-11-26T12:31:26Z | 0.19 | failure | yes |
| Unified Audit Dashboard | main | 2026-11-26T12:03:40Z | 0.65 | failure | NEVER (prune candidate if dormant) |
| Daily Feed Summary | main | 2026-11-26T11:24:07Z | 1.31 | failure | yes |
| CI Tests | main | 2026-11-26T10:59:20Z | 1.73 | failure | yes |
| Verification Tests | main | 2026-11-26T10:27:47Z | 2.25 | failure | NEVER (prune candidate if dormant) |
| Edge stability refresh | main | 2026-11-26T10:26:40Z | 2.27 | failure | NEVER (prune candidate if dormant) |

_(+5 more in JSON)_

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (29 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Verification Tests @ fix/verification-origin-main-fetch — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Verification Tests @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Edge stability refresh @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- DB Sync: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Branch Large File Duplicate Guard @ verify/self-hosted-routing — cadence 168.0h, expect resolution by 2026-12-10T09:40:45.658749+00:00

- resolved: Outcome Resolver  Validate Unresolved Picks → **resolved_flapping**
- resolved: portfolio-tracker → **resolved_flapping**
- resolved: QA Market Validation → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 4
  - run 43097674708 Enhanced ML Crypto Train & Predict queued 2026-11-11T20:42:57Z (age 352.0h) — uncancelable ⇒ GitHub Support batch
  - run 43097693735 Copy Trader Forward Test queued 2026-11-11T20:43:08Z (age 352.0h) — uncancelable ⇒ GitHub Support batch
  - run 43097707633 Meta-Strategy Permutation Engine queued 2026-11-11T20:43:16Z (age 351.99h) — uncancelable ⇒ GitHub Support batch
  - run 43097722505 Audit Hourly Update queued 2026-11-11T20:43:24Z (age 351.99h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 6.32h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 3
  - Signal Recorder — run 45812307518 killed at 1817.0s mid-step `Commit data` — timeout problem, not churn
  - portfolio-tracker — run 45785417296 killed at 618.0s mid-step `Commit the book` — timeout problem, not churn
  - portfolio-tracker — run 45790477827 killed at 618.0s mid-step `Commit the book` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 18 cancelled run(s) examined (18 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 3 · eviction-shaped: 3 · stack-kill: 0 · pr-close: 0 · external: 12
  - external residual (12) — the true R7 signal, investigate:
    - run 45783162353 Insider Trades Refresh — cancelled at 2026-11-26T08:26:27Z (branch main)
    - run 45783078590 Fix Ghost Cards & Thumbnails  All Sites — cancelled at 2026-11-26T08:26:33Z (branch main)
    - run 45783084993 Forex Agent — cancelled at 2026-11-26T08:26:36Z (branch main)
    - run 45783047929 ETF Agent — cancelled at 2026-11-26T08:26:54Z (branch main)
    - run 45783098592 Ops - Authorize gx10 key on the laptop — cancelled at 2026-11-26T08:36:27Z (branch main)
    - run 45783234427 portfolio-tracker — cancelled at 2026-11-26T08:38:18Z (branch main)
    - run 45784081484 realtime-challenge — cancelled at 2026-11-26T08:47:01Z (branch main)
    - run 45786115317 realtime-challenge — cancelled at 2026-11-26T08:57:33Z (branch main)
    - run 45784040820 DNA Strategy Pipeline — cancelled at 2026-11-26T09:04:08Z (branch main)
    - run 45789303750 Verification Tests — cancelled at 2026-11-26T09:10:04Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.2 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.1 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (30 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - FRED Macro Refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - GHA scan job (reusable) [unknown] — SKIPPED(budget): latest-run probe cap reached
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
  - gha-summary-report [daily] — SKIPPED(budget): latest-run probe cap reached
  - Goldmine Tracker - Archive & Maintain [daily] — SKIPPED(budget): latest-run probe cap reached
  - H-103 Forward Logger [monthly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**3** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **307** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
