# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-22T04:40:01.264233+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-14T04:40:01.264233+00:00 → 2026-11-22T04:40:01.264233+00:00 (1000 runs scanned, truncated=False; 376 workflows)
- **API budget:** 117/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| Sign-Coherence Gate | main | 2026-11-22T04:38:47Z | 0.02 | failure | NEVER (prune candidate if dormant) |
| CI Tests | fix/dsr-baselines-h146-key-scrub-2026-11-21 | 2026-11-22T04:38:38Z | 0.02 | failure | NEVER (prune candidate if dormant) |
| QA Market Validation | main | 2026-11-22T04:36:17Z | 0.06 | failure | NEVER (prune candidate if dormant) |
| Forward-Test New Strategies Tracker | main | 2026-11-22T01:23:36Z | 3.27 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (14 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ feat/audit2-data-driven-pods — cadence 24.0h, expect resolution by 2026-11-22T05:39:20.963153+00:00
- CI Tests @ feat/pod-emission-audit — cadence 24.0h, expect resolution by 2026-11-22T05:39:20.963153+00:00
- pod emission audit @ feat/pod-emission-audit — cadence 24.0h, expect resolution by 2026-11-22T05:39:20.963153+00:00
- CI Tests @ fix/wire-emitting-pods — cadence 24.0h, expect resolution by 2026-11-22T05:39:20.963153+00:00
- CI Tests @ test/audit3-ledger-e2e-canary — cadence 24.0h, expect resolution by 2026-11-22T05:39:20.963153+00:00

- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**
- resolved: CI Tests → **escalated_scheduler_dead**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 248.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 248.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 248.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 248.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 248.07h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 3.18h running (p90 0.88h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 4
  - Claude's Test - Portfolio Manager — run 44971049203 killed at 317.0s mid-step `Commit updated state and dashboard` — timeout problem, not churn
  - Meme Coin Scanner v2  Fixed & Monitored — run 44963096223 killed at 306.0s mid-step `Checkout code` — timeout problem, not churn
  - Meta-Strategy Permutation Engine — run 44971085905 killed at 1817.0s mid-step `Commit results` — timeout problem, not churn
  - [torontoevent.net] Deploy Competition to Live Site — run 44968213438 killed at 1816.0s mid-step `Deploy competition files to *** via FTP` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 15 cancelled run(s) examined (15 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 4 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 10
  - external residual (10) — the true R7 signal, investigate:
    - run 44959311577 CI Tests — cancelled at 2026-11-21T22:58:49Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44961362551 walkforward-gate — cancelled at 2026-11-21T23:22:10Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44961362386 Secret Scan (M-043) — cancelled at 2026-11-21T23:22:12Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44961362430 CI Tests — cancelled at 2026-11-21T23:22:25Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44963566753 Money-Ready Registry Gate — cancelled at 2026-11-21T23:49:20Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44963566691 walkforward-gate — cancelled at 2026-11-21T23:49:22Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44963566683 Secret Scan (M-043) — cancelled at 2026-11-21T23:49:22Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44963566675 CI Tests — cancelled at 2026-11-21T23:49:36Z (branch fix/dsr-baselines-h146-key-scrub-2026-11-21)
    - run 44968329356 DNA Strategy Pipeline — cancelled at 2026-11-22T01:18:52Z (branch main)
    - run 44968225415 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-22T02:29:57Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.6 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.4 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Futures Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
  - GHA scan job (reusable) [unknown] — SKIPPED(budget): latest-run probe cap reached
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**1** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **211** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
