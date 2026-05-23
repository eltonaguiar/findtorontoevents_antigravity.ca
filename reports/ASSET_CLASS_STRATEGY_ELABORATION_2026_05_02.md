# Asset-Class Strategy Research Elaboration — 2026-05-02

**Author:** Claude Opus 4.7 — synthesizing Grok + Cloud Agent + Mercury 2 + DeepSeek + Cerebras Qwen + Codex bot reviews + Kimi cross-comparison
**Goal:** consolidated reference for /audit operators — glossary, per-class empirical evidence, methodology, and cross-class recommendations.

## Glossary of abbreviations

### Performance metrics
| Term | Meaning | Reading |
|---|---|---|
| **PF** (Profit Factor) | Sum of gross wins / abs(sum of gross losses) | >1.5 = real edge; >2.0 = strong; >3.0 = exceptional |
| **WR** (Win Rate) | Fraction of trades closing positive | Asset-class dependent: crypto >55% strong; non-crypto >50% strong |
| **MDD** (Max Drawdown) | Largest peak-to-trough equity decline | Tier 1 <10%; Tier 2 <20%; Tier 3 <30% |
| **Sharpe** (Sharpe Ratio) | (excess return) / (return std) annualized | >1 acceptable; >2 strong; >3 institutional |
| **Calmar** | Annualized return / Max DD | >1 good; >3 excellent |
| **Sortino** | Sharpe but only downside variance in denominator | Better measure when returns are skewed |
| **Omega** | Probability-weighted gain/loss ratio at threshold τ | Higher = better |
| **MAR** | Compound annual return / Max DD | Operator-friendly Calmar variant |

### Statistical rigor
| Term | Meaning | Use |
|---|---|---|
| **CI** (Confidence Interval) | Range containing true value with probability 1-α | Bootstrap CIs surface uncertainty around point estimates |
| **BH-FDR** (Benjamini-Hochberg False Discovery Rate) | Multiple-testing correction limiting expected proportion of false rejections | Required when testing many strategies; only BH-survivors are statistically distinguishable from coin flips |
| **PSR** (Probabilistic Sharpe Ratio) | P(true Sharpe > benchmark) given sample stats + skew/kurt | >0.95 = 95% confident strategy beats benchmark |
| **DSR** (Deflated Sharpe Ratio, Bailey-López de Prado 2014) | PSR adjusted for multiple-trials selection bias | >0.95 = strategy survives multiplicity correction; the gold-standard "is this real?" test |
| **CPCV** (Combinatorial Purged Cross-Validation, López de Prado) | Walk-forward variant that purges train/test leakage from autocorrelated time series | Required for honest backtest stats |
| **IC** (Information Coefficient) | Spearman rank-correlation between predicted and realized | >0.05 = weak edge; >0.15 = strong |
| **wilson_lb** (Wilson score lower bound) | Lower edge of WR confidence interval | Gates against small-sample fluke promotion |

### Risk / portfolio
| Term | Meaning | Use |
|---|---|---|
| **HRP** (Hierarchical Risk Parity, López de Prado) | Allocates risk by single-linkage clustering on correlation matrix | Capital flows automatically to uncorrelated edges |
| **vol-targeting** | Position size = target_vol / forecast_vol | Renaissance/Citadel-grade risk shaping; turns crypto MDD 178% into <30% |
| **Kelly** | Optimal-growth bet fraction from edge/odds | Cap at 1/4-Kelly to avoid blow-up |
| **HAR-RV** (Heterogeneous AutoRegressive Realized Volatility) | Vol forecast model using daily/weekly/monthly RV components | Powers vol-targeting forecast |
| **GARCH** | Generalized AutoRegressive Conditional Heteroskedasticity | Vol-of-vol modeling |
| **HMM** (Hidden Markov Model) | Regime-switching latent-state model | Detects bull/bear/crisis regimes for conditional sizing |
| **CTA** (Commodity Trading Advisor) | Trend-following systematic fund category | Reference benchmark + target allocation style |

### Cost / execution
| Term | Meaning | Why it matters |
|---|---|---|
| **bps** (basis points) | 1bp = 0.01% | Settlement noise threshold; round-trip slippage |
| **slippage** | Realized vs quoted execution gap | Eats edge; per-class: crypto 10bp, equity 5bp, forex 2bp, commodity 8bp |
| **ADV** (Average Daily Volume) | 30-day median trading volume | Caps position size to avoid market impact |
| **Almgren-Chriss** | Optimal-execution model balancing impact vs timing | Source for liquidity-adjusted slippage curves |

## Per-asset-class evidence (from PR #626 backtest on 7,445 closed picks)

Source: `reports/strategy_research_data_2026_05_02.json` (in main as of 2026-05-02). All metrics computed by `tools/run_strategy_research.py` with seed=42, no network calls, deterministic.

### CRYPTO (n=6,884 — 92.5% of dataset)

| Metric | Point | 95% Bootstrap CI |
|---|---|---|
| Profit Factor | **0.409** | [0.386, 0.435] |
| Win Rate | 32.8% | [31.9%, 33.8%] |
| Sharpe | **−5.20** | [−5.56, −4.84] |
| PSR vs zero | 0.000 | (definitively below baseline) |
| Resolver flicker (wins <10bp) | **45.1%** | (significant noise component) |
| Net PF after 10bp slippage | **0.251** | (worse than gross) |

**Interpretation:** the forward-test crypto stream is predominantly losing across n=6,884. Per the data caveat in `reports/strategy_research_using_framework_2026_05_02.md`, this is the **forward-test ensemble**, not the active-promoted subset (which the `/audit` headline shows as PF 1.140 / MDD 178%). The active subset has edge; the forward-test ensemble does not. **Action:** vol-targeting must apply to the active-promoted subset, not the forward-test universe (vol-targeting cannot rescue a losing series).

### EQUITY (n=30 — 0.4% of dataset)

| Metric | Point | 95% Bootstrap CI |
|---|---|---|
| Profit Factor | **1.212** | [0.66, 2.18] (CI straddles 1.0) |
| Win Rate | 43.3% | [30%, 56.7%] |
| Sharpe | 1.43 | [−3.04, 6.26] (very wide) |
| PSR vs zero | 0.689 | (suggestive but not robust) |
| Resolver flicker (wins <10bp) | **100.0%** | (every win is sub-10bp noise) |
| Net PF after 5bp slippage | **0.000** | (gross edge entirely eaten by costs) |

**Interpretation:** the forward-test EQUITY n is too thin (30 picks) to make confident claims. **The 100% resolver-flicker rate is the alarm bell** — under the legacy 0.1bp threshold, every "win" was a 1bp resolver tick masquerading as alpha. Asset-class-gated 20bp threshold (per Theme B) eliminates these. The active-promoted EQUITY subset (PF 1.385 per `/audit`) is the relevant population; this evidence flags the forward-test ensemble as **unevaluable until the asset-class threshold lands** in resolver v2.

### FOREX (n=423 — 5.7% of dataset)

| Metric | Point | 95% Bootstrap CI |
|---|---|---|
| Profit Factor | **0.394** | [0.32, 0.47] |
| Win Rate | 27.2% | [23.9%, 31.0%] |
| Sharpe | **−7.19** | [−8.80, −5.73] |
| PSR vs zero | 2.5e-15 | (effectively zero) |
| Resolver flicker (wins <10bp) | **100.0%** | (all 115 wins are sub-10bp) |
| Resolver flicker (wins <5bp) | **100.0%** | (all 115 wins are sub-5bp) |
| Net PF after 2bp slippage | **0.000** | (no surviving edge) |

**Interpretation:** **the most catastrophic data-integrity story in the dataset.** Every single FOREX win is below 5bp — meaning the FOREX class is currently **unevaluable** because the legacy resolver is generating false-positive wins from execution-level noise. The asset-class-gated FOREX threshold (10bp per the plan) reclassifies all 115 "wins" as flat trades → eliminates the false-edge contamination. **Action:** verdict on FOREX edge is impossible until resolver v2 + asset-class threshold are active. PR #610 (resolver v2.1 bug fixes) is the blocker.

### COMMODITY (n=76 — 1.0% of dataset)

| Metric | Point | 95% Bootstrap CI |
|---|---|---|
| Profit Factor | **6.560** | [4.19, 12.00] (very wide) |
| Win Rate | **80.3%** | [73.7%, 88.2%] |
| Sharpe | **15.83** | [11.72, 22.25] |
| PSR vs zero | 1.00 | |
| Resolver flicker (wins <10bp) | **100.0%** | |
| Resolver flicker (wins <5bp) | 55.7% | |
| Net PF after 8bp slippage | **0.000** | (entire PF 6.56 collapses) |

**Interpretation:** the headline numbers look spectacular (PF 6.56, WR 80%) but **two crushing caveats:**
1. 100% of wins are sub-10bp — half are sub-5bp. The asset-class-gated 25bp threshold reclassifies most as flat.
2. At literature-prior 8bp round-trip slippage on commodity futures, the entire PF 6.56 collapses to 0.00.

**Both caveats apply to the SAME source** — `multi_asset_cot` (n=41) drives the whole COMMODITY edge. It's the only BH-FDR survivor in the dataset (p<10⁻⁴), but its net-of-cost PF is 0.00. **Action:** promote `multi_asset_cot` for capacity research (deeper dive into its actual fill quality), do NOT promote it for sizing yet.

### FUTURES (n=31 — 0.4% of dataset)

| Metric | Point |
|---|---|
| Profit Factor | **0.000** |
| Win Rate | 0.0% |
| Sharpe | **−669.7** |
| Net PF after 4bp slippage | 0.000 |

**Interpretation:** completely losing on the forward-test ensemble. n is too thin for confident claim, but with 0/31 wins the verdict is unambiguous. **Action:** investigation per `STRATEGY_INVESTIGATION_BEFORE_KILL.md`; expand sample size before any promotion attempt.

### Source-system BH-FDR results (n=6 sources, 1 survives at 5%)

| Source | n | PF | WR | p-value | Survives BH 5%? |
|---|---|---|---|---|---|
| **multi_asset_cot** | 41 | **8.029** | 85.4% | **1.15e-13** | ✅ |
| cta_replicator | 83 | 0.813 | 47.0% | 0.712 | ❌ |
| multi_asset_copytrader | 412 | 0.787 | 25.2% | 0.942 | ❌ |
| unknown | 782 | 0.643 | 52.4% | 0.997 | ❌ |
| rapid_fire | 207 | **0.158** | 29.0% | **0.99996** | ❌ (cleanest demote candidate) |
| quan_engine | 5,896 | 0.411 | 30.4% | 1.000 | ❌ |

**Action:** `rapid_fire` (PF 0.158, p=1.0) is the cleanest demote candidate per the BH-FDR table. Per `STRATEGY_INVESTIGATION_BEFORE_KILL.md`, formal investigation is mandatory before kill — this report initiates that investigation.

## Methodology

### Why these techniques (each with brief justification)

1. **Bootstrap CIs (1000 resamples)** — point estimates without uncertainty are misleading. PF 1.385 with [1.05, 1.71] is investable; PF 1.385 with [0.7, 2.0] is not. Bootstrap is the most-general nonparametric CI; works on any metric (PF, WR, Sharpe).

2. **BH-FDR multiple-testing correction** — when testing many strategies (we have 6+ source-systems × multiple asset classes), naive p<0.05 rejection produces ≥5% false discoveries. BH controls the *expected proportion* of false discoveries among rejections, which is the right error rate for the "which sources have edge?" question.

3. **DSR (deflated Sharpe)** — selection bias inflates the headline Sharpe of the *best* strategy from a search. DSR is the probability the headline Sharpe survives the deflation correction. **Now in `alpha_engine/statistical_rigor.py`** (PR #633 cherry-pick from Kimi).

4. **Resolver-flicker accounting** — `outcome_resolver.py` v2 ships asset-class thresholds (PR #610 awaits operator merge). Without them, sub-bp execution noise becomes "wins" and corrupts every downstream metric.

5. **Transaction-cost overlay** — gross numbers are not investable claims. Renaissance / Two Sigma never publish gross. PR #627 wired `transaction_cost_model` into `dashboard_generator._normalize_pick` behind `HF_NET_PF_ENABLED` flag.

6. **HRP allocation over source-systems** — equal-count allocation doesn't reflect risk. HRP clusters by correlation and allocates risk equally per cluster — capital flows to uncorrelated edges, starves correlated zombies. Wire-up requires date-pivoted matrix (today's per-trade-stream input is degenerate).

7. **HMM regime detection** — single-state metrics hide regime-conditional edge collapse. The conditional-worst-regime Sharpe is what Two Sigma uses internally; if positive across all 4 regimes, edge is robust.

8. **Vol-targeting (HAR-RV + 1/4-Kelly)** — turns single-shot picks into Sharpe-equalized risk allocation. Single biggest move on CRYPTO MDD per `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md`.

## Cross-class recommendations (priority order)

| # | Action | Class | Estimated impact |
|---|---|---|---|
| 1 | **Land asset-class-gated resolver thresholds** (PR #610) | FOREX/EQUITY/COMMODITY | unblocks all non-crypto verdicts |
| 2 | **Wire vol-targeting to active CRYPTO subset** (Theme A) | CRYPTO | MDD 178% → <30% |
| 3 | **Wire `transaction_cost_model` net-PF on /audit panels** (PR #627 default-OFF; flip flag) | All | Headline numbers become investable |
| 4 | **Add `survives_bh_5pct` + `dsr` columns to source-system table** | All | Visitor sees real vs lucky at a glance |
| 5 | **Investigate `rapid_fire` per `STRATEGY_INVESTIGATION_BEFORE_KILL.md`** | All | Cleanest demote candidate (p=1.0, PF 0.158) |
| 6 | **Date-pivot HRP input matrix** | All | Allocator stops returning degenerate equal-weight |
| 7 | **Promote `multi_asset_cot` for capacity research** (NOT sizing) | COMMODITY | Verify net-of-impact edge before capital weight |
| 8 | **Wire decay tracker into live dashboard generator** | All | Auto-demote rolling-90d Sharpe collapses |

## What this evidence does NOT prove

- The **active-promoted** subset (the `/audit` headline numbers) may behave differently from the **forward-test ensemble** analyzed here.
- 30-day or 90-day OOS validation has not been re-run with the new statistical rigor — that's Phase 5 in the roadmap.
- HMM regime decomposition requires 5y of macro-factor history (VIX z-score, DXY momentum, BTC RV, 10y-2y slope) — not yet built.
- Factor-overlay tests (12-1 momentum, quality, low-vol, carry, term-structure) require Compustat-grade fundamentals + curve data — not in scope for this driver.

## References

- Bailey & López de Prado (2014). *The Deflated Sharpe Ratio.* Journal of Portfolio Management 40(5).
- Benjamini & Hochberg (1995). *Controlling the False Discovery Rate.* JRSSB 57(1).
- López de Prado (2018). *Advances in Financial Machine Learning.* Wiley.
- Almgren & Chriss (2000). *Optimal Execution of Portfolio Transactions.* Journal of Risk 3.
- `reports/HEDGE_FUND_UPLIFT_ROADMAP_2026_05_02.md` — multi-PR roadmap with sequencing
- `reports/strategy_research_using_framework_2026_05_02.md` — original PR #626 backtest report
- `reports/strategy_research_data_2026_05_02.json` — machine-readable backtest data
- `reports/PR_621_REVIEW_2026_05_02.md` — 4-reviewer DECOMPOSE consensus on Kimi alternative
- `reports/KIMI_VS_MAIN_COMPARISON_2026_05_02.md` — head-to-head verdict (KEEP-MAIN)
