# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-16T04:01:32.113934+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-08T04:01:32.113934+00:00 → 2026-11-16T04:01:32.113934+00:00 (1000 runs scanned, truncated=False; 360 workflows)
- **API budget:** 88/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Regime Terminal  HMM Live Scanner | main | 2026-11-16T03:58:55Z | 0.04 | failure | yes |
| CI Tests | main | 2026-11-16T03:56:52Z | 0.08 | failure | yes |
| ALPHA ENGINE - Dynamic Runner (Cloud or Local) | main | 2026-11-16T03:43:32Z | 0.3 | failure | yes |
| .github/workflows/mysql-q001-sync.yml | main | 2026-11-16T01:54:11Z | 2.12 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/ml-gatekeeper-ab-bootstrap.yml | main | 2026-11-16T01:54:10Z | 2.12 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/mysql-q001-sync.yml | fix/disable-dead-workflows-2026-11-16 | 2026-11-16T01:51:06Z | 2.17 | failure | NEVER (prune candidate if dormant) |
| .github/workflows/ml-gatekeeper-ab-bootstrap.yml | fix/disable-dead-workflows-2026-11-16 | 2026-11-16T01:51:06Z | 2.17 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (3 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- Regime Terminal  HMM Live Scanner @ main — cadence 1.0h, expect resolution by 2026-11-16T07:01:32.113934+00:00
- CI Tests @ main — cadence 24.0h, expect resolution by 2026-11-18T05:01:32.113934+00:00
- ALPHA ENGINE - Dynamic Runner (Cloud or Local) @ main — cadence 24.0h, expect resolution by 2026-11-18T05:01:32.113934+00:00

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 21
  - run 43095833399 Rapid Fire - NOW Scanner queued 2026-11-11T20:24:10Z (age 103.62h) — uncancelable ⇒ GitHub Support batch
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 103.43h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 103.43h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 103.43h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 103.42h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 4
  - Discord Bot  Persistent — 9.79h running (p90 n/a)
  - Copy Trader Forward Test — 0.33h running (p90 0.16h)
  - Signal Recorder — 0.33h running (p90 0.05h)
  - Winner Pattern Precursor Scanner — 0.14h running (p90 0.02h)
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
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Futures Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Growth Stock Screener Daily [weekly] — SKIPPED(budget): latest-run probe cap reached
  - H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**0** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **230** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
