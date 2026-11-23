# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-23T16:40:07.525576+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-15T16:40:07.525576+00:00 → 2026-11-23T16:40:07.525576+00:00 (1000 runs scanned, truncated=False; 385 workflows)
- **API budget:** 125/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| QA Market Validation | main | 2026-11-23T16:28:18Z | 0.2 | failure | yes |
| portfolio-tracker | main | 2026-11-23T16:25:13Z | 0.25 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-23T13:25:58Z | 3.24 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (17 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ research/per-class-edge-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ buffy/verify-live-claim-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ fix/dsr-skip-contract — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ fix/dsr-nbtrials-floor — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- Forward-Test New Strategies Tracker @ main — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00

- resolved: portfolio-tracker → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 284.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 284.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 284.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 284.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 284.07h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 4.08h running (p90 0.24h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 16
  - 2hour-challenge — run 45173463422 killed at 1817.0s mid-step `Run 2-hour trading challenge` — timeout problem, not churn
  - Dashboard Pick Trader — run 45167505616 killed at 617.0s mid-step `Commit portfolio changes` — timeout problem, not churn
  - LuxAlgo Signal Generator — run 45167544839 killed at 918.0s mid-step `Commit picks` — timeout problem, not churn
  - Mega Mutation Live Tracker — run 45207478013 killed at 607.0s mid-step `Set up Python` — timeout problem, not churn
  - crypto intraday sim — run 45167479226 killed at 618.0s mid-step `Commit sim state + forward ledger (data only, [skip ci])` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 19 cancelled run(s) examined (19 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 16 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 2
  - external residual (2) — the true R7 signal, investigate:
    - run 45164380617 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-23T11:23:02Z (branch main)
    - run 45175735891 DNA Strategy Pipeline — cancelled at 2026-11-23T13:07:00Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.8 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Funding-Rate Archive Collector [daily] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
  - GHA scan job (reusable) [unknown] — SKIPPED(budget): latest-run probe cap reached
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Goldmine Tracker - Archive & Maintain [daily] — SKIPPED(budget): latest-run probe cap reached
  - H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**3** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **227** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
