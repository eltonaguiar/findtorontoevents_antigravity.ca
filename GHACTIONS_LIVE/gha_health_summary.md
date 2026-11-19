# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-19T04:40:13.044746+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-11T04:40:13.044746+00:00 → 2026-11-19T04:40:13.044746+00:00 (1000 runs scanned, truncated=False; 365 workflows)
- **API budget:** 99/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Sign-Coherence Gate | main | 2026-11-19T04:39:13Z | 0.02 | failure | NEVER (prune candidate if dormant) |
| QA Market Validation | main | 2026-11-19T04:26:15Z | 0.23 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (2 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Sign-Coherence Gate @ main — cadence 24.0h, expect resolution by 2026-11-19T05:39:52.849857+00:00
- QA Market Validation @ main — cadence 1.0h, expect resolution by 2026-11-19T07:40:13.044746+00:00

- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: QA Market Validation → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 176.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 176.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 176.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 176.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 176.07h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 0
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 1
  - Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities — run 44446715673 killed at 918.0s mid-step `Commit and push changes` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 6 cancelled run(s) examined (6 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 1 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 4
  - external residual (4) — the true R7 signal, investigate:
    - run 44434869118 CI Tests — cancelled at 2026-11-19T01:12:05Z (branch bestiejob-page-tests)
    - run 44431554335 DNA Strategy Pipeline — cancelled at 2026-11-19T01:16:53Z (branch main)
    - run 44435172045 Deploy BESTIEJOB page — cancelled at 2026-11-19T01:19:07Z (branch main)
    - run 44436423449 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-19T01:24:30Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.4 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.6 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Growth Stock Screener Daily [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-103 Forward Logger [monthly] — SKIPPED(budget): latest-run probe cap reached
  - HC Evaluator Parity Test [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Hyro Quan Bridge Regen [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**4** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **237** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
