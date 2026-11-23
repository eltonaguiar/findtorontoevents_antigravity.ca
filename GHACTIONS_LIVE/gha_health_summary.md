# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-23T04:40:58.132862+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-15T04:40:58.132862+00:00 → 2026-11-23T04:40:58.132862+00:00 (1000 runs scanned, truncated=False; 382 workflows)
- **API budget:** 147/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| realtime-challenge | main | 2026-11-23T04:36:04Z | 0.08 | failure | NEVER (prune candidate if dormant) |
| portfolio-tracker | main | 2026-11-23T04:27:58Z | 0.22 | failure | NEVER (prune candidate if dormant) |
| CI Tests | pr/h201-pit-universe-2026-11-23 | 2026-11-23T03:21:41Z | 1.32 | failure | yes |
| Forward-Test New Strategies Tracker | main | 2026-11-23T01:25:16Z | 3.26 | failure | NEVER (prune candidate if dormant) |
| Kalshi snapshot (sports markets cache) | main | 2026-11-23T01:25:04Z | 3.27 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (16 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ audit-denominator-forward-clock-dsr-baselines — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ dsr-baseline-skip — cadence 24.0h, expect resolution by 2026-11-23T09:39:52.599485+00:00
- CI Tests @ research/per-class-edge-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ buffy/verify-live-claim-2026-11-22 — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00
- CI Tests @ fix/dsr-skip-contract — cadence 24.0h, expect resolution by 2026-11-24T09:39:18.782703+00:00

- resolved: realtime-challenge → **escalated_still_broken**
- resolved: portfolio-tracker → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 272.08h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 272.08h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 272.08h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 272.08h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 272.08h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - Discord Bot  Persistent — 3.81h running (p90 0.25h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 4
  - Claude's Test - Portfolio Manager — run 45106065360 killed at 317.0s mid-step `Commit updated state and dashboard` — timeout problem, not churn
  - Daily Top-Picks Filter — run 45090696527 killed at 487.0s mid-step `Run actions/setup-python@v6` — timeout problem, not churn
  - Dynamic Universe Scanner — run 45090112801 killed at 917.0s mid-step `Commit updated universe` — timeout problem, not churn
  - Meta-Strategy Permutation Engine — run 45106046198 killed at 1819.0s mid-step `Commit results` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 59 cancelled run(s) examined (30 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 4 · eviction-shaped: 1 · stack-kill: 27 · pr-close: 0 · external: 27
  - stack-kill sub-buckets: supersede: 0 · cancel-in-progress: 27 (supersede = 'higher priority waiting request' + newer same/referenced run ≤10m)
  - external residual (27) — the true R7 signal, investigate:
    - run 45088391003 Secret Scan (M-043) — cancelled at 2026-11-23T00:24:05Z (branch pr/h201-pit-universe-2026-11-23)
    - run 45089875247 Discord Bot  Persistent — cancelled at 2026-11-23T00:52:26Z (branch main)
    - run 45093589725 Secret Scan (M-043) — cancelled at 2026-11-23T01:16:35Z (branch pr/h201-pit-universe-2026-11-23)
    - run 45093589766 No stale DB passwords — cancelled at 2026-11-23T01:16:35Z (branch pr/h201-pit-universe-2026-11-23)
    - run 45093589791 DB Password Leak Guard — cancelled at 2026-11-23T01:16:35Z (branch pr/h201-pit-universe-2026-11-23)
    - run 45093589704 Conflict Marker Check — cancelled at 2026-11-23T01:16:36Z (branch pr/h201-pit-universe-2026-11-23)
    - run 45093589833 Tribunal Runtime Gate — cancelled at 2026-11-23T01:16:45Z (branch pr/h201-pit-universe-2026-11-23)
    - run 45090903049 DNA Strategy Pipeline — cancelled at 2026-11-23T01:19:41Z (branch main)
    - run 45094390336 Conflict Marker Check — cancelled at 2026-11-23T01:24:50Z (branch pr/h201-pit-universe-2026-11-23)
    - run 45094390299 DB Password Leak Guard — cancelled at 2026-11-23T01:24:51Z (branch pr/h201-pit-universe-2026-11-23)
    - _(+7 more in JSON)_
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 3.1 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.6 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.8 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.1 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.1 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (26 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - ETF & Bond Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Feature Stability Check (Weekly) [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Refresh Movies Databases (50webs + GoDaddy) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Fix Battleground Deployment [daily] — SKIPPED(budget): latest-run probe cap reached
  - Forex Smart Picks Scanner [weekly] — SKIPPED(budget): latest-run probe cap reached
  - Forward Benchmark Ledger Refresh (Daily) [daily] — SKIPPED(budget): latest-run probe cap reached
  - Futures Agent [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**2** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **261** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
