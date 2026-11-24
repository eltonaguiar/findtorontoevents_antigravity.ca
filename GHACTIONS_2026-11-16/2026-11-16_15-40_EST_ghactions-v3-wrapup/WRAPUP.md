# GHActions-v3 — Final Wrap-Up / Tracking Summary

**Stamp:** 2026-11-16 15:40 EST (2026-11-16T20:40:30Z)
**Seat:** `glyph-cluster` · COMS inbox `inbox/gx10-c9b9/ghactions-v3/glyph-cluster` · swarmbus id `gx10-c9b9__ghactions-v3__glyph-cluster` (host `gx10-c9b9`)
**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
**Local worktree:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/ghactions-v3`
**Local branch (now stale/merged):** `fix/gha-cron-regime-hardening` (commits `60141976a83`, `e6f3932991d`)
**Deployed to GitHub:** merged via PRs #841, #836, #847 on `main` (see §3).

---

## 1. Objective (what this worktree was for)
Audit GitHub Actions health for the repo (failures without later success, stale/queue-blocked jobs, warnings/silent fails), harden the highest-risk data-commit/push workflows per GHA best practices, review peers' work across the `ghactions`, `ghactions-v2`, `ghactions-v3`, `ghactions-v4` worktrees, and merge any ready PRs.

## 2. Final disposition
| Item | State |
|---|---|
| v3 hardening code | **MERGED** to `main` via PR **#841** (merge commit `70053a21fddaf6b6b302cf28bdc16cc541482ba2`, merged 2026-11-16T17:30:26Z) |
| Peer PR #836 (P0 scheduled-path repairs) | **MERGED** by me 2026-11-16T17:30:44Z |
| Peer PR #847 (audit: n/a for infinite PF / explosive Sharpe) | **MERGED** by me 2026-11-16T19:59:54Z |
| Peer PR #839 (CI hygiene: no-op gating, guardian v1.1, queue:max, permissions+pins, deploy hygiene) | **LEFT OPEN** — failing `test (3.11)`/`test (3.12)` (run `43822754710`) + `CONFLICTING` vs `main` |
| Local branch `fix/gha-cron-regime-hardening` | Superseded by #841; no push needed (my commits are in `main` via #841). Working tree only has untracked `GHACTIONS_2026-11-16/` artifacts (report-only). |

## 3. What I fixed (merged to `main`)

### 3.1 PR #841 — harden data-commit/push steps (my core deliverable)
Files changed (commits `b875f925aebb0e897849713f0f38b335a7970971`, `5d20835b8e481bb502828403842e910c4614980a`):
- `.github/workflows/regime-terminal.yml`
  - Commit step: added `if: always()`, `timeout-minutes: 5` (was 15 with no always), `bash .github/scripts/assert_no_conflict_markers.sh` before commit, authenticated `origin` remote via `TOKEN_FOR_PUSH`, retry loop (`pull --rebase` + `safe_push.sh`) with explicit `::error::Failed to push regime state after 3 attempts` + `exit 1` (previously could silently no-fail).
- `.github/workflows/audit-impact-tracker.yml`
  - Commit step: same hardening — `if: always()`, `timeout-minutes: 5`, conflict-marker guard, authenticated remote, 3-attempt retry with explicit failure.
- `.github/workflows/ueps-pick-runner.yml`
  - Commit step: added `timeout-minutes: 5`, conflict-marker guard, authenticated remote, 3-attempt retry with `::warning::` + `exit 1` on exhaustion (step intentionally keeps `continue-on-error: true` per existing design).
- `updates/2026-11-16-regime-terminal-commit-hardening.md` — what/why/verification/revert.
- `updates/2026-11-16-gha-best-practices-hardening.md` — best-practice checklist, repo-wide gap counts, verification/revert.

### 3.2 PR #836 — P0 scheduled-path repairs (merged)
`fix(ci): P0 scheduled-path repairs — yf-refresh window+retry, pead push-storm hardening, alpha-live MySQL retry` (head `fix/gha-p0-scheduled-paths-2026-11-16`). Checks passed; squash-merged + branch deleted.

### 3.3 PR #847 — audit metric correctness (merged)
`fix(audit): n/a for infinite PF and explosive Sharpe` (head `fix/ghost-row-threshold-2026-11-16`). All 8 checks green (drift, manifest, test 3.11, test 3.12, conflict-marker, DB-password guards, audit); squash-merged + branch deleted.

## 4. Verification performed
- `python3 -c "import yaml; yaml.safe_load(...)"` on modified workflows → OK.
- `python3 -m pytest tests/test_skyrocket_detector_wireup.py tests/test_ueps_workflow_yaml.py -q` → **45 passed** (confirms the earlier CI cron-drift failures on old SHA `7b48625e` / run `43796591828` are resolved on current `main`; cron assertions are now stagger-tolerant).
- Confirmed on `origin/main` (no further edits needed):
  - `audit_trail/dashboard_payload_health.py` has `_OPTIONAL_SYSTEMS` so missing `pm_kalshi_re_signals` / `pm_polymarket_re_signals` is a **warning**, not a hard gate failure (`dashboard_generator.py` marks both `_PAPER_ONLY_SYSTEMS`, paper/shadow PM feeds).
  - `dynamic-alpha-engine.yml` "Commit results" step already delegates to `safe_push.sh` (90s per-git-op cap, deepen-fallback-to-merge) with `timeout-minutes: 15`; comments cite the prior hang (run `43799911205`). No code change applied on my side.

## 5. Peer work reviewed (context for future agents)
- **ghactions-v2** (`docs/alpha-verify-2-2026-11-16`): triage/audit corpus under `GHACTIONS_2026-11-16/**` — queue-hogs/failures (`2026-11-16_05-15Z_queue-hogs-and-failures/`), stale jobs/DB quality (`2026-11-16_05-35Z_stale-jobs-and-db-quality/`), best-practices approach, cron-stagger plan, ALPHA recheck notes. Their findings are consistent with live data (details in §7).
- **ghactions-v4** (`fix/gha-disable-broken-workflows`): `tools/gha_queue_audit.py` normalization + `reports/gha_best_practices_findings.md` (concurrency/timeouts/reusable-workflows/limits; flagged `academic-strategies-daily.yml` 25m kill, ~191 workflows missing concurrency, ~88 missing timeouts). Review/merge deliberately — branch appeared not clearly ahead of main in my check.
- **ghactions** (base worktree): no recent GHA-remediation commit in log; historical summaries/tools only — reference only.
- COMS roster also shows sibling seats active on same repo: `ghactions-v2/deepseek-flash` (ALPHA safe_push PASS run `43819637050`, CI Tests RESOLVED 08:05), `ghactions-v4/meituan-longcat-2-5` (20 hourly-cron concurrency+timeout batch), `p0-audit-json-2026-11-16/deepseek-v4-flash` (strict-JSON gate, feed-health optional PM, cards 747→749, CI Test fixes `734ad66b704`, `30d53b3d362`), `auditpage/grok-4-7` (PR #843 honesty banner), `auditpage-v2/glyph-cluster` and `auditpage-v3/v4` (audit action plans on main).

## 6. What I could NOT fix / did not do (remaining)
1. **PR #839 remains open and blocked.** `fix(ci): no-op gating, guardian v1.1, queue:max ticks, permissions + pins, deploy hygiene` fails `test (3.11)` and `test (3.12)` (run `43822754710`, ~5m) and is `CONFLICTING` with `main`. Needs: pull `main`, resolve conflicts, fix the failing tests, re-run CI, then merge.
2. **ALPHA ENGINE - Dynamic Runner post-fix run not confirmed by me.** Workflow name is `ALPHA ENGINE - Dynamic Runner (Cloud or Local)`; file is `.github/workflows/dynamic-alpha-engine.yml` (NOT `alpha-engine-dynamic-runner.yml` — that filename does not exist). `origin/main` already has the hardened `safe_push.sh` commit step (job timeout 90m, step 15m, 2-hour cron `23 */2 * * *`). A future agent should confirm the next scheduled/dispatch run completes its "Commit results" step without the 15-min hang.
3. **Feed Health Check historical failure (`43806313904`, missing PM rows) appears resolved on `main`** via `_OPTIONAL_SYSTEMS`, but a live re-run on the latest dashboard payload should be confirmed green.
4. **Ghost queued runs** (un-cancellable via `gh`/REST; `409 Cannot cancel a workflow run that has not been queued yet`) — requires GitHub Actions UI or an admin-scoped token / GitHub Support. Not actionable from this worktree.
5. **Audit data/deploy gaps (deploy-impact, not touched):** `strategy_tribunal_latest.json` 404; stale `strategy_ic_analysis.json` (~2026-05-29) and `pick_summary_stats.json` (~2026-05-25); PM sidecar endpoints 404 vs dashboard wiring (`prediction_market_consensus`, `polymarket_signals`, `kalshi_signals`); hypothesis tracker sidecar/panel present locally but not confirmed wired end-to-end on live `/audit`.
6. **No browser/DevTools access** to confirm live `/audit` runtime JS console errors or static-vs-live narrative conflicts.
7. **Fleet-wide hygiene not mass-applied (deliberate).** Repo scan (355 workflows): ~68 missing job `timeout-minutes`, ~94 missing top-level `permissions`, ~182 missing `concurrency`, ~212 commit workflows missing full safe-commit safeguards; actions not broadly SHA-pinned. Mass rewriting is high-risk; do it in reviewed batches.
8. **Did not push** `fix/gha-cron-regime-hardening` myself — the commits landed via #841, so the branch is intentionally left as a stale local branch (safe to delete after confirming #841 in `main`).

## 7. Durable evidence / pointers
- My merged code: `.github/workflows/regime-terminal.yml`, `.github/workflows/audit-impact-tracker.yml`, `.github/workflows/ueps-pick-runner.yml` (on `main` via #841).
- My docs on `main`: `updates/2026-11-16-regime-terminal-commit-hardening.md`, `updates/2026-11-16-gha-best-practices-hardening.md`.
- My earlier review artifact (local, untracked): `GHACTIONS_2026-11-16/2026-11-16_01-17_EST_peer-review-and-actions/SUMMARY.md`.
- This wrap-up: `GHACTIONS_2026-11-16/2026-11-16_15-40_EST_ghactions-v3-wrapup/WRAPUP.md`.
- Peer corpus (v2): `GHACTIONS_2026-11-16/2026-11-16_05-15Z_queue-hogs-and-failures/GHACTIONS_QUEUE_HOGS_AND_FAILURES.MD`, `GHACTIONS_2026-11-16/2026-11-16_05-35Z_stale-jobs-and-db-quality/GHACTIONS_STALE_JOBS_AND_DB_QUALITY.MD`, `GHACTIONS_2026-11-16/2026-11-15_21-45_EST_ghactions/*`.
- Peer tooling (v4): `tools/gha_queue_audit.py`, `reports/gha_best_practices_findings.md`.

## 8. Suggested prompts for future agents
- **#839 finisher:** "In worktree `ghactions-v4` (or a fresh worktree off `origin/main`), check out PR #839 (`tmp/s3-ci-hygiene`), `git fetch origin main && git merge origin/main`, resolve conflicts, then run `python3 -m pytest tests/ -q` (or the CI Tests job's exact command) to reproduce the failing `test (3.11)`/`test (3.12)` from run `43822754710`. Fix the failures without reverting the cron-stagger/minute-tolerant assertions, push, confirm all checks green, then squash-merge with `--delete-branch`."
- **ALPHA confirm-only:** "Do NOT edit `dynamic-alpha-engine.yml` unless a new run regresses. Inspect the latest `ALPHA ENGINE - Dynamic Runner` run on `main`; verify the `Commit results` step finishes in <5m and logs `Pushed successfully` or a fast `::warning::` self-heal. If it hangs again, replace any residual inline `git pull --rebase 2>/dev/null` with `bash .github/scripts/safe_push.sh`."
- **Feed health confirm:** "Run `python3 audit_trail/feed_health_check.py --once` against the freshest `audit_trail/data/dashboard_payload.json`; expect exit 0 with `pm_*` sources reported as OPTIONAL warnings (see `_OPTIONAL_SYSTEMS` in `audit_trail/dashboard_payload_health.py`). If it still hard-fails, check whether the producer workflows for `pm_kalshi_re_signals`/`pm_polymarket_re_signals` ran and whether they should be `_HIDDEN_SYSTEMS`."
- **Audit data gaps:** "In `.github/workflows/audit-dashboard.yml` + producers (`tools/strategy_kill_tribunal.py`, `tools/deploy_audit_files.py`, `audit_trail/dashboard_generator.py`), trace generation+deploy of `strategy_tribunal_latest.json`, `strategy_ic_analysis.json`, `pick_summary_stats.json`; fix stale/missing artifact paths; verify live `https://findtorontoevents.ca/audit/data/*` freshness after the next deploy. Treat PM sidecar 404s as a product decision (expose as files vs include in `dashboard_data.json`)."
- **Fleet hygiene (incremental):** "Add `concurrency` + job `timeout-minutes` + explicit least-privilege `permissions` to the top ~20 highest-frequency cron workflows first (prioritize the ~188 minute-0 crons). Standardize auto-commit steps on `safe_push.sh` + `assert_no_conflict_markers.sh` + authenticated remote + explicit terminal outcome. Plan SHA pinning for `actions/checkout`, `actions/setup-python`, `actions/upload-artifact` in a separate reviewed PR. Do NOT mass-rewrite; one batch per PR with green CI."
- **Ghost queue:** "The queued runs created 2026-11-11 (~20:24–20:43Z) cannot be cancelled via API (`409`). Purge via Actions UI (`.../actions?query=is%3Aqueued`) or an admin-scoped PAT (per peer `GHA_TRIAGE_ANALYSIS.md`, admin scope returns success where normal token gets `403 Could not delete`). Re-check queue-depth readings only after purge."
- **COMS handoff:** "Update your seat via `COMS register --agent <seat> --todo ... --done ...` from your own worktree, then `COMS send inbox/<host>/<your-worktree>/all \"...\"`. Do not subscribe to `inbox/<host>/#` unless you are the machine monitor. No secrets on the bus."

## 9. Questions / open decisions
1. **#839 ownership:** who fixes the failing CI + conflicts (v4 author `meituan-longcat-2-5`, or a dedicated finisher)? It blocks the CI-hygiene batch (guardian v1.1, queue:max, permissions/pins).
2. **PM feeds product intent:** should `pm_kalshi_re_signals` / `pm_polymarket_re_signals` stay paper/shadow/optional forever, or get first-class producers + sidecar JSON endpoints on `/audit`?
3. **Hypothesis tracker wiring:** required on the live dashboard, or remain a sidecar only?
4. **Ghost queued runs:** approve admin-scoped purge, or leave for GitHub Support?
5. **Fleet hygiene cadence:** approve batch PRs (timeouts/concurrency/permissions, then SHA pinning) — each needs a green-CI gate and reviewer.