# FOREX Strategies / Class — B_failed (2026-05-21 Firing 2)

**Status:** FAILED 6/8 gates (or INSUFFICIENT data/power for full validation) on all named strategies with real usage/attention. No A_passed for FOREX this cycle.

**Class Aggregate (edge_stability + resolved pipeline + reality checks):**
- n resolved ~68-342 (dashboard/6GATES snapshots); edge_stability n=1033 (dirty incl. history)
- 90d: WR 43.9%, PF 1.17, sharpe +0.027 (wilson 41-47%)
- 30d/7d: WR 29-42%, PF 0.64-0.96, sharpe negative
- Dashboard (2026-05-15): PF 0.81, WR 52.3%, total_pnl -24.37%, expectancy -0.07, sizing_allowed=false, "stressed"
- SPA/reality check (whites 2026-05-17): family edge survives but **0/5+ FOREX-named strats pass** (negative means, p=1.0 for carry/ig/rsi/cta variants)
- Historical deep: PF 0.27-0.29 n~1343 (pre-fixes); direction bias (LONG WR~29% PF<1 primary drag)

**Named Strategies (selected 5-7; all B_failed):**
- carry_trade_momentum / fx_smart_carry... : Hist Sharpe 1.07 WR43% (in-sample); prod n=20 WR25% PF0.63; whites n=28 mean -0.089 p=1.0 FAIL SPA. G1 marginal/FAIL, G2 FAIL, G7/G8 FAIL (25%<40%, 0.63<1). Citations: alpha_engine/forex_smart_picks.py:85; reports/forex_mutation_autopsy_20260515.md:64; whites_reality_check_winsorized_2026-05-17.md:31
- asian_range_breakout: No stats; ineffective on daily data (needs 1h). All gates INSUFFICIENT. Citations: alpha_engine/forex_strategies.py:228; updates/2026-05-05-forex-audit-swarm-review.md:57
- forex_rsi2_mean_reversion (connors/MeanReversionBB variants): Hist Sharpe1.33 WR43.5%; autopsy n=22-44 WR22.7-54.5% PF1.68-2.09 (mixed); whites n=131 mean-0.35 p=1.0 FAIL. G1 FAIL prod, G2 FAIL, G7 mixed/FAIL low WR slices. Citations: alpha_engine/forex_smart_picks.py:86; reports/forex_mutation_autopsy_20260515.md:66-68; whites...2026-05-17.md:34
- cot_positioning_forex: Proxy (zscore, not real COT); hypothesis F-ANON-001/H-024 TESTED_WEAK. No positive FOREX SPA/edge (COMMODITY cot passes but irrelevant). All gates INSUFFICIENT/FAIL. Citations: alpha_engine/forex_strategies.py:536; reports/hypothesis_registry.json:583+; reports/asset_class_90day_plan_FOREX_2026-05-15.md:77 (noise)
- ig_contrarian_sentiment: Hist Sharpe5.87 WR58.3% (claimed best); prod n=197-254 WR16.8% mean-0.18 p=1.0 FAIL SPA; LONG 16-21% WR. G1/G2/G7 FAIL live. Citations: alpha_engine/forex_strategies.py:985; whites...2026-05-17.md:32; LOOP_STATUS_2026-05-21T0411Z.md:72
- cta_fx_multifactor (cta_cross_asset_tsmom): Dashboard top 21% share / 36% USDJPY conc.; whites n=248 mean-0.50 p=1.0 FAIL; SHORT better than LONG. G1/G2/G7/G8 FAIL. Citations: reports/asset_class_90day_plan_FOREX_2026-05-15.md:25; whites...2026-05-17.md:37
- forex_mean_reversion_200d: Hist WR39.6% Sharpe0.17 (low). G1 FAIL. Citations: alpha_engine/forex_smart_picks.py:87

**Failed Gates Summary (using 6GATES MD + CYCLE defs + harness targets; FOREX-tuned relaxes noted):**
- G1 Sharpe: FAIL (class 0.027; most named negative/low in prod/reality check; hist claims in-sample only)
- G2 p<0.05: FAIL (SPA p=1.0 on all named FOREX variants; negative means)
- G3 MDD<15%: INSUFFICIENT (historical extremes e.g. 994% in one source; no recent per-strat)
- G4 WF>60%: INSUFFICIENT (n too low for reliable windows; harness design exists but not run on clean resolved FOREX for these)
- G5 MC 5th>0: INSUFFICIENT (no published per-named)
- G6 FDR/SPA: FAIL (reality check shows snooping inflation; no named FOREX passes family correction)
- G7 WR>40%: FAIL or borderline (class 43.9%; many named 16-30% in recent; some variant slices >50% but dragged by direction)
- G8 PF>1: Marginal on class 1.17 / some outliers (1.68-2.09); FAIL on carry/cta/overall resolved 0.81 and most named

**Root Causes (cited):** Direction bias (LONG anti-edge 80%+ volume); proxy data (COT/ carry static); granularity (daily for range strats); data inconsistency (PF/n snapshots vary wildly pre/post resolver-v2); concentration (USDJPY via cta); no regime (DXY etc.); multiple testing without correction in emissions.

**Recommendation:** (B) Failed / Quarantine. Apply/enforce direction blocks (LONG on ig/carry/cta/rsi/forex_carry), symbol blocks (NZDUSD/EURJPY/USDCHF), source penalties. De-emphasize FOREX emissions. Fresh full harness only after 1h data + real COT + DXY gates + clean n>200 resolved. Compare to EQUITY T2 / cleaned COMMODITY. No live sizing.

**Citations (key):** 6GATES_2026-05-21_V1_FREEBUFF.MD:160-169 (FOREX sparse, tuning); reports/continual_research/6gate_validation/CYCLE_2026-05-21_01_SUMMARY.md:105,124 (deferral); reports/asset_class_90day_plan_FOREX_2026-05-15.md:8-9 (verdict not production-grade), 89 (direction smoking gun); reports/forex_mutation_autopsy_20260515.md:39-68 (tables + actions); whites_reality_check_winsorized_2026-05-17.md:57-73 (SPA FAILs); edge_stability_FOREX.json:53-79 (sharpe 0.027); alpha_engine/forex_strategies.py + forex_smart_picks.py (defs + hist); hypothesis_registry.json:583+ (F-ANON/H-024 WEAK).

*Marker created 2026-05-21 firing 2. Builds on A_passed/luxalgo... and B_failed/cross_sectional_crypto... pattern.*
