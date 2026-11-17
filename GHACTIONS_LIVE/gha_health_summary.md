# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-17T20:39:35.275385+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-09T20:39:35.275385+00:00 → 2026-11-17T20:39:35.275385+00:00 (1000 runs scanned, truncated=False; 362 workflows)
- **API budget:** 99/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| QA Market Validation | main | 2026-11-17T20:25:52Z | 0.23 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (15 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ tmp/s2-emitters — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ tmp/s3-ci-hygiene — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ tmp/s1-data-gates — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ fix/audit-pm-ingest-shadow-pin-2026-11-16 — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00
- CI Tests @ fix/dashboard-cse-new-picks-int — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00

- resolved: QA Market Validation → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 144.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 144.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 144.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 144.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 144.06h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 4.49h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 3
  - Breakout Arena  3 Approaches — run 44130916053 killed at 1205.0s mid-step `Run actions/checkout@v6` — timeout problem, not churn
  - Dashboard Pick Trader — run 44161272601 killed at 606.0s mid-step `Checkout repository` — timeout problem, not churn
  - crypto-ohlcv refresh — run 44131419315 killed at 1506.0s mid-step `Checkout` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 6 cancelled run(s) examined (6 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 3 · eviction-shaped: 0 · stack-kill: 0 · pr-close: 0 · external: 3
  - external residual (3) — the true R7 signal, investigate:
    - run 44126760101 DNA Strategy Pipeline — cancelled at 2026-11-17T17:03:21Z (branch main)
    - run 44165806449 Master Automation Scheduler — cancelled at 2026-11-17T20:07:14Z (branch main)
    - run 44148354343 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-17T20:27:01Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.5 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.6 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (25 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Edge stability refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Edge stability refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Equities & Stocks Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Refresh Movies Databases (50webs + GoDaddy) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**1** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **180** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
