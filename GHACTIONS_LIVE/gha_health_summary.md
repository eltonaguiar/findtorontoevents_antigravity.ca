# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-26T20:39:30.841003+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-18T20:39:30.841003+00:00 → 2026-11-26T20:39:30.841003+00:00 (1000 runs scanned, truncated=False; 400 workflows)
- **API budget:** 94/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Deploy Rise of the Claw Dashboard | main | 2026-11-26T20:27:07Z | 0.21 | failure | yes |
| DB Sync: findtorontoevents.ca  torontoevent.net | main | 2026-11-26T20:26:23Z | 0.22 | failure | NEVER (prune candidate if dormant) |
| Alpha Engine  Daily Picks | main | 2026-11-26T20:25:55Z | 0.23 | failure | yes |
| Deploy Strategy Bundle | main | 2026-11-26T20:25:05Z | 0.24 | failure | NEVER (prune candidate if dormant) |
| Verification Tests | main | 2026-11-26T19:27:43Z | 1.2 | failure | NEVER (prune candidate if dormant) |
| forward observations ingest | main | 2026-11-26T19:24:40Z | 1.25 | failure | NEVER (prune candidate if dormant) |
| Clear Channel Command | main | 2026-11-26T19:23:56Z | 1.26 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (24 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Verification Tests @ fix/verification-origin-main-fetch — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Verification Tests @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- DB Sync: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Branch Large File Duplicate Guard @ verify/self-hosted-routing — cadence 168.0h, expect resolution by 2026-12-10T09:40:45.658749+00:00
- Mirror: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00

- resolved: Edge stability refresh → **resolved_flapping**
- resolved: Deploy Competition to Live Site → **resolved_flapping**
- resolved: Daily Feed Summary → **resolved_flapping**
- resolved: CI Tests → **resolved_flapping**
- resolved: Picks-Now Live PnL (hourly) → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 1
  - run 43097722505 Audit Hourly Update queued 2026-11-11T20:43:24Z (age 359.94h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 5.49h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 4
  - AsterDEX Paper Trading — run 45866213125 killed at 739.0s mid-step `Deploy dashboard to FTP` — timeout problem, not churn
  - Check Streamer Live Status — run 45863024602 killed at 1818.0s mid-step `Run streamer status check` — timeout problem, not churn
  - Meme Coin Scanner v2  Fixed & Monitored — run 45864509999 killed at 317.0s mid-step `Deploy meme_scanner_fixed.php to server` — timeout problem, not churn
  - Mirror: findtorontoevents.ca  torontoevent.net — run 45876384114 killed at 5418.0s mid-step `Deploy fc/api/.env to GoDaddy (GoDaddy MySQL creds)` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 13 cancelled run(s) examined (13 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 4 · eviction-shaped: 3 · stack-kill: 1 · pr-close: 0 · external: 5
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 1 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (5) — the true R7 signal, investigate:
    - run 45859565430 DNA Strategy Pipeline — cancelled at 2026-11-26T17:03:22Z (branch main)
    - run 45863610045 DB Sync: findtorontoevents.ca  torontoevent.net — cancelled at 2026-11-26T17:16:43Z (branch main)
    - run 45858698516 Send Accountability Reminders — cancelled at 2026-11-26T17:24:48Z (branch main)
    - run 45886128666 No stale DB passwords — cancelled at 2026-11-26T19:46:37Z (branch main)
    - run 45876361022 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-26T20:26:01Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.4 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (36 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Refresh Movies Databases (50webs + GoDaddy) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Funding-Rate Archive Collector [daily] — SKIPPED(budget): latest-run probe cap reached
  - Futures Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**10** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **192** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
