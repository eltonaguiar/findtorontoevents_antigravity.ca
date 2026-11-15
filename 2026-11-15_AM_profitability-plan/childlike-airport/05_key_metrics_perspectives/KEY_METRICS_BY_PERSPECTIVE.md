# 05 — Key Metrics That Must Be Satisfied (Multi-Perspective)

**Rule:** no single metric is sufficient. Require **net-of-cost, benchmark-relative, risk-aware, statistically valid** evidence. Thresholds below are common *gates/targets* (context-dependent); failing any critical gate ⇒ not money-ready.

## A. Metric glossary (core)
| Metric | What it measures | Notes / pitfalls |
|---|---|---|
| **Net return / CAGR** | Growth after all costs | Must compare to correct benchmark & horizon |
| **Alpha / beta / tracking error** | Excess vs benchmark & factor exposure | “Profit” can be pure beta |
| **Sharpe** | (Return − Rf) / volatility | Sensitive to horizon, non-normality, serial corr; use consistent sampling |
| **Sortino** | Return / downside deviation | Focuses on harmful vol; still assumption-sensitive |
| **Calmar** | CAGR / Max Drawdown | Period-dependent |
| **Max Drawdown (MDD), time-underwater** | Peak-to-trough loss & recovery time | Survival-critical |
| **Volatility** | Dispersion of returns | Annualization must match frequency |
| **CVaR / ES (e.g. 95%)** | Tail loss severity | Complements MDD |
| **Profit Factor (PF)** | Gross wins / gross losses | Unstable on small n; meaningless if costs/leakage wrong |
| **Win rate & payoff ratio** | Hit rate vs avg win/loss | Expectancy = p*W − (1−p)*L − costs must be > 0 |
| **Expectancy (net)** | Avg $/trade or % after costs | Primary trading edge sanity check |
| **Hit rate / IC (info coefficient)** | Predictive ranking skill | IC≈0 with high turnover ⇒ no edge (and costs kill) |
| **Turnover & cost drag** | Trading intensity & friction | Can erase gross alpha |
| **Capacity / slippage** | Scalability | Backtests often assume free liquidity |
| **Stability** | Subperiod/regime/OOS consistency | One-regime wonders fail live |
| **n / effective-N** | Sample & independence | Clustered bets inflate n |
| **DSR, PBO/CSCV** | Multiple-testing/overfit controls | Essential when many trials/params |
| **Ulcer/Recovery, streaks** | Pain & path risk | Behavioral/mandate limits |

## B. Perspective-based gates

### 1) Quant researcher (is there signal?)
- **Must:** point-in-time/leak-safe data; reproducible pipeline; net expectancy > 0; **benchmark-relative** improvement.
- **Stats:** OOS/walk-forward positive; **DSR/PBO** acceptable given trial count; effective-N sufficient; IC/stability not regime-accidental.
- **Red flags:** PF/Sharpe collapses after costs, next-bar/intrabar realism, or parameter nudges.

### 2) Professional portfolio manager / trader (can we run it?)
- **Must:** positive expectancy net of realistic execution; acceptable **MDD, vol, CVaR**; scalable capacity; clear thesis & exit rules.
- **Targets (illustrative, strategy-dependent):** Sharpe often judged >1 as “good” in context (not sufficient), Sortino strong, Calmar robust, stable rolling metrics; concentration within limits.
- **Red flags:** edge only in one regime, path risk too high for mandate, execution shortfall dominates.

### 3) Mutual fund manager (fiduciary, benchmarked, cost-sensitive)
- **Must:** **net-of-fee** outperformance vs stated benchmark over meaningful horizons; tracking error/active share consistent with mandate; liquidity/daily NAV constraints respected.
- **Metrics:** alpha, information ratio (alpha/TE), downside capture, expense/turnover impact, consistency across rolling periods; compliance with diversification/limits.
- **Reality:** persistent net alpha is rare (SPIVA-like evidence); process, cost control, and risk management are central.

### 4) Bank’s top trader / prop-style desk (PnL with strict risk)
- **Must:** risk-adjusted PnL within **VaR/ES, stress, and drawdown limits**; liquidity-aware sizing; clean limit/mandate adherence.
- **Metrics:** daily/MTD/YTD P&L, Sharpe/Sortino (desk-specific), hit rate vs payoff, max loss per trade/day, utilization, stress P&L, tail behavior.
- **Red flags:** concentrated/illiquid bets, limit breaches, unexplainable PnL swings, model/mark issues.

### 5) Risk manager / compliance / allocator (should real money trust it?)
- **Must:** independent verification, reconciled marks, defined limits & kill-switches, scenario/stress results, governance (model change log, approvals).
- **Metrics:** MDD/CVaR/VaR (with limits), leverage/gross-net exposure, liquidity horizon, correlation/concentration, operational error rates, benchmark & mandate compliance.
- **Promotion:** only after forward/paper evidence with controls — never on backtest alone.

## C. Suggested minimum promotion gates (pre-registered, adapt per sleeve)
| Gate | Target (illustrative) | Rationale |
|---|---|---|
| Sample | n ≥ 100 trades (≥500 preferred for noisy/crypto); effective-N adequate | Reduce noise/selection luck |
| Net expectancy | > 0 after all costs | Economic viability |
| Profit Factor | ≥ 1.5 (≥1.2 contextual) **and stable** | Buffer over frictions |
| Sharpe | ≥ 1.0 (net, consistent calc) | Risk-adjusted return |
| Sortino / Calmar | Sortino ≥ 1.0; Calmar ≥ 0.5 (contextual) | Downside/path efficiency |
| MDD / tail | MDD < 20% (prefer <15%); CVaR within mandate | Survivability |
| Benchmark | Net outperformance vs correct hurdle (risk-matched) | Alpha vs beta/cash |
| Validity | PBO < 0.3; DSR > 0.95 (effective-N/trial-aware) | Overfit/multiple-testing control |
| Stability | Positive in OOS/walk-forward & key subperiods; limited decay | Robustness |
| Forward | Paper/live-shadow meets gates over defined window | Execution reality |
| Ops | Reconciled, fresh data, kill-switch tested, limits enforced | Trust & control |

## D. How to read “good” numbers (anti-patterns)
- High Sharpe on tiny n / short window / single regime ⇒ **likely noise or overfit**.
- Gross PF>2 but net<1 ⇒ **cost illusion**.
- Beats cash but lags SPY with higher DD ⇒ **bad equity risk-adjusted proposition**.
- Tournament/leaderboard WR without net, intrabar-realistic, capacity-aware accounting ⇒ **non-sizing**.
