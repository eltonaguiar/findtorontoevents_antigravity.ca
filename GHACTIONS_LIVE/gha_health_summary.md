# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-21T08:39:52.599485+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-13T08:39:52.599485+00:00 → 2026-11-21T08:39:52.599485+00:00 (1000 runs scanned, truncated=False; 376 workflows)
- **API budget:** 111/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| CI Tests | main | 2026-11-21T08:38:45Z | 0.02 | failure | yes |
| CI Tests | audit-denominator-forward-clock-dsr-baselines | 2026-11-21T08:38:30Z | 0.02 | failure | NEVER (prune candidate if dormant) |
| QA Market Validation | main | 2026-11-21T08:36:33Z | 0.06 | failure | yes |
| Forward-Test New Strategies Tracker | main | 2026-11-21T07:24:28Z | 1.26 | failure | NEVER (prune candidate if dormant) |
| Unified Audit Dashboard | main | 2026-11-21T07:02:40Z | 1.62 | failure | yes |
| CI Tests | dsr-baseline-skip | 2026-11-21T05:35:42Z | 3.07 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (32 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ feat/forward-gate-and-ingest — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/forward-observations-contract — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ fix/h119-vintage-and-kill-list-reconcile — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ fix/verdict-fixtures-and-key-redaction — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/wr-semantics-measured-cost-timeline — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00

- resolved: Sign-Coherence Gate → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 228.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 228.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 228.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 228.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 228.06h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Unified Audit Dashboard — 2.29h running (p90 1.31h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 2
  - Claude's Test - Portfolio Manager — run 44882140750 killed at 319.0s mid-step `Commit updated state and dashboard` — timeout problem, not churn
  - Conviction Picks Ultra-Selective Discord Alert — run 44882246479 killed at 1217.0s mid-step `Commit results` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 12 cancelled run(s) examined (12 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 2 · eviction-shaped: 1 · stack-kill: 2 · pr-close: 0 · external: 7
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 2 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (7) — the true R7 signal, investigate:
    - run 44864498786 Master Automation Scheduler — cancelled at 2026-11-21T04:08:05Z (branch main)
    - run 44866497573 DNA Strategy Pipeline — cancelled at 2026-11-21T05:02:45Z (branch main)
    - run 44868507431 QA Market Validation — cancelled at 2026-11-21T05:02:51Z (branch main)
    - run 44868971259 QA Market Validation — cancelled at 2026-11-21T05:03:24Z (branch main)
    - run 44878611567 DB Sync: findtorontoevents.ca  torontoevent.net — cancelled at 2026-11-21T07:52:16Z (branch main)
    - run 44881668017 Cross-System Signal Aggregator — cancelled at 2026-11-21T08:18:54Z (branch main)
    - run 44882137822 Deploy Rise of the Claw Dashboard — cancelled at 2026-11-21T08:24:23Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.5 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.2 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-103 Forward Logger [monthly] — SKIPPED(budget): latest-run probe cap reached
  - HC Evaluator Parity Test [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Hierarchical Bayesian Edge Update [daily] — SKIPPED(budget): latest-run probe cap reached
  - Honest Kill Switch [daily] — SKIPPED(budget): latest-run probe cap reached
  - Hyro daily (filter + backtest) [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **255** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
