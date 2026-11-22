# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-22T00:51:57.292463+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-14T00:51:57.292463+00:00 → 2026-11-22T00:51:57.292463+00:00 (1000 runs scanned, truncated=False; 376 workflows)
- **API budget:** 133/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| QA Market Validation | main | 2026-11-22T00:47:16Z | 0.08 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/dsr-baselines-h146-key-scrub-2026-11-21 | 2026-11-22T00:04:32Z | 0.79 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-21T19:23:34Z | 5.47 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (16 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ test/audit3-cli-smoke — cadence 24.0h, expect resolution by 2026-11-22T01:49:24.110831+00:00
- CI Tests @ hotfix/restore-denylist-hits — cadence 24.0h, expect resolution by 2026-11-22T01:49:24.110831+00:00
- CI Tests @ hotfix/audit3-merge-repair — cadence 24.0h, expect resolution by 2026-11-22T01:49:24.110831+00:00
- CI Tests @ feat/audit2-data-driven-pods — cadence 24.0h, expect resolution by 2026-11-22T05:39:20.963153+00:00
- CI Tests @ feat/pod-emission-audit — cadence 24.0h, expect resolution by 2026-11-22T05:39:20.963153+00:00

- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 244.27h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 244.27h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 244.27h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 244.26h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 244.26h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 2
  - Discord Bot  Persistent — 5.22h running (p90 n/a)
  - [torontoevent.net] Deploy Competition to Live Site — 0.1h running (p90 0.02h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 10
  - AsterDEX Paper Trading — run 44945400151 killed at 739.0s mid-step `Deploy dashboard to FTP` — timeout problem, not churn
  - Claude Gainer Short-Term Predictor — run 44942480715 killed at 2119.0s mid-step `Run Short-Term Scanner` — timeout problem, not churn
  - Claude's Test - Portfolio Manager — run 44945866308 killed at 317.0s mid-step `Run portfolio manager` — timeout problem, not churn
  - Daily Feed Summary — run 44947803487 killed at 317.0s mid-step `Deploy to production via FTP` — timeout problem, not churn
  - Daily Top-Picks Filter — run 44946029550 killed at 497.0s mid-step `Regenerate filter` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 23 cancelled run(s) examined (23 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 10 · eviction-shaped: 0 · stack-kill: 0 · pr-close: 0 · external: 13
  - external residual (13) — the true R7 signal, investigate:
    - run 44942561997 Cross-System Signal Aggregator — cancelled at 2026-11-21T20:15:33Z (branch main)
    - run 44942898926 Outcome Resolver  Validate Unresolved Picks — cancelled at 2026-11-21T20:15:45Z (branch main)
    - run 44945294727 Cross-System Signal Aggregator — cancelled at 2026-11-21T20:44:45Z (branch main)
    - run 44946705689 DNA Strategy Pipeline — cancelled at 2026-11-21T21:02:48Z (branch main)
    - run 44947868725 Cross-System Signal Aggregator — cancelled at 2026-11-21T21:14:25Z (branch main)
    - run 44959311577 CI Tests — cancelled at 2026-11-21T22:58:49Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44961362551 walkforward-gate — cancelled at 2026-11-21T23:22:10Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44961362386 Secret Scan (M-043) — cancelled at 2026-11-21T23:22:12Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44961362430 CI Tests — cancelled at 2026-11-21T23:22:25Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44963566753 Money-Ready Registry Gate — cancelled at 2026-11-21T23:49:20Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.1 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
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
  - Forex Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**6** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **180** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
