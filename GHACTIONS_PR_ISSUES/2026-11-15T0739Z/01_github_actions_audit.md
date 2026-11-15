# 01 — GitHub Actions Audit

## 1. Workflow inventory

`.github/workflows/` contains **381 files**:

| Category | Count | Meaning |
|---|---|---|
| Active `.yml`/`.yaml` | 362 | Executed by GitHub Actions |
| `*.disabled` | 5 | Dead, retained for reference |
| `*.retired` | 10 | Retired, retained for reference |
| `*.draft` | 1 | Draft |
| `.md` (non-workflow) | 3 | `FIXES_2026-03-08.md`, `The edge is real. The data proves it.md`, `Untitled-1.md` |

**Hygiene problems:**
- 362 live workflows is unmanageable. Many are hourly scanners that each push a `[skip ci]` commit to `main` every hour (see the ~120-commit/hour commit log below). This is the root cause of the constant `main` churn and the `Branch Large File Duplicate Guard` / `Conflict Marker Check` cancellation storms.
- 16 disabled/retired/draft files + 3 `.md` notes should be moved out of `.github/workflows/` into an archive (e.g. `.github/workflows-archive/`) so they stop showing up in every grep/audit.
- `actions-failure-guardian.yml` exists but is not preventing the failures below.

## 2. Recurring failing workflows (root-caused)

### 2.1 `backup-verify.yml` — "Backup Restore Verification" *(P0, architectural bug)*
- **Failure:** `dashboard_data.json NOT FOUND` → `Critical file missing: audit_dashboard/data/dashboard_data.json`, every run.
- **Root cause:** `audit_dashboard/data/dashboard_data.json` is **gitignored** (`git check-ignore` confirms) and never committed — it is a generated deploy artifact produced by `audit_trail/dashboard_generator.py`. The workflow checks for a file that is, by design, absent from the checkout. It will fail 100% of the time, forever.
- **Amplifier:** on `failure()` the workflow opens a **new GitHub issue every run** (`actions/github-script` `issues.create`) with no dedup — so each manual re-run adds another identical issue. This produced **42 open issues** (Jun→Nov 2026).
- **Fix:** (a) stop treating a generated artifact as a critical restore file (remove it from `critical_files` and the `trading_picks_count` proxy, or generate/fetch it first); (b) add issue dedup — search for an existing open `[backup-verify]` issue and comment/reuse instead of `issues.create`. **Already implemented in open PR #713** (`fix/ci-backup-verify-and-dupguard`) — merge it.

### 2.2 `sports-smoke-and-e2e.yml` — "Sports endpoint smoke + Playwright" *(hourly, fails)*
- **Root cause (fixed in PR #786):** `runs-on: ubuntu-latest` now resolves to 26.04, and Playwright refuses to install chromium there — the job died on the install step every hour (`Playwright does not support chromium on ubuntu26.04-x64`). Pin to `ubuntu-24.04`.
- **Remaining issues:** (a) the `deploy-guard` job still uses `ubuntu-latest`; (b) the smoke suite hits **live production endpoints** (read-only), so any prod outage = CI failure even though the repo is fine — consider marking prod-down as a warning, not a hard failure.

### 2.3 `qa-market-validation.yml` — "QA Market Validation" *(hourly, fails)*
- **Root cause (fixed in PR #786):** it ran with **none** of the quote-chain API keys. `alpha_engine/equity_price_failover.py` adapters 2–6 return `None` when their env var is unset, leaving only Stooq (blocked from runner IPs) and yfinance (flaky) → `ALL 7 sources failed` for every ticker.
- **Fix:** pass `FINNHUB_API_KEY`, `TIINGO_API_KEY`, `TWELVE_DATA_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY`. **Note:** if these 5 secrets are not set on the repo, the job keeps failing honestly — the secrets must be configured at the repo level, not just in the YAML.

### 2.4 `ci-tests.yml` — "CI Tests" *(fails repeatedly, real regression)*
- **Failure:** 8 tests fail (6659 collected), all with `assert False is True`:
  - `tests/test_m097_book_direction_conflict.py::TestM097BookDirectionConflict::*` (7 tests: shadow/enforce/no-conflict/fail-open/disabled)
  - `tests/test_dashboard_generator.py::test_pre_score_active_candidate_keeps_valid_zero_score_pick_alive`
- **Root cause:** `quality_gates.passes_active_gate(pick)` returns `False` where the tests expect `True` — a gate/fixture regression in the M097 book-direction-conflict logic. A `fix/passes-active-gate-fixture` branch exists locally; its fix should be landed.
- **Impact:** this is the *gating* test workflow, so a failing `CI Tests` red-herrings every PR.

### 2.5 Sporadic failures (monitor, don't chase individually)
`Mirror: findtorontoevents.ca → torontoevent.net` (FTP mirror), `Verified pilot daily`, `Feed Health Check`, `Edge stability refresh`, `robust-edge-miner`, `Missed Opportunity Analyzer`, `HC Evaluator Parity Test`, `Mermaid Test Deploy`, `ALPHA ENGINE - Dynamic Runner`, `ALPHA ENGINE FAST`, `Market Beating System`. Most are data/FTP/env flakiness rather than code defects — but their failure rate should be tracked in one place (see `04_fix_and_enhance_plan.md`).

## 3. The `main` commit firehose

`main` receives **~60–120 auto-commits/hour**, nearly all `[skip ci]` data/scanner updates (`Gainer scan`, `Coinglass scan`, `QuickGuess ML`, `Hindsight learner`, `QuanEngine forward tracker`, `Signal Engine`, `Regime Terminal`, `Scanner data update`, `Auto-update`, …). Consequences:
- Constant non-fast-forward churn that breaks the snapshot-push workflows (the `git rebase origin/main` fix in PR #786 targets exactly this).
- `Branch Large File Duplicate Guard` and `Conflict Marker Check` get cancelled/restarted in a cascade on every push.
- Genuine human/agent work (the `WIRED_IN/` docs) is buried in the noise.

**Recommendation:** batch the hourly `[skip ci]` data commits (e.g. one roll-up commit per 15–30 min), or move scanner state out of `git` into S3/DB, so `main` stops being a high-frequency write target.
