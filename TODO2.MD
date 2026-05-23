# TODO2 — Cross-Asset Performance Autopsy & Critical Pipeline Fixes (2026-03-26)

**Author:** Claude Opus 4.6 (peer i8mbe7tv)
**Period:** Mar 26, 2026 (04:00-10:00 AM EST)
**Goal:** Investigate why performance is low across all asset classes despite copying "the best" traders/systems, and fix critical pipeline bugs to reach hedge-fund-grade picks.

---

## RUNTIME REALITY CHECK (2026-03-26, Supersedes Part Of The Original Autopsy)

The original autopsy was directionally correct, but the live `/audit` runtime path exposed additional issues that now outrank pure model/strategy work.

### Corrections To Keep In Mind
- Prediction markets are **not literally "0 ever" anymore**. There are realized `polymarket_prediction` closes in `alpha_engine/data/closed_picks.json`, but the sample is weak and negative enough that PM should still be treated as experimental.
- The live dashboard was showing prediction-market rows in Active Picks that were **signals, not trades** (`entry_price = 0`, no live execution context).
- Forex is more structurally broken than a simple TP calibration problem:
  - actives surface through the `multi_asset` mirror
  - realized closes mostly live in a different file/source family
  - current realized forex copy-trader validation is sparse and poor
- MySQL is **not** the runtime source for `/audit`. The page is driven by GitHub raw artifacts, so DB fixes alone will not correct the live dashboard.

### What This Means For Development Trajectory
- Cross-asset edge cannot be judged honestly from dashboard cards until **active/closed lineage is unified per source family**.
- For crypto, vetting must happen at the **source-family level**, not at the trader-profile-win-rate level.
- For forex, the current "copytrader" naming is misleading. Most of the live forex path behaves more like a **multi-asset model portfolio feed** than true external trader replication.

### New P0 Additions
- Unify `/audit` artifact ownership so dashboard payload, Smart Picks, and Smart WR history come from one coherent run.
- Purge or version-reset polluted `smart_picks_history.json` after feed hygiene is deployed.
- Separate **signal-only** prediction-market rows from **tradeable** active picks.
- Unify forex active and closed lineage under one consistent source namespace before using forex WR for product claims.

### Grok Cross-Check (2026-03-26)
- **Validated:** Grok is right that the repo is shipping fixes quickly, that non-crypto bleeding has been reduced, that copy-trader cleanup happened, and that the next leverage point is honest outcome visibility.
- **Validated:** The `0% WR / no PnL` problem is still largely a resolution/lineage issue, not just bad trading. Missing outcome wiring keeps hundreds of rows from showing honest W/L.
- **Validated:** The battle-test output is now conservative and low-volume, which matches the current quality-first posture.
- **Correction:** A simple dashboard regeneration is **not sufficient**. The page is reading multiple independently published GitHub raw artifacts, so regeneration without publisher unification can still leave the live page inconsistent.
- **Correction:** Forex should not be described as merely "low volume but improving." The more important problem is that active and closed forex copy rows do not reconcile to the same source family.
- **Correction:** Method C verification should happen only after active-feed hygiene and Smart WR/history hygiene, otherwise old polluted batches can obscure current gains.

### Additional PM Integration Review (2026-03-26)
- **Already implemented in part:** `audit_trail/dashboard_generator.py` already contains PM loader entries for `momentum_signals.json`, `whale_signals.json`, `kalshi_signals.json`, plus a special handler for `consensus_signals.json` that remaps `num_sources -> agreement_count` and duplicates `high_conviction` rows into a virtual PM tier.
- **Main blocker is not source wiring anymore:** Active-feed hygiene now removes rows without a real `entry_price`, so zero-entry PM signals will not survive into Active Picks unless they are enriched into tradeable rows **before** dashboard generation.
- **Critical correction:** `cross_aggregation/data/consensus_outcomes.json` is a broad cross-system consensus file, not a prediction-market-only file. Treating it as a PM-only `5+` source would contaminate PM metrics with unrelated systems.
- **Critical correction:** the coarse post-load dedup key `(symbol, direction, entry_price)` is too blunt. It can collapse distinct PM tiers and other cross-system agreement rows, which defeats the goal of making PM visibility more truthful.
- **Implementation implication:** the next PM work should be:
  1. real entry/TP/SL enrichment upstream,
  2. PM-aware outcome resolution,
  3. PM-specific dedup that preserves `pm_high_conviction`,
  4. only then dashboard promotion.

## COMPLETED ITEMS

### Investigation Phase (4 Parallel Subagents)

#### Copy Trader Pipeline — 31% WR, -91% Cumulative PnL
- [x] **Root cause 1: HFT contamination** — 95% of "qualified" traders in `qualified_traders.json` are HFT/market-makers (median hold <6 min). Their edge is un-copyable at our 30-min scan interval. 11 of 42 traders have 100% WR with thousands of trades = classic market-maker signature.
- [x] **Root cause 2: Entry drift always 0%** — `copy_trader_intel/main.py` line 604 sets `original_trader_entry = entry_price`, making drift tracking useless. Alpha is gone by the time we detect positions.
- [x] **Root cause 3: All 28 active picks stale** — 2 Bitget picks 40h old, 26 others 6.8 days old. Stale filter broken because `original_trader_entry = 0.0`.
- [x] **Root cause 4: SL gap-through bug** — `force_close_breached.py` exited at `live_price` not SL level. LITUSDT: -27% actual on 2.5% SL = 11x amplification. **FIXED** (commit `47789e577d`).
- [x] **Root cause 5: TP/SL widening backfires** — "Mercury sprint" whale widening (8%/4%) makes TP unreachable for HFT traders who hold 2-6 min. All wins used original 3% TP.
- [x] **Root cause 6: Fake ML scores** — `ml_score = confidence` in copy_trader_intel. Previously fixed in 5 locations.
- [x] **Root cause 7: Every platform loses** — `binance_smart_money` (-37.59%) + `hl_funding_fade` (-39.44%) = -77% PnL on just 19 trades.

#### Prediction Market Pipeline — Previously Dead, Still Experimental
- [x] **At investigation time, production flow was effectively dead** — later runtime audit found sparse realized `polymarket_prediction` closes, but the sample is still weak/negative and not fit for product claims.
- [x] **Whale tracker dead** — `polymarket_scraper.scan_polymarket_traders()` returns `([], [])`. API changed or crypto-qualification filter too strict.
- [x] **Kalshi dead** — Finds 9 events but `fetch_event_markets()` returns empty for all. Silent failure (no logging for "0 markets found").
- [x] **Consensus blocked** — Required 2+ sources (lowered to 1 by peer). Only 2/4 sources work, and they conflict on BTC (SHORT vs LONG).
- [x] **Entry=0/TP=0/SL=0 by design** — Orchestrator intentionally sets 0 prices expecting downstream enrichment that never happens. **FIXED** with inline price enrichment.

#### Forex — 0 TP Hits in 26 Trades
- [x] **TP targets unreachable** — 0.8-1.7% TP on pairs that move 0.1-0.5%/day. "Wins" capture only 3-40% of TP target.
- [x] **cta_tsmom_blend toxic** — Academic monthly strategy forced into daily execution = 22.2% WR. Now PERMANENTLY_KILLED.
- [x] **Math kills the category** — Wins avg +0.19% but losses avg -0.30% (SL hits at -0.5%). Need >62% WR to break even; actual WR is 42.3%.

#### Equity & Commodity
- [x] **yahoo_analyst_consensus** — Used 12-month analyst target prices as swing TP (e.g., PG had 16.4% TP). Now PERMANENTLY_KILLED.
- [x] **Commodity TP absurd** — Silver 19.5%, Gold 10.8%, Nat Gas 13.8% TP targets on assets that move 1-3%/day.
- [x] **PRICE_RESOLVED asymmetry** — Wins avg +0.52%, losses avg -3.05%. At 50% WR, expected PnL = -1.27% per trade.

#### Incubator Backtests
- [x] **Grid Trading** — Broken position accounting (18K+ open positions, -853K% returns). Needs position management rewrite. **Abandoned.**
- [x] **Bollinger MeanRev** — Total wipeout (-87% to -100%) across all 9 combos. **Abandoned.**
- [x] **RSI Momentum** — Only viable incubator strategy (SOL 1d: +85%, Sharpe 0.47).

#### Kill List Prefix Bug Audit
- [x] **7 files fixed** — `winner_pattern_strategy.py`, `relative_strength_strategy.py`, `volatile_alt_scanner.py`, `kimi_inverse_scanner.py`, `fc_crypto_pro.py`, `_fix_active_picks.py`, `_audit_data_quality.py`.
- [x] **5 files already correct** — `production_scanner.py` (2 locations), `forward_validator.py`, `isolated_signal_integrator.py`, `picks_router.py`, `dashboard_generator.py`.

#### ML Symbol Coverage Expansion (4 → 13)
- [x] **9 new symbols added to ml_strategy_reviver.py** — TRX (100% WR/3 trades), OP (100%/3), LINK (75%/4), AVAX (67%/3), SUI (67%/3), ARB (67%/3), APT (67%/3), LTC (67%/3), ZK (67%/3).
- [x] **CoinGecko ID mappings added** for price failover.

#### ML Crypto Predictor Cache Fix
- [x] **data_fetcher.py** — Replaced `os.path.getmtime()` cache with content-based check (last candle timestamp).
- [x] **live_predictor.py** — Broke circular dependency in candle gate.
- [x] **498 stale parquet files deleted** + `.gitkeep` preserved.
- [x] **`.gitignore` updated** — `ml_crypto_predictor/enhanced_models/data/klines/`.

---

### Fixes Applied & Committed

| # | Fix | File(s) | Commit | Impact |
|---|-----|---------|--------|--------|
| 1 | SL/TP gap-through | `force_close_breached.py` | `47789e577d` | Prevents 5-11x loss amplification |
| 2 | PM merge confidence 0.80→0.60 | `orchestrator.py` | `8719296609` | Unblocks PM signal flow |
| 3 | PM inline price enrichment | `orchestrator.py` | `8719296609` | Fixes entry=0/TP=0/SL=0 |
| 4 | Copy trader HFT filter | `copy_trader_intel/main.py` | `38e4430617` | 4h min hold, stale cleanup, conf cap 0.60 |
| 5 | Forex TP calibration (11 files) | `forex_strategies.py` + 10 more | pushed | TP 0.8%→0.3%, SL 0.6%→0.2% |
| 6 | Updates page entry | `updates/index.html` | `3642e51423` | Documented all findings |
| 7 | Binance-only price → 5-source failover | `check_top_picks_outcome.py` | `9b207efd41` | Forex/exotic crypto now resolvable |
| 8 | 20-position cap → 200 | `portfolio_manager.py` + `db_sync.py` | `9b207efd41` | Full trade history for WR |
| 9 | MySQL ENUM + COMMODITY | `mysql_schema.sql` + migration | pushed | FUTURES/ETF/COMMODITY no longer lost |
| 10 | TODO files created | `TODO2.MD` + `TODO5.MD` | pushed | Master roadmap consolidated |
| 11 | WR formula standardized | `portfolio_manager.py` + `strategy_leaderboard.py` | `55968ad17d` | 4 formulas → 1 (zero-PnL excluded) |
| 12 | Forex caps in production_scanner | `production_scanner.py` | `d2f6358839` | TP 1.0%→0.3%, SL 0.5%→0.2% |
| 13 | check_top_picks_outcome → 45min | `alpha-engine-live.yml` | `d2f6358839` | Was 4h, now runs every 45min |
| 14 | Full MySQL sync in alpha-engine | `alpha-engine-live.yml` | `d2f6358839` | sync_all_picks_to_mysql.py now automated |

---

## REMAINING ITEMS

### P0 — Stop the Bleeding
- [x] SL gap-through bug — **FIXED**
- [x] Copy trader HFT filter — **FIXED**
- [x] Forex TP calibration — **FIXED**
- [ ] Validate forex TP fix generates actual TP hits (needs forward test data, ~2 days)
- [ ] Validate copy trader HFT filter rejects the right traders (next workflow run)
- [ ] Monitor copy trader WR improvement after filter (target: 31% → 50%+)

### P1 — Revive Dead Systems
- [x] PM orchestrator merge confidence lowered — **FIXED**
- [x] PM inline price enrichment — **FIXED**
- [ ] Fix Polymarket whale tracker (scraper returns 0 wallets — API format changed?)
- [ ] Fix Kalshi markets API (returns empty for all events — format mismatch?)
- [ ] Debug PM consensus end-to-end signal flow
- [ ] Verify NMTD copy trader picks reaching active_picks.json

### P2 — Structural Improvements
- [ ] Fix PRICE_RESOLVED exit asymmetry — implement trailing TP or min win threshold
- [ ] Recalibrate commodity TP to 2-3% (currently 5-19%)
- [ ] Cap crypto ML TP at 15% (FETUSDT has 47% TP — too aggressive)
- [ ] Recalibrate IC scoring after SL fix (historical PnL data included inflated losses)
- [ ] Validate walk-forward for Wave 2 ML symbols

### P3 — Forward Validation
- [ ] Track forex picks with new 0.3% TP — first TP hits expected within 2 days
- [ ] Track PM picks — verify they reach active_picks.json (1 PM pick seen already!)
- [ ] Monitor copy trader WR after HFT exclusion
- [ ] Validate ML Wave 2 symbol performance in forward test
- [ ] Confirm inverse strategies generating active picks (not stuck in mutation engine)

---

## KEY METRICS TO TRACK

| Metric | Before | Target | Current |
|--------|--------|--------|---------|
| Copy Trader WR | 31% | 55%+ | Pending (filter just deployed) |
| Forex TP Hit Rate | 0/26 (0%) | 30%+ | Pending (0.3% TP just deployed) |
| PM Picks Produced | 0 ever | 1+ per day | 1 seen in active_picks! |
| ML Symbol Coverage | 4 | 13 | 13 (done) |
| SL Amplification | 5-11x | 1.0x | 1.0x (fixed) |
| Overall Portfolio WR | ~35% | 55%+ | Pending full cycle |

---

## PEER COORDINATION

| Peer | Task | Status |
|------|------|--------|
| ms6wyhav | IC scoring, inverse mutations, walk-forward | Dropped off (was active earlier) |
| 1nq79mga | Kill ML 15m, deploy 6 inverse strategies | Active, asked for TODO |
| 9384deiv | Method C scoring, RSI enrichment, regime labels | Active, asked for TODO |
| fdi8fcyb | PM forward test, forex hold, copy trader investigation | Active, asked for TODO |
| 4svczvs4 | Data flow investigation, orphan sources | Active, asked for TODO |
| prxmx7sg | Unknown (new peer, no summary) | Active, asked for summary |
