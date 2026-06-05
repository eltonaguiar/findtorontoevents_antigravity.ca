# BOND Real-Money Picks — 2026-06-05

**Author:** claude-sonnet-4.6
**Date:** 2026-06-05
**Status:** 3 candidates — MUB (MED-HIGH), EMB (MED), TLT (LOW)
**Total BOND exposure cap:** 4.0% portfolio

---

## 0. Methodology + Data Sources

| Source | Status | Used for |
|---|---|---|
| Yahoo Finance OHLCV (^TNX, ^FVX, ^TYX, ^IRX, ^VIX, DX-Y.NYB, TLT, IEF, SHY, HYG, LQD, EMB, TBT, JNK, MUB, TIP, TLH) | LIVE 2026-06-05 | Returns, vol, SMA, RSI |
| `alpha_engine/data/macro_factors_snapshot.json` | LIVE (YAHOO_FALLBACK) | Regime "NEUTRAL", fed_funds=3.755, fed_funds_90d_chg=-13bp |
| `tools/data/fred_macro_context.json` | **DEAD** (FRED API 400) | CPI/HY-OAS not queryable — view adjusted |
| `trading_picks` DB | **EXCLUDED** per task spec (2026-06-04 backfill) | n/a |
| `macro_circuit_breaker.json` | Stale 2026-04-17, OFF | No override |

**OHLCV:** 425d window, 30d vol × √252, Wilder RSI(14), simple SMA20/50.

---

## 1. Macro Regime Read

- **Fed:** funds 3.755%, down 13bp in 90d = easing bias. BUT 10Y yield +42bp in 3m, 5Y +56bp, 30Y +28bp = **term premium re-pricing**. Steepener active (2s10s ~+48bp, 5s30s +79bp).
- **Credit:** HYG 12m +0.44% but 6m -1.07% (range-bound). HY-IG relative +0.84% 60d = slight tightening. VIX 15.4 (down from 90d avg 19) = no recession alarm.
- **Inflation/real yields:** TIP RSI=32 (oversold), TIP 1m -1.23% = real yields rising. FRED CPI dead so no direct read.
- **DXY:** 99.4, +1.85% 90d = USD strength (mild headwind for EMB).
- **Verdict:** Long-end is the pain trade. Avoid duration >7y unless Fed pivots. Edge = carry (short duration + EM + tax-exempt munis).

---

## 2. Bond ETF Scoreboard

| Ticker | Class | 12m | 3m | 30d vol | Above SMA50? | RSI | Sharpe 12m/vol |
|---|---|---|---|---|---|---|---|
| TLT | 20Y+ UST | -1.0% | -4.1% | 8.8% | NO | 55.1 | -0.12 |
| IEF | 7-10Y UST | -0.4% | -2.8% | 5.1% | NO | 48.1 | -0.09 |
| SHY | 1-3Y UST | -0.5% | -0.9% | 1.8% | NO | 42.9 | -0.28 |
| HYG | HY Corp | +0.4% | -0.7% | 4.5% | NO | 49.6 | +0.10 |
| LQD | IG Corp | +0.9% | -1.9% | 5.5% | NO | 53.2 | +0.16 |
| **EMB** | EM Sovereign | **+5.9%** | -0.8% | 6.3% | **YES** | 56.0 | **+0.93** |
| TBT | 20Y+ SHORT 2x | -2.9% | +7.2% | 18.1% | YES | 43.7 | -0.16 |
| JNK | HY Corp | +0.4% | -0.7% | 4.4% | NO | 50.5 | +0.08 |
| **MUB** | National Muni | **+3.5%** | -0.5% | 3.2% | **YES** | 58.4 | **+1.10** |
| TIP | TIPS | +0.7% | -1.3% | 4.3% | NO | 32.2 | +0.17 |
| TLH | 10-20Y UST | -0.4% | -3.7% | 7.9% | NO | 52.9 | -0.05 |

---

## 3. Top 3 Candidates

| # | Ticker | Dir | Entry | TP | SL | Edge | Hold |
|---|---|---|---|---|---|---|---|
| 1 | **MUB** | LONG | 107.19 | 110.50 (+3.1%) | 105.50 (-1.6%) | Lowest vol, full bullish alignment, tax-exempt carry, 12m +3.5% | 60-90d |
| 2 | **EMB** | LONG | 96.10 | 99.00 (+3.0%) | 94.20 (-2.0%) | Highest 12m return (+5.85%), above both SMAs, EM carry vs UST 4.48% | 60-90d |
| 3 | **TLT** | LONG (mean-rev) | 85.50 | 89.00 (+4.1%) | 83.00 (-2.9%) | 60d -3.15%, above SMA20 = short-term turn, Fed easing bias tailwind | 30-60d |

**Rejected:** HYG/JNK (below both SMAs, 6m -1.1%, range-bound); TBT (18% vol, 12m -2.9% = whipsaw); TIP (RSI 32 but below SMAs); SHY (too low vol, no edge).

---

## 4. Per-Candidate Deep-Dive

### 4.1 MUB — LONG (MED-HIGH)
Last 107.19; 60d range 105.60-107.42 (at top, no chase). SMA20=106.65, SMA50=106.74 (price above both). RSI 58.4 (room to 65). Vol 3.19% = lowest in BOND universe. Edge: tax-exempt federal carry, flight-to-quality bid if VIX spikes. Risk: muni tax-reform tail, illiquidity in stress. **Sharpe 1.10 = best in class.**

### 4.2 EMB — LONG (MED)
Last 96.10; 60d range 92.95-96.67 (recovering from low). SMA20=95.60, SMA50=95.40 (above both = bullish). RSI 56.0. 12m +5.85% = strongest in universe. Yield ~5.5% gross over UST 4.48% = carry trade working. **Risk:** DXY +1.85% 90d (USD strength = EM headwind), sovereign default tail (Argentina/Turkey/Egypt in top-10). EMB is USD-denominated so local-FX doesn't kill it, but credit risk real.

### 4.3 TLT — LONG mean-reversion (LOW)
Last 85.50; 60d range 83.02-87.49 (2.3% off high). Above SMA20=84.94, below SMA50=85.82 — short-term bounce, intermediate trend down. RSI 55.1. 60d -3.15% is only ~0.7σ (30d vol 8.78% × √60/252 = 4.4%) — **not extreme**, so mean-reversion is weak. Edge: Fed funds -13bp 90d = easing bias; if growth disappoints TLT rallies. CTA/vol-target funds are short duration — if term premium keeps rising, TLT can keep falling. **This is a fade-the-trend tail bet, not a base case.**

---

## 5. Risk Parameters

| Pick | DV01 per $100k | Annual carry | Max loss to SL | Position size |
|---|---|---|---|---|
| MUB | ~$5,500 (7yr dur × 0.07) | ~3.5% tax-equiv | -$1,600 | 1.0% portfolio |
| EMB | ~$6,000 (8yr dur) | ~5.5% gross | -$2,000 | 1.0% |
| TLT | ~$17,000 (17yr dur) | ~4.5% gross | -$2,900 | 1.5% |

**Total BOND: 3.5% of portfolio** (under 4% cap).
**Parallel +50bp shock:** TLT -8.5% × 1.5% + EMB -4% × 1.0% + MUB -3.5% × 1.0% = **-0.205% portfolio**. Acceptable.
**Cross-correlation:** TLT vs MUB/EMB low (~0.3-0.5). TLT adds diversification.

---

## 6. Failure Modes

1. **Fed hawkish surprise** (hike signal): TLT implodes; MUB/EMB mildly hurt.
2. **Inflation re-accel** (CPI >3.5%): all three hurt; TLT worst.
3. **Recession** (VIX >25, 10y-2y inverts): TLT rallies hard (HELPS mean-rev); MUB/EMB hurt by credit.
4. **EM credit event**: EMB -5-10% in weeks.
5. **Muni tax reform**: MUB -5-15% on announcement.
6. **Weak Treasury auction**: TLT hurt disproportionately.

**Gate:** If `macro_circuit_breaker.json` activates or 10Y yield >5.0%, do not enter. Currently neither triggered.

---

## 7. Confidence

| Pick | Confidence | Why |
|---|---|---|
| MUB | **MED-HIGH** | Best risk-adjusted return in BOND; clear momentum; only tax-reform tail concern |
| EMB | **MED** | Best absolute return; DXY strength a real headwind; EM credit tail real |
| TLT | **LOW** | 60d -3.15% is not extreme; trade is right only if Fed pivots or growth disappoints |

**Execution:** Size MUB+EMB at 1.0% each, TLT at 1.0% (mental stop 83.00 close; exit immediately if breached — mean-reversion thesis is dead). Hold 60-90d unless circuit breaker activates. Review weekly against VIX + DXY + 10Y.

**Honest disclaimer:** Macro-view report, not a backtested edge. Bond edges are usually macro calls. None validated against contaminated `trading_picks` (per task spec). FRED CPI/HY-OAS not queryable, so inflation/credit views are inferred from TIP/HYG/JNK price action. If `macro_factors_snapshot.json` flips to hawkish, cut all three.
