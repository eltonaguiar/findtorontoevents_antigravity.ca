# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-16T08:51:04.687016+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-08T08:51:04.687016+00:00 → 2026-11-16T08:51:04.687016+00:00 (1000 runs scanned, truncated=False; 361 workflows)
- **API budget:** 114/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| CI Tests | tmp/s2-emitters | 2026-11-16T07:26:17Z | 1.41 | failure | NEVER (prune candidate if dormant) |
| CI Tests | tmp/s3-ci-hygiene | 2026-11-16T07:22:30Z | 1.48 | failure | NEVER (prune candidate if dormant) |
| CI Tests | tmp/s1-data-gates | 2026-11-16T07:22:21Z | 1.48 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/audit-truth-layer-2026-11-16 | 2026-11-16T06:48:13Z | 2.05 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (4 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ tmp/s2-emitters — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ tmp/s3-ci-hygiene — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ tmp/s1-data-gates — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ fix/audit-truth-layer-2026-11-16 — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00

- resolved: ALPHA ENGINE - Dynamic Runner (Cloud or Local) → **resolved_flapping**
- resolved: Feed Health Check → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 21
  - run 43095833399 Rapid Fire - NOW Scanner queued 2026-11-11T20:24:10Z (age 108.45h) — uncancelable ⇒ GitHub Support batch
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 108.25h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 108.25h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 108.25h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 108.25h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 8.2h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 8
  - Coinglass DNA Scanner — run 43799571487 killed at 918.0s mid-step `Commit data changes` — timeout problem, not churn
  - Consensus Outcome Tracker — run 43799713400 killed at 917.0s mid-step `Commit outcome updates` — timeout problem, not churn
  - Copy Trader Forward Test — run 43799713959 killed at 2117.0s mid-step `Commit and push changes` — timeout problem, not churn
  - Gainer Predictor Scanner — run 43799545212 killed at 1818.0s mid-step `Commit results` — timeout problem, not churn
  - Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities — run 43800186406 killed at 917.0s mid-step `Commit and push changes` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 26 cancelled run(s) examined (26 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 8 · eviction-shaped: 1 · stack-kill: 3 · pr-close: 0 · external: 14
  - external residual (14) — the true R7 signal, investigate:
    - run 43800668052 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-16T03:53:45Z (branch main)
    - run 43799775582 Branch Large File Duplicate Guard — cancelled at 2026-11-16T03:57:50Z (branch feat/finpredict-final-v001)
    - run 43803077133 CI Tests — cancelled at 2026-11-16T04:23:08Z (branch main)
    - run 43799746374 ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds — cancelled at 2026-11-16T04:38:59Z (branch main)
    - run 43808472586 CI Tests — cancelled at 2026-11-16T05:14:15Z (branch main)
    - run 43810128269 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-16T05:29:15Z (branch main)
    - run 43809108656 Unified Audit Dashboard — cancelled at 2026-11-16T06:11:08Z (branch main)
    - run 43819223043 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-16T06:50:20Z (branch main)
    - run 43814271519 CI Tests — cancelled at 2026-11-16T06:50:25Z (branch main)
    - run 43819654397 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-16T07:37:01Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 5.1 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.9 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.2 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (25 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - 📺 News Video Health Check [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Optimize Score Thresholds [daily] — SKIPPED(budget): latest-run probe cap reached
  - Overnight Mutations [weekly] — SKIPPED(budget): latest-run probe cap reached
  - paper-pilot-daily [daily] — SKIPPED(budget): latest-run probe cap reached
  - Penny Skyrocket Detector [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Penny Stock Daily Picks [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Pick Data Quality Gate [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**5** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **288** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
