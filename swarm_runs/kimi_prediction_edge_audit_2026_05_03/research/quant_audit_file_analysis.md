# Phase F: File Intake & Deep Analysis

## File Inventory

| # | File | Type | Size | Summary |
|---|------|------|------|---------|
| 1 | FOOLPROOF_ACTION_PLAN.docx | Document | ~8,500 words | Comprehensive 12-week action plan with per-asset-class analysis, gate recommendations, UI plan, and backtesting protocols |
| 2 | image.png | Screenshot | Dashboard view | Dark-themed audit dashboard showing Crypto (S-Tier 70.4%, A-Tier 42.4%, B-Tier 45.0%, C-Tier 28.1%) and Non-Crypto (Equities 53.1%, Forex 21.4%, Commodities 21.2%, Futures 0.0%, ETFs 52.9%, Bonds 50.0%) panels |
| 3 | image(1).png | Screenshot | Dashboard view | Shows MAJOR GOAL section with per-asset-class PF/WR summary, Tier-2 Proven strategies section, walk-forward OOS metrics, and flagged strategy dropouts |

---

## Per-File Extraction

### File 1: FOOLPROOF_ACTION_PLAN.docx

**Core Themes:**
1. Per-asset-class performance diagnosis and action plans
2. Corrected gate recommendations (R:R floor/ceiling, ml_score thresholds, Kelly sizing)
3. UI/UX redesign (13 tabs → 5 tabs, "High Conviction" as default)
4. Orphaned goldmine code integration (Signal Quality ML, Alpha/Beta benchmark)
5. Backtesting protocol with PSR/DSR requirements
6. 12-week implementation timeline

**Key Claims & Data Points:**
- **1.5-2.0 R:R band is where ALL alpha lives**: PF 5.81, Kelly +47.2%, avg PnL +4.98%
- **R:R >2.0 is catastrophic**: PF 0.35, avg loss -17.88%
- **ml_score >= 0.90 optimal** (66.7% accuracy) vs 0.82 (39.3% accuracy - worse than coin flip)
- **Only 27.3% of picks hit TP or SL within 24h** — 72.7% still open
- **Equity is Crown Jewel**: T1 L100, PF 2.90, WR 59%
- **Crypto S-Tier**: T1, PF 30.17, WR 85.7% — but n=14 (survivorship bias)
- **Crypto C-Tier**: FAIL, PF 0.36, WR 28% — value destroyer
- **Forex**: FAIL post-bug, TRUE WR ~49% (was 0% due to infinite retry loop bug)
- **Commodity**: FAIL, 58% flat exits — strategy finding no real setups
- **Bond**: T3, PF 1.72, WR 50% — blocked by wrong elite_score gate
- **MEME coins**: WR 65.6% but avg PnL -12.96% — "small wins, catastrophic losses"

**Methodology:**
- Shadow data analysis (n=253)
- Independent quant verification with 6+ specialized agents
- Walk-forward out-of-sample validation
- Probabilistic Sharpe Ratio (PSR) and Deflated Sharpe Ratio (DSR) requirements

**Limitations/Caveats:**
- Crypto S-Tier has n=14 — statistically meaningless
- Multiple "THIN" sample sizes flagged throughout
- C-Tier recommendation corrected from hard-suspend to 5% allocation
- Several strategies flagged as "paper trade first" — unverified

---

### File 2: image.png (Dashboard Screenshot)

**Visual Data Extracted:**

**Crypto Panel:**
| Tier | Win Rate | Closed | W/L/F | Profit Factor | Avg PnL/Trade | Overall PnL |
|------|----------|--------|-------|---------------|---------------|-------------|
| S-Tier | 70.4% | 27 | 19/8/0 | 6.80 | +3.44% | +92.91% |
| A-Tier | 42.4% | 304 | 129/175/0 | 1.58 | +0.31% | +95.23% |
| B-Tier | 45.0% | 940 | 423/514/3 | 1.28 | +0.16% | +147.56% |
| C-Tier | 28.1% | 224 | 63/161/0 | 0.56 | -0.55% | -123.53% |

**Non-Crypto Panel:**
| Asset Class | Win Rate | Active/Closed | W/L/F | Profit Factor | Avg PnL/Trade | Overall PnL |
|-------------|----------|---------------|-------|---------------|---------------|-------------|
| Equities & Stocks | 53.1% | 4/256 | 136/105/15 | 1.72 | +0.17% | +233.46% |
| Forex | 21.4% | 2/912 | 195/232/485 | 1.41 | +0.03% | +23.15% |
| Commodities | 21.2% | 0/675 | 143/187/345 | 1.04 | +0.01% | +5.72% |
| Futures | 0.0% | 0/0 | — | — | — | 0.00% |
| ETFs | 52.9% | 0/85 | 45/37/3 | 1.32 | +0.40% | +28.58% |
| Bonds | 50.0% | 0/20 | 10/8/2 | 1.72 | +0.17% | +3.41% |

**Key Observations from Image:**
- Aggregate for Crypto: 42.5% WR, +212.16% PnL (12 active, 1492 closed)
- Aggregate for Non-Crypto: 27.2% WR, +254.43% PnL (6 active, 1948 closed)
- Split by: Score / Source / Strategy buttons visible
- Filter row: All picks | High-grade | Trusted | R:R 1.5+ | Safe symbols | Recent | All | Last 10 | Last 20 | Last 60 | Last 100 | ?Guide

---

### File 3: image(1).png (Dashboard Screenshot - Major Goal Section)

**Visual Data Extracted:**

**MAJOR GOAL Status:**
| Asset Class | PF | WR | n | Status |
|-------------|-----|-------|------|--------|
| EQUITY | 1.41 | 52.7% | 421 | T2 candidate, Scale |
| CRYPTO | 1.25 | 44.6% | 8067 | Sub-T2, cut quan_engine drag |
| ETF | 1.24 | 55.2% | 87 | Borderline T3, n→100 |
| COMMODITY | 1.78 | 46.9% | 750 | Meets T2 PF, lift WR |
| FOREX | 0.27 | 46.4% | 1169 | Sub-floor, investigate-before-kill |
| BOND | 1.72 | 55.6% | 18 | Meets T2 thresholds, n<100 charter floor |

**Tier Definitions:** T1 PF>2/WR>55/MDD<10 (Renaissance), T2 PF>1.5/WR>50/MDD<20 (Institutional), T3 PF>1.2/WR>48/MDD<30 (Retail-OK)

**Walk-Forward OOS Metrics:**
| Class | Folds | OOS WR | OOS Sharpe | Decay | Consistency | Worst-fold WR |
|-------|-------|--------|------------|-------|-------------|---------------|
| COMMODITY | 130 | 43.2% | -2.412 | 0.2 | 36.2% | 0.0% |
| CRYPTO | 302 | 43.0% | -0.242 | 0.1 | 57.3% | 0.0% |
| EQUITY | 47 | 57.9% | 3.527 | 0.2 | 66.0% | 20.0% |
| ETF | 12 | 61.7% | 6.368 | 10.8 | 66.7% | 20.0% |
| FOREX | 177 | 47.5% | -1.406 | 0.1 | 57.6% | 0.0% |

**Tier-2 Proven Strategies (only 1/4 clear strict Tier-2):**
- signal_validation: Tier 2, WR 63.0%, PF 2.58, n=184
- mega_mutation: Building, WR 67.9%, PF 3.19, n=78 (THIN)
- rl_agent: Building, WR 60.0%, PF 2.54, n=5 (THIN)
- claude_gainer: Building, WR 56.2%, PF 2.23, n=32 (THIN)

**Flagged Strategy Dropouts (7d WR >20% below baseline):**
- myfxbook_retail_contrarian, forex_rsi2_mean_reversion, stocks_rsi2_pullback, futures_momentum, ensemble, goldmine_1x_consensus, st_obv_support_divergence, unknown, gainer_compression_relaxed_mut, MomentumEMA, signal_engine_momentum_mut

---

## Cross-File Mapping

### Overlapping Themes:
1. **Asset class health metrics** — All three files agree Equity is best-in-class
2. **Crypto B-Tier as workhorse** — Action plan and dashboard agree
3. **Forex as broken** — Both sources flag forex as failing (but action plan notes bug-fix may help)
4. **R:R 1.5-2.0 as optimal** — Action plan emphasizes this; dashboard has R:R 1.5+ filter

### Contradictions:
1. **Crypto PF**: Dashboard shows aggregate 42.5% WR, action plan shows more granular tier breakdown with S-Tier at 85.7% WR but n=14
2. **Bond status**: Dashboard shows n=20, PF 1.72; Action plan says n=18, "n<100 charter floor" — can't draw conclusions
3. **Commodity status**: Dashboard shows PF 1.78, but action plan says strategy is broken with 58% flat exits — mixed signal
4. **ETF OOS Sharpe 6.368** looks suspiciously high with only 12 folds and 10.8 decay

### Gaps (what files DON'T cover):
1. **No explanation of F-Score vs Score difference** — User explicitly asks about this
2. **No UI walkthrough data** — Which button/filter produces best picks? Need to test live
3. **No penny stock backtest data** — Only 139 shadow picks mentioned, no detailed analysis
4. **No meme coin strategy specifics** — Only aggregate data, no per-strategy breakdown
5. **No closed picks analysis** — User wants swing plays, closed holds analyzed
6. **No ?Guide content** — Need to check what it says
7. **Recent code change impact** — Dashboard shows "resolver fix shipped 2026-04-28" but no detailed impact analysis
8. **HTML bug details** — User mentions weird text but no specifics in files
9. **Quant hedge fund methodology** — Need external research on what professionals would do

## Consolidated Theme List (for Phase 2 Dimension Decomposition):

1. Per-asset-class edge determination (SAFE vs DANGEROUS verdicts)
2. Scoring methodology (F-Score vs Score vs Composite Score)
3. UI/UX analysis (optimal path to best picks)
4. Strategy failure analysis and inverse opportunities
5. Backtesting methodology improvements (quant hedge fund standards)
6. Penny stock profitability for small investors
7. Meme coin predictability and profit potential
8. Risk management and position sizing optimization
9. Technical issues (HTML bugs, dashboard problems)
10. Guide/documentation accuracy
11. Recent code change impact assessment
12. Quantitative validation standards (PSR, DSR, walk-forward)
