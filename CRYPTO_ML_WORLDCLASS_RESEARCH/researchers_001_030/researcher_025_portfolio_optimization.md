# Researcher Profile: Dr. James Miller

## Persona
- **Title:** Portfolio Optimization and Asset Allocation Lead
- **Expertise:** Mean-variance optimization, Black-Litterman, risk parity, factor models
- **Years Experience:** 15
- **Background:** PhD Wharton Finance, former portfolio manager at PIMCO, now applies quantitative allocation to crypto.

## Research Scope
**Primary Question:** How do top funds construct and optimize crypto portfolios from ML predictions to maximize risk-adjusted returns?

**Target Systems/Areas:**
- Mean-variance (Markowitz) with crypto constraints
- Black-Litterman model (views from ML predictions)
- Risk parity across crypto assets
- Factor-based allocation (momentum, value, volatility)
- Hierarchical risk parity (HRP)
- CVaR optimization

## Methodology
1. **Sources:** Full codebase audit of `alpha_engine/`, `ml_battleground/`, `crypto_ml_edge/`, `scripts/`, and supporting modules.
2. **Extraction:** Reviewed all position sizing functions, portfolio construction classes, cost models, correlation handling, rebalancing logic, and risk constraints.
3. **Analysis:** Compared implemented methods against institutional best practices; identified gaps and strengths.
4. **Validation:** Cross-referenced config parameters, default values, and control flow across all subsystems.

---

## Key Findings (Codebase Audit)

### Finding 1: Multi-Method Position Sizing (STRONG)

**Files:**
- `alpha_engine/backtest/position_sizing.py` -- `PositionSizer` class
- `scripts/position_sizer.py` -- Half-Kelly + EWMA Vol + Regime modulation
- `scripts/dynamic_position_sizer.py` -- `DynamicPositionSizer` class
- `ml_battleground/shared/risk_manager.py` -- Fractional Kelly (0.25x)
- `crypto_ml_edge/risk.py` -- ATR-based fractional Kelly

**What exists:**
The codebase implements **5 distinct position sizing methods**, each tailored to its subsystem:

| Method | File | Fraction | Max Position | Notes |
|--------|------|----------|-------------|-------|
| Composite (Kelly + Vol + Fixed Risk + EW) | `alpha_engine/backtest/position_sizing.py` | Configurable (default 0.25 Kelly) | `MAX_POSITION_PCT` from config | Takes minimum of risk-based and vol-based (conservative) |
| Half-Kelly + EWMA Vol + Regime | `scripts/position_sizer.py` | 0.50 Kelly | 15% | Includes regime modifier (0.3-1.2x), alpha decay detection, Almgren-Chriss slippage |
| Quarter-Kelly + Vol Weighting | `scripts/dynamic_position_sizer.py` | 0.25 Kelly | 15% | Blends 60% vol-sizing + 40% Kelly-sizing |
| Fractional Kelly (0.25x) | `ml_battleground/shared/risk_manager.py` | 0.25 Kelly | 2% risk per trade | Circuit breaker at 10% drawdown, max 5 concurrent |
| ATR-Fractional Kelly (0.15x) | `crypto_ml_edge/risk.py` | 0.15 Kelly | 5% of capital | ATR-volatility adjusted; confidence-driven edge: `2*conf - 1` |

**Assessment:** STRONG. Multiple Kelly variants with volatility adjustment is institutional-grade. The `alpha_engine` composite method that takes the **minimum** of risk-based and vol-based sizing is particularly conservative and well-designed. The `crypto_ml_edge` ATR-based sizing with 15% Kelly is well-documented with academic citations (Kelly 1956, Thorp 2008, Vince 1992).

**Gap:** No unified position sizer shared across all subsystems. Each module has its own implementation with different fraction defaults (0.15, 0.25, 0.50). This inconsistency could cause confusion in cross-system portfolio aggregation.

---

### Finding 2: Black-Litterman + Risk Parity Portfolio Optimization (PRESENT)

**File:** `scripts/portfolio_optimizer.py`

**What exists:**
A complete Black-Litterman + Risk Parity + CVaR optimization pipeline using `riskfolio-lib`:

- **Black-Litterman:** Combines market equilibrium returns with ML signal "views" (from active signals API). Uses `delta=2.5` risk aversion, daily risk-free rate from annual. P/Q matrices constructed from signal strength mapped to expected returns. CVaR-constrained Sharpe maximization.
- **Risk Parity:** Bridgewater All-Weather style -- each asset contributes equally to portfolio risk. Uses `rp_optimization()` from riskfolio-lib with Classic MV risk measure.
- **CVaR Computation:** `compute_portfolio_risk()` calculates VaR-95, CVaR-95, max drawdown, Sharpe, annual return/vol for each allocation method.
- **Selection Logic:** Compares equal-weight, risk-parity, and Black-Litterman by Sharpe ratio. Selects highest Sharpe automatically.

**Assessment:** GOOD implementation of institutional methods. The automatic fallback to equal-weight when `riskfolio-lib` is unavailable is practical. However, the optimizer is in `scripts/` (a utility layer) and does not directly feed into the `alpha_engine` scanner or `crypto_ml_edge` scanner pipelines. It posts results to a PHP API, suggesting it runs on a separate schedule.

**Gap:** No Hierarchical Risk Parity (HRP) implementation exists despite being referenced in research documents. HRP would be valuable for crypto where covariance matrices are often unstable/singular. The `riskfolio-lib` dependency supports HRP (`port.hrp_optimization()`), so this is a low-effort addition.

---

### Finding 3: Correlation/Covariance Handling (PARTIAL)

**Files:**
- `scripts/corr_pruner.py` -- Greedy correlation pruning (threshold 0.70)
- `alpha_engine/scripts/prune_correlated_picks.py` -- SQL-based correlation pruning (threshold 0.75)
- `scripts/position_sizer.py` -- `check_factor_exposure()` via PCA eigenvalue analysis
- `scripts/dynamic_position_sizer.py` -- `correlation_adjusted_size()` portfolio variance check
- `alpha_engine/ensemble/signal_combiner.py` -- `compute_strategy_diversity()` returns correlation matrix
- `alpha_engine/config.py` -- `MAX_CORRELATED_EXPOSURE = 0.30` (30% same asset class)

**What exists:**
- **Correlation Pruning:** Two independent pruners remove highly correlated picks. `corr_pruner.py` fetches 3-month prices, computes `np.corrcoef`, and greedily removes correlated assets (>0.70 threshold, keeping higher-ranked). `prune_correlated_picks.py` does the same via MySQL with a 0.75 threshold.
- **Factor Exposure Check:** `check_factor_exposure()` in `position_sizer.py` performs PCA on the correlation matrix and checks if the top eigenvector explains >30% of variance (too concentrated on one factor).
- **Portfolio Variance Adjustment:** `DynamicPositionSizer.correlation_adjusted_size()` computes full portfolio variance from position sizes and a correlation matrix, then scales all positions down if portfolio vol exceeds target.
- **Sector/Asset Class Caps:** `alpha_engine/config.py` enforces `MAX_CORRELATED_EXPOSURE = 0.30` and `alpha_engine/backtest/portfolio.py` enforces `max_sector_pct = 0.25`.

**Assessment:** PARTIAL. Multiple correlation-aware components exist but they are scattered and not integrated into a single covariance-aware optimization. The greedy pruning approach is simple but suboptimal -- it doesn't consider that removing one asset might make another pair acceptable. The PCA factor exposure check is a nice innovation.

**Gap:** No rolling covariance estimation (DCC-GARCH, exponentially weighted, or shrinkage estimators like Ledoit-Wolf). Crypto correlations are notoriously unstable, spiking to near-1.0 during crashes. Static 3-month correlation matrices are insufficient. Need DCC or EWMA covariance with decay ~0.97.

---

### Finding 4: Drawdown Constraints and Risk Budgeting (STRONG)

**Files:**
- `alpha_engine/backtest/portfolio.py` -- `max_drawdown_halt = 0.15` (15% circuit breaker)
- `ml_battleground/shared/risk_manager.py` -- `MAX_DRAWDOWN = 0.10` (10% circuit breaker)
- `scripts/position_sizer.py` -- `drawdown_position_scale()` continuous scaling + `cvar_position_limit()`
- `alpha_engine/config.py` -- `MAX_TOTAL_EXPOSURE = 0.80`, `MAX_CORRELATED_EXPOSURE = 0.30`

**What exists:**
- **Binary Circuit Breakers:** `PortfolioConstructor` halts all trading and closes all positions when drawdown exceeds 15%. `ml_battleground` triggers at 10%.
- **Continuous Drawdown Scaling:** `drawdown_position_scale()` in `position_sizer.py` uses exponential decay: `scale = e^(-0.08 * dd%)`. This smoothly reduces position sizes as drawdown increases (5% DD -> 85% size, 10% DD -> 60%, 15% DD -> 40%, 20%+ -> 25% minimum).
- **CVaR Position Limiting:** `cvar_position_limit()` scales positions when portfolio CVaR exceeds threshold (default 10% daily). Minimum scale is 25%.
- **Exposure Caps:** Total portfolio exposure capped at 80%. Correlated exposure (same asset class) capped at 30%. Individual position capped at 15% (`alpha_engine`) or 5% (`crypto_ml_edge`).

**Assessment:** STRONG. The combination of binary circuit breakers (for catastrophic events) with continuous scaling (for gradual deterioration) is institutional best practice. The CVaR-based scaling is particularly sophisticated. The multi-layer caps (position, sector, total exposure, drawdown) provide defense-in-depth.

**Gap:** No volatility-of-volatility (vol-of-vol) scaling. During regime transitions, realized vol itself becomes unstable. A GARCH(1,1) or exponential vol-of-vol metric could provide earlier warning than drawdown-based measures.

---

### Finding 5: Rebalancing Logic (GOOD)

**Files:**
- `alpha_engine/backtest/engine.py` -- `rebalance_frequency` parameter (daily/weekly/monthly)
- `alpha_engine/backtest/portfolio.py` -- `max_daily_turnover_pct = 0.20` (20% daily turnover cap)
- `alpha_engine/ensemble/regime_allocator.py` -- Regime-dependent strategy weight shifting

**What exists:**
- **Frequency Options:** BacktestEngine supports daily, weekly, and monthly rebalancing. Weekly is the default (Mondays).
- **Turnover Constraint:** `PortfolioConstructor` enforces 20% daily turnover cap, preventing excessive trading.
- **Regime-Adaptive Rebalancing:** `RegimeAllocator` shifts strategy weights based on market regime (risk_on/neutral/risk_off/crisis). In crisis mode, momentum and breakout go to 0% while quality and dividends scale up to 30% and 25% respectively. A DXY filter further shifts growth to value when the dollar is strong.
- **Signal Combination:** `SignalCombiner` supports equal-weight, performance-weighted, and rank-average signal combining. Diversity-weighted (low correlation boost) is mentioned but not fully implemented.

**Assessment:** GOOD. The regime-based allocation shifting is a key differentiator. The 4-regime model (risk_on/neutral/risk_off/crisis) with soft probability blending (`compute_blended_weights`) is more sophisticated than binary switches. Turnover constraint prevents cost-destroying overtrading.

**Gap:** No calendar-based rebalancing optimization (e.g., avoiding rebalancing during high-vol events, month-end effects). No partial rebalancing (only rebalance positions that deviate >X% from target, known as "bandwidth rebalancing").

---

### Finding 6: Transaction Cost Optimization (STRONG)

**Files:**
- `alpha_engine/backtest/costs.py` -- `CostModel` class with IB, Questrade, and zero-cost presets
- `alpha_engine/transaction_costs.py` -- Per-asset-class cost models (6 tiers)
- `ml_battleground/shared/cost_model.py` -- Tiered crypto costs (tier1/2/3)
- `crypto_ml_edge/config.py` -- Per-pair slippage maps
- `scripts/position_sizer.py` -- Almgren-Chriss inspired slippage model

**What exists:**
- **Multi-Broker Cost Models:** `CostModel` class models commission, slippage, spread, borrow cost, and exchange fees. Presets for Interactive Brokers and Questrade Canada (including 1.75% forex fee and ECN fees).
- **Per-Asset-Class Costs:** 6 cost tiers from forex (0.03% round-trip) to penny stocks (1.50% round-trip). Crypto splits into spot (0.25%), altcoin (0.70%), and meme (1.00%).
- **Per-Pair Slippage:** `crypto_ml_edge/config.py` has calibrated slippage per Binance pair (BTC 5bps, alts 7-10bps).
- **Cost-Adjusted Kelly:** `transaction_costs.py` provides `kelly_position_size()` that adjusts win/loss for costs before computing Kelly. Also provides `adjusted_win_rate()` and `net_expectancy()` functions.
- **TP Adjustment:** `adjust_tp_for_costs()` widens take-profit targets to ensure net profitability after costs.
- **Market Impact:** `estimate_slippage()` in `position_sizer.py` implements Almgren-Chriss temporary + permanent impact with participation-rate scaling and volatility-proportional permanent impact.

**Assessment:** STRONG. This is one of the most thorough cost implementations I've seen in an open codebase. The TP adjustment for costs is a critical practical detail that many systems miss. The Almgren-Chriss slippage model, while simplified, provides useful market-impact awareness.

**Gap:** No execution optimization (TWAP/VWAP scheduling, optimal execution algorithms). For the position sizes involved ($10K capital), this is acceptable -- market impact is minimal. Would become important at >$100K capital or in illiquid altcoins.

---

### Finding 7: Diversification Across Strategies and Assets (GOOD)

**Files:**
- `alpha_engine/config.py` -- 34 crypto + 10 forex + 20 equity symbols; `MAX_PICKS_PER_STRATEGY = 3`
- `alpha_engine/ensemble/regime_allocator.py` -- 9 strategy types weighted by regime
- `alpha_engine/ensemble/signal_combiner.py` -- Multi-strategy signal combining
- `alpha_engine/backtest/portfolio.py` -- `compute_target_weights()` with 4 methods

**What exists:**
- **Asset Class Diversification:** Portfolio spans crypto (34 symbols across major/alt/DeFi/meme), forex (10 major/cross pairs), and equities (20 stocks/ETFs/penny). Three distinct asset classes.
- **Strategy Diversification:** 9 strategy categories (momentum, trend, breakout, mean_reversion, earnings_drift, quality, value, dividend, ml) with regime-dependent allocation. Individual strategies capped at 3 picks each.
- **Portfolio Construction Methods:** 4 target weight methods: equal_weight, score_weighted, risk_weighted (inverse vol), and risk_parity (equalize risk contribution). Max 30 positions.
- **Max Position Caps:** 5% per position (`alpha_engine/backtest/portfolio.py`), 25% per sector, 15% max (`alpha_engine/config.py`).

**Assessment:** GOOD diversification architecture. The 3-asset-class, 9-strategy-category framework with regime-dependent allocation is well-structured. The 3-picks-per-strategy cap prevents any single signal source from dominating.

**Gap:** No formal diversification ratio tracking (e.g., Choueifaty's diversification ratio = weighted vol / portfolio vol). No minimum number of active strategies constraint. During crisis mode, only 4 of 9 strategies have non-zero weight -- portfolio could become concentrated.

---

## Summary Assessment

| Category | Grade | Key Strength | Key Gap |
|----------|-------|-------------|---------|
| Position Sizing | A- | 5 methods across subsystems; composite min(risk, vol) approach | No unified sizer; inconsistent Kelly fractions |
| Portfolio Optimization | B+ | Black-Litterman + Risk Parity + CVaR via riskfolio-lib | No HRP; optimizer not integrated into scanner pipeline |
| Correlation Handling | B- | Greedy pruning + PCA factor check + sector caps | No dynamic covariance (DCC/EWMA); static 3mo windows |
| Drawdown Constraints | A | Binary breakers + continuous exponential scaling + CVaR limits | No vol-of-vol early warning |
| Rebalancing | B+ | Regime-adaptive + turnover constraints + 3 frequency options | No bandwidth rebalancing; no calendar awareness |
| Transaction Costs | A | 6 asset-class tiers + Almgren-Chriss + cost-adjusted Kelly/TP | No TWAP/VWAP execution (acceptable at current scale) |
| Diversification | B+ | 3 asset classes, 9 strategies, regime-dependent allocation | No diversification ratio tracking |

**Overall Grade: B+ (Strong foundation, institutional-grade in cost modeling and risk controls, gaps in covariance dynamics and HRP)**

## Actionable Recommendations

### High Priority (1-2 weeks)
1. **Add HRP to `scripts/portfolio_optimizer.py`:** `riskfolio-lib` already supports `port.hrp_optimization()`. Add as third optimization method alongside BL and risk parity. HRP is more stable than mean-variance for crypto's noisy covariance matrices.
2. **Unify Kelly fraction across subsystems:** Standardize on 0.25 Kelly (quarter-Kelly) everywhere. Current range of 0.15-0.50 creates inconsistent risk profiles.
3. **Integrate portfolio optimizer into scanner pipeline:** Currently `scripts/portfolio_optimizer.py` posts to PHP API separately. Should feed weights directly into `alpha_engine/scanner.py` via a shared config or database.

### Medium Priority (1 month)
4. **Implement EWMA covariance with decay 0.97:** Replace static 3-month correlation windows with exponentially weighted covariance. This captures regime-dependent correlation spikes (crypto correlations spike to ~0.95 during crashes).
5. **Add bandwidth rebalancing:** Only rebalance positions deviating >5% from target weight. Reduces turnover by ~40% in typical conditions.
6. **Track diversification ratio:** Implement `DR = sum(w_i * sigma_i) / sigma_portfolio`. When DR < 1.2, portfolio is under-diversified.

### Low Priority (3 months)
7. **Add vol-of-vol scaling:** Use GARCH(1,1) on 20-day realized vol to detect vol regime transitions before drawdown occurs.
8. **Implement Ledoit-Wolf shrinkage estimator:** For covariance matrix estimation with small sample sizes (common when adding new crypto assets).
9. **Add execution cost optimization:** For positions >$50K, implement basic TWAP splitting to reduce market impact.

## References
- Kelly, J.L. (1956). "A New Interpretation of Information Rate." Bell System Technical Journal.
- Thorp, E.O. (2008). "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market." Handbook of Asset and Liability Management.
- Black, F. & Litterman, R. (1992). "Global Portfolio Optimization." Financial Analysts Journal.
- Lopez de Prado, M. (2016). "Building Diversified Portfolios that Outperform Out of Sample." Journal of Portfolio Management (HRP).
- Almgren, R. & Chriss, N. (2001). "Optimal Execution of Portfolio Transactions." Journal of Risk.
- Choueifaty, Y. & Coignard, Y. (2008). "Toward Maximum Diversification." Journal of Portfolio Management.
- Ledoit, O. & Wolf, M. (2004). "Honey, I Shrunk the Sample Covariance Matrix." Journal of Portfolio Management.
- Vince, R. (1992). "The Mathematics of Money Management."

---
*Researcher ID: 025* | *Status: Complete* | *Audit Date: 2026-02-24*
