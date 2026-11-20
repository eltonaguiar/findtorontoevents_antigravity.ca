# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-20T04:39:20.963153+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-12T04:39:20.963153+00:00 → 2026-11-20T04:39:20.963153+00:00 (1000 runs scanned, truncated=False; 374 workflows)
- **API budget:** 133/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Sign-Coherence Gate | main | 2026-11-20T04:38:57Z | 0.01 | failure | NEVER (prune candidate if dormant) |
| QA Market Validation | main | 2026-11-20T04:28:16Z | 0.18 | failure | NEVER (prune candidate if dormant) |
| CI Tests | feat/audit2-data-driven-pods | 2026-11-20T01:55:01Z | 2.74 | failure | NEVER (prune candidate if dormant) |
| CI Tests | feat/pod-emission-audit | 2026-11-20T01:46:05Z | 2.89 | failure | NEVER (prune candidate if dormant) |
| pod emission audit | feat/pod-emission-audit | 2026-11-20T01:41:17Z | 2.97 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/wire-emitting-pods | 2026-11-20T01:27:41Z | 3.19 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-20T01:23:24Z | 3.27 | failure | NEVER (prune candidate if dormant) |
| CI Tests | test/audit3-ledger-e2e-canary | 2026-11-20T00:53:15Z | 3.77 | failure | NEVER (prune candidate if dormant) |
| CI Tests | test/audit3-cli-smoke | 2026-11-20T00:19:01Z | 4.34 | failure | NEVER (prune candidate if dormant) |
| CI Tests | hotfix/restore-denylist-hits | 2026-11-20T00:09:31Z | 4.5 | failure | NEVER (prune candidate if dormant) |

_(+1 more in JSON)_

## 2. FLAPPING (watch list + failing steps)

| Workflow | Branch | Fails/15 | Failing steps | Infra vs bug |
|---|---|---|---|---|
| CI Tests | main | 9/15 | Run all tests (gating — known-drift quarantined) | infra 0 / bug 4 |

**R2 monitor-next-run (27 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ feat/forward-gate-and-ingest — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/forward-observations-contract — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ fix/h119-vintage-and-kill-list-reconcile — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ fix/verdict-fixtures-and-key-redaction — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/wr-semantics-measured-cost-timeline — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00

- resolved: CI Tests → **resolved_flapping**
- resolved: QA Market Validation → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 200.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 200.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 200.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 200.05h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 200.05h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 2.02h running (p90 2.1h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 4
  - Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities — run 44649247726 killed at 922.0s mid-step `Commit and push changes` — timeout problem, not churn
  - Winner Pattern Precursor Scanner — run 44667852631 killed at 618.0s mid-step `Commit results` — timeout problem, not churn
  - Winner Pattern Precursor Scanner — run 44670694584 killed at 617.0s mid-step `Commit results` — timeout problem, not churn
  - [torontoevent.net] Deploy Competition to Live Site — run 44667773635 killed at 1817.0s mid-step `Deploy competition files to *** via FTP` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 22 cancelled run(s) examined (22 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 4 · eviction-shaped: 3 · stack-kill: 0 · pr-close: 0 · external: 15
  - external residual (15) — the true R7 signal, investigate:
    - run 44648181788 DNA Strategy Pipeline — cancelled at 2026-11-20T01:15:18Z (branch main)
    - run 44656026599 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-20T01:51:06Z (branch main)
    - run 44656584273 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-20T01:55:37Z (branch main)
    - run 44658439347 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-20T02:08:56Z (branch main)
    - run 44660139971 CI Tests — cancelled at 2026-11-20T02:24:00Z (branch fix/audit3-main-greens-20261120)
    - run 44660466237 walkforward-gate — cancelled at 2026-11-20T02:24:25Z (branch fix/audit3-main-greens-20261120)
    - run 44660466244 Secret Scan (M-043) — cancelled at 2026-11-20T02:24:25Z (branch fix/audit3-main-greens-20261120)
    - run 44660466272 CI Tests — cancelled at 2026-11-20T02:24:25Z (branch fix/audit3-main-greens-20261120)
    - run 44652055937 ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds — cancelled at 2026-11-20T02:36:26Z (branch main)
    - run 44667313626 walkforward-gate — cancelled at 2026-11-20T03:23:55Z (branch fix/audit3-publish-split-and-sleeve-gate)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.1 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.2 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Futures Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
  - GHA scan job (reusable) [unknown] — SKIPPED(budget): latest-run probe cap reached
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**4** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **294** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
