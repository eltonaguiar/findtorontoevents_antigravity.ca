# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-18T04:39:38.831701+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-10T04:39:38.831701+00:00 → 2026-11-18T04:39:38.831701+00:00 (1000 runs scanned, truncated=False; 363 workflows)
- **API budget:** 97/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Sign-Coherence Gate | main | 2026-11-18T04:38:42Z | 0.02 | failure | NEVER (prune candidate if dormant) |
| QA Market Validation | main | 2026-11-18T04:28:15Z | 0.19 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (15 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ tmp/s2-emitters — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ tmp/s3-ci-hygiene — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ tmp/s1-data-gates — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ fix/audit-pm-ingest-shadow-pin-2026-11-16 — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00
- CI Tests @ fix/dashboard-cse-new-picks-int — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00

- resolved: QA Market Validation → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 152.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 152.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 152.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 152.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 152.06h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 0
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 2
  - [torontoevent.net] Deploy Competition to Live Site — run 44230471901 killed at 1818.0s mid-step `Deploy competition files to *** via FTP` — timeout problem, not churn
  - [torontoevent.net] Deploy Rise of the Claw — run 44194043787 killed at 1805.0s mid-step `Verify deployment` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 5 cancelled run(s) examined (5 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 2 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 2
  - external residual (2) — the true R7 signal, investigate:
    - run 44210443672 DNA Strategy Pipeline — cancelled at 2026-11-18T01:17:10Z (branch main)
    - run 44230805870 Baby Strat Real Forward Monitor — cancelled at 2026-11-18T04:14:46Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.5 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.6 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (25 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Growth Stock Screener Daily [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-103 Forward Logger [monthly] — SKIPPED(budget): latest-run probe cap reached
  - HC Evaluator Parity Test [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Hyro Quan Bridge Regen [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**0** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **217** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
