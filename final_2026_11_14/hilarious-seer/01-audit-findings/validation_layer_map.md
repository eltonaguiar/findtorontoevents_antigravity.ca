# Validation / Measurement Layer Map — Proving Trading Edge

**Date:** 2026-11-14
**Worktree:** hilarious-seer
**Agent:** ML algorithms audit asset classes stale data fixes

---

## Executive Summary

The repo contains **world-class statistical machinery that is largely NOT wired into the production edge-proof path**, and the **production path itself is the weak link**. The single most rigorous artifact — `benchmark_closed_ledger.py` (Task 10) — has already been run and its output shows **only 4 of 67 full-proof ledgers pass the paired-bootstrap-vs-benchmark gate, and only 9 of 67 land in the top decile of the random-entry Monte-Carlo timing test**. Prior audits independently conclude: **no asset class shows a proven, leakage-free edge**. The gap to "z>1.96 with PF>1.5 post-costs" is therefore mostly a **data-quality + wiring gap, not a missing-formula gap**.

---

## 1. `audit_trail/universal_pick_resolver.py` (1614 lines) — Rigor: BASIC

**What it does:** Resolves TP/SL/time exits for ~90 pick sources. Fetches live prices via 4-API crypto failover chain + yfinance for non-crypto. Prefetches intrabar OHLC (Binance klines 48x1h for crypto, yfinance 5dx1h for non-crypto).

**How it decides TP/SL-first:**
- `_check_tp_sl_intrabar` (L618) replays bars chronologically with **SL-first conservative ordering**
- When both hit in the same bar it sets `pick["_intrabar_ambiguous"] = True` but **still returns SL_HIT**
- **Inconsistency:** `tools/hyro_pick_performance_validator.py` does the **opposite** — TP-first

**Known bugs / honesty patches (all present in-code):**
- Intrabar ambiguity — flagged but conservatively resolved to SL
- `close_approx` path (Bug 1B) — single-snapshot price check, NOT intrabar first-touch
- Entry-anchored window (Bug 1A) — gated `RESOLVER_ENTRY_ANCHORED` (default ON)
- Bad-geometry guard (Bug 1C) — LONG needs `sl<entry<tp`, SHORT needs `tp<entry<sl`
- Frozen-exit stamping — fixed by `_per_pick_price` (2026-10-22)
- Fabricated flat-0% closes — `_priceless_close` and `_heal_no_price_row` convert no-live-price TIME_EXIT rows to `pnl_pct=None`
- EXPIRED/WON mislabels — unknown `exit_reason` defaults to `EXPIRED`/`TIME_EXPIRED`
- **254d stale** — mechanism: intrabar window bounded (48x1h crypto ≈ 2 days), picks older than window degrade to `close_approx`/`None`

---

## 2. `forward_validator.py` + `walkforward_validator.py` — Rigor: BASIC / BASIC

**`forward_validator.py`:**
- Computes: WR, avg/total PnL, Sharpe (annualized x√252), Sortino, max DD, profit factor, Kelly, avg win/loss
- `p_value` via `binomial_p_value` (one-sided binomial vs 0.5, normal-approx erfc)
- `statistically_significant = p_value < 0.05 AND n >= 20`
- Forward gate: `FORWARD_GATE_MIN_TRADES = 50` (crypto), overrides BOND 10 / EQUITY 20 / ETF 15
- Costs: TP slippage 0.05%, SL slippage 0.10%, 0.3% SL buffer
- Multiple-testing: `run_white_reality_check` with `MonteCarloSimulator.whites_reality_check` (needs ≥10 trades/strategy); DSR computed in `run_generation` (needs ≥20 trades)
- **No Bonferroni here** — relies on WRC + DSR

**`walkforward_validator.py`:**
- Rolling-window WF (train 20/test 10/step 5), per-class WF (CRYPTO 500/200/100/50 … BOND 5/3/2/1)
- Metrics: WR, PF, Sharpe, max DD, `ttest_pvalue` (two-sided t-test, normal approx), `bootstrap_sharpe_ci` (5000 resamples, seed 42)
- Mercury-2 `perf_score`/`proof_score`/`final_score`; verdict ELITE≥0.70 … FAILING
- **Gaps:** t-test uses normal approximation; Sharpe annualization assumes 1 trade/day; **no multiple-testing correction** in proof_score; PnL is raw `pnl_pct` (no cost drag)

---

## 3. `alpha_engine/benchmark_closed_ledger.py` (585 lines) — Rigor: RIGOROUS

Per `(strategy, asset_class)` ledger computes:
1. Trade-level: n, WR (hidden below n=20), **Wilson 95% CI**, **profit factor**, **compound return**
2. Same-window benchmark: benchmark bought at entry date, sold at exit date
3. **Paired bootstrap** (10,000 seeded resamples): CI + `frac_positive`; `pass_95 = frac_positive >= 0.95`
4. **Random-entry Monte-Carlo timing** (same-asset, direction-aware, window-matched nulls): `percentile ~1.0` = timing edge, `~0.5` = coin flip

**Last-known result** (`reports/benchmark_ledger_proof_2026-10-19.json`): **n_ledgers=170, n_full_proof=67, n_pass_95=4, n_mc_top_decile=9.** Largest ledger `luxalgo_confluence` CRYPTO: n=1211, WR 41.9%, PF 1.03, cum_return −26.4%, `pass_95=false` (frac_positive 0.521), MC percentile 0.568 (coin flip). **No ledger clears PF>1.5 post-costs with timing significance.**

---

## 4. Monte-Carlo Null / Permutation / Same-Asset Random-Entry Machinery (Repo-Wide)

| Module | What | Rigor |
|---|---|---|
| `benchmark_closed_ledger.py::random_entry_mc` | Same-asset, direction-aware, window-matched random-entry timing null | **RIGOROUS** |
| `alpha_engine/validation/monte_carlo.py::MonteCarloSimulator` | bootstrap_returns, block_bootstrap, stationary_block_bootstrap, whites_reality_check, probability_of_ruin | **RIGOROUS** |
| `alpha_engine/validation/statistical_gates.py` | BH-FDR, DSR, Newey-West HAC t-stat, power analysis | **RIGOROUS** |
| `alpha_engine/admissibility_pipeline.py` | 10-step pipeline: purged+embargoed WF, cost model, DSR/PBO/SPA, block bootstrap, regime robustness | **RIGOROUS** |
| `audit_trail/hf_statistical_rigor.py` | Harvey-Liu (2015) multiple-testing + DSR + BH-FDR | **RIGOROUS** |
| `tools/pf_ci_lower.py` | **Cluster-bootstrap 95% CI lower bound of net PF** + `effective_n` | **RIGOROUS** |

**Documented gaps (not built):**
- Bootstrap Sharpe (10k permutations) — HIGH-LEVERAGE GAP (`groksstuff.txt:10314`)
- Bootstrap Sharpe permutation test (P0) (`groksstuff.txt:10337`)
- MC shuffled-return Sharpe "partial" (`groksstuff.txt:10317`)
- `.claude/PEER_INTEL.md:227` warns MC p-values were once meaningless due to a sign-flip bug (since fixed)
- `eagle_gates.py:199` lists "Bootstrap CI PF" as a **v3 planned** gate (still not wired)

---

## 5. The Four `tools/` Validators — What They Check + Last-Known Results

| Tool | Checks | Rigor | Last-known output |
|---|---|---|---|
| `hyro_pick_performance_validator.py` | Replays hyro signals vs Binance 1h klines; per-strategy strength_score; PF. **TP-first ordering (inconsistent with resolver).** | BASIC | `hyro_pick_performance.json` generated **2026-11-08** (STALE) |
| `non_crypto_pick_audit.py` | Counts active picks per category | NONE | `non_crypto_pick_audit.json` generated **2026-11-14** (fresh) |
| `db_freshness_check.py` | RED/YELLOW/GREEN staleness | NONE | `db_freshness.json` **overall=RED**, generated **2026-05-23** (itself ~6mo stale) |
| `cross_db_consistency.py` | Diffs strategy keys between MySQL tables | NONE | `cross_db_audit.json` **MISSING** |

---

## 6. Statistical Gates — What EXISTS vs MISSING

**EXISTS (grep-confirmed):**
- Wilson CI / lower bound, z=1.96, binomial p-value, t-test / Newey-West
- Multiple-testing corrections: Bonferroni-family, BH-FDR, DSR, PBO, White's Reality Check, MinTRL, power analysis
- Bootstrap: paired, Sharpe CI, block/stationary, cluster net-PF CI
- Profit factor everywhere; net-PF CI lower bound bar = >1.15 at n≥80

**MISSING (gaps to "z>1.96 AND PF>1.5 post-costs"):**
1. **No single combined gate** that requires z>1.96 on WR/mean-return AND PF>1.5 net-of-cost simultaneously per ledger. Existing bars are fragmented.
2. **Bootstrap CI on PF is "planned" not wired** (`eagle_gates.py:199` v3); `pf_ci_lower.py` is not called by the main edge-proof path.
3. **`benchmark_closed_ledger.py` applies no cross-ledger multiple-testing correction** — 170 ledgers tested, no Bonferroni/BH on the 4 `pass_95` survivors.
4. **The rigorous modules are not the production gate.** `forward_validator`/`walkforward_validator` (daily path) use raw binomial/t-test with no MT correction; the rigorous `admissibility_pipeline`/`statistical_gates`/`benchmark_closed_ledger` run as separate/occasional jobs.
5. **Intrabar first-touch ambiguity unresolved** (SL-first in resolver, TP-first in hyro validator); `close_approx` rows not excluded from WR/PF in the main path.
6. **Cost drag inconsistent** — slippage in `forward_validator` fills, `pf_ci_lower` expects pre-net pnls, `benchmark_closed_ledger` MC nulls are frictionless (conservative) but realized returns' cost basis varies by source.

---

## 7. Tests — Validation-Related Files + How to Run

**Runner:** pytest. `pytest.ini` → `pythonpath=.`, `testpaths=tests`, markers `slow`/`integration`/`network`.

```bash
python3 -m pytest tests/test_benchmark_closed_ledger.py -q          # 33 deterministic tests
python3 -m pytest tests/test_statistical_rigor.py tests/test_multiple_testing_correction.py -q
python3 -m pytest tests/test_deflated_sharpe_ratio.py tests/test_data_integrity_wilson.py -q
python3 -m pytest tests/test_universal_pick_resolver.py tests/test_resolver_intrabar_accuracy.py tests/test_resolver_frozen_exit_fix.py -q
python3 -m pytest tests/test_walkforward_by_class.py tests/test_walkforward_gate.py tests/test_anti_overfit_validator.py -q
python3 -m pytest tests/test_hf_validation_stats.py tests/test_validation_gate.py tests/test_forward_edge_audit.py -q
```

Key files: `test_benchmark_closed_ledger.py`, `test_statistical_rigor.py`, `test_multiple_testing_correction.py`, `test_deflated_sharpe_ratio.py`, `test_data_integrity_wilson.py`, `test_universal_pick_resolver.py`, `test_resolver_intrabar_accuracy.py`, `test_resolver_frozen_exit_fix.py`, `test_walkforward_by_class.py`, `test_walkforward_gate.py`, `test_anti_overfit_validator.py`, `test_hf_validation_stats.py`, `test_validation_gate.py`, `test_forward_edge_audit.py`, `test_forward_validator_aggregation_collision.py`, `test_sharpe_lower_bound.py`, `test_rolling_sharpe_drawdown.py`, `test_edge_stability_harness_regime.py`.

---

## 8. `reports/` — Prior Validation Outputs & Conclusions

- **`benchmark_ledger_proof_2026-10-19.json`** (Task-10 run): 4/67 `pass_95`, 9/67 MC top-decile; top ledger coin-flip (PF 1.03, −26% cum, −72pp vs BTC). **Verdict: no proven timing edge.**
- **`AUDIT_STAT_VALIDATION_2026-05-22.md`**: "impressive numbers are not real returns… No asset class shows a proven, leakage-free statistical edge."
- **`2026-06-06-money-ready-screen-clean-cohort.md`**: bar n≥50/≥3mo/PF>1.5/WR>52%; only survivor `luxalgo_confluence` (n=73, WR 63%, PF 5.35) = 3.6% of its n=2040 history and **not intrabar-validated**. "No confirmed mutual-fund-worthy edge in any asset class today."

---

## Consolidated GAP LIST to Prove Edge at z>1.96 with PF>1.5 Post-Costs

**Must BUILD (code):**
1. A single **unified edge-proof gate** per `(strategy, asset_class)` ledger that requires simultaneously: (a) WR/mean-return **z>1.96**, (b) **net-of-cost PF>1.5** with bootstrap/cluster CI lower bound >1.5, (c) **paired-bootstrap `pass_95`**, (d) **random-entry MC percentile ≥0.90**, (e) **cross-ledger BH-FDR/Bonferroni**, (f) n≥threshold (≥80–100) and ≥3 months.
2. **Wire the rigorous modules into the daily path** — currently `forward_validator`/`walkforward_validator` (production) lack MT correction and net-cost PF.
3. **Resolve intrabar first-touch ambiguity** and **unify resolver vs hyro TP/SL ordering**; exclude `close_approx`/ambiguous rows from WR/PF.
4. **Implement the "Bootstrap CI PF" v3 gate** in `eagle_gates.py` and enforce PF>1.5 for real-money promotion.

**Must FIX (data quality — the true blocker):**
5. Deepen `crypto_ohlcv`/add `stock_ohlcv` so intrabar re-resolution covers full history (currently 1,422/3,000 out-of-window); run `reresolve_intrabar.py --apply`.
6. Quarantine artifacts (backfill 68–100%, 36k ghost rows, reverse-split/feed-bug rows) and fix the resolver **WON/LOST-vs-PnL sign** writer bug; refresh the stale `db_freshness` signal_outcomes lane.
7. Standardize **net-cost PnL** at the source so every consumer measures against the same cost basis.

**Bottom line:** the formulas for z>1.96 + PF>1.5 + bootstrap + permutation nulls **all exist and are well-tested**; what is missing is (a) one gate that ANDs them together with cross-ledger MT correction, (b) wiring them into the production edge-proof path, and (c) the data-quality cleanup without which every ledger is a coin-flip artifact.
