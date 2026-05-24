# Asset Class 90-Day Plan — BOND — 2026-05-15

**Senior Quant Audit** using the "money-maker-continual-improve" skill (brutally skeptical, citation-driven, hedge-fund-grade lens per `reports/hedge_fund_performance_review_*.md` tier table).  
**Focus areas** (per task): tiny sample (n=11 vs charter floor 100), extreme concentration (TLT/HYG), data sources (FRED availability + corporate bond proxies), root causes of weak performance, feasibility of universe expansion (14 symbols on paper), realistic 90-day plan or explicit de-prioritize recommendation.  
**Data sources (all concrete citations)**: `audit_dashboard/data/dashboard_data.json` (2026-05-15T02:06:57Z, sha 35d3e77), `reports/{asset_class_deep_dive_BOND_2026-05-12.md, bond_root_cause_2026-05-12.md, bond_deep_dive_round2_2026-05-13.md, bond_regression_deep_dive_2026-05-15.md, bond_overlay_attempts_20260513.md, commodity_bond_forensic_2026-05-13.md, MASTER_ACTION_PLAN_2026-05-15.md (M-020/M-024/M-032), audit_asset_feedback_2026-05-05T0121Z_BOND.md}`, `alpha_engine/{config.py:781 (BOND_SYMBOLS 14 entries), bond_strategies.py (6 strategies + BOND_STRATEGIES dict), bond_data_fred.py, bond_scanner.py, forward_validator.py:397 (FORWARD_GATE_OVERRIDES), production_scanner.py}`, `.github/workflows/{bond-agent.yml (BOND_ELITE_FLOOR, SKIP_FRED=1, BR-3 merge), alpha-engine-bond.yml}`, `non_crypto_agent/data/bond_picks.json` (2026-05-14T15:20), `alpha_engine/data/active_picks.json` (0 BOND), `baby_strategies/bond_yield_curve_momentum.py`, `audit_trail/dashboard_generator.py:3925+`.

**Core Verdict (lead answer, no hedge):**  
**BOND is not a money-maker and should be de-prioritized for any real-money sizing (shadow or live) for the full 90 days.** Current metrics (n=11 resolved, PF 0.66, WR 54.5%, total_pnl_pct −1.53%, thin_sample, sizing_allowed=false, tier=WARN) are statistically meaningless noise from a 2-symbol (TLT 79% share) concentration that has already regressed from the prior legacy-inflated snapshot (n=18 / PF 1.72 / WR 55.6% on 2026-05-03). The 11 closed picks are dominated by TLT LONG duration bets in an adverse rate regime; the dedicated bond emitter (bond-agent.yml) produces ~10 raw signals/day but 0 quality because the elite_score floor (default 40) is unreachable for structurally low-vol bond ETFs. Legacy ZN=F futures_momentum mis-classifications (per `commodity_bond_forensic_2026-05-13.md` and `bond_root_cause_2026-05-12.md`) have rolled off, exposing the true desert. 14-symbol universe exists in `config.py` since 2026-04-17 expansion but effective coverage is 2 ETFs. Three research-backed pilots (Fleckenstein-Longstaff-Lustig TIPS MR, Cochrane-Piazzesi curve carry + MOVE gate, Frazzini-Pedersen HYG-LQD credit MR) are fully specified in `bond_deep_dive_round2_2026-05-13.md` but unwired. Forward gate override ("bond":10) and merge step (BR-3) are now in code; elite floor reduction and pilot implementation have not shipped. BOND violates charter floor by 9×, shows no path to Tier-2 (PF>1.5/WR>50/MDD<20/n≥100) without 60-90 days of disciplined sidecar work that yields lower ROI than COMMODITY (CT=F PF 2.49 post-COT fixes) or EQUITY (T2-candidate PF 1.41-1.57). **Recommendation: treat as pure research / opt-in sidecar only (Wire-Up compliant, zero blast radius). Freeze dedicated emitter sizing path. Revisit only after n≥50 clean post-expansion + per-pilot DSR/CPCV validation. Do not update /audit banner or master-plan institutional timeline for BOND.**

---

## 1. Brutal Baseline — Live Performance (2026-05-15T02:06Z snapshot)

**From `dashboard_data.json::performance.asset_class_health.BOND` + `by_asset_class.BOND` + `asset_class_concentration.BOND`:**
- status: "thin_sample", sample_tier: "thin", sizing_allowed: false
- n=11 (resolved_n=11), closed=13 (by_asset_class), wins=6, losses=5, win_rate=54.5%
- profit_factor=0.66, total_pnl_pct=−1.53, expectancy=−0.14, avg_win=0.5, avg_loss=0.91
- circuit_breaker: breached=false but "cold_start (n=0<30)" on 30d realized
- Concentration (WARN tier): top_symbol="TLT" 78.92% share / 5.95% PnL mass; top_strategy="betting-against-beta" (kimi_riseoftheclaw) 55.59% share; honest_label="BOND edge = betting-against-beta on TLT (79% of class PnL)"; is_concentrated_warn=true, is_concentrated_block=false
- active: 0 (confirmed via `active_picks.json` scan: zero BOND-tagged or TLT/HYG/IEF/LQD entries)
- `non_crypto_agent/data/bond_picks.json` (latest 2026-05-14T15:20): total_raw=10, quality=0, picks=[], symbols_tracked=14, strategies_run=5 (note: yml now lists 6)

**vs prior snapshots (regression documented in `bond_regression_deep_dive_2026-05-15.md`):**
- ~2026-05-03 / May-5 feedback: n=18, PF 1.72, WR 55.6% (legacy ZN=F futures_momentum on ZN=F/ZB=F mis-tagged as "bond" per `commodity_bond_forensic_2026-05-13.md` and `bond_root_cause_2026-05-12.md` Layer 0). Those 7+ rows have since rolled out of the window.
- Current clean 12-pick list (from regression autopsy, excluding 1 UNRESOLVED): 6 wins (+3.005 gross) / 5 losses (−4.537 gross) on TLT (8 entries) + HYG (4 entries). PF math verified 0.66. Cosmetic bug: pick #9 TLT SL_HIT but +0.13% pnl labeled LOST (resolver status vs sign mismatch, non-metric impact).
- `edge_stability_BOND.json` (cited in round-2): n≈12, all strategies INSUFFICIENT_DATA (n≤5), top drag "betting-against-beta" PF 0.37 on TLT LONG.

**Comparison to charter / other classes (from same dashboard + MASTER_ACTION_PLAN_2026-05-15.md):**
- T2 minimum: PF>1.5 / WR>50 / MDD<20 / n≥100. BOND fails every dimension.
- COMMODITY: PF 2.49 / 61.5% / n=322 (but COT over-emission falsified, real post-dedup sub-floor).
- EQUITY: PF 1.41-1.57 / 52.7% / n=421 (T2-candidate).
- ETF: PF 1.48 / 58.5% / n=106 (just crossed floor, improving).
- FOREX: PF 0.27 (sub-floor, mutate-before-kill).
- BOND: lowest priority per supreme plan; tertiary track only.

---

## 2. Symbol Universe, Liquidity & Concentration Risk

**Defined in `alpha_engine/config.py:781-798` (BOND_SYMBOLS, 2026-04-17 expansion from 8→14 per supply-pipeline Step 5):**
- Treasury duration ladder: TLT (20+ Y long), IEF (7-10Y), SHY (1-3Y short), TLH (10-20Y), GOVT
- Credit: LQD (IG corp), HYG (HY corp), JNK (HY), EMB (EM)
- Broad/others: AGG, BND (total bond), MUB (muni), TIP (TIPS), BNDX (intl)

**CATEGORY_RISK["bond"] = (−0.04, 0.06, 15)** — 4% SL / 6% TP / 15d max hold (lowest vol bucket, correct). TRAILING_STOP["bond"]=0.04.

**Reality on the ground (effective universe):**
- 80%+ of historical + current closed picks on TLT alone; HYG secondary. Zero resolved history on IEF/SHY/TIP/LQD/MUB/BNDX/EMB per `bond_deep_dive_round2_2026-05-13.md` and regression list.
- Liquidity: All 14 are liquid US ETFs (daily volume >$100M for TLT/HYG/LQD/AGG; lower for MUB/TLH/BNDX). yfinance OHLCV daily is high-quality for these. Wider spreads vs equities (10-30bp round-trip typical for TLT).
- Concentration risk: top_symbol 79% share violates diversification (CLAUDE.md + concentration_cap.py). Single-strategy 55% PnL mass. TLT is long-duration (high beta to 10Y/30Y yields and MOVE vol); current tape (losses −1.28, −1.07, −0.97, −0.82 on TLT) consistent with "higher-for-longer" or sticky rates regime. HYG (credit) 2W/1L positive but tiny weight.
- Futures overlap note: ZN=F/ZB=F (10Y/30Y bond futures) intentionally routed to FUTURES/COMMODITY (not BOND) to avoid mis-tag; legacy ZN=F rows were the source of the old "n=18 PF 1.72" fiction.

**Verdict on universe:** On-paper 14-symbol coverage is excellent (duration + credit + intl + TIPS buckets). In-practice 2-symbol desert. Expansion requires strategy changes, not ticker list changes.

---

## 3. Data Sources — FRED, yfinance, Corporate Proxies, Gaps

**Primary for live emitter (`bond-agent.yml` + `bond_strategies.py`):**
- yfinance daily OHLCV (2y history) on all 14 BOND_SYMBOLS + extras (ZN=F, ZB=F, ^TNX, ^IRX, TLT/IEF). Reliable for ETF price action, volume, ATR. NYSE-hours only for realistic execution.
- `SKIP_FRED='1'` in bond-agent.yml env — main daily emitter deliberately avoids FRED (no timeout risk).

**FRED integration (`alpha_engine/bond_data_fred.py` + `fetch_fred_series` / `fetch_bond_bundle`):**
- Series: DGS2/DGS10/DGS30 (par yields), T10Y2Y/T10Y3M (curve), T10YIE/T5YIE (breakevens), BAMLH0A0HYM2 (HY OAS), BAMLC0A0CM (IG OAS).
- Used in: `etf-bond-scanner.yml`, `worldclass-pipeline.yml`, `bond_yield_curve_slope` (optional fred_data param), some baby/overlay attempts.
- Availability: Public FRED (pandas_datareader fallback) or fredapi with key. Rate-limited; cache in `alpha_engine/data/fred_cache/`. Earlier "FRED timeout kills emission" diagnosis (`asset_class_deep_dive_BOND_2026-05-12.md`) was **falsified** for the live bond-agent (it never called FRED); conflated with etf-bond-scanner. `bond_yield_curve_slope` can consume it when wired.
- Corporate bond reality: No free high-frequency TRACE or single-name corporate data. HYG/LQD/EMB/JNK serve as liquid ETF proxies for credit-spread MR (OAS via FRED BAML series). Acceptable for systematic but not fundamental credit selection.

**Other sources:**
- Cboe MOVE (^MOVE) for vol regime (proposed in pilots).
- No on-chain, alt-data, or earnings for pure bonds.
- `bond_pricer.py` / `bond_yield_curve_inversion.py` exist for research.

**Data quality verdict:** yfinance sufficient and stable for price/volume/ATR strategies. FRED adds macro alpha (breakeven, OAS, curve slope) at low cost but optional (SKIP_FRED works). Gap: no high-frequency or single-name corp bond depth. Resolver exits must be time+level (not yf spot) to avoid the known non-crypto live-close bug cited in round-2.

---

## 4. Why Performance Has Been Weak — Root Cause Autopsy

1. **Legacy pollution + sample turnover (primary explanation for "PF 1.72 → 0.66" headline regression):** Old n=18 included ZN=F futures_momentum (mis-classified "bond"). Rolled off → true BOND n=11 exposed as noise. See `bond_regression_deep_dive_2026-05-15.md` + `commodity_bond_forensic_2026-05-13.md`.

2. **Emitter alive but completely gated (quality=0 daily):** `bond-agent.yml` (cron 14:32 UTC weekdays) + 6 strategies in `bond_strategies.py` (yield_momentum SMA/RSI, duration_rotation TLT SMA50/200, mean_reversion BB, connors_rsi2, credit_spread_mean_reversion LQD/HYG, yield_curve_slope) produce ~7-10 raw signals but 0 pass curation:
   - confidence ≥0.50
   - risk_reward ≥1.10 (reasonable for low-vol)
   - elite_score ≥ _elite_floor (default 40 via BOND_ELITE_FLOOR var or hardcode)
   Low-vol bond signals compress elite_score magnitudes (calibrated on crypto/equity vol). `non_crypto_agent/data/bond_picks.json` consistently quality=0. BR-1 (lower floor to 32-35) never shipped.

3. **Forward gate + integration (now partially fixed):** FORWARD_GATE_MIN_TRADES=50 global (no BOND override until post-root-cause); bond_picks.json never merged to active_picks.json until BR-3 added to workflow. Forward override "bond":10 now lives in `forward_validator.py:397-400` and test. Merge step present in yml (lines 156-207) and `bond_scanner.py:_merge_into_active_picks`. Still 0 BOND in active_picks because quality=0 upstream.

4. **Concentration + regime mismatch:** 79% TLT LONG (duration bet) during tape that produced 4 material losses. "betting-against-beta" (kimi_riseoftheclaw, not pure bond-agent) dominates. No duration rotation or credit MR firing in volume.

5. **Missing proven academic edges:** `bond_deep_dive_round2_2026-05-13.md` specifies 3 code-ready pilots with expected 114 events/yr:
   - Pilot A: TIPS-Treasury breakeven MR (Fleckenstein-Longstaff-Lustig 2014) using FRED T10YIE + yf TIP/IEF.
   - Pilot B: Cochrane-Piazzesi (2005) curve-carry momentum (rank IEF/TLH/TLT by 3m return, MOVE<20d MA gate).
   - Pilot C: HYG-LQD credit-spread 2σ MR (Frazzini-Pedersen style, SPY regime filter).
   None wired to BOND_STRATEGIES or emitter. `baby_strategies/bond_yield_curve_momentum.py` exists but low contribution. `proven_research_strategies.py` grep returns 0 for bond priors.

6. **Structural low edge density + resolver cosmetics:** Bonds have tight ranges; 4%/6% caps appropriate but hard to clear high bars. Resolver SL_HIT vs pnl sign mismatch (cosmetic, fixed in recommendation of regression doc).

No evidence of data corruption or resolver-v2 systemic bias against BOND.

---

## 5. Hidden Drags, Missed Insights & External Options

**Drags:**
- `production_scanner.py` normalizes bond → equity post-admission (affects score_booster keying, erases bond-specific floors).
- Baby/kimi generic strategies (betting-against-beta, vwap etc.) tagging TLT/HYG without bond-aware TP/SL or duration metadata.
- No per-class elite_score or risk_reward override in main quality_gates.py for bond.
- FRED key not in bond-agent (but not needed for core yf path).

**Missed (in code but not live):**
- `bond_yield_curve_inversion.py`, `bond_pricer.py`.
- Academic citations in deep-dive docs but zero production modules (contrast COMMODITY `commodity_carry_momo.json` sidecar).
- Cross-asset (BOND + EQUITY VIX or YC regime) already partially in `vix_regime_gate.py` but not BOND-specific.

**External replication options (low priority):**
- PIMCO / iShares bond factor ETFs + duration/credit rotation.
- QuantConnect Lean yield-curve slope algorithms (steepener/flattener).
- DBMF/KMLM-style managed futures (but those route to COMMODITY/FUTURES).
- Hyperliquid or futures basis for bond futures (again, not BOND ETF class).

---

## 6. Feasibility of Expanding the Universe

**High on paper, medium execution risk:**
- Tickers: already 14 in config.py (no new symbols needed; just use IEF/SHY/TIP/LQD/AGG/EMB/MUB in new spread logic).
- Strategies: 6 conventional + 3 research pilots fully specced (150 LoC total). Signature matches existing `(data: dict[str,DataFrame]) -> list[pick]`. Opt-in via env flags or BOND_STRATEGIES dict.
- Data: yfinance free + sufficient. FRED optional (add secret for M-032 if richer breakeven/OAS desired; public fallback exists).
- Emission path: bond-agent.yml + bond_scanner.py + merge + forward override (10) + dashboard_generator registry all present or recently added. One-line floor change + pilot registration = emission unblock.
- Expected volume: pilots + fixed emitter → 70-95 closed picks in 90 days (conservative, accounting overlap + regime skips). Combined with legacy ~12/quarter → n≥80-100 feasible.
- Risk: low notional (bond vol << equity/crypto; CATEGORY_RISK already tuned). NYSE hours limit (after-hours spreads bad for TLT). Need rigorous per-pilot backtest (CPCV, slippage 5-15bp stress, DSR) before shadow.
- Blockers: GitHub var BOND_ELITE_FLOOR still defaults 40 (not lowered); no pilot code on disk; master plan M-020/M-024/M-032 still PENDING.
- Wire-Up compliance: all proposed changes are opt-in sidecars (env flags, new modules under proven_ or bond_*, no core mutation). Fits CLAUDE.md.

**Challenges:** Stat power at n<30 per pilot remains weak; single-name corporate depth impossible without paid data; duration timing requires accurate yield data (FRED helps).

**Conclusion on feasibility:** Trivial to unblock current emitter (1 PR: lower floor + confirm). Meaningful expansion (n≥100, diversified) requires 2-3 PRs for pilots + backtest harness + 30-60d paper validation. Low cost, high optionality, but ROI lower than COMMODITY COT hygiene or EQUITY factor sleeves.

---

## 7. Realistic 90-Day Plan (or Explicit De-Prioritize)

**Guiding principle (per CLAUDE.md Goal #1 + master plan):** Only invest dev time where edge is "best worth the risk." BOND currently fails. Plan below is minimal-effort research track only; success metrics are conservative. Parallel to (never ahead of) COMMODITY M-021, EQUITY, ETF M-036.

**Phase 1: Hygiene & Unblock (Days 0-14) — P0, low LOC**
- Set `BOND_ELITE_FLOOR=32` (or 35) default in `bond-agent.yml:53` and GitHub repo var (BR-1). Add comment citing `bond_root_cause_2026-05-12.md`.
- Verify daily runs produce quality ≥3-5 (monitor bond_picks.json + commit logs).
- Confirm merge (BR-3) lands BOND in active_picks.json and forward_validator accepts with n≥10 override.
- Minor: fix resolver cosmetic (SL_HIT status derive from pnl_pct sign) in `outcome_resolver.py` (one function).
- Wire basic `bond_scanner.py` call in shadow if not already.
- Success metrics: bond_picks quality>0 consistently, `edge_stability_BOND.json` n≥20-25, 0 active sizing, no new legacy mis-tags.
- Deliverable: small PR "bond: lower elite floor + emission telemetry" (Wire-Up section).

**Phase 2: Research Pilots + Paper (Days 15-60)**
- Implement 3 pilots from `bond_deep_dive_round2_2026-05-13.md` as new functions in `bond_strategies.py` (or `alpha_engine/proven_research_strategies.py` under BOND_BREAKEVEN_MR / CURVE_CARRY / CREDIT_SPREAD_MR) — ~150 LoC + unit tests. Opt-in via `BOND_ENABLE_PILOTS=1` or strategy registry flag.
- Add FRED consumption to `bond_yield_curve_slope` / new pilots (M-032) if secret available; else pure yf+^MOVE.
- Rigorous backtest harness (CPCV, 5-15bp slippage, regime splits, DSR per Lopez de Prado) for each pilot individually (target n≥30 closed per pilot in walk-forward).
- Shadow paper-trade (tv-paper-trade or TESTER account, 0.25% risk, time+level exits) starting ~Day 20. Track per-pilot rolling 30d metrics.
- Update `quality_gates.py`, `data_quality_gates.yaml`, dashboard_generator for bond-specific floors.
- Success metrics (per pilot, not aggregate): n≥20 closed shadow, PF≥1.40, WR≥48%, MDD≤8% (bond-adjusted), CLV ≤2bp, no single-symbol >35% of pilot PnL. Class-level: n≥40, no WARN concentration.
- Deliverable: 1-2 PRs "BOND pilots: TIPS MR + curve carry + credit MR (opt-in sidecar)" with full Wiring Plan.

**Phase 3: Validation Gate & Decision (Days 61-90)**
- Promote: any pilot meeting 5-gate (n≥30 per-pilot closed, PF≥1.5/WR≥50 sustained rolling, MDD≤8%, execution audit, resolver clean) gets micro 0.1% live sizing via `passes_active_gate` + `charter_position_sizer`.
- Class gate: aggregate n≥70-80, PF≥1.35 stable 30d, concentration <40% top symbol, at least 2 independent strategies contributing >15% each.
- If metrics fail (most likely): freeze emitter to research-only, deprecate dedicated daily cron or reduce frequency, fold any surviving logic into EQUITY/ETF multi-asset or FUTURES bond-futures. Update MASTER_ACTION_PLAN drop BOND institutional timeline.
- Parallel: implement M-024 `ust_tsmom_level` TSMOM on TLT/IEF/SHY as sidecar if pilots succeed.
- Success metrics for "continue": 2 pilots promoted or class PF>1.4 / n>80 / diversified. Else: permanent de-prioritize.
- Deliverable: decision memo + (optional) micro-PR for live gate.

**Resource estimate:** 4-6 PRs total (mostly small), <300 new LOC. Fits existing workflows. No core engine mutation. Cost: 1-2 sessions + backtest CPU.

**Stop-loss:** If after Phase 1 any 14-day window shows PF<1.0 on new emissions, raise floor back to 40 and abandon dedicated emitter.

**External validation:** After 30 clean shadow picks, replicate one pilot on QuantConnect Lean or public bond ETF backtest (PIMCO research) for sanity.

---

## 8. Final Verdict & Recommendations

**BOND fails the "phenomenal performance" north star and the "edge best worth the risk" filter.** Tiny noisy sample + 79% TLT concentration + gated emitter + missing academic edges = not investable. The regression from legacy-inflated 1.72 to real 0.66 is the honest signal: there was never a robust BOND edge in production.

**Recommendation:** 
- **De-prioritize** for real capital (0.0% allocation) for 90 days.
- **Pursue expansion** as pure low-priority research / opt-in sidecar (M-020/024/032) only after higher-ROI items (COMMODITY COT dedup hygiene M-021, EQUITY T2 maturation, ETF sector-rotation pilot) land. One small PR for floor + telemetry in Phase 1 is acceptable hygiene; full pilot wire-up only if dev capacity after those.
- Update `MASTER_ACTION_PLAN_2026-05-15.md` Section 21 + Antigravity schedule: BOND institutional date → "RESEARCH ONLY / post n=50 validation".
- Add frozen snapshot mechanism (as recommended in regression doc) so future verdicts are reproducible.
- If after 90 days Phase 3 metrics clear on 2+ pilots: reconsider 0.1% micro-pilot. Otherwise, archive dedicated BOND agent or merge survivors into multi-asset.

This aligns with Goal #1 (phenomenal /audit across classes), Wire-Up Rule, MUTATION_THREE_AXIS_PROTOCOL (mutate-before-kill not applicable yet — no live strategies to kill), and "prioritize where the edge is best worth the risk."

**References for follow-up (exact):**
- All cited reports + `alpha_engine/bond_strategies.py:58-651`, `bond-agent.yml:77-207`, `config.py:781-808`, `forward_validator.py:392-400`, `non_crypto_agent/data/bond_picks.json`.
- Next action owner: BOND expansion author per 11-PR list in 2026-05-15 memory.

**NFA.** Research surface only. No live recommendations.

---
*Generated 2026-05-15 by senior quant "money-maker-continual-improve" audit. Brutal honesty over optimism. Update only after Phase 1 telemetry.*
---

## 2026-05-24 — Institutional-Readiness Refresh

A 4-AI external consult (Mercury 2 + Grok + ChatGPT + Gemini, 2026-05-24) and a 5-engine swarm second-opinion (deepseek + groq + inception + pollinations) produced an honesty/risk/governance overlay captured in [INSTITUTIONAL_READINESS_PLAN_2026-05-24.md](./INSTITUTIONAL_READINESS_PLAN_2026-05-24.md). This appendix records what changes for THIS class specifically.

**Universal additions (apply to every class):**
- Per-pick freshness SLA enforced at the gate level (class threshold listed below); auto-suppress beyond threshold.
- Cross-provider price reconciliation (≥2 providers); `data_quality=degraded` flag on divergence.
- `smart_score` Platt/isotonic calibration runs per asset class; rank-vs-realized-WR must be monotonic on hold-out before any size-up.
- Lookahead-leakage CI guard (`entry_ts < signal_ts` fails the pipeline).
- Stage-1 gate: PF>1.3 / WR>48% / Sharpe>1.0 / MDD<25% / 90 days clean. Stage-2 gate (institutional): PF>1.5 / WR>50% / Sharpe>1.5 / MDD<20% / 6 months clean. **Real money only after Stage-2 holds 6 consecutive months.**
- Workstream G (governance) applies: real-time alerts + circuit-breaker on Stage-1 floor violation + data lineage + golden-set regression in CI.

**BOND-specific changes:**
- **Freshness threshold:** 5 minutes. Bond signals are slower than equities; 1-day for mutual-fund-style holdings.
- **Sample size remains the blocker.** PF 1.72 / WR 55.6% looks great but n=18 is far below the 100 floor required for Stage-1 calibration to be meaningful. Wilson-lower-95% CI is too wide to act on.
- **Workstream F1 (wire missing BOND emitters) is P0** — without more signal volume, BOND cannot reach Stage-1 in this 90-day window regardless of edge quality. Concentration on TLT (75% of volume per May-15) is the symptom; thin emitters are the cause.
- **Duration + convexity + real yields + breakeven inflation + credit spreads** become first-class columns (Workstream F3). Pure-technical bond signals usually fail per ChatGPT's review.
- **Pairs sleeve (C2):** TLT/IEF (long-short duration), HYG/LQD (credit-quality spread), TIP/IEF (breakeven inflation) are natural. Opt-in sidecar.
- **Speculative split (D1):** BOND stays in the institutional path. High-yield single-name corporate bonds get `speculative_flag=True` (when/if we ever emit them).
- **Verdict (refreshed):** BOND remains de-prioritized for size-up but **upgraded for honesty** — the dashboard must stop showing BOND as "T2 candidate" when n=18 is the truth. Workstream A5 (honest stat surface) enforces this. F1 emitter wire-up is the only path to Stage-1 by Day 90.
