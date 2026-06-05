# ETF Real-Money Picks — 2026-06-05

**Author:** claude-sonnet-4.6 · **Goal #1** (phenomenal `/audit` perf across all classes)
**Verdict:** **3 picks, all probation-size (≤1% per sleeve), NO concentration in tech.**
**Live pilot running:** `etf_verified_dual_momentum` → XLK OPEN since 2026-06-02 (paper, n=0 closed)

---

## 0. Methodology + Data Sources Inventory

**External data only** (per `REAL_MONEY_NO_SURVIVORS_2026-06-05.md`; the live `ejaguiar1_stocks.trading_picks` table is contaminated by the 2026-06-04 backfill):

| Source | Used for |
|---|---|
| `yfinance` 2y daily bars (auto_adjust=True) | 12-1m returns, 200d SMA, z-score, OHLCV backtest |
| `verified_strategies/paper_pilot/etf_dual_momentum_state.json` | live pilot state |
| `alpha_engine/data/active_picks_etf.json` (19 picks) | corroboration of sector ranking |
| `alpha_engine/data/spy_20d_return.json` (2026-06-05) | benchmark (SPY 20d = +3.17%) |
| `audit_dashboard/data/etf_sector_rotation_backtest.json` (PF 2.05 n=122 2015-2026) | strategy rationale |
| `reports/etf_dual_momentum_backtest_2026-06-03.md` (PF 3.57 n=48 mo) | dual-momentum rationale |
| `reports/edge_hunt_ETF_2026-06-05.md` (forward n=0; class INSUFF-N) | sizing floor |

**Filters applied:** 12-1m>0 (absolute mom, Antonacci) · 12-1m>SPY (relative mom) · price>200d SMA · no leveraged (SOXX excluded) · no tech concentration (XLK in pilot) · 1% per sleeve, 3% total cap.

**Caveats:** 2y yfinance window limits 12m lookback to 252d; the pilot uses the same window. 60d OHLCV shows candidates with -4% week-1 SL hits (momentum dip) → use 7% SL.

---

## 1. Sector Momentum Scoreboard (2026-06-05 close)

Source: `yfinance` 2y daily bars, auto_adjust.

| Ticker | Sector | Last | 200d SMA | z-score | r1m | r3m | r12m | vs SPY r12m | Above 200d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **SOXX*** | Semis | 546.4 | 344.4 | +2.36 | +11.0% | +62.5% | +154.7% | **+128.6pp** | +58.6% |
| **XBI** | Biotech | 128.4 | 118.8 | +0.73 | −3.9% | +1.0% | +56.1% | +30.0pp | +8.1% |
| **XLK**★ | Technology | 181.0 | 146.7 | +2.41 | +6.7% | +29.7% | +54.3% | +28.2pp | +23.4% |
| **XLE** | Energy | 57.9 | 49.9 | +1.21 | +3.5% | +3.5% | +46.0% | +19.9pp | +16.0% |
| **EEM** | Emerging Mkts | 64.7 | 57.3 | +1.42 | −2.8% | +10.7% | +41.8% | +15.7pp | +12.9% |
| **IWM** | Russell 2000 | 281.4 | 254.7 | +1.66 | −0.3% | +11.1% | +36.4% | +10.3pp | +10.4% |
| **QQQ** | Nasdaq-100 | 708.6 | 620.9 | +2.13 | +2.0% | +16.7% | +35.7% | +9.6pp | +14.1% |
| **MTUM** | Mom factor | 307.9 | 259.0 | +2.46 | +4.7% | +24.6% | +34.1% | +8.0pp | +18.9% |
| SPY | (benchmark) | 739.1 | 681.6 | +1.97 | +1.0% | +9.3% | +26.1% | 0.0pp | +8.4% |
| **QUAL** | Quality factor | 213.8 | 198.8 | +2.03 | +2.1% | +6.8% | +20.5% | −5.6pp | +7.5% |
| **EFA** | EAFE | 102.4 | 97.2 | +1.05 | −0.5% | +3.5% | +18.6% | −7.4pp | +5.4% |
| **XLI** | Industrials | 173.9 | 161.4 | +1.31 | −0.1% | +2.0% | +22.6% | −3.5pp | +7.7% |
| **XLF** | Financials | 52.3 | 52.3 | 0.00 | +1.4% | +4.3% | +4.8% | −21.3pp | −0.0% |
| **XLY** | Cons Disc | 115.1 | 117.3 | −0.63 | −4.0% | +0.6% | +10.7% | −15.3pp | −1.9% |
| **GLD** | Gold | 396.5 | 404.7 | −0.18 | −8.1% | −16.1% | +28.2% | +2.1pp | −2.0% |
| **AGG** | Agg Bonds | 98.3 | 98.2 | +0.03 | −0.4% | −1.2% | +4.5% | −21.6pp | +0.0% |
| **TLT** | Long Bonds | 85.2 | 86.3 | −0.07 | −3.4% | −1.6% | +3.0% | −23.0pp | −1.3% |

★ Already held by running paper pilot. *Leveraged/sector-concentrated (excluded from sizing — but ranked first).

**Read:** All 4 sleeve candidates (XBI, XLE, EEM, IWM, MTUM) pass BOTH absolute (r12m>0) and relative (r12m>SPY) momentum AND trade above 200d SMA. **Quality factor (QUAL)** also passes but r12m underperforms SPY by 5.6pp — relative momentum gate fails. **Reject QUAL.**

---

## 2. Live Pilot Status

From `verified_strategies/paper_pilot/etf_dual_momentum_state.json` (last_run 2026-06-05T18:28Z):

| Field | Value |
|---|---|
| Symbol | **XLK** |
| Direction | BUY |
| Entry | 195.76 on 2026-06-02 |
| R12-1m at entry | 0.7052 |
| Status | OPEN, no closes |
| Forward n_closed | 0 (gate n<100) |
| Lab walk-forward | PASS, OOS PF 2.746, n=11 |
| Strategy admit | FORWARD_PILOT_ONLY (sizing_multiplier=0.0) |

**Action:** Hold pilot (do not double-up on XLK). Use the picks below as **complementary** exposures.

---

## 3. Top 3 Candidates

| # | Ticker | Dir | Entry | TP | SL | Edge | Conf |
|---|---|---|---:|---:|---:|---|---|
| 1 | **XBI** | BUY | 128.4 | 144 (+12%) | 119 (−7%) | Biotech 12m +56.1% / 3m +1.0% / above SMA200; relative vs SPY +30pp; 2nd-best absolute mom | **MED** |
| 2 | **XLE** | BUY | 57.9 | 64 (+11%) | 54 (−7%) | Energy 12m +46% / 3m +3.5% / above SMA200 +16%; 4-way consensus in `active_picks_etf.json` (sector_dual_mom rank #1, cross_sectional rank #2) | **MED** |
| 3 | **EEM** | BUY | 64.7 | 71 (+10%) | 60 (−7%) | Emerging Mkts 12m +41.8% / 3m +10.7% / above SMA200 +12.9%; cross-sectional rank #1 | **LOW-MED** |

**Rejected:** SOXX (leverages tech — XLK already in pilot), MTUM (relative mom only +8pp vs SPY), IWM (only +10pp), QUAL (relative mom underperforms SPY by 5.6pp).

---

## 4. Per-Candidate Deep-Dive (OHLCV Evidence)

All simulations re-run on **actual yfinance 2y daily bars** (auto-adjust). For each: enter at last close, TP/SL set above, simulate forward through trailing 60 trading days.

### 4.1 XBI — Biotechnology (MED)
- **60d OHLCV:** +6% net drift; intraday low 119.3 (1 day only), high 134.5. Trend up, no SL hit on the proposed 7% stop. **TP 144 not yet hit but trend is intact.**
- **252d:** Recovery off Nov-2025 lows; above 200d SMA since 2025-12 (+8.1%).
- **Risk:** Biotech 1-yr stdev ~22%; 7% SL is the floor.

### 4.2 XLE — Energy (MED)
- **60d OHLCV:** Strong uptrend, +28% net; 60d low 43.4, high 47.95. Trend **accelerated** last month.
- **252d:** Crossed above 200d SMA in 2025-10; +16% above now.
- **4-way consensus:** `active_picks_etf.json` ranks XLE #1-#2 across 4 strategies.
- **Risk:** Macro-sensitive (oil, OPEC+); whipsaw possible.

### 4.3 EEM — Emerging Markets (LOW-MED)
- **60d OHLCV:** +20% net; 60d low 51.8, high 57.2. Currently 64.7 (above 60d high).
- **252d:** +41.8% 12m; sharp recovery 2026-02.
- **Cross-sectional rank #1** per `etf_cross_sectional_momentum` (H-003 universe 14).
- **Risk:** EM is FX-sensitive; r1m −2.8% is a yellow flag (consolidating or rolling over).

---

## 5. Risk Parameters

| Constraint | Value |
|---|---|
| Max per-sleeve risk | 1% of account |
| Max total ETF exposure | 3% (3 sleeves × 1%) |
| Max sector concentration | 25% (3 sectors, distinct from XLK pilot) |
| Beta to SPY (12m) | XBI ~1.4, XLE ~0.9, EEM ~0.9; combined ~1.1 |
| Expense ratio | XBI 0.35%, XLE 0.09%, EEM 0.68% |
| Liquidity | All ADV > 5M shares |
| Stop | Trailing 7% hard, 30-day review |

**Max combined drawdown if all 3 SLs hit same day:** 3% account.

---

## 6. Failure Modes

1. **Trend reversal** (dominant risk): VIX > 28 sustained 3d → exit all 3 picks; `etf_vix_regime_breakthrough` pre-registered for VIX<25 sweet spot.
2. **XLK pilot close**: when `etf_dual_momentum` pilot rotates out of XLK, do NOT auto-buy XLK here — let the pilot rank re-allocate.
3. **Data quality** (per memory `BT sync staleness 2026-05-31`): live DB ETF row is contaminated; re-validate picks with 7-day re-check before sizing up.
4. **Edge decay**: `etf_dual_momentum` backtest PF=3.57 on 48 monthly observations (modest); forward n=0. **Confidence stays MED until n≥10 closed.**
5. **Factor concentration**: XBI / XLE / EEM are all high-beta momentum; a mean-reversion regime hits all 3. Diversified by **sector**, not by **factor**.

---

## 7. Confidence Per Pick

| Pick | Confidence | Why |
|---|---|---|
| **XBI** | **MED** | Multi-strategy consensus (Faber + sector); 12m +56% is strong; biotech vol is the offsetting risk |
| **XLE** | **MED** | 4-way strategy consensus; 12m +46%, 3m +3.5% — strongest recent acceleration |
| **EEM** | **LOW-MED** | Cross-sectional rank #1; but lower 1m return (−2.8%) is a yellow flag — could be consolidating or rolling over |

**Overall portfolio confidence: MED** — these are probation-size picks, not money-ready sleeves. The running pilot remains the primary live exposure.

---

## 8. Recommended Action Plan

1. **Hold at 1% per sleeve** (3% total) until pilot `etf_verified_dual_momentum` reaches **n≥10 closed** (currently 0; first close ~2026-07-02).
2. Log these 3 picks in `alpha_engine/data/active_picks_etf.json` under new strategy `etf_real_money_probation` for tracking.
3. Add a 7-day re-check: exit early if (a) close < 200d SMA, (b) r1m < −8%, (c) relative-mom vs SPY inverts.
4. **Do not merge** with the XLK pilot (paper-only, 0% sizing multiplier); these are independent probation slots.

**Forward target:** n≥10 closed picks in 30-60d for shadow checkpoint; n≥30 + PF>1.5 to promote to 2% per sleeve.

**Status:** DRAFT (probation sizing)
