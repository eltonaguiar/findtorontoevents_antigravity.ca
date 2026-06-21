# Cluster B — Position-Cap-Constant Fixture Reconciliation (2026-06-21)

## What was broken

`tests/test_portfolio_engine.py` had **8 tests quarantined** in `/tmp/known_drift_tests.txt`
out of the 106 ci-tests gating failures (the rest of which cluster around the
CRYPTO-LONG-block, category inference, ETF P1 tight, M-096 CTF cap, PEAD
surprise-scaling, M-044 forex-hard-disable, and ~7 single-test miscellaneous
families — Cluster A owns CRYPTO-LONG-block and is a parallel task).

**Failing tests (pre-PR baseline):**

| # | Test | Drift symptom |
|---|---|---|
| 1 | `test_drawdown_breaker` | Hardcoded `-9.0` / `-5.0` against `CONS["drawdown_breaker_pct"]=-8.0`. Test signed wrong direction (failure flipped as upstream drift on the JSON). |
| 2 | `test_evaluate_entry_aggressive_crypto_open_trail` | Hardcoded `0.85` SL (= AGG-15%) + we asserted `tp_price is None`. AGG profile was rewritten on 2026-06-10 (tournament-portfolio-loss-fix) to a fixed 30% TP — `tp is None` no longer reachable. |
| 3 | `test_evaluate_entry_happy_path_open` | Hardcoded `93.5` SL (-6.5%) but CONS profile `pct_floor=-8.0` → SL is `92.0`. |
| 4 | `test_tp_sl_aggressive_short_trail` | Asserted `tp is None` / `sl=115.0`; AGG now has fixed 30% tp, sl=-15% of entry. |
| 5 | `test_tp_sl_aggressive_trail_no_tp` | Same as #4 — AGG no longer trail-only. |
| 6 | `test_tp_sl_long_pct_floor` | Hardcoded `sl=93.5` (-6.5%) but CONS `pct_floor=-8.0` → SL=`92.0`. |
| 7 | `test_tp_sl_short_pct_floor` | Hardcoded `sl=106.5` (-6.5% short SL); CONS `pct_floor=-8.0` → short SL=`108.0`. |
| 8 | `test_would_breach_gross_cap_explicit` | BAL scenario (15 opens × 7% + 1 cand = 16 positions × 7% = 112% > 110% gross) — but BAL was tightened 2026-05-29 (max_open=10, vs the old 20). 16 positions now breach `max_open_positions` first. The BAL→gross scenario is **mathematically unreachable** today. |

## What changed

Single PR (`fix/cluster-b-position-cap-fixture-reconciliation`), 100% test-side,
131 lines diff (103 added / 28 deleted) total in `tests/test_portfolio_engine.py`:

1. **Added the per-class import** the user explicitly requested:
   ```python
   from alpha_engine.per_class_position_caps import (
       PER_CLASS_POSITION_PCT,
       PER_CLASS_MAX_CONCURRENT,
   )
   ```

2. **8 test rewrites** — magic numbers replaced with PROFILES-driven formulas:
   - 5 tests (tp/sl long/short/agg/agg_short) now derive sl/tp from `CONS["stop_loss"]["pct_floor"]` / `CONS["take_profit"]["pct"]` and AGG equivalents. The fixture auto-tracks upstream edits to the JSON profile.
   - 1 test (`test_drawdown_breaker`) drives the threshold from `CONS["drawdown_breaker_pct"]`.
   - 1 test (`test_would_breach_gross_cap_explicit`) **switches BAL → AGG**: AGG's config (max_open=15, single=15%, class=65%, gross=160%) permits 10 opens × 15% + 1 cand × 15% = 165% to trip `gross_exposure_cap_pct` while staying under all other caps. AGG also includes all 8 asset classes that PER_CLASS_POSITION_PCT covers (so the test is per-class-system-safe once PR-B wires it).

3. **Added a drift-detection sentinel** (`test_per_class_caps_module_resolves`) that:
   - Asserts `PER_CLASS_POSITION_PCT` and `PER_CLASS_MAX_CONCURRENT` cover all 8 asset classes (CRYPTO/MEME/EQUITY/ETF/COMMODITY/FUTURES/FOREX/BOND).
   - Asserts key values are sane (non-zero pct, ≥1 concurrent slot).
   - Catches upstream drift in `alpha_engine/per_class_position_caps.py` before PR-B wires it into `risk.py` / `engine.py`.

## What was NOT changed

- ❌ **No production code touched.** `risk.py` / `engine.py` / `sizing.py` / `alpha_engine/per_class_position_caps.py` / `config/portfolio_risk_profiles.json` — all unchanged.
- ❌ **No per-class wire-up** (out of scope per the docstring on
  `alpha_engine/per_class_position_caps.py`: "OPT-IN SIDECAR … Caller wire-up
  follows in PR-B"). The drift-detection sentinel future-proofs the test for
  when PR-B lands — at that point, `risk.would_breach` and `engine.evaluate_entry`
  will read per-class caps and the new sentinel + the AGG-aligned gross-cap test
  both light up automatically.
- ❌ **No CI workflow edits.** No `.github/workflows/*` touched.

## Verification

**Pre-PR baseline (origin/main):** all 8 quarantined tests FAIL.
- Test 1 (`test_drawdown_breaker`): FAIL — `False == isclose(-9.0, -8.0)`.
- Test 3 (`test_evaluate_entry_happy_path_open`): SL drift → FAIL.
- Test 6 (`test_tp_sl_long_pct_floor`): `92.0 ≠ 93.5` → FAIL.
- Test 7 (`test_tp_sl_short_pct_floor`): `108.0 ≠ 106.5` → FAIL.
- Test 8 (`test_would_breach_gross_cap_explicit`): `max_open_positions` trips
  first (16 > 10), so `gross_exposure_cap_pct` assertion fails.

**Post-PR (this branch):** 50/50 tests PASS (49 original + 1 new sentinel).

```
$ python3 -m pytest tests/test_portfolio_engine.py
========================== 50 passed in 0.13s ===========================
```

## Risks / Caveats

1. **`test_would_breach_gross_cap_explicit` switched from BAL to AGG.** The original
   test scope (BAL gross cap alone) is no longer physically reachable under the
   2026-05-29 tightening. Trade-off accepted: the new AGG scenario tests the same
   gate symbol (`gross_exposure_cap_pct`) with valid AGG inputs. A future PR could
   add a separate BAL-path test using non-uniform weights, but that's outside the
   80-150 LOC budget.

2. **`test_tp_sl_aggressive_*` no longer tests the trail-only branch.** The
   `compute_tp_sl` else-branch (where `tp_price is None` due to missing TP config)
   loses coverage — AGG no longer has trail-only (fixed-tp on 2026-06-10).
   Mitigation: a future follow-on could add ONE new synthetic test for trail-only
   using a bare-bones appetite `{tp_pct: None, r_multiple: None}` — flagged as
   a potential follow-up, not in this PR.

3. **Per-class import is a sentinel TODAY.** It doesn't yet affect engine
   semantics. Will become a real driver once PR-B wires `per_class_position_caps`
   into `risk.py` / `engine.py`. The drift-detection sentinel validates the
   dicts are intact and sane before that lands.

4. **No regression risk.** 41 of the 49 unaffected tests were unchanged; only
   `CONS`/`AGG`-driven magic-number substitution in the 8 quarantined tests +
   1 new sentinel test added.

## Related (NOT in this PR)

These are separate Clusters queued for follow-up PRs (per the cluster plan from
the swarm-ci-failure-analysis):

- **Cluster A** (CRYPTO-LONG-block drift, 8 tests): reconcile
  `test_money_ready_verdict` + `test_m070_*` against M-036 / M-105 / M-070
  post-Eagle2 calibration.
- **Cluster C–H** (other 25 quarantined = 41 — 8 (A) — 8 (B) = 25): category
  inference, ETF P1 tight, M-096 CTF cap, PEAD surprise-scaling, M-044
  forex-hard-disable, plus 7 single-test miscellaneous queues.

These will be tackled as separate PRs (each ~80-150 LOC, single-cluster
scope, no regression risk).
