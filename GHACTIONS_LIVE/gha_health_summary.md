# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-16T20:39:18.854093+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-08T20:39:18.854093+00:00 → 2026-11-16T20:39:18.854093+00:00 (1000 runs scanned, truncated=False; 362 workflows)
- **API budget:** 148/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| CI Tests | main | 2026-11-16T20:37:52Z | 0.02 | failure | yes |
| CI Tests | fix/audit-pm-ingest-shadow-pin-2026-11-16 | 2026-11-16T20:35:41Z | 0.06 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/dashboard-cse-new-picks-int | 2026-11-16T20:32:36Z | 0.11 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/dashboard-audit-events-2026-11-16 | 2026-11-16T20:32:38Z | 0.11 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/audit-remaining-honesty | 2026-11-16T20:31:33Z | 0.13 | failure | NEVER (prune candidate if dormant) |
| CI Tests | tmp/s9-ghost-rootcause | 2026-11-16T20:30:40Z | 0.14 | failure | NEVER (prune candidate if dormant) |
| pages-build-deployment | gh-pages | 2026-11-16T20:26:48Z | 0.21 | failure | yes |
| QA Market Validation | main | 2026-11-16T20:24:53Z | 0.24 | failure | NEVER (prune candidate if dormant) |
| Feed Health Check | main | 2026-11-16T20:24:15Z | 0.25 | failure | yes |
| CI Tests | fix/audit-quant-fixes-2026-11-16 | 2026-11-16T20:14:32Z | 0.41 | failure | NEVER (prune candidate if dormant) |

_(+4 more in JSON)_

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (16 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ tmp/s2-emitters — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ tmp/s3-ci-hygiene — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ tmp/s1-data-gates — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- Unified Audit Dashboard @ main — cadence 24.0h, expect resolution by 2026-11-18T17:40:55.881294+00:00
- CI Tests @ main — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00

- resolved: CI Tests → **resolved_flapping**
- resolved: QA Market Validation → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 21
  - run 43095833399 Rapid Fire - NOW Scanner queued 2026-11-11T20:24:10Z (age 120.25h) — uncancelable ⇒ GitHub Support batch
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 120.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 120.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 120.05h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 120.05h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 2
  - Discord Bot  Persistent — 8.21h running (p90 n/a)
  - Claude Code Gainer ML Tracker — 0.33h running (p90 0.02h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 5
  - Copy Trader Intelligence  Scrape + Analyze + Track — run 43920712798 killed at 3018.0s mid-step `Commit all data changes` — timeout problem, not churn
  - Forward Trade Tracking v2 — run 43919189517 killed at 1817.0s mid-step `Commit stats` — timeout problem, not churn
  - ML Battleground System F (Claws of Doom) — run 43919925920 killed at 318.0s mid-step `Commit synced data` — timeout problem, not churn
  - Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities — run 43921935671 killed at 919.0s mid-step `Commit and push changes` — timeout problem, not churn
  - Test Portfolios  Hourly Strategy Validation — run 43907019983 killed at 608.0s mid-step `Run actions/checkout@v6` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 41 cancelled run(s) examined (30 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 5 · eviction-shaped: 10 · stack-kill: 8 · pr-close: 0 · external: 18
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 8 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (18) — the true R7 signal, investigate:
    - run 43903928567 Master Automation Scheduler — cancelled at 2026-11-16T16:08:07Z (branch main)
    - run 43908458865 DNA Strategy Pipeline — cancelled at 2026-11-16T17:03:14Z (branch main)
    - run 43915470974 DB Password Leak Guard — cancelled at 2026-11-16T17:10:25Z (branch fix/audit-truth-layer-2026-11-16)
    - run 43915470846 Conflict Marker Check — cancelled at 2026-11-16T17:10:26Z (branch fix/audit-truth-layer-2026-11-16)
    - run 43915470921 No stale DB passwords — cancelled at 2026-11-16T17:10:26Z (branch fix/audit-truth-layer-2026-11-16)
    - run 43915470942 CI Tests — cancelled at 2026-11-16T17:10:28Z (branch fix/audit-truth-layer-2026-11-16)
    - run 43919287739 Quant Auditor (fast PR check) — cancelled at 2026-11-16T17:31:59Z (branch tmp/s1-data-gates)
    - run 43919288007 Conflict Marker Check — cancelled at 2026-11-16T17:32:00Z (branch tmp/s1-data-gates)
    - run 43919287828 DB Password Leak Guard — cancelled at 2026-11-16T17:32:00Z (branch tmp/s1-data-gates)
    - run 43919365915 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-16T17:35:51Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.1 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (25 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - ETF Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ETF & Bond Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Refresh Movies Databases (50webs + GoDaddy) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**1** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **264** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
