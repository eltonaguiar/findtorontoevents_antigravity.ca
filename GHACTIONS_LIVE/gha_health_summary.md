# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-27T04:39:47.825283+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-19T04:39:47.825283+00:00 → 2026-11-27T04:39:47.825283+00:00 (1000 runs scanned, truncated=False; 400 workflows)
- **API budget:** 93/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| DB Freshness Guardian | main | 2026-11-27T04:27:12Z | 0.21 | failure | NEVER (prune candidate if dormant) |
| schema probe (temporary) | main | 2026-11-27T02:52:00Z | 1.8 | failure | NEVER (prune candidate if dormant) |
| forward observations ingest | main | 2026-11-27T02:30:03Z | 2.16 | failure | yes |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (22 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Verification Tests @ fix/verification-origin-main-fetch — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- DB Sync: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Branch Large File Duplicate Guard @ verify/self-hosted-routing — cadence 168.0h, expect resolution by 2026-12-10T09:40:45.658749+00:00
- DB Sync: findtorontoevents.ca  torontoevent.net @ verify/self-hosted-routing — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- ALPHA  Verify Predictions @ verify/self-hosted-routing — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00

- resolved: Verification Tests → **resolved_flapping**
- resolved: forward observations ingest → **resolved_flapping**
- resolved: Kalshi snapshot (sports markets cache) → **resolved_flapping**
- resolved: DB Freshness Guardian → **escalated_still_broken**
- resolved: CI Tests → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 0
- **Runner hogs (in_progress > 2h or > 2x p90):** 0
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 0
- **CANCEL BUCKETS (R7)** — 13 cancelled run(s) examined (13 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 0 · eviction-shaped: 5 · stack-kill: 4 · pr-close: 0 · external: 4
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 4 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (4) — the true R7 signal, investigate:
    - run 45914674064 No stale DB passwords — cancelled at 2026-11-27T00:05:43Z (branch main)
    - run 45914702476 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-27T00:06:35Z (branch main)
    - run 45918339862 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-27T00:45:55Z (branch main)
    - run 45926297646 Verification Tests — cancelled at 2026-11-27T02:05:52Z (branch main)
- **workflow_run fan-in chains:** 6
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.9 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (34 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - ETF Trend Forward Clock (month-end) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Refresh Movies Databases (50webs + GoDaddy) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Futures Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - fx-cost-overlap [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 1
  - Sign-Coherence Gate @ main — never passed in window, last failure 9999.0h ago

## 5. NOT AN ISSUE (recovered) — suppressed count

**6** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **209** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
