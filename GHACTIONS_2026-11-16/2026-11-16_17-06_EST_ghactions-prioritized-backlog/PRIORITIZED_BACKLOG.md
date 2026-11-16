# GHActions — Prioritized Backlog (post-v3 wrap-up)

**Stamp:** 2026-11-16 17:06 EST (2026-11-16T22:06Z)
**Author seat:** `glyph-cluster` (COMS `inbox/gx10-c9b9/ghactions-v3/glyph-cluster`)
**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
**Companion docs:** `GHACTIONS_2026-11-16/2026-11-16_15-40_EST_ghactions-v3-wrapup/WRAPUP.md` (merged via #861), `GHACTIONS_2026-11-16/2026-11-16_01-17_EST_peer-review-and-actions/SUMMARY.md`.

## 0. Confirmed state on `main` (2026-11-16T22:06Z)
- **Merged:** #836 (P0 scheduled-path repairs), #841 (v3 commit-step hardening), #847 (audit n/a for infinite PF / explosive Sharpe), #839 (CI hygiene, merged by owner), #859 (auditpage docs wrap), #861 (v3 wrap-up docs).
- **Verified GREEN post-merge on `main`:**
  - `ALPHA ENGINE - Dynamic Runner` — 6/6 recent runs **success** (10:30→20:26Z); commit-step hang is resolved.
  - `Feed Health Check` — run `43962282193` (21:39Z) **success** (optional PM shadow feeds no longer hard-fail).
  - `Regime Terminal HMM Live Scanner` — run `43962132091` (21:38Z) **success** (hardened commit step working).
- **Open PR:** #856 `fix(audit): skip int CSE new_picks so the dashboard can deploy` — **CONFLICTING** + `test (3.11)`/`test (3.12)` FAILURE (run `43949904751`). Touches `audit_trail/dashboard_generator.py`, `tests/test_dashboard_cse_new_picks.py`, `updates/2026-11-16-dashboard-cse-new-picks-crash.md`.

## 1. Prioritized items

### P0 — Dashboard deploy blocker (do first)
1. **Fix PR #856 (`fix/dashboard-cse-new-picks-int`).**
   - Rebase onto `origin/main`, resolve conflicts, then reproduce the failing `test (3.11)`/`test (3.12)` (run `43949904751`) and fix without reverting intended behavior (`skip int CSE new_picks`).
   - Rationale: title says it unblocks dashboard deploy; until merged, the audit dashboard deploy path may stay broken for CSE int new_picks.
   - Files: `audit_trail/dashboard_generator.py`, `tests/test_dashboard_cse_new_picks.py`.

### P1 — Audit `/audit` data & deploy integrity
2. **Missing/stale audit artifacts (deploy-impact).**
   - `strategy_tribunal_latest.json` → 404 on live `/audit/data/`; `strategy_ic_analysis.json` stale (~2026-05-29); `pick_summary_stats.json` stale (~2026-05-25).
   - Trace generation + deploy in `.github/workflows/audit-dashboard.yml`, `tools/strategy_kill_tribunal.py`, `tools/deploy_audit_files.py`, `audit_trail/dashboard_generator.py`; verify live endpoints after next deploy.
3. **Prediction-market feeds exposure.**
   - Decide: keep `pm_kalshi_re_signals` / `pm_polymarket_re_signals` as paper/shadow/optional (current) vs first-class sidecar JSON endpoints (`prediction_market_consensus`, `polymarket_signals`, `kalshi_signals` currently 404) or fold into `dashboard_data.json`.
4. **Hypothesis tracker wiring.**
   - Confirm whether the hypothesis tracker sidecar/panel is required end-to-end on live `/audit` or remains sidecar-only.

### P1 — Queue hygiene (manual/admin)
5. **Purge ghost queued runs.**
   - Runs created 2026-11-11 (~20:24–20:43Z) are un-cancellable via `gh`/REST (`409 Cannot cancel a workflow run that has not been queued yet`). Requires Actions UI or an admin-scoped PAT (per peer `GHA_TRIAGE_ANALYSIS.md`, admin scope deletes where normal token gets `403`).
   - Until purged, queue-depth readings are unreliable.

### P2 — Fleet hygiene (incremental, reviewed batches — never mass-rewrite)
6. **Add `concurrency` + job `timeout-minutes` + least-privilege `permissions`** to the highest-frequency cron workflows first (repo scan: ~68 missing job timeout, ~94 missing `permissions`, ~182 missing `concurrency`; ~188 minute-0 crons concentrate load).
7. **Standardize auto-commit steps** on `safe_push.sh` + `assert_no_conflict_markers.sh` + authenticated remote + explicit terminal outcome (~212 commit workflows lack full safeguards).
8. **Pin `uses:` actions to commit SHAs** (start with `actions/checkout`, `actions/setup-python`, `actions/upload-artifact`) in a separate reviewed PR.

### P2 — Data quality (from peer v2 DB audit; needs owner decision)
9. **Clamp/quarantine PnL outliers** (`|pnl_pct| > 100`) — two rows (SHIBUSDT 1,000,000%, ARBUSDT 18,611%) flip COMMODITY PF 0.79→6,690; exclude from class aggregates until fixed.
10. **Resolve OPEN-row backlog** — `trading_picks` 91,855 OPEN vs 21 ACTIVE (74,394 >30 days); `at_local_picks` 108.6M ACTIVE rows.
11. **Re-arm frozen resolution lanes** — `lm_signals.resolved_at` frozen since 2026-02-16; `trading_picks.intrabar_resolved_at` frozen since 2026-06-09 (never-run `Resolver Step 5-6/7` workflows are likely owners).
12. **Reject/repair impossible geometry** (LONG TP<entry / SL>entry, SHORT TP>entry / SL<entry; ~2,688 `trading_picks` + ~5,808 `at_raw_picks`) and fix `ml_enhanced` date-only `closed_at` writes (1,810 inverted timestamps).
13. **Retire never-run / owner-decided-disabled workflows** (19 never-run drafts; 5 sports + ai-tournament-pipeline + battle_test already `disabled_manually`) — only with explicit owner confirmation.

## 2. Open questions
1. PM feeds: permanent paper/shadow/optional, or promote to first-class endpoints?
2. Hypothesis tracker: required on live dashboard or sidecar-only?
3. Ghost queued runs: approve admin-scoped purge vs GitHub Support?
4. DB data-quality fixes (P2 §9–13): assign owner + approve approach (clamp vs quarantine, truncation policy for `at_local_picks`)?
5. Fleet hygiene: approve incremental batch PRs (timeouts/concurrency/permissions, then SHA pinning) each gated on green CI?

## 3. Suggested future-agent prompts
- **#856 finisher:** "Rebase `fix/dashboard-cse-new-picks-int` onto `origin/main`, resolve conflicts, run `python3 -m pytest tests/test_dashboard_cse_new_picks.py -q` plus the CI Tests command to fix the failing 3.11/3.12 jobs (run `43949904751`), push, confirm green, squash-merge."
- **Audit deploy:** "Fix `strategy_tribunal_latest.json` 404 + stale `strategy_ic_analysis.json`/`pick_summary_stats.json` in the `audit-dashboard` generation/deploy path; verify live `/audit/data/*` freshness after deploy."
- **Queue purge:** "Purge 2026-11-11 ghost queued runs via Actions UI or admin-scoped PAT; re-run `tools/gha_queue_audit.py` after."
- **Fleet batch:** "One PR per batch: add `concurrency`/`timeout-minutes`/`permissions` to top ~20 highest-frequency workflows; then SHA-pin checkout/setup-python/upload-artifact. Never mass-rewrite; require green CI per batch."
- **COMS:** "Update your seat (`COMS register --agent <seat> --todo ... --done ...`) and post to `inbox/<host>/<worktree>/all`. No secrets on the bus."