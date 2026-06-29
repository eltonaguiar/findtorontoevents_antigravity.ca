# GHA Hourly Health Monitor — 2026-06-29

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Chronic workflows:** none detected
- Sports Smoke & E2E (`sports-smoke-and-e2e.yml`): 15/15 success — healthy
- Other sampled workflows: all green

**Root cause (CI Tests failure):**
- Failing file: `alpha_engine/backtest_quant_algorithms.py`
- Error (both Python 3.11 and 3.12 jobs): `Couldn't parse '...alpha_engine/backtest_quant_algorithms.py' as Python source: 'invalid syntax' at line 1`
- Classification: **AUTHOR_FIX** — real syntax error in tracked file, not an infra flake
- Duration: RED since at least **2026-06-27T21:05 UTC** (30+ consecutive failures over 39+ hours)
- Failing run IDs (today): 28372469696, 28365663891, 28360066796, 28353337645, 28348120886
- Latest failing run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28372469696

**Open PRs RED:** Unable to determine individual PR CI check status via this run (statusCheckRollup not returned by list endpoint). Key open PRs: #667, #666, #665, #657, #600, #595, #581, #564, #562. Any PR touching `alpha_engine/backtest_quant_algorithms.py` will also fail CI.

**Action required:** author should fix `alpha_engine/backtest_quant_algorithms.py` — line 1 contains invalid Python syntax (likely merge conflict markers or truncated file). This has been blocking CI for 39+ hours.
