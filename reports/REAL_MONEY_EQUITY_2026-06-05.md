# EQUITY Real-Money Picks — 2026-06-05

**Date:** 2026-06-05
**Author:** claude-sonnet-4.6 (Goal #1 — `/audit` EQUITY)
**Status:** **4 candidate picks with LOW–MED confidence. No HIGH-conviction real-money deployment recommended.**

---

## 0. Methodology + Data Sources

**Sources (all verified, no DB-trading-picks):** `data/earnings/{TICKER}/latest.json` (yfinance, 19 tickers), `stock_ohlcv` 1h bars (109k rows, last 2026-06-04 19:30 UTC), `audit_dashboard/data/ai_tournament_picks_latest.json` (1,323 EQUITY picks), `alpha_engine/data/macro_factors_snapshot.json` (NEUTRAL).

**Method:** Score 19 tickers on (a) beats/last 7q, (b) avg surprise %, (c) days to next earnings. Cross-check with AI-tournament OPEN LONG consensus. PEAD hypothesis: 30d forward return after historical beat, computed from 1h OHLCV (n=1 per ticker only — 1h bars span <1y). Cap: quarter-Kelly 2% per pick, 5% total EQUITY.

**Limitations:** 1h OHLCV <1y → PEAD backtest is n=1 per ticker (statistically thin). 2026-06-04 closed_at backfill contaminated `trading_picks` per `REAL_MONEY_NO_SURVIVORS_2026-06-05.md`; we ignored that table. Macro NEUTRAL → no overlay, conservative size.

---

## 1. Earnings Beat Scoreboard (all 19 tickers, last 7-8 quarters)

| Ticker | Beats/last_7 | Avg surprise % | Next earnings | Next EPS est |
|---|---:|---:|---|---:|
| **PFE** | **7/7** | +34.35% | 2026-07-29 | 0.68 |
| **GOOGL** | **7/7** | +27.02% | **2026-07-23** | 2.88 |
| **GS** | **7/7** | +17.36% | 2026-07-14 | 13.72 |
| **META** | **7/7** | +14.67% | 2026-07-29 | 7.51 |
| **BAC** | **7/7** | +7.14% | 2026-07-14 | 1.10 |
| **NVDA** | **7/7** | +5.74% | 2026-08-26 | 2.08 |
| **MSFT** | **7/7** | +5.37% | 2026-07-29 | 4.24 |
| **AAPL** | **7/7** | +4.24% | 2026-07-30 | 1.90 |
| AMZN | 6/7 | +26.89% | 2026-07-30 | 1.81 |
| CRM | 6/7 | +14.06% | 2026-09-02 | 3.27 |
| CVX | 6/7 | +10.15% | 2026-07-31 | 5.23 |
| JPM | 6/7 | +8.07% | 2026-07-14 | 5.39 |
| COP | 6/7 | +6.03% | 2026-08-06 | 2.88 |
| JNJ | 5/7 | +15.82% | 2026-07-15 | 2.85 |
| WFC | 5/7 | +7.08% | 2026-07-14 | 1.71 |
| XOM | 5/7 | +3.17% | 2026-07-31 | 3.73 |
| NFLX | 5/7 | +1.42% | 2026-07-16 | 0.79 |
| AMD | 4/7 | +3.91% | 2026-08-04 | 1.61 |
| UNH | 4/7 | +1.00% | 2026-07-28 | 4.85 |
| TSLA | 1/7 | -13.19% | 2026-07-22 | 0.45 |
| XYZ | 1/7 | -17.67% | 2026-05-07 (passed) | 0.87 |

**Tier-1 (7/7 + positive avg):** PFE, GOOGL, GS, META, BAC, NVDA, MSFT, AAPL. **Tier-2 (6/7):** AMZN, CRM, CVX, JPM, COP. **Disqualified:** TSLA, XYZ.

---

## 2. Top 4 Candidates (LONG, 30-60 day PEAD hold into next earnings)

| # | Ticker | Dir | Entry | TP | SL | Conf | Hold | Rationale |
|---|---|---|---:|---:|---:|---|---|---|
| 1 | **MSFT** | LONG | 428.08 | 465 | 410 | **MED** | 30-60d → 07-29 | 7/7, 5.4% surp, **9 OPEN LONG** AI consensus, +5.7% post-beat |
| 2 | **GOOGL** | LONG | 372.33 | 405 | 355 | **MED** | 30-55d → 07-23 | 7/7, 27% surp, **5 OPEN LONG** AI, +8.7% post-beat (soonest) |
| 3 | **GS** | LONG | 1092.74 | 1185 | 1040 | **LOW-MED** | 30-39d → 07-14 | 7/7, 17.4% surp, **no AI coverage**, +7.3% post-beat (already +14% post 30d) |
| 4 | **AMZN** | LONG | 253.91 | 275 | 240 | **LOW-MED** | 30-55d → 07-30 | 6/7, 26.9% surp, 2 OPEN LONG AI, +2.8% post-beat |

**Excluded (with reasons):** PFE (1h -2.8% post-2026-05-05 beat), NVDA (2L/2S split), META (3L/4S contested), AAPL (8L/3S mixed, no 30d test), JPM/BAC (-3.6%/-8.4% post-beat), CRM (90d hold).

---

## 3. Per-Candidate Deep-Dive

### 3.1 MSFT (MED)
7/7 beats, avg +5.37% surp; last close 428.08; 30d post 2026-04-29 beat: +5.66% (424.59→448.64). **9 OPEN LONG, 0 SHORT** in AI tournament (Gemini HIGH, DeepSeek r1 HIGH, Nous Hermes HIGH — cluster TP +6%, SL -3%). **Plan:** entry 428 (limit 425), TP 465 (+8.6%), SL 410 (-4.2%), hold 30-60d.

### 3.2 GOOGL (MED)
7/7 beats, avg +27% surp (skewed by 2026-04-29 +94.3%); last close 372.33; 30d post 2026-04-29 beat: +8.68% (350.02→380.39) — strongest in testable set. **5 OPEN LONG, 0 SHORT** (Gemini HIGH, DeepSeek v3 HIGH ×2). Tournament entries stale ($175 era) — only TP/SL ratios valid. **Plan:** entry 372 (limit 368), TP 405 (+8.8%), SL 355 (-4.7%), hold into 2026-07-23 (soonest earnings).

### 3.3 GS (LOW-MED)
7/7 beats, avg +17.36% surp — most consistent. Last close 1092.74; 30d post 2026-04-13 beat: +7.27% (890.65→955.44). **No AI tournament coverage** (data gap). Price already +14% above 30d target — momentum partly in. **Plan:** entry 1092 (limit 1085), TP 1185 (+8.5%), SL 1040 (-4.8%), hold 30-39d, size 1% NAV (discount for no AI consensus + run-up).

### 3.4 AMZN (LOW-MED)
6/7 beats, avg +26.89% surp; last close 253.91; 30d post 2026-04-29 beat: +2.79% (263.30→270.65). **2 OPEN LONG** (Gemini HIGH, DeepSeek v4 HIGH) — modest consensus, stale prices. **Plan:** entry 254 (limit 250), TP 275 (+8.3%), SL 240 (-5.5%), hold 30-55d.

---

## 4. PEAD Strategy Backtest (30-day forward returns after historical beats, n=1 per ticker)

Computed from `stock_ohlcv` 1h bars (only 1 historical beat testable per ticker since 1h data starts ~early 2026):

| Ticker | Beat date | Surp % | c0 (beat) | c30 (30d) | 30d return |
|---|---|---:|---:|---:|---:|
| GOOGL | 2026-04-29 | +94.30% | 350.02 | 380.39 | **+8.68%** |
| GS | 2026-04-13 | +8.09% | 890.65 | 955.44 | **+7.27%** |
| MSFT | 2026-04-29 | +5.22% | 424.59 | 448.64 | **+5.66%** |
| AMZN | 2026-04-29 | +69.02% | 263.30 | 270.65 | +2.79% |
| PFE | 2026-05-05 | +3.93% | 26.44 | 25.70 | -2.80% |
| JPM | 2026-04-14 | +7.78% | 311.20 | 300.01 | -3.59% |
| META | 2026-04-29 | +7.20% | 669.91 | 632.52 | -5.58% |
| BAC | 2026-04-15 | +8.78% | 54.32 | 49.77 | **-8.39%** |

**Aggregate n=8, WR=50%, mean 30d return = +0.57%, median ~+1.6%.** Half-working PEAD: 4 winners (GOOGL/GS/MSFT/AMZN), 4 losers (PFE/JPM/META/BAC). n=1 per ticker is **directional evidence only**, not a backtest. Picks above use the 4 winners — that's hindsight-screening, so confidence is discounted.

**Honest read:** 50% WR, mean ~0% is consistent with post-2010 academic PEAD literature (decayed substantially; surviving edge ~1-2%/qtr on small-caps, near 0 on mega-caps). Picks are **directional bias + earnings quality**, not statistical edge.

---

## 5. Risk Parameters

| Parameter | Value |
|---|---|
| **Per-pick max** | 2% of NAV (quarter-Kelly) |
| **Total EQUITY sleeve** | 5% of NAV (4 picks × 1.25%) |
| **Sector concentration** | 3 tech (MSFT/GOOGL/AMZN) + 1 financials (GS). Tech 75% — high. Drop AMZN if sector balance critical. |
| **Market beta (avg)** | MSFT ~1.0, GOOGL ~1.05, GS ~1.15, AMZN ~1.2. Sleeve beta ~1.1. |
| **Earnings date concentration** | 3 of 4 report in 30-39d (GS 07-14, GOOGL 07-23, MSFT 07-29), AMZN 07-30. **Clustered risk** — 75% of sleeve prints in 16 days. |
| **Stop discipline** | Stops 4-6% below entry; exit 1-2d before earnings if not at TP (gaps skip stops). |
| **Macro overlay** | NEUTRAL. 10y-2y at +7.5 bp (vs -50 in 2022) — not alarming. |

---

## 6. Failure Modes

1. **PEAD edge decay:** Post-2010 literature: PEAD alpha ~50-100 bps/quarter, mostly small-caps. Mega-cap edge near 0. Our n=8 30d test (50% WR, +0.57% mean) = noise.
2. **Earnings gap:** Stops don't protect gaps. Exit 1-2d before print if not at TP.
3. **Concentrated earnings risk:** 75% of sleeve prints in 16d — single bad print can wipe 2 picks.
4. **Stale AI prices:** GOOGL/AMZN tournament entries at $175/$185 from earlier regime. Trust direction + TP/SL ratios, not absolutes.
5. **Sector concentration:** MSFT/GOOGL/AMZN correlation ~0.7 risk-off. De-concentrate to 1-2 names if needed.
6. **No statistical backtest:** n=1 per ticker; +0.57% mean is single observation, not proof.

---

## 7. Confidence

| Pick | Confidence | Why |
|---|---|---|
| **MSFT** | **MED** | 7/7, 9-AI LONG consensus, +5.7% 30d post-beat. |
| **GOOGL** | **MED** | 7/7, 27% surp, 5-AI LONG, +8.7% 30d, **soonest earnings**. |
| **GS** | **LOW-MED** | 7/7, 17% surp, +7.3% 30d, but **no AI coverage** + price already +14%. |
| **AMZN** | **LOW-MED** | 6/7, 27% surp, 2 AI LONG (modest), +2.8% 30d (weakest drift). |

**Sleeve confidence: LOW-MED.** Directional bet, not quantified edge. **Do not size up.** If any pick -3% adverse pre-earnings, exit and re-evaluate.

**Better than nothing:** Yes — these have more independent support (real earnings, real OHLCV, real AI consensus) than the contaminated `trading_picks` underlying `/audit` EQUITY FAIL status.

**Worse than T2 edge:** Yes — missing ingredient is *quantified* PEAD (paper-trade 20 picks, measure 30d drift, build CI). Picks are a *starting point*, not the conclusion.
