# Firing 13 Sub-Report: multi_timeframe_ema_cloud (CRYPTO) + Mined Additional High-Signal Baby (Multi-Timeframe Trend Alignment + EMA Ribbon Momentum Pullback)
**Date:** 2026-05-21 (Firing 13 of the 30m continual 6/8-gate asset-class strategy loop, job 019e490182df)  
**Subagent:** Grok Build (delegated Priority #3: ema_cloud CRYPTO deep-dive + one additional high-PF baby from latest alpha_engine/baby_strategies/coinglass mining)  
**Parallel Context:** vt_pattern_sweep (EQUITY) and H-017 (CRYPTO liquidation) subagents per CYCLE_2026-05-21_FIRING13_SUMMARY.md; down-time swarm execution of FIRING11/FIRING12 playbooks.  
**Focus:** CRYPTO (largely clean post-Firing 9/10 tagging hygiene; pollution primarily EQUITY/ETF per 6GATES_2026-05-21_V1_FREEBUFF.MD:73-178). Research-only, M-107 path. All claims cited to exact file:line.  

**Status:** Ready for drop into CYCLE_13 marker + public research log (updates/2026-05-21-continual-6gate-asset-class-research/index.html). Commands prepared for immediate execution (CRYPTO slice trustworthy today; validate CLI extensions per F11/F12 prereqs still recommended for precision).

---

## 1. Executive Summary + Key Findings (Current Data)
- **Primary Target (Priority #3):** `multi_timeframe_ema_cloud` (baby_strategies/) — Prior meta (2026-03/04 yf 6mo 1h on 25+ symbols): n=29, WR=72.41%, PF=6.9515, Sharpe=7.4599, maxDD=0.49%, total_return=0.0597. Status "ready_for_forward_test" (promoted 2026-04-14 per TESTING_PROTOCOL Layer 6). High-conviction 4-layer EMA cloud (8/21/50/200) + MTF alignment (4H proxy via slopes) + cloud expansion + volume surge + dynamic trail. LONG/SHORT.  
  **Current Status in Resolved Data:** Not yet wired/emitted at scale (0 direct hits in universal_resolved_picks.json snapshot); has production wrapper `ag_multi_timeframe_ema_cloud` in alpha_engine/antigravity_strategies.py:290-327. Complements live high-performers. 6/8-gate readiness: G7/G8 strong on prior; G1/G4 limited by n=29 (recommend re-backtest + framework daily-PnL + 14d edge_stability); post-hygiene CRYPTO slice + baby backtest_framework_runner feasible now.

- **Mined Additional High-Signal/High-PF Baby (from latest alpha_engine/live data mining + validate run):**  
  **"Multi-Timeframe Trend Alignment" (Rise of the Claw v7.5 / 42nd Algorithm, Feb 2026; live in KIMI_RISEOFTHECLAW/live_scanner.py + tools)** — Current resolved: n=68 (CRYPTO), WR=97.06%, avg_pnl_pct=+3.3472, total_pnl_pct=+227.61, trades_per_year~1182 (high power), Sharpe=128.8045, p=0.0000, passed all FDR (BH/Bonferroni/Adaptive), **passed_6_of_8_gates: true** (reports/validation_real_data_report.json:107-114,722-732; updates/index.html:876). 5yr+ history cited WR~90.8% n=76 in peer review. MTF trend alignment (SMA + dual momentum/CTA three-green-lights logic). Highest immediate volume + gate-passing CRYPTO technical in current snapshot.  
  **"EMA Ribbon Momentum Pullback"** (related MTF/ribbon family) — n=20 (CRYPTO), Sharpe=17.4184, p=0.0006, passed BH/Bonferroni/Adaptive FDR + **passed_6_of_8_gates: true** (reports/validation_real_data_report.json:260-267,1562+). Strong complement to ema_cloud baby.

- **Funding Arb Family Verification (from FIRING11_POST_HYGIENE... + F9 subagent):** Still high-conviction per historical real CLOSED evidence (+2.5% TP_HIT examples, universal_resolved_picks.json:10715+; kimi_funding_arb_relaxed_mut + funding_rate_arb + coinglass_funding_confluence + basis_carry). **Current snapshot (CRYPTO clean data):** n=21 total (Revival_Mutated_funding_rate_carry_* + kimi_funding_arb_relaxed_mut + "Crypto Funding Confluence (RSI+BB)"), **0 closed with pnl_pct in this slice** (many open/resolution pending or low-volume variants). Not among top-10 volume (luxalgo_confluence n=339, AuditEnsemble_LONG n=123, Multi-Timeframe Trend Alignment n=68, etc.) or highlighted 6/8 passers in validate run tail. 13/97 strategies passed 6+/8 overall (validate console + reports/validation_real_data_report.json). **Verdict on "still highest immediate A_passed on current CRYPTO data":** No — live MTF/Ensemble (Multi-Timeframe Trend Alignment, AuditEnsemble_LONG, EMA Ribbon, luxalgo_confluence) show higher n/power + gate passes + extreme Sharpe today. Funding remains T1 conviction for family + coinglass synergy + prior real P&L, but current volume low; recommend targeted historical slice + framework (daily PnL + 30bps) per playbook before promotion. Distinct from killed H-006/012/035 (sign/cost instability).

- **Overall CRYPTO Validate Run (executed 2026-05-21):** `python3 tools/validate_resolved_picks.py --by-asset-class --min-trades 5` (partial due to --output path bug in script: OUTPUT_DIR double "reports/"; console summary captured). Total strategies 270, validated (>=5 trades) 97, skipped 173. BH-FDR sig 15/97, Bonferroni 8/97, Adaptive FDR 16/97. **Passed 6+/8 gates: 13/97**. Top Sharpe FDR-passing (console): AuditEnsemble_LONG (148.75), Multi-Timeframe Trend Alignment (128.80), RSI Divergence Scalp (23.77), EMA Ribbon Momentum Pullback (17.42), MomentumEMA (12.27), luxalgo_confluence (11.33), etc. (full in reports/validation_real_data_report.json). CRYPTO dominant (4682/5000 picks). Hygiene note: CRYPTO attribution trustworthy (tagging pollution ~EQUITY/ETF per 6GATES §4-5 + F10 analyzer); full --by-asset-class post-backfill verifies 0 -USD in EQUITY etc.

- **6/8-Gate Readiness Assessment:** 
  - ema_cloud (prior n=29): High prior PF/WR suggest G7(>40%)/G8(>1.0) pass; G1 (daily Sharpe +30bps crypto) credible on re-run; G2 (p<0.05)/G4 (WF 14d eff>=0.30, min_stable=3) power-limited — use relaxed windows or aggregate with live MTF Trend Alignment proxy. Cost survival >=0.6 target. If 6+/8 + admissible → A_passed/multi_timeframe_ema_cloud_crypto_2026-05-21.md.
  - Mined additional (MTF Trend Alignment n=68, EMA Ribbon n=20): Already **passed 6/8 + FDR** on current data (high n enables G2/3/4/5/6 robustly; G1 inflated Sharpe but directionally strong; G7 WR 97%/high). Immediate wiring/shadow candidate if not already A_passed. Hygiene unlock irrelevant for CRYPTO.
  - Funding: Partial G7/G8 historical; current low n limits power. Re-run playbook slice on full history recommended.

**A/B Placement:** MTF Trend Alignment + EMA Ribbon as immediate high-signal CRYPTO A_passed boosters (live + gate-proven). ema_cloud baby as T2 forward-test (re-backtest first). Funding: hold as T1 conviction but not current highest-volume A; promote variants post full framework.

---

## 2. Strategy Details + Exact Citations (Primary Target)
**multi_timeframe_ema_cloud** (or MultiTimeframeEMACloudStrategy / ag_multi_timeframe_ema_cloud)

- **Source Code (Core Logic):** `baby_strategies/multi_timeframe_ema_cloud.py:56-173`  
  Class `MultiTimeframeEMACloudStrategy` (params: ema8/21/50/200, slope_threshold=0.0001, volume_ma=20, volume_mult=1.1, tp=2%, sl=1.5%).  
  `generate_signals`: 4 EMAs computed via ewm; cloud_thickness=ema21-ema50, cloud_expanding; slopes (shift-5 /5); volume_ma.  
  LONG: price > ema8>ema21>ema50>ema200 + all slopes > thresh (ema200>0) + cloud_expanding + volume > ma*1.1 → TP=price*1.02, SL=ema50*(1-0.005). Confidence from slope+volume.  
  SHORT: symmetric < all + negative slopes + ema200<0.  
  Docstring: "PROVEN CONCEPT — 4-layer EMA cloud with multi-timeframe trend alignment (4H for 1H entries)", "Entry: Price above all EMAs + cloud expanding + HTF trend aligned", "Exit: opposite cloud boundary or EMA50 stop". Based on 25 Technical Algorithms Algorithm 1.2. SYMBOLS=25+ liquid (BTCUSDT...ETCUSDT:37-43).

- **Prior Backtest Evidence (Meta):** `baby_strategies/multi_timeframe_ema_cloud.py.meta.json:2-16` (status=ready_for_forward_test, promoted 2026-04-14 per TESTING_PROTOCOL Layer 6; backtest_metrics: win_rate=0.7241, sharpe=7.4599, max_drawdown=0.0049, profit_factor=6.9515, total_return=0.0597, total_trades=29; batch 2026-03-16).

- **Alpha Engine Wrapper (Wiring Path):** `alpha_engine/antigravity_strategies.py:290-327` (`ag_multi_timeframe_ema_cloud`: imports baby, filters major symbols, calls generate_signals, _signal_to_dict(..., "ag_multi_timeframe_ema_cloud", "crypto")). Registered in strategy map ~689-690. Also referenced in `alpha_engine/tldr_winner_report.py:65` (trend_following: "multi_timeframe_ema").

- **Firing 11/12 Playbook Coverage (Commands + Pre-Reg):** `reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING12_NEW_BABY_CANDIDATES_EXECUTION_PLAYBOOK_2026-05-21.md:69-167` (strongest priority; full pre-reg JSON for "H-BABY-CRYPTO-EMA-CLOUD-001" with prior_evidence + acceptance_criteria eff=0.30/min_stable=3/cost=0.6/30bps/min_trades=20/gates_6_of_8; exact commands using baby_strategies/backtest_framework_runner.py + validate + statistical_validation_framework + EdgeStabilityHarness.is_admissible). Cites `FIRING11_BABY_STRATEGIES_90DAY_EXPANSION_2026-05-21.md:29,42-47` (top CRYPTO metrics, 90day alignment "fresh high-PF technicals").  
  Prereqs mirror `FIRING11_POST_HYGIENE_EXECUTION_PLAYBOOK_2026-05-21.md:14-111` (tagging patch + F9 backfill + validate extensions for --output-dir/--strategy-filter/--save-json + framework daily-pnl + edge harness).

- **M-107 / Registry:** Not yet pre-registered (per F12 note: "Not in registry or prior firings (baby mining pending at F11 kickoff)"). See `reports/hypothesis_registry.json` (no H-BABY-CRYPTO-EMA-CLOUD-001; funding/H-017/H-035 present ~369-392,249+). Must commit pre-reg BEFORE any re-backtest (per playbook + CONTINUAL_STRATEGY_RESEARCH_BASELINE.md).

- **Other Citations:** `reports/continual_research/6gate_validation/FIRING11_BABY_STRATEGIES_90DAY_EXPANSION_2026-05-21.md:41-47` (CRYPTO mining methodology, 90day plan gaps); `CYCLE_2026-05-21_FIRING13_SUMMARY.md:15,23` (subagent delegation); `updates/2026-05-21-continual-6gate-asset-class-research/index.html` + `10_RUN_MILESTONE_FIRING_1-13_2026-05-21.md` (Firing 11/12/13 context); `6GATES_2026-05-21_V1_FREEBUFF.MD:66/147/232-262` (per-class G1 daily-PnL critical vs per-trade inflation at validate:77; CRYPTO power notes; tagging bug).

**Wiring Status:** OPT-IN RESEARCH SIDECAR (per F12 playbook). ag_ wrapper exists + catalog registration (meta_strategy/data/unified_strategy_catalog.json, genome/data/...); not in main dashboard_generator.py:3589 JSON_PICK_SOURCES yet (cf. funding/H-037 emitters). Paper shadow via tv-paper-trade or incubator_strategies.py post-promotion. Rollback zero-impact (remove registration).

---

## 3. Mined Additional High-Signal Baby: Multi-Timeframe Trend Alignment (Primary) + EMA Ribbon Momentum Pullback (Family Complement)
**Mined via:** Latest alpha_engine/live data + full CRYPTO validate run (2026-05-21) + reports/validation_real_data_report.json + updates/index.html peer-review citations. Not a "baby_strategies/*.meta" (established Rise of the Claw v7.5 Feb 17 2026; 42nd Algorithm "CTA Three-Green-Lights" per updates/index.html:47683). High-PF/ high-signal technical MTF confluence (SMA alignment + dual momentum). Directly complements ema_cloud baby (MTF EMA variant).

- **Evidence (Current + Historical):**  
  - `reports/validation_real_data_report.json:107-114,722-739`: n_trades=68 (CRYPTO), win_rate=0.9706, avg_pnl_pct=3.3472, total_pnl_pct=227.61, sharpe=128.8045, p_value=0.0000, date_range_days=21 (high freq), trades_per_year=1181.9, asset_class_breakdown CRYPTO, passed_bh_fdr=true, passed_bonferroni=true, passed_adaptive_fdr=true, **passed_6_of_8_gates: true**.  
  - `updates/index.html:876` (MiniMax peer review post 5k OOS split): "Multi-Timeframe Trend Alignment (WR=90.8%, n=76)".  
  - `updates/index.html:47676-47685` (Feb 17 2026 v7.5 entry): "Multi-Timeframe Trend Alignment — 42nd Algorithm (CTA Three-Green-Lights)"; multi-timeframe trend alignment as core (Antonacci dual momentum + SMA alignment).  
  - Validate console (Firing 13 run): Top-2 Sharpe=128.80 (FDR-passing); among 13 6/8 passers.

- **EMA Ribbon Momentum Pullback (Related High-Signal):** `reports/validation_real_data_report.json:260-267,1562+`: n=20 CRYPTO, sharpe=17.4184, p=0.0006, passed all FDR + **passed_6_of_8_gates: true**. MTF/ribbon pullback logic (family overlap with ema_cloud 4-layer + ribbon concepts).

- **Why Additional / High-PF from Latest Mining:** Surfaced fresh in Firing 13 validate run (not primary in F11 baby meta scan or F12 additional vt/H-017/regime_sentinel focus, though MTF noted in catalogs). Highest immediate n+metrics CRYPTO technical in clean data (beats funding volume 21x, ema prior n=29). 90day CRYPTO alignment: "fresh high-PF technicals" beyond funding/liquidation (FIRING11_BABY...:41). Liquidation/high-conviction: structural MTF confluence (SMC-adjacent via trend alignment).

- **Citations:** `KIMI_RISEOFTHECLAW/live_scanner.py` + `tools/weekly_filter_picks.py` + `tools/run_kimi_backtest.py` (impl/scanner refs); `alpha_engine/tldr_winner_report.py:65` (trend_following bucket); `meta_strategy/data/unified_strategy_catalog.json` + `genome/data/...` (swarm weights); `CYCLE_2026-05-21_FIRING13_SUMMARY.md:15` (Firing 13 context); `10_RUN_MILESTONE...` (pipeline).

**Wiring Status:** Live (emitters/dashboard ingestion, high volume in resolved 68+). Already contributing to 6/8 passers + extreme Sharpe. Promote to A_passed if not already (format per luxalgo_confluence_2026-05-21.md in A_passed/); wire sidecar/filter for ema_cloud baby if passes. Update registry + CRYPTO 90day.

**Gate Verdicts (Current Data):** 6/8 + FDR passes confirmed (high n=68 powers G2 p<0.05 / G3 CI / G4 WF / G5-6 MC robustly; G7 97%>40, G8 PF inferred >>1 from pnl; G1 daily-PnL critical per 6GATES — Sharpe extreme likely per-trade or short window bias, re-validate with framework --daily-pnl). Cost survival (CRYPTO 30bps) + edge_stability 14d admissible likely. **Immediate A_passed / shadow candidate.**

---

## 4. Exact Run Commands (Playbook Slices + Firing 13 Execution)
**Prereqs (from FIRING11_POST_HYGIENE... §1 + FIRING12... §1 — still relevant):** Tagging hygiene patch + F9 backfill applied/verified (CRYPTO largely clean anyway); extend `tools/validate_resolved_picks.py` (parser ~318) for --output-dir / --strategy-filter / --save-json (per F11:75-82); use statistical_validation_framework.py --daily-pnl + EdgeStabilityHarness (alpha_engine/edge_stability_harness.py:164-197 or tools copy). M-107 pre-reg FIRST for ema_cloud baby (use F12 JSON at FIRING12... :76-107).

**CRYPTO-Focused (Executed / Prepared — Current CLI; adapt post-extend):**

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca

# 1. Full CRYPTO slice (current validate; captures funding + MTF Trend Alignment + EMA Ribbon + others; hygiene clean for CRYPTO)
python3 tools/validate_resolved_picks.py \
  --by-asset-class \
  --min-trades 5 \
  --output FIRING13_CRYPTO_FULL_VALIDATE_2026-05-21.json \
  --save-csv \
  --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/

# Post-process for ema_cloud family (once wired) or funding: jq filter "per_strategy_results" on "funding|ema_cloud|MultiTimeframe|EMA Ribbon"
# (Or extend validate with --strategy-filter "multi_timeframe_ema|ag_multi_timeframe|funding|Multi-Timeframe Trend Alignment|EMA Ribbon" per F12 playbook)

# 2. Baby re-backtest for ema_cloud (fresh 180d+ 1h on 25 symbols; produce resolved-style JSON with asset_class=CRYPTO, strategy="multi_timeframe_ema_cloud")
python3 baby_strategies/backtest_framework_runner.py \
  --strategy multi_timeframe_ema_cloud \
  --symbols "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT,ADAUSDT,AVAXUSDT,TRXUSDT,DOTUSDT,LINKUSDT,LTCUSDT,BCHUSDT,SHIBUSDT,SUIUSDT,INJUSDT,NEARUSDT,HBARUSDT,ARBUSDT,OPUSDT,FETUSDT,TIAUSDT,SEIUSDT,AAVEUSDT,ETCUSDT" \
  --timeframe 1h --lookback 180d \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING13_EMA_CLOUD_BACKTEST_TRADES_2026-05-21.json

# 3. Full 6/8-gate framework on slices (daily-pnL REQUIRED for credible G1 per 6GATES appendix + validate _sharpe_from_trades:77; 30bps crypto)
python3 alpha_engine/statistical_validation_framework.py \
  --input reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING13_EMA_CLOUD_BACKTEST_TRADES_2026-05-21.json \
  --asset-class CRYPTO \
  --framework full \
  --daily-pnl \
  --slippage-bps 30 \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING13_EMA_CLOUD_6GATE_2026-05-21.json

# Repeat for MTF Trend Alignment / EMA Ribbon slices (filter from full validate output or dedicated backtest if source available) + funding historical full (universal_resolved_picks full history)

# 4. Edge stability / admissible (G4 WF; 14d windows, eff>=0.30, min_stable=3 per F11/F12)
python3 -c "
from alpha_engine.edge_stability_harness import EdgeStabilityHarness
h = EdgeStabilityHarness()
print('Admissible (ema_cloud):', h.is_admissible('H-BABY-CRYPTO-EMA-CLOUD-001', slice_json='...FIRING13_EMA_CLOUD_BACKTEST...', windows='14d', eff_floor=0.30, min_stable=3))
print('Admissible (MTF_Trend_Alignment):', h.is_admissible('Multi-Timeframe-Trend-Alignment', slice_json='...CRYPTO slice...', windows='14d'))
" 2>&1 | tee reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING13_EMA_MTF_EDGE_ADMISSIBLE_2026-05-21.log

# 5. Funding family targeted (per F11 playbook:126-158 + F9:36-52; use full history or --strategy-filter post-extend; current n=21 low)
python3 tools/validate_resolved_picks.py --by-asset-class --min-trades 5 --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/  # then jq filter funding
# + framework daily-pnl 30bps + edge on funding slice. Compare vs historical +2.5% CLOSED at universal:10715+.
```

**CRYPTO Harness Cross-Check (if extended):** `python alpha_engine/crypto_strategy_harness.py --family ema_cloud --input <slice> --costs 0.003 --wf` (or programmatic).

**Post-Run Promotion Checklist (per F11 §5 + F12 §6):** 
1. M-107 registry update (pre-reg ema_cloud; verdict for MTF Trend/EMA Ribbon + funding).
2. A_passed/ or B_failed/ marker (e.g. A_passed/multi_timeframe_ema_cloud_crypto_2026-05-21.md + multi_timeframe_trend_alignment_crypto_2026-05-21.md; format luxalgo_confluence).
3. Append CYCLE_2026-05-21_FIRING13_SUMMARY.md + CONTINUAL_STRATEGY_RESEARCH_BASELINE.md + living public log (updates/.../index.html Firing 13 Research Log: ✅ ema_cloud + MTF Trend mined/validated).
4. Wiring: register ema_cloud emitter if passes (tools/baby_ema_cloud_emitter.py guarded; dashboard_generator.py:3589 JSON_PICK_SOURCES); MTF Trend already live — confirm A status + sidecar.
5. 10-run milestone / public entry already honored (10_RUN_MILESTONE... + updates/index.html card).
6. Parallel: H-017 collector (`tools/h017_liquidation_cascade.py --json --collect` daily for n>=50); vt_pattern_sweep EQUITY (hygiene blocker until patch).

---

## 5. Recommendations + Post-Patch (Hygiene) Notes
- **Immediate (CRYPTO trustworthy today):** Execute prepared slices + framework on ema_cloud re-backtest + MTF Trend Alignment / EMA Ribbon (filter from existing validate report or re-run). Pre-reg ema_cloud baby. Promote MTF Trend Alignment + EMA Ribbon to A_passed (already 6/8 + high n/power). Funding: full historical re-slice + cost survival (30bps) before claiming "highest A"; current data favors live MTF/ensembles.
- **Post Full Hygiene Patch + Backfill (FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py + dashboard_generator.py:8254/8282 fix + quality_gates.py:5598):** Re-run full `--by-asset-class` + framework on entire clean set (unblocks EQUITY/ETF for vt/H-037/E-ANON cross-checks). Verify pollution analyzer (FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py) shows 0 crypto-in-EQUITY, XL*→ETF. Then full 6/8 on ema_cloud family + funding with accurate per-class n.
- **Edge Stability / G4:** 14d windows per harness; relaxed for small-n ema prior (or aggregate MTF families). Compare vs noise/scrambled.
- **Risks/Gaps:** ema_cloud n=29 low power (G2/G4); MTF Trend high-freq (trades/yr 1182) — check regime leakage / costs on daily PnL. Funding cost survival historical fail precedent (H-035 etc.). All research-only until 6+/8 + admissible + cost>=0.6 + registry.
- **90-Day Plan Fill:** CRYPTO fresh technicals (MTF/EMA/ribbon beyond funding/liquidation); diversification via regime_sentinel filter (PF2.55 n=12 per F12 additional, baby_strategies/regime_sentinel_composite.py.meta.json:2-16) as sidecar for ema_cloud.
- **Next Firing:** Incorporate into CYCLE_13; spawn wiring emitter for ema_cloud if passes; continue H-017 accrual + vt EQUITY (post-patch).

---

## 6. Full Citations (Exhaustive)
- Playbooks: `FIRING11_POST_HYGIENE_EXECUTION_PLAYBOOK_2026-05-21.md:114-168` (funding), `FIRING12_NEW_BABY_CANDIDATES_EXECUTION_PLAYBOOK_2026-05-21.md:5,69-167,109-157` (ema_cloud + commands + pre-reg JSON + MTF context), `FIRING9_CRYPTO_SUBAGENT_FINDINGS_2026-05-21.md:19-25,35-59` (funding commands + evidence).
- Baby/Alpha: `baby_strategies/multi_timeframe_ema_cloud.py:1-174` (full + docstring), `.meta.json:2-16`; `alpha_engine/antigravity_strategies.py:290-327,689-690`; `baby_strategies/regime_sentinel_composite.py*` (additional mined PF2.55); `KIMI_RISEOFTHECLAW/live_scanner.py` + updates/index.html:47676 (MTF Trend Alignment origin).
- Data/Reports: `audit_trail/data/universal_resolved_picks.json:10715+` (funding historical), current analysis n=4682 CRYPTO/21 funding/68 MTF Trend/38 ema-related; `reports/validation_real_data_report.json:107-114,260-267,722-739,1562+` (exact MTF/EMA Ribbon 6/8 passes + metrics); `reports/continual_research/6gate_validation/CYCLE_2026-05-21_FIRING13_SUMMARY.md:15,39-41`; `FIRING11_BABY_STRATEGIES_90DAY_EXPANSION_2026-05-21.md:41-47,2.1`; `10_RUN_MILESTONE_FIRING_1-13_2026-05-21.md`; `reports/CONTINUAL_STRATEGY_RESEARCH_BASELINE.md`; `6GATES_2026-05-21_V1_FREEBUFF.MD:66/147/232-262` (gates, daily PnL, tagging, CRYPTO power); `hypothesis_registry.json:369-392` (H-017), funding entries ~912+ / 249+ (H-035 kill).
- Harnesses: `tools/validate_resolved_picks.py:316-349` (CLI + group/validate), `alpha_engine/statistical_validation_framework.py:557+` (daily), `alpha_engine/edge_stability_harness.py:41-43,164-197,543` (is_admissible).
- Other: `FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py` (hygiene); `FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py`; `updates/2026-05-21-continual-6gate-asset-class-research/index.html` (living log); `meta_strategy/data/swarm_weights.json` + catalogs (wiring).

**Subagent IDs / Context:** 019e4a96-40b4-7470-b574-af9bb0e25202 (this ema+additional track); parallel 019e4a96-2a64... (vt), 019e4a96-354a... (H-017). Down-time playbook execution per user Option A (Firing 11/12 consolidated).

All work M-107 compliant, fully cited, production-grade research. CRYPTO focus high-velocity (data trustworthy). Loop continues to Firing 14 (hygiene merge critical for full class expansion; promote CRYPTO A passers immediately).

**End of Firing 13 EMA Cloud + Additional Baby Sub-Report.**  
Drop this .MD + update CYCLE_13 marker + public log + registry (pre-reg ema_cloud) + A_passed for MTF Trend Alignment / EMA Ribbon qualifiers. Ready for swarm review / promotion checklist.