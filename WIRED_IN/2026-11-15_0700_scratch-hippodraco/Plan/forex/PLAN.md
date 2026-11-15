# PLAN.md — FOREX, BOND, ETF, MUTUAL_FUNDS Strategy Forensic Audit & Proof Experiments

**Date:** 2026-11-15
**Asset classes:** FOREX, BOND, ETF, MUTUAL_FUNDS
**Worktree:** WIRED_IN/2026-11-15_0700_scratch-hippodraco/Plan/forex
**Status:** Draft — ready for execution
**Source of truth:** `audit_dashboard/data/money_ready_verdict.json` (generated 2026-11-15T00:05:20Z)

---

## 1. HYPOTHESIS

### 1.1 FOREX — Contrarian sentiment + carry / mean-reversion hybrid

**Primary hypothesis:** Directional bias based on IG contrarian sentiment. The SHORT-axis of `ig_contrarian_sentiment` showed 57% WR vs LANG 21% (36pp spread) per mission context and the 2026-05-13 action plan (§9). No strategy passes SPA (spa_p=0.502, n_spa_pass=0), so directional IG contrarian alone is not promotable. **Test two replacements:**

- **H1a (Carry trade with yield differential):** LONG high-yield currency vs LOW-yield funding currency when carry differential > 0 AND price > SMA200 (trend confirmation to avoid carry crash). Pairs: AUD/JPY, NZD/JPY (long), USD/JPY (short funding). Based on Lustig & Verdelhan (2007) carry risk premium; already implemented as `carry_trade_momentum` in `alpha_engine/forex_strategies.py:125` but never SPA-validated live.
- **H1b (Mean-reversion on major pairs during low-vol Asian session):** BUY when Z-score deviation from 200d SMA < -1.5 with RSI < 52 (oversold below mean); SELL when Z > +1.5 with RSI > 48. Only when 20d vol / 60d vol <= 1.3 (quiet Asian session). Based on Poterba & Summers (1988); already implemented as `forex_mean_reversion_200d` in `alpha_engine/forex_strategies.py:742`.

**Rationale:** FOREX has n=612 resolved picks but WR=32.19%, PF=0.6596, verdict=NOT_READY per `money_ready_verdict.json:363-529`. Expectancy -0.002226 (adj_win=0.012713, adj_loss=0.009318, slippage=5bps) — marginal negative expectancy, fixable by cost control and tighter entry filters. Gates failing: WR (≥50%), PF (≥1.5), DSR (0.001), expectancy (>0), MDD (0.8212 > 20%), bootstrap CI ([-0.005729, 0.003409] straddles 0), SPA (p=0.502 > 0.10), single_source (no profitable strategy n≥20). Gates passing: n (≥100), recency (1.91d), walk-forward OOS (ratio 3.03, OOS PF 1.7414). Source concentration extreme: top_source=UNKNOWN at 88.43%.

This plan fills the gap by specifying two pre-registered FOREX strategies (carry with yield differential, 200d SMA mean-reversion) with exact parameters, exact gates, exact pass criteria, and ATR-based TP/SL sized to outrun 8bp round-trip cost.

### 1.2 ETF — Sector rotation momentum (top-N by 12-month momentum)

**Primary hypothesis:** Top-N sector ETFs ranked by 12-month momentum (1-month lag to avoid reversal), monthly rebalance, long-only, cash when no ETF beats cash. This is the Antonacci dual-momentum / Faber TAA approach already partially implemented in `alpha_engine/etf_strategies.py` (`etf_cross_sectional_momentum` H-003 line 875, `etf_sector_dual_momentum` E-002 line 733, `etf_dual_momentum` line 75).

**Rationale:** ETF had the cleanest OOS profile in prior analysis: walk-forward consistency 100%, OOS WR 75%, decay +23% (2026-05-13 action plan §2, §9). But current n=45, WR=2.22%, PF=0.0216, verdict=INSUFFICIENT_DATA per `money_ready_verdict.json:817-961`. The intrabar truth shows daily_wr=68.42%, daily_pf=1.7877 (flag=true, PF inflation x82.77) — meaning the live emitter is producing correct-direction picks but the resolver/mis-tagging is destroying recorded outcomes. Universe expansion (currently thin at n=88-100 floor per action plan §9) to XLF/XLE/XLK plus full SPDR sector list will lift n to the ≥100 floor.

This plan fills the gap by specifying exact top-N momentum rules, monthly rebalance cadence, universe expansion to 16 ETFs, and exact gates.

### 1.3 BOND — Duration/roll yield strategy on bond ETFs

**Primary hypothesis:** Duration rotation driven by 2s10s yield-curve slope (FRED T10Y2Y) and UST time-series momentum (FRED DGS10). When curve inverts (T10Y2Y ≤ -0.10) → BUY TLT (long duration rallies as Fed cuts). When curve steepens (T10Y2Y ≥ +1.50) → SELL TLT / BUY IEF. Confirm with TLT price vs SMA50. Implemented as `bond_yield_curve_slope` (`alpha_engine/bond_strategies.py:587`) and `bond_ust_tsmom` (line 706), both gated behind `BOND_ENABLE_YIELD_CURVE=1` / `BOND_ENABLE_UST_TSMOM=1` and requiring FRED data.

**Rationale:** BOND has n=1, WR=0.0%, PF=0.0, verdict=INSUFFICIENT_DATA per `money_ready_verdict.json:675-816`. n_ok=false (n=1 < 100), all gates null/insufficient. top_symbol=TLT (100% share), top_source=bond_duration_rotation (100%). recency_gate_48h=false (last pick 4.39d ago). policy_frozen=true. The single existing pick is from `bond_duration_rotation` — the scanner emits but nothing resolves. **Blocker: no FRED_API_KEY, so `bond_yield_curve_slope`/`bond_ust_tsmom` fall back to a TLT/SHY synthetic slope proxy and emit almost nothing.** This plan fills the gap by specifying FRED-backed duration/roll-yield rules and the data unblock needed to reach n≥100.

### 1.4 MUTUAL_FUNDS — NOT a prediction class; beta capture via low-cost index allocation

**Hypothesis (rejected for prediction):** Mutual funds are NOT a prediction target. class id -1 (not in `ml_gatekeeper/gatekeeper.py:73` ASSET_CLASS_MAP = {CRYPTO:0, FOREX:1, EQUITY:2, COMMODITY:3, ETF:4, BOND:5, FUTURES:6}), so `extract_features` returns asset_class=-1 and the ML gate drops the pick. No `mutual_fund_strategies.py` exists (file not found — confirmed missing). No scanner, no NAV data source, no dashboard tile, no money_ready_verdict.json entry for MUTUAL_FUND.

**Recommended alternative:** Low-cost index mutual fund allocation (beta capture, not alpha). Universe: VFIAX, VTSAX, FXAIX, VWINX, VFSTX, PRBLX, PIMIX, VWELX. Allocate by asset-class target weights (e.g. 60% equity VFIAX/VTSAX/FXAIX, 20% bond VWINX/VFSTX/PRBLX, 20% balanced PIMIX/VWELX), rebalance monthly or quarterly. No TP/SL, no directional prediction, no intraday signals (MF NAV struck once daily after close — intra-day TP/SL meaningless). Respect 30-day frequent-trading limits (no round-trips within 30 days on the same fund).

**Infrastructure needed IF they later want MF predictions:** (a) register MUTUAL_FUND class in `ASSET_CLASS_MAP` and `asset_class.py` category map, (b) source NAV data (yfinance mutual fund NAV or fund-family API), (c) build EOD pipeline (NAV struck once daily after 4pm ET), (d) build validator with monthly resolution (no intrabar), (e) add dashboard tile + money_ready_verdict.json entry, (f) frequent-trading-limit rule engine.

---

## 2. GAP FILLED

No `00_inventory.csv` exists in the repo (searched `**/00_inventory*` and `**/*inventory*.csv` — no match). The canonical implementation files are:
- `alpha_engine/forex_strategies.py` (10 strategies, lines 125-1075, registered in `FOREX_STRATEGIES` dict line 1099)
- `alpha_engine/bond_strategies.py` (7 strategies, lines 66-829, registered in `BOND_STRATEGIES` dict line 821)
- `alpha_engine/etf_strategies.py` (8 strategies, lines 75-983, registered in `ETF_STRATEGIES` dict line 974)
- `alpha_engine/mutual_fund_strategies.py` — **does not exist** (no stub found; searched entire repo)

Per `money_ready_verdict.json`, each class fails all §6 gates:

### FOREX gate table (§6) — verdict NOT_READY

| Gate | Threshold | FOREX actual | Pass? | Source |
|------|-----------|--------------|-------|--------|
| n (sample size) | ≥ 100 | 612 | PASS | `money_ready_verdict.json:386` |
| WR | ≥ 50% | 32.19% | FAIL | `:387` |
| PF | ≥ 1.5 | 0.6596 | FAIL | `:389` |
| DSR | ≥ 0.95 | 0.001 | FAIL | `:394` |
| SPA | family-wise p ≤ 0.10 | p=0.502, n_spa_pass=0 | FAIL | `:397-399` |
| PBO | ≤ 0.55 | null (need ≥2 strategies n≥20, got 1) | FAIL | `:395-396` |
| Expectancy (net slippage) | > 0 | -0.002226 | FAIL | `:400-401` |
| MDD | ≤ 20% | 0.8212 (82.12%) | FAIL | `:408` |
| CVaR 95% | pass threshold | -5.8626% | PASS | `:410` |
| Bootstrap CI lower | > 0 | -0.005729 | FAIL | `:430-431` |
| FDR | q ≤ 0.10 | null (n_fdr_tested=1, need ≥2) | FAIL | `:415-418` |
| Single source (profitable strat n≥20) | ≥ 1 | 0 | FAIL | `:421-423` |
| Walk-forward OOS | OOS PF > 1.5 | OOS PF 1.7414, ratio 3.03 | PASS | `:433-436` |
| Recency (48h) | ≤ 48h | 1.91 days | PASS | `:425-429` |

Policy clean net: n=432, WR=35.88%, PF=0.8385 (`:382-385`). Top symbol USDJPY=X (14.81%), top source UNKNOWN (88.43%). Policy frozen=true.

### BOND gate table (§6) — verdict INSUFFICIENT_DATA

| Gate | Threshold | BOND actual | Pass? | Source |
|------|-----------|-------------|-------|--------|
| n | ≥ 100 | 1 | FAIL | `money_ready_verdict.json:698` |
| WR | ≥ 50% | 0.0% | FAIL | `:699` |
| PF | ≥ 1.5 | 0.0 | FAIL | `:701` |
| DSR | ≥ 0.95 | null (n=1 too small) | FAIL | `:705-706` |
| SPA | p ≤ 0.10 | null (no strategies n≥20) | FAIL | `:709-711` |
| PBO | ≤ 0.55 | null (need ≥2 strategies n≥20, got 0) | FAIL | `:707-708` |
| Expectancy | > 0 | null (no pick data) | FAIL | `:712-713` |
| MDD | ≤ 20% | null | FAIL | `:720-721` |
| Bootstrap CI | > 0 | null | FAIL | `:742-743` |
| FDR | q ≤ 0.10 | null (n_fdr_tested=0) | FAIL | `:726-730` |
| Single source | ≥ 1 | 0 | FAIL | `:733-735` |
| Walk-forward | n≥min_trades | skipped (n=11 < min_trades=60) | FAIL | `:745-747` |
| Recency 48h | ≤ 48h | 4.39 days | FAIL | `:737-741` |

Policy clean net: n=1, WR=0.0%, PF=0.0 (`:694-697`). Data source closed_picks. Policy frozen=true.

### ETF gate table (§6) — verdict INSUFFICIENT_DATA

| Gate | Threshold | ETF actual | Pass? | Source |
|------|-----------|------------|-------|--------|
| n | ≥ 100 | 45 | FAIL | `money_ready_verdict.json:840` |
| WR | ≥ 50% | 2.22% | FAIL | `:841` |
| PF | ≥ 1.5 | 0.0216 | FAIL | `:843` |
| DSR | ≥ 0.95 | null (n=5 too small) | FAIL | `:847-848` |
| SPA | p ≤ 0.10 | null (no strategies n≥20) | FAIL | `:851-853` |
| PBO | ≤ 0.55 | null (need ≥2 strategies n≥20, got 0) | FAIL | `:849-850` |
| Expectancy | > 0 | -0.025559 | FAIL | `:854-855` |
| MDD | ≤ 20% | null | FAIL | `:862-863` |
| Bootstrap CI | > 0 | null | FAIL | `:884-885` |
| FDR | q ≤ 0.10 | null (n_fdr_tested=0) | FAIL | `:868-872` |
| Single source | ≥ 1 | 0 | FAIL | `:875-877` |
| Walk-forward | OOS PF > 1.5 | null | FAIL | `:887-890` |
| Recency 48h | ≤ 48h | 1.42 days | PASS | `:879-883` |

Intrabar truth: n=45, WR=2.22%, PF=0.0216 (`:818-822`). Honest intrabar: daily_wr=68.42%, daily_pf=1.7877 — PF inflation x82.77, WR inflation +66.2pp (flag=true, `:825-834`). Policy clean net: n=19, WR=68.42%, PF=1.7877 (`:836-839`). Expectancy -0.025559 (slippage 8bps, `:854-855`). Top symbol QQQ (40%), top source institutional_picks_engine (60%). Policy frozen=false.

### MUTUAL_FUNDS gate table (§6)

| Gate | Threshold | MUTUAL_FUNDS actual | Pass? | Source |
|------|-----------|---------------------|-------|--------|
| All §6 gates | various | Not a tracked class — no entry in `money_ready_verdict.json` classes | N/A (excluded) | `money_ready_verdict.json` classes object has no MUTUAL_FUND key |
| asset_class id | 0-6 valid | -1 (not in `ASSET_CLASS_MAP`) | FAIL (dropped by ML gate) | `ml_gatekeeper/gatekeeper.py:146,73` |
| Scanner | exists | No `mutual_fund_strategies.py`; no scanner | FAIL | File not found |
| NAV data source | exists | None | FAIL | Confirmed by repo scan |
| Dashboard tile | exists | None | FAIL | Confirmed by repo scan |

This plan fills the gap for FOREX (2 pre-registered strategies), ETF (top-N momentum), BOND (FRED-backed duration/roll yield), and documents the MF exclusion with the conditional infrastructure path.

---

## 3. METHOD

### 3.1 FOREX — exact entry/exit rules

#### Strategy A: Carry trade with yield differential (LONG high-yield, SHORT low-yield funding)
**Universe pairs:** AUDJPY, NZDJPY (long high-yield), USDJPY (short funding leg), plus EURUSD/GBPUSD/USDCAD/AUDUSD/USDCHF as carry candidates per `FOREX_SYMBOLS` in config.

**Entry rules (evaluated at daily close):**
1. Carry differential `carry_yield_diff` (from `FOREX_SYMBOLS[symbol].carry_yield_diff`) > 0 → candidate for LONG the high-yield currency. carry_yield_diff ≤ 0 → skip (no edge, Lustig 2011).
2. Trend filter: Close > SMA200. If Close ≤ SMA200 → skip (carry crash risk).
3. FX regime gate: 20d vol / 60d vol ≤ 2.0 (`_fx_regime_ok`, line 97). Skip if > 2.0 (flash-crash/news).
4. Volatility timing: 20d vol / 60d vol ≤ 1.3 (tighter). Skip if > 1.3 (carry unwind risk).
5. RSI(14) ≤ 70 (not overbought). Skip if > 70.
6. ADX(14) ≥ 18 (trending market). Skip if < 18.
7. Carry differential momentum: mom_20d > 0 AND mom_20d > mom_60d/3 → "widening" (+4% conf). Else "narrowing" (-3% conf).
8. Entry price = daily close. TP = entry + min(1.5×ATR14, 1.5% of entry). SL = entry - min(1.0×ATR14, 0.8% of entry). Require R:R ≥ 1.0.
9. Confidence: base = min(0.72, 0.52 + carry_diff/15) + trend_strength bonus (≤+5%) + carry_widening (+4%) / narrowing (-3%). Cap via `_forex_conf_cap` (0.65 unvalidated, 0.72 validated).
10. Max hold: 7 bars.

**Exit rules (evaluated at daily close):**
- TP hit → exit at TP (win).
- SL hit → exit at SL (loss).
- Max hold 7 bars → time exit at close.
- RSI(14) > 70 on long → early exit (overbought).

#### Strategy B: 200d SMA mean-reversion (fade extremes)
**Universe:** EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF (the 6 major pairs from Section 6).

**Entry rules (daily close):**
1. FX regime gate: 20d/60d vol ≤ 2.0. Skip if > 2.0.
2. Z-score of (Close − SMA200) over 60-day lookback: |z| ≥ 1.5. Skip if |z| < 1.5.
3. z > 1.5 (overextended above mean) → SELL (fade), require RSI(14) ≥ 48.
4. z < -1.5 (overextended below mean) → BUY (fade), require RSI(14) ≤ 52.
5. Entry = daily close. TP = SMA200 value (dynamic mean-reversion target). SL = entry ± 1.0×ATR14 (mirror side), require R:R ≥ 1.0.
6. Confidence: min(0.75, 0.55 + |z|×0.08). Cap via `_forex_conf_cap`.
7. Max hold: 14 bars.

**Exit rules:**
- Price touches SMA200 (TP) → exit at SMA200 (win).
- SL hit → exit at SL (loss).
- Max hold 14 bars → time exit.
- RSI crosses back through neutral (50) → early exit optional.

#### Position sizing (FOREX)
| Parameter | Value |
|-----------|-------|
| Base size | 1% of portfolio equity per symbol |
| Max concurrent positions | 5 (5% max gross) |
| Per-symbol cap | 1 position |
| Leverage | None (spot, 1x) |
| Rebalance | Daily at close on signal |
| Ranking | By |z| descending (B) / carry_diff descending (A) |

#### SL/TP exact parameters (FOREX)
| Parameter | Value | Range |
|-----------|-------|-------|
| Stop-loss (A) | min(1.0×ATR14, 0.8% of entry) | 0.5% - 0.8% |
| Take-profit (A) | min(1.5×ATR14, 1.5% of entry) | 1.0% - 1.5% |
| Stop-loss (B) | 1.0×ATR14 (mirror) | 0.5% - 0.8% |
| Take-profit (B) | SMA200 (dynamic) | N/A (mean target) |
| ATR period | 14 | fixed |
| R:R floor | 1.0 | fixed |
| Max hold (A) | 7 bars | 4-10 bars |
| Max hold (B) | 14 bars | 7-21 bars |

**R:R (A):** 1.5:1 nominal (1.5% TP / 0.8% SL). After 8bp round-trip: net TP ≈ 1.42%, net SL ≈ -0.88%, net R:R ≈ 1.61.

---

### 3.2 ETF — sector rotation momentum (top-N by 12-month momentum)

**Universe:** SPY, QQQ, IWM, XLF, XLE, XLK, XLV, XLI, XLB, XLP, XLU, XLRE, XLC, EFA, EEM, AGG, TLT (16 ETFs, Section 6).

**Entry rules (evaluated at monthly rebalance, first trading day of month):**
1. Require ≥ 252 trading days of history per ETF (skip if < 252).
2. Compute 12-month return with 1-month lag: r12m = Close[-22] / Close[-252] - 1 (skip last month to avoid reversal, Antonacci standard).
3. Absolute momentum filter: r12m > 0 (beats cash/T-bills). Skip if ≤ 0.
4. Rank qualifying ETFs by r12m descending.
5. Select top N (N=3 default, range 1-5) with positive absolute momentum.
6. LONG each selected ETF at monthly rebalance. Equal weight across selected (1/N each). Cash the remainder.
7. If no ETF has r12m > 0 → 100% cash (no pick) for that month.
8. Confidence: 0.60 + min(r12m, 0.40)×0.4 − (rank−1)×0.03, clamped [0.55, 0.82] (`etf_cross_sectional_momentum`, line 940).

**Exit rules:**
- Monthly rebalance: re-rank; drop ETFs no longer in top N or with r12m ≤ 0 → rotate to cash or next qualifier.
- Stop-loss: 4% from entry (hard stop, evaluated daily). If hit → exit to cash immediately.
- Take-profit: none (let winners run; Faber-style). Exit only on rebalance rotation or SL.
- Max hold: indefinite until rebalance rotation or SL.

**Position sizing (ETF)**
| Parameter | Value |
|-----------|-------|
| Base size | 1/N of equity per selected ETF (N=3 → ~33% each) |
| Max concurrent positions | 5 |
| Cash reserve | Remainder when < N qualifiers |
| Rebalance | Monthly (first trading day) |
| Lookback | 12 months (252 days), 1-month lag |

**SL/TP exact parameters (ETF)**
| Parameter | Value | Range |
|-----------|-------|-------|
| Stop-loss | 4% from entry | 2% - 4% |
| Take-profit | None (trend-following, exit on rebalance) | N/A |
| Lookback | 12 months | 3-12 months |
| Position size | 1-5% per name (concentrated top-N) | 1-5% |
| Max hold | Until monthly rotation | 1-6 months |

**R:R:** Trend-following, no fixed TP. Target R:R ≥ 1.20 via `_etf_tp_sl` defaults (tp_mult=2.5, sl_mult=1.5 → ~1.67) if a TP is used for backtest bookkeeping; production exits on rebalance/SL only.

---

### 3.3 BOND — duration / roll yield strategy

**Universe:** TLT, IEF, AGG, HYG, LQD (Section 6).

**Entry rules (daily, requires FRED data):**
1. Read FRED T10Y2Y (2s10s yield curve slope) and DGS10 (10y Treasury yield).
2. Regime classification:
   - T10Y2Y ≤ -0.10 (inverted) → recession signal → LONG duration: BUY TLT.
   - T10Y2Y ≥ +1.50 (steep) → expansion/Fed tightening → SHORT duration: SELL TLT, BUY IEF.
   - -0.10 < T10Y2Y < +1.50 → neutral → no pick (cash).
3. Price confirmation: TLT Close vs SMA50. BUY TLT requires TLT > SMA50 (bullish). SELL TLT requires TLT < SMA50 (bearish). If confirmation fails → no pick.
4. Inflation booster: T10YIE ≥ 2.5% raises confidence for SELL TLT (rising rates).
5. Entry = daily close. TP/SL via `_bond_tp_sl`: TP = entry ± min(tp_mult×ATR14, 6% of entry); SL = entry ∓ min(sl_mult×ATR14, 4% of entry). Require R:R ≥ 1.20 (bond policy floor).
6. Confidence: base 0.58 + min(|slope|, 2.0)×0.05 + inflation booster, clamped [0.58, 0.80].

**Fallback (no FRED key):** synthetic slope proxy = SHY 20d return − TLT 20d return (scaled). Emit only if |proxy| exceeds threshold equivalent to ±0.10pp. Mark `data_source=TLT_PRICE_PROXY`.

**Exit rules:**
- TP hit → exit.
- SL hit → exit.
- Regime flip (inverted→neutral or steep→neutral) → exit at next daily close.
- Max hold: 20 bars (1 month).

**Position sizing (BOND)**
| Parameter | Value |
|-----------|-------|
| Base size | 2% of equity per bond ETF |
| Max concurrent positions | 3 (6% max gross) |
| Per-symbol cap | 1 position |
| Rebalance | Daily on regime change |
| Leverage | None |

**SL/TP exact parameters (BOND)**
| Parameter | Value | Range |
|-----------|-------|-------|
| Stop-loss | min(1.2×ATR14, 4% of entry) | 2% - 4% |
| Take-profit | min(2.5×ATR14, 6% of entry) | 3% - 8% |
| ATR period | 14 | fixed |
| R:R floor | 1.20 | fixed |
| Max hold | 20 bars | 10-30 bars |

**R:R (BOND):** 2.5:1 nominal (up to 6% TP / 4% SL cap). After 5bp round-trip: net TP ≈ 5.95%, net SL ≈ -4.05%, net R:R ≈ 1.47.

---

### 3.4 MUTUAL_FUNDS — allocation method (NOT prediction)

**Method:** Static/monthly-rebalanced low-cost index fund allocation. No directional signals, no TP/SL, no intraday.

| Fund | Role | Target weight |
|------|------|---------------|
| VFIAX | S&P 500 index (equity core) | 30% |
| VTSAX | Total stock market (equity core) | 20% |
| FXAIX | S&P 500 index (equity, Fidelity) | 10% |
| VWINX | Balanced (60/40) | 15% |
| VFSTX | Short-term Treasury (bond) | 10% |
| PRBLX | Total bond market (bond) | 10% |
| PIMIX | Balanced/income | 5% |
| VWELX | Balanced growth | — (reserve/substitute) |

**Rules:**
- Rebalance monthly (or quarterly) to target weights; drift band ±5% triggers interim rebalance.
- No TP/SL. No stop. No take-profit.
- Minimum holding period 30 days per fund (frequent-trading limit) — no round-trip within 30 days of purchase on the same fund.
- NAV struck once daily after 4pm ET; all orders execute at next NAV (forward pricing). Intra-day TP/SL meaningless — not supported.
- Allocation only: beta capture, not alpha. Expected return ≈ blended index return (~8% equity, ~4% bond blended), no claim of outperformance.

---

## 4. DATA SOURCE

| Class | Primary source | Details |
|-------|---------------|---------|
| FOREX | yfinance + existing `dashboard_data.json` | yfinance daily OHLCV for EURUSD=X, GBPUSD=X, USDJPY=X, AUDUSD=X, USDCAD=X, USDCHF=X (≥252 days for SMA200). `carry_yield_diff` per-symbol metadata from `FOREX_SYMBOLS` config. Cross-validate vs `audit_dashboard/data/dashboard_data.json` closed FOREX picks (n=612). |
| ETF | yfinance + `dashboard_data.json` | Daily OHLCV for 16 ETFs (≥252 days). Cross-validate vs dashboard ETF picks (n=45 intrabar; honest daily_wr=68.42%, daily_pf=1.7877). |
| BOND | yfinance + FRED (T10Y2Y, DGS10, T10YIE) | Daily OHLCV for TLT, IEF, AGG, HYG, LQD. FRED API for yield-curve slope and 10y yield. `fred_data_fetcher.py` exists; needs `FRED_API_KEY` (repo secret) — this is the unblock. Fallback: TLT/SHY synthetic slope proxy. |
| MUTUAL_FUNDS | None (no NAV source) | If allocation-only: yfinance mutual fund NAV (daily, once/day after close). If prediction later: new NAV pipeline required (Section 1.4 infra list). |

Cost model source: `tools/data/transaction_costs.json` (FOREX 8bps, ETF 10bps, BOND 5bps, Section 8).

---

## 5. TIMEFRAME

**Daily** for FOREX, ETF, BOND — no intraday needed for these classes per mission.

- FOREX: signals generated at daily close (New York 5pm ET / 21:00 UTC). ATR(14), SMA(50/200), RSI(14), ADX(14) all on daily bars.
- ETF: signals generated at monthly rebalance (first trading day, daily close). Momentum on daily bars with 252-day lookback.
- BOND: signals generated at daily close. FRED yield data is daily (T10Y2Y, DGS10). SMA50/200 on daily bars.
- MUTUAL_FUNDS: NAV struck once daily after 4pm ET; allocation reviewed monthly/quarterly. No intraday.

**Not used:** 1-hour / intrabar resolution (not needed; FOREX/ETF/BOND are daily strategies). Intrabar TP-before-SL resolution (Section 10, gate 15) applies only if intrabar backtesting is added later; not required for daily plans.

---

## 6. UNIVERSE

| Class | Symbols | Notes |
|-------|---------|-------|
| FOREX | EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF | 6 major pairs. yfinance suffix =X (e.g. EURUSD=X). `asset_class_from_symbol` returns "forex" for =X suffix and 6-char FOREX_CODES pairs (`asset_class.py:142-156`). |
| ETF | SPY, QQQ, IWM, XLF, XLE, XLK, XLV, XLI, XLB, XLP, XLU, XLRE, XLC, EFA, EEM, AGG, TLT | 16 ETFs. Full SPDR sector list (XLF, XLE, XLK, XLV, XLI, XLB, XLP, XLU, XLRE, XLC) plus broad market (SPY, QQQ, IWM) and international/bond (EFA, EEM, AGG, TLT). Note: AGG/TLT also live in BOND_SYMBOLS; `normalize_asset_class` category field beats symbol guessing (`asset_class.py:232-237`). |
| BOND | TLT, IEF, AGG, HYG, LQD | 5 bond ETFs. All in `BOND_SYMBOLS` frozenset (`asset_class.py:28-35`). |
| MUTUAL_FUNDS | VFIAX, VTSAX, FXAIX, VWINX, VFSTX, PRBLX, PIMIX, VWELX | 8 funds. Allocation only — NOT a prediction universe. No =X suffix; `asset_class_from_symbol` returns "unknown" for these (not in any frozenset) unless explicit category="mutual_fund" set (`database_consolidation.py:81-82`). |

No substitutions without documented reason. Universe fixed at plan registration; changes require re-pre-registration.

---

## 7. PARAMETER RANGES (grid search for optimization)

| Parameter | Range | Step | Default |
|-----------|-------|------|---------|
| Lookback (momentum/trend) | 3 - 12 months | 1 month | 12 months (ETF/BOND), 200d SMA (FOREX mean-rev) |
| Position size | 1% - 5% | 1% | FOREX 1%, ETF 1/N (N=3), BOND 2% |
| Stop-loss | 2% - 4% | 0.5% | FOREX 0.8% cap (ATR-based), ETF 4%, BOND 4% cap |
| Take-profit | 3% - 8% | 1% | FOREX 1.5% cap (ATR-based), BOND 6% cap, ETF none |
| Carry yield diff threshold (FOREX A) | 0 - 3% | 0.5% | > 0 |
| Z-score entry (FOREX B) | 1.5 - 2.5 | 0.5 | 1.5 |
| T10Y2Y inversion threshold (BOND) | -0.20 to -0.05 pp | 0.05 | -0.10 |
| T10Y2Y steep threshold (BOND) | 1.00 to 2.00 pp | 0.25 | +1.50 |
| Top-N (ETF) | 1 - 5 | 1 | 3 |
| Rebalance cadence (ETF) | Monthly, Quarterly | — | Monthly |
| Max hold (bars) | FOREX A: 4-10; FOREX B: 7-21; BOND: 10-30 | — | 7 / 14 / 20 |

**Grid size:** ETF (lookback 4 × top-N 5 × size 5 × SL 4) = 400 combinations — trivial. FOREX (carry diff 7 × z-entry 3 × size 5 × SL 3 × TP 3) = 945 per pair × 6 pairs = 5,670 — trivial on daily data. BOND (inversion 4 × steep 5 × size 5 × SL 4 × TP 6) = 2,400 — trivial.

**Optimization objective:** maximize PF subject to WR ≥ 50%, MDD ≤ 20%, n ≥ 100, bootstrap CI lower bound > 0, net of per-class round-trip cost (Section 8).

---

## 8. COST MODEL

Round-trip transaction costs from `tools/data/transaction_costs.json` (FOREX 8bps, ETF 10bps, BOND 5bps):

| Class | cost_bps | cost_pct | Note |
|-------|----------|----------|------|
| FOREX | 8 | 0.08% | Major FX pairs; avg spread ~1-2 pips = ~4bp/side |
| ETF | 10 | 0.10% | Same as EQUITY; ETFs trade on exchanges |
| BOND | 5 | 0.05% | Treasury/IG bond ETF; tight spreads on liquid issues |
| MUTUAL_FUNDS | N/A (allocation, no TP/SL) | — | Expense ratios apply instead (not modeled here) |

All backtest returns computed **net of costs**: each trade's PnL reduced by the per-class round-trip cost (half entry + half exit, or equivalent). Slippage per `money_ready_verdict.py` expectancy blocks: FOREX 5bps, ETF 8bps, BOND 5bps (aligned with cost_bps).

**Net expectancy gate:** adj_win × WR − adj_loss × (1−WR) > 0 after per-class slippage. Current baselines: FOREX -0.002226 (FAIL), ETF -0.025559 (FAIL), BOND null (no data). All targets must cross above 0 net of costs.

---

## 9. BENCHMARK

| Class | Benchmark | Rationale |
|-------|-----------|-----------|
| FOREX | Flat cash (0% return, unlevered) | FX is a zero-sum directional market; no carry benchmark without yield data. Beat flat cash net of 8bp cost. |
| ETF | SPY total return | SPY is the equity buy-and-hold benchmark per charter (SPY for EQUITY/ETF). Paired bootstrap of (trade_return − SPY_return) per trade window. |
| BOND | TLT / IEF / AGG (blended) | Bond buy-and-hold benchmark per charter. Weighted blend of the three core Treasury ETFs. |
| MUTUAL_FUNDS | Blended index (60% equity / 40% bond) | Beta capture target; no alpha claim. Benchmark = weighted blend of underlying index returns. |

**Benchmark method:** For each trade, compute buy-and-hold return of the benchmark over the same entry→exit window. Paired bootstrap: mean(trade_return − benchmark_return) over 10,000 resamples; pass requires frac_positive ≥ 0.95 and CI lower bound > 0. Random-entry Monte Carlo: same-asset null with window-matched nulls, 10,000 permutations; percentile ≥ 0.90 indicates timing edge.

---

## 10. PROOF TESTS (§6 Gates)

All gates must pass for promotion. Each maps to `alpha_engine/money_ready_verdict.py` gate logic.

| # | Gate | Threshold | Implementation | Classes |
|---|------|-----------|----------------|---------|
| 1 | Sample size n | n ≥ 100 closed clean picks | Count of completed trades (WON+LOST, exclude active) | All |
| 2 | Tier metrics (PF/WR/MDD) | PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20% | PF = gross_wins/gross_losses; WR = wins/(wins+losses); MDD = peak-to-trough cumulative net PnL | All |
| 3 | DSR | DSR ≥ 0.95 with nb_trials correction | `alpha_engine/deflated_sharpe.py`, nb_trials = grid combinations | All |
| 4 | SPA (White's Reality Check) | family-wise p ≤ 0.10 | `tools/whites_reality_check.py` via `money_ready_verdict.py:_spa_gate`, MIN_N_STRATEGY=20 | FOREX, ETF, BOND |
| 5 | PBO | PBO ≤ 0.55 | `tools/pbo_cscv.py` via `money_ready_verdict.py:_pbo_gate`, requires ≥ 5 strategies (parameter variants) | FOREX, ETF, BOND |
| 6 | Symbol/source concentration | top symbol ≤ 60%, top source ≤ 40% | `money_ready_verdict.py:_verdict` concentration caps | All |
| 7 | Net-of-slippage expectancy | adj_win × WR − adj_loss × (1−WR) > 0 | `money_ready_verdict.py` expectancy with class slippage | All |
| 8 | Bootstrap CI | 95% CI lower bound > 0 | `alpha_engine/benchmark_closed_ledger.py:paired_bootstrap`, 10,000 resamples | All |
| 9 | Walk-forward OOS | OOS WR within 10pp of IS, OOS PF > 1.5 | `alpha_engine/walkforward_validator.py`, 4 overlapping sleeves | All |
| 10 | Monte Carlo (random entry) | percentile ≥ 0.90 | `alpha_engine/benchmark_closed_ledger.py:random_entry_mc`, 10,000 permutations | All |
| 11 | Regime split | PF ≥ 1.2 in both bull and bear sub-periods | Split at median benchmark 200-SMA; test each regime | All |
| 12 | Shuffle control | Sharpe of shuffled < observed Sharpe | Shuffle daily returns 1,000×, compare | All |
| 13 | Pre-registered forward test | n ≥ 30 forward trades, PF ≥ 1.2 | Out-of-sample paper forward after grid frozen; no changes after seeing forward data | All |
| 14 | Reproducibility | Same seed, code, data → identical results | Fixed seed 42, deterministic grid, version-controlled code | All |
| 15 | Daily-resolution (no intrabar needed) | All TP/SL resolved at daily close | N/A for these classes (daily timeframe) | FOREX, ETF, BOND |

**Promotion rule:** All 15 gates must pass simultaneously on both (a) rolling-90d window and (b) frozen walk-forward window. Daily-resolution results are authoritative for these classes.

**Current baselines (to beat):**

FOREX: WR 32.19% → ≥50%; PF 0.6596 → ≥1.5; Expectancy -0.002226 → >0; MDD 82.12% → ≤20%; Bootstrap CI [-0.005729, 0.003409] → lower >0; SPA p=0.502 → ≤0.10; Source concentration UNKNOWN 88.43% → top source ≤40%.

ETF: WR 2.22% → ≥50%; PF 0.0216 → ≥1.5; Expectancy -0.025559 → >0; n=45 → ≥100; Bootstrap CI null → lower >0; SPA null → p ≤0.10 (need ≥2 strategies n≥20).

BOND: WR 0.0% → ≥50%; PF 0.0 → ≥1.5; n=1 → ≥100; all gates null → pass; Recency 4.39d → ≤48h; need FRED unblock to emit picks.

MUTUAL_FUNDS: Not a tracked class. Excluded from gates. If allocation-only: track vs blended index benchmark, no §6 gates apply (no predictions).

---

## 11. EXPECTED OUTCOME

**"Proven" = T2 Tier-2 floor cleared AND all §6 gates pass:**

| Metric | T2 Floor | "Proven" Target |
|--------|----------|-----------------|
| PF | ≥ 1.5 | ≥ 1.5 |
| WR | ≥ 50% | ≥ 50% |
| MDD | ≤ 20% | ≤ 20% |
| n | ≥ 100 | ≥ 100 |
| Sharpe | ≥ 1.0 | ≥ 1.0 |
| DSR | ≥ 0.95 | ≥ 0.95 |
| Bootstrap CI lower | > 0 | > 0 |
| Net expectancy | > 0 | > 0 |

**If proven (FOREX/ETF/BOND):** Strategy added to `alpha_engine/data/anti_overfit_registry.json` as validated, promoted to OOS_READY per class state machine (BLOCKED → REHAB → OOS_READY → SHADOW → LIVE_ELIGIBLE), sized per Section 3 position caps.

**If not proven:** Document failure in `updates/` directory per AGENTS.md "Document Every Fix" rule, classify as Below Tier 3 per charter, do not size real capital.

**MUTUAL_FUNDS:** Do NOT build MF prediction picks. Recommend low-cost index MF allocation (beta capture, not alpha). Track vs blended 60/40 index benchmark. If predictions ever wanted, build the Section 1.4 infrastructure first (register class, source NAV, EOD pipeline, validator, dashboard tile, verdict entry) and then run §6 gates.

---

## 12. EXECUTION CHECKLIST

- [ ] Verify `FOREX_SYMBOLS`, `BOND_SYMBOLS`, `ETF_SYMBOLS` in `alpha_engine/config.py` contain the Section 6 universes (add missing tickers).
- [ ] Confirm `alpha_engine/forex_strategies.py` `carry_trade_momentum` (line 125) and `forex_mean_reversion_200d` (line 742) are wired into `FOREX_STRATEGIES` registry (line 1099) — they are.
- [ ] Confirm `alpha_engine/bond_strategies.py` `bond_yield_curve_slope` (line 587) and `bond_ust_tsmom` (line 706) are wired into `BOND_STRATEGIES` (line 821) — they are, gated behind `BOND_ENABLE_YIELD_CURVE`/`BOND_ENABLE_UST_TSMOM`.
- [ ] Confirm `alpha_engine/etf_strategies.py` `etf_cross_sectional_momentum` (line 875, H-003) and `etf_sector_dual_momentum` (line 733, E-002) are wired into `ETF_STRATEGIES` (line 974) — they are.
- [ ] Set `FRED_API_KEY` in repo secrets to unblock BOND scanner (0 picks since ~Apr 20 per 2026-05-13 action plan P1-2).
- [ ] Create backtest scripts implementing Sections 3-5 exactly: `tools/forex_carry_meanrev_backtest.py`, `tools/etf_sector_momentum_backtest.py`, `tools/bond_duration_roll_backtest.py`.
- [ ] Run grid search (Section 7) per class on daily data.
- [ ] Run all 15 §6 gates (Section 10) on results.
- [ ] Document results in `updates/YYYY-MM-DD-forex-bond-etf-plan-backtest.md` per AGENTS.md "Document Every Fix" rule.
- [ ] If all gates pass: register in `alpha_engine/data/anti_overfit_registry.json`, wire into `production_scanner.py`.
- [ ] If any gate fails: document failure, do not promote.
- [ ] MUTUAL_FUNDS: confirm no `mutual_fund_strategies.py` exists (confirmed missing), no dashboard tile, no money_ready_verdict entry. Recommend allocation-only path; do not build prediction picks.

---
