# Mutual Fund & ETF Solid Pick Plan

**Worktree:** flaxen-hair_2026-11-14T2304 | **Date:** 2026-11-14T23:04Z

## Current State: Zero Coverage

**Critical finding:** Mutual fund infrastructure does NOT exist anywhere in this repository:

| Asset | Status | Evidence |
|-------|--------|----------|
| Mutual fund NAV cache | DOES NOT EXIST | `audit_dashboard/data/mutual_fund_nav_cache/` — directory missing |
| Mutual fund backtest cache | DOES NOT EXIST | `audit_dashboard/data/mf_backtest_cache/` — directory missing |
| Mutual fund ranker | DOES NOT EXIST | `alpha_engine/mutual_fund_ranker.py` — no match |
| Mutual fund metadata | DOES NOT EXIST | `alpha_engine/data/mutual_fund_metadata.csv` — no match |
| MF walkforward tools | DO NOT EXIST | 4 tools missing |
| MUTUAL_FUND asset class | NOT REGISTERED | ML gate class id = -1 (unknown) |
| Mutual fund picks | ZERO live | No picks in dashboard or copy_trader_intel |
| ETF picks | ZERO live | SPY miscategorized as "equity" |

All 9 ETF hypotheses are NOT_PROVED. No ETF or mutual fund picks are live anywhere.

---

## Phase 1: Build Mutual Fund Infrastructure (Weeks 1-2)

### New Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `alpha_engine/mutual_fund_ranker.py` | Rank mutual funds by solid-pick criteria |
| 2 | `alpha_engine/data/mutual_fund_metadata.csv` | Fund metadata (ER, load, 12b-1, min, AUM, turnover, category, benchmark, inception) |
| 3 | `audit_dashboard/data/mutual_fund_nav_cache/` | NAV CSV cache (one file per fund) |
| 4 | `audit_dashboard/data/mf_backtest_cache/` | MF backtest result cache |
| 5 | `audit_dashboard/data/mf_cache_manifest.json` | SHA-256 provenance manifest |
| 6 | `tools/mf_traits_walkforward_runner.py` | MF walkforward runner |
| 7 | `tools/mf_walkforward_backtest.py` | MF walkforward backtest |
| 8 | `tools/mf_trait_features.py` | MF trait feature computation |
| 9 | `alpha_engine/mutual_fund_strategies.py` | MF strategy stubs (NAV-based monthly rebalance) |

### Files to Modify

| # | File | Change |
|---|------|--------|
| A | `alpha_engine/asset_class.py` | Add MUTUAL_FUND_SYMBOLS frozenset, register in CAT_MAP, add is_mutual_fund() helper |
| B | `ml_gatekeeper/gatekeeper.py` | Add `"MUTUAL_FUND": 7` to ASSET_CLASS_MAP |
| C | `audit_trail/dashboard_generator.py` | Add mutual fund to dashboard classes |

### Mutual Fund Solid Pick Criteria (All Must Pass)

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Expense ratio | ≤ 0.20% | Index funds should be cheap |
| Load fees | None | Loads destroy returns |
| 12b-1 fees | None | Marketing drag |
| Minimum investment | ≤ $1,000 | Retail accessibility |
| AUM | ≥ $1B | Liquidity, stability |
| Turnover | ≤ 20% | Lower transaction costs |
| Tracking error | ≤ 0.25% | Tight benchmark adherence |
| Track record | ≥ 10 years | Multiple market cycles |
| Net return > benchmark | 5+ years net of fees | Core "solid pick" test |
| NAV freshness | ≤ 24h | T+1 settlement |
| Daily NAV pricing | Yes | 16:00 ET once daily |
| No round-trip restrictions | Yes | Avoid penalties |

### Starter Mutual Fund Universe

| Symbol | Name | Category | Expense Ratio | AUM |
|--------|------|----------|---------------|-----|
| VFIAX | Vanguard 500 Index Admiral | Large Blend | 0.05% | $400B+ |
| VTSAX | Vanguard Total Stock Mkt Admiral | Large Blend | 0.04% | $1.3T+ |
| FXAIX | Fidelity 500 Index Premium | Large Blend | 0.015% | $170B+ |
| VBTLX | Vanguard Total Bond Mkt Admiral | Intermediate Bond | 0.05% | $300B+ |
| VWELX | Vanguard Wellington Admiral | Allocation—50/70% Equity | 0.25% | $100B+ |
| VGSLX | Vanguard Real Estate Index Admiral | Real Estate | 0.12% | $50B+ |
| VTIAX | Vanguard Total Intl Stock Admiral | Foreign Large Blend | 0.11% | $350B+ |

*(Verify current fees/AUM from prospectus before trading)*

---

## Phase 2: Build ETF Infrastructure (Weeks 3-4)

### ETF Solid Pick Criteria

| Criterion | Threshold |
|-----------|-----------|
| Expense ratio | ≤ 0.10% |
| AUM | ≥ $500M |
| Avg daily volume | ≥ $10M |
| Bid-ask spread | ≤ 0.05% |
| Tracking error | ≤ 0.20% |
| Track record | ≥ 5 years |
| No leverage / no inverse | Plain beta only |
| Net return > benchmark | 3+ years after costs |

### ETF Data Requirements

- Intraday price data (ETFs trade throughout the day)
- Bid-ask spread monitoring
- Creation/redemption mechanism data
- Premium/discount to NAV tracking

---

## Phase 3: Backtest & Validation (Weeks 5-8)

### Backtest Infrastructure

| Tool | Purpose |
|------|---------|
| `tools/mf_walkforward_backtest.py` | Monthly NAV rebalance backtest |
| `tools/mf_traits_walkforward_runner.py` | Walkforward with trait features |
| `tools/mf_trait_features.py` | Compute expense ratio, AUM, turnover features |

### Validation Gates (per PROTOCOL.md)

| Gate | Requirement |
|------|-------------|
| Gate 0 | n ≥ 30, complete trade log |
| Gate 1 | Bootstrap 95% CI: PF_lower > 1.0 |
| Gate 2 | Walk-forward: ≥ 60% profitable folds |
| Gate 3 | PF > 1.5, Sharpe > 1.0, WR > 50% |
| Gate 4 | Net PF > 1.2, DSR > 0.95 |
| Gate 5 | Both directions pass Gate 4 |

---

## Mutual Fund Probability of Success Framework

```
Expectancy = (Win_Rate × Avg_Win) − (Loss_Rate × Avg_Loss)
Kelly f* = Expectancy / Avg_Win
Prob_Ruin = ((1−Edge)/(1+Edge))^(Bankroll/Unit_Risk)
```

### Minimum Thresholds for MF Picks

| Metric | Minimum | Target |
|--------|---------|--------|
| Win rate | > 40% | > 50% |
| Expectancy | > 0.5% per trade | > 1.0% |
| Profit factor | > 1.3 | > 1.5 |
| Sharpe | > 0.5 | > 1.0 |
| Max DD | < 15% | < 10% |
| Forward n | ≥ 100 | ≥ 200 |

---

## Implementation Timeline

| Week | Task | Deliverable |
|------|------|-------------|
| 1 | Create MF infrastructure files | 9 new files created |
| 2 | Register MUTUAL_FUND class, wire dashboard | asset_class.py, gatekeeper.py, dashboard_generator.py |
| 3 | Build MF ranker + backtest tools | ranker.py, walkforward files |
| 4 | Create cache manifest, populate NAV data | mf_cache_manifest.json, NAV CSVs |
| 5 | Run MF backtest on starter universe | Backtest results JSON |
| 6 | Validate ETF criteria, add ETF picks | ETF validation |
| 7 | QA validation on all picks | QA dashboard |
| 8 | Go/No-Go decision | Promote or hold |

---
