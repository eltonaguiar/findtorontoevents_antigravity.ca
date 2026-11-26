# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-26T16:40:07.555731+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-18T16:40:07.555731+00:00 → 2026-11-26T16:40:07.555731+00:00 (1000 runs scanned, truncated=False; 394 workflows)
- **API budget:** 79/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Deploy Competition to Live Site | main | 2026-11-26T16:33:57Z | 0.1 | failure | NEVER (prune candidate if dormant) |
| Picks-Now Live PnL (hourly) | main | 2026-11-26T16:31:45Z | 0.14 | failure | NEVER (prune candidate if dormant) |
| GHCOPILOT prospective paper monitor | main | 2026-11-26T16:27:35Z | 0.21 | failure | NEVER (prune candidate if dormant) |
| Send Accountability Reminders | main | 2026-11-26T16:26:04Z | 0.23 | failure | NEVER (prune candidate if dormant) |
| Daily Feed Summary | main | 2026-11-26T15:24:44Z | 1.26 | failure | NEVER (prune candidate if dormant) |
| Picks NOW Refresh | main | 2026-11-26T14:03:39Z | 2.61 | failure | NEVER (prune candidate if dormant) |
| gha-summary-report | main | 2026-11-26T13:58:27Z | 2.69 | failure | NEVER (prune candidate if dormant) |
| forward observations ingest | main | 2026-11-26T13:26:16Z | 3.23 | failure | NEVER (prune candidate if dormant) |
| Mirror: findtorontoevents.ca  torontoevent.net | main | 2026-11-26T13:25:42Z | 3.24 | failure | NEVER (prune candidate if dormant) |
| Deploy MOVIESHOWS2 + MOVIESHOWS3 (All 3 Domains) | main | 2026-11-26T13:25:15Z | 3.25 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (31 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Verification Tests @ fix/verification-origin-main-fetch — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Verification Tests @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Edge stability refresh @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- DB Sync: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Branch Large File Duplicate Guard @ verify/self-hosted-routing — cadence 168.0h, expect resolution by 2026-12-10T09:40:45.658749+00:00

- resolved: Picks-Now Live PnL (hourly) → **escalated_still_broken**
- resolved: GHCOPILOT prospective paper monitor → **escalated_still_broken**
- resolved: Send Accountability Reminders → **escalated_still_broken**
- resolved: Unified Audit Dashboard → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 4
  - run 43097674708 Enhanced ML Crypto Train & Predict queued 2026-11-11T20:42:57Z (age 355.95h) — uncancelable ⇒ GitHub Support batch
  - run 43097693735 Copy Trader Forward Test queued 2026-11-11T20:43:08Z (age 355.95h) — uncancelable ⇒ GitHub Support batch
  - run 43097707633 Meta-Strategy Permutation Engine queued 2026-11-11T20:43:16Z (age 355.95h) — uncancelable ⇒ GitHub Support batch
  - run 43097722505 Audit Hourly Update queued 2026-11-11T20:43:24Z (age 355.95h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 0
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 2
  - 2hour-challenge — run 45818757485 killed at 1817.0s mid-step `Run 2-hour trading challenge` — timeout problem, not churn
  - Signal Recorder — run 45812307518 killed at 1817.0s mid-step `Commit data` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 4 cancelled run(s) examined (4 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 2 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 1
  - external residual (1) — the true R7 signal, investigate:
    - run 45821048293 DNA Strategy Pipeline — cancelled at 2026-11-26T13:07:08Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.0 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (30 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Refresh Movies Databases (50webs + GoDaddy) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Funding-Rate Archive Collector [daily] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **199** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
