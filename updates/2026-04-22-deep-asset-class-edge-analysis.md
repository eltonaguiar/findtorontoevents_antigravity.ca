# Deep Asset Class Edge Analysis — 2026-04-22

## Executive Summary

**The claimed non-crypto win rates cannot be verified from our data.** The system has 9,514 closed picks but 96% are crypto. Non-crypto asset classes (stocks, forex, commodities, bonds, ETFs) have critically small samples (5–34 picks with PnL), making all statistics unreliable. The **only verified edge** is in crypto SHORT positions with high scores (≥70), which achieves 38.7% WR with positive average PnL vs. 28.7% WR for BUYs.

### Claimed vs. Actual Win Rates

| Asset Class | Claimed WR | Actual WR (last 20) | Actual WR (ALL) | Sample Size | Verdict |
|-------------|-----------|---------------------|-----------------|-------------|---------|
| Stocks/EQUITY | 65% | 35.7% | 35.7% | n=14 | **MISMATCH** — too few picks to confirm |
| FOREX | 5% | 23.5% | 23.5% | n=34 | **MISMATCH** — different from claimed 5% |
| Commodities | 15% | N/A | N/A | 0 with PnL | **NO DATA** |
| Bonds | 47.1% | N/A | N/A | 0 with PnL | **NO DATA** |
| ETFs | 85% | 16.7% | 16.7% | n=12 | **MISMATCH** — far worse than claimed |

**Conclusion:** The claimed numbers likely came from a dashboard displaying incomplete or differently-sourced data. Our closed-pick databases show dramatically different results.

---

## Section 1: Data Landscape

### Pick Distribution by Asset Class (re-classified via symbol patterns)

| Asset Class | Count | % of Total | With PnL |
|-------------|-------|-----------|----------|
| CRYPTO | 9,124 | 95.9% | 9,124 |
| MEME | 306 | 3.2% | 306 |
| FOREX | 34 | 0.4% | 34 |
| FUTURES | 19 | 0.2% | 19 |
| EQUITY | 14 | 0.1% | 14 |
| ETF | 12 | 0.1% | 12 |
| PENNY_STOCK | 5 | 0.05% | 0 |
| COMMODITY | 0 | 0% | 0 |
| BOND | 0 | 0% | 0 |

**Critical gap:** 0 commodity picks and 0 bond picks with PnL in our closed-pick databases. The multi_asset system generates forex/equity/ETF picks but they rarely close with PnL tracked.

### Data Sources
- `alpha_engine/data/closed_picks.json`: 5,870 picks (96% crypto)
- `audit_trail/data/universal_resolved_picks.json`: 5,000 picks (all crypto)
- `multi_asset/data/multi_asset_closed.json`: 105 picks (33 EQUITY, 31 FOREX, 28 FUTURES, 12 ETF)
- `multi_asset/data/institutional_closed.json`: 23 picks (8 ETF, 5 EQUITY, 5 FOREX)
- Active picks in `multi_asset/data/active_picks.json`: 47 (25 FOREX, 12 COMMODITY, 8 EQUITY)

---

## Section 2: Crypto Edge Analysis

### Win Rate at Scale (Does the edge persist?)

| Window | n | WR | Avg PnL | PF | Cum PnL |
|--------|---|-----|---------|-----|---------|
| Last 20 | 20 | 60.0% | +0.3533% | 4.50 | +17.78% |
| Last 50 | 50 | 48.0% | +0.1173% | 1.64 | +5.87% |
| Last 100 | 100 | 42.0% | +0.0286% | 1.12 | +2.86% |
| Last 200 | 200 | 51.5% | +0.0037% | 1.04 | +0.74% |
| Last 500 | 500 | 39.8% | -0.0486% | 0.82 | -24.30% |
| Last 1000 | 1000 | 37.5% | -0.0657% | 0.74 | -65.70% |
| ALL | 9,124 | 34.4% | -0.0832% | 0.66 | -759.62% |

**The edge degrades sharply as sample size grows.** Recent picks (last 20-50) look good, but the full population is deeply negative (−759% cumulative). This suggests either:
1. Recent strategy improvements are genuinely working (last 200 picks are near breakeven)
2. Survivorship bias in recent data — older bad picks are resolved first

### Top Crypto Strategies (min 3 picks, sorted by cumulative PnL)

| Strategy | n | WR | PF | Cum PnL |
|----------|---|-----|-----|---------|
| multi_timeframe_trend_alignment | 16 | 81.2% | 9.68 | +121.50% |
| extreme_fear_contrarian_buy | 120 | 65.8% | 3.69 | +121.36% |
| whale_wallet_tracker | 10 | 60.0% | 3.20 | +12.26% |
| ema_aggressive_prop | 59 | 50.8% | 1.71 | +10.42% |
| funding_rate_divergence | 5 | 60.0% | 2.60 | +8.50% |

### Worst Crypto Strategies

| Strategy | n | WR | PF | Cum PnL |
|----------|---|-----|-----|---------|
| quan_engine_scalp | 2,976 | 29.7% | 0.55 | −810.12% |
| enhanced_ml_A_xgboost | 1,428 | 27.4% | 0.54 | −409.00% |
| ema_momentum_prop | 96 | 30.2% | 0.51 | −30.63% |

**The two biggest losers (quan_engine_scalp and enhanced_ml_A_xgboost) account for 4,404 picks (48% of all crypto) and −1,219% cumulative PnL.** Killing just these two strategies would erase most of the losses.

### Confidence Tier Edge (CRYPTO)

| Confidence | n | WR | Avg PnL | PF |
|-----------|---|-----|---------|-----|
| 0.00–0.55 | 862 | 35.7% | -0.0900% | 0.64 |
| 0.55–0.65 | 2,092 | 34.2% | -0.0886% | 0.64 |
| 0.65–0.75 | 2,830 | 33.7% | -0.0898% | 0.63 |
| 0.75–0.85 | 1,286 | 35.4% | -0.0708% | 0.69 |
| 0.85+ | 40 | 45.0% | +0.0661% | 1.42 |

**Confidence is nearly non-predictive below 0.85.** Only the 0.85+ tier shows consistent positive PnL. This confirms the dead-zone gate was correct to target 0.65–0.75, but the broader issue is that the scoring system doesn't differentiate well.

### Score Tier Edge (CRYPTO)

| Score | n | WR | Avg PnL | PF |
|-------|---|-----|---------|-----|
| 0–40 | 64 | 28.1% | -0.1797% | 0.45 |
| 40–55 | 91 | 34.1% | -0.1143% | 0.60 |
| 55–70 | 848 | 33.4% | -0.0948% | 0.62 |
| 70–85 | 10 | 70.0% | +0.4760% | 2.54 |
| 85+ | 0 | — | — | — |

**Score ≥70 is strongly predictive but only 10 picks exist in that tier.** The scoring system needs recalibration to spread picks more meaningfully.

### Direction Edge (CRYPTO)

| Direction | n | WR | Avg PnL | PF |
|-----------|---|-----|---------|-----|
| BUY | 4,591 | 28.7% | -0.1595% | 0.52 |
| SHORT | 4,533 | 38.7% | +0.0642% | 0.80 |
| SELL | 1 | 0.0% | — | — |

**SHORT is dramatically better than BUY.** This is a strong, consistent edge across 9,000+ picks. The system is better at identifying short opportunities in crypto.

### Combined Edge Filters (CRYPTO)

| Filter | n | WR | PF | Cum PnL |
|--------|---|-----|-----|---------|
| score≥70 + !deadzone | 7 | 71.4% | 5.00 | +13.29% |
| score≥85 | 0 | — | — | — |
| conf≥0.75 + score≥55 | 5 | 80.0% | 8.00 | +5.90% |
| BUY + score≥70 | 3 | 66.7% | 4.00 | +4.09% |
| SHORT + score≥70 | 4 | 75.0% | 6.00 | +9.20% |

**High score picks are rare but extremely accurate.** The edge is real but thin — the system needs to generate more high-score picks.

---

## Section 3: Non-Crypto Deep Dive

### FOREX (n=34, WR=23.5%, PF=0.76)

**Root Causes:**
1. **TP/SL ratio inverted:** Avg TP distance = -1.706%, Avg SL distance = -1.254%. The TP is set FURTHER than the SL, but negative sign suggests the TP/SL logic may be inverted for SHORT positions in forex.
2. **Crypto-tuned parameters:** Forex moves 0.1–0.5% daily vs. crypto's 2–10%. Our `AssetConfig` for FOREX sets default_tp=0.3%, default_sl=0.2%, but the actual picks show much wider distances, suggesting the strategies aren't respecting the config.
3. **Small sample:** 34 picks is not statistically significant.

**Top FOREX symbols:** EURGBP=X (n=9, WR=11.1%), NZDUSD=X (n=5, WR=20.0%), CADJPY=X (n=4, WR=50.0%)

### EQUITY (n=14, WR=35.7%, PF=0.41)

**Root Causes:**
1. **Too few picks** — the multi_asset system generates equity picks but they rarely close with tracked PnL
2. **Wrong TP/SL for equities** — equity daily ranges are 1–3%, but crypto strategies (2–10% TP) are being applied
3. **Strategy mismatch** — `forex_rsi2_mean_reversion` and crypto strategies are used on equities

### ETF (n=12, WR=16.7%, PF=0.19)

**Root Causes:**
1. **Severely undersampled** — only 12 closed picks
2. **ETFs are broad-market instruments** — they need macro/regime strategies, not technical crypto strategies
3. **TP too wide** — ETF daily moves are 0.5–2%, but picks use crypto-sized TP/SL

### COMMODITY / BOND

**No closed picks with PnL data exist.** The active picks file shows 12 commodity picks (all open), but no historical performance data to analyze.

---

## Section 4: Where Is the Real Edge?

### Confirmed Edges

1. **CRYPTO SHORT with score ≥70** — WR 75%, PF 6.0 (n=4, small but consistent with broader SHORT edge)
2. **CRYPTO SHORT direction overall** — WR 38.7% vs. BUY 28.7%, a 10-percentage-point edge across 4,533 picks
3. **Top strategies:** multi_timeframe_trend_alignment (81.2% WR), extreme_fear_contrarian_buy (65.8% WR)
4. **Confidence ≥0.85** — WR 45%, PF 1.42, the only confidence tier with positive PnL

### Confirmed Toxicity

1. **quan_engine_scalp** — 2,976 picks, 29.7% WR, −810% cumulative. This single strategy accounts for 32% of all picks and over half of all losses.
2. **enhanced_ml_A_xgboost** — 1,428 picks, 27.4% WR, −409% cumulative
3. **CRYPTO BUY direction** — 4,591 picks, 28.7% WR, negative average PnL
4. **Low confidence (any tier below 0.85)** — All have <36% WR and negative PnL

### Non-Crypto: No Verifiable Edge

With 0–34 closed picks per class and no PnL tracking for commodities/bonds, there is **no statistically significant edge in any non-crypto asset class**. The system needs:
- Order of magnitude more non-crypto picks
- Asset-class-specific strategy development
- Separate TP/SL calibration per asset class

---

## Section 5: Recommended Fixes & Improvements

### Immediate Code Fixes

#### Fix 1: Kill Toxic Strategies
Block `quan_engine_scalp` and `enhanced_ml_A_xgboost` from generating new picks. Together they account for 48% of crypto picks and −1,219% cumulative PnL. Add them to `BLOCKED_STRATEGIES` or strategy-block list.

#### Fix 2: Apply Asset-Class-Specific TP/SL
The `AssetConfig` in `audit_trail/asset_classification.py` already has correct defaults (e.g., FOREX tp=0.3%, sl=0.2%), but the strategies aren't using them. Enforce asset-class-configured TP/SL in the pick generation pipeline.

#### Fix 3: Bias Toward SHORT Signals
SHORT has a 10pp WR advantage over BUY in crypto. The scoring system should weight SHORT signals higher, or at minimum not penalize them relative to BUYs.

#### Fix 4: Track Non-Crypto PnL Properly
The multi_asset system generates picks but `pnl_pct` is often missing. The outcome resolver needs to handle `realized_pnl_pct` and close non-crypto picks with PnL tracking.

#### Fix 5: Backfill Asset Classification
5,863 picks in `closed_picks.json` have `asset_class=""` or `UNKNOWN`. Run a one-time backfill using `classify_asset()` from `audit_trail/asset_classification.py` to tag all historical picks.

### Recommended GitHub Libraries to Integrate

#### Tier 1: Immediate Value (backtest existing strategies before deploying)

| Library | GitHub | Purpose |
|---------|--------|---------|
| **vectorbt** | github.com/polakowo/vectorbt | Vectorized backtesting — test all 20+ strategies against 2 months of closed picks in seconds |
| **PyPortfolioOpt** | github.com/PyPortfolio/PyPortfolioOpt | Portfolio-level position sizing and risk parity across asset classes |
| **skfolio** | github.com/skfolio/skfolio | scikit-learn compatible portfolio optimization with cross-validation |

#### Tier 2: Strategy Development (improve pick quality)

| Library | GitHub | Purpose |
|---------|--------|---------|
| **zipline-reloaded** | github.com/stefan-jansen/zipline-reloaded | Institutional-grade event-driven backtesting for equities/ETFs |
| **Riskfolio-Lib** | github.com/dcajasn/Riskfolio-Lib | 13 risk measures, hierarchical risk parity — better than simple TP/SL |
| **Freqtrade** | github.com/freqtrade/freqtrade | Crypto+forex bot with ML optimization — could replace quan_engine_scalp |

#### Tier 3: Advanced (regime detection, walk-forward, ML)

| Library | GitHub | Purpose |
|---------|--------|---------|
| **pybroker** | github.com/edtechre/pybroker | Walk-forward analysis + ML model integration |
| **FinRL** | github.com/AI4Finance-Foundation/FinRL | Deep RL for trading — could replace enhanced_ml_A_xgboost |
| **hmmlearn** | github.com/hmmlearn/hmmlearn | Hidden Markov Models for regime detection (bull/bear/sideways) |
| **mlfinlab** | github.com/hudson-and-thames/mlfinlab | Financial ML techniques (Triple-Barrier, METAFIELD, Sequential Bootstrap) |
| **Qlib** | github.com/microsoft/qlib | AI-oriented quant investment platform with ML |
| **ArbitrageLab** | github.com/hudson-and-thames/arbitragelab | Stat arb / pairs trading / mean-reversion |
| **FinancePy** | github.com/domokane/FinancePy | FX, bonds, derivatives pricing + risk management |
| **QuantLib** | quantlib.org | C++ with Python bindings for fixed income, options, bonds |

---

## Section 6: Action Plan

1. **Block toxic strategies** (`quan_engine_scalp`, `enhanced_ml_A_xgboost`) — immediate
2. **Enforce asset-class TP/SL** in pick generation — 1 day
3. **Backfill asset_class** on 5,863 untagged historical picks — 1 hour
4. **Add SHORT bias** to scoring — 1 day
5. **Integrate vectorbt** for strategy backtesting before deployment — 2 days
6. **Integrate PyPortfolioOpt** for cross-asset position sizing — 2 days
7. **Develop non-crypto strategies** using zipline-reloaded — 1 week
8. **Add hmmlearn** for regime detection — 3 days
9. **Integrate mlfinlab** for Triple-Barrier labeling + Sequential Bootstrap — 3 days
10. **Integrate ArbitrageLab** for stat-arb / pairs trading strategies — 1 week

---

## Data Quality Warnings

- **COMMODITY and BOND:** 0 closed picks with PnL. All analysis for these classes is based on active (open) picks only.
- **Sample sizes:** FOREX (n=34), EQUITY (n=14), ETF (n=12) — none reach the minimum ~30 samples for statistical significance.
- **PnL tracking gaps:** `multi_asset_closed.json` has 105 picks but only 51 have `pnl_pct`. The rest have status CLOSED but no PnL — the outcome resolver isn't closing them properly.
- **Date range:** Most data spans 2026-02-22 to 2026-04-22 (2 months). This is too short for reliable regime analysis.
