# Baby Strategies + Alpha Engine Status by Asset Class — 2026-05-31

Read-only audit. Sources:
- `baby_strategies/*.py` (215 .py defs; 284 total entries including bundles + .meta.json)
- `battleground/data/closed_picks.json` (forward paper ledger)
- `reports/baby_dsr_scan_20260517T195643Z.md` (last scan, 14 days stale)
- `alpha_engine/data/*.json` (per-class feeds; latest_ts walked from content, not mtime)
- `alpha_engine/data/feed_health_report.json` (last refresh 2026-05-25 20:29Z → 6.1 days stale)
- `audit_dashboard/data/dashboard_data.json::data_freshness` (last_alpha_scan 0.0h)

## Hatch gate (baby strategies)

From `tools/baby_dsr_scanner.py`:
- `MIN_TRADES = 10` → DSR eligibility floor
- `MIN_N_WIRE = 100` → wire-to-production floor
- `DSR ≥ 0.95` → statistical-edge threshold (with nb_trials=213 haircut)

## Baby ledger reality

| Metric | Value |
|---|---|
| Baby strategy .py files | 215 |
| Distinct strategies with ≥1 closed forward pick | **6** |
| Strategies with **zero** forward picks | **209** (97.2%) |
| Strategies n≥10 (DSR-eligible) | 4 (down from 5 in 2026-05-17 scan — n shrank for `multi_period_rsi_confluence_eth`) |
| Strategies n≥100 (wire-ready) | **0** |
| Total closed forward picks | 123 (was 126 on 2026-05-17 — net -3) |

### Active baby strategies (per current `closed_picks.json`)

| strategy | n | WR% | PF | Class |
|---|---|---|---|---|
| crypto_liquidity_wick_reversal_v1 | 43 | 58.1 | 1.50 | CRYPTO |
| atr_percentile_gate | 29 | 58.6 | 1.10 | CRYPTO |
| multi_period_rsi_confluence_eth | 27 | 44.4 | 0.85 | CRYPTO |
| drawdown_recovery_rsi_eth | 14 | 64.3 | 5.98 | CRYPTO |
| drawdown_recovery_rsi_sol | 6 | 66.7 | 8.57 | CRYPTO (sub-DSR) |
| drawdown_recovery_rsi_xrp | 4 | 75.0 | 3.35 | CRYPTO (sub-DSR) |

**100% of forward-emitting baby strategies are CRYPTO.** EQUITY/FOREX/COMMODITY/ETF/BOND babies emit **zero** forward picks despite ~209 dormant strategy defs.

### Hatch gate growth velocity

Between 2026-05-17 and 2026-05-31 (14 days):
- net closed picks: +0 (actually -3, some strategies pruned)
- new DSR-eligible: 0
- new wire-ready: 0
- **Velocity = 0**. At this rate the n=100 wire-ready gate is **unreachable**.

Root cause = the upstream `baby-strat-forward-paper` workflow (the only path that ingests 215 strategies into `closed_picks.json`) is either not running or only sampling ~6 strategies. **209 strategies are NOT being backtested or forward-evaluated at all.**

## Alpha engine data-feed status by class

Walked `created_at|generated_at|signal_ts|updated_at|entry_time|date|release_date` keys inside each JSON, recorded MAX timestamp, computed age.

| Class | Feed | Content age | Status |
|---|---|---|---|
| **CRYPTO** | active_picks.json | 0.1h | FRESH |
| | tsmom/rocket/volatile_alt/short_dominant | 0.7–0.8h | FRESH |
| | cot_btc_latest.json | mtime 145.8h (no internal ts) | **STALE >72h** |
| **EQUITY** | equity_rsi_divergence_backtest.json | mtime 145.8h | **STALE >72h** |
| | equity_inverse_paper_picks.json (151B = empty array) | 145.8h | **STALE + EMPTY** |
| | equity_bb_zscore_mr_compliance_test.json | 145.8h | **STALE >72h** |
| **FOREX** | forex_backtest_results.json | content **1990h** (2026-03-10) | **STALE 83 days** |
| | forex_deep_audit.json | mtime 145.8h | **STALE >72h** |
| | forex_carry_ppp_compliance_test.json | 145.8h | **STALE >72h** |
| **COMMODITY** | commodity_active_picks.json | **2 bytes = `[]`** | **DEAD / EMPTY** |
| | joint_filtered_commodity_lean_2026-04-04.json | 145.8h | **STALE >72h** (dated 2026-04-04) |
| **ETF** | active_picks_etf.json / etf_decay_picks.json / etf_sector_picks.json | 3.7h | FRESH |
| | leveraged_etf_backtest.json | 1373.7h (2026-04-04) | **STALE 57 days** |
| **BOND** | active_picks_bond.json | 55.2h (2026-05-29) | **STALE >48h** |
| stock_forex_prices.json (shared px feed used by EQ/FX/COMM) | 0.6h | FRESH (prices live; backtest/audit DOWNSTREAM is stale) |

`stock_forex_prices.json` proves the underlying yfinance price feed is healthy — but the per-class **backtest + audit + paper-pick** files that consume it are all 145.8h+ stale. The downstream consumers stopped running.

`alpha_engine/data/feed_health_report.json` itself last refreshed 2026-05-25 20:29Z (6.1 days stale) — the **feed-health monitor is also stale**, hiding the fact that EQUITY/FOREX/COMMODITY/BOND consumers froze around 2026-05-25. This contradicts the dashboard's `data_freshness.last_alpha_scan = 0.0h` — that timestamp tracks CRYPTO scanning only; non-crypto branches are NOT covered by it.

## By-asset-class summary

### CRYPTO
- **Baby**: 6 strategies emitting, 4 DSR-eligible, 0 wire-ready. Top candidate `crypto_liquidity_wick_reversal_v1` n=43 WR 58% PF 1.50 — needs n=100 (57 more picks) to wire.
- **Alpha engine feeds**: FRESH (active_picks/tsmom/rocket/volatile_alt all <1h).
- **Stale**: `cot_btc_latest.json` 145.8h (CoT BTC release feed frozen).
- **Unblock**: (a) raise emission rate on the 4 DSR-eligible babies via lower confidence-threshold paper mode; (b) restart `cot_btc_latest` writer.

### EQUITY
- **Baby**: 0 forward picks. 209 dormant baby defs include many equity candidates (alpha_arena_strategies, equity-tagged variants). None are being scanned.
- **Alpha engine feeds**: ALL stale 145.8h. `equity_inverse_paper_picks.json` is **empty (151B)**.
- **Unblock**: restart `equity_*` scanners (last successful run ~2026-05-25 20:29Z). `tools/equity_baby_strategies_backtest.py` exists and produced a complete backtest on 2026-05-17 (`equity_vix_regime_momentum` n=604 WR 40.6 PF 1.03, `equity_sector_rotation_momentum` see file) — but never wired to forward-paper.

### FOREX
- **Baby**: 0 forward picks. ≥5 FX-prefixed baby defs exist (forex_*.py).
- **Alpha engine feeds**: `forex_backtest_results.json` content from **2026-03-10 (83 days stale)**. Compliance test + deep audit both 145.8h stale.
- **Unblock**: FOREX baby workflow has not run in 12 weeks. Re-trigger `tools/forex_baby_*.py` (if exists) or wire `baby_strategies/forex_*.py` into `battleground/` paper loop.

### COMMODITY
- **Baby**: 0 forward picks. `bond_yield_curve_momentum.py`, `cot_paper_pilot.py`, joint_filtered commodity bundles exist as defs.
- **Alpha engine feeds**: `commodity_active_picks.json` is **2 bytes (empty `[]`)** — generator wrote then nothing emitted. `joint_filtered_commodity_lean_*.json` dated 2026-04-04 (57 days stale).
- **Unblock**: HIGHEST PRIORITY for hatch — class shows worst money-ready (PF 0.31 / WR 11%). Must restart `tools/commodity_*` writers and re-run `commodity_baby_strategies_backtest.py` (likely missing — only equity version found).

### ETF
- **Baby**: 0 forward picks. `etf_decay_shorts.py` + Faber rotation present.
- **Alpha engine feeds**: live picks FRESH (3.7h). `leveraged_etf_backtest.json` is **57 days stale**.
- **Unblock**: refresh leveraged_etf backtest; expand ETF baby def coverage.

### BOND
- **Baby**: 0 forward picks. `bond_yield_curve_momentum.py` exists.
- **Alpha engine feeds**: `active_picks_bond.json` 55.2h stale (last 2026-05-29 14:55).
- **Unblock**: restart bond writer (~48h drift suggests a daily cron that missed last 2 days).

## Top blockers ranked

| Rank | Blocker | Impact |
|---|---|---|
| **#1** | `baby-strat-forward-paper` workflow only emits picks for 6 of 215 babies — **209 babies (97%) never get a forward trade and therefore never approach the n=100 hatch gate** | Money-Maker Goal #1 cannot progress on edge breadth |
| #2 | EQUITY/FOREX/COMMODITY/BOND alpha-engine consumers frozen since ~2026-05-25 (145.8h) | 4 of 6 asset classes have **no live picks** at all |
| #3 | `commodity_active_picks.json` is empty array; `forex_backtest_results.json` from 2026-03-10 | The two worst-PF classes (COMMODITY 0.31, FOREX 0.55) cannot even feed mutation analyses |
| #4 | `feed_health_report.json` itself 6.1 days stale → no automated alerting that classes are dead | Operator believes pipeline is healthy (dashboard says 0.0h) when 4/6 classes are dark |

## Recommendations (no code changes per RULES)

1. Re-run `python tools/baby_dsr_scanner.py` (it is read-only) to refresh the 2026-05-17 verdict — verify the negative-velocity observation above.
2. Investigate why the `baby-strat-forward-paper` workflow only samples 6 of 215 strategies. Suspect causes: (a) strategy registry filter, (b) per-strategy emit caps, (c) the workflow never iterates beyond a hardcoded shortlist.
3. Restart EQUITY/FOREX/COMMODITY/BOND alpha-engine writers (or identify which cron broke on 2026-05-25 20:29Z when `feed_health_report.json` last refreshed).
4. Add `feed_health_report.json` age to dashboard's stale-warning logic — currently `data_freshness.stale_warning=false` while half the asset classes are dark.

## Headline numbers

- baby_stuck = **209/215 = 97.2% dormant; 0 wire-ready**
- alpha_stale_feeds = **9 of 18 inspected feeds stale >48h** (EQUITY 3, FOREX 3, COMMODITY 2, BOND 1; plus dead commodity_active_picks + 1990h forex_backtest)
- classes_affected = **EQUITY, FOREX, COMMODITY, BOND** (CRYPTO + ETF live picks fresh)
- top_blocker = **baby-strat-forward-paper workflow emits for only 6/215 strategies → hatch gate unreachable at current velocity**

— peer_claude, 2026-05-31
