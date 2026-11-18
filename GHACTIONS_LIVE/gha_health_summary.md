# GHA Health Summary (R1-R12)

- **Generated:** 2026-11-18T16:40:13.231369+00:00 · repo `eltonaguiar/findtorontoevents_antigravity.ca`
- **Window:** 2026-11-10T16:40:13.231369+00:00 → 2026-11-18T16:40:13.231369+00:00 (1000 runs scanned, truncated=False; 363 workflows)
- **API budget:** 99/300 calls used

## 1. BROKEN NOW (action required)

| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |
|---|---|---|---|---|---|
| QA Market Validation | main | 2026-11-18T16:27:00Z | 0.22 | failure | NEVER (prune candidate if dormant) |
| Picks NOW Refresh | main | 2026-11-18T13:37:01Z | 3.05 | failure | NEVER (prune candidate if dormant) |
| Deploy MOVIESHOWS2 + MOVIESHOWS3 (All 3 Domains) | main | 2026-11-18T13:24:23Z | 3.26 | failure | NEVER (prune candidate if dormant) |
| Mirror: findtorontoevents.ca  torontoevent.net | main | 2026-11-18T13:24:55Z | 3.26 | failure | NEVER (prune candidate if dormant) |

## 2. FLAPPING (watch list + failing steps)

_None — no workflow has ≥5 fails in its last 15 runs with a green latest._

**R2 monitor-next-run (14 watching):** auto-watch next 2 occurrences; green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).
- CI Tests @ fix/audit-pm-ingest-shadow-pin-2026-11-16 — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00
- CI Tests @ fix/dashboard-cse-new-picks-int — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00
- CI Tests @ fix/audit-remaining-honesty — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00
- CI Tests @ tmp/s9-ghost-rootcause — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00
- CI Tests @ fix/audit-quant-fixes-2026-11-16 — cadence 24.0h, expect resolution by 2026-11-18T21:39:18.854093+00:00

- resolved: Sidecar Status Markdown Update → **resolved_flapping**
- resolved: DNA Genome Daily Pipeline → **resolved_flapping**
- resolved: Deploy Competition to Live Site → **resolved_flapping**
- resolved: Picks-Now Live PnL (hourly) → **resolved_flapping**
- resolved: QA Market Validation → **escalated_still_broken**

## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)

- **Phantom queued runs (> 24h, 0 jobs):** 20
  - run 43096994785 Portfolio Trackers (Real Money + Theory) queued 2026-11-11T20:35:58Z (age 164.07h) — uncancelable ⇒ GitHub Support batch
  - run 43096994522 Sports endpoint smoke + Playwright queued 2026-11-11T20:35:58Z (age 164.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097000114 Deploy Vetted Master-Picks queued 2026-11-11T20:36:01Z (age 164.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097004990 Sustained Gainer Confluence Scanner queued 2026-11-11T20:36:04Z (age 164.07h) — uncancelable ⇒ GitHub Support batch
  - run 43097010333 Claude Gainer ML  Live Scanner queued 2026-11-11T20:36:06Z (age 164.07h) — uncancelable ⇒ GitHub Support batch
- **Runner hogs (in_progress > 2h or > 2x p90):** 1
  - [torontoevent.net] Deploy Competition to Live Site — 0.27h running (p90 0.02h)
- **Cancel churn (≥50% cancelled/15, own tick spacing, timeout-shaped excluded):** 0
- **Timeout kills (R5/R6 `timeout-kill`, excluded from churn):** 4
  - 2hour-challenge — run 44302931664 killed at 1818.0s mid-step `Run 2-hour trading challenge` — timeout problem, not churn
  - Meme Coin Scanner v2  Fixed & Monitored — run 44291342363 killed at 319.0s mid-step `Deploy meme_scanner_fixed.php to server` — timeout problem, not churn
  - What Worked Active Picks Insights — run 44308090286 killed at 622.0s mid-step `Commit results` — timeout problem, not churn
  - 🧠 Smart Money Intelligence — run 44291866566 killed at 318.0s mid-step `Fetch analyst ratings + price targets` — timeout problem, not churn
- **CANCEL BUCKETS (R7)** — 6 cancelled run(s) examined (6 jobs probes; created_at herds are cron stamps, not cancel evidence):
  - timeout-shaped: 4 · eviction-shaped: 1 · stack-kill: 0 · pr-close: 0 · external: 1
  - external residual (1) — the true R7 signal, investigate:
    - run 44305045498 DNA Strategy Pipeline — cancelled at 2026-11-18T13:04:56Z (branch main)
- **workflow_run fan-in chains:** 7
  - Deploy Competition to Live Site ← 8 upstreams ≈ 4.4 runs/day
  - [torontoevent.net] Deploy Competition to Live Site ← 4 upstreams ≈ 0.8 runs/day
  - Deploy Battleground to FTP ← 3 upstreams ≈ 0.9 runs/day
  - Deploy FindCryptoPairs to FTP ← 1 upstreams ≈ 1.6 runs/day
  - Deploy findtorontoevents.ca next/events.json ← 1 upstreams ≈ 0.0 runs/day

## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)

- **Perpetual skips (R8):** 1
  - dynamic-alpha-engine — skip ratio None — known always-skipped job: measured 2026-11-16 audit: job if: always false (static config)
- **Stale-by-cadence (R9):** 40 (25 dispatch-only workflows EXEMPT by design)
  - Dynamic Runner Template [unknown] — NEVER RUN with live trigger (unknown) — dead trigger or broken filter
  - Funding-Rate Archive Collector [daily] — SKIPPED(budget): latest-run probe cap reached
  - Gate Config Emit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Strategy Genome Evolution [weekly] — SKIPPED(budget): latest-run probe cap reached
  - GHA scan job (reusable) [unknown] — SKIPPED(budget): latest-run probe cap reached
  - GHA stale workflows audit [daily] — SKIPPED(budget): latest-run probe cap reached
  - Goldmine Tracker - Archive & Maintain [daily] — SKIPPED(budget): latest-run probe cap reached
  - H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) [weekly] — SKIPPED(budget): latest-run probe cap reached
- **Branch-only push waste (R10):** 0
- **Prune rows (R1: never passed + dormant):** 0

## 5. NOT AN ISSUE (recovered) — suppressed count

**15** workflow/branch group(s) had a success complete AFTER their most recent failure — suppressed per triage principle (recovered failures are explicitly filtered so 'green' and 'filtered noise' stay distinguishable).
- additionally **184** group(s) were plain green (no failure in window).
- queue-hog / stale rows above are live issues, NOT included in this suppressed count.

---

**Rule status:** R1=ok · R2=ok · R3=ok · R4=ok · R5=ok · R6=ok · R7=ok · R8=ok · R9=ok · R10=ok · R11=ok · R12=ok

_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. R12 is a static known-findings config block. This report is detection-only: it never retries, kills or cancels anything._
