# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-24T20:40:13.119473+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-16T20:40:13.119473+00:00 → 2026-11-24T20:40:13.119473+00:00 (1000 runs scanned, truncated=False; 385 workflows)
- **API budget:** 129/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| QA Market Validation | main | 2026-11-24T20:24:36Z | 0.26 | failure | NEVER (prune candidate if dormant) |
| portfolio-tracker | main | 2026-11-24T20:23:29Z | 0.28 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-24T19:24:04Z | 1.27 | failure | NEVER (prune candidate if dormant) |
| CI Tests | research/commodity-tsmom-v3-2026-11-22 | 2026-11-24T17:51:22Z | 2.81 | failure | NEVER (prune candidate if dormant) |
| fx-cost-overlap | main | 2026-11-24T16:52:46Z | 3.79 | failure | yes |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (10 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Audit Frontend Manifest @ push/phase2-round-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-25T01:53:20.923766+00:00
- CI Tests @ ci/verification-test-gate — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ verify/claim-retirement — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ fix/peer-claim-b5-split-2026-11-23 — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ fix/peer-claim-verification-shallow-clone-2026-11-23 — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00

- resolved: Kalshi snapshot (sports markets cache) → **resolved_flapping**
- resolved: QA Market Validation → **escalated_still_broken**
- resolved: portfolio-tracker → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 312.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 312.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 312.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 312.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 312.07h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 2.77h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 15
  - realtime-challenge — run 45421014039 killed at 619.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45423935865 killed at 620.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45426716930 killed at 620.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45429556490 killed at 620.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45432773328 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 21 cancelled run(s) examined (21 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 15 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 5
  - external residual (5) — the true R7 signal, investigate:
    - run 45430333989 Deploy Rise of the Claw Dashboard — cancelled at 2026-11-24T15:51:49Z (branch main)
    - run 45433442118 Master Automation Scheduler — cancelled at 2026-11-24T16:08:25Z (branch main)
    - run 45438077833 DNA Strategy Pipeline — cancelled at 2026-11-24T17:02:56Z (branch main)
    - run 45475323063 provenance-verify — cancelled at 2026-11-24T20:10:32Z (branch main)
    - run 45459977686 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-24T20:26:53Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.8 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Edge stability refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Equities & Stocks Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ETF Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ETF & Bond Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Refresh Movies Databases (50webs + GoDaddy) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **205** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
