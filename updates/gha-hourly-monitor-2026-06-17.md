# GHA Hourly Health Monitor — 2026-06-17

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Failure duration:** 57+ consecutive hours — first failure observed 2026-06-15T02:14:40Z, ongoing through latest run 2026-06-17T11:39:12Z (run ID 27686234577).

**Failing step:** `Run all tests (gating — known-drift quarantined)` — 35 failed, 35 passed (both Python 3.11 and 3.12 jobs fail identically).

**Failing tests (latest run 27686234577):**

| Test file | Test name | Failure |
|---|---|---|
| `tests/test_portfolio_engine.py` | `test_evaluate_entry_aggressive_crypto_open_trail` | `assert 65000.0 is None` |
| `tests/test_portfolio_engine.py` | `test_evaluate_entry_happy_path_open` | `isclose(92.0, 93.5)` → False |
| `tests/test_portfolio_engine.py` | `test_tp_sl_aggressive_short_trail` | `assert 70.0 is None` |
| `tests/test_portfolio_engine.py` | `test_tp_sl_aggressive_trail_no_tp` | `assert 130.0 is None` |
| `tests/test_portfolio_engine.py` | `test_tp_sl_long_pct_floor` | `isclose(92.0, 93.5)` → False |
| `tests/test_portfolio_engine.py` | `test_tp_sl_short_pct_floor` | `isclose(108.0, 106.5)` → False |
| `tests/test_portfolio_engine.py` | `test_would_breach_gross_cap_explicit` | `'max_open_positions' != 'gross_exposure_cap_pct'` |
| `tests/test_quality_gates.py` | `TestForexCopytradeBypas::test_gate_on_still_blocks_other_forex_sources` | `cta_replicator FOREX not blocked: reason=''` |
| `tests/test_quality_gates.py` | `TestM044GateParity::test_forex_hard_disable_default_on` | `FOREX_HARD_DISABLE must default ON — assert True is False` |
| `tests/test_kimi_promotion_unblock.py` | `test_equity_kimi_pick_high_score_passes` | `passes_active_gate() → False (expected True)` |
| `tests/test_kimi_promotion_unblock.py` | `test_equity_kimi_pick_score_0_still_passes` | `passes_active_gate() → False (expected True)` |
| `tests/test_trust_tier_non_crypto_default_on.py` | `test_equity_banned_passes_by_default` | `passes_active_gate() → False (expected True)` |
| `tests/test_trust_tier_non_crypto_default_on.py` | `test_etf_banned_passes_by_default` | `passes_active_gate() → False (expected True)` |
| `tests/test_trust_tier_non_crypto_default_on.py` | `test_force_flag_non_one_value_treated_off` | `passes_active_gate() → False (expected True)` |
| `tests/test_trust_tier_non_crypto_default_on.py` | `test_pr508_legacy_flag_still_works_for_equity` | `passes_active_gate() → False (expected True)` |
| *(20 more not listed — full count 35 failed)* | | |

**Secondary signal:** Coverage step warns `alpha_engine/backtest_quant_algorithms.py` has **invalid syntax at line 1** (both Python versions). Likely a merge-conflict marker or generator artifact in that file.

**Root cause hypothesis:** PR #566 (merged 2026-06-13T17:50:40Z) added `kimi_riseoftheclaw` to `BLOCKED_SOURCE_SYSTEMS` and changed FOREX_HARD_DISABLE gate behavior. Tests in `test_kimi_promotion_unblock.py` and `test_trust_tier_non_crypto_default_on.py` were written expecting `kimi_riseoftheclaw` picks to pass for EQUITY — now blocked. FOREX gate tests expect `FOREX_HARD_DISABLE` default ON, but gate appears to pass FOREX now. TP/SL numeric mismatches in `test_portfolio_engine.py` suggest a formula change (93.5→92 delta = 1.5 discrepancy, consistent with a floor or multiplier change).

**Open PRs already tracking this:**
- PR #601 `fix(tests): wf_verdict gate tests use EQUITY base (unblock from M-036 CRYPTO-LONG block)` — body explicitly notes "91 gate-test failures on main-CI" (AUTHOR_FIX)
- PR #599 `fix(tests): stamp_feed_membership fixture exempts M-036 + CRYPTO_PRODUCTION_BLOCK_LONG` — body notes "PRE-EXISTING failures on main" (AUTHOR_FIX)

**Chronic workflows:** none detected (no chronic-cancellation pattern in last 15 runs of any checked workflow)

**Other workflow health:**
- **Sports endpoint smoke + Playwright** — GREEN: 30/30 successes (2026-06-15 through 2026-06-17T11:54Z)
- **Claude Gainer ML Live Scanner** — GREEN: 30/30 successes (2026-06-15 through 2026-06-17T11:54Z)
- **alpha-engine-live.yml** — RED: 30/30 failures since 2026-06-16T19:45Z (16+ hours); likely same root cause as CI Tests since alpha-engine imports the same quality-gates module

**Open PRs RED:** CI check-runs data requires per-SHA API calls not available here; PR bodies for #601 and #599 confirm pre-existing CI breakage is known and being worked. Recommended action: author merge one of #599/#601 to unblock main CI.

**Action required:** Author should fix — PRs #599 and #601 are in-flight fixes for the pre-existing CI failures. Priority: merge whichever unblocks the gate tests fastest. Also investigate `alpha_engine/backtest_quant_algorithms.py` line 1 syntax error. Failing run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27686234577

---
*Previous known verdict: GREEN (2026-05-22T00:00Z — last monitor run before this session)*
*Status change: GREEN → RED (transition date unknown; CI Tests first failure visible in data: 2026-06-15T02:14Z)*
