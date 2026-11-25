# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-25T20:39:34.440634+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-17T20:39:34.440634+00:00 → 2026-11-25T20:39:34.440634+00:00 (1000 runs scanned, truncated=False; 386 workflows)
- **API budget:** 129/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Deploy MOVIESHOWS2 + MOVIESHOWS3 (All 3 Domains) | main | 2026-11-25T20:29:35Z | 0.17 | failure | NEVER (prune candidate if dormant) |
| QA Market Validation | main | 2026-11-25T20:25:54Z | 0.23 | failure | NEVER (prune candidate if dormant) |
| portfolio-tracker | main | 2026-11-25T20:15:06Z | 0.41 | failure | NEVER (prune candidate if dormant) |
| DB Credentials Test | main | 2026-11-25T19:53:25Z | 0.77 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-25T19:24:11Z | 1.26 | failure | NEVER (prune candidate if dormant) |
| DNA Genome Daily Pipeline | main | 2026-11-25T19:24:03Z | 1.26 | failure | yes |
| Mirror: findtorontoevents.ca  torontoevent.net | main | 2026-11-25T18:52:54Z | 1.78 | failure | NEVER (prune candidate if dormant) |
| What Worked Active Picks Insights | main | 2026-11-25T17:53:01Z | 2.78 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

| Workflow | Branch | Fails/15 | Failing steps | Infra vs bug |
|---|---|---|---|---|
| Deploy Competition to Live Site | main | 7/15 | Deploy competition files to live site via FTP | infra 0 / bug 2 |
| [torontoevent.net] Run Backtests & Deploy Dashboards | main | 6/15 | Deploy dashboard to *** via FTP | infra 0 / bug 2 |

**R2 monitor-next-run (10 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Forward-Test New Strategies Tracker @ main — cadence 24.0h, expect resolution by 2026-11-26T13:42:09.012005+00:00
- CI Tests @ research/commodity-tsmom-v3-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-26T21:40:13.119473+00:00
- Sign-Coherence Gate @ main — cadence 24.0h, expect resolution by 2026-11-27T05:39:29.754198+00:00
- What Worked Active Picks Insights @ main — cadence 24.0h, expect resolution by 2026-11-27T13:53:07.020558+00:00
- Asset Class Freshness Watchdog @ main — cadence 24.0h, expect resolution by 2026-11-27T17:40:08.573783+00:00

- resolved: Update Creator News → **resolved_flapping**
- resolved: Feed Health Check → **resolved_flapping**
- resolved: Sidecar Status Markdown Update → **resolved_flapping**
- resolved: QA Market Validation → **escalated_still_broken**
- resolved: Low-Score Winner Tracker → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 336.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 336.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 336.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 336.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 336.06h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 3.32h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 15
  - audit3 ledger — run 45675645124 killed at 922.0s mid-step `Commit ledger (data only, [skip ci])` — timeout problem, not churn
  - portfolio-tracker — run 45694863152 killed at 620.0s mid-step `Commit the book` — timeout problem, not churn
  - realtime-challenge — run 45640868236 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45650822915 killed at 617.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45653191074 killed at 617.0s mid-step `Commit the ledger` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 19 cancelled run(s) examined (19 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 15 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 3
  - external residual (3) — the true R7 signal, investigate:
    - run 45654960625 realtime-challenge — cancelled at 2026-11-25T16:43:20Z (branch main)
    - run 45654835612 DNA Strategy Pipeline — cancelled at 2026-11-25T17:04:02Z (branch main)
    - run 45694415446 Deploy Rise of the Claw Dashboard — cancelled at 2026-11-25T20:26:01Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.0 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - DNA Mutation Cycle [daily] — SKIPPED(budget): latest-run probe cap reached
  - DXY State Update [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Edge decay monitor [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Edge stability refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Edge stability refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Equities & Stocks Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ETF Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**15** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **163** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
