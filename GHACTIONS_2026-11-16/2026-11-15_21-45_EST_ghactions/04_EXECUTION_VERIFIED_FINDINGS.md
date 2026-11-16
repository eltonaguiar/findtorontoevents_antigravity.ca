# 04 — Execution Record, Verified Findings & Open Items

**STAMP:** 2026-11-15_21-45_EST_ghactions (analysis window 2026-11-15 20:13 – 2026-11-16 02:45 UTC)
Companion to `GHA_TRIAGE_ANALYSIS.md`, `02_FIX_BATCH_1_DEDUP.md`, the `2026-11-15_21-00-33_EST_ghactions/`
8-file audit set, and `AGENT_PROMPT_job_analysis.md` (same folder).

## 1. Push status (this session's work — all landed)

| Item | Commit | State |
|---|---|---|
| Fix batch 1: 9 duplicate/dead workflows removed | `c2393512637` | on main, verified (02:05 UTC tick produced no run of the deleted daily workflow) |
| dup-guard concurrency serialize | `a174e2d00c2` | on main; first non-cancelled run observed (56 min in progress) — ratio verdict at 04:00 UTC monitor |
| GHA_TRIAGE_ANALYSIS.md + 02_FIX_BATCH_1_DEDUP.md | `a113ce6a9a7` | on main |
| Backup/undo branch `backup/gha-audit-2026-11-16` | @ `c2393512637` | on origin — durable pre/post SHA anchor (main SHAs churn via bot rebase races; see `push_chain_impact.md`) |

Nothing of this session's work remains unpushed.

## 2. NEW VERIFIED FINDING — 5 sports workflows are disabled in the GitHub UI (browser-verified 02:45 UTC)

Converts `orphan_items.md`'s "UNVERIFIED carrier claim" to **confirmed fact**:

| Workflow | UI state | Impact if left off |
|---|---|---|
| sports-betting-refresh.yml (Odds Refresh & Auto-Settle) | **DISABLED** | **HIGH** — no odds refresh, no auto-place, **no auto-settle**; picks never resolve → win rate / ROI / CLV silently freeze on `/live-monitor/sports-betting.html` |
| sports-data-snapshots.yml | **DISABLED** | MED-HIGH — Pinnacle snapshots age past the 15-min staleness guard → Shin devig path silently lost |
| sports-prediction-market-sync.yml | **DISABLED** | MED — PM divergence badges/boost go stale |
| sports-forensics-weekly.yml | **DISABLED** | LOW — loses Monday canary |
| sports-smoke-and-e2e.yml | **DISABLED** | MED — loses hourly git-HEAD-vs-FTP drift canary |

(Also disabled: `ai-tournament-pipeline.yml`, `battle_test.yml` — previously known.)
**Decision needed from the owner** (not auto-re-enabled, since someone disabled them deliberately):
seasonal/cost pause vs accidental kill-switch. Note `/audit` is unaffected by design — it drops
sports at data load (`_applyGlobalSportsFilter`, "User directive: ensure sports is removed from
findtorontoevents.ca/audit").

## 3. Downstream /audit verdicts (this session's changed workflows)

| Change | /audit dependency | Evidence |
|---|---|---|
| cross-db-consistency.yml deleted | **NONE** | only referrer of `cross_db_*` is `tools/cross_db_consistency.py` itself; `deploy_audit_files.py` deploy list has no `cross_db_*` entry |
| db-freshness-check.yml deleted | **NONE rendered** (latent trap) | no php/js/html consumer of `db_freshness.json` (independent double-check agrees with `orphan_items.md`); file's only committer is gone → it now freezes. Fix option: port a commit step into `db-freshness-guardian.yml` (owner decision) |
| live_trading_canada_free.yml deleted | **NONE** | `trading_results.json`/`trading_bot.log` have zero consumers in `audit_dashboard/` + `audit_trail/` |
| meme-scanner-fixed.yml + 4×.retired + daily-price-refresh.yml.disabled | **NONE** | inert/manual/never-ran |
| dup-guard `cancel-in-progress:false` | **NONE on /audit** | its "Update job health page" writer now actually completes (previously 0/15 runs finished) |

## 4. Open items after reconciling all GHACTIONS_* folders

| # | Item | Owner/Status |
|---|---|---|
| 1 | **Sports disabled decision** (§2) | **OWNER DECISION** — highest-value open item |
| 2 | `site_impact_audit.md` per-file "/audit dependency" column | sibling `analyst-2` (their push gate #4) |
| 3 | 3-writer push race confirmation in `push_chain_impact.md` | sibling `queue_auditor` (their push gate #5) |
| 4 | Cron stagger execution (189/360 at `:00`; deterministic plan ready in `cron_stagger_plan.md`, 2 tie-breaks) | unexecuted — mechanical 356-file edit, awaiting a fix pass (use `AGENT_PROMPT_job_analysis.md`) |
| 5 | Branch cleanup execution (159 stale >30d) | HELD: `git cherry` verdicts — lost-fix audit found ~45 branches with unmerged work incl. provably LOST June tools (rescue list in the task report); unshallow fetch running to restore ancestry checks. Deletion only for zero-unique-content branches, with SHA undo map |
| 6 | 51 phantom queued runs | BLOCKED for good (4 removal paths tested incl. logged-in browser UI) → GitHub Support / admin-scoped PAT |
| 7 | Mermaid Test Deploy (only remaining failed-without-success item) | fires only on `wiring` branch; delete there or leave (harmless outside that branch) |
| 8 | `claude-gainer-ml-live.yml` vs `claude-gainer-tracker.yml` both write `updates/data/antigravity_ml_performance.json` (silent clobber, 48 runs/day) | merge-first decision needed |
| 9 | Meme-scanner v2 `*/10` cadence (144 runs/day) | trading-behavior knob — product decision, not CI hygiene |

## 5. Verified-check table (fix batch 1 subsequent runs)

| Check | Result |
|---|---|
| Cross-DB consistency guardian (M-005) run at 02:00 UTC tick (deleted 01:47) | NONE — pass |
| Cross-DB Strategy Consistency Audit survivor | unaffected — pass |
| Failures since 2026-11-16 | 0 — pass |
| Phantom queue | 51±1 stable — pass |
| Discord Bot – Persistent 24/7 runner | sole 7h+ runner, by design |
| dup-guard post-fix | 01:39 run survived 56 min (first ever); final ratio at 04:00 UTC monitor cron |
