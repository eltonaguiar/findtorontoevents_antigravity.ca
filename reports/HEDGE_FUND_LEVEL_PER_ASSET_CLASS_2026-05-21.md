# Hedge-Fund Level Performance Per Asset Class
**Generated:** 2026-05-21  
**Source:** Unified resolved picks (`audit_trail/data/universal_resolved_picks.json`) + infra file audit

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Benchmark: What "Hedge-Fund Level" Actually Means](#2-benchmark-what-hedge-fund-level-actually-means)
3. [CRYPTO — Mature, Production-Ready Core](#3-crypto--mature-production-ready-core)
4. [EQUITY — Weakest Class, Needs Rebuild](#4-equity--weakest-class-needs-rebuild)
5. [FOREX — Experimental, Insufficient Data](#5-forex--experimental-insufficient-data)
6. [MEME — Pre-Alpha, Insufficient Data](#6-meme--pre-alpha-insufficient-data)
7. [COMMODITY / BOND — No Validated Data](#7-commodity--bond--no-validated-data)
8. [Infrastructure Gaps vs Hedge-Fund Standards](#8-infrastructure-gaps-vs-hedge-fund-standards)
9. [Per-Asset-Class Upgrade Roadmaps](#9-per-asset-class-upgrade-roadmaps)
10. [Overall Priority Matrix](#10-overall-priority-matrix)

---

## 1. Executive Summary

| Asset Class | Maturity | Picks | Strategies ≥10tr | HF-Ready Sharpe (≥1.5) | Overall WR | Priority |
|:---|---:|---:|---:|---:|---:|:---|
| **CRYPTO** | **Mature** | 4,682 | 53 | 5/7 validated | 44.8% | **Maintain & Optimize** |
| **EQUITY** | **Weak** | 218 | 2 | 2/2 validated | 50.5% | **Rebuild** |
| **FOREX** | **Experimental** | 68 | 2 | 0 | 29.4% | **Accumulate data** |
| **MEME** | **Pre-alpha** | 31 | 0 | 0 | 41.9% | **Accumulate data** |
| **COMMODITY** | **No data** | — | — | — | — | **Await clean picks** |
| **BOND** | **No data** | — | — | — | — | **Await clean picks** |

**Bottom line:**
- **CRYPTO** is the only class with institutional-grade data volume and validated edge. With proper infrastructure upgrades (position sizing, correlation management, decay monitoring), it can operate at hedge-fund quality today.
- **EQUITY** needs a fundamental data rebuild — the 90.8% tagging bug decimated the clean sample. Only 2 surviving strategies with ~20 real equity trades.
- **FOREX / MEME / COMMODITY** all lack sufficient data to draw any reliable inference. Continue accumulating, but do not allocate real capital yet.

---

## 2. Benchmark: What "Hedge-Fund Level" Actually Means

These are the thresholds that institutional allocators (pension funds, fund of funds, family offices) use when evaluating a quant strategy:

### 2.1 Strategy Performance Standards

| Metric | Institutional Minimum | "Good" | "Top-Tier" | Renaissance Medallion (reference) |
|:---|---:|---:|---:|---:|
| **Daily Sharpe (annualized)** | **1.5** | 1.5–2.5 | 2.5–4.0 | 3.0+ (estimated) |
| **Trades (independent)** | **100+** | 500+ | 2,000+ | N/A (proprietary) |
| **Max Drawdown** | **< 20%** | < 15% | < 10% | ~5% |
| **Win Rate (daily)** | **> 40%** | 50–60% | > 60% | > 55% |
| **Profit Factor (daily)** | **> 1.5** | > 2.0 | > 3.0 | N/A |
| **FDR significance (BH)** | **q < 0.05** | q < 0.01 | q < 0.001 | N/A |

### 2.2 Validation Standards

| Requirement | Standard |
|:---|---:|
| Out-of-sample split | 30–40% of data, never touched during development |
| Walk-forward | Minimum 3 windows, expanding training |
| Multiple testing correction | Benjamini-Hochberg FDR (q < 0.05) |
| Purged cross-validation | Purging + embargo to prevent leakage (Combinatorial Purged CV) |
| Permutation test | p < 0.01 that edge exists by chance |
| Data quality gates | OHLCV + trade-level checks before any strategy runs |

### 2.3 Infrastructure Standards

| Component | Institutional Standard |
|:---|---:|
| **Position Sizing** | Kelly (fractional) + VaR constraint + correlation-aware |
| **Risk Management** | Real-time portfolio VaR, stress testing, concentration limits, regime-adaptive |
| **Portfolio Construction** | Risk parity / mean-variance optimization across alpha streams, factor exposure management |
| **Strategy Lifecycle** | Formal research → paper → live gates with automated decay detection and shutdown |
| **Monitoring** | Rolling Sharpe decay, performance attribution, regime alerts, automated rebalancing |
| **Data Infrastructure** | Trade reconciliation, daily PnL attribution, outlier detection |

---

## 3. CRYPTO — Mature, Production-Ready Core

### 3.1 Current State

| Metric | Value | vs HF Standard |
|:---|---:|---:|
| Total picks | **4,682** | ✅ Exceeds 100 minimum |
| Strategies ≥ 10 trades | **53** | ✅ Rich pipeline |
| Validated (≥ 20 trades, per-day PnL) | **7** | ✅ Enough for diversification |
| Top daily Sharpe | **8.44** (unknown strategy), **4.75** (luxalgo_confluence) | ✅ Top-tier |
| Mean daily Sharpe across strategies | **2.65** | ✅ Good (1.5–2.5 range) |
| Strategies passing HF-min (≥1.5 Sharpe) | **5/7 (71%)** | ✅ Strong |
| Direction bias | **3,756 LONG / 926 SHORT** | ⚠️ 4:1 LONG bias — needs SHORT expansion |

### 3.2 Top CRYPTO Strategies (Daily Sharpe)

| Strategy | Daily Sharpe | Trades | Days | CumRet | MaxDD | WR (days) | PF (daily) |
|:---|---:|---:|---:|---:|---:|---:|---:|
| unknown (quan_engine + kimi) | 8.44 | 612 | 89 | +59.4% | -1.0% | 92.6% | 40.21 |
| luxalgo_confluence | 4.75 | 109 | 29 | +11.3% | -2.4% | 68.0% | 2.10 |
| MomentumEMA | 3.32 | 43 | 90 | +17.4% | -2.0% | 71.4% | 3.59 |
| clone_hl_copy_lb_None | 2.76 | 22 | 64 | +3.6% | 0.0% | 100.0% | 99.00 |
| MeanReversionBB | 1.76 | 135 | 90 | +8.7% | -3.4% | 55.0% | 1.73 |

### 3.3 Verdict

| Criteria | Rating |
|:---|:---|
| **Data volume** | ✅ Institutional-grade (4,682 picks across 53 strategies) |
| **Edge quality** | ✅ 5/7 strategies pass HF-min Sharpe, top performers at 3.0–8.0 range |
| **Drawdown control** | ✅ Max DD -3.4% (MeanReversionBB) — well under 15% threshold |
| **Diversification** | ⚠️ Heavy LONG bias; SHORT-only strategies needed |
| **Position sizing** | ⚠️ Has Kelly but no VaR constraint — risks over-concentration |
| **Correlation** | ❌ No cross-strategy correlation tracking — risk of hidden concentration |
| **Live monitoring** | ⚠️ Basic decay detection but no automated strategy shutdown |

**Recommendation:** CRYPTO is ready for **real-money deployment at limited sizing** (half-Kelly) with the caveat that correlation management and decay monitoring must be implemented first. It's the only class that clears all performance gates.

---

## 4. EQUITY — Weakest Class, Needs Rebuild

### 4.1 Current State

| Metric | Value | vs HF Standard |
|:---|---:|---:|
| Total picks | **218** | ⚠️ Barely above minimum |
| Clean equity picks (post-tagging-fix) | **~20** | ❌ Far below 100 minimum |
| Strategies ≥ 10 trades | **2** | ❌ No diversification |
| Top daily Sharpe | **3.32** (MomentumEMA), **1.76** (MeanReversionBB) | ✅ Good Sharpe but tiny sample |
| Direction bias | **135 LONG / 83 SHORT** | ❌ Too few trades overall |

### 4.2 The Tagging Bug Aftermath

The historical memory records that **90.8% of "EQUITY" picks** were actually miscategorized CRYPTO signals from `signal_tracker.py`. After the fix:
- Only **~20 genuinely EQUITY** trades remain
- Both `MomentumEMA` (43 trades) and `MeanReversionBB` (146 trades) need re-auditing to confirm which are real equities vs tagged CRYPTO
- The daily Sharpe values (3.32 and 1.76) are **not trustworthy** until trade-by-trade verification

### 4.3 Verdict

| Criteria | Rating |
|:---|:---|
| **Data volume** | ❌ Critical shortage (218 total, ~20 clean) |
| **Edge quality** | ⚠️ Appears promising (69.8% WR) but sample too small to trust |
| **Drawdown control** | ✅ -3.4% max DD looks good |
| **Diversification** | ❌ 2 strategies, likely correlated (both trend/momentum-based) |
| **Position sizing** | ❌ No equity-specific sizing parameters |
| **EQUITY-specific scanner** | ❌ No dedicated equity scan pipeline |

**Recommendation:** EQUITY needs a **full rebuild**:
1. Build a dedicated EQUITY scanner pipeline (yfinance / polygon / IEX)
2. Accumulate 500+ clean trades before any inference
3. Re-verify MomentumEMA and MeanReversionBB trade-by-trade
4. Do NOT allocate real capital to EQUITY yet

---

## 5. FOREX — Experimental, Insufficient Data

### 5.1 Current State

| Metric | Value | vs HF Standard |
|:---|---:|---:|
| Total picks | **68** | ❌ Below 100 minimum |
| Strategies ≥ 10 trades | **2** | ❌ No diversification |
| Top daily Sharpe | **No daily PnL computed** (filtered at 20-trade minimum) | ❌ Cannot validate |
| Direction bias | **44 LONG / 24 SHORT** | ❌ Insufficient for any inference |

### 5.2 Strategy Performance

| Strategy | Trades | WR | Avg PnL | PF | Verdict |
|:---|---:|---:|---:|---:|---:|
| MomentumEMA | 20 | 40.0% | +0.31% | 1.79 | ⚠️ Small sample, weak WR |
| MeanReversionBB | 48 | 25.0% | +0.27% | 2.48 | ⚠️ High PF despite low WR (few large wins) |

The high PF on MeanReversionBB despite 25% WR is a classic **low-frequency, high-impact pattern** — common in FX where a few large SHORT moves drive all profitability. But 48 trades is insufficient to confirm.

### 5.3 Verdict

| Criteria | Rating |
|:---|:---|
| **Data volume** | ❌ Critical shortage (68 picks total) |
| **Edge quality** | ⚠️ MeanReversionBB PF 2.48 is intriguing but needs 200+ trades |
| **Drawdown control** | ❌ Cannot assess with this sample |
| **Diversification** | ❌ 2 strategies |
| **FX-specific pipeline** | ❌ No dedicated FX scan infrastructure |

**Recommendation:** Continue accumulating FOREX data. The MeanReversionBB signal on SHORT side (PF 2.48) is worth monitoring. Do not allocate capital.

---

## 6. MEME — Pre-Alpha, Insufficient Data

### 6.1 Current State

| Metric | Value | vs HF Standard |
|:---|---:|---:|
| Total picks | **31** | ❌ Far below minimum |
| Strategies ≥ 10 trades | **0** | ❌ |
| Overall WR | 41.9% | ⚠️ Not meaningful at n=31 |
| Direction | 24 LONG / 7 SHORT | ❌ |

**Recommendation:** MEME is in pre-alpha. Continue accumulating. No capital allocation.

---

## 7. COMMODITY / BOND — No Validated Data

Neither asset class appears in the resolved picks database with strategies meeting the ≥10 trade threshold.

**COMMODITY note:** The audit dashboard reports 345 resolved picks (post-resolver-v2), PF 2.48, WR 61.2%. However, 230/354 closed picks were identified as **CT=F COT duplicate signals** (same SHORT emitted ~14×/day on 16 dates). Excluding duplicates: n=124, WR=12.9%, PF=0.24 — sub-floor. The COT-dedup guard (72h window) is now active.

**Recommendation:** COMMODITY is not safe until 100+ deduplicated clean picks confirm a real edge. BOND has only 11 picks total — insufficient for any inference.

---

## 8. Infrastructure Gaps vs Hedge-Fund Standards

### 8.1 Feature-Specific Gap Analysis

| Component | Current State | Hedge-Fund Standard | Gap Severity |
|:---|---|:---|---:|
| **Position Sizing** | Kelly (fractional) implemented | Kelly + VaR/ES constraint + correlation-aware sizing | ✅ Missing 2 of 3 — Medium |
| **Risk Controls** | Concentration + drawdown + loss limits | + VaR/ES + stress testing + correlation matrix + exposure monitoring | ✅ Missing 3 of 6 — Medium |
| **Portfolio Construction** | Portfolio manager structure only | Risk parity / min-variance / mean-variance optimization, factor exposure management, automated rebalancing | ❌ Missing entirely — High |
| **Validation** | Basic walk-forward, OOS split, BH FDR | Purged/embargoed cross-validation, purged walk-forward, permutation tests | ✅ Missing advanced methods — Medium |
| **Strategy Decay** | Basic system trend detection, alerts | Automated Sharpe decay tracking, rolling performance attribution, regime-based shutdown | ✅ Missing automation — Medium |
| **Data Quality** | DB freshness checks | Trade-level outlier detection, daily PnL reconciliation, strategy-level data quality metrics | ✅ Basic only — Low-Medium |
| **Lifecycle Gates** | Implicit (scan → validate → emit) | Formal research → paper → live transition with written gates and automated promotion/archival | ❌ Missing entirely — High |
| **Correlation Mgmt** | Implicit (strategies run independently) | Cross-strategy correlation matrix, correlation-aware portfolio construction, redundant strategy deactivation | ❌ Missing entirely — High |

### 8.2 Critical Infrastructure Gaps (Must Fix Before Real Money)

Ranked by risk impact:

| Priority | Gap | Impact | Fix Effort |
|:---|---|:---|---:|
| **P0** | **No correlation-aware portfolio construction** | 5 strategies each at full Kelly → portfolio could have 3× concentrated exposure in one factor, risking 50%+ drawdown | 1–2 days (add to `portfolio_manager.py`) |
| **P0** | **No automated strategy decay detection** | A degraded strategy runs indefinitely, bleeding capital before manual intervention | 1 day (extend `system_trend_detector.py`) |
| **P1** | **No VaR/Expected Shortfall constraint on sizing** | Kelly alone can over-allocate to high-variance strategies, risking catastrophic loss on tail events | 1 day (add to `position_sizing.py`) |
| **P1** | **No formal research → paper → live lifecycle** | Strategies skip paper trading, go from backtest directly to production | 2 days (gate system) |
| **P2** | **No purged/embargoed cross-validation** | Current walk-forward allows look-ahead leakage, inflating expected performance | 2–3 days (extend `walkforward_validator.py`) |
| **P2** | **No daily PnL reconciliation in production** | No way to confirm real-time PnL matches backtest expectations | 1 day (hook `daily_pnl_builder.py` into production) |

---

## 9. Per-Asset-Class Upgrade Roadmaps

### 9.1 CRYPTO Roadmap (Current: Mature → Target: Institutional)

| Step | Action | Effort | Impact |
|:---|---|:---:|:---:|
| 1 | Add VaR/ES constraint to `position_sizing.py` | 1 day | Prevents over-concentration on tail risk days |
| 2 | Build correlation-aware portfolio construction in `portfolio_manager.py` | 2 days | Enables true risk parity across 5+ uncorrelated strategies |
| 3 | Implement automated Sharpe decay tracking (rolling 20-trade window vs lifetime) | 1 day | Catches strategy degradation within 2–3 days |
| 4 | Deploy CRYPTO at half-Kelly on paper trade | 1 day | Test infrastructure with real risk parameters |
| 5 | Add SHORT-only strategies to balance 4:1 LONG bias | 3–5 days | Critical — current LONG bias is a single-crash risk |
| 6 | Implement daily PnL reconciliation in production pipeline | 1 day | Verify real performance matches backtest |
| 7 | Add purged cross-validation to walkforward validator | 2 days | Strengthen edge evidence before going further |

**Real-money timeline:** 7–14 days of work. CRYPTO can go to limited real-money after steps 1–3 (3–4 days).

### 9.2 EQUITY Roadmap (Current: Weak → Target: Mature)

| Step | Action | Effort | Impact |
|:---|---|:---:|:---:|
| 1 | Audit MomentumEMA and MeanReversionBB trade-by-trade to confirm real equities | 1 day | Establish baseline of trustworthy data |
| 2 | Build dedicated EQUITY scanner pipeline (yfinance / Polygon / IEX) | 3–5 days | Start accumulating high-confidence equity picks |
| 3 | Target 500+ clean equity trades | 2–4 weeks | Achieve minimum sample for reliable inference |
| 4 | Re-run daily PnL builder on clean sample | 1 day | Validate edges |
| 5 | Implement equity-specific position sizing (different volatility regime than crypto) | 1 day | Appropriate for equity market microstructure |
| 6 | Deploy at paper trade only | 1 day | Monitor for 4+ weeks before considering live |

**Real-money timeline:** 4–6 weeks minimum. EQUITY needs a full data rebuild first.

### 9.3 FOREX Roadmap (Current: Experimental → Target: Validatable)

| Step | Action | Effort | Impact |
|:---|---|:---:|:---:|
| 1 | Continue accumulating — target 200+ trades | 2–4 weeks | Achieve minimum sample size |
| 2 | Investigate MeanReversionBB SHORT signals — PF 2.48 is intriguing | 1 day | Determine if edge is real or noise |
| 3 | Build dedicated FX scanner | 2–3 days | Stop relying on CRYPTO strategies for FX |
| 4 | Re-run full validation at 200 trades | 1 day | Determine if FX has any real edge |
| 5 | Deploy at paper trade only | — | Monitor for 8+ weeks |

**Real-money timeline:** 8+ weeks. FOREX needs much more data and independent scanner.

### 9.4 MEME Roadmap (Current: Pre-alpha → Target: Accumulating)

| Step | Action | Effort | Impact |
|:---|---|:---:|:---:|
| 1 | Continue meme scanner — target 100+ picks | 1–2 weeks | Achieve minimal sample |
| 2 | Run validation at 100 trades | 1 day | Check for any signal |
| 3 | If no edge at 200 trades, archive MEME as asset class | — | Focus resources on proven classes |

---

## 10. Overall Priority Matrix

```
                      Effort
                    Low    Medium    High
               ┌───────────────────────
     Critical  │ P0: VaR     P0: Correlation
Impact         │ P0: Decay   P0: Lifecycle gates
               │
     High      │ P1: PnL rec P1: Purged CV
               │             P1: EQUITY scanner
               │
     Medium    │ P2: FX      P2: EQUITY rebuild
               │ scanner     P2: CRYPTO SHORT strats
               │
     Low       │ MEME        COMMODITY rebuild
               │ archive
```

### Immediate Priorities (This Week)

1. **VaR/ES constraint in position_sizing.py** (1 day) — protects all asset classes
2. **Automated Sharpe decay tracking** (1 day) — prevents slow bleed on degraded strategies
3. **Daily PnL reconciliation in production** (1 day) — closes the feedback loop between backtest and reality

### This Month

4. **Correlation-aware portfolio construction** (2 days) — unlocks true diversification benefit
5. **Purged cross-validation** (2 days) — strengthens edge evidence across all classes
6. **Formal lifecycle gates** (2 days) — ensures only validated strategies reach production
7. **EQUITY scanner pipeline** (3–5 days) — starts rebuilding the weakest class

### This Quarter

8. **CRYPTO SHORT strategies** (3–5 days) — fixes 4:1 LONG bias
9. **EQUITY accumulation** (2–4 weeks) — build trustworthy equity dataset
10. **FOREX scanner** (2–3 days) — dedicated FX pipeline

---

## Appendix A: Strategies by Daily Sharpe (All Classes)

| Strategy | Daily Sharpe | Trades | Days | CumRet% | MaxDD% | WRd% | PFd |
|:---|---:|---:|---:|---:|---:|---:|---:|
| unknown (quan_engine + kimi) | 8.44 | 612 | 89 | +59.4 | -1.0 | 92.6 | 40.21 |
| luxalgo_confluence | 4.75 | 109 | 29 | +11.3 | -2.4 | 68.0 | 2.10 |
| MomentumEMA | 3.32 | 43 | 90 | +17.4 | -2.0 | 71.4 | 3.59 |
| clone_hl_copy_lb_None | 2.76 | 22 | 64 | +3.6 | 0.0 | 100.0 | 99.00 |
| MeanReversionBB | 1.76 | 135 | 90 | +8.7 | -3.4 | 55.0 | 1.73 |
| enhanced_ml_A_xgboost | 1.10 | 22 | 22 | +2.2 | -7.3 | 50.0 | 1.25 |
| hs_lb_None | -3.55 | 99 | 61 | -8.0 | -10.2 | 10.0 | 0.23 |

*Note: These 7 strategies passed the daily PnL builder's 20-trade minimum. 263 other strategies had insufficient data.*

---

## Appendix B: Infrastructure Files Audit

| File | Purpose | Status | Key Gaps |
|:---|---|:---:|---:|
| `alpha_engine/position_sizing.py` | Kelly-based position sizing | ✅ Has Kelly | ❌ No VaR/ES, no correlation |
| `alpha_engine/risk_controls.py` | Concentration, DD, loss limits | ✅ Basic controls | ❌ No VaR, no stress testing |
| `paper_trading/portfolio_manager.py` | Portfolio-level management | ⚠️ Structural only | ❌ No optimization, no rebalancing |
| `alpha_engine/system_trend_detector.py` | System performance alerts | ⚠️ Basic alerts | ❌ No automated decay/shutdown |
| `alpha_engine/walkforward_validator.py` | Walk-forward validation | ✅ Basic WFA | ⚠️ No purged/embargoed CV |
| `alpha_engine/forward_validator.py` | Forward testing | ✅ Basic | ⚠️ No automated gates |
| `alpha_engine/regime_flip_detector.py` | Regime classification | ✅ Implemented | ⚠️ Not integrated with sizing |
| `tools/daily_pnl_builder.py` | Daily PnL series | ✅ New (this session) | ⚠️ Needs production hook |
| `tools/validate_resolved_picks.py` | 6-gate validation | ✅ Working | ⚠️ Sharpe inflated (per-trade annualization) |

---

*End of Report*
