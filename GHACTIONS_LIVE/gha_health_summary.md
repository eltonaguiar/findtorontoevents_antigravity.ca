# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-25T08:40:54.088551+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-17T08:40:54.088551+00:00 → 2026-11-25T08:40:54.088551+00:00 (1000 runs scanned, truncated=False; 386 workflows)
- **API budget:** 125/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| portfolio-tracker | main | 2026-11-25T08:28:27Z | 0.21 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-25T07:26:10Z | 1.25 | failure | NEVER (prune candidate if dormant) |
| Sign-Coherence Gate | main | 2026-11-25T05:25:57Z | 3.25 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (9 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ ci/verification-test-gate — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ verify/claim-retirement — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ fix/peer-claim-b5-split-2026-11-23 — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ fix/peer-claim-verification-shallow-clone-2026-11-23 — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- Forward-Test New Strategies Tracker @ main — cadence 24.0h, expect resolution by 2026-11-26T13:42:09.012005+00:00

- resolved: portfolio-tracker → **escalated_still_broken**
- resolved: CI → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 324.08h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 324.08h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 324.08h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 324.08h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 324.08h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 3.07h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 15
  - realtime-challenge — run 45535375440 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45539290013 killed at 619.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45540848205 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45542361657 killed at 617.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45546147659 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 19 cancelled run(s) examined (19 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 15 · eviction-shaped: 0 · stack-kill: 0 · pr-close: 0 · external: 4
  - external residual (4) — the true R7 signal, investigate:
    - run 45547337036 DNA Strategy Pipeline — cancelled at 2026-11-25T05:02:46Z (branch main)
    - run 45563808822 realtime-challenge — cancelled at 2026-11-25T07:04:21Z (branch main)
    - run 45565206183 realtime-challenge — cancelled at 2026-11-25T07:14:39Z (branch main)
    - run 45561944035 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-25T08:30:57Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.0 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.6 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.2 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - ETF Trend Forward Clock (month-end) [weekly] — NEVER RUN with live trigger (weekly) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Growth Stock Screener Daily [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-103 Forward Logger [monthly] — SKIPPED(budget): latest-run probe cap reached
  - HC Evaluator Parity Test [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Hierarchical Bayesian Edge Update [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **221** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
