# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-22T08:39:18.782703+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-14T08:39:18.782703+00:00 → 2026-11-22T08:39:18.782703+00:00 (1000 runs scanned, truncated=False; 376 workflows)
- **API budget:** 145/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| CI Tests | research/per-class-edge-2026-11-22 | 2026-11-22T08:38:56Z | 0.01 | failure | NEVER (prune candidate if dormant) |
| QA Market Validation | main | 2026-11-22T08:27:12Z | 0.2 | failure | NEVER (prune candidate if dormant) |
| CI Tests | buffy/verify-live-claim-2026-11-22 | 2026-11-22T08:05:56Z | 0.56 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/dsr-skip-contract | 2026-11-22T08:05:20Z | 0.57 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/dsr-nbtrials-floor | 2026-11-22T07:58:42Z | 0.68 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-22T07:23:55Z | 1.26 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/dsr-baselines-h146-key-scrub-2026-11-21 | 2026-11-22T06:56:30Z | 1.71 | failure | NEVER (prune candidate if dormant) |
| audit3 Health Monitor | main | 2026-11-22T06:31:23Z | 2.13 | failure | NEVER (prune candidate if dormant) |
| Sign-Coherence Gate | main | 2026-11-22T05:24:14Z | 3.25 | failure | NEVER (prune candidate if dormant) |
| CI Tests | main | 2026-11-22T08:39:18Z | 9999.0 | failure | yes |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (14 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Unified Audit Dashboard @ docs/correct-dashboard-cadence — cadence 24.0h, expect resolution by 2026-11-22T09:40:08.060818+00:00
- CI Tests @ zoo/p0-recovery-2026-11-20 — cadence 24.0h, expect resolution by 2026-11-22T21:39:21.216936+00:00
- CI Tests @ audit-denominator-forward-clock-dsr-baselines — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ dsr-baseline-skip — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ research/per-class-edge-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00

- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 252.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 252.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 252.05h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 252.05h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 252.05h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Branch Large File Duplicate Guard — 2.36h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 0
- **CANCEL BUCKETS (R7)** — 29 cancelled run(s) examined (29 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 0 · eviction-shaped: 1 · stack-kill: 16 · pr-close: 0 · external: 12
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 16 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (12) — the true R7 signal, investigate:
    - run 44985417455 DNA Strategy Pipeline — cancelled at 2026-11-22T05:02:28Z (branch main)
    - run 44995782334 Conflict Marker Check — cancelled at 2026-11-22T06:54:26Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44995782331 masking-policy-lint — cancelled at 2026-11-22T06:54:28Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44995782280 No stale DB passwords — cancelled at 2026-11-22T06:54:28Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44995782362 DB Password Leak Guard — cancelled at 2026-11-22T06:54:29Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44999402830 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-22T07:42:21Z (branch main)
    - run 44999402795 No stale DB passwords — cancelled at 2026-11-22T07:42:22Z (branch main)
    - run 45000956768 Secret Scan (M-043) — cancelled at 2026-11-22T08:03:55Z (branch buffy/verify-live-claim-2026-11-22)
    - run 45000956792 CI Tests — cancelled at 2026-11-22T08:04:09Z (branch buffy/verify-live-claim-2026-11-22)
    - run 45001245827 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-22T08:09:30Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.4 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.2 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Honest Kill Switch [daily] — SKIPPED(budget): latest-run probe cap reached
  - Hyro daily (filter + backtest) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Index All Creator Content [daily] — SKIPPED(budget): latest-run probe cap reached
  - Insider Trades Refresh [weekly] — SKIPPED(budget): latest-run probe cap reached
  - macd_rsi_m048 Shadow Generator [daily] — SKIPPED(budget): latest-run probe cap reached
  - Mercury 2  Weekly Retrain [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**1** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **277** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
