# GHA Hourly Health Monitor — 2026-07-17

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

Runs (newest first):
| Run ID | Created | Conclusion | SHA |
|---|---|---|---|
| 29582037989 | 2026-07-17T12:55:44Z | failure | d1d70477 |
| 29578320987 | 2026-07-17T11:52:50Z | failure | 5a21b5cc |
| 29574710904 | 2026-07-17T10:48:37Z | failure | c45b1e0c |
| 29571175328 | 2026-07-17T09:46:42Z | failure | 8a910544 |
| 29567605584 | 2026-07-17T08:46:52Z | failure | f77789dc |

**Chronic workflows:** none detected via cancellation criteria. CI Tests itself is CHRONIC RED — 30/30 consecutive failures across 36+ hours (2026-07-16T01:43Z → 2026-07-17T12:55Z), but the failure mode is a test error (not cancellation).

**Failing step:** `Run all tests (gating — known-drift quarantined)` — both `test (3.11)` and `test (3.12)` jobs.

**Root cause (confirmed):**
`alpha_engine/backtest_quant_algorithms.py` contains corrupted non-Python content at line 1:
```
IsADirectoryErrorCHATWITHIT.mdmd atTH..D
```
This causes both Python 3.11 and 3.12 coverage parsers to fail with:
```
Couldn't parse '.../alpha_engine/backtest_quant_algorithms.py' as Python source: 'invalid syntax' at line 1
```
File was last touched by commit `7b43f8f3` ("Recommended portfolio 2026-07-17 11:01 UTC [skip ci]") — a bot workflow that appears to have overwritten the Python source with garbage content.

**Open PRs CI status:** 9 open PRs (#667, #666, #665, #657, #600, #595, #581, #564, #562). All target `main` and will inherit the same CI breakage since `backtest_quant_algorithms.py` is in the repository at HEAD. Classification: **AUTHOR_FIX** — requires restoring the valid Python content of `alpha_engine/backtest_quant_algorithms.py` before any PR can go green.

**Action required:** AUTHOR must restore `alpha_engine/backtest_quant_algorithms.py` to valid Python source. The file currently contains 3 lines of corrupted text instead of Python code. Recommended fix: `git show <good-sha>:alpha_engine/backtest_quant_algorithms.py > alpha_engine/backtest_quant_algorithms.py` using a commit prior to `7b43f8f3`. Then commit and push to unblock all CI.

**Failing run:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/29582037989

---
