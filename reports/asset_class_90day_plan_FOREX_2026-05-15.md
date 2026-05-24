# Asset Class 90-Day Plan: FOREX (Majors + Crosses with Carry/Momentum/COT Proxies) — 2026-05-15

**Author:** Senior Quant (Grok "money-maker-continual-improve" skill)  
**Date:** 2026-05-15  
**Scope:** Full skeptical audit of FOREX asset class (spot pairs via yfinance =X tickers + alpha_engine/forex_strategies.py + multi-source scanners). Covers 20-symbol universe (majors + JPY/minor crosses + exotics), carry/momentum/tsmom/cot proxies, direction bias, source drags, and outcome tracking post-resolver-v2. Explicit focus on why PF remains <1 despite 52%+ WR in latest snapshot, liquidity realities, and whether this class merits continued capital allocation vs EQUITY T2-candidate or cleaned COMMODITY.  
**References (concrete citations only):** `audit_dashboard/data/dashboard_data.json` (2026-05-15T02:28Z generation, 18MB, performance.asset_class_health.FOREX + concentration + by_asset_class + smart_picks_by_asset), `audit_dashboard/data/edge_stability/edge_stability_FOREX.json` (as_of 2026-05-12T21:53, n_total=1033), `reports/forex_mutation_autopsy_20260515.md` (picks n=148, three-axis: symbol/direction/source), `reports/asset_class_deep_dive_FOREX_2026-05-12.md`, `reports/deep_dive_forex_2026-05-12.md`, `reports/forex_salvage_2026-05-13.md`, `reports/aa7_forex_per_symbol_mutation_20260513.md`, `reports/audit_asset_feedback_2026-05-05T0121Z_FOREX.md`, `CLAUDE_FOREX.md` (Mar 2026, 16 strategies), `alpha_engine/config.py:536-581` (FOREX_SYMBOLS + carry_yield_diff), `alpha_engine/forex_strategies.py:124` (carry_trade), `536` (cot_positioning_forex placeholder), `228` (asian_range), `352` (connors_rsi2), `463` (cross_sectional_momentum), `622` (london), `741` (mean_reversion_200d), `863` (inverse_carry), `985` (ig_contrarian), `audit_trail/quality_gates.py:4408-4412` (source penalties: multi_asset_scanner -25, kimi_riseoftheclaw -12, alpha_engine -8), `4400+` (BLOCKED), `audit_dashboard/data/data_quality_gates.yaml:39-47` (forex: symbols_min:7, session_aware, central_bank_window), `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, `reports/MASTER_ACTION_PLAN_2026-05-15.md` (M-007 FOREX_HARD_DISABLE PENDING, old snapshot PF 0.27/46.4%/n=1169), `alpha_engine/scanner.py` (STRATEGY_REGIME_MAP), `copy_trader_intel/` (MQL5 forex signals per MEMORY.md), `reports/asset_class_90day_plan_COMMODITY_2026-05-15.md` (style/template).

**Core Verdict (lead with the answer):**  
**FOREX is NOT production-grade and is the weakest of the tracked asset classes; it is barely worth the continued investment of engineering time beyond a tightly-scoped 90-day mutate-and-prune paper exercise.** Latest dashboard_data.json (2026-05-15) shows stressed status, sizing_allowed=false, n=342 resolved (win_rate=52.3%, profit_factor=0.81, total_pnl_pct=-24.37, expectancy=-0.07), closed=1089 with mixed wins/losses, smart_picks_by_asset.FOREX=[], top concentration USDJPY=X (36% share) via cta_fx_multifactor (21% strategy share). PF<1 means losses are larger than wins on average despite "above 50% WR" — classic sign that the edge is illusory or heavily regime-dependent. Edge stability (May 12) 90d: WR 43.9% PF 1.17 sharpe 0.027 (wilson 41-47%); 7d/30d windows far worse (WR 29-42%, PF<1, negative sharpe). Mutation autopsy (today) on recent picks confirms primary drag is LONG direction (80% of volume, 29.4% WR, PF 0.80) vs SHORT (PF 8.11 on small n=29). Bad symbols (NZDUSD=X PF0.32, EURJPY=X 0.20, USDCHF=X 0.00) + legacy drags (dxy-reversal-scout PF0.44, fx_smart_carry_trade_momentum 0.63, kimi_riseoftheclaw 37.5% n=56, alpha_engine 29% n=24, multi_asset_scanner 0% n=11) persist despite source penalties now wired in quality_gates.py. Existing "carry" (static yield_diff + trend/vol gate in forex_strategies.py:134-172), "COT" (price zscore proxy, not real CFTC futures positioning), tsmom/cta are academic on paper (Lustig/Verdelhan 2007, Moskowitz 2012) but fail live because of un-gated DXY regime, session noise, spread costs on narrow targets (pre-May ATR widen fixes), and no independent outcome tracking for non-crypto. Universe is mostly liquid majors (good) but includes exotics (USDMXN etc) that amplify drag at current PF. Charter floor (n>=100) met on paper, but real statistical power low (edge_stability n=1033 includes dirty history; post-resolver-v2 still negative PnL). **Compared to EQUITY (T2-candidate PF~1.4+), cleaned COMMODITY potential, BOND/ETF thin but higher WR — FOREX is the one to de-risk first.** Per Claude.md Goal #1 and MUTATION_THREE_AXIS_PROTOCOL.md: do NOT silently kill; execute focused mutate (direction/SHORT bias + symbol allowlist + source de-weight) + 30d paper on 4 majors before any decision. If no PF>1.3 / real WR>50% / positive expectancy on n>50 clean independent by day 60, recommend M-007 HARD_DISABLE or pivot to external low-cost replication (MQL5/MyFXBook verified forex copy traders per MEMORY.md long-term note). This class has genuine liquidity edge and proven academic factors but current implementation + data hygiene has produced a value-destroying book. Prioritize only if the 90d prune beats opportunity cost of scaling stronger classes.

---

## 1. Latest Performance from dashboard_data.json + Recent Reports (2026-05-15 snapshot)

**From `audit_dashboard/data/dashboard_data.json` (generated ~2026-05-15T02:28Z, repo context post recent penalties):**
- **FOREX asset_class_health:**
  - status: "stressed", sample_tier: "stable", sizing_allowed: false
  - n=342 (resolved_n=342), win_rate=52.3%, total_pnl_pct=-24.37, profit_factor=0.81
  - min_display_n=10, min_candidate_n=50, min_stable_n=100 (charter floor met on n but fails PF/ PnL gates)
  - circuit_breaker: {breached: false, reason: "no_backtest", realized_wr_30d: null, realized_n_30d: 0}
  - by_asset_class (performance): active=17, closed=1089, wins=179, losses=163, pnl=-24.37, win_rate=52.3, avg_win=0.58, avg_loss=0.79, profit_factor=0.81, expectancy=-0.07

- **asset_class_concentration.FOREX:**
  - top_symbol: "USDJPY=X", top_share_pct: 36.07, top_symbol_pnl_mass_pct: 83.99 (of total 232.86)
  - top_strategy: "cta_fx_multifactor", top_strategy_share_pct: 20.94, top_strategy_pnl_mass_pct: 48.76
  - is_concentrated_warn: false, is_concentrated_block: false, tier: "OK"
  - honest_label: "FOREX edge = cta_fx_multifactor on USDJPY=X (36% of class PnL)"
  - smart_picks_by_asset.FOREX: [] (empty; mirrors COMMODITY pre-clean state)

**Historical snapshots for context (showing volatility in reported numbers = data quality flag):**
- 2026-05-03 (Claude.md/MASTER_ACTION_PLAN): PF 0.27 / WR 46.4% / n=1169 (pre some noise filter, -1029% cum in deep_dive)
- 2026-05-05/12 deep_dive_FOREX + asset_class_deep_dive_FOREX: PF 0.28-0.29, WR~45.6%, n~1169-1343 resolved, BLOCKED strategies list (signal_validation, MomentumEMA, myfxbook_retail_contrarian, forex_carry_momentum, quan_engine_swing LONG-only); ig_contrarian unblocked temp (SHORT 57.1% vs LONG 20.9%)
- 2026-05-12 edge_stability_FOREX.json (n_total=1033): 90d WR 43.9% PF 1.17 sharpe +0.027 (wilson_ci 41.0-47.0), 30d WR42.3% PF0.64 negative, 7d WR28.9% PF0.96 negative sharpe. All-window identical to 90d.
- 2026-05-13 forex_salvage: PF 0.63 WR41.4% n=432 (by_asset), top drags multi_asset (PF0.32 n=225), alpha_engine_fast (0.62), multi_asset_scanner (0.71 WR13% n=111)
- 2026-05-15 forex_mutation_autopsy (picks slice n=148 closed+resolved): PF=0.81 WR=52.3% (matches today's health), LONG 119 trades 29.4% WR PF0.80 (primary drag), SHORT 29 trades PF8.11; symbol kills NZDUSD/EURJPY/USDCHF; source penalties applied for multi_asset_scanner/kimi/alpha_engine; survivors AUDUSD (PF3.55 n=11), AUDJPY (2.45), alpha_engine_fast (53.8% WR), signal_validation/MeanReversionBB (PF2.09 n=44)

**By-strategy/system note:** cta_fx_multifactor (new top, momentum family) and MeanReversionBB now carrying class; legacy carry/tsmom/cot under-emitting or dragging. 17 active but no smart_picks. Negative expectancy confirms "52.3% WR" is misleading — avg loss > avg win.

**Comparison to T2 floor (hedge_fund_performance_review_* + Goal #1):** Requires PF>1.5 / WR>50 / MDD<20 / n>100. FOREX fails PF and PnL hard; only WR marginally passes on latest slice. EQUITY T2-candidate (PF1.41+), COMMODITY post-clean potential (2.49 headline but falsified per cot forensic).

---

## 2. Symbol Universe Coverage and Liquidity (Major vs Exotic Pairs)

**Defined universe (`alpha_engine/config.py:536-581` FOREX_SYMBOLS, 20 entries + carry_yield_diff static field):**
- **Majors (7, deepest liquidity, tightest spreads ~0.5-1.5 pips retail):** EURUSD=X (carry -1.75), GBPUSD=X (+0.25), USDJPY=X (+4.5), AUDUSD=X (+1.2), USDCAD=X (-0.3), NZDUSD=X (+1.5), USDCHF=X (+4.0)
- **JPY crosses (5+):** EURJPY=X (+2.0), GBPJPY=X (+4.0), AUDJPY=X (+3.6), NZDJPY=X (+3.8), CADJPY=X (+3.5)
- **Minor crosses:** EURGBP=X (-2.0), EURAUD=X (-2.5), GBPAUD=X (-1.0), AUDNZD=X (-0.3), EURCHF=X (+2.0), GBPCHF=X (+3.5)
- **Exotics/minors with wider spreads:** USDSGD=X (+0.8), USDMXN=X (-6.0), USDNOK=X (-0.5)

**Liquidity & practical reality:**
- Majors: Excellent (OANDA/IB/prime brokers, 24/5 deep books, options for defined risk). Daily ATR 0.3-0.8% as noted in forex_strategies.py:16. Round-trip costs (spread + commission) 3-6 pips typical retail; must outrun with 1.5%+ TP targets (post May-08 widen in _forex_tp_sl:74 and config.py).
- JPY crosses: Good liquidity but wider than majors (1-3 pips+), higher vol, JPY-specific carry unwind risk (BoJ policy).
- Exotics (USDMXN, USDNOK, USDSGD): Spreads 5-20+ pips, lower volume, higher slippage on news. At current class PF 0.81, these are guaranteed EV destroyers — mutation autopsy already flags NZDUSD/EURJPY/USDCHF (PF 0.00-0.32) for block.
- **No true emerging (e.g. USDTRY, USDZAR, USDCNH) — correct decision** given stressed state (deep_dive_2026-05-12 explicitly: "No emerging-market exotics — correct call").

**Concentration risk:** 36% PnL mass on USDJPY=X alone (via cta_fx_multifactor). Top symbol + top strategy = ~57% combined. Violates diversification north-star even if "OK" tier today (dashboard). Single BoJ surprise or DXY regime shift wipes class. Compare COMMODITY 73% CT=F warning.

**Gap:** No live per-symbol liquidity/avg_spread/pip_cost matrix in quality_gates.py or data_quality_gates.yaml (only static symbols_min:7 + cross_provider_spread_pips_max:2.0). carry_yield_diff is hardcoded snapshot (not live FRED/central bank rates). Session_aware + central_bank_window exist in gates but enforcement spotty across scanners (alpha_engine vs kimi vs multi_asset).

**Verdict on universe:** Mostly sensible liquid core (majors + key crosses), but polluted by low-edge exotics/crosses that should have been pruned earlier. 20 symbols > charter min but effective tradable after gates ~4-6 (EURUSD/GBPUSD/AUDUSD/USDJPY + 1-2 JPY with SHORT bias).

---

## 3. Data Quality and Outcome Tracking Issues

**Strengths:**
- yfinance =X provides consistent daily/ intraday for all 20 (continuous adjusted). data_quality_gates.yaml forex feed_age 15s strict + price_outlier 4σ + session_aware.
- resolver-v2 (post Apr 2026) fixed live-close labeling bug that mislabeled ~1700 non-crypto (deep_dive_2026-05-12 root cause #1).
- ATR-based TP/SL in forex_strategies.py (_forex_tp_sl + widened 2026-05-08 to 1.5%/0.8% caps) + regime gates (_fx_regime_ok vol check).
- Source penalties now live in quality_gates.py:4408 (post-autopsy) de-weight drags without full block.
- Some external replication candidates in deep_dive (stefan-jansen ML-for-trading Ch12-18, FinRL DRL FX env, hudson-and-thames/mlfinlab CPCV).

**Major Weaknesses (brutally documented across reports):**
- **Varying n/PF across snapshots and tools (core data integrity red flag):** dashboard health n=342 PF0.81 WR52.3 (2026-05-15); autopsy picks slice n=148 same metrics; edge_stability n=1033 PF1.17 WR43.9 (May12); older deep_dive n=1169-1343 PF0.27-0.29 WR45.6. Indicates inconsistent "resolved/closed" definitions, pre/post noise-filter, and possible lingering resolver artifacts for non-crypto (similar to COMMODITY COT over-emission). dashboard_generator.py + MySQL trading_picks still pollute aggregates (cf. cot forensic).
- **Outcome tracking for FOREX specifically weak:** Non-crypto resolver issues flagged in feedback_noncrypto_resolver_live_close_bug history. 3 corrupted +40-95% rows noted in deep_dive (USDCAD/EURUSD/AUDUSD with confidence=9.9999, id=MISSING). No robust independent-cycle counting (unlike weekly COT for commodity). 7d window in edge_stability shows 29% WR — recent production still broken.
- **COT for FOREX is a weak proxy, not real data:** cot_positioning_forex (forex_strategies.py:536) uses price zscore(-50) + RSI filter as "extreme positioning proxy". Real CFTC COT covers CME/ICE FX futures (6E, 6B, 6J etc.) not spot pairs; commercial hedger net positioning for USDJPY futures is high-quality but never wired here (contrast real COT module for CT=F). Placeholder produces mean-reversion signals but no edge in autopsy.
- **Carry implementation limited:** carry_trade (124) uses static carry_yield_diff from config (snapshot, no live rate diff from FRED/BoE etc.) + SMA200 + vol timing + RSI<70 + mom acceleration. Only positive carry symbols. But autopsy shows fx_smart_carry_trade_momentum (related/legacy) PF0.63 n=20 — underperforms because carry crashes (JPY unwind, AUD funding) not fully gated, and momentum overlay conflicts in ranging DXY regimes. Lustig & Verdelhan 2007 edge exists in academic but requires dynamic rates + crash-risk vol filter (partially present but insufficient).
- **Momentum/TSMOM/CTA:** forex_tsmom_12m (config 1696, Moskowitz 2012), cta_fx_multifactor (top now), cross_sectional_momentum_forex (463). These should thrive in trending (DXY strong/weak regimes) but fail when un-gated for London/NY open spikes or economic calendar (NFP/CPI/FOMC within 90min). Session vol expansion / sunday gap in CLAUDE_FOREX (Mar) waiting for conditions. london_session_breakout (622) and asian_range (228) have practitioner backing but narrow targets pre-fix ate spreads.
- **No full CPCV/DSR/PSR on FOREX history** (hudson-and-thames/mlfinlab integrated but not leveraged for this class per deep_dive). Wilson CI barely positive (41% lower) on 90d. Small true independent n vs CRYPTO 8k+.
- **Other gaps:** quality_gates.py has JPY_CROSS_BUY_KILL hardcoded (some blocks), BLOCKED strategies list from May12 (some unblocked temp), but no unified per-class DXY/ yield-curve / VIX confluence matrix live for all scanners (kimi, alpha_engine, multi_asset_scanner still leak LONG bias). spread_pips_max=2.0 in yaml but no enforcement in _forex_tp_sl for exotics.

**Verdict on data quality:** Substandard for "phenomenal" production. Resolver fixes helped system-wide but FOREX-specific outcome hygiene + proxy data (COT/zscore, static carry) + inconsistent reporting = inflated or misleading metrics. Exactly the trap caught in COMMODITY COT forensic (over-emission, dirty historicals).

---

## 4. Hidden Insights & Gaps Others Missed (Carry, Momentum, COT Underperformance)

1. **Direction axis is the smoking gun (autopsy 20260515 + deep_dive_05-12):** 80%+ of FOREX volume is LONG with 29.4% WR / PF 0.80 (anti-edge). SHORT side has real edge (PF 8.11 on n=29 in slice; ig_contrarian SHORT 57% vs LONG 16-21%; myfxbook 46% vs 11%; quan_engine_swing 60% vs 26%). Root: many sources (kimi_riseoftheclaw, alpha_engine, multi_asset_scanner) are LONG-biased during the sample's DXY regime or retail contrarian logic misfired on trending USD. Mutation protocol applied (penalties + proposed blocks) but not yet full direction gate in all paths. This is why "52% WR" coexists with negative expectancy — the wins are small, losses large on wrong-direction bets.

2. **Carry + momentum academic but implementation incomplete:** Static carry_yield_diff + trend filter in carry_trade skips negative-carry (correct) but misses live rate changes (e.g. recent BoJ hikes vs Fed cuts flip JPY crosses). Vol timing (1.3x 60d) + ADX>18 present but DXY confluence (strong USD = long USDJPY carry better) absent in core path. cta_fx_multifactor now "edge" (36% USDJPY) likely riding one regime; no cross-asset overlay (DXY futures, US10Y, VIX) as in salvage plan. Moskowitz TSMOM works cross-sectional on FX but requires 12m lookback + skip month + vol scaling — partial in cross_sectional_momentum_forex but low volume.

3. **COT proxy is noise, not signal:** zscore on price (not positioning) + RSI is just fancy mean-reversion (similar to connors_rsi2 or mean_reversion_200d). Real FX COT (CFTC legacy/disaggregated on 6J etc.) has commercial net extremes that predict reversals (practitioner literature + MyFXBook retail sentiment complement). Never wired; placeholder emits but doesn't move needle in autopsy.

4. **Source + scanner fragmentation:** alpha_engine (incl fast) + kimi + multi_asset_scanner + cta_ + signal_validation all feed FOREX but with different regime logic. Penalties de-weight but don't fix root (e.g. multi_asset_scanner 0/11 wins = routing bug per salvage). ig_contrarian + myfxbook retail_contrarian have proven SHORT asymmetry (deep_dive) but were partially blocked earlier.

5. **Liquidity/execution gaps missed:** No dynamic spread cost model in sizing (quality_gates or risk). Exotics in universe despite data_quality_gates spread check. Pre-May ATR fixes (CLAUDE_FOREX + strategies.py comments) meant 0.3-0.8% targets eaten by 3-6% costs. 17 active but 0 smart_picks = internal distrust.

6. **External low-cost edge ignored:** MEMORY.md + copy_trader_intel/ + CLAUDE_FOREX note BingX/MQL5 forex signal cards (growth, reliability, copy price). Verified MQL5 forex providers have public verified track records (often PF>1.5 on majors with real broker statements). Cheaper/faster than building in-house vs. current 0.81 PF. Never deeply integrated despite 2026-04 PRs for baby FOREX/PAXG.

7. **Process debt:** M-007 HARD_DISABLE in MASTER_ACTION_PLAN still PENDING despite multiple deep_dives (05-12, salvage 05-13, autopsy 05-15). "DROP-AND-REPLACE" scheduled 2026-06-15. No full 6-stage rehab pipeline applied to class (per MEMORY institutional policy). Overlap with FUTURES bucket for some crosses?

These surfaced by cross-referencing autopsy three-axis + edge_stability windows + strategy source code + yaml gates + old CLAUDE_FOREX vs current dashboard — not visible from single /audit view.

---

## 5. Realistic 90-Day Plan: Prune Ruthlessly, Gate on DXY/Session, Paper-Only, Pivot or Disable

**North Star:** Focused FOREX book on 4 liquid majors (EURUSD, GBPUSD, AUDUSD, USDJPY) + 1-2 JPY crosses, SHORT-bias or DXY-confluence gated on contrarian/mean-rev + survivors (AUDUSD/AUDJPY per autopsy, alpha_engine_fast, signal_validation/MeanReversionBB), real expectancy >0, PF>1.3, WR>50% on n>50 independent clean post all filters, MDD<15% in paper. Enforce mutate-before-kill (no silent kill). If gates not met by day 60, execute M-007 HARD_DISABLE or external MQL5 copy (low cost, verified). All-classes-first per codex; zero real $ until shadow + graduation. Reference COMMODITY plan hygiene first.

**Phase 1: Days 1-14 — Data Integrity, Symbol/Strategy Prune, Direction Gate (P0, immediate)**
- Enforce **directional mutation** in quality_gates.py + all scanners: LONG FOREX picks get -20-30 score penalty (or block except DXY-strong confirmed); prioritize SHORT on ig_contrarian, myfxbook_retail, quan_engine_swing, mean_reversion, cot proxy. Wire BLOCKED_DIRECTION_TRIPLES or equivalent (per deep_dive_05-12 Step A).
- **Symbol allowlist/block (user approval per CLAUDE.md + autopsy):** Add NZDUSD=X, EURJPY=X, USDCHF=X, USDMXN=X, USDNOK=X (and any PF<0.8 n>=5) to FOREX_BLOCKED_SYMBOLS. Restrict emission to EURUSD/GBPUSD/AUDUSD/USDJPY + AUDJPY/GBPJPY only. Update FOREX_SYMBOLS or gate in scanner.py.
- **Strategy blocks (post 30d probation in autopsy):** Add ("FOREX", "dxy-reversal-scout"), ("FOREX", "fx_smart_carry_trade_momentum"), ("FOREX", "multi_asset_scanner" if still 0-win) to BLOCKED_ASSET_STRATEGY_PAIRS (quality_gates.py). Keep/BOOST cta_fx_multifactor only with DXY gate, MeanReversionBB, alpha_engine_fast, AUD survivors.
- Re-aggregate historical FOREX closed_picks in MySQL + dashboard_generator.py for consistent "resolved" definition (fix n/PF drift across tools). Refresh edge_stability_FOREX.json + effective_n_report.
- Audit/enforce data_quality_gates.yaml forex: session_aware + central_bank_window in *all* paths (alpha_engine_fast, kimi, cta, scanners). Add live DXY_4h/1d EMA confluence + ATR% spike filter (salvage plan Axis 2).
- Update carry_trade to use live rates (FRED API or cheap proxy) instead of static carry_yield_diff; add DXY trend confirmation for USD-base pairs.
- Milestone: dashboard FOREX health "WARN" until gates pass; M-007 status updated; no emission from blocked symbols/strategies/directions; 0 smart_picks remains until clean n>=20.

**Phase 2: Days 15-45 — Wire Real Regime Gates + Diversify Low-Cost Edges (DXY + Session + Real COT)**
- **DXY regime gate (core missing edge):** For USD-base pairs (EURUSD etc): LONG only when DXY 4H/1D EMA20 < EMA50 (USD weak); SHORT only when DXY strong. For JPY crosses: BoJ policy proxy (or yield diff live). Wire in _fx_regime_ok + quality_gates + scanner. (Salavage + deep_dive Step C.)
- Expand **real FX COT:** Pull CFTC COT (via quandl or free FRED/cftc.gov legacy reports for 6E/6B/6J/6A etc futures). Map to spot pairs (EURUSD ~6E). Replace zscore proxy in cot_positioning_forex. Target 3-4 currency futures COT extremes (commercial net >2σ). Reference backtest_forex_cot_2026-05-12.
- **Session + calendar:** Enforce London/NY overlap (07:00-17:00 UTC) + skip 22:00-02:00 Asia + 15min post open spikes (salvage). Add economic calendar (NFP/CPI/FOMC/ECB/BoE/BoJ ±90min high-impact skip or invert) — already partially in yaml, make universal.
- Wire survivors + mutated: AUDUSD/AUDJPY momentum/carry (autopsy PF>2), SHORT contrarian on majors, cta_fx_multifactor + DXY. Drop or sandbox tsmom_12m / cross_sectional if volume low post prune.
- Add low-cost external: Integrate MQL5/MyFXBook forex signal cards (copy_trader_intel/ + MEMORY.md) as sidecar source (verified PF often >1.5 on majors, low dev cost). Compare to in-house.
- Backtest full pruned basket (4-6 symbols) with CPCV (mlfinlab), PSR/DSR, regime (DXY states), realistic pip costs/spreads/slippage (use data_quality_gates spread max). Stress vs 2022/2024 vol spikes.
- Update smart_picks_by_asset.FOREX + assetClassSummary (raise minTrades). Enforce single-symbol <=25% class PnL mass.
- Milestone: >=4 symbols with positive cleaned expectancy, total independent n>60, DXY/session gated, PF>1.2 on 30d paper slice, CT/FX concentration <30%.

**Phase 3: Days 46-75 — Rigorous Paper Validation + Risk Engineering (30d live paper pilot)**
- 30-day (or 40+ independent signals) **live paper pilot** on pruned/gated universe only (TradingView paper or broker demo per .claude/skills/tv-paper-trade). Use circuit_breaker_system.py + FOREX-specific (DXY, session, cb windows, spread alerts). Daily reconciliation of fills vs signal (resolver hygiene).
- Realistic sizing: 0.5-1.5% risk per trade, lot calc from pip value + avg ATR, max 2-3 concurrent. Stress margin (none for spot but rollover/swap on carry), weekend gap (sunday_night_gap strategy), news.
- Monte Carlo/bootstrap on cleaned PnL distro + external comp (simple DXY trend-follow or carry ETF like DBV/Carry trade ETN). If basket underperforms passive FX or MQL5 copy, kill.
- Full 6-stage rehab on any remaining underperformer (e.g. old london_breakout).
- Refresh reports + edge_stability + hedge_fund tier table. Update MASTER_ACTION_PLAN M-007 + Section 21.
- Milestone: graduation_gate = PASS (PF>=1.4, real WR>=51%, expectancy>0.1, MDD<12%, DSR>0.85 on paper); n>=80 clean; smart_picks non-empty; sizing_allowed still false until user sign-off.

**Phase 4: Days 76-90 — Gate Decision & Production Path or Pivot**
- If T2 gates met on pruned set (PF>1.5 / WR>50 real post-noise / MDD<15 / n>100 / liquidity verified / positive expectancy): 
  - Shadow mode (micro sizing, all-classes-first per codex).
  - Then LIVE_MICRO (M-050 style).
  - Conservative sizing (e.g. 0.25-0.5 lot on $10k+ account using cleaned expectancy).
  - Document + link to SUPREME_PLAN + updates/ page.
- If gates fail (likely given history): Execute M-007 FOREX_HARD_DISABLE (env switch + active-gate wire in quality_gates.passes_active_gate + config.py). Or pivot to external: allocate small % to top verified MQL5/MyFXBook forex copy traders (low cost, no dev, real broker statements, per MEMORY long-term copy_trading research). Prune to research tier (2-3 majors only, paper monitoring).
- Final deliverable: Updated MASTER_ACTION_PLAN (M-007 resolved), this 90d plan + evidence (pruned matrix, CPCV results, MQL5 comp), edge_stability refresh.
- Ongoing: Weekly mutation re-run (tools/mutation_analysis.py), monthly re-audit of direction split / symbol PF / feed freshness.

**Success Metrics (quantified, measurable, no optimism):**
- Pruned to 4-6 symbols (USDJPY/EURUSD/GBPUSD/AUDUSD + AUDJPY max), bad symbols 0 emission.
- Direction: LONG volume <30% or PF>1.5 on LONG subset; SHORT PF>1.8.
- PF >=1.4, real WR >=51%, expectancy >0, sharpe >0.3, MDD <15% on 30d+ paper (wilson lower >48%).
- smart_picks_by_asset.FOREX non-empty + dashboard sizing_allowed true (post user gate).
- Carry/COT real (live rates + CFTC futures) contributing >=30% of class; cta_fx_multifactor + DXY gated.
- Zero over-reliance on single source/symbol/strategy (>25% cap).
- Decision gate: "Production-grade pruned FOREX" **or** "HARD_DISABLE + external MQL5 pivot" (documented, no silent kill).

---

## 6. Brutally Honest Risks & Why Skepticism Is Warranted

- **Statistical fragility + regime dependence:** FX edges (carry, tsmom, contrarian) are real in academic long samples but crash in specific regimes (2015 CHF, 2022 rate vol, BoJ interventions). Current sample (n~300-1000) has negative expectancy; 7d/30d windows show the edge vanishing. Wilson CI 41% lower bound = coin-flip territory. One DXY super-trend or central bank surprise erases 90d "improvement" to 0.81 PF.
- **Execution reality for retail/prime:** Spreads + slippage on anything but top majors during London open/NFP destroy narrow targets (even post-widen). 0.81 PF means the book loses after costs. No micro-lot issues like CT=F but rollover/swaps on carry positions add drag.
- **Data vendor + proxy risk:** yfinance fine for research, risky for production (stale ticks, adjustment artifacts on crosses). COT/zscore proxy + static carry = look-alike of mean-reversion already in other strats — multiple testing trap. Corrupted historical outcomes still polluting (varying n across tools).
- **Overfitting + process debt:** Multiple mutations (May12 deep_dive, salvage, today's autopsy) + penalties applied yet still stressed/PF<1. M-007 still pending after 2+ weeks of docs. "52% WR" headline lures; expectancy and PF tell truth. Similar to COMMODITY COT falsified 90% WR.
- **Opportunity cost vs charter:** 17 active but 0 smart_picks, negative PnL. Time on FOREX forensics competes with scaling EQUITY (already T2-candidate PF1.41+ n=421) or COMMODITY diversify (real COT + carry_momo). Per Goal #1: "prioritize where the edge is best worth the risk." FOREX is lowest ROI.
- **External superior low-cost option:** MQL5 + MyFXBook verified forex signals (MEMORY.md) offer plug-and-play with real verified broker P&L, often on exact majors, with risk management. Cheaper dev cost than fixing 10+ internal scanners. DBMF/KMLM-style for FX (currency CTA) exists externally.
- **If it fails 90d (high probability):** Accept FOREX as satellite/research only (or disable). Redirect resources. "Phenomenal performance across ALL" does not require forcing every class; some are better bought than built.

**Final Recommendation:** Execute the 90-day prune + gate plan with zero tolerance for direction bias, bad symbols, or proxy data. Force the mutate (SHORT bias + 4 majors + DXY) and paper it rigorously. If it hits gates, cautious shadow. If not (expected), document, invoke M-007 HARD_DISABLE or pivot to MQL5 copy-trading (lowest cost real edge), and treat FOREX as non-core. This class exposes the limits of "build everything in-house" when data proxies + fragmented sources produce anti-edge on the majority side. Brutal honesty now saves capital later — exactly the quant discipline the /audit dashboard and hedge-fund tier table demand.

**Next Immediate Actions (today/this week, no auto scripts per AGENTS.md):**
1. User review/approve symbol/strategy blocks from autopsy (NZDUSD etc + dxy-reversal-scout + fx_smart_carry) + add to quality_gates.py + matrix_symbol_gates.json.
2. Wire explicit DXY EMA confluence + direction penalty in quality_gates + forex_strategies core paths (small PR, Wiring Plan section).
3. Update MASTER_ACTION_PLAN_2026-05-15.md M-007 + Section 21 with this 90d reference + current dashboard numbers (0.81 PF).
4. Force fresh dashboard_data.json + edge_stability_FOREX after any gate changes; produce pruned mutation matrix.
5. Explicit user sign-off before any FOREX real-money (nfa + graduation + all-classes shadow).
6. Consider cheap external eval: pull top MQL5 forex signal providers for 90d comparison backtest vs pruned in-house.

NFA. All numbers, paths, and citations from 2026-05-15 workspace files (dashboard 05-15T02:28, autopsy 05-15, edge 05-12, strategies/config current). This plan advances Goal #1 (phenomenal /audit performance across classes) by forcing ruthless focus or honest deprecation. References COMMODITY 90d plan for consistency in "money-maker-continual-improve" process.

---

*End of report. Brutal honesty, concrete files/lines/metrics, no hedging. Quality over volume. References named explicitly for auditability and reproducibility.*

---

## 2026-05-24 — Institutional-Readiness Refresh

A 4-AI external consult (Mercury 2 + Grok + ChatGPT + Gemini, 2026-05-24) and a 5-engine swarm second-opinion (deepseek + groq + inception + pollinations) produced an honesty/risk/governance overlay captured in [INSTITUTIONAL_READINESS_PLAN_2026-05-24.md](./INSTITUTIONAL_READINESS_PLAN_2026-05-24.md). This appendix records what changes for THIS class specifically.

**Universal additions (apply to every class):**
- Per-pick freshness SLA enforced at the gate level (class threshold listed below); auto-suppress beyond threshold.
- Cross-provider price reconciliation (≥2 providers); `data_quality=degraded` flag on divergence.
- `smart_score` Platt/isotonic calibration runs per asset class; rank-vs-realized-WR must be monotonic on hold-out before any size-up.
- Lookahead-leakage CI guard (`entry_ts < signal_ts` fails the pipeline).
- Stage-1 gate: PF>1.3 / WR>48% / Sharpe>1.0 / MDD<25% / 90 days clean. Stage-2 gate (institutional): PF>1.5 / WR>50% / Sharpe>1.5 / MDD<20% / 6 months clean. **Real money only after Stage-2 holds 6 consecutive months.**
- Workstream G (governance) applies: real-time alerts + circuit-breaker on Stage-1 floor violation + data lineage + golden-set regression in CI.

**FOREX-specific changes:**
- **Freshness threshold:** 10 seconds. FOREX is the tightest SLA across all classes.
- **FOREX is genuinely sub-floor** (PF 0.27 / WR 46.4% / n=1169 post-noise). Per CLAUDE.md, this requires the **mutate-before-kill protocol** (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`) plus a deep-dive doc before any new gates — DO NOT silently kill.
- **Macro-calendar blackout (B2) is non-negotiable** — central-bank meetings + scheduled releases (NFP, CPI, GDP, retail sales, PMI) dominate FX. Hard suppress within ±90 minutes.
- **Rate differential + carry + DXY correlation + COT positioning + central-bank surprise index** become first-class columns (Workstream F3). Without these, FOREX models are running blind per Gemini's review.
- **No real-money path in 90 days.** Plan stays maintenance-mode + research per May-15. The institutional-readiness work here is to make the dashboard *honest* about FX (Stage-1 not achievable in this window) rather than try to force it.
- **Speculative split (D1):** exotic pairs (any non-major) get `speculative_flag=True`. Majors only for institutional consideration once Stage-1 is conceivable.
- **Verdict (refreshed):** FOREX gets the honesty layer (A) + the macro-blackout filter (B2) + the data-feature expansion (F3), but Workstreams C/D/E are out-of-scope for FOREX in this 90-day window. Goal is "stop pretending FOREX is close to ready," not "get FOREX to Stage-1."
