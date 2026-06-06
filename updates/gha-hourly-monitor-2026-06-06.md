# GHA Hourly Health Monitor — 2026-06-06

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

All 15 sampled CI Tests runs on main are failures (earliest: 2026-06-05T17:38Z). Run attempt counter reached 6 on run 27056316059, confirming this is not a transient flake.

**Failing tests (31 total) — AUTHOR_FIX:** `= 31 failed, 6125 passed, 62 skipped in 369.83s`

| Group | Tests | Root cause |
|---|---|---|
| FOREX hard-disable gate | `test_audusd_blocked_for_all_forex_sources`, `test_forex_hard_disable_default_on`, `test_gate_on_still_blocks_other_forex_sources`, `test_ns_e_filter_default_off` | `FOREX_HARD_DISABLE` not defaulting ON; `passes_active_gate` returns True for FOREX sources |
| M-096 CT=F concentration cap | 4 tests in `test_m096_ctf_concentration_cap.py` | Gate returns False for all cases including fail-open and below-cap; gate not implemented/wired |
| Money ready verdict | 6 tests in `test_money_ready_verdict.py` | Returning `NOT_READY` where `MONEY_READY` or `WATCH` expected; concentration cap changes likely over-firing |
| MySQL sync category inference | 6 tests in `test_mysql_sync_category_inference.py` | Code returns `'CRYPTO'` (uppercase); tests expect `'crypto'` (lowercase); normalization changed |
| ETF tight gate | 3 tests in `test_p1_gates_etf_tight_crypto_consensus.py` | Gate returning False for scores that should pass; `ETF_TIGHT_GATE` logic inverted or absent |
| PEAD equity signals | 2 tests in `test_equity_pead_strategy.py` | `len([]) == 0` — signals not generated; PEAD emitter not running |
| Eagle2 equity dragger blocks | `test_equity_dragger_strategies_blocked_2026_06_05` | `('EQUITY', 'multi_asset_copytrader')` not in `BLOCKED_ASSET_STRATEGY_PAIRS` |
| M-001 COT stale gate | `test_multi_asset_cot_source_stamped` | `assert False is True` |
| Tournament DB loader | `test_tournament_loader_transforms_db_rows` | 0 rows returned instead of 2 |

**Additional syntax error:** `Couldn't parse 'alpha_engine/backtest_quant_algorithms.py' as Python source: 'invalid syntax' at line 1` — this file cannot be imported by any production code until fixed.

**Likely root cause:** PR #552 "feat(ops): PEAD shadow cron + EQUITY dragger blocks" (merged 2026-06-05T14:42Z) — CI first failed at 2026-06-05T17:38Z (~3 h post-merge). The eagle2 equity dragger test is dated 2026-06-05 matching the PR. Multiple subsequent test failures in M-096, money_ready_verdict, and ETF gates suggest either dependent gates share a config path or additional commits after #552 introduced secondary breakage.

**Chronic workflows:** none — no per-workflow chronic cancellation detected. From 100 recent runs: 28/30 unique workflows had `success`; `MySQL Trading Picks Sync` had one `failure` (run 27062869569, `ModuleNotFoundError: No module named 'alpha_engine'` — PYTHONPATH not set in workflow, AUTHOR_FIX); `Social Media Prediction Tracker` had one `in_progress` run (no chronic pattern).

**Open PRs RED:**

| PR | Title | CI Status | Classification | Action |
|---|---|---|---|---|
| #553 | feat(picks-now): multi-factor quant screener + actionable picks per asset class | CI Tests failing (same 31-test failure set as main; branch is off main) | AUTHOR_FIX (inherited from main RED) | Block merge until main CI is green |

**Action required:** **Author must fix CI Tests on main before any PR can merge.**

Priority fixes by test count:
1. `FOREX_HARD_DISABLE` gate (4 tests) — ensure default is `True` in `alpha_engine/config.py` or `gates.py`
2. M-096 CT=F concentration cap (4 tests) — gate is returning `False` for all inputs including fail-open path
3. Money ready verdict (6 tests) — likely downstream of M-096 or concentration gate over-blocking
4. MySQL sync category case (6 tests) — decide: normalize to lowercase or update test expectations
5. ETF tight gate (3 tests) — `ETF_TIGHT_GATE` env var handling
6. Syntax error in `alpha_engine/backtest_quant_algorithms.py` line 1

**Failing run:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27056316059

**Status change vs 2026-05-22 00:00 UTC (last recorded):** GREEN → RED (verdict changed; no monitor runs between 2026-05-22 and 2026-06-06).
