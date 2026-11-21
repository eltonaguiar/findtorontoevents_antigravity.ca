# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-21T12:39:17.692564+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-13T12:39:17.692564+00:00 → 2026-11-21T12:39:17.692564+00:00 (1000 runs scanned, truncated=False; 376 workflows)
- **API budget:** 103/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| QA Market Validation | main | 2026-11-21T12:28:19Z | 0.18 | failure | NEVER (prune candidate if dormant) |
| CI Tests | main | 2026-11-21T09:25:28Z | 3.23 | failure | NEVER (prune candidate if dormant) |
| CI Tests | audit-denominator-forward-clock-dsr-baselines | 2026-11-21T08:38:30Z | 4.01 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-21T07:24:28Z | 5.25 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (24 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ audit3-dsr-global-trials — cadence 24.0h, expect resolution by 2026-11-21T13:41:43.601128+00:00
- CI Tests @ audit3-intrabar-resolver — cadence 24.0h, expect resolution by 2026-11-21T13:41:43.601128+00:00
- CI Tests @ feat/audit3-intraday-stop-panel — cadence 24.0h, expect resolution by 2026-11-21T13:41:43.601128+00:00
- CI Tests @ fix/alpha-slice-scan-tie — cadence 24.0h, expect resolution by 2026-11-21T13:41:43.601128+00:00
- CI Tests @ fix/alpha-slice-scan-test — cadence 24.0h, expect resolution by 2026-11-21T13:41:43.601128+00:00

- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 232.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 232.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 232.05h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 232.05h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 232.05h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 2
  - Discord Bot  Persistent — 4.78h running (p90 n/a)
  - ML Battleground System F (Claws of Doom) — 0.08h running (p90 0.02h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 4
  - Claude's Test - Portfolio Manager — run 44882140750 killed at 319.0s mid-step `Commit updated state and dashboard` — timeout problem, not churn
  - Conviction Picks Ultra-Selective Discord Alert — run 44882246479 killed at 1217.0s mid-step `Commit results` — timeout problem, not churn
  - Meta-Strategy Permutation Engine — run 44897049187 killed at 1818.0s mid-step `Commit results` — timeout problem, not churn
  - crypto intraday sim — run 44898066232 killed at 619.0s mid-step `Commit sim state + forward ledger (data only, [skip ci])` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 8 cancelled run(s) examined (8 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 4 · eviction-shaped: 0 · stack-kill: 0 · pr-close: 0 · external: 4
  - external residual (4) — the true R7 signal, investigate:
    - run 44878611567 DB Sync: findtorontoevents.ca  torontoevent.net — cancelled at 2026-11-21T07:52:16Z (branch main)
    - run 44881668017 Cross-System Signal Aggregator — cancelled at 2026-11-21T08:18:54Z (branch main)
    - run 44882137822 Deploy Rise of the Claw Dashboard — cancelled at 2026-11-21T08:24:23Z (branch main)
    - run 44885253806 DNA Strategy Pipeline — cancelled at 2026-11-21T09:02:23Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.5 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 1.0 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.8 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Funding-Rate Archive Collector [daily] — SKIPPED(budget): latest-run probe cap reached
  - Futures Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
  - GHA scan job (reusable) [unknown] — SKIPPED(budget): latest-run probe cap reached
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Growth Stock Screener Daily [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**0** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **208** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
