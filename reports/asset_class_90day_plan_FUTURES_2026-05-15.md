# Asset Class 90-Day Plan: FUTURES (Financial / Index / Rates / FX Futures — Separate from COMMODITY) — 2026-05-15

**Author:** Senior Quant (Grok "money-maker-continual-improve" mode)  
**Date:** 2026-05-15  
**Scope:** Deep skeptical audit of the *separate* FUTURES asset class (financial futures: equity index, interest rates, FX; distinct from physical-commodity futures in COMMODITY). Covers symbol coverage (15 tickers), why n≈0 activity, data quality (yfinance continuous contracts, roll mechanics, gaps), relationship/misclassification with COMMODITY, 4 academic strategies in `alpha_engine/futures_strategies.py`, quality gates, and concrete recommendation (revive / merge / deprecate).  
**References (concrete citations):** `audit_dashboard/data/dashboard_data.json` (2026-05-15T02:06Z: FUTURES "insufficient_data" n=0 / resolved_n=0 / sizing_allowed=false), `non_crypto_agent/data/futures_picks.json` (2026-05-14: total_raw=3, quality=0, picks=[], live WR 0.0% 0/3), `alpha_engine/futures_strategies.py:457` (FUTURES_STRATEGIES registry: futures_tsmom, futures_connors_rsi2, futures_cross_asset_momentum, futures_vol_regime_breakout), `alpha_engine/config.py:649-668` (FUTURES_SYMBOLS + overlap GC/SI/HG with COMMODITY), `audit_trail/dashboard_generator.py:3344-3350` (_COMMODITY_ROOTS vs _INDEX_FUTURES_ROOTS classification; 70%+ =F activity routed to COMMODITY), `audit_trail/quality_gates.py:1317` (BLOCKED_ASSET_CLASSES removed FUTURES 2026-04-16 but -60 penalty + BLOCKED_ASSET_STRATEGY_PAIRS kills old variants; SMART_PICKS_MIN_SCORE_FUTURES=45), `reports/{asset_class_deep_dive_FUTURES_2026-05-12.md, futures_deep_dive_round2_2026-05-13.md, audit_asset_feedback_2026-05-05T0121Z_FUTURES.md, fix_FUTURES_20260505T005402Z.md, MASTER_ACTION_PLAN_2026-05-15.md (M-027)}`, `reports/asset_class_90day_plan_COMMODITY_2026-05-15.md` (notes 73% CT=F concentration + overlap), `non_crypto_agent/main.py:388-391` (strategy calls + curate_quality_picks futures conf≥0.50 / elite≥55 / rr≥1.15 / vix/mtf/sl gates).

**Core Verdict (lead with the answer):**  
**FUTURES is genuinely dead / has almost no activity (n=0 in 2026-05-15 dashboard, 0 quality picks from 3 raw signals). It is not a viable standalone asset class today.** The tile shows "insufficient_data" / sizing_allowed=false because (1) 70%+ of all =F futures contract activity is deliberately misclassified into the COMMODITY bucket via root-symbol logic (CT=F, GC=F, HG=F, NG=F, KC=F etc. → COMMODITY; only ES/NQ/ZN/6E etc. → FUTURES), so the "COMMODITY" T2-beating numbers (PF 2.49/61.5% but COT-overemission polluted per today's COMMODITY audit) are actually commodity-*futures* CTA performance; (2) the 4 academic strategies wired for the true FUTURES symbols (TSMOM Moskowitz 2012, ConnorsRSI2, cross-asset mom Gargano 2019, vol-regime Donchian+ATR) produce almost zero signals that survive curation in the current regime (sideways/low-vol/no-breakout markets) and fail elite_score / rr / vix / mtf gates; (3) historical baggage: old futures variants killed for 0-6.3% WR (n=2-56), quarantined, blocklist pairs, data-starvation catch-22 even after unblock. Symbol universe exists on paper (15 tickers) but data quality is yfinance-continuous only (synthetic rolls distort levels, volume unreliable, no OI/term structure, Globex 24h vs daily bar gaps). **No independent edge proven for financial futures here** (unlike commodity futures COT/carry sleeve). **Recommendation: MERGE (reclassify all =F contracts under a unified FUTURES / COMMODITY_FUTURES tile) + deprecate the empty separate FUTURES bucket.** Redirect financial-futures research (index overnight drift, rates carry, FX macro) as OPT_IN sleeve inside the existing COMMODITY CTA framework (or rename COMMODITY → FUTURES_CTA). Do NOT revive standalone — it would duplicate COMMODITY's futures plumbing and split already-thin n. Prioritize only after COMMODITY COT hygiene + classification fix; otherwise fold into EQUITY macro or research-only. This advances Goal #1 (phenomenal performance visibility across classes on /audit) without creating a zombie tile.

---

## 1. Latest Performance from dashboard_data.json + Recent Reports (2026-05-15 snapshot)

**From `audit_dashboard/data/dashboard_data.json` (generated 2026-05-15T02:06:57Z, repo_sha 35d3e77):**
- **FUTURES asset_class_health:**
  - status: "insufficient_data", sample_tier: "insufficient", sizing_allowed: false
  - n=0, resolved_n=0, win_rate=0.0, total_pnl_pct=0.0, profit_factor=null
  - circuit_breaker: {breached: false, reason: "no_backtest", realized_n_30d: 0}
  - min_display_n:10, min_candidate_n:50, min_stable_n:100

- **by_asset_class / concentration:** empty for FUTURES (no entries). Compare COMMODITY: n=322 resolved, WR 61.5%, PF 2.49, 73.36% PnL mass on CT=F via cot_positioning (but post-forensic COT over-emission collapses real n≈5, WR40%, PF0.17 per `cot_paper_pilot_overemission_falsified_20260513.md` + `cot_pipeline_audit_20260514.md`).

**Historical snapshots (pre-2026-05-15):**
- `non_crypto_agent/data/futures_picks.json` (2026-05-14T22:31): total_raw=3, quality=0, picks=[], symbols_tracked=15, strategies_run=4, "Live WR: 0.0% (0/3 closed) — CRITICAL: no dedicated futures strategies existed [pre-2026-04]. 4 new strategies deployed..."
- `edge_stability_FUTURES.json` (2026-05-12): n_total=0 across all windows (7d/30d/90d/all); wilson_ci [0,0]
- `asset_class_deep_dive_FUTURES_2026-05-12.md`: 6 paper-only strategies in blocklist (futures_rsi_divergence etc.), BLOCKED in hedge_fund_sprint, 5.9% WR residual n=2, zero /audit tile picks.
- `futures_deep_dive_round2_2026-05-13.md` + `fix_FUTURES_20260505`: n=0 (or historical n=2/17 at 6.3% WR / 100% on n=2), "mostly real but COMMODITY is hidden FUTURES bucket", old strats 0% WR.
- `audit_asset_feedback_2026-05-05T0121Z_FUTURES.md`: n=2, 100% WR (noise), "not analyzable... do not report until n>=100".
- `MASTER_ACTION_PLAN_2026-05-15.md`: M-027 "FUTURES Thursday short momentum (+2.56% n=9)" PENDING (DOW gate; require n>30); table notes "FUTURES | n=2 | needs accumulation 90d | Donchian breakout system".

**Brutal observation:** The class has been in "insufficient" / zombie state for months. Any quoted WR (5.9-100%) is n<20 noise. The 3 raw signals on 2026-05-14 were generated by the 4 new strategies but 100% rejected in `curate_quality_picks` (likely low_confidence <0.50 or elite<55 or rr<1.15 or vix_hard_block or mtf_rsi or sl_distance_floor). No active picks, no smart_picks, no shadow/live emission.

---

## 2. Symbol Universe Size, Liquidity & Concentration Risk

**Defined universe (`alpha_engine/config.py:649-668` FUTURES_SYMBOLS):**
- 15 entries (plus 3 commented/removed like CL=F):
  - Equity index futures (CME/CBOT): ES=F (S&P 500 E-mini), NQ=F (Nasdaq 100 E-mini), YM=F (Dow E-mini), RTY=F (Russell 2000 E-mini)
  - Metals (overlaps COMMODITY): GC=F (Gold, COMEX), SI=F (Silver), HG=F (Copper)
  - Rates / bonds (CBOT): ZN=F (10Y T-Note), ZT=F (2Y T-Note), ZB=F (30Y T-Bond)
  - FX futures (CME): 6E=F (Euro), 6B=F (GBP), 6J=F (JPY), 6A=F (AUD), 6C=F (CAD)
- Note: **CL=F explicitly removed** from both FUTURES and COMMODITY ("26 futures trades, 3.8% WR, -29.82% PnL — worse than random").
- COMMODITY_SYMBOLS (config:615-646) has ~25 largely overlapping =F: GC/SI/HG/NG/PL/PA + full ags (CT=F cotton flagship, KC/SB/CC/ZC/ZS/ZW/LE/GF/HE/OJ) + energy proxies (BZ/RB/HO) + ETFs (USO/UNG/DBA). CT=F classified COMMODITY despite being ICE futures contract.
- **Overlap verdict:** GC=F, SI=F, HG=F appear in *both* dicts (cat="futures" vs "commodity"). Classification root-prefix decides tile (`dashboard_generator.py:3344`: _COMMODITY_ROOTS = {CL,GC,HG,NG,SI,...CT,...} → COMMODITY; _INDEX_FUTURES_ROOTS={ES,NQ,YM,RTY,ZN,ZB,ZT,6E,...} → FUTURES). Result: ~70% of real futures PnL mass (per round2 report) lands in COMMODITY tile.

**Liquidity realities (contract specs + known yf behavior):**
- ES/F NQ etc: Excellent (Globex, deep books, micros MES/MNQ/MYM/M2K exist but *not used* in FUTURES_SYMBOLS or strategies — high notional risk for full-size).
- GC/SI/HG: Excellent (COMEX), but already "owned" by COMMODITY COT/carry.
- ZN/ZT/ZB: Good but lower vol; term-structure / curve trades ignored.
- 6E/6B etc: Liquid G10 FX futures, but carry/interest-rate diff edge (Lustig et al) not implemented beyond one proposed pilot.
- **Concentration risk:** Zero in FUTURES (n=0). In COMMODITY: 73% on single CT=F (high unit risk ~$35k notional, $1500 daily limit move, no micro, ICE physical delivery basis risk).
- **Gap:** No micro-contract mapping (MES etc), no per-symbol liquidity/position-size matrix in quality_gates or data_quality_gates.yaml (only generic commodity: symbols_min:5, roll_yield_check).

**Verdict:** Universe exists but split artificially; financial futures side has no volume/activity while commodity futures side (mislabelled) carries the class "edge".

---

## 3. Data Quality & Outcome Tracking for (Financial) Futures

**Strengths:**
- yfinance provides free daily continuous OHLCV for all =F (used in futures_strategies + non_crypto fetch).
- Strategies implement solid academic logic (inverse-vol sizing, ATR TP/SL capped 8%/5%, rr floors 1.2-1.5, ADX>20 + ATR expansion for breakouts, SMA200 filter for Connors).
- outcome_resolver.py aware of class-FUTURES (5bp PNL_WIN_THRESHOLD).
- Some historical backtests referenced (e.g. M-027 Thursday short momentum n=9 +2.56%).

**Major Weaknesses (brutally documented):**
- **yfinance continuous =F series quality issues (same as COMMODITY report flags):** 
  - Synthetic roll adjustment (ratio or additive) distorts absolute price levels used for entry/TP/SL in _futures_tp_sl — realistic live fills on front-month contract differ.
  - Volume: often summed across contracts or front-month only; unreliable for liquidity filters.
  - No open interest, no exact first_notice/expiration dates → poor roll-yield or basis modeling (critical for rates/FX, less for pure mom).
  - Gaps / settlement artifacts around quarterly rolls (Mar/Jun/Sep/Dec for index; monthly for some FX).
  - 24h Globex trading vs single daily bar (yf default 00:00-23:59 or exchange tz) misses overnight session edges (e.g. proposed mes_overnight_drift in round2).
- **No dedicated futures data feed:** Unlike potential CQG/IBKR/Refinitiv for accurate front-month + continuous unadjusted + OI. Same yf used for COMMODITY (where COT + carry_momo.json are the real differentiators, not price series).
- **Outcome tracking gaps:** 
  - Historical closed_picks for FUTURES predate the 4 new strategies (old variants 0% WR killed).
  - dashboard_generator / MySQL still reflect pre-unblock starvation (n=0 today).
  - No CPCV/DSR/PSR on the 4 strats (unlike COT pilot's attempted but falsified DSR=1.0).
  - `futures_picks.json` explicitly calls out "no dedicated futures strategies existed" until Apr 2026 deployment; 0/3 closed since.
- **Regime mismatch:** TSMOM (trend-following) fails in low-vol/chop (common 2026 regime per EQUITY/CRYPTO audits); ConnorsRSI2 requires deep RSI(2)<5 + SMA200 + not crash (rare in current data); vol-breakout requires ADX expansion (false breakouts filtered but also kills signals); cross-asset requires ZN momentum alignment (may not fire).
- **Gates too strict for thin class:** In `non_crypto_agent/main.py:431` futures conf_floor=0.50 (same as commodity), but strategies cap confidence ~0.55-0.83; elite_score >=55 hard (no symbol_pf_boost for most financial futures?); rr>=1.15; + vix_hard_block (LONGs blocked VIX>30), mtf_rsi_confluence, sl_distance_floor. 3 raw signals failed all → quality=0.
- **Roll mechanics absent:** No explicit front-month roll logic or contango/backwardation adjustment in any futures_strat (unlike academic CTA or Miffre carry in commodity_carry_momo.json).

**Verdict on data quality:** Sub-institutional for financial futures. yf continuous is "good enough" for sign-of-momentum research but insufficient for production TP/SL, sizing, or roll-sensitive strategies. COMMODITY benefits from CFTC COT ground-truth + seasonal (not available for ES/ZN/6E). Explains zero activity.

---

## 4. Relationship to COMMODITY Strategies & Broader System

- **Misclassification is the dominant reason FUTURES appears dead:** Per `futures_deep_dive_round2_2026-05-13.md`: "COMMODITY is a hidden FUTURES bucket". All CT=F (73% COMMODITY PnL), GC=F, HG=F, NG=F, KC=F etc. picks are =F contracts but tagged COMMODITY. The FUTURES tile only ever sees the financial subset (index/rates/FX), which has zero proven production edge.
- **COMMODITY's "edge" is futures:** COT on CT=F (over-emitted historically), carry_momo on 18 ag/energy/metals futures, seasonal. The 4 futures_strategies are *not* used for COMMODITY symbols (COMMODITY uses separate commodities_strategies + cot_paper_pilot + carry).
- **Strategy split:** futures_strategies.py (4 academic, financial-focused, safe_contracts subset for vol-breakout) vs multi_asset/commodity_futures_strategies.py (separate for COMMODITY).
- **Gates / blocklist history:** FUTURES had dedicated BLOCKED_ASSET_STRATEGY_PAIRS kills ("futures_momentum", "futures_ema_stack_momentum", "futures_mean_reversion", "connors_rsi2" variants) + old paper-only strats in strategy_blocklist. New 4 are clean but unproven in live (0 closed).
- **Non-crypto agent unifies fetch** (NON_CRYPTO_SYMBOLS includes both dicts) but classification downstream splits tiles.
- **Master plan / audit:** M-027 pending for FUTURES specifically; COMMODITY has M-008/021/022/050 (COT lag/dedup + carry wire). No cross-reference wiring between the two futures books.
- **/audit surface:** Separate tiles hide that "phenomenal COMMODITY" = mostly futures contracts. Violates transparent per-class visibility (Claude.md Goal #1).

**Hidden insight:** The system already *has* a working futures engine (commodity side via COT/carry + yf), but the label "FUTURES" was reserved for the underperforming financial side. This is backwards — financial futures (equity index overnight, rates, FX carry) have extensive literature (Asness, Lustig, Donchian) but zero realized sample here.

---

## 5. Why This Class Is Performing Poorly / Has Almost No Activity — Root Causes

1. **Classification tax (70%+ effect):** Real futures volume/PnL hidden in COMMODITY → FUTURES tile starved of data → appears n=0 → further deprioritized.
2. **Strategies not firing in regime + fail gates:** 4 strats academic but rigid; current market (per other class audits) lacks strong multi-horizon trends, deep RSI2 oversolds on index, or ADX+ATR breakouts. The 3 raw on 2026-05-14 all rejected (curate_quality_picks + vix/mtf/sl).
3. **Historical self-fulfilling kill loop:** Pre-2026-04 only 3 trades total → variants killed for low WR → blocklist/penalty → data starvation → n remains 0 even after 4 new strats deployed Apr 2026.
4. **Data feed inadequate for the class:** yf continuous sufficient for COMMODITY COT overlay but poor for financial futures (no curve, no session breakdown for overnight drift, roll artifacts).
5. **No micro / realistic sizing:** Full-size ES/ZN notional too large for safe paper-to-live; micros (MES etc) proposed in round2 but never added to config/FUTURES_SYMBOLS or wired.
6. **Missing drivers for financial futures:** No policy-rate, yield-curve, risk-parity, or COT-for-FX (TFF reports exist but unused). COMMODITY has COT + carry + seasonal; FUTURES has only price mom/meanrev.
7. **Wiring gaps:** Strategies wired only in non_crypto_agent (paper-only path?) and alpha_engine/scanner; no dedicated futures agent like quan_engine or cot pilot; not in hedge_fund_sprint set without unblocks.
8. **Small true N + no validation:** n=0-9 historical; no CPCV/DSR on the 4 strats; graduation gates never reached.

**Not "revivable with minor param tweak"** — structural (classification + data + missing micro + regime-inappropriate rigid academic rules without adaptation).

---

## 6. 90-Day Plan — Concrete, Phased, Measurable (Success = Merge or T2-Eligible Sleeve)

**Primary Recommendation: MERGE + deprecate separate FUTURES class (P0).** Re-route all =F contracts (COMMODITY_ROOTS + INDEX_FUTURES_ROOTS) to a single "FUTURES" or "COMMODITY_FUTURES" asset_class label (update dashboard_generator.py + asset_class_health + tiles + MASTER_ACTION_PLAN). Keep COMMODITY for any non-futures commodity exposure (ETFs USO etc as proxy only). This gives /audit one honest "futures CTA" tile with real n≈322+ (post COT clean) + financial sleeve pilots. Financial futures research (overnight drift, Asia MR on MGC, FX carry) becomes OPT_IN sub-strategies inside the unified futures book. Deprecate empty "FUTURES" bucket to avoid zombie class. If separate kept (not recommended), treat as research-only, no sizing.

**Phase 1 — Hygiene + Classification Fix + Micro Add (Days 0-14, P0)**
- Patch `audit_trail/dashboard_generator.py:3344` (add env MAP_ALL_FUTURES_TO_FUTURES=1 or contract_type tag) so all =F → FUTURES tile (or unified name). Update _derive_asset_class, by_asset_class aggregation, concentration. Expected: FUTURES n jumps to ~440 closed (carry-over from COMMODITY), PF~2+ (post COT dedup).
- Add micros to config.py FUTURES_SYMBOLS + COMMODITY if merged: "MES=F", "MNQ=F", "MGC=F", "MYM=F" (lower notional, realistic sizing for paper).
- Update quality_gates.py: remove any lingering FUTURES penalties for new strats; set min_trades=0 for new pilots; wire futures_tsmom etc to SMART_PICKS if desired.
- Seed dedup / freshness for any new financial COT (TFF reports) if pursued.
- Update MASTER_ACTION_PLAN_2026-05-15.md Section 21 + M-027 to reference merge.
- Success metric: dashboard FUTURES n_resolved ≥50 (post re-agg), tile visible with real history; 0 "insufficient_data".

**Phase 2 — Wire 3 Targeted Pilots + Shadow Emission (Days 14-45)**
- Implement (or revive from round2 proposals) in alpha_engine/futures_strategies.py or new pilots:
  1. mes_overnight_drift (ES proxy): LONG 16:00 ET exit 09:30 next (Asness overnight edge), VIX<25 filter, TP0.4% SL0.5%. Expected 60%+ WR, n≥80/mo.
  2. mgc_asia_mean_reversion (GC/MGC): 18:00 ET RSI(14)<35 LONG to 03:00 London (Asia overshoot lit), TP0.3% SL0.45%.
  3. m6a_carry_sign (6A=F or AUD): LONG when 3M rate diff >0 + 20d SMA slope >0 (Lustig carry), weekly update.
- Use micro contracts in paper sim (theswarm account style).
- Wire to non_crypto_agent + scanner + shadow via quality_gates (new BLOCKED_ASSET_STRATEGY_PAIRS only if fails).
- Add to commodity_carry_momo.json style or new futures_carry if merged.
- Success: ≥30 independent resolved paper trades across pilots, PF≥1.4, WR≥52% on 30d rolling; DSR >0.5 on CPCV walk-forward (use existing anti_overfit tools).

**Phase 3 — Validation, CPCV/DSR, Graduation Gate (Days 45-75)**
- Run 30d+ paper pilot + forward_test (like COT pilot_status.json).
- Full Lopez de Prado CPCV + DSR/PSR on combined sleeve (target DSR≥0.8 for T2 candidate).
- Cross-asset corr check vs EQUITY/CRYPTO <0.6.
- Update edge_stability_FUTURES.json + dashboard health.
- If merged: integrate with existing COT/carry on CT/GC so unified futures n≥200, PF≥1.6, WR≥52%, MDD<18%, concentration ≤30% per symbol/strategy (fix COMMODITY 73% CT risk as byproduct).
- Success: graduation_gate = "LIVE_ELIGIBLE" or "T2-candidate" (PF>1.5/WR>50/MDD<20/n>100) *and* beats EQUITY T2-candidate on risk-adjusted basis; else archive pilots.

**Phase 4 — Gate or Deprecate (Days 75-90)**
- If Phase 3 passes + COMMODITY COT cleaned: size micro (0.25-0.5% risk/unit) in shadow then micro-live (user approval per NFA).
- Else: deprecate financial futures sleeve (keep only commodity futures in unified class); redirect capital to ETF/BOND expansion (n→100 charter floor) or EQUITY vix-regime.
- Update /audit template, reports/hedge_fund_performance_review, data_quality_gates.yaml (add futures_roll_check, micro_notional_cap).
- Document in updates/ + findtorontoevents.ca/audit notes.

**Risks / NFA:** 
- Merge has low blast radius (label change + 1 PR) but requires dashboard re-gen + historical re-class (pollutes old COMMODITY stats temporarily — use as-of flag).
- New pilots unproven; yf data artifacts can inflate backtests (use anti_overfit_audit_sidecar.py + real fills verification).
- Single-symbol concentration (CT or ES) remains system risk — enforce ≤25-30% per future.
- Research surface only. No real-money on FUTURES or merged sleeve without explicit graduation + user sign-off + 6-stage rehab per institutional policy (TESTING_PROTOCOL.MD).

**Expected Impact on /audit (Goal #1):** Eliminates zombie "FUTURES insufficient" tile; unifies ~all futures activity into one honest CTA/FUTURES bucket with visible n/PF/WR (post COT fix); surfaces whether financial futures add orthogonal edge or are noise. Aligns with SUPREME_PLAN per-asset diversification. If edge survives merge + pilots better than EQUITY T2-candidate (PF 1.41+), size; else de-risk and note "futures edge = commodity contracts only (COT/carry)".

**Next immediate actions (no auto-run):** 
- Open focused PR for classification patch (Wire-Up compliant, small blast radius).
- Swarm review of this 90day + round2 pilots.
- Update MASTER_ACTION_PLAN M-027/M-0xx with merge decision.
- Re-gen dashboard after patch to confirm n lift.

This plan is brutally honest, evidence-based (file:line + report citations), and executable in 90d without scope creep. Prioritize only if it advances phenomenal performance; otherwise merge-and-archive is the cleanest path.

---
**NFA / Disclaimer:** All analysis research-grade. Past (polluted) performance no guarantee. Contract specs, yf data, and live slippage not stress-tested at scale. Consult risk/compliance before any sizing. Report produced 2026-05-15 per "money-maker-continual-improve" skill without running forbidden heavy scripts (check_active_picks / smart_picks_engine).

**Refs for follow-up:** All cited files + `reports/asset_class_90day_plan_COMMODITY_2026-05-15.md` (COT falsification details), `futures_deep_dive_round2_2026-05-13.md` (pilot specs), `alpha_engine/futures_strategies.py:74-462` (full strategy code).