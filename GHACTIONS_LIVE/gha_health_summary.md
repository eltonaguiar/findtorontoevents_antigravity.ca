# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-22T20:39:45.821229+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-14T20:39:45.821229+00:00 → 2026-11-22T20:39:45.821229+00:00 (1000 runs scanned, truncated=False; 377 workflows)
- **API budget:** 93/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| realtime-challenge | main | 2026-11-22T20:34:00Z | 0.1 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-22T19:23:43Z | 1.27 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (16 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ zoo/p0-recovery-2026-11-20 — cadence 24.0h, expect resolution by 2026-11-22T21:39:21.216936+00:00
- CI Tests @ audit-denominator-forward-clock-dsr-baselines — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ dsr-baseline-skip — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ research/per-class-edge-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ buffy/verify-live-claim-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00

- resolved: audit3 Health Monitor → **resolved_flapping**
- resolved: realtime-challenge → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 264.06h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 264.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 264.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 264.06h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 264.06h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 1.63h running (p90 0.77h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 1
  - Claude's Test - Portfolio Manager — run 45054760786 killed at 306.0s mid-step `Checkout` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 3 cancelled run(s) examined (3 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 1 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 1
  - external residual (1) — the true R7 signal, investigate:
    - run 45044286274 DNA Strategy Pipeline — cancelled at 2026-11-22T17:02:44Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.4 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.9 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.6 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Deploy findtorontoevents.ca core site [daily] — SKIPPED(budget): latest-run probe cap reached
  - DNA Mutation Cycle [daily] — SKIPPED(budget): latest-run probe cap reached
  - DXY State Update [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Edge decay monitor [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Edge stability refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Edge stability refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - Equities & Stocks Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**1** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **173** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
