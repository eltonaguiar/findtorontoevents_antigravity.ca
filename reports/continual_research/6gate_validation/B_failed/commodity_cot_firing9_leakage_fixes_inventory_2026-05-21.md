# COMMODITY / COT Leakage Fixes + Strategy Inventory — Firing 9 (2026-05-21)

**Subagent:** COMMODITY/COT focus for Firing 9 of 30m continual 6-gate research loop (task 019e490182df parallel).
**Status:** B_failed for all current COT paths (H-001 REJECTED, multi_asset_cot / cftc_cot_commercial_signal / cot_positioning on COMMODITY still hygiene-blocked or power-insufficient post-partial-fixes). Non-COT commodity carry/momo/seasonal families remain salvageable only after full COT hygiene + conc caps + n accrual. No A_passed/COMMODITY this cycle.
**References:** Matches prior B_failed/commodity_strategies_cot_leakage_no_6gate_pass_2026-05-21.md (firing2 baseline) + CYCLE_2026-05-21_01_SUMMARY.md + public log updates/2026-05-21-continual-6gate-asset-class-research/index.html (Firing 9 section lines 41-73 explicitly calls out this subagent's scope: "COMMODITY: COT leakage forensics (M-095, CT=F 73% mass, publication lag) + guard proposals + salvage list... references COT forensics, KIMI_BUNDLE_AUDIT, alpha_engine/commodities_strategies.py").

## 1. Mined Sources (Exact File Citations)

### alpha_engine / multi_asset commodity strategies (non-COT core + COT sidecars)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/commodities_strategies.py:87` (seasonal_momentum: monthly bullish filter + SMA/RSI; Bodie/Rosansky 1980 ref; 8 strategies total incl. oil_inventory_momentum:268, metals_mean_reversion:366, dxy_inverse:805, commodity_tsmom_12m:919).
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/commodity_cot_contrarian.py:215` (commodity_cot_contrarian_picks: OPT-IN sidecar, fades non-comm on 21-contract TIER1 incl. CT:85 "CT": {"code": "033661", "yahoo": "CT=F"}; inline lag guard 236-252 using COT_PUBLICATION_LAG_DAYS=3; source_system="commodity_cot_contrarian"; synthetic backtest only).
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/cot_positioning.py:45` (COT_PUBLICATION_LAG_DAYS=3; _is_cot_row_public:290-303; ledger dedup _load/_record_emitted_releases + O_EXCL lock PR#994; main cot_positioning_strategy:306; FOREX-centric COT_CONTRACTS but used for COMMODITY CT=F pilot historically).
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/commodity_strategy_harness.py:67` (COT_POSITIONING cat; 12+ COT strats e.g. cot_commercial_extreme:748, cot_noncommercial_extreme:757 on synthetic generate_cot_data:470; COMMODITY_BLACKLIST={"CT=F", "GLD"}:114; taxonomy CARRY/MOM/INV/SEAS/TERM).
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/commodity_signal_generator.py`: (no direct COT; VT commodity hooks).
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/multi_asset/commodity_futures_strategies.py`: (futures variants).

### COT-related in audit_trail/ + dashboard + emitters (leakage surface)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py:1436` (M-095 kill: "cot_positioning" — COT-publication LOOK-AHEAD LEAKAGE. ~85% of 134 picks CT=F; post-dedup+ex-CT=F: n=20 WR30% PF0.51 loser. COT_DEDUP_SYSTEMS:2075 incl. "cftc_cot_commercial_signal", "multi_asset_cot", "multi_asset_copytrader":2076-2082; COT_DEDUP_WINDOW_HOURS=72; M-001 COT stale gate).
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/dashboard_generator.py:8253` (cftc_cot_commercial_signal default strategy + asset_class fallback; COT handling 4091-4308, 5302, 5668 (73% CT=F PnL conc callout), 8218 (cot_signals.json), 8224+ (stale 14d guard); _infer_asset_class patches in Firing7/8 refs).
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/copy_trader_intel/multi_asset_copytrader_scraper.py:1716` (scrape_cftc_cot_weekly: REAL Socrata CFTC API for cftc_cot_commercial_signal on COMMODITY; _fetch_cftc_cot_data:1698 using as_of_date_in_form_yymmdd; NO _is_cot_row_public lag guard or COT_PUBLICATION check before emit 1831+; fallback RSI proxy 1854; source_system default "multi_asset_copytrader" not CFTC-tagged:406; dedup only in RSI path 1121+ / _last_cot_friday stamp 1219 for M-001; CFTC_CODES incl. CT=F mapping 184+).
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py:1967` (multi_asset_cot CT=F 94.3% artifact; 2068 "multi_asset_cot CT=F (cotton) accounted for 94.3% of all COMMODITY picks (toxic_concentration=true)").
- Other: alpha_engine/feed_hygiene.py, emitter_dedup.py, universal_pick_resolver.py (partial COT paths).

### Hypothesis registry (H-001 COT commercial + siblings)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/hypothesis_registry.json:7-31` (H-001: "CFTC COT commercial-net positioning... COMMODITY"; status="REJECTED"; result: "REJECTED - look-ahead leakage (M-095). 85% ... CT=F ... Pre-fix WR=78.4% n=134 falsified... After dedup + publication-lag guard: WR=30%, PF=0.51... operator_note: ... NOT salvageable... Do NOT re-test COT_positioning... If ... small-spec exhaustion H-021"); m095_fix_applied 2026-05-20 in scraper.py per note; H-004 inventory HARNESS_REJECTED, H-007 roll_yield REJECTED, H-021 small-spec NEAR_ADMISSIBLE (n insuff), H-027/034 UNTESTED/REJECTED, seasonal variants UNTESTED_DATA_GAP:1647+.

### KIMI_BUNDLE_AUDIT + COT forensics (recent audits)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/KIMI_BUNDLE_AUDIT_2026-05-21.md:90-96` (archives commodity_strategy_harness.py as reference design only — synthetic COT, not production; statistical_validation_framework.py KEEP; no real COT hygiene validation performed in bundle).
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/cot_paper_pilot_status.json` (or audit_dashboard/data/): n=5 WR40% cum_pnl_usd=-51.29 (2026-05-21T03:28), SHADOW_INSUFFICIENT_N, DSR withheld, falsification_refs to overemission_20260513 + leakage_audit_2026-05-13 (post 1-per-cycle collapse from artifact 101/123 ~24.6x).
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/cot_pipeline_audit_20260514.md`, `cot_timing_leakage_audit_2026-05-13.md`, `cot_paper_pilot_overemission_falsified_20260513.md`, `multi_asset_cot_audit_20260514.md`: 73%+ PnL mass CT=F, 20-50x asymmetric over-emission (winners), M-095 lookahead (CFTC Tuesday settle used pre-Friday 15:30 ET public), partial fixes in ledger/lag but not all emitters (esp. cftc_cot path in scraper).
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/asset_class_90day_plan_COMMODITY_2026-05-15.md:84-97` (over-emission + hygiene as #1 weakness; CT=F no micro, high unit risk; post-consolidation flagship collapses; carry proxy "MODERATE-confidence free-path").
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/tools/validate_resolved_picks.py` + `--by-asset-class` runs (prior: post-COT clean n~5-20 for flagship, 0 closed for exact "commodity_carry_momo_double_sort").
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/tools/research/commodity_carry_momo.py:84-313` (double_sort_basket 12-1 mom + carry_proxy rolling mean; quintile intersect; build_picks "commodity_carry_momo_double_sort"; 18-sym incl CT/GC/HG/NG/OJ etc.; audit_dashboard/data/commodity_carry_momo.json:2-49 WIRED 2026-05-20, 1 OPEN SHORT OJ=F, proxy caveat).
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/tools/kimi_research_2026_05_20/alpha_engine/commodity_strategy_harness.py:745+` (COT 12 strats on synthetic; carry expectations Sharpe 1.0-1.4 per Fuertes/Miffre/Rallis 2010 SSRN1127213).

### Other supporting
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/edge_stability/edge_stability_COMMODITY.json` (pre-full-hygiene: n=178 sharpe0.352 PF4.31 90d; cot heavy).
- `alpha_engine/config.py:780-810` (COMMODITY_SYMBOLS incl. CT=F).
- Firing 7/8/9 patches: FIRING*_DASHBOARD_GENERATOR_PATCHED_REFERENCE_2026-05-21.py (cftc_cot normalization), FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py (related but tagging-focused), 6GATES_2026-05-21_V1_FREEBUFF.MD:30-41 (gate defs + sparse relaxes), CONTINUAL_STRATEGY_RESEARCH_BASELINE.md:37 (H-001 REJECTED + carry pending).

## 2. Current Leakage Issues Documented (Firing 9 Snapshot)

- **M-095 Lookahead on CT=F (core blocker):** CFTC COT (Tuesday settlement) used for signals before Friday ~15:30 ET public release. Pre-fix: WR78.4% n=134 / DSR=1.0 / TIER1 artifact on CT=F (85-94% of COMMODITY COT PnL mass per quality_gates:1967,2068). H-001 registry explicitly "falsified by future-data bias". Post partial dedup/ledger: n=5 WR40% PF0.17 cum -51 USD (cot_paper_pilot_status.json:26-30). Still present in production path: scrape_cftc_cot_weekly (scraper.py:1736-1846) fetches latest as_of without calling _is_cot_row_public or equivalent lag check (unlike cot_positioning:332 and commodity_cot_contrarian:236-252 inline).
- **73%+ PnL mass / toxic concentration on one future (CT=F cotton):** No micro contract; single contract risk (daily limit moves ~$1500 notional high); COT_DEDUP + M-003 diversification (HG/PL added) only partial; still cited in 90day plan + edge_stability + dashboard 5668 as "headline PF ... materially overstated".
- **Publication lag problems:** COT_PUBLICATION_LAG_DAYS=3 defined in 3 places but **not uniformly enforced**. scraper.py cftc path lacks it entirely (emits on API latest regardless of public time); dedup is week-anchor or 72h post-facto in quality_gates COT_DEDUP (not preventive at emission); M-001 stale gate relies on stamped latest_cot_date (present in RSI path 1227, missing or proxy in real cftc path); historicals still pollute some artifacts per cot_pipeline_audit.
- **Over-emission despite partial dedup:** Pre 24.6x on winners (asymmetric); ledger in cot_positioning + import in scraper (1121+) but cftc_weekly path bypasses (no release_key check on actual CFTC as_of); dashboard/edge still show inflated pre-reagg.
- **Tagging / source_system hygiene gaps:** cftc_cot_commercial_signal defaults to source_system="multi_asset_copytrader" (not "cftc"/"cftc_socrata"); no fail-loud on CT=F COT emits; asset_class inference fallbacks polluted cross-class views (addressed in Firing9 tagging backfill but COT-specific not yet).
- **Post-clean power collapse:** True independent cycles = CFTC weekly releases (~1 per 5-7d); n<< required for G4 (WF >=4 windows, min~42-100 per 6GATES), G5/G6 MC, G1 Sharpe (class dirty 0.35 <<1). Resolved closed for named COT paths: 0-5 post-hygiene. H-001: "Do NOT re-test".
- **Evidence of partial progress but incomplete (Firing9 state):** m095_fix noted in registry for scraper (2026-05-20), ledger + lag in alpha_engine/cot_* , COT_DEDUP in gates, but cftc_cot_weekly (primary COMMODITY emitter for "cftc_cot_commercial_signal") + dashboard paths + full historical re-agg still gaps. Matches "COT data hygiene failures (leakage/duplicates)" in session memory.

**B_failed Reasons for Current COT Paths:**
- **H-001 / cot_positioning / cftc_cot_commercial_signal / multi_asset_cot (COMMODITY):** REJECTED / BLOCKED (quality_gates:1444,2076) by M-095 leakage + negative post-clean EV (WR<50% PF<1.0 n=5) + conc 73%+ on CT=F + INSUFFICIENT_N/power for all 6/8 gates (G1 Sharpe fail, G4/G5/G6 0 windows/power, G7/G8 marginal/failed on clean). Partial guards do not close all emission paths. Matches registry + cot_paper_pilot + prior B_failed marker.
- **commodity_cot_contrarian (sidecar):** OPT-IN / UNWIRED for prod; synthetic only; same underlying COT data hygiene risk + low n.
- All COT-derived: fail G1-G8 or data gate; quarantine pending full re-agg + uniform enforcement.

## 3. Concrete Guard Improvements Proposed (Prioritized, File-Exact)

1. **Uniform publication-lag enforcement (P0, fail-loud):** 
   - Import/share `_is_cot_row_public` (or equiv using report's as_of_date vs now - COT_PUBLICATION_LAG_DAYS=3) from cot_positioning.py into scrape_cftc_cot_weekly (scraper.py:1745+ before any signal calc/emit at 1831 and 1925) and any other COT emitters (dashboard_generator COT paths, commodity_signal_generator, new_strategies_emitter).
   - Add at top of cftc fn: `if not _is_cot_row_public(latest.get("as_of...") or report_date): continue` + log "SKIP: CFTC report not public (M-095 guard)".
   - Extend to historical backfills / re-agg scripts (verify_cot_post_patch.py, backfill_*.py).
   - Citation: mirror commodity_cot_contrarian:236 and cot_positioning:332; close the bypass in scraper cftc path.

2. **Full historical re-agg + strict 1-per-CFTC-cycle dedup + lag retro-enforcement:**
   - Re-process ALL historical COT picks in trading_picks/*.json, universal_resolved_picks.json, closed_picks, MySQL ejaguiar1_* tables, edge_stability_COMMODITY.json, cot_*.json, dashboard_data using COT release key (symbol + as_of_date or CFTC report Friday).
   - Use atomic ledger + O_EXCL everywhere (extend PR#994 pattern).
   - Target post-reagg: n>=20 clean unique cycles for flagship, PF>=1.5 WR>=50% on non-CT=F or diversified.
   - Scripts: extend tools/verify_cot_post_patch.py + cot_pipeline_audit recs + FIRING9 backfill pattern.
   - Re-gen all artifacts + re-validate.

3. **source_system tagging for CFTC (hygiene + auditability):**
   - In scraper.py _make_pick for cftc_cot path (1832/1926): force `source_system="cftc_socrata" if api_success else "cftc_proxy_rsi"`.
   - Update commodity_cot_contrarian (already "commodity_cot_contrarian"), cot_positioning, dashboard_generator adapters, quality_gates COT_DEDUP, pick_schema.
   - Add to JSON_PICK_SOURCES / collect_sources for traceability. Enables "fail-loud on suspicious CT=F CFTC emissions".

4. **Fail-loud / hard conc cap + CT=F probation on COT paths:**
   - In quality_gates + concentration_cap.py + emitter: if strategy in COT_* and symbol=="CT=F" and no explicit ALLOW_CTF_COT=1: log ERROR + drop or shadow (extend M-003 / BLOCKED).
   - Enforce per-symbol/strat <=25-30% of COMMODITY COT PnL (M-002 style).
   - In scraper cftc loop: if symbol=="CT=F": warn/fail-loud unless diversified basket.

5. **Additional:**
   - Stamp `latest_cot_date` + `report_date` from actual API as_of in cftc_cot_weekly (not computed Friday).
   - Update M-001 gate + dashboard freshness to use real CFTC pub time.
   - CI test: assert no COT pick with report_date within <3d of generated_at.
   - For H-001 revival: only via new construction (e.g. H-021 small-spec) + M-107 pre-reg + full guards.

These close the remaining vectors cited in task (M-095, lag, CT=F mass, tagging).

## 4. Salvageability of Commodity Carry/Momo Strategies Post-Hygiene + COT Guard

- **commodity_carry_momo_double_sort (tools/research/commodity_carry_momo.py:140-244 + audit_dashboard/data/commodity_carry_momo.json:2-49):** **Potentially salvageable post-fixes.** Non-COT (mom 12-1 + carry_proxy quintile intersect; academic Fuertes 2010 ref). Currently B_failed (firing3/4: 0 closed resolved for exact name, n low, "MODERATE-confidence" proxy caveat, G1-8 INSUFFICIENT_N/power=0; 1 OPEN SHORT OJ=F). Post COT hygiene (removes CT=F pollution from class aggregates) + true carry (FRED inventory or basis not rolling-mean proxy) + conc cap (<=25% any sym) + 30-60d accrual + harness run (commodity_strategy_harness + statistical_validation_framework on clean COMMODITY slice): candidate for 6/8 if Sharpe>=0.7+ / WR>50 / PF>1.2 / WF>=3 admissible (target per 90day). Wire as sidecar first (already "WIRED").
- **seasonal_momentum / commodity_seasonal (alpha_engine/commodities_strategies.py:87 + commodity_seasonal.py:197):** Salvageable academically (Bodie ref; per-symbol bullish months + filters). Low production resolved attribution; UNTESTED_DATA_GAP in registry for related H. Post-hygiene + diversified (ex heavy CT=F) + daily PnL: run full gates. Low power currently.
- **oil_inventory_momentum (commodities_strategies:268, H-004 family), commodity_tsmom_12m (919, cta overlap), metals_mr (366), dxy_inverse (805):** Similar — academic + harness cats; currently INSUFFICIENT or REJECTED (sign-unstable for inventory/roll). Salvageable if post-COT clean n>50-100 + CPCV/DSR + no proxy leakage.
- **Overall post-hygiene outlook:** COMMODITY class can graduate from B_failed if diversified basket (carry+momo+seasonal+tsmom quintiles, conc<=25%) achieves clean n>=100, G4 pass, SPA>0, PF>1.5 WR>50 on resolved (vs current flagship negative). 90day plan + harness design support; yfinance futures quality + no micro CT=F still risks. De-emphasize vs cleaned EQUITY T2 or external (KMLM) until proven.

**Non-salvageable:** Pure COT directional (H-001 family) — "NOT salvageable" per registry; only fundamentally different (small-spec exhaustion) with strict guards.

## 5. New Candidate Families That Could Pass 6 Gates Once Leakage Closed

- **H-021 small-spec COT exhaustion (tools/hypothesis/h021_cot_smallspec_harness.py:155+; registry:1179+):** NEAR_ADMISSIBLE now (n=2/3 windows); post full COT hygiene + lag/dedup/source tagging: high potential (fades retail/small vs commercial; free CFTC). Pre-reg M-107, run on clean slice.
- **Diversified cross-sectional commodity carry + mom (extend commodity_carry_momo + basis_strategies.py + futures_strategies.py):** Quintile on 18-25 sym (ex CT=F or cap it), true basis (second-month vs spot via yf rolls or FRED), + COT filter only as regime (post-guard). Target Sharpe 1.0-1.4 per academic.
- **FRED-augmented inventory surprise / term structure (H-004/H-027/H-034 revival; commodity_crop_condition.py, fred_data_fetcher.py):** Physical inventory (not COT proxy) + seasonal + tsmom. UNTESTED/REJECTED due data gap/hygiene; clean COT context + new data may admit.
- **commodity_seasonal.py variants + spread (agricultural_spread, energy_momentum_breakout):** Harness cats; academic only currently. Post n accrual + gates.
- **Ensemble non-COT COMMODITY (seasonal + tsmom + carry quintiles + dxy inverse):** From kimi taxonomy 150+ (tools/kimi.../COMMODITY_STRATEGY_REPORT.md:627+); CPCV/DSR on post-clean resolved.
- **COT as meta/regime only (not primary signal):** e.g. COT extreme as filter on carry/momo entries (after guards close leakage).

**Recommendation:** P0 execute proposed guards + re-agg (use FIRING9 backfill as template + cot verify tools). Then: `python tools/validate_resolved_picks.py --by-asset-class --min-trades 10 --save-csv reports/continual_research/6gate_validation/firing9_commodity_postfix.csv`; run commodity_strategy_harness + statistical_validation_framework + edge_stability on clean slice; 6/8 gate per 6GATES MD; pre-reg any promoted (M-107); create A_passed/ or updated B_failed marker; update public log + CONTINUAL...BASELINE + hypothesis_registry. CT=F: probation or diversify only. No live sizing until n/power + all-classes shadow.

**Citations summary (all absolute, key lines/sections as above):** See full list in sections 1 + prior B_failed commodity marker lines 64-81 + Firing9 public log:51 + registry:7-31 + quality_gates:1436/2075 + scraper:1716/406 + cot_positioning:45/290 + cot_paper_pilot_status.json:2-50 + KIMI_AUDIT:90 + 90day_COMMODITY:84 + commodities_strategies.py:87+ + carry_momo.py:84.

*Marker created 2026-05-21 Firing 9 COMMODITY subagent (parallel to CRYPTO/EQUITY/H-037). Pattern-matched to B_failed/commodity_strategies_cot..._2026-05-21.md + FOREX stressed. Hygiene first, then re-harness salvageables + H-021 family. Ready for PR/execution handoff.*

## Appendix: Prioritized Fix List (Actionable, File-Exact)
1. Patch scrape_cftc_cot_weekly (copy_trader_intel/multi_asset_copytrader_scraper.py:1745 before 1780 signal, and 1925 fallback) + add lag import/guard + source_system="cftc_*" + CT=F fail-loud (P0, 2-4h).
2. Full re-agg dedup script (extend FIRING9_TAGGING... + verify_cot_*.py + cot_pipeline recs) on all COT artifacts/DB (P0, 1d).
3. Unify lag fn + CI assert (cot_positioning.py:290 export; quality_gates + dashboard_generator COT sections).
4. Update registry H-001 note + add H-021 pre-reg if promoting (hypothesis_registry.json).
5. Run validate + harness post-fix; move to A/B markers (tools/validate_resolved_picks.py + 6gate dirs).
6. Conc cap + blacklist CT=F COT (quality_gates.py COT_DEDUP + concentration_*.py).
7. Wire diversified carry/momo + H-021 shadow (post n).

All ties directly to task requirements + session memory (EQUITY tagging separate P0; COT hygiene blocks COMMODITY power outside CRYPTO).