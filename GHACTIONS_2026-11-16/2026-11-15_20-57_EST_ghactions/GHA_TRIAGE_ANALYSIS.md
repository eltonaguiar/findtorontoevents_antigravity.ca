# GitHub Actions Triage Analysis — eltonaguiar/findtorontoevents_antigravity.ca

- **Analysis performed:** 2026-11-16 01:13–02:05 UTC = **2026-11-15 20:13–21:05 EST**
- **Delivered:** 2026-11-15 20:57 EST (folder/file date-times are EST per request; UTC noted throughout)
- **Method:** logged-in browser session (Playwright over CDP port 9222, persistent Chrome profile) scraping GitHub Actions HTML pages — zero/minimal REST API usage; cross-checked against a 6-hour 1,000-run API snapshot taken 01:15 UTC, 367-workflow history pulls (15 runs deep each), and local YAML analysis of all 389 workflow files on `origin/main` + 90 remote branches.
- **Scope:** 367 registered workflows (incl. branch/dynamic), 389 workflow files on main (incl. `.disabled`/`.retired`), ~4,000 runs/day (1,000 runs in the 6h window 2026-11-15 19:09 → 2026-11-16 01:15 UTC), 88% schedule-triggered.
- **Triage principle:** a run's conclusion only means anything in sequence context. Every workflow classified into one bucket; worst bucket wins; recovered failures are explicitly suppressed (listed as "NOT an issue") so "green" and "filtered noise" are distinguishable.

---

## Bucket 1 — BROKEN NOW: failed with NO subsequent successful run

| Workflow | Last run (UTC) | Fails / last 15 | Ever passed? | Verdict |
|---|---|---|---|---|
| Mermaid Test Deploy | 2026-11-14 18:23 | 5 | NEVER | Branch-only workflow (not on main). Runs on pushes to 7 doc branches; fails at **Deploy to GH Pages**. Delete from branches or fix the pages step. |
| DB Freshness Check (Legacy Manual) | 2026-05-23 18:28 | 2 | NEVER | Dead 176d, manual-only. Prune. |
| MySQL Q-001 — Create picks table + sync | 2026-05-24 08:48 | 1 | NEVER | Dead 176d. Prune. |
| ML Gatekeeper A/B Bootstrap | 2026-05-27 03:50 | 1 | NEVER | Dead 173d. Prune. |
| DB Secret Scan | 2026-06-05 06:57 | 2 | NEVER | Dead 164d. Prune. |

Severity note: the four dormant ones are stale+broken → one-line prune items, not incidents. Mermaid Test Deploy is the only actively-failing one (its failures come from feature-branch doc pushes, not main).

Transient add: **Model Picks Emission (finpredict-v4)** failed 2026-11-16 01:26 UTC → its next run succeeded 01:39 UTC (`data(model-picks): refresh…`) — recovered (Bucket 2).

## Bucket 2 — RECOVERED / FLAPPING (informational; NOT issues)

Failures in the 7 days to 2026-11-15: ~1,000 (capped view: 12 on Nov 9 → 200+/day Nov 10–14 → 67 on Nov 15 → **zero since 2026-11-15 18:08 UTC** after the `fix(ci)` campaign landed). All of these have a later success — suppressed as issues.

Top flappers (≥5 fails / last 15 runs, still green now):

| Workflow | Fails/15 | Last failure | Failing step / cause |
|---|---|---|---|
| H-002 PEAD Shadow Collector | 14 | 11-13 22:32 | — |
| Algorithm Competition Refresh (+ torontoevent twin) | 13 each | 11-08 | — |
| Daily Prices yfinance Refresh | 13 | 11-13 22:40 | — |
| HC Evaluator Parity Test | 13 | 11-15 08:33 | parity gate scope (fix branch exists: `fix-hc-parity-cost-gate-scope-2026-11-15`) |
| Stale Branch Cleanup / Weekly score quartile spread | 13 | 11-09 | addressed by `fix-stale-failures-2-2026-11-15` |
| robust-edge-miner / Verified pilot daily / Mirror | 10–11 | 11-15 | mirror incremental-cache fix in `fix/mirror-incremental-cache-2026-11-15` |
| Edge stability refresh | 9 | 11-15 01:39 | — |
| Sports endpoint smoke + Playwright | 130 fails/7d | — | **Install Playwright (chromium)** — infra flake |
| ALPHA ENGINE FAST | 123 fails/7d | — | Run Alpha Engine FAST variant |
| ALPHA ENGINE Dynamic Runner | 118 fails/7d | — | Run Alpha Engine (wsl-direct job always skipped) |
| CI Tests | 102 fails/7d | — | **Run all tests (gating)** — real test failures on 3.11 + 3.12 |
| Signal Tracking & Validation | 59 fails/7d | — | **Install dependencies** — infra flake |

## Bucket 3 — QUEUE HOGS

### 3a. Phantom queued runs (51) — THE queue problem
Batches stuck `queued` forever, **0 jobs ever materialized**:
- 2026-08-07 ×1 (100 days old), 2026-08-19 ×6, 2026-09-13/15 ×9, 2026-10-07 ×14, 2026-11-11 ×21 (20:24–20:43 UTC cron stampede)

**All four removal paths were tried and failed (evidence):**
1. REST cancel → `409 Cannot cancel a workflow run that has not been queued yet` (phantom state)
2. REST delete run → `403 Could not delete the workflow run` (token lacks admin delete scope)
3. Browser UI "Cancel workflow" button → `Failed to cancel workflow.`
4. Browser UI "Delete workflow run" → not offered for queued runs

**Action required (repo owner / GitHub Support):** delete with a classic `repo`-scoped PAT or fine-grained token with Actions administration, or open a GitHub Support ticket to purge phantom runs. They do not block current scheduling (affected workflows all run successfully since) but permanently pollute the queue view and concurrency accounting.

### 3b. Runner hogs
- **Discord Bot – Persistent** occupies a hosted runner 24/7 (job `run-bot` in-progress 7h+ at scan time) and stacks duplicate runs `pending` behind it (no concurrency group). Design decision needed: it's a permanent hosted-runner occupant.

### 3c. Cancel churn (runs that never complete)
- **Branch Large File Duplicate Guard: 0 of last 15 runs completed (15/15 cancelled).** Root cause found and **fixed in this delivery** (see Fixes): `on: push` for ALL non-main branches × ONE shared concurrency group `branch-large-file-dup-guard` × 2–3h scan × constant auto-committer push storms → every run cancelled before finishing. The guard currently provides **zero protection** while burning runner minutes. (In-file comment history shows the owner already fought pile-ups here; the earlier `fix(ci): scope the blob guard's concurrency to a single branch` commit did not leave a per-ref group in the file.)
- Mass-cancel batches at **identical timestamps across unrelated workflows** (03:09, 04:03, 04:11, 07:03 UTC on Nov 15: Blacklist Reconciler, rsi5070, Swarm Pick Review, Sign-Coherence Gate…) = **external bulk cancellations** (cleanup runs / incidents), NOT concurrency self-cancels — don't "fix" these configs. (Checked `auto-shutdown-monitor.yml`: it is a DB source monitor, not a run canceller.)
- Genuine self-churn still visible: STOCKSUNIFY2 13/15, Operator Review 12/15, Dynamic Runner 9/15 (wsl-direct job permanently skipped inside it), Academic Strategies Daily 9/15 (recovered, last 3 green).

### 3d. Volume hogs / fan-out chains (~4,000 runs/day)
| Workflow | Runs/6h | Est./day | Driver |
|---|---|---|---|
| Deploy Competition to Live Site | 40 | ~160 | **`workflow_run` fan-in from 8 upstream workflows** (`deploy-competition-to-site.yml`) |
| Meme Coin Scanner v2 | 40 | ~160 | cron ~every 9 min |
| TV Paper TP/SL Watchdog | 23 | ~92 | cron |
| Sports data snapshots | 20 | ~80 | cron |
| Deploy FindCryptoPairs to FTP | 13 | ~52 | fan-in ← Rapid Fire - NOW Scanner |

Other fan-in chains: `deploy-battleground-ftp.yml` ← 3 upstreams; `deploy-fte-events-json.yml` **and** `deploy-fte-index.yml` ← both fire on "Scrape events" (twin double-deploy — redundant); `pine-generator.yml` ← ALPHA ENGINE Live.

## Bucket 4 — STALE / NEVER-RUN (trigger-aware verdicts)

- **Never run (20 active files):** WSL Runner Manager, Battleground Mass Backtest (base), Clear/Closed Picks Command, DB Credentials Test, deploy hotfix workflows (fc-api-env-godaddy, fc-api-hotfix, movieshows3-hotfix), Deploy Strategy Bundle, Fast Stocks Competition, Fix Ghost Cards, Meme Coin Scanner (Fixed with Monitoring), MySQL Dedup Fix, REAL 2-HOUR CHALLENGE, Resolver Step 5-6/7, RL Agent (PPO), Test Fast Variants, Won PNL Contradiction Backfill. → abandoned drafts; delete or wire up. (`rl-agent-ppo.yml` also has `if: false` on its jobs — registered but does nothing by construction.)
- **150–176 days silent (12):** Pick Flow Snapshot (Fast), Copilot cloud agent, Deploy Alpha Engine Dashboard, Deploy FriendTracker, strategy_performance no-regression guard, [torontoevent.net] Deploy Live Monitor APIs, AI Leaderboard Refresh, Battleground Mass Backtest Part 2, POC Picks Checkpoint + others (last runs May–Jul 2026) → dead triggers.
- **Manual-only quiet = correct** (Fetch Movies, Kimi Fetch Movies, deploy hotfixes): not stale by design.
- **Cadence-correct quiet:** monthly (Nov 1: ML Monthly Retrain, Beta Portfolio Refresh, Monthly DNA Tournament, M-060 Calibrator) and weekly (Nov 9 batch) — healthy.
- **Disabled but registered (3):** AI Tournament Pipeline, Real-Time Battle Test, Sports Forensics Weekly → prune or re-enable deliberately.

---

## Extended edge cases (beyond the 4 buckets)

| # | Edge case | Evidence | Recommendation |
|---|---|---|---|
| E1 | **Phantom run limbo** — status `queued` but "never queued": uncancelable (409), undeletable (403), UI-cancel fails, UI-delete hidden | the 51 runs | GitHub Support purge; treat as its own health metric (batch count must not grow) |
| E2 | **Cron stampede at minute 0** — 195 workflows fire at `:00`, 36 at `:30`, 26 at `:15` | YAML cron histogram | Spread minutes (`7 * * * *` etc.); the Nov 11 phantom batch formed inside a 20:24–20:43 stampede |
| E3 | **Cross-workflow concurrency collisions** — `movies-database-refresh` shared by 4 workflows (fetch-movies, fetch-movies-v3, kimi-fetch-movies, deploy-movieshows-all); `edge-stability-shared` ×2; dup-guard unscoped group | YAML scan | Unique group per workflow (fixed for dup-guard here) |
| E4 | **Self-feedback loops** — `on: push` + `git push` in steps: ab_analysis, audit-frontend-manifest, gate-config-emit, incidents-enhancements-nightly, fix-battleground | YAML scan | Keep `[skip ci]` discipline; prefer `workflow_dispatch`/schedule over push for emitters |
| E5 | **`workflow_run` fan-in multiplier** — one upstream completion spawns a deploy run; `deploy-competition-to-site` ← 8 upstreams; FTE twin deploys both fire on "Scrape events" | YAML scan | Gate deploys on changed paths or debounce; merge the FTE twins |
| E6 | **Deprecated action pins (node16-era)** — `slackapi/slack-github-action@v1` (deploy_bundle), `gitleaks/gitleaks-action@v2`, `shivammathur/setup-php@v2`, `dawidd6/action-send-mail@v3`, `peaceiris/actions-gh-pages@v3`, `peter-evans/repository-dispatch@v3` | YAML scan | Bump majors before GitHub drops node16 shims |
| E7 | **Dead-code workflows** — `rl-agent-ppo.yml` with `if: false` jobs; `_dynamic-runner-template.yml` never runs | YAML + run history | Delete |
| E8 | **External mass-cancel events** — identical cancel timestamps across unrelated workflows | run history | Don't misattribute to concurrency config; identify the cancelling actor (owner/agent cleanup) |
| E9 | **Pending-run stacking** — Discord Bot: no concurrency group → duplicate runs queue `pending` behind the 24/7 job | run list | Add `concurrency` + decide if a persistent bot belongs on hosted runners |
| E10 | **Branch-namespace pollution** — `sam-repo/*` branches carry a different project's workflows (deploy-pages, render-sam-videos); `pr/145` + `pr/562…601` (~30 June PR branches) still registered | branch scan | Delete stale branches (biggest single cleanup) |

---

## Main vs other branches — redundant tasks

- **~90 remote branches**, most untouched since Jun–Oct 2026. Every push to them re-runs **branch-era copies** of workflows (273–290 files diverge on old branches).
- **Branch-only workflow files still firing:**
  - `daily-price-refresh.yml` — exists on **~50 branches**, deleted from main. Fires on every push to those branches. Pure waste. (It also produced the "Daily Price Refresh" failures.)
  - `mermaid-test-deploy.yml` — 7 doc branches (multi4-v3, ollama-checks, ollama-checks-v3, salesforceagain-v3, samagain-v4, swarmmethodquality-v2, swarmmethodquality-v4, wiring). **This is the Bucket-1 "Mermaid Test Deploy" failure source.**
  - `forward-ledger-sync.yml` (wired-in/buffy), `winner-hunt-replay.yml` + `deploy-fte-integrations.yml` (fix/js-reference-accuracy-audit, opencode/audit-empty-state), `options-iv-collector.yml.draft`, `alpha-engine-bond.yml` (pr/145).
- **Overlapping task families on main (redundant work):**
  - Live-trading: Live Trading Bot, Live Trading Bot – Canada Edition, (FREE Data), Autonomous Trading Bot, Self-Optimizing Trading Bot — 5 overlapping bots (each 29 fails in the Nov 10–14 window when the shared dependency broke).
  - ML Battleground family ×6 (System D/E/F, Ensemble, Pick Monitor, Daily Retrain).
  - Meme coin ×3 (v2 active ~160 runs/day, Auto Scan, Fixed-with-Monitoring never ran).
  - Gainer ML ×3 (Claude Gainer ML Live, Claude Code Gainer ML Tracker, Crypto Gainer ML Live).
  - Data refresh ×4 (Daily Prices yfinance, Daily Stock Data Refresh, crypto-ohlcv, FRED Macro).
  - DB freshness ×2 (Guardian + Legacy Manual), cross-DB audit ×2 (cross-db-audit + cross-db-consistency-guardian M-005).
  - Intentional twins (keep): `[torontoevent.net]` ×7 second-domain deploys.
- **`fix/*` branches from the Nov 15 fix campaign** (~20) contain partially-unmerged deltas (fix-gha-failures, fix-hc-parity-cost-gate-scope, fix-verified-pilot-series-scalar, fix/ci-pandas-py314-and-mirror-553…): verify none of their fixes were lost vs main before deleting.

## Fixes in this delivery

| Fix | Status | Verification (subsequent runs) |
|---|---|---|
| F1. `branch-large-file-dup-guard.yml`: concurrency group → `branch-large-file-dup-guard-${{ github.ref }}` (per-branch scope) | **Landed in this commit** | Watch dup-guard runs on branch pushes: completed:cancelled ratio must go from 0:15 toward completions (runs take 2–3h) |
| F2. Drain 51 phantom queued runs | **BLOCKED** — all 4 paths failed (see 3a) | Owner token / GitHub Support; monitor batch count stays 51 and does not grow |
| F3. Everything else | Documented above (recommendations) | — |

## Monitoring plan (runs every 4h via session cron)

1. Phantom batch count (baseline 51) — alert on any new batch (new timestamps).
2. Dup-guard completed:cancelled ratio post-fix (baseline 0 completed / 15 cancelled).
3. Bucket-1 list — any new workflow whose latest run failed with no later success.
4. Flapper list deltas (esp. HC Evaluator Parity, robust-edge-miner, Verified pilot, CI Tests).
5. Discord Bot pending stacking + runner occupancy.
6. Any new `is:timed_out` / `is:action_required` (baseline 0 since Nov 1).
