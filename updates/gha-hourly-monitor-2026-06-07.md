# GHA Hourly Health Monitor — 2026-06-07

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

> Last 5 runs on main (all failed):
> - 27074654009 — 2026-06-06T21:41Z — https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27074654009
> - 27074537172 — 2026-06-06T21:36Z
> - 27074289083 — 2026-06-06T21:24Z
> - 27071375492 — 2026-06-06T19:13Z
> - 27063442097 — 2026-06-06T13:21Z
>
> Total CI Tests failures in history: 469+ runs. Streak unbroken since 2026-06-05T14:36Z (40+ consecutive failures).
> Failure mode: **AUTHOR_FIX** — multiple real assertion errors (not infra flake), step "Run all tests" in both Python 3.11 (cancelled) and 3.12 (failure) matrix jobs.
>
> **Failing test files (from run 27074654009 / job 79922911767):**
> - `tests/test_m096_ctf_concentration_cap.py` — M-096 CTF concentration cap returns False for all cases (should pass ≤35%, non-CT=F symbols, fail-open with no data, skip when n<5 COMMODITY)
> - `tests/test_money_ready_verdict.py` — M-070 concentration caps returning NOT_READY instead of WATCH; M-105 shadow mode stamping returns None instead of NOT_READY
> - `tests/test_mysql_sync_category_inference.py` — category inference returns `'CRYPTO'` (uppercase) but tests expect `'crypto'` (lowercase); 6+ test cases
> - `tests/test_equity_pead_strategy.py` — PEAD signals: 0 generated vs 1 expected, 0 vs 3 confidence; correlates with PR #552 (PEAD shadow cron, merged 2026-06-05T14:42Z)
> - `tests/test_m001_cot_stale_gate.py` — multi-asset COT source stamp: assert False is True
> - `tests/test_pf_registry_tournament_db.py` — tournament loader transforms DB rows: 0 rows vs 2
> - `tests/test_cta_replicator_symbol_gate.py` — AUDUSD FOREX block assertion
> - ETF tight gate tests — score=62 above floor=60 returns False

**Chronic workflows (cancellation criteria):** none — no workflow shows ≥4 cancellations in last 15 runs with 0 successes

> ⚠️ **Operational chronic failure (NOT cancellation-based, flagged separately):**
> - **MySQL Trading Picks Sync** (`mysql-trading-sync.yml`, workflow ID 281979102): 30/30 failures since 2026-06-05T23:53Z (40+ hour streak). Failing step: "Sync trading picks to MySQL" (job `sync`, step 5). Total run count: 264. Run frequency: ~hourly/every-2h. Latest failing run: 27093367205 (2026-06-07T13:03Z). This is an **operational failure** — trading picks are NOT being synced to MySQL. Likely related to `test_mysql_sync_category_inference.py` failures (CRYPTO vs crypto casing regression).

**Open PRs RED:** #553 — `feat(picks-now): multi-factor quant screener + actionable picks per asset class`
> - Branch: `money-ready-picks-now-2026-06-06`, head SHA `5be042d7`
> - Classification: **AUTHOR_FIX** — same upstream test assertion failures that have broken main CI since June 5 will block this PR. The CI failure is NOT specific to PR #553's changes; it reflects a broken main baseline. The PR cannot be merged until main CI Tests passes.
> - Recommended action: fix the failing test suites on main first, then rebase PR #553 on the fixed main.

**Action required:** **AUTHOR FIX — multiple test suites broken on main**
- Fix `tests/test_mysql_sync_category_inference.py`: category inference returns `'CRYPTO'` (uppercase) but expects `'crypto'` — likely a case normalization regression
- Fix `tests/test_m096_ctf_concentration_cap.py`: M-096 CTF concentration gate logic broken (all assertions return False)
- Fix `tests/test_equity_pead_strategy.py`: PEAD signal generation returning 0 — check `alpha_engine/equity_pead_strategy.py` against PR #552 changes
- Fix `tests/test_money_ready_verdict.py`: M-070/M-105 verdict logic returning NOT_READY or None instead of expected states
- Fix MySQL Trading Picks Sync operational failure — 40+ hour outage, trading picks not reaching DB
- Note: 15-day monitoring gap (last run 2026-05-22 verdict GREEN → today RED); no intermediate state available

**Verdict change:** GREEN (2026-05-22 06:15Z) → RED (2026-06-07 13:00Z)

---
