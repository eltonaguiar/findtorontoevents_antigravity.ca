# GHA Hourly Health Monitor — 2026-06-27

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

> Note: all 14 completed runs sampled (2026-06-26T18:48 → 2026-06-27T11:52) are `failure`. Run #1278 at 13:01 UTC is still in_progress. This is a persistent multi-hour regression, not a flap.

**Root cause (confirmed):** `alpha_engine/backtest_quant_algorithms.py` contains garbage text at line 1:
```
IsADirectoryErrorCHATWITHIT.mdmd atTH..D
```
Python `py_compile` fails immediately with `invalid syntax` at line 1 on both Python 3.11 and 3.12. Both `test (3.11)` and `test (3.12)` jobs in CI Tests exit with failure before any pytest runs. The file is 42 bytes and was last modified 2026-06-05 13:04 on disk. Git log shows the garbage content was carried into recent commits (`bea47423`, `14ac60dd`).

**Failing run (most recent completed):** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28288393768
- Job: `test (3.11)` — `Couldn't parse 'alpha_engine/backtest_quant_algorithms.py' as Python source: 'invalid syntax' at line 1`
- Job: `test (3.12)` — same error

**Chronic workflows:** none — 100-run global sample + per-workflow spot check showed no workflow with ≥4 cancellations and 0 successes. All 28 distinct non-CI workflows in the sample completed `success`.

**Open PRs RED (CI Tests `test` jobs failing):**

| PR | Title | Failure | Recommended action |
|----|-------|---------|-------------------|
| #667 | feat(b5): forward-track cell selector | test (3.11) + (3.12) FAILURE | AUTHOR_FIX — same root cause (backtest_quant_algorithms.py on head) |
| #666 | fix(resolver): B1 backfill price guard | test (3.11) + (3.12) FAILURE | AUTHOR_FIX |
| #665 | audit(stalled-producer-detector): v2.0+2 | test (3.11) + (3.12) FAILURE | AUTHOR_FIX |
| #600 | feat(edge): money-ready hunt — intrabar tools | test (3.11) + (3.12) FAILURE | AUTHOR_FIX (older branch, Jun 13) |
| #657 | feat(contract-test): cold-merge atomic | No CI checks | Has `[skip ci]` in commit — intentional |

**Action required:** Operator must fix `alpha_engine/backtest_quant_algorithms.py`. The file needs to be replaced with valid Python (or deleted if unused) and committed to main. Every CI Tests run will continue to fail until this file is corrected. PRs #667, #666, #665, #600 cannot pass CI until the file is fixed on their branches as well.

Fix command (if file should be empty/stub):
```bash
echo "# backtest_quant_algorithms — stub" > alpha_engine/backtest_quant_algorithms.py
git add alpha_engine/backtest_quant_algorithms.py
git commit -m "fix(ci): restore valid Python in backtest_quant_algorithms.py (garbage content broke CI)"
git push origin main
```
