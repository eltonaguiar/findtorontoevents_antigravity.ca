# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-26T04:39:53.615011+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-18T04:39:53.615011+00:00 → 2026-11-26T04:39:53.615011+00:00 (1000 runs scanned, truncated=False; 386 workflows)
- **API budget:** 119/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Sign-Coherence Gate | main | 2026-11-26T04:39:25Z | 0.01 | failure | yes |
| Audit Impact Tracker | main | 2026-11-26T04:32:51Z | 0.12 | failure | NEVER (prune candidate if dormant) |
| forward observations ingest | main | 2026-11-26T04:28:14Z | 0.19 | failure | NEVER (prune candidate if dormant) |
| Mercury 2  Signal Scanner | main | 2026-11-26T04:26:50Z | 0.22 | failure | NEVER (prune candidate if dormant) |
| gha-quality-framework | main | 2026-11-26T04:26:35Z | 0.22 | failure | NEVER (prune candidate if dormant) |
| fx-cost-overlap | main | 2026-11-26T04:26:25Z | 0.22 | failure | NEVER (prune candidate if dormant) |
| WSL Runner Manager | main | 2026-11-26T04:26:06Z | 0.23 | failure | NEVER (prune candidate if dormant) |
| Deploy Competition to Live Site | main | 2026-11-26T03:35:22Z | 1.08 | failure | yes |
| anti-overfit-gate | main | 2026-11-26T03:27:23Z | 1.21 | failure | NEVER (prune candidate if dormant) |
| Kimi Fetch Movies/TV (Manual) | main | 2026-11-26T03:09:09Z | 1.51 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (13 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ research/commodity-tsmom-v3-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-26T21:40:13.119473+00:00
- Mirror: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-27T21:39:34.440634+00:00
- audit3 ledger @ fix/audit3-ftp-fallback — cadence 24.0h, expect resolution by 2026-11-28T01:57:16.117073+00:00
- ALPHA ENGINE - Live Autonomous Scanner @ fix/safe-push-retry-budget — cadence 24.0h, expect resolution by 2026-11-28T01:57:16.117073+00:00
- Mercury 2  Signal Scanner @ main — cadence 1.0h, expect resolution by 2026-11-26T05:34:56.688843+00:00

- resolved: Deploy Rise of the Claw Dashboard → **escalated_scheduler_dead**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 344.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 344.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 344.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 344.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 344.06h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Branch Large File Duplicate Guard — 2.46h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 3
  - ALPHA ENGINE Gainer Capture (15min) — run 45746833141 killed at 724.0s mid-step `?` — timeout problem, not churn
  - ML Battleground System F (Claws of Doom) — run 45742959485 killed at 270.0s mid-step `?` — timeout problem, not churn
  - 📺 News Video Health Check — run 45750255534 killed at 287.0s mid-step `?` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 181 cancelled run(s) examined (30 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 3 · eviction-shaped: 13 · stack-kill: 5 · pr-close: 0 · external: 160
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 5 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (160) — the true R7 signal, investigate:
    - run 45742965490 Spike Scanner — cancelled at 2026-11-26T02:35:11Z (branch main)
    - run 45743215257 QA Market Validation — cancelled at 2026-11-26T02:35:55Z (branch main)
    - run 45743429125 [torontoevent.net] Spike Scanner — cancelled at 2026-11-26T02:36:18Z (branch main)
    - run 45743005674 TV Paper TP/SL Watchdog — cancelled at 2026-11-26T02:36:28Z (branch main)
    - run 45743178148 Polymarket Prediction Market Signals (Multi-Asset) — cancelled at 2026-11-26T02:37:01Z (branch main)
    - run 45743505468 [torontoevent.net] Deploy Competition to Live Site — cancelled at 2026-11-26T02:38:11Z (branch main)
    - run 45743557741 Update Creator News — cancelled at 2026-11-26T02:38:15Z (branch main)
    - run 45743200129 Prediction Quality Tracker — cancelled at 2026-11-26T02:39:43Z (branch main)
    - run 45743358684 Signal Tracking & Validation - Beat the Market — cancelled at 2026-11-26T02:39:49Z (branch main)
    - run 45743268215 Refresh Creator Updates — cancelled at 2026-11-26T02:41:30Z (branch main)
    - _(+140 more in JSON)_
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 2.1 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.9 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 1.1 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 0.8 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.5 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 5 (22 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - strategy_performance.json no-regression guard [unknown] — stale by cadence: silent 182d as unknown (threshold 60d)
  - AI Tournament Pipeline — Daily Picks + DB Ingest [daily] — stale by cadence: silent 175d as daily (threshold 30d)
  - Real-Time Battle Test - Eliminate Losers, Optimize Winners [hourly] — stale by cadence: silent 166d as hourly (threshold 30d)
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 1
  - Unified Audit Dashboard @ main — never passed in window, last failure 9999.0h ago

## 5. NOT AN ISSUE (recovered) — suppressed count

**5** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **358** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
