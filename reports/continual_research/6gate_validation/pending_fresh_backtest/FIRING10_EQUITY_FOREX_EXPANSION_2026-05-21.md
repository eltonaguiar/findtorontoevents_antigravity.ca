# Firing 10 EQUITY/FOREX Expansion — Inventory Mining & 6/8-Gate Candidates
**Date:** 2026-05-21 (Firing 10 of the 30m continual 6-gate asset-class research loop; subagent for EQUITY/FOREX + hypothesis_registry focus)  
**Task:** Expand inventory beyond Firing 9 (CRYPTO/H-037/COMMODITY). Mine alpha_engine/equity_strategies.py, forex_strategies.py, baby_strategies/ (*.py + *.meta.json), cross-reference hypothesis_registry.json for H-/E-/F- entries in EQUITY/FOREX not yet fully 6/8-gated. Identify 2-3 promising (high-PF or liquidation-related) that benefit from upcoming tagging hygiene fix. For strongest, outline backtest plan using harnesses. Output structured report + A/B placement recs. Citations exhaustive. Continues per-class expansion.

**Citations (exhaustive, key files/lines):** 
- alpha_engine/equity_strategies.py:73-1292 (momentum_factor_12m, penny_volume_breakout, meme_social_velocity, quality_value_composite, intermarket_risk_on, support_resistance_bounce, connors_rsi2_scanner/short, equity_two_bar_rsi_reversal, triple_rsi_scanner, vix_spike_reversal_scanner, turn_of_month_scanner, earnings_gap_reversal_scanner, gap_reversal_tech_stocks, optimized_stock_momentum + _wrap_with_factor_model, _apply_factor_model via equity_factor_model)
- alpha_engine/forex_strategies.py:124-1077+ (carry_trade, asian_range_breakout, orb_breakout, connors_rsi2_forex, cross_sectional_momentum_forex, cot_positioning_forex, london_session_breakout, mean_reversion_200d, inverse_carry_contrarian, ig_contrarian_sentiment_forex + _session_guard)
- alpha_engine/equity_strategy_harness.py:149+ (StrategyCategory, SignalGenerator impls for EarningsSurprise/PEAD/PostEarningsDrift, Value/Growth/Quality/LowVol/Momentum/SmallCap/Profitability factors, ResistanceBreakout, SupportBounce etc.; full harness/BacktestResult/EnsembleAllocation)
- alpha_engine/forex_strategy_harness.py (parallel design, 1,094-cand refs in prereqs)
- alpha_engine/equity_vix_regime_momentum.py + baby_strategies/equity_vix_regime_momentum.py (VIX term structure contango/backwardation regime filter for SPY/QQQ/IWM)
- baby_strategies/ (equity_earnings_drift_pead.py:1-140+ (PEAD 60d drift, expected 60-68% WR / 1.8-2.5 PF), equity_sector_rotation_momentum.py:1- (dual momo + defensive, expected 60-65% WR / 1.3-1.6 PF), equity_two_day_rsi_reversal.py, equity_vix_regime_momentum.py; forex_bb_mr_rehab_v1.py, forex_carry_momentum_harvest.py:1- (carry+momo+VIX<25 filter), forex_ensemble_4h_rehab.py, forex_inside_day_breakout.py, forex_weekly_open_gap_fill.py:1- (80%+ gap fill MR, RSI2+BB confirm))
- baby_strategies/*.meta.json (inverse_earnings_drift.meta.json + inverse_goldmine_stocks etc. for EQUITY-related; no direct equity/forex .meta but families align)
- reports/hypothesis_registry.json:33- (H-002 EQUITY PEAD SHADOW_IMPLEMENTATION, pooled_wr=0.532 n=1964), 173- (H-009 options_iv_skew KILL), 194- (H-011 options_dealer_gamma KILL), 348- (H-016 EQUITY pead_intraday_anchored UNTESTED_DATA_GAP Polygon), 464- (H-028v2 EQUITY insider_open_market_cluster_buy_diverse UNTESTED_DATA_GAP, n=11 real clusters negative), 495-560 (E-ANON-001 EQUITY short_term_price_momentum TESTED_PASS PF=1.2307 WR=0.5379 n=48616 5-fold OOS 4/5 folds >1.2 PF; VIX gate tested), 583- (F-ANON-001 FOREX carry_trade TESTED_WEAK PF=1.0332 WR=0.5116 n=1933; JPY slice PF=1.257 WR=57.8%), 707- (F-ANON-001-JPY PRE_REGISTERED), 723- (H-028v3 EQUITY insider_cluster_buy PRE_REGISTERED), 850- (H-010 EQUITY PEAD_post_earnings_drift), 1151- (H-020 EQUITY insider), 1265- (H-024 FOREX g10_carry_differential), 1289- (H-024b FOREX carry_block IMPLEMENTED), 1458- (H-028 EQUITY insider small-cap), 1556- (H-028v3), 1611- (H-030 EQUITY smallcap_liquidity_shock_reversion TESTED_KILL negative EV), 1721- (H-033 EQUITY residualized_overnight_return_xs_reversal TESTED_KILL), 1758- (H-034 EQUITY anti_pead_oneday_postearnings_reversal UNTESTED_DATA_GAP), 1868- (H-OPT-001 EQUITY momentum_options_overlay PRE), ~1929- (H-040? equity_sector_cross_sectional_momentum PRE)
- reports/continual_research/6gate_validation/B_failed/forex_strategies_stressed_no_6gate_pass_2026-05-21.md:1-39 (class WR43.9% PF1.17 stressed; 0/5+ named pass SPA; direction bias LONG anti-edge; cites alpha_engine/forex_*.py, whites_reality_check..., hypothesis F-ANON/H-024)
- reports/continual_research/6gate_validation/pending_fresh_backtest/FOREX_harness_rerun_prereqs_2026-05-21.md:1-24 (10 prereqs: direction blocks, symbol quarantine NZDUSD/EURJPY, 1h data, real FRED/COT, DXY regime, post-resolver hygiene, daily PnL, M-107 pre-reg, harness run via statistical_validation_framework + edge_stability_harness + forex_strategy_harness, whites RC)
- reports/continual_research/6gate_validation/B_failed/equity_vix_regime_momentum_and_carry_momo_no_6gate_pass_firing3_2026-05-20.md + EQUITY_TAGGING_BUG_P0_FIX_PROPOSAL_2026-05-21.md
- reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING8_H037_POSTFIX_6GATE_SIM_2026-05-21.md + FIRING9_H037_POSTFIX_REVALIDATION_SIM_2026-05-21.md (H-037 ETF vix_term_structure_carry proxy: n=1185 WR58.9% PF1.295 eff=0.75 3/4 admissible; strong G4/G7/G8; hygiene unblocks)
- reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py + FIRING10_HYGIENE_MINIMAL_MERGE_DIFF_2026-05-21.md + FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py (tagging hygiene: _infer_asset_class replaces hardcoded "EQUITY"/"FOREX" defaults in dashboard_generator.py:8254/8282; cleans 198 crypto-in-EQUITY; ETF XL* -> ETF)
- 6GATES_2026-05-21_V1_FREEBUFF.MD:100-138 (real EQUITY only ~20 picks post-reclass; FOREX 68 sparse; G1-8 defs + per-class tuning notes: EQUITY insufficient power, FOREX relax G1>=0.5/G8>=0.8)
- updates/2026-05-21-continual-6gate-asset-class-research/index.html:41-94 (Firing 9 context: CRYPTO funding/ H-017, H-037 post-fix proxy, COMMODITY COT; hygiene as P0 blocker; living log)
- CONTINUAL_STRATEGY_RESEARCH_BASELINE.md + CYCLE_2026-05-21_FIRING9_SUMMARY.md
- tools/validate_resolved_picks.py, alpha_engine/statistical_validation_framework.py, tools/edge_stability_harness.py:41-43 (EFF_MIN=0.30, MIN_STABLE_WINDOWS=3, admissible), alpha_engine/backtest/ + baby_strategies_backtest.py, equity_strategy_harness.py

---

## Mined Families & Under-Tested Status (EQUITY + FOREX)

**EQUITY families mined (alpha_engine/equity_strategies.py + baby + harness + registry H-/E-):**
- Short-term momentum / 5d-vs-30d / cross-sectional (E-ANON-001 TESTED_PASS PF1.2307 n=48k; distinct from 12m momentum_factor_12m in equity_strategies.py:73+ and H-003)
- PEAD / post-earnings drift / earnings_gap_reversal / anti-PEAD (H-002 SHADOW, H-010/016/034 UNTESTED/KILL/gap, baby equity_earnings_drift_pead.py claimed 1.8-2.5 PF, equity_strategy_harness PostEarningsDriftSignal, earnings_gap_reversal_scanner)
- VIX regime / term-structure carry / momentum (equity_vix_regime_momentum.py + H-037 ETF adjacent; baby claims 1.5-2.0 PF; B_failed pre-fix due to tagging/power)
- Insider cluster-buy / open-market Form-4 (H-028/H-028v2/v3 PRE/UNTESTED_DATA_GAP/TESTED_KILL on meme vs diverse small-cap; free EDGAR; equity_factor_model integration)
- Sector rotation / cross-sectional momentum / dual-momo (baby equity_sector_rotation_momentum.py claimed 1.3-1.6 PF; H-040? equity_sector_cross_sectional_momentum PRE; intermarket_risk_on / quality_value_composite in alpha)
- Factor composites (value/growth/quality/lowvol/momentum/smallcap/profitability via equity_factor_model + harness signals)
- Liquidity shock reversion / overnight residual reversal (H-030/H-033 TESTED_KILL negative EV)
- Connors RSI2 / two-bar / triple RSI / support-resistance / vix_spike / turn-of-month / gap tech (multiple scanners in equity_strategies.py; under-tested in resolved pipeline)
- Penny/meme velocity / breakout (wider stops; equity_strategies.py:160+)

**FOREX families mined (alpha_engine/forex_strategies.py + baby + registry F-/H-):**
- Carry / inverse-carry / G10 differential + momentum harvest (F-ANON-001 TESTED_WEAK PF1.033 overall / 1.257 JPY slice; F-ANON-001-JPY PRE; H-024/H-024b; baby forex_carry_momentum_harvest.py + VIX filter; carry_trade in forex_strategies.py:124+)
- Mean-reversion / BB / RSI2 / weekly gap-fill (forex_bb_mr_rehab_v1, forex_weekly_open_gap_fill.py:1- (80%+ fill MR, RSI2+BB, claimed high efficacy); connors_rsi2_forex)
- Session / range / ORB / London/Asian breakout (asian_range_breakout, orb_breakout, london_session_breakout; needs 1h granularity per prereqs)
- COT positioning proxy / cross-sectional momentum (cot_positioning_forex, cross_sectional_momentum_forex; H-024 related)
- IG contrarian sentiment (ig_contrarian_sentiment_forex:985+; stressed in B_failed)
- Mean reversion 200d / CTA multifactor (under-perf in reality checks)

**Hypothesis registry cross-ref (EQUITY/FOREX not fully 6/8-gated):**
- EQUITY: E-ANON-001 (TESTED_PASS on anon 5-fold but NOT full pipeline statistical_validation_framework + edge_stability_harness + 8-gate on resolved picks; sidecar only); H-002/H-016/H-034 (PEAD variants: SHADOW/UNTESTED/gap, insufficient windows for harness); H-028v*/H-020 (insider: data-gap/negative/kill on wrong universe); H-030/H-033 (kills negative); H-009/H-011 (options KILL pre-merge); H-OPT-001/H-040 sector (PRE, untested); most lack resolved n/power for G1-8 (per 6GATES: real EQUITY ~20 picks pre-hygiene).
- FOREX: F-ANON-001/F-ANON-001-JPY (TESTED_WEAK/PRE on yf; PF thin overall, slices >1.25 but no full harness post-direction fixes); H-024/H-024b (carry, IMPLEMENTED block but no clean 6/8); no A_passed; all B_failed/stressed per dedicated marker (SPA p=1.0, direction bias, insufficient for WF/MC).
- None have complete post-M-107 + hygiene + full 8-gate (G1 Sharpe, G2 bootstrap p, G3 CI, G4 WF consistency via harness, G5 MC, G6 crash/FDR, G7 WR>40, G8 PF>1) on clean resolved pipeline data. Tagging pollution (90.8% "EQUITY" actually crypto) invalidates prior EQUITY conclusions; hygiene + backfill unblocks.

**Liquidation-related:** None native in EQUITY/FOREX (cascades are CRYPTO H-017 family; FOREX has COT/IG but no liq). High-PF focus used instead.

**Prior evidence/gaps:**
- EQUITY real power tiny pre-hygiene (6GATES:20 picks); VIX/PEAD/insider/momentum families have academic + baby/anon backtests but no production resolved 6/8.
- FOREX: stressed (dashboard PF0.81, whites SPA fail all named); direction LONG drag primary; prereqs block reliable gates.
- Hygiene fix (FIRING10 minimal diff + backfill) directly benefits EQUITY (clean XL* ETF + no crypto pollution) and improves FOREX inference consistency.

---

## Prioritized Promising Candidates (2-3) Benefiting from Tagging Hygiene Fix

1. **E-ANON-001 (EQUITY short_term_price_momentum family)** — Highest immediate: TESTED_PASS (PF=1.2307 WR=53.79% n=48,616 2020-2026 S&P mid/large 59 symbols, 5-fold OOS, 4/5 folds PF>=1.2; VIX>=28 gate tested but weakens bear fold). Distinct 5d>30d rolling avg return (vs long-term 12m in equity_strategies). Sidecar pre-reg M-107. **Benefits enormously from hygiene**: clean EQUITY attribution in resolved_picks/universal/dashboard post-backfill enables full pipeline G1-8 + harness (currently anon yf only; post-fix integrates to audit flow without crypto noise pollution). High power for WF/MC.

2. **VIX term-structure / equity_vix_regime_momentum + H-037 adjacent (EQUITY/ETF vix_term_structure_carry)** — Proxy strong (FIRING8/9: n=1185 WR58.9% PF1.295 eff=0.75 3/4 admissible same-sign; G4/G7/G8 clear pass). Baby/alpha impls + harness factor signals. equity_vix B_failed pre-fix (power/tagging). **Direct hygiene beneficiary**: _infer_asset_class fixes ETF XL* tagging + EQUITY cleanup (FIRING10 diff, H-037 sims); unblocks clean VIX contango/backwardation for sector rotation/momentum validation. Ties to ongoing Firing 8/9 work.

3. **FOREX carry slices (F-ANON-001-JPY / AUD-boosted) + weekly gap-fill MR family (F-ANON-001, H-024, baby forex_weekly_open_gap_fill.py + forex_carry_momentum_harvest.py)** — JPY slice PF=1.257 WR57.8% n=322; gap-fill claims 80%+ fill rate (French/Cao lit); carry+momo hybrid. Under-tested post-direction blocks (H-024b). **Benefits from hygiene + prereqs**: improved FOREX tag inference + clean n for harness rerun; pairs with 1h data / real rates / DXY gates for reliable 6/8 (tuned G1>=0.5 / G8>=0.8 per 6GATES).

All 3 leverage post-hygiene clean slices for accurate per-asset-class 6/8 (no more "EQUITY"=crypto misclass). No liquidation-native but high-PF / regime / MR families prioritized.

---

## Strongest #1: E-ANON-001 EQUITY short_term_price_momentum — Backtest Plan (Harnesses + Post-Hygiene)

**Rationale for strongest:** Largest n + positive TESTED_PASS metrics among EQUITY/FOREX registry entries; concrete 5-fold evidence (Jegadeesh & Titman underreaction); sidecar wiring ready (OPT-IN RESEARCH); directly unblocked by Firing10 hygiene (clean EQUITY bucket for resolved validation, vs prior sparse 20 real picks). High leverage for A_passed promotion vs. kills/gaps in PEAD/insider/anti-pead.

**Prerequisites (execute first):**
- Merge/apply Firing10 hygiene (FIRING10_HYGIENE_MINIMAL_MERGE_DIFF_2026-05-21.md diff to dashboard_generator.py:8254/8282 + _infer_asset_class) + run FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py --apply (or equiv) on dashboard_data.json / universal_resolved_picks.json / closed_picks / SQL ejaguiar1_* tables.
- Verify: python tools/validate_resolved_picks.py --by-asset-class EQUITY --min-trades 5 (confirm crypto pairs like BTC-USD/ETH-USD gone from EQUITY; ETF XL* -> "ETF"; real stocks rise; n sufficient).
- Confirm no overlap: E-ANON 5d/30d variant != momentum_factor_12m (12m skip-1m) or H-003; distinct family per registry note.
- Wire as opt-in sidecar (if not present): add to equity_strategies.py or equity_smart_picks equivalent, emit with strategy_name="e_anon_001_short_term_momentum" or "short_term_price_momentum_equity", asset_class inferred cleanly. Use equity_strategy_harness.MomentumFactorSignal as base. Pre-reg already done.

**Validation Run Outline (post-clean data):**
```bash
# 1. Extract clean EQUITY slice for family (post-hygiene)
python tools/validate_resolved_picks.py \
  --by-asset-class EQUITY \
  --min-trades 20 \
  --strategy-filter "short_term|momentum| E-ANON|price_momentum|5d.*30d" \
  --save-json reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING10_EQUITY_EANON001_SLICE_2026-05-21.json \
  --output-dir reports/continual_research/6gate_validation/

# 2. Full 6/8-gate framework (G1-6 statistical + G7/8 WR/PF) + daily PnL for realistic Sharpe
python alpha_engine/statistical_validation_framework.py \
  --input reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING10_EQUITY_EANON001_SLICE_2026-05-21.json \
  --asset-class EQUITY \
  --framework full --daily-pnl --slippage-bps 15 \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING10_EQUITY_EANON001_6GATE_2026-05-21.json

# 3. Edge stability / harness admissible (eff>=0.30, >=3 same-sign windows, 14d)
python -c "
from tools.edge_stability_harness import EdgeStabilityHarness
h = EdgeStabilityHarness()
admissible = h.is_admissible('E-ANON-001', slice_json='...FIRING10...json', windows=14)
print(admissible)  # expect True for promotion
"

# 4. Equity-specific harness (factors + momentum signals + WF)
python alpha_engine/equity_strategy_harness.py \
  --strategy momentum --universe sp500_mid_large \
  --backtest E-ANON-001 --wf-folds 5 --costs 0.0015 \
  --input ...slice... --output ...FIRING10_EQUITY_HARNESS_EANON...

# 5. Cross-check baby / anon repro if needed + whites RC/SPA family correction
python baby_strategies_backtest.py --family equity_momentum --filter e_anon
# + reality check tools from whites_reality_check...
```

**Gate Mapping Expectations (leveraging anon stats + hygiene power boost):**
- G4 WF (harness): Likely strong (prior 4/5 folds positive; clean tags increase n/attribution).
- G7 WR>40 / G8 PF>1: Already 53.8%/1.23 — PASS.
- G1 Sharpe (daily): Need real run (prior per-trade inflated?); target >=0.5-1.0 post-slip.
- G2/G3 bootstrap/CI, G5 MC, G6 FDR/crash: High n enables; expect pass vs. anon folds.
- If 6+/8 + admissible: promote.

**If passes:** Create A_passed/e_anon_001_short_term_momentum_equity_2026-05-21.md (format per luxalgo_confluence_2026-05-21.md + A_passed/); update hypothesis_registry.json E-ANON-001 status + result (add harness_verdict, full gates, hygiene_fix_applied); wire to emitters/quality_gates for shadow/paper (tv-paper-trade); add to 90-day plans / CONTINUAL baseline. Update living index.html Firing 10 section.

**If fails:** B_failed/ with specific gaps (e.g. G1 daily costs, bear-fold weakness); archive per M-107; propose regime filter fix (distinct from VIX gate).

**Citations for plan:** hypothesis_registry.json:495-560 (exact backtest_result + verdict_rationale + vix_gate), equity_strategy_harness.py:507 (MomentumFactorSignal), statistical_validation_framework.py + edge_stability_harness.py, 6GATES MD:171 (EQUITY power needs), FIRING10 hygiene markers, updates living log Firing9/10.

---

## Recommendations for A/B Placement & Next Steps

- **A_passed candidates (post-hygiene + successful run):** E-ANON-001 (strongest, promote T1/T2 if 6+/8); H-037/ VIX term (T2 per proxy, ETF/EQUITY diversification from CRYPTO heavy); PEAD variants if H-016/H-034 accrue power (academic robustness).
- **B_failed / quarantine (current or post-run fail):** Most FOREX named (stressed, direction bias; apply H-024b blocks + 1h + real data first); H-030/H-033 (already killed negative); H-028 meme versions (wrong universe); options gamma/skew (structural KILL).
- **Pending/Research:** FOREX carry JPY/gap-fill (after prereqs + clean tags); insider H-028v* diverse (wire real EDGAR parser per v3, re-harness on small-cap); sector rotation (H-040); equity factor composites via harness (integrate _apply_factor_model more broadly).
- **Immediate actions:** (1) Hygiene merge + backfill execution (P0, unblocks all EQUITY). (2) E-ANON-001 slice + full harness run (strongest leverage). (3) VIX/H-037 real validation on clean ETF. (4) FOREX direction/symbol fixes + 1h feed for re-harness. (5) Update hypothesis_registry + living report + new A/B markers. (6) Spawn parallel for any remaining (e.g. bond/ETF lighter if power accrues).
- **Risks/gaps addressed:** Tagging pollution (hygiene), low EQUITY n (clean + sidecar accrual), FOREX stress (fixes + tuned gates per 6GATES), M-107 (all pre-reg cited), snooping (SPA/FDR in framework).

**Firing 10 status:** Inventory expanded; 3 candidates identified with hygiene synergy; strongest backtest plan ready for autonomous execution post-patch. Synchronizes with Firing9 CRYPTO/COMMODITY + H-037 work. Add to CONTINUAL_STRATEGY_RESEARCH_BASELINE.md + public index.html Research Log Firing 10 subsection.

*Marker created 2026-05-21 Firing 10 per subagent convention (parallel to FIRING9_CRYPTO_SUBAGENT_FINDINGS etc.). All work directly cited to source lines/files. Ready for hygiene execution + E-ANON-001 validation.*
