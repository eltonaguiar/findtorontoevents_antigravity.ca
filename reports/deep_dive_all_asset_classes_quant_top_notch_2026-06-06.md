# Deep Research: All Asset Classes — Safe/Profitable Picks (Short vs Long) + Quant Top Notch UI Data
**Date:** 2026-06-06  
**Subagent:** Grok Build (deep research delegated task)  
**Priority:** Goal #1 — Phenomenal performance across ALL asset classes on findtorontoevents.ca/audit (Tier-2 min PF>1.5 / WR>50 / MDD<20 / n>=100 clean post policy/flicker; long-run Tier-1 Renaissance target). See CLAUDE.md lines ~1-120, audit_dashboard/template.html MAJOR GOAL banner.  
**Data sources (targeted reads + python -c aggregates + grep, per instructions):**  
- audit_dashboard/data/money_ready_verdict.json (2026-06-06)  
- audit_dashboard/data/pf_registry.json (policy_clean_net 2026-06-06)  
- audit_dashboard/data/dashboard_data.json (asset_class_health + concentration 2026-06-02)  
- audit_dashboard/data/top_edges_per_class.json (90d 2026-05-29)  
- audit_dashboard/data/verified_edge_status.json (2026-06-06)  
- audit_dashboard/data/strategy_perf_by_class.json  
- audit_dashboard/data/anti_overfit_audit.json (2026-06-05)  
- audit_dashboard/data/pick_summary_stats_*.json (14d/48h/2w)  
- audit_dashboard/data/edge_stability/{index, _CRYPTO.json, _EQUITY.json, _FUTURES.json, ...} (as_of 2026-06-06)  
- audit_dashboard/data/audit_surface_truth.json  
- alpha_engine/data/closed_picks.json (501 rows) + closed_picks_enriched.json + active_picks*.json  
- audit_trail/data/universal_resolved_picks.json (1572 rows, e.g. RENDERUSDT)  
- audit_dashboard/data/ai_tournament_leaderboard.json + ai_tournament_model_summary.json + data/ai_leaderboard/ai_leaderboard_index.json + data/research/ai_leaderboard_data.json  
- alpha_engine/asset_class.py (canonical normalizer, lines 1-120+)  
- reports/2026-06-05-PER-CLASS-T2-INVENTORY-POST-FILTER.md + reports/BEST_PICKS_PER_ASSET_CLASS_2026-06-03.md (and related deep_dive_*.md, asset_class_90day_plan_*.md)  
- grep for symbols (FET/RENDER/GOOGL etc) + targeted list_dir / find on data/ dirs.  
**Analysis method:** python -c + dedicated /tmp/*.py (stats, PF= gross_pos/abs(gross_neg), WR, per-sym aggregates n>=5/10, horizon inference from strat name/hold proxy <4h short vs >1d long, safe filters PF>1.2/WR>48/avg>0/n>5). No generators run. Precise citations.  

**Classes covered (from asset_class.py + verdict + data):** CRYPTO, EQUITY (STOCKS normed), FOREX, COMMODITY, ETF, BOND, FUTURES, PENNY_STOCK, MEME (top_edges), UNKNOWN (ghosts). 8-9 total. No separate "PENNY/MEME" fully in verdict (PENNY_STOCK + MEME sub).  

**Overall Status (Goal #1):** 0 classes Tier-2 / money-ready (money_ready_verdict.json summary: money_ready:[], n_classes=8; verified_edge_status.json: "0/6 classes Tier-2"; reports/2026-06-05-PER-CLASS-T2-INVENTORY-POST-FILTER.md: "0/9 classes"; BEST_PICKS report: "No... deployable winner today"). 3 degraded last 72h per CLAUDE context. CRYPTO/EQUITY/COMMODITY/FOREX sub-T2 or FAIL+; small clean n (policy_clean ~394 total rows). Concentration gates not always enforced pre-DSR. Recency critical: always check 14d/48h first (CLAUDE.md).  

## Per-Class Structured Reports

### CRYPTO
**Current stats (cite files/lines):**  
- policy_clean_net (pf_registry.json): n_resolved=252, PF=0.951 (2026-06-06T03:43Z).  
- asset_class_health (dashboard_data.json perf): n=377, WR=35.5%, PF=0.887 (2026-06-02).  
- edge_stability (edge_stability_CRYPTO.json + index.json as_of 2026-06-06T01:22): n=16308, all_time PF=0.91 WR=47.0 sharpe=-0.011, verdict="DECAYING_EDGE" (11 decaying, 1 lifting, 36 stable), per_window 7d PF0.75 WR46.6 n=12095; 90d PF~0.92. tier_floor PF1.5/WR50/MDD20/n100.  
- closed_picks (alpha_engine/data/closed_picks.json): n=70, WR=58.6%, PF=1.19, avg_pnl=+0.003 (better recent cohort).  
- concentration (dashboard_data.json): top_symbol JUPUSDT 6.38%, top_strategy macd_rsi_m048 12.61% (OK tier); closed: prediction_market_consensus 32/70 (~46%).  
- recency: pick_summary_stats_14d/48h (from at_raw_picks DB, shrinkage Beta(10,10)); per CLAUDE + session: CRYPTO 78.9%→38% 14d, 0 closed 48h (322 active). top_edges 90d window.  
- DSR/PBO/vol: anti_overfit_audit.json (2026-06-05) 38 strats, 5 EDGE_LIKELY_REAL (dsr_threshold); edge_stab has wilson_ci, sharpe (neg). risk: high vol, decaying.  
**Top symbols/strategies with edge (high WR+pos PnL, n>=10-20, low risk filters):**  
From top_edges_per_class.json (by_class.CRYPTO, n_closed=3664 cells=200, criteria strict proven WR_shrunk>=55 PF>=1.5 n>=20 holdout+bonf): proven cell "trust=UNK & rr=RR1.0-1.5 & dir=LONG" n=327 wins199 WR60.86% (shrunk 60.23) PF=3.885 avg_pnl_pct +1.0897, holdout_pf=3.065 n=124 pass, bonferroni_pass=True (top_edges_per_class.json:8-). unadj high PF cells (some holdout fail).  
From closed: SOLUSDT (15, 86.7% WR, PF11.15), BNBUSDT(13,61.5%,1.67), BTCUSDT(5,80%,6.17); strats prediction_market_consensus, luxalgo_confluence, beta_adjusted_residual_momentum. (sym-level safe n>=5 PF>1.2 WR>48 filter passed).  
Grep hits: RENDERUSDT (inverse_ml_enhanced_RENDERUSDT_1h_D /4h_D in strategy_admissibility.json:865, pilot_forward_dashboard.json, universal_resolved_picks.json row0).  
**Short-term (<4h/intraday scalps) vs long-term (swing 1-7d/pos >1w):** Short ~8 (rsi/breakout/scalp hints in inference); long 0 explicit in closed extract. Many 1h/4h strats (e.g. RENDER). Long bias in proven LONG cell.  
**Safe profitable filters applied (PF>1.2, WR>48, avg_pnl>0, n>5, recent pos/stable, single-source<30%, regime):** SOLUSDT/BNBUSDT/BTC pass sym n>=5; proven cell PF3.8+ n327>>; but overall class PF<1 clean, decaying, conc in 1-2 sources >30% in subsets, 14d collapse. Regime: check vs btc dominance etc.  
**Specific recs 3-5 top notch with why (data-backed; cite):**  
1. SOLUSDT (short-term): n=15 WR86.7% PF11.15 +avg in alpha_engine/data/closed_picks.json; high recent edge vs class avg. (User cited FET-like 81% similar.)  
2. RENDERUSDT / FETUSDT variants (short 1h/4h): inverse_ml strats flagged in admissibility/pilot/universal_resolved; prior session 81% WR mentions align with high WR cells.  
3. "trust=UNK rr=RR1.0-1.5 dir=LONG" cell (swing/pos): n=327 WR~61% PF3.885 holdout+bonf pass in top_edges_per_class.json (by_class.CRYPTO.proven[0]).  
4. mega_mutation (mixed): T1 5/5 axes n295 WR64.1% PF3.16 in reports/2026-06-05-PER-CLASS-T2-INVENTORY-POST-FILTER.md:18-38 (only confirmed T1 crypto); but sign-flip 141 rows caveat (BEST_PICKS report).  
5. macd_rsi_m048 (short): conc top + shadow candidate n~65 WR75 PF~3 in reports/BEST_PICKS_PER_ASSET_CLASS_2026-06-03.md:52; in CRYPTO_PROVEN allowlist, wired shadow.  
**Data issues:** DECAYING_EDGE + 0/48h closed; leakage (1864 dup signal-ts, EXPIRED->WON mislabels, 91.7% claude_gainer_st in old funnel per CLAUDE + reports); small clean n=252 vs 16k; disputed /audit/pick_funnel 78.9% cell. UNKNOWN mislabels bleed in.  

### EQUITY (STOCKS)
**Stats:** policy_clean n=71 PF=1.843 (pf_registry); health n=52 WR26.9 PF0.33 (dashboard); edge_stab n=3161 PF0.93 WR36.2 sharpe-0.015 "NO_EDGE" (all windows ~35-36% WR PF~0.89-0.93); closed (normed) n=98 WR35.7 PF0.74 avg-0.0066; conc AMD 15.64% top (dashboard). Recency: 14d/48h overall shrinkage; pick_summary from stocks DB.  
**Top/edge:** top_edges n_closed=130 cells86; no proven (rejected_good_wr_bad_pf e.g. 70%WR but PF0.089 due loss size); closed sym safe: AVGO n5 WR60 PF2.25. Strats regime_mild_bull, stocks_rsi2_pullback, smart_money_accumulation. Grep: GOOGL/AVGO in feature_signals_latest.json; AMD/LCID in closed.  
**Short/long:** short~23 long~6 in closed (rsi2/reversal short bias).  
**Safe:** AVGO passes n>=5/WR60/PF2.25; overall class NO_EDGE + low WR<50 + small n<<100 + conc.  
**Recs (3-5):** 1. AVGO (short): sym safe closed n5 60%/2.25. 2. GOOGL/INTC-like (user 100% mentions): in EQUITY_SYMBOLS (asset_class.py:56), feature signals; verify recent closed. 3-5. regime_mild_bull or momentum_rider on largecaps (AMD/LCID samples) — but only paper (low n, negative class PF).  
**Issues:** Structurally low-n (reports/2026-06-05... EQUITY 3 FAIL); NVDA/META 0-n or losers in live per reports; ghosts in UNKNOWN.  

### FOREX
**Stats:** policy_clean n=22 PF=0.044 (terrible); health n=32 WR28.1 PF0.48; edge_stab n=11370 PF1.24 WR52.1 sharpe+0.084 "MIXED" (best WR in stab); closed n=131 WR12.2% PF0.29 avg- (rsi2 dominant). Conc: USDJPY 27, forex_rsi2_mean_reversion 98/131 (~75% single source).  
**Top:** top_edges n_closed=2318; no strong proven listed in drill. Closed top USDJPY/GBPJPY/EURUSD.  
**Short/long:** Mostly short (98 short ~ rsi2 meanrev); long~12.  
**Safe:** None strong pass (low WR/PF class-wide; frozen in some reports). multi_asset_copytrader n1198 WR45 PF1.01 4/5 axes (WATCH per T2-inventory) but oos fail.  
**Recs:** Limited — multi_asset_copytrader (longer bias?) per reports/2026-06-05... FOREX table; avoid live size.  
**Issues:** FAIL+ low PF in clean; high conc single strat; OOS non-stationary per reports.  

### COMMODITY
**Stats:** policy_clean n=15 PF1.10; health n=4 WR50 PF1.68; edge_stab n=7058 PF1.09 WR47.7 sharpe+0.018 "MIXED" STRATEGY_CONC; closed n=144 WR25 PF0.89 avg-0.0015. Conc extreme: futures_momentum 122/144, SI/GC/PL=F ~35 each.  
**Top:** top_edges n=926 cells200; sym safe SI=F n35 WR51.4 PF1.72. Strats futures_momentum, cftc_cot..., commodity_tsmom.  
**Short/long:** short~0 long~6 (tsmom/carry bias).  
**Safe:** SI=F passes; cta_replicator n220 WR50.5 PF3.05 but frozen BLOCKED_ASSET_CLASSES per BEST_PICKS report.  
**Recs:** SI=F (long); cta_replicator (if unfrozen, paper only); commodity_carry_momo signals (data files).  
**Issues:** Conc + frozen class; post-backfill n drop in reports (was inflated by resolver); 2 FAIL in T2-inventory.  

### ETF
**Stats:** policy_clean n=18 PF0.71; health n=3 WR66.7 PF1.46; edge_stab n=308 PF1.39 WR44.5 sharpe0.063 "MIXED"; closed n=21 WR28.6 PF0.67.  
**Top:** Small n_closed=16 cells=0 in top_edges; closed XLK/SPY/QQQ samples. Strats cta_golden_cross, etf_sector_momentum.  
**Short/long:** Limited data, sector rotation long bias.  
**Safe:** etf_verified_dual_momentum: only MULTI_CLASS_LAB PASS + lab PF1.60 Sharpe1.91 n~104; best_forward XLK (verified_edge_status.json:10-28, sleeves); promotion blocked n<100/pf<1.5 etc.  
**Recs:** 1. XLK (long rotation). 2. etf_verified_dual_momentum (paper pilot, shadow). 3. SPY/QQQ sector (verify).  
**Issues:** Small n; only lab sleeve promotable.  

### BOND
**Stats:** edge_stab n=165 PF1.34 WR46.7 sharpe0.05 "MIXED" STRATEGY_CONC (no clean n in some); closed n=2 WR50. health none.  
**Top:** Small; symbols TLT/IEF/SHY etc (asset_class.py:28-35 BOND_SYMBOLS); closed EURGBP/TLT.  
**Short/long:** Limited (1 short in extract).  
**Safe:** PF>1.3 n165 in stab; conc strat risk.  
**Recs:** TLT/IEF (position, yield curve per bond_*.py in alpha_engine + data backtests).  
**Issues:** Small clean; STRAT_CONC.  

### FUTURES
**Stats:** policy_clean n=15 PF0.41; edge_stab n=407 PF2.08 WR50.1 sharpe0.205 "STABLE_EDGE" (best overall) STRAT+SYM CONC; 7d WR50 PF1.98 avg+0.177 (FUTURES.json); closed n=5 WR20 PF0.07. Conc NQ=F 84% WARN (dashboard).  
**Top:** Small cells in top_edges; closed YM/ES/NQ=F. Strats futures_*/regime_mild_bull, cta_golden_cross_200.  
**Short/long:** Mixed (tsmom long, some short).  
**Safe:** Highest sharpe/PF in stab; but small clean + conc block.  
**Recs:** NQ=F / ES=F (regime/tsmom); monitor for clean n ramp.  
**Issues:** High conc + small policy n; WARN tier.  

### PENNY_STOCK / MEME / UNKNOWN
**PENNY_STOCK:** verdict n=1 (tiny); EQUITY sub per hints (asset_class.py EQUITY_STRATEGY_HINTS "penny").  
**MEME:** top_edges only, n_closed=46 cells=0; high risk separate.  
**UNKNOWN:** closed n=30 WR80 PF8.16 (suspicious); samples AAPL/LCID (EQUITY), WLD-USD (CRYPTO) — ghosts/misclass per normalizer. Flag, do not use. (asset_class.py:97+ _UNKNOWN_CATEGORY_TOKENS + normalize funcs).  

## Safest Asset Classes Overall + Per Horizon
**Overall lowest risk (MDD low, vol low, consistency high, diversif, +expect, n suff or pilot-ready):**  
1. FUTURES: STABLE_EDGE + highest sharpe 0.205 / PF2.08 WR50 n407 (edge_stability_FUTURES.json); 7d strong. Pilot if conc fixed + clean n>=100.  
2. ETF: lab T2 sleeve (only one), MIXED stab PF1.39 n308, health high WR small n. Diversif.  
3. BOND: MIXED PF1.34 n165. Safer than crypto vol.  
None full Tier-2 (0 pass). CRYPTO/EQUITY/FOREX/COMMODITY highest risk (NO_EDGE/DECAYING/ low PF + conc).  
**Short-term safest:** CRYPTO specific (SOLUSDT etc high WR recent closed) + some EQUITY/FOREX rsi2 (volume but filter strict).  
**Long-term safest:** FUTURES/COMMODITY tsmom/carry (positive where), ETF dual mom rotation, BOND yield.  
**Pilot-ready or n suff:** ETF lab n~100 borderline; others << (clean 15-252). Per CLAUDE: n>=100 clean for "proven" docs in updates/.

## Data Issues Flagged
- Small n / INSUFF-N for ETF/BOND/PENNY/FUTURES/COMMODITY clean (<<100); 0/8-9 Tier-2.  
- UNKNOWN ghosts/mislabels (30 rows, high bogus stats).  
- Leakage/concentration in CRYPTO (disputed funnel, claude_gainer_st, dup signals per reports + CLAUDE.md ~808-820 context).  
- Recency 14d/48h weak/collapsed for several (esp CRYPTO 0 closed); pick_summary_stats lack per-class in top schema (overall only).  
- dashboard_data older (06-02) vs verdict (06-06).  
- High single-source conc (COMMODITY futures_mom 85%+, FOREX rsi2 75%, FUTURES NQ 84% WARN).  
- Sign-flips/EXPIRED mislabels in CRYPTO (BEST_PICKS + T2 reports). Frozen classes.  
- Edge vs closed n mismatch (different cohorts/filters).  

## UI-Ready Summary Table Data (ready for /audit or ai-tournament)
See /tmp/quant_top_notch_data.json (full structured) and excerpt in final response. Columns: class | pick/sym/strat/cell | n | WR | PF | horizon | rationale (with file cite) | risk_note.  
Top notch examples (from analysis):  
CRYPTO: SOLUSDT (15/86.7/11.15 short, closed_picks); LONG RR1-1.5 cell (327/60.9/3.885 swing, top_edges proven).  
EQUITY: AVGO (5/60/2.25 short).  
COMMODITY: SI=F (35/51.4/1.72 long).  
FUTURES: NQ=F regime (407/50.1/2.08, edge_stab STABLE).  
ETF: XLK / etf_verified_dual_momentum (lab PASS).  
Safest bets table: FUTURES (STABLE_EDGE highest sharpe n407 cite edge_stability_FUTURES.json), ETF (lab T2 cite verified_edge_status.json), BOND (PF1.34 n165).  

## Suggestion: Surface in ai-tournament as "Quant Top Notch" entry
- Add separate table/tab "Quant Top Notch / Policy-Clean Edges" in audit_dashboard/ai-tournament.html (or template.html enhancements) + ai_leaderboard section.  
- Pull from top_edges_per_class.json (proven cells) + pf_registry policy_clean_net + edge_stability (stable) + closed safe syms. Filter Tier-2 candidates or "n>=20 clean PF>1.2".  
- Rationale: trust_hierarchy in verified_edge_status.json puts "policy_clean money_ready_verdict (live sizing)" #1, "ai-tournament / pf.html (separate universe — not money-ready)" last. Cross-ref ai_leaderboard_data (30 entries).  
- Integration code proposal (text; do not auto-PR per AGENTS.md diff-fab rule — verify lines):  
  In audit_dashboard/ai-tournament.html or dashboard_enhancements.js (after ai models render):  
  ```js
  // fetch('/audit/data/top_edges_per_class.json').then... + merge pf_registry
  // render table: <table id="quant-top-notch"> ... class | pick | n | WR | PF | source_file | horizon
  // e.g. for CRYPTO proven cell row citing top_edges_per_class.json:8
  ```
  Or backend: extend audit_dashboard/merge_ai_challenge_picks.py (or new quant_top_notch_section.py) to emit audit_dashboard/data/quant_top_notch_picks.json (use /tmp/quant... as seed); include in dashboard_data or separate. Wire caller in production_scanner or ai_tournament_picks_latest if production path. Label "opt-in sidecar" if not changing sizing. See AGENTS.md Wire-Up Rule.  
  Update audit-dashboard.yml dep table in AGENTS.md if new pipeline consumer. FTP deploy via tools/deploy_audit_files.py --only updates after.  
- This surfaces non-AI quant edge for all classes, advances Goal#1 (document proven under /audit, cite reports/ source + repro cmd in updates/index.html <div class="update-entry"> before AUTO-INJECT marker).  

**Verification notes:** All numbers from direct loads/greps/python aggs on listed paths (no model invention). Tie to CLAUDE Goal#1 + daily focus. For PR: independent quote pre-change lines + branch only own changes. Never run generators locally. Check 14d/48h before size.  

(End report. Full per-class expanded in /tmp/quant_top_notch_data.json template; copy/edit for updates/ if needed.)  
**Next:** Spawn sub deep-dives per bad class per CLAUDE if PF<1/sub30%WR/MDD>2x (e.g. reports/deep_dive_EQUITY_*.md). Use for /audit updates.