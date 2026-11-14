# Peer Review Results — Cross-Check Summary

**Worktree:** flaxen-hair_2026-11-14T2304 | **Date:** 2026-11-14T23:04Z

Three subagents were dispatched to review the plan in detail. Their findings are summarized below.

---

## Subagent 1: Peer File Cross-Checker

### Areas Reviewed
- Peer reports and summaries (final_v3/, final_v2/, final_2026_11_14/)
- Peer profitability claims
- Contradictory metrics across peer reports
- Data quality issues (PnL=0, blank fields, stale timestamps)
- Mutual fund coverage in peer reports
- Workflow/CI status

### Key Findings

**Peer contradictions found:**
- ETF win rate: 2.22% vs 68.42% across different files (85× spread)
- CRYPCO count: 3,705 vs 22,055 (6× difference)
- VWAP claim: Claimed Sharpe 3.76, actual ~1.18 (falsified)
- Mega-mutation: 21/50 forward picks may be synthetic/replay
- Promotion gates: Both FDR and single-source default OFF
- Cost gate: Fail-open on missing evidence

**Data quality issues:**
- PnL=0% entries in live_picks.json (many strategies)
- Blank fields in pick records
- Stale timestamps on many data files

**Mutual fund coverage:** Zero coverage across all peer reports — confirmed NOT_BUILT

**Workflow failures:** CI tests failing (Python 3.11 and 3.12, run 43644095951)

### Recommended Fixes
1. Reconcile contradictory metrics with cohort_id and filter hashes
2. Fix PnL calculation bugs (PnL=0% with price movement)
3. Add blank field validation
4. Enable promotion gates (fail-closed)
5. Fix cost gate fail-open paths
6. Investigate CI failures

---

## Subagent 2: Mutual Fund + ETF Reviewer

### Mutual Fund Data Quality Assessment

**Finding: Zero coverage — no mutual fund infrastructure exists**

| Attribute | Expected | Actual |
|-----------|----------|--------|
| mutual_fund_nav_cache/ | 46 CSVs | Directory does not exist |
| mf_backtest_cache/ | 71 CSVs | Directory does not exist |
| mf_walkforward_results.json | Dated 2026-10-23 | Does not exist |
| mf_traits_walkforward_results.json | Dated 2026-10-23 | Does not exist |
| alpha_engine/mutual_fund_ranker.py | Ranker logic | Does not exist |
| alpha_engine/data/mutual_fund_metadata.csv | Fund metadata | Does not exist |
| MUTUAL_FUND in ASSET_CLASS_MAP | Class ID | Missing (class id = -1, unknown) |

### ETF Coverage Assessment

All 9 ETF hypotheses are NOT_PROVED:
- H5 ETF dual momentum: Sharpe 0.99, n=6 (fails n≥30)
- H8 Sector RSI(2): Sharpe 1.16, DSR 0.603 (fails DSR)
- H16 ETF XS momentum: Sharpe 0.98 vs 1.18 benchmark (SPA 0.488)
- H17 ETF reversal: Sharpe 0.76 vs 1.18
- H18 ETF TSMOM: Sharpe 1.00, WF 0.37
- H19 Country rotation: Sharpe 0.76, n=22

No ETF or mutual fund picks are live anywhere.

### Proposed Mutual Fund Selection Criteria

| Criterion | Threshold |
|-----------|-----------|
| Expense ratio | ≤ 0.20% |
| Load fees | None |
| 12b-1 fees | None |
| Min investment | ≤ $1,000 |
| AUM | ≥ $1B |
| Turnover | ≤ 20% |
| Tracking error | ≤ 0.25% |
| Track record | ≥ 10 years |
| NAV freshness | ≤ 24h |

### Files to Create (10 new files)
1. `alpha_engine/mutual_fund_ranker.py`
2. `alpha_engine/data/mutual_fund_metadata.csv`
3. `audit_dashboard/data/mutual_fund_nav_cache/`
4. `audit_dashboard/data/mf_backtest_cache/`
5. `audit_dashboard/data/mf_cache_manifest.json`
6. `tools/mf_traits_walkforward_runner.py`
7. `tools/mf_walkforward_backtest.py`
8. `tools/mf_trait_features.py`
9. `alpha_engine/mutual_fund_strategies.py`

### Files to Modify (5 existing files)
- `alpha_engine/asset_class.py` — Add MUTUAL_FUND_SYMBOLS
- `ml_gatekeeper/gatekeeper.py` — Add MUTUAL_FUND: 7
- `audit_trail/dashboard_generator.py` — Add MF dashboard bucket
- `multi_asset/portfolio_defs.py` — Verify/extend MF universe
- `research/profitability/HYPOTHESES.md` — Add MF hypotheses

---

## Subagent 3: Risk Management Reviewer

### Risk Management Coverage Assessment

| Risk Area | Coverage | Status |
|-----------|----------|--------|
| Position sizing (Kelly) | ✅ Complete | kelly_position_sizer.py |
| Position sizing (fixed %) | ⚠️ Partial | Fallback only |
| Volatility-based sizing | ✅ Complete | tpsl_policy.py |
| Stop loss (ATR-based) | ✅ Complete | sl_calibrator.py |
| Stop loss (fixed %) | ⚠️ Partial | Fallback only |
| Take profit | ✅ Complete | ATR-based + MAE/MFE |
| Risk-adjusted returns | ✅ Complete | Sharpe, Sortino, Calmar, PSR |
| Drawdown controls (circuit breaker) | ✅ Complete | -5%/-10%/-15% |
| Drawdown controls (weekly/monthly) | ❌ Missing | Not implemented |
| Correlation limits | ✅ Complete | Groups, max 3/group |
| Kill switch | ✅ Complete | 4-tier system |
| VaR/ES | ✅ Complete | Historical VaR(95%) |
| Stress testing | ✅ Complete | 5 scenarios |
| QA validation | ⚠️ Partial | Zero-PnL detector exists |
| Risk dashboard webpage | ❌ Missing | No standalone page |
| Expectancy framework | ❌ Missing | No unified calculator |

### Recommended Risk Management Parameters

| Parameter | Conservative | Moderate | Aggressive |
|-----------|-------------|----------|------------|
| Risk per trade | 1.0% | 1.5% | 2.0% |
| Kelly fraction | 0.25 | 0.25 | 0.25 |
| Max single position | 3% | 4% | 5% |
| Daily loss cap | -0.5% | -1.0% | -2.0% |
| Weekly loss cap | -1.5% | -3.0% | -5.0% |
| Monthly loss cap | -3.0% | -6.0% | -10.0% |

### Separate Risk Dashboard Webpage

**File:** `risk_dashboard.html` (standalone)

**Sections:**
1. Portfolio Health Gauge (equity curve, drawdown, VaR, CVaR)
2. Drawdown Controls Progress Bars (daily/weekly/monthly)
3. Position Sizing Table (Kelly %, position %, risk $, ATR stop)
4. Correlation Heatmap (asset correlation matrix)
5. Risk-Adjusted Returns Table (Sharpe, Sortino, Calmar, PSR)
6. Kill Switch Status (level, multiplier, auto-recovery)
7. QA Alerts (PnL=0%, blank fields, open items)

**Data JSON Schema:** `alpha_engine/data/risk_metrics.json`
**Generation Script:** `tools/risk_dashboard_data.py`

---

## Consolidated Recommended Action Items

| Priority | Action | Owner File(s) |
|----------|--------|---------------|
| P0 | Enable promotion gates (FDR + single-source) | alpha_engine/money_ready_verdict.py |
| P0 | Close cost gate fail-open paths | alpha_engine/per_class_cost_gate.py |
| P0 | Stop suppressing after-cost errors | audit_trail/dashboard_generator.py |
| P0 | Add weekly/monthly loss limits | alpha_engine/risk_controls.py |
| P1 | Create QA validator (PnL=0%, blank fields, open items) | alpha_engine/risk_qa_validator.py |
| P1 | Wire QA checks into production scanner | production_scanner.py |
| P2 | Register MUTUAL_FUND asset class | alpha_engine/asset_class.py |
| P2 | Add MUTUAL_FUND class ID to gatekeeper | ml_gatekeeper/gatekeeper.py |
| P2 | Add mutual fund dashboard bucket | audit_trail/dashboard_generator.py |
| P2 | Create risk thresholds config | alpha_engine/risk_thresholds.json |
| P2 | Create mutual fund ranker | alpha_engine/mutual_fund_ranker.py |
| P2 | Create MF backtest tools | tools/mf_*.py |
| P2 | Create MF cache manifest | audit_dashboard/data/mf_cache_manifest.json |
| P2 | Create risk dashboard webpage | risk_dashboard.html |
| P2 | Create risk dashboard data script | tools/risk_dashboard_data.py |

---
