# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-19T12:41:43.601128+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-11T12:41:43.601128+00:00 → 2026-11-19T12:41:43.601128+00:00 (1000 runs scanned, truncated=False; 369 workflows)
- **API budget:** 143/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| audit3 ledger | main | 2026-11-19T12:33:59Z | 0.13 | failure | yes |
| Mirror: findtorontoevents.ca  torontoevent.net | main | 2026-11-19T12:32:53Z | 0.15 | failure | NEVER (prune candidate if dormant) |
| [torontoevent.net] Deploy Competition to Live Site | main | 2026-11-19T12:31:46Z | 0.17 | failure | yes |
| QA Market Validation | main | 2026-11-19T12:31:03Z | 0.18 | failure | NEVER (prune candidate if dormant) |
| CI Tests | audit3-dsr-global-trials | 2026-11-19T11:51:11Z | 0.84 | failure | NEVER (prune candidate if dormant) |
| CI Tests | audit3-intrabar-resolver | 2026-11-19T10:00:26Z | 2.69 | failure | NEVER (prune candidate if dormant) |
| CI Tests | feat/audit3-intraday-stop-panel | 2026-11-19T09:55:46Z | 2.77 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/alpha-slice-scan-tie | 2026-11-19T09:07:22Z | 3.57 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/alpha-slice-scan-test | 2026-11-19T09:05:36Z | 3.6 | failure | NEVER (prune candidate if dormant) |
| CI Tests | feat/alpha-slice-scan | 2026-11-19T09:04:22Z | 3.62 | failure | NEVER (prune candidate if dormant) |

_(+2 more in JSON)_

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (20 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ feat/forward-gate-and-ingest — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/forward-observations-contract — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ fix/h119-vintage-and-kill-list-reconcile — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ fix/verdict-fixtures-and-key-redaction — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/wr-semantics-measured-cost-timeline — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00

- resolved: CI Tests → **resolved_flapping**
- resolved: QA Market Validation → **escalated_still_broken**
- resolved: GHCOPILOT prospective paper monitor → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 184.1h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 184.1h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 184.1h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 184.09h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 184.09h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 3.6h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 4
  - Claude's Test - Portfolio Manager — run 44491016672 killed at 317.0s mid-step `Commit updated state and dashboard` — timeout problem, not churn
  - Claude's Test - Portfolio Manager — run 44518483065 killed at 317.0s mid-step `Commit updated state and dashboard` — timeout problem, not churn
  - Meta-Strategy Permutation Engine — run 44511004454 killed at 1819.0s mid-step `Commit results` — timeout problem, not churn
  - Outcome Resolver  Validate Unresolved Picks — run 44490759838 killed at 1518.0s mid-step `Commit resolved picks` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 28 cancelled run(s) examined (28 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 4 · eviction-shaped: 2 · stack-kill: 15 · pr-close: 0 · external: 7
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 15 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (7) — the true R7 signal, investigate:
    - run 44479095983 No stale DB passwords — cancelled at 2026-11-19T07:22:24Z (branch feat/forward-gate-and-ingest)
    - run 44491055680 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-19T08:51:55Z (branch main)
    - run 44492223825 No stale DB passwords — cancelled at 2026-11-19T08:59:24Z (branch main)
    - run 44488360061 DNA Strategy Pipeline — cancelled at 2026-11-19T09:03:17Z (branch main)
    - run 44490223095 Cross-System Signal Aggregator — cancelled at 2026-11-19T09:18:37Z (branch main)
    - run 44500250917 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-19T09:54:39Z (branch main)
    - run 44500401215 Conflict Marker Check — cancelled at 2026-11-19T09:57:35Z (branch coms/update-2026-11-19)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.5 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Forward-Test New Strategies Tracker [daily] — SKIPPED(budget): latest-run probe cap reached
  - FRED Macro Refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Funding-Rate Archive Collector [daily] — SKIPPED(budget): latest-run probe cap reached
  - Futures Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
  - GHA scan job (reusable) [unknown] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **244** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
