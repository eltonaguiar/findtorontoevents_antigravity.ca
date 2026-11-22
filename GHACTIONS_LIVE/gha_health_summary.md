# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-22T12:40:02.478591+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-14T12:40:02.478591+00:00 → 2026-11-22T12:40:02.478591+00:00 (1000 runs scanned, truncated=False; 377 workflows)
- **API budget:** 111/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| realtime-challenge | main | 2026-11-22T12:34:31Z | 0.09 | failure | NEVER (prune candidate if dormant) |
| Kalshi snapshot (sports markets cache) | main | 2026-11-22T12:28:49Z | 0.19 | failure | NEVER (prune candidate if dormant) |
| CI Tests | main | 2026-11-22T09:59:40Z | 2.67 | failure | yes |
| CI Tests | research/horizon-allocation-review-2026-11-22 | 2026-11-22T09:57:28Z | 2.71 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/portfolio-tracking-2026-11-22 | 2026-11-22T09:52:21Z | 2.79 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/commodity-roll-adjust-2026-11-22 | 2026-11-22T09:19:11Z | 3.35 | failure | NEVER (prune candidate if dormant) |
| CI Tests | feat/h201-forward-pod | 2026-11-22T08:47:03Z | 3.88 | failure | NEVER (prune candidate if dormant) |
| CI Tests | research/per-class-edge-2026-11-22 | 2026-11-22T08:38:56Z | 4.02 | failure | NEVER (prune candidate if dormant) |
| CI Tests | buffy/verify-live-claim-2026-11-22 | 2026-11-22T08:05:56Z | 4.57 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/dsr-skip-contract | 2026-11-22T08:05:20Z | 4.58 | failure | NEVER (prune candidate if dormant) |

_(+1 more in JSON)_

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (18 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ zoo/p0-recovery-2026-11-20 — cadence 24.0h, expect resolution by 2026-11-22T21:39:21.216936+00:00
- CI Tests @ audit-denominator-forward-clock-dsr-baselines — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ dsr-baseline-skip — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ research/per-class-edge-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ buffy/verify-live-claim-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00

- resolved: Unified Audit Dashboard → **escalated_scheduler_dead**
- resolved: QA Market Validation → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 256.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 256.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 256.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 256.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 256.07h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 5.33h running (p90 n/a)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 0
- **CANCEL BUCKETS (R7)** — 12 cancelled run(s) examined (12 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 0 · eviction-shaped: 0 · stack-kill: 2 · pr-close: 0 · external: 10
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 2 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (10) — the true R7 signal, investigate:
    - run 44999402830 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-22T07:42:21Z (branch main)
    - run 44999402795 No stale DB passwords — cancelled at 2026-11-22T07:42:22Z (branch main)
    - run 45000956768 Secret Scan (M-043) — cancelled at 2026-11-22T08:03:55Z (branch buffy/verify-live-claim-2026-11-22)
    - run 45000956792 CI Tests — cancelled at 2026-11-22T08:04:09Z (branch buffy/verify-live-claim-2026-11-22)
    - run 45001245827 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-22T08:09:30Z (branch main)
    - run 45002249042 No stale DB passwords — cancelled at 2026-11-22T08:19:45Z (branch docs/edge-proof-plan)
    - run 45002249090 Tribunal Runtime Gate — cancelled at 2026-11-22T08:19:58Z (branch docs/edge-proof-plan)
    - run 45003209031 DNA Strategy Pipeline — cancelled at 2026-11-22T09:02:56Z (branch main)
    - run 45018258872 Secret Scan (M-043) — cancelled at 2026-11-22T11:38:47Z (branch research/commodity-tsmom-v3-2026-11-22)
    - run 45018258856 CI Tests — cancelled at 2026-11-22T11:39:00Z (branch research/commodity-tsmom-v3-2026-11-22)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.8 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.5 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Refresh Movies Databases (50webs + GoDaddy) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forex Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - forward observations ingest [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forward-Test New Strategies Tracker [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**4** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **247** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
