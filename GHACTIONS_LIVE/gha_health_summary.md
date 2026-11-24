# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-24T04:39:23.194329+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-16T04:39:23.194329+00:00 → 2026-11-24T04:39:23.194329+00:00 (1000 runs scanned, truncated=False; 385 workflows)
- **API budget:** 147/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| portfolio-tracker | main | 2026-11-24T04:26:26Z | 0.22 | failure | NEVER (prune candidate if dormant) |
| CI | main | 2026-11-24T04:26:28Z | 0.22 | failure | yes |
| .github/workflows/validation-gates.yml | coverage-and-verdict-tooling-2026-11-24 | 2026-11-24T04:21:51Z | 0.29 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-24T01:24:53Z | 3.24 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (15 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ research/per-class-edge-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ buffy/verify-live-claim-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ fix/dsr-skip-contract — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ fix/dsr-nbtrials-floor — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- Forward-Test New Strategies Tracker @ main — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00

- resolved: CI Tests → **resolved_flapping**
- resolved: CI Tests → **resolved_flapping**
- resolved: Verification Tests → **resolved_flapping**
- resolved: Deploy Rise of the Claw Dashboard → **resolved_flapping**
- resolved: portfolio-tracker → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 296.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 296.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 296.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 296.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 296.05h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 2
  - Discord Bot  Persistent — 4.34h running (p90 n/a)
  - [torontoevent.net] Spike Scanner — 0.09h running (p90 0.01h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 21
  - ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds — run 45297904920 killed at 3617.0s mid-step `Push with retry` — timeout problem, not churn
  - Claude's Test - Portfolio Manager — run 45307988641 killed at 318.0s mid-step `Commit updated state and dashboard` — timeout problem, not churn
  - Crypto Test Portfolios — run 45299259113 killed at 918.0s mid-step `Commit results` — timeout problem, not churn
  - GHA queue & duration audit — run 45298435003 killed at 1217.0s mid-step `Commit audit report` — timeout problem, not churn
  - Gainer Predictor Scanner — run 45299514162 killed at 1818.0s mid-step `Commit results` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 30 cancelled run(s) examined (30 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 21 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 8
  - external residual (8) — the true R7 signal, investigate:
    - run 45298928900 Deploy FindCryptoPairs to FTP — cancelled at 2026-11-24T00:39:51Z (branch main)
    - run 45300481855 realtime-challenge — cancelled at 2026-11-24T01:01:48Z (branch main)
    - run 45299268600 DNA Strategy Pipeline — cancelled at 2026-11-24T01:13:32Z (branch main)
    - run 45297818148 DNA Genome Daily Pipeline — cancelled at 2026-11-24T01:22:56Z (branch main)
    - run 45307329075 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-24T01:49:28Z (branch main)
    - run 45307858257 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-24T01:51:27Z (branch main)
    - run 45299127204 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-24T02:30:35Z (branch main)
    - run 45319758662 Picks-Now Live PnL (hourly) — cancelled at 2026-11-24T03:48:35Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.4 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Futures Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - fx-cost-overlap [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 1
  - Sign-Coherence Gate @ main — never passed in window, last failure 9999.0h ago

## 5. NOT AN ISSUE (recovered) — suppressed count

**5** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **284** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
