# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-21T00:49:17.607614+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-13T00:49:17.607614+00:00 → 2026-11-21T00:49:17.607614+00:00 (1000 runs scanned, truncated=False; 376 workflows)
- **API budget:** 121/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| QA Market Validation | main | 2026-11-21T00:44:31Z | 0.08 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (29 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ feat/forward-gate-and-ingest — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/forward-observations-contract — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ fix/h119-vintage-and-kill-list-reconcile — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ fix/verdict-fixtures-and-key-redaction — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/wr-semantics-measured-cost-timeline — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00

- resolved: QA Market Validation → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 220.22h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 220.22h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 220.22h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 220.22h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 220.22h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 2
  - Discord Bot  Persistent — 4.64h running (p90 n/a)
  - Unified Audit Dashboard — 0.96h running (p90 0.06h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 4
  - Claude's Test - Portfolio Manager — run 44845354775 killed at 317.0s mid-step `Commit updated state and dashboard` — timeout problem, not churn
  - Forward Signal Scanner — run 44814410542 killed at 1818.0s mid-step `Commit results` — timeout problem, not churn
  - Meta-Strategy Permutation Engine — run 44833656297 killed at 1817.0s mid-step `Commit results` — timeout problem, not churn
  - Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities — run 44814407532 killed at 917.0s mid-step `Commit and push changes` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 17 cancelled run(s) examined (17 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 4 · eviction-shaped: 1 · stack-kill: 2 · pr-close: 0 · external: 10
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 2 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (10) — the true R7 signal, investigate:
    - run 44805526889 Tribunal Runtime Gate — cancelled at 2026-11-20T19:48:33Z (branch deploy-lease-financial-surfaces-20261120)
    - run 44805526733 No stale DB passwords — cancelled at 2026-11-20T19:48:33Z (branch deploy-lease-financial-surfaces-20261120)
    - run 44805526680 Conflict Marker Check — cancelled at 2026-11-20T19:48:34Z (branch deploy-lease-financial-surfaces-20261120)
    - run 44805526697 Secret Scan (M-043) — cancelled at 2026-11-20T19:48:35Z (branch deploy-lease-financial-surfaces-20261120)
    - run 44808299634 Master Automation Scheduler — cancelled at 2026-11-20T20:07:10Z (branch main)
    - run 44810874228 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-20T20:25:04Z (branch main)
    - run 44812153689 DNA Strategy Pipeline — cancelled at 2026-11-20T21:02:55Z (branch main)
    - run 44814098925 Cross-System Signal Aggregator — cancelled at 2026-11-20T21:15:27Z (branch main)
    - run 44811398292 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-20T22:26:33Z (branch main)
    - run 44845194204 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-21T00:41:59Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 5.1 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - forward observations ingest [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forward-Test New Strategies Tracker [daily] — SKIPPED(budget): latest-run probe cap reached
  - FRED Macro Refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Funding-Rate Archive Collector [daily] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **268** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
