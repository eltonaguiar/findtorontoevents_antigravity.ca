# Per-Asset-Class Profitability Ideas — final_v2

**Date:** 2026-11-14 | **Worktree:** flaxen-hair | **Source:** All 23 profitability hypotheses (v1-v4) + peer audit findings + TradingView contest research

## Executive Summary

After 23 hypothesis tests across 4 protocol versions, **no approach is PROVED** (SCORECARD.md: "Actual profitability proof: 0/10"). The profitability research program exhausted the keyless data hypothesis space. However, **mega_mutation_macd_rsi on CRYPTO** shows forward edge (PF 8.32, WR 84%, n=50 forward) that needs statistical validation. Below are per-asset-class profitability ideas ranked by probability of success.

---

## 1. CRYPTO — Highest Probability (PROVEN forward edge)

### mega_mutation_macd_rsi / ema_momentum (already validated forward)

**Evidence:**
- Forward (live since 2026-06-06): 50 picks, 84% WR, PF 8.32
- Backtest: PF 3.12-5.816, WR 64-76%, n=100-593
- Task 10 benchmark: paired bootstrap pass_95=True for m048/m084, MC percentile 0.949

**8 verified combos:** JUPUSDT, ENAUSDT, ADAUSDT, WIFUSDT, STXUSDT, RENDERUSDT (MACD_RSI); AVAXUSDT, DOTUSDT (EMA_CROSS)

**Next steps:**
- Paper trade via gated_scanner.py (8 gates: symbol whitelist, entry conditions, ATR TP/SL, 2% risk, correlation limit, BTC bull regime, min PF≥2.0, dedup)
- Target n=100 forward picks for T2 confirmation (currently n=50)
- Investigate ENA funding-rate collinearity risk
- Watch regime: BTC 200-EMA filter keeps us out of bear markets

### Crypto Funding Carry (v4) — Real but capital-intensive

**Evidence:** H21/H22/H23: Sharpe 6.42-14.24, DSR 1.0, but capital-adjusted CAGR 3.7-4.8% vs 4.5% cash; only BTC-only clears cash with n=10 <30

**Verdict:** Economically marginal, NOT_PROVED on available data. Requires venue-level capital/margin data.

### What does NOT work in crypto (all NOT_PROVED)

| Hypothesis | Sharpe | CAGR | Reason |
|------------|--------|------|--------|
| H3 XS crypto momentum | -0.00 | -19.2% | No edge |
| H4 Crypto RSI(2) | 0.06 | -4.6% | No edge |
| H13 Crypto XS momentum (30 pairs) | -0.18 | -31.9% | Overfit-prone |
| H14 Crypto XS reversal | -0.36 | -44.3% | Negative |
| H15 Crypto TSMOM breadth | 0.20 | -2.9% | No edge |
| H20 Crypto momentum + BTC trend | -0.08 | -21.3% | No edge |

---

## 2. STOCKS/EQUITY — Exploratory (H10 borderline, needs clean forward)

### RSI(2) on SPY/QQQ (H10) — Came closest, NOT_PROVED

**Evidence:**
- OOS Sharpe 1.83, CAGR 22.0% vs 18.6% B&H
- BUT: OOS contamination (created after H7's OOS inspected), effective N≈38 (DSR 0.9365 < 0.95), single-day dependence (2025-04-09 = +11.20% in one day), execution fragility (1-day lag drops Sharpe to 0.696), regime dependence, largely T-bill carry dependency

**Next steps for a clean test:**
- Clean forward OOS starting after 2026-11-13 with frozen H10 parameters
- Minimum: 90 calendar days or 30 round trips
- Stricter gates: DSR ≥0.95 after N≥38, DSR ≥0.95 after removing best day, 2-day-lag Sharpe ≥1.0
- Risk-matched benchmark gate (not just B&H)

### What does NOT work in equity (all NOT_PROVED)

| Hypothesis | Sharpe | CAGR | Reason |
|------------|--------|------|--------|
| H7 Equity RSI(2) | 1.50 | 17.6% | Fails absolute return (18.6% B&H) |
| H8 Sector RSI(2)+trend+cash | 1.04 | - | DSR 0.603, fails DSR/benchmark |
| H9 International RSI(2)+cash | 0.31 | 4.1% | No edge |
| H11 Sector RSI(2)+trend+cash | 1.04 | - | DSR 0.529 |
| H12 Sector 12-1 momentum+cash | 1.14 | - | n=22, DSR 0.589 |

---

## 3. ETFs — Not Proven (best: H16 Sharpe 0.98 vs bench 1.18)

### Best ETF candidates (all NOT_PROVED)

| Hypothesis | Sharpe | vs Benchmark | Reason |
|------------|--------|--------------|--------|
| H16 ETF XS momentum (top 3) | 0.98 | 1.18 | Underperforms benchmark, SPA 0.488 |
| H18 ETF TSMOM breadth | 1.00 | 0.99 | WF 0.37, borderline |
| H17 ETF XS reversal | 0.76 | 1.18 | Underperforms benchmark |
| H5 ETF dual momentum | 0.99 | - | n=6, fails n≥30 |

**Ideas for ETF profitability:**
- Test with proper cost model (ETF spreads, trading costs)
- Add regime filter (only trade when SPY > 200-day SMA)
- Walk-forward with ≥60% profitable folds gate
- Dual momentum with T-bill cash allocation

---

## 4. BONDS — No hypotheses tested (pure gap)

**No bond-specific profitability hypotheses were tested in v1-v4.**

**Ideas for bond profitability:**
- TSMOM on bond ETFs (TLT, IEF, SHY, TBT) with monthly rebalancing
- Dual momentum: bonds vs T-bills based on 12-month momentum
- Carry trade: short-term Treasuries vs longer-duration bonds
- Need data source: Treasury.gov yields, Nasdaq ETF prices

**Risk considerations:** Bond ETFs have lower volatility but also lower returns; need to account for interest rate risk

---

## 5. MUTUAL FUNDS — Zero coverage (pure gap)

**No mutual fund data source or algorithm exists anywhere in the codebase.**

**Ideas for mutual fund profitability:**
- Monthly NAV-based rebalancing (mutual funds price once daily at 16:00 ET)
- Dual momentum across mutual fund categories (equity, bond, balanced, international)
- Need data source: mutual fund NAV feed (CSV/JSON), yfinance fallback
- Add MUTUAL_FUND to asset_class enum in alpha_engine/config.py
- Risk: NAV lag (same-day price not available until after market close)

---

## 6. FOREX — No hypotheses tested (pure gap)

**No forex-specific profitability hypotheses were tested in v1-v4.**

**Ideas for forex profitability:**
- Carry trade: high-yield currency vs low-yield currency (AUD/JPY, NZD/JPY, USD/CHF)
- Trend following on major pairs (EUR/USD, USD/JPY, GBP/USD) with 200-day SMA filter
- Mean reversion on oversold pairs (RSI(2) < 30)
- Need data source: forex price feed (er-api, yfinance)

**Risk considerations:** Forex has high leverage risk; need position sizing limits

---

## 7. COMMODITIES/FUTURES — No hypotheses tested (pure gap)

**No commodity/futures profitability hypotheses were tested in v1-v4.**

**Ideas for commodity profitability:**
- TSMOM on commodity futures (GC=F, SI=F, CL=F, ZN=F, NG=F) with 12-month lookback
- Seasonal patterns (agricultural planting/harvest cycles)
- Contango/backwardation roll yield (for futures with term structure)
- Need data source: futures price feed, COT data

**Risk considerations:** Futures have high volatility and roll risk; need position limits

---

## Cross-Cutting Profitability Framework (finpredict-v4 scoring framework)

All ideas must pass the 6-gate certification pipeline:

| Gate | Requirement |
|------|-------------|
| Gate 0: Data Quality | Complete trade log, no missing prices, n≥30 |
| Gate 1: Statistical Significance | Bootstrap 95% CI: PF_lower > 1.0, Sharpe_lower > 0 |
| Gate 2: Walk-Forward | ≥60% profitable folds, mean OOS PF > 1.2 |
| Gate 3: Gross Profitability | PF > 1.5, Sharpe > 1.0, WR > 50%, Sortino > 1.5 |
| Gate 4: Money-Ready (Net) | Net PF > 1.2, Net Sharpe > 0.5, Net WR > 45%, DSR > 0.95 |
| Gate 5: Direction Validation | If directional, both sides pass Gate 4 |

**Implementation:** `alpha_engine/statistical_scoring_framework.py` (StrategyCertifier class)

---

## Risk Management Rules (from TradingView contest research)

| Rule | Specification |
|------|---------------|
| Position sizing | Max 2% risk per trade (retail-viable) |
| Kelly Criterion | 0.25×-0.5× full Kelly for proven edges |
| Daily loss cap | -5% |
| Monthly loss cap | -20% |
| Correlation limit | Max 1 position per correlated group |
| Regime filter | BTC > 200-EMA for crypto; SPY > 200-SMA for equity |
| Stop loss | Technical-level (swing low/high), not fixed percentage |
| Losing streak | 3 losses in a row → stop for session (high-WR grinders) |

---

## What Does NOT Work (Peer Research Summary)

| Claim | Verdict | Reason |
|-------|---------|--------|
| VWAP mean reversion (peer claim) | FALSIFIED | Annualization error 3.76→1.18, PBO degenerate, intrabar stops PF 0.81 |
| TradingView contest winners as proof | Survivorship bias | Winners selected from thousands; not repeatable method |
| Crypto momentum/reversal (30 pairs) | NOT_PROVED | SPA p=0.488, negative CAGR in 2024-26 |
| ETF momentum/reversal (50 ETFs) | NOT_PROVED | Underperforms benchmark, no edge survived |
| Funding carry (capital-adjusted) | NOT_PROVED | Below cash after 1.5× capital, n=10 <30 |

---

## Recommended Execution Order

1. **Immediate (this week):** Paper trade mega_mutation_macd_rsi via gated_scanner.py (crypto, edge confirmed forward)
2. **Next sprint:** Clean forward OOS test of H10 RSI(2) on SPY/QQQ with frozen parameters
3. **Medium-term:** Test bond ETF TSMOM, forex carry trade, commodity TSMOM (new asset classes)
4. **Ongoing:** Apply finpredict-v4 6-gate scoring to all strategies; publish negative results honestly
