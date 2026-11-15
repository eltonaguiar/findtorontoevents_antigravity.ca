# GH Actions Fixes — CI Tests + Verified-pilot

**Date:** 2026-11-15
**Author:** Kilo (wire-fix-ghactions-pr-issues-v3)
**Branch:** `fix/kilo-ci-tests-backup-verify` (PR #797)

## Fix 1 — CI Tests: 8 deterministic failures

`test_m097_book_direction_conflict.py` (7) and
`test_dashboard_generator.py::test_pre_score_active_candidate_keeps_valid_zero_score_pick_alive`
(1) failed with `assert False is True` because both use CRYPTO **LONG** fixtures but did
not neutralize the CRYPTO-LONG block gates that default ON in CI
(`CRYPTO_PRODUCTION_BLOCK_LONG=1` repo variable, M-036b `CRYPTO_BUY_DIRECTION_GATE_ENABLED`).
`conftest.py` uses `setdefault`, a no-op when the env already sets them.

**Fix:** `monkeypatch.setenv(..., "0")` for the 7 crypto gates in both fixtures (mirrors
`test_blacklist_exec_gate_enforcement._NEUTRALIZE`). Verified 9 passed under CI-like env,
94 passed with related gate tests.

## Fix 2 — `Verified pilot daily`: strategy admission false-failure

`tools/run_verified_pilots_daily.py` gated the whole workflow on `all(returncode == 0)`,
but `strategy_admit.py` exits 1 on **REJECT** — a legitimate daily verdict (0 strategies
pass the proof protocol). The workflow failed every night even when all pilots ran clean.

**Fix:** mark the `strategy_admit.py` step `gating=False`. The verdict stays in the report
but no longer fails the workflow.

## Fix 3 — `Verified pilot daily`: `pymysql` missing

`forex_carry_g10_pilot.py --write-db` imports `pymysql`, but the workflow only installed
`pandas numpy yfinance requests`. **Fix:** add `pymysql` to the install step.

## Fix 4 — `Verified pilot daily`: `--write-db` fails on missing DB creds

`--write-db` calls `get_stocks_creds(raise_on_missing=True)` which raises when no DB
secrets are in the workflow env. **Fix:** make the `--write-db` step **fail-open** (log
the error, don't crash the paper pilot). The paper log is the pilot's primary output; the
DB write is best-effort.

## Already fixed by peers (not in this branch — reconciled away)

Parallel PRs landed during this session and cover the rest, so this branch deliberately
does **not** duplicate them:

- **PR #798** — yfinance MultiIndex `float() got Series` fix (`.iloc[:,0]` / `.item()`
  collapse) in `etf_dual_momentum_pilot.py` + `forex_carry_g10_pilot.py`.
- **PR #799** — `algorithm-competition-refresh.yml` + `torontoevent-algorithm-refresh.yml`
  slim-JSON guard, `weekly_score_quartile_spread.yml`, `stale-branch-cleanup.yml`.
- **PR #789** — `backup-verify.yml`, `qa-market-validation.yml`, snapshot-push rebase,
  Playwright `ubuntu-24.04` runners.
- **PR #793** — `daily-price-refresh.yml` (disabled), `hc-parity.yml`, `mirror-site.yml`,
  `robust-edge-miner.yml`.
- **PR #795** — `market_beating.yml` py3.14 + mirror uploads.

## Deferred / out of scope

- 5 quote-chain API secrets for `qa-market-validation.yml` (per instruction).
- `Mermaid Test Deploy` — on the `wiring` feature branch, GH Pages push permission;
  workflow file no longer present in this checkout.
- Abandoned one-off workflows still "failed" since May–Jun 2026 (should be disabled):
  `DB Secret Scan`, `ML Gatekeeper A/B Bootstrap`, `MySQL Q-001`, `DB Freshness Check
  (Legacy Manual)`.
