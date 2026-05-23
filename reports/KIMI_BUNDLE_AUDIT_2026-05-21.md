# Kimi Research Bundle — Independent Audit

**Date:** 2026-05-21
**Bundle:** `tools/kimi_research_2026_05_20/` (18,091 lines across ~30 files)
**Source:** Kimi Agent parallel fleet deployment (8 subagents)
**Auditor:** Codebuff Buffy + Cursor Agent second opinion

---

## Executive Summary

The Kimi bundle is a **simulator-aligned research prototype** — not production-ready trading infrastructure. Its headline claim ("ALL 6 GATES PASSED") is misleading because the validation is circular: the synthetic data generator bakes in the exact signals the strategy trades. However, the bundle contains **1 genuinely useful module** (`statistical_validation_framework.py`) and several **valuable design patterns** worth porting.

**Verdict:** Do NOT deploy `six_gate_validated_strategy.py` to /audit. Do NOT size real capital from this report. Extract `statistical_validation_framework.py` as a shared validation layer. Archive the asset-class harnesses as reference designs.

---

## Per-Gate Honest Scorecard

### Gate 1: Bootstrapped Sharpe — ✅ PASS (on sim data only)
- **Kimi claim:** Sharpe = 2.516, CI [1.918, 3.162], PASS
- **Real interpretation:** Meaningful in-sample on the synthetic data. Valid bootstrap with 10K resamples. The value is inflated because the data has embedded signals the strategy is designed to harvest.
- **Mitigation:** Must be re-run on real audit picks with resolver PnL.

### Gate 2: t-test — ✅ PASS (on sim data only)
- **Kimi claim:** p < 0.000001, PASS
- **Real interpretation:** Same caveat — significant mean return on synthetic data. Trivially passes when the data generator encodes momentum + carry.
- **Mitigation:** Re-run on real returns.

### Gate 3: Max Drawdown — ✅ PASS
- **Kimi claim:** 0.24% max DD, PASS
- **Real interpretation:** Easy on a low-volatility synthetic equity curve. The simulated daily vol is 0.027% — unrealistically low for any real asset class.
- **Mitigation:** Re-run with real-market volatility (typically 1-3% daily for equities, 3-8% for crypto).

### Gate 4: Walk-Forward — ⚠️ PASS (broken implementation)
- **Kimi claim:** 4/5 folds passed (80% > 60% threshold), PASS
- **Real issues:**
  - **Fold 0 is dead:** `n_days: 0, sharpe: -999` because `test_start < train_start` when `test_start == usable_start` with 7-day embargo
  - **Weak bar:** Threshold is Sharpe > 0, not Sharpe > 1.0 or OOS degradation vs IS
  - **No fit step:** Uses `MultiFactorStrategy()` default params on every fold — no training/fitting on train windows
  - Pass rate would still be 4/5 = 80% even counting fold 0 as fail
- **Mitigation:** Fix fold indexing. Require OOS Sharpe > 1.0. Add optional parameter fit on train.

### Gate 5: Monte Carlo Stress — ❌ NOT VALID (implementation bug)
- **Kimi claim:** 5th pctile = 2.516, PASS
- **Real interpretation:** **BROKEN.** Block-shuffling returns preserves mean AND standard deviation. Sharpe = mean/std * sqrt(252). Since mean and std are invariant under reordering, all percentiles are identical to the observed Sharpe (2.5161). This is mathematically tautological — the gate cannot fail by design.
  ```
  validation_report.json:
  "mc_sharpe_5th": 2.5161,
  "mc_sharpe_median": 2.5161,
  "mc_sharpe_95th": 2.5161
  ```
- **Mitigation:** Use bootstrap resampling (with replacement) or parametric paths (Gaussian with observed mu/sigma). The project's own `statistical_validation_framework.py` `MonteCarloStressTester` already supports bootstrap/parametric/regime_shift/crash scenarios — use that instead.
- **Severity:** HIGH — this is the most critical bug. A gate that always passes provides zero information.

### Gate 6: BH-FDR — ⚠️ Conditional PASS (directionally right, implementation sloppy)
- **Kimi claim:** q = 0.001378, rank #1/1001, PASS
- **Kimi's fix (correct idea):** Replace permuted returns null with pure-noise synthetic data (momentum_strength=0, mean_reversion_strength=0, carry_strength=0). This properly centers the null near zero.
- **Real issues:**
  - **kwargs bug:** Category-2 noise strategies pass wrong constructor args (`mean_reversion_zscore_threshold` instead of `mr_zscore_threshold`). They raise TypeError, get caught, and append 0.0 Sharpe — artificially depressing the null.
  - **400 runs are the same strategy on different noise seeds** — not 400 independent hypotheses. BH-FDR assumes independent tests.
  - Normal tail approximation from noise mean/std, not per-strategy empirical p-values.
- **Mitigation:** Fix kwargs. Generate genuinely different null strategies. Use empirical p-values. Report per-strategy q-values.

### Overall Effective Score

| Gate | Kimi Status | Real Status |
|------|------------|-------------|
| 1 Bootstrap Sharpe | PASS | Meaningful on sim data only |
| 2 t-test | PASS | Meaningful on sim data only |
| 3 Max DD | PASS | Unrealistically low vol |
| 4 Walk-Forward | PASS (80%) | Broken fold 0; weak bar |
| 5 Monte Carlo | PASS | **Invalid — implementation bug** |
| 6 BH-FDR | PASS (q=0.0014) | Fix idea OK; stats sloppy |

**Effective score: ~3/6 on synthetic data, 0/6 on live audit history.**

---

## Bundle Contents: Keep vs Archive

### ✅ KEEP — `statistical_validation_framework.py`
- **1,119 lines.** Well-structured shared validation library.
- Contains: `StrategyBacktest`, `BootstrapValidator`, `MultipleTestingCorrector` (BH-FDR + Bonferroni + Storey adaptive FDR), `WalkForwardValidator`, `MonteCarloStressTester` (bootstrap/parametric/regime_shift/crash), `EnsembleConstructor` (risk-parity + correlation clustering), `UnifiedValidator`.
- Uses `scipy.stats`, `sklearn.covariance.LedoitWolf`, `scipy.cluster.hierarchy`.
- **Immediate candidate** for porting to `alpha_engine/statistical_validation_framework.py` (rename to avoid collisions with the existing `alpha_engine/walkforward_validator.py`).
- **Already partially redundant** with `alpha_engine/walkforward_validator.py` — but this one is more comprehensive and shared across asset classes.

### ⬜ ARCHIVE — Asset-class harnesses
- `crypto_strategy_harness.py` (2,094 lines)
- `equity_strategy_harness.py` (1,883 lines)
- `etf_strategy_harness.py` (1,073 lines)
- `penny_stock_strategy_harness.py` (1,869 lines)
- `forex_strategy_harness.py` (referenced in plan, not in bundle)
- `commodity_strategy_harness.py` (referenced in plan, not in bundle)
- `bond_strategy_harness.py` (referenced in plan, not in bundle)

**Value:** Reference designs for multi-strategy generation per asset class. The strategy enumeration logic (200+ crypto strategies, 1,094 forex strategies, etc.) is useful as a brainstorming reference.
**Problem:** Not wired to any real data source. No DB connections, no price feed integration. All trade recommendations use synthetic symbols (`ASSET_00`, `ASSET_01`...) with many `stop_loss: null`.
**Action:** Archive in `references/kimi_harnesses/` if future reference is needed. Do not deploy.

### ⬜ ARCHIVE — `six_gate_validated_strategy.py`
- **1,870 lines.** The main validation script.
- **Do NOT deploy.** The circular synthetic data + broken Gate 5 mean its "6/6 PASS" verdict is not trustworthy.
- **Valuable patterns:** Factor classes (CrossSectionalMomentum, MeanReversionFactor, CarryFactor, TrendFilter, CorrelationRiskControl, PositionSizer) are well-designed and could be ported individually to real strategy implementations.
- **Action:** Archive with a README noting the caveats. Extract factor classes only if/when building real strategy variants.

### ⬜ ARCHIVE — Reports and JSON blobs
- `validation_report.json` — Useful as a record of what the bundle produced.
- `penny_stock_audit_payload.json`, `etf_alpha_pipeline.json` — Large JSON blobs, not audited.
- All 14 `.md` report files — Marketing narrative, not reliable as evidence.
- `copy_trader_engine_v2.py`, `prediction_market_signals.py`, `outcome_resolver_v2.py`, `db_integrity_harness.py`, `edge_stability_harness.py` — Standalone scripts, not integrated, not audited.
- `ml_engine_v2.py` — 1,870 lines, not audited.

---

## Recommendations

### Short-term (this session)
1. **Port `statistical_validation_framework.py`** to `alpha_engine/` — this is the highest-value piece of the entire bundle. It provides a proper shared validation layer that all asset-class pipelines can use.
2. **Archive the rest** in `references/kimi_2026_05_20/` with a caveat README.

### Medium-term
3. **Fix the existing `alpha_engine/walkforward_validator.py`** to match the statistical rigour of the Kimi framework (bootstrapped CIs, FDR correction, multiple MC scenarios).
4. **Run `statistical_validation_framework.py` on real resolver output** — feed it daily returns from resolved picks in `ejaguiar1_stocks` and `ejaguiar1_backtests` for one asset class (EQUITY) to get a genuine validation.

### Long-term
5. **Hypothesis registry (M-107):** Any strategy promoted to production still needs pre-registration + harness on historical audit picks, not sim-only PASS.

---

## References

- Bundle: `tools/kimi_research_2026_05_20/`
- Existing validation: `alpha_engine/walkforward_validator.py`
- Existing scoring: `alpha_engine/score_booster.py`, `alpha_engine/hyrotrader_enhanced_scoring.py`
- Existing gate: `alpha_engine/forward_validator.py`
- Hypothesis registry: `reports/hypothesis_registry.json`
