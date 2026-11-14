# A — Consolidated Common Themes: Bugs + Deeper Investigation

**Scope:** cross-peer consolidation of the 2026-11-14 financial-prediction audit (9 peers: finpredict v1–v4, flaxen-hair, hilarious-seer, scratch-hippodraco, childlike-airport/ML, quant-audit, deepAI/inspect-wt).
**Status:** READ-ONLY synthesis. Every bug below was flagged by ≥1 peer; items flagged by ≥2 peers are marked `[2+ peers]` / `[3+ peers]`.
**Source folders:** `final_2026_11_14/{quant-audit-2026-11-14,finpredict-v2,finpredict-v3,finpredict,flaxen-hair}/`, `final_v2/*`, and local worktrees `{finpredict-v2,finpredict-v3,flaxen-hair,hilarious-seer,scratch-hippodraco,childlike-airport}`.

---

## 1. BUGS (concrete, deduplicated, grouped by category)

### (a) Data-integrity

**A1. Frozen / unquoted prices masquerade as 0% PnL.** `[3+ peers]`
- `fetch_prices.php` has returned HTTP 404 since 2026-04-29; the yfinance replacement also fails → dead price refresh.
- 19/20 curated active picks have `pnl_pct == 0.0`; 7/20 have `current_price` bit-identical to `entry_price`; only NEARUSDT is actually marked to market. XRPUSDT shows 0.00% against a live +0.52% Binance move.
- Root: `audit_trail/dashboard_generator.py:1752-1755` leaves the pick untouched on price-fetch failure (current==entry clone) instead of emitting `price_source=null` + `pnl=null`.
- FUTURES rows still carry April-2026 closes (ZN=F 111.015625 = Yahoo 2026-04-02 exactly; CL=F −21.0%, GC=F −17.3% vs live, all `pnl_pct=0.0`).

**A2. PnL-unit mix (ratio vs percent) — off by up to 100×.** `[3+ peers — highest-value fix]`
- `audit_trail/dashboard_generator.py:8065-8072`: `if abs(pnl_val) < 0.10: pnl_val *= 100` misclassifies ambiguous values, mixing fraction and percent within one ledger.
- flaxen-hair recomputed `multi_asset_closed.json`: 47 rows ratio / 32 percent / 14 inconsistent; `vix_reversal::SI=F::2026-03-11` same symbol+strategy differs 100× (−0.04244 vs −3.6402). `institutional_closed.json` is all-percent, contradicting the sibling file.
- Writer-side: `forward_validator.py:1375-1384` writes fraction; `universal_pick_resolver.py:286-306` `_compute_pnl()` writes percent; `at_signal_outcomes.pnl_pct` mixes 17,632 percent / 6,306 fraction; `trading_picks` mixes 3,543.
- Invalidates all cross-class PnL aggregates.

**A3. Zero / null entry rows.** `[2+ peers]`
- `sync_all_picks_to_mysql.py` inserts `bt_backtest_trades` rows with null `entry_price`; BTCUSDT active rows show `entry` min 0.2608 (a non-price).
- `prediction_market_consensus.py` coerces `None → 0.0` entry (Kalshi entry:0 → None fix adopted by v2).

**A4. EXPIRED → WON mislabeling (survivorship inflation).** `[3+ peers]`
- `tools/relabel_crypto_expired.py` + `tools/resolver_hygiene_check.py`; `PNL_WIN_THRESHOLD=0.00001` (0.1 bp) turned spread noise into "WIN" labels for ~1,700 non-crypto picks.
- Dashboard CRYPTO "Smart Picks" WR 78.93% / PF 9.69 vs DB raw 39.38% / PF 0.371 — the dashboard cohort is 91.7% one source (`claude_gainer_st`) with only 3 closed rows and 63.9% of 97 EXPIRED rows mislabeled WON.

**A5. Ghost / zombie rows.** `[3+ peers]`
- `db_health.ghost_rows.total_ghost_rows = 22,947` while the dashboard banner claims "Ghost rows: 0".
- 2,838 "zombies" (age >30 d AND `pnl_pct==0`) — all EXPIRED, never resolved, never pruned; 3,378 EXPIRED rows with `closed_at` empty and P/L 0.
- `trading_picks`: 90,567 OPEN + 21 ACTIVE; 86,064 OPEN >7d; FOREX alone 43,056 OPEN (oldest 2026-04-03).
- `pick_history`: 136 rows all `event=REGISTERED`, no CLOSED/EXIT/TP/SL — picks can never age out.

**A6. Dedup / duplicate IDs.** `[2+ peers]`
- 248 duplicate groups / 297 extra rows / 56 cross-ledger conflicts; 414 duplicate (symbol,dir,day,strategy) groups = 997 rows, max 9 (pseudo-replication).
- Non-unique pick `id`: `vix_reversal::SI=F::2026-03-11` appears 4× with different exit prices/reasons; date-only IDs collide. 4,148 active rows / 3,851 unique IDs.

**A7. Single-source concentration.** `[3+ peers]`
- All 166 strategy×class×direction cells are single-source (100% from one `source_system`); only 1 of 166 clears n≥100. `luxalgo_confluence` CRYPCO 94% one source; `alpha_engine` CRYPCO 98.5%.
- All 24 "statistically significant winners" have `single_source_pct = 1.00` and `top_source = file:mysql:at_pick_outcomes`, flagged `is_single_source_artifact = True`.

**A8. `summary_picks.json` WR > 100%.** `[2+ peers]`
- `tools/sync_summary_picks_json.py:63-65` counts `wins`/`losses` over *all* rows while `resolved` counts only terminal statuses → INDEX 1141.2%, FUTURES 363.9%, COMMODITY 240.2%, ETF 232.9%, EQUITY 162.4%, FOREX 147.0%, BOND 127.8%. Arithmetically impossible published payload.

**A9. Vacuous PASS (empty class → green).** `[2+ peers]`
- `audit_trail/dashboard_generator.py:6824-6826`: a class with `active_count == 0` short-circuits to `thresholdPass = true`, so BOND renders green PASS with 0 picks while `money_ready_verdict` says `INSUFFICIENT_DATA`. Also affects ETF/FUTURES.

**A10. Class-taxonomy contamination.** `[2+ peers]`
- Four different class inventories in one payload (7 vs 9 vs 11 vs 8 classes); `INDEX`/`MANAGED_FUTURES`/`SPORTS` are phantom classes (0 rows elsewhere).
- COMMODITY is 44/44 `=F` futures; 49/277 FOREX rows aren't spot FX (44 currency ETFs + 5 `EURUSDT` crypto); EQUITY contains ETFs (SPY/QQQ/XLE/XLK); BOND class is a mislabeled ETF book (PFXF/PFFA/LQD/VTEB…).
- `alpha_engine/config.py:1127-1132` labels any 6-letter alpha string FOREX; emitter `category` overrides symbol evidence (`asset_class.py:236-237`).

---

### (b) Resolver

**B1. TIME_EXIT limbo.** `[2+ peers]`
- 4,220 picks stuck in `TIME_EXIT` limbo; only 301/4,820 resolved = 6.2%. `at_signal_outcomes` intrabar truth 254d stale, n_resolved_today=0.
- `MAX_HOLD_HOURS_BY_CLASS` exists (`universal_pick_resolver.py:32,39`) but never drains.

**B2. UNKNOWN phantoms.** `[2+ peers]`
- 11 frozen FOREX "phantom" rows with no provenance; `at_signal_outcomes` UNKNOWN status rows never resolved; 6 picks in `live_picks.db` with no `asset_class`; 108/273 active picks UNK in JSON feeds.
- Two "never-run" workflows are resolver-critical: `Resolver Step 5-6 — at_raw_picks Backfill` and `Resolver Step 7 — active_picks_sync APPLY`.

**B3. TP/SL geometry invalid.** `[2+ peers]`
- `BTCUSDT super_signals…strong_consensus` LONG entry 78,336.01 with **SL 79,491.18 > entry** (invalid); `ETHUSDT super_signals…super_consensus` LONG entry 2,047.29, SL 2,072.80 > entry, yet labelled LOST/SL_HIT.
- Status/PNL contradiction: QQQ LONG +0.335% marked LOST/SL_HIT; CL=F SHORT +2.049% marked LOST/TP_HIT; TLT +0.131% LOST/SL_HIT.

**B4. exit_price fallback / rounding fabricates PnL.** `[2+ peers]`
- `audit_trail/dashboard_generator.py:1453-1464` hardcodes XAU $3050 / XAG $33.50, silently fabricating PnL for unpriced rows.
- `audit_trail/fetch_stock_prices.py:23` rounds all prices to 2dp — a ~40-pip error on EURUSD.
- `audit_sync.py:595` accepts only WON/LOST/EXPIRED, silently dropping TP_HIT/SL_HIT.
- Clamp anarchy: ≥5 different clamps (ingest `pnl_ingest_sanity.py:12-14` [−99,+500]; resolver ±100 `:1107,1472`; frontend >100 vs >500); COMMODITY hit `|pnl|=999,999.9999`.

---

### (c) ML

**C1. Target leakage (REAL).** `[3+ peers]`
- `ml_gatekeeper/gatekeeper.py:170-186` — leakage features at indices 5/6/19/30 (`forward_wr`, `strat_fwd_wr`, `eb_forward_wr`, `age_hours`).
- `claude_gainer_ml/train_model.py:685-711` — look-ahead in training.
- Commit `d8c8dd25581` (now on `origin/main`) flips `_drop_leakage_enabled()` ON by default — fix is live but was made **unreviewed during the audit**; needs coordinator sign-off.

**B2 (ML) inverted confidence is a data bug, not model bug.** `[2+ peers]`
- `data/live_picks.db`: 8 picks have `unrealized_pnl_pct` sign-flipped vs `pnl_pct` (NEARUSDT −0.129339 vs +0.128512); WUSDT/HBARUSDT `pnl_pct` off by ~100–200× (magnitude, not direction).
- `sync_all_picks_to_mysql.py` does a blind `pnl *= 100` corruption.

**C3. Horizon harness: 0/6 and 0/26.** `[2+ peers]`
- v3 `ML_VALIDATION`: **0/6 horizon groups pass (n≥60), 0/26 (n≥30)**; **0 backtest↔forward overlap** (0 rows have both bt_trades>0 and fwd_trades>0). Strengthens the negative verdict.
- `ml_score == confidence` on every OPEN pick — score copied, not an independent model output.

---

### (d) Frontend

**D1. `dashboard_enhancements.js` parse-broken since 2026-10-04.** `[2+ peers]`
- Malformed nested ternary (double `:`) committed 2026-10-04 → the entire enhancement IIFE fails to parse → every hourly deploy pushed dead JS to all 3 sites. Part of the "empty fields" was a frontend parse failure, not just empty backend.
- Fix (`fix/audit-js-syntax-and-deploy-guard`, `ba1378cbfa9`, content on main via `5ad40e83c08`) adds a pre-FTP `node --check` guard.

**D2. Dead Edge/Track/FWD columns.** `[2+ peers]`
- `_build_strategy_symbol_track_stats` called with the *active* list filtered to closed statuses (always `[]`), not the closed ledger: `dashboard_generator.py:1830-1832` vs call site `:14551`. Explains the dead "Track" column.
- `edge_ratio` missing/empty on the live ledger; Edge/Track/FWD-WR/FWD-N empty on 18–20 of 20 active picks.
- `strategy_tribunal_latest.json` hard 404 → panel always errors.

**D3. Frontend recomputes PnL with inconsistent caps.** `[2+ peers]`
- `template.html` recomputes PnL in ≥4 places (`:4325-4329,4459-4467,4727-4731,4821-4826`) with different caps than the server, so two panels disagree on the same pick.

---

### (e) GitHub Actions

**E1. Python 3.14 masquerade.** `[2+ peers]`
- **197 workflows** set `update-environment: false`, so `actions/setup-python` never activates the pinned 3.11; `pandas==2.1.4` then source-builds against system Python 3.14 (`/usr/include/python3.14`) and fails. Root cause of the "Install dependencies" failure cluster.

**E2. `scanner.py` KeyError `'LONG'`.** `[2+ peers]`
- `alpha_engine/scanner.py:2942` appends to a dict with only `BUY`/`SELL` keys → `KeyError: 'LONG'` in `_forex_by_sym[s["symbol"]][sig_type]`. Crashes **hourly** (93 failed runs/24h); this is the main ALPHA pick generator crash-looping.

**E3. FTP deploy 56.6 min.** `[2+ peers]`
- `audit-dashboard.yml` p50 runtime **97.2 min** (p95 111.6) vs 60-min cron; driver is a **56.6-min serial FTP deploy step (54% of job)** — the "30–35 min" cron comment is ~3× wrong.

**E4. Cron saturation.** `[2+ peers]`
- **196 crons at `:00`**; 166/310 scheduled workflows lack `concurrency`. Queue saturation p50: Signal 91.4 / Market 118.5 / Mirror 174 / PEAD 221.2 min; PEAD 60/60 push-retry exhaustion, Mirror 60/60 FTP timeout.

**E5. 0-job cancels.** `[2+ peers]`
- audit-dashboard: 21/22 cancels ran **0 jobs** = 35% of last 60 runs; 61/168 (36%) of 7d runs cancelled. Hourly cron + ~97-min job → GitHub keeps only the newest queued run per concurrency group.

**E6. Playwright vs ubuntu26.04.** `[2+ peers]`
- Playwright 1.58.2 vs `ubuntu26.04-x64` — `Sports endpoint smoke + Playwright` fails at the "Install Playwright (chromium only)" step (24/24 in 24h).

**E7. 100MB JSON.** `[2+ peers]`
- `wrong_guesses_log.json` = **100.22 MB** → GH001 (file exceeds GitHub's 100MB limit).

**E8. pandas `ME` frequency.** `[2+ peers]`
- `CI Tests`: `ValueError: Invalid frequency: ME` / `KeyError: 'ME'` in `tests/test_combined_book_sleeves.py` (pandas monthly-end alias). Both Python 3.11 and 3.12 shards red.

**E9. Never-run / stale workflows.** `[2+ peers]`
- 20 active workflows never ran (incl. resolver Steps 5-6 and 7); 19 with last run >90d; 4 trading-critical disabled (Forex Agent, Forex Smart Picks, AI Tournament Pipeline, Real-Time Battle Test). 30 workflows whose most-recent run failed.

---

## 2. ITEMS NEEDING DEEPER INVESTIGATION (multi-peer UNVERIFIED / unresolved)

1. **The 11 FOREX phantom rows — provenance UNVERIFIED.** v3 flagged 11 frozen FOREX "phantoms"; no peer established where they were emitted or whether they are real fills. A hard `DELETE` is vetoed; resolution must be a validity filter / VOID quarantine with rows retained, after provenance is traced.

2. **Date-only `ES=F` seed (and date-only `entry_time`).** The single FUTURES active pick (`multi_asset_futures_connors_rsi2::ES=F`) carries date-only `entry_time`/`signal_time` (`"2026-11-14"`), on a non-trading Saturday priced at Friday's close. Same defect wider: FOREX `entry_time` is date-only in **105/277** rows (not the earlier "12"). Fix location `dashboard_generator.py:8136-8154, 8351-8352` (reject date-only at ingest) — but the full blast radius is unresolved.

3. **PnL-unit bug root cause — which writer wrote fraction vs percent?** The generator heal at `dashboard_generator.py:8065-8072` is confirmed (3-peer corroborated), but the *upstream* writer is not pinned down: `forward_validator.py:1375-1384` (fraction) vs `universal_pick_resolver.py:286-306` `_compute_pnl()` (percent) vs legacy rows with no `pnl_source`. Need an explicit `pnl_source` column (`intrabar|daily|close_approx|legacy_unknown`) and a backfill that only recomputes where a fraction-guard matches — never a bare `|v|≤1 → ×100` normalizer.

4. **Do trend / carry / VWAP edges survive a bear-inclusive window?** The 40-trial edge search (OOS 2024-07→2026-11, B&H −23.2% / −68.5% MDD) found 0/40 pass the null; funding carry's honest number is ~3.8% annual **below T-bills**; peer VWAP MR "Sharpe 3.76" was FALSIFIED to ~1.18 (t=0.91). Remaining question: are there any candidate families that still show edge when the window *includes* a full bear leg, or is all apparent edge drawdown-avoidance? Unresolved.

5. **Benchmark-relative alpha for every claim.** Most claims are vs buy-and-hold, which is not risk-matched. `benchmark_closed_ledger.py:66-76` maps FOREX→SPY (meaningless; should be DXY `DX-Y.NYB`); the paired bootstrap needs to be direction-aware for SHORT ledgers (`:357,123-159`). The SCORECARD itself flags "risk-matched benchmark gate, not just buy-and-hold" as the missing gate. Unresolved — no claim yet carries a matched benchmark.

6. **Mutual-fund ranker is an untracked prototype.** `alpha_engine/mutual_fund_ranker.py` + `mutual_fund_metadata.csv` exist only as untracked `??` files in the checkout, **absent from `origin/main`**, with a `mutut_fund_rankings.json` typo; output existence is disputed (v2 first said "never produced", then corrected: 39KB `mutut_fund_rankings.json` + NAV cache *does* exist untracked). Monthly NAV has no intraday mark. Decide: `NOT_BUILT`/de-advertise vs promote — unresolved.

7. **Three divergent data stores disagree.** SQLite (`data/live_picks.db` 128/129 picks 172d stale; `data/audit_trail.db` 9 tables empty), MySQL (`at_pick_outcomes` 24,172 rows; `trading_picks`), and JSON (`dashboard_data.json`, `pf_registry.json`, `recent_closed_array.json`) report incompatible counts, ages, and PnL (dashboard PF 1.80 vs raw-DB 0.371; 10 displayed active vs 4,361 tracked open = ~436×). No single source of truth is established. Unresolved.

---

## Cross-cutting note

All nine peers converge on the same verdict: **NOT money-ready; the data pipeline is broken; the binding constraints are single-source concentration, PnL-unit mixing, and zombie/EXPIRED ledger bloat.** Highest-value first fixes (peer consensus): PnL-unit contract + NULL-tombstone zombie drain, followed by enforcing the already-computed FDR/single-source gates (`_fdr_gate_enforce` is currently `false`).
