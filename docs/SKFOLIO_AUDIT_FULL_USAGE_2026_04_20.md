# skfolio — Full Feature Usage for findtorontoevents.ca/audit
**Date:** 2026-04-20 | **Source:** skfolio.org/api.html, GitHub README (v0.20.1, Apr 2026)
**Verdict:** Mercury's "MV / RP / BL" framing captures <15% of skfolio's surface area. The library is a full scikit-learn–compatible research platform, and several components map *better* onto our signal-selection problem than onto classical portfolio construction.

---

## 1. Full Feature Inventory (every class relevant to us)

### Optimizers
- **Naive:** `EqualWeighted`, `InverseVolatility`, `Random`
- **Convex (cvxpy-backed):** `MeanRisk`, `RiskBudgeting`, `MaximumDiversification`, `DistributionallyRobustCVaR`, `BenchmarkTracker`
- **Hierarchical / cluster:** `HierarchicalRiskParity` (HRP), `HierarchicalEqualRiskContribution` (HERC), `SchurComplementary`, `NestedClustersOptimization` (NCO)
- **Ensemble:** `StackingOptimization`

### Risk Measures (`RiskMeasure` enum — 15+)
Variance, Semi-Variance, StdDev, Semi-Deviation, MAD, CVaR, EVaR, VaR, CDaR, EDaR, Max Drawdown, Avg Drawdown, Ulcer Index, Gini Mean Difference, Worst Realization, Skewness, Kurtosis (via `ExtraRiskMeasure`).

### Expected-Return Estimators (`BaseMu`)
`EmpiricalMu`, `EWMu`, `ShrunkMu` (James-Stein / Bayes-Stein / Bodnar-Okhrin), `EquilibriumMu`.

### Covariance Estimators (`BaseCovariance`) — 11 implementations
`EmpiricalCovariance`, `EWCovariance`, `GerberCovariance`, `DenoiseCovariance`, `DetoneCovariance`, `LedoitWolf`, `OAS`, `ShrunkCovariance`, `GraphicalLassoCV`, `ImpliedCovariance`, `RegimeAdjustedEWCovariance`.

### Prior / Views (`BasePrior`)
`EmpiricalPrior`, `BlackLitterman`, `TimeSeriesFactorModel`, `SyntheticData`, `EntropyPooling`, `OpinionPooling`.

### Distance Estimators
Pearson, Kendall, Spearman, Covariance, Distance Correlation, Mutual Information / Variation of Information.

### Clustering
`HierarchicalClustering` + `LinkageMethod` (single, complete, average, ward).

### Uncertainty Sets (robust optimization)
`Empirical*UncertaintySet`, `Bootstrap*UncertaintySet` for both μ and Σ.

### Cross-Validation
`WalkForward`, **`CombinatorialPurgedCV`** (López de Prado), `MultipleRandomizedCV`, `OnlineGridSearch`, `OnlineRandomizedSearch`, `CovarianceForecastEvaluation`, `CovarianceForecastComparison`.

### Pre-Selection Transformers (sklearn Pipeline-compatible)
`DropCorrelated`, `DropZeroVariance`, `SelectKExtremes`, `SelectNonDominated`, `SelectComplete`, `SelectNonExpiring`.

### Distributions & Copulas
Univariate: `Gaussian`, `StudentT`, `JohnsonSU`, `NormalInverseGaussian`. Bivariate copulas: Gaussian, Student-t, Clayton, Gumbel, Joe, Independent (+ rotations). Multivariate: `VineCopula` (regular / centered / clustered / conditional sampling).

### Constraints (on `MeanRisk`/`RiskBudgeting`)
Weight bounds, group constraints, budget, tracking error, turnover, **cardinality**, **threshold** (min position), transaction costs, management fees.

### Portfolio / Population
`Portfolio`, `MultiPeriodPortfolio`, `Population` with built-in Sharpe, Sortino, Calmar, Omega, Tail Ratio, VaR, CVaR, skew, kurtosis, DSR, PBO.

---

## 2. Signal-Selection Remix — reframing for our audit

Our problem is *not* "allocate capital across assets." It is: **given N feeds/strategies producing trade returns, which subset (and with what aggregation weight) should drive Active Picks?** Portfolio math maps 1:1:

| Portfolio concept | Our signal-selection equivalent |
|---|---|
| Asset = column of returns | Feed/strategy = column of per-pick PnL% |
| Weight vector w | Feed aggregation weight / vote mass |
| Covariance Σ | Feed-return correlation (redundancy detector) |
| μ (expected return) | Feed edge estimate (shrunk, not raw) |
| Risk parity | Equal *risk contribution* per feed — avoids one noisy strategy dominating |
| HRP clustering | Auto-detects redundant-strategy clusters from correlation dendrogram |
| Cardinality constraint | "Use at most K feeds this week" (explainability) |
| Turnover constraint | Limit week-over-week feed-weight churn |
| Transaction cost | Operational cost of activating a feed (compute, API quota) |

So the "portfolio" is a **meta-strategy of strategies**, and skfolio becomes our Phase 4 feed-selector engine.

---

## 3. Top 5 Non-Obvious Applications Mercury Missed

1. **`CombinatorialPurgedCV`** — the gold-standard CV for financial time-series with overlapping labels (our active-pick windows overlap). Directly upgrades Phase 4 walk-forward from simple rolling k-fold to López-de-Prado-grade, with purge + embargo to kill leakage. Also yields **PBO (Probability of Backtest Overfitting)** natively.
2. **`VineCopula` + `StudentTCopula` / `ClaytonCopula`** — crypto returns are heavy-tailed and exhibit **lower-tail dependence** (crashes correlate more than rallies). Clayton/Gumbel copulas model this; Gaussian Σ does not. Use to simulate realistic joint stress scenarios for feed-portfolio drawdown estimation.
3. **`EntropyPooling` / `OpinionPooling` priors** — lets us inject *qualitative* views (e.g., "regime is risk-off, demote momentum feeds") into the optimizer as soft constraints without rewriting the whole pipeline. This is the principled replacement for our ad-hoc regime multipliers.
4. **`NestedClustersOptimization` (NCO)** — cluster feeds by correlation → run risk parity *within* clusters → combine clusters. Exactly the "strategy-cohort" structure we already have (momentum cohort, mean-reversion cohort, KOL cohort). NCO gives a rigorous weighting scheme instead of hand-tuned cohort multipliers.
5. **`ImpliedCovariance` + `DetoneCovariance`** — denoises the correlation matrix by removing the dominant market-beta eigenvector. For us this isolates each feed's **idiosyncratic edge** vs. market drift — directly answers "does this feed add alpha beyond BTC beta?"

Bonus: `DistributionallyRobustCVaR` — worst-case CVaR over an ambiguity set of distributions. Perfect for adversarial regime change (2022-style deleveraging).

---

## 4. Recommended Integration Order

1. **Phase 4a — CV upgrade (1–2 days):** Swap current walk-forward for `CombinatorialPurgedCV` on per-feed return series. Emit PBO per feed into audit dashboard. Zero optimizer work required.
2. **Phase 4b — Risk measures (1 day):** Replace Sharpe-only per-feed ranking with a `Population`-scored panel: Sortino, Calmar, CVaR₉₅, Ulcer. Pure metric swap, no optimizer.
3. **Phase 4c — Covariance + clustering (2–3 days):** Compute `DenoiseCovariance` → `HierarchicalClustering` dendrogram of feeds. Ship as read-only "Feed Redundancy Map" widget before any weight changes.
4. **Phase 4d — HRP weights (shadow):** Run `HierarchicalRiskParity` weekly, log weights vs. current aggregation, *do not* trade off it yet.
5. **Phase 4e — NCO + constraints (live):** Promote `NestedClustersOptimization` with cardinality ≤ K and turnover cap ≤ Δ as the production feed-weighter.
6. **Phase 4f — Copula stress tests:** Weekly `VineCopula` Monte Carlo of aggregated portfolio drawdown; feed into risk dashboard.

### Wiring
- New module `audit_trail/skfolio_feed_selector.py`: reads closed-pick CSV → per-feed return matrix → sklearn Pipeline (`DropZeroVariance` → `DropCorrelated` → `DenoiseCovariance` → `NestedClustersOptimization`) → writes `feed_weights_<date>.json`.
- Weekly GitHub Actions cron (not inside `dashboard_generator.py` — that file only renders, per CLAUDE.md rules).
- Dashboard reads the JSON; `template.html` (not `index.html`) gains a "Feed Allocation" panel.

---

## 5. What Mercury Missed (summary)

- **Cross-validation:** ignored `CombinatorialPurgedCV` — the single most valuable piece for us.
- **Risk measures:** variance-only framing; skfolio has 15+ incl. tail/drawdown measures we actually care about.
- **Covariance zoo:** didn't mention Gerber, Denoise, Detone, GraphicalLassoCV, Implied, Regime-Adjusted — all robust to our noisy crypto data.
- **Priors:** missed `EntropyPooling` / `OpinionPooling` (principled qualitative-view injection) and `SyntheticData` (stress-test prior).
- **Hierarchical optimizers:** HRP/HERC/NCO/Schur are arguably better fits than MV for non-stationary, small-sample feed returns.
- **Copulas & vines:** entire tail-dependence toolkit ignored.
- **Robust optimization:** bootstrap uncertainty sets + `DistributionallyRobustCVaR` unmentioned.
- **Pre-selection transformers:** sklearn-compatible feed filters that slot directly into a Pipeline.
- **Portfolio analytics:** `Population` object gives Sharpe/Sortino/Calmar/PBO/DSR for free.

**Bottom line:** treat skfolio as our Phase 4 backbone, not a one-shot MV solver. Start with `CombinatorialPurgedCV` this week.
