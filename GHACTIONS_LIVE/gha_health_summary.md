# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-28T12:39:53.254853+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-20T12:39:53.254853+00:00 → 2026-11-28T12:39:53.254853+00:00 (1000 runs scanned, truncated=False; 400 workflows)
- **API budget:** 103/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| DB Freshness Guardian | main | 2026-11-28T12:27:54Z | 0.2 | failure | NEVER (prune candidate if dormant) |
| CI | fix/ingest-guards-and-labels-20261128 | 2026-11-28T08:09:07Z | 4.51 | failure | NEVER (prune candidate if dormant) |
| DB Sync: findtorontoevents.ca  torontoevent.net | main | 2026-11-28T07:54:53Z | 4.75 | failure | NEVER (prune candidate if dormant) |
| Refresh Movies Databases (50webs + GoDaddy) | main | 2026-11-28T07:53:44Z | 4.77 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (17 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Branch Large File Duplicate Guard @ verify/self-hosted-routing — cadence 168.0h, expect resolution by 2026-12-10T09:40:45.658749+00:00
- H-002 PEAD Shadow Collector @ verify/self-hosted-routing — cadence 168.0h, expect resolution by 2026-12-10T09:40:45.658749+00:00
- Algorithm Competition Refresh @ verify/self-hosted-routing — cadence 168.0h, expect resolution by 2026-12-10T09:40:45.658749+00:00
- audit3 evidence registry @ verify/self-hosted-routing — cadence 168.0h, expect resolution by 2026-12-10T09:40:45.658749+00:00
- Sign-Coherence Gate @ main — cadence 24.0h, expect resolution by 2026-11-29T05:39:47.825283+00:00

- resolved: Verification Tests → **escalated_scheduler_dead**
- resolved: DB Sync: findtorontoevents.ca  torontoevent.net → **escalated_still_broken**
- resolved: DB Sync: findtorontoevents.ca  torontoevent.net → **escalated_scheduler_dead**
- resolved: ALPHA  Verify Predictions → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 0
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 4.57h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 1
  - Meme Coin Scanner v2  Fixed & Monitored — run 46124178695 killed at 317.0s mid-step `Deploy meme_scanner_fixed.php to server` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 18 cancelled run(s) examined (18 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 1 · eviction-shaped: 2 · stack-kill: 4 · pr-close: 0 · external: 11
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 4 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (11) — the true R7 signal, investigate:
    - run 46124441990 DB Password Leak Guard — cancelled at 2026-11-28T08:09:13Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46124441982 masking-policy-lint — cancelled at 2026-11-28T08:09:13Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46124441951 walkforward-gate — cancelled at 2026-11-28T08:09:13Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46124442024 Conflict Marker Check — cancelled at 2026-11-28T08:09:13Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46124441938 Secret Scan (M-043) — cancelled at 2026-11-28T08:09:13Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46124442003 No stale DB passwords — cancelled at 2026-11-28T08:09:13Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46124441969 Tribunal Runtime Gate — cancelled at 2026-11-28T08:09:13Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46124441949 CI Tests — cancelled at 2026-11-28T08:09:14Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46124441995 Quant Auditor (fast PR check) — cancelled at 2026-11-28T08:09:14Z (branch fix/ingest-guards-and-labels-20261128)
    - run 46124442007 Validation Gates (P0.0h) — cancelled at 2026-11-28T08:09:14Z (branch fix/ingest-guards-and-labels-20261128)
- **workflow_run fan-in chains:** 6
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.0 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (35 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - ETF & Bond Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ETF Trend Forward Clock (month-end) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forex Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forward Ledger — daily sync [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**3** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **213** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
