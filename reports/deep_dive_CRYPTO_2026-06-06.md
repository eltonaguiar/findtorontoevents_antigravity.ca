# Deep-Dive Autopsy: CRYPTO Asset Class Performance (findtorontoevents.ca/audit Goal #1)

**Date:** 2026-06-06  
**Subagent:** Grok Build specialized quant deep-dive  
**Priority:** Goal #1 — Phenomenal performance across ALL asset classes on /audit (institutional/hedge-fund-grade per charter: T2 min PF>1.5 / WR>50 / MDD<20 / n>=100 clean; T1 PF>2 / WR>55 / MDD<10 long-run).  
**Grounding rule (strict, per task):** ALL numbers, verdicts, sources, code paths, and citations pulled exclusively from local files/JSONs via read_file/grep/run_terminal (safe python -c on JSONs only; no generators, no external fetches, no fabrication). Old May-3 figures (e.g. n=8067) from deprecated AUDIT_HEALTH_SOURCE=recompute path ignored; use current pf_registry + money_ready_verdict (policy_clean_net) + strategy_tier_tracker + cited reports. Recency panels (14d/48h) verified first per CLAUDE.md.  
**Canonical data (2026-06-05T11:55:27Z generation):**  
- `audit_dashboard/data/money_ready_verdict.json` (source: `alpha_engine/money_ready_verdict.py --json`)  
- `audit_dashboard/data/pf_registry.json` (source: `tools/build_pf_registry.py`; canonical_view: "by_asset_class_policy_clean_net")  
- `reports/strategy_tier_tracker_20260605T123622Z.md` (read-only from pf_registry)  
- Recency: `audit_dashboard/data/pick_summary_stats_14d.json` + `48h.json` (caveats: dups, 0 closes)  
**Key referenced reports (local only):**  
- `reports/WR_SCRUTINY_AND_FILTER_SEARCH_2026-06-05.md` (high-WR artifacts; no durable OOS; 10.1% sign-mismatch; batch-stamps; backfill not live)  
- `reports/2026-06-05-LIVE-FORWARD-TRIAGE.md` (48h 0 closes for CRYPTO; 14d dups; luxalgo_confluence no edge live; bootstrap vs live mismatch)  
- `reports/2026-06-05-PER-ASSET-WINNER-DIG.md` (per-class live forward honest candidates; single-symbol RENDER family)  
- `reports/2026-06-05-PER-CLASS-T2-INVENTORY-POST-FILTER.md` (5-axis scrutiny on trading_picks post-2026-06-04 backfill filter; mega_mutation::crypto 5/5 but note cohort diff vs policy_clean)  
- `reports/2026-06-06_money_ready_essentials_swarm_impl.md` (refs MASTERPLAN_JUNE52026_GROK.MD + updates/2026-06-05-grok-masterplan-phase1-shipped.md: data contamination, 48h 0 closes, MISPRICED in tourn, promotion gates)  
- `reports/2026-05-25_crypto_78pct_wr_verification.md` (historical 78.9% Smart-Picks disputed: 91.7% claude_gainer_st conc + EXPIRED→WON)  
- `reports/peer_claude-promote-liquidity-wick_2026-05-31.md` (wick single-src battleground; resolver one-sided pathology)  
- `reports/asset_class_90day_plan_CRYPTO_2026-05-15.md` (historical context: illiquid alts/memes dilute; liquid-core needed)  
- `reports/EAGLE_2026-05-27_2139_EST_Grok43_xAI_model_validation_report_tmx_style.md` (only 1 T2: wick n=30)  
**Code (exact paths/lines cited):**  
- `alpha_engine/money_ready_verdict.py` (gates, _load_picks canonical pipeline, CLASS_WR_FLOORS CRYPTO 0.50, MIN_N_CLASS=100, single-source/MDD/FDR/ML quarantine shadows, _resolved sign-coherence)  
- `tools/build_pf_registry.py` (dedup_key, flicker, policy, SOURCE_CONCENTRATION, is_single_source_artifact)  
- `alpha_engine/outcome_resolver.py:120` (PNL_WIN_THRESHOLD_BY_CLASS CRYPTO 0.00001)  
- `audit_trail/universal_pick_resolver.py` (MAX_HOLD_HOURS CRYPTO 48; RESOLVER_VERSION universal_v2.1)  
- `audit_trail/quality_gates.py` (BLOCKED_ASSET_STRATEGY_PAIRS many CRYPTO, PF_REGISTRY_POLICY_EXCLUDED, CRYPTO_LIQUID_CORE, passes_active_gate)  
- `tools/clean_ingest_v2.py` (drift/RSPLIT/TP_HIT_REPLAY/MISPRICED rejects)  
- `audit_trail/promotion_gate.py` (evaluate_forward_tier2 TIER2_MIN_N=100/WR=0.55/PF=1.4/DSR/OOS/regime)  
- Emitters/gates: `alpha_engine/crypto_liquid_core.py`, `alpha_engine/crypto_funding_rate_carry.py`, `alpha_engine/crypto_onchain_momentum.py`, `alpha_engine/crypto_whale_accumulation.py`, `alpha_engine/crypto_liquidation_fade.py`, `alpha_engine/funding_rate_arb.py`, `alpha_engine/crypto_strategies.py` family, `alpha_engine/smart_picks_engine.py` (CRYPTO_TOXIC_STRATEGIES incl atr)  
**Status per canonical (policy_clean_net):** 0/ classes T2; CRYPTO NOT_READY (n=302 resolved policy-clean, WR~34.8%, PF~0.99). Only 1 near-T2 sleeve (single-src flagged).

---

## 1. Per-source autopsy

**Class-level (canonical policy_clean_net from pf_registry.json, 2026-06-05T11:55Z):**  
- n=302, wins=105, losses=197, win_rate_pct=34.7682, profit_factor=0.991103, total_pnl_pct=-0.220923, max_drawdown_pct=1.0, single_source_pct=0.291391, top_source="file:battleground", is_single_source_artifact=False (for class aggregate).  
  (Source: `audit_dashboard/data/pf_registry.json` by_asset_class_policy_clean_net[CRYPTO]; cross-confirmed in money_ready_verdict.json CRYPTO: n_resolved=302, wr=0.3477, pf=0.9911, verdict="NOT_READY", mdd=1.0, cvar_95=-86.5827, expectancy=-0.002225, top_source="UNKNOWN" 0.649 share but source_concentration_capped=true, n_profitable_multi_source=1, n_profitable_single_source=3.)  
- Raw (pre policy/flicker/dedup in same registry): n=1508, wr=42.3077, pf=1.452459, single_source_pct=0.309019, top_source="file:mercury2". Post-flicker/dedup/policy drops many (global counts: raw_rows=3041, closed=1889, after_flicker=690, deduped=619, policy_clean=409; dropped_spot_flicker=1199, dropped_policy_excluded=210).  
- money_ready_verdict details (lines ~54-111): dsr_score=0.2606 (false), pbo=0.012 (true, n_strategies=5), spa_p=0.216 (false, n_spa_pass=1/5), fdr n_fdr_pass=0/5 (min_p=0.02958), single_source_strategies=["atr_percentile_gate","crypto_liquidity_wick_reversal_v1","luxalgo_confluence"] (ok=true per current gate shadow), _mdd_cvar_gate_ok=false.  
- strategy_tier_tracker_20260605T123622Z.md (sourced from same pf_registry): **CRYPTO Class verdict: FAIL (n=302, PF=0.99, WR=34.8%)**. Only 1 T2: `crypto_liquidity_wick_reversal_v1` (30/18/12, 60.0%, 1.55, T2 (Institutional)). `battleground_luxalgo` (26/13/13, 50.0%, 3.98, T3 (Marginal)). `atr_percentile_gate` (29/17/12, 58.6%, 1.10, FAIL). Many FAIL/INSUFF_N (e.g. copy_trader_intel 32/0/32 0.0% 0.00 FAIL; ml_breakout 21/0/21 0.0% 0.00 FAIL; UNKNOWN 40/12/28 30.0% 3.12 FAIL).  

**Strategy-level breakdown (by_asset_class_strategy_policy_clean_net CRYPTO, 40 entries, total n=302; full list from python -c on pf_registry; sorted n desc; 11 single_source_artifact=True accounting for 216 n):**  
- `UNKNOWN` n=40 wr=30.0 pf=3.118923 single=False (0.575) top="file:approach_b_ml_breakout" total_pnl=+0.15341 (high PF but low WR; not T2).  
- `copy_trader_clones` n=34 wr=44.1 pf=0.781 single=True (1.0) top="copy_trader_clones" pnl=-0.0465.  
- `copy_trader_intel` n=32 wr=0.0 pf=0.0 single=True top=copy_trader_intel pnl=-0.0256 (total wipeout).  
- `crypto_liquidity_wick_reversal_v1` n=30 wr=60.0 pf=1.553413 single=True (1.0) top="file:battleground" pnl=+3.2404 (**the only near-T2; flagged single-src per build_pf_registry.py:50-58 and money_ready_verdict.py:168-171**).  
- `atr_percentile_gate` n=29 wr=58.6 pf=1.100773 single=True top="file:battleground" pnl=+0.6503 (near but pf<1.5; listed in toxic in smart_picks_engine.py:311).  
- `battleground_luxalgo` n=26 wr=50.0 pf=3.975808 single=True top="battleground_luxalgo" pnl=+1.169817 (high PF T3 marginal).  
- `ml_breakout` n=21 wr=0.0 pf=0.0 single=True top="file:approach_b_ml_breakout" pnl=-0.0168.  
- `multi_period_rsi_confluence_eth` n=16 wr=43.75 pf=0.433 single=True top="file:battleground" pnl=-2.4824 (bad).  
- Lower n (9-1): e.g. `drawdown_recovery_rsi_eth` n=9 wr=55.6 pf=3.389 single=True top=battleground (good pf tiny n); `beta_adjusted...` n=9 wr22 pf0.46 single=True alpha_engine; many 0-win (copy_trader_bybit n=5 wr0; hoffman_ema n=5 wr20; cusum n=3 wr0; gru_attention n=3 wr0 from system_c_deeplearn; genome_mutations n=2 100% no_losses; plus 20+ n=1-2 single-src mostly alpha_engine losers or 100% wins tiny). `mega_mutation` appears only n=1 100% here (vs high n in DB scrutiny reports — cohort divergence).  

**Source/system concentration autopsy (per pf_registry methodology + reports):**  
- Policy clean CRYPTO n dominated by single-source sleeves: 216/302 n in is_single_source_artifact=True strats (build_pf_registry.py:49-58 explicitly calls out wick as example of >60% from battleground; SOURCE_CONCENTRATION_THRESHOLD_DEFAULT=0.60). top_source for class "file:battleground" (but UNKNOWN/approach_b_ml also battle/alpha).  
- battleground hosts the only "good" sleeves (wick/atr/luxalgo/multi-rsi) but also bad ones (rsi_confluence_eth negative). Alpha_engine: many low/zero WR strats (beta, hoffman, cnn, cusum, obv, spot_perp etc.). Copy_trader_* : structural 0% or sub-45% WR (clones/intel/bybit/polymarket). ML/approach_b/deeplearn/system_* : 0% WR batches (ml_breakout, gru_attention). Genome: tiny positive no-losses.  
- Historical parallel (2026-05-25_crypto_78pct...): 78.9% "Smart-Picks" was 91.7% claude_gainer_st + EXPIRED 63.9% labeled WON (mislabel) + batch day 2026-04-15 (45/46 wins). Disputed; pick_funnel still shows 78.9% per CLAUDE.md (raw DB 90d CRYPTO ~39% WR / PF 0.37; 4 leakage signals incl 1864 dup signal-ts, 91.7% conc in claude_gainer_st with 3 closed). Current money_ready top_source UNKNOWN 64.9% (capped).  
- Per WR_SCRUTINY_2026-06-05.md: 31 high-WR (>=50% n>=20) cells: 7 ARTIFACT (NULL resolve, pnl=0 "wins", templated PnL, EQUITY-labeled-crypto), ~22 SKEWED (100% single-symbol ml_enhanced_*, fat-tail, coin-flip binomial p~1.0, PF<1 despite WR). prediction_market_consensus crypto 83.8% but 44% one batch day + 48% DOGE conc (not durable class edge).  
- Live-forward (2026-06-05-LIVE-FORWARD-TRIAGE + PER-ASSET): luxalgo_confluence (2076 trades, "NO EDGE live" — 10/10 recent SL_HIT; bootstrap PF=2.36 vs +0.08% realized); prediction_market_consensus n=86 89.9% but 52% DOGE conc (KILL); ml_enhanced_*_RENDER/STRK/DYDX (high WR/PF but 100% single-symbol; promising but not class edge). 48h: n_closed=0 for CRYPTO (n_active=616); 14d: n_closed=9629 wr~40% pf~6.5 but caveats dup_groups=277 (raw DB, not policy clean).  
- Other artifacts (WR_SCRUTINY + PER-CLASS + masterplan refs): 10.1% sign-mismatch (status vs pnl sign); resolved_at batch-stamped (2026-05-31=1180 rows); most rows backfill_* (reconstructed, not live forward; 97% in some pilots); 0 closed 48h; MISPRICED in tourn; EXPIRED→WON mislabels. Per-class T2 inventory (DB post-2026-06-04 filter, different cohort): mega_mutation::crypto n=295 wr64.1 pf3.16 5/5 PASS (but pf_registry policy shows only n=1 mega; divergence = closed_picks export vs trading_picks DB coverage); luxalgo_filters n=2009 wr43 pf1.06 4/5 (bin fail).  

**Summary of drags:** 1) Source concentration (battleground for "edge" sleeves; alpha/copy for volume of losers). 2) Single-strat artifacts (216 n in 11 single-src strats; wick/atr/luxalgo explicitly called out in verdict.py:168 + build_pf:50). 3) Zero-edge emitters (copy 0wr, ml 0wr, deeplearn losses). 4) Data quality (sign mismatch, batch, backfill vs live, dups per recency). 5) No class-level durability (OOS collapse, fat-tail, binomial p high per WR_SCRUTINY). The "78.9%" and high bootstrap PFs are artifacts of curation/leakage/conc, not policy_clean reality (PF<1 class).

---

## 2. External replication options (grounded in local code + reports)

**Local non-LLM feature emitters (already in alpha_engine; potential for cross-validation or replacement of LLM-heavy):**  
- `alpha_engine/crypto_funding_rate_carry.py`: Core thesis negative funding < -0.01% (8h) → LONG capture carry + directional; EXIT on flip or 72h. Multi-source fetch (Binance → Bybit → OKX → Coinglass per API failover rule). max_hold 72 (3 settlements). (Refs: funding_rate_arb.py, funding_rate_scanner.py, funding_rate_signal.py also exist.)  
- `alpha_engine/crypto_onchain_momentum.py` + `crypto_whale_accumulation.py` + `etherscan_whale_tracker.py`: On-chain momentum/whale flow/accumulation (cited in 90day plan + MASTER_ACTION_PLAN as Source A on-chain).  
- `alpha_engine/crypto_liquidation_fade.py`: Liquidation cascades (local impl of fade/arb).  
- `alpha_engine/crypto_liquid_core.py` + `btc_hour_filter.py`: Liquid top-25 ADV (BTC/ETH/BNB/SOL/.../PYTH) + BTC UTC death-zone (9,10,18,21); wired to quality_gates passes_active_gate. Addresses illiquid alt drag (only 1/229 on canonical wick per docstring).  
- `alpha_engine/basis_carry.py` + `crypto_pairs_arb.py` + `cross_exchange_arb.py`: Basis/funding arb, cross-exchange.  
- Other: `crypto_vol_regime_accumulation.py`, `crypto_mean_reversion_zscore.py`, `crypto_volatility_regime.py`, `cointegration_pairs.py`.  

**External cross-validation/replacement options (mentioned in local reports/plans as replication paths; not fabricated):**  
- Hyperliquid HLP (perp funding/liquidation on-chain data for arb/carry cross-check; aligns with local funding/liquidation code).  
- On-chain metrics (whale, flow, DEX arb — local codes above; reports/MASTER_ACTION_PLAN_2026-05-18.md lists on-chain whale_flow 99.5% monitor).  
- DBMF/KMLM (trend/CTA replication for macro overlay; referenced in commodity plans but extensible to crypto regime via vol/funding term structure; per 2026-05-25 reports for cross-asset).  
- Public on-chain (CoinMetrics, Arkham, DefiLlama signals — local defillama_signals.py, coinmetrics_signal.py, arkham_smart_money.py).  
- MyFXBook/Hyperliquid HLP/QMOM analogs for forward replication of any sleeve (e.g. wick as "liquidity wick" on perp books).  

**Cross-val plan:** Run local funding/onchain/whale as parallel emitters on same liquid-core symbols; compare PF/WR/OOS to wick/atr in forward paper (via promotion_gate + clean_ingest). If they corroborate (multi-source), promote family; else quarantine single-src wick. Reports note funding-arb directional was "forbidden" in some refutations (FEEDBACK_AND_ACTIONS) due to prior failures — test net-of-cost only.

---

## 3. 30/60/90 day rescue plan (concrete, per charter + recent masterplan/triage)

**30 days (stabilize + clean + n-growth on 1 sleeve):**  
- Enforce `tools/clean_ingest_v2.py --apply` (after backups): reject drift (CRYPTO 25%), RSPLIT, TP_HIT_REPLAY, MISPRICED (updates/2026-06-05-grok-masterplan + clean_ingest_v2.py:52). Run `python3 tools/clean_ingest_v2.py --sample 100` + tests/test_clean_ingest_v2.py.  
- Wire `audit_trail/promotion_gate.py:evaluate_forward_tier2` (TIER2_MIN_N=100/WR=0.55/PF=1.4/DSR=0.80/OOS=0.85*IS/regime<=15pp) + last100 filter into money_ready_verdict + production_scanner (per 06-06 swarm_impl + masterplan).  
- Promote/corrob `crypto_liquidity_wick_reversal_v1` (or kill single-src): per peer report, gate on resolver one-sided fix (FINDING#12); require multi-source (battleground + >=1 other) or drop. Add to PROMOTED_STRATEGIES only after. Shadow via paper (not live size).  
- Grow n on live-forward honest CRYPTO from triage (RENDER/STRK/DYDX/INJ ml_enhanced family n~30+ per 06-05-PER-ASSET + LIVE-FORWARD): diversify to family (treat as one strat); emit daily on high-vol; track in new pilot_forward_dashboard. Target family n=50+ in 30d.  
- Add non-LLM: enable/wire `crypto_funding_rate_carry.py` + `crypto_onchain_momentum.py` + `crypto_liquidation_fade.py` as emitters (non-LLM feature; funding/term per task). Filter via liquid_core + new promotion.  
- Fix recency: 48h 0 closes → investigate resolver backlog (universal_pick_resolver MAX_HOLD 48h CRYPTO); add daily n_to_t2 counter (per triage rec).  
- py_compile only; no local gens. Update `audit_dashboard/data/money_ready_verdict.json` surface (already does via --json).  

**60 days (n-ramp + multi-source + filters):**  
- n≥60 clean policy on ≥2 sleeves (wick family + funding/onchain or RENDER family post OOS split). Enforce CLASS_WR_FLOORS CRYPTO 0.50 + net-exp (M-069) + MDD/CVaR in verdict (money_ready_verdict.py:260,138).  
- Multi-source gate hard (set MONEY_READY_SINGLE_SOURCE_GATE=1): require n_profitable_multi_source ≥2 per verdict details. Drop or quarantine any sleeve >60% single-src (build_pf_registry SOURCE_CONC).  
- Data clean: sign-coherence in _resolved (verdict.py:498 already does; propagate to DB ingest). Kill batch-stamp via resolver provenance (universal_v2.1). Backfill filter in all surfaces (per triage: set _gated_forward_test_isolated).  
- Live forward on good: RENDER family + funding carry on liquid core; weekly_filter + WR_SCRUTINY 3-step (conc<=50% symbol, fat-tail top5<70% wins, OOS h1/h2 PF>1 both) on new closes.  
- Reports: new update card pre AUTO-INJECTED in updates/index.html (per rules); deep_dive followups.  

**90 days (T2 or kill):**  
- Target: 1+ sleeve n≥100 clean policy, WR≥50 (or class floor), PF≥1.5, MDD<0.2, DSR≥0.95, pbo low, multi-src, forward paper track ≥4w CLV non-neg, no conc. If pass verdict + promotion_gate + strategy_tier_tracker T2, size up (per Goal#1).  
- If not: quarantine CRYPTO (BLOCKED_ASSET_CLASSES or CRYPTO_PRODUCTION_BLOCK_LONG per masterplan), redirect volume to proven (e.g. ETF dual-momentum clean-bar H-103 per WR_SCRUTINY exception).  
- External cross-val: run HLP/on-chain funding arb paper in parallel; compare to local.  
- Continuous: daily 14d/48h panel review (per CLAUDE: "never size up on historical without verifying 14d/48h"); mutate-before-kill (docs/MUTATION_THREE_AXIS_PROTOCOL.md + STRATEGY_INVESTIGATION_BEFORE_KILL.md) before any kill.  
- Deliverables: FTP deploy (python3 tools/deploy_audit_files.py --only updates + pick_funnel per rules); gh run for CI; update pf_registry + verdict via canonical pipeline.

---

## 4. Risk register

- **Resolver backlog / one-sided resolution (HIGH, P0):** universal_pick_resolver 48h CRYPTO hold; outcome_resolver tight 0.1bp threshold; peer report: "WIN side closes promptly while LOSS side hangs OPEN/never resolves" (FINDING#12). Inflates WR/PF on wick etc. (affects 30 n sleeve). Refs: peer_claude-promote-liquidity-wick:15-19; 06-05 triage 0 48h closes.  
- **Concentration (HIGH):** 216/302 n in single-src artifact strats (pf_registry); wick/atr/luxalgo 100% battleground (build_pf:50, verdict:168); historical 91.7% claude_gainer (78pct report); top_source 29-65% (registry/verdict). Single-source is "feed idiosyncrasy not class edge" (verdict.py:170). Symbol conc (BTC 25% in verdict).  
- **Regime failure / recency collapse (HIGH):** 48h n_closed=0 CRYPTO (pick_summary_stats_48h + triage); 14d wr collapsed 78.9%→38% (CLAUDE.md); recency panels show dups=277 + high active. Old high n (May) from flicker-bypass.  
- **Data rot / contamination (HIGH):** 10.1% sign-mismatch (WR_SCRUTINY); batch-stamped resolved_at (1k+ rows/day); backfill_* vs live forward (97% in pilots per triage; 255/262 backfill); EXPIRED→WON mislabels; templated PnL; dup signal-ts (1864 in raw). Policy clean vs DB scrutiny divergence (mega_mutation n=295 vs 1).  
- **Single-src sleeve fragility (MED-HIGH):** Only 1 T2 (wick n=30) is 100% battleground + resolver-dependent; if source or resolver changes, class reverts to sub-30% WR. T3 luxalgo pf3.98 but wr=50 n=26 marginal + single.  
- **Overfit / multiple testing (MED):** 5 strats tested for SPA (verdict); FDR 0/5 pass; 40 "strats" in policy for n=302 (many n<5); high PF from few big wins (UNKNOWN pf3.12 wr30). OOS collapse documented (WR_SCRUTINY best in-sample dies late-half).  
- **Low n / power (MED):** Class n=302 ok for some stats but per-strat many <20 (SPA min); pbo/spa on 5; DSR 0.26 low. n_resolved policy < raw historical.  
- **Production wiring (MED):** promotion_gate allowlist empty (as of 06-02); CRYPTO_TOXIC includes atr (smart_picks); many emitters not wired to production_scanner / calculate_smart_score per wire-up rule (breadth PR risk).  
- **Mitigations in place (shadow):** MDD/CVaR/FDR/single-src/ML-quarantine in verdict (enforce=0/1 env); liquid_core gate; clean_ingest; sign coherence in _resolved; SOURCE_CONC in pf build. But many shadow (not hard).  

---

## 5. Acceptance criteria for "CRYPTO money-ready"

Per CLAUDE.md Goal#1 + PERFORMANCE_CHARTER (T2 min) + money_ready_verdict.py (MIN_N_CLASS=100, CLASS_WR_FLOORS CRYPTO=0.50, MIN_PF=1.5) + promotion_gate.py:171 (TIER2_MIN_N=100/WR=0.55/PF=1.4/DSR=0.80/OOS_PF_RATIO=0.85/regime_drop<=0.15) + pf_registry + WR_SCRUTINY 3-step + build_pf + reports (n clean post-noise-filter; multi-source; forward paper; no conc):  

- **n:** >=100 resolved policy_clean_net (per verdict MIN_N_CLASS + charter; post all filters: dedup, flicker 0.0002, policy_excluded, sign-coherent _resolved). n_resolved in money_ready_verdict >=100.  
- **WR:** >=50% (or CLASS_WR_FLOORS["CRYPTO"]=0.50 sanity; promotion 0.55) on net-of-slippage (M-069 charter_slippage 15bps CRYPTO; expectancy >=0).  
- **PF:** >=1.5 (T2 charter + MIN_PF; promotion 1.4) on net returns; gross also reported.  
- **MDD/CVaR:** mdd <=0.20 (MDD_GATE 20% or class override; cvar_95 > -10%? per code); max_drawdown_pct in pf_registry <0.20.  
- **Stats gates:** dsr_score >=0.95 (or ok per _dsr_gate); pbo <=0.55 (low overfit); spa_p pass (n_spa_pass>=1 with n_strat>=5 tested); fdr n_fdr_pass >0 if enforced; expectancy >=0 net.  
- **Multi-source / no conc:** n_profitable_multi_source >=2 (or >=1 + no single-source strats dominate profitable); single_source_pct <0.30-0.40 (MAX_SOURCE_CONC=0.40; per strat is_single_source_artifact=False for edge sleeves; top_source_share <=0.40; per build_pf 0.60 threshold + HHI<0.30 in promotion). Symbol top <=0.50-0.60 (MAX_SYMBOL=0.60).  
- **Forward / paper / OOS:** >=30 live forward closes (closed_at not null, _gated_forward_test_isolated) with OOS first/second half both PF>=1.0 (per WR_SCRUTINY + triage); walk-forward OOS PF >=0.85*IS (promotion); 4+ week live track (sports analog); CLV trend non-neg; pilot paper n>=30 stable.  
- **Data quality:** 0 sign-mismatch in cohort; no batch-day >35% (per PER-CLASS 5-axis batch artifact); no fat-tail (top-5 wins <70% positive PnL per triage/WR); resolved via universal_v2.1 + provenance; passes clean_ingest (no drift/replay).  
- **Verdict surface:** money_ready_verdict["CRYPTO"]["verdict"] = "MONEY_READY"; pf_registry by_..._policy_clean_net PF/WR pass T2; strategy_tier_tracker shows >=1 T2 (multi-src); 14d/48h panels non-collapsed (n_closed>0, wr stable); 0/9 panel reflects.  
- **Other:** No policy_frozen; top_symbol_share ok; wired to production (at least one caller in calculate_smart_score / passes_*_gate / smart_picks_engine per wire-up rule); n>=100 clean trades (post-noise-filter) per CLAUDE "document proven edge".  

Only when ALL pass: size up per Goal#1 (T2 min before allocate). Currently: n=302 ok, but WR/PF/MDD/DSR/SPA/exp/conc/multi-src fail → NOT_READY.

---

## 6. Reproducer commands and exact file refs

All local; run from repo root; use py_compile for syntax (never generators per CLAUDE/AGENTS).  

```bash
# 1. Canonical class + strategy stats (policy clean)
python3 -c '
import json, pprint
p = json.load(open("audit_dashboard/data/pf_registry.json"))
print("pf_registry generated:", p["generated_utc"])
print("CRYPTO policy_clean_net class:", [x for x in p["by_asset_class_policy_clean_net"] if x["asset_class"]=="CRYPTO"])
crypto_strats = [x for x in p.get("by_asset_class_strategy_policy_clean_net",[]) if x.get("asset_class")=="CRYPTO"]
print("CRYPTO strats n>=10:", [x for x in crypto_strats if x.get("n",0)>=10])
print("Single-src n total:", sum(x.get("n",0) for x in crypto_strats if x.get("is_single_source_artifact")))
'

# 2. money_ready verdict (gates)
python3 -c '
import json, pprint
v = json.load(open("audit_dashboard/data/money_ready_verdict.json"))
print("verdict generated:", v["generated_at"])
pprint.pprint(v["classes"]["CRYPTO"])
'

# 3. Tier table (exact 1 T2)
cat reports/strategy_tier_tracker_20260605T123622Z.md | head -70

# 4. Recency (verify 14d/48h before any historical)
python3 -c '
import json
for f in ["audit_dashboard/data/pick_summary_stats_14d.json", "audit_dashboard/data/pick_summary_stats_48h.json"]:
    d=json.load(open(f)); print(f, "CRYPTO n_closed:", d.get("by_class",{}).get("CRYPTO",{}).get("n_closed"))
'

# 5. Code refs (py_compile + grep)
python3 -m py_compile alpha_engine/money_ready_verdict.py tools/build_pf_registry.py audit_trail/quality_gates.py tools/clean_ingest_v2.py audit_trail/promotion_gate.py alpha_engine/outcome_resolver.py audit_trail/universal_pick_resolver.py
grep -n "CRYPTO" alpha_engine/money_ready_verdict.py | head -5
grep -n "crypto_liquidity_wick_reversal_v1\|is_single_source_artifact" tools/build_pf_registry.py alpha_engine/money_ready_verdict.py
grep -n "PNL_WIN_THRESHOLD_BY_CLASS" alpha_engine/outcome_resolver.py
grep -n "BLOCKED_ASSET_STRATEGY_PAIRS\|PF_REGISTRY_POLICY_EXCLUDED" audit_trail/quality_gates.py | head -3
grep -n "CRYPTO" tools/clean_ingest_v2.py audit_trail/promotion_gate.py | head -5

# 6. Reports (full context)
cat reports/WR_SCRUTINY_AND_FILTER_SEARCH_2026-06-05.md
cat reports/2026-06-05-LIVE-FORWARD-TRIAGE.md | head -100
cat reports/2026-06-05-PER-CLASS-T2-INVENTORY-POST-FILTER.md | head -60
cat reports/2026-06-06_money_ready_essentials_swarm_impl.md
cat reports/2026-05-25_crypto_78pct_wr_verification.md | head -30
cat reports/peer_claude-promote-liquidity-wick_2026-05-31.md | head -30
ls -l reports/*CRYPTO* reports/*2026-06-05* reports/strategy_tier_tracker_20260605*.md

# 7. Emitters (non-LLM)
ls alpha_engine/crypto_funding_rate_carry.py alpha_engine/crypto_onchain_momentum.py alpha_engine/crypto_liquidation_fade.py alpha_engine/crypto_whale_accumulation.py alpha_engine/crypto_liquid_core.py
grep -n "def .*funding\|onchain\|whale\|liquidation" alpha_engine/crypto_funding_rate_carry.py alpha_engine/crypto_onchain_momentum.py

# 8. Closed sample (if present; else use registry)
ls alpha_engine/data/closed_picks.json battleground/data/closed_picks.json 2>/dev/null || echo "use pf_registry source_files"
```

**Exact file refs (absolute in workspace):**  
- `audit_dashboard/data/money_ready_verdict.json:6-112` (CRYPTO dict)  
- `audit_dashboard/data/pf_registry.json:255-268` (raw CRYPTO), `by_asset_class_policy_clean_net` (302 row), `by_asset_class_strategy_policy_clean_net` (40 rows), source_files list, methodology:187.  
- `reports/strategy_tier_tracker_20260605T123622Z.md:21-64` (CRYPTO table)  
- `alpha_engine/money_ready_verdict.py:123-135` (_canonical_pipeline), `390-417` (_load_picks), `497-512` (_resolved sign), `260-267` (CLASS_WR_FLOORS CRYPTO), `138` (MIN_N_CLASS), `168-180` (single src gate), `422-452` (_top_money_ready_sleeves).  
- `tools/build_pf_registry.py:49-58` (wick single-src example), `72-100` (_row_source), `187-207` (dedup/flicker/policy), source_files:7-183.  
- `alpha_engine/outcome_resolver.py:115-131` (PNL_WIN... CRYPTO 0.00001).  
- `audit_trail/quality_gates.py:1535-1551` (PF_REGISTRY_POLICY_EXCLUDED), `2551+` (BLOCKED_ASSET... goldmine/quan etc for CRYPTO), liquid core sections ~6925.  
- `tools/clean_ingest_v2.py:1-80` (rejects).  
- `audit_trail/promotion_gate.py:170-199` (evaluate_forward_tier2 + TIER2_*).  
- `audit_trail/universal_pick_resolver.py:32-50` (MAX_HOLD CRYPTO 48).  
- `alpha_engine/crypto_liquid_core.py:28-32` (wick 1/229).  
- Recency + reports as above.  
- `updates/2026-06-05-grok-masterplan-phase1-shipped.md` + `reports/2026-06-06_money_ready_essentials_swarm_impl.md` (MASTERPLAN refs).

**Next actions for main agent (clear handoff):**  
1. Review this report + cited files (esp. pf_registry strategy list + WR_SCRUTINY + 06-05 triage).  
2. Per CLAUDE: name Goal#1; check_messages / list_peers / set_summary if multi-agent.  
3. Pull latest (`git stash && git pull --rebase origin main && git stash pop`).  
4. Wire 1-2 non-LLM (funding carry + onchain) + RENDER family via promotion_gate + clean_ingest; hard-enforce single-src/MDD in verdict (env=1).  
5. Run verified pilots on wick (post resolver fix) + new; track 14d/48h daily.  
6. After changes: py_compile, tests (no gens), read full updates/index.html before edit (insert pre AUTO marker), FTP deploy via tools/deploy_audit_files.py --only updates (or pick_funnel). Verify curl. Do NOT push others' commits.  
7. If n-growth on good sleeves reaches criteria, open PR with this deep_dive as doc + repro. Spawn sub-dive on other classes if needed.  
8. Update MEMORY.md / daily memory with key decisions (e.g. wick is only T2 but single-src; policy_clean vs DB cohort diff).  

**Bottom line (grounded):** CRYPTO policy-clean is FAIL (PF<1 WR~35% n=302) due to source conc (battleground for 1 sleeve), zero-edge volume (copy/ml), data artifacts (sign/batch/backfill per WR_SCRUTINY/triage), and no durable multi-src OOS edge (all high-WR artifacts). 1 near-T2 sleeve (wick n=30 pf1.55) but single-src + resolver risk. Rescue via clean + non-LLM + forward n on RENDER/funding family + promotion gates. 0/9 money-ready is correct per all sources. Do not size up until acceptance met + 14d/48h verified.

(End of report. All citations local + exact.)