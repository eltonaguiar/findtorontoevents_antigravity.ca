# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-16T04:49:22.530654+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-08T04:49:22.530654+00:00 → 2026-11-16T04:49:22.530654+00:00 (1000 runs scanned, truncated=False; 360 workflows)
- **API budget:** 88/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| ALPHA ENGINE - Dynamic Runner (Cloud or Local) | main | 2026-11-16T04:33:34Z | 0.26 | failure | yes |
| .github/workflows/mysql-q001-sync.yml | main | 2026-11-16T01:54:11Z | 2.92 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/ml-gatekeeper-ab-bootstrap.yml | main | 2026-11-16T01:54:10Z | 2.92 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/mysql-q001-sync.yml | fix/disable-dead-workflows-2026-11-16 | 2026-11-16T01:51:06Z | 2.97 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/ml-gatekeeper-ab-bootstrap.yml | fix/disable-dead-workflows-2026-11-16 | 2026-11-16T01:51:06Z | 2.97 | failure | NEVER (prune candidate if dormant) |
| Feed Health Check | main | 2026-11-16T04:49:19Z | 9999.0 | failure | yes |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (2 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- ALPHA ENGINE - Dynamic Runner (Cloud or Local) @ main — cadence 24.0h, expect resolution by 2026-11-18T05:01:32.113934+00:00
- Feed Health Check @ main — cadence 24.0h, expect resolution by 2026-11-18T05:49:22.530654+00:00

- resolved: Regime Terminal  HMM Live Scanner → **resolved_flapping**
- resolved: CI Tests → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 21
  - run 43095833399 Rapid Fire - NOW Scanner queued 2026-11-11T20:24:10Z (age 104.42h) — uncancelable ⇒ GitHub Support batch
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 104.22h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 104.22h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 104.22h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 104.22h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 10.58h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing):** 0
- **External mass-cancel clusters:** 0
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.9 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (25 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Growth Stock Screener Daily [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-103 Forward Logger [monthly] — SKIPPED(budget): latest-run probe cap reached
  - HC Evaluator Parity Test [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **248** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
