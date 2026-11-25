# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-25T16:40:08.573783+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-17T16:40:08.573783+00:00 → 2026-11-25T16:40:08.573783+00:00 (1000 runs scanned, truncated=False; 386 workflows)
- **API budget:** 119/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Sidecar Status Markdown Update | main | 2026-11-25T16:37:36Z | 0.04 | failure | NEVER (prune candidate if dormant) |
| Update Creator News | main | 2026-11-25T16:36:56Z | 0.05 | failure | NEVER (prune candidate if dormant) |
| QA Market Validation | main | 2026-11-25T16:32:22Z | 0.13 | failure | yes |
| Low-Score Winner Tracker | main | 2026-11-25T16:29:22Z | 0.18 | failure | yes |
| portfolio-tracker | main | 2026-11-25T16:28:31Z | 0.19 | failure | NEVER (prune candidate if dormant) |
| Check Streamer Live Status | main | 2026-11-25T16:28:34Z | 0.19 | failure | yes |
| Feed Health Check | main | 2026-11-25T16:28:19Z | 0.2 | failure | NEVER (prune candidate if dormant) |
| Claude's Test - Portfolio Manager | main | 2026-11-25T16:28:07Z | 0.2 | failure | yes |
| Asset Class Freshness Watchdog | main | 2026-11-25T13:52:18Z | 2.8 | failure | NEVER (prune candidate if dormant) |
| audit3 ledger | main | 2026-11-25T13:27:01Z | 3.22 | failure | NEVER (prune candidate if dormant) |

_(+3 more in JSON)_

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (14 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Forward-Test New Strategies Tracker @ main — cadence 24.0h, expect resolution by 2026-11-26T13:42:09.012005+00:00
- CI Tests @ research/commodity-tsmom-v3-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-26T21:40:13.119473+00:00
- Sign-Coherence Gate @ main — cadence 24.0h, expect resolution by 2026-11-27T05:39:29.754198+00:00
- Update Creator News @ main — cadence 24.0h, expect resolution by 2026-11-27T13:53:07.020558+00:00
- What Worked Active Picks Insights @ main — cadence 24.0h, expect resolution by 2026-11-27T13:53:07.020558+00:00

- resolved: fx-cost-overlap → **resolved_flapping**
- resolved: Deploy Rise of the Claw Dashboard → **resolved_flapping**
- resolved: Claude's Test - Portfolio Manager → **escalated_still_broken**
- resolved: portfolio-tracker → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 332.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 332.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 332.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 332.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 332.07h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 5.19h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 14
  - 2hour-challenge — run 45612951752 killed at 1818.0s mid-step `Run 2-hour trading challenge` — timeout problem, not churn
  - realtime-challenge — run 45613514839 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45615363431 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45617112636 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45619719935 killed at 617.0s mid-step `Commit the ledger` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 16 cancelled run(s) examined (16 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 14 · eviction-shaped: 0 · stack-kill: 0 · pr-close: 0 · external: 2
  - external residual (2) — the true R7 signal, investigate:
    - run 45615258591 DNA Strategy Pipeline — cancelled at 2026-11-25T13:07:25Z (branch main)
    - run 45627899984 Deploy Rise of the Claw Dashboard — cancelled at 2026-11-25T13:51:51Z (branch main)
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
  - Edge stability refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - ETF Trend Forward Clock (month-end) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Refresh Movies Databases (50webs + GoDaddy) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Funding-Rate Archive Collector [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**3** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **192** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
