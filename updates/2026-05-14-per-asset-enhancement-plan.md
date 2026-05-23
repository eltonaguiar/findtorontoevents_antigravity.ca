# Per-Asset-Class Enhancement Plan — May 2026

**Date:** 2026-05-14
**Basis:** Live dashboard_data.json snapshot, 210 baby strategies audit, activatable strategies audit, 3-engine swarm consensus
**Goal:** Stronger picks per asset class through more strategies, more symbols, and stronger safety gates

---

## Current State vs Target

| Class | Current PF | Active Picks | Active Score Range | Strategies Emitting | Target PF | Target Active |
|-------|-----------|-------------|-------------------|-------------------|-----------|---------------|
| CRYPTO | 1.34 | 30 (score 0-100, med 47) | 20+ strategies | 1.50+ | 30-40 |
| COMMODITY | 4.03 | **0** | — | **0** (highest PF, nothing running!) | 4.00+ | 5-10 |
| EQUITY | 1.55 | 4 (score 14-30) | ~3 strategies | 1.80+ | 8-12 |
| FOREX | 0.81 | 2 (score 18) | ~2 strategies | 1.20+ | 5-8 |
| ETF | 1.41 | 3 (score 30-32) | ~4 strategies | 1.60+ | 5-10 |
| BOND | 0.66 | **0** | — | **0** (5 strategies coded, scanner broken) | 1.20+ | 3-5 |
| FUTURES | None | **0** | — | **0** (no strategies, no scanner) | 1.00+ | 2-4 |

**Root cause of zero picks for COMMODITY and BOND:** Score floors too high for what their non-crypto score boosters can achieve. Crypto-only MTF/Ensemble boosters (+13 score) are absent for non-crypto, so scores max out at 30-55 even when strategies have strong underlying edge.

---

## Enhancement by Asset Class

### 1. COMMODITY — PF 4.03, 0 Active Picks (Highest Priority)

**Why nothing is emitting:** 9 strategies exist in `commodities_strategies.py` and register in scanner, but scores land at 30-55 because crypto-only boosters (MTF +8, Ensemble +5) are absent. The floor was lowered to 40 but most picks still don't reach it.

**Strategy additions:**
| Strategy | Source | Status | Action |
|----------|--------|--------|--------|
| `commodity_range_position_reversion` | baby_strategies/ | New (2026-04-18), untested | Backtest → wire |
| `commodity_trend_pullback_rsi` | baby_strategies/ | SMA200+20EMA+RSI on USO/metals ETFs | Backtest → wire |
| `gold_safe_haven` | commodities_strategies.py | Already registered, zero picks | Needs score booster |
| `dxy_inverse_commodities` | commodities_strategies.py | Registered | Needs DXY data source |
| `xau_bollinger_mr_rehab` | baby_strategies/ | Rehab candidate, direct XAUTUSDT | Promote from rehab |
| `paxg_bollinger_mr_rehab` | baby_strategies/ | PAXGUSDT gold proxy | Promote from rehab |

**Symbol expansion:** Add GC=F (gold futures), SI=F (silver futures), CL=F (crude oil), NG=F (natural gas), HG=F (copper), ZC=F (corn), ZS=F (soybeans), ZW=F (wheat) — currently only crypto-tracked commodities exist.

**Gate improvements:**
- Add commodity-specific score booster: DXY inverse correlation (+6), COT positioning alignment (+6), roll yield bonus (+4)
- Lower commodity elite floor to 55 (DONE — was 65)
- Add `SMART_PICKS_MIN_SCORE_COMMODITY` from 40 → 35 (data shows even good commodity signals score low)

**Expected impact:** 5-10 active commodity picks within 2 weeks. PF retention should hold (4.03 backtest) with wider admission.

---

### 2. EQUITY — PF 1.55, 4 Active (score 14-30, floor is 60!)

**Why only 4 active:** Elite score floor 60 vs actual scores 14-30. Nothing qualifies. The VIX regime gate (proven PF 4.55 in backtest) is OFF by default.

**Strategy additions:**
| Strategy | Source | Status | Action |
|----------|--------|--------|--------|
| `equity_vix_regime_momentum` | baby_strategies/ | VIX term structure, 70%+ accuracy | Backtest → wire |
| `equity_sector_rotation_momentum` | baby_strategies/ | Dual momentum on sector ETFs | Backtest → wire |
| `equity_earnings_drift_pead` | baby_strategies/ | Post-earnings announcement drift | Backtest → wire |
| `etf_faber_tactical` | etf_strategies.py:609 | NOT in etf_scanner.py dispatch | Add to dispatch |
| `etf_connors_rsi2_mr` | new_strategies/ | Not in ETF_STRATEGIES registry | Wire to registry |
| 20 new equity/commodity strategies | `new_equity_commodity_strategies_20.py` | Imported in scanner but not emitting | Audit which are live-ready |

**Gate improvements:**
- **IMMEDIATE:** Set `VIX_REGIME_GATE_ENABLED=1` — proven PF 4.55 on EQUITY, PF 3.32 on ETF (backtested, env-var only)
- **IMMEDIATE:** Set `YC_REGIME_GATE_ENABLED=1` — combined VIX+YC pushes to PF 4.98
- Add SPY 200-SMA gate: block EQUITY LONGs when SPY below 200-SMA
- Lower EQUITY elite floor: currently 60, but scores max at 30. The floor is 2x higher than actual attainable scores.

**Expected impact:** 8-12 active equity picks with VIX gate activated. PF should improve from 1.55 to 2.0+.

---

### 3. FOREX — PF 0.81, 2 Active (score 18, floor 70)

**Why only 2 active:** Score floor 70 vs actual score 18 — impossible to reach without crypto boosters. Multiple strategies surgical-blocked. Only penalty mechanisms applied.

**Strategy additions:**
| Strategy | Source | Status | Action |
|----------|--------|--------|--------|
| `forex_carry_momentum_harvest` | baby_strategies/ | Academic carry+momentum, VIX filter | Backtest → wire |
| `forex_ensemble_4h_rehab` | baby_strategies/ | EUR/GBP/AUD/CAD ensemble | Promote from rehab |
| `forex_inside_day_breakout` | baby_strategies/ | Inside day breakout pattern | Backtest → wire |
| `forex_weekly_open_gap_fill` | baby_strategies/ | Weekly gap fill | Backtest → wire |
| `ig_contrarian_sentiment` | forex_strategies.py | Sharpe 5.87 backtest, LONG blocked | Unblock LONG (pending phantom fix) |

**Gate improvements:**
- Add FOREX SHORT-only preference: SHORT side across all forex strategies shows 46-60% WR vs LONG at 10-35%. Gate: favor SHORT, penalize LONG unless proven.
- Add session liquidity gate: only emit FOREX picks during London/NY overlap (07:00-17:00 UTC)
- Add DXY trend awareness: favor USD SHORTs when DXY falling, USD LONGs when DXY rising
- Lower FOREX elite score floor: currently 70, but scores land at 18. Need to either lower floor OR add FOREX score boosters.
- **Re-evaluate:** `myfxbook_retail_contrarian` block (quality_gates.py:1666) — blocked due to phantom_expired data. Re-check after resolver fix.

**Expected impact:** 5-8 active forex picks. WR should improve from 46.4% to 50%+ if SHORT-only gate applied.

---

### 4. ETF — PF 1.41, 3 Active (score 30-32)

**Strategy additions:**
| Strategy | Source | Status | Action |
|----------|--------|--------|--------|
| `etf_faber_tactical` | etf_strategies.py | Coded but NOT in scanner dispatch | Add to etf_scanner.py:77-82 |
| `etf_connors_rsi2_mr` | new_strategies/ | Not in ETF_STRATEGIES registry | Wire to registry |
| VIX regime gate | vix_regime_gate.py | PF 3.91 on ETF with VIX<20 | Set `VIX_REGIME_GATE_ENABLED=1` |

**Symbol expansion:** ETF symbols already well-covered (55 in config.py). Consider adding sector ETFs: XBI (biotech), XRT (retail), XHB (homebuilders), XME (metals/mining).

**Expected impact:** 5-10 active ETF picks with VIX gate. PF should improve from 1.41 to 2.0+.

---

### 5. BOND — PF 0.66, 0 Active (5 Strategies Coded, Scanner Broken)

**Why nothing is emitting:** `bond_scanner.py` exists (303 lines, 5 strategies), `bond_strategies.py` exists (538 lines), but the FRED API timeout blocks data fetching. The scanner is imported in `scanner.py` but `active_picks_bond.json` shows `pick_count: 0, is_draft: true`.

**Strategy additions:**
| Strategy | Source | Status | Action |
|----------|--------|--------|--------|
| `bond_yield_momentum` | bond_strategies.py:58 | SMA20/50+RSI | Works on yfinance OHLC (no FRED needed) |
| `bond_duration_rotation` | bond_strategies.py:159 | TLT SMA50/200 proxy | Works on yfinance OHLC |
| `bond_mean_reversion` | bond_strategies.py:240 | Bollinger Bands + volume | Works on yfinance OHLC |
| `bond_connors_rsi2` | bond_strategies.py:354 | Connors on TLT/IEF/LQD | Works on yfinance OHLC |
| `bond_credit_spread_mean_reversion` | bond_strategies.py:452 | HYG-LQD spread | Needs `BOND_ENABLE_CREDIT_SPREAD=1` (env var) |

**Critical fix:** Set `SKIP_FRED=1` (already in workflow), verify TLT/IEF/SHY/LQD/HYG/AGG/BND/EMB yfinance data is fetchable, then run `python -m alpha_engine.bond_scanner --merge`.

**Symbol expansion:** Already have TLT, IEF, SHY, LQD, HYG, AGG, BND, EMB. Add TIP (TIPS), MUB (munis), BNDX (international bonds).

**Expected impact:** 3-5 active bond picks within days of fixing data pipeline. PF should improve from 0.66 with quality-gated strategies.

---

### 6. FUTURES — PF None, 0 Active (No Strategies, No Scanner)

**Strategy additions (need to build):**
- Futures trend following: 12-month time-series momentum on ES, NQ, CL, GC, ZB
- Futures carry: calendar spread carry on commodity futures
- VIX futures term structure: contango/backwardation signals
- Micro futures: MES, MNQ, MCL, MGC for position sizing compatibility

**Immediate opportunity:** Adapt existing `commodity_tsmom_12m` strategy to futures tickers (ES=F, NQ=F, CL=F, GC=F, ZB=F). The strategy exists but targets ETF proxies instead of direct futures.

**Expected impact:** 2-4 active futures picks within 2-4 weeks (requires new scanner build).

---

## Cross-Cutting Improvements

### Score Booster Expansion (Enables Non-Crypto Picks)

Currently, only CRYPTO gets signal confirmation boosters:
- MTF multi-timeframe (+8): score_booster.py:1015-1057 — CRYPTO ONLY
- Ensemble 2-of-3 (+5): score_booster.py:1059-1119 — CRYPTO ONLY

**Build non-crypto equivalents:**
| Asset Class | Booster | Score | Data Source |
|------------|---------|-------|-------------|
| EQUITY | VWAP + OBV + SPY sector alignment | +6/+8 | yfinance |
| FOREX | DXY correlation + session liquidity | +5/+8 | OANDA/yfinance |
| COMMODITY | DXY inverse + COT positioning | +6/+8 | CFTC COT report |
| ETF | Sector relative strength + VIX regime | +5/+7 | yfinance |
| BOND | Yield curve slope + credit spread | +4/+6 | FRED/yfinance |

### Gate Standardization

**Elite score floors should be data-calibrated, not manual-guessed:**

| Class | Current Floor | Actual Score Range | Recommended | Reason |
|-------|--------------|-------------------|-------------|--------|
| CRYPTO | 70 | 0-100 (med 47) | 70 | Keep — crypto gets boosters |
| EQUITY | 60 | 14-30 | **40** | Floor 2x higher than max attainable |
| COMMODITY | 55 (was 65) | — | **35** | PF 4.03 justifies wider admission |
| FOREX | 70 | 18 | **45** | No score boosters, floor unreachable |
| ETF | 50 | 30-32 | **35** | Similar to EQUITY |
| BOND | 40 | — | **30** | Smallest sample, widest floor |

### Strategy Promotion Pipeline

210 baby strategies exist. Only ~30 wired to production. Create a systematic promotion gate:

1. Backtest runner: automated backtest of all 210 on historical data
2. Survivor filter: WR ≥ 50%, PF ≥ 1.2, Sharpe ≥ 0.5, n ≥ 50
3. Walk-forward: 12-month OOS validation
4. Promotion: survivors → registered in scanner with lowered score floors
5. Monitoring: daily performance tracking, auto-demotion if PF < 0.8 for 20+ trades

---

## Implementation Roadmap

### Phase 1: Immediate Activation (Today, 0 Risk)

| # | Action | Class | Env Var / Code | Impact |
|---|--------|-------|----------------|--------|
| 1 | Activate VIX regime gate | EQUITY, ETF | `VIX_REGIME_GATE_ENABLED=1` | PF 2.82→4.55 (EQUITY), PF→3.32 (ETF) |
| 2 | Activate YC regime gate | EQUITY, ETF | `YC_REGIME_GATE_ENABLED=1` | PF→4.98 combined |
| 3 | Fix bond scanner data pipeline | BOND | `SKIP_FRED=1` + verify yfinance | 5 strategies go live |
| 4 | Enable bond credit spread | BOND | `BOND_ENABLE_CREDIT_SPREAD=1` | One more bond strategy |
| 5 | Lower EQUITY elite floor 60→40 | EQUITY | config.py | Admits 4 existing picks |
| 6 | Lower COMMODITY elite floor 55→35 | COMMODITY | config.py | Admits commodity picks |
| 7 | Lower FOREX elite floor 70→45 | FOREX | config.py | Admits 2 existing picks |
| 8 | Lower ETF elite floor 50→35 | ETF | config.py | Admits existing picks |

### Phase 2: Strategy Wiring (This Week, ~8h)

| # | Action | Class | Source |
|---|--------|-------|--------|
| 9 | Wire `commodity_range_position_reversion` | COMMODITY | baby_strategies/ |
| 10 | Wire `commodity_trend_pullback_rsi` | COMMODITY | baby_strategies/ |
| 11 | Wire `equity_vix_regime_momentum` | EQUITY | baby_strategies/ |
| 12 | Wire `equity_sector_rotation_momentum` | EQUITY | baby_strategies/ |
| 13 | Wire `forex_carry_momentum_harvest` | FOREX | baby_strategies/ |
| 14 | Wire `forex_ensemble_4h_rehab` | FOREX | baby_strategies/ |
| 15 | Add `etf_faber_tactical` to etf_scanner.py dispatch | ETF | etf_strategies.py |
| 16 | Wire `etf_connors_rsi2_mr` to ETF_STRATEGIES | ETF | new_strategies/ |
| 17 | Backtest top 15 baby strategies (WR≥60%, PF≥1.5) | ALL | baby_strategies/ |
| 18 | Wire survivors from backtest | ALL | promotion pipeline |

### Phase 3: Score Booster Expansion (Next 2 Weeks, ~12h)

| # | Action | Class |
|---|--------|-------|
| 19 | Build EQUITY confirmation gate (VWAP+OBV+SPY) | EQUITY |
| 20 | Build FOREX confirmation gate (DXY+session) | FOREX |
| 21 | Build COMMODITY confirmation gate (DXY inverse+COT) | COMMODITY |
| 22 | Build ETF confirmation gate (sector RS+VIX) | ETF |
| 23 | Build BOND confirmation gate (yield curve+credit spread) | BOND |

### Phase 4: New Asset Class Development (Next Month, ~20h)

| # | Action | Class |
|---|--------|-------|
| 24 | Build futures scanner + strategies (ES, NQ, CL, GC) | FUTURES |
| 25 | Build standalone BOND baby strategies (TLT momentum, yield carry) | BOND |
| 26 | Build direct commodity strategies (GC=F, SI=F, CL=F) | COMMODITY |
| 27 | Auto-promotion pipeline: backtest → WF → promote → monitor | ALL |

---

## Success Metrics

| Metric | Current | Phase 1 Target | Phase 2 Target | Phase 3+4 Target |
|--------|---------|---------------|---------------|-----------------|
| COMMODITY active picks | 0 | 3-5 | 5-8 | 8-12 |
| EQUITY active picks | 4 | 6-10 | 10-15 | 15-20 |
| FOREX active picks | 2 | 3-5 | 6-10 | 8-12 |
| ETF active picks | 3 | 5-8 | 8-12 | 10-15 |
| BOND active picks | 0 | 2-4 | 3-5 | 5-8 |
| FUTURES active picks | 0 | 0 | 1-2 | 3-5 |
| Total active (non-crypto) | 9 | 19-32 | 33-52 | 50-70 |
| Overall system PF | — | +0.05-0.10 | +0.10-0.20 | +0.15-0.30 |
| Per-class coverage | 4/7 classes | 6/7 classes | 7/7 classes | 7/7 classes |

---

## Verification

After each phase:
1. Run `python tools/analyze_audit_scores_vs_pnl.py` to measure per-class IC changes
2. Check `dashboard_data.json` for active pick count per class
3. Verify no regression in CRYPTO (93% volume, must not degrade)
4. Monitor smart_picks feed for under-represented classes
5. Run syntax checks on all modified files

---

## Files Referenced

| File | Purpose |
|------|---------|
| `baby_strategies/*.py` (210 files) | Untapped strategy pool |
| `alpha_engine/commodities_strategies.py` | 9 commodity strategies, zero emitting |
| `alpha_engine/bond_strategies.py` / `bond_scanner.py` | 5 bond strategies, scanner broken |
| `alpha_engine/etf_strategies.py` / `etf_scanner.py` | ETF strategies, 1 missing from dispatch |
| `alpha_engine/forex_strategies.py` | Forex strategies, several blocked |
| `alpha_engine/new_equity_commodity_strategies_20.py` | 20 new equity/commodity strategies |
| `audit_trail/vix_regime_gate.py` | VIX gate, OFF by default, PF 4.55 backtest |
| `alpha_engine/score_booster.py` | Crypto-only boosters, needs expansion |
| `alpha_engine/config.py` | Elite score floors, per-class risk params |
| `audit_trail/quality_gates.py` | Blocked strategies, score floors, per-class gates |
