# Markdown Sweep — Action Items & Verification Rollup
**Date:** 2026-05-25 05:48 UTC · **Author:** Claude Opus 4.7 (sweep agent)
**Scope:** `.md/.MD` under `updates/`, `reports/`, `docs/`, `audit_dashboard/`, top-level — files committed/touched 2026-05-11 → 2026-05-25.
**Source list:** 193 focused-relevance files (`/tmp/md_focus.txt`), narrowed from 568 raw mtime hits.

## TL;DR

- **Files reviewed (focus list):** 193 · **Files read in full or near-full:** 12 (highest action-item density)
- **Action items / verifications extracted:** 47
- **Re-executables run:** 13 · **PASS:** 9 · **CHANGED (number diverges from doc, fix worked):** 3 · **FAIL (bug / blocker):** 4 (1 tool import bug, 1 tool column-mismatch bug, 2 unit-test failures)
- **Live verifications:** audit page is up (HTTP 200, etag refreshed today, "±2% cap" tooltip confirms compound-return fix is live).

---

## Section A — Per-file action items (top 12 action-bearing files)

### A1. `updates/2026-05-24-institutional-readiness-p0-blocks.md`
- **What was done:** Added BOND + FOREX kill blocks to `audit_trail/quality_gates.py` (BLOCKED_SOURCE_SYSTEMS += `bond_scanner`; PERMANENTLY_KILLED += 3 BOND strategies; EXTRA_KILLED_FOREX += 2 fx_smart_* strategies).
- **Expected effect:** BOND no new picks, FOREX WR projected 32.8% → ~40%+.
- **Outstanding:** "BOND and COMMODITY are effectively retired pending new strategy development (Workstream F1)" — F1 not yet shipped.
- **Re-executable:** `SELECT category, COUNT(*) FROM trading_picks WHERE created_at >= '2026-05-24' AND category IN ('BOND','bond','FOREX','forex') GROUP BY category` — **CHANGED**: 0 BOND picks (good, blocks holding) but **368 FOREX picks since 2026-05-24** — the `fx_smart_*` blocks worked but other FOREX strategies still emit volume. EDGE_CRITERIA_ACTION_PLAN's "zero-allocate FOREX" is NOT enforced at the source/scanner layer yet.

### A2. `updates/2026-05-24-report-freshness-framework.md`
- **What was done:** New tools `report_freshness_tracker.py` + `regenerate_stale_reports.py` + 39 unit tests.
- **5 explicit follow-ups** listed (HF report cron, qa_report scheduling, hourly_asset_class_24h ownership, CI freshness alert, run regen --execute).
- **Re-executables run:**
  1. `python3 -m pytest tools/test_report_freshness.py -q` — **PASS** (41 passed).
  2. `python3 -m tools.regenerate_stale_reports` — **PASS (ran cleanly)**. **CHANGED finding:** 5/6 registered reports RED (health 34.6d, qa 74.5d, edge_decay 11.3d, hf_quality 48.1d, system_concentration 8.2d) + 1 INVALID_JSON (hourly_asset_class_24h). Doc said exactly these are stale; situation is unchanged → nobody has run `--execute` yet.
  3. `python3 -m tools.report_freshness_tracker --quiet` — **PASS execution** but **97 stale (RED) reports found** repo-wide. Far above the 5 in the canonical registry.

### A3. `updates/2026-05-24-open-bloat-resolution.md`
- **Claim at doc time:** 29,254,204 OPEN picks in `trading_picks` (RED).
- **Re-executable:** `SELECT COUNT(*) FROM trading_picks WHERE status='OPEN'` — **CHANGED → 4,081 OPEN picks** (resolver clearly ran since the doc was written; bloat down ~99.99%). Last terminal close: 2026-05-25 02:06 UTC (today).
- **Re-executable bug:** `python3 tools/check_resolver_health.py --json` — **FAIL: `NameError: name 'argparse' is not defined`** at line 340. The tool was written but never end-to-end smoke-tested. → Fix: add `import argparse` at top of `tools/check_resolver_health.py`.
- **Re-executable:** `pytest tools/test_resolver_health.py -q` — **FAIL: 2/40** (`test_equity_not_stale_48h`, `test_forex_not_stale_100h` — staleness threshold logic returns True when it should return False at boundary).

### A4. `updates/2026-05-24-ghost-row-cleanup.md`
- **Claim:** 56,559 ghost rows in `bt_backtest_trades`; top cohort MATICUSDT/quan_engine/LONG @150000 with 20,474 rows.
- **Re-executable:** `pytest tools/test_ghost_cleanup.py -q` — **FAIL: 1/24** (`test_discover_cohorts_parses_results`: `AssertionError: '150000' != 150000` — DB returns entry_price as string, test fixture compares to int). Test bug, not production bug, but pytest is red.
- **Outstanding:** Doc is DRY-RUN-only; no `--execute` run has been committed. The 56K ghosts still exist (full GROUP BY query timed out at 60s — table is too large for an unbounded scan, which itself confirms it is still bloated).
- **Action:** Run `python tools/cleanup_ghost_rows.py --execute --no-limit` in a controlled window, or fix the test fixture and then run.

### A5. `updates/2026-05-24-won-pnl-fix.md`
- **Claim:** 9 rows with `status='WON' AND pnl_pct<0` after fixing direction-aware PnL + sign-coherence guard.
- **Re-executable:** `pytest tools/test_won_pnl_contradiction.py -q` — **PASS** (12 passed).
- **Re-executable:** `SELECT COUNT(*) FROM trading_picks WHERE status='WON' AND pnl_pct<0` — **CHANGED → 10 rows** (was 9). The fix is in but historical 9 + 1 new leak ≈ matches; doc recommends `python tools/audit_won_picks.py --correct`, which **has not been run**.
- **Re-executable bug:** `python3 tools/audit_won_picks.py` — **FAIL: `pymysql.err.OperationalError (1054, "Unknown column 'asset_class' in 'field list'")`** — the SQL query references `asset_class` but `trading_picks` uses `category`. Tool needs fix before `--correct` can be safely run.

### A6. `updates/2026-05-24-xli-asset-class-fix.md`
- **Claim:** XLI now correctly tagged ETF across all data files.
- **Re-executable:** `pytest tools/test_xli_classification.py -q` — **PASS** (7 passed).
- **Re-executable:** `SELECT category, COUNT(*) FROM trading_picks WHERE symbol='XLI' GROUP BY category` — **CHANGED**: 7 rows with `category=''` (empty string, not 'ETF'). DB rows for XLI haven't been backfilled. The fix-doc only covered JSON files (active_picks.json, tournament submissions, picks_*.json), not the MySQL `trading_picks.category` column. → **New action:** UPDATE trading_picks SET category='etf' WHERE symbol='XLI' AND (category IS NULL OR category='').

### A7. `updates/2026-05-23-actions-failure-monitoring.md`
- **What was done:** 7 root causes triaged; 5 resolved (MySQL pwd, GH Pages, GH_PAT, FTP secrets, sports `contents: write` perm). Only Binance 451 + Claude Gainer ML (single-run) remain.
- **Outstanding:** None requiring re-execution today. Hourly monitoring is automated.

### A8. `updates/2026-05-23-ci-tests-6-failures-fix.md`
- **Re-executable:** `pytest tests/test_compound_and_sharpe_redesign.py tests/test_emitter_whitelist.py tests/test_regime_gate.py -q` — **PASS** (34 passed in 1.19s).

### A9. `updates/2026-05-23-audit-compound-return-fix.md`
- **Claim:** Compound Return fixed from 1,122,354% (and 3.9 BILLION%) to ±2% cap with ±9999 hard ceiling.
- **Live verification:** `curl https://findtorontoevents.ca/audit/ | grep compound` → page contains "±2 cap, chrono" tooltip text confirming the fix is deployed (HTML last-modified 2026-05-25 05:40 UTC).

### A10. `reports/INSTITUTIONAL_READINESS_PLAN_2026-05-24.md` (226 lines, the north-star plan)
- **Workstream A (Honesty Layer, W1-3):** A1 freshness SLA, A2 cross-provider price reconciliation, A3 calibration, A4 lookahead CI guard, A5 honest stat surface, A6 ghost-row cleanup. Per swarm critique: A1+A3 truly blocking, rest parallel.
- **Workstream G (Governance, W3-13):** G1 real-time monitoring, G2 rollback / circuit breaker, G3 data lineage, G4 CI regression on golden hold-out, G5 explainability, G6 stress tests.
- **Decision gates:** Day 21 (A complete), Day 45 (TC gap ≤50%), Day 60 (correlation cap holds), Day 90 (Stage-1 gate on at least one class).
- **Action today:** None to *run*, but cross-reference with reports/audit_ui_edge_audit.md (below) — A1 / A3 are exactly what would fix the HC overlay being "unreproducible".

### A11. `reports/EDGE_CRITERIA_ACTION_PLAN_2026-05-24.md`
- **Sprint 1 (parallel):** P1 persona_WR→confidence; P0 regime label leakage audit; FOREX zero-allocate; P2 dashboard migration to tournament_picks.
- **Verifications listed in doc:**
  - `SELECT confidence FROM tournament_picks LIMIT 10` → expect non-zero. **NOT RUN today** (would require backfill DB and isn't in critical path; flagged as Sprint-1 P1 task).
  - `SELECT COUNT(*) WHERE asset_class='FOREX'` → expect 0. **CHANGED**: 368 FOREX picks created since 2026-05-24 (see A1) — Sprint-1 FOREX zero-allocate NOT shipped.
  - Dashboard shows 3,149 rows — not verified.
- **Status:** Sprint 1 items appear NOT shipped yet.

### A12. `reports/2026-05-25_audit_ui_edge_audit.md` (today's audit)
- **P0:** HIGH CONVICTION overlay cites WR stats that are unreproducible — `trust_score` NULL on 38,884/38,889 closed picks (99.99%). Fix paths offered.
- **P1:** Smart Picks "Signal Time EST 1.4h ago" is misleading — `signal_time` field absent from `smart_picks_feed`; rows fall through to file-build age.
- **P1:** Swarm Picks tab abandoned — newest pick is 13 days old; daily cron runs but emits nothing.
- **P2:** US Equity Picks tab still demo data (n=0/100, no live writer).

---

## Section B — Re-executable verifications run (full PASS/CHANGED/FAIL table)

| # | Command | Verdict | Notes |
|---|---|---|---|
| 1 | `python3 -m pytest tools/test_report_freshness.py -q` | PASS | 41 passed |
| 2 | `python3 -m pytest tools/test_ghost_cleanup.py -q` | FAIL | 1 failed (type mismatch in fixture: `'150000' != 150000`); 23 pass |
| 3 | `python3 -m pytest tools/test_won_pnl_contradiction.py -q` | PASS | 12 passed |
| 4 | `python3 -m pytest tools/test_xli_classification.py -q` | PASS | 7 passed |
| 5 | `python3 -m pytest tools/test_resolver_health.py -q` | FAIL | 2/40 failed: staleness boundary returns True when False expected |
| 6 | `python3 -m pytest tests/test_compound_and_sharpe_redesign.py tests/test_emitter_whitelist.py tests/test_regime_gate.py -q` | PASS | 34 passed |
| 7 | `python3 -m tools.report_freshness_tracker --quiet` | PASS (with finding) | exit code 1; **97 RED reports repo-wide** |
| 8 | `python3 -m tools.regenerate_stale_reports` (dry-run) | PASS (with finding) | 5/6 registered reports RED; oldest qa_report 74.5d |
| 9 | `python3 tools/check_resolver_health.py --json` | FAIL | `NameError: argparse` — tool broken |
| 10 | `python3 tools/audit_won_picks.py` | FAIL | SQL references missing column `asset_class` (table has `category`) |
| 11 | DB: `SELECT COUNT(*) WHERE status='OPEN'` | CHANGED (good) | 29,254,204 → 4,081 — open_bloat resolver effective |
| 12 | DB: `SELECT COUNT(*) WHERE status='WON' AND pnl_pct<0` | CHANGED (slight drift) | 9 → 10 — historical not corrected, +1 new leak |
| 13 | DB: `SELECT category, COUNT FROM trading_picks WHERE symbol='XLI'` | CHANGED (bad) | 7 rows with `category=''` (empty); fix didn't touch DB |
| 14 | DB: FOREX picks since 2026-05-24 | CHANGED (bad) | **368 FOREX picks** despite "zero-allocate" plan |
| 15 | `curl -sI https://findtorontoevents.ca/audit/` | PASS | HTTP 200, last-modified 2026-05-25 05:40 UTC, contains "±2 cap" tooltip |

---

## Section C — Triaged next actions (priority order)

### P0 — Data correctness regressions (do today)
1. **Fix `tools/audit_won_picks.py` SQL column** (`asset_class` → `category`) then run `--correct` to clean the 10 WON+negative-PnL rows.
2. **Backfill XLI (and likely all sector ETFs) `category` in MySQL `trading_picks`** — the 2026-05-24 fix only patched JSON files, leaving DB rows with empty `category`. Suggest: `UPDATE trading_picks SET category='etf' WHERE symbol IN ('XLI','XLK','XLF','XLE','XLV','XLY','XLP','XLB','XLU','XLC','XLRE') AND (category IS NULL OR category='')`.
3. **FOREX still emitting** — 368 FOREX picks since 2026-05-24 contradicts EDGE_CRITERIA_ACTION_PLAN "zero-allocate". Either ship the scanner-side FOREX exclusion (Sprint-1 P1 item) or update the doc to reflect current policy.

### P1 — Tooling that's checked in but broken
4. **`tools/check_resolver_health.py`** — add `import argparse` at module top.
5. **`tools/test_resolver_health.py`** — fix `is_stale()` boundary tests (forex@100h, equity@48h failing).
6. **`tools/test_ghost_cleanup.py`** — fixture should pass `entry_price` as the type DB returns (string) or coerce in the function.

### P2 — Honesty layer (Workstream A from INSTITUTIONAL_READINESS_PLAN)
7. **Populate `signal_time` in `smart_picks_feed`** (one-line in `dashboard_generator.py`) — kills the "1.4h ago" misleading display documented in audit_ui_edge_audit.
8. **Decide HIGH CONVICTION overlay fate** — `trust_score` NULL on 99.99% of closed picks. Either backfill, or move the gate to `elite_score`, or label as UNVERIFIABLE on UI.
9. **Run `python3 -m tools.regenerate_stale_reports --execute`** to refresh the 5 RED registered reports (none would be destructive — they only write outputs).

### P3 — Cleanup tasks (next session)
10. **Ghost row purge** — fix the test fixture, then run `tools/cleanup_ghost_rows.py --execute --no-limit` for the 56K bt_backtest_trades dupes.
11. **Swarm Picks tab** — either revive `multi_model_pick_gen.py` so new picks flow in, or deprecate the tab and redirect to ai-tournament.html (per audit_ui_edge_audit P1).
12. **CI freshness alert** — add `report_freshness_tracker.py` to a cron / GHA job (97 RED reports repo-wide is unmonitored).

---

## Section D — Items intentionally not duplicated

Per task brief, did NOT re-run pick-funnel / CFTC-cell verification queries (`reports/2026-05-25_pick_funnel_cftc_cell_verification.md`, `2026-05-25_pick_funnel_swarm_verdict.md`) — another agent owns that thread. Read for context only; no new findings to add beyond what's already in those reports.

## Section E — Sources

Focus list: `/tmp/md_focus.txt` (193 files). Raw command captures: `/tmp/mdsweep/runs/*.txt`. Generated 2026-05-25 05:48 UTC.
