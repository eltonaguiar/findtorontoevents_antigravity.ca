# Quant libraries integration — what each buys us, per asset class

**Date:** 2026-04-20
**Landing:** 5 open-source quant libraries integrated as read-only analytics tools; 3 parallel web-research critiques of how to use them maximally.

Mercury proposed a 6-step workflow (`LSTM → arch.bootstrap → skfolio → pypbo BO`). Research surfaced that his framing misidentifies `pypbo` (it's **Probabilistic Backtest Overfitting**, not Bayesian Optimisation) and only touches ~15% of `skfolio`'s actual feature surface. Corrected workflow + full feature inventories are now on main.

---

## Library-by-library — what it is, what it buys us, how it helps each asset class

### 1. `pypbo` — Probabilistic Backtest Overfitting (Bailey & Lopez de Prado)

**What it actually is:** NOT Bayesian optimisation. It's a suite of statistical validation tools:
- **`pbo()`** — Probability of Backtest Overfitting via Combinatorial Symmetric CV (CSCV)
- **`psr()`** — Probabilistic Sharpe Ratio (accounts for skew/kurtosis)
- **`dsr()`** — Deflated Sharpe Ratio (haircut for multiple-testing across N strategies)
- **`minTRL` / `minBTL`** — Minimum Track Record / Backtest Length for statistical confidence

**Empirical result on our 3,500-pick history:**
| Feed | Raw Sharpe | PSR vs 0 | PSR vs 1 | Interpretation |
|---|---|---|---|---|
| HC (grade-a+b) | **5.26** | 0.969 | 0.934 | Strong edge, tiny sample (n=28) |
| Smart Picks | 3.44 | 1.000 | 0.999 | **Most robust feed by PSR** |
| All baseline | -1.13 | 0.000 | 0.000 | Confirms pool-level net-negative |

**Per-asset leverage:**
- **CRYPTO**: Raw Sharpe -2.19, PSR 0.000 → drags baseline; the HC + Smart gates correctly invert this
- **EQUITY**: Raw Sharpe +2.07 but DSR collapses to ~0 after multi-testing haircut (57 strategies tested) → edge not robust to selection bias
- **BOND**: Same pattern as EQUITY at n=5 strategies — small sample
- **FOREX/COMMODITY/ETF**: PSR near 0 → no demonstrated edge yet on current data

**Decision gate we can now enforce:** `PSR ≥ 0.95 AND DSR ≥ 0.95 AND PBO ≤ 0.5` → SHIP. Otherwise paper-flag or reject.

**What Mercury actually wanted (Bayesian opt over hyperparameters):** use Optuna or scikit-optimize separately. Not pypbo.

---

### 2. `skfolio` — Portfolio / signal-selection + CV framework

**What Mercury mentioned (~15% of the library):** MeanVariance, RiskParity, Black-Litterman optimisation.

**What Mercury missed (the other 85%):**
- **CombinatorialPurgedCV** — López-de-Prado-grade walk-forward with purge/embargo; yields PBO natively. Direct upgrade to our Phase 4 / Phase 2 backfill.
- **Risk measures beyond variance:** CVaR, CDaR, EVaR, MAD, Worst Realization, Omega — **critical** for crypto's heavy tails where variance underestimates joint drawdowns.
- **11 covariance estimators:** LedoitWolf, OAS, Denoising, Gerber, Graphical Lasso, Implied — pick the one suited to each asset class.
- **Hierarchical Risk Parity (HRP) / HERC / NCO:** cluster strategies by return correlation → auto-identify redundant strategies.
- **Vine copulas** for tail-dependent asset modeling (crypto-specific win).
- **EntropyPooling / OpinionPooling:** principled Bayesian view injection (replaces our ad-hoc regime multipliers).

**Signal-selection remix (non-obvious):** skfolio is built for portfolio weight allocation. Our repo is signal-selection. But the math maps: feed slots ≈ portfolio slots. HRP on return-correlation matrix ≈ "which strategies are redundant?" → auto-prune.

**Empirical result on walk-forward validation:**
- 6 of 191 source systems passed filters (n≥30 + positive PnL)
- **Top stable (OOS Sharpe ≥ IS Sharpe):** `stocks_competition` (IS 2.01 / OOS 2.71, n=170), `baby_strats_forward` (IS 2.24 / OOS 2.02, n=171)
- **Top overfit (IS-OOS gap > 50%):** `non_crypto_consensus` (IS 2.39 / OOS -0.93 — **edge inverted OOS**), `kimi_riseoftheclaw` (IS 1.68 / OOS -0.15)

The `non_crypto_consensus` flag drove today's hard-retirement commit (`41a79c2c1`).

**Per-asset leverage:**
- **CRYPTO**: CVaR/CDaR risk measures + Gumbel copula tail modeling
- **EQUITY**: CombinatorialPurgedCV on stocks_competition-style strategies (already validated OOS)
- **ETF/BOND**: NCO for cluster-aware feed selection once BOND data flows (see FRED below)
- **FOREX/COMMODITY**: Shrunk covariance (LedoitWolf) for the ~30-symbol universe

---

### 3. `arch.bootstrap` — Block-bootstrap CIs on metrics

**Full features in use:**
- **`MovingBlockBootstrap` + `StationaryBootstrap`** — time-series-aware resampling
- **`optimal_block_length()`** — auto-size blocks via Politis-White
- **BCa (bias-corrected accelerated) CIs** — the gold standard for skewed metrics (Sharpe on crypto)
- **Multi-statistic joint CIs** — `func` returns an array → CIs on `[PF, Sharpe, WR, MaxDD]` in one pass
- **Model Confidence Set (MCS)** — Hansen-Lunde formal multiple-testing; prunes strategy zoo to provably-non-dominated set

**Empirical PF 95% CIs from our 3,500 closed picks:**
| Feed | Point PF | 95% CI | Verdict |
|---|---|---|---|
| **HC** | 2.532 | [1.811, 3.836] | **Edge statistically distinguishable from random** |
| CRYPTO (all) | 1.17 | [1.03, 1.35] | Edge confirmed |
| EQUITY | 1.28 | [1.06, 1.56] | Edge confirmed |
| Verified Alpha | 0.858 | [0.609, 1.187] | **CI includes 1.0 — no detectable edge** |
| FOREX | 0.855 | [0.399, 2.004] | Inconclusive |
| ETF | 1.007 | [0.491, 1.908] | Inconclusive |
| COMMODITY | 1.025 | [0.573, 1.830] | Inconclusive |

This is the exact banner material for Phase 4: we can now say "HC PF 2.53, 95% CI [1.81, 3.84]" with statistical honesty.

---

### 4. `fredapi` — BOND data gap filler

**Before:** BOND asset class was a data desert (n=12 resolved trades entire history), zero live picks.

**After:** 10 FRED series × ~260 daily obs = 2,533 observations cached locally:
- Treasury yields (DGS2, DGS10, DGS30)
- Yield curve spreads (T10Y2Y, T10Y3M)
- TIPS breakevens (T10YIE, T5YIE, T5YIFR)
- Credit spreads (BAMLH0A0HYM2)

**Current snapshot (2026-04-20):**
- DGS10: 4.26% (range 3.97-4.58 over 12m, median 4.23)
- T10Y2Y: 0.52 pp (curve positively sloped)

**3 proposed BOND strategies** (S0 hypothesis stubs; not yet deployed):
1. **Yield-Curve Carry & Roll-Down (2s10s)**: enter long 7-10Y when T10Y2Y > 0.30 pp AND 5d Δ > 0
2. **TIPS Breakeven Mean Reversion (5y5y fwd)**: fade T5YIFR deviations > ±1.0σ from 252d mean
3. **Credit Spread Regime Switch (HY OAS)**: rotate HY→UST when BAMLH0A0HYM2 crosses 63d MA by +15 bp

---

### 5. `pandas-datareader` + Stooq — non-US equity coverage

**Before:** equity coverage via yfinance / TwelveData / AlphaVantage / FMP, patchy outside US.

**After:** 20 verified non-US tickers via Stooq free endpoint:
- **DE (5)**: SAP, SIE, ALV, BMW, DTE
- **NL (1)**: ASML
- **UK (7)**: SHEL, AZN, HSBA, BP, RIO, ULVR, DGE
- **JP (4)**: 7203 (Toyota), 6758 (Sony), 9984 (SoftBank), 8306 (MUFG)
- **HK (3)**: 700 (Tencent), 9988 (Alibaba), 5 (HSBC)

**Caveats:** France, Switzerland, Nordics, Korea listings are gated on free endpoint. Need `STOOQ_API_KEY` or yfinance fallback.

---

## Corrected workflow (Mercury fixed)

After web-research critique, the right pipeline is:

1. **Per-feed point metrics** from `recent_closed` (PF, Sharpe, WR, MaxDD)
2. **`StationaryBootstrap + BCa` joint-vector CI** — one pass for all metrics
3. **`skfolio.WalkForward` or `CombinatorialPurgedCV`** — validation, not portfolio optimization
4. **`pypbo` DSR/PBO** on trial equity curves — multi-testing haircut
5. **Deterministic banner gate**: `PF BCa-lower > 1.0 AND DSR p≤0.05 AND PBO≤0.5`
6. **Hansen MCS** — prune to provably non-dominated feed cohort
7. **Optuna separately** if hyperparameter search is actually needed (most of the time: don't search, calibrate)

---

## What users will see over the next week

- **No immediate UI change** (Phase 0's descriptive legend is still the front-end honesty layer)
- Internally: these tools start producing Phase 4 artifacts (JSON under `tools/data/`)
- When Phase 4 lands, the banner will quote `HC PF 2.53 [1.81, 3.84]` — a number every reviewer can defend, not the risk-naked PF 1.61 that v2 proposed

---

## Cross-references (all on main)

- `docs/PYPBO_AUDIT_FULL_USAGE_2026_04_20.md`
- `docs/SKFOLIO_AUDIT_FULL_USAGE_2026_04_20.md`
- `docs/MERCURY_WORKFLOW_CRITIQUE_2026_04_20.md`
- `docs/BOND_STRATEGY_PROPOSALS_2026_04_20.md`
- `docs/EQUITY_STOOQ_COVERAGE_2026_04_20.md`
- Tools: `tools/deflated_sharpe_per_feed.py`, `tools/walk_forward_validation.py`, `tools/block_bootstrap_ci.py`
- Data helpers: `alpha_engine/bond_data_fred.py`, `alpha_engine/equity_data_stooq.py`
