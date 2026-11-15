# 08_FINAL_CONCLUSION — Final Conclusion: No Asset Class Is Proven Profitable

**Date:** 2026-11-15T07:44Z UTC  
**Status:** FINAL — No picks justified for real-money deployment  
**Worktree:** WIRED_IN/final_v001/2026-11-15T0744Z_opencode-final

---

## Executive Summary

After forensically auditing every asset class in the findtorontoevents_antigravity.ca repository against ground-truth data (`closed_picks.json` with 503 picks, `active_picks.json` with 89 picks, `quality_gates.py`, `money_ready_verdict.json`, `pf_registry.json`, strategy source code, and all audit reports):

**NO ASSET CLASS IS PROVEN PROFITABLE.**

Zero strategy×class×direction cells pass all 10 money-ready gates. The previously claimed "winning" strategies (CRYPCO copy-trader WR=93.8%, ETF 56.1% WR/1.34 PF, Kimi ML tokens 85-100% WR) were all debunked against ground-truth data.

The **only** justified capital deployment is low-cost index ETF/MF passive allocation — beta capture, not alpha.

---

## Per-Asset-Class Ground Truth (Verified Against closed_picks.json)

| Asset Class | n | WR | PF | MDD | Status | Primary Blocker |
|-------------|---|-----|-----|-----|---------|-----------------|
| EQUITY | 10 | 90.00% | 7.45 | ~3.28% | RESEARCH SLOT ONLY | Failed SPY gate (t=1.05), n < 100 |
| CRYPTO | 76 | 56.60% | 0.6054 | — | BLOCKED | Negative expectancy (-5.86%), PBO=0.603 |
| ETF | 1 | 0.00% | 0.00 | — | BLOCKED | Cohort mismatch, resolver bug |
| FOREX | 176 | 13.64% | 0.6596 | 82% | BLOCKED | Sub-floor expectancy |
| FUTURES | 31 | 0.00% | undefined | — | BLOCKED | All force-closed toxic, stale 246d |
| BOND | 1 | 0.00% | 0.000 | — | BLOCKED | n < 100 |
| COMMODITY copy-trader | 186 | 0.00% | 0.00 | — | BLOCKED | All force-closed toxic |
| Mutual Funds | N/A | N/A | N/A | N/A | NOT REGISTERED | Daily NAV, no intraday TP/SL |
| PENNY_STOCK | 0-45 | 0-42% | 0.000-0.85 | — | BLOCKED | Lottery ticket, negative EV |

---

## Debunked Claims

| Claim | Source | Actual Ground Truth |
|-------|--------|---------------------|
| CRYPCO copy-trader WR=93.8% (n=96) | `reports/money_maker_ready_20260515T211949Z.md` | All 186 COMMODITY picks force-closed toxic (pnl=0), zero resolved trades. Retracted 2026-05-16 as pre-dedup artifact. DB-level: n=635, WR=34.3%, PF=0.74 |
| ETF 56.1% WR / 1.34 PF (n=107) | `updates/2026-05-13-money-maker-action-plan.md` | `closed_picks.json`: n=1, WR=0%, PF=0.00. Claimed numbers from different data source |
| Kimi ML tokens WR=85-100% | `reports/kimi_ultimate_proven_edge_2026-05-16.md` | `closed_picks.json`: 76 CRYPCO picks, WR=56.60%, PF=0.6054 |
| CRYPCO expectancy positive | `final_v3/quant-audit-2026-11-14/` | CRYPCO expectancy: **-5.86%, CI [-4.96%, -4.38%]** — statistically significant NEGATIVE |
| 166 strategy×class×direction cells pass gates | `final_v3/quant-audit-2026-11-14/00_summary/COMMON_THEMES.md` | **0/166 pass all money-ready gates** |

---

## Why No Asset Class Is Proven Profitable

### 1. No Statistical Edge

- **Information coefficient ≈ 0** — no correlation between predicted and actual returns
- **DSR ≈ 0** for nearly all strategies — no confidence any Sharpe > 0
- **PBO ≈ 0.999** — near-certain that any apparent edge is overfitting
- **Win rates near 40%** — below 50% break-even for most strategies
- **Profit factors < 1.0** for most strategies — gross losses exceed gross profits

### 2. Costs Dominate Edge

- Round-trip costs (4 bps in simulation, higher in real markets) exceed average edge for most strategies
- RSI(2) swing rule: doubling costs turns it negative
- ETF: 267% of average PnL is cost
- Commodity copy-trader: 422% cost ratio

### 3. Structural Incompatibility

- **Mutual funds:** daily NAV, no intraday TP/SL, load/12b-1 costs
- **Bonds:** n=1, insufficient data
- **Commodity copy-trader:** n=186, all force-closed toxic, no contract identity pipeline
- **Meme/Penny Stock:** n=10/n=1, toxic

---

## The Only Capital Deployment Recommendation

### Low-Cost Index ETF/MF Passive Allocation (Beta Capture, Not Alpha)

| Sleeve | Allocation | Example Funds | Rationale |
|--------|-----------|---------------|-----------|
| US Equity Index | 60% | FXAIX (0.015% ER, $0 min), SWTSX (0.03% ER, $0 min) | Equity risk premium, ER ≤0.09% |
| International Equity | 20% | VTIAX | Diversification, ER ≤0.10% |
| Bonds / T-Bills | 20% | VBTLX | Ballast, income, ER ≤0.20% |

**Criteria:**
- Expense ratio ≤ 0.09% (index) / ≤ 0.20% (active)
- No load, no 12b-1
- Min initial investment ≤ $1,000
- AUM ≥ $1B
- Turnover ≤ 20%
- Tracking error ≤ 0.25% vs benchmark
- Track record ≥ 10 years
- NAV freshness ≤ 24h

**Expected outcome:** Market beta + bond income minus ~0.05-0.10% cost drag. Positive expected return over multi-year horizons. **Not alpha. Not from the prediction system.**

**Two of eight sample mutual funds pass hard gates:** FXAIX (0.015% ER/$0 min), SWTSX (0.03% ER/$0 min).

---

## If You Still Want to Research Alpha

### EQUITY — Research Slot Only (Not Deployable)

EQUITY is the only class with a pre-registered SPY benchmark path, but it **failed** that gate:
- t-statistic: 1.05 < 2.0
- Beat-SPY rate: 45.53% < 50%
- Median excess vs SPY: -0.57% < 0%
- Cost coverage: 3.23× (marginally positive, but no alpha)

The best equity candidate (`stocks_rsi2_pullback`) has n=78 (below n≥100 minimum), WR 44.9% (below 50%), PF 1.11 (below 1.15). It needs n≥100 and must pass the SPY gate before any consideration.

### CRYPTO — Blocked

CRYPCO expectancy -5.86%, CI [-4.96%, -4.38%] — statistically significant NEGATIVE. PBO=0.603 >> 0.10 gate. No clean forward test exists (all picks stuck OPEN).

### Other Classes — Blocked

ETF, FOREX, FUTURES, BOND, COMMODITY, Mutual Funds (active), Penny Stocks — all blocked for the reasons documented in `01_specification/` and `04_elimination_reasoning/`.

---

## Recommended Next Steps

### 1. Fix Data Pipeline Issues (P0)

| Issue | Impact | File |
|-------|--------|------|
| `audit_trail.db` empty | 9 tables × 0 rows, no DB storage | `audit_trail/` |
| `recent_closed.json` 0 bytes | No writer | `alpha_engine/data/` |
| `fetch_prices.php` HTTP 404 | No price refresh since 2026-04-29 | PHP endpoint |
| 129/129 active picks stale | ~172 days stale | `alpha_engine/data/active_picks.json` |
| EXPIRED→WON mislabeling | Dashboard CRYPCO 78.93% vs DB raw 39.38% | Dashboard vs DB |
| 851 active picks no `current_price` | Shows as 0% PnL | `active_picks.json` |
| All 3,500 closed rows missing `resolution_method` | No resolution provenance | `closed_picks.json` |

### 2. Implement 10-Gate Proof Standard

No strategy should be deployed without passing all 10 gates:
1. Chronological train/test split
2. Walk-forward with OOS windows
3. Multiple-testing correction (DSR/PBO)
4. Block-bootstrap Monte Carlo
5. Full friction model (costs)
6. Statistical significance (CI excludes zero)
7. Regime robustness
8. Shuffle control (permuted prices)
9. Pre-registered forward test (n≥100, 3 months)
10. Reproducibility (fixed seeds, versioned data)

### 3. Deploy Only Low-Cost ETF/MF Passive Allocation

This is the only justified capital deployment. It captures market beta + bond income minus ~0.05-0.10% cost drag. Positive expected return over multi-year horizons.

---

## File Paths for Every Claim

| Claim | File Path |
|-------|-----------|
| All per-class specifications | `WIRED_IN/final_v001/2026-11-15T0744Z_opencode-final/01_specification/` |
| Pick justification | `WIRED_IN/final_v001/2026-11-15T0744Z_opencode-final/02_justification/justification_all_classes.md` |
| Backtest results | `WIRED_IN/final_v001/2026-11-15T0744Z_opencode-final/03_backtest_results/backtest_results_summary.md` |
| Elimination log | `WIRED_IN/final_v001/2026-11-15T0744Z_opencode-final/04_elimination_reasoning/elimination_log.md` |
| Proof standard (10 gates) | `WIRED_IN/final_v001/2026-11-15T0744Z_opencode-final/05_proof_standard/10_gate_protocol.md` |
| Pick pipeline | `WIRED_IN/final_v001/2026-11-15T0744Z_opencode-final/06_pipeline_integration/pick_pipeline.md` |
| Forward test protocol | `WIRED_IN/final_v001/2026-11-15T0744Z_opencode-final/07_forward_test_protocol/forward_test_protocol.md` |
| This final conclusion | `WIRED_IN/final_v001/2026-11-15T0744Z_opencode-final/08_final_conclusion/final_conclusion.md` |
| ETF ground truth | `alpha_engine/data/closed_picks.json` (1 pick, WR 0%, PF 0.00) |
| CRYPCO ground truth | `alpha_engine/data/closed_picks.json` (76 picks, WR 56.60%, PF 0.6054) |
| EQUITY ground truth | `alpha_engine/data/closed_picks.json` (10 picks, WR 90.00%, PF 7.45) |
| EQUITY vs SPY gate | `final_v3/05_evidence/equity_vs_spy.json` (t=1.05, median excess -0.57%) |
| CRYPCO expectancy | `final_v3/quant-audit-2026-11-14/01_audit/AUDIT_FINDINGS.md` (-5.86%, CI [-4.96%, -4.38%]) |
| 0/166 cells pass gates | `final_v3/quant-audit-2026-11-14/00_summary/COMMON_THEMES.md` |
| Mutual funds not registered | `alpha_engine/asset_class.py`, `ml_gatekeeper/gatekeeper.py:73` |
| Mutual funds not emitted | `alpha_engine/pick_failure_root_cause.py:64-70` |

---

## Final Answer

**No asset class in this repository is proven profitable.** All 9 asset classes fail the 10-gate proof standard. All previously claimed "winning" strategies (CRYPCO copy-trader WR=93.8%, ETF 56.1% WR/1.34 PF, Kimi ML tokens 85-100% WR) were debunked against ground-truth data.

**Deploy real money only into low-cost index ETF/MF passive allocation** (60% US equity, 20% international, 20% bonds/T-bills). This is beta capture, not alpha — and it is the only capital deployment recommendation supported by the evidence.

**Do not deploy any active prediction strategy** until one asset class passes all 10 proof gates. Currently, none do.
