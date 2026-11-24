# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-24T08:40:14.563808+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-16T08:40:14.563808+00:00 → 2026-11-24T08:40:14.563808+00:00 (1000 runs scanned, truncated=False; 385 workflows)
- **API budget:** 125/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Deploy Rise of the Claw Dashboard | main | 2026-11-24T08:31:01Z | 0.15 | failure | yes |
| portfolio-tracker | main | 2026-11-24T08:28:17Z | 0.2 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-24T07:25:42Z | 1.24 | failure | NEVER (prune candidate if dormant) |
| Sign-Coherence Gate | main | 2026-11-24T05:25:42Z | 3.24 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/validation-gates.yml | coverage-and-verdict-tooling-2026-11-24 | 2026-11-24T04:40:54Z | 3.99 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (15 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ research/per-class-edge-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ buffy/verify-live-claim-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ fix/dsr-skip-contract — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ fix/dsr-nbtrials-floor — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- Forward-Test New Strategies Tracker @ main — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00

- resolved: portfolio-tracker → **escalated_still_broken**
- resolved: CI → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 300.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 300.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 300.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 300.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 300.07h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 2.5h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 15
  - Kalshi snapshot (sports markets cache) — run 45341521773 killed at 1219.0s mid-step `Commit snapshot (only when changed)` — timeout problem, not churn
  - Pine Script Generator — run 45346739817 killed at 1817.0s mid-step `Commit and push if changed` — timeout problem, not churn
  - realtime-challenge — run 45320226395 killed at 617.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45321855625 killed at 617.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45325652846 killed at 617.0s mid-step `Commit the ledger` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 19 cancelled run(s) examined (19 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 15 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 3
  - external residual (3) — the true R7 signal, investigate:
    - run 45319758662 Picks-Now Live PnL (hourly) — cancelled at 2026-11-24T03:48:35Z (branch main)
    - run 45326943681 DNA Strategy Pipeline — cancelled at 2026-11-24T05:02:38Z (branch main)
    - run 45343462861 realtime-challenge — cancelled at 2026-11-24T07:02:29Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.8 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.2 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Hierarchical Bayesian Edge Update [daily] — SKIPPED(budget): latest-run probe cap reached
  - Honest Kill Switch [daily] — SKIPPED(budget): latest-run probe cap reached
  - Hyro daily (filter + backtest) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Insider Trades Refresh [weekly] — SKIPPED(budget): latest-run probe cap reached
  - macd_rsi_m048 Shadow Generator [daily] — SKIPPED(budget): latest-run probe cap reached
  - Mercury 2  Weekly Retrain [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**3** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **254** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
