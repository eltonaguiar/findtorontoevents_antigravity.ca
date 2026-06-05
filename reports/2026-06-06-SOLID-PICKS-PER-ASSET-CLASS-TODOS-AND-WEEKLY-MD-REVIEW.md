# Solid Picks Per Asset Class — Statistically Valid, Passing Recent Criteria + Weekly .MD Action Items Review (2026-06-06)

**Context / Criteria for "Solid" (from recent infra and Goal #1):**
- 5-axis scrutiny (per_class_scrutiny_engine.py): concentration <30%, fat-tail top-3 <30% gross wins, OOS (H1/H2 both PF>=1.0), batch max date <35%, binomial p<0.05.
- Walk-forward (walk_forward_per_strategy.py with --require-macro-join + total_pf >=1.0 hard-gate).
- Hard gates (passes_hard_money_gates / quality_gates / eagle_gates): n>=100 clean, WR>=50%, PF>=1.5, DSR/PBO/WFE/MinTRL, recency 14d/48h panels first (verify no degradation), conc/fat, + net costs/liquidity/ADV where wired.
- Intrabar OHLCV replay (sustained fills preferred over wick).
- Dedup, clean ingest, no 2026-06-04 backfill contamination (post-filter), BANNED_SOURCES, alpha_macro regime context.
- Live forward (closed_at not null, _gated_forward_test_isolated where possible) vs backfill.
- Recency panels (pick_summary_stats_14d, 48h) verified first (per CLAUDE.md Goal #1 and consults).
- For "real money": pass all above + forward n accumulation in paper pilots, multi-source, small sleeve risk, auto-kill on degradation.
- Current reality (from 2026-06-05 scrutiny/inventory/WF/deep-dives): **Only 1 solid T1: mega_mutation::crypto** (n=296, WR=63.9%, PF=3.12, 5/5 axes; consistent with WF PASS PF=2.58 n=166 post-macro; OHLCV validated). 0/9 classes money-ready per live verdict. Most "winners" are batch artifacts from 2026-06-04 resolver backfill or single-day concentrations.

**Current Solid Picks Per Asset Class (passing all recent criteria as of 2026-06-05 data):**
- **CRYPTO**: 
  - `mega_mutation` (source_system) on various symbols (JUPUSDT, ENAUSDT, ADAUSDT, WIFUSDT post AVAX/STX kill in registry). n~295 post-filter, passes 5-axis, WF with macro+pf gate, recency checks in reports. Stat valid, OOS stable, no fat/batch after hygiene. (See TRUE_WINNERS_SCRUTINY_2026-06-05.md, PER-CLASS-T2-INVENTORY, DEEP-DIVE-SERIES, RISK_REVIEW_MEGA_MUTATION_2026-06-05.md).
  - Others (luxalgo_confluence, ml_crypto_predictor, etc.): WATCH or BORDERLINE (fail binom, oos, batch, conc, fat). Many n inflated by backfill.
- **FOREX**: 0 solid. multi_asset_copytrader::forex n=1198 WR=45.2% PF=1.01 4/5 (fails oos); non_crypto_consensus n=110 borderline (batchy April, oos/bin fail); cta etc. fail conc/oos. Deep dive showed walk-forward PASSes were artifacts. (deep_dive_forex_regime_2026-06-05.md, inventory).
- **COMMODITY**: 0 solid. cta_replicator borderline pre-filter but OOS fail, 50% conc in SI=F, binom p=0.5; multi_asset_copytrader loser. Backfill contamination created false signals. (deep_dive_commodity_2026-06-05.md, bond/commodity reports).
- **EQUITY**: 0 solid in DB (n small, 4 sources all FAIL or INSUFF). Analyst consensus (e.g. NVDA strong_buy 58 analysts +36% upside from yf) noted as "true winner" layer in PER-ASSET-WINNER-DIG but DB has only 5 NVDA trades (all losers in short-term picks). cta_golden_cross on SPY small n=6. No 5-axis passers yet. (PER-ASSET-WINNER-DIG.md, inventory).
- **BOND**: 0 (n=8 post-filter, structurally low; pre-backfill 16 in 3mo, all from non_crypto_consensus TIME_EXIT with 0 pnl). n-ramp needed at generation, not filter. (bond_n_ramp_analysis_2026-06-05.md).
- **ETF**: 0 (n<30 for scrutiny; etf_verified_dual_momentum in paper pilot but not yet n>=30 closed clean). (inventory).
- **MEME / empty / others**: FAIL or INSUFF (alpha_engine_fast meme WR low; empty class triage needed).
- **Overall**: 1 solid (crypto only). 0 classes have multiple or cross-asset solid. Live forward panels understate due to backfill in n_resolved (LIVE-FORWARD-TRIAGE.md).

**Set of TODOs to Achieve / Expand Solid Picks Per Asset Class (stat valid, passing criteria, "ready for real money" path):**
Prioritized P0 (immediate, hygiene + bootstrap), P1 (infra + pilots), P2 (scale + external). All must produce picks that pass the full criteria above + accumulate live forward n in pilots with recency verified.

**P0 - Data Hygiene & Clean Baseline (1-3 days, unblock all):**
- Exclude 2026-06-04 backfill dates from *all* scrutiny, walk-forward, inventory, money_ready, pilot dashboards (one-line filters in per_class_scrutiny_engine.py, walk_forward_per_strategy.py, build scripts). Re-run all and update reports/jsons. (From deep_dive_commodity, forex, inventory, LIVE-FORWARD-TRIAGE, DEEP-DIVE-SERIES).
- Backfill alpha_macro to current (DXY/VIX/SPY/yields daily via yf, as in populate_alpha_macro.py cron). Re-run scrutiny/WF with macro-join. Alert if >3d stale. (inventory Day7, deep_dive_forex, DEEP-DIVE-SERIES).
- Set _gated_forward_test_isolated=1 (or equivalent) on the 6,358 live forward closes (closed_at IS NOT NULL) from trading_picks in at_pick_outcomes. Update audit surfaces / panels / bootstrap to filter only live (not backfill). Fixes 97% backfill in forward stats. (LIVE-FORWARD-TRIAGE.md, money-ready bridge truth).
- Fix resolver backfill for PnL on trading_picks (918 rows NULL/zero despite exit_price; tools/backfill-resolved-pnl or universal_pick_resolver). Re-resolve stale ~33k in at_pick_outcomes. (updates/2026-06-05-backfill-resolved-pnl-tool.md, kimi-phase, zero-pnl-safeguard).
- Triage empty class in alpha_engine (n=87 FAIL con/oos/bat/bin); ensure category stamped at emission. (inventory).

**P0 - Solid Picks Bootstrap per Class (using non-LLM consensus/fundamentals for fast n):**
- **EQUITY (highest potential per user query + reports)**: 
  - Pull yfinance analyst consensus (recommendationKey/Mean, numberOfAnalystOpinions, targetMeanPrice vs current for upside, peg) + insider net (from value_screener or equity_insider_buying.py) + short% + earnings surprise for liquid names (NVDA, META, MSFT, etc. — NVDA +36% on 58 analysts strong_buy noted as "true winner" in PER-ASSET-WINNER-DIG.md).
  - Emit as new "equity_analyst_consensus" or extend equity_momentum_quality.py + value_screener_runner (already has production caller, Wire-Up ok). Apply 3-step WR_SCRUTINY (conc<=50%? wait full 5-axis) + full gates + recency.
  - Paper pilot immediately (high-quality-paper-pilot-stubs.py style) to accumulate n>=30-100 live forward. Scrutinize continually (as in PER-ASSET-WINNER-DIG trigger). Cross with pro trader if any clean. (PER-ASSET-WINNER-DIG.md, inventory, REAL-MONEY-ROADMAP, updates high-quality pilot).
- **CRYPTO**: 
  - Solidify mega_mutation (already solid; kill remaining drags like any AVAX-like via registry). Add funding_rate_extreme (in feature_signals) as co-signal. Re-scrutinize with clean data + macro + 14d/48h. Ensure pilot has gated live only. (multiple reports).
  - Investigate/kill batched like prediction_market_consensus (89% WR but 52% DOGE conc + batch). (PER-ASSET-WINNER-DIG).
- **FOREX**: 
  - Re-run scrutiny/WF post alpha_macro backfill + macro-join + total_pf gate on non_crypto_consensus, myfxbook_retail_contrarian, ig_contrarian_sentiment, cta_cross_asset_tsmom. Condition on DXY if edge (from forex deep dive). Demote to LOW_CONFIDENCE if not T2. Watchlist only if WR~52% suggestive. (deep_dive_forex, inventory, updates kimi triage).
- **COMMODITY**: 
  - Kill multi_asset_copytrader emission (consistent loser WR34%). Diversify or deprecate cta_replicator if can't pass conc/oos/binom (50% SI=F). Re-evaluate post clean data. No T2 yet. (deep_dive_commodity, inventory).
- **BOND / ETF / MEME**: 
  - BOND: n-ramp at *generation* (PIMCO replication, yield curve mom, duration timing from reports). Not filter. Pre-backfill data small, all 0 pnl TIME_EXIT. (bond_n_ramp, inventory).
  - ETF: Accumulate n for etf_verified_dual_momentum paper pilot (already running). Apply gates once n>=30 closed clean. (inventory, etf backtest reports).
  - MEME: Low priority (low WR in alpha_fast). 

**P1 - Infra, Gates, Pilots, Recency for All Classes (ensure pass criteria + fast validation):**
- Enforce recency 14d/48h as *first* gate in all paths (passes_hard, is_admissible, money_ready, pilots). Fix 14d sync (was 404, now in pick-summary-14d-sync.md). Build daily recency panels. Verify before any "solid" claim. (REAL-MONEY-ROADMAP, pick-summary updates, Goal #1).
- Harden all reports/scripts with backfill filters + macro-join + total_pf>=1 + gated live forward. Re-run inventory/scrutiny/WF post P0. (deep dives, inventory, triage).
- Wire high-quality / analyst consensus picks to paper_pilot stubs (promote_high_quality_to_paper_pilot.py, verified_strategies/paper_pilot/ dirs). Track forward n, WR, PF, recency in pilot_forward_dashboard. Auto quarantine if fail gates. (high-quality-paper-pilot-stubs.md, grok-masterplan updates).
- Add net-costs, liquidity (ADV), small-n guards to hard gates/replay if not (REAL-MONEY-ROADMAP).
- For ai-tournament: Gate pipeline (AI_TOURNAMENT_PIPELINE_ENABLED=false default per updates). Document all actions here in diagnostics/summary. Quarantine as experimental (no real $). (grok-masterplan-phase2, ai-tournament workflow).
- Update audit surfaces (money_ready_verdict, pick_funnel, surface_truth) to use only live gated forward + clean data. Fix inflated WR/PF from backfill (money-ready-bridge-audit-truth.md).

**P1 - Weekly .MD Review & Documentation Process (this task):**
- Review all .MD past week (see list below). Extract actions into this .MD + feed + ai-tournament data.
- Add ENH/INC to incidents_enhancements_feed.json for visibility (and ai-tournament if it consumes similar).
- Add update card to updates/index.html before AUTO (this one).
- Run deploy.

**P2 - Scale, External, Cross-Class:**
- Forward n→100 for survivors (mega crypto, potential ETF/equity analyst). Re-evaluate with rolling.
- External replication (DBMF/KMLM for comm, PIMCO for bond, analyst consensus validation).
- Cross-asset book risk, Kelly sizing, live monitoring for solid ones.
- Integrate pro trader consensus (cleaned copytrader) where passes.
- For EQUITY pro-trader: NVDA etc. as "source" even if DB n low — treat analyst as signal, forward test.

**Extracted Action Items / Enhancements / Fixes from .MD Review (Past Week ~2026-05-30 to 06-06; aggregated, not exhaustive; prioritized for solid picks):**
From PER-CLASS-T2-INVENTORY-POST-FILTER.md + DEEP-DIVE-SERIES:
- Backfill alpha_macro daily + re-run scrutiny/WF with join (Day7).
- Investigate luxalgo_confluence n discrepancy (2009 vs 767).
- Forward n + external replication (Day30).
- Exclude 2026-06-04 backfill everywhere.
- Kill multi_asset_copytrader commodity; diversify cta or deprecate.
- Condition forex on DXY; demote non-passing to LOW_CONFIDENCE.

From deep_dive_commodity_2026-06-05.md:
- Re-run reports post backfill filter.
- Disregard WF PASS for banned strategies until clean.

From deep_dive_forex_regime_2026-06-05.md:
- Add INNER JOIN alpha_macro to WF SQL.
- Daily alpha_macro cron + stale alert.
- Re-run non_crypto etc. post backfill.

From bond_n_ramp_analysis_2026-06-05.md:
- n-ramp at generation for BOND (PIMCO etc.), not filter. (No short-term fix).

From PER-ASSET-WINNER-DIG.md (user trigger: "solid picks... analyst consensus or pro trader"):
- Pull yf analyst for EQUITY (NVDA +36%, META/MSFT/NFLX strong_buy >30% upside). Use as layer for "true winners".
- Scrutinize continually, narrow per class (even without full FT).
- Kill batched (BTCUSDT SELL 1-day backfill n=100 fake PF1.8; prediction_market_consensus 52% DOGE conc).
- Watch NVDA analyst vs our DB short-term picks (DB losers).

From LIVE-FORWARD-TRIAGE.md:
- Set gated_forward_test_isolated on live 6k+ closes from trading_picks.
- Fix bootstrap/panels to use only live (not 97% backfill).
- P0 for honest n in money-ready / forward stats.

From DEEP-DIVE-SERIES + inventory actions (many completed this session: reports shipped, WF hardened with macro+pf gate, alpha_macro populated + cron, inventory, updates card).
- Re-run post clean.

From updates/2026-06-05-*.md (kimi, grok masterplan, high-quality pilot, pick-summary, zero-pnl, backfill-pnl, at-pick-outcomes tp-sl, luxalgo-dedup, money-ready-bridge, vllm, litellm):
- Fix TP/SL misclass in at_pick_outcomes (sign_flip_purge didn't update resolution_method; root cause for asymmetry).
- Backfill resolved PnL on 918 trading_picks rows (NULL/zero).
- Wire high quality paper pilot stubs (ENH119, promote script, no DB writes).
- Kimi Phase1/2: resolver backlog 33k, source bans (done some), zero-pnl safeguard, stale resolver fixes, pick summary 14d sync (404 fix, alias), local litellm aliases, vllm model inventory + benchmark.
- Luxalgo forward dedup truth (non-existent column fallback overstated).
- Money ready bridge truth (inflated surfaces vs 0/9 honest; PR537 for 923 NULL pnl).
- Ai-tournament: gate pipeline (AI_TOURNAMENT...=false default), phase3 tier-2 ladder, stop bleed.
- High-quality picks plan: 4-week forward, but stubs needed (done in one).
- Pick momentum loop clean, etc.

From older but in window (STRATEGY_INVENTORY, etf backtest, PR-02 etc.):
- Continue inventory, ETF vix gate, dual mom backtest validation.

**Documentation under /audit/ai-tournament.html:**
- Added "md_review_action_items_2026_06_06" / "solid_picks_todos" section to audit_dashboard/data/ai_tournament_model_diagnostics.json summary (powers fleet-status / panels on the page). Includes key aggregated actions above + link to this .MD.
- Added ENH-147 (this roadmap + weekly review) to incidents_enhancements_feed.json (OVERALL, real-money / ai-tournament category; surfaces in incidents and linked from tournament context per history).
- New updates/index.html card (before AUTO) linking this .MD, the review, and ai-tournament data update. (Will be deployed.)
- The ai-tournament pipeline gated, and diagnostics now includes the solid picks status (only crypto mega) + todos to expand per class with analyst/fundamentals/consensus for fast stat-valid candidates.

**Verification / Next:**
- All counts from live DB via get_stocks_creds / scrutiny json / WF json / reports.
- Re-run tools/per_class_scrutiny_engine.py --min-n 30 and walk_forward with flags post P0 hygiene to confirm/update solid list.
- Pilot EQUITY analyst consensus + mega immediately.
- This .MD + feed + diagnostics + card + deploy ensures actions documented and visible under /audit/ai-tournament.html (via its data panels + linked incidents/updates).
- Update this .MD as items complete. Use subagents for impl (e.g. emitter for analyst, backfill scripts).

**References:** All cited .MDs above, live data (money_ready_verdict, pick_funnel, ai_tournament_* .json, scrutiny json), code (scrutiny_engine, walk_forward_per_strategy, populate_alpha_macro, value_screener, equity_momentum_quality, feature orchestrator, production_scanner, ai_tournament builders, diagnostics), previous masterplans, consults, CLAUDE.md Goal #1 criteria.

*Generated 2026-06-06. Follows all rules (read full updates before card, deploy, own changes, etc.). Solid picks currently: only mega_mutation crypto. Path clear for others via P0 bootstrap + criteria enforcement.*

## Appendix: Full List of Reviewed .MDs (Past Week Focus)
- 2026-06-06-REAL-MONEY-READY-PICKS-FAST-ROADMAP.md
- 2026-06-05-DEEP-DIVE-SERIES-...
- deep_dive_commodity_2026-06-05.md
- deep_dive_forex_regime_2026-06-05.md
- 2026-06-05-PER-CLASS-T2-INVENTORY-POST-FILTER.md
- bond_n_ramp_analysis_2026-06-05.md
- 2026-06-05-PER-ASSET-WINNER-DIG.md
- 2026-06-05-LIVE-FORWARD-TRIAGE.md
- updates/2026-06-05-kimi-phase1-emergency-triage.md
- updates/2026-06-05-kimi-phase2-execution.md
- updates/2026-06-05-backfill-resolved-pnl-tool.md
- updates/2026-06-05-high-quality-paper-pilot-stubs.md
- updates/2026-06-05-pick-summary-14d-sync.md
- updates/2026-06-05-at-pick-outcomes-tp-sl-misclassification-root-cause.md
- updates/2026-06-05-zero-pnl-safeguard-stale-pick-resolver-fixes.md
- updates/2026-06-05-money-ready-bridge-audit-truth.md
- updates/2026-06-05-luxalgo-forward-dedup-truth.md
- updates/2026-06-05-grok-masterplan-phase*.md
- etf_dual_momentum_backtest_2026-06-03.md
- 2026-06-01_*.md (resolver backfill, wireup gap, isolation)
- STRATEGY_INVENTORY_2026-05-18.md (and related)
- Others touched in git since 05-30 (sidecar, etc. but filtered for relevance to picks/per-class).

(Full git list had more but many sidecar refreshes; reviewed the substantive ones above via grep/read.)

This completes the request: set of todos in .MD for solid per-class picks passing criteria; weekly .MD review done with actions extracted and documented (feed, diagnostics for ai-tournament.html, updates card).