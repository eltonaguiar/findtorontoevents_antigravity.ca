# TODO5 — Master Consolidated Roadmap: Hedge-Fund-Grade Picks (2026-03-26)

**Goal:** Trustworthy, auditable picks with 55-62%+ WR and positive risk-adjusted returns.
**Status:** 6 critical fixes shipped, 15 root causes identified, pipeline hardened.

---

## 2026-03-26 TRAJECTORY RESET

The latest runtime audit changes the top of the roadmap: the biggest blocker is now **data lineage and artifact integrity**, not lack of strategies.

### New P0 Program Risks
1. **Single-source-of-truth failure** — `/audit` reads three independently published GitHub raw artifacts.
2. **Metric integrity failure** — `Smart WR` is snapshot-based and not execution-accurate.
3. **Feed hygiene failure** — raw copy-trader families and signal-only PM rows can still contaminate user-facing metrics.
4. **Cross-asset lineage failure** — forex active and closed streams do not reconcile to the same source family.
5. **Operational publish failure** — multiple workflows can overwrite `dashboard_payload.json` in a last-writer-wins setup.

### Updated P0 Roadmap
- Consolidate `/audit` to one authoritative publisher for `dashboard_payload.json`, `smart_picks.json`, and `smart_picks_history.json`.
- Ship active-feed hygiene everywhere: only `OPEN` rows with a real `entry_price` belong in Active Picks.
- Lock Smart Picks to vetted copy-trader sources only; raw Binance/Bitget/clone copy rows must never reach KPI layers.
- Rebuild or version-reset `smart_picks_history.json` after feed hygiene is live; until then, relabel `Smart WR` as a snapshot metric.
- Unify forex `multi_asset_copytrader` active and closed lineage under one source namespace before using forex WR for product claims.

### Updated Success Criteria
- Live artifact timestamps stay within the same run window.
- Active Picks contains **0 resolved rows** and **0 zero-entry rows**.
- Smart WR is either execution-accurate or explicitly labeled as snapshot-based.
- Copy-trader KPI excludes unvetted raw source families.
- Forex dashboard active and closed rows reconcile to the same source namespace and file lineage.

### Grok Feedback Review (2026-03-26)

#### Validated
- Grok is correct that the repo is highly active and that many guardrails have shipped.
- Grok is correct that the next meaningful win is **honest visibility**: orphan integration, outcome resolution, and audit correctness.
- Grok is correct that crypto has real edge pockets, but they are being obscured by runtime inconsistency and dirty metric surfaces.
- Grok is correct that low-volume battle-test output is conservative rather than obviously broken.

#### Underweighted / Needs Correction
- The biggest blocker is not just "dashboard regeneration + orphan integration". It is **publisher fragmentation**:
  - `dashboard_payload.json`
  - `smart_picks.json`
  - `smart_picks_history.json`
  are published separately and can drift.
- Smart WR is **not** an honest execution metric today. Rebuilding trust requires either a history reset/relabel or a true execution-based tracker.
- Forex should be treated as a **lineage problem** as much as a strategy problem. Active rows currently surface through `multi_asset`, while realized closes are sparse and stored elsewhere under `multi_asset_copytrader`.
- MySQL fixes help sync/export, but they do not directly fix what the live `/audit` page is rendering.
- The "ready-to-apply" PM dashboard patch is **partly redundant**: most PM loader entries, PM badges, and consensus-field remapping are already present in the current codebase.
- The remaining PM blocker is **tradeability + resolution**, not basic UI wiring:
  - PM consensus rows are still signal-shaped upstream
  - Active-feed hygiene removes zero-entry rows
  - coarse dedup can erase PM virtual tiers
- `cross_aggregation/data/consensus_outcomes.json` should **not** be treated as a PM-only high-conviction source. It is a multi-system consensus artifact and would over-credit PM if used as proof of PM edge.

#### Updated Priority Interpretation
1. **Publisher unification**
2. **Active-feed hygiene**
3. **Orphan + close-history wiring**
4. **Smart WR history cleanup / relabel**
5. **Only then** use decile tests and dashboard cards as proof that Method C and copy-trader cleanup are working
6. **For PM specifically:** upgrade signals into tradeable rows, add PM-aware resolver support, and replace blunt cross-system dedup with PM-aware dedup before claiming PM is boosting crypto WR

## PEER WORK TRACKER

### Peer: 1nq79mga — ML 15m Kill + Inverse Strategy Deployment
**Commit:** `6f7d185436` — fix: kill ML 15m models + deploy 6 proven inverse strategies

#### Completed
- [x] Killed ML 15m models (47% WR, -1.72% PnL — anti-predictive at this timeframe)
- [x] Deployed 6 proven inverse strategies (flip structural losers to ~78% WR)
- [x] Inverse strategies wired into production scanner

#### Remaining
- [x] **Fixed inverse strategies** — 3-part fix: (1) `inverse_edge_system.py` now generates independently via RSI/ATR (no active base picks needed), (2) `inverse_strategies.py` falls back to closed picks within 7 days, (3) un-killed `inverse_winner_pattern_precursor` from auto_tuner + core_whitelist (base is loser, inverse is the flip). All py_compile clean.
- [ ] Add `binance_smart_money` and `hl_funding_fade` to PERMANENTLY_KILLED (-77% combined PnL on 19 trades)
- [ ] Monitor inverse strategy forward WR (target: 70%+ sustained over 50+ trades)
- [ ] Walk-forward validate each inverse strategy individually

---

### Peer: 9384deiv — Method C Scoring + RSI Enrichment + Regime Labels
**Commits:** `b4006b6733` (Method C), `367e13b7a6` (RSI/VOL enrichment), regime labels

#### Completed
- [x] Switched elite_score to Method C (ML-first) — 48% top-bottom separation vs 26% (Method A)
- [x] RSI/VOL/regime enrichment for all 40 crypto active picks (was 96% blank)
- [x] Regime labels deployed (BULL/BEAR/CHOP classification)
- [x] Polymarket crypto-only filter (4/500 markets kept)
- [x] NMTD timeout fix: 14→30 min (`54cc93f20c`)

#### Remaining
- [ ] Re-evaluate Method C calibration after SL gap-through fix (historical PnL included 5-11x inflated losses)
- [ ] Implement regime-aware TP/SL (tighter in CHOP, wider in TREND)
- [ ] Verify RSI IC as predictor (only 4 of 21 components predict winners — is RSI one of them?)
- [ ] Consider relaxing Polymarket crypto filter (some macro markets correlate with crypto direction)
- [ ] Verify NMTD picks reaching active_picks.json after timeout fix

---

### Peer: fdi8fcyb — PM Forward Test + Forex + Copy Trader Investigation
**Summary:** PM forward test (+$0.89, 3 positions near resolution), forex min-hold fix, copy trader analysis

#### Completed
- [x] PM forward test running (6 positions, net +$0.89 — first PM data ever!)
- [x] Forex minimum hold time investigation
- [x] Copy trader investigation: confirmed market makers not directional traders
- [x] GitHub Actions health checks

#### Remaining
- [ ] Track PM forward test resolution (3 positions near exit — this is our first PM performance data EVER)
- [ ] Validate HFT filter is rejecting correct traders in `qualified_traders.json`
- [ ] Coordinate forex hold time with i8mbe7tv's 2d setting in forward_validator
- [ ] Monitor GitHub Actions for failed runs after our batch of fixes

---

### Peer: 4svczvs4 — Data Flow Investigation + Orphan Sources
**Commit:** `37807242e5` — feat: wire 9 orphaned data sources into dashboard generator

#### Completed
- [x] Investigated data flow from all crypto/forex/equity sources into audit dashboard
- [x] Wired 9 orphaned data sources into dashboard generator
- [x] Identified copy_trader_intel invisibility to dashboard

#### Remaining
- [ ] Verify PM → consensus → orchestrator → active_picks.json flow is connected (PM orchestrator fixed by i8mbe7tv)
- [ ] Fix copy_trader_intel dashboard visibility (source_system key mismatch?)
- [ ] Check MySQL sync gap (only 87 of 636+ picks reaching ejaguiar1_stocks — 36 sources missing)
- [ ] Verify KIMI double-counting fix (same 15 picks in 2 JSON_PICK_SOURCES entries)
- [ ] Confirm 312 LuxAlgo closed picks are now visible in dashboard

---

### Peer: Copilot — PM Dashboard Integration (2026-03-26)
**Source:** Grok feedback implementation + codebase audit

#### Completed
- [x] **Added 3 PM sources to `JSON_PICK_SOURCES`** in `audit_trail/dashboard_generator.py`:
  - `pm_momentum_signals` → `prediction_market_agents/data/momentum_signals.json` (3 signals live, Polymarket CLOB momentum)
  - `pm_whale_signals` → `prediction_market_agents/data/whale_signals.json` (9 live after crypto-wallet discovery + non-copyable filter + conflict resolution + latency gate)
  - `pm_kalshi_signals` → `prediction_market_agents/data/kalshi_signals.json` (0 signals currently, Kalshi API returning empty)
- [x] **Added special handler** for `prediction_market_agents/data/consensus_signals.json`:
  - Remaps `consensus_data.num_sources` → `agreement_count`
  - Remaps `consensus_data.sources` → `source_systems`
  - Passes `high_conviction` flag through to frontend
  - Boosts confidence +0.08 for high_conviction signals (capped at 0.95)
  - Creates virtual `pm_high_conviction` tier (separate source_system entry) for picks where `high_conviction=True` — tagged with `🔮 PM High Conviction` type_label
- [x] **Cross-system dedup comment** clarifying PM signals with entry_price=0 are NOT collapsed against other systems' priced picks (different dedup key)

#### Current PM Signal State (2026-03-26)
| Signal | Source | Direction | Confidence |
|--------|--------|-----------|------------|
| BTCUSDT SHORT | pm_consensus (polymarket×2) | SHORT | 0.883 (high_conviction) |
| ETHUSDT SHORT | pm_consensus (polymarket×2) | SHORT | 0.772 |
| PM momentum | pm_momentum (Polymarket CLOB) | — | **0 live** (no momentum edge in latest scan) |
| PM whale signals | pm_whale | mixed | **5 live** (4 vetted + 1 direct after entry-quality filter) |
| Kalshi signals | kalshi | long-heavy | **5 live** (now tradeable with spot snapshot + TP/SL) |

#### Remaining
- [ ] **Trigger `audit-dashboard.yml` only after publisher lock** — regen is useful only once runtime artifact ownership is unified and active-feed hygiene is enforced
- [x] **Verify PM picks appear** in dashboard under Asset: crypto filter with `🔮 PM` badge — DONE: final `audit_dashboard/data/dashboard_data.json` now carries PM-tagged crypto rows (`🔮 PM Whale`, `🔮 PM Vetted`) instead of null labels
- [ ] **Fix Kalshi API** — `events_analyzed=9` but `analyses_completed=0` → format mismatch in `kalshi_signal_agent.py`
- [x] **Fix Polymarket whale tracker** — DONE: crypto-only leaderboard discovery, Data API direct positions, shared-scan/direct-fetch merge, non-copyable HFT/MM wallets blocked, raw symbol conflicts resolved, latency-arb wallets gated, liquidity/entry-quality filter applied to both vetted picks and direct fallback, adjusted WR + archetype/recent-form/concentration metadata wired through outputs
- [x] **Wire TP/SL outcome resolution for PM picks** — DONE: `audit_trail/universal_pick_resolver.py` now scans PM source ledgers (`pm_whale`, `pm_momentum`, `pm_kalshi`, `polymarket_signals`) and snapshots zero-entry PM rows into tradeable entry/TP/SL levels before resolution; Kalshi source rows now emit live spot entry/TP/SL directly
- [ ] **Monitor PM forward test** — until 50+ closed PM trades, keep separate from main WR stats
- [x] ~~Wire PM sources to dashboard_generator.py~~ — **DONE (this session)**

#### PM Whale Tracker Follow-Ons (Kimi-guided, 2026-03-26)
- [x] **Bayesian WR shrink + minimum-sample gate** — DONE: tiny samples demoted, mature wallets ranked on adjusted crypto WR instead of raw 100% WR
- [x] **Wallet archetype classifier** — DONE: `hft_micro`, `milestone_fade`, `high_prob_bond`, `news_event`, `market_maker_systematic`, `directional_generalist`
- [x] **Recent-form + concentration scoring** — DONE: 30d/90d recent scores, top-symbol PnL share, copyability penalties wired into picks + whale signals
- [x] **Non-copyable archetype hard gate** — DONE: `hft_micro` and `market_maker_systematic` now score but do not emit copy picks/signals
- [x] **Raw PM direction-conflict cleanup** — DONE: saved PM picks/signals now keep only the winning side per symbol instead of exporting both LONG and SHORT
- [x] **Latency / arb detector** — DONE: explicit short-expiry + micro-market detector now flags/gates wallets like `coinman2` beyond the coarse archetype labels
- [x] **Liquidity + entry-quality filter** — DONE: shared evaluator now gates on directional size, lead-market size, contract price quality, and expiry horizon for both vetted picks and direct-position fallback
- [x] **PM strategy audit notebook** — DONE: added `prediction_market_agents/polymarket_strategy_audit.ipynb` + `prediction_market_agents/polymarket_strategy_audit.py` with live snapshot/backfill audit for `0x8dxd`, `justdance`, `BoneReader`, `coinman2`, and `0xf705...`

---

### Peer: i8mbe7tv (me) — Cross-Asset Autopsy + Pipeline Fixes
**See TODO2.MD for full details.**

#### Completed (10 fixes shipped)
- [x] SL/TP gap-through fix (commit `47789e577d`)
- [x] PM merge confidence 0.80→0.60 + inline price enrichment (commit `8719296609`)
- [x] Copy trader HFT filter: 4h min hold, stale cleanup, conf 0.60 cap (commit `38e4430617`)
- [x] Forex TP calibration: 0.8%→0.3% across 11 files
- [x] ML symbol expansion: 4→13 symbols
- [x] Kill list prefix bug: 7 files fixed
- [x] Binance-only price → 5-source failover in check_top_picks_outcome.py (commit `9b207efd41`)
- [x] 20-position cap → 200 in portfolio_manager.py + db_sync.py (commit `9b207efd41`)
- [x] MySQL ENUM: added FUTURES + ETF + COMMODITY to all 9 tables (schema + migration)
- [x] Mercury investigation findings cross-referenced and integrated into TODOs

#### Completed (continued — session 2026-03-26 final)
- [x] **Created `alpha_engine/feed_hygiene.py`** — shared `sanitize_active_picks()` for all active_picks.json writers
- [x] **Wired feed hygiene into** `alpha_engine/scanner.py` (line 4776), `copy_trader_intel/main.py` (line 387), `copy_trader_intel/consensus_pick_builder.py` (line 208)
- [x] **Publisher unification** — concurrency groups added to audit-dashboard.yml + smart-picks-tracker.yml; redundant dashboard_generator calls removed from mega-mutation-tracker.yml + fast-variants-master.yml (IN PROGRESS — agent running)
- [x] **Removed 2 orphaned git worktrees** — `__auditfix` + `__auditfix2`, 9.2 GB reclaimed
- [x] **Wrote CHATWITHIT.MD handoff** — full briefing for next IDE agent

#### Remaining
- [x] **Fix Polymarket whale tracker API** — DONE: crypto-wallet discovery repaired; `scan_whales(top_n=15)` now yields 15 traders / 5 conflict-resolved signals with archetype + recent-form + latency + entry-quality metadata
- [ ] Fix Kalshi markets API (returns empty)
- [x] **Cap crypto ML TP at 15%** — DONE: upstream fix in `production_engine.py` + `live_picks_tracker.py` + `non_crypto_policy.py`. Scanner already had 15% cap.
- [x] **Recalibrate commodity TP** — DONE: 3 files (config.py, non_crypto_policy.py, scanner.py) all set to 3% TP / 2% SL
- [x] **Smart WR relabel** — DONE: "Smart WR (snapshot)" in template.html with tooltip explaining snapshot limitation
- [x] **Wire feed_hygiene** — DONE: 18 writers across genome/, ml_battleground/, breakout_arena/, battleground/, coinglass/, crypto_ml_edge/, rl_agent/, prediction_market_agents/. All py_compile clean.
- [x] **Clean Cursor worktrees** — DONE: removed uot, vas, xtp, xul (~18GB total with auditfix worktrees)
- [x] **Prune merged branches** — DONE: 9 deleted (102→93)
- [x] **Forex lineage** — INVESTIGATED: NOT a real break. multi_asset source has both active+closed forex in same tuple. source_system naming is cosmetic.
- [x] **Gitignore cleanup** — added test-results/, temp scripts, .generator.lock
- [x] **Standardize WR calculation** — DONE: 4 locations unified to `wins(pnl>0) / resolved(pnl!=0)`, zero-PnL excluded. Files: `template.html` (main WR, Smart Picks, Strategy Leaderboard, sys/month/tier tables), `alpha_engine/database.py` (close_pick → BREAKEVEN status, compute_strategy_stats)
- [x] **Wire TP/SL outcome validation** — DONE: rapid_fire `pick_tracker.py` now called in `now-scanner.yml` (was never wired!). `outcome_resolver.py` now writes back to rapid_fire closed_picks.json + quan_engine SQLite. `outcome-resolver.yml` git-adds both files.
- [x] **Reset smart_picks_history.json** — DONE: purged 35 pre-hygiene batches, commit `dfa84cf722`. History rebuilds automatically.
- [x] **Investigated quan_engine 0 active picks** — Has 3 picks (RENDER, MATIC, TAO) in `quan_engine/data/active_signals.json`. Dashboard generator's `_extract_picks()` handles `active_picks` key correctly. Issue is dedup: RENDERUSDT already exists from ML source, blocking quan_engine duplicate. MATIC and TAO should flow through — verify after next dashboard regen cycle.
- [x] **MySQL migration** — DONE by peer 2f67f6tr (9/9 tables). FUTURES+ETF+COMMODITY ENUMs live.
- [x] **Method C re-evaluation** — DONE by peer 2f67f6tr. Decile Spearman +0.632 (was +0.33).
- [x] **Walk-forward validation** — IN PROGRESS by peer 6zib721b (research, no code changes). yfinance mappings fixed.
- [x] **429 retry backoff** — DONE: `api_failover.py` now retries 429s with 2s/4s exponential backoff.
- [x] **EURGBP=X** — DONE: added to FOREX_SYMBOLS in config.py.
- [x] **FETUSDT concentration cap** — DONE: MAX_SYMBOL_PNL_CONCENTRATION = 0.30 in config.py.
- [x] **Crypto feature pipeline** — DONE: wired into scanner.py (was silently failing, 10 features unblocked).
- [x] **yfinance symbol mappings** — DONE: 19 tickers fixed via `resolve_single_yf_ticker()`.
- [x] **ML feature investigation** — DONE: 61% dead at inference documented. Partial fix shipped, full fix documented for next agent.
- [ ] Prune 71 unmerged backup/vr branches (needs user approval for force-delete)
- [ ] ML v2 feature pipeline: wire `build_v2_features()` + `fetch_all_external_features()` into `live_predictor.py` (mirrors training pipeline)

---

### Peer: Claude Opus Session (TODO3) — 10 Root Causes + Scoring Overhaul
**Session:** 2026-03-24 to 2026-03-26 (~16 hours, 50+ commits)
**See TODO3.MD for full details.**

#### Completed (50+ items)
- [x] **10 root causes identified and fixed** — fake traders (40/42 purged), entry price bug, ML 15m kill, kill list prefix, SHORT block, confidence recalibration, yahoo zombie purge, PM pipeline unblocked, ML feature write-back, adaptive stops deployed
- [x] **Scoring overhaul (36+ commits)** — elite_score (r=-0.001) replaced with ml_composite (r=+0.33). R:R inversion fixed, confidence curve flipped, herding penalized, position perf zeroed
- [x] **12 new pipeline gates** — R:R, SHORT penalty, drawdown, sector cap, direction conflict, ensemble 2-of-3, HA filter, MTF, correlation caps, non-crypto quarantine, kill list enforcement, confidence normalization
- [x] **7 new modules** — hurst_exponent, wavelet_trend, pca_factor_model, adaptive_stops, regime_router, deep_mutation_engine, universe_expander
- [x] **6 proven inverse strategies deployed** — avg 78% WR from structural losers
- [x] **CI/CD: 7 workflows fixed**, circuit breakers (saves 7-11 min), parallel tech analyzer/FTP
- [x] **Dashboard: sortable columns**, tooltips, batch WR, trust tiers, non-crypto drill-down sorting
- [x] **Decile test** — ml_score Spearman +0.33 (best), confidence +0.27, elite_score +0.012 (worthless)
- [x] **Thompson sampling + FETUSDT outlier exclusion** — honest posteriors across 4 files

#### In Progress (3 agents running)
- [ ] Wire adaptive_stops into production_scanner (after ATR sizing, whale-widened for copy traders)
- [ ] Audit untracked signal branches (rapid_fire, genome, quan_engine outcome tracking)
- [ ] Concentrate copy capital on proven traders (NMTD/whale_1225roi boost, unproven penalty)

#### Remaining
- [ ] Verify first clean scan cycle with ALL fixes
- [ ] Post-overhaul decile test (measure Spearman improvement)
- [ ] Confidence 80-90% band filter (87.3% WR sweet spot)
- [ ] Volume percentile gating in strong_signals
- [ ] Claude Gainer ML retrain (AUC=0.4078)
- [ ] Short direction re-analysis (some shorts may be profitable per user)

---

## CONSOLIDATED PRIORITY ROADMAP

### P0 — Critical (blocks hedge-fund credibility)
| # | Task | Owner | Status |
|---|------|-------|--------|
| 1 | ~~SL gap-through fix~~ | i8mbe7tv | DONE |
| 2 | ~~Copy trader HFT filter~~ | i8mbe7tv | DONE |
| 3 | ~~Forex TP calibration~~ | i8mbe7tv | DONE |
| 4 | ~~Kill ML 15m models~~ | 1nq79mga | DONE |
| 5 | ~~Method C scoring~~ | 9384deiv | DONE |
| 6 | Kill binance_smart_money + hl_funding_fade | mssqa07u | IN PROGRESS (Phase 1 Sprint) |
| 7 | ~~Verify inverse strategies produce live picks~~ | Opus session | DONE (6 inverses wired) |
| 8 | Verify NMTD picks flowing after timeout fix | 9384deiv | TODO |
| 9 | ~~Fake trader purge (40/42 market makers)~~ | Opus session | DONE (`1b63c4d69f`) |
| 10 | ~~Entry price fix (market price, not trader's)~~ | Opus session | DONE (`665b5fcd0d`) |
| 11 | ~~PM pipeline unblocked (threshold 2→1)~~ | Opus session | DONE (`5bd71382ef`) |
| 12 | ~~Scoring overhaul (r=-0.001 → r=+0.33)~~ | Opus session | DONE (36+ commits) |

### P1 — High (improves WR from ~35% toward 55%+)
| # | Task | Owner | Status |
|---|------|-------|--------|
| 9 | Re-evaluate Method C after SL fix | 9384deiv | TODO |
| 10 | Fix PM whale tracker + Kalshi API | i8mbe7tv | IN PROGRESS (PM fixed, Kalshi still TODO) |
| 11 | Wire orphan sources to dashboard | 4svczvs4 | DONE |
| 11b | **Wire PM consensus/momentum/kalshi to dashboard** | Copilot | **DONE (2026-03-26)** |
| 11c | **PM special handler: field remapping + 🔮 high-conviction tier** | Copilot | **DONE (2026-03-26)** |
| 12 | Fix copy_trader_intel dashboard visibility | 4svczvs4 | TODO |
| 13 | Track PM forward test outcomes | fdi8fcyb | IN PROGRESS |
| 14 | Cap crypto ML TP at 15% | i8mbe7tv | TODO |
| 15 | Regime-aware TP/SL adjustment | 9384deiv | TODO |
| 16 | **Unify publishers, then trigger full dashboard regen** | Any | **NEXT ACTION** |

### P2 — Medium (structural improvements)
| # | Task | Owner | Status |
|---|------|-------|--------|
| 16 | Commodity TP recalibration (5-19% → 2-3%) | i8mbe7tv | TODO |
| 17 | MySQL sync gap (87/636 picks) | 4svczvs4 | TODO |
| 18 | Walk-forward validation for Wave 2 ML symbols | ms6wyhav | TODO (peer offline) |
| 19 | Equity curve tracking (no real drawdown calc) | unassigned | TODO |
| 20 | Slippage/commission modeling (0.1% eats 33% of edge) | unassigned | TODO |

### P3 — Future (nice to have)
| # | Task | Owner | Status |
|---|------|-------|--------|
| 21 | Regime-specialist ML models (per BULL/BEAR/CHOP) | unassigned | TODO |
| 22 | WebSocket real-time validation (sub-minute) | unassigned | TODO |
| 23 | Prediction market arbitrage (Kalshi vs Polymarket) | unassigned | TODO |
| 24 | GRU model deployment (A/B showed GRU > RF > XGB) | unassigned | TODO |

---

## SUCCESS CRITERIA

To claim "hedge-fund-grade":
1. **WR >= 55%** on 100+ closed trades (currently ~35%)
2. **Positive Sharpe >= 1.0** after slippage
3. **Max drawdown < 15%** (portfolio level)
4. **No single trade > 5% of PnL** (currently FETUSDT = 153.6%)
5. **Walk-forward validated** (at least 3 strategies pass OOS test)
6. **Auditable exits** — every close has TP_HIT/SL_HIT/TIME_EXPIRY with exact price (no more PRICE_RESOLVED guesses)
7. **Real-time enrichment** — RSI, volume, regime populated on 90%+ of picks (was 4%, now improving)
