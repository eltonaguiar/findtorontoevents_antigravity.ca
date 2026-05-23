# pending_fresh_backtest: Firing 4 Targeted Candidates (3 high-conviction + H-037/H-017 new) 6/8 Rerun Prereqs — 2026-05-20

**Job:** 019e490182df firing 4 (quant validation subagent, targeted + new mining)
**Target:** After P0 hygiene (tagging + COT) + daily PnL + emission/accrual, enable real 6/8-gate (validate_resolved_picks + statistical_validation_framework full suite) on:
- commodity_carry_momo_double_sort
- equity_vix_regime_momentum
- CRYPTO funding/confluence (kimi_funding_arb_relaxed_mut / coinglass_funding_confluence / funding_rate_arb family)
- Brand new: H-037 vix_term_structure_carry (ETF), H-017 funding_settlement_liquidation_cascade (CRYPTO), related confluence/funding scanners.
**Status:** BLOCKED on same prereqs as firing3 lighter (no evidence fixes landed; tagging bug persists per file inspection; COT not re-agg'd; daily PnL not extended; n/power low for 1/2/ new ETF). 12 prereqs below (extends LIGHTER_CLASSES_..._FIRING3_PREREQS_2026-05-20.md + COMMODITY/FOREX pending).

## Prereqs (P0-P2, must complete BEFORE fresh harness/validate run on these)
1. **Tagging Bug Fix (P0, 6GATES_2026-05-21_V1_FREEBUFF.MD:266-272 + B_failed/*_firing3):** Fix signal_tracker.py (set "CRYPTO" for *-USD native via _CAT_TO_ASSET_CLASS map); dashboard_generator.py:8282 fallback="UNKNOWN" (not EQUITY); backfill 198 misclassified in at_raw_picks/universal_resolved_picks.json; add symbol validation (regex reject) in universal_pick_resolver.py + collect_all_picks(); remove quality_gates.py:5598 EQUITY +10 bonus for signal_validation. Verify post-fix: grep resolved asset_class vs symbol; re-run validate asset_class_breakdown (real EQUITY/ETF increase, CRYPTO corrected). Enables #2 + H-037 + lighter.
2. **COT Hygiene Completion (P0, B_failed/commodity_strategies_cot_leakage..._2026-05-21.md + PR#941 + 90day_COMMODITY):** Full historical re-agg + dedup to exactly 1-per-CFTC-cycle (Tue settle/Fri release) in scraper, cot_positioning.py, commodity_*.py, generators, quality_gates, edge builders, MySQL; enforce COT_PUBLICATION_LAG_DAYS=3 + _is_cot_row_public guard everywhere (not partial); re-gen cot_*.json / edge_stability_COMMODITY / dashboard; confirm post-fix CT=F n>=20 clean PF>=1.5 WR>=50. Update H-001/H-036 notes. Critical for #1 carry_momo context (non-COT but COMMODITY polluted).
3. **Daily PnL Series + Realistic Sharpe (P1, 6GATES appendix + statistical_validation_framework.py:557 daily path + validate:77 note):** Extend validate_resolved_picks.py + framework to build/ use daily aggregated returns (not per-trade _sharpe_from_trades annualization) for G1/G3/MC. Required to reality-check baby Sharpe0.202 (vix) + carry expected 1.0-1.4 + H-037 backtest. Add option --daily-pnl.
4. **Lighter/ETF + VIX Wiring + Accrual (P0-P1, 90day ETF + config.py:836+ ETF_SYMBOLS + vix_regime_gate + quality_gates:4418):** Enable ETF_SECTOR_EMITTER + default VIX<25 gate on ETF emissions; wire etf_sector_momentum + vix_term (H-037 shadow); add tx_cost/slippage; target rotation contrib 40%+ to resolved. Accrue 30-60d paper/live for ETF/EQUITY n>=50-100 (post-tagging). H-037: run shadow on 11 SPDR sectors when contango.
5. **Candidate-Specific Wiring/Accrual (P1):** 
   - commodity_carry_momo: Full consume in dashboard_generator (JSON_PICK_SOURCES) + edge; validate proxy carry vs basis (Quandl); paper trade 14d+ (tv-paper-trade); accrue closed resolved n>50 for named "commodity_carry_momo_double_sort".
   - equity_vix_regime_momentum: Migrate baby to prod resolver path (vix_regime_gate + equity_strategies); accrue real EQUITY/ETF post-tag-fix.
   - CRYPTO funding (kimi_funding_arb_relaxed_mut / coinglass_funding_confluence / funding_rate_arb): Ensure full attribution in resolved (already some closed); increase coinglass scanner volume if needed; pre-reg any mut as H-017 variant if used.
6. **H-017 / New Funding Cascade Accrual (P1, hypothesis_registry:369-392):** Shadow run tools/h017_liquidation_cascade.py daily (collect 1min settlement events + displacement filters); target n>=50 cascade trades (est 2-3mo free Binance klines archive or Coinalyze); then backtest with edge_stability_harness.
7. **Fresh Harness + Full 6/8 Validate Run (P2):** Post 1-6: `python tools/validate_resolved_picks.py --by-asset-class --min-trades 10 --save-json reports/6gate_firing4_candidates.json`; run commodity_strategy_harness + etf/equity_strategy_harness + coinglass scanner harness on clean slices; statistical_validation_framework full (BootstrapValidator daily, WalkForward 752, MC stress, MTC FDR); edge_stability update + CPCV/DSR/anti-overfit on n>=100 candidates/new (H-037/H-017); per-class power analysis (min n for G4=4 windows).
8. **M-107 Pre-reg + Hypothesis Updates (P0):** For any new variant/mutation of carry/vix/funding/confluence/H-037/H-017: add/update reports/hypothesis_registry.json BEFORE backtest (record sample_lock, acceptance, operator_note). Already done for H-037/H-017/H-035 etc.
9. **Conc/Liquidity/Stress + Paper (P1):** Enforce MAX_PICKS_PER_SYMBOL + sector caps (CT=F <25-30% COMMODITY; XLE/ETF conc); liquidity ADV filter; no-micro FUTURES; 14d paper trade all 3 candidates + H-037 (use tv-paper-trade skill); stress CT=F live sizing limits $1500.
10. **Gates Tuning + Class-Specific (P1, 6GATES:273-278):** Relax G1 Sharpe for low-vol/ETF/EQUITY >=0.5-0.7 (H-037 backtest ~0. ?); G8 PF >=0.9-1.0; tighten MC G5/G6 (5th pctile >0.5 or harder crash per framework); add ETF VIX/YC filters to framework; re-eval G7 for high-vol CRYPTO funding. Add daily-PnL flag.
11. **CI / Audit / Re-run 6GATES + Markers:** Add test in tests/ for asset_class vs symbol consistency + named strat attribution; update 6GATES_*.MD with firing4 tables (per-candidate + H-037/H-017); create A_passed/ or updated B/pending based on fresh run results; update FIRING4 section + public log + CONTINUAL_STRATEGY_RESEARCH_BASELINE.md + hypothesis notes.
12. **Data Accrual Monitoring (P1):** Post-fixes: monitor audit_dashboard/data/ + edge_stability_*.json + universal_resolved_picks for n growth per named/asset_class; 30d target for lighter/candidates/new.

## Candidate + New Specific Prereqs (extends firing3 pending)
- commodity_carry_momo: Clean resolved attribution post-COT + proxy validation (second-month basis); n>50 closed; full wire.
- equity_vix_regime_momentum: Baby -> prod migration + real EQUITY/ETF n (post-tag); daily PnL Sharpe reality check vs 0.202.
- CRYPTO funding variants: Full slice in validate (already some closed kimi_funding_arb); confirm coinglass_funding_confluence attribution; distinguish from killed H-003/H-035.
- H-037 (new): Shadow on ETF sectors (contango LONG 5d); post-tagging ETF visibility; full framework on resolved after 30d+ accrual (builds on its existing WF backtest n=1185).
- H-017 (new): Data collection shadow for cascade events (settlement +1min + filters); n>=50 before harness (Ring different-alpha note).

**Expected Outcome Post-Prereqs:** #3 CRYPTO funding family + H-037 may reach T2 (real data + WF stats); #1/#2 accrue power or confirmed B; H-017 testable. Then firing5 re-run full loop + promote A where pass. ETF rotation + VIX (H-037 tie-in) strong transfer candidate.

**Blockers if Skipped:** False positives (tagging pollution on EQUITY/ETF), falsified stats (COT on COMMODITY), low power (n=0-20 or data gap for H-017), unvalidated backtest edges (wiring/accrual gap for H-037).

**Refs (builds on firing3):** pending/LIGHTER_CLASSES_ETF..._FIRING3_PREREQS_2026-05-20.md:1-33 (10 prereqs base); B_failed/targeted..._firing4... (this cycle's sim); 6GATES:266-292 + appendix; hypothesis_registry:369-462 (H-017/037); FIRING4_TARGETED..._SECTION.md; alpha_engine/statistical... + tools/validate...; 90day plans (all asset + carry/vix); prior B_failed/*_firing3 + CYCLE_01.

Ready for execution after P0 tagging + COT + daily PnL + ETF wire. Firing 4 targeted + new mining complete (inspection + B marker + this pending + section). No A_passed/ this cycle.

*For continual loop 019e490182df. Citations absolute.*
