# audit3 P1 — evidence registry (old backtests are no longer invisible)

**Date:** 2026-11-19
**Surface:** `/audit3` — new `alpha_engine/audit3_evidence.py`, `audit3_evidence.json`,
`Evidence Registry` tab, `.github/workflows/audit3-evidence.yml`
**Depends on:** P0 (doctrine + section×class matrix, PR #884/#885)

## What was broken

`audit3_tribunal.py` could only see the live closed-pick ledger. Everything the
repo had already measured was invisible to it:

- 285 rows in `bt_backtest_runs`, 1,105 in `at_large_backtest_results`, 1,285 in
  `at_incubator_backtest_results`
- 77+ backtest JSONs (`reports/strategy_bt_*`, `equity_baby_strategies_backtest.json`,
  `backtest_path_forward.json`, copytrader/bond/Hyro/Piotroski results)

Two data defects made that evidence actively misleading:

1. **`bt_backtest_runs.asset_class` labels all 285 rows `CRYPTO`** — including
   `NZDUSD=X`. Any class count taken from that column is wrong.
2. **`reports/hypothesis_registry.json` uses 28 spellings for ~10 states**
   (`FORWARD_OBSERVATION`, `FORWARD_SHADOW`, `forward-shadow`,
   `REGISTERED-UNTESTED`, `PRE-REGISTERED`, `REJECTED - only 0 scored windows
   (need 3)` …), so the tracker could not count anything reliably.

The doctrine from P0 says nothing useful is thrown away. Evidence nobody can
find or trust is thrown away in practice.

## What changed

`alpha_engine/audit3_evidence.py` (stdlib for JSON, `pymysql` only for the
optional DB read):

- **Symbol-derived asset class.** `NZDUSD=X → FOREX`, `CT=F → COMMODITY`,
  `ES=F → FUTURES`, `BTC-USD`/`*USDT → CRYPTO`, known ETFs → `ETF`, else
  `EQUITY`. Disagreements with the stored column are reported, not silently
  resolved.
- **Canonical hypothesis enum** (13 states) with exact-map + prefix rules; the
  raw spelling and "matched exactly?" flag are kept so cleanup is possible.
- **Shape-agnostic JSON ingestion.** One BFS `find_stats` + alias table handles
  `main`, `overall`, `results.overall`, and per-strategy bundles, normalising
  win rates that arrive as 0–1 or 0–100 and drawdowns as ratio or percent.
- **Provenance on every record**: file path + sha256, or table + row id, plus
  the DB `source_db`/`source_table` chain where present.
- **Opportunistic recomputation.** If a payload ships a trade log, WR/PF/mean
  PnL are recomputed and stored under `recomputed` (labelled gross — costs are
  unknown), so stated numbers can be checked rather than believed.
- **Read-only DB ingestion** with per-table `SHOW COLUMNS` + row cap; a missing
  driver or credential degrades to JSON-only with `db.error` recorded instead of
  failing the job.
- **Continuous `known_gaps`** so the page states what this registry cannot see
  (the 32.7M-row trades table, missing costs, absent `RECOVERY_PROTOCOL.MD`).

`.github/workflows/audit3-evidence.yml`: weekly (Mondays 05:41), own concurrency
group `audit3-evidence`, no `push:` trigger, installs `pymysql`, commits only
`audit_dashboard/data/audit3_evidence.json` with `[skip ci]`, deploys the JSON +
page over the same FTP secrets as the ledger workflow.

`audit_dashboard/audit3.html`: new **Evidence Registry** tab showing summary
chips by derived class, the source list with hashes, the records table
(n / WR / PF / Sharpe / MaxDD / recomputed / provenance), class mismatches, and
the normalised hypothesis enum. It fetches `audit3_evidence.json` separately and
degrades to a clear message when the weekly job has not run yet.

## Verification

- `python3 -m pytest tests/test_audit3_evidence.py -q` — 15 tests.
- `python3 -m pytest tests/test_audit3_tribunal.py -q` — 16 tests (unchanged, still green);
  31 together.
- `python3 alpha_engine/audit3_evidence.py --no-db --out ...` — 52 records from 50 repo
  files (the payloads that carry metrics).
- Full run with the live DB: **2,727 records, 145 strategies, 50 source files,
  ~66.7k trades covered, 11 class mismatches, 11 records recomputed from shipped
  trade logs, DB connected (2,675 rows from 3 tables)**.
- Live after deploy: `/audit3/audit3_evidence.json` 200 (2,523,018 B),
  `/audit3/` 200 and contains the Evidence Registry tab; the ledger tab still
  reports 11 kills / 34 weak / 65 segment cells.
- Syntax: `py_compile`, plus `node --check` on the page's extracted `<script>`.

## What this does NOT do

- It does not re-score backtests or promote anything; prior evidence has no
  timing null, so it stays evidence.
- It does not scan `bt_backtest_trades` (~32.7M rows); that needs a pre-aggregated
  rollup first.
- It does not touch `/audit`, `/audit2`, or `audit-dashboard.yml`.
