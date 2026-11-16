# GHA Peer Review & Prioritized Actions Summary

- **Generated:** 2026-11-16 01:17 EST (2026-11-16T06:17:49Z)
- **Author/worktree:** `ghactions-v3` (`/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/ghactions-v3`)
- **Scope:** Review of ghactions work in `ghactions`, `ghactions-v2`, `ghactions-v3`, `ghactions-v4`; current `origin/main` state check; recommended/prioritized code fixes and file locations.

## 1. Peer work reviewed

| Worktree | Branch / HEAD | GHA-relevant work | Key files |
|---|---|---|---|
| `ghactions-v3` (this session) | `fix/gha-cron-regime-hardening` @ `e6f3932991de` (ahead 2 of `origin/main`, behind 152 at review time; **not pushed**) | Hardened data-commit/push steps for 3 workflows; docs with verification/revert | `.github/workflows/regime-terminal.yml`, `.github/workflows/audit-impact-tracker.yml`, `.github/workflows/ueps-pick-runner.yml`, `updates/2026-11-16-regime-terminal-commit-hardening.md`, `updates/2026-11-16-gha-best-practices-hardening.md` |
| `ghactions-v4` | `fix/gha-disable-broken-workflows` @ `04a30246aef` | Queue-audit tool normalization + best-practices findings report (no diff vs `origin/main` in branch comparison shown; changes local/unpushed state needs care) | `tools/gha_queue_audit.py`, `reports/gha_best_practices_findings.md` |
| `ghactions-v2` | `docs/alpha-verify-2-2026-11-16` @ `5ce2bdfc32f` (tracks origin) | Extensive triage/audit artifacts and verification notes (ALPHA recheck, queue/stale/failure analyses, cron-stagger planning, best-practices approach) | `GHACTIONS_2026-11-16/**` (e.g. `2026-11-16_05-15Z_queue-hogs-and-failures/GHACTIONS_QUEUE_HOGS_AND_FAILURES.MD`, `2026-11-16_05-35Z_stale-jobs-and-db-quality/GHACTIONS_STALE_JOBS_AND_DB_QUALITY.MD`, `2026-11-15_21-45_EST_ghactions/06_GHA_BEST_PRACTICES_APPROACH.md`), `GHACTIONS_2026-11-16/2026-11-16_03-45Z_alpha-fix-verification/VERIFICATION.md` |
| `ghactions` (base worktree) | `ghactions` @ `99a44602602` | No recent GHA-remediation commit observed in log; contains historical summaries/tools across repo | Review for reference only; avoid mixing unrelated changes |

### Cross-check vs peers (validated)
- **Confirmed fixed on `origin/main`:** cron-drift test assertions (`tests/test_skyrocket_detector_wireup.py`, `tests/test_ueps_workflow_yaml.py`) now align with staggered schedules — targeted suite passes (45). CI failure on SHA `7b48625e` (`43796591828`) was the known drift; newer `main` includes fixes.
- **Confirmed/accepted from peer audits:** ghost queued runs persist as un-cancellable via `gh`/REST (v2/v3/v4 report class of issue; counts vary by snapshot — treat live UI/API snapshot as source of truth); minute-0 cron concentration and large fleet hygiene gaps (missing timeouts/permissions/concurrency, weak commit-step safeguards) are real; ALPHA Dynamic Runner push/commit hang was the critical failure mode (peers addressed via timeout/safe-push evolution — verify latest post-fix runs).
- **Corrected/superseded context:** some peer “verified fixed” claims were premature for intermediate patches; re-verify against latest run IDs on `origin/main`. v4 `tools/gha_queue_audit.py` normalization is a useful tooling improvement but should be reviewed/merged deliberately (branch not clearly ahead of main).

## 2. My work (ghactions-v3) — files & verification

**Branch:** `fix/gha-cron-regime-hardening` (clean, from `origin/main`)
**Commits:**
- `60141976a83b` — `ci: harden regime-terminal commit and push step`
- `e6f3932991de` — `ci: harden audit-impact and ueps commit steps per best practices`

**Modified/added files:**
- `.github/workflows/regime-terminal.yml` — `if: always()`, `timeout-minutes: 5` on commit step, `assert_no_conflict_markers.sh`, authenticated remote (`TOKEN_FOR_PUSH`), retry push with explicit failure after 3 attempts.
- `.github/workflows/audit-impact-tracker.yml` — same hardening pattern + explicit final failure.
- `.github/workflows/ueps-pick-runner.yml` — bounded timeout, conflict guard, authenticated retries, warning+exit on exhausted retries (step remains `continue-on-error`).
- `updates/2026-11-16-regime-terminal-commit-hardening.md` — change/rationale/verification/revert.
- `updates/2026-11-16-gha-best-practices-hardening.md` — best-practice checklist, gaps, verification/revert.
- `GHACTIONS_2026-11-16/2026-11-16_01-17_EST_peer-review-and-actions/SUMMARY.md` — this report.

**Verification:**
- `python3 -c "import yaml; yaml.safe_load(...)"` for modified workflows: **OK**
- `python3 -m pytest tests/test_skyrocket_detector_wireup.py tests/test_ueps_workflow_yaml.py -q`: **45 passed**

**Revert:** `git revert e6f3932991de 60141976a83b` (or cherry-pick selectively). **Push status:** not pushed.

## 3. Prioritized code fixes (recommended)

### P0 — Reliability & active failures (do first)
1. **Publish/review v3 hardening PR**
   - **What:** Push `fix/gha-cron-regime-hardening`, open PR, validate next scheduled/manual runs for `Regime Terminal`, `Audit Impact Tracker`, `UEPS Pick Runner`.
   - **Where:** `.github/workflows/regime-terminal.yml`, `.github/workflows/audit-impact-tracker.yml`, `.github/workflows/ueps-pick-runner.yml`, docs in `updates/2026-11-16-*.md`.
   - **Why:** Prevents silent push failures, hung commit steps, conflict-marker commits; aligns with `safe_push`/repo safety patterns.
   - **Risk:** Low (scoped to commit/push steps).

2. **Harden `ALPHA ENGINE - Dynamic Runner` commit/push path**
   - **What:** Refactor “Commit results” to bounded step timeout + `if: always()` where appropriate, conflict-marker guard, authenticated remote, and `safe_push.sh`/equivalent retry with explicit terminal outcome; preserve intentional self-heal/non-fatal semantics only if documented and safe.
   - **Where:** `.github/workflows/alpha-engine-dynamic-runner.yml` (and any shared script it invokes).
   - **Evidence:** run `43799911205` timed out at 15m in commit step after long no-output period.
   - **Risk:** Medium (behavioral/compute semantics) — validate on `workflow_dispatch`.

3. **Fix `Feed Health Check` data dependency failure**
   - **What:** Ensure required payload/system rows exist or adjust check/generation contract: `pm_kalshi_re_signals`, `pm_polymarket_re_signals` missing in run `43806313904`. Align producers, `audit-dashboard`/payload generation, and health thresholds (treat truly optional shadow feeds explicitly).
   - **Where:** `audit_trail/feed_health_check.py` (or invoked script), `audit_trail/dashboard_generator.py`, `.github/workflows/audit-dashboard.yml`, PM signal producers/workflows, deployed `/audit/data/*` artifacts.
   - **Risk:** Medium (data correctness/alerting).

### P1 — Correctness & observability
4. **Audit artifact/deploy gaps (`/audit`)**
   - **What:** Restore/fix generation+deploy for `strategy_tribunal_latest.json` (404), refresh stale `strategy_ic_analysis.json` and `pick_summary_stats.json`, and resolve PM sidecar endpoint exposure (`prediction_market_consensus`, `polymarket_signals`, `kalshi_signals`) vs inclusion in `dashboard_data.json`; wire hypothesis tracker only if required by product/spec.
   - **Where:** `.github/workflows/audit-dashboard.yml`, `audit_trail/dashboard_generator.py`, `audit_trail/universal_pick_resolver.py`, `tools/deploy_audit_files.py`, `tools/strategy_kill_tribunal.py`, relevant producers, `audit_dashboard/*`.
   - **Risk:** Medium (deploy/user-visible).

5. **Adopt v4 queue-audit tooling fix (reviewed)**
   - **What:** Review and merge `tools/gha_queue_audit.py` normalization and keep `reports/gha_best_practices_findings.md` as living guidance (or move to `updates/`/`docs/` per convention).
   - **Where:** `ghactions-v4`: `tools/gha_queue_audit.py`, `reports/gha_best_practices_findings.md`.
   - **Risk:** Low if scoped.

### P2 — Fleet hygiene (incremental, avoid mass risky rewrites)
6. **Add `concurrency`, `timeout-minutes`, explicit `permissions` to highest-churn cron/data-commit workflows first**
   - **Where:** prioritize workflows with frequent schedules/pushes and known contention (start from audit lists; ~68 no job timeout, ~94 no permissions, ~182 no concurrency in scan).
   - **Pattern:** repo-safe groups (include workflow/ref as appropriate), bounded job/step timeouts, least-privilege permissions.

7. **Standardize auto-commit steps**
   - **What:** Reuse `safe_push.sh` + conflict-marker guard + authenticated remote + explicit terminal outcome for commit workflows (212 flagged missing full safeguards).
   - **Where:** highest-impact workflows first (e.g. audit-impact-like, alpha/data pipelines), then batches with per-workflow review.

8. **Cron staggering & queue reduction**
   - **What:** Continue spreading minute-0 schedules; monitor queue depth/durations (v4/v2 tooling).
   - **Where:** `.github/workflows/*.yml` schedules; track via `tools/gha_queue_audit.py` / reports.

### P3 — Supply chain & ops
9. **Pin critical `uses:` actions to commit SHAs** (phased; start with checkout/setup/python/upload/deploy actions in critical workflows).
10. **Ghost queued runs cleanup (manual):** clear via Actions UI or GitHub Support/admin-scoped API as applicable (API `gh run cancel`/REST returned 409/un-cancellable in prior checks).
11. **Retire/archive never-run/abandoned or owner-decided-disabled workflows** per peer audits, only with explicit confirmation.

## 4. Results / blockers
- **Done now:** peer review completed; v3 hardening implemented and verified locally; this stamped summary written.
- **Not done:** no pushes/PRs created; no mass workflow refactor; no live `/audit` data fixes deployed; no manual ghost-run UI cleanup.
- **Blockers/needs decision:** push permission/confirmation for `fix/gha-cron-regime-hardening`; admin/UI access for ghost queue purge; product/data decisions for PM sidecar + hypothesis tracker exposure; acceptance of non-fatal vs fatal semantics for alpha-engine commit retries.

## 5. Quick file index
- v3 fixes/docs: `.github/workflows/regime-terminal.yml`, `.github/workflows/audit-impact-tracker.yml`, `.github/workflows/ueps-pick-runner.yml`, `updates/2026-11-16-regime-terminal-commit-hardening.md`, `updates/2026-11-16-gha-best-practices-hardening.md`
- v3 summary (this file): `GHACTIONS_2026-11-16/2026-11-16_01-17_EST_peer-review-and-actions/SUMMARY.md`
- v4 artifacts: `reports/gha_best_practices_findings.md`, `tools/gha_queue_audit.py`
- v2 audit corpus: `GHACTIONS_2026-11-16/**` (notably `2026-11-16_05-15Z_queue-hogs-and-failures/`, `2026-11-16_05-35Z_stale-jobs-and-db-quality/`, `2026-11-15_21-45_EST_ghactions/`)
