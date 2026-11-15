# 05_PROOF_STANDARD — 10-Gate Money-Ready Protocol

**Date:** 2026-11-15T07:44Z UTC  
**Purpose:** Define the mandatory proof standard that every strategy must pass before any capital deployment.

---

## The 10 Gates (Must Pass ALL)

| Gate | Requirement | Threshold | Purpose |
|------|-------------|-----------|---------|
| G1 | Temporal discipline | Strict chronological train/test split; features computed only from past data; rolling recalibration | Prevent look-ahead bias |
| G2 | Walk-forward optimization with embedded OOS windows | Report walk-forward efficiency; parameter-stability heatmaps | Detect regime dependence |
| G3 | Multiple-testing correction | State total configurations tried project-wide; report DSR and/or White's Reality Check p-value; apply Bonferroni/Holm where needed | Detect data snooping |
| G4 | Monte Carlo resampling | Block-bootstrap trade sequences; report distribution of net returns, % of paths positive after costs, 5th-percentile worst case | Detect statistical significance |
| G5 | Full friction model | Spread, commission, slippage, funding/borrow costs; state breakeven cost level and margin of safety | Detect cost-dominated edges |
| G6 | Statistical significance | Bootstrap CI for mean excess return excluding zero; t-stat on mean daily/weekly return; report p-values | Detect statistical significance |
| G7 | Regime robustness | Split history into bull/bear/sideways and high/low volatility; require positive expectancy in majority of regimes | Detect regime dependence |
| G8 | Control experiment | Same pipeline on permuted/shuffled price series must NOT produce similar performance | Detect look-ahead bias / bugs |
| G9 | Pre-registered forward test | Defined paper-trading protocol (duration, rules, live tracking URL, decision thresholds) | Validate forward performance |
| G10 | Reproducibility | Fixed random seeds, versioned data, exact formulas documented, runnable code | Ensure reproducibility |

---

## Why Each Gate Matters

| Gate | What It Catches | Example from This Audit |
|------|-----------------|-------------------------|
| G1 | Look-ahead bias | EXPIRED→WON mislabeling (78.93% vs 39.38%) |
| G2 | Regime dependence | EQUITY strategy works in bull market but not bear |
| G3 | Data snooping | 27+ parameter combos tested without correction → false positives |
| G4 | Small sample false positives | n=10 equity picks showing 90% WR |
| G5 | Cost dominance | ETF 267% of average PnL is cost; Commodity 422% |
| G6 | Statistical significance | n=738 equity picks but median excess vs SPY is -0.57% |
| G7 | Regime dependence | CRYPCO works in bull market but crashes in bear |
| G8 | Look-ahead bias / bugs | 134 ETF TIME_EXIT with forced pnl_pct=0; 851 active picks with no current_price |
| G9 | Forward validation | Zero forward closes for any crypto strategy |
| G10 | Reproducibility | No runnable backtest code with fixed seeds |

---

## Application to This Repository

| Asset Class | G1 | G2 | G3 | G4 | G5 | G6 | G7 | G8 | G9 | G10 | Overall |
|-------------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|---------|
| EQUITY | PASS | FAIL | FAIL | FAIL | PASS (3.23×) | FAIL (median -0.57%) | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| CRYPTO | FAIL | FAIL | FAIL | FAIL | FAIL (0.6054) | FAIL (-5.86%) | FAIL | FAIL | FAIL (0 forward closes) | FAIL | **FAIL** |
| ETF | FAIL | FAIL | FAIL | FAIL | FAIL (0.00) | FAIL (0.00) | FAIL | FAIL (resolver bug) | FAIL (0 resolved) | FAIL | **FAIL** |
| FOREX | FAIL | FAIL | FAIL | FAIL | FAIL (0.6596) | FAIL (32.19%) | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| FUTURES | FAIL | FAIL | FAIL | FAIL | FAIL (undefined) | FAIL (0.00%) | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| BOND | FAIL | FAIL | FAIL | FAIL | FAIL (0.000) | FAIL (0.00%) | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| COMMODITY | FAIL | FAIL | FAIL | FAIL | FAIL (undefined) | FAIL (0.00%) | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| Mutual Funds | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | **NOT REGISTERED** |
| PENNY_STOCK | FAIL | FAIL | FAIL | FAIL | FAIL (0.000-0.85) | FAIL (0-42%) | FAIL | FAIL | FAIL | FAIL | **FAIL** |

**0/9 asset classes pass all 10 gates.**

---

## Proof Standard Implementation

### Gate G1: Temporal Discipline

**Requirement:** All features must be computed using only past data. No look-ahead bias.

**Verification:**
- Check that no future data is used in signal generation
- Verify that entry signals use only information available at entry time
- Confirm that TP/SL levels are not based on future prices

**Repository Evidence:**
- `audit_trail/universal_pick_resolver.py` — resolves exits after entry
- `alpha_engine/sync_summary_picks_json.py` — aggregates pick timestamps
- No evidence of look-ahead bias in code, but data quality issues (EXPIRED→WON mislabeling) suggest potential issues

### Gate G2: Walk-Forward Optimization

**Requirement:** Embedded out-of-sample windows with walk-forward efficiency reporting.

**Repository Evidence:**
- NOT IMPLEMENTED. No walk-forward backtest with purged/embargoed windows found in codebase.
- BACKTEST_FIXES.md D-6: "Walk-Forward with Purged/Embargoed Windows" — NOT implemented

### Gate G3: Multiple-Testing Correction

**Requirement:** State total configurations tried project-wide; report DSR and/or White's Reality Check p-value; apply Bonferroni/Holm.

**Repository Evidence:**
- NOT IMPLEMENTED. No multiple-testing correction found in codebase.
- `final_v3/quant-audit-2026-11-14/03_backtest_simulation/BACKTEST_FIXES.md` D-3: "MIN_WINDOWS=4 not enforced, no multiple-testing correction"

### Gate G4: Monte Carlo Resampling

**Requirement:** Block-bootstrap trade sequences; report distribution of net returns, % of paths positive after costs, 5th-percentile worst case.

**Repository Evidence:**
- NOT IMPLEMENTED. No block-bootstrap Monte Carlo found in codebase.
- `final_v3/quant-audit-2026-11-14/03_backtest_simulation/BACKTEST_FIXES.md` D-7: "Block-Bootstrap CI on Net Expectancy" — not implemented

### Gate G5: Full Friction Model

**Requirement:** Spread, commission, slippage, funding/borrow costs; state breakeven cost level and margin of safety.

**Repository Evidence:**
- PARTIALLY IMPLEMENTED. `alpha_engine/money_ready_verdict.py:SLIPPAGE_BPS` defines per-class slippage (EQUITY: 10 bps, FOREX: 8 bps). But not applied to individual strategies.

### Gate G6: Statistical Significance

**Requirement:** Bootstrap CI for mean excess return excluding zero; t-stat on mean daily/weekly return; report p-values.

**Repository Evidence:**
- NOT IMPLEMENTED. No bootstrap CI or t-stat computation found in codebase.
- `final_v3/quant-audit-2026-11-14/03_backtest_simulation/BACKTEST_FIXES.md` D-7: "Block-Bootstrap CI on Net Expectancy" — not implemented

### Gate G7: Regime Robustness

**Requirement:** Split history into bull/bear/sideways and high/low volatility; require positive expectancy in majority of regimes.

**Repository Evidence:**
- NOT IMPLEMENTED. No regime-split analysis found in codebase.

### Gate G8: Control Experiment

**Requirement:** Same pipeline on permuted/shuffled price series must NOT produce similar performance.

**Repository Evidence:**
- NOT IMPLEMENTED. No shuffle control found in codebase.

### Gate G9: Pre-Registered Forward Test

**Requirement:** Defined paper-trading protocol (duration, rules, live tracking URL, decision thresholds).

**Repository Evidence:**
- NOT IMPLEMENTED. No forward-test protocol found in codebase.
- `forward-tracker.py` exists but is not connected to live pick emission.

### Gate G10: Reproducibility

**Requirement:** Fixed random seeds, versioned data, exact formulas documented, runnable code.

**Repository Evidence:**
- PARTIALLY IMPLEMENTED. Code is versioned in Git, but no fixed seeds or documented formulas found for strategies.

---

## Conclusion

**No strategy in this repository passes all 10 proof gates.** The most common failures are:
1. **G3 (Multiple-testing correction):** Not implemented anywhere
2. **G4 (Monte Carlo):** Not implemented anywhere
3. **G6 (Statistical significance):** Not implemented anywhere
4. **G7 (Regime robustness):** Not implemented anywhere
5. **G8 (Shuffle control):** Not implemented anywhere
6. **G9 (Forward test):** Not implemented anywhere

The proof standard is designed to prevent false positives. Given that no strategy passes even the basic gates, the repository should not deploy any active prediction strategy to real money.
