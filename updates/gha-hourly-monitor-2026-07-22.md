# GHA Hourly Health Monitor — 2026-07-22

## 13:00 UTC

**Verdict:** DEGRADED

**Note on "CI Tests" workflow:** No workflow named "CI Tests" exists in this repository (362 workflows present). The equivalent CI gate is the `test (3.11)` / `test (3.12)` matrix jobs that run on every PR via the pytest CI workflow. Production cron workflows are used as the main-branch health proxy.

**Main production workflows (last 15 runs each):**

| Workflow | Successes | Failures | Cancels | Latest |
|---|---|---|---|---|
| Sports endpoint smoke + Playwright | 15/15 | 0 | 0 | success (12:46Z) |
| Unified Audit Dashboard | 13/15 | 0 | 1 | in_progress (12:44Z) |
| ALPHA ENGINE - Live Autonomous Scanner | 14/15 | 0 | 0 | in_progress (12:40Z) |

**Chronic workflows:** none (0 workflows meet the 4-cancel / 0-success / latest=cancelled threshold in the scanned window)

**Open PRs with CI test failures:**

| PR | Title | Failing checks | Root cause | Action |
|---|---|---|---|---|
| #667 | feat(b5): forward-track cell selector | test(3.11) FAIL, test(3.12) FAIL | Syntax error in `alpha_engine/backtest_quant_algorithms.py:1` on main | AUTHOR_FIX |
| #666 | fix(resolver): B1 backfill price guard | test(3.11) FAIL, test(3.12) FAIL | Same root cause | AUTHOR_FIX |
| #665 | audit(stalled-producer-detector): v2.0+2 | test(3.11) FAIL, test(3.12) FAIL | Same root cause | AUTHOR_FIX |
| #600 | feat(edge): money-ready hunt | test(3.11) FAIL, test(3.12) FAIL | Same root cause | AUTHOR_FIX |
| #657 | feat(contract-test): cold-merge gate | no checks (PR has `[skip ci]`) | — | NONE |

**Root cause detail:**

`alpha_engine/backtest_quant_algorithms.py` on `main` has corrupted content at line 1:
```
IsADirectoryErrorCHATWITHIT.mdmd atTH..D
```

This is a garbled error message written to the file (likely an `IsADirectoryError` from a script that tried to write to a directory path). `py_compile` fails on this immediately, causing all pytest CI runs to abort before any tests execute. Last commit touching this file: `9c78e61b` (Gainer scan 2026-07-22 12:41 UTC [skip ci]).

All 4 failing PRs share the same base (`69c8ff54`) and have been blocked since at least June 24, 2026. Production cron workflows remain healthy because they don't invoke `py_compile` on this file at startup.

**Action required:** Operator should fix `alpha_engine/backtest_quant_algorithms.py` on main — restore or regenerate the file from its last known-good state, then push to main with `[skip ci]` if needed to avoid re-triggering, then rerun CI on affected PRs. Run IDs for reference: PR #667 = 28109985534, PR #666 = 28108849365, PR #665 = 28068271376.
