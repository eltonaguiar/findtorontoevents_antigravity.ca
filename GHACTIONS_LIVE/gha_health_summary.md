# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-28T04:39:28.032153+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-20T04:39:28.032153+00:00 → 2026-11-28T04:39:28.032153+00:00 (1000 runs scanned, truncated=False; 400 workflows)
- **API budget:** 85/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| DB Freshness Guardian | main | 2026-11-28T04:25:16Z | 0.24 | failure | NEVER (prune candidate if dormant) |
| CI | fix/ingest-guards-and-labels-20261128 | 2026-11-28T04:06:58Z | 0.54 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (29 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Verification Tests @ fix/verification-origin-main-fetch — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- DB Sync: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- Branch Large File Duplicate Guard @ verify/self-hosted-routing — cadence 168.0h, expect resolution by 2026-12-10T09:40:45.658749+00:00
- DB Sync: findtorontoevents.ca  torontoevent.net @ verify/self-hosted-routing — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00
- ALPHA  Verify Predictions @ verify/self-hosted-routing — cadence 24.0h, expect resolution by 2026-11-28T09:40:45.658749+00:00

- resolved: Unified Audit Dashboard → **resolved_flapping**
- resolved: DB Freshness Guardian → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 0
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 2.41h running (p90 1.7h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 1
  - Claude's Test - Portfolio Manager — run 46092769222 killed at 317.0s mid-step `Commit updated state and dashboard` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 9 cancelled run(s) examined (9 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 1 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 7
  - external residual (7) — the true R7 signal, investigate:
    - run 46100090575 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-28T02:54:53Z (branch main)
    - run 46105984275 Secret Scan (M-043) — cancelled at 2026-11-28T04:07:07Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46105984287 Validation Gates (P0.0h) — cancelled at 2026-11-28T04:07:08Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46105984389 walkforward-gate — cancelled at 2026-11-28T04:07:08Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46105984324 DB Password Leak Guard — cancelled at 2026-11-28T04:07:09Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46105984328 Tribunal Runtime Gate — cancelled at 2026-11-28T04:07:18Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46105984266 CI Tests — cancelled at 2026-11-28T04:07:22Z (branch fix/ingest-guards-and-labels-20261128)
- **workflow_run fan-in chains:** 6
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.0 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (35 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Refresh Movies Databases (50webs + GoDaddy) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forex Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forward Ledger — daily sync [daily] — SKIPPED(budget): latest-run probe cap reached
  - fx-cost-overlap [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 1
  - Sign-Coherence Gate @ main — never passed in window, last failure 9999.0h ago

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **224** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
