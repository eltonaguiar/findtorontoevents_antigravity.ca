# MIT Quant Bible — Harvest Report

**Date:** 2026-05-03
**Source:** "QUANT BIBLE — MIT Sloan Business Club" (51-page PDF, 166k chars text-extracted)
**Reviewer goal:** Harvest concrete trading-system upgrades to lift Goal #1 per-asset PF/WR.
**Method:** Full-text extraction → general-purpose subagent cross-check vs repo (Grep on `alpha_engine/`, `audit_trail/`).

---

## 1. Document scope

This is **interview-prep material**, not research material. A study guide written by undergrad members of the MIT Sloan Business Club (lead author + Kyri Chen, Ravi Raghavan, Guang Cui, Evan Vogelbaum, Brian) to help SBC members pass quant-finance recruiting (Jane Street / Citadel / Two Sigma / SIG / HRT / Optiver / Akuna / Five Rings / Virtu).

Section breakdown:
- **§1 Intro + class list** (pp 2-5): MIT course-road (18.600, 18.06, 14.32, 6.036, 18.650), book list (ESL, Heard on the Street, Hull). Zero novel content.
- **§2 Probability fundamentals** (pp 5-10): Bayes, conditional prob, expectation/variance, classical PMFs/PDFs (Bernoulli, Binomial, Poisson, Geometric, Uniform, Normal, Exponential), covariance/correlation. Textbook.
- **§3 Stats fundamentals** (pp 10-12): LLN, CLT, confidence intervals via Slutsky. Textbook.
- **§4 Quant research / data science** (pp 12-25): Condensed restatement of "Elements of Statistical Learning" — least squares, k-NN, ridge, lasso, elastic net, PCR, LAR, stepwise selection, F-test, OVB, CIA. Plus econometrics perspective (selection bias, randomized trials, OLS robust standard error).
- **§5 Case studies** (pp 26-30): Two Sigma NYC housing (multivariate regression with log-square-footage), QuantCo opera house (dynamic pricing with time-to-event + scarcity terms), Two Sigma CitiBike (cyclical encodings, geographic basis transforms).
- **§6 Market making** (pp 31-35): Bid-ask spread theory by undergrads — theoretical value + last traded price + inventory skew. Toy cases (Red Sox win count, Tanzania population, Trade-or-Tighten). **No Avellaneda-Stoikov, no Glosten-Milgrom, no Kyle.**
- **§7 Question bank** (pp 36-51): 50+ brainteasers. Coin-flip games, dice EV, geometric prob, ant-on-circle invariants, Cauchy-Schwarz on regression betas, Kelly criterion (mentioned in passing on p49).

**Rigor level:** 1st-year undergrad. Useful for someone preparing for a Jane Street superday. **Not useful as a primary source for a 156-strategy live system already running PSR/DSR/HRP/Kelly/walk-forward + 10k MC.** Does not cite López de Prado, does not mention CPCV/PBO/CSCV, has nothing on microstructure beyond a paragraph, nothing on regime detection, nothing on cointegration, no SDE/stochastic calculus, no portfolio optimization beyond mean-variance hand-wave, no execution algos, no transaction cost models.

**Bottom line:** The bible clears a low bar. Net harvest: **4 small concepts + 1 strategy proposal + 1 OVB-sensitivity idea**. Rest is already in repo or below our bar.

---

## 2. New quant concepts (not already in repo)

Cross-checked via Grep against `alpha_engine/`, `audit_trail/`:

| # | Concept | Page | Repo attach point | Lift | Class |
|---|---|---|---|---|---|
| 2.1 | **Three-correlations PSD bound** — positive-semidefinite constraint on 3×3 correlation matrix gives feasible interval for unknown ρ_XZ given ρ_XY, ρ_YZ. Catches data corruption. | 38 | `alpha_engine/feature_health.py` + `hrp_allocator.py`: PSD-validate inferred correlation matrices before HRP clustering. Catches the ghost MATIC artifact pattern. | **Low-Med** | system-wide |
| 2.2 | **Cyclical encoding via sin/cos basis** (CitiBike case) — encode hour-of-day and month as `(sin(2πh/24), cos(2πh/24))` instead of one-hot or raw integer; preserves wraparound continuity. | 29 | `alpha_engine/non_crypto_boosters.py::_forex_session_boost` currently uses raw hour buckets. Replace with sin/cos features for ML rankers. | **Med** | **FOREX (top), CRYPTO** |
| 2.3 | **Strategy embedding via PCA → k-NN smoothing** (CitiBike case) — instead of one-hot `source_system`, embed each strategy in low-dim coord (PCA on hour/symbol/direction profile). Borrow strength across neighbor strategies for small-n classes. | 29 | New `alpha_engine/strategy_embeddings.py`; consumed by `dashboard_generator.py` per-strategy stat block. | **Med** | **BOND (n=18), ETF (n=87)** |
| 2.4 | **Inventory-skewed quoting → state-dependent score floors** (Market Making §6.2) — when over-allocated to a class, raise floor by Δ proportional to over-exposure; when under-allocated, lower it. | 32 | `alpha_engine/quality_gates.py` — wrap per-asset floors as function of `portfolio_state.class_exposure / target_exposure`. | **Med** | EQUITY/CRYPTO (over) + BOND/ETF (under) |

---

## 3. Concepts already in repo (skip these)

Confirmed via Grep — do not re-implement:

- **Kelly criterion** (p 49) → `alpha_engine/kelly_position_sizer.py`
- **Bootstrap CIs / PSR / Benjamini-Hochberg FDR** → `alpha_engine/statistical_rigor.py` already has all three; the doc doesn't even mention them.
- **Ridge / Lasso / Elastic Net / PCA** (pp 18-20) → sklearn-based across `elite_scorer.py`, `scanner.py`, `production_scanner.py`.
- **Spearman rank correlation** (p 27) → `elite_scorer.py`, `confidence_calibrator.py`, `trust_score.py`.
- **OLS / multivariate regression / FWL** (pp 16-17) → `scanner.py`, `fwls_stacker.py`.
- **Walk-forward / OVB controls** (pp 23-25) → `walk_forward_backtester.py`, `anti_overfit_validator.py`.
- **Confidence intervals / t-test** (pp 11, 16) → `statistical_rigor.py`, `consensus_what_if.py`.
- **HRP allocator** → `hrp_allocator.py` (doc only mentions mean-variance hand-wave).
- **Bayes posterior updating** (pp 5-6) → `bayes_optimizer.py`.

---

## 4. Top 5 ROI ideas, ranked

### #1 — Cyclical sin/cos encoding for FX session feature
- **Hypothesis:** FX session is continuous; raw hour buckets in `_forex_session_boost` create artificial step changes that mis-classify pre/post-session-boundary picks.
- **Target:** FOREX (sub-floor PF 0.27, n=1169 — biggest opportunity).
- **Metric:** FOREX PF ≥ 0.50 over forward 30d.
- **Experiment:** Add `sin_hour`, `cos_hour`, `sin_dow`, `cos_dow` features; A/B via `USE_CYCLICAL_HOUR=1` env flag for 30d on FX picks only. Pass = FX PF lift ≥ +0.15 vs control with p<0.10 via bootstrap.
- **Files:** `alpha_engine/ml_ranker.py`, `alpha_engine/non_crypto_boosters.py:_forex_session_boost`, new `alpha_engine/features/cyclical.py`.

### #2 — Inventory-skewed score floors (state-dependent gates)
- **Hypothesis:** Static per-class floors over-trade over-allocated classes (CRYPTO, EQUITY) and under-trade under-allocated (BOND n=18, ETF n=87).
- **Target:** BOND + ETF n-growth without sacrificing PF; CRYPTO drag reduction.
- **Metric:** BOND n: 18→60 in 30d, PF ≥1.5; ETF n: 87→150, PF ≥1.2; CRYPTO n cuts by 20% with PF lift to ≥1.35.
- **Experiment:** Wrap `passes_active_gate` to multiply class floor by `min(2.0, max(0.5, target_share / current_share))`. Sidecar 14d, A/B compare. Pass = directional change matches hypothesis on 4/6 classes.
- **Files:** `alpha_engine/quality_gates.py`, `alpha_engine/portfolio_state.py`.

### #3 — Strategy embedding via PCA → k-NN smoothing for small-n classes
- **Hypothesis:** BOND (n=18) and ETF (n=87) lack trade-count for per-strategy PSR confidence. Embed in 4-d coord, borrow strength from k=3 nearest neighbors' historical PF as Bayesian prior.
- **Metric:** BOND CI tightness — 90% bootstrap PF interval width drops from ±0.8 to ±0.4 within 14d.
- **Experiment:** Build `alpha_engine/strategy_embeddings.py`, plug into `dashboard_generator.py` per-strategy block. Pass = BOND PSR>0.6 reachable on 3+ strategies with n>=20.
- **Files:** New `alpha_engine/strategy_embeddings.py` (sidecar with Wiring Plan per Wire-Up Rule), `audit_trail/dashboard_generator.py`.

### #4 — Three-correlation PSD sanity check
- **Hypothesis:** "100% correlated" pseudo-features in `feature_correlation.json` are data artifacts (ghost MATIC pattern, clone_hl placeholder pattern). PSD-violation check on inferred 3×3 sub-matrices catches them before HRP allocates capital.
- **Metric:** PSD-violating triples drop to 0 within 7d after cleanup.
- **Experiment:** `validate_psd_triples()` in `feature_health.py`; dump violations to `reports/psd_violations_*.json`. Pass = identified ≥1 known ghost (ghost MATIC) on first pass.
- **Files:** `alpha_engine/feature_health.py`, `alpha_engine/hrp_allocator.py`.

### #5 — Log-transform of pnl_pct before per-strategy aggregation
- **Hypothesis (synthesis with §5.1 NYC housing case):** ESL-style argument — when distribution is right-skewed lognormal-like, naive arithmetic mean over-weights extreme winners. Switching to log-mean (geometric) yields ranking that better matches realized compounded returns.
- **Metric:** Spearman ρ between rank(log-mean-pnl) and rank(realized-30d-cumulative-return) > Spearman ρ vs arith-mean-pnl. Threshold: +0.10 ρ improvement.
- **Experiment:** Compute both rankings nightly for 14d, surface in `reports/ranking_comparison_*.md`. Pass = log-mean wins 10/14 days.
- **Files:** `alpha_engine/elite_scorer.py`, `alpha_engine/trust_score.py`.

---

## 5. New strategy proposals

The bible has no actual strategy specs — it's interview prep. Only one proposal is genuinely doc-derived:

### Strategy: `fx_session_continuity_boost`

- **Asset class:** FOREX (priority), then COMMODITY (gold/silver have similar session-dependence).
- **Signal:** Long EURUSD/GBPUSD/USDJPY only when `cyclical_session_score > 0.7` AND a base technical signal (EMA cross / RSI divergence / breakout) fires. Score = `0.5 * (1 + sin(2π * (h - h_optimal)/24))` where `h_optimal=12 UTC` for EUR/GBP, `h_optimal=2 UTC` for JPY.
- **Risk:** SL at 1.0× ATR(14, 1h), TP at 2.0× ATR. Max position size = 0.5% NAV (FX is sub-floor — start small).
- **Sizing:** Kelly fraction × 0.25 (quarter-Kelly, conservative until n>=50).
- **Complementarity:** Pairs with `cftc_cot_commercial_signal` (68.8% WR / PF 3.5) — when COT bullish on EUR AND session_continuity > 0.7 AND base technical fires, stack confidence (consensus rule, like `non_crypto_consensus` 56.4%). Adds the "right time of day" dimension that `signal_validation` (63.6% WR / PF 2.62) doesn't currently model.
- **Where to add:** New file `alpha_engine/fx_session_continuity_strategy.py`, wired into `production_scanner.py` per Wire-Up Rule. Default OFF behind `FX_SESSION_CONTINUITY_ENABLED=1`.

Only 1 strategy worth a slot — doc is too thin on real signal logic for more.

---

## 6. Risk/validation methods worth borrowing

**Almost nothing.** The doc covers t-test, F-test, CIs, BH FDR, walk-forward, OVB/CIA reasoning — all already in `statistical_rigor.py` / `anti_overfit_validator.py`.

**One genuine pickup — OVB-style sensitivity analysis** (econometrics §4.6): for each strategy, run "long" regression of PnL on (signal + 3 control features) and "short" regression on (signal alone), compare betas. Big delta = OVB present = signal is partly proxy for a control. Implement as sidecar method in `anti_overfit_validator.py`.

**Robust standard errors / heteroskedasticity correction** (p 24-25) — NOT in repo, but only marginally useful; trade-level PnL is non-Gaussian and bootstrap CI handles this fine. Skip.

**What's still missing per `project_cpcv_gap_2026_04_28.md`:** CPCV, PBO, CSCV. **Doc does not mention any of them** — undergrad guide predates the modern López de Prado canon for backtest overfit. **No help here.**

---

## 7. Things to skip

- **Pages 5-12** — pure textbook probability/stats. NumPy/SciPy covers it.
- **Pages 12-18** — least squares + k-NN + bias-variance theory. sklearn covers it.
- **§4.6 randomized trials / RCT framework (pp 22-23)** — irrelevant to time-series trading; cannot randomly assign treatment to symbols.
- **§5.1 NYC housing case (p 26)** — interesting framework but cross-sectional regression, not time-series. Direct port = bad fit.
- **§5.2 opera house dynamic pricing (p 27-28)** — domain-specific (event ticketing). Skip.
- **§6 market making toy cases (pp 31-35)** — undergrad-level "make a market on number of magazines in the AirBnB". Real MM needs Avellaneda-Stoikov, Glosten-Milgrom, Kyle's lambda — **not in this doc**. Source from primary literature if we want MM.
- **§7 question bank (pp 36-51)** — coin-flip / dice / ants-on-circle brainteasers. Zero trading content with the lone exceptions of the three-correlations PSD bound (used in §2.1) and Cauchy-Schwarz beta bound on p 44 (interesting but not load-bearing).
- **Naive R:R intuition** — doc never explicitly endorses raw R:R thresholds, but MM toy frame ("compensate spread-keeper for risk") flirts with it. Per `feedback_confidence_is_not_edge.md`, ignore any "R:R math = edge" framing.
- **Self-reported confidence as sizing input** — doc's §6.2 "your CI should be wider when uncertain" maps poorly to our ML confidence scores. Per `project_performance_reality.md`, confidence inverts on ETF/CRYPTO with ρ=-0.07. Don't import the framing.
- **Mean-variance/single-Gaussian PnL assumptions** — CLT framing assumes well-behaved returns. Crypto returns are fat-tailed; we already use empirical bootstrap, which is correct.

---

## TL;DR

- Doc = undergrad interview prep, not research.
- Net actionable harvest: **4 concepts + 1 strategy proposal + 1 OVB-sensitivity idea**.
- All five §4 ideas combined ≈ 1-2 weeks of code work.
- None individually moves FOREX from PF 0.27 to T2 — that requires the rescue plan in `reports/forex_*` already on file (PR #724 corruption-filter root cause).
- **Do not commission a follow-up "MIT bible deep dive."**

**Next reads to clear a higher bar:**
1. López de Prado, *Advances in Financial Machine Learning* (CPCV/PBO chapter — closes the `project_cpcv_gap_2026_04_28.md` gap).
2. Cartea/Jaimungal, *Algorithmic and High-Frequency Trading* (proper market microstructure if MM strategies are on the roadmap).

---

_Generated 2026-05-03 by Antigravity session via general-purpose subagent harvest. Successor sessions: read `updates/2026-05-03-per-asset-class-enhancement-playbook.md` (PR #735) + `reports/PR_INTEGRATION_PLAN_2026_05_03_0540Z.md` (PR #736) + this file in that order._
