# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-19T16:39:25.072246+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-11T16:39:25.072246+00:00 → 2026-11-19T16:39:25.072246+00:00 (1000 runs scanned, truncated=False; 369 workflows)
- **API budget:** 103/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| QA Market Validation | main | 2026-11-19T16:26:11Z | 0.22 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-19T13:24:35Z | 3.25 | failure | NEVER (prune candidate if dormant) |
| audit3 ledger | fix/audit3-ledger-push | 2026-11-19T13:00:32Z | 3.65 | failure | NEVER (prune candidate if dormant) |
| CI Tests | audit3-dsr-global-trials | 2026-11-19T11:51:11Z | 4.8 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (19 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ feat/forward-gate-and-ingest — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/forward-observations-contract — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ fix/h119-vintage-and-kill-list-reconcile — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ fix/verdict-fixtures-and-key-redaction — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/wr-semantics-measured-cost-timeline — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00

- resolved: audit3 ledger → **resolved_flapping**
- resolved: Mirror: findtorontoevents.ca  torontoevent.net → **resolved_flapping**
- resolved: [torontoevent.net] Deploy Competition to Live Site → **resolved_flapping**
- resolved: QA Market Validation → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 188.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 188.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 188.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 188.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 188.06h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 0
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 6
  - 2hour-challenge — run 44522886134 killed at 1818.0s mid-step `Run 2-hour trading challenge` — timeout problem, not churn
  - Claude's Test - Portfolio Manager — run 44518483065 killed at 317.0s mid-step `Commit updated state and dashboard` — timeout problem, not churn
  - MOMENTUM TRACKER - Real-Time Gainer Scanner — run 44548682760 killed at 619.0s mid-step `Commit results` — timeout problem, not churn
  - Meta-Strategy Permutation Engine — run 44511004454 killed at 1819.0s mid-step `Commit results` — timeout problem, not churn
  - Winner Pattern Precursor Scanner — run 44548605385 killed at 619.0s mid-step `Commit results` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 9 cancelled run(s) examined (8 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 6 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 2
  - external residual (2) — the true R7 signal, investigate:
    - run 44525081061 DNA Strategy Pipeline — cancelled at 2026-11-19T13:05:33Z (branch main)
    - run 44561221324 Audit Drift Telemetry — cancelled at 2026-11-19T16:00:47Z (branch audit2-excluded-cohorts)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.2 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
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
- additionally **250** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
