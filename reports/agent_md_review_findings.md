# Agent MD Review Findings — High-Confidence Claims Audit
**Review Date:** 2026-06-05  
**Agent:** Agent-MD-REVIEWER  
**Scope:** Root + research/, docs/, reports/ directories (last 30 days priority)

---

## Executive Summary

Scanned 265+ keyword matches across 100+ .MD files. Identified **systematic overstatement** of "trustworthy", "proven", "institutional-grade", and "validated" claims — especially for non-crypto asset classes. The audit dashboard data (cross-referenced via session-ses_1a2f.md and related reports) shows **contradictory evidence**: most non-crypto classes have **catastrophic validated performance** (WR 6.8%–33.3%) despite marketing language suggesting otherwise.

---

## 1. High-Confidence Asset Class / Strategy Claims Identified

### 1.1 COMMODITY — COT Positioning Family (Strongest Claim)
**Files:** `session-ses_1a2f.md` (lines 2290, 3536), `QUANT_EDGE_ANALYSIS_PER_ASSET_CLASS.md`

- **Claim:** "This is the single most statistically validated edge on the system."
- **Metrics cited:**
  - n=104 closed picks, WR 86.5%, Sharpe +1.377, **DSR=1.0000**
  - Independent confirmation: `cot_positioning_CT_locked` LONG = 89.8% WR, PF 13.1, n=49
- **Trust Tier:** PROVEN (elite edge)
- **Contradiction:** Later audit notes (line 4382) reveal **PF inflated by COT-dedup artifact**; after guard, recent PF drops to ~1.09. 4-week paper-pilot shadow status — **not yet real-money ready**.

### 1.2 CRYPTO — ML-Enhanced Sleeves (Multiple Strong Claims)
**Files:** `session-ses_1a2f.md` (lines 2291, 3537), `QUANTUM_FUSION_SUPERIORITY_REPORT.md`

- **Claimed strategies (all DSR ≥ 0.9995):**
  - `ml_enhanced_INJUSDT_1d_B_lightgbm` — n=27, WR 100%, Sharpe +2.49
  - `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` — n=31, WR 96.8%
  - `ml_enhanced_FETUSDT_1d_B_lightgbm` — n=25, WR 100%
  - `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` — n=34, WR 85.3%
- **Asset Class Edge:** ML-Enhanced (crypto) = 55.1% WR, PF 1.77 (vs Quan Engine 29.0% WR, PF 0.38)
- **Validation:** Forward-tested, DSR-tested, multi-pair validated (6 major pairs per QUANTUM report)
- **Status:** **Only crypto sleeves meet PF > 1.5 bar with decent n** (per line 4383).

### 1.3 "Institutional-Grade" Algorithm Suites (Broad Claims)
**Files:** `alternative_data_algorithms.md`, `100_ALGORITHMS_MASTER_CATALOG.md`, `25_Technical_Algorithms.md`

- **Claim:** "25 institutional-grade algorithms", "100 institutional-grade trading algorithms"
- **Evidence cited:** 13F filings, ETF flows, order-book imbalance, on-chain metrics
- **Validation level:** Mostly theoretical/backtest-only; few forward-tested cohorts mentioned
- **Contradiction:** No closed-pick validation numbers provided for non-crypto implementations.

### 1.4 "Proven Strategies" Directory / VWAP Scalper Pro
**Files:** `BTC_SCALPING_INTEGRATION_SUMMARY.md`, `proven_strategies/` references

- **Claim:** "Production-ready VWAP strategy with full audit logging"
- **Evidence:** 37k+ lines in `proven_strategies/proven_strategies.py`
- **Validation:** Backtested; no forward WR or DSR numbers cited in the summary.

---

## 2. Evidence / Validation Metrics Extracted

| Asset Class / Strategy | Claimed Validation | Actual Evidence Found | Trust Tier | Notes |
|------------------------|--------------------|-----------------------|------------|-------|
| Commodity (COT) | DSR=1.0, WR 86.5%, n=104 | PF inflated; paper-pilot only | PROVEN (marketing) → WATCH (audit) | Dedup artifact discovered post-claim |
| Crypto ML sleeves | DSR≥0.9995, WR 85–100%, n=25–34 | Forward + DSR tested | PROVEN | Only class meeting real-money thresholds |
| Forex | "Institutional participation" language | True validated WR = 33.3% (n=18) | PROBATION | Sample too small; PF 0.85 |
| Equity / Non-crypto | "Institutional-grade" suites | Validated WR 6.8% combined | PROBATION | 1,541+ picks untracked |
| General "institutional" algos | 25/100 "institutional-grade" | Mostly backtest/theoretical | — | No forward n cited |

---

## 3. Contradictions with Audit Dashboard State

### 3.1 Non-Crypto Catastrophic Performance (Explicitly Documented)
**Source:** `NONCRYPTO_PF_TRUST_INVESTIGATION_openclaw-mimo_2026-04-17T1239CST.md` (lines 24, 229, 234)

> "After investigating the full audit trail... **the profit factors are almost certainly inflated or fabricated**... The actual validated performance of non-crypto asset classes is catastrophic."
>
> "Non-crypto validated WR is 6.8% — far below the <50% stated, and worse than coin-flipping."
>
> "The reported profit factors for non-crypto asset classes are **not trustworthy**."

### 3.2 "High Conviction" Tier Over-Promised
**Source:** `session-ses_1a2f.md` (lines 2283, 3529, 4393)

- **Marketing claim:** High Conviction = "strictest preset... forward-validated tier... passes every single gate."
- **Audit reality:** "Putting real money into **any** current pick (Smart Picks, High Conviction, or raw active picks) would **not be profitable** based on the validated edge set; the system is still in remediation/rehab mode for most classes."

### 3.3 "Money-Ready" Verdict Remains 0/9
**Source:** `research/SESSION_ACHIEVEMENTS_2026-06-01.md` (line 3)

> "0/9 money-ready baseline (audit_dashboard/data/money_ready_verdict.json 2026-05-24) unchanged."

Despite repeated "PROVEN", "institutional", and "validated" language across dozens of .MD files, **zero asset classes** have cleared the money-ready gate as of the latest session.

---

## 4. Recommendations

1. **Strip "PROVEN" / "institutional-grade" labels** from all non-crypto references until forward n≥100 + DSR>0.95 + live Sharpe>0.5 are demonstrated.
2. **Add provenance tags** to every claim (e.g., "backtest only", "paper-pilot", "forward n=XX").
3. **Update High Conviction tooltip** to reflect the audit finding that no current HC pick is profitable in validated data.
4. **Archive or heavily caveat** `alternative_data_algorithms.md` and `100_ALGORITHMS_MASTER_CATALOG.md` — they read as marketing collateral rather than validated research.

---

**End of Report**  
*Generated by Agent-MD-REVIEWER per task specification.*