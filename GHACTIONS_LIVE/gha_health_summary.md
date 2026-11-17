# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-17T00:50:23.322862+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-09T00:50:23.322862+00:00 → 2026-11-17T00:50:23.322862+00:00 (1000 runs scanned, truncated=False; 362 workflows)
- **API budget:** 114/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| QA Market Validation | main | 2026-11-17T00:45:13Z | 0.09 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/audit-quant-fixes-round3-2026-11-16 | 2026-11-16T21:05:34Z | 3.75 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/cohort-guards-n-eff | 2026-11-16T20:59:28Z | 3.85 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/audit-pm-ingest-shadow-pin-2026-11-16 | 2026-11-16T20:35:41Z | 4.25 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/dashboard-cse-new-picks-int | 2026-11-16T20:32:36Z | 4.3 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/audit-remaining-honesty | 2026-11-16T20:31:33Z | 4.31 | failure | NEVER (prune candidate if dormant) |
| CI Tests | tmp/s9-ghost-rootcause | 2026-11-16T20:30:40Z | 4.33 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/audit-quant-fixes-2026-11-16 | 2026-11-16T20:14:32Z | 4.6 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/top-sleeves-artifact-guard | 2026-11-16T20:08:47Z | 4.69 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/feed-health-optional-pm-sources-2026-11-16 | 2026-11-16T20:06:58Z | 4.72 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

| Workflow | Branch | Fails/15 | Failing steps | Infra vs bug |
|---|---|---|---|---|
| CI Tests | main | 5/15 | Run all tests (gating — known-drift quarantined) | infra 0 / bug 4 |

**R2 monitor-next-run (14 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ tmp/s2-emitters — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ tmp/s3-ci-hygiene — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ tmp/s1-data-gates — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ fix/audit-pm-ingest-shadow-pin-2026-11-16 — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00
- CI Tests @ fix/dashboard-cse-new-picks-int — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00

- resolved: Unified Audit Dashboard → **resolved_flapping**
- resolved: CI Tests → **resolved_flapping**
- resolved: CI Tests → **resolved_flapping**
- resolved: QA Market Validation → **escalated_still_broken**
- resolved: Feed Health Check → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 21
  - run 43095833399 Rapid Fire - NOW Scanner queued 2026-11-11T20:24:10Z (age 124.44h) — uncancelable ⇒ GitHub Support batch
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 124.24h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 124.24h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 124.24h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 124.24h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 6.56h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 1
  - Winner Pattern Precursor Scanner — run 43969577709 killed at 619.0s mid-step `Commit results` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 12 cancelled run(s) examined (12 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 1 · eviction-shaped: 4 · stack-kill: 0 · pr-close: 0 · external: 7
  - external residual (7) — the true R7 signal, investigate:
    - run 43945253797 No stale DB passwords — cancelled at 2026-11-16T20:01:12Z (branch main)
    - run 43949528053 Quant Auditor (fast PR check) — cancelled at 2026-11-16T20:25:27Z (branch tmp/s9-ghost-rootcause)
    - run 43949527855 Conflict Marker Check — cancelled at 2026-11-16T20:25:28Z (branch tmp/s9-ghost-rootcause)
    - run 43949528215 CI Tests — cancelled at 2026-11-16T20:25:31Z (branch tmp/s9-ghost-rootcause)
    - run 43950654919 DNA Strategy Pipeline — cancelled at 2026-11-16T21:03:06Z (branch main)
    - run 43967115669 CI Tests — cancelled at 2026-11-16T22:09:30Z (branch fix/audit-quant-fixes-round4-2026-11-16)
    - run 43949871810 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-16T22:27:07Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.2 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (25 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
  - GHA scan job (reusable) [unknown] — SKIPPED(budget): latest-run probe cap reached
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
  - gha-summary-report [daily] — SKIPPED(budget): latest-run probe cap reached
  - Growth Stock Screener Daily [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-103 Forward Logger [monthly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**5** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **270** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
