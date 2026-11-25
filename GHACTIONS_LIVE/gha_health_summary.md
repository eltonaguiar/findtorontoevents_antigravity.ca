# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-25T12:53:07.020558+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-17T12:53:07.020558+00:00 → 2026-11-25T12:53:07.020558+00:00 (1000 runs scanned, truncated=False; 386 workflows)
- **API budget:** 121/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Update Creator News | main | 2026-11-25T12:52:46Z | 0.01 | failure | yes |
| Deploy Rise of the Claw Dashboard | main | 2026-11-25T12:33:47Z | 0.32 | failure | yes |
| Claude's Test - Portfolio Manager | main | 2026-11-25T12:31:16Z | 0.36 | failure | yes |
| portfolio-tracker | main | 2026-11-25T11:52:43Z | 1.01 | failure | NEVER (prune candidate if dormant) |
| What Worked Active Picks Insights | main | 2026-11-25T12:52:50Z | 9999.0 | failure | yes |
| Feed Health Check | main | 2026-11-25T12:53:08Z | 9999.0 | failure | yes |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (10 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Forward-Test New Strategies Tracker @ main — cadence 24.0h, expect resolution by 2026-11-26T13:42:09.012005+00:00
- fx-cost-overlap @ main — cadence 168.0h, expect resolution by 2026-12-08T17:40:05.235883+00:00
- CI Tests @ research/commodity-tsmom-v3-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-26T21:40:13.119473+00:00
- Sign-Coherence Gate @ main — cadence 24.0h, expect resolution by 2026-11-27T05:39:29.754198+00:00
- Update Creator News @ main — cadence 24.0h, expect resolution by 2026-11-27T13:53:07.020558+00:00

- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: portfolio-tracker → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 328.29h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 328.29h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 328.29h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 328.28h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 328.28h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 0
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 14
  - 2hour-challenge — run 45612951752 killed at 1818.0s mid-step `Run 2-hour trading challenge` — timeout problem, not churn
  - realtime-challenge — run 45567281496 killed at 617.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45568916214 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45570872675 killed at 617.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45575753893 killed at 619.0s mid-step `Commit the ledger` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 17 cancelled run(s) examined (17 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 14 · eviction-shaped: 0 · stack-kill: 0 · pr-close: 0 · external: 3
  - external residual (3) — the true R7 signal, investigate:
    - run 45565206183 realtime-challenge — cancelled at 2026-11-25T07:14:39Z (branch main)
    - run 45577220514 DNA Strategy Pipeline — cancelled at 2026-11-25T09:04:37Z (branch main)
    - run 45585173979 Deploy Rise of the Claw Dashboard — cancelled at 2026-11-25T09:51:50Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.0 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.6 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - ETF Trend Forward Clock (month-end) [weekly] — NEVER RUN with live trigger (weekly) — dead trigger or broken filter
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Funding-Rate Archive Collector [daily] — SKIPPED(budget): latest-run probe cap reached
  - Futures Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - fx-cost-overlap [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **193** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
