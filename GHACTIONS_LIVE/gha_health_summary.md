# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-23T00:53:20.923766+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-15T00:53:20.923766+00:00 → 2026-11-23T00:53:20.923766+00:00 (1000 runs scanned, truncated=False; 381 workflows)
- **API budget:** 147/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| realtime-challenge | main | 2026-11-23T00:48:12Z | 0.09 | failure | NEVER (prune candidate if dormant) |
| Kalshi snapshot (sports markets cache) | main | 2026-11-23T00:47:28Z | 0.1 | failure | NEVER (prune candidate if dormant) |
| portfolio-tracker | main | 2026-11-23T00:47:11Z | 0.1 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/validation-gates.yml | block-d-session-record-2026-11-22 | 2026-11-22T23:55:31Z | 0.96 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/validation-gates.yml | fc-opportunity-frequency-2026-11-22 | 2026-11-22T23:55:27Z | 0.96 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/validation-gates.yml | tally-drift-fix-2026-11-22 | 2026-11-22T23:55:23Z | 0.97 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/validation-gates.yml | push-readiness/handoff-2026-11-22 | 2026-11-22T23:55:19Z | 0.97 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/validation-gates.yml | reconcile/tally-enumeration | 2026-11-22T23:55:14Z | 0.97 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/validation-gates.yml | closing-edge-programme-2026-11-22 | 2026-11-22T23:55:10Z | 0.97 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/validation-gates.yml | research/edge-candidates-2026-11-22 | 2026-11-22T23:55:06Z | 0.97 | failure | NEVER (prune candidate if dormant) |

_(+6 more in JSON)_

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (15 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ audit-denominator-forward-clock-dsr-baselines — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ dsr-baseline-skip — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ research/per-class-edge-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ buffy/verify-live-claim-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ fix/dsr-skip-contract — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00

- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **resolved_flapping**
- resolved: CI Tests → **resolved_flapping**
- resolved: CI Tests → **resolved_flapping**
- resolved: realtime-challenge → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 268.29h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 268.29h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 268.29h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 268.29h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 268.29h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Dynamic Universe Scanner — 0.22h running (p90 0.01h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 1
  - AI Tournament Price Tracker — run 45084836212 killed at 2718.0s mid-step `?` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 41 cancelled run(s) examined (30 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 1 · eviction-shaped: 2 · stack-kill: 8 · pr-close: 0 · external: 30
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 8 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (30) — the true R7 signal, investigate:
    - run 45066914012 DNA Strategy Pipeline — cancelled at 2026-11-22T21:03:08Z (branch main)
    - run 45074597080 No stale DB passwords — cancelled at 2026-11-22T21:53:37Z (branch main)
    - run 45074405598 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-22T21:53:37Z (branch main)
    - run 45081201221 Conflict Marker Check — cancelled at 2026-11-22T23:04:36Z (branch feat/provenance-ledger-2026-11-22)
    - run 45081201297 masking-policy-lint — cancelled at 2026-11-22T23:04:36Z (branch feat/provenance-ledger-2026-11-22)
    - run 45081201216 Tribunal Runtime Gate — cancelled at 2026-11-22T23:04:36Z (branch feat/provenance-ledger-2026-11-22)
    - run 45081201217 DB Password Leak Guard — cancelled at 2026-11-22T23:04:36Z (branch feat/provenance-ledger-2026-11-22)
    - run 45081201218 walkforward-gate — cancelled at 2026-11-22T23:04:37Z (branch feat/provenance-ledger-2026-11-22)
    - run 45081201264 Secret Scan (M-043) — cancelled at 2026-11-22T23:04:37Z (branch feat/provenance-ledger-2026-11-22)
    - run 45081201256 No stale DB passwords — cancelled at 2026-11-22T23:04:37Z (branch feat/provenance-ledger-2026-11-22)
    - _(+10 more in JSON)_
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.2 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.6 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.2 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Equities & Stocks Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ETF Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ETF & Bond Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Refresh Movies Databases (50webs + GoDaddy) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**4** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **211** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
