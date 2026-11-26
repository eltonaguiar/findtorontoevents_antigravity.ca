# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-26T00:57:16.117073+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-18T00:57:16.117073+00:00 → 2026-11-26T00:57:16.117073+00:00 (1000 runs scanned, truncated=False; 388 workflows)
- **API budget:** 147/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| audit3 ledger | fix/audit3-ftp-fallback | 2026-11-26T00:51:17Z | 0.1 | failure | NEVER (prune candidate if dormant) |
| masking-policy-lint | ci/2026-11-25-gha-digest | 2026-11-25T23:57:33Z | 1.0 | failure | NEVER (prune candidate if dormant) |
| ALPHA ENGINE - Live Autonomous Scanner | fix/safe-push-retry-budget | 2026-11-25T23:43:57Z | 1.22 | failure | NEVER (prune candidate if dormant) |
| Deploy Rise of the Claw Dashboard | fix/pages-artifact-wait | 2026-11-25T22:37:42Z | 2.33 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (8 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ research/commodity-tsmom-v3-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-26T21:40:13.119473+00:00
- Sign-Coherence Gate @ main — cadence 24.0h, expect resolution by 2026-11-27T05:39:29.754198+00:00
- Asset Class Freshness Watchdog @ main — cadence 24.0h, expect resolution by 2026-11-27T17:40:08.573783+00:00
- audit3 ledger @ main — cadence 24.0h, expect resolution by 2026-11-27T17:40:08.573783+00:00
- Mirror: findtorontoevents.ca  torontoevent.net @ main — cadence 24.0h, expect resolution by 2026-11-27T21:39:34.440634+00:00

- resolved: Forward-Test New Strategies Tracker → **resolved_flapping**
- resolved: What Worked Active Picks Insights → **resolved_flapping**
- resolved: QA Market Validation → **resolved_flapping**
- resolved: portfolio-tracker → **resolved_flapping**
- resolved: DNA Genome Daily Pipeline → **resolved_flapping**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 340.36h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 340.36h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 340.35h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 340.35h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 340.35h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 2
  - Discord Bot  Persistent — 3.42h running (p90 n/a)
  - Deploy Rise of the Claw Dashboard — 0.02h running (p90 0.0h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 3
  - Claude's Test - Portfolio Manager — run 45728444953 killed at 318.0s mid-step `Fetch prior portfolio state from production` — timeout problem, not churn
  - Claude's Test - Portfolio Manager — run 45730474225 killed at 319.0s mid-step `Fetch prior portfolio state from production` — timeout problem, not churn
  - Meta-Strategy Permutation Engine — run 45718033983 killed at 1817.0s mid-step `Commit results` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 31 cancelled run(s) examined (30 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 3 · eviction-shaped: 1 · stack-kill: 6 · pr-close: 0 · external: 21
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 6 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (21) — the true R7 signal, investigate:
    - run 45702850695 realtime-challenge — cancelled at 2026-11-25T21:27:00Z (branch main)
    - run 45705253215 realtime-challenge — cancelled at 2026-11-25T21:42:37Z (branch main)
    - run 45706846769 portfolio-tracker — cancelled at 2026-11-25T21:53:10Z (branch main)
    - run 45707403730 realtime-challenge — cancelled at 2026-11-25T21:56:50Z (branch main)
    - run 45711573578 portfolio-tracker — cancelled at 2026-11-25T22:25:16Z (branch main)
    - run 45711972928 realtime-challenge — cancelled at 2026-11-25T22:27:56Z (branch main)
    - run 45713209968 ALPHA ENGINE - Live Autonomous Scanner — cancelled at 2026-11-25T22:38:35Z (branch main)
    - run 45714047186 realtime-challenge — cancelled at 2026-11-25T22:42:22Z (branch main)
    - run 45715565714 Secret Scan (M-043) — cancelled at 2026-11-25T22:44:42Z (branch ci/land-orphan-tool-workflows)
    - run 45715565773 Validation Gates (P0.0h) — cancelled at 2026-11-25T22:44:43Z (branch ci/land-orphan-tool-workflows)
    - _(+1 more in JSON)_
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.0 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.2 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (24 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - FRED Macro Refresh [daily] — SKIPPED(budget): latest-run probe cap reached
  - fx-cost-overlap [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
  - GHA scan job (reusable) [unknown] — SKIPPED(budget): latest-run probe cap reached
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Growth Stock Screener Daily [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**3** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **386** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
