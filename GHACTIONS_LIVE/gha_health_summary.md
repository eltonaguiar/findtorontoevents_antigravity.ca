# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-27T08:40:27.790951+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-19T08:40:27.790951+00:00 → 2026-11-27T08:40:27.790951+00:00 (1000 runs scanned, truncated=False; 400 workflows)
- **API budget:** 81/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| DB Sync: findtorontoevents.ca  torontoevent.net | main | 2026-11-27T08:32:11Z | 0.14 | failure | NEVER (prune candidate if dormant) |
| DB Freshness Guardian | main | 2026-11-27T08:28:18Z | 0.2 | failure | NEVER (prune candidate if dormant) |
| Refresh Movies Databases (50webs + GoDaddy) | main | 2026-11-27T07:53:13Z | 0.79 | failure | NEVER (prune candidate if dormant) |
| _tmp probe rest | main | 2026-11-27T07:52:17Z | 0.8 | failure | NEVER (prune candidate if dormant) |
| _tmp probe equity | main | 2026-11-27T07:25:22Z | 1.25 | failure | NEVER (prune candidate if dormant) |
| Gate Config Emit | main | 2026-11-27T05:53:19Z | 2.79 | failure | NEVER (prune candidate if dormant) |
| Sign-Coherence Gate | main | 2026-11-27T05:26:11Z | 3.24 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (23 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Verification Tests @ fix/verification-origin-main-fetch — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- DB Sync: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Branch Large File Duplicate Guard @ verify/self-hosted-routing — cadence 168.0h, expect resolution by 2026-12-10T09:40:45.658749+00:00
- DB Sync: findtorontoevents.ca  torontoevent.net @ verify/self-hosted-routing — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- ALPHA  Verify Predictions @ verify/self-hosted-routing — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00

- resolved: DB Freshness Guardian → **escalated_still_broken**
- resolved: forward observations ingest → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 0
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 5.82h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 0
- **CANCEL BUCKETS (R7)** — 7 cancelled run(s) examined (7 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 0 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 6
  - external residual (6) — the true R7 signal, investigate:
    - run 45946357497 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-27T05:33:28Z (branch main)
    - run 45956189282 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-27T07:08:47Z (branch main)
    - run 45957634811 No stale DB passwords — cancelled at 2026-11-27T07:19:18Z (branch main)
    - run 45957634615 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-27T07:19:18Z (branch main)
    - run 45957643426 Audit Drift Telemetry — cancelled at 2026-11-27T07:19:58Z (branch main)
    - run 45952983693 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-27T08:30:14Z (branch main)
- **workflow_run fan-in chains:** 6
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.9 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.2 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (35 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Growth Stock Screener Daily [weekly] — SKIPPED(budget): latest-run probe cap reached
  - guard-ops-workflows [daily] — SKIPPED(budget): latest-run probe cap reached
  - H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-103 Forward Logger [monthly] — SKIPPED(budget): latest-run probe cap reached
  - HC Evaluator Parity Test [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Hierarchical Bayesian Edge Update [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**8** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **226** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
