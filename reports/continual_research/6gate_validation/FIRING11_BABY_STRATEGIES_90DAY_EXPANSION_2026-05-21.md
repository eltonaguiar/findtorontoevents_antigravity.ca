# Firing 11: Baby Strategies + 90-Day Plan Expansion Report
**Date:** 2026-05-21  
**Subagent:** Grok (Firing 11 of 30m continual 6-gate research loop)  
**Focus:** Systematic mining of `baby_strategies/*.meta.json` + cross-reference with all `asset_class_90day_plan_*.md` (CRYPTO/EQUITY/FOREX/COMMODITY/ETF/FUTURES/PENNY_MEME/BOND) for new or under-tested high-PF/liquidation/high-conviction candidates. Special attention to candidates benefiting from Firing 10 hygiene artifacts (tagging patch, pollution analyzer) and COMMODITY COT guard.  
**Prioritization:** Liquidation/cascade names, high-PF (PF>1.2 with n>=20 where possible), promoted/forward-test ready, cross-asset inverses/mutations, COT-proxy strategies. Exclude heavily analyzed prior-firing candidates (e.g. cross_sectional_crypto_carry in B_failed reports, E-ANON-001/H-037/funding family from Firing 10).  
**Output:** 3-5 candidates with evidence citations, A/B placement recommendations, and 6/8-gate harness run outlines for strongest 1-2. All research-only, M-107 pre-reg compliant path.

**Citations (key files):**
- `baby_strategies/*.meta.json` (49 total; scanned via glob + content for PF/WR/n)
- `reports/asset_class_90day_plan_{CRYPTO,EQUITY,FOREX,COMMODITY,ETF,...}_2026-05-15.md`
- `6GATES_2026-05-21_V1_FREEBUFF.MD` (8 gates: G1 Sharpe>=1, G2 p<0.05, G3 CI>0, G4 WF>=50%, G5 MC bootstrap, G6 MC crash, G7 WR>40%, G8 PF>1.0)
- `reports/continual_research/6gate_validation/CYCLE_2026-05-21_FIRING10_SUMMARY.md` + `COMMODITY_COT_GUARD_PATCH_firing10_2026-05-21.md` + `FIRING10_HYGIENE_MINIMAL_MERGE_DIFF_2026-05-21.md` + `FIRING10_EQUITY_FOREX_EXPANSION_2026-05-21.md` (hygiene/COT/EQUITY expansion context)
- `updates/2026-05-21-continual-6gate-asset-class-research/index.html` (living report: "baby_strategies/*.meta.json mining ... results pending")
- `reports/hypothesis_registry.json` (M-107 pre-reg; baby names largely absent → under-tested)
- `tools/validate_resolved_picks.py`, `tools/kimi_research_2026_05_20/six_gate_validated_strategy.py`, `baby_strategies/backtest_framework_runner.py` + `baby_strategies_backtest.py` (harnesses)
- `reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_POST_HYGIENE_EXECUTION_PLAYBOOK_2026-05-21.md` (post-hygiene context)
- Specific: `baby_strategies/multi_timeframe_ema_cloud.py` (and .meta), `moving_average_slope_momentum.py` (and .meta), `rsi_pairs_arbitrage.py` (and .meta), `logistic_microstructure.py` (and .meta), `inverse_goldmine_stocks.meta.json` + `inverse_earnings_drift.meta.json` + `inverse_value_quality.meta.json`, `copper_platinum_cot_momentum.py`, `commodity_trend_pullback_rsi.py`, `commodity_range_position_reversion.py`
- Firing 9/10 B_failed: `commodity_strategies_cot_leakage_no_6gate_pass_2026-05-21.md`, `forex_strategies_stressed_no_6gate_pass_2026-05-21.md`, `targeted_candidates_commodity_carry..._firing4...`
- `PEER_RESEARCH_CANDIDATES_2026-04-20.md` (in baby_strategies/)

---

## 1. Executive Summary & Mining Methodology
Mined all 49 `*.meta.json` (via `grep -r` equivalent on glob `**/*.meta.json` for keys "profit_factor", "win_rate", "total_trades", "sharpe", "backtest_metrics", "status", "promotion_note") + all non-meta high-signal .py (commodity_*, forex_*, equity_*, prop_*, hoffman_*, keltner_*, liquidation_*, price_roc_*, inverse_*.meta.json). Cross-referenced every 90-day plan for explicit mentions/gaps (e.g. COMMODITY diversification beyond CT=F 73% concentration + COT hygiene; EQUITY T2 evidence-first + mutations/inverses/PEAD; FOREX stressed PF<1; CRYPTO rich but "baby meta mining pending").

**Key Finding:** Most baby metas from ~2026-03/04 batch (yfinance 6mo hourly backtests). High-PF standouts have small n (<20) limiting gate power (G4 WF especially); solid n>=29+ are mostly CRYPTO with PF 1.1-7 range. No liquidation_cascade delivered (n=1). Strong EQUITY inverse mutations (.meta only) and COMMODITY COT-proxy are hygiene/guard beneficiaries and align directly with 90-day expansion calls. Living report confirms baby mining "pending" → these are fresh for Firing 11.

**3-5 Candidates Selected (with evidence):**
- **multi_timeframe_ema_cloud.py** (CRYPTO) — Top metrics.
- **moving_average_slope_momentum.py** (CRYPTO) — Best volume.
- **rsi_pairs_arbitrage.py** (CRYPTO) — Highest n.
- **inverse_goldmine_stocks** (EQUITY) — Hygiene + class expansion synergy.
- **copper_platinum_cot_momentum.py** (COMMODITY) — Direct COT guard beneficiary + diversification fit.

**A/B Recommendations:** See Section 4. Prioritize post-hygiene (Firing 10 patch + backfill) + M-107 registry entry before any re-backtest.

---

## 2. Detailed Candidate Inventory (Citations from meta + Plans)

### 2.1 CRYPTO Candidates (Rich data; 90day plan calls for fresh technicals beyond alpha_engine/coinglass)
- **multi_timeframe_ema_cloud.py + .meta.json**  
  Backtest evidence (meta): status="ready_for_forward_test", WR=0.7241, sharpe=7.4599, PF=6.9515, total_return=0.0597, total_trades=29. Promoted 2026-04-14 "per TESTING_PROTOCOL Layer 6".  
  Code: 4-layer EMA cloud (8/21/50/200) + MTF alignment (4H for 1H) + cloud expansion + volume + dynamic trail. SYMBOLS=25+ BTCUSDT... (crypto only).  
  90day alignment: CRYPTO plan (not explicitly naming but "fresh high-PF technicals", funding/liquidation/basis gaps noted in living report). Not in hypothesis_registry (under-tested). Not in prior firing summaries (pending in living report baby mining).  
  Liquidation/high-conviction: MTF confluence high-conviction technical; not liquidation named but strong edge.

- **moving_average_slope_momentum.py + .meta.json**  
  Evidence: status=ready_for_forward_test, WR=0.5638, sharpe=1.8099, PF=1.332, total_return=0.0883, n=94. Promoted 2026-04-14.  
  Code: Triple EMA slope (Fib 5/13/34) + hierarchy/acceleration. Same 25+ CRYPTO symbols.  
  90day: Fits CRYPTO volume needs for G4 WF power. Under-tested.

- **rsi_pairs_arbitrage.py + .meta.json**  
  Evidence: status=backtest_failed (but metrics present), WR=0.4231, sharpe=1.2934, PF=1.2694, total_return=0.1236, n=130 (highest n).  
  Code: Z-score spread + RSI-timed pairs arb on correlated crypto (BTC/ETH etc). Market-neutral.  
  90day: Good for n-power in gates; pairs angle complements single-name funding in coinglass/alpha_engine. (Note: cross_sectional_crypto_carry sibling in B_failed with n=189 PF<1.)

- **logistic_microstructure.py + .meta.json** (borderline)  
  Evidence: status=backtest_failed, WR=0.4677, sharpe=0.6229, PF=1.142, n=62.  
  Code: L1 logistic on orderbook micro features. CRYPTO symbols.  
  Lower priority (PF marginal).

- **liquidation_cascade_contrarian.py + .meta.json** (attempted priority)  
  Evidence: n=1, PF=999 (noise), WR=1.0, status=backtest_failed, note="0 signals... Entry conditions too strict".  
  Prioritized per task but insufficient evidence; needs relaxation before 6gate.

Other CRYPTO metas (vol_scaled_keltner PF~21 n=8; regime_sentinel PF=2.55 n=12; keltner_rsi PF=1.7 n=3) — high PF but n too low for reliable G1-G6 (esp. G4).

### 2.2 EQUITY Candidates (Sparse data per 6GATES; hygiene critical; 90day calls for inverses/mutations/PEAD)
- **inverse_goldmine_stocks.meta.json** (no .py, mutation)  
  Evidence: asset_class=EQUITY, parent="goldmine_stocks" (n=85 closed, WR=21.2%, PF=0.38, 71.8% SL hit, sum_return=-217%), inverse_theoretical_WR=78.8%, inverse_theoretical_PF=2.61, inverse_confirmed_pf=null, status=awaiting_forward_test, created=2026-04-14 (post PR#207 exposure of goldmine bug). Config: flip_direction, max_concurrent=5, size 0.5x. Promotion: n>=20 + WR>=60 + PF>=1.5.  
  90day alignment: EQUITY plan "T2-candidate (PF 1.57 n=420)", "mutations", "inverses", "evidence-first", "M-009 PEAD", "VIX sidecar". Perfect hygiene beneficiary (Firing 10 tagging patch fixes the 90.8% crypto-in-EQUITY pollution per 6GATES §4-5; EQUITY real n only ~20 pre-fix). Not in registry.

- **inverse_earnings_drift.meta.json**  
  Evidence: EQUITY, parent "Earnings Drift" n=19 WR15.8% PF0.30 (79% SL), inverse_theoretical PF=2.07, awaiting_forward. Symbol filter prefer_short MARA/PLTR/MSTR etc. (earnings drift fade).  
  90day: Direct PEAD/earnings mutation fit (M-009 pending in plan).

- **inverse_value_quality.meta.json**  
  Evidence: EQUITY, parent n=48 WR6.2% PF0.14 (94% SL), inverse_theoretical high WR93.8%, awaiting.  
  90day: Value/quality factor gap noted.

- **inverse_extreme_oversold_bounce.meta.json** (multi-class but EQUITY overlap)  
  Small parent n=14.

**Hygiene note:** These benefit enormously from Firing 10 `FIRING10_HYGIENE_MINIMAL_MERGE_DIFF` (dashboard_generator.py:8255/8282 hardcoded defaults) + backfill + quality_gates.py:5598 bonus removal. Post-fix, EQUITY slice trustworthy for G1-G8.

### 2.3 COMMODITY Candidates (COT leakage fixed in Firing 10; 90day: diversify CT=F 73%, post-guard rehab)
- **copper_platinum_cot_momentum.py** (no .meta, but explicit COT)  
  No numeric backtest evidence in file (proxy logic only); rationale: EMA20>EMA50 + 45<=RSI<=60 + price>EMA50 for HG=F/PL=F (whitelisted historically in quality_gates). "COT-proxy" via price (commercials net short in rising mkts). Presets for vol.  
  90day alignment: COMMODITY plan "diversification" (CT=F 73% PnL mass violation), "COT data quality", "HG/PL previously restricted/whitelisted n=168/138", "post-clean COT n~5-20", "M-021 lag-corrected re-run". **Direct Firing 10 beneficiary** (COMMODITY_COT_GUARD_PATCH + lag enforcement in multi_asset_copytrader_scraper.py + source_system="cftc_socrata"). Under-tested (no meta, absent from firings 2-10 summaries).

- **commodity_trend_pullback_rsi.py**, **commodity_range_position_reversion.py**  
  Strategy code (SMA200 trend + pullback + RSI; range MR). USO/metals presets + RV gate for oil. No meta/backtest evidence found. Fits "carry/momo sidecars" + "seasonal ag/energy/metals" in 90day COMMODITY. Would benefit from guard + yfinance futures data hygiene.

- **wti_ensemble_rehab.py**, **xau_bollinger_mr_rehab.py**, **xag_ensemble_rehab.py** (rehab variants)  
  No strong numeric evidence; "rehab" implies prior stress (aligns FOREX/COMMODITY salvage patterns in plans).

**COMMODITY guard synergy:** Any COT-using baby now has fail-loud 3d lag + dedup + tagging. Re-backtest copper etc. post-guard = clean G2/G5 etc.

### 2.4 FOREX/ETF/Other
- Forex_* (bb_mr_rehab_v1, carry_momentum_harvest, ensemble_4h_rehab, inside_day, weekly_gap_fill): Expected WR/PF cited in docstrings (e.g. 75-85% WR) but no meta/numeric backtest evidence. 90day FOREX: "weakest class PF<1 stressed", "LONG bias drag", "rehab" fits but low priority (insufficient for 6gate per firing reports).
- ETF plans reference H-037 (from Firing 10, not baby).
- No strong new liquidation/high-PF in lighter classes (PENNY/BOND insufficient per firing3/4).

**Gaps vs 90day plans:** Baby mining fills "fresh candidates" gap in CRYPTO (living report pending); provides mutations/inverses for EQUITY T2 evidence push; supplies COT-proxy diversification for COMMODITY post-guard; limited help for stressed FOREX.

---

## 3. Strongest 1-2 + 6/8-Gate Harness Run Outlines
**Strongest 1: multi_timeframe_ema_cloud.py (CRYPTO)** — Standout PF/WR/Shapre on n=29 (gate-viable); promoted; fresh (not in registry/firings).

**Strongest 2: inverse_goldmine_stocks (EQUITY)** — Highest conviction hygiene beneficiary + theoretical edge; aligns EQUITY 90day + Firing 10 expansion; parent data real (n=85).

### 3.1 Run Outline for multi_timeframe_ema_cloud (Post-Hygiene, M-107 First)
1. **Registry Pre-Reg (mandatory before re-backtest):**  
   Edit `reports/hypothesis_registry.json` (append):  
   ```json
   {
     "id": "H-BABY-CRYPTO-EMA-CLOUD-001",
     "hypothesis": "Multi-timeframe 4-layer EMA cloud + expansion + volume confluence delivers >70% WR / PF>3 edge on liquid CRYPTO (25 symbols) in 1H/4H.",
     "asset_class": "CRYPTO",
     "strategy_name": "MultiTimeframeEMACloudStrategy",
     "source_file": "baby_strategies/multi_timeframe_ema_cloud.py",
     "prior_evidence": {"backtest": {"n":29, "WR":0.7241, "PF":6.9515, "Sharpe":7.46, "date":"2026-03/04"}, "meta_path":"baby_strategies/multi_timeframe_ema_cloud.py.meta.json"},
     "pre_reg_date": "2026-05-21",
     "status": "pre-registered",
     "expected_gates": ["all 8 per 6GATES_V1"],
     "tags": ["baby", "technical", "MTF", "firing11"]
   }
   ```
   (See hypothesis-registry skill + M-107.)

2. **Backtest Refresh (hygiene-aware data):**  
   ```bash
   # Use/enhance baby harness (or integrate signals into alpha_engine for resolver path)
   python baby_strategies/backtest_framework_runner.py \
     --strategy multi_timeframe_ema_cloud \
     --symbols "BTCUSDT,ETHUSDT,SOLUSDT,..." \
     --timeframe 1h --lookback 180d \
     --output backtest_results/firing11_ema_cloud_trades.json
   # Or: python baby_strategies/baby_strategies_backtest.py --filter ema_cloud
   # Capture: entry/exit, pnl_pct, direction, asset_class=CRYPTO (post-infer)
   ```

3. **6/8-Gate Validation (core harnesses):**  
   ```bash
   # Basic stats + G7/G8
   python tools/validate_resolved_picks.py \
     --min-trades 20 \
     --by-asset-class CRYPTO \
     --strategy-filter "ema_cloud|MultiTimeframeEMACloud" \
     --input backtest_results/firing11_ema_cloud_trades.json \
     --output reports/continual_research/6gate_validation/firing11_ema_cloud_validate.json

   # Full 8 gates (G1-6 statistical + bootstrap/WF/MC)
   python tools/kimi_research_2026_05_20/six_gate_validated_strategy.py \
     --picks-file reports/.../firing11_ema_cloud_validate.json \
     --asset-class CRYPTO \
     --min-n 20 \
     --run-all-gates \
     --bootstrap-iters 1000 \
     --wf-windows 4 \
     --output reports/continual_research/6gate_validation/firing11_ema_cloud_8gate.json
   ```
   Expected: High chance G1/G3/G5/G6/G7/G8 pass (from prior metrics); G2/G4 critical (n=29 limits WF windows — may need relaxed or more data). Compare vs scrambled noise.

4. **Post-Run:** Update registry verdict + living report A/B. If 6+/8 + edge_stability >50% lower CI + no regime leak: wire as sidecar or promote. Add to CRYPTO 90day tracking.

**Adaptations:** For small n, note G4 may use fewer windows; use CRYPTO-specific (high Sharpe natural per 6GATES).

### 3.2 Run Outline for inverse_goldmine_stocks (EQUITY, Post Firing 10 Hygiene)
1. **Registry Pre-Reg:** Similar H-BABY-EQUITY-INV-GOLDMINE-001; cite parent n=85 PF0.38 + theoretical inverse PF 2.61; "benefits Firing10 tagging hygiene".

2. **Backtest:** yfinance stocks (focus AMD, NVDA, MARA, PLTR per config + parent exposure). Flip direction on goldmine signals or independent fade. Use equity backtest paths (e.g. equity_strategies or vt_baby). Ensure post-`FIRING9_TAGGING_BACKFILL_SCRIPT` + hygiene patch (no crypto pollution in EQUITY tags; use FIRING10_CURRENT_POLLUTION_ANALYZER pre/post).

3. **Validation:** Same `validate_resolved_picks.py --by-asset-class EQUITY --min-trades 10` (relax per 6GATES sparse data note) + `six_gate...` (relax G1 Sharpe >=0.8? for equities; G4 harder). Explicitly test tagging: assert no ETH-USD etc in EQUITY slice.

4. **Special:** Run after hygiene merge + backfill (per FIRING11 playbook). Size 0.5x per meta. If passes: strong T2 evidence for EQUITY 90day.

**COMMODITY candidate (copper...):** Similar flow but yfinance futures (HG=F, PL=F), proxy only (or historical COT), post-guard verification (`_is_cot_row_public`), asset_class=COMMODITY. Expect small n initially.

---

## 4. A/B Placement Recommendations & Next Steps
**A_passed (proceed to wiring/shadow/live after gates):**  
- multi_timeframe_ema_cloud (if 6+/8 + WF ok; high stats warrant priority CRYPTO slot).  
- inverse_goldmine_stocks (if forward n>=20 confirms theoretical; hygiene-cleaned EQUITY T2 booster).

**B_failed / refresh (needs work or more data):**  
- rsi_pairs_arbitrage, moving_average_slope_momentum, logistic (PF>1 but borderline WR/sharpe; retest post any resolver fixes; high n good for power).  
- copper_platinum_cot_momentum (add meta + numeric backtest; run post-guard).  
- commodity_*_py, forex_*_rehab (add .meta + evidence; low current data).  
- liquidation_cascade (relax conditions, larger n).  
- Small-n high-PF metas (vol_scaled etc.): aggregate or ignore for gates.

**90-Day Plan Expansions Enabled:**  
- **CRYPTO:** Add 2-3 baby technicals to alpha_engine/crypto_* + 90day tracking (fresh high-PF).  
- **EQUITY:** Wire inverses (goldmine/earnings/value) as mutations per M-xxx; use as T2 evidence + hygiene validation case study.  
- **COMMODITY:** Promote copper COT-proxy + trend/range as diversification (reduce CT=F 73%); re-agg post-guard in edge_stability_COMMODITY.json.  
- **FOREX:** Low yield; use rehab patterns if any numeric emerge.  
- **General:** Update living report + CYCLE summary; spawn subagents for parallel gate runs on these; link from updates/index.html.

**Risks/Blockers:** n small for some → G4/G2 power low (per 6GATES CRYPTO G4 only 22% pass rate historically). Tagging hygiene must be merged first (else EQUITY/COMMODITY polluted). M-107 registry before retest. No real-money until full admissible + 30d shadow.

**Immediate Actions (Firing 11):**  
1. Registry entries + hygiene patch application (per playbook).  
2. Backtest the 2 strongest + copper (parallel subagents).  
3. 8-gate runs + update living report / 90day plans.  
4. PR for any wiring (e.g. EMA cloud to CRYPTO bundle).

All fully cited, production-grade research. Ready for engineering window or next 30m firing.

**Report Location:** This file + cross-link in `updates/2026-05-21-continual-6gate-asset-class-research/index.html` (Research Log section) and `reports/CONTINUAL_STRATEGY_RESEARCH_BASELINE.md`.

---
*End of Firing 11 Baby + 90-Day Expansion. Subagent complete.*
---

## 2026-05-24 — Institutional-Readiness Refresh

The 4-AI consult + 5-engine swarm second-opinion on 2026-05-24 produced [reports/INSTITUTIONAL_READINESS_PLAN_2026-05-24.md](../../INSTITUTIONAL_READINESS_PLAN_2026-05-24.md). The baby-strategy 90-day expansion catalogued in this doc remains the **strategy candidate pipeline**, but the **promotion criteria** now follow the two-stage gate:

- **Stage 1 (paper-trustworthy, what a baby strategy must hit to be considered for live emission):** PF>1.3 / WR>48% / Sharpe>1.0 / MDD<25% / n≥100 / 90 days clean / monotonic Platt-calibrated score / passes lookahead-CI guard.
- **Stage 2 (institutional, what a candidate must hit before sized-up real-money allocation):** PF>1.5 / WR>50% / Sharpe>1.5 / MDD<20% / n≥100 / 6 months clean.

**Specific impacts on the FIRING 11 baby strategy candidates:**

- **`funding_arb` family (CRYPTO)** — still the highest-conviction. Stage-1 requires the freshness-30s gate + funding-rate freshness check (Bybit/Binance/Hyperliquid free APIs). Must pass Workstream A4 lookahead CI on the funding-rate timestamp.
- **`vt_pattern_sweep.py` (EQUITY, n=245/PF 1.479)** — Stage 1 is within reach. Requires Workstream B2 macro-calendar blackout to prevent earnings/CPI contamination from inflating the apparent edge.
- **`multi_timeframe_ema_cloud` (PF 6.95)** — too good to be true; PF 6.95 is the kind of number that usually means lookahead. **Must clear Workstream A4 CI** before any promotion consideration.
- **H-037 (ETF VIX carry, n=1185)** — best Stage-1 candidate by sample size. Wire VIX freshness check; calibrate per Stage 1.
- **H-017 liquidation cascade** — CRYPTO speculative; auto-gets `speculative_flag=True` per D1 Step 1.
- **E-ANON-001** — needs source_id lineage (Workstream G3) before any forward emission. "Anonymous" sources do not pass governance.

**Calibration & explainability rule (Workstream G5):** every baby strategy that graduates to live emission must surface "why it fired" in the per-pick explainability modal — gate names that passed, top-3 feature contributors, source provenance, calibrated score percentile. No black-box promotions.

**CI gate (Workstream G4):** any PR that adds or modifies a baby-strategy emitter must pass the golden hold-out regression — back-test on the frozen golden set must not lose > 5% PF vs main. The continual research loop fires that test on each emitter graduation.
