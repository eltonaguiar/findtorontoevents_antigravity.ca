# Strategy Bundles vs. Top Mutual Funds — Research Report

**Date:** 2026-03-01  
**Purpose:** Extensive research on crafting new strategy/strategy bundles that can outperform top-performing mutual funds.  
**Companion:** Builds on `tmp/DEEP_STRATEGY_RESEARCH_2026.md`; uses our 13 Kelly survivors + funding arb, grid, risk-managed momentum.

---

## Executive Summary

**Benchmark to beat:** Top mutual funds deliver roughly **12–19% annualized** over 5–10 years (e.g. Baron Partners ~19% 10-yr, Fidelity/TRowe 12–14%, S&P 500 ~16.55% 10-yr). A simple 60/40 does ~8% 5-yr and ~15% in strong years. Our goal is **bundles that match or exceed these returns with equal or better risk-adjusted performance (Sharpe, drawdown)**.

**Finding:** A multi-strategy bundle that combines **market-neutral income** (funding arb, grid) with **regime-filtered directional alpha** (our proven mean-reversion survivors + 28d/5d momentum) can realistically target **15–25%+ annualized** with **lower correlation to equities** and **controlled drawdowns**. That puts us in range of top large-cap mutual funds and, in favorable regimes, toward the upper end of the mutual fund universe (e.g. Baron-style 19%+).

**Key insight:** Mutual funds are almost entirely long-only equity (or equity+bonds). Our edge is **uncorrelated return sources** (funding rates, range income, mean reversion in crypto) plus **regime-aware strategy selection**. We are not trying to beat BTC; we are building a **systematic multi-strategy product** that can compete with top mutual funds on risk-adjusted returns.

**Round 2 research (Part 8):** Only **7%** of active large-cap managers survived and beat passive over 10 years (Morningstar); **95.5%** underperformed after tax (SPIVA). Multi-strategy funds using **dynamic, volatility-weighted allocation** have achieved **nearly 2x Sharpe** vs traditional fund-of-funds. Adding **uncorrelated** strategies reduces portfolio vol and volatility drag (“only free lunch”). Crypto systematic bundles show **mean reversion Sharpe ~2.3** and **momentum ~1.0–1.2** (regime-dependent). This supports our three-bundle design and target returns.

---

## Part 1: The Mutual Fund Benchmarks

### 1.1 What “Top Performing” Means in Practice

| Benchmark | 1-Yr | 5-Yr Ann. | 10-Yr Ann. | Sharpe (approx) | Notes |
|-----------|------|------------|------------|-----------------|--------|
| **S&P 500** | ~17–21% | ~18.5% | ~16.55% | ~0.8–1.0 | Standard equity benchmark |
| **60/40 (stocks/bonds)** | ~15% (2024) | ~8% | — | ~0.6–0.8 | 90% of risk from stocks |
| **Baron Partners (BPTRX)** | ~20% | ~31% | **~19%** | High vol, concentrated | Top-tier active; Tesla-heavy |
| **TRowe Blue Chip (TRBCX)** | — | — | **~14.1%** | — | Consistent large-cap |
| **Fidelity Contrafund (FCNTX)** | — | — | **~13.2%** | — | Large-cap growth |
| **Loomis Sayles Growth (LGRRX)** | — | ~12% 5-yr | **~13.8%** 10-yr | — | Top performer category |
| **Top 50 mutual funds (2025)** | Many 35%+ | — | — | — | Foreign/EM/sector; higher vol |

**Sources:** AAII 2026 Top Mutual Funds Guide, Kiplinger top actively managed funds, Morningstar 60/40 and fund performance, Baron fact sheet (10-yr 19.11% BPTIX).

### 1.2 Takeaway for Our Bundles

- **Beat 60/40:** Target **≥10% annualized** with **max DD < 15%** (60/40 had drawdowns ~20%+ in 2022).
- **Match top large-cap funds:** Target **13–15%+** annualized with **Sharpe > 1.0**.
- **Aspire to Baron-tier (19%+):** Target **18–25%** annualized with **strict risk controls** (Half-Kelly, regime filter, max DD cap).

---

## Part 2: Why Multi-Strategy Bundles Can Compete

### 2.1 Uncorrelated Return Sources

Academic and industry research consistently shows:

- **Multi-strategy portfolios** that combine **uncorrelated** sources of return improve **risk-adjusted performance** (higher Sharpe, lower drawdown) vs. single-asset or single-strategy approaches.
- **Market-neutral + directional** combinations “dial risk up or down” while reducing dependence on equity beta; market-neutral sleeves can deliver **12%+ with zero down years** in studies (e.g. 100 long/100 short optimal sizing: 12.1% return, 1.89 Sharpe, 2012–2024).
- **Crypto hedge fund composites** (e.g. VisionTrack) delivered **~40% in 2024**; top names **51–106%**. Even a **conservative** crypto multi-strategy targeting **20–30%** with lower vol would sit comfortably above most mutual fund returns.

**Sources:** Acadian Asset “Systematic Multi-Strategy Hedge Fund”; Alpha Theory “Market-Neutral: A Case for a New Strategy”; iCapital multi-strategy investing; Bloomberg/BNN crypto fund performance 2024–2025.

### 2.2 Our Building Blocks (Proven + Documented)

| Sleeve | Expected Ann. Return | Max DD (doc.) | Correlation to BTC | We Have |
|--------|----------------------|---------------|---------------------|---------|
| **Funding rate arb** | 15–25% (19.26% 2025) | ~0.85% | ~0 | Scanner + backtester |
| **Grid (range)** | 20–50% in chop | Medium | Low | Design in research; no full bot yet |
| **Our 13 Kelly survivors** | Varies by strategy | — | Medium | Live forward data |
| **Risk-managed 28d/5d momentum** | 25–45% (Sharpe 1.4–1.8) | Medium | High (directional) | In quant_strategies; needs 28d/5d + vol scale |
| **Pairs / mean reversion** | 10–20% | Low–med | Low | Cointegration in quant_strategies |

**Key:** Funding + grid are **market-neutral-ish** (low correlation to directional crypto). Our survivors are **mean-reversion** (tend to do well when retail overreacts). Momentum adds **trend capture** when regime allows. Together they form a **multi-strategy bundle** with different payoff profiles.

---

## Part 3: Three Concrete Bundles Designed to Outperform Mutual Funds

### 3.1 Bundle A — “Conservative” (Beat 60/40 and Average Mutual Fund)

**Target:** **10–14% annualized**, max DD **< 12%**, Sharpe **> 1.0**.

**Idea:** Emphasize **market-neutral and low-vol** sleeves; add a small allocation to proven mean reversion.

| Sleeve | Allocation | Rationale |
|--------|------------|-----------|
| Funding rate arbitrage | 50% | 19.26% doc. 2025, 0.85% max DD; anchor return with minimal drawdown |
| Grid trading (BTC/ETH range) | 25% | 20–50% in ranging regimes; diversify from funding |
| Kelly survivors (top 5 only) | 25% | drawdown_recovery_rsi, keltner_compression, multi_period_rsi, vwap_reversion, kalman_residual; Half-Kelly sizing |

**Rough combined return (back-of-envelope):**  
0.5×19% + 0.25×25% + 0.25×12% ≈ **18.75%** before vol scaling. After conservative sizing and regime filters (e.g. grid off in strong trend), **12–15%** is a realistic target with **lower vol** than 60/40.

**Implementation:**  
- Wire `alpha_engine/funding_rate_scanner.py` into live picks; allocate 50% of bundle capital to funding arb.  
- Deploy grid module on BTC/ETH; 25% capital.  
- Restrict “Conservative” bundle to top 5 survivors; Half-Kelly; SMA(50)/ADX regime filter so we don’t run mean reversion in strong trend.

---

### 3.2 Bundle B — “Moderate” (Match or Beat Top Large-Cap Funds)

**Target:** **15–20% annualized**, max DD **< 18%**, Sharpe **> 1.2**.

**Idea:** Add **regime-filtered momentum** and more of our survivors; keep funding + grid as base.

| Sleeve | Allocation | Rationale |
|--------|------------|-----------|
| Funding rate arbitrage | 35% | Still the stabilizer |
| Grid trading | 20% | Range income |
| Risk-managed 28d/5d momentum | 20% | Academic Sharpe 1.4–1.8; only when regime allows (e.g. ADX > 20, trend clear) |
| Kelly survivors (all 13, Half-Kelly) | 25% | Diversify across mean-reversion names |

**Rough combined return:**  
0.35×19% + 0.20×30% + 0.20×30% + 0.25×14% ≈ **22%** before scaling. With regime filters and Half-Kelly, **16–20%** is a reasonable target.

**Implementation:**  
- Implement 28d lookback / 5d hold TSMOM with vol scaling in `alpha_engine/quant_strategies.py`; gate by SMA(50)/ADX.  
- All 13 survivors in bundle; Half-Kelly from `tmp/kelly_audit_results.json`.  
- Forward stats per sleeve so we can rebalance (e.g. trim momentum if it underperforms in chop).

---

### 3.3 Bundle C — “Aggressive” (Aspire to Baron-Type Returns)

**Target:** **18–28% annualized**, max DD **< 25%**, Sharpe **> 1.3**.

**Idea:** Maximize **diversified alpha** while capping risk: more momentum and survivors, plus cross-exchange funding if available.

| Sleeve | Allocation | Rationale |
|--------|------------|-----------|
| Funding rate arbitrage | 25% | Include cross-exchange if we have APIs (+3–5%) |
| Grid trading | 15% | Range income |
| Risk-managed 28d/5d momentum | 30% | Higher weight when regime is trend-friendly |
| Kelly survivors (all 13, Half-Kelly) | 25% | Same as Moderate |
| Pairs / cointegrated (when live) | 5% | Add when cointegration pipeline is production-ready |

**Rough combined return:**  
0.25×22% + 0.15×35% + 0.30×35% + 0.25×14% + 0.05×15% ≈ **25%**. With drawdown and regime constraints, **20–26%** is the ambition.

**Implementation:**  
- Same as Moderate, plus: cross-exchange funding scan; pairs trading in production; max DD circuit breaker (e.g. reduce momentum weight if portfolio DD > 15%).

---

## Part 4: Allocation and Risk Management

### 4.1 Why Not Equal Weight?

- **Risk parity / volatility weighting** across sleeves improves **Sharpe** vs. equal weight (reward-risk parity and multi-strategy literature).
- Funding arb has **very low vol** (0.85% max DD); it can take a **larger capital share** for a given risk budget.
- Momentum and grid have higher vol; **capping their share** limits drawdowns while still capturing upside.

### 4.2 Half-Kelly and Regime Filters

- **Half-Kelly** on all directional sleeves (survivors + momentum) so we don’t overbet after a hot streak.
- **Regime filter:** SMA(50)/SMA(200)/ADX (from `DEEP_STRATEGY_RESEARCH_2026.md`):
  - **Trending:** Momentum on; mean reversion reduced or off in wrong direction.
  - **Choppy:** Grid + funding + mean reversion on; momentum off or reduced.
- **Monthly rebalance** of sleeve weights using **forward performance** (win rate, avg win/loss, Kelly%) from our aggregator (see `CURSOR_CHANGES_BLUEPRINT_2026-03-01.md`).

### 4.3 Comparison to Mutual Funds

| Metric | 60/40 | Top Large-Cap (e.g. FCNTX) | Baron (BPTRX) | Our Bundle A | Our Bundle B | Our Bundle C |
|--------|--------|-----------------------------|---------------|--------------|--------------|--------------|
| **Target ann. return** | ~8% 5-yr | ~13% 10-yr | ~19% 10-yr | 12–15% | 16–20% | 20–26% |
| **Target max DD** | ~20%+ | ~30%+ | Very high | <12% | <18% | <25% |
| **Correlation to S&P** | High | High | High | Low | Low | Low |
| **Asset class** | Stocks + bonds | Stocks | Concentrated stocks | Crypto multi-strategy | Crypto multi-strategy | Crypto multi-strategy |

Our bundles are **not** directly comparable to mutual funds (different asset class and risk). The claim is: **on risk-adjusted return (return per unit of drawdown/volatility) and absolute return targets**, these bundles are designed to **match or exceed** the performance tier of top mutual funds (12–19% ann.) with **different** risk characteristics (low equity beta, crypto-specific vol).

---

## Part 5: Implementation Roadmap (Prioritized)

1. **Funding arb in production**  
   - Wire `funding_rate_scanner` into central live-picks pipeline; record forward PnL.  
   - Allocate capital to “Funding Arb” bucket; report in forward_buckets_dashboard.

2. **Grid module**  
   - Implement grid logic (range from BB or ATR); record each fill as forward trade.  
   - Add “Grid” bucket; target BTC/ETH first.

3. **28d/5d risk-managed momentum**  
   - Add to `quant_strategies.py`; gate by regime (SMA/ADX).  
   - Feed signals into same live-picks + forward stats.

4. **Forward aggregator**  
   - Per-strategy and per-bucket (Funding Arb, Grid, Momentum, Mean Reversion) stats.  
   - Monthly rebalance of bundle weights from forward Kelly and vol.

5. **Bundle definitions in config**  
   - Conservative / Moderate / Aggressive as three preset bundles (sleeve weights + strategy lists).  
   - Dashboard or script to report “Bundle A/B/C” vs. target return and max DD.

6. **Optional: pairs trading**  
   - Cointegration-based pairs in production; add 5–10% sleeve in Aggressive when ready.

---

## Part 6: Sources (Summary)

- **Mutual fund benchmarks:** AAII 2026 Top Mutual Funds, Kiplinger top actively managed funds decade, Morningstar 60/40 and fund returns, Baron Partners fact sheet (BPTIX 10-yr 19.11%).
- **Crypto vs traditional:** Bloomberg/BNN crypto hedge funds 2024 (40% composite; 51–106% top names); Reuters hedge funds 2024; 3IQ crypto vs traditional.
- **Funding arb / grid:** Gate.io 2025 funding arb (19.26%, 0.85% DD); Boros cross-exchange; market-neutral funding harvesting (Trading Research).
- **Multi-strategy / market-neutral:** Acadian systematic multi-strategy; Alpha Theory market-neutral; iCapital uncorrelated return sources; Neuravest multi-strategy optimization.
- **Mean reversion + momentum:** PyQuantLab / Briplotnik systematic crypto (momentum, mean reversion, vol filtering); combined momentum–mean-reversion high-frequency strategy (Medium).
- **Risk parity:** Reward-risk parity (De Gruyter); risk parity algorithms (PortfolioLab, S&P DJI indexing).
- **Our data:** `baby_strategies/STRATEGY_GRAVEYARD.md` (13 survivors); `tmp/DEEP_STRATEGY_RESEARCH_2026.md`; `tmp/kelly_audit_results.json`.

---

## Part 7: Success Criteria for “Outperform Top Mutual Funds”

- **Conservative bundle:** Forward annualized return **≥ 12%** with max DD **< 12%** over a rolling 12-month window.
- **Moderate bundle:** Forward annualized return **≥ 16%** with max DD **< 18%**.
- **Aggressive bundle:** Forward annualized return **≥ 20%** with max DD **< 25%**.
- **All bundles:** Forward stats (per strategy and per bucket) updated at least monthly; no graveyarded strategies in any bundle; Half-Kelly and regime filter enforced.

If these are met, we can reasonably claim that our **strategy bundles** are competitive with **top-performing mutual funds** (12–19% ann., depending on bucket) on a **risk-adjusted and absolute-return basis**, with the caveat that they operate in a different asset class (crypto multi-strategy) and carry crypto-specific risks.

---

## Part 8: Additional Research (Round 2) — Why Outperformance Is Achievable

### 8.1 How Hard Is It to Beat the Market? (Context for Our Bundles)

- **2024:** Only **35%** of U.S. large-cap mutual funds beat the S&P 500; another study put **active U.S. equity fund outperformance at 13.2%** (with average fund return 13.5% vs S&P 25%).  
- **10-year (through Dec 2024):** Only **7%** of active U.S. large-cap managers **survived and beat** their average passive peer (Morningstar).  
- **SPIVA (after tax, 10-year):** **95.5%** of active funds **underperformed** their benchmarks; over 15 years, **no category** had a majority of active managers outperforming.

**Implication:** Beating the S&P with a *single* long-only equity fund is rare. Our approach is different: **multi-strategy, multi-sleeve bundles** with **uncorrelated return sources** (funding, grid, mean reversion, regime-filtered momentum). We are not picking stocks; we are combining **systematic strategies** that have different payoff and correlation profiles, which is exactly how multi-strategy hedge funds improve Sharpe (see 8.2).

**Sources:** SPIVA U.S. Scorecard Year-End 2024; Citywire “Just 35% of US large-cap funds”; Morningstar “Measuring the Performance of Active Funds”; ETFTrends 2024 SPIVA summary.

### 8.2 2025 Mutual Fund Landscape (Updated Benchmarks)

- **2025:** Foreign/EM dominated; **S&P 500 +17.9%**; **S&P Developed Ex-U.S. BMI +35.5%**. More than half of the top 50 mutual funds were foreign large-cap or EM.  
- **Sector standouts:** Precious metals (record gold), semiconductors (e.g. Fidelity Select Semiconductors, Communication Services).  
- **Takeaway:** Top *mutual fund* returns in 2025 were in the **mid-20s to 50%+** for niche categories (international, sector), but with **high volatility and concentration**. Our bundles target **12–26%** with **controlled vol and diversification across sleeves**, which is comparable to or better than **top large-cap diversified** funds (12–19% long-term) on a risk-adjusted basis.

**Sources:** AAII 2026 Top Mutual Funds Guide (50 best-performing of 2025); InvestGuiding/Fundavia top performers 2025.

### 8.3 Managed Futures / Trend Following (Uncorrelated Alternative)

- **2025:** Trend-following indices (TTU, SG Trend, BTOP50) returned **+1.78% to +2.81%** vs S&P **+17.89%** (trailing 12 months)—a bad year due to whipsaws and consolidation.  
- **Long-term:** Managed futures have delivered **equity-like returns with low correlation to stocks** and **positive returns during equity drawdowns** (e.g. Barclay CTA Index vs S&P over 1980–2024).

**Implication:** Adding a **low-correlation** sleeve (e.g. funding arb, grid) to a directional sleeve (momentum, mean reversion) can improve **overall portfolio Sharpe** even when one sleeve has a down year—consistent with “diversification as the only free lunch” and our Conservative/Moderate bundle design.

**Sources:** Top Traders Unplugged Trend Following Performance (Aug/Dec 2025); AlphaSimplex “Market Cycles and Managed Futures”; LPL “Are Managed Futures Strategies Paying Off in 2025?”; Efficient.com “Why Managed Futures?”

### 8.4 Multi-Strategy Allocation: Dynamic and Volatility-Weighted

- **Dynamic allocation:** Multi-strategy hedge funds using **dynamic allocation** have achieved **Sharpe ratios nearly twice** those of traditional fund-of-funds over the past five years.  
- **Volatility weighting:** When strategies have **very different volatilities** (e.g. funding arb ~0.85% max DD vs momentum), **volatility-adjusted** allocation equalizes risk contribution and improves **out-of-sample Sharpe** vs equal weight.  
- **Higher moments:** Incorporating **skewness and kurtosis** (not just vol) in strategy allocation can further improve efficiency.

**Implication:** Our bundle construction should use **volatility- or risk-parity-style** weights across sleeves (e.g. funding gets a larger capital share per unit risk) and **rebalance from forward stats** (Half-Kelly, win rate, drawdown) so allocation is dynamic, not static.

**Sources:** Archyde “Dynamic Allocation Gives Multi-Strategy Hedge Funds a Sharpe Edge”; Wiley “Efficient Hedge Fund Strategy Allocations – Higher Moments”; SSRN “Asset or Strategy Allocation for Semi-Optimal Sharpe Ratio”; QuantPedia “Multi Strategy Management for Your Portfolio.”

### 8.5 Diversification Benefit (Uncorrelated Strategies)

- **MPT:** Portfolio variance depends on **correlation (ρ)**. Lower correlation **reduces portfolio vol** for the same expected return; adding a low-correlation strategy can **increase total return** because volatility drag (e.g. 10% loss → 11.1% gain needed to break even) is reduced.  
- **Evidence:** Uncorrelated assets/strategies improve **risk-adjusted returns**; combining **highly correlated** strategies (e.g. multiple similar mean-reversion systems) gives **minimal** diversification benefit.

**Implication:** Our sleeves are chosen to be **genuinely different**: funding (market-neutral), grid (range), mean reversion (retail overreaction), momentum (trend). That maximizes the diversification benefit and supports target Sharpe > 1.0 for Conservative and higher for Moderate/Aggressive.

**Sources:** Investopedia “Protecting Portfolios Using Correlation Diversification”; Quantified Strategies “Uncorrelated Assets And Strategies – Benefits And Advantages”; Rembrandt Capital “Why Diversification Is the Only Free Lunch in Finance.”

### 8.6 Crypto Strategy Bundles (Published and Backtest Evidence)

- **Backtest (Q2 2024):** One automated-trading portfolio reported **~382% return on minimum starting value**, **profit factor 2.78** (hypothetical; futures/crypto).  
- **Systematic crypto (Briplotnik-style):** **Mean reversion** strategies showed **Sharpe ~2.3** post-2021; **momentum** ~1.0–1.2; results **regime-dependent**.  
- **Funding + options hybrid:** Funding arb combined with **protective options** (OTM puts) to reduce tail risk; entry when funding > 0.02% (8h), 2–5x leverage on perps, rebalance at 5–10% price move.

**Implication:** Our blend of **mean reversion** (our 13 survivors), **funding arb**, and **regime-filtered momentum** is aligned with published crypto multi-strategy evidence; adding **vol scaling and regime filters** should keep real-world performance in a similar ballpark to backtests if we avoid overfitting.

**Sources:** Automated Trading Strategies Q2 2024 Backtest Portfolio; Briplotnik systematic-crypto (momentum/mean reversion/vol filtering); Medium “Funding Rate Arbitrage with Protective Options”; 1Token “Strategy Index: Long Short I and Funding Arb II”; Presto Labs “Optimizing Funding Fee Arbitrage.”

### 8.7 Summary: Why Our Bundles Can Outperform Top Mutual Funds

1. **Different game:** We are not long-only equity pickers. We run **uncorrelated systematic sleeves** (funding, grid, mean reversion, momentum), which improves **Sharpe** and **reduces vol drag** vs a single strategy or single asset.  
2. **Benchmark is beatable on risk-adjusted terms:** Most active mutual funds **underperform** the S&P over 10 years. Top *diversified* large-cap funds deliver **12–19%** annualized. Our targets (**12–26%** by bundle) are in that range or above, with **explicit max DD and regime controls**.  
3. **Allocation and rebalancing:** **Dynamic, volatility-aware** allocation (and Half-Kelly on directional sleeves) matches institutional multi-strategy practice and supports **sustained** outperformance vs static equal weight.  
4. **Crypto-specific edge:** Funding arb and grid have **documented** returns (19.26% and 20–50% in range regimes) with **low correlation** to directional crypto; combining them with our **proven** mean-reversion survivors and **academic-backed** 28d/5d momentum gives a realistic path to **top mutual fund–level or better** risk-adjusted returns.

---

## Part 9: Sources (Round 2)

- **Active underperformance:** SPIVA U.S. Scorecard Year-End 2024; Citywire; Morningstar; ETFTrends; Fortune S&P 500 vs active.  
- **2025 mutual funds:** AAII 2026 Top Mutual Funds Guide; InvestGuiding; Fundavia top 10 2025.  
- **Managed futures:** Top Traders Unplugged (TTU, SG, BTOP50); AlphaSimplex; LPL; Efficient.com.  
- **Multi-strategy allocation:** Archyde; Wiley (higher moments); SSRN (semi-optimal Sharpe); QuantPedia.  
- **Diversification:** Investopedia; Quantified Strategies; Rembrandt Capital; Forbes diversification.  
- **Crypto bundles / funding:** Automated Trading Strategies; Briplotnik; Medium (funding + options); 1Token; Presto Labs; Funding Rate Tracker; CoinCryptorank.

---

## Part 10: Deep Research (Round 3) — Academic and Empirical Evidence

### 10.1 Crypto Systematic Strategies: Documented Sharpe and Drawdown

- **AdaptiveTrend (2022–2024):** Trend-following with adaptive portfolio construction on 150+ crypto pairs achieved **Sharpe 2.41**, **max DD -12.7%**, **Calmar 3.18**—outperforming TSMOM and buy-and-hold. Uses 6h intervals, dynamic trailing stops, volatility scaling, rolling Sharpe-based asset selection, and 70/30 long-short asymmetry.  
- **Volatility-scaled portfolios:** Adaptive risk allocation in crypto improves risk-adjusted returns; strategies remain effective under transaction costs and leverage constraints.  
- **2025 systematic review:** Persistent inefficiencies in cross-exchange arb, factor investing (size, momentum, liquidity), and on-chain signals; ML (N-BEATS, CNN-LSTM) outperforms traditional stats.

**Implication:** Our target Sharpe > 1.0 for Conservative and > 1.2 for Moderate is **conservative** vs. documented adaptive crypto strategies (2.41). Our max DD targets (12–25%) are in line with academic evidence (-12.7% for a strong strategy).

**Sources:** arXiv 2602.11708 “Systematic Trend-Following with Adaptive Portfolio Construction”; SSRN “Quantitative Alpha in Crypto Markets”; SSRN “Adaptive Risk Allocation in Crypto Markets”; MDPI “Timing Usage of Technical Analysis in Cryptocurrency Market.”

### 10.2 Kelly Criterion: Why Half-Kelly Wins in Practice

- **Textbook vs reality:** Full Kelly systematically **overstates** position size; historical data reduces optimal leverage by **22–36%** vs theory when accounting for fat tails and discrete rebalancing.  
- **Half-Kelly:** Delivers ~**75%** of optimal growth while cutting variance by ~**50%**; more resilient to estimation error and psychological stress.  
- **Quote:** “In theory, Kelly bets most when your edge is highest. In practice, Kelly bets most when your mistakes are biggest.”  
- **Risk-constrained Kelly:** Adding explicit drawdown-probability constraints via convex optimization can outperform fractional Kelly for equivalent drawdown risk.

**Implication:** Our use of **Half-Kelly** on directional sleeves is empirically justified; it trades some growth for stability and robustness to parameter error. Consider **risk-constrained Kelly** (drawdown cap) for future refinement.

**Sources:** ResearchGate “Long-term capital growth: Kelly and fractional Kelly”; Frontiers “Practical Implementation of the Kelly Criterion”; arXiv 1603.06183 (risk-constrained Kelly); Academic Signal “Kelly in the Real World”; McGinnis/Harry Crane on fractional Kelly.

### 10.3 Regime-Switching Allocation: Asset-Specific Signals

- **2024 factor allocation:** Integrating **asset-specific or factor-specific regime forecasts** (sparse jump model) into Black-Litterman improved **information ratio from 0.05 to ~0.4** vs market and **0.4–0.5** vs equally weighted; **reduced max drawdown**.  
- **Multi-asset (1991–2023):** Hybrid unsupervised regime ID + supervised gradient-boosted trees across equities, bonds, real estate, commodities **consistently outperformed** min-variance, mean-variance, and naive diversified portfolios.  
- **Insight:** Single broad economic regimes underperform; **asset-specific regime forecasts** enable tailored allocation and capture factor cyclicality.

**Implication:** Our **SMA(50)/ADX regime filter** is a simplified version of this; moving toward **asset-specific** (e.g. BTC regime vs ETH vs per-strategy) could further improve allocation. The documented IR improvement (0.05 → 0.4) supports regime-aware design.

**Sources:** arXiv 2410.14841 “Dynamic Factor Allocation Leveraging Regime-Switching Signals”; SSRN 4960484; MDPI “Regime-Switching Asset Allocation”; SSRN 4864358 “Dynamic Asset Allocation with Asset-Specific Regime Forecasts.”

### 10.4 Institutional Funding Carry and Portfolio Allocation

- **Delta-neutral funding carry:** In **neutral funding** environments, delta-neutral strategies achieved **16% annualized** with **6.1 Sharpe**; when funding is strongly positive, capture carry with reduced liquidation risk vs leveraged directional bets.  
- **Core-satellite allocation:** Institutions use 60–80% BTC (core), 15–25% ETH, 5–10% alts; conservative 80/15/5, moderate 70/20/10, aggressive 60/25/15.  
- **Basis trading structures:** (1) Spot–futures cash-and-carry, (2) spot–perpetual funding capture, (3) perp–perp cross-exchange basis. All delta-neutral, repeatable, direction-independent.

**Implication:** Our **50% funding arb** in Conservative and **25–35%** in Moderate/Aggressive aligns with institutional use of funding carry as a **core income sleeve**. The 16% ann. / 6.1 Sharpe in neutral funding supports our 19.26% target (which includes positive-funding regimes).

**Sources:** CryptoProfitCalc “Most Effective Funding Rate Strategy 2026”; XBTO “Crypto Portfolio Allocation 2026 Institutional Guide”; Decentralised.news “Crypto Basis Trading 2026”; Sandmark “Bitcoin Carry Curve”; AInvest “Bitcoin Futures Funding Rates.”

### 10.5 Backtest to Live: Realistic Performance Expectations

- **Typical decay:** Live underperforms backtest due to overfitting, execution friction (slippage, partial fills, latency), regime change, and data issues. One documented case: **25.65% backtest → 24.23% live** (~1.4% decay); Sharpe 2.31 → 2.09.  
- **Rule of thumb:** A **45% backtest return** might deliver **~25% live** after friction—still profitable alpha. Reduce trade frequency **30–50%** to focus on highest-conviction signals.  
- **Mitigation:** Walk-forward testing, adaptive limit orders, position sizing ≤ 5% of average daily volume, kill switches on slippage, continuous monitoring of live vs backtest gap.

**Implication:** Our target returns (12–26%) should be treated as **forward/live targets**, not backtest. Building in **30–50% decay buffer** from theoretical backtest would mean we need backtest-level 20–40% to achieve 12–26% live—consistent with our sleeve return assumptions if we avoid overfitting and control friction.

**Sources:** Backtestra “Why Most Trading Strategies Fail After Backtesting”; Medium/Kryptera “Strategy Fails in Walk-Forward Stress Tests”; AutoTradeLab “How to Salvage Strategies That Backtest Perfectly”; AlgoStrategyAnalyzer “Validate Trading Strategy 2026”; Quantified Strategies “Backtest vs Live Trading”; TuringTrader; Kryll.io.

### 10.6 Crypto–Equity Correlation and Diversification

- **2024:** Crypto–S&P 500 correlation hit **~0.67** (40-day, 100 largest assets)—second-highest ever after 0.72 in Q2 2022; driven by Fed policy and macro.  
- **Longer-term (2021–2024):** BTC and ETH showed **2–28%** correlation with major asset classes; BlackRock calls Bitcoin a “unique diversifier” with cyclical correlation (high in stress, decoupling in bull runs).  
- **Market-neutral sleeves:** Funding arb and grid have **low correlation to directional crypto** and **near-zero to equities**; they can improve portfolio Sharpe even when crypto-equity correlation is elevated.

**Implication:** Our bundles are **crypto multi-strategy**, not pure long crypto. The **market-neutral sleeves** (funding, grid) provide diversification *within* crypto and relative to directional beta. If crypto–equity correlation stays high, our **low-equity-beta** design (market-neutral heavy) remains a differentiator vs long-only mutual funds.

**Sources:** Fortune “BlackRock Bitcoin Unique Diversifier”; Crypto-Economy “Crypto S&P 500 Correlation Record High”; AICoin; BNN Bloomberg “Crypto Correlation With US Stocks”; 21Shares “Cryptoassets in Diversified Portfolio Q4 2024.”

### 10.7 Summary: Round 3 Takeaways

1. **Academic crypto strategies** achieve Sharpe 2.4+ and max DD -12.7%; our targets are conservative.  
2. **Half-Kelly** is empirically superior to full Kelly; risk-constrained Kelly is a future upgrade.  
3. **Asset-specific regime forecasts** improve IR from 0.05 to 0.4; our SMA/ADX filter is a start.  
4. **Institutional funding carry** delivers 16% / 6.1 Sharpe in neutral funding; our allocation is aligned.  
5. **Backtest→live decay** of 30–50% is common; target returns as live, not backtest.  
6. **Crypto–equity correlation** is cyclical; market-neutral sleeves retain diversification value.

---

## Part 11: Sources (Round 3)

- **Crypto systematic:** arXiv 2602.11708; SSRN 5225612, 5090097; MDPI 15/23/12802.  
- **Kelly:** ResearchGate 227623956; Frontiers 577050; arXiv 1603.06183; Academic Signal; McGinnis; Harry Crane.  
- **Regime switching:** arXiv 2410.14841; SSRN 4960484, 4864358; MDPI 13/17/2837.  
- **Funding / institutional:** CryptoProfitCalc; XBTO; Decentralised.news; Sandmark; AInvest.  
- **Backtest vs live:** Backtestra; Medium/Kryptera; AutoTradeLab; AlgoStrategyAnalyzer; Quantified Strategies; TuringTrader; Kryll.  
- **Crypto correlation:** Fortune; Crypto-Economy; AICoin; BNN Bloomberg; 21Shares.

---

## Part 12: Deep Research Rounds 4–13 — Strategy Areas We May Have Missed

*Engineered topics based on strategy areas under-researched in prior rounds.*

### Round 4: Options / Volatility Selling (Strangles)

- **Short strangle:** Sell OTM call + put; profit when price stays between strikes; unlimited loss if large move.  
- **Long strangle:** Buy OTM call + put; defined risk, unlimited upside; best before catalysts (Fed, elections).  
- **IV focus:** Strangles thrive in high IV; crypto IV often 20–40% above realized.  
- **2024:** Long strangle gained attention around U.S. election, Fed decisions; benefits from either rally or pullback.

**Implication:** Vol risk premium (P3 in our roadmap) has structural edge; requires Deribit/options access. Consider as **future sleeve** when infrastructure exists.

**Sources:** CoinUnited; ASX; CME Group; OKX strangle guide.

### Round 5: Cross-Exchange Arbitrage

- **Triangular arb:** 4,879 opportunities on Binance (BTC/LTC/USD) in one study—but **transaction costs, slippage, liquidity eliminate profitability**; markets are efficient.  
- **Cross-exchange spreads:** BTC arbitrage spreads **8.67–15.69%** across 80 exchanges (2019–2023); higher on non-trustworthy/DEX.  
- **Strategies:** Spot-spot (pre-positioned inventory), spot-perpetual (funding), transfer arb.  
- **Execution:** Rapid response, liquid pairs, fee/slippage/transfer cost management critical.

**Implication:** Triangular arb is **not** a standalone edge for retail; cross-exchange funding (we have) and spot-perp basis are more viable. Focus on funding, not triangular.

**Sources:** ScienceDirect “Exploitability of Triangular Arbitrage”; Cointelegraph; Sharpe AI; SSRN 4816710 “Pricing and Arbitrage Across 80 Exchanges”; CryptoProfitCalc.

### Round 6: BTC Dominance / Altcoin Season Rotation

- **Altcoin Season Index:** 75%+ of top 100 alts outperform BTC over 90d = altseason; &lt;25% = BTC season.  
- **Rotation sequence:** BTC leadership (60%+ dominance) → ETH transition → broad altseason (dominance &lt;60%) → speculative euphoria (&lt;50%).  
- **ETH/BTC ratio:** Most reliable altseason predictor; break above 0.032 with volume → broader alt outperformance.  
- **Duration:** 4–12 weeks for rotations; 6–18 months for full cycles.

**Implication:** Our graveyard has `altcoin_season_rotation` and `btc_dominance_reversal` disabled. Rotation is **tactical**, not systematic; 7-signal checklist and ETH/BTC could inform **regime overlay** (when to favor alts vs BTC) rather than standalone strategy.

**Sources:** Token Metrics; Mudrex; QuantStrategy; Fat Pig Signals; Millionero.

### Round 7: Token Unlock Events

- **16,000+ unlocks analyzed:** **90%** result in negative price pressure; 90% drop 6–22% before, 70% drop 4–24% after.  
- **Team unlocks:** Most severe (-25% avg); investor unlocks more controlled.  
- **Ecosystem unlocks:** +1.18% avg return (exception).  
- **Timing:** Impact begins ~30d before; high negative Twitter sentiment (4.5%+) before unlock → 2–14% rebound post-unlock (buy opportunity).

**Implication:** **Token unlock short** is a documented edge (we have in alpha_engine); team unlocks are highest conviction. Add **sentiment filter** (Twitter) for post-unlock mean reversion; consider as **event-driven sleeve** in Aggressive bundle.

**Sources:** Medium (Andreas Stegusks); OKX; NextAlpha; Gate.io “16,000+ Token Unlocks”; The Block Beats.

### Round 8: DeFi Staking / Restaking Yield

- **Base ETH staking:** 3–4%; **restaking (EigenLayer):** 4.8–6%; aggressive multi-AVS ~7–10%+.  
- **EigenLayer:** $15B+ TVL, 93.9% share (Feb 2026).  
- **Risks:** Slashing, smart contract, LRT de-pegging, coordination risk.  
- **Asset-agnostic:** Symbiotic, Karak support ERC-20, stablecoins, wBTC.

**Implication:** **Passive yield** (3–10%) beats our current 0.9%; low correlation to trading. Consider as **capital allocation** for idle cash (not trading capital) or as **Conservative bundle** satellite when on-chain infra is ready.

**Sources:** Exmon; Coira; Token Tool Hub; Coin Bureau; PistachioFi.

### Round 9: BTC-DXY Correlation (Cross-Asset Macro)

- **Inverse correlation:** DXY up → BTC down; dollar strength reduces liquidity and risk appetite.  
- **June 2025:** DXY 105.80 → BTC below $63K; Nov 2025 DXY &gt;100 → headwind for crypto.  
- **Caveat:** Correlation is **dynamic**; stress periods tighten it; avoid fixed correlation alone.

**Implication:** DXY can **gate** directional entries (e.g. no long when DXY breaking out). We have `crypto_dxy_funding_squeeze_v1` in cursor_ai; DXY as **regime filter** (not signal) is supported.

**Sources:** Blockchain.News; BeInCrypto; TradingView; CoinDesk.

### Round 10: Fee Optimization (Maker/Taker, Rebates)

- **Maker vs taker:** Maker (limit) often lower or rebate; taker (market) higher. Binance Futures: 0.02% taker, 0.01% maker rebate at top tier.  
- **Impact:** 20% gain minus 2% fees = 18% net; every basis point compounds.  
- **Tactics:** Limit orders for maker; tier optimization; multi-venue routing; TCA (queue position, rebate timing).  
- **Fee cap:** 0.5% of position; consolidate trades.

**Implication:** **Critical for live**; our backtest-to-live decay is partly fee/slippage. Use limit orders, track tier, model 0.15–0.5% round-trip in backtests.

**Sources:** Axon; AlphaExCapital; Binance Blog; TradingBrowser.

### Round 11: Slippage & Market Impact Modelling

- **Dynamic slippage:** Vol (higher vol → more slippage), order size vs liquidity, bid-ask spread, time of day.  
- **Rule of thumb:** 0.05–0.1% top-10 coins; 0.5–2% outside top-100; 5–10% microcaps.  
- **Round-trip:** Optimistic 0.15%, moderate 0.3%, conservative 0.5%.  
- **Stress test:** 2× historical spread, 100–200ms latency, full taker fees.

**Implication:** Our **30–50% backtest→live decay** assumption should include: 0.3% round-trip, 0.1% slippage for majors, 2× spread in stress. Talos-style impact models for large orders.

**Sources:** Hyper Quant; Medium (ts_sphere); Talos; Stephen Diehl; Paybis.

### Round 12: Machine Learning (N-BEATS vs LSTM)

- **N-BEATS** outperforms LSTM and Linear Regression for BTC price prediction (2025 study); better at capturing temporal dependencies.  
- **Systematic review:** ML (N-BEATS, CNN-LSTM) outperforms traditional stats for crypto; useful for “decisions and risk management.”  
- **Caveat:** Point forecasts are noisy; ML may overfit; regime-dependent.

**Implication:** **ML as signal enhancer** (not replacement) for our 28d/5d momentum or regime filter is a future upgrade. N-BEATS for spread forecasting in pairs trading (Frontiers 2026) is promising.

**Sources:** EAI N-BEATS Bitcoin; Springer “Copula-based cointegrated”; Frontiers “Deep learning pairs trading.”

### Round 13: On-Chain (MVRV), OI Divergence, Pairs (Copula)

**MVRV:**  
- **&lt;1.0:** Undervalued, accumulation; **3.5+:** Overheated, top.  
- **365d MA:** Cross above = bullish; cross below = bearish.  
- **Cycles:** Peak MVRV declined (6.0 in 2013 → 3.7 in 2021); maturing market.

**OI Divergence:**  
- **OI↑Price↓:** Bearish divergence, liquidation cascade risk (most actionable).  
- **OI↓Price↑:** Organic rally (healthier).  
- **Thresholds:** 7d OI ±15% + opposite price ≥5%; 30d OI ≥25% + opposite price ≥10%.  
- **Caveat:** Use USD-denominated OI; avoid coin-margined inflation.

**Pairs (Copula):**  
- **Copula-based** cointegrated pairs trading **outperforms** standard cointegration (Springer 2024).  
- **Deep learning + LSTM** improves spread forecasting.

**Implication:**  
- **MVRV** as regime/overlay (not entry): &lt;1 = favor accumulation; 3.5+ = reduce risk.  
- **OI divergence** is in our alpha_engine (`oi_price_divergence`); OI↑Price↓ = bearish signal.  
- **Copula pairs** are a future upgrade path for our cointegration sleeve.

**Sources:** Glassnode; CryptoQuant; TradingView MVRV; Axel Adler OI; Gate.io derivatives; Decentralised.news; Springer “Copula-based cointegrated”; Frontiers pairs trading.

### Summary: Rounds 4–13 — Strategy Gaps and Priorities

| Area | Priority | Action |
|------|----------|--------|
| Vol selling (strangles) | P3 | Add when Deribit/options infra |
| Triangular arb | Low | Skip; costs eliminate edge |
| Altcoin rotation | Low | Use as regime overlay, not standalone |
| Token unlocks | P2 | Add event-driven sleeve; team unlocks highest conviction |
| DeFi restaking | Passive | Idle capital allocation; 3–10% |
| BTC-DXY | Low | Regime filter for directional entries |
| Fee optimization | P0 | Limit orders, tier tracking, 0.3% round-trip in backtest |
| Slippage modelling | P0 | 0.1% majors, 2× spread stress; Talos-style for large |
| ML (N-BEATS) | P3 | Signal enhancer for momentum/pairs |
| MVRV / OI / Copula | P2 | MVRV overlay; OI divergence (have); Copula pairs upgrade |

---

## Part 13: Sources (Rounds 4–13)

- **Options:** CoinUnited; ASX; CME; OKX.  
- **Cross-exchange:** ScienceDirect; Cointelegraph; Sharpe AI; SSRN 4816710; CryptoProfitCalc.  
- **Rotation:** Token Metrics; Mudrex; QuantStrategy; Fat Pig Signals; Millionero.  
- **Token unlocks:** Medium; OKX; NextAlpha; Gate.io; The Block Beats.  
- **DeFi:** Exmon; Coira; Token Tool Hub; Coin Bureau; PistachioFi.  
- **DXY:** Blockchain.News; BeInCrypto; TradingView; CoinDesk.  
- **Fees:** Axon; AlphaExCapital; Binance; TradingBrowser.  
- **Slippage:** Hyper Quant; Medium; Talos; Stephen Diehl; Paybis.  
- **ML:** EAI N-BEATS; Springer Copula; Frontiers pairs.  
- **On-chain / OI / Pairs:** Glassnode; CryptoQuant; TradingView; Axel Adler; Gate.io; Decentralised.news; Springer; Frontiers.

---

*Report compiled 2026-03-01. Parts 8–13 added after extensive second-, third-, and fourth-round research (10 rounds on missed strategy areas). Performance targets are forward-looking and not guaranteed. Past performance (mutual fund or crypto) does not guarantee future results.*
