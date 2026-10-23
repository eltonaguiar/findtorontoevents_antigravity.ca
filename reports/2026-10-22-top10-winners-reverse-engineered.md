# Top-10 Winners Reverse-Engineered — 2026-10-22

**Author:** trading analysis subagent
**Date:** 2026-10-22 (UTC)
**Data source:** `/tmp/prod_dashboard_data.json` (generated 2026-10-22T22:14:47Z) — `picks.recent_closed` = 3,500 rows; cross-checked against `audit_dashboard/data/dashboard_data.json`.
**Window:** picks with `closed_at >= 2026-10-19` (last ~24–72h before report time). **376** resolved rows, **172** `WON`.

---

## 0. Data hygiene — artifacts excluded (critical)

A raw sort by `pnl_pct` is dominated by **non-genuine exits** that are not real trades. These were excluded per rigor (task constraint: do not count placeholder exits). 17 rows removed:

1. **`super_signals` "strong consensus" `FORCE_CLOSED` rows** — opened and "closed" 30–70 seconds apart at synthetic exit prices (entry→exit durations 0.008–0.011h), with `rr_ratio ≈ 0`.
   - ARBUSDT LONG **+100.0%** (entry 0.091 → exit 0.1895, dur 0.011h)
   - LINKUSDT LONG **+48.5%** (8.0 → 11.881, dur 0.008h)
   - LINKUSDT LONG **+34.3%** (9.1 → 12.221, dur 0.013h)
   - LTCUSDT LONG **+31.3%** (44.75 → 58.76, dur 0.010h)
2. **`mega_mutation` same-second TP fills** — opened/closed at the same timestamp (dur ~0h): ADAUSDT SHORT +8.36% ×3.

Suspending/fixing these two pipelines is a **data hygiene** recommendation (no production code is modified in this report).

---

## 1. Top-10 genuine winners (real holds, resolved in window)

Ranked by realized `pnl_pct` among the **155 genuine WON rows**.

| # | Symbol | Dir | Asset | Source system | Strategy | Entry | Exit | PnL % | Exit reason | Closed (UTC) | Hold | Score | Trust |
|---|--------|-----|-------|---------------|----------|-------|------|-------|-------------|---------------|------|-------|-------|
| 1 | BNBUSDT | LONG | CRYPTO | alpha_engine | st_fear_greed_contrarian (Revival) | 610.96 | 741.85 | **+21.42** | TP_HIT | 2026-10-21 04:54 | ~206d | 54 | RELIABLE |
| 2 | RNDR-USD | LONG | CRYPTO | alpha_engine | stochrsi_oversold_bounce | 1.8423 | 2.10897 | **+14.47** | TP_HIT | 2026-10-21 02:54 | 2.9h | 79 (A) | RELIABLE |
| 3 | MSTR | LONG | EQUITY | kimi_riseoftheclaw | golden-cross-stocks | 140.01 | 155.00 | **+10.71** | TP_HIT | 2026-10-21 16:43 | INTRADAY | 48 | WATCH |
| 4 | AVAXUSDT | LONG | CRYPTO | alpha_engine | st_fear_greed_contrarian (Revival) | 8.74 | 9.674 | **+10.69** | TP_HIT | 2026-10-21 04:54 | ~206d | 54 | RELIABLE |
| 5 | LINK-USD | LONG | CRYPTO | kimi_riseoftheclaw | crypto-rsi-divergence-scout | 11.6118 | 12.6689 | **+9.10** | TP_HIT | 2026-10-21 15:26 | INTRADAY | 40 | WATCH |
| 6 | NEARUSDT | LONG | CRYPTO | luxalgo_filters | luxalgo_confluence | 4.674 | 5.030 | **+7.62** | FORCE_CLOSED | 2026-10-20 14:35 | 4.0h | 40 | RELIABLE |
| 7 | XRP-USD | LONG | CRYPTO | kimi_riseoftheclaw | crypto-momentum-scout | 1.2992 | 1.3898 | **+6.98** | TP_HIT | 2026-10-21 18:10 | INTRADAY | 38 | WATCH |
| 8 | STXUSDT | SHORT | CRYPTO | alpha_engine | luxalgo_confluence | 0.3799 | 0.3588 | **+5.55** | TP_HIT | 2026-10-19 14:51 | 5.1h | 46 | RELIABLE |
| 9 | NEARUSDT | SHORT | CRYPTO | luxalgo_filters | luxalgo_confluence | 5.338 | 5.043 | **+5.53** | FORCE_CLOSED | 2026-10-22 05:36 | 13.0h | 47 | RELIABLE |
| 10 | STXUSDT | LONG | CRYPTO | luxalgo_filters | luxalgo_confluence | 0.3379 | 0.3553 | **+5.15** | FORCE_CLOSED | 2026-10-20 14:35 | 1.8h | 38 | RELIABLE |

> Note: rows 1 & 4 (Revival) are long-duration swing holds entered 2026-03-29 that resolved in-window; they are genuine TP_HIT wins, not same-day entries.

---

## 2. Reverse-engineered common features (genuine cohort, n=155)

### 2.1 Direction — LONG-dominated
- Winners: **LONG 65.8%** (102) vs SHORT 34.2% (53).
- Window win-rate: **LONG 42.5%** (102/240) vs SHORT 39.0% (53/136). Longs are both more frequent *and* higher-wr in this window.

### 2.2 Asset class — Crypto + FX crosses
- **CRYPTO 78.1%** (121), FOREX 14.8% (23), ETF 3.9% (6), EQUITY 1.9% (3), BOND 1.3% (2).

### 2.3 Source systems / strategy families
Winner share (of 155): `signal_validation` 27.1% (42), `alpha_engine` 21.3% (33), `luxalgo_filters` 21.3% (33), `multi_asset_copytrader` 14.8% (23), `kimi_riseoftheclaw` 12.3% (19).
- Strategy families: **MomentumEMA 42**, **luxalgo_confluence 37**, **forex_rsi2_mean_reversion 23**, **alpha_engine 17** → these 4 families ≈ **77%** of all genuine wins.
- **Win-rate leaders by source** (window): `multi_asset_copytrader` **82.1%** (23/28), `signal_validation` **57.5%** (42/73), `alpha_engine` **48.5%** (33/68), `kimi_riseoftheclaw` **44.2%** (19/43). Low: `super_signals` 11.9% genuine, `luxalgo_filters` 30.6% (but high volume).

### 2.4 Symbols — liquid crypto majors + JPY crosses
Top winner symbols: BTC-USD 17, ETH-USD 10, CADJPY=X 9, SOL-USD 8, NEARUSDT 7, LINK-USD 7, STXUSDT 6, AVAXUSDT/AVAX-USD 6 each, AUDJPY=X 5, LINKUSDT 5, INJ-USD 4.

### 2.5 Timeframe & close-time clustering
- INTRADAY 78 vs SWING 77 (balanced).
- Close-hour clusters (UTC): **21:00Z (44)**, **14:00Z (32)**, 01:00Z (15), 16:00Z (15) — i.e. winners tend to resolve around the US afternoon/NY-close session and the late-evening rollover.

### 2.6 Magnitude
Mean pnl **+2.85%**, median **+2.60%**, max **+21.42%**. Top-10 are tail events (≥ +5%); most winning days are ~+2–3%.

---

## 3. Are the winners available in the active universe?

Checked against `picks.active_raw` (4,423 live rows, 285 symbols). **Nearly all winner symbols are active and liquid:**
- Active & winning: BTCUSDT (276), ETHUSDT (242), SOLUSDT (223), AVAXUSDT (218), XRPUSDT (205), LINKUSDT (197), DOTUSDT (178), ADAUSDT (168), RENDERUSDT (156), NEARUSDT (154), JUPUSDT (143), ARBUSDT (140), STXUSDT (138), SUIUSDT (134), WIFUSDT (132), etc.
- **Proven winners NOT in the current active universe** (expansion candidates): **AUDJPY=X, GBPJPY=X** (FX crosses), and **BAT-USD, CRV-USD, ZECUSDT, WLD-USD, XTZ-USD, MINAUSDT** (crypto).

---

## 4. Concrete recommendations — where to hunt more winners

1. **Add the missing proven-winner symbols to the active universe** (highest ROI — they already won, just aren't being scanned now): `AUDJPY=X`, `GBPJPY=X`, `BAT-USD`, `CRV-USD`, `ZECUSDT`, `WLD-USD`, `XTZ-USD`, `MINAUSDT`.
2. **Hunt LONG in liquid crypto majors/alts** — direction + asset class with 65.8% of wins and higher WR: `BTC`, `ETH`, `SOL`, `LINK`, `NEAR`, `STX`, `AVAX`, `INJ`, `TIA`, `ARB`, `JUP`, `SUI`; via `signal_validation` MomentumEMA + `alpha_engine` + `kimi_riseoftheclaw` momentum/RSI scouts.
3. **Lean into `multi_asset_copytrader` (82.1% WR)** — expand its symbol coverage into the winner set above; it is the single best win-rate source in the window.
4. **Keep `luxalgo_confluence` for two-sided hunting** — it produced both SHORT (STX, NEAR) and LONG winners; use it where you want SHORT exposure (overall SHORT WR is lower, but confluence shorts worked on STX/NEAR/INJ).
5. **Prefer the 14:00Z / 21:00Z close windows** — that is where winners concentrate; schedule/locate entries to capture these resolution sessions.
6. **Data hygiene (no code change):** freeze `super_signals` strong-consensus and `mega_mutation` same-second fills from P&L rankings until their instant/synthetic fills are fixed — they currently flood the top of any pnl sort.

---

## 5. Method notes
- Loaded `/tmp/prod_dashboard_data.json` (25.4MB) → `picks.recent_closed`.
- Filters: skip `UNRESOLVED`, `exit_price<=0`, `pnl_pct==0` placeholder, and artifact rows (entry→exit duration < 1h OR same-second fills).
- All figures are from the live prod payload; no production code was modified.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
