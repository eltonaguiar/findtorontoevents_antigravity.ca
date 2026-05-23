# TODO1: Cross-Asset Performance Autopsy & Fix Sprint

**Session:** March 26, 2026 (04:00 AM EST)
**Goal:** Investigate why performance is low across all asset classes despite copying "the best" traders/systems, and fix critical pipeline bugs.

---

## TRAJECTORY REVIEW UPDATE (2026-03-26, Post-Runtime Audit)

This document is still directionally useful, but the latest runtime investigation changed the priority order.

### What The Runtime Audit Corrected
- `/audit` is **not** primarily powered by `mysql.50webs.com / ejaguiar1_stocks`. The live page reads GitHub raw JSON artifacts directly.
- The site is mixing **three different runtime artifacts** on different cadences:
  - `audit_trail/data/dashboard_payload.json`
  - `alpha_engine/data/smart_picks.json`
  - `alpha_engine/data/smart_picks_history.json`
- The `Smart WR` card is **not an execution-accurate trade metric**. It is a 24-hour snapshot-based history metric derived from `smart_picks_history.json`.
- Crypto underperformance is no longer best explained by "bad scoring alone." The bigger issue is **polluted raw copy-trader inputs + stale artifact ownership + metric mismatch**.
- Forex validation is structurally split: active rows come from the `multi_asset` mirror, while realized closes land elsewhere under a different source label.

### Verified Evidence From This Session
- Live `dashboard_payload.json` at `2026-03-26T11:13:21Z` contained **215 active rows**, but only **153 were actually OPEN**; the rest were `SL_HIT` / `TP_HIT`, plus 4 prediction-market rows with `entry_price = 0`.
- Live `smart_picks_history.json` reported **54.37% Smart WR on 263 picks**, but those historical batches still include older raw copy-trader and prediction-market rows.
- Realized close data contradicts the "copy winners" story:
  - `copy_trader_binance`: **37.5% WR**, negative total PnL
  - `copy_trader_bitget`: **0% WR**, negative total PnL
  - `polymarket_prediction`: **33.3% WR**, slightly negative total PnL
  - vetted `copy_hl_*`: materially better than the raw copy families

### Direction Change
- Treat **data integrity and artifact ownership** as `P0`.
- Do **not** trust Smart WR or Active Picks unrealized P/L as primary KPIs until the publisher split is fixed.
- Pause broad strategy expansion if the dashboard still mixes stale, resolved, or signal-only rows into user-facing metrics.

## COMPLETED

### 1. Investigation Phase (4 Parallel Subagents)

#### 1a. Copy Trader Pipeline — 31% WR, -91% PnL
- **7 root causes identified:**
  1. 95% of "qualified" traders are HFT/market-makers (hold <6 min) — edge un-copyable at 30-min scan
  2. Entry drift tracking broken (`original_trader_entry = entry_price` always 0%)
  3. All 28 active picks are 2-7 days stale
  4. **SL gap-through bug** — exits at live_price, not SL price (LITUSDT: -27% on 2.5% SL = 11x)
  5. TP/SL widening (8%/4%) makes TP unreachable for HFT traders
  6. Fake ML scores (ml_score = confidence)
  7. Every platform loses — binance_smart_money + hl_funding_fade = -77% PnL on 19 trades

#### 1b. Prediction Market Pipeline — Completely Dead
- 0 picks have EVER reached production
- Whale tracker: Polymarket scraper returns 0 wallets
- Kalshi: finds 9 events but markets API returns empty for all
- Consensus required 2+ sources but only 2/4 work, and they conflict
- entry=0/TP=0/SL=0 by design — downstream enricher never sees PM picks

#### 1c. Forex — 0 TP Hits in 26 Trades
- TP targets (0.8-1.7%) unreachable for forex volatility (0.1-0.5%/day)
- "Wins" capture only 3-40% of TP target
- cta_tsmom_blend: academic monthly strategy forced into daily execution = 22% WR

#### 1d. Equity & Commodity
- yahoo_analyst_consensus used 12-month analyst targets as swing TP (now PERMANENTLY_KILLED)
- Commodity TP 5-19% on assets that move 1-3%/day
- PRICE_RESOLVED exit creates asymmetric wins (+0.2%) vs losses (-3.0%)

#### 1e. Incubator Backtests
- Grid Trading: Broken position accounting (18K+ open positions), abandoned
- Bollinger MeanRev: Total wipeout (-87% to -100%), abandoned
- RSI Momentum: Only viable incubator strategy (SOL 1d: +85%, Sharpe 0.47)

#### 1f. Kill List Prefix Bug Audit
- 7 files fixed with `::` prefix mismatch bug
- 5 files were already correct

#### 1g. ML Symbol Coverage Expansion
- 9 new symbols added to ml_strategy_reviver.py (TRX, OP, LINK, AVAX, SUI, ARB, APT, LTC, ZK)
- Coverage: 4 → 13 symbols, WR range 67-100%

#### 1h. ML Crypto Predictor Cache Fix
- data_fetcher.py: Replaced mtime-based cache with content-based (parquet last candle timestamp)
- live_predictor.py: Broke circular dependency in candle gate
- .gitignore: Added klines/ directory
- Deleted 498 stale parquet files + stale last_scan_state.json

---

### 2. Fixes Applied & Committed

| Fix | File | Commit | Impact |
|-----|------|--------|--------|
| SL/TP gap-through | `force_close_breached.py` | `47789e577d` | Prevents 5-11x loss amplification |
| PM merge confidence 0.80→0.60 | `orchestrator.py` | `8719296609` | Unblocks PM signal flow |
| PM inline price enrichment | `orchestrator.py` | `8719296609` | Fixes entry=0/TP=0/SL=0 |
| Updates page entry | `updates/index.html` | `3642e51423` | Documented all findings |
| Copy trader HFT filter | `copy_trader_intel/main.py` | `38e4430617` | Filters HFT <4h hold, stale >24h, conf cap 0.60 |
| Forex TP calibration (11 files) | `forex_strategies.py` + 10 more | pushed | TP 0.8%→0.3%, SL 0.6%→0.2%, hold 5d→2d |

---

### 3. Peer Coordination
- 9 peers active in repo
- Shared findings with 5zajmzss (deep investigation overlap)
- mssqa07u executing Phase 1 hedge fund sprint (killing binance_smart_money)
- 314emojt had PM forward test concern — answered (PM was never live)

---

## COMPLETED (Background Agents — Both Done)

### 4a. Copy Trader HFT Filter Fix (DONE — commit `38e4430617`)
- HFT lookup from qualified_traders.json — cross-references trader profiles
- 4-hour minimum hold — traders with median hold <4h get `qualified: false`
- Stale pick filter — picks >24h old marked STALE and removed
- Confidence hard cap 0.60

### 4b. Forex TP Calibration (DONE — 11 files fixed, pushed)
- TP cap: 0.8-1.0% → 0.3% (achievable in 1-2 days)
- SL cap: 0.5-0.6% → 0.2% (1.5:1 R:R)
- Forex min hold: 5d → 2d
- Files: forex_strategies, proven_forex_strategies, cta_strategy_replicator, adaptive_tp_sl, non_crypto_policy, config, pick_accelerator, volume_microstructure_strategies, community_strategies, forward_validator, multi_asset_test_portfolios

---

## REMAINING (Priority Order)

### P0 — Stop the Bleeding
- [x] SL gap-through bug — FIXED
- [x] Copy trader HFT filter + stale cleanup + confidence cap — FIXED
- [x] Forex TP calibration 0.8%→0.3% across 11 files — FIXED
- [ ] Validate forex TP fix generates TP hits (needs forward test data)

### P1 — Revive Dead Systems
- [x] PM orchestrator merge confidence lowered — FIXED
- [x] PM inline price enrichment — FIXED
- [ ] Fix Polymarket whale tracker (scraper returns 0 wallets — API changed?)
- [ ] Fix Kalshi markets API (returns empty for all events — format mismatch?)
- [ ] Debug PM consensus to verify signals now flow end-to-end

### P2 — Structural Improvements
- [ ] Fix PRICE_RESOLVED exit asymmetry — implement trailing TP or min win threshold
- [ ] Fix commodity TP targets (5-19% → 2-3%)
- [ ] Validate walk-forward results for inverse strategies
- [ ] Grid Trading: rewrite position management if worth salvaging

---

## KIMI AGENT INVESTIGATION FINDINGS (CRITICAL)

The Kimi Agent swarm conducted a 6-pronged investigation into the Crypto/Forex Win Rate discrepancies, uncovering the following root causes:

### 1. Copy Trader System Validation is Missing
- **135 closed picks display 0% WR** simply because there is NO background job resolving their TP/SL prices against real market data.
- The forward test workflow timeline is tied out after 10 minutes (insufficient). Picks remain permanently "OPEN".
- **Immediate Fix Required:** Implement an `outcome_resolver.py` specifically for `copy_trader_intel`.

### 2. Over 1,400 Picks Excluded from Tracking
- **Systems like `rapid_fire` (334 picks), `predictions` (324 picks), `quan_engine`, and `genome/revival_*`** have zero outcome tracking pipeline.
- MySQL receives discord event notifications, but system outcomes are never matched properly. 

### 3. Anti-Predictive Meta-Scoring (`MIN_SCORE=80` Inversion)
- **Highest scored picks LOSE money**, while **unscored ML picks (score=0) perform best** (~70.7% WR). 
- `alpha_engine/portfolio_tracker_copytrader.py` is potentially inverted. Lower scored picks perform better.
- **Fix:** `ml_score` (+0.337 correlation) was incorrectly zeroed previously based on biased IC analysis and needs its weight fully restored.

### 4. Junk & Gamed System Purge Needed
- `binance_smart_money`: NOT a true copy trader. A mere sentiment aggregate picking illiquid alts. **HARD_KILL**.
- **Bitget Traders**: Game WR via tiny grid trades. Needs block for `PF > 10`.
- **Whale profiles**: A 2-3% SL triggers repeatedly on market noise. Whales need 8% TP / 4% SL.
- Limit copy allocations strictly to `NMTD_25M` (60%) and `whale_123M` (30%).

### 5. ML Feature Death Stream
- **62% of features have failed since March 8th** within `ml_crypto_predictor/production_engine.py`. Models are trading on incomplete data inputs.

---

## DEEP INVESTIGATION FINDINGS (Added 2026-03-26)

> Source: Multi-agent codebase audit across dashboard JS, DB schema, sync pipeline, copytrader intel, and polymarket scraper.

### Win Rate Calculation — 4 Different Formulas (CRITICAL BUG)

The dashboard reports a SINGLE "win rate" figure but the codebase has AT LEAST 4 incompatible definitions:

| Location | Formula | Zero-PnL Treatment | Denominator |
|----------|---------|-------------------|-------------|
| `template.html` main WR card | `wins(pnl>0) / (wins+losses)` | **EXCLUDED** from both | Only non-zero resolved |
| `portfolio_manager.py` close | `net_pnl>0 ? win++ : loss++` | Counts as **LOSS** | All closed |
| Smart Picks tab (template.html) | `pnl > 0` | Counts as **LOSS** | All Smart picks |
| Strategy Leaderboard | `wins / all_trades` | Counted in **denominator** | ALL trades (incl. open) |

**Impact:** A strategy with 50% real WR could show anywhere from 42% to 58% depending on which component renders it. The leaderboard is most damaged — counting open/unresolved picks inflates denominator, suppressing reported WR.

### MySQL Schema Bug — FUTURES & ETF Not in ENUM

`at_raw_picks.asset_class` is defined as:
```sql
ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','UNKNOWN')
```
But `derive_asset_class()` in `sync_all_picks_to_mysql.py` returns `'FUTURES'` and `'ETF'` which are **missing from this ENUM**. In MySQL strict mode these inserts fail silently. All ETF picks (SPY, QQQ, GLD, TLT) and futures picks (ES=F, NQ=F) are either lost or stored as `UNKNOWN`, making asset-class filtering on the dashboard return wrong counts.

### `status='CLOSED'` Excluded from Win Rate Queries

Standard WR query counts `status IN ('WON','LOST')`. Any pick closed with exit_price but no explicit WON/LOST outcome stored gets `status='CLOSED'` — which is **excluded from both numerator and denominator**. This silently deflates the trade count and can shift reported WR by 5-15 percentage points.

### 0% WR Systems — Root Cause Confirmed

The _hundreds of picks showing 0% WR_ are caused by missing TP/SL price validation, **not** by the picks actually losing. The outcome resolution pipeline (compare exit time price to stored TP/SL levels) was never wired for: `copy_trader_intel`, `quan_engine`, `rapid_fire_data`, `predictions/`, `revival_*` genome files. These systems have closed picks where `pnl_pct=NULL` because nobody ever populated the exit prices — they show 0% by default in the dashboard JS (null coalesced to 0).

### Orphan Sources — 43 Still Not Wired to Dashboard (As of 2026-03-26)

Confirmed orphan sources not in `dashboard_generator.py` JSON_PICK_SOURCES:
- `copy_trader_intel/` (active + consensus/clones/highscore sub-files)
- `smart_money/active_picks.json`
- `prediction_market_agents/` (whale_signals + consensus_signals)
- `alpha_engine/momentum_tracker_picks.json`
- `genome/revival_*` files
- **Closed files being missed:** `battleground/luxalgo_closed_picks.json` (312 picks!), `multi_asset/multi_asset_closed.json` (105 picks)

### Dedup Hash Mismatch (Dual-Write Path)

`recorder.py` and `sync_all_picks_to_mysql.py` compute SHA-256 with DIFFERENT inputs. `recorder.py` uses full pick dict fields; sync uses `symbol|direction|entry_price|floor(epoch/300)*300`. Same pick can appear twice in the DB with different UUIDs, doubling its weight in all aggregate WR stats.

### Updated Status vs Grok Baseline (2026-03-26)

| Metric | This Session Target | Grok-Confirmed Current | Gap |
|--------|--------------------|-----------------------|-----|
| Copy Trader WR | 55%+ | **~31%** (filter just shipped, not yet measured) | -24pp |
| Forex TP Hit Rate | 30%+ hits | **~0/26 old; new 0.3% TP unvalidated** | Unknown |
| PM Picks in Production | 1+/day | **~0 ever confirmed in closed** | Active |
| Overall Crypto WR | 55%+ | **~51-53% (recent sessions)** | -2-4pp |
| Volume (closed trades) | Hundreds | **~1,900 closed system-wide** | At volume |
| Score-PnL Correlation | r>0.40 | **+0.33 (Method C)** | Yellow |

### Immediate Next Actions (P0, this session)

1. **Unify runtime artifact ownership first** — designate one authoritative publisher for `dashboard_payload.json`, `smart_picks.json`, and `smart_picks_history.json` so the live page stops mixing mismatched run states.
2. **Ship active-feed hygiene everywhere, then regenerate** — only `OPEN` rows with a real `entry_price` should survive into Active Picks before any dashboard regen is used as evidence of improvement.
3. **Reset or relabel `Smart WR` history** — current `smart_picks_history.json` still carries older polluted batches, so it should not be treated as execution proof until rebuilt or explicitly labeled snapshot-based.
4. **Wire TP/SL outcome validation** for `copy_trader_intel`, `quan_engine`, `rapid_fire_data` — this unblocks honest WR on 300+ currently 0% picks.
5. **Unify forex active/closed lineage and add missing close files** — bring `multi_asset` / `multi_asset_copytrader` naming and close-history sources into one coherent namespace before using forex WR as a product KPI.

### Mercury (Inception Labs) Investigation Fixes — In Progress

| # | Mercury Finding | Status | Action |
|---|----------------|--------|--------|
| 1 | Missing picks in DB (NG=F not in at_local_picks) | Agent fixing MySQL ENUM | FUTURES/ETF picks silently lost |
| 2 | Binance-only price source in check_top_picks_outcome.py | Agent wiring api_failover | Forex/exotic crypto unresolvable |
| 3 | 20-position cap (portfolio_manager.py line 3820) | Agent expanding to 200 | Older trades dropped from WR |
| 4 | Unrealized P/L not counted | BY DESIGN | Hedge funds don't count unrealized |
| 5 | Timestamp parsing fragility | Low priority | Partial fix in outcome_resolver |
| 6 | 4 WR formulas across codebase | TODO | Standardize to one definition |
| 7 | Dedup hash mismatch (recorder vs sync) | ALREADY FIXED | Dual-write path removed (line 300 of sync) |

### P3 — Forward Validation
- [ ] Track forex picks with new 0.3% TP — do we get TP hits now?
- [ ] Track PM picks — do they actually reach active_picks.json?
- [ ] Monitor copy trader filter — does HFT exclusion improve WR?
- [ ] Validate ML symbol expansion — do Wave 2 symbols perform in forward test?

---

## KEY METRICS TO TRACK

| Metric | Before | Target | Current |
|--------|--------|--------|---------|
| Copy Trader WR | 31% | 55%+ | TBD (after HFT filter) |
| Forex TP Hit Rate | 0/26 (0%) | 30%+ | TBD (after 0.3% TP) |
| PM Picks Produced | 0 ever | 1+ per day | TBD (after orchestrator fix) |
| ML Symbol Coverage | 4 | 13 | 13 (done) |
| Overall Portfolio WR | ~35% | 55%+ | TBD |
| SL Amplification | 5-11x | 1.0x | 1.0x (fixed) |

---

## AI Co-Pilot Extensive Insight & Assessment

1. **The 'Garbage In' Problem Overcome:** The identification of 95% of 'qualified' copy traders as HFT market-makers explains the fundamental disconnect between reported backtest win-rates and actual forward-testing. HFT alpha is highly execution-dependent; attempting to track it on a 30-minute lag guarantees failure. Filtering by median-hold > 4h is a critical save.
2. **SL Gap-Through:** Taking exits at `live_price` instead of `SL price` was systematically skewing risk parameters (the 11x amplification). Removing this structural handicap alone will significantly alter our baseline metrics closer to a sustainable R:R.
3. **Forex Calibration Alignment:** Forex ATR inherently contradicts the previous 0.8% TP. Validating the drop to 0.3% is mathematically sound and aligns with standard FX pipeline dynamics.
**Recommendation:** Focus immediate validation efforts on ensuring the HFT blocklist persists across workflow runs and monitoring the true risk-adjusted return (Sharpe) of the newly calibrated 0.3% Forex TPs over a 20-trade sample size.
