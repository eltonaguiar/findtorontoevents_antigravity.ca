# GHA Hourly Health Monitor — 2026-06-10

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

Failing run IDs (most-recent first):
- 27275459244 — 2026-06-10T12:14Z — SHA 312b440
- 27269432095 — 2026-06-10T10:17Z — SHA 914a3cb
- 27260009786 — 2026-06-10T07:19Z — SHA 8827b7a
- 27257583668 — 2026-06-10T06:25Z — SHA 5fda366
- 27255576640 — 2026-06-10T05:34Z — SHA 37ff92f

CI has been failing continuously since at least 05:34 UTC. Total across 30 sampled runs today: **0 success / 30 failure**.

**Failure summary (run 27275459244):** `41 failed, 6140 passed, 62 skipped` in 363s.

Top failing tests (AUTHOR_FIX required):

| Test file | Assertion | Classification |
|---|---|---|
| `test_mysql_sync_category_inference.py` (6 tests) | `'CRYPTO' == 'crypto'` — code returns uppercase, tests expect lowercase | AUTHOR_FIX |
| `test_stocks_7_classifier_override.py` | `'CRYPTO' == 'crypto'` — same case normalization regression | AUTHOR_FIX |
| `test_money_ready_verdict.py` (7 tests) | `n=67 == 15`, `NOT_READY` vs `WATCH`, `NOT_READY` vs `MONEY_READY` | AUTHOR_FIX |
| `test_portfolio_engine.py` (7 tests) | `isclose(92.0, 93.5)`, `drawdown_breaker` logic, `gross_exposure_cap_pct` key | AUTHOR_FIX |
| `test_quality_gates.py` (2 tests) | `FOREX_HARD_DISABLE` must default ON; CTA replicator bypass broken | AUTHOR_FIX |
| `test_p1_gates_etf_tight_crypto_consensus.py` (3 tests) | ETF tight gate score threshold failures | AUTHOR_FIX |
| `test_ns_c_e_exec_gate_filters.py` | `FOREX_HARD_DISABLE` env var not set / returns None | AUTHOR_FIX |
| `test_pf_registry_tournament_db.py` | `tournament_loader_transforms_db_rows`: 0 == 2 | AUTHOR_FIX |

**Root cause analysis (two regression groups):**
1. **Case normalization regression** — `test_mysql_sync_category_inference.py` and `test_stocks_7_classifier_override.py` all expect lowercase `'crypto'` but code returns `'CRYPTO'`. Likely introduced by a PR changing `asset_class` normalization to uppercase (PRs #559/#560/#561 all touched resolver/portfolio logic today).
2. **Logic regressions** — `money_ready_verdict` min_n threshold changed (67 vs expected 15); `portfolio_engine` TP/SL math and `drawdown_breaker` behavior; `quality_gates` `FOREX_HARD_DISABLE` default flipped. Matches portfolio risk profile changes in PR #560 (`drawdown_breaker_pct` tightening) and resolver changes in PR #559.

Failing run URL: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27275459244

**Chronic workflows:** none — all sampled high-frequency workflows are healthy:
- ALPHA ENGINE Gainer Capture (15min): 30/30 success
- Audit Hourly Update: 30/30 success
- ALPHA ENGINE - Live Autonomous Scanner: 30/30 success
- Sports endpoint smoke + Playwright: 30/30 success

**Open PRs RED:** none — no open PRs at time of scan.

**Action required:** operator/author should fix the 41 failing tests on main. Priority:
1. Fix case normalization — `asset_class` return value changed to uppercase; tests expect lowercase `'crypto'`. Check recent changes to `mysql_sync` / classifier code.
2. Fix `money_ready_verdict` min_n threshold (test expects 15, code returns 67).
3. Fix `FOREX_HARD_DISABLE` default — must be ON by default.
4. Fix `portfolio_engine` TP/SL math and `drawdown_breaker` logic (likely regression from PR #560 `portfolio_risk_profiles.json` changes).

**Status change vs previous run (2026-05-22 23:00 UTC):** GREEN → RED (first run for 2026-06-10; no intermediate daily files exist for 2026-05-23 through 2026-06-09 — status was not monitored during that period).
