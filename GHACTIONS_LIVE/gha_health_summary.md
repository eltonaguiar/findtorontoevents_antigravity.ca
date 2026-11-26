# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-26T03:37:20.527746+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-18T03:37:20.527746+00:00 → 2026-11-26T03:37:20.527746+00:00 (1000 runs scanned, truncated=False; 386 workflows)
- **API budget:** 108/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Deploy Competition to Live Site | main | 2026-11-26T03:35:22Z | 0.03 | failure | yes |
| Audit Impact Tracker | main | 2026-11-26T03:32:59Z | 0.07 | failure | yes |
| anti-overfit-gate | main | 2026-11-26T03:27:23Z | 0.17 | failure | NEVER (prune candidate if dormant) |
| forward observations ingest | main | 2026-11-26T03:10:30Z | 0.45 | failure | NEVER (prune candidate if dormant) |
| Kimi Fetch Movies/TV (Manual) | main | 2026-11-26T03:09:09Z | 0.47 | failure | NEVER (prune candidate if dormant) |
| Mercury 2  Signal Scanner | main | 2026-11-26T03:08:35Z | 0.48 | failure | yes |
| WSL Runner Manager | main | 2026-11-26T03:07:49Z | 0.49 | failure | NEVER (prune candidate if dormant) |
| Mirror: findtorontoevents.ca  torontoevent.net | main | 2026-11-26T03:03:22Z | 0.57 | failure | NEVER (prune candidate if dormant) |
| Clear Channel Command | main | 2026-11-26T02:57:34Z | 0.66 | failure | NEVER (prune candidate if dormant) |
| DB Sync: findtorontoevents.ca  torontoevent.net | main | 2026-11-26T02:55:35Z | 0.7 | failure | NEVER (prune candidate if dormant) |

_(+1 more in JSON)_

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (12 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ research/commodity-tsmom-v3-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-26T21:40:13.119473+00:00
- Mirror: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-27T21:39:34.440634+00:00
- audit3 ledger @ fix/audit3-ftp-fallback — cadence 24.0h, expect resolution by 2026-11-28T01:57:16.117073+00:00
- ALPHA ENGINE - Live Autonomous Scanner @ fix/safe-push-retry-budget — cadence 24.0h, expect resolution by 2026-11-28T01:57:16.117073+00:00
- Deploy Rise of the Claw Dashboard @ fix/pages-artifact-wait — cadence 1.0h, expect resolution by 2026-11-26T03:57:16.117073+00:00

- resolved: H-201 Pod Forward Clock → **resolved_flapping**
- resolved: Coinglass DNA Scanner → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 343.02h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 343.02h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 343.02h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 343.02h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 343.02h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 3
  - REAL 2-HOUR CHALLENGE - Live Market Data — 1.42h running (p90 0.0h)
  - Mirror: findtorontoevents.ca  torontoevent.net — 1.1h running (p90 0.41h)
  - Backfill Missing Audit Trail Sources — 0.49h running (p90 0.2h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 4
  - 2hour-challenge — run 45740875661 killed at 1818.0s mid-step `?` — timeout problem, not churn
  - ALPHA ENGINE Gainer Capture (15min) — run 45746833141 killed at 724.0s mid-step `?` — timeout problem, not churn
  - Alpha Engine - Weekly Validation Suite — run 45746847087 killed at 919.0s mid-step `?` — timeout problem, not churn
  - ML Battleground System F (Claws of Doom) — run 45742959485 killed at 270.0s mid-step `Sync Claws of Doom data` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 52 cancelled run(s) examined (30 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 4 · eviction-shaped: 10 · stack-kill: 0 · pr-close: 0 · external: 38
  - external residual (38) — the true R7 signal, investigate:
    - run 45738440843 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-26T01:52:09Z (branch main)
    - run 45739058032 No stale DB passwords — cancelled at 2026-11-26T01:56:39Z (branch ci/2026-11-26-nan-producers)
    - run 45740383883 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-26T02:11:34Z (branch main)
    - run 45740730241 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-26T02:14:03Z (branch main)
    - run 45741959521 Closed Picks Command — cancelled at 2026-11-26T02:25:26Z (branch main)
    - run 45742306614 Closed Picks Command — cancelled at 2026-11-26T02:26:14Z (branch main)
    - run 45740820521 Clear Channel Command — cancelled at 2026-11-26T02:26:22Z (branch main)
    - run 45742480279 Deploy Battleground to FTP — cancelled at 2026-11-26T02:27:50Z (branch main)
    - run 45742517455 Deploy Rise of the Claw Dashboard — cancelled at 2026-11-26T02:27:54Z (branch main)
    - run 45742376961 Claude Gainer ML  Live Scanner — cancelled at 2026-11-26T02:29:04Z (branch main)
    - _(+18 more in JSON)_
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 2.9 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.9 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 1.1 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 0.9 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.4 runs/day

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
  - fx-cost-overlap @ main — never passed in window, last failure 9999.0h ago

## 5. NOT AN ISSUE (recovered) — suppressed count

**7** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **427** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
