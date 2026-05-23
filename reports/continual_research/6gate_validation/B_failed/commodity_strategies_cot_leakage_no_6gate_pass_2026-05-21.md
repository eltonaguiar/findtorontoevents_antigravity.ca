# COMMODITY Strategies / Class — B_failed (2026-05-21 Firing 2)

**Status:** FAILED 6/8 gates (or INSUFFICIENT data/power for full validation) on all named strategies with real usage/research attention. Heavy COT leakage/bypass documented; flagship post-clean negative. No A_passed for COMMODITY this cycle. Builds directly on FOREX firing 2 precedent and prior deferral in CYCLE_2026-05-21_01_SUMMARY.md.

**Class Aggregate (edge_stability + resolved pipeline + cot forensics + 90day plan):**
- n resolved historically inflated (e.g. 322 in May15 dashboard with 73% CT=F conc via cot_positioning 41% share); post-forensic clean n~5-178 in edge (May12 pre-full-reagg); true independent cycles tiny (COT weekly cadence).
- edge_stability_COMMODITY.json (as_of 2026-05-12, n_total=178): 90d/all WR 58.4%, PF 4.31, sharpe 0.352 (wilson_ci 50.5-64.9%); 30d WR62.3% PF7.75 sharpe0.436; 7d insane WR94.3% PF44 but n=35 (artifactual). All windows identical in "all".
- Dashboard (2026-05-15 per 90day): PF 2.49 WR61.5% n=322 total_pnl 557% but "honest_label: COMMODITY edge = cot_positioning on CT=F (73% of class PnL)"; smart_picks empty; concentration_warn true; sizing_allowed true but graduation_gate BELOW_EXPECTED.
- Post-clean cot_paper_pilot_status.json (2026-05-21): flagship cot_positioning::CT=F n=5 (from 5 unique CFTC releases, 123 raw emissions ~24.6x over), WR 40%, cum_pnl_usd -51.29, avg -10.26/trade, negative EV, tier SHADOW_INSUFFICIENT_N, DSR withheld (prior DSR=1.0 falsified).
- SPA/reality check note (from whites via FOREX report contrast): COMMODITY cot_positioning +3.28% p=0.000 n=134 (pre-clean CFTC version); no equivalent clean positive for current.
- 90day plan verdict: NOT production-grade; "headline Tier-2-beating numbers ... materially overstated by ... signal emission bug"; post-consolidation flagship collapses; yfinance futures quality issues, no micro for CT=F, high unit risk.
- Hypothesis: multiple COMMODITY H-00x (H-001, H-004, H-007, H-027, H-034, H-? seasonal) mostly REJECTED / HARNESS_REJECTED / TESTED_KILL / UNTESTED_DATA_GAP / KILL (leakage, eff negative/unstable, n/power issues, data gaps).
- Data hygiene critical failures: COT look-ahead (M-095), over-emission (20-50x on winners), historicals still polluting some dashboards/generators per cot_pipeline_audit_20260514.md; carry_momo proxy (not true basis), concentration risk extreme.

**Selected 5-7 Named Strategies (concrete implementations mined; COT variants + non-COT paths prioritized):**
1. **cot_positioning** (alpha_engine/cot_positioning.py:306 cot_positioning_strategy; also cftc_cot_commercial_signal in edge, multi_asset_cot, commodity_cot_contrarian.py:215 commodity_cot_contrarian_picks; H-001 family) — dominant emitter (41% share pre-clean).
2. **commodity_carry_momo_double_sort** (tools/research/commodity_carry_momo.py:140+ double_sort_basket + build_picks; audit_dashboard/data/commodity_carry_momo.json:2 "WIRED" as of 2026-05-20; M-022; 18-symbol universe incl CT/GC/HG/NG/Z*; academic Fuertes/Miffre/Rallis 2010 ref) — non-COT carry+mom diversifier, recently wired sidecar.
3. **seasonal_momentum** (alpha_engine/commodities_strategies.py:87 seasonal_momentum; per-symbol seasonal_bullish months + SMA/RSI filter; STRATEGY 1 with Bodie/Rosansky ref) — core non-COT.
4. **oil_inventory_momentum** (alpha_engine/commodities_strategies.py:268 oil_inventory_momentum; STRATEGY 3; inventory/roll related to H-004/H-027 families) — inventory surprise proxy path.
5. **commodity_tsmom_12m** (alpha_engine/commodities_strategies.py:919 commodity_tsmom_12m; STRATEGY 9 12-month time-series momentum; overlaps cta_cross_asset_tsmom in edge data) — momentum non-COT.
6. **metals_mean_reversion** (alpha_engine/commodities_strategies.py:366 metals_mean_reversion; STRATEGY 4) — mean-reversion non-COT.
7. **dxy_inverse_commodities** (alpha_engine/commodities_strategies.py:805 dxy_inverse_commodities; STRATEGY 8) — USD correlation non-COT (plus agricultural_spread, energy_momentum_breakout, commodity_seasonal.py:197 for completeness as variants).

(Excluded or lower: gold_safe_haven, energy_momentum_breakout, agricultural_spread — similar academic but less emission/attention in resolved set; full harness 150+ in kimi report / commodity_strategy_harness.py but not per-named production resolved.)

**Existing Backtest / Validation Stats (from Mined Sources; No Single Clean Full 6/8-Gate Run on Post-Dedup/Lag Resolved COMMODITY for These Names):**
- **COT flagship forensics (cot_paper_pilot_status.json 2026-05-21 + reports/cot_paper_pilot_overemission_falsified_20260513.md + cot_pipeline_audit_20260514.md):** Pre: n=101/123 WR~90% PF~2.7+ TIER_1 DSR1.0 (artifact); Post 1-per-cycle: n=5 WR40% PF0.17 PnL -$52 (negative); over-emission ratio 24.6x asymmetric (winners 19-50x, losers 3x). H-001 registry: pre-fix WR78.4% n=134 falsified by future-data bias (M-095 leakage); post-fix WR30% PF0.51 loser. "Do NOT re-test COT_positioning on this sample."
- **Edge stability (audit_dashboard/data/edge_stability/edge_stability_COMMODITY.json May12 n=178):** per_strategy includes cftc_cot_commercial_signal n=59 high short-window WR/PF; cot_positioning (multi_asset_cot n=33, alpha_engine n=3); cta_cross_asset_tsmom n=33; futures_bb_mean_reversion etc. Aggregate sharpe 0.35 / PF4.31 90d (pre full hygiene).
- **90day plan + dashboard (reports/asset_class_90day_plan_COMMODITY_2026-05-15.md + dashboard_data.json May15/21):** Class PF2.49 WR61.5% n=322 but 73% CT=F / 41% cot_positioning; post-clean callout collapse; carry_momo.json has data for 18 symbols but "MODERATE-confidence" proxy, wiring was OPT_IN now WIRED; graduation failed on economics.
- **Hypothesis registry (reports/hypothesis_registry.json):** H-001 COT REJECTED (leakage); H-004 inventory HARNESS_REJECTED (eff -0.0285, 0/18 windows); H-007 roll_yield REJECTED sign-unstable; H-027 physical inventory REJECTED; H-034 term_structure UNTESTED; H-? seasonal UNTESTED_DATA_GAP; small-spec COT variant NEAR_ADMISSIBLE but n insufficient (2/3 windows).
- **Harness / kimi report (alpha_engine/commodity_strategy_harness.py + tools/kimi_research_2026_05_20/COMMODITY_STRATEGY_REPORT.md + commodity_strategy_harness.py):** 150+ strats across 12 cats (COT_POSITIONING, CARRY, MOMENTUM, SEASONALITY, INVENTORY_DATA, TERM_STRUCTURE etc.) on 25 futures; targets Sharpe>=1, p<0.05, FDR<0.1, WF>=4 windows, ensemble 5-8. Expectations Sharpe 1.0-1.4 for carry etc. but production mismatch + hygiene issues per 90day. No per-named clean 6/8 table on resolved.
- **Other (config.py:780 COMMODITY_SYMBOLS ~22 entries incl. CT/GC/HG/NG/Z*/LE etc. + seasonal_bullish; multi_asset/commodity_futures_strategies.py; new_strategies_2026_04_13/commodity_seasonal_momentum.py; tests/test_m022...; audit_dashboard/data/cot_*.json per-symbol):** yfinance proxies, kill_switches, no full recent CPCV/DSR per-named clean; baby/seasonal claims academic only.
- **MDD/WF/MC/FDR specifics:** Sparse. No recent per-strat WF pass% or full MC/FDR on clean n for these 7. COT n too low for G4 (min~42 trades). Edge sharpe low vs G1>=1. Reality checks (SPA family) positive only on pre-clean COT slice.

**Failed Gates Summary (using 6GATES_2026-05-21_V1_FREEBUFF.MD:30-41 defs + CYCLE/FOREX-tuned relaxes: G1 relax >=0.5 for sparse, G8 >=0.8; G3 MDD<15% or<20%; G4 WF>=50-60%; G5 MC 5th>0; G6 crash>=-2; G2 p<0.05 or SPA; G7>40%; G8>1.0; INSUFFICIENT where n<~40-100 or no WF/MC/FDR run per 6GATES:160-169,282-288):**
- **G1 Sharpe:** FAIL (class 0.352 <<1.0 / even relaxed 0.5 marginal at best on dirty; post-clean cot negative; hist claims in-sample only; per-trade annualization inflates as noted in 6GATES:300+).
- **G2 Bootstrap p<0.05 / SPA:** FAIL or INSUFFICIENT (H-001 post-fix negative; flagship negative mean; most non-COT no published positive SPA/family pass on clean resolved; pre-clean COT p=0.000 but falsified).
- **G3 MDD / CI lower:** INSUFFICIENT (historical extremes in class; no recent per-named bootstrap CI/MDD on clean set; wilson barely + on 90d dirty).
- **G4 Walk-Forward:** INSUFFICIENT (n too low for 4+ windows on flagship post-clean n=5 and most named; harness design in commodity_strategy_harness.py but not executed on post-dedup/lag resolved for 5-7; COT weekly natural freq vs hourly emission).
- **G5 MC Bootstrap 5th>0:** INSUFFICIENT (no per-named published on clean; power limited by n~178 total / 5 for flagship).
- **G6 MC Crash:** INSUFFICIENT (same; 6GATES notes MC too easy anyway, needs tighten).
- **G7 WR>40%:** FAIL for flagship (post-clean 40% borderline but negative EV); class dirty 58% but many slices low; non-COT no strong clean confirmation.
- **G8 PF>1.0 (relax 0.8):** FAIL on flagship post-clean 0.17; class dirty high PF4+ but artifact + concentration; some variants mixed but overall not sustained clean.

**Root Causes / Data Hygiene (Critical per task note on COT leakage + 90day plan + registry):** 
- COT leakage/bypass/over-emission (M-095 look-ahead, 20x+ re-fires of same weekly release, asymmetric on winners, historicals polluting dashboard_generator + MySQL per cot_pipeline_audit_20260514.md and reports/cot_*_falsified_*.md; H-001 explicitly "NOT salvageable", "do not re-test").
- Concentration (73% CT=F one ag future no micro, high risk unit $1500 daily limit move).
- Proxy data (carry "free-path" moderate conf not true basis; some COT zscore proxies).
- Small true independent n (COT cadence weekly; yfinance roll/volume artifacts for futures).
- No daily mark-to-market PnL for realistic Sharpe (per 6GATES rec); per-trade inflates G1.
- Carry_momo / seasonal / inventory / tsmom non-COT paths defined + academic but limited production track record in resolved (recent wiring, sidecar status, UNTESTED/REJECTED in registry for related H).
- 90.8% EQUITY mis-tag bug (from 6GATES) indirectly affects cross views but COMMODITY tags cleaner yet still hygiene-failed.
- Harness power insufficient (G4 hardest per 6GATES ~22% overall pass even rich CRYPTO).

**Recommendation (B) Failed / Quarantine + Hygiene First:** 
P0: Complete re-aggregation of all historical cot_positioning/multi_asset_cot in trading_picks + dashboard_generator.py + edge files to strict 1-per-(symbol,COT_release,dir) + lag guard enforcement everywhere (follow 90day Phase1 + cot_pipeline recs). Verify post-reagg n>=20 cycles, PF>=1.5, WR>=50% on cleaned. 
Wire/expand non-COT (carry_momo quintile across 18, seasonal windows, clean inventory surprises if any pass new harness, tsmom cross-sectional) with hard conc cap <=25-30% per symbol/strat. 
Run full 6/8-gate harness (commodity_strategy_harness.py + statistical_validation_framework.py + six_gate... + edge_stability_harness.py + daily PnL series) ONLY post-clean on n>100 independent target + CPCV/DSR/PSR. 
Pre-register any promoted variant (M-107 via hypothesis-registry skill) BEFORE backtest. 
Enforce liquidity/roll checks, no micro risk stress for CT=F. 
De-emphasize vs EQUITY T2 / cleaned COMMODITY basket or external (KMLM/DBMF). If cleaned diversified fails T2 (PF>1.5/WR>50/MDD<20/n>100 sustained + SPA), treat as research satellite only. No live sizing until graduation + all-classes shadow.
Pending: COMMODITY_harness_rerun_prereqs similar to FOREX pending/.

**Citations (absolute paths, key lines):** 
6GATES_2026-05-21_V1_FREEBUFF.MD:30-41 (gates), 160-169 (sparse tuning), 282-292 (re-run + daily PnL recs); 
reports/continual_research/6gate_validation/CYCLE_2026-05-21_01_SUMMARY.md:12,20 (COMMODITY contrast + deferral); 
reports/asset_class_90day_plan_COMMODITY_2026-05-15.md:8-9 (core verdict NOT prod), 84-97 (over-emission + hygiene), 104-118 (gaps), 122-174 (90d plan phases); 
reports/hypothesis_registry.json:7-31 (H-001 REJECTED leakage M-095 n=134 WR78->30), 80-104 (H-004), 1179+ (H-021 small-spec), 1426+ (H-027), 1647+ (seasonal), 1844+ (H-034); 
audit_dashboard/data/edge_stability/edge_stability_COMMODITY.json:53-86 (90d sharpe0.352 n=178), 169+ (cot_positioning), 90+ (cftc_cot); 
audit_dashboard/data/cot_paper_pilot_status.json:2-50 (2026-05-21 n=5 WR40% neg PnL, falsification_refs); 
audit_dashboard/data/commodity_carry_momo.json:2-49 (WIRED, 18 sym, proxy caveat); 
reports/cot_paper_pilot_overemission_falsified_20260513.md:1-30 (20x artifact, n=5 WR40% collapse); 
reports/cot_pipeline_audit_20260514.md + cot_timing_leakage_audit_2026-05-13.md (forensics); 
alpha_engine/commodities_strategies.py:87 (seasonal_momentum), 268 (oil_inventory), 366 (metals_mr), 805 (dxy), 919 (tsmom); 
alpha_engine/cot_positioning.py:306+ (main fn + ledger dedup); 
alpha_engine/commodity_cot_contrarian.py:215; 
alpha_engine/commodity_strategy_harness.py:61+ (cats COT/CARRY/MOM/INV/SEAS); 
alpha_engine/config.py:780-810 (COMMODITY_SYMBOLS + CT=F etc.); 
tools/kimi_research_2026_05_20/COMMODITY_STRATEGY_REPORT.md:153+ (taxonomy 150+), 627+ (manifest carry/seasonal/cot/inv); 
tools/research/commodity_carry_momo.py:84+ (fetch/double_sort); 
reports/asset_class_90day_plan_COMMODITY_2026-05-15.md:52 (universe), 84 (major weaknesses); whites_reality_check (SPA COMMODITY cot pre-clean).

*Marker created 2026-05-21 as quant validation subagent in continual loop (firing 2, task 019e490182df). Pattern-matched to B_failed/forex_strategies_stressed_no_6gate_pass_2026-05-21.md and A_passed/luxalgo. Prioritize hygiene before any re-harness.*
