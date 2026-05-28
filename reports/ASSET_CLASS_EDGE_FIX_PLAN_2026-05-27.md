# Asset-Class Edge & Nav-Integration Fix Plan — 2026-05-27

**Author:** 7-agent swarm (CRYPTO / EQUITY / COMMODITY / ETF / FOREX / BOND specialists + nav-integration auditor)
**Scope:** Every clickable nav surface on `findtorontoevents.ca/audit` + integration parity with `/audit/pick_funnel.html`.
**Ground-truth sources** (read, never invented):
- `audit_dashboard/data/money_ready_verdict.json` (canonical verdict, 2026-05-25)
- `audit_dashboard/data/nav_surface_edge_matrix.json` (8 surfaces × 6 classes, 2026-05-25T04:50Z)
- `audit_dashboard/data/pf_registry.json` (policy-clean-net PnL, 2026-05-25T04Z)
- `audit_dashboard/data/pick_summary_stats{,_2w,_48h}.json`
- `audit_dashboard/data/pick_funnel_{90d,today,rejected_universe}.json`
- `audit_dashboard/data/cot_paper_pilot_status.json` (2026-05-27T19:24Z)
- `audit_dashboard/data/hourly_asset_class_24h_report.json`

---

## 1. EXECUTIVE VERDICT — Edge Per Asset Class (current truth)

| Class | Where it shows edge | Where it's **falsified / disputed** | Verdict (today) |
|---|---|---|---|
| **CRYPTO** | Nowhere honest. Smart/VA/HC/ELITE all PF 9-18 but **DISPUTED** (claude_gainer_st 91.7% concentration + EXPIRED→WON mislabels). Honest cells: pf_registry policy-clean PF 0.98 / WR 39.7% / n=229; money_ready PF 0.96 / WR 31.3% / DSR 0.0073. | All 4 inflated surfaces. Banner exists on pick_funnel.html (line 118) but **does not propagate to template.html**. | **FAIL** — no real edge; falsified DSR claim |
| **EQUITY** | Single sleeve: `stocks_rsi2_pullback` n=70, WR 62.9% (template L1143). UEPS pipeline live but n=0/100 (long-term thesis-break resolver). | Template L897 banner "T2 candidate PF 1.55 WR 51.4% n=426" — current is PF 0.70 WR 37.4% n=567. 14d "67% WR PF 5.56 n=8249" → 61.6% single-source `smart_money` + 6 dup-groups. | **FAIL** at class level, **edge in 1 sleeve** |
| **COMMODITY** | None statistically. Policy-clean n=3 (2 SI longs + 1 GC short) — INSUFF-N. **COT/CT=F DSR=1.0 has been FALSIFIED 2026-05-13** (6.33× over-emission); pilot now `SHADOW_INSUFFICIENT_N`, `dsr=null`. | Template L854, L900, L1141 still cite "DSR=1.0, most validated edge" — directly contradicted by `cot_paper_pilot_status.json`. | **FAIL** — falsified edge still rendered |
| **ETF** | Backtests are best in the repo: `etf_rotation_vix_regime` PF 4.50 / WR 80.8% / MDD 7%, `etf_sector_rotation` PF 2.05 / WR 70.5%. **ZERO production wire-up** — `_ETF_FV_EXEMPT` carve-out hides this. | Template L899 "PF 1.33 WR 57.4% n=108" — actual n=1 clean-net, n=13 dashboard. money_ready_verdict.json has **no ETF row at all**. | **INSUFF-N** but **orphan backtest gold** |
| **FOREX** | None. PF 0.39 / WR 15.4% / n=13 policy-clean — worse than CLAUDE.md cites. Mutation autopsy: SHORT PF 8.11 vs LONG PF 0.80. | Template L861, L901, L1177 all stale ("PF 0.86 WR 55%"). `forex_rsi2_mean_reversion` blocked in source list but leaks through `multi_asset_copytrader` emit path. | **FAIL** — biggest noise sink (15,720 scanned, 0 HC) |
| **BOND** | Backtests: `bond_hyg_lqd_v1` PF 1.62 WR 62.7%, `bond_tlt_ief_v3_24m` PF 1.29 WR 54.3% — all orphan. | Template L902, L13066 cite "PF 0.66 WR 54.5% n=11" — disagrees with pf_registry (n=2), pick_summary (n=7), funnel (n=12 decisive). 5 different numerators. BOND row missing from `money_ready_verdict.json` and **not rendered on pick_funnel.html**. | **INSUFF-N** + universe too narrow (5 symbols vs 25+ available) |

### Bottom line
**0 / 6 classes pass Tier-2 today.** Of those:
- 2 classes (CRYPTO, COMMODITY) have **falsified/disputed surface numbers still rendered to users**.
- 2 classes (ETF, BOND) have **proven backtest edge that is 100% orphan** per Wire-Up Rule.
- 1 class (FOREX) is a pure value-destruction pipeline that should be **scanner-frozen** until external (MyFXBook) replication validates.
- 1 class (EQUITY) has one real sleeve (`stocks_rsi2_pullback`) drowned in oscillating noise from `smart_money` + `AlphaEngine` single-source concentration.

---

## 2. WHY NO EDGE — Common Root Causes Across Classes

| Root cause | Where it bites | Evidence |
|---|---|---|
| **Concentration not gated before DSR/SPA** | CRYPTO (BTCUSDT 34.6%, claude_gainer_st 91.7%), COMMODITY (CL=F 100% in money-ready row), FOREX (USDCAD=F 55.2%, AlphaEngine 100%), ETF (TLT 38%, QQQ 77.8% in 48h panel) | `money_ready_verdict.json` `concentration_capped: false`; caveat strings present in `pick_summary_stats_*.json` but UI ignores them |
| **EXPIRED → WON resolver mislabel** | CRYPTO `claude_gainer_st`, FOREX 14d (`EXPIRED_pos_pnl_share=76%_likely_mislabeled_WON`), COMMODITY COT over-emission | Caveats in stats JSON; nav-matrix doesn't filter on them |
| **Single-source over-emission** | CRYPTO `incubator_gainer` 66%, COMMODITY `multi_asset_cot_positioning` 6.33× over-emit, FOREX `multi_asset_copytrader` bypassing blocks | `cot_paper_pilot_status.json::over_emission_ratio=6.33`; `pick_summary_stats_2w` `top_source_share` |
| **Resolver flat-rate too high** | EQUITY 1982 closed → only 125 decisive (94% flat), BOND 133 closed → 12 decisive (91% flat) | `pick_funnel_90d.json` decisive vs closed counts; PNL_WIN_THRESHOLD = 5bp too tight for bond ETFs |
| **Backtest → live propagation broken** | ETF (5 wire-up gaps), BOND (6 orphan backtests), all violate CLAUDE.md Wire-Up Rule | `grep` for caller in production scanners returns 0 hits for `bond_tlt_ief*`, `etf_sector_rotation`, `bond_hyg_lqd_v1` etc. |
| **Stale template banners** | EQUITY L897, CRYPTO L898, COMMODITY L900, FOREX L901, BOND L902 — all hard-coded numbers ≥6 days old, disagree with live JSON | Direct file diff vs `pf_registry.json` + `money_ready_verdict.json` |
| **No production scanner / narrow universe** | BOND (5 symbols), ETF (no live emitter that produces closeable picks) | `alpha_engine/bond_scanner.py` symbols list, `tools/etf_sector_emitter.py` monthly-rebalance with no entry/exit |
| **Stale `CLAUDE.md` snapshots** | Per-class headline strings cite 90d numbers that are 6+ days stale | CLAUDE.md vs current `money_ready_verdict.json` |

---

## 3. NAV-INTEGRATION GAPS (template.html ↔ pick_funnel.html)

### 3.1 Surfaces template.html exposes but pick_funnel.html / nav-surface-matrix DOES NOT cover

| Missing surface | template location | Required data source |
|---|---|---|
| Anti-Overfit (DSR) | L1365 (`anti_overfit.html`) | `anti_overfit_audit.json` (exists) |
| COT Paper Pilot | L1366 (`paper_pilot.html`) | `cot_paper_pilot_status.json` (exists) |
| Strat. Leaderboard | L1370 (`data-tab="leaderboard"`) | `dashboard_data.json::leaderboard` joined per-class with `pf_registry` |
| Permutations | L1371 (`data-tab="permutations"`) | `dashboard_data.json::permutations` |
| Performance tab (Sections 1-5) | L1372 (`data-tab="performance"`) | `dashboard_data.json::picks.recent_closed` segmented by class |
| Portfolios | L1364 (`portfolio_history.html`) | `consolidated_portfolios.json` |
| AI Tournament | pick_funnel L88 link | `ai_tournament_leaderboard.json` + `ai_tournament_model_summary.json` |
| HyroTrader | Links tab L2391 | `hyrotrader_picks.json` |
| Score Tracker / ML Health | L1373-1374 | Unbuildable server-side (LocalStorage / per-model only) |

**Currently emitted by `build_nav_surface_matrix.py` (only 8):** verified_alpha, smart_picks, money_ready, high_conviction, ueps_long_term, ueps_swing, ueps_closed, elite_display_tier.

### 3.2 Numeric Drift (5 documented examples)

| # | Cell | template.html value | nav_surface_edge_matrix.json value | Cause |
|---|---|---|---|---|
| 1 | CRYPTO Smart Picks WR | 46.3% PF 1.30 n=8115 (L898, `asset_class_health`) | 78.9% PF 9.69 n=337 (`smart_picks` predicate) | Different pools; pick_funnel L278 admits 46-pp gap; template doesn't surface DISPUTED chip |
| 2 | EQUITY Smart Picks | "T2 candidate PF 1.55 WR 51.4% n=426" (L897) | PF 0.56 WR 50.0% n=4 | Headline = full-history `asset_class_health` (stale); matrix = `recent_closed` post-predicate |
| 3 | CRYPTO HC PF | "recent PF 0.89" (L968 hf_stats) | PF 18.5 (HC matrix) | 21× spread; same page, no resolution |
| 4 | EQUITY Money Ready WR | "stocks_rsi2_pullback n=70 WR 62.9%" (L1142) | WR 88.9% PF 5.14 n=9 (XOM 55% concentration) | Different strategy slices; not cross-linked |
| 5 | UEPS EQUITY | No headline number (tab L1941) | WR 34.2% PF 0.63 n=316 (long_term) | Tab silent; matrix flags failure |

### 3.3 Per-tab class-filter parity gaps in template.html

- **Smart Picks / Verified Alpha tabs**: render flat lists — **no per-class WR/PF panel inside the tab**. User must leave to pick_funnel.html.
- **Performance tab**: Sections 1-5 all-class only; Section 6 has class dropdown but only on Super Parameter sub-table.
- **Strat. Leaderboard**: client-side `filterAssetClass` subset but no per-class WR/PF/holdout computed.
- **Score Tracker / ML Health / Permutations**: no per-class breakdown at all.

---

## 4. FIX PLAN — Ordered by ROI

### TIER 0 (P0 — falsified numbers visible to operators; ship today/tomorrow)

| # | Action | File / Function | Risk if not fixed |
|---|---|---|---|
| 1 | **Kill stale "DSR=1.0 / most validated edge" copy** for COMMODITY/CT=F | `audit_dashboard/template.html` L854, L900, L1141 (Sahil-claim modal) | Operator sizes capital on falsified edge |
| 2 | **Quarantine `claude_gainer_st` from Smart/VA/HC/ELITE cohorts** | `audit_trail/quality_gates.py` — add `BLOCKED_SOURCE_SYSTEMS.add('claude_gainer_st')`. Follow `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` first | Removes 91.7% concentration; collapses 4 inflated CRYPTO surfaces in one line |
| 3 | **Enforce concentration gate BEFORE DSR/SPA** in money_ready verdict | `tools/money_maker/build_money_ready_verdict.py` — auto-FAIL when `top_symbol_share>0.30` OR `top_source_share>0.40` | Closes the open P0 from CLAUDE.md (2 false Tier-1 PASSes 2026-05-17) |
| 4 | **Propagate CRYPTO DISPUTED banner from pick_funnel.html → template.html headline** | Lift `pick_funnel.html:118-129` markup, condition on `money_ready_verdict.CRYPTO.verdict=="NOT_READY"`, place above `template.html:898` per-class spans | Removes 46-pp WR misrepresentation |
| 5 | **Freeze FOREX Smart/HC admissions** until MyFXBook replication validates | `audit_trail/quality_gates.py::passes_smart_gate` — add `BLOCKED_ASSET_CLASSES = {"FOREX"}` short-circuit; keep ingest for audit visibility | Stops PF-0.39 bleed; FOREX is the largest noise sink (15,720 scanned, 0 HC) |
| 6 | **Fix `forex_rsi2_mean_reversion` block leak through `multi_asset_copytrader`** | `audit_trail/quality_gates.py` L1456, L1924 — add `BLOCKED_ASSET_SOURCE_PAIRS += [("FOREX","multi_asset_copytrader"), ("FOREX","forex_copy_trader")]` | Removes top-volume drag emitter |

### TIER 1 (P1 — drift / data binding; this week)

| # | Action | File |
|---|---|---|
| 7 | **Rebind ALL per-class headline banners** (L861, L897-902, L968, L1145, L1177, L1240, L13066) to live JSON — `pf_registry.by_asset_class_policy_clean_net` for the headline; `money_ready_verdict` for the verdict chip | `audit_dashboard/template.html` + dashboard generator |
| 8 | **Fix `verified_alpha` "no_closed_picks" mislabel** when `passed_verified_alpha>0` but `n_closed_va==0` — emit `awaiting_closure` instead | `tools/audit_pick_funnel/build_nav_surface_matrix.py` |
| 9 | **Add `money_ready_verdict.json` ETF + BOND rows** (currently silently dropped) — force `INSUFFICIENT_N` rather than absent key | verdict builder |
| 10 | **Fix UEPS gate-floor doc drift** | `audit_dashboard/pick_funnel.html:207` change `EQUITY=60` → `=50` (one-line) |
| 11 | **Quarantine inflated 14d/48h cells** behind single-source caveat — if `top_source_share>0.9` OR `top_symbol_share>0.75`, render as `INSUFF-DIVERSITY` not the raw PF | `audit_dashboard/template.html` Active Picks section + dashboard generator |
| 12 | **Render BOND row on pick_funnel.html** (data exists in JSON, HTML doesn't surface it) | `audit_dashboard/pick_funnel.html` |
| 13 | **Add COMMODITY governance banner to pick_funnel.html** mirroring CRYPTO DISPUTED ("COT pilot DSR=1.0 falsified 2026-05-13") | `audit_dashboard/pick_funnel.html` |

### TIER 2 (P1 — nav-surface-matrix completeness; this sprint)

| # | Action | File |
|---|---|---|
| 14 | **Extend `build_nav_surface_matrix.py` SURFACES list** to add: `anti_overfit_dsr`, `paper_pilot_cot`, `strat_leaderboard`, `portfolio_history`, `ai_tournament`, `performance_all_class`, `permutations`. Each predicate documented in §3.1 above. Join `anti_overfit_audit.json` on strategy name; join `cot_paper_pilot_status.json` for SHADOW state | `tools/audit_pick_funnel/build_nav_surface_matrix.py` |
| 15 | **Update `n_surfaces` Bonferroni count automatically** (already self-corrects via `len(SURFACES)` — verify) | same file |
| 16 | **Add per-class WR/PF panel atop Smart Picks + Verified Alpha tabs** with link "See per-class holdout analysis → pick_funnel.html#nav-surface-matrix" | `audit_dashboard/template.html` L1435, L1478 |
| 17 | **Add per-class summary row to Strat. Leaderboard** grouping `D.leaderboard` by `asset_class` | `audit_dashboard/template.html::renderLeaderboard` L12093 |
| 18 | **Add per-class breakout to Performance tab Sections 1-4** via `calcStats(class)` loop before Section 1 | `audit_dashboard/template.html::renderPerformance` L15852 |

### TIER 3 (Wire-Up Rule — the orphan backtests; opt-in sidecars per CLAUDE.md)

| # | Action | File | Backtest evidence |
|---|---|---|---|
| 19 | **Wire `etf_sector_rotation` as opt-in sidecar with real close path** — convert monthly-rebalance candidates into resolver-compatible picks (TP/SL = ±1σ monthly return) | `tools/etf_sector_emitter.py` + caller in `audit_trail/dashboard_generator.py:3975` | PF 2.05 / WR 70.5% / Sharpe 0.97 (etf_sector_rotation_backtest.json) |
| 20 | **Wire `etf_rotation_vix_regime` overlay** on top of #19 | `alpha_engine/etf_scanner.py` STRATEGIES | PF 4.50 / WR 80.8% / MDD 7.05% / Sharpe 2.10 — **highest Sharpe in repo** |
| 21 | **Remove `_ETF_FV_EXEMPT` cold-start exemption** in `quality_gates.py:8999` once #19 ships | `audit_trail/quality_gates.py` | currently hides "0 closed picks" failure |
| 22 | **Wire `bond_tlt_ief_v3_24m` filter** into bond_scanner as opt-in sidecar | `alpha_engine/bond_scanner.py:run_bond_scanner` | PF 1.29 / WR 54.3% / MDD 23% on 24m walk-forward |
| 23 | **Wire `bond_hyg_lqd_v1`** credit risk-on/off rotation | `alpha_engine/bond_scanner.py` | PF 1.62 / WR 62.7% — highest BOND backtest PF |
| 24 | **Expand BOND universe** from 5 symbols (TLT/IEF/LQD/HYG/SHY) to 15+ (add AGG/MUB/MBB/BNDX/EMB/BND/VCIT/VCSH/VGSH) | `alpha_engine/bond_scanner.py` | n=2 in 90d is universe-limited |
| 25 | **Whitelist EQUITY Smart Picks to proven sleeves** — `STRATEGY_SCORE_OVERRIDES`: `stocks_rsi2_pullback: 35`; gate other EQUITY strategies behind `min_trades≥20 & FwdWR≥0.55` | `audit_trail/quality_gates.py` | sleeve n=70 WR 62.9% verified |
| 26 | **Wire UEPS into `pf_registry`** so SPA/PBO has a 2nd EQUITY strategy slot | `tools/build_pf_registry.py` | unblocks PBO "need ≥2 strategies" |

### TIER 4 (resolver + emission discipline; this month)

| # | Action | File |
|---|---|---|
| 27 | **Lower `PNL_WIN_THRESHOLD_BY_CLASS` for BOND** 5bp → 2bp (current 91% flat-rate) | `alpha_engine/outcome_resolver.py:115-126` |
| 28 | **Force-decisive EQUITY resolver** — drop 5bp → 2bp OR cap hold at 5d (current 94% flat) | `alpha_engine/outcome_resolver.py` |
| 29 | **Force-close 48h stale CRYPTO actives** (322 actives, 0 closed in 48h starves recency panel) | `python alpha_engine/outcome_resolver.py --asset-class CRYPTO --max-age-hours 48 --force-expire` |
| 30 | **Per-source emission cap (≤30% of class daily picks)** to stop `incubator_gainer 66%`, `multi_asset_copytrader 100%` patterns | `alpha_engine/smart_picks_engine.py::_select_top_n_per_class` |
| 31 | **Fix COT 6.33× over-emission** — hash `(symbol, release_week)` and refuse duplicates | `alpha_engine/strategies/cot_paper_pilot.py::_emit_signal` |
| 32 | **Fix EQUITY confidence-band penalty** — invert 0.85-0.90 band (20% WR — worst band) from booster to crusher | `audit_trail/quality_gates.py` confidence penalty stack |

### TIER 5 (external replication gates — re-entry path for blocked classes)

| # | Action | File |
|---|---|---|
| 33 | **Create `alpha_engine/myfxbook_replication_gate.py`** — requires live MyFXBook strategy PF>1.3 / n≥50 / 30d real before any FOREX strategy unblocks; wire from `passes_active_gate` per Wire-Up Rule | new + `audit_trail/quality_gates.py` |
| 34 | **Integrate PIMCO BOND / AGG benchmark proxies into `alpha_engine/fred_macro_context.py`** for regime-conditioning of bond_tlt_ief_v3 filter | `alpha_engine/fred_macro_context.py` |
| 35 | **Add Hyperliquid HLP / QMOM external comp for CRYPTO** so a real-broker baseline must be beat before any size-up | new gate file |

### TIER 6 (docs / CLAUDE.md refresh)

| # | Action | File |
|---|---|---|
| 36 | **Refresh CLAUDE.md per-class snapshot** to current numbers (replace stale ETF "PF 11.99 n=2", BOND "n=8", COMMODITY "n=28", FOREX "USDJPY 55%", EQUITY "n=33", CRYPTO "78.9%") | `CLAUDE.md` |
| 37 | **Update CLAUDE.md COT line** — DSR=1.0 is FALSIFIED; pilot is SHADOW_INSUFFICIENT_N | `CLAUDE.md` |
| 38 | **Add `## Wiring Plan` template** to PR template for any new `alpha_engine/*_integration.py` or backtest-promotion | `.github/PULL_REQUEST_TEMPLATE.md` |

---

## 5. Acceptance Criteria

A class moves from FAIL → INSUFF-N → T3 → T2 only when **ALL** of these hold against canonical `money_ready_verdict.json`:

1. `n ≥ 100` decisive closed picks (post-resolver-v2 thresholds)
2. `concentration_capped: true` AND `top_symbol_share ≤ 0.30` AND `top_source_share ≤ 0.40`
3. `dsr_score ≥ 0.95` AND `dsr_ok: true`
4. SPA p-value passes on ≥2 strategies with n≥20 each
5. PF ≥ 1.5 (T2) / 2.0 (T1) on **policy-clean-net** registry, holdout PF ≥ 1.2
6. Recency 14d AND 48h panels free of `EXPIRED_pos_pnl_share_likely_mislabeled_WON` AND `single_source_concentration` caveats
7. Bonferroni-corrected pass (α=0.05/N where N = total nav_surface_edge_matrix surfaces)

**Today, 0/6 classes meet all 7.** The fix plan above is sequenced so that within ~30 days, ETF + BOND (via Tier 3 wire-ups) and EQUITY (via Tier 3 sleeve whitelist + Tier 4 resolver) become realistic T3 candidates; CRYPTO, COMMODITY, FOREX require Tier 5 external replication before any honest verdict above INSUFFICIENT_N.

---

## 6. Open Disagreements Between Sub-Audits (not yet resolved)

- **CRYPTO Smart Picks WR**: 4 different numbers across 4 files. Treat as **DISPUTED until** `nav_surface_edge_matrix.json` adds a `source_note` field and `template.html:898` switches its data source to `pf_registry.by_asset_class_policy_clean_net`.
- **BOND n**: 5 different numerators (template L13066 says n=11, pf_registry raw says n=2, pick_summary says n=7, pick_funnel says n=12 decisive, policy-clean says BOND absent). Action 7 + 9 + 12 resolve this.
- **EQUITY 14d vs 90d**: 14d says 66.7% WR PF 5.56 but 6 dup-groups + 61.6% smart_money concentration; 90d says 37.4% WR PF 0.70. Treat 14d as INSUFF-DIVERSITY pending Action 11.

---

## 7. References

- All 6 per-class audits captured in this swarm run (CRYPTO/EQUITY/COMMODITY/ETF/FOREX/BOND specialists)
- Nav-integration audit (dashboard-contract-reviewer agent)
- `CLAUDE.md` MAJOR GOALS block (lines 5-25)
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- `reports/cot_paper_pilot_overemission_falsified_20260513.md`
- `reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md` (Wire-Up Rule precedent)
- `reports/asset_class_90day_plan_{BOND,COMMODITY,CRYPTO,EQUITY,ETF,FOREX,FUTURES}_2026-05-15.md`
