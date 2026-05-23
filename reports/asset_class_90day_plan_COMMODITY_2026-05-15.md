# Asset Class 90-Day Plan: COMMODITY (CT=F Cotton + Broader Futures Universe) — 2026-05-15

**Author:** Senior Quant (Grok "money-maker-continual-improve" mode)  
**Date:** 2026-05-15  
**Scope:** Full skeptical audit of COMMODITY (yfinance futures + COT-driven + carry/momo sidecars). Includes CT=F cotton pilot as current flagship + 18+ symbol universe (GC=F, HG=F, NG=F, ZC=F, KC=F, SB=F, CC=F, CL proxies, livestock, metals).  
**References (concrete, not generic):** Lopez de Prado *Advances in Financial Machine Learning* (DSR/PSR/CPCV), Miffre/Rallis/Fuertes (2010) SSRN 1127213 "Tactical Allocation in Commodity Futures", CFTC COT legacy reports, ICE/CT contract specs, internal `alpha_engine/config.py:COMMODITY_SYMBOLS`, `audit_dashboard/data/{dashboard_data.json, commodity_carry_momo.json, cot_paper_pilot_status.json, cot_step7_ror_mc.json, edge_stability_COMMODITY.json}`, `reports/{cot_paper_pilot_overemission_falsified_20260513.md, cot_pipeline_audit_20260514.md, cotton_cot_real_money_sizing_2026-05-12.md, asset_class_research_COMMODITY_2026_05_12_0438Z.md, MASTER_ACTION_PLAN_2026-05-15.md (M-008/021/022/050)}`, `audit_trail/quality_gates.py` (historical HG/PL restriction + _COMMODITY_NON_BLACKLIST_SYMBOLS), `audit_dashboard/data/data_quality_gates.yaml`.

**Core Verdict (lead with the answer):**  
**COMMODITY is NOT production-grade and not yet close to safe real-money sizing.** The headline Tier-2-beating numbers (dashboard_data.json 2026-05-15T02:06Z: PF 2.49 / 61.5% WR / n=322 resolved / 557% PnL / 8 active; concentration tier "WARN") are materially overstated by a now-documented signal emission bug in the dominant `cot_positioning::CT=F` strategy. Post-consolidation to true independent weekly COT cycles, the flagship collapses to n≈5, WR 40%, PF 0.17, negative PnL. 73% of class PnL mass is still tied to a single ag future (CT=F) with no micro-contract, high minimum risk unit, and clustered "trades" that are economically fractional in the paper pilot. Broader universe (25 symbols defined in config.py) exists on paper but production activity is negligible outside CT=F. `commodity_carry_momo_double_sort` (classic academic) is defined in `commodity_carry_momo.json` (18 symbols, wiring=OPT_IN_SIDECAR) but not live. Graduation gate explicitly "BELOW_EXPECTED / ready_for_live: false". Historical dashboard/MySQL data not yet re-aggregated post PR #941 (lag) + #961 (dedup). **Realistic path to T2 exists via ruthless diversification + hygiene, but 90 days of disciplined execution required before any shadow/live capital. Prioritize this only if edge survives cleaning better than EQUITY's current T2-candidate (PF 1.57). Otherwise, de-risk to paper/research.**

---

## 1. Latest Performance from dashboard_data.json + Recent Reports (2026-05-15 snapshot)

**From `audit_dashboard/data/dashboard_data.json` (generated 2026-05-15T02:06:57Z, repo_sha 35d3e77):**

- **COMMODITY asset_class_health:**
  - status: stable, sample_tier: stable, sizing_allowed: true
  - n=322 (resolved_n=322), win_rate=61.5%, total_pnl_pct=557.22, profit_factor=2.49
  - circuit_breaker: no_backtest (note: "no_backtest" but live PF quoted in session memory as 2.49/61.5% n=322 for CT=F pilot)
  - by_asset_class closed: 507 (wins 198 / losses 124), active=8, expectancy=1.73, avg_win=4.71 / avg_loss=3.03

- **asset_class_concentration.COMMODITY (critical):**
  - top_symbol: "CT=F", top_share_pct: **73.36%**, top_symbol_pnl_mass_pct: 959.26 (of total_pnl_mass 1307.67)
  - top_strategy: "cot_positioning", top_strategy_share_pct: **41.19%**, top_strategy_pnl_mass_pct: 538.69
  - is_concentrated_warn: **true**, is_concentrated_block: false, tier: **"WARN"**
  - honest_label: "COMMODITY edge = cot_positioning on CT=F (73% of class PnL)"
  - smart_picks_by_asset.COMMODITY: [] (empty; assetClassSummary activeCount=0, smartCount=0, thresholdPass=true only because minTrades=0)

- **Comparison context (from MASTER_ACTION_PLAN + older snapshots):**
  - 2026-05-03 health (per prompt/Claude.md): PF 1.78 / WR 46.9% / n=750 (pre some resolver-v2 noise filter)
  - 2026-05-12 edge_stability_COMMODITY.json (n_total=178): 90d WR 58.4%, PF 4.31, sharpe 0.352 (wilson_ci 50.5-64.9%), 7d insane PF 44.07 on n=35 recent cotton shorts. "all" window identical to 90d.
  - asset_class_research_COMMODITY_2026_05_12: swarm claimed live n=412 / WR 66.7% / PF 3.77, 90% T2 attainability via seasonal ag / energy shock / metals demand candidates.
  - audit_asset_feedback_2026-05-05T0121Z_COMMODITY.md: n=816 / WR 48.7% / PF 2.08 (pre-cleaner filters), "best class-level PF but misses WR gate".
  - fix_COMMODITY_20260505: declared T2 on PF alone, flagged SHORT copy_trader 50% LOST rate + MDD verification needed.

**By_asset_class note:** Separate FUTURES bucket has n=0-4 (insufficient), BOND thin n=11-13. COMMODITY treated distinctly but overlaps symbols (GC=F etc appear in both COMMODITY_SYMBOLS and FUTURES_SYMBOLS in config.py).

**Recent COT pilot specifics (cot_paper_pilot_status.json + cot_step7_ror_mc.json, generated ~2026-05-13):**
- Strategy: cot_positioning on CT=F (ICE US, 50k lbs, tick $5, notional ~$35k, **no micro**).
- Paper stats (pre-forensic): n=101, WR 90.1%, cum_pnl_usd +359.62 (avg +3.56/trade), 91W/10L, many clustered SHORT entries May 1-12 around $83→$80 with ~4-7% moves, tiny net $3-15 per "trade" (implies <<1 contract sizing in sim).
- Contract risk: daily limit 3¢/lb = $1,500/contract move risk. Margin ~$1.2-2k.
- **graduation_gate:** verdict="BELOW_EXPECTED", detail="avg $3.56 below tolerance floor $4.20; investigate before sizing", ready_for_live=false.
- codex_state_machine: OOS_READY (target LIVE_ELIGIBLE), global_blockers=["all-classes-first (0/6 SHADOW)", "user single-class deviation accepted 2026-05-12"].
- nfa note: "Research surface only. No real-money sizing without explicit user approval + graduation gate clear."

**Brutal observation:** The 101 "trades" are not independent economic decisions — they are the same weekly COT signal re-fired hourly for days (see below). Per-trade PnL economics only make sense at 0.1-0.2 contract scale; live requires full contracts → risk per signal jumps 5-10x.

---

## 2. Symbol Universe Size, Liquidity & Concentration Risk (Especially Cotton)

**Defined universe (alpha_engine/config.py:615-646 COMMODITY_SYMBOLS, + carry_momo.json:12-30):**
- ~25 entries: 
  - Precious/industrial metals: GC=F (Gold, seasonal 1/2/8/9), SI=F (Silver), HG=F (Copper), PL=F (Platinum), PA=F (Palladium)
  - Energy: NG=F (NatGas, high vol seasonal 10-12), CL=F (removed: "26 futures trades, 3.8% WR, -29.82% PnL — worse than random"), plus ETF proxies USO/UNG/DBA + BZ=F/RB=F/HO=F (added 2026-04-17 for yfinance reliability)
  - Ags (COT-eligible): CT=F (Cotton, seasonal 3/4/5), KC=F (Coffee), SB=F (Sugar), CC=F (Cocoa), OJ=F (OJ), ZC=F (Corn), ZS=F (Soybeans), ZW=F (Wheat), ZM/ZL (meal/oil), LE/F/GF/HE (cattle/hogs)
- carry_momo.json (2026-05-12) explicitly lists 18 for double-sort (mom_12_1 + carry_proxy via rolling mean diff): CT, KC, SB, CC, OJ, GC, SI, HG, PL, PA, CL, NG, ZC, ZS, ZW, HE, LE. "Free-path carry proxy... Real Miffre uses second-month contract basis (premium data). Treat as MODERATE-confidence signal." wiring_status="OPT_IN_SIDECAR — not yet consumed by production pick path."

**Live concentration (dashboard 2026-05-15):**
- 73% PnL mass on **CT=F** alone via cot_positioning (41% of class from that one strategy). 
- Earlier quality_gates.py comments (lines ~1257-1272, 6186): COMMODITY was temporarily restricted to **HG=F (copper n=168 WR47%) + PL=F (platinum n=138 WR44.9%)** as Phase 2-D KEEP after killing GC, SI, CL, CT (old small-n poor perf). CT=F has since been revived via COT but without full 6-stage rehab documented.
- Liquidity realities (cotton_cot_real_money_sizing_2026-05-12.md + contract specs):
  - CT=F: ICE Futures US, full-size only (no micro like MES/MNQ), notional ~$35k @ $0.70/lb, tick $5, round-trip ~$10, daily limit risk $1,500/contract. Volume decent for ag but thinner than GC/CL. High basis risk on physical delivery/rolls.
  - GC=F / HG=F: Excellent liquidity (COMEX), deep books, options chains for defined risk.
  - NG=F: Liquid but extreme vol (can gap 10%+ on storage/inventory).
  - Z* grains / livestock: Moderate liquidity, seasonal + weather gaps, CFTC COT coverage good.
  - ETF proxies (USO etc): Easier fractional but tracking error + contango drag; not true futures edge.

**Risk:** 73% concentration on one mid-tier ag future violates "phenomenal performance across ALL asset classes" + diversification north-star. Single weather/China demand/COT regime shift on cotton can erase class edge. Per MASTER_ACTION_PLAN: CT=F PF 10.94 on n=39 in sub-view, but "single-class deviation" accepted only temporarily.

**Gap:** No per-symbol liquidity score / position sizing matrix live in production gates (quality_gates.py has some bypass for HG/PL + trusted sources, but CT=F now dominant).

---

## 3. Data Quality & Outcome Tracking for Commodities

**Strengths:**
- CFTC COT data (commercial/non-commercial/net positioning) is high-quality public ground truth, released Fridays ~3:30 ET (3d lag from Tue settlement). Good for ags (CT/KC/SB/CC/ZC etc.).
- yfinance covers continuous futures (GC=F etc.) + some ETFs as proxies.
- carry_momo.json + commodity_carry_momo_double_sort references solid academic (Fuertes/Miffre/Rallis 2010; Jiang & Liu 2024 replication note).
- Recent fixes: PR #941 (COT_PUBLICATION_LAG_DAYS=3 + _is_cot_row_public guard), PR #961 (cot_emitted_releases.json dedup ledger + record function). 14d freshness in dashboard. data_quality_gates.yaml has commodity: symbols_min:5, feed_age 600s, price_outlier 4.5σ, cot_release_day friday, roll_yield_check:true, pnl_window 30d.

**Major Weaknesses (brutally documented):**
- **Over-emission artifact (primary hidden insight):** `reports/cot_paper_pilot_overemission_falsified_20260513.md` + `cot_pipeline_audit_20260514.md` (May 13-14 forensics via tools/verify_cot_post_patch.py):
  - 101 paper "trades" on CT=F from **only 5 unique CFTC weekly releases** (~20× over-emission).
  - Winner reports (Apr 28, May 5) over-fired 50/19/26× → inflated WR to 90.1%.
  - Loser reports under-fired (3×) → asymmetric bias.
  - Consolidated 1-per-cycle: n=5, WR 40%, PF 0.17, PnL -$52 (vs headline +$360 / PF 2.73 / TIER_1_RENAISSANCE / DSR 1.0).
  - "The 90% WR is asymmetric over-emission, NOT real edge." Same pattern as kimi_signal_tracking resolver-denominator artifacts.
  - **Current state (2026-05-14 audit):** Lag timing fixed (all 101 pass 3d lag, 0 invalid). Dedup ledger active go-forward (seeded empty). But **historical dashboard_data.json + MySQL trading_picks still count all 101 as independent** → PF 21.86 / WR 94.1% for multi_asset_cot / cot_positioning still polluting COMMODITY metrics on 2026-05-15 dashboard (2.49 PF, 61.5% WR). dashboard_generator.py does NOT apply 1-per-cycle re-agg on historical reads. "PF=21.86 is an over-emission artifact."
- **Paper pilot economics unrealistic:** 101 trades with ~$3-7 net on $35k notional = fractional sizing in sim. Live = 1 contract min → slippage, commissions, margin calls, daily limit moves ($1500 risk) not stress-tested at scale in the 101-trade set. graduation_gate explicitly failed on avg $3.56 < $4.20 floor.
- **yfinance futures quality:** Known issues (roll dates, volume for back months, survivorship in continuous series). CL=F explicitly killed for bad data/perf. GC=F has "Bad Data Protection" special case in quality_gates.py (line 4993+). carry proxy in commodity_carry_momo is "free-path... MODERATE-confidence" (not true second-month basis).
- **Outcome tracking gaps:** resolver-v2 noise filter helped system-wide but COT emission hygiene was missed until May 13 forensic. Many "closed_picks" for COMMODITY pre-date dedup. No robust independent-cycle counting (weekly COT releases are the natural frequency, not hourly bars). edge_stability wilson_ci for 90d barely >50% lower bound.
- **Small true N:** Post-clean COT n~5-20 cycles max. Dashboard n=322/507 includes pre-bug + other strats (some killed historically). Compare to CRYPTO n=8000+ or EQUITY 420+ for statistical power.
- **Other reports flags:** cot_timing_leakage_audit_2026-05-13.md, commodity_bond_forensic_2026-05-13.md, backtest_commodity_seasonal_2026-05-12. MASTER_ACTION_PLAN flags M-021 "COT lag-corrected re-run + paper-pilot acceptance ≥75% on n=100" as PENDING; 2026-05-18 "DROP-AND-REPLACE-WITH-DATA-GATE" for COMMODITY because "WR likely ~45-55% not 86.5%".

**Verdict on data quality:** Substandard for institutional production. Emission bug + dirty historicals = classic "inflated stats" trap. Roll/yield/volume checks exist in gates but enforcement incomplete for futures.

---

## 4. Hidden Insights & Gaps Others Missed

1. **The falsified flagship (most important):** Even with lag/dedup PRs landed, the 2026-05-15 dashboard COMMODITY "stable / sizing_allowed / PF 2.49" is still carrying pre-May13 inflated COT data. Re-aggregation of MySQL historicals + dashboard_generator update is P0 but not yet done (per cot_pipeline_audit). This explains why concentration remains 73% on CT=F and smart_picks empty — the "edge" is not trusted internally yet.

2. **Carry_momo sidecar ignored:** commodity_carry_momo.json (generated 05-12, references Fuertes 2010 + Jiang/Liu 2024) has full 18-symbol data + mom/carry values for CT (strong +11.8% mom +12% carry), GC (+47% mom), SI (+133% mom), HG etc. But "not yet consumed by production". This is the natural diversifier (Miffre-style tactical in commodities has decades of academic backing). Why not wired when COT on one symbol is failing gates? Gap in execution vs research.

3. **Historical whiplash in universe:** quality_gates.py shows COMMODITY was narrowed to HG/PL only after killing CT/GC/SI/CL for poor small-n results, then COT revived CT=F with spectacular (but artifactual) numbers. No full 6-stage Rehabilitation Pipeline (Cross-symbol → Cross-asset → Inverse → Mutation → Regime → Crossover) applied per institutional policy in MEMORY.md. Risk of repeating.

4. **No micro + high unit risk for CT:** cotton_cot_real_money_sizing recommends $10-15k capital for 1 contract ($170-670/yr est at old 90% WR). Post-clean (40% WR, negative), this is negative EV at live sizing. Options on CT or BAL ETN illiquid alternatives noted but not implemented.

5. **Missing cross-asset / external replication:** No comparison in reports to KMLM (KFA Mount Lucas Managed Futures), DBMF (iMGP DBi Managed Futures), or PIMCO commodity strategies. Seasonal ag (USDA crop reports) + weather mentioned in swarm research but no concrete module.

6. **Small n + Wilson CI barely positive:** edge_stability 90d lower CI 50.5% WR. Sharpe 0.35 anemic for "Renaissance Tier 1" target (PF>2 / WR>55 / MDD<10).

7. **FUTURES vs COMMODITY bucket confusion:** Separate tracking (FUTURES n~0) despite symbol overlap (GC in both). Splits attention.

These gaps were surfaced by cross-referencing the May 13-14 cot forensic reports against live dashboard_data.json and master plan — not obvious from single dashboard view.

---

## 5. Realistic 90-Day Plan: Diversify Beyond CT=F, Fix Hygiene, Gate Properly

**North Star:** Deliver diversified COMMODITY basket (≤30% CT=F PnL share, 5-7 symbols) meeting T2 minimum (PF>1.5 / real WR>50% post all filters / MDD<20% / independent n>100) or deprecate underperformers. Follow "all-classes-first" + Codex state machine (OOS_READY → SHADOW → LIVE_MICRO only after 6/6 classes have shadow coverage). Wire existing research (carry_momo, expanded COT). No real $ until graduation + re-agg + CPCV/DSR.

**Phase 1: Days 1-14 — Data Integrity & Emission Hygiene (P0)**
- Re-aggregate **all** historical `cot_positioning` + `multi_asset_cot` trades in MySQL `trading_picks` + `alpha_engine/data/cot_signals.json` + dashboard_generator.py to enforce strict 1-pick-per-(symbol, COT_report_date, direction). Update `cot_paper_pilot_status.json`, `cot_step7_ror_mc.json`, and force dashboard_data.json regen. (Directly addresses cot_pipeline_audit rec #1.)
- Verify post-re-agg: n≥20 independent weekly cycles, PF≥1.5, WR≥50% on cleaned set. Run `tools/verify_cot_post_patch.py` + new bootstrap/MC.
- Complete dedup ledger seeding for historicals (PR #961 was go-forward only).
- Audit yfinance feed quality for all 18 carry_momo symbols (missing bars, roll yield accuracy, volume). Add explicit roll_calendar_check enforcement (already in futures gate).
- Update `data_quality_gates.yaml` + `audit_trail/quality_gates.py`: add `max_emission_per_cot_release: 1`, `min_independent_cycles: 20`, `liquidity_min_avg_daily_volume` per symbol, force COMMODITY bypass only for HG/PL + now-cleaned COT ags.
- Refresh edge_stability_COMMODITY.json + effective_n_report with cleaned data.
- Milestone: COMMODITY health in dashboard shows "WARN" or lower until re-agg passes; update MASTER_ACTION_PLAN M-008 (multi_asset_cot MATCH gate) + M-021 status.

**Phase 2: Days 15-45 — Wire Diversification (Carry+Momo + Multi-COT)**
- **Wire `commodity_carry_momo_double_sort`** (M-022): production opt-in sidecar in alpha_engine / smart_picks path. Long top-3 carry+mom quintile, short bottom-3 across the 18 symbols from commodity_carry_momo.json (use quintile_size=3, lookback 12m skip 1m). Apply per-symbol ATR stops from config.py, realistic futures roll costs, contract multipliers, liquidity caps (e.g. smaller size on CT/KC vs GC/HG).
- Extend **deduped COT** to other CFTC ags: KC=F, SB=F, CC=F, ZC/F, ZS=F, ZW=F (high COT coverage). Target 4-6 COT symbols.
- Add liquid anchors: HG=F (copper, industrial demand), GC=F (gold, with existing bad-data protections), NG=F (capped vol), ZS=F (soy, carry strong per 05-12 json).
- Enforce hard concentration: single symbol ≤25-30% class PnL mass (CT=F cap explicit); top_strategy ≤25%.
- Backtest full basket with CPCV (Lopez de Prado), PSR/DSR, regime filters (contango/backwardation, VIX overlay if correlated). Reference backtest_commodity_seasonal_2026-05-12.
- Integrate USDA crop reports / FRED commodity indices / weather as side features (per swarm research in asset_class_research_COMMODITY).
- Update `smart_picks_by_asset.COMMODITY` + assetClassSummary thresholds (raise minTrades to 10+).
- Produce per-symbol mini-audits (e.g. GC=F vs CT=F edge stability).
- Milestone: ≥4 symbols with positive cleaned expectancy, total independent n>80, CT=F share <50%.

**Phase 3: Days 46-75 — Rigorous Paper Validation + Risk Engineering**
- 30-day (or 8-12 independent COT cycles) **live paper pilot** on diversified basket (no real capital). Daily reconciliation, outcome tracking via existing check_*.py but only on explicit request per AGENTS.md. Use circuit_breaker_system.py + new COMMODITY-specific (COT release windows, roll dates, limit-move halts).
- Realistic sizing sim: full contract for CT (or defined-risk options), fractional via proxies only if volume >$5M/day. Stress test margin calls, $1500 daily limits, slippage on ags.
- Monte Carlo / bootstrap per cotton_cot_real_money_sizing contract specs (update with cleaned PnL distro).
- External replication: compare basket to KMLM/DBMF commodity sleeve, simple long-only roll of GSCI or BCOM. If basket underperforms passive in OOS, kill.
- Full 6-stage rehab on any underperformer (e.g. livestock or old mean-reversion metals).
- Update codex_state_machine for COMMODITY symbols; require all-classes shadow before LIVE.
- Refresh reports: new deep_dive if needed, edge_stability, hedge_fund tier table comparison.
- Milestone: graduation_gate = PASS on basket (avg net > floor after costs, DSR>0.9, no MDD breach in sims); independent n>120.

**Phase 4: Days 76-90 — Gate Decision & Production Path**
- If T2 gates met on diversified set (PF>1.5 / WR>50% real post-noise / MDD<20 / n>100 / liquidity ok / DSR high): 
  - Shadow mode (micro sizing, all-classes-first).
  - Then LIVE_MICRO per master plan M-050 (30 picks @ projected PF on live tape).
  - Sizing: conservative (e.g. 1 CT contract on $15k+ capital using cleaned expectancy ~$3-4 net/trade or better; scale with vol targeting).
  - Document + link SUPREME_PLAN_90days companion + per-asset updates/ page.
- If gates fail: continue paper, apply mutations (three-axis protocol), or drop low-edge symbols (e.g. if CT post-clean remains sub-1.0 PF, de-emphasize vs EQUITY). Re-evaluate vs BOND/ETF expansion.
- Final deliverable: Updated MASTER_ACTION_PLAN Section 21 + `reports/asset_class_90day_plan_COMMODITY_2026-05-15.md` (this doc) + evidence pack (cleaned json, CPCV results, external comp).
- Ongoing: Monthly re-audit of emission rate, concentration, feed freshness.

**Success Metrics (quantified, measurable):**
- CT=F PnL share ≤30% (from 73%).
- 5+ symbols with ≥15 independent resolved picks, positive expectancy each.
- Cleaned COMMODITY: PF ≥1.6, real WR ≥52%, sharpe ≥0.4, MDD <18% in 90d OOS.
- Carry_momo + multi-COT contributing ≥40% of class PnL (no single source >25%).
- Dashboard "sizing_allowed: true" + smart_picks non-empty + graduation_gate PASS.
- Zero over-emission (verified by ledger + 1-per-cycle in generator).
- Decision gate: "Production-grade for diversified COMMODITY" or "De-risk / focus resources elsewhere".

---

## 6. Brutally Honest Risks & Why Skepticism Is Warranted

- **Statistical fragility:** True independent signals for COT are weekly (CFTC release cadence). n=5-20 is tiny for "Renaissance" claims (PF>2 requires robust tails). One bad COT cycle or regime shift (e.g. post-2022 inflation hedging changes commercial behavior) kills it.
- **Execution reality for CT=F:** No micro = high minimum bet size. A limit-down day (-$1500/contract) exceeds many per-trade expects. Basis risk, delivery, storage costs ignored in paper sims.
- **Data vendor risk:** Heavy yfinance reliance for futures — community consensus is it is "good enough for research, dangerous for production" (roll artifacts, stale volumes). Paid tick-level or exchange direct feeds recommended before live $.
- **Overfitting temptation:** Clustered entries in pilot + high headline PF before forensic = classic look-ahead + multiple-testing trap. DSR=1.0 on dirty data is meaningless.
- **Opportunity cost & charter conflict:** COMMODITY currently ~8 active picks vs CRYPTO 165 / EQUITY 65. Time on cotton forensics competes with scaling EQUITY (already T2-candidate) or fixing FOREX (sub-floor, mutate protocol). Per goals: "prioritize where the edge is best worth the risk."
- **Process debt:** Emission bug slipped through for weeks; historicals still dirty on day of this report. Indicates need for stricter pre-prod gates (quality_gates.py + resolver + dashboard_generator must be synchronized).
- **Regime / external:** Commodity super-cycles, USD strength, China demand, weather (La Niña etc.) can dominate COT signal. Carry+momo has long history but drawdowns in 2008/2020/2022 were severe for trend/carry CTAs.
- **If it fails 90d:** Accept that COMMODITY edge is marginal (better as small satellite allocation in a multi-asset book, not standalone class). Redirect to stronger classes or external replication (e.g. allocate to KMLM/DBMF instead of building in-house).

**Final Recommendation:** Execute the 90-day plan with zero tolerance for dirty data or concentration. If cleaned diversified basket hits T2 gates by day 90, cautiously size (start paper → shadow). If not, document lessons, prune to 2-3 best symbols (likely HG/GC + 1-2 clean ag COT), and treat COMMODITY as experimental/research tier rather than production candidate. This class has academic promise and infrastructure seeds, but current "phenomenal" appearance is a cautionary tale in signal hygiene and single-symbol risk — exactly the kind of trap institutional quants are paid to catch early.

**Next Immediate Actions (today/this week):**
1. Run re-aggregation script for COT historicals (update dashboard_generator + MySQL views).
2. Wire commodity_carry_momo as sidecar (small PR with Wiring Plan section).
3. Update MASTER_ACTION_PLAN M-008/021/022 with this 90d plan reference.
4. Force fresh dashboard_data.json + edge_stability after clean.
5. Explicit user sign-off before any CT=F real-money (per nfa + graduation).

NFA. All numbers from 2026-05-15 workspace files. This plan advances Goal #1 (phenomenal performance across classes on /audit) by forcing diversification and integrity before sizing. 

---

*End of report. Brutal honesty prioritized over optimism. Concrete files, dates, and metrics cited throughout for auditability.*