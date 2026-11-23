# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-23T08:41:26.404040+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-15T08:41:26.404040+00:00 → 2026-11-23T08:41:26.404040+00:00 (1000 runs scanned, truncated=False; 385 workflows)
- **API budget:** 139/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| realtime-challenge | main | 2026-11-23T08:37:00Z | 0.07 | failure | NEVER (prune candidate if dormant) |
| portfolio-tracker | main | 2026-11-23T08:30:53Z | 0.18 | failure | NEVER (prune candidate if dormant) |
| CI Tests | ci/verification-test-gate | 2026-11-23T07:47:04Z | 0.91 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-23T07:27:44Z | 1.23 | failure | NEVER (prune candidate if dormant) |
| CI Tests | verify/claim-retirement | 2026-11-23T07:07:51Z | 1.56 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/peer-claim-b5-split-2026-11-23 | 2026-11-23T06:28:45Z | 2.21 | failure | NEVER (prune candidate if dormant) |
| Sign-Coherence Gate | main | 2026-11-23T05:26:33Z | 3.25 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/peer-claim-verification-shallow-clone-2026-11-23 | 2026-11-23T05:11:32Z | 3.5 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (19 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ audit-denominator-forward-clock-dsr-baselines — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ dsr-baseline-skip — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ research/per-class-edge-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ buffy/verify-live-claim-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ fix/dsr-skip-contract — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00

- resolved: Kalshi snapshot (sports markets cache) → **resolved_flapping**
- resolved: realtime-challenge → **escalated_still_broken**
- resolved: portfolio-tracker → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 276.09h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 276.09h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 276.09h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 276.09h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 276.09h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 1.95h running (p90 0.21h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 14
  - CI — run 45113051785 killed at 605.0s mid-step `Run actions/checkout@v4` — timeout problem, not churn
  - CI — run 45113595340 killed at 605.0s mid-step `Run actions/checkout@v4` — timeout problem, not churn
  - CI — run 45114001281 killed at 605.0s mid-step `Run actions/checkout@v4` — timeout problem, not churn
  - Claude's Test - Portfolio Manager — run 45120281269 killed at 318.0s mid-step `Commit updated state and dashboard` — timeout problem, not churn
  - Claude's Test - Portfolio Manager — run 45127901967 killed at 317.0s mid-step `Fetch prior portfolio state from production` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 27 cancelled run(s) examined (26 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 14 · eviction-shaped: 1 · stack-kill: 2 · pr-close: 0 · external: 10
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 2 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (10) — the true R7 signal, investigate:
    - run 45114001308 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-23T04:51:41Z (branch main)
    - run 45112571482 DNA Strategy Pipeline — cancelled at 2026-11-23T05:04:45Z (branch main)
    - run 45125973758 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-23T06:46:34Z (branch main)
    - run 45127569359 Secret Scan (M-043) — cancelled at 2026-11-23T06:57:56Z (branch copilot/hub-audit-2026-11-23)
    - run 45127569337 CI Tests — cancelled at 2026-11-23T07:02:09Z (branch copilot/hub-audit-2026-11-23)
    - run 45127919869 [torontoevent.net] Deploy Rise of the Claw — cancelled at 2026-11-23T07:02:20Z (branch main)
    - run 45133810591 Secret Scan (M-043) — cancelled at 2026-11-23T07:50:10Z (branch test/fix-remote-map-env-var)
    - run 45133810591 Secret Scan (M-043) — cancelled at 2026-11-23T07:50:10Z (branch test/fix-remote-map-env-var)
    - run 45133810585 CI Tests — cancelled at 2026-11-23T07:50:26Z (branch test/fix-remote-map-env-var)
    - run 45126345332 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-23T08:31:52Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 2.9 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.5 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.6 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.1 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - fx-cost-overlap [weekly] — NEVER RUN with live trigger (weekly) — dead trigger or broken filter
  - GHA scan job (reusable) [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Insider Trades Refresh [weekly] — SKIPPED(budget): latest-run probe cap reached
  - macd_rsi_m048 Shadow Generator [daily] — SKIPPED(budget): latest-run probe cap reached
  - Mercury 2  Weekly Retrain [weekly] — SKIPPED(budget): latest-run probe cap reached
  - ML Feedback Retrain  Learn from Closed Trades [daily] — SKIPPED(budget): latest-run probe cap reached
  - ML Gatekeeper Train A/B (Phase D) [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**4** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **317** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
