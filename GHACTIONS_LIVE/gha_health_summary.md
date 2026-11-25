# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-25T00:57:42.674390+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-17T00:57:42.674390+00:00 → 2026-11-25T00:57:42.674390+00:00 (1000 runs scanned, truncated=False; 386 workflows)
- **API budget:** 134/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| .github/workflows/validation-gates.yml | coverage-and-verdict-tooling-2026-11-24 | 2026-11-25T00:21:42Z | 0.6 | failure | NEVER (prune candidate if dormant) |
| portfolio-tracker | main | 2026-11-24T23:52:31Z | 1.09 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (9 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Audit Frontend Manifest @ push/phase2-round-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-25T01:53:20.923766+00:00
- CI Tests @ ci/verification-test-gate — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ verify/claim-retirement — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ fix/peer-claim-b5-split-2026-11-23 — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ fix/peer-claim-verification-shallow-clone-2026-11-23 — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00

- resolved: QA Market Validation → **resolved_flapping**
- resolved: portfolio-tracker → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 316.36h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 316.36h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 316.36h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 316.36h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 316.36h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 0
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 10
  - Meta-Strategy Permutation Engine — run 45506251744 killed at 1817.0s mid-step `Commit results` — timeout problem, not churn
  - realtime-challenge — run 45481834144 killed at 617.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45484314873 killed at 620.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45489595905 killed at 619.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45492072484 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 23 cancelled run(s) examined (23 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 10 · eviction-shaped: 2 · stack-kill: 1 · pr-close: 0 · external: 10
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 1 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (10) — the true R7 signal, investigate:
    - run 45475323063 provenance-verify — cancelled at 2026-11-24T20:10:32Z (branch main)
    - run 45481655831 DNA Strategy Pipeline — cancelled at 2026-11-24T21:02:58Z (branch main)
    - run 45485896761 provenance-verify — cancelled at 2026-11-24T21:11:06Z (branch main)
    - run 45490521512 Deploy Rise of the Claw Dashboard — cancelled at 2026-11-24T21:51:45Z (branch main)
    - run 45480855315 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-24T22:26:24Z (branch main)
    - run 45505627505 No stale DB passwords — cancelled at 2026-11-24T22:57:31Z (branch main)
    - run 45505627457 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-24T22:57:32Z (branch main)
    - run 45505627365 provenance-verify — cancelled at 2026-11-24T23:12:11Z (branch main)
    - run 45502741167 ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds — cancelled at 2026-11-24T23:43:35Z (branch main)
    - run 45500899325 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-25T00:45:27Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.8 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 2
  - Pine Script Generator — skip ratio 1.0 — perpetual skip: dead code / broken filter (if: always false or paths never match)
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - ETF Trend Forward Clock (month-end) [weekly] — NEVER RUN with live trigger (weekly) — dead trigger or broken filter
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - FRED Macro Refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - fx-cost-overlap [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**4** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **217** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
