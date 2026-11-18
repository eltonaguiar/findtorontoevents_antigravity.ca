# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-18T12:41:34.023241+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-10T12:41:34.023241+00:00 → 2026-11-18T12:41:34.023241+00:00 (1000 runs scanned, truncated=False; 363 workflows)
- **API budget:** 97/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Sidecar Status Markdown Update | main | 2026-11-18T12:39:59Z | 0.03 | failure | yes |
| DNA Genome Daily Pipeline | main | 2026-11-18T12:37:06Z | 0.07 | failure | yes |
| Deploy Competition to Live Site | main | 2026-11-18T12:36:37Z | 0.08 | failure | yes |
| Picks-Now Live PnL (hourly) | main | 2026-11-18T12:33:23Z | 0.14 | failure | yes |
| Mirror: findtorontoevents.ca  torontoevent.net | main | 2026-11-18T12:32:21Z | 0.15 | failure | yes |
| QA Market Validation | main | 2026-11-18T12:32:18Z | 0.15 | failure | NEVER (prune candidate if dormant) |
| pages-build-deployment | gh-pages | 2026-11-18T12:32:03Z | 0.16 | failure | yes |
| GHCOPILOT prospective paper monitor | main | 2026-11-18T12:31:03Z | 0.18 | failure | yes |
| Feed Health Check | main | 2026-11-18T12:29:41Z | 0.2 | failure | yes |
| Send Accountability Reminders | main | 2026-11-18T12:29:25Z | 0.2 | failure | yes |

_(+3 more in JSON)_

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (23 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ fix/audit-pm-ingest-shadow-pin-2026-11-16 — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00
- CI Tests @ fix/dashboard-cse-new-picks-int — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00
- CI Tests @ fix/audit-remaining-honesty — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00
- CI Tests @ tmp/s9-ghost-rootcause — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00
- CI Tests @ fix/audit-quant-fixes-2026-11-16 — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00

- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: QA Market Validation → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 160.09h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 160.09h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 160.09h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 160.09h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 160.09h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 2.99h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 3
  - Meme Coin Scanner v2  Fixed & Monitored — run 44291342363 killed at 319.0s mid-step `Deploy meme_scanner_fixed.php to server` — timeout problem, not churn
  - [torontoevent.net] Deploy Competition to Live Site — run 44267166802 killed at 1817.0s mid-step `Deploy competition files to *** via FTP` — timeout problem, not churn
  - 🧠 Smart Money Intelligence — run 44291866566 killed at 318.0s mid-step `Fetch analyst ratings + price targets` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 5 cancelled run(s) examined (5 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 3 · eviction-shaped: 0 · stack-kill: 0 · pr-close: 0 · external: 2
  - external residual (2) — the true R7 signal, investigate:
    - run 44252383098 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-18T08:29:20Z (branch main)
    - run 44267770086 DNA Strategy Pipeline — cancelled at 2026-11-18T09:03:21Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.5 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.9 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 1.0 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.6 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (25 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — SKIPPED(budget): latest-run probe cap reached
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Growth Stock Screener Daily [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-103 Forward Logger [monthly] — SKIPPED(budget): latest-run probe cap reached
  - HC Evaluator Parity Test [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Hierarchical Bayesian Edge Update [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**0** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **189** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
