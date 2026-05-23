# FOREX Fresh 6/8-Gate Harness Rerun — Pending Queue (Firing 2, 2026-05-21)

**Priority:** HIGH (class stressed; no A_passed; deferred from firing 1)

**Prerequisites (must complete before reliable 6/8-gate run on clean data):**
1. Direction bias fixes: Add/enforce LONG blocks for ig_contrarian_sentiment, carry_trade_momentum variants, cta_cross_asset_tsmom, forex_rsi2/connors variants, forex_carry_momentum (per mutation_autopsy + LOOP_STATUS + H-024b precedent). SHORT bias or flip where data supports (e.g. ig SHORT 57% historical).
2. Symbol quarantine: NZDUSD=X, EURJPY=X, USDCHF=X (PF 0.00-0.32, WR<25%; autopsy 20260515).
3. Data feed upgrade: 1h (or better) OHLCV for asian_range_breakout, london_session_breakout, session strats (daily yf misses intraday ranges per 2026-05-05 swarm review).
4. Real data integration (replace proxies): Live FRED/central bank rates for carry (static carry_yield_diff in config.py/alpha_engine/config.py:628+); real CFTC COT for FX futures (6J,6B etc. with 3-day pub lag guard per M-095/H-001 fix in copy_trader_intel). Update cot_positioning_forex + carry (F-ANON-001/H-024).
5. Regime overlays: DXY, VIX, YC, central_bank_window, session_aware hard gates wired consistently across alpha_engine, kimi, multi_asset_scanner (partial in data_quality_gates.yaml + quality_gates.py).
6. Resolved pipeline hygiene: Post-resolver-v2 backfill/scrub for FOREX (n inconsistency 68 vs 342 vs 1343 historical; confirm asset_class tags). Target n>200 clean resolved for power.
7. Daily PnL series: Generate mark-to-market for realistic (non per-trade annualized) Sharpe (per 6GATES MD rec 2026-05-21:290).
8. Pre-registration: Any new/promoted F- variant via hypothesis-registry skill (M-107) BEFORE touching data or running harness. Archive failures.
9. Harness execution: Run full pipeline from tools/kimi_research_2026_05_20/statistical_validation_framework.py + six_gate_validated_strategy.py (G1-6 + bootstrap/FDR/MC/WF) + edge_stability_harness.py + alpha_engine/forex_strategy_harness.py (1,094-cand design) or multi_asset equivalents. Include costs/spreads, WF rolling (6mo/3mo), 1000 MC, BH-FDR or SPA family. Use FOREX-tuned thresholds (G1≥0.5, G8≥0.8 per 6GATES:164,278). Output per-strat + ensemble gates + A/B markers.
10. Validation cross-check: Whites RC/SPA or DSR on the cleaned set; compare to COMMODITY COT forensic lessons.

**Target Output for Next Firing:** Updated A_passed/B_failed markers for FOREX named strats (e.g. any AUD-boosted SHORT variant or MeanReversionBB that clears all 8 post-fixes). Class health metrics with daily-PnL Sharpe. Entry in main CYCLE summary + 90day_plan update.

**Related Pending (from firing 1):** MTF Confluence / funding variants (CRYPTO); VIX-momentum (EQUITY post-tagging fix). FOREX now highest class priority per stress status.

**Citations/Blockers:** 6GATES_2026-05-21_V1_FREEBUFF.MD:282-288 (re-run after fixes + daily PnL); reports/continual_research/6gate_validation/CYCLE_2026-05-21_01_SUMMARY.md:127-129 (next priorities include FOREX harness); reports/asset_class_90day_plan_FOREX_2026-05-15.md:82 (CPCV/DSR/PSR gap), 97 (execution gaps); reports/forex_mutation_autopsy_20260515.md:71-80 (implemented + proposed fixes); hypothesis_registry.json (F-ANON/H-024 status WEAK/IMPLEMENTED variants).

*Added to pending_fresh_backtest/ 2026-05-21 firing 2. Ready for autonomous execution when prereqs met (or parallel subagent).*
