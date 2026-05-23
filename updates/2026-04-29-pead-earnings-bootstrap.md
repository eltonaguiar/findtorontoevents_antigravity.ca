# PEAD earnings cache bootstrap (opt-in)

**Date:** 2026-04-29
**Branch:** `fix/pead-earnings-bootstrap-2026-04-29`
**Goal:** #1 (audit performance — equity edge unblock)

## What

Per peer w03yqel9 research/25 audit: PEAD is wired through
`alpha_engine/scanner.py:2045-2046` -> `VT_BABY_STRATEGIES["vt_earnings_pead"]`
-> `alpha_engine/vt_baby_strategies.py:376` (`vt_equity_earnings_drift_pead`),
but the on-disk cache directory `data/earnings/` does **not** exist. The
strategy short-circuits at line 389-390 (`if not earnings_dir.exists(): return []`),
so flipping `UEPS_ENABLE_PEAD=1` today produces zero picks.

This PR bootstraps the cache so PEAD can actually emit signals once the
two flags are flipped together.

## Changes

- **New: `tools/earnings_calendar_fetcher.py`** — opt-in CLI bootstrapper.
  Default OFF via `EARNINGS_FETCHER_ENABLED=0`. When enabled, calls the
  existing library at `alpha_engine/earnings_calendar_fetcher.py` (Finnhub
  primary -> EDGAR stub -> yfinance fallback) for a default S&P mega-cap
  universe and writes per-ticker JSON to `data/earnings/<TICKER>/latest.json`
  plus a top-level `data/earnings/calendar.json` summary.
- **New: `data/earnings/.gitkeep`** — ensures the directory exists in
  fresh checkouts and on cloud GHA runners.
- **New: `tests/test_tools_earnings_calendar_fetcher.py`** — 9 tests covering
  env-var gating, schema of `calendar.json`, bootstrap-only mode, library
  routing, ticker-file parsing, and `.gitkeep` idempotency. The library
  itself is already exercised by `tests/test_earnings_calendar_fetcher.py`.

## Default-off proof

- `EARNINGS_FETCHER_ENABLED` unset / "0" / "false" / "off" / "" all return
  `cli._is_enabled() == False` (test
  `test_env_var_off_values`).
- Disabled run takes the no-network path; sentinel monkeypatches the
  library `EarningsCalendarFetcher` to raise — the test passes
  (`test_disabled_path_writes_stub_index_no_network`).
- Bootstrap-only mode does not write `calendar.json` either
  (`test_bootstrap_only_creates_directory`).

## Wiring Plan

This module is **opt-in sidecar**, not auto-wired into the live scanner. To
turn it on:

1. **Validation step (this PR):** add a workflow step calling
   `python tools/earnings_calendar_fetcher.py --bootstrap-only` to whichever
   live cron actually consumes PEAD (`alpha-engine-live.yml` is the
   2-hourly equity scanner). Default-off; this just creates the directory.
2. **Smoke test (next PR, ~2026-05-01):** run with
   `EARNINGS_FETCHER_ENABLED=1 python tools/earnings_calendar_fetcher.py
   --tickers AAPL,MSFT,NVDA --verbose` in a one-shot manual `workflow_dispatch`
   and inspect `data/earnings/calendar.json`. Confirm Finnhub key is set or
   the yfinance fallback returned non-empty history.
3. **Production wire-up (PR after smoke):** add the fetch step before the
   scanner step in `.github/workflows/alpha-engine-live.yml`, then flip
   both `EARNINGS_FETCHER_ENABLED=1` and `UEPS_ENABLE_PEAD=1` together.
   Verify in the next run that `vt_earnings_pead` shows non-zero signal
   counts in the alpha-engine logs.
4. **Acceptance criterion:** at least one `vt_earnings_pead` pick in
   `audit_dashboard/data/dashboard_data.json` within 48h of flip-on.

## Rollback

Deleting `data/earnings/` and unsetting `EARNINGS_FETCHER_ENABLED` reverts
to the current (zero-PEAD-picks) state. Setting `UEPS_ENABLE_PEAD=0` alone
also disables — the gate in `vt_baby_strategies.py:378` is the same one this
plan keys off.

## Why not auto-wire today

CLAUDE.md Wire-Up Rule explicitly favours opt-in sidecars with a wiring plan
over breadth-only PRs (`reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md`,
20/21 orphan rate). PEAD is wired; this PR just removes the silent-empty
failure mode by ensuring the directory exists, plus hands a CLI to the
follow-up wiring PR.
