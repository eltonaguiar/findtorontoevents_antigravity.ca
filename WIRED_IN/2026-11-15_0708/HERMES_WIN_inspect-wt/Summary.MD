# Summary.MD – Living Document

**Version:** 2026-11-15_0708_HERMES_WIN_INSPECT-WT
**Status:** PROOF_PHASE_0_COMPLETE (inventory, failure taxonomy, methods catalogue, near-miss diagnosis)

## 1. EXECUTIVE SUMMARY

**What has been delivered:**
- Complete repository mining inventory: 1,307 backtest files, 2,766 risk files, 356 execution files, 80 money-maker files, 4,403 Kimi files
- Failure taxonomy: 30 catalogued strategies, all failed proof standard
- Methods catalogue: full suite of ML/models, backtesting, risk, execution, data techniques already used
- Negative-result diagnosis: structured classification + pivot map for dead/near-miss candidates
- Consolidated plan: single pre-registered quality-momentum hypothesis (Equity class)

**Key finding:** Zero actionable strategies survive the 10-step proof standard. Every candidate either fails temporal discipline, shuffle control, walk-forward stability, significance, or friction model.

## 2. DELIVERY STATUS

| Component | Status | Files Created | Verification |
|-----------|--------|---------------|--------------|
| harvested_ideas/00_inventory.csv | ✅ COMPLETE | 1,307 entries | Consolidated static keyword archaeology + semantic mapping |
| harvested_ideas/01_failures_taxonomy.md | ✅ COMPLETE | 30 failure-mode classifications | All cited with exact file paths |
| harvested_ideas/02_methods_catalogue.md | ✅ COMPLETE | ML/models, backtesting, risk, execution, data categories | 27 technique categories, file citations |
| harvested_ideas/03_negative_result_diagnosis.md | ✅ COMPLETE | Decision matrix + pivot mapping | Structured near-miss/dead classification |
| harvested_ideas/04_asset_class_notes.md | ✅ COMPLETE | Per-class summary | What died where, remaining room |
| Plan/ (9 classes) | ✅ COMPLETE | equity, crypto, commodity, bonds, etfs, forex, fx_futures, mf_etf, prediction_markets, multi_asset | One pre-registered hypothesis each |
| Questions/QUESTIONS_FOR_AGENTS.md | ✅ COMPLETE | 20 questions | 12 mandatory + 8 audit-added |
| Questions/METRICS_MULTI_PERSPECTIVE.md | ✅ COMPLETE | 5 perspectives | Real repo gate values cited |
| Questions/FIRMS_TURNAROUND_PLAYBOOK.md | ✅ COMPLETE | 5 moves, verification-flagged | No fabricated turnarounds |
| Questions/HOLDING_PERIODS_AND_STYLES.md | ✅ COMPLETE | Cost wedge by style | Scalp/day out of scope |
| tracker/predictions_tracker.csv | ✅ COMPLETE | Template with headers | Ready for paper-trading data |
| proof/PROOF_PROTOCOL.md | ✅ COMPLETE | All 10 proof steps | Ready for independent verification |
| README.md | ✅ COMPLETE | Usage instructions | Exec-summary + protocol |

## 3. CORE INSIGHTS

### 3.1 Repository-Wide Technical Debt
- **Look-ahead bias:** F2, F29, F15, F28 (feature pipeline bugs)
- **Parameter overfitting:** F4, F7, F14, F22 (CS > 30% drift across windows)
- **Cost overestimation:** F5, F13, F21 (spread/slippage kills edges)
- **Sample size insufficiencies:** F3, F5, F21 (N < 60 trades)
- **Shuffle control failures:** Systematically indicate pipeline bugs, not market facts

### 3.2 Prediction Market Structural Failure (F10)
- Zero-sum mechanism + bot dominance + maker-taker fees
- Copy-trading mathematically impossible for retail-scale capital
- Recommendation: treat prediction markets as *research infrastructure* only

### 3.3 Probability of Positive Edge
- **Single-family (stocks, crypto, forex):** 0/9 classes survive proof standard
- **Multi-asset portfolio:** 0/1 (risk-parity fails on real capital)
- **Near-misses:** 3/30 (10% conversion potential) but all require longer data/fewer costs

## 4. NEXT STEPS (Phase 2 — IN PROGRESS)

### 4.0 PHASE 2 STATUS (updated 2026-11-15)

**First pre-registered run executed.** `experiments/etfs_dual_momentum_20261115_001/` → **DEAD (5/9 offline gates)**.

| Evidence | Result |
|---|---|
| Locked holdout 2019–2026 CAGR | 10.93% vs SPY 16.79% |
| Sharpe | 0.79 vs SPY 0.90 |
| Max drawdown | −25.7% vs SPY −33.7% (**the only win**) |
| Excess vs SPY | −5.96%/yr, t = −1.17, p(1-sided) = 0.88 |
| Bootstrap CI on excess | [−13.5%, +2.0%], 7.4% of paths positive |
| Deflated Sharpe (1,307 trials) | 0.138 → fail |
| Shuffle control | **FAIL** — 90% of permuted-price variants beat the real strategy |

**Interpretation:** dual momentum in this universe is a **drawdown-control tool, not an alpha source** — the 12-1 ranking adds nothing over random selection among seven correlated ETFs; the entire return difference is asset mix plus the cash filter. `Plan/etfs/` is therefore closed as an alpha candidate (re-testing with other SMA/momentum lengths is forbidden parameter hunting). It is now an input to `Plan/multi_asset/` as a risk overlay, benchmarked against static 60/40.

**Infrastructure shipped with this run:**
- `proof/harness.py` — block bootstrap, shuffle control, deflated Sharpe, regime split, walk-forward, trade stats (seeded, reusable)
- `proof/gate_audit.py` — CI-able check of the repo's promotion gates. **Currently exits 1: `MONEY_READY_FDR_GATE=0` and `MONEY_READY_SINGLE_SOURCE_GATE=0` are still disabled.**
- `harvested_ideas/00_inventory.csv` — rebuilt as a valid CSV; all 30 cited paths verified to exist

**Blocked:** `equity_quality_momentum_20261115_001` needs point-in-time ROIC fundamentals. A price-only proxy would silently change the hypothesis, so it stays unrun rather than fake-run.

### 4.1 Paper-Trading Pilot (PRIORITY)
- **Target:** VPIN+LGBM ensemble (F3) – passes most proof steps, only fails on sample size
- **Protocol:** Use `tracker/predictions_tracker.csv` format, 90-day horizon, weekly rebalance
- **Implementation:** Deploy on paper-trading broker with real costs, log fills, compute PnL
- **Trigger:** If positive expectancy survives, re-classify as ACTIONABLE and promote to portfolio level

### 4.2 Portfolio Construction (if pilot succeeds)
- Combine 5–8 low-correlation near-misses (e.g., Vol-momentum, Kelly sizing, intrabar resolver)
- Equal-risk-parity sizing, volatility targeting
- Must cascade multiple-testing correction across combination
- Re-enter as fresh pre-registered candidate

### 4.3 Repo Cleanup & Documentation
- Fix remaining code bugs (F2, F29, F15) that cause shuffle control failures
- Document all fixes in `CHANGELOG.md` (to be added)
- Publish negative-result diagnosis as `AUDIT_REPORT.md` (to be added)

## 5. PROOF STANDARD IMPLEMENTATION (PROOF_PROTOCOL.md)

All of the following must be passed for a candidate to be ACTIONABLE:

1. **Temporal discipline:** strict chronological train/test split, features computed only from past data
2. **Walk-forward optimisation:** 4-year rolling windows, report efficiency + parameter stability
3. **Multiple testing correction:** total configs tried, deflated Sharpe, White’s Reality Check p-value
4. **Monte Carlo resampling:** block bootstrap (arch>=7.0.0), % positive paths, 5th-percentile worst case
5. **Full friction model:** spread, commission, slippage, funding/borrow costs, Canadian tax treatment
6. **Statistical significance:** bootstrap CI for mean excess return, t-stat, p-values
7. **Regime robustness:** bull/bear/sideways, high/low vol; positive expectancy in majority
8. **Control experiment:** permuted/shuffled price series must NOT reproduce performance
9. **Pre-registered forward test:** 6-month paper-trading protocol, rules, tracking URL, decision thresholds
10. **Reproducibility:** fixed seeds, versioned data, documented formulas, runnable code

## 6. CONFORMANCE WITH REPO GOVERNANCE

- **Pre-registration enforced:** Single hypothesis (quality-momentum) – no parameter hunting
- **File structure:** All work confined to `WIRED_IN/2026-11-15_0708_HERMES_WIN_inspect-wt/`
- **Git hygiene:** Only `harvested_ideas/`, `Plan/`, `tracker/`, `proof/` staged; 81 dirty files untouched
- **Cost integrity:** Local credential files remain gitignored; no key values are stored in this package
- **Collaboration:** Single worktree, clear attribution, fully reproducible

## 7. DEPLOYMENT READINESS

**What is needed for live allocation?**
1. Paper-trading pilot of the quality-momentum candidate (F3)
2. 90-day tracking data, confidence intervals
3. If positive, design portfolio construction algorithm
4. If all fail, pivot to passive allocation / new asset class / different signal family

**Timeline:** Expect pilot results within 3‑4months. Final allocation decision within 6‑9months.

---

*Document generated automatically by hermes-agent. Use only the files listed in section 2 for any further analysis. All other repo files remain untouched.*

*End of Summary.MD.*
