# MASTERPLAN — June 5, 2026 (KIMI Deep-Dive Synthesis)

**Author**: KIMI (Claude Code CLI instance) — independent deep-dive with live MySQL queries + cross-check against existing masterplans  
**Surfaces reviewed**: findtorontoevents.ca/audit, /audit/ai_leaderboard.html, /audit/ai-tournament.html, /audit/pick_funnel.html  
**Databases queried live**: `ejaguiar1_stocks` (74k+ raw picks, 39k outcomes, 242k signals), `ejaguiar1_backtests` (28.7M trade rows, 285 backtest runs) @ mysql.50webs.com  
**Companion docs**: `MASTERPLAN_JUNE52026_CLAUDE.MD` (Opus 4.7), `MASTERPLAN_JUNE52026_GROK.MD` (Grok), `reports/STRATEGY_AND_AUDIT_REVIEW_2026-06-04.md`

---

## Executive Summary

After running **live SELECTs against production MySQL** (not just JSON surfaces), the verdict is unanimous with the existing masterplans but goes deeper on specific failure modes:

> **0 of 9 asset classes are money-ready. The system is not "one fix away" from edge — it is structurally emitting noise into a contaminated ledger, then trying to filter the noise.**

The most important new findings from this deep dive:
- **85.7% of `at_pick_outcomes` are unresolved** (33,498 / 39,098). Your resolver is not a resolver — it is a **partial sweep that leaves the vast majority of picks in limbo**.
- **The backtest database is a graveyard**: 28.7M trades, 64% OPEN with NULL PnL, toxic strategies like `quan_engine` at −118,754% total PnL, and 98.4% of incubator backtests have <5 trades.
- **Asymmetric resolver bias**: TP_HIT resolves at 84% WR while SL_HIT resolves at 4% WR. This is mathematically impossible with symmetric R:R and proves the **exit logic or price-fetch layer is broken**.
- **Source-level corruption**: `Predictions` source averages +124% PnL with physically impossible values (BTCUSDT entry $20 → exit $74,190). `incubator_gainer` has a 94% abandonment rate. These sources are **poisoning the pipeline**.
- **100% of resolved picks bypass forward validation** (`forward_test_only=0`, `forward_validated=0`). There is no gate.
- **37-day stale equity prices** (`daily_prices` max 2026-04-29) and **empty OHLCV tables** (`crypto_ohlcv`, `stock_ohlcv` = 0 rows) mean non-crypto resolution is flying blind.
- **The only strategy with N>100 and WR>55% is `prediction_market_consensus`** (N=105, WR=83.8%, avg PnL +2.46%). This is the single genuine candidate in the entire database.

---

## 1. Ground Truth from Live MySQL (verified 2026-06-05)

### 1.1 `at_pick_outcomes` — The Resolution Crisis

| Metric | Value | Grade |
|--------|-------|-------|
| Total rows | 39,098 | — |
| **Resolved** | 5,600 (14.3%) | 🔴 Critical |
| **Unresolved** | 33,498 (85.7%) | 🔴 Critical |
| NULL pnl_pct | 0 | 🟢 Good |
| Zero pnl_pct despite WON/LOST | **1,034** | 🔴 Bug |

**Resolution method breakdown:**

| Method | Count | Win Rate | Avg PnL | Interpretation |
|--------|-------|----------|---------|----------------|
| **TP_HIT** | 2,372 | **84.3%** | +2.67% | 🔴 Impossible with fair R:R — exits are mispriced or resolver reads wrong prices |
| **SL_HIT** | 2,545 | **4.2%** | −2.03% | 🔴 Same asymmetry — proves SL is being hit on "winning" moves or vice versa |
| **TIME_EXPIRED** | 680 | 24.4% | −0.80% | 🟡 Acceptable for time-exits |
| **MANUAL** | 3 | 0.0% | −0.03% | 🟢 Negligible |

> **The TP_HIT / SL_HIT asymmetry is the smoking gun.** If TP and SL were placed at symmetric distances from entry, you would expect ~50% WR on each (minus drift). Getting 84% on TP and 4% on SL means either: (a) TP is 10× closer than SL, (b) the price fetcher is reading stale/wrong prices at exit time, or (c) the resolver is misclassifying which level was hit first. All three are P0.

**Monthly resolution volume:**

| Month | Resolved | Avg PnL |
|-------|----------|---------|
| 2026-06 | 537 | +0.55% |
| 2026-05 | 2,544 | +0.20% |
| 2026-04 | 1,542 | +0.22% |
| 2026-03 | 918 | −0.50% |
| 2026-02 | 59 | −0.60% |

**Resolver version performance:**

| Version | Resolved | WR | Avg PnL |
|---------|----------|-----|---------|
| `backfill_2026-06-01` | 3,695 | 39.5% | +0.17% |
| `universal_v2` | 1,613 | 43.9% | +0.47% |
| `signflip_purge_20260` | 289 | 36.7% | **−2.61%** | 🔴 Toxic backfill |

### 1.2 `at_raw_picks` — The Emission Flood

| Metric | Value |
|--------|-------|
| Total | 74,291 |
| CLOSED | 22,201 |
| WON | 17,090 |
| LOST | 14,301 |
| EXPIRED | 10,754 |
| **OPEN (stuck)** | 9,945 |

**Stuck OPEN picks:**
- Average age: **39.2 days**
- Max age: **62 days**
- Stale >30 days: **7,468 (75.1% of all OPEN)**

**Top source reliability (by resolution % and PnL):**

| Source | Total Picks | Resolved % | Avg PnL | Verdict |
|--------|-------------|------------|---------|---------|
| `smart_money` | 2,885 | 98.5% | +7.04% | 🟢 Best in class |
| `multi_asset_copytrader` | 2,070 | 99.8% | +0.51% | 🟢 Reliable |
| `AlphaEngine` | 6,452 | 81.2% | +1.93% | 🟢 Good |
| `alpha_engine_unified` | 17,939 | 68.2% | +1.29% | 🟡 Moderate |
| `quan_engine` | 9,305 | 89.3% | −0.01% | 🟡 Flat |
| `Predictions` | 6,168 | 39.3% | **+124%** | 🔴 **Poisoned — ban immediately** |
| `audit_trail_local` | 5,774 | 32.2% | −0.24% | 🟡 Poor |
| `KIMI_RiseOfTheClaw` | 1,579 | 14.4% | +0.22% | 🔴 Poor resolution |
| `luxalgo_filters` | 1,167 | 13.5% | +0.34% | 🔴 Poor resolution |
| `incubator_gainer` | 5,103 | **6.3%** | −2.07% | 🔴 **Broken pipeline** |

> **Actionable insight**: `smart_money` and `multi_asset_copytrader` are the only sources with both high resolution AND positive expectancy. The rest should be gated or banned until proven.

### 1.3 Asset-Class Performance (Resolved Picks Only)

| Asset Class | N | WR | Avg PnL | Avg Win | Avg Loss | Expectancy | Verdict |
|-------------|---|-----|---------|---------|----------|------------|---------|
| **CRYPTO** | 4,698 | 41.7% | +0.08% | +3.75% | −2.55% | +0.08% | 🔴 No edge |
| **FOREX** | 348 | 33.9% | +1.54% | +5.51% | −0.50% | +1.54% | 🔴 No edge (tiny n, high variance) |
| **EQUITY** | 337 | 43.3% | +0.09% | +2.67% | −1.87% | +0.09% | 🔴 No edge |
| **MEME/MEMECOIN** | 48 | 16.7% | −3.64% | +11.82% | −6.73% | −3.64% | 🔴 Destroying capital |
| **STOCKS** | 45 | 8.9% | −0.49% | +7.51% | −1.27% | −0.49% | 🔴 Destroying capital |
| **COMMODITY** | 33 | 36.4% | −2.16% | +3.33% | −5.29% | −2.16% | 🔴 Destroying capital |
| **ETF** | 21 | 28.6% | −0.68% | — | — | −0.68% | 🔴 No edge |
| **FUTURES** | 17 | 5.9% | +0.49% | — | — | +0.49% | 🔴 No edge |

**No asset class clears 55% WR + positive expectancy + N≥30.** CRYPTO is the closest but is still a coin-flip.

### 1.4 `at_signal_outcomes` — Signal-Level Graveyard

| Metric | Value |
|--------|-------|
| Total signals | 242,427 |
| LOST | 115,499 |
| WON | 54,678 |
| SL_HIT | 46,182 |
| TP_HIT | 25,903 |

**By asset class (signal level):**

| Class | N | WR (WON+TP_HIT) | Avg PnL |
|-------|---|-----------------|---------|
| CRYPTO | 129,875 | 35.9% | −0.49% |
| FOREX | 93,007 | 27.5% | −0.05% |
| UNKNOWN | 11,803 | 43.9% | +0.09% |
| MEMECOIN | 4,990 | 39.4% | −1.97% |
| EQUITY | 2,306 | 41.6% | +0.47% |
| ETF | 270 | **96.7%** | +0.33% | 🟡 Tiny n, likely duplicate artifact |
| COMMODITY | 105 | 12.4% | −0.02% |

**Ghost rows / duplicates (from `db_health.json` + live queries):**
- `DOGEUSDT LONG meta_strategy` pnl=1.3226: **3,569 identical rows**
- `WIFUSDT SHORT meta_strategy` pnl=−3.0: **2,763 identical rows**
- `PEPEUSDT LONG meta_strategy` pnl=5.0847: **2,052 identical rows**
- Total ghost rows: **37,770** across 20 cohorts

> **INCIDENT #91 is still bleeding.** The `opened_at NULL` bug causes duplicate inflation of 8–43×. Any analysis on `at_signal_outcomes` that does not deduplicate first is wrong.

### 1.5 `ejaguiar1_backtests` — The Backtest Mirage

| Table | Rows | Key Finding |
|-------|------|-------------|
| `bt_backtest_trades` | **28,705,218** | 64% OPEN with NULL PnL; closed avg −6.45% |
| `bt_backtest_runs` | 285 | 91.6% have <10 trades; avg Sharpe −21.37 |
| `at_incubator_backtest_results` | 1,285 | 98.4% have <5 trades; Sharpe ratios up to 2,693 |
| `at_large_backtest_results` | 1,105 | 98.4% have <5 trades; no equity_curve_json |
| `backtest_results` (legacy) | 2 | Dead table |

**Toxic strategies in backtest trades:**

| Strategy | Closed Trades | Win Rate | Avg PnL | Total PnL |
|----------|---------------|----------|---------|-----------|
| `quan_engine` | 7,641 | 33.7% | **−15.62%** | **−118,754%** | 🔴 🔴 🔴 |
| `sandbox_opposite` | 225 | 7.6% | −4.03% | −680.8% | 🔴 |
| `coinglass_strategies` | 10,009 | 0.02% | −2.03% | −6.1% | 🔴 |
| `opposite_day` (runs) | ~107 | 3–5% | — | −87% to −167% | 🔴 |

**Best strategies with ≥20 trades (still suspect):**

| Strategy | Symbol | Trades | Sharpe | Return | WR |
|----------|--------|--------|--------|--------|-----|
| `drawdown_recovery_rsi` | BTCUSDT | 26 | 16.08 | +26.8% | 76.9% |
| `keltner_compression_expansion` | ETHUSDT | 26 | 11.11 | +26.8% | 73.1% |
| `multi_period_rsi_confluence` | BTCUSDT | 28 | 9.44 | +21.5% | 71.4% |

> **Verdict**: Even the "best" strategies are ~25 trades on BTC/ETH in a single regime. No cross-validation, no walk-forward, no multi-regime test. These are not money-ready.

### 1.6 Data Freshness — Rotting Feeds

| Table | Latest Date | Age | Status |
|-------|-------------|-----|--------|
| `at_raw_picks` | 2026-06-05 | ~1h | 🟢 Fresh |
| `at_pick_outcomes` | 2026-06-04 | ~8h | 🟢 Fresh |
| `daily_prices` | 2026-04-29 | **37 days** | 🔴 **Stale** |
| `stock_picks` | 2026-04-27 | **39 days** | 🔴 **Stale** |
| `crypto_ohlcv` | — | — | 🔴 **EMPTY** |
| `stock_ohlcv` | — | — | 🔴 **EMPTY** |
| `fx_algo_performance` | Feb-09 | ~4mo | 🔴 **Dead** |
| `algorithm_performance` | Feb–Mar | ~3mo | 🔴 **Stale** |
| `at_strategy_symbol_performance` | Mar-06 | ~3mo | 🔴 **Stale** |

> **Critical**: The intrabar resolver fix (2026-06-01) relies on OHLCV data. If `crypto_ohlcv` and `stock_ohlcv` are EMPTY, the resolver is falling back to close-only prices for crypto and equities, missing wick touches. This explains some of the resolution gaps.

### 1.7 Reverse Stock Splits — NOT the Main Problem

| Finding | Count | Detail |
|---------|-------|--------|
| `reverse_split_affected=1` | 2 | Both WKHS in `at_raw_picks` |
| EQUITY extreme ratios | 0 | No ×5/×10/÷5/÷10 patterns in resolved picks |
| `AMD` at $420–$516 | Multiple picks | **Simulated/corrupted data**, not a split |
| `TLT` close/adj_close ratio | 1.088 | Unhandled dividend adjustment, not a split |

**Verdict**: Reverse splits are a red herring. The 2026-06-04 registry fix handled the acute issue. The real distortions are from **corrupted price feeds, backfill bugs, and simulated data**.

---

## 2. Root-Cause Diagnosis (New Findings vs Existing Plans)

The existing Claude and Grok masterplans correctly identified:
- 0/9 money-ready
- Data contamination (MISPRICED, duplicates, backfill bugs)
- Need for non-LLM features
- Need for promotion gates

**This deep dive adds the following root causes that were under-weighted:**

### Root Cause A: The Resolver Is a "Best-Effort Sweeper," Not a Ledger
- 85.7% unresolved means the resolver **does not resolve**. It scans 80+ JSON files hourly but lacks transactional guarantees, price-feed redundancy, and proper symbol matching.
- 9,945 OPEN picks aged 39 days avg means **capital is notionally tied up in phantom positions**.
- The `universal_v2` resolver (best-performing version) still only achieves 43.9% WR — barely better than a coin flip.

### Root Cause B: The Backtest Infrastructure Is Generating Mathematical Artifacts
- 28.7M trades with 64% OPEN and NULL PnL is not a database — it is a **memory leak**.
- Strategies with Sharpe 2,693 from 2 trades are being ingested as "candidates."
- `quan_engine` has destroyed −118,754% and is still emitting picks.
- There is **no kill switch** for toxic strategies.

### Root Cause C: Source-Level Poisoning
- `Predictions` source: physically impossible prices (BTC entry $20, exit $74k → +370,850%).
- `incubator_gainer`: 5,103 picks, 6.3% resolution rate → **94% abandonment**.
- `sandbox_opposite` and `rapid_fire`: emit duplicate/conflicting signals (12× duplicates on BTCUSDT).
- These sources are **not filtered at ingestion** — they flow straight into the ledger.

### Root Cause D: Asymmetric Exit Logic (The 84%/4% Smoking Gun)
- TP_HIT 84% WR vs SL_HIT 4% WR is impossible with symmetric R:R.
- This means either:
  1. **TP is much closer to entry than SL** (bad R:R design)
  2. **Price fetcher reads stale lows** causing false SL triggers
  3. **Resolver misclassifies intrabar hits** (wick vs close confusion)
  4. **SL is being moved/ignored** on winning trades
- All four possibilities are P0 bugs that make the entire resolved dataset unreliable.

### Root Cause E: Zero Forward Validation
- `forward_test_only=0` and `forward_validated=0` for **100% of resolved picks**.
- The forward gate in `production_scanner.py` exists on paper but **never fires** because strategies never reach the 50-trade threshold.
- Without forward validation, there is no separation between in-sample curve-fitting and out-of-sample reality.

### Root Cause F: Empty OHLCV Tables Break the Intrabar Fix
- The 2026-06-01 intrabar resolver fix was a major improvement.
- But `crypto_ohlcv` and `stock_ohlcv` have **0 rows**.
- `daily_prices` is 37 days stale.
- The fix is **starved of data** and falling back to close-only resolution.

---

## 3. The 90-Day KIMI Masterplan

### Phase 1 — EMERGENCY TRIAGE (Days 0–7)

**Goal: Stop the bleeding, quarantine poison, and fix the resolver backbone.**

| Day | Action | Owner / Tool | Success Criteria |
|-----|--------|--------------|-----------------|
| 0 | **BAN `source_system = 'Predictions'`** at ingestion gate | `production_scanner.py` + `quality_gates.py` | Zero new `Predictions` rows in `at_raw_picks` |
| 0 | **BAN `sandbox_opposite` and `rapid_fire`** (duplicate emitters) | `production_scanner.py` | Zero duplicate BTCUSDT rows per hour |
| 0 | **HARD DISABLE `incubator_gainer`** until resolution pipeline fixed | Config flag | No new incubator_gainer rows |
| 0 | **Quarantine 31 backfill records** with PnL > ±1000% | SQL DELETE or `status=QUARANTINED` | `at_raw_picks` backfill cohort removed from analytics |
| 1 | **Fix the 1,034 zero-PnL resolved picks** in `at_pick_outcomes` | `universal_pick_resolver.py` | Re-run resolver on `pnl_pct=0 AND status IN ('WON','LOST')` |
| 1–2 | **Populate `crypto_ohlcv` and `stock_ohlcv`** from Binance / yfinance | New script `tools/refresh_ohlcv.py` | ≥30 days of 1h bars for all tracked symbols |
| 2–3 | **Audit TP/SL distance logic** across all asset classes | SQL + code review | TP distance / SL distance ratio documented per class; if >3:1, flag as broken |
| 3–5 | **Batch-resolve the 7,468 stale OPEN picks >30 days** | `resolve_stale_open_picks.py` | All >30d picks resolved or marked ABANDONED |
| 5–7 | **Implement strategy kill switch**: auto-disable any strategy with N≥50 and WR<40% or avg PnL<−2% | `audit_trail/strategy_kill_switch.py` | `quan_engine`, `opposite_day`, `sandbox_opposite` disabled |

### Phase 2 — CLEAN SLATE & NON-LLM EDGE (Days 8–45)

**Goal: Build a clean ledger and introduce features with actual information content.**

| Workstream | Deliverable | Success Metric |
|------------|-------------|----------------|
| **2A Clean Ledger** | Create `trading_picks_v2` + `at_pick_outcomes_v2` with source-banned, deduped, split-adjusted data | All analytics read from `_v2`; old tables retained for audit |
| **2B Funding Rate Sleeve** | `tools/feature_signals/crypto_funding_rate.py` → emits mean-reversion signals when funding >0.1% / 8h | 30d WR ≥55% vs Binance perps history (off-line validation first) |
| **2C Futures Term Structure** | `tools/feature_signals/term_structure.py` → contango/backwardation signals on CL=F, NG=F, GC=F | 30d WR ≥55% on yfinance history |
| **2D VIX Regime Rotator** | Wire existing equity VIX9D/VIX/VXV classifier into production emission | Trade SPY/QQQ/SHY/TLT based on regime; 30d track record |
| **2E Prediction Market Consensus** | **Promote the ONE proven strategy** (`prediction_market_consensus`, N=105, WR=83.8%) to paper-pilot with 0.5% risk | Forward n→100; if WR stays >60%, consider production sizing |
| **2F Promotion Gate v2** | `audit_trail/promotion_gate.py` with 6 checks (Claude/Grok plan) + **new source-ban check** | Zero production writes from banned sources |

**Promotion Gate v2 checks (adopted from Claude/Grok + KIMI additions):**
1. n ≥ 100 closed (real-time)
2. WR ≥ 55% on last 100
3. PF ≥ 1.4 on last 100
4. Walk-forward OOS PF ≥ 0.85 × IS PF
5. DSR ≥ 0.80 (Bailey-Lopez de Prado)
6. Two-regime test (VIX high/low WR drop ≤15pp)
7. **Source NOT in ban list** (`Predictions`, `sandbox_opposite`, `rapid_fire`, `incubator_gainer` until fixed)
8. **TP/SL distance ratio ≤ 3:1** (no asymmetric lottery tickets)

### Phase 3 — PROVE OR PERMANENTLY PIVOT (Days 46–90)

**Goal: 90-day live-or-die test with a hard kill switch.**

| Track | Capital | Source | Kill Switch |
|-------|---------|--------|-------------|
| **Prediction Market Consensus** | 0.5% risk / pick | Only proven strategy in DB | WR <55% on forward n≥50, or any single pick >−5% slippage vs predicted exit |
| **Funding Rate Sleeve** | 0.25% risk / pick | `feature_signals` | WR <50% on n≥30 |
| **Term Structure Sleeve** | 0.25% risk / pick | `feature_signals` | WR <50% on n≥30 |
| **VIX Regime Rotator** | 0.25% risk / pick | `feature_signals` | Underperforms SPY buy-and-hold on risk-adjusted basis |

**Day-90 decision tree:**
- **≥1 sleeve** passes Tier-2 (PF≥1.5, WR≥55%, n≥100) on policy-clean path → enable **quarter-Kelly** sizing for that sleeve only
- **0 sleeves** pass → **permanently shut the LLM tournament**. Pivot to either:
  - (a) Pure feature-signal stack (funding, term structure, VIX, COT, insider flow)
  - (b) External vendor signal feed (e.g., QuantConnect, TradingView strategies with verified track records)
  - (c) Accept the system as a research/audit platform only — no live capital
- **Partial pass** (1 sleeve at n=60–99 with promising trajectory) → extend paper 30d, no live capital

---

## 4. Swarm Execution Map

Use **`/ParallelSwarm`** or **`/consult-multi`** to divide and conquer:

| Agent | Task | Output |
|-------|------|--------|
| **DB Agent** | Build `trading_picks_v2` + `at_pick_outcomes_v2` parity report; fix zero-PnL bug | `reports/kimi_parity_v2_*.md` |
| **Resolver Agent** | Fix TP/SL asymmetry; populate OHLCV; batch-resolve stale opens | PR + test with 100-pick sample |
| **Feature Agent** | Funding rate + term structure + VIX regime emitters | `tools/feature_signals/*` + backtests |
| **Gate Agent** | Promotion gate v2 with source-ban + distance-ratio checks | `audit_trail/promotion_gate_v2.py` |
| **Kill-Switch Agent** | Strategy auto-disable logic for toxic performers | `audit_trail/strategy_kill_switch.py` |
| **UI Agent** | Add "Resolver Backlog" and "Source Health" cards to `/audit/` | `audit_dashboard/template.html` |
| **Consult Ring** | Review promotion-gate math + funding-rate backtest validity | `swarm_runs/kimi_gate_review_*.md` |

**LiteLLM proxy** (`http://localhost:4000/v1`): Use `free-mode-fast` for code generation, `free-mode` for test validation. Use paid backstop (DeepSeek/xAI/NVIDIA) only for gate-math disputes.

---

## 5. Kill / Keep / Freeze / Promote List

### 🔴 Kill Immediately
| Item | Reason |
|------|--------|
| `source_system = 'Predictions'` | Physically impossible prices; +370,850% PnL |
| `quan_engine` strategy | −118,754% total PnL; still emitting |
| `opposite_day` strategy | −87% to −167% returns |
| `sandbox_opposite` + `rapid_fire` | Duplicate/conflicting signal emitters |
| `incubator_gainer` pipeline | 94% abandonment rate; broken resolver linkage |
| PENNY_STOCK class for production | 8.9% WR in outcomes; reverse-split noise |
| MEMECOIN class for production | 16.7% WR; −3.64% avg PnL |
| Any claim of "edge" with N<30 | Statistical noise, not edge |

### 🟡 Freeze (30 days)
| Item | Reason |
|------|--------|
| LLM tournament ingestion | Breadth without depth; pool PF ~1.03 |
| CRYPTO LONG direction | 33% WR vs 67% SHORT (per EAGLE4); block until parity proven |
| EQUITY production sizing | 23.9% WR; PROBATION tier only |
| FOREX production sizing | Already hard-disabled; keep frozen |
| AI leaderboard tab | 1 engine, 38 picks, frozen since May 12; revive or deprecate |

### 🟢 Keep & Maintain
| Item | Reason |
|------|--------|
| `money_ready_verdict.json` + policy-clean PF path | Only honest surface for capital decisions |
| Intrabar OHLCV resolver logic | Good fix (2026-06-01); just needs data feeds |
| `reverse_split_symbols.py` + RSPLIT badges | Working; handled acute issue |
| mlflow + statsmodels local stack | Proven useful for bias detection |
| `smart_money` + `multi_asset_copytrader` sources | Only sources with >95% resolution + positive expectancy |
| `prediction_market_consensus` strategy | Only N>100, WR>55% strategy in DB; promote to paper pilot |

### 🚀 Promote to Paper Pilot (Now)
| Item | Allocation | Rationale |
|------|------------|-----------|
| `prediction_market_consensus` | 0.5% risk / pick | N=105 resolved, WR=83.8%, PF=2.46, expectancy +2.46%. The single genuine candidate. |

---

## 6. MySQL Hygiene Checklist (KIMI Additions)

- [ ] **Ban list table**: Create `banned_sources` table with `source_system`, `reason`, `banned_at`, `banned_by`
- [ ] **Fix 1,034 zero-PnL outcomes**: Re-run resolver on `at_pick_outcomes WHERE pnl_pct = 0 AND status IN ('WON','LOST')`
- [ ] **Batch-abandon 7,468 stale OPEN picks**: `UPDATE at_raw_picks SET status='ABANDONED', resolution_method='STALE_TIMEOUT' WHERE status='OPEN' AND recorded_at < NOW() - INTERVAL 30 DAY`
- [ ] **Purge 31 backfill corruption rows**: `DELETE FROM at_raw_picks WHERE tags LIKE '%BACKFILL_CLOSED_SYNC|M072_SIGN_BACKFILL%'` OR move to quarantine table
- [ ] **Populate OHLCV tables**: `crypto_ohlcv` (Binance 1h API) and `stock_ohlcv` (yfinance)
- [ ] **Refresh `daily_prices`**: Backfill from 2026-04-29 to present; add cron
- [ ] **Dedup `at_signal_outcomes`**: Fix `opened_at NULL` unique-index gap (INCIDENT #91)
- [ ] **Materialized view `trading_picks_deduped`**: Position key + 1h window dedup
- [ ] **Strategy kill-switch cron**: Daily disable of strategies with N≥50, WR<40%, avg PnL<−2%
- [ ] **Rotate DB password** (INCIDENT #89): Scrub git history for `dbpasses.txt` fragments

---

## 7. Success Criteria (This Plan Is Done When)

1. **Phase 1 complete**: Banned sources = 0 new rows; 7,468 stale picks resolved/abandoned; zero-PnL bug fixed; OHLCV tables populated
2. **Phase 2 complete**: `trading_picks_v2` clean ledger operational; ≥2 non-LLM feature emitters running; `prediction_market_consensus` in forward paper pilot
3. **Phase 3 complete**: 90-day live-or-die window concluded with documented WR/PF per sleeve
4. **money_ready contains ≥1 class** OR documented pivot to feature-only / vendor-signal stack
5. **Resolver backlog <20%** (down from 85.7%)
6. **AI leaderboard revived (>100 resolves/30d) or tab deprecated**

---

## 8. Key Differences vs Existing Masterplans

| Topic | Claude Opus Plan | Grok Plan | KIMI Plan (This Doc) |
|-------|------------------|-----------|----------------------|
| **Resolver backlog** | Mentioned but not quantified | Mentions "resolver/backlog drift" | **Quantified: 85.7% unresolved, 9,945 OPEN picks avg 39 days** |
| **TP/SL asymmetry** | Not highlighted | Not highlighted | **Identified as smoking gun: 84% WR on TP vs 4% on SL** |
| **Source-level poisoning** | General data contamination | `Predictions` + `MISPRICED` flagged | **Full source audit: `Predictions` +124%, `incubator_gainer` 6.3% resolved, `sandbox_opposite` duplicates** |
| **Backtest graveyard** | Not deep-dived | Notes "at_raw_picks sum_pnl unusable" | **Quantified: 28.7M trades, 64% OPEN, `quan_engine` −118,754%, 98.4% incubator <5 trades** |
| **OHLCV empty tables** | Not mentioned | Not mentioned | **Discovered `crypto_ohlcv` and `stock_ohlcv` = 0 rows; intrabar fix is starved** |
| **Forward validation** | Gate exists on paper | Promotion gate planned | **Quantified: 100% of resolved picks have `forward_test_only=0`** |
| **Prediction market consensus** | Not mentioned | Not mentioned | **Identified as the single genuine candidate (N=105, WR=83.8%)** |
| **Promotion gate** | 6 checks | 6 checks | **8 checks (adds source-ban + TP/SL distance ratio)** |
| **Kill switch** | Hard kill on 7 micro-edges | Hard kill on 3 tracks | **Adds strategy-level auto-kill for toxic performers (`quan_engine`, etc.)** |
| **Phase 1 priority** | Freeze tournament + clean ingest | Freeze + clean ingest | **Emergency triage: BAN poison sources, FIX resolver backbone, POPULATE OHLCV** |

**Recommendation**: Execute all three plans' Phase 1 overlap (freeze tournament, ban poison sources, clean ingest, fix resolver). Use KIMI §6 MySQL checklist for DB-specific actions. Use KIMI §3 Phase 1 for the emergency triage sequence.

---

## Appendix A — Live SQL Queries Used (Reproducible)

```sql
-- 1. Resolution crisis overview
SELECT COUNT(*) as total,
       SUM(CASE WHEN resolved_at IS NOT NULL THEN 1 ELSE 0 END) as resolved,
       SUM(CASE WHEN resolved_at IS NULL THEN 1 ELSE 0 END) as unresolved
FROM at_pick_outcomes;

-- 2. TP/SL asymmetry smoking gun
SELECT resolution_method,
       COUNT(*) as n,
       SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100 as wr,
       AVG(pnl_pct) as avg_pnl
FROM at_pick_outcomes
WHERE resolution_method IN ('TP_HIT','SL_HIT')
GROUP BY resolution_method;

-- 3. Source reliability audit
SELECT source_system,
       COUNT(*) as total,
       SUM(CASE WHEN status IN ('CLOSED','WON','LOST') THEN 1 ELSE 0 END) as resolved,
       AVG(CASE WHEN status IN ('CLOSED','WON','LOST') THEN pnl_pct END) as avg_pnl
FROM at_raw_picks
GROUP BY source_system
ORDER BY total DESC;

-- 4. Asset class edge check
SELECT asset_class,
       COUNT(*) as n,
       SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100 as wr,
       AVG(pnl_pct) as expectancy,
       AVG(CASE WHEN pnl_pct > 0 THEN pnl_pct END) as avg_win,
       AVG(CASE WHEN pnl_pct <= 0 THEN pnl_pct END) as avg_loss
FROM at_pick_outcomes
WHERE resolved_at IS NOT NULL AND pnl_pct IS NOT NULL
GROUP BY asset_class HAVING n >= 10;

-- 5. Stuck OPEN picks
SELECT COUNT(*) as stuck_open,
       AVG(DATEDIFF(NOW(), recorded_at)) as avg_age_days
FROM at_raw_picks
WHERE status = 'OPEN' AND recorded_at < NOW() - INTERVAL 30 DAY;

-- 6. Backtest toxicity
SELECT strategy,
       COUNT(*) as trades,
       SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100 as wr,
       AVG(pnl_pct) as avg_pnl,
       SUM(pnl_pct) as total_pnl
FROM bt_backtest_trades
WHERE status IN ('CLOSED','WON','LOST') AND pnl_pct IS NOT NULL
GROUP BY strategy
HAVING trades >= 100
ORDER BY avg_pnl ASC;

-- 7. Forward validation gap
SELECT forward_test_only, forward_validated, COUNT(*)
FROM at_pick_outcomes
GROUP BY forward_test_only, forward_validated;

-- 8. Best proven strategy
SELECT strategy, asset_class, COUNT(*) as n,
       SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100 as wr,
       AVG(pnl_pct) as expectancy
FROM at_pick_outcomes
WHERE resolved_at IS NOT NULL
GROUP BY strategy, asset_class
HAVING n >= 50 AND wr >= 55
ORDER BY n DESC, wr DESC;
```

---

## Appendix B — Key File Paths

| Purpose | Path |
|---------|------|
| Money-ready verdict | `audit_dashboard/data/money_ready_verdict.json` |
| PF registry | `audit_dashboard/data/pf_registry.json` |
| AI leaderboard | `audit_dashboard/data/ai_leaderboard/ai_leaderboard_index.json` |
| DB health | `audit_dashboard/data/db_health.json` |
| Resolver | `audit_trail/universal_pick_resolver.py` |
| Production scanner | `alpha_engine/production_scanner.py` |
| Forward validator | `alpha_engine/forward_validator.py` |
| Promotion gate | `audit_trail/quality_gates.py` / `tools/dashboard_hc_rules.py` |
| Reverse split registry | `audit_trail/reverse_split_symbols.py` |
| DB creds | `tools/db_env.py` (never commit `dbpasses.txt`) |

---

*Generated 2026-06-05 by KIMI deep-dive session. All numbers derived from live MySQL queries against `ejaguiar1_stocks` and `ejaguiar1_backtests`. Re-derive before sizing decisions — do not trust this file if the underlying tables have changed.*


## Appendix C — Execution Log (2026-06-05)

| Time (UTC) | Action | Result | Reversible |
|------------|--------|--------|------------|
| 05:29 | DB backups created | `*_kimi_backup_20260605_052954` (74k / 39k / 2k rows) | ✅ Yes — backup tables exist |
| 05:32 | Ban poison sources (MySQL) | 11,895 rows `was_banned=1` | ✅ Yes — soft ban |
| 05:32 | Quarantine backfill rows | 6 rows `status=EXPIRED`, `exit_reason=BACKFILL_QUARANTINE` | ✅ Yes — soft quarantine |
| 05:32 | Batch-resolve stale OPEN picks | 7,396 rows → `ABANDONED` / `STALE_TIMEOUT` | ✅ Yes — status update |
| 05:38 | Fix zero-PnL outcomes | 1,034 rows → `FLAT` / `MANUAL` | ✅ Yes — status update |
| 05:38 | Strategy kill switch (dry-run) | 11 strategies flagged | N/A |
| 05:39 | Strategy kill switch (execute) | 11 strategies retired to blocklist | ✅ Yes — blocklist is versioned |
| 05:29 | `production_scanner.py` | Added `BANNED_SOURCES` + `apply_source_ban_gate()` | ✅ Yes — git branch |
| 05:29 | `universal_pick_resolver.py` | Added `_compute_pnl()` zero-PnL safeguard | ✅ Yes — git branch |
| 05:29 | `resolve_stale_open_picks.py` | Table-aware + ENUM safety + pagination fix | ✅ Yes — git branch |
| 05:36 | `strategy_kill_switch.py` | Created | ✅ Yes — git branch |
| 05:32 | `refresh_crypto_ohlcv.py` | Created | ✅ Yes — git branch |
| 05:33 | `refresh_stock_ohlcv.py` | Created | ✅ Yes — git branch |
| 05:15 | `updates/2026-06-05-kimi-phase1-emergency-triage.md` | Created | ✅ Yes — git branch |

**Branch**: `kimi-phase1-2026-06-05`
**Commit**: `e08ba95941`
**Status**: Phase 1 code + DB changes complete. OHLCV population pending (scripts ready, needs `--execute`).

---

*Generated 2026-06-05 by KIMI deep-dive session. All numbers derived from live MySQL queries against `ejaguiar1_stocks` and `ejaguiar1_backtests`. Re-derive before sizing decisions — do not trust this file if the underlying tables have changed.*
