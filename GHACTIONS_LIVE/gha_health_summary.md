# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-16T12:53:57.420259+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-08T12:53:57.420259+00:00 → 2026-11-16T12:53:57.420259+00:00 (1000 runs scanned, truncated=False; 361 workflows)
- **API budget:** 94/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| CI Tests | tmp/s2-emitters | 2026-11-16T07:26:17Z | 5.46 | failure | NEVER (prune candidate if dormant) |
| CI Tests | tmp/s3-ci-hygiene | 2026-11-16T07:22:30Z | 5.52 | failure | NEVER (prune candidate if dormant) |
| CI Tests | tmp/s1-data-gates | 2026-11-16T07:22:21Z | 5.53 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (4 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ tmp/s2-emitters — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ tmp/s3-ci-hygiene — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ tmp/s1-data-gates — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00
- CI Tests @ fix/audit-truth-layer-2026-11-16 — cadence 24.0h, expect resolution by 2026-11-18T09:51:04.687016+00:00

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 21
  - run 43095833399 Rapid Fire - NOW Scanner queued 2026-11-11T20:24:10Z (age 112.5h) — uncancelable ⇒ GitHub Support batch
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 112.3h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 112.3h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 112.3h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 112.3h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 6.31h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 0
- **CANCEL BUCKETS (R7)** — 6 cancelled run(s) examined (6 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 0 · eviction-shaped: 0 · stack-kill: 0 · pr-close: 0 · external: 6
  - external residual (6) — the true R7 signal, investigate:
    - run 43827578528 CI Tests — cancelled at 2026-11-16T08:06:06Z (branch main)
    - run 43831006655 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-16T08:29:25Z (branch main)
    - run 43831599703 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-16T08:31:30Z (branch main)
    - run 43825062157 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-16T08:42:02Z (branch fix/gha-p0-scheduled-paths-2026-11-16)
    - run 43831886388 DNA Strategy Pipeline — cancelled at 2026-11-16T09:02:49Z (branch main)
    - run 43833436188 DNA Strategy Pipeline — cancelled at 2026-11-16T09:34:19Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.6 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.9 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 1.0 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.8 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (25 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Incidents + Enhancements — Nightly Page Render [daily] — SKIPPED(budget): latest-run probe cap reached
  - Index All Creator Content [daily] — SKIPPED(budget): latest-run probe cap reached
  - macd_rsi_m048 Shadow Generator [daily] — SKIPPED(budget): latest-run probe cap reached
  - Mercury 2  Weekly Retrain [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ML Battleground Daily Retrain [daily] — SKIPPED(budget): latest-run probe cap reached
  - ML Gatekeeper Train A/B (Phase D) [daily] — SKIPPED(budget): latest-run probe cap reached
  - ML Monthly Full Retrain [monthly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **232** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
