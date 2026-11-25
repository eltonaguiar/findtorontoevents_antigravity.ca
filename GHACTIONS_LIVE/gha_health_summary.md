# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-25T04:39:29.754198+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-17T04:39:29.754198+00:00 → 2026-11-25T04:39:29.754198+00:00 (1000 runs scanned, truncated=False; 386 workflows)
- **API budget:** 137/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| portfolio-tracker | main | 2026-11-25T04:26:29Z | 0.22 | failure | NEVER (prune candidate if dormant) |
| CI | main | 2026-11-25T04:26:19Z | 0.22 | failure | yes |
| .github/workflows/validation-gates.yml | coverage-and-verdict-tooling-2026-11-24 | 2026-11-25T02:05:27Z | 2.57 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-25T01:24:54Z | 3.24 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (10 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ ci/verification-test-gate — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ verify/claim-retirement — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ fix/peer-claim-b5-split-2026-11-23 — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- CI Tests @ fix/peer-claim-verification-shallow-clone-2026-11-23 — cadence 24.0h, expect resolution by 2026-11-25T09:41:26.404040+00:00
- Forward-Test New Strategies Tracker @ main — cadence 24.0h, expect resolution by 2026-11-26T13:42:09.012005+00:00

- resolved: Audit Frontend Manifest → **escalated_scheduler_dead**
- resolved: portfolio-tracker → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 320.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 320.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 320.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 320.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 320.06h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 4.9h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 16
  - Meta-Strategy Permutation Engine — run 45506251744 killed at 1817.0s mid-step `Commit results` — timeout problem, not churn
  - Winner Pattern Precursor Scanner — run 45525610286 killed at 619.0s mid-step `Commit results` — timeout problem, not churn
  - realtime-challenge — run 45504242969 killed at 620.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45510772420 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45512740533 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 25 cancelled run(s) examined (25 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 16 · eviction-shaped: 2 · stack-kill: 1 · pr-close: 0 · external: 6
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 1 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (6) — the true R7 signal, investigate:
    - run 45505627505 No stale DB passwords — cancelled at 2026-11-24T22:57:31Z (branch main)
    - run 45505627457 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-24T22:57:32Z (branch main)
    - run 45505627365 provenance-verify — cancelled at 2026-11-24T23:12:11Z (branch main)
    - run 45522888910 realtime-challenge — cancelled at 2026-11-25T01:15:31Z (branch main)
    - run 45520656914 DNA Strategy Pipeline — cancelled at 2026-11-25T01:17:40Z (branch main)
    - run 45533174589 Deploy Rise of the Claw Dashboard — cancelled at 2026-11-25T02:28:29Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.0 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - ETF Trend Forward Clock (month-end) [weekly] — NEVER RUN with live trigger (weekly) — dead trigger or broken filter
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - fx-cost-overlap [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 1
  - Sign-Coherence Gate @ main — never passed in window, last failure 9999.0h ago

## 5. NOT AN ISSUE (recovered) — suppressed count

**3** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **209** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
