# 04 — Fix & Enhance Plan (prioritized)

## P0 — Blockers (fix this week)

### P0-1: Stop the backup-verify failure + issue spam
- Merge PR **#713**. Then close the 42 spam issues.
- In `backup-verify.yml`: remove the gitignored `dashboard_data.json` from `critical_files` and from the `trading_picks_count` proxy (or generate it before checking). Add dedup — search for an existing open `[backup-verify]` issue and reuse it instead of `issues.create`.

### P0-2: Land the CI workflow fixes
- Merge PR **#786** (sports-smoke ubuntu pin, QA API keys, snapshot rebase).
- **Precondition:** set `FINNHUB_API_KEY`, `TIINGO_API_KEY`, `TWELVE_DATA_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY` as repo secrets, otherwise QA validation keeps failing honestly.

### P0-3: Fix the 8 failing CI Tests
- `quality_gates.passes_active_gate()` returns `False` where tests expect `True` in `test_m097_book_direction_conflict.py` (7 tests) and `test_dashboard_generator.py` (1 test). Land the `fix/passes-active-gate-fixture` fix.

### P0-4: Fix the gross-vs-net excess-return bug (profitability blocker)
- `tools/forward_tracker.py` and `tools/pick_excess.py` compute `excess_pp`/`ret_pct` **gross of fees**. A +1.96pp prior shrinks by ~0.12pp after a 12bp round-trip. Before trusting any forward-test verdict, subtract fees on both legs (like the `sync` net path already does for the ledger).

## P1 — Hygiene & consolidation (this month)

1. **Workflow inventory:** move 16 `.disabled`/`.retired`/`.draft` files + 3 `.md` notes out of `.github/workflows/` into `.github/workflows-archive/`. Consider consolidating the 362 active workflows (many hourly scanners are near-duplicates).
2. **Reduce `main` churn:** batch hourly `[skip ci]` data commits (15–30 min roll-ups) or move scanner state off `git` (S3/DB). This alone would cut the push-cascade cancellations.
3. **PR backlog:** merge ~4, rebase 1, close ~20 stale (see `02_open_prs_triage.md`).
4. **Issue hygiene:** close 42 spam + 5 secret-rotation reminders after acting.
5. **Rotate secrets** (Aug–Nov reminders outstanding): `DB_PASS_*`, Binance, CoinGecko, Discord, SendGrid — follow `docs/DB_ROTATION_RUNBOOK_2026-05-13.md`.

## P2 — Enhancements (next quarter)

1. **One CI-failure dashboard:** route every workflow's failure into a single roll-up (extend `actions-failure-guardian.yml` or `gha-summary-report.yml`) so recurring failures surface as one issue, not dozens.
2. **Auto-dedup for auto-created issues:** a shared helper (search-by-title-then-comment) for any workflow that opens issues on failure.
3. **Runner pinning:** standardize on `ubuntu-24.04` (or `vars.ACTIONS_RUNNER_LABEL`) repo-wide so the 26.04 Playwright break can't recur in another job (note: `sports-smoke-and-e2e.yml` `deploy-guard` job still uses `ubuntu-latest`).
4. **Snapshot-push retry pattern:** the `git fetch origin main && git rebase origin/main` retry added in PR #786 should be extracted into a reusable composite action and applied to *every* workflow that pushes a JSON snapshot (there are several: rsi5070, operator-review, master-picks, forward-tracker, etc.).
5. **Secrets presence check:** add a pre-flight step to workflows that need specific secrets, failing with a clear "secret X is unset" message instead of a downstream `ALL sources failed`.

## Dependencies / ordering

```
P0-2 (secrets) ──▶ P0-2 (merge #786)
P0-1 (merge #713) ──▶ close 42 issues
P0-3 (fixture fix) ──▶ CI Tests green ──▶ unblocks every PR
P0-4 (net-excess) ──▶ profitability forward-test becomes trustworthy
```
