# pending_fresh_backtest: Lighter Asset Classes (ETF/FUTURES/BOND/PENNY/MEME) + Candidate 6/8 Rerun Prereqs — Firing 3 (2026-05-20)

**Job:** 019e490182df firing 3 (quant validation subagent)
**Target:** After tagging bug fix + COT hygiene + emitter wiring, enable real 6/8 on ETF etc. + commodity_carry_momo, equity_vix_regime_momentum, seasonal/funding variants.
**Status:** BLOCKED on n/power/hygiene/tagging. 10+ prereqs below (modeled on FOREX/COMMODITY pending/ files).

## Prereqs (P0-P2, must complete BEFORE any fresh harness/validate_resolved_picks --by-asset-class run)
1. **Tagging Bug Fix (P0, from 6GATES_2026-05-21_V1_FREEBUFF.MD:266-272):** Implement + test signal_tracker.py + stocks_competition asset_class setter for crypto symbols; dashboard_generator.py:8282 fallback="UNKNOWN"; backfill 198 rows; add symbol validation in universal_pick_resolver.py and collect_all_picks; remove quality_gates EQUITY bonus for signal_validation. Verify in resolved_picks.json grep and validate_resolved_picks asset_class_breakdown (real EQUITY/ETF should increase, CRYPTO correct).
2. **COT Hygiene Completion (P0, from B_failed/commodity... + cot_pipeline_audit + PR#941):** Full historical re-agg + exact 1-per-cycle dedup + lag=3 guard in ALL files (scraper, cot_positioning.py, generators, quality_gates, edge json, MySQL); re-gen cot_*.json / edge_stability_COMMODITY / dashboard; confirm post-fix CT=F n>=20 clean PF>=1.5 WR>=50. Update H-001 note.
3. **Lighter Emitter Wiring + Volume (P0):** ETF: set ETF_SECTOR_EMITTER_ENABLED=1 + schedule alpha-engine-etf.yml; enforce VIX<25 default in vix_regime_gate.py for asset_class=ETF (quality_gates + dashboard); promote etf_sector_momentum / etf_dual_momentum primary (config weights, passes_*_gate); add tx_cost/slippage_validator wiring (PR#1026 scaffold). FUTURES/BOND: unblock futures_strategies.py / bond_strategies.py emissions (if hygiene ok); wire futures_momentum + bond_yield_curve_inversion as sidecars; use config FUTURES/BOND_SYMBOLS + permissive floors. PENNY/MEME: integrate penny_stock_strategy_harness outputs to resolver; increase screener emission; map sub_class correctly.
4. **Data Accrual (P1):** Run live/paper for 30-60d to hit n>=50-100 per lighter class (ETF target rotation contrib 40%+; FUTURES/BOND/PENNY from 0/11/31 to 50+). Use baby_strategies + etf/bond/futures harness for synthetic fill if needed. Monitor via audit_dashboard/data/ + edge_stability_*.json.
5. **Daily PnL Series + Realistic Sharpe (P1, per 6GATES appendix + framework):** Extend validate_resolved_picks.py + statistical_validation_framework.py to compute daily returns (not per-trade annualization) for G1 Sharpe/CI/MC. Required for ETF backtest transfer (0.97-1.63) vs current inflated.
6. **Fresh Harness + Validate Run (P2):** Post 1-5: python tools/validate_resolved_picks.py --by-asset-class --min-trades 10 --save-json reports/6gate_lighter_firing3.json; run etf_strategy_harness.py / bond_strategy_harness.py / futures* / penny* on clean resolved slice; statistical_validation_framework full (Bootstrap + WF + MC + MTC); edge_stability update; CPCV/DSR/anti-overfit on candidates if n>=100.
7. **M-107 Pre-reg + Hypothesis (P0):** For any new lighter/carry/vix/seasonal/funding strat variant: add to reports/hypothesis_registry.json BEFORE backtest (e.g. extend H-003/037 for ETF rotation VIX, H-005 for FUTURES). Record sample_lock + acceptance.
8. **Conc/Liquidity/Stress (P1):** Enforce per-symbol caps (config MAX_PICKS_PER_SYMBOL=1) + sector for ETF/FUTURES (XLE, CT=F risk); paper TV trade lighter picks 14d (tv-paper-trade skill); liquidity filter (ADV/volume in etf_quality_filters.py); no-micro for FUTURES (high margin risk per 90day).
9. **Gates Tuning + Class-Specific (P1, 6GATES:273-278):** Relax G1 Sharpe for low-vol (ETF/FUTURES/BOND ≥0.5-0.7); G8 PF ≥0.9-1.0; tighten MC G5/G6 (5th pctile >0.5 or harder crash); add ETF-specific VIX/YC in framework. Re-eval G7 >40% for PENNY (higher vol).
10. **CI / Audit / Re-run 6GATES:** Add test in tests/test_quality_gates.py for asset_class vs symbol; update 6GATES_*.MD with re-run tables post-fix; create A_passed/ or updated B for lighter if pass.

## Candidate-Specific Prereqs
- commodity_carry_momo: Full wire to dashboard/edge (already partial); clean resolved attribution post-COT-hygiene; proxy carry validation (second-month basis vs free-path); n>50 closed for gates.
- equity_vix_regime_momentum: Migrate baby backtest to prod resolved path (use vix_regime_gate + equity_strategies); accrue real EQUITY n (post-tagging fix); daily PnL for Sharpe 0.202 reality check.
- Seasonal/funding: Attribute in resolved_picks; pre-reg; hygiene on any COT overlap.

**Expected Outcome Post-Prereqs:** ETF rotation + VIX may reach T2 (PF>1.5+ from backtest transfer); others accrue to n-power for G4+; candidates either graduate to A or confirmed B with stats. Then firing 4 re-run full loop.

**Blockers if skipped:** False positives (tagging pollution), falsified stats (COT), low power (n=0-20), unvalidated backtest edges (wiring gap).

**Refs:** 90day plans (all 5 lighter), 6GATES:266-292, CYCLE_01, COMMODITY/FOREX pending/, alpha_engine/config.py:343 (min_elite_score_for), statistical_validation_framework.py:1051 (full gates), hypothesis_registry.json (H-003/005/037).

Ready for execution after P0 tagging+COT+emitter. Firing 3 lighter expansion complete (inspection + markers).

*For continual loop 019e490182df.*
