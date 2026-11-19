# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-19T08:40:05.005316+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-11T08:40:05.005316+00:00 → 2026-11-19T08:40:05.005316+00:00 (1000 runs scanned, truncated=False; 367 workflows)
- **API budget:** 137/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| CI Tests | main | 2026-11-19T08:33:12Z | 0.11 | failure | yes |
| QA Market Validation | main | 2026-11-19T08:30:01Z | 0.17 | failure | NEVER (prune candidate if dormant) |
| GHCOPILOT prospective paper monitor | main | 2026-11-19T08:28:33Z | 0.19 | failure | yes |
| CI Tests | feat/forward-gate-and-ingest | 2026-11-19T07:28:12Z | 1.2 | failure | NEVER (prune candidate if dormant) |
| CI Tests | feat/forward-observations-contract | 2026-11-19T06:52:54Z | 1.79 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/h119-vintage-and-kill-list-reconcile | 2026-11-19T06:49:49Z | 1.84 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/verdict-fixtures-and-key-redaction | 2026-11-19T06:27:50Z | 2.2 | failure | NEVER (prune candidate if dormant) |
| CI Tests | feat/wr-semantics-measured-cost-timeline | 2026-11-19T06:17:45Z | 2.37 | failure | NEVER (prune candidate if dormant) |
| CI Tests | feat/audit3-canonical-denominator-and-gates | 2026-11-19T06:09:02Z | 2.52 | failure | NEVER (prune candidate if dormant) |
| CI Tests | feat/audit3-class-gate-pods | 2026-11-19T05:52:09Z | 2.8 | failure | NEVER (prune candidate if dormant) |

_(+2 more in JSON)_

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (12 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ main — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- QA Market Validation @ main — cadence 1.0h, expect resolution by 2026-11-19T11:40:05.005316+00:00
- GHCOPILOT prospective paper monitor @ main — cadence 1.0h, expect resolution by 2026-11-19T11:40:05.005316+00:00
- CI Tests @ feat/forward-gate-and-ingest — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/forward-observations-contract — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00

- resolved: Sign-Coherence Gate → **escalated_still_broken**
- resolved: QA Market Validation → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 180.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 180.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 180.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 180.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 180.07h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 5.42h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 0
- **CANCEL BUCKETS (R7)** — 25 cancelled run(s) examined (25 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 0 · eviction-shaped: 7 · stack-kill: 6 · pr-close: 0 · external: 12
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 6 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (12) — the true R7 signal, investigate:
    - run 44460651455 CI Tests — cancelled at 2026-11-19T04:54:20Z (branch main)
    - run 44461407293 No stale DB passwords — cancelled at 2026-11-19T04:58:46Z (branch audit3-innocent-until-proven-guilty)
    - run 44458809493 DNA Strategy Pipeline — cancelled at 2026-11-19T05:02:11Z (branch main)
    - run 44464524679 No stale DB passwords — cancelled at 2026-11-19T05:21:06Z (branch docs/finance-db-schema)
    - run 44464524612 Conflict Marker Check — cancelled at 2026-11-19T05:21:07Z (branch docs/finance-db-schema)
    - run 44465389091 CI Tests — cancelled at 2026-11-19T05:33:44Z (branch main)
    - run 44466605847 walkforward-gate — cancelled at 2026-11-19T05:40:23Z (branch feat/audit3-emission-denylist)
    - run 44467436686 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-19T05:51:52Z (branch main)
    - run 44470416398 Money-Ready Registry Gate — cancelled at 2026-11-19T06:12:00Z (branch feat/wr-semantics-measured-cost-timeline)
    - run 44470416430 No stale DB passwords — cancelled at 2026-11-19T06:17:00Z (branch feat/wr-semantics-measured-cost-timeline)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 5.0 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.2 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.2 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Hyro daily (filter + backtest) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Insider Trades Refresh [weekly] — SKIPPED(budget): latest-run probe cap reached
  - macd_rsi_m048 Shadow Generator [daily] — SKIPPED(budget): latest-run probe cap reached
  - Mercury 2  Weekly Retrain [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ML Feedback Retrain  Learn from Closed Trades [daily] — SKIPPED(budget): latest-run probe cap reached
  - ML Gatekeeper Train A/B (Phase D) [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**1** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **329** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
