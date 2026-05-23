# crypto_pairs_arb — Research Optimisations Roadmap

These are concrete, source-cited extensions ranked by expected lift over the
Engle–Granger / GGR baseline currently shipped in
`alpha_engine/crypto_pairs_arb.py`. Each item has a clear acceptance test
and a target follow-up PR window.

## 1. Kalman-Filter time-varying hedge ratio (HIGH LIFT)

**Problem.** The 60-bar rolling OLS β is a discrete approximation of a
slowly-evolving cointegration coefficient. In crypto, β between BTC/ETH
genuinely drifts on multi-week timescales (BTC dominance regime). Rolling
OLS lags the true β by ~½ window — that lag is where the spurious blow-up
trades come from.

**Approach.** Replace `_ols_hedge_ratio` with a 1-D state-space Kalman
filter:

```
β_t = β_{t-1} + w_t          # state evolution, w ~ N(0, Q)
ln(A_t) = β_t · ln(B_t) + v_t # observation, v ~ N(0, R)
```

Initialise β_0 from full-window OLS, then update bar-by-bar. Tunable
Q/R via likelihood maximisation on training set.

**Refs.**
- Chan, E. P. (2013). *Algorithmic Trading*, ch. 3, "Mean Reversion of Stocks and ETFs", Kalman-filter hedge-ratio code (Wiley, pp. 75–82).
- Triantafyllopoulos & Montana (2011). *Dynamic Modeling of Mean-Reverting Spreads for Statistical Arbitrage*. Computational Management Science 8(1–2): 23–49 — direct Kalman application to pairs.
- de Moura, Pizzinga, Zubelli (2016). A pairs trading strategy based on linear state space models and the Kalman filter. *Quantitative Finance* 16(10): 1559–1573.

**Acceptance.** On the same synthetic backtest harness in
`__main__`, Kalman β must reduce avg adverse excursion (per-leg drawdown
between entry and exit) by ≥20% vs rolling OLS without dropping signal
count below 80% of baseline.

**Target PR window.** 2026-05-26.

## 2. Copula-based entry filter (HIGH LIFT, paper-backed for crypto)

**Problem.** z-score entry assumes Gaussian spread innovations. Crypto
spreads have fat-tailed asymmetric tail dependence — a z=2 in a Gaussian
world is materially different from a z=2 when the lower tail of the
spread distribution is heavy.

**Approach.** Fit a Student-t or Clayton copula on the pair's empirical
log-returns (training window), then trade on the *conditional* CDF
mispricing:

```
mispricing_t = P(U_A ≤ u_a | U_B = u_b) − 0.5
```

Enter when `|mispricing_t| > 0.45` (i.e. ≥ 95th conditional pct).
Replaces the linear-spread z-score with a tail-aware non-parametric
divergence signal.

**Refs.**
- Liew, R. Q. & Wu, Y. (2013). Pairs trading: A copula approach. *Journal of Derivatives & Hedge Funds* 19(1): 12–30.
- da Silva, A., Lee, W. (2016). Pairs trading using empirical copula. (preprint, SSRN id 2782059).
- Springer (2024) cited in `alpha_engine/INSTITUTIONAL_SHORT_TERM_STRATEGIES.md` — *Copula-based Trading of Cointegrated Crypto Pairs* — reports 79–100% WR on 81k crypto data points (as cross-validation of the approach for our exact asset class).

**Acceptance.** Real ledger A/B over 30 days with 50/50 split between
copula-gated and pure-z entries — copula entries must show ≥ +10pp WR
or ≥ +0.4 PF lift, n ≥ 30 each arm.

**Target PR window.** 2026-06-09 (after Kalman lands).

## 3. Regime-detection ML feature (MEDIUM LIFT)

**Problem.** Pairs trading dies catastrophically in *cointegration breaks*
— typically driven by an idiosyncratic shock (chain hack, regulatory
announcement, exchange listing change, BTC-halving regime shift). The
half-life filter detects this *after* the spread has already diverged.
We want a forward-looking gate.

**Approach.** Train a binary classifier (gradient-boosted trees,
sklearn-compatible — repo already imports `flaml`/`feature-engine`) to
predict P(spread half-life will breach 30 in next 24h) from features:
* Realised correlation regime (HMM state from `regime_terminal.md`).
* Funding-rate divergence between the two perps.
* On-chain transfer concentration (whale wallets) per leg (Glassnode/Arkham).
* Recent news-flow asymmetry (LunarCrush sentiment z-diff).
* Implied vol gap (Deribit options for BTC/ETH).

If P(break) > 0.6, suppress the entry on that pair only. Acts as the
*third* gate (cointegration → half-life → break-risk).

**Refs.**
- López de Prado, M. (2018). *Advances in Financial Machine Learning*, ch. 7 "Cross-Validation in Finance" + ch. 13 "Backtesting on Synthetic Data" — for purged-CV training discipline (already partially in repo `alpha_engine/integrations/purged_cv_core.py`).
- Krauss, C., Do, X. A., & Huck, N. (2017). Deep neural networks, gradient-boosted trees, random forests: Statistical arbitrage on the S&P 500. *European Journal of Operational Research* 259(2): 689–702 — direct GBT-on-pairs application.
- Sarmento, S. M. & Horta, N. (2020). Enhancing a pairs trading strategy with the application of machine learning. *Expert Systems with Applications* 158: 113490 — covers feature engineering for cointegration-break prediction.

**Acceptance.** Out-of-sample 5-fold purged-CV AUROC ≥ 0.65 on the
break-vs-no-break label; gate must improve live PF by ≥ +0.15 with
signal count drop ≤ 25%.

**Target PR window.** 2026-06-23.

## 4. Cross-Pair Portfolio Allocation (LOW EFFORT, MEDIUM LIFT)

**Problem.** Currently we fire each pair independently with equal sizing.
When BTC/ETH and BTC/BNB simultaneously fire `z>2`, they're not
independent bets — both are essentially BTC-rich-vs-altcoins.

**Approach.** Apply skfolio mean-variance / HRP allocation
(`alpha_engine/integrations/skfolio_*` already in repo) to a portfolio
of cointegrated pairs, sizing each pair's notional inversely to spread
return correlation across pairs. Hard cap: ≤ 1× total CRYPTO sleeve
nominal exposure regardless of n_pairs firing.

**Refs.**
- López de Prado, M. (2016). Building diversified portfolios that outperform out of sample. *Journal of Portfolio Management* 42(4): 59–69 — the original HRP paper.
- skfolio docs: `HierarchicalRiskParity`, `MeanVariance`.

**Acceptance.** Realised Sharpe of the pair portfolio ≥ 1.3× the
equal-weighted baseline on 90-day forward run.

**Target PR window.** 2026-07-07.

## 5. Multi-leg / triangular (RESEARCH STAGE)

**Problem.** BTC, ETH, SOL collectively form a 3-asset cointegrated
system; a 2-leg pair only captures the lowest-rank reversion mode.

**Approach.** Johansen-style multivariate cointegration (skip statsmodels:
implement minimal eigen-decomposition of the VAR companion matrix
manually with `np.linalg.eig`) → trade the *first* cointegrating vector,
which is by construction the most stationary linear combination.

**Refs.**
- Johansen, S. (1991). Estimation and hypothesis testing of cointegration vectors in Gaussian vector autoregressive models. *Econometrica* 59(6): 1551–1580.
- Dunis, C. L. & Ho, R. (2005). Cointegration portfolios of European equities for index tracking and market neutral strategies. *Journal of Asset Management* 6(1): 33–52 — multi-asset cointegration applied to portfolio construction.

**Acceptance.** Walk-forward on synthetic 3-asset cointegrated system
must dominate every 2-leg subset by Sharpe.

**Target PR window.** 2026-07-21 (research spike, not committed).
