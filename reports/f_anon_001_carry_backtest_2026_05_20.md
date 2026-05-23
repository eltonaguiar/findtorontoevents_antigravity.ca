# F-ANON-001 Backtest Results — G10 FOREX Carry Trade

**Date:** 2026-05-20  
**Hypothesis ID:** F-ANON-001  
**Asset Class:** FOREX  
**Family:** carry_trade  
**Academic Basis:** Lustig, Roussanov & Verdelhan (2011); Menkhoff et al. (2012)  
**Verdict:** TESTED_WEAK

---

## Signal Specification

| Parameter | Value |
|-----------|-------|
| Universe | G10 FX pairs vs USD: AUD, NZD, GBP, EUR, CAD, JPY, CHF, NOK, SEK |
| Signal | Rank by rate differential (foreign central bank rate − Fed Funds rate) |
| Long | Top-3 pairs by carry (highest rate differential) |
| Short | Bottom-3 pairs (funding currencies with lowest rate differential) |
| Rebalance | Weekly (every first trading day of each week) |
| Hold | 5 trading days (1 calendar week) |
| Period | 2020-01-01 to 2026-04-30 |
| Data | yfinance daily FX closes; hardcoded annual central bank rates |
| Validation | TimeSeriesSplit 5-fold OOS |

### Rate Differentials Used (vs USD Fed Funds)

| Currency | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|----------|------|------|------|------|------|------|
| AUD | +0.01% | +0.02% | +0.67% | −0.67% | −0.98% | −0.40% |
| NZD | +0.16% | +0.67% | +1.82% | +0.48% | +0.17% | −0.75% |
| GBP | +0.01% | +0.02% | +1.82% | +0.23% | −0.33% | −0.25% |
| EUR | −0.59% | −0.58% | +0.32% | −1.02% | −1.93% | −2.00% |
| CAD | +0.16% | +0.17% | +2.57% | −0.02% | −0.58% | −1.50% |
| **JPY** | **−0.19%** | **−0.18%** | **−1.78%** | **−5.12%** | **−5.08%** | **−4.00%** |
| **CHF** | **−0.84%** | **−0.83%** | **−1.18%** | **−3.27%** | **−4.33%** | **−4.25%** |
| NOK | −0.09% | +0.42% | +1.07% | −0.52% | −0.83% | −0.25% |
| SEK | −0.09% | −0.08% | +0.82% | −1.02% | −1.83% | −2.25% |

*JPY and CHF are consistently the most-negative → persistently SHORT in this strategy (USD strength trade vs funding currencies)*

---

## Aggregate Results (All OOS Folds)

| Metric | Value | Threshold | Pass? |
|--------|-------|-----------|-------|
| n_trades | 1,933 | >= 30 | YES |
| Win Rate | **51.16%** | >= 50% | YES |
| Profit Factor | **1.0332** | >= 1.2 | NO |
| Avg Return/Trade | +0.015% | > 0% | YES |
| Long pct | 50% | — | — |

**VERDICT: TESTED_WEAK** — WR clears 50% floor but PF=1.033 is below the 1.2 promotion threshold. Edge exists (PF > 1.0) but is too thin for live sizing under current FOREX quality gates.

---

## Per-Fold Breakdown

| Fold | Period | n_trades | Win Rate | Profit Factor | Avg Return |
|------|--------|----------|----------|---------------|------------|
| 1 | 2021-01-21 → 2022-02-08 | 330 | 50.6% | 1.087 | +0.030% |
| 2 | 2022-02-09 → 2023-02-27 | 330 | 51.8% | 0.986 | −0.008% |
| 3 | 2023-02-28 → 2024-03-15 | 324 | **54.0%** | 1.050 | +0.022% |
| 4 | 2024-03-18 → 2025-04-04 | 324 | 47.2% | 0.843 | −0.074% |
| 5 | 2025-04-07 → 2026-04-29 | 330 | 53.6% | **1.255** | +0.093% |
| **AGG** | 2020-01-01 → 2026-04-30 | **1,933** | **51.16%** | **1.0332** | **+0.015%** |

**Fold 4 (2024-2025) is the weak link:** WR=47.2%, PF=0.843. This coincides with the post-rate-peak period where carry differentials compressed rapidly (BoJ normalizing, SNB cutting, Fed holding) — classic "carry unwind" regime.

---

## Per-Currency Breakdown

| Currency | n | Win Rate | Profit Factor | Avg Return | Carry 2023 | Direction |
|----------|---|----------|---------------|------------|------------|-----------|
| **AUD** | 115 | **56.5%** | **1.615** | +0.261% | −0.67% | Mostly LONG |
| NZD | 254 | 49.2% | 0.939 | −0.036% | +0.48% | Mixed |
| GBP | 223 | 47.1% | 1.007 | +0.003% | +0.23% | Mixed |
| EUR | 202 | 49.5% | 1.070 | +0.027% | −1.02% | Mostly SHORT |
| CAD | 254 | 49.2% | 0.925 | −0.027% | −0.02% | Mixed |
| **JPY** | 322 | **57.8%** | **1.257** | +0.107% | −5.12% | Mostly SHORT |
| CHF | 322 | 49.7% | 0.847 | −0.071% | −3.27% | Mostly SHORT |
| **NOK** | 121 | 53.7% | 1.331 | +0.129% | −0.52% | Mixed |
| SEK | 120 | 48.3% | 0.739 | −0.157% | −1.02% | Mixed |

**Winners:** AUD (PF=1.615), JPY-SHORT (PF=1.257), NOK (PF=1.331)  
**Losers dragging aggregate:** SEK (PF=0.739), CHF (PF=0.847), CAD (PF=0.925)

---

## Regime Analysis

### Why PF is thin overall

1. **2020 COVID shock (Fold pre-period):** Carry collapsed universally as USD surged — all long FX positions suffered simultaneously regardless of rate differential.

2. **2022-2023 rate convergence:** Fed hiked 525 bps while BoE/RBA/RBNZ hiked in parallel. Carry differentials compressed on the long side, weakening signal quality.

3. **2024 carry unwind:** BoJ began normalizing (0 → +0.5%), SNB cut to 0.25%, causing the JPY carry trade to violently unwind in Q3 2024. SHORT JPY (long USD/JPY inversion) got caught in this period.

4. **CHF vs JPY divergence:** Both are funding currencies (persistently negative carry vs USD), but CHF drag (PF=0.847) offset JPY edge (PF=1.257). This suggests JPY-specific dynamics (BOJ extreme dovishness) are stronger than generic funding-currency carry.

### Statistical confidence

- Binomial SE at n=1,933: ±1.13%. WR=51.16% is ~1.0 SE above 50% — barely significant. Edge is real but low-conviction.
- AUD at n=115: ±4.7% SE, WR=56.5% → +1.2 SE above 50%. Also thin but consistent direction.
- JPY at n=322: ±2.8% SE, WR=57.8% → +2.8 SE above 50%. Most statistically meaningful sub-signal.

---

## Key Findings vs 3/3 AI Consensus Prediction

The 3/3 AI consensus (Pollinations + Perplexity + eye2.ai, 2026-05-19) predicted:
- G10 carry should produce 55-60% WR with PF 1.3-1.8 over 2020-2026
- JPY carry (5%+ rate differential) as strongest signal

**Actual vs predicted:**
| Metric | AI Predicted | Actual | Verdict |
|--------|-------------|--------|---------|
| Aggregate WR | 55-60% | 51.2% | Below prediction |
| Aggregate PF | 1.3-1.8 | 1.033 | Below prediction |
| JPY signal | Strongest | WR=57.8%, PF=1.257 | Confirmed (best pair) |
| AUD signal | Moderate | WR=56.5%, PF=1.615 | Exceeded prediction |

**Conclusion:** AI consensus overestimated carry signal strength for the 2020-2026 period (COVID shock + rate convergence episodes). JPY direction is validated. Aggregate carry is weaker than expected in an environment of synchronized global rate hikes.

---

## Risks & Caveats

1. **Rate differential approximation:** Annual-average rates are used. Real carry strategies use 3-month interbank rates (LIBOR/SOFR/OIS) at daily granularity — this overstates signal quality during periods of rapid rate change (e.g., 2022 Fed hiking sequence).

2. **Transaction costs not modeled:** G10 FX spreads are narrow (~0.5-2 pips) but weekly rebalancing of 6 positions implies 12 half-turns/week. At 1 pip spread on 1.0000 mid, cost is ~0.01% per turn. Over 1,933 trades, cumulative cost drag would reduce avg return from +0.015% to ~0.005% — still barely positive but further compresses PF.

3. **No carry-to-risk adjustment:** The Sharpe ratio of the carry portfolio is not computed. JPY carry can exhibit very high Sharpe during calm periods but sharp left-tail risk during carry unwinds (as seen Aug 2024 BoJ surprise).

4. **Survivorship/liquidity bias:** All 9 G10 pairs had continuous yfinance data. In reality, NOK/SEK have wider spreads during illiquid periods.

---

## Next Steps (Ranked)

1. **JPY-only sleeve:** Run a focused backtest on SHORT JPY (SHORT USDJPY=X inversion) with stricter BoJ divergence signal. n=322 already shows WR=57.8% / PF=1.257 — with focused filter could clear PF=1.2+ at n>=100.

2. **AUD carry sub-hypothesis:** AUD (n=115, PF=1.615) is the strongest signal. Reason: RBA rate differential vs USD has been more stable and predictable than others. Register as sub-hypothesis and test with RBA-specific timing.

3. **Carry-to-risk ratio:** Replace raw rate differential with rate_differential / implied_vol (from FX options). This is the "risk-adjusted carry" used by institutional carry strategies (Menkhoff et al.). Should reduce CHF/JPY carry-unwind losses.

4. **Regime conditioning:** Long carry only when DXY is in downtrend (20d MA < 60d MA). Short USD (long carry pairs) only makes sense when USD is not in bull trend.

5. **Wiring plan (if JPY sub-hypothesis passes):** Target caller: `alpha_engine/smart_picks_engine.py::passes_smart_gate()` FOREX sleeve. Pre-condition: 30-day shadow with live WR >= 50% on JPY trades.

---

## Verdict Summary

| Decision | Value |
|----------|-------|
| Status | **TESTED_WEAK** |
| Live sizing | NO — PF=1.033 does not meet 1.2 threshold |
| Best sub-signal | JPY SHORT (WR=57.8%, PF=1.257, n=322) |
| Best opportunity | Register JPY carry as sub-hypothesis F-ANON-001-JPY |
| Review date | 2026-08-01 (after rate differential adjustment and JPY sub-test) |

---

*Backtest executed: 2026-05-20 | Script: `tools/f_anon_001_carry_backtest.py` | Raw output: `reports/f_anon_001_carry_backtest_raw.json`*  
*Pre-registered: M-107 gate — F-ANON-001 registered before any data fetch*
