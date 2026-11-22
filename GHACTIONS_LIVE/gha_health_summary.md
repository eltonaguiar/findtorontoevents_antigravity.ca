# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-22T16:39:22.664640+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-14T16:39:22.664640+00:00 → 2026-11-22T16:39:22.664640+00:00 (1000 runs scanned, truncated=False; 377 workflows)
- **API budget:** 99/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| realtime-challenge | main | 2026-11-22T16:34:08Z | 0.09 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-22T13:23:48Z | 3.26 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (17 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ zoo/p0-recovery-2026-11-20 — cadence 24.0h, expect resolution by 2026-11-22T21:39:21.216936+00:00
- CI Tests @ audit-denominator-forward-clock-dsr-baselines — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ dsr-baseline-skip — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ research/per-class-edge-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ buffy/verify-live-claim-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00

- resolved: realtime-challenge → **escalated_still_broken**
- resolved: Kalshi snapshot (sports markets cache) → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 260.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 260.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 260.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 260.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 260.05h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 3.47h running (p90 0.88h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 1
  - Pine Script Generator — run 45025576413 killed at 1817.0s mid-step `Commit and push if changed` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 6 cancelled run(s) examined (6 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 1 · eviction-shaped: 2 · stack-kill: 0 · pr-close: 0 · external: 3
  - external residual (3) — the true R7 signal, investigate:
    - run 45018258872 Secret Scan (M-043) — cancelled at 2026-11-22T11:38:47Z (branch research/commodity-tsmom-v3-2026-11-22)
    - run 45018258856 CI Tests — cancelled at 2026-11-22T11:39:00Z (branch research/commodity-tsmom-v3-2026-11-22)
    - run 45022726132 DNA Strategy Pipeline — cancelled at 2026-11-22T13:02:50Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.1 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.9 runs/day
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

**3** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **196** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
