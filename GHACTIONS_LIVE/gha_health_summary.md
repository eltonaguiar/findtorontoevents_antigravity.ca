# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-26T02:34:56.688843+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-18T02:34:56.688843+00:00 → 2026-11-26T02:34:56.688843+00:00 (1000 runs scanned, truncated=False; 386 workflows)
- **API budget:** 141/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Mercury 2  Signal Scanner | main | 2026-11-26T02:33:11Z | 0.03 | failure | yes |
| H-201 Pod Forward Clock | main | 2026-11-26T02:32:34Z | 0.04 | failure | NEVER (prune candidate if dormant) |
| DB Sync: findtorontoevents.ca  torontoevent.net | main | 2026-11-26T02:31:43Z | 0.05 | failure | NEVER (prune candidate if dormant) |
| Coinglass DNA Scanner | main | 2026-11-26T02:31:39Z | 0.05 | failure | yes |
| anti-overfit-gate | main | 2026-11-26T02:31:35Z | 0.06 | failure | NEVER (prune candidate if dormant) |
| WSL Runner Manager | main | 2026-11-26T02:30:36Z | 0.07 | failure | NEVER (prune candidate if dormant) |
| forward observations ingest | main | 2026-11-26T02:27:13Z | 0.13 | failure | NEVER (prune candidate if dormant) |
| audit3 ledger | fix/audit3-ftp-fallback | 2026-11-26T00:51:17Z | 1.73 | failure | NEVER (prune candidate if dormant) |
| masking-policy-lint | ci/2026-11-25-gha-digest | 2026-11-25T23:57:33Z | 2.62 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (11 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ research/commodity-tsmom-v3-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-26T21:40:13.119473+00:00
- Mirror: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-27T21:39:34.440634+00:00
- audit3 ledger @ fix/audit3-ftp-fallback — cadence 24.0h, expect resolution by 2026-11-28T01:57:16.117073+00:00
- ALPHA ENGINE - Live Autonomous Scanner @ fix/safe-push-retry-budget — cadence 24.0h, expect resolution by 2026-11-28T01:57:16.117073+00:00
- Deploy Rise of the Claw Dashboard @ fix/pages-artifact-wait — cadence 1.0h, expect resolution by 2026-11-26T03:57:16.117073+00:00

- resolved: Sign-Coherence Gate → **resolved_flapping**
- resolved: Asset Class Freshness Watchdog → **resolved_flapping**
- resolved: audit3 ledger → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 341.98h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 341.98h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 341.98h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 341.98h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 341.98h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 8
  - Discord Bot  Persistent — 5.05h running (p90 1.9h)
  - REAL 2-HOUR CHALLENGE - Live Market Data — 0.38h running (p90 0.0h)
  - Deploy FC API Hotfix (3 domains) — 0.12h running (p90 0.02h)
  - Hierarchical Bayesian Edge Update — 0.09h running (p90 0.04h)
  - gha-summary-report · workflow_dispatch · 41505139a7f3d235a42cbd93597afa8a9cf6cc93 — 0.09h running (p90 0.04h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 6
  - Claude's Test - Portfolio Manager — run 45728444953 killed at 318.0s mid-step `Fetch prior portfolio state from production` — timeout problem, not churn
  - Claude's Test - Portfolio Manager — run 45730474225 killed at 319.0s mid-step `Fetch prior portfolio state from production` — timeout problem, not churn
  - Claude's Test - Portfolio Manager — run 45732187165 killed at 319.0s mid-step `Fetch prior portfolio state from production` — timeout problem, not churn
  - Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities — run 45734805647 killed at 919.0s mid-step `Commit and push changes` — timeout problem, not churn
  - audit3 ledger — run 45731744440 killed at 920.0s mid-step `?` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 37 cancelled run(s) examined (30 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 6 · eviction-shaped: 8 · stack-kill: 3 · pr-close: 0 · external: 20
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 3 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (20) — the true R7 signal, investigate:
    - run 45729206032 Secret Scan (M-043) — cancelled at 2026-11-26T00:31:55Z (branch fix/audit-dashboard-registry-tribunal-20261125)
    - run 45729387455 CI Tests — cancelled at 2026-11-26T00:34:35Z (branch fix/audit-dashboard-registry-tribunal-20261125)
    - run 45730564278 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-26T00:45:19Z (branch main)
    - run 45730970357 DNA Strategy Pipeline — cancelled at 2026-11-26T01:16:43Z (branch main)
    - run 45738440843 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-26T01:52:09Z (branch main)
    - run 45739058032 No stale DB passwords — cancelled at 2026-11-26T01:56:39Z (branch ci/2026-11-26-nan-producers)
    - run 45740383883 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-26T02:11:34Z (branch main)
    - run 45740730241 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-26T02:14:03Z (branch main)
    - run 45741959521 Closed Picks Command — cancelled at 2026-11-26T02:25:26Z (branch main)
    - run 45742306614 Closed Picks Command — cancelled at 2026-11-26T02:26:14Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 2.8 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.5 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 0.9 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

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
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**7** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **362** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
