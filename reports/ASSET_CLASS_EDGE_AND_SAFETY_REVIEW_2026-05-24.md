# Asset-Class Edge & Safety Review — Hedge Fund Grade
**Date:** 2026-05-24 | **Scope:** findtorontoevents.ca/audit + /audit/hyrotrader + /audit/ai-tournament

---

## Executive Summary

We audited the prediction stack across 6 asset classes (EQUITY, CRYPTO, FOREX, COMMODITY, ETF, BOND) to identify gaps preventing hedge-fund-quality picks. Only **2 proven edge pairs exist** (deep_value × EQUITY: n=60, WR 60.0%; momentum_breakout × ETF: n=46, WR 58.7%). FOREX is a statistical trap (57.3% WR but -0.39% avg PnL, Sharpe -0.22). FUTURES is hard-blocked (157 picks, 2.5% WR). The pipeline has a broken confidence field (0.00 across all tournament_picks rows) and possible regime label data leakage (regime_adaptive: 84.6% WR on n=13).

**Immediate priority:** Fix P1 (confidence proxy) + P0 (regime label audit) + FOREX zero-allocation — all parallelizable, ~38 lines total.

---

## Part 1: US Equity Long-Term Value Picks — Safety Critique

The UEPS (Universal Equity Pick Screener) produces `long_term_value` picks using the `magic_formula_x_piotroski_x_acquirers` strategy. All 21 picks pass the safety gate (Altman Z'' ≥ 1.10 AND Beneish M ≤ -1.78). Here is a hedge-fund-grade critique of the top 3:

### ADBE (Adobe) — Score 0.839 | Rank #1

| Metric | Value | Grade | Notes |
|--------|-------|-------|-------|
| Magic Formula Rank | #1 of 49 | 🟢 Elite | Best composite of ROIC + earnings yield in universe |
| F-Score | 7/9 | 🟢 Strong | High fundamental momentum |
| ROIC | 45.1% | 🟢 Exceptional | Moat indicator — software IP with 90%+ gross margins |
| Acquirer's Multiple | 12.87 | 🟢 Cheap | Operating earnings / EV — well below 15x "value" threshold |
| Altman Z'' | 3.94 | 🟢 Safe | 3.6x above the 1.10 distress threshold |
| Beneish M | -2.90 | 🟢 Clean | Strongly negative = zero earnings manipulation probability |
| FCF Yield | 8.8% | 🟢 Excellent | Generates real cash, not accounting profits |
| D/E | 1.54 | 🟡 Moderate | Acceptable for a software company with recurring revenue |
| EPS Trend | 8 consecutive beats | 🟢 Consistent | Management under-promises, over-delivers |
| Dividend | None | 🟡 Neutral | Capital allocation toward buybacks + AI R&D, not dividends |
| Intrinsic Value | $367.14 (50% upside) | 🟢 Deep discount | Entry at ~67% of IV |

**SAFETY VERDICT: ✅ SAFE — Highest quality pick in the universe.**
ADBE is a fortress pick. It ranks #1 on Magic Formula, has near-perfect manipulation scores, generates 8.8% FCF yield on a 45% ROIC business, and has 8 consecutive EPS beats. The only yellow flag is D/E=1.54, which is well within tolerance for a software company with $20B+ in recurring revenue. This is the type of pick a value hedge fund (Baupost, Greenlight) would hold for 3+ years. **Fortress-grade.**

### PYPL (PayPal) — Score 0.785 | Rank #2

| Metric | Value | Grade | Notes |
|--------|-------|-------|-------|
| Magic Formula Rank | #6 of 49 | 🟢 Excellent | Top decile |
| F-Score | 8/9 | 🟢 Exceptional | Highest F-Score in the top 10 — fundamental momentum is peaking |
| ROIC | 18.0% | 🟢 Good | Above cost of capital, but not moat-level |
| Acquirer's Multiple | 14.83 | 🟢 Cheap | Solid value at <15x |
| Altman Z'' | 2.78 | 🟢 Safe | 2.5x above distress |
| Beneish M | -2.58 | 🟢 Clean | No manipulation flags |
| FCF Yield | 6.2% | 🟢 Good | Solid cash generation |
| D/E | 2.96 | 🟡 Elevated | Fintech leverage — monitor if rates stay high |
| EPS Trend | 7 consecutive beats, 1 upcoming | 🟢 Strong | Recent beats include +23% and +14% surprises |
| Dividend | 0.63% yield, 5.3% payout ratio | 🟢 Growing | Tiny payout ratio = dividend growth runway |
| Intrinsic Value | $66.34 (50% upside) | 🟢 Deep discount | |

**SAFETY VERDICT: ✅ SAFE — Strong fundamentals with one yellow flag.**
PYPL is a high-quality value play. The F-Score of 8/9 is exceptional — this is a company in fundamental acceleration. EPS beats are large and consistent. The D/E of 2.96 is the primary concern (fintech balance sheets are rate-sensitive), but with a 5.3% payout ratio and 6.2% FCF yield, the debt is well-covered. **Investment-grade with a monitor flag on leverage.**

### QCOM (Qualcomm) — Score 0.738 | Rank #3

| Metric | Value | Grade | Notes |
|--------|-------|-------|-------|
| Magic Formula Rank | #5 of 49 | 🟢 Excellent | |
| F-Score | 7/9 | 🟢 Strong | |
| ROIC | 30.1% | 🟢 Excellent | IP licensing + chip design = high structural ROIC |
| Acquirer's Multiple | 22.19 | 🟡 Fair | Above 15x — less "deep value" than ADBE/PYPL |
| Altman Z'' | 4.33 | 🟢 Very Safe | Highest Z'' in the top 5 |
| Beneish M | -3.20 | 🟢 Very Clean | Best manipulation score among top 3 |
| FCF Yield | 5.1% | 🟡 Moderate | Lower than peers due to high capex cycle |
| D/E | 5.89 | 🔴 High | Semiconductor fab + 5G investment cycle — structural, but elevated |
| EPS Trend | 5 of 7 beats, 2 misses | 🟡 Mixed | Recent misses suggest cyclical headwinds |
| Dividend | 1.49% yield, 38% payout | 🟢 Strong | 5-year consecutive growth, well-covered |
| Intrinsic Value | $345.33 (45% upside) | 🟢 Discount | |

**SAFETY VERDICT: ⚠️ CAUTIOUSLY SAFE — Excellent quality + structural leverage concern.**
QCOM has the best Altman Z'' (4.33) and Beneish M (-3.20) of the top 3 — the business is fundamentally sound and earnings are clean. But D/E of 5.89 is genuinely high (semiconductor capex cycle), the Acquirer's Multiple at 22.19 suggests it's less of a bargain, and recent EPS misses hint at cyclical pressure. This is a quality company but not a "sleep-well-at-night" pick at this entry. **Quality-grade, but size smaller and monitor semiconductor cycle.**

### Full UEPS Top-10 Rankings (Safety-Adjusted)

| Rank | Symbol | Score | Safety | Key Concern |
|------|--------|-------|--------|-------------|
| 1 | ADBE | 0.839 | 🟢 Fortress | None |
| 2 | PYPL | 0.785 | 🟢 Safe | D/E 2.96 |
| 3 | QCOM | 0.738 | 🟡 Cautious | D/E 5.89, recent EPS misses |
| 4 | META | 0.729 | 🟡 Cautious | F-Score 5/9, 1 massive EPS miss (-84%) |
| 5 | HD | 0.717 | 🟢 Safe | D/E 7.20 (retail — structurally high), 3 EPS misses |
| 6 | MA | 0.712 | 🟢 Safe | D/E 6.00 (payments — structurally high) |
| 7 | GOOGL | 0.647 | 🟢 Safe | Magic Rank #24 (higher AM at 36.81) |
| 8 | XOM | 0.631 | 🟢 Safe | ROIC 11% (low), F-Score 5/9 |
| 9 | MDT | 0.623 | 🟡 Cautious | 2 large EPS misses (-12%, -33%) |
| 10 | V | 0.620 | 🟢 Safe | AM 27.69 (fair, not cheap) |

### UEPS Safety Gates — What's Working and What's Missing

**Working well:**
- Altman Z'' gate (all picks > 1.10): Effective bankruptcy filter
- Beneish M gate (all picks ≤ -1.78): Effective manipulation filter
- ROIC/D/E thesis-break rules: Automated exit if fundamentals deteriorate
- 8-quarter EPS history: Good transparency on earnings consistency

**Missing — should be added for hedge-fund grade:**
1. **Position sizing by conviction:** All 21 picks are equally weighted. ADBE at 0.839 should get 2-3x the allocation of JNJ at 0.436.
2. **Sector concentration check:** Top 10 includes 3 tech (ADBE, QCOM, GOOGL), 2 payments (PYPL, MA, V), 1 social (META). Need a max-sector-exposure rule.
3. **Earnings catalyst calendar:** Upcoming earnings dates (ADBE Jun 11, PYPL Jul 28, QCOM Jul 29) should trigger position review, not blind holds.
4. **D/E threshold:** D/E > 5.0 should trigger a yellow flag (QCOM 5.89, HD 7.20, MA 6.00). Currently only the thesis-break at much higher thresholds catches this.
5. **Momentum overlay:** Entry timing matters even for 3y holds. A simple 50-day MA filter would avoid entering deep value traps.

---

## Part 2: Per-Asset-Class Feature Matrix & Gaps

### EQUITY — Current State: 🟢 BEST-IN-CLASS

**Live features (per_asset_class_predictor.py weights):**
- trust_score: 0.35 (strongest verified IC: +0.154)
- elite_score: 0.15 (IC +0.023 — borderline noise)
- direction_x_regime: 0.20 (design intent, not empirically verified)
- freshness: 0.10
- tp_upside_remaining: 0.10
- htf_alignment: 0.05
- sector_rs_score: 0.05 (IDEA-A — not yet wired live)

**UEPS-specific features (value_screener.py):**
- Magic Formula rank (ROIC + earnings yield composite)
- Piotroski F-Score (9-point fundamental momentum)
- Acquirer's Multiple (operating earnings / EV)
- Altman Z'' (bankruptcy risk)
- Beneish M-Score (earnings manipulation)
- ROIC, FCF Yield, D/E
- 8-quarter EPS surprise history
- 5-year dividend growth record
- Next earnings date (catalyst calendar)

**Edge pairs proven:** deep_value × EQUITY (n=60, WR 60.0%, +1.07% avg)

**Gaps to close:**
| Gap | Priority | Effort | Impact | Notes |
|-----|----------|--------|--------|-------|
| Sector RS score live wiring | P1 | 2h | Medium | Already in weights map, just needs data pipeline |
| Earnings revision momentum | P2 | 4h | High | Zacks-style — strongest post-announcement drift signal |
| Short interest / days-to-cover | P2 | 3h | Medium | Contrarian signal — high SI + strong fundamentals = squeeze candidate |
| Institutional ownership flows | P2 | 4h | Medium | 13F filings — "smart money" following |
| Management quality (ROIC stability) | P3 | 2h | Low | Can derive from existing ROIC data (coefficient of variation) |
| Beta to macro factors | P3 | 3h | Low | Rate sensitivity, inflation beta — for regime-appropriate sizing |
| D/E threshold flag (<3.0 green, 3-5 yellow, >5 red) | P1 | 1h | High | Simple rule, catches QCOM/HD/MA leverage |

### CRYPTO — Current State: 🟡 MATURE BUT GAPPY

**Live features:** trust_score: 0.40, direction_x_regime: 0.25, elite_score: 0.10, freshness: 0.10, tp_upside_remaining: 0.10, htf_alignment: 0.05

**Quality gates active:**
- Banned symbols: DOGE, OP, LINK, ADA, LTC, TON, WIF, PEPE, BONK, SHIB, FLOKI, BOME
- Banned strategies: macd_rsi_confluence
- Confidence dead band: [0.60, 0.70)
- RSI-1h overbought: ≥60
- C-TIER suspended (PF 0.36, -46.59% PnL)

**Conviction tiers:** S (DOT/SUI/LTC/NEAR/XRP × fear_greed + PROVEN + bull regime), A (expanded symbols + PROVEN/WATCH), B (BTC/ETH + PROVEN)

**Edge pairs proven:** None meet n≥20 + WR≥55% thresholds

**Gaps to close:**
| Gap | Priority | Effort | Impact | Notes |
|-----|----------|--------|--------|-------|
| On-chain exchange flows (whale accumulation) | P1 | 6h | High | Net exchange outflow = accumulation = bullish |
| Funding rate premium vs spot | P1 | 3h | High | Extreme positive funding → short signal; extreme negative → long |
| Open interest momentum | P2 | 3h | Medium | OI increasing + price rising = trend confirmation |
| Stablecoin market cap change | P2 | 2h | Medium | USDT/USDC supply expansion = buying power inflow |
| BTC dominance trend | P2 | 1h | Medium | BTC.D rising = risk-off; falling = alt season |
| Volume profile (VPVR support/resistance) | P3 | 4h | Low | Better entry/exit levels |
| Bid-ask spread / market depth | P3 | 3h | Low | Liquidity filter for position sizing |

### FOREX — Current State: 🔴 STATISTICAL TRAP

**Live features:** trust_score: 0.40, direction_x_regime: 0.20, elite_score: 0.10, freshness/tp_upside/htf_alignment: 0.10 each

**Quality gates active:**
- Banned symbols: AUDUSD, CADJPY, EURJPY (PF < 0.50 on n≥44)
- Banned strategies: Breakout Momentum (45% WR, -0.551% avg)
- Confidence reject: [0.95, 1.00) (overconfidence trap)
- Score floor: 45 (raised from 40 for HF performance)

**Reality:** 57.3% WR but -0.39% avg PnL, Sharpe -0.22. Many small wins, few large losers (3.2:1 loss-to-win ratio). **The signal is real but the risk management is broken.**

**Recommendation:** Zero-allocate FOREX immediately (Sprint 1, Item 3 in EDGE_CRITERIA action plan).

**Gaps to close (only if/when re-enabled):**
| Gap | Priority | Effort | Impact | Notes |
|-----|----------|--------|--------|-------|
| Asymmetric TP/SL (wider TP, tighter SL) | P0 | 2h | Critical | Current 3.2:1 loss-to-win ratio is the root cause |
| Carry trade signal (IR differential) | P1 | 4h | High | Most persistent FX anomaly in academic literature |
| CoT positioning (speculator vs commercial) | P1 | 3h | High | Commercials are usually right at extremes |
| Central bank policy divergence | P2 | 3h | Medium | Hawkish vs dovish — rate path pricing |
| Economic surprise index | P2 | 2h | Medium | Citigroup ESI — data vs consensus |
| Volatility regime (realized vs implied) | P3 | 2h | Low | GARCH/EWMA vol for position sizing |

### COMMODITY — Current State: 🟡 EMERGING

**Live features:** trust_score: 0.35, direction_x_regime: 0.20, elite_score: 0.10, freshness/tp_upside: 0.10 each, htf_alignment: 0.05, **bdi_momentum_score: 0.05 (IDEA-A)**, **crop_condition_score: 0.05 (IDEA-A)**

**Quality gates:** Banned strategy (cta_commodity_momentum_term: PF 0.02, n=46), confidence minimum 0.70

**Gaps to close:**
| Gap | Priority | Effort | Impact | Notes |
|-----|----------|--------|--------|-------|
| Term structure (backwardation/contango) | P1 | 3h | High | Backwardation = positive roll yield = long bias |
| BDI momentum live wiring | P1 | 2h | Medium | Already in weights, needs data pipeline |
| Crop condition live wiring | P1 | 2h | Medium | USDA NASS — seasonal, but high signal for ags |
| Inventory levels (EIA for energy, WASDE for ags) | P2 | 4h | Medium | Supply-side shocks |
| China demand proxy (copper imports, PMI) | P2 | 3h | Medium | China = 50%+ of global commodity demand |
| USD strength index (DXY correlation) | P2 | 1h | Medium | Strong dollar = commodity headwind (mostly) |

### ETF — Current State: 🟢 PROVEN EDGE

**Live features:** trust_score: 0.35, elite_score: 0.15, direction_x_regime: 0.20, freshness: 0.10, tp_upside: 0.10, htf_alignment: 0.10

**Quality gates:** Banned symbols (IWM, GLD)

**Edge pairs proven:** momentum_breakout × ETF (n=46, WR 58.7%, +0.17% avg) ✅ Tier-1

**Gaps to close:**
| Gap | Priority | Effort | Impact | Notes |
|-----|----------|--------|--------|-------|
| Sector rotation signals (relative strength) | P1 | 3h | High | RS vs SPY — momentum factor applied to sectors |
| Flow-of-funds (ETF inflows/outflows) | P2 | 4h | Medium | Weekly ETF flow data — sentiment proxy |
| NAV premium/discount | P2 | 2h | Low | Arbitrage signal — mean-reverts quickly |
| Tracking error | P3 | 1h | Low | Quality filter — skip ETFs with >1% TE |

### BOND — Current State: 🔴 DATA-STARVED

**Live features:** trust_score: 0.40, elite_score: 0.10, direction_x_regime: 0.20, freshness/tp_upside/htf_alignment: 0.10 each

**Reality:** n=17 closed picks total. Too small for any statistical claim. Allow all (no gates).

**Gaps to close:**
| Gap | Priority | Effort | Impact | Notes |
|-----|----------|--------|--------|-------|
| Duration risk metric | P1 | 3h | High | Modified duration × rate forecast = expected return |
| Yield curve slope signal | P1 | 2h | High | 2s10s spread — steepening = long duration, flattening = short |
| Credit spread (OAS) analysis | P2 | 3h | Medium | Corporate bond quality filter |
| Fed funds futures implied path | P2 | 2h | Medium | Market-implied rate expectations |
| Inflation breakeven (TIPS vs nominals) | P3 | 2h | Low | Real rate signal |

---

## Part 3: Super-Secure Pick Personas — Per Asset Class

### EQUITY "Fortress Value" 🏰

Only fires when ALL conditions align. Expected: 1-3 picks per month from a 49-stock universe.

```yaml
persona: fortress_value
asset_class: EQUITY
holding_horizon: 3y+
max_positions: 5

conditions:
  ALL:
    - magic_formula_rank <= 3            # Top 6% of universe
    - piotroski_f >= 7                   # High fundamental momentum
    - altman_z_double_prime > 2.5        # 2.3x above distress
    - beneish_m < -2.5                   # Zero manipulation probability
    - debt_to_equity < 3.0               # Conservative leverage
    - roic > 0.15                        # Moat-worthy returns on capital
    - fcf_yield > 0.05                   # Real cash generation
    - dividend_growth_years >= 3         # OR buyback yield > 2%
    - eps_misses_last_4q == 0            # No recent disappointments
    - sector_concentration <= 30%        # Max 30% in any one sector

  sizing: 1.5% of NAV per position (max 7.5% total)
  exit: thesis_break (any condition fails) OR 30% trailing stop from peak
  review: quarterly with earnings
```

**Current picks qualifying:** ADBE (meets all 10 conditions). PYPL fails D/E (2.96 < 3.0 barely — borderline). QCOM fails D/E (5.89) and Magic Rank (#5 vs #3 threshold).

### CRYPTO "Institutional Grade" 🏦

Only fires on BTC/ETH with PROVEN trust and verified edge. Expected: 0-2 picks per week.

```yaml
persona: institutional_crypto
asset_class: CRYPTO
holding_horizon: 7-30d
max_positions: 3

conditions:
  ALL:
    - symbol in [BTCUSDT, ETHUSDT]      # Institutional-grade only
    - trust_tier == PROVEN               # Verified track record
    - strategy contains fear_greed_contrarian
    - forward_wr >= 60%                  # Statistical edge threshold
    - forward_trades >= 30               # Sufficient sample
    - regime in [bull, neutral, uptrend] # No bear-market longs
    - ml_score >= 0.82 if present        # ML quality gate
    - confidence NOT in [0.60, 0.70)     # Dead band reject
    - rsi_1h < 60 if present             # Not overbought on fast TF
    - funding_rate > -0.01%              # Not in extreme backwardation
    - symbol NOT in CRYPTO_BANNED_SYMBOLS

  sizing: 0.75% of NAV per position (max 2.25% total)
  exit: TP/SL as per strategy, OR 14d time stop
  review: daily
```

### FOREX "Carry Fortress" 💱 — DEFERRED

```yaml
persona: carry_fortress
status: SUSPENDED
reason: Zero-allocated per EDGE_CRITERIA_SWARM. 57.3% WR but -0.39% avg PnL.
       Asymmetric TP/SL fix needed before any FOREX persona can fire.
re_evaluation: After asymmetric TP/SL fix + 30d paper-trading proof of life.
```

### COMMODITY "Supply-Demand Fortress" 🛢️

```yaml
persona: supply_demand_fortress
asset_class: COMMODITY
holding_horizon: 14-60d
max_positions: 4

conditions:
  ALL:
    - confidence >= 0.70                 # Above structural-break threshold
    - confidence < 0.95                  # Not in overconfidence trap
    - strategy NOT in COMMODITY_BANNED_STRATEGIES
    - term_structure == backwardation    # Positive roll yield
    - bdi_momentum_score > 50 if present # BDI supportive (IDEA-A)
    - crop_condition_score > 50 if ag    # Favorable growing conditions (IDEA-A)
  ANY:
    - inventory_below_5yr_avg            # Supply tightness
    - china_demand_index > 50            # Demand tailwind

  sizing: 1.0% of NAV per position (max 4% total)
  exit: term structure flips to contango OR 60d time stop
  review: weekly
```

### ETF "Momentum Fortress" 📈

```yaml
persona: momentum_fortress
asset_class: ETF
holding_horizon: 14-45d
max_positions: 5

conditions:
  ALL:
    - strategy == momentum_breakout       # Only proven edge pair
    - forward_wr >= 55%                   # Verified WR threshold
    - trust_tier in [PROVEN, RELIABLE]
    - regime in [bull, neutral, uptrend]
    - sector_rs_score > 60 if equity ETF   # Sector outperforming
    - symbol NOT in ETF_BANNED_SYMBOLS    # IWM, GLD excluded
    - confidence NOT overconfident

  sizing: 1.0% of NAV per position (max 5% total)
  exit: momentum signal flips OR 45d time stop
  review: weekly
```

### BOND "Duration Fortress" 📊 — ACCUMULATING

```yaml
persona: duration_fortress
asset_class: BOND
status: ACCUMULATING
reason: n=17 closed picks — too small for statistical claims.
       Need n>=50 before any persona can fire.
action: Run in shadow mode, stamp picks as bond_shadow, collect data.
```

---

## Part 4: Gap-Closing Priority Matrix

### Immediate (Sprint 1, this week) — ~38 lines

| # | Gap | Where | Lines | Impact |
|---|-----|-------|-------|--------|
| 1 | **Confidence field fixed** (persona_WR proxy) | `alpha_engine/score_booster.py` ~L45 | 5 | Unlocks Kelly sizing, conviction tiers, all downstream logic |
| 2 | **Regime label timestamp audit** | `alpha_engine/regime_flip_detector.py` + `regime_position_sizer.py` | 25 | Prevents strategy-killing data leakage |
| 3 | **FOREX zero-allocation** | `alpha_engine/scanner.py` filter stage | 8 | Stops bleeding on proven losing asset class |
| 4 | **UEPS D/E yellow/red flag** | `alpha_engine/value_screener.py` or `long_term_pick_contract.py` | ~10 | Flags QCOM (5.89), HD (7.20), MA (6.00) |

### Short-term (Sprint 2, next week)

| # | Gap | Effort | Impact |
|---|-----|--------|--------|
| 5 | Whale consensus boost (≥2 verified whales) | 3h | +0.10 confidence for consensus picks |
| 6 | Position sizing rules (Kelly, max 10 positions, 5% class cap) | 4h | Portfolio-level risk management |
| 7 | Sector RS score live wiring (EQUITY) | 2h | Already in weight map — data pipeline only |
| 8 | US Equity Fortress Value persona implementation | 3h | Super-secure picks for 3y holds |

### Medium-term (Sprint 3-4)

| # | Gap | Effort | Impact |
|---|-----|--------|--------|
| 9 | On-chain exchange flows (CRYPTO) | 6h | Whale accumulation signal |
| 10 | Funding rate premium (CRYPTO) | 3h | Sentiment extreme detector |
| 11 | Term structure (COMMODITY) | 3h | Roll yield signal |
| 12 | CoT positioning (FOREX — if re-enabled) | 3h | Smart money following |
| 13 | Carry trade signal (FOREX — if re-enabled) | 4h | Most persistent FX anomaly |
| 14 | Yield curve slope (BOND) | 2h | Duration timing |
| 15 | Duration risk metric (BOND) | 3h | Rate sensitivity sizing |

---

## Part 5: Integration with Existing Action Plan

This review extends the EDGE_CRITERIA_ACTION_PLAN_2026-05-24.md. Items map as follows:

| EDGE_CRITERIA Item | This Review | Status |
|-------------------|-------------|--------|
| P1 — Persona_WR confidence | Part 4, Item 1 | Same — foundation fix |
| P0 — Regime label audit | Part 4, Item 2 | Same — P0 critical |
| FOREX zero allocation | Part 4, Item 3 | Same — immediately needed |
| P2 Dashboard migration | Not covered here | Separate infra task |
| P2 Whale consensus boost | Part 4, Item 5 | Same — Sprint 2 |
| P3 Position sizing | Part 4, Item 6 | Same — Sprint 2 |
| — | UEPS D/E flag | **NEW** — Part 4, Item 4 |
| — | Fortress personas | **NEW** — Part 3 |
| — | Per-asset feature gaps | **NEW** — Part 2 |

---

## Appendix A: Files Referenced

| File | Purpose |
|------|---------|
| `alpha_engine/per_asset_class_predictor.py` | Per-class smart-score predictor with verified-IC weights |
| `alpha_engine/conviction_stack.py` | HF conviction tier system (S/A/B) |
| `alpha_engine/hedge_fund_quality_gate.py` | Per-asset-class rejection rules |
| `alpha_engine/value_screener.py` | UEPS Magic Formula × Piotroski × Acquirer's pipeline |
| `alpha_engine/long_term_pick_contract.py` | long_term_value pick contract + validation |
| `audit_dashboard/data/ueps_picks.json` | Live UEPS picks (21 symbols, 2026-05-24) |
| `config/hf_quality_gates.json` | HF quality gate thresholds (v2) |
| `config/hf_conviction_tiers.json` | HF conviction tier config (v2) |
| `reports/EDGE_CRITERIA_SWARM_SYNTHESIS_2026-05-24.md` | 3-agent swarm audit findings |
| `reports/EDGE_CRITERIA_ACTION_PLAN_2026-05-24.md` | 2-engine action plan consensus |

## Appendix B: Key Statistical Constants

| Constant | Value | Source |
|----------|-------|--------|
| trust_score IC (Spearman ρ vs pnl_pct) | +0.154 | per_asset_class_predictor.py |
| elite_score IC (Spearman ρ vs pnl_pct) | +0.023 | per_asset_class_predictor.py — NOISE |
| confidence IC (Spearman ρ vs pnl_pct) | -0.048 | per_asset_class_predictor.py — INVERTS |
| deep_value × EQUITY edge | n=60, WR 60.0%, +1.07% | EDGE_CRITERIA_SWARM |
| momentum_breakout × ETF edge | n=46, WR 58.7%, +0.17% | EDGE_CRITERIA_SWARM |
| FOREX loss-to-win ratio | 3.2:1 | EDGE_CRITERIA_SWARM |
| FOREX Sharpe | -0.22 | EDGE_CRITERIA_SWARM |
| regime_adaptive WR | 84.6% (n=13, CI [54.6%, 98.1%]) | EDGE_CRITERIA_SWARM |
| CRYPTO confidence dead band PF | 0.69 (n=882) | hedge_fund_quality_gate.py |
| EQUITY confidence reject band PF | cum -28.1% (n=52, [0.60,0.65)) | hedge_fund_quality_gate.py |
| CRYPTO C-TIER PF | 0.36, -46.59% PnL | hf_quality_gates.json |
| EQUITY SHORT edge | n=4, 0/3 went 0% WR | hedge_fund_quality_gate.py |
