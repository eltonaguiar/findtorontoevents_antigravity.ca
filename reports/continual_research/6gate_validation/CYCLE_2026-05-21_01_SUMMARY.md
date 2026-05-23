## Firing 2 Update (FOREX Subagent, 2026-05-21)
**Completed:** Full mining of alpha_engine/forex_*.py (carry_trade_momentum, asian_range_breakout, connors_rsi2_forex/forex_rsi2_mean_reversion, cot_positioning_forex, ig_contrarian_sentiment_forex, etc.), multi_asset/forex_strategies.py, forex_smart_picks.py (hist stats + Portfolio C), reports/asset_class_90day_plan_FOREX_2026-05-15.md + deep_dive/salvage/mutation_autopsy/aa7, hypothesis_registry.json (F-ANON-001 carry, H-024 g10_carry family), edge_stability_FOREX.json, whites_reality_check_winsorized_2026-05-17.md (SPA), LOOP_STATUS recent, 6GATES MD, harness reports, baby forex* files.

**Selected & Assessed (5-7 named with usage):** carry_trade_momentum (fx_smart variant), asian_range_breakout, forex_rsi2_mean_reversion (incl. MeanReversionBB/forex-rsi-ema-scout), cot_positioning_forex, ig_contrarian_sentiment, cta_fx_multifactor (cta_cross_asset_tsmom, top dashboard share), forex_mean_reversion_200d.

**Key Findings (detailed in new report):** 
- No strategies pass full 6/8 gates on clean production/resolved FOREX data (n sparse 68-342 resolved; edge n=1033 dirty). Historical backtest claims (ig Sharpe 5.87 WR58.3%, carry Sharpe1.07 WR43%, Portfolio C Sharpe2.06/WR45.9%/PF1.30) fail replication (whites SPA: all named FOREX variants negative mean p=1.0 FAIL; recent autopsy PF0.63 WR25% for carry, WR16.8% for ig n=197, class PF0.81 WR52.3% negative expectancy).
- Class edge_stability 90d: WR43.9% PF1.17 sharpe+0.027 (G1 FAIL; G7 borderline; G8 marginal); 30d/7d negative sharpe/PF<1.
- Reality check SPA family p=0.000 but 0 FOREX-named pass (contrast COMMODITY cot_positioning +3.28% p=0.000 n=134).
- Data issues: LONG bias (29% WR PF0.80 drag vs SHORT PF8+), proxy COT/carry, daily granularity for range strats, concentration (USDJPY 36% via cta 21% share), inconsistent n/PF snapshots.
- Gates: G1/G2/G7/G8 mostly FAIL or INSUF on live (tuned relaxes per 6GATES MD insufficient to save); G3/G4/G5/G6 INSUFFICIENT (n limits WF power, no per-named MC/FDR/MDD recent). Matches 6GATES MD:160-169 (FOREX sparse, 2 strats >=10 trades, can't run full WF).

**Markers Created:** B_failed/forex_strategies_stressed_no_6gate_pass_2026-05-21.md (class + 5-7 named FAIL details + citations); pending_fresh_backtest/FOREX_harness_rerun_prereqs_2026-05-21.md (10 prereqs: direction/symbol blocks, 1h data, real COT/FRED, regime gates, daily PnL, pre-reg, fresh harness run). Dedicated full section: reports/continual_research/6gate_validation/FOREX_CYCLE_FIRING2_2026-05-21.md (table + rigorous prelim assessment + recs + absolute citations).

**Recs (P0-P2):** Enforce direction/symbol/source blocks (LONG on ig/carry/cta/rsi; toxic symbols; penalties); upgrade data (1h + real COT/rates + DXY); fresh harness (statistical_validation + six_gate + edge_stability + forex_strategy_harness) only post-fixes on n>200 clean + daily PnL; de-emphasize FOREX vs T2 EQUITY/COMMODITY until sustained PF>1.5/WR>50 + SPA pass. No A_passed/FOREX.

**Citations:** See FOREX_CYCLE_FIRING2_2026-05-21.md (full list incl. 6GATES MD:160-292, 90day:8-97, whites:24-73, autopsy:53-80, hypothesis:583-1295, smart_picks:84-91, strategies.py:124-1111, edge_stability_FOREX.json:53-79, CYCLE_01:105/124).

Firing 2 FOREX complete. Ready for firing 3 (COMMODITY or re-run post-prereqs).

## Firing 2 COMMODITY Subagent Update (2026-05-21, parallel)
**Completed:** Full mining of alpha_engine/commodities_strategies.py (9 named: seasonal_momentum, gold_safe_haven, oil_inventory_momentum, metals_mean_reversion, agricultural_spread, energy_momentum_breakout, commodity_rsi_divergence, dxy_inverse_commodities, commodity_tsmom_12m), alpha_engine/commodity_strategy_harness.py + commodity_signal_generator.py + cot_positioning.py + commodity_cot_contrarian.py + commodity_seasonal.py, tools/kimi_research_2026_05_20/COMMODITY_STRATEGY_REPORT.md + alpha_engine/commodity_strategy_harness.py copy, tools/research/commodity_carry_momo.py, reports/asset_class_90day_plan_COMMODITY_2026-05-15.md + cot_paper_pilot_* / cot_pipeline_audit / commodity_deep_dive, hypothesis_registry.json (H-001 COT, H-004 inventory, H-007/027/034 roll/inv/term, seasonal), audit_dashboard/data/{edge_stability_COMMODITY.json, commodity_carry_momo.json, cot_paper_pilot_status.json (2026-05-21), dashboard_data.json, cot_*.json}, alpha_engine/config.py:780 COMMODITY_SYMBOLS, multi_asset/commodity_futures_strategies.py, new_strategies/commodity_seasonal_momentum.py, 6GATES MD, CYCLE deferral notes.

**Selected & Assessed (5-7 named):** cot_positioning (incl. cftc_cot_commercial_signal, commodity_cot_contrarian_picks; H-001 dominant 41% share), commodity_carry_momo_double_sort (M-022 WIRED sidecar 18-sym), seasonal_momentum (STRAT1), oil_inventory_momentum (STRAT3, H-004 family), commodity_tsmom_12m (STRAT9, cta tsmom overlap), metals_mean_reversion (STRAT4), dxy_inverse_commodities (STRAT8). Non-COT paths emphasized; COT leakage noted heavily.

**Key Findings (detailed in B_failed marker + new COMMODITY section):** 
- No strategies pass full 6/8 gates on clean post-dedup/lag resolved COMMODITY data. Flagship cot_positioning::CT=F post-clean n=5 WR40% PF0.17 cum PnL -$51 (negative EV, SHADOW_INSUFFICIENT_N, DSR withheld); pre-clean 101/123 trades ~24x over-emission artifact (winners 19-50x) falsified WR90%+ / PF2.7+ / DSR1.0 (cot_paper_pilot_overemission_falsified_20260513.md + cot_pipeline_audit + H-001 REJECTED M-095 leakage WR78->30 PF0.51 loser; "NOT salvageable").
- Class edge_stability (May12 n=178 dirty): 90d WR58.4% PF4.31 sharpe0.352 (wilson 50.5-64.9%); 7d/30d inflated. 90day plan May15: dashboard PF2.49 WR61.5% n=322 73% CT=F conc via cot 41% but "materially overstated"; graduation failed; hygiene gaps (yfinance rolls, proxy carry, no micro CT high risk).
- SPA contrast pre-clean positive for COMMODITY COT but irrelevant post-forensic. Registry: 7+ COMMODITY H- REJECTED/HARNESS_KILL/UNTESTED (leakage, eff negative/unstable, data gaps, n< power).
- carry_momo recently WIRED (json 05-20) but proxy caveat, limited resolved track. Non-COT (seasonal/tsmom/inv/mr/dxy) academic + harness cats but no strong clean per-named 6/8 or SPA on production resolved.
- Data issues: COT leakage/bypass/over-emission primary (M-095 + 20x+), concentration (CT=F 73% one ag no-micro), small true n (weekly COT vs hourly re-emit), proxy data, yfinance futures quality, historicals polluting, no daily PnL realistic Sharpe, G4 power impossible on n=5-20.
- Gates: G1 FAIL (sharpe 0.35 <<0.5 relaxed); G2 FAIL/INSUF (negative post-clean, no clean SPA pass on named); G3/G4/G5/G6 INSUFFICIENT (n limits WF/MC/FDR; harness exists but not clean-run); G7/G8 FAIL flagship (40%/0.17) or marginal dirty class. Matches 6GATES sparse notes + FOREX precedent. No A_passed/COMMODITY.

**Markers Created:** B_failed/commodity_strategies_cot_leakage_no_6gate_pass_2026-05-21.md (class + 5-7 named FAIL + citations + root hygiene); pending_fresh_backtest/COMMODITY_harness_rerun_prereqs_2026-05-21.md (10 prereqs: COT re-agg/dedup/lag, daily PnL, carry_momo full wire, full harness post-clean n>100, pre-reg, conc caps, liquidity stress). Pattern: B_failed/forex... + pending/FOREX...

**Recs (P0-P2):** P0 hygiene first (re-agg all COT historicals to 1-per-cycle + lag everywhere; verify n>=20 clean cycles PF>=1.5 WR>=50; update generators/edges/quality_gates). Diversify ruthlessly via wired carry_momo quintiles + seasonal/tsmom/inventory clean variants (conc cap 25-30% CT); run full harness (commodity_strategy_harness + stat validation + edge + daily PnL) only post-fixes on clean target + CPCV/DSR. Pre-reg (M-107) before any backtest. Stress CT=F live sizing (no micro, $1500 limits). De-emphasize vs EQUITY T2 until sustained T2 gates + SPA; treat as research if fails 90d diversified. No live sizing. Ready for firing 3 post-prereqs or EQUITY re-run.

**Citations:** See B_failed/commodity_strategies_cot_leakage_no_6gate_pass_2026-05-21.md (full list: 6GATES:30-292, 90day_COMMODITY:8-197, hypothesis:7-1861, edge_stability_COMMODITY:53-1120, cot_paper_pilot_status:2-50 (2026-05-21), overemission report, commodities_strategies.py:87-1026, cot_positioning.py:306, commodity_carry_momo.py:84, config.py:780, kimi COMMODITY_STRATEGY_REPORT:153-723, CYCLE_01:10-20, FOREX_CYCLE:43 (SPA contrast)).

Firing 2 COMMODITY complete (B marker + pending prereqs + full section). Firing 3: post-hygiene COMMODITY harness rerun or EQUITY deep validation + cycle summary close.

---

## Firing 2 Consolidated Summary (2026-05-21)

**Progress this firing:**
- Two high-quality parallel subagents completed for FOREX and COMMODITY (full mining, 5-7 named strategies each, 6/8-gate tables, citations).
- Fresh validation run attempted via `tools/validate_resolved_picks.py --by-asset-class --save-csv` (partial success; confirmed high-Sharpe CRYPTO names and low-n limitations for FOREX/COMMODITY).
- New B_failed and pending_fresh_backtest markers created for both classes.
- Main living baseline document created at `reports/CONTINUAL_STRATEGY_RESEARCH_BASELINE.md`.

**Overall Loop Status after 2 firings:**
- CRYPTO: Several clear 8-gate passers identified on real data.
- EQUITY: Blocked by tagging bug (real n~20).
- FOREX: Entire class B_failed / stressed — no full gate passers on clean data.
- COMMODITY: COT flagship falsified; non-COT promising but insufficient clean power.

**Persistent Blockers:** Asset class tagging, COT data hygiene + bypasses, lack of daily PnL for realistic Sharpe, low statistical power on FOREX/COMMODITY/EQUITY.

**Next Firing (3):** Targeted harness execution on 1-2 high-priority non-COT or VIX-EQUITY candidates post noted hygiene, or light expansion to ETF/FUTURES.

All work remains research-only and fully cited.

