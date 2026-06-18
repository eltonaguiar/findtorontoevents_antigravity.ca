# GHA Hourly Health Monitor — 2026-06-18

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 15 on main):** 0 success, 15 failure, 0 in_progress  
*(All 30 runs in payload are failures — persistent breakage since at least 2026-06-17T15:08Z, ~22h unresolved)*

**Chronic workflows:** none  
*(sports-smoke-and-e2e: GREEN — 10+ consecutive successes as of 11:37Z; 3 old cancellations on 2026-06-17, not CHRONIC)*

**Open PRs RED:** 23 open PRs total; statusCheckRollup unavailable from list API, but the following are known test-fix PRs for the CI breakage:
- **#599** `fix(tests): stamp_feed_membership fixture exempts M-036 + CRYPTO_PRODUCTION_BLOCK_LONG` — AUTHOR_FIX: fixes `test_stamp_feed_membership.py` for 91 gate-test failures from M-036 CRYPTO LONG block; **unmerged**
- **#601** `fix(tests): wf_verdict gate tests use EQUITY base (unblock from M-036 CRYPTO-LONG block)` — AUTHOR_FIX: companion fix for `test_wf_verdict_*`; **unmerged**

**Failure diagnosis (run 27759346825, 2026-06-18T12:27Z):**
- **Root cause A** (confirmed): `alpha_engine/backtest_quant_algorithms.py` has garbage content at line 1 (`IsADirectoryErrorCHATWITHIT.mdmd atTH..D`) — not valid Python. Introduced by `[skip ci]` data commit `8d13fcd1` ("data: specialized scanner picks update [2026-06-18_10:37]"). CI coverage stage cannot parse the file.
- **Root cause B** (known, pre-existing): 91 gate-test failures from M-036 CRYPTO LONG block policy introduced ~2026-06-13. Fix PRs #599 and #601 are open but not yet merged.
- **Both jobs fail**: `test (3.11)` (job 82129353401) and `test (3.12)` (job 82129353412) — same error on both Python versions.
- **Failing run URL**: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27759346825

**Pytest results (run 27759346825):**
- Python 3.11: **35 failed, 35 passed** in 50.57s
- Python 3.12: **92 failed, 6062 passed**, 62 skipped in 181.21s

**Failure clusters (3.11 job):**

| Cluster | Count | Signal |
|---|---|---|
| `test_money_ready_verdict.py` M070/M105 | 7 | `money_ready_verdict()` returns `NOT_READY` where `WATCH`/`MONEY_READY` expected |
| `test_portfolio_engine.py` | 7 | TP/SL floor, drawdown breaker, `max_open_positions` vs `gross_exposure_cap_pct` key |
| `test_trust_tier_non_crypto_default_on.py` | 4 | Non-crypto EQUITY/ETF `passes_active_gate` returns False; bypass flags broken |
| `test_quality_gates.py` FOREX | 2 | `FOREX_HARD_DISABLE` not defaulting ON; FOREX passes gate without override |
| `test_kimi_promotion_unblock.py` | 2 | `passes_active_gate` False for EQUITY kimi picks |
| `test_ns_c_e_exec_gate_filters.py` | 1 | `FOREX_HARD_DISABLE` env var unreadable with default |
| `test_pf_registry_tournament_db.py` | 1 | Tournament loader returns 0 rows instead of 2 |

**3.12-only failures:** `test_wf_verdict_null_block.py` — CRYPTO `passes_active_gate` returns False when True expected (5+ visible; this is the M-036 block from PR #601). Secondary run hit a live network timeout in `alpha_engine/bond_data_fred.py` (real HTTPS call to FRED API not mocked, 120s pytest-timeout fired).

**Action required:** operator must:
1. Fix `alpha_engine/backtest_quant_algorithms.py` — restore valid Python content (current line 1 is garbage: `IsADirectoryErrorCHATWITHIT.mdmd atTH..D`); last touched by commit `8d13fcd1`
2. Merge PR #599 and PR #601 to fix the M-036 gate-test failures on main
3. Review `test_money_ready_verdict.py`, `test_portfolio_engine.py`, `test_trust_tier_non_crypto_default_on.py`, and `test_quality_gates.py` failure clusters — these are broader than the M-036 single-axis fix in #599/#601 and may require additional investigation
4. Mock or skip the live FRED API call in `bond_data_fred.py` for CI (causes 120s+ hang in secondary run)
5. Audit how a [skip ci] data commit overwrote a Python source file — `backtest_quant_algorithms.py` was clobbered by a runaway automated writer
