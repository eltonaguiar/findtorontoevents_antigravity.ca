# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-24T00:47:59.827016+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-16T00:47:59.827016+00:00 → 2026-11-24T00:47:59.827016+00:00 (1000 runs scanned, truncated=False; 385 workflows)
- **API budget:** 117/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Verification Tests | main | 2026-11-24T00:44:15Z | 0.06 | failure | NEVER (prune candidate if dormant) |
| Deploy Rise of the Claw Dashboard | main | 2026-11-24T00:42:54Z | 0.08 | failure | yes |
| portfolio-tracker | main | 2026-11-24T00:39:58Z | 0.13 | failure | NEVER (prune candidate if dormant) |
| Regime Terminal  HMM Live Scanner | main | 2026-11-24T00:39:38Z | 0.14 | failure | yes |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (19 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ research/per-class-edge-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ buffy/verify-live-claim-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ fix/dsr-skip-contract — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ fix/dsr-nbtrials-floor — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- Forward-Test New Strategies Tracker @ main — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00

- resolved: QA Market Validation → **resolved_flapping**
- resolved: portfolio-tracker → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 292.2h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 292.2h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 292.2h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 292.2h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 292.2h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - ML Battleground System F (Claws of Doom) — 0.07h running (p90 0.02h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 12
  - Winner Pattern Precursor Scanner — run 45274181670 killed at 619.0s mid-step `Commit results` — timeout problem, not churn
  - realtime-challenge — run 45244695136 killed at 618.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45247321845 killed at 621.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45249963061 killed at 620.0s mid-step `Commit the ledger` — timeout problem, not churn
  - realtime-challenge — run 45257799371 killed at 617.0s mid-step `Commit the ledger` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 15 cancelled run(s) examined (15 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 12 · eviction-shaped: 0 · stack-kill: 0 · pr-close: 0 · external: 3
  - external residual (3) — the true R7 signal, investigate:
    - run 45253352261 Deploy Rise of the Claw Dashboard — cancelled at 2026-11-23T19:52:03Z (branch main)
    - run 45260244801 DNA Strategy Pipeline — cancelled at 2026-11-23T21:03:08Z (branch main)
    - run 45298928900 Deploy FindCryptoPairs to FTP — cancelled at 2026-11-24T00:39:51Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.8 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - forward observations ingest [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forward-Test New Strategies Tracker [daily] — SKIPPED(budget): latest-run probe cap reached
  - Funding-Rate Archive Collector [daily] — SKIPPED(budget): latest-run probe cap reached
  - fx-cost-overlap [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**1** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **228** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
