# PF1 — Review of peer folder `finpredict` (v1)

**Verdict: PASS (conditional) for merge-readiness.**
Mergeable as a master-plan *input* after the corrections in §5 and the vetoes in §6. Nothing in it invalidates our FAIL
verdict; several items materially strengthen it. Three proposed fixes must be vetoed before any
cherry-pick (BOND entry-copy backfill, FOREX "data purge", CRYPTO "relabel/purge"), and one action
item is stale (the JS parse fix is already on `origin/main`).

- Reviewer: PF1 (read-only; no repo source modified)
- Review clock: 2026-11-14 ~17:55–18:05Z
- Folder: `.kilo/worktrees/finpredict/2026-11-14/finpredict/2026-11-14T160004Z/`
- Peer worktree HEAD: `817f3735997` (branch `archive/2026-11-14-finpredict`)
- Our worktree HEAD: `27a6d6bed79` (branch `finpredict-v2`); `origin/main` = `7e8c7ac82da`
- Source-blob equality check: `scanner.py`, `sync_summary_picks_json.py`, `quality_gates.py`,
  `dashboard_generator.py`, `prediction_market_consensus.py`, `kalshi_signal_agent.py`,
  `multi_asset_copytrader_scraper.py` are **byte-identical** between the two worktrees, so the
  cited `file:line` values are directly comparable (no branch drift on those files).

---

## 1. File inventory (25 files, 197,022 bytes, 1,871 md lines)

| # | Path (relative to folder) | mtime | Size | One-line description |
|---:|---|---:|---:|---|
| 1 | `README.md` | 16:07 | 4,546 | Session summary: verdict, peer cross-ref (v3, inspect-wt), unique additions (127-pick batch, flat-3% cohort, metric liveness). |
| 2 | `updates/2026-11-14-prediction-system-audit.md` | 16:22 | 16,676 | The full 178-line audit: Actions, per-class actives, frozen data, metric liveness, closed picks, multiple-testing verdict, UNVERIFIED. |
| 3 | `quick-wins/README.md` | 16:22 | 5,207 | Priority matrix (QW-1…19), apply order, "peer-superseding" note, guardrails. |
| 4 | `quick-wins/OVERALL.md` | 16:20 | 5,076 | Cross-cutting QW-1…8: honesty metrics, edge_ratio, INSUFFICIENT, sidecars, outlier clamp, Actions, gated rows, MF claim. |
| 5 | `quick-wins/by-asset-class/CRYPTO.md` | 16:20 | 4,196 | 7 fixes: Binance failover, None→0, entry sanity, unquoted label, Kalshi, flat-3% cohort, forward-seed flag. |
| 6 | `quick-wins/by-asset-class/EQUITY.md` | 16:20 | 1,717 | `last_quote`/`price_asof` provenance; n + Wilson CI headline. |
| 7 | `quick-wins/by-asset-class/ETF.md` | 16:20 | 1,365 | "Parked at last close" label; hide empty UEPS Swing/Closed-Holds tabs. |
| 8 | `quick-wins/by-asset-class/FOREX.md` | 16:20 | 2,252 | Purge 11 phantoms; `stock_forex_prices.json` age-guard; consensus threshold 1→2. |
| 9 | `quick-wins/by-asset-class/FUTURES.md` | 16:20 | 1,056 | Full ISO timestamps; hide gated rows. |
| 10 | `quick-wins/by-asset-class/COMMODITY.md` | 16:20 | 970 | Backfill `current_price` at emit; drop pick on fetch failure. |
| 11 | `quick-wins/by-asset-class/BOND.md` | 16:20 | 1,408 | Price "backfill" (stamps `current_price=entry_price`); auto-expire unquoted seeds. |
| 12 | `quick-wins/by-asset-class/MUTUAL_FUNDS.md` | 16:20 | 1,154 | De-advertise unbuilt MF; optional future ranker scope. |
| 13 | `master-plan/PLAN.md` | 17:47 | 7,150 | Phase 0–3 master plan, P0-1…12, binding veto list, verification commands. |
| 14 | `master-plan/inputs/01-crypto.md` | 17:47 | 17,324 | CRYPTO consolidation: C1–C6 consensus, F-1…F-23 unified fixes, conflicts, P0 order. |
| 15 | `master-plan/inputs/02-equity-etf.md` | 17:47 | 11,702 | EQUITY+ETF consolidation: C1–C5, F1–F15, conflicts (v4 freshness, ALIVE vs unpriced), P0 order. |
| 16 | `master-plan/inputs/03-forex.md` | 17:47 | 12,414 | FOREX consolidation: PR#6 bypass, fix table A–F, purge-vs-quarantine conflict, P0 order. |
| 17 | `master-plan/inputs/04-futures-commodity.md` | 17:47 | 10,965 | FUTURES+COMMODITY consolidation: dead/blocked, F1–F16, retire-vs-restart conflict. |
| 18 | `master-plan/inputs/05-bond-mutual-funds.md` | 17:47 | 9,978 | BOND+MF consolidation: vacuous PASS, n=1, MF unbuilt, F1–F16, vetoed backfill. |
| 19 | `master-plan/inputs/06-overall-statistical.md` | 17:47 | 15,061 | Statistical consolidation: headline numbers, N=658/Bonferroni, survivorship, 9 conflicts, P0 sequence. |
| 20 | `master-plan/inputs/07-infra-ci.md` | 17:47 | 18,165 | Infra/CI consolidation: C1–C11, F1–F27, vetoed SQL, 5 conflicts, P0 order. |
| 21 | `master-plan/inputs/folder-review/v2.md` | 17:54 | 12,305 | Read-only review of our archive + `actions_deepdive/` (GA1/GA2/GA4 numbers). |
| 22 | `master-plan/inputs/folder-review/v3.md` | 17:54 | 6,978 | Review of v3: 5 iterations, 14 tests, `FABRICATED_FLAT_PNL_COHORT`, `d8c8dd` read-only violation, horizon results. |
| 23 | `master-plan/inputs/folder-review/v4.md` | 17:54 | 8,896 | Review of v4: 8 destructive fixes, stale-snapshot self-contradiction, fresh DB-health/PF corrections. |
| 24 | `master-plan/inputs/folder-review/ml.md` | 17:54 | 6,057 | Review of ML: ML sound/data broken, SQL schema drift, WUSDT/HBARUSDT magnitude errors. |
| 25 | `peer-review/PEER_RECONCILIATION.md` | 17:54 | 14,404 | The folder's own reconciliation: corrections to its audit, new peer findings, round-2 delta, coordinator actions. |

Long files were summarized, not dumped: `updates/…audit.md` (read in full), `01`–`07` (fix/conflict
tables extracted), `folder-review/*` (delta extracted), `PEER_RECONCILIATION.md` (read in full).

---

## 2. Findings — what is genuinely new vs our archive

Checked against `MASTER_AUDIT.md`, `PEER_CROSSREF.md`, `recommendations/**`, `sub/**`, `raw/**`.
"NEW" = not present anywhere in our archived files (grep-verified).

| # | Finding (delta) | Status | Evidence in PF1 | Notes |
|---:|---|---|---|---|
| N1 | `dashboard_enhancements.js` was **parse-broken** (nested ternary, `: null`) and the enhancement layer was dead since 2026-10-04; pre-FTP `node --check` guard added | **NEW finding; already fixed** | `peer-review/PEER_RECONCILIATION.md:78` | Verified: parent of `ba1378cbfa9` fails `node --check` at line 145. Fix content is already on `origin/main` (`5ad40e83c08`, ancestor of our HEAD). PF1's "confirm this merges" action is **stale**. |
| N2 | v3 commit `d8c8dd25581` flips `ml_gatekeeper._drop_leakage_enabled()` to **ON by default** and is on `origin/main` | **NEW, material** | `master-plan/inputs/folder-review/v3.md:45-60`; `PEER_RECONCILIATION.md:82` | Verified: `d8c8dd25581` is an ancestor of `origin/main`; the blob differs from our branch (`d7323bb…` vs `2d542e9…`). A production behavior change made during the audit; needs coordinator keep/revert decision. |
| N3 | v4's "PF 1.80 vs 0.37" is a **173-day-old snapshot**; fresh `money_ready` CRYPTO PF = 0.9196, policy-clean 0.2628; `evidence_db_health` shows 21 active, write 3h ago, harness 5/5; FDR/single-source gates are **disabled**, not failing; `at_signal_outcomes` "254d stale" is internally inconsistent (115,782 min = 80d) and intrabar truth is fresh today | **NEW corrective** | `folder-review/v4.md:61-87`; `PEER_RECONCILIATION.md:84` | Our `MASTER_AUDIT.md:208` currently presents v4's 1.801/0.371 as "peer-accepted". Must correct. |
| N4 | ML peer: WUSDT/HBARUSDT "correct" PnL values are off ~100–200×; `audit_trail.db` is **not fully empty** (`bt_backtest_runs=20`, `meta=1`; 8 empty tables); its SQL targets a nonexistent top-level `asset_class` column and wrong tables (`picks`/`closed_picks.db` vs `live_picks`/`pick_history`) | **NEW corrective** | `folder-review/ml.md:32-39` | Our `MASTER_AUDIT.md:207` says "9 audit tables with 0 rows" — overstated. |
| N5 | v3 has **5 iterations** (not 3), **14 tests** (docs still say 11), a `FABRICATED_FLAT_PNL_COHORT` detector, empty `T175100Z/PEER_REVIEW_R2`; horizon harness: **n≥60 → 0/6 pass; n≥30 → 0/26 pass** | **NEW evidence** | `folder-review/v3.md:7-22, 55-60` | Negative result reinforces our verdict; not re-run here (UNVERIFIED). |
| N6 | Audit-dashboard exact runtime/scheduling: p50 **97.2** / p95 **111.6** (nearest-rank 119.1) vs 60-min cron; 21/22 cancels zero-job = 35% of runs; **FTP step 56.6 min = 54%** of job; `timeout-minutes: 115` undersized; queue p50 Signal 91 / Market 118.5 / Mirror 174 / PEAD 221; PEAD 60/60 push-retry exhaustion; Mirror 60/60 FTP timeout; 166/310 scheduled workflows lack `concurrency`; 196 crons at `:00`; `dashboard-publish` shared by 3 workflows | **Ours, needs canonical merge** | `folder-review/v2.md:84-112` (reviewing `actions_deepdive/GA4`) | Present in `actions_deepdive/` (worktree root, untracked) but **not** in archived `MASTER_AUDIT.md`, which still says median 84.5 min (`MASTER_AUDIT.md:19,65`). |
| N7 | `edge_ratio` is **hyrotrader-only**; the main dashboard reads `edge_surfaces.verified_lab` (our audit note was imprecise) | **NEW corrective** | `quick-wins/README.md:70`; `quick-wins/OVERALL.md:9-11` | Low impact; correct `MASTER_AUDIT.md:80`. |
| N8 | `strong_signals.json` and `stock_forex_prices.json` have **no producer in this worktree** (orphan deploy refs), so "refresh" requires re-wiring a producer or deleting the deploy entry | **NEW root-cause detail** | `quick-wins/README.md:69` | Sharpens our "stale sidecar" recommendation (P0-7). |
| N9 | New CI failure root causes: `wrong_guesses_log.json` 100.22 MB > GH 100 MB (GH001); Playwright/chromium unsupported on `ubuntu26.04-x64`; `ValueError: Invalid frequency: ME` in `tests/test_combined_book_sleeves.py`; CPython-3.14 pandas build despite declared 3.11 (why = UNVERIFIED) | **NEW** | `folder-review/v2.md:31-39` | Our `sub/A_actions_health.md` has the clusters but not these exact errors. |
| N10 | `ai_challenge_antigravity_active_picks.json` 9 OPEN/null/no-timestamp with TP/SL breaches (BTC/SOL/TRX past TP, NEAR past SL) | **Partial — NEW detail** | `peer_review/crypto_commodity_review.md:44,65` (our own peer memo, re-surfaced) | Our plan scopes it out; PF1 proposes a destructive SQL purge (see VETO). |
| N11 | BOND layer counts: 1,293 (`picks_now_live_pnl`) vs 15 (`active_raw`) vs 2 (`live_picks.db`) vs 7 (fresh feed); `funds.html` exists but role unconfirmed | **NEW nuance** | `master-plan/inputs/05-bond-mutual-funds.md:25,61,64` | Layer naming, not a contradiction; useful for the final report. |
| N12 | MF prototype details: untracked `mutut_fund_rankings.json` **39,508 B** + `mutual_fund_nav_cache/` exist; typo at `mutual_fund_ranker.py:53`; ranker/metadata absent from `origin/main` | **Correction/refinement** | `master-plan/inputs/05-bond-mutual-funds.md:14`; `folder-review/v2.md:120` | Our correction #8 already says "untracked prototype exists"; adopt the exact output/typo detail. |
| N13 | `CT=F` `DSR=1.0` claim falsified 2026-05-13 (6.33× over-emission); `MISPRICED_ENTRY` false positive for NG=F/CL=F | **NEW supporting detail** | `folder-review/v3.md:32`; `master-plan/inputs/04-futures-commodity.md:29,80` | Corroborates CT=F over-emission already in our audit; not re-derived. |
| N14 | Concrete un-owned fixes not first-class in our plan: Kalshi `entry_price: 0 → None` + >7d gate; flat-3% placeholder detector keyed on fallback TP; forward-seed `_unquoted` flag; empty UEPS tabs; `stock_forex_prices` **consumer** age-guard; FOREX consensus 1→2; visibility-floor gating; `INSUFFICIENT` at `forward_trades==0`; outlier-clamp count; Wilson CI; entry band 0.5×–2×; PF-inflation `COUNT(DISTINCT pick_id)`; Smart-Picks n<20 gate; forward-validation repair/retire; SL/TP + LOST-sign enforcement; case-dup normalization | **NEW fixes** | see §3 | Our `recommendations/peer_review/*` flags several as "Absent"; PF1 supplies the concrete targets. |
| N15 | "Mutual funds are UNBUILT (production)" and "`kalshi_mtf_consensus` real code, frozen output" | Already covered | `updates/…audit.md:162` | Our `MASTER_AUDIT.md:104,342` has both. |
| N16 | 127-pick forward-seed batch, flat-3% cohort, 11 FOREX phantoms, 127/123 frozen, 2,267 inverse zombies, COMMODITY crypto proxies, `BLOCKED_ASSET_CLASSES`, `summary_picks` WR>100%, 105/277 date-only FOREX, 44/44 COMMODITY `=F`, ETF n=15 PF 1.84, BOND n=1, 0/9 money-ready | Already covered | `01`–`07`, `updates/…audit.md` | All present in `MASTER_AUDIT.md` / `per_asset_class/**`. |

---

## 3. ADOPT / MERGE / REJECT / ALREADY_COVERED

Canonical targets in our archive:
**C1** `recommendations/patch_plan/P0_QUICK_WINS.md` ·
**C2** `recommendations/overall/DATA_CONTRACT.md` ·
**C3** `recommendations/overall/CI_GATES.md` ·
**C4** `recommendations/per_asset_class/crypto_commodity.md` ·
**C5** `recommendations/per_asset_class/equity_etf.md` ·
**C6** `recommendations/per_asset_class/forex_futures.md` ·
**C7** `recommendations/per_asset_class/bond_mutual_funds.md` ·
**C8** `recommendations/patch_plan/P1_STRUCTURAL.md`

| # | PF1 proposal (exact path:line) | Verdict | Canonical target / rationale |
|---:|---|---|---|
| 1 | `master-plan/PLAN.md:23` P0-1 FX bucket `KeyError:'LONG'` → `alpha_engine/scanner.py:2942` | **ALREADY_COVERED** | C1 P0-1 (same line). |
| 2 | `PLAN.md:24` P0-2 `summary_picks` WR>100% → `tools/sync_summary_picks_json.py:63-65,161` | **ALREADY_COVERED (MERGE wording)** | C1 P0-2; keep our "single terminal population + clamp/assert". |
| 3 | `PLAN.md:25` P0-3 Python 3.14 / `update-environment:false` → 5 workflows | **ALREADY_COVERED** | C1 P0-3. |
| 4 | `PLAN.md:26` P0-4 audit cron ≥ p95 → `.github/workflows/audit-dashboard.yml:5` | **MERGE** | C1 P0-4. Replace our 84.5-min basis with GA4 p50 97.2 / p95 111.6 and add the FTP 56.6-min split as the real driver (`GA4 §1, §5`). |
| 5 | `PLAN.md:27` P0-5 stop `None→0.0` + entry sanity → `prediction_market_consensus.py:589-591`, `quality_gates.py:9082` | **ALREADY_COVERED / ADOPT the sanity band** | C4 P0-5; add the 0.5×–2× band (N14) to C1 P0-5. |
| 6 | `PLAN.md:28` P0-6 quote-provenance contract → `dashboard_generator.py:1618-1846, 1739-1755, 1179` | **MERGE (enum conflict)** | C2 §2.2 + C1 P0-5. Canonical enum must be chosen (see §5.1). |
| 7 | `PLAN.md:29` P0-7 render `UNQUOTED/STALE/LAST CLOSE` → `template.html:8883-8905,9134-9145,9222-9227` | **MERGE** | C5 P0-2/P0-3, C4 P0-2. Add `PLACEHOLDER` from REVIEW_SYNTHESIS. |
| 8 | `PLAN.md:30` P0-8 honesty metrics (n + Wilson + excluded + `INSUFFICIENT` + clamp count) | **ADOPT (concrete implementation)** | C3 G3 + C1 P1-6; add Wilson helper reuse (`tools/adaptive/strategy_trust.py::wilson_ci_95`). |
| 9 | `PLAN.md:31` P0-9 vacuous PASS / `NOT_BUILT` → `dashboard_generator.py:6824-6826`, `template.html:4946` | **ALREADY_COVERED** | C7 QW-1/QW-2, C1 P0-7 after peer review. |
| 10 | `PLAN.md:32` P0-10 dedup + quarantine inverse zombies → `dashboard_generator.py:9831-9836,9538,17481-17485` | **MERGE** | C1 P0-8. Use our registry key (`build_pf_registry.py:818-835`) as canonical; PF1's economic key is complementary. |
| 11 | `PLAN.md:33` P0-11 sidecar freshness manifest | **ALREADY_COVERED** | C1 P0-7 + C3 G5. Add N8 (no producer). |
| 12 | `PLAN.md:34` P0-12 security (Google keys, `dbpasses.txt`) | **ALREADY_COVERED** | C1 P0-9 + C3 G13. |
| 13 | `quick-wins/by-asset-class/CRYPTO.md:3-7` Binance mirror failover → `dashboard_generator.py:1179`, reuse `universal_price_enricher.py:172,:52` | **ADOPT** | C4 P1-1 (concrete implementation). Verified `:172` / `:52` exist. |
| 14 | `CRYPTO.md:9-13` stop `None→0.0` → `prediction_market_consensus.py:589` | **ALREADY_COVERED** | C4 P0-5. |
| 15 | `CRYPTO.md:15-19` entry sanity band → `quality_gates.py:9082`, `:2375` | **ADOPT** | C1 P0-5 / C4 P0-5. |
| 16 | `CRYPTO.md:21-25` `_unquoted` + `pnl_pct=None` → `dashboard_generator.py:1753, :481` | **MERGE (mechanics conflict)** | C2 H1; set status in enrich, null at publish (see §5.2). |
| 17 | `CRYPTO.md:27-31` Kalshi `entry_price:0`→`None`, drop >7d → `kalshi_signal_agent.py:489`, `kalshi_signals.py:621,650` | **ADOPT** | C4 (new P1 item) — verified `:489` is `"entry_price": 0`. |
| 18 | `CRYPTO.md:33-37` flat-3% placeholder detector keyed on fallback TP → `dashboard_generator.py:7516,8040-8081,8102` | **ADOPT** | C4 (new P1). Verified `:7516` and `_ac_defaults` at `:8101`. |
| 19 | `CRYPTO.md:40-44` forward-seed `_seeded_at`/`_unquoted` flag → `incubator/backtest_team/forward_signal_scanner.py` | **ADOPT** | C4 (new P1). |
| 20 | `EQUITY.md:3-7` `last_quote`/`price_asof` provenance → `universal_price_enricher.py`, `long_term_pick_contract.py`, `template.html` | **ALREADY_COVERED (MERGE label)** | C5 P0-1/P0-2. Label source truthfully (`yfinance`/`FRED`), never a hardcoded string. |
| 21 | `EQUITY.md:9-13` EQUITY n + Wilson 95% CI → `dashboard_generator.py:5916`, `summary.html` | **ADOPT** | C3 G3 + C5 P0-4. |
| 22 | `ETF.md:3-6` parked-at-close label | **ALREADY_COVERED** | C5 P0-2/P0-3. |
| 23 | `ETF.md:8-12` hide empty UEPS tabs → `ueps_section_renderer.py:909` | **ADOPT** | C5 (new small item) — verified 3 tab buttons are emitted unconditionally. |
| 24 | `FOREX.md:3-5` "purge 11 phantoms … do once as a data purge" | **REJECT (purge); MERGE (guard)** | Replace with C6 P0-4 / C7 quarantine filter. **VETO V2.** |
| 25 | `FOREX.md:10-13` `stock_forex_prices.json` >24h age-guard → `outcome_resolver.py:413`, `production_scanner.py:2362`, `continuous_improvement_monitor.py:392` | **ADOPT** | C6 (new P1) — consumer-side freshness; complements C1 P0-7. |
| 26 | `FOREX.md:16-18` consensus threshold 1→2 → `non_crypto_consensus.py:134,150` | **ADOPT (staged)** | C6 P1-2 shadow→enforce; do not enforce before shadow counts (our sequencing). |
| 27 | `FUTURES.md:3-6` full ISO timestamps → `multi_asset_copytrader_scraper.py:409,452` | **ALREADY_COVERED** | C6 P0-1 (same target). |
| 28 | `FUTURES.md:9-10` hide gated rows | **MERGE** | C6 P1-6 (make `_gate_passed=false` exclusion explicit). |
| 29 | `BOND.md:3-5` stamp `current_price = entry_price` after `_save_bond_picks()` | **REJECT** | **VETO V1** — directly contradicts `PLAN.md:62` and C2 H1. Use C7 QW-4 real marks. |
| 30 | `BOND.md:9-11` auto-expire `current_price==null && age>24h` as `STALE_NO_QUOTE` | **MERGE (guarded)** | C7 QW-7 / C6 P1-6. Must be resolver-emitted, no PnL fabrication, behind a flag. |
| 31 | `MUTUAL_FUNDS.md:3-6` de-advertise MF | **ALREADY_COVERED** | C7 QW-2. |
| 32 | `MUTUAL_FUNDS.md:9-11` build ranker/page | **REJECT** | **VETO V6** (`PLAN.md:63`, C7 "Do-not-do"). |
| 33 | `OVERALL.md:3-7` honesty metrics (n/excluded/CI) | **ADOPT** | C3 G3 + C5 P0-4. |
| 34 | `OVERALL.md:9-13` `edge_ratio` re-emit or delete reader → `hyro_pick_performance_validator.py:549`, `hyrotrader/index.html:1730` | **ADOPT (low)** | C3 (new small item) — fix our imprecise audit note (N7). |
| 35 | `OVERALL.md:15-20` `INSUFFICIENT` at `forward_trades==0` → `dashboard_generator.py` forward-stat assembly | **ADOPT** | C2 §7 + C3 G3. |
| 36 | `OVERALL.md:21-26` refresh/remove dead sections → `dashboard_freshness.js`, `deploy_audit_files.py:38,59` | **ALREADY_COVERED (MERGE N8)** | C1 P0-7 + C3 G5. Verified `:38` = `strategy_ic_analysis.json`, `:59` = `regime_report.json`. |
| 37 | `OVERALL.md:27-32` outlier clamp count → `pnl_ingest_sanity.py`, `universal_pick_resolver.py:1470` | **ADOPT** | C3 G3 (new count field). |
| 38 | `OVERALL.md:33-38` Actions installs/Playwright | **ALREADY_COVERED** | C1 P0-3; add N9 root causes. |
| 39 | `OVERALL.md:39-43` hide gated/placeholder rows → `_apply_per_class_visibility_floor()` `:14311` | **ADOPT** | C6 P1-6 + C5 P0-7. Verified `:14311`. |
| 40 | `01-crypto.md:79` F-17 one-off `UPDATE … status='EXPIRED'` for AI Challenge | **REJECT (mechanics)** | **VETO V4** — quarantine/age-out only; dry-run + archive if ever applied. |
| 41 | `01-crypto.md:73` F-11 recompute `unrealized_pnl_pct`, emit `EXIT_STALE` in `live_picks.db` | **MERGE (M/High)** | C8 P1-2/P1-8 with ML schema corrections; require dry-run + backup. |
| 42 | `01-crypto.md:69` F-7 dedupe `id` + `id_conflicts.jsonl` | **ALREADY_COVERED** | C1 P0-8 / C8 P1-5. |
| 43 | `01-crypto.md:70` F-8 LOST-with-positive-PnL + SL/TP ordering | **ADOPT** | C2 §4.2 + C6 (new guard). |
| 44 | `01-crypto.md:78` F-16 PF inflation guard (`COUNT(DISTINCT pick_id)`, show raw vs dashboard) | **ADOPT** | C3 G1/G2 + C5 P1-6. |
| 45 | `01-crypto.md:83` F-21 Smart Picks n<20 gate | **ADOPT** | C4 P1-8. |
| 46 | `01-crypto.md:84` F-22 forward-validation repair-or-retire | **ADOPT** | C8 P1-8. |
| 47 | `01-crypto.md:75` F-13 case-dupe class normalization | **ADOPT** | C8 P1-1 + C6. |
| 48 | `02-equity-etf.md:36-39` F1–F4 quote provenance / summary / CI / n-gate | **ALREADY_COVERED** | C5 P0-1…P0-4. |
| 49 | `02-equity-etf.md:41` F6 quarantine stale opens (non-destructive) | **ALREADY_COVERED** | C5 P0-7. |
| 50 | `02-equity-etf.md:42` F7 population split | **ALREADY_COVERED** | C5 P0-5. |
| 51 | `02-equity-etf.md:43` F8 DB backfill / ETF feed sync | **MERGE** | C8 P1-2 with ML schema correction; write class to `metadata`, not a nonexistent column. |
| 52 | `03-forex.md:42` raise threshold / non-null price | **ADOPT (staged)** | C6 P1-2. |
| 53 | `03-forex.md:48` FX provider branch + write-back | **ALREADY_COVERED** | C6 P1-3. |
| 54 | `04-futures-commodity.md:45` F5 canonical class shadow / F6 real feed | **CONDITIONAL** | Only if retired-vs-restart picks restart; **do not ship display plumbing that implies live exposure** (our C4 P1-3 premise was already flagged wrong by PR1). |
| 55 | `04-futures-commodity.md:53` F13 unblock FUTURES | **REJECT** | **VETO V7** (`PLAN.md:64`, C4/C6). Keep blocked + shadow promotion gate. |
| 56 | `05-bond-mutual-funds.md:37` F1 vacuous PASS / F2 MF NOT_BUILT | **ALREADY_COVERED** | C7 QW-1/QW-2. |
| 57 | `05-bond-mutual-funds.md:40` F4 BOND price coverage (real marks) | **ALREADY_COVERED** | C7 QW-4. |
| 58 | `05-bond-mutual-funds.md:41` F5 BOND dedupe 15→6 | **MERGE** | C7 QW-5; use canonical economic key, not `(ac,symbol,direction,strategy)` alone. |
| 59 | `05-bond-mutual-funds.md:42` F6 sync feed→`live_picks.db`, F7 exits | **MERGE (M)** | C8 P1-2; dry-run/backup, ML schema corrections. |
| 60 | `05-bond-mutual-funds.md:45` F9 FRED re-enable, F10 coverage gate | **ALREADY_COVERED** | C7 QW-6 / QW-7. |
| 61 | `06-overall-statistical.md:78-80, 86-91` honesty/CI/INSUFFICIENT/outlier | **ADOPT** | C3 G3. |
| 62 | `06-overall-statistical.md:83-84` `edge_ratio` | **ADOPT (low)** | C3. |
| 63 | `06-overall-statistical.md:78-80` dual-cohort disclosure + guardian CI gate | **ADOPT** | C3 (new G14: run `tools/pi_data_hygiene.py`, exit 1). |
| 64 | `07-infra-ci.md:72-75` F1/F1b/F2/F3/F7 CI fixes | **ALREADY_COVERED** | C1 P0-1/P0-3/P0-4. |
| 65 | `07-infra-ci.md:76` F4 dedup/prune (archive-only) | **ALREADY_COVERED** | C1 P0-8. |
| 66 | `07-infra-ci.md:77` F5 keys/rotation | **ALREADY_COVERED** | C1 P0-9. |
| 67 | `07-infra-ci.md:78` F6 `mysql_dedup_fix` dry_run=false DELETE | **REJECT (unattended)** | **VETO V5** — manual dispatch only, after archive + reviewed preview; our veto list forbids `DELETE`. |
| 68 | `07-infra-ci.md:80-82` F8 non-fatal masking, F9 hourly freshness, F10 orphan pipes | **ADOPT (partial)** | C8 P1-2/P1-7 (visibility and freshness), not P0. |
| 69 | `07-infra-ci.md:83-86` F11 fail-loud MySQL sync, F12 guardian gate, F13 payload lag, F14 unpin crypto price | **ADOPT/MERGE** | C3 + C1 P0-5/0-7. |
| 70 | `07-infra-ci.md:94-99` F22–F27 (delta sync, telemetry, circuit breaker, orchestrator) | **MERGE (P2)** | C8 "long-term infra"; do not promote to P0. |
| 71 | `07-infra-ci.md:89` F17 add `MUTUAL_FUND` class id | **REJECT** | **VETO V6** (contradicts `PLAN.md:63`; classification-only is acceptable, class admission is not). |

---

## 4. Citation spot-check (25 refs verified; 6 drifts — 5 line + 1 semantic)

Verified by reading the current source in the `finpredict-v2` worktree (same blobs as the peer worktree).

| # | Citation (PF1) | Verified content | Result |
|---:|---|---|---|
| 1 | `alpha_engine/scanner.py:2942` | `_forex_by_sym[s["symbol"]][sig_type].append(s)` with inner dict `{"BUY":[],"SELL":[]}` (line 2937) → `KeyError: 'LONG'` | ✅ exact |
| 2 | `tools/sync_summary_picks_json.py:63-65,161` | `resolved` = 6 statuses; `wins`/`losses` over **all** PnL rows; division at `:161` | ✅ exact |
| 3 | `audit_trail/quality_gates.py:1724` | `BLOCKED_ASSET_CLASSES = {"FOREX","COMMODITY","FUTURES","BOND"}` | ✅ exact |
| 4 | `audit_trail/quality_gates.py:6739` | `def passes_active_gate(...)` | ✅ exact |
| 5 | `audit_trail/quality_gates.py:9082` | Entry block is at **9083** (`if entry_price <= 0`); 9082 is the `_float(...)` line | ⚠️ 1-line drift |
| 6 | `audit_trail/quality_gates.py:2375` | `MAX_ENTRY_PRICE = 1_000_000.0` (line 2374) | ⚠️ 1-line drift |
| 7 | `alpha_engine/prediction_market_consensus.py:589` | `merged_pick["entry_price"] = merged_pick.get("entry_price") or 0` | ✅ exact |
| 8 | `prediction_market_agents/kalshi_signal_agent.py:489` | `"entry_price": 0,` | ✅ exact |
| 9 | `copy_trader_intel/multi_asset_copytrader_scraper.py:409,452` | `def _make_pick(...)` at 409; `"entry_date": now.strftime("%Y-%m-%d")` at 452 | ✅ exact |
| 10 | `copy_trader_intel/non_crypto_consensus.py:134,150` | `_min_agreement_for_pick` (FOREX→1) at 134; `consensus_vote` at 150 | ✅ exact |
| 11 | `audit_trail/dashboard_generator.py:6824-6826` | `threshold_pass = (active_count == 0 …` | ✅ exact |
| 12 | `audit_trail/dashboard_generator.py:1179` | `def _fetch_prices_with_failover` is at **1180** | ⚠️ 1-line drift |
| 13 | `audit_trail/dashboard_generator.py:1618,1753,1830-1832` | `_enrich_live_pnl` @1618; no-quote `continue` @1753; track stats built from active list @1830-1832 | ✅ exact |
| 14 | `audit_trail/dashboard_generator.py:14311,15483,5916,7516` | `_apply_per_class_visibility_floor` @14311; `total = wins+losses` @15483; `compute_asset_class_health` @5916; `_coerce_closed_zero_pnl_from_outcome` @7516 | ✅ exact |
| 15 | `audit_trail/dashboard_generator.py:8102` | `_ac_defaults` dict starts at **8101** (8102 = `"EQUITY"` row) | ⚠️ 1-line drift |
| 16 | `audit_dashboard/template.html:8883-8905,9134-9145,9222-9227` | PnL cell; `current_price` cell with green live dot `\u25CF`; age cell | ✅ blocks exact |
| 17 | `audit_trail/universal_pick_resolver.py:931` | `def _heal_no_price_row(row)` | ✅ exact |
| 18 | `alpha_engine/commodity_price_failover.py:387,413` | `fetch_commodity_price` @387; `fetch_commodity_prices_batch` @413 | ✅ exact |
| 19 | `tools/deploy_audit_files.py:38,59` | 38 = `strategy_ic_analysis.json`; 59 = `regime_report.json` | ✅ exact |
| 20 | `audit_dashboard/ueps_section_renderer.py:909` | Inside `render_ueps_section` (def 859); unconditional 3 tab buttons | ✅ exact-ish |
| 21 | `audit_dashboard/institutional_readiness_plan.html:190` | Card F: "mutual-fund ranker on `/audit/mutual-funds.html`" | ✅ exact |
| 22 | `audit_trail/dashboard_generator.py:1599` | `…quote-short/{sym}?apikey=demo` | ✅ exact |
| 23 | `dashboard_generator.py:8136-8154,8351-8352` | Entry-timestamp key list at 8136-8150; **no date-only rejection exists** — this is a target site, not current behavior | ⚠️ semantic drift |
| 24 | `alpha_engine/scanner.py:2937-2942` (PLAN cites range) | Conflict-resolution block begins at 2932; `_forex_by_sym` at 2937 | ✅ |
| 25 | `prediction_market_consensus.py:478,489` (CRYPTO #2) | `:478` = `status = …`; `:489` = `"entry_date"`; `entry_price or None` is ~488 | ⚠️ 1–2 line drift |

**Net:** 19/25 exact, 5 minor line drifts (≤2 lines), 1 semantic drift (target site presented as
existing behavior). No fabricated citations found. This is materially better than typical peer
archives.

---

## 5. Conflicts with our per-class plans

### 5.1 Quote-status representation (blocking)
- PF1 `PLAN.md:28` / `01-crypto.md:63` (F-1): `quote_status ∈ {LIVE, UNQUOTED, STALE, LAST_CLOSE}` (+ `quote_age_hours`).
- PF1 `CRYPTO.md:23` / `EQUITY.md`: boolean `_unquoted=True` + `pnl_pct=None`.
- Our `DATA_CONTRACT.md:54`: **2-value** `{QUOTED, UNQUOTED}`.
- Our `REVIEW_SYNTHESIS.md:35`: **5-value** `{LIVE, LAST_CLOSE, STALE, UNQUOTED, PLACEHOLDER}`.

**Required merge:** one enum. Recommendation: adopt the 5-value enum from `REVIEW_SYNTHESIS.md`
(matches PF1 and the master PLAN), amend `DATA_CONTRACT.md §2.2` to the 5 values plus an optional
`quote_freshness` band, and drop the boolean `_unquoted` as a public field (keep it internal only).

### 5.2 `pnl_pct` mutation point
PF1 `01-crypto.md:63` (F-1) says "do **not** mutate `pnl_pct` in the enrich loop", while `CRYPTO.md:23`
says set `pnl_pct=None`. Our `DATA_CONTRACT.md:64` (H1) requires `pnl_pct:null` + `UNQUOTED` at
publish. **Resolve:** stamp `quote_status` in `_enrich_live_pnl`, set `pnl_pct=null` once at the
serialization boundary. Both statements are satisfiable; do not apply both in the same pass.

### 5.3 `summary_picks`
Same bug, same fix, same lines (`sync_summary_picks_json.py:63-65,161`). No conflict; canonical is
our C1 P0-2 wording (single terminal population + clamp + assert).

### 5.4 Dedup key
- PF1 BOND `05:F5`: `(asset_class, symbol, direction, strategy)`.
- PF1 `PLAN.md:42`: ID key + economic key `(symbol,strategy,direction,entry_time,entry_price)`.
- Our C1 P0-8: existing registry key `(strategy, symbol, direction, trade_date, round(entry_price,4))`.

**Required merge:** registry key is canonical (don't fork it); the PF1 economic key is an
additional cross-source annotation, not a replacement. BOND 15→6 is a symptom that must not
override the ledger key.

### 5.5 ML gate
No conflict: both reject v4's inversion; both treat inverted confidence as a **data** bug. PF1 adds
`d8c8dd25581` (leakage masking now default-ON on `origin/main`) — a governance item, not a fix.

### 5.6 FUTURES block
PF1 `04:F13` lists "unblock FUTURES" as contested, but its own `PLAN.md:64` vetoes it. Our position
(keep blocked; build a shadow promotion gate) wins. **Master plan must state "keep blocked" explicitly**;
the input files must not be read as endorsing F13.

### 5.7 BOND price backfill — internal contradiction
PF1 `BOND.md:5` recommends `current_price = entry_price`; PF1 `PLAN.md:62` vetoes exactly that.
`05-bond-mutual-funds.md:53` records the veto and `:62` resolves to "fetch a real mark". **The
quick-win file is wrong and must not be cherry-picked** (VETO V1).

### 5.8 Audit runtime number
Our `MASTER_AUDIT.md:19,65` says median **84.5 min** (5 sampled jobs). PF1/GA4 says p50 **97.2** /
p95 **111.6** (15 runs) and identifies the **56.6-min FTP step** as 54% of the job. Merge GA4 as
canonical and label 84.5 as a small-sample estimate.

### 5.9 Per-class plan conflicts (file-by-file)
| Class | PF1 quick-win | Our plan | Conflict? | Resolution |
|---|---|---|---|---|
| CRYPTO | Binance failover, entry band, Kalshi, flat-3% detector, forward-seed flag | C4 P0-1/P0-2, P1-1 | No; additive | Add as concrete implementations under C4 P1-1/P1-5 |
| EQUITY | last_quote/asof, Wilson CI | C5 P0-1/P0-2/P0-4 | No | Add Wilson helper + thin-sample badge |
| ETF | parked label, UEPS tabs | C5 P0-2/P0-3 | No | Add UEPS tab suppression |
| FOREX | purge 11, age-guard, threshold 1→2 | C6 P0-4 (quarantine), P0-6 (shadow) | **Yes** on purge and enforce-now | Quarantine, not purge; shadow→enforce |
| FUTURES | ISO timestamps, hide gated | C6 P0-1, P1-6 | No | Make gated exclusion explicit |
| COMMODITY | backfill/emit, drop on fetch fail | C4 P1-3 | Premise conflict (COMMODITY is gate-blocked; generator uses crypto proxies) | Do not ship class plumbing; only real `=F` feed |
| BOND | `current_price=entry_price`, auto-expire | C7 QW-4 real marks, QW-7 gate | **Yes** on entry-copy | VETO entry-copy; keep real-mark coverage gate |
| MUTUAL FUNDS | de-advertise (ok), build ranker (no) | C7 QW-2 | **Yes** on build | De-advertise + `NOT_BUILT` only |

### 5.10 Other corrections the master plan must adopt
1. `MASTER_AUDIT.md:207` "9 audit tables with 0 rows" → **8 empty + 2 non-empty** (`bt_backtest_runs=20`, `meta=1`).
2. `MASTER_AUDIT.md:208` v4 "PF 1.801 vs 0.371" → **stale May snapshot**; fresh CRYPTO PF 0.9196 / policy-clean 0.2628; gates **disabled** (`_fdr_gate_enforce=false`).
3. `MASTER_AUDIT.md:80` `edge_ratio` → **hyrotrader-only**; main reads `edge_surfaces.verified_lab`.
4. `MASTER_AUDIT.md:19,65` runtime → **p50 97.2 / p95 111.6**, FTP 56.6 min.
5. `MASTER_AUDIT.md` §1 failure root causes → add GH001 100 MB file, Playwright/ubuntu26.04, `Invalid frequency: ME`.
6. `MASTER_AUDIT.md` §10 → add v3 **14 tests / 5 iterations / horizon 0/6 & 0/26** and the `d8c8dd25581` production change.

---

## 6. Veto list (destructive / policy-reversing) — do NOT cherry-pick as-is

| ID | Item (exact path:line) | Why veto | Safe replacement |
|---|---|---|---|
| **V1** | `quick-wins/by-asset-class/BOND.md:5` — `current_price = entry_price` | Manufactures the exact frozen-price artifact; contradicts PF1 `PLAN.md:62` and our `DATA_CONTRACT.md` H1. It also stamps `price_source="yfinance_close"` although BOND marks come from FRED/yfinance — a false provenance label. | C7 QW-4: fetch a real mark; coverage gate at <80% → `DATA_STALE` (C7 QW-7). |
| **V2** | `quick-wins/by-asset-class/FOREX.md:5` — "Do once as a data purge" of 11 phantoms | Hard delete of closed rows; provenance of the 11 rows is itself UNVERIFIED (`folder-review/v3.md:39`). Destroys auditability. | C6 P0-4: validity filter / `VOID` quarantine in `_is_valid_resolved_pick()`, rows retained. |
| **V3** | `quick-wins/by-asset-class/CRYPTO.md:33` — "Relabel/**purge** the flat-3% cohort" | "Purge" is unspecified; if it means row deletion it breaks the audit trail for 286 trades. | Detector + `_placeholder_stats=True` + exclude from WR/PF; keep rows. |
| **V4** | `master-plan/inputs/01-crypto.md:79` F-17 — one-off `UPDATE … status='EXPIRED'` on `ai_challenge` | Destructive SQL UPDATE on live rows; **not** in PF1's own PLAN veto list, so it can leak through. | View-level quarantine + documented age-out; if ever applied: dry-run, backup, archive. |
| **V5** | `master-plan/inputs/07-infra-ci.md:78` F6 — run `mysql_dedup_fix` with `dry_run=false` (DELETE 22,947 ghost rows) | Irreversible DELETE; our veto list forbids it; a UNIQUE index add can fail against existing duplicates. | Archive JSONL + quarantine; manual dispatch only after reviewed preview. |
| **V6** | `master-plan/inputs/07-infra-ci.md:89` F17 and `quick-wins/by-asset-class/MUTUAL_FUNDS.md:9-11` — add `MUTUAL_FUND` class / build ranker | Re-opens vacuous PASS for a class with no emitter/NAV source; contradicts `PLAN.md:63`. | De-advertise + `NOT_BUILT` (C7 QW-2); classification-only if fund tickers must stop misclassifying. |
| **V7** | `master-plan/inputs/04-futures-commodity.md:53` F13 — remove FUTURES from `BLOCKED_ASSET_CLASSES` | Policy reversal without a real feed or promotion gate; contradicts `PLAN.md:64`. | Keep blocked; shadow promotion gate (BOND P1-2 pattern, max-hold + 60-day accrual). |
| **V8** | `master-plan/inputs/05-bond-mutual-funds.md:54-58` F6 / `07:67-70` F11 / `01:67-70` F-11 — DB upserts/UPDATEs into `live_picks.db` | Not inherently wrong, but the ML peer's SQL targets **nonexistent columns/tables** (`asset_class` is in `metadata` JSON; tables are `live_picks`/`pick_history`). Applying as written would no-op or corrupt. | Merge only after schema-corrected statements + dry-run + backup; `INSERT OR REPLACE` is destructive. |
| **V9** | `quick-wins/by-asset-class/BOND.md:9-15` — auto-expire status rewrite | Lower severity, but it converts OPEN→closed and can move closed-ledger stats without a resolver trail. | Resolver-emitted `STALE_NO_QUOTE` with `resolution_kind`, behind a flag; no PnL fabrication. |
| **V10** | `quick-wins/by-asset-class/FOREX.md:23-31` — threshold 1→2 **enforce now** | Sequencing risk: changes emission volume before shadow counts exist; our P0-6 requires shadow-first. | Stage shadow → block-new-only. |

No `git push --force`, `git reset --hard`, `rm -rf`, branch deletion, or status-rewrite commands
exist in the folder itself; the folder correctly quotes and vetoes v4/ML destructive SQL. V1–V10 are
the residual items the folder did **not** fully self-veto.

---

## 7. UNVERIFIED (not re-derived in this review)

- ML PnL magnitude errors (WUSDT +0.9615 vs ~+0.0048; HBARUSDT −0.269 vs ~−0.0027) — not recomputed from `live_picks.db`.
- v4 `evidence_db_health.json` (21 active / 3h write / 5-of-5 checks) and fresh `money_ready` PF 0.9196 / 0.2628 — quoted, not re-fetched.
- v3 horizon-harness results (n≥60 0/6, n≥30 0/26) and 14-test count — not re-run.
- `wrong_guesses_log.json` 100.22 MB, Playwright/ubuntu26.04, `Invalid frequency: ME` — not reproduced.
- `CT=F` DSR falsification and NG=F/CL=F `MISPRICED_ENTRY` false positive — not re-derived.
- JS parse-dead **start date** 2026-10-04 — the parent commit's `node --check` failure is verified; the date is not.
- Provenance/owner of the 11 FOREX phantoms and of the date-only `ES=F` seed.
- BOND 1,293 (`picks_now_live_pnl`) layer — not inspected.
- `funds.html` purpose/role.
- `deepAI` / `inspect-wt` / `hilarious-seer` Windows-host artifacts — not on this host, not on origin (consistent with our archive).
- `d8c8dd25581` behavioral impact on live ML scoring — the default flip is verified; its downstream effect is not measured.
- Post-merge visual rendering of `UNQUOTED`/`STALE`/`LAST_CLOSE`/`PLACEHOLDER` badges.

---

## 8. What the REVIEW AGENT must merge before the master plan (top 5)

1. **Adopt the three stale-snapshot corrections into `MASTER_AUDIT.md`** — v4's CRYPTO PF "1.801 vs 0.371" is a 173-day-old artifact (fresh 0.9196 / policy-clean 0.2628); v4's "0 active/26-day-stale" is a repo-copy artifact; ML's "9 empty audit tables" is 8 empty + 2 non-empty, and ML's SQL targets a nonexistent top-level `asset_class` column. Also record FDR/single-source gates as **disabled**, not failing.
2. **Escalate `d8c8dd25581` for an explicit keep/revert decision** — v3 flipped `ml_gatekeeper._drop_leakage_enabled()` to ON by default and the commit is already an ancestor of `origin/main` (17:49Z, after our audit clock). This is an unreviewed production behavior change made during a read-only audit.
3. **Fold PF1's 12 genuinely new fixes into canonical plans** — Kalshi `entry_price:0→None` + >7d gate (`kalshi_signal_agent.py:489`), flat-3% detector keyed on fallback TP (`dashboard_generator.py:7516,8101`), forward-seed `_unquoted` flag, UEPS empty-tab suppression (`ueps_section_renderer.py:909`), `stock_forex_prices` consumer age-guard (`outcome_resolver.py:413`), FOREX threshold 1→2 (shadow), visibility-floor gating (`:14311`), `edge_ratio` fix, `INSUFFICIENT` at `forward_trades==0`, outlier-clamp count, Wilson CI, entry band 0.5×–2×.
4. **Veto/repair PF1's 4 veto-grade items before any cherry-pick** — `BOND.md:5` entry-copy, `FOREX.md:5` data purge, `CRYPTO.md:33` relabel/purge, `01-crypto.md:79` F-17 UPDATE; then reconcile PF1's `PLAN.md` vs its own `quick-wins/*` (PLAN already vetoes the first two — the quick-wins files were not updated).
5. **Resolve the two contract conflicts and refresh the runtime numbers** — pick one `quote_status` enum (recommend 5-value: `LIVE/LAST_CLOSE/STALE/UNQUOTED/PLACEHOLDER`, amending `DATA_CONTRACT.md §2.2`) and one dedup key (existing registry key is canonical); replace `MASTER_AUDIT.md`'s 84.5-min median with GA4 p50 97.2 / p95 111.6 + the 56.6-min FTP step, and mark the JS parse-guard action as **already merged** (`5ad40e83c08`; `ba1378cbfa9` is a redundant duplicate branch).
