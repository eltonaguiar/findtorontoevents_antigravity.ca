# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-24T16:40:05.235883+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-16T16:40:05.235883+00:00 → 2026-11-24T16:40:05.235883+00:00 (1000 runs scanned, truncated=False; 385 workflows)
- **API budget:** 135/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| QA Market Validation | main | 2026-11-24T16:30:14Z | 0.16 | failure | yes |
| portfolio-tracker | main | 2026-11-24T16:26:54Z | 0.22 | failure | NEVER (prune candidate if dormant) |
| fx-cost-overlap | main | 2026-11-24T16:26:46Z | 0.22 | failure | yes |
| Forward-Test New Strategies Tracker | main | 2026-11-24T13:23:57Z | 3.27 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (10 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Audit Frontend Manifest @ push/phase2-round-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-25T01:53:20.923766+00:00
- CI Tests @ ci/verification-test-gate — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ verify/claim-retirement — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ fix/peer-claim-b5-split-2026-11-23 — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ fix/peer-claim-verification-shallow-clone-2026-11-23 — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00

- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: Deploy Rise of the Claw Dashboard → **resolved_flapping**
- resolved: portfolio-tracker → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 308.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 308.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 308.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 308.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 308.07h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 10.28h running (p90 0.32h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 19
  - 2hour-challenge — run 45392712983 killed at 1817.0s mid-step `Run 2-hour trading challenge` — timeout problem, not churn
  - Claude's Test - Portfolio Manager — run 45407705261 killed at 308.0s mid-step `Fetch prior portfolio state from production` — timeout problem, not churn
  - Kalshi snapshot (sports markets cache) — run 45394371335 killed at 1220.0s mid-step `Commit snapshot (only when changed)` — timeout problem, not churn
  - realtime-challenge — run 45382853194 killed at 619.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45385129627 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 24 cancelled run(s) examined (24 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 19 · eviction-shaped: 2 · stack-kill: 0 · pr-close: 0 · external: 3
  - external residual (3) — the true R7 signal, investigate:
    - run 45394946619 DNA Strategy Pipeline — cancelled at 2026-11-24T13:06:52Z (branch main)
    - run 45430333989 Deploy Rise of the Claw Dashboard — cancelled at 2026-11-24T15:51:49Z (branch main)
    - run 45433442118 Master Automation Scheduler — cancelled at 2026-11-24T16:08:25Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.0 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
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

**1** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **204** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
