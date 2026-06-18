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

**Action required:** operator must:
1. Fix `alpha_engine/backtest_quant_algorithms.py` — restore valid Python content (current line 1 is garbage: `IsADirectoryErrorCHATWITHIT.mdmd atTH..D`); last touched by commit `8d13fcd1`
2. Merge PR #599 and PR #601 to fix the 91 M-036 gate-test failures on main
3. Optionally audit how a [skip ci] data commit overwrote a Python source file with markdown/error content — `backtest_quant_algorithms.py` may have been clobbered by a runaway automated writer
