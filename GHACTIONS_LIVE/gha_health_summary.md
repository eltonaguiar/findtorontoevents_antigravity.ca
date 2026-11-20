# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-20T08:40:08.060818+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-12T08:40:08.060818+00:00 → 2026-11-20T08:40:08.060818+00:00 (1000 runs scanned, truncated=False; 375 workflows)
- **API budget:** 109/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| QA Market Validation | main | 2026-11-20T08:28:29Z | 0.19 | failure | NEVER (prune candidate if dormant) |
| Unified Audit Dashboard | main | 2026-11-20T07:32:03Z | 1.13 | failure | yes |
| Unified Audit Dashboard | docs/correct-dashboard-cadence | 2026-11-20T07:31:20Z | 1.15 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-20T07:25:51Z | 1.24 | failure | NEVER (prune candidate if dormant) |
| Sign-Coherence Gate | main | 2026-11-20T05:24:43Z | 3.26 | failure | NEVER (prune candidate if dormant) |

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
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 204.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 204.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 204.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 204.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 204.07h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 0
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 4
  - Incubator Pipeline  Strategy Graduation — run 44690856732 killed at 1820.0s mid-step `Commit results` — timeout problem, not churn
  - Kalshi snapshot (sports markets cache) — run 44688769785 killed at 1220.0s mid-step `Commit snapshot (only when changed)` — timeout problem, not churn
  - Picks-Now Live PnL (hourly) — run 44695102109 killed at 918.0s mid-step `Push data commit` — timeout problem, not churn
  - Winner Pattern Precursor Scanner — run 44670694584 killed at 617.0s mid-step `Commit results` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 11 cancelled run(s) examined (11 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 4 · eviction-shaped: 3 · stack-kill: 0 · pr-close: 0 · external: 4
  - external residual (4) — the true R7 signal, investigate:
    - run 44670591217 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-20T03:54:36Z (branch main)
    - run 44677226988 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-20T04:56:22Z (branch main)
    - run 44674892372 DNA Strategy Pipeline — cancelled at 2026-11-20T05:02:13Z (branch main)
    - run 44689808142 ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds — cancelled at 2026-11-20T07:59:09Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.0 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.2 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Honest Kill Switch [daily] — SKIPPED(budget): latest-run probe cap reached
  - Hyro daily (filter + backtest) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Insider Trades Refresh [weekly] — SKIPPED(budget): latest-run probe cap reached
  - macd_rsi_m048 Shadow Generator [daily] — SKIPPED(budget): latest-run probe cap reached
  - Mercury 2  Weekly Retrain [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ML Feedback Retrain  Learn from Closed Trades [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **303** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
