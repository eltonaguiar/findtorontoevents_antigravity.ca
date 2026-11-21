# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-21T16:39:38.438297+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-13T16:39:38.438297+00:00 → 2026-11-21T16:39:38.438297+00:00 (1000 runs scanned, truncated=False; 376 workflows)
- **API budget:** 99/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Picks-Now Live PnL (hourly) | main | 2026-11-21T16:28:07Z | 0.19 | failure | yes |
| QA Market Validation | main | 2026-11-21T16:23:52Z | 0.26 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-21T13:23:42Z | 3.27 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (17 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Forward-Test New Strategies Tracker @ main — cadence 24.0h, expect resolution by 2026-11-21T17:39:25.072246+00:00
- audit3 ledger @ fix/audit3-ledger-push — cadence 24.0h, expect resolution by 2026-11-21T17:39:25.072246+00:00
- CI Tests @ test/audit3-cli-smoke — cadence 24.0h, expect resolution by 2026-11-22T01:49:24.110831+00:00
- CI Tests @ hotfix/restore-denylist-hits — cadence 24.0h, expect resolution by 2026-11-22T01:49:24.110831+00:00
- CI Tests @ hotfix/audit3-merge-repair — cadence 24.0h, expect resolution by 2026-11-22T01:49:24.110831+00:00

- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 236.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 236.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 236.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 236.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 236.06h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 2.87h running (p90 1.49h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 3
  - ML Battleground System F (Claws of Doom) — run 44904582687 killed at 319.0s mid-step `Commit synced data` — timeout problem, not churn
  - Meta-Strategy Permutation Engine — run 44897049187 killed at 1818.0s mid-step `Commit results` — timeout problem, not churn
  - crypto intraday sim — run 44898066232 killed at 619.0s mid-step `Commit sim state + forward ledger (data only, [skip ci])` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 6 cancelled run(s) examined (6 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 3 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 2
  - external residual (2) — the true R7 signal, investigate:
    - run 44904367419 DNA Strategy Pipeline — cancelled at 2026-11-21T13:03:09Z (branch main)
    - run 44922710928 Master Automation Scheduler — cancelled at 2026-11-21T16:07:08Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.8 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.9 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.6 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Edge decay monitor [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Edge stability refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Edge stability refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Equities & Stocks Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ETF Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ETF & Bond Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **179** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
