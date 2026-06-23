# GHA Hourly Health Monitor — 2026-06-23

## 13:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 30 on main):** 28 success, 0 failure, 2 in_progress (Forward Signal Scanner, Mirror deploy — both launched at ~13:06-13:07 UTC)

**Sports endpoint smoke + Playwright:** HEALTHY — 30/30 success in last 30 runs; last run 2026-06-23T11:23:50Z (run 28022641406)

**Chronic workflows:** none — zero cancellations detected across main branch (last 30 runs) and sports smoke (last 30 runs)

**Note on "CI Tests" workflow:** No workflow file named `CI Tests` or `ci.yml` exists in this repo (404 on direct query). The Python test suite runs as jobs `test (3.11)` and `test (3.12)` inside a multi-job CI workflow triggered on PR pushes. Main branch itself shows no test failures in the last 30 runs.

---

### Open PRs CI Snapshot (7 open PRs)

| PR | Title | test (3.11) | test (3.12) | scan | Verdict | Action |
|---|---|---|---|---|---|---|
| #657 | feat(contract-test): cold-merge atomic contract-test gate | — | — | — | SKIP_CI | PR body contains `[skip ci]`; no checks ran — intentional |
| #622 | feat(honest-kill-switch): per-class thresholds + dashboard | FAIL ❌ | FAIL ❌ | pass | AUTHOR_FIX | `alpha_engine/backtest_quant_algorithms.py` invalid syntax at line 1 |
| #600 | feat(edge): money-ready hunt — intrabar tools | FAIL ❌ | FAIL ❌ | pass | AUTHOR_FIX | Same file: `alpha_engine/backtest_quant_algorithms.py` invalid syntax |
| #595 | feat(validate): non-crypto intrabar replay scaffold | pass | — | pass | GREEN | No pytest job triggered on this PR's head (security-only checks ran) |
| #581 | feat(audit): P2-9 model_portfolios + P1-4/6/7/8 investigations | FAIL ❌ | FAIL ❌ | FAIL ❌ | AUTHOR_FIX | test: same syntax error; scan: additional conflict/scan failure |
| #564 | docs: Audit Edge Hunt Action Plan & Deep Dive | FAIL ❌ | FAIL ❌ | FAIL ❌ | AUTHOR_FIX | test: same syntax error; scan: additional scan failure |
| #562 | feat(audit): edge hunt session docs, pass-hunter tools | pass ✅ | pass ✅ | pass | GREEN | All checks pass (oldest PR, pre-dates the syntax breakage) |

**Root cause for all test failures (PRs #622, #600, #581, #564):**
```
Couldn't parse 'alpha_engine/backtest_quant_algorithms.py' as Python source: 'invalid syntax' at line 1
```
This is a real code defect introduced into `alpha_engine/backtest_quant_algorithms.py` — the file has broken Python syntax at line 1. This is blocking CI on 4 open PRs. All 4 require an **AUTHOR_FIX**.

**Open PRs RED:** #622, #600, #581, #564 — author must fix `alpha_engine/backtest_quant_algorithms.py` (invalid syntax at line 1) on each branch.

**Action required:** Authors of PRs #622, #600, #581, #564 should fix `alpha_engine/backtest_quant_algorithms.py` syntax on their respective branches. Main is unaffected (the file either differs on main or these branches predate the fix).
