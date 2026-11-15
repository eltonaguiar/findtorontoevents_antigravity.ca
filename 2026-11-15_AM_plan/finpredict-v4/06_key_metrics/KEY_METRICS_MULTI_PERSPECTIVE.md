# Key Metrics — Multi-Perspective (Sharpe and beyond)

**Date:** 2026-11-15 (AM)
**Purpose:** What thresholds must a strategy satisfy to earn trust from different capital allocators.

---

## 1. The Metric Dashboard

| Metric | Formula / definition | Why it matters |
|--------|----------------------|----------------|
| **Sharpe ratio** | (Rp − Rf) / σp | Return per unit of total risk |
| **Sortino ratio** | (Rp − Rf) / downside deviation | Return per unit of *bad* risk |
| **Calmar ratio** | CAGR / max drawdown | Return per unit of peak-to-trough pain |
| **Profit factor** | gross wins / gross losses | Only meaningful at n≥100 |
| **Win rate** | wins / (wins+losses) | Meaningless without R:R |
| **Max drawdown** | worst peak-to-trough | Capital-survival limit |
| **Information ratio** | active return / tracking error | vs a benchmark |
| **DSR** (Deflated Sharpe) | corrects Sharpe for # trials | kills multiple-testing artifacts |
| **PBO** (Prob. of Backtest Overfitting) | ≤0.10 target | are the results luck? |
| **Effective N** | correlation-adjusted independent trades | not raw row count |
| **Net expectancy** | (avg win×WR) − (avg loss×(1−WR)) − costs | must be >0 after costs |

---

## 2. Perspective Thresholds

### Pro Investor (retail/angel)
| Metric | Threshold |
|--------|----------|
| Sharpe (annualized) | ≥0.7 to consider; ≥1.0 preferred |
| Max drawdown | ≤20% |
| Win rate | ≥45% with R:R ≥1.5:1 |
| Horizon | ≥12 months sustained |
| Reality check | must beat buy-and-hold after costs; not just "positive" |

### Mutual Fund Manager (institutional)
| Metric | Threshold |
|--------|----------|
| Sharpe | ≥0.5 net relative to benchmark (they monetize beta; alpha is bonus) |
| Information ratio | ≥0.5 (active skill) |
| Tracking error | must be small for index funds; higher for active |
| Load / ER | ≤0.20% for index; justify higher only with real alpha |
| Drawdown | must survive -30% bear without forced liquidation |
| Trust | audited returns, benchmark attribution, regulation |

### Bank's Top Stock Trader (prop/proprietary)
| Metric | Threshold |
|--------|----------|
| Sharpe | ≥1.5-2.0 (they carry leverage; need high risk-adjusted edge) |
| Daily/weekly consistency | near-no-drawdown streaks (Virtu: 1,277/1,278 days green) |
| Win rate (HFT) | may be 51-52% but tiny edge + huge volume |
| Capacity | edge must not erode with size |
| Risk control | pre-committed VaR/stop, margin discipline |

### Risk Manager (the one who says no)
| Metric | Threshold |
|--------|----------|
| Max drawdown | <15-20% hard limit |
| Tail risk (CVaR) | 95% 1-month CVaR must be survivable |
| Leverage | capped; no forced-liquidation path |
| Concentration | single-source HHI <0.5 |
| Correlation | low across sleeves |
| Kill-switch | automatic on gate failure / loss caps |

---

## 3. The Universal Bar (minimum to deploy real money)

A strategy must satisfy ALL (not one):

- **Sharpe ≥1.0** annualized net of costs
- **Max drawdown <20%** (and <8% for allocation core)
- **n_effective ≥200** (≥100 minimum, correlation-adjusted)
- **Net expectancy >0 after all costs**
- **DSR ≥0.95** (deflated; corrects for trials)
- **PBO ≤0.10**
- **Beats the relevant buy-and-hold benchmark** (SPY for equity, BTC-hold for crypto)
- **90-day paper track** before a dollar is deployed

---

## 4. Why Sharpe alone is insufficient

Sharpe rewards *consistency* but hides:
- Tail risk (a 40% crash once a decade can wreck a high-Sharpe strategy)
- Benchmark underperformance (a high Sharpe can still lose to buy-and-hold)
- Multiple-testing bias (a lucky Sharpe survives 100 trials)
- Capacity (Sharpe decays with AUM)

So Sharpe must be paired with **drawdown, benchmark-relative, DSR/PBO, and cost-inclusive expectancy**.

---

## 5. Application to this system

- The **allocation core** (VTI/BND/SGOV) targets Sharpe ~0.30 vs T-bill — acceptable *because it is beta*, not alpha. The correct benchmark is 60/40, not zero.
- Any **alpha claim** must beat its benchmark with Sharpe ≥1.0, DSR ≥0.95, PBO ≤0.10, n_eff ≥200.
- The **risk overlay** enforces the risk-manager thresholds on every live sleeve.
