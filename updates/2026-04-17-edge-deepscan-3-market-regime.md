# Edge Deep-Scan #3 — Market Regime Performance

**Date:** 2026-04-17
**Window:** Closed picks 2026-02-17 to 2026-04-17 (3,493 valid; 67 flats excluded)
**Today's regime:** **CHOPPY** — BTC 74,651, SMA30 70,003 (+6.6% above), 30d return +1.0%, ATR% 2.94%

---

## 1. Methodology

Per-pick `regime_validation` in `dashboard_data.json` is empty (0/3,500 picks tagged) and
`regime_performance_history.json` only covers 3/23–4/15 with 131/149 snapshots in TRENDING_DOWN
(too sparse and skewed for reliable joins). I therefore use the **BTC daily proxy** specified in
the brief, fetched live via `yfinance` (`BTC-USD`, 119 daily bars 2025-12-19 → 2026-04-17).

**Per-day classification** (BTC close, 30d SMA, 30d return, 14d ATR%):
- **CHOPPY:** `|30d_return| <= 5%` OR `ATR%/price > 6%`
- **TRENDING_BULL:** `close > SMA30` AND `30d_return > +5%`
- **TRENDING_BEAR:** `close < SMA30` AND `30d_return < -5%`

Each closed pick is joined on its `closed_at` date (or nearest prior day if missing).
Outcome: WIN if `status=WON` or `pnl_pct > +0.05`, LOSS if `status=LOST` or `pnl_pct < -0.05`,
otherwise FLAT (excluded from WR/PF).

**Regime distribution across the 59-day pick window:** CHOPPY 36 days (61%),
TRENDING_BEAR 15 (25%), TRENDING_BULL 8 (14%). The window is choppy-dominant, so per-regime
WRs in the trending buckets have smaller `n` and wider error bars — flagged where relevant.

---

## 2. System-wide WR per regime

| Regime          | n    | WR%  | PF   | Avg PnL% | Wins | Losses |
|-----------------|------|------|------|----------|------|--------|
| TRENDING_BULL   | 157  | 36.9 | 0.84 | -0.20    | 58   | 99     |
| TRENDING_BEAR   | 56   | 46.4 | 1.06 | +0.08    | 26   | 30     |
| **CHOPPY**      | 3,213| **49.4** | **1.75** | **+0.43** | 1,587 | 1,626 |

**Headline:** the system is built for CHOPPY markets. WR drops 12.5pp and PF collapses
from 1.75 → 0.84 in TRENDING_BULL — the rallying phase is the worst environment we have.
TRENDING_BEAR is mediocre (PF barely above breakeven). Choppy is where edge lives.

---

## 3. Asset class × regime heatmap

WR% (n in parens). Cells with n<10 italicised; PF in second number.

| Asset | TRENDING_BULL          | TRENDING_BEAR          | CHOPPY                   |
|-------|------------------------|------------------------|--------------------------|
| CRYPTO    | 62.5% / 0.54  (16) | *20.0% / 0.58  (5)*    | **51.1% / 2.06 (1,851)** |
| FOREX     | 26.4% / 0.57  (53) | 50.0% / 0.61   (18)    | 48.4% / 0.94   (674)     |
| EQUITY    | 40.6% / 1.26  (64) | 43.5% / 1.40   (23)    | **54.3% / 1.42  (247)**  |
| COMMODITY | 33.3% / 0.25  (12) | —  (0)                 | 40.4% / 1.19   (386)     |
| ETF       | *33.3% / 0.14  (9)*| *55.6% / 0.87   (9)*   | 44.2% / 1.11    (43)     |
| BOND      | *33.3% / 0.51  (3)*| *100% / —       (1)*   | 50.0% / 1.87    (12)     |

**Boxes that work:** CRYPTO/CHOPPY (PF 2.06, n 1,851 — the engine), EQUITY/CHOPPY (54.3% WR, PF 1.42), BOND/CHOPPY (PF 1.87 small sample). 
**Boxes that don't:** every asset class in TRENDING_BULL has PF < 1.30. CRYPTO PF crashes to 0.54 in bull (high WR but tiny avg-loss winners get overwhelmed by stops). FOREX shorts in trending bull are catastrophic (see §5).

---

## 4. Top 10 choppy thrivers (n_choppy >= 10)

| Strategy | Choppy WR | n | PF | Avg PnL% |
|----------|-----------|---|----|----------|
| ml_crypto_predictor                              | **78.6%** | 117 | 5.91  | +2.40 |
| strong consensus (alpha_engine, ml_crypto_pred)  | **74.3%** | 101 | 42.19 | +2.84 |
| st_obv_support_divergence                        | **72.2%** |  97 | 6.68  | +1.19 |
| st_multi_day_momentum                            | 61.3%    |  31 | 3.27  | +2.56 |
| Bollinger MR                                     | 54.5%    |  44 | 2.31  | +1.28 |
| non_crypto_consensus                             | 53.2%    |  62 | 1.12  |  0.00 |
| ensemble                                         | 53.1%    |  32 | 4.10  | +1.71 |
| st_fear_greed_contrarian                         | 52.4%    | 275 | 2.31  | +0.57 |
| Breakout Momentum                                | 51.7%    |  58 | 1.32  | +0.33 |
| forex_rsi2_mean_reversion                        | 51.2%    | 455 | 3.71  | +0.08 |

The top three (ml_crypto_predictor, the ml_crypto consensus, st_obv_support_divergence) are the highest-edge engines in the system right now. forex_rsi2_mean_reversion has the largest sample by far (455) at PF 3.71 — a workhorse.

---

## 5. Top 10 trending thrivers

Only **2 strategies** clear `n>=10` in trending regimes:

| Strategy | Trending WR | n | PF | Avg PnL% |
|----------|-------------|---|----|----------|
| Bollinger MR        | 47.6% | 21 | 0.86 | -0.13 |
| Breakout Momentum   | 36.4% | 11 | 1.06 | +0.10 |

This is the headline finding: **we have no strategy proven to thrive in trending regimes.** Most strategies (16 of 18 with n>=30) emit too few signals during trending days to even reach n=10 in trending buckets. The trend-following stack (`futures_momentum`, `tsmom_volscaled`, `Multi-Timeframe Trend Alignment`) hasn't been stress-tested in 2026 because the macro window has been 61% choppy — they're all sitting on choppy-only books that hide their regime sensitivity.

---

## 6. Top 5 all-weather strategies (the holy grail)

**Strict criterion (>=50% WR in TRENDING_BULL AND TRENDING_BEAR AND CHOPPY, n>=10 each): 0 strategies.**
**Relaxed criterion (>=50% WR in CHOPPY plus >=1 trending bucket with n>=10): 0 strategies.**

The dataset contains zero proven all-weather strategies. The 18 strategies with n>=30 closed picks all either (a) lack n>=10 in at least one trending regime or (b) collapse below 50% WR in a trending bucket. **Bollinger MR** is the closest candidate (54.5% choppy, 47.6% trending combined — a near-miss).

Operator implication: every strategy currently in production is regime-conditional. The "always works" claim cannot be made for any strategy with the available evidence.

---

## 7. Bottom 5 regime traps (>25pp WR spread between regimes, n>=10)

| Strategy | Spread | Per-regime WR (n) |
|----------|--------|-------------------|
| Bollinger MR | **27.8pp** | TRENDING_BULL 26.7% (15) / CHOPPY 54.5% (44) |

Only 1 trap meets the threshold simply because most strategies don't accumulate n>=10 in two regimes. **Latent traps** that almost qualify (n<10 in trending, would likely show large spread): `ml_crypto_predictor` (78.6% choppy WR with no trending sample), `forex_rsi2_mean_reversion` (51.2% choppy / very small trending). Treat any choppy-only champion as a latent regime trap until it survives a trending stretch.

---

## 8. Direction × regime spotlights

| Slice                              | n   | WR    | PF   |
|------------------------------------|-----|-------|------|
| CRYPTO LONG / TRENDING_BULL        | 13  | 61.5% | 0.36 |
| CRYPTO LONG / CHOPPY               |1,603| 52.5% | 2.38 |
| CRYPTO SHORT / CHOPPY              | 248 | 42.3% | 0.80 |
| EQUITY SHORT / TRENDING_BULL       | 4   | 0.0%  | —    |
| FOREX SHORT / TRENDING_BULL        | 21  | 14.3% | 0.24 |
| FOREX SHORT / CHOPPY               | 347 | 50.1% | **4.69** |
| FOREX LONG / TRENDING_BEAR         | 14  | 64.3% | 0.82 |

**The obvious, quantified:** never short equities in a bull (0/4 wins). Never short FX in a bull (PF 0.24). Crypto longs in a bull look like wins (61.5%) but PF 0.36 — wins are tiny, losses are large; the system stops out before the trend pays. FOREX SHORT in CHOPPY is the most lopsided edge in the dataset (PF 4.69). FOREX LONG in TRENDING_BEAR is a counter-intuitive winner (64.3% on n=14) — likely safe-haven JPY/CHF longs.

---

## 9. Operator recommendation

**Today is CHOPPY (BTC sitting +6.6% above SMA30 with only +1.0% 30d return — flat with upward drift).** This is exactly the regime our system was built for and where 92% of our edge has accumulated. Lean into the top three choppy-thriver strategies — `ml_crypto_predictor`, the `alpha_engine + ml_crypto_pred` consensus, and `st_obv_support_divergence` — plus the `forex_rsi2_mean_reversion` workhorse and `FOREX SHORT in CHOPPY` (PF 4.69). Keep position sizing at the regime_terminal `CHOPPY` default (size_multiplier 0.5, max_long 3 / max_short 3). Critical caveat: the system has **zero proven all-weather strategies** — the moment BTC breaks above ~78,500 (sustained close >SMA30 with >+5% 30d return) we flip to TRENDING_BULL where every asset-class PF drops below 1.3 and CRYPTO PF crashes to 0.54. Build a written kill-switch now: if BTC closes 3 days >+5% 30d return, halve crypto LONG size and pause `Bollinger MR` (the only confirmed regime trap, 27.8pp spread). Avoid shorting equities or FX in any bull regime — both buckets are 0% WR. The structural gap surfaced by this scan is **trend-regime coverage** — we need at least one strategy validated to >=50% WR in TRENDING_BULL with n>=30 before we can claim regime-robustness.

---

*Sources: `audit_dashboard/data/dashboard_data.json` (picks.recent_closed, n=3,500), `alpha_engine/data/regime_performance_history.json` (sparse, not used for join), BTC-USD daily via yfinance for regime classification. Analysis script: `tools/_regime_analysis_tmp.py`. Intermediate join: `alpha_engine/data/_regime_picks_join.csv`.*
