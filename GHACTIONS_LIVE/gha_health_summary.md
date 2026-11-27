# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-27T00:50:59.960656+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-19T00:50:59.960656+00:00 → 2026-11-27T00:50:59.960656+00:00 (1000 runs scanned, truncated=False; 400 workflows)
- **API budget:** 105/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Kalshi snapshot (sports markets cache) | main | 2026-11-27T00:44:13Z | 0.11 | failure | NEVER (prune candidate if dormant) |
| DB Freshness Guardian | main | 2026-11-27T00:43:43Z | 0.12 | failure | yes |
| CI Tests | main | 2026-11-27T00:43:18Z | 0.13 | failure | yes |
| DB Sync: findtorontoevents.ca  torontoevent.net | main | 2026-11-26T20:54:39Z | 3.94 | failure | NEVER (prune candidate if dormant) |
| Deploy Strategy Bundle | main | 2026-11-26T20:25:05Z | 4.43 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (24 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Verification Tests @ fix/verification-origin-main-fetch — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Verification Tests @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- DB Sync: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Branch Large File Duplicate Guard @ verify/self-hosted-routing — cadence 168.0h, expect resolution by 2026-12-10T09:40:45.658749+00:00
- DB Sync: findtorontoevents.ca  torontoevent.net @ verify/self-hosted-routing — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00

- resolved: Mirror: findtorontoevents.ca  torontoevent.net → **resolved_flapping**
- resolved: Deploy Rise of the Claw Dashboard → **resolved_flapping**
- resolved: Alpha Engine  Daily Picks → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 0
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 3.83h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 0
- **CANCEL BUCKETS (R7)** — 19 cancelled run(s) examined (19 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 0 · eviction-shaped: 5 · stack-kill: 5 · pr-close: 0 · external: 9
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 5 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (9) — the true R7 signal, investigate:
    - run 45886128666 No stale DB passwords — cancelled at 2026-11-26T19:46:37Z (branch main)
    - run 45892742286 Validation Gates (P0.0h) — cancelled at 2026-11-26T20:40:58Z (branch main)
    - run 45893544536 Runner Smoke Test (Linux) — cancelled at 2026-11-26T20:57:30Z (branch main)
    - run 45887396376 DNA Strategy Pipeline — cancelled at 2026-11-26T21:30:06Z (branch main)
    - run 45891609049 DNA Strategy Pipeline — cancelled at 2026-11-26T22:31:33Z (branch main)
    - run 45889377844 Branch Large File Duplicate Guard — cancelled at 2026-11-26T22:50:10Z (branch main)
    - run 45914674064 No stale DB passwords — cancelled at 2026-11-27T00:05:43Z (branch main)
    - run 45914702476 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-27T00:06:35Z (branch main)
    - run 45918339862 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-27T00:45:55Z (branch main)
- **workflow_run fan-in chains:** 6
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.4 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (35 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Forward Ledger — daily sync [daily] — SKIPPED(budget): latest-run probe cap reached
  - forward observations ingest [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forward-Test New Strategies Tracker [daily] — SKIPPED(budget): latest-run probe cap reached
  - FRED Macro Refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Funding-Rate Archive Collector [daily] — SKIPPED(budget): latest-run probe cap reached
  - fx-cost-overlap [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**5** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **208** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
