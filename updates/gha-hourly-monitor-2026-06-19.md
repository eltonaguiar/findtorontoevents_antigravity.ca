# GHA Hourly Health Monitor — 2026-06-19

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 15):** 0 success, 15 failure, 0 in_progress

All 15 CI Tests runs on main today have failed — continuous from 00:43 UTC through 12:53 UTC (12+ hours). Latest failing run: `27826874260` (12:53 UTC, commit `d3b38a87a5`).

**Failing step (both py3.11 and py3.12 jobs):** `Run all tests (gating — known-drift quarantined)` (step 8 of 13)
**Score:** 35 failed / 35 passed in 50.04s

**Failing tests — 35 failures across 7 test files:**

| File | Failure summary |
|---|---|
| `test_money_ready_verdict.py` | `test_shadow_mode_stamps_quarantine_fields` (None ≠ 'NOT_READY'); `test_commodity_source_concentration_fails_above_60pct` ('NOT_READY' ≠ 'WATCH'); `test_m070_*` (4 tests: NOT_READY returned instead of WATCH or MONEY_READY); `test_money_ready_high_edge` (NOT_READY not in allowed) |
| `test_portfolio_engine.py` | `test_drawdown_breaker` (True is not False); `test_evaluate_entry_happy_path_open` (isclose(92.0,93.5) fails); `test_evaluate_entry_aggressive_crypto_open_trail` (65000.0 is not None); `test_tp_sl_*` (4 tests — TP/SL price computation wrong); `test_would_breach_gross_cap_explicit` (wrong reason key: 'max_open_positions' ≠ 'gross_exposure_cap_pct') |
| `test_quality_gates.py` | `test_gate_on_still_blocks_other_forex_sources` (cta_replicator FOREX not blocked, reason=''); `test_forex_hard_disable_default_on` (FOREX_HARD_DISABLE not defaulting ON — passes_active_gate returns True) |
| `test_trust_tier_non_crypto_default_on.py` | `test_equity_banned_passes_by_default`, `test_etf_banned_passes_by_default`, `test_force_flag_non_one_value_treated_off`, `test_pr508_legacy_flag_still_works_for_equity` — all: passes_active_gate returns False when True expected |
| `test_kimi_promotion_unblock.py` | `test_equity_kimi_pick_high_score_passes`, `test_equity_kimi_pick_score_0_still_passes` — passes_active_gate returns False |
| `test_ns_c_e_exec_gate_filters.py` | `test_ns_e_filter_default_off` — FOREX_HARD_DISABLE flag not readable (None) |
| `test_pf_registry_tournament_db.py` | `test_tournament_loader_transforms_db_rows` — assert 0 == 2 |

**Secondary finding:** `alpha_engine/backtest_quant_algorithms.py` reports **syntax error at line 1** during the coverage pass — not the primary failure cause but indicates a broken file on main.

**Failure classification:** AUTHOR_FIX — assertion errors in core business logic (`passes_active_gate`, FOREX gate, portfolio engine TP/SL, drawdown breaker, money ready verdict). Not infra flakes.

**Likely root cause:** A recent commit to main changed the semantics of `passes_active_gate` and/or the FOREX_HARD_DISABLE default — EQUITY and ETF picks now fail the gate (False instead of True), and FOREX hard-disable is no longer defaulting ON. The portfolio engine TP/SL price formula also regressed (off by ~1.5 units in the test assertions). The money ready verdict M-070 concentration logic was loosened — WATCH cases now return NOT_READY. Recommend identifying the commit landed between the last green CI run and 00:43 UTC today.

**Chronic workflows:** none — no workflow meets the chronic-cancellation definition (latest=cancelled AND ≥4 cancels in last 15 AND 0 successes AND no success in 48h).

**Notable: `.github/workflows/alpha-engine-live.yml` in pure-failure death spiral:** 15/15 consecutive failures in last 15 runs (today only), 0 successes, 0 cancels — all on main. Does NOT meet the CHRONIC (cancellation-based) definition but is effectively broken and needs triage alongside CI Tests.

**Open PRs RED:**

| PR | Title | CI Status | Recommended action |
|---|---|---|---|
| #581 | feat(audit): P2-9 model_portfolios.html + P1-4/6/7/8 investigations | `test (3.11)` ❌ `test (3.12)` ❌ | AUTHOR_FIX — CI was already failing on this branch's head (run 27457937894, 2026-06-13); same logic regression as main |
| #600 | feat(edge): money-ready hunt — intrabar tools + 4-agent verdict | Not recently checked — branch head `801482e6e1` | Likely AUTHOR_FIX same root cause |
| #595 | feat(validate): non-crypto intrabar replay scaffold (Stage-4 gate) | Not recently checked | Likely AUTHOR_FIX same root cause |
| #594 | docs: session progress summary | Not recently checked | May be unaffected (docs only) |
| #577 | fix(blocklist): kill luxalgo_filters | Not recently checked | Likely AUTHOR_FIX same root cause |
| #564 | docs: Audit Edge Hunt Action Plan & Deep Dive | Not recently checked | May be unaffected (docs only) |
| #562 | feat(audit): edge hunt session docs, pass-hunter tools | Not recently checked | May be unaffected (tools + docs) |

**Action required:** Author fix on main — core logic regression in `passes_active_gate` (EQUITY/ETF now blocked; FOREX gate defaulting wrong), portfolio engine TP/SL computation, and money ready verdict M-070 concentration rules. `alpha_engine/backtest_quant_algorithms.py` syntax error needs fixing separately.

**Failing run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27826874260

**Status change vs 2026-05-22 00:00 UTC:** GREEN → RED (first monitor entry for 2026-06-19; CI has been red all day since 00:43 UTC).
