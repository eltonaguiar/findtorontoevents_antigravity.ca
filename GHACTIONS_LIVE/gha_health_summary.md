# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-20T20:39:21.216936+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-12T20:39:21.216936+00:00 → 2026-11-20T20:39:21.216936+00:00 (1000 runs scanned, truncated=False; 376 workflows)
- **API budget:** 121/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| QA Market Validation | main | 2026-11-20T20:25:13Z | 0.24 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-20T19:24:38Z | 1.25 | failure | NEVER (prune candidate if dormant) |
| CI Tests | zoo/p0-recovery-2026-11-20 | 2026-11-20T17:44:53Z | 2.91 | failure | NEVER (prune candidate if dormant) |
| anti-overfit-gate | fix/audit-ledger-population-survivorship | 2026-11-20T17:32:42Z | 3.11 | failure | NEVER (prune candidate if dormant) |
| masking-policy-lint | fix/audit-ledger-population-survivorship | 2026-11-20T17:32:09Z | 3.12 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (29 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ feat/forward-gate-and-ingest — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/forward-observations-contract — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ fix/h119-vintage-and-kill-list-reconcile — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ fix/verdict-fixtures-and-key-redaction — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00
- CI Tests @ feat/wr-semantics-measured-cost-timeline — cadence 24.0h, expect resolution by 2026-11-21T09:40:05.005316+00:00

- resolved: QA Market Validation → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 216.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 216.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 216.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 216.05h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 216.05h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 0
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 0
- **CANCEL BUCKETS (R7)** — 17 cancelled run(s) examined (17 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 0 · eviction-shaped: 2 · stack-kill: 0 · pr-close: 0 · external: 15
  - external residual (15) — the true R7 signal, investigate:
    - run 44770017720 Master Automation Scheduler — cancelled at 2026-11-20T16:07:24Z (branch main)
    - run 44773752557 Secret Scan (M-043) — cancelled at 2026-11-20T16:30:52Z (branch review/grok-verdict-2026-11-20)
    - run 44777409382 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-20T16:51:33Z (branch main)
    - run 44779141110 Secret Scan (M-043) — cancelled at 2026-11-20T17:02:29Z (branch withdraw-1-of-154-20261120)
    - run 44779141200 Tribunal Runtime Gate — cancelled at 2026-11-20T17:02:40Z (branch withdraw-1-of-154-20261120)
    - run 44774244922 DNA Strategy Pipeline — cancelled at 2026-11-20T17:03:11Z (branch main)
    - run 44780744274 No stale DB passwords — cancelled at 2026-11-20T17:10:48Z (branch anti-overfit-gate-crypto-pf-20261120)
    - run 44788426028 No stale DB passwords — cancelled at 2026-11-20T17:59:02Z (branch pbo-align-pf-labels-dsr-20261120)
    - run 44788426227 Money-Ready Registry Gate — cancelled at 2026-11-20T17:59:03Z (branch pbo-align-pf-labels-dsr-20261120)
    - run 44805526889 Tribunal Runtime Gate — cancelled at 2026-11-20T19:48:33Z (branch deploy-lease-financial-surfaces-20261120)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.1 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Edge stability refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Equities & Stocks Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ETF Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ETF & Bond Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Refresh Movies Databases (50webs + GoDaddy) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**1** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **307** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
