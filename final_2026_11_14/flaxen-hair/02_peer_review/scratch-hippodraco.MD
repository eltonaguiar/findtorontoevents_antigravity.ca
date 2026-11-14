# scratch-hippodraco — AI/ML, Asset-Class, PnL & Database Audit

**Date:** 2026-11-14 ~16:04–16:10Z · **Worktree:** `scratch-hippodraco` · **Mode:** read-only audit (no code fixes applied, no scanners run)
**Evidence:** live `dashboard_data.json` fetched 16:05Z from all 3 sites (byte-identical MD5 `d19f4587…`, 25.1 MB, generated `2026-11-14T14:30:07Z`), live MySQL (`mysql.50webs.com` via `tools/db_env.py`, **no secret values printed/copied** — `~/dbpasses.txt` checked by key-name only and never read into this report), repo code review.
**Not run (per AGENTS.md mandate):** `check_active_picks.py`, `alpha_engine/smart_picks_engine.py`.

---

## 1. Executive verdict

**FAIL — headline PnL is not trustworthy and must not be quoted externally.**

1. **PnL is stored in two different units in the same column.** In MySQL `at_signal_outcomes`, 17,632 rows store `pnl_pct` as percent (e.g. `-4.096`) and **6,306 rows as a fraction (e.g. `-0.0410` for the same trade)**. Any SUM/PF/WR downstream mixes them 100×.
2. **Resolution stalled ~7.5 h before the dashboard was built.** Dashboard generated 14:30Z, but `trading_picks` resolver, `at_signal_outcomes.closed_at` and `intrabar_resolved_at` all last moved **08:21–08:50Z** (YELLOW in the freshness guardian, run live during this audit). The dashboard claims `stale_warning: false`.
3. **90,588 picks sit `OPEN` in MySQL** — 86,064 older than 7 days, only 41 created in the last 2 h. The resolver/expiry lane is not draining the backlog; it resolves ~5–7 rows/day at current rate.
4. **Three different "active pick" counts are published simultaneously:** `picks.active = 20`, `performance.by_asset_class` active sum = **158**, `picks.active_raw = 4,148` (of which **3,377 are already `EXPIRED`**). With 0 smart picks everywhere, `smartCount = 0` in every asset class.
5. **No asset class is money-ready on the honest (intrabar) lane** — CRYPTO PF 0.92, EQUITY 0.94, FOREX 0.66, ETF 0.02, BOND 0.39 (all `NOT_READY`/`INSUFFICIENT_DATA`). The daily-bar lane that flatters ETF (PF 1.84 vs intrabar 0.02 — an **~85× inflation**) is the one feeding most visible stats.
6. **Mutual funds do not exist as an asset class.** The `mf_*`/`mf2_*` MySQL tables are a frozen side system: NAV history ends **2026-02-06 / 2026-03-27**, last tracked pick **2026-02-15**. Anything labelled "mutual fund" in the product is unused legacy schema. Bonds are likewise bond-**ETF proxies** (TLT/HYG only in closed picks), with BOND `thresholdPass: true` vacuously because `minTrades = 0`.

**What is healthy:** live dashboard JSON is fresh on all 3 sites (≤1.6 h, identical), displayed `picks.active` (20) is internally clean (0 PnL-sign errors on recomputation, 0 inverted TP/SL, median age 2.2 h), `status` values in `trading_picks` are 100% canonical, and the dashboard now carries honest `money_ready_verdicts`/`integrity_excluded` disclosures. The failures are in the ledgers underneath and in stale ML artifacts, not in the page shell.

---

## 2. What was checked

| Surface | Method |
|---|---|
| AI/ML algorithms (all asset classes) | Code review: `alpha_engine/` (config, asset_class, forward/walkforward validators, benchmark_closed_ledger), `ml_gatekeeper/`, `ml_consensus/`, `ml_crypto_predictor/`, `claude_gainer_ml/`, `crypto_gainer_ml/`, `empirical_bayes_scorer.py`, `lightgbm_ensemble.py`, `model_health_agent.py` |
| Stats DB per asset class | Live payload sections: `asset_class_summary`, `performance.by_asset_class`, `money_ready_verdicts`, `walkforward`, `readiness`, `ml_health`, `regime_validation`, `smart_picks_feed`, `leaderboard` (1,004 rows), `backtest_vs_forward` (255), `hf_stats`, `slippage_validation` (198 strategies) |
| `dbpasses.txt` + databases | Key-name inventory only (70 labelled entries, values never output). Live read-only queries against `ejaguiar1_stocks` (`trading_picks` 46 k rows live estimate, `at_signal_outcomes` 50,735, `mf_*`, `etf_daily_ohlcv`) and `ejaguiar1_backtests` (34.6 M `bt_backtest_trades`); ran `tools/db_freshness_check.py` live |
| PnL cross-reference | Recomputed `(exit−entry)/entry×100×(SHORT?−1:+1)` for every row of `picks.active`, `picks.active_raw`, `picks.recent_closed` (3,500) and in SQL for both MySQL ledgers; per-class WR/PF/expectancy recomputed and compared vs published |
| Every column | Null/zero/empty rate, distinct values, TP/SL-vs-direction geometry, status-vs-PnL-sign, timestamp age distribution for all three pick arrays (full table §5) |

---

## 3. Findings — P0 (PnL is wrong or unverifiable)

### P0-1 · Mixed PnL units in `at_signal_outcomes.pnl_pct` (fraction vs percent)
SQL ratio test on 24.4 k rows with a real price move:

| Stored unit | Rows | Example |
|---|---:|---|
| percent (1×) | 17,632 | ETHUSDT `pnl_pct=-4.096`, calc `-4.096` ✓ |
| **fraction (0.01×)** | **6,306** | QQQ `-0.0105` vs calc `-1.051`; AAPL `0.0151` vs `1.514` |
| other/neither | 453 | — |

Total **5,400 of ~25 k checkable rows mismatch recomputed PnL by >0.5 pp** (715 by >5 pp, 117 by >20 pp). `trading_picks` has the same disease (3,543 mismatches; e.g. INJ-USD stored `0.0395` for a +3.95% move). Dashboard generator "heals" this at ingest with a `|pnl| < 0.10 → ×100` fraction guess (`audit_trail/dashboard_generator.py:8065-8072`) — which also converts a genuine +0.08 % trade into +8 %. **Fix:** add `pnl_unit` provenance at write time (resolver `audit_trail/universal_pick_resolver.py:286-306`), backfill by recomputing from entry/exit, and drop the ingest ×100 heuristic.

### P0-2 · Extreme/garbage PnL values reach stats
COMMODITY `MAX(ABS(pnl_pct)) = 999,999.9999` in `at_signal_outcomes` (class avg |pnl| = 1,985 %). CRYPTO max 18,611 %. Generator/resolver clamp inconsistently (crypto [−99,+500], resolver ±100, generator ingest via `pnl_ingest_sanity.py:12-14`, headline PF cap ±500, rolling-100 ±10, frontend nulls >100 in one path and >500 in another) — the same trade contributes different numbers to the row, the PF, the headline and the screen. **Fix:** one shared clamp module; reject `|pnl| > asset-class bound` at the resolver write, not at display.

### P0-3 · 90,588 zombie OPEN picks; resolver throughput ≈ 0
`trading_picks`: OPEN 90,567 + ACTIVE 21; created-by-month shows continuous accrual since 2026-06 (14–19 k/month) with almost no drain. Only 41 OPEN rows are <2 h old; 72,963 are >30 days. Live freshness run: `resolver_outputs YELLOW 449.7 min`, `signal_outcomes YELLOW 464 min`, `intrabar_resolution YELLOW 435 min` — all frozen at ~08:2x–08:50Z while `live_picks` stays GREEN (37 min). `picks.active_raw` mirrors this: median age **2,055 h (86 d)**, 3,377 rows already `EXPIRED` still labelled active, 86.4 % with `current_price = 0`. **Fix:** batch-expire/drain the OPEN backlog per class with per-class max-hold, and alert when new accrual exceeds resolution for 2 consecutive days (see §8 fix 1–2).

### P0-4 · Daily-bar PnL materially inflates the honest intrabar truth
`money_ready_verdicts` proves the divergence against itself: ETF daily PF 1.84 / WR 73% vs intrabar PF **0.02** / WR 2.2%; EQUITY daily PF 1.30 vs intrabar 0.94; COMMODITY daily PF 0.17 vs intrabar 1.03 — the two lanes do not even agree on sign of edge per class. TP-before-SL same-bar assumption (`alpha_engine/forward_validator.py:1281-1302`) inflates daily WR. **Fix:** promote OHLC intrabar resolution to primary (TP-before-SL where unresolvable), label daily-bar stats "upper bound", and do not display daily PF without the intrabar PF beside it.

### P0-5 · Stale ML / validation artifacts presented as current
| Artifact | Timestamp in live payload / file | Age at audit |
|---|---|---:|
| `walkforward.by_class` | `2026-04-15T17:19Z` | **212 days** |
| `ml_health` Claude Gainer ML | `2026-05-25T17:04Z` (cv_auc 0.6877, version 1.0.245, status `active`) | 173 days |
| `ml_crypto_predictor/models/training_results.json` | 2026-02-22 | 265 days |
| `hyro_pick_performance.json` (live URL) | 2026-11-08 (`generated_at`) | 6.5 days, served fresh-looking |
| `analyst_active_calls` / `analyst_leaderboard` | 2026-03-26 | 233 days |
| `data/score_thresholds.json` / local `data/walkforward_results.json` | 2026-04-13 | 215 days |
| `smart_picks_feed` | generated 12:57Z, `total_scored=0`, 0 picks | dead at build time |

ML Crypto Predictor is honestly marked `disabled` ("36.8% WR, -32% PnL"); Claude Gainer ML is not - it says `active` on a May model. **Fix:** `generated_at` + max-age budget per artifact; render STALE badge in payload when exceeded; never stamp `status: active` without a fresh training/eval record.

---

## 4. Per-asset-class scorecard (live, recomputed)

### 4.1 Published vs recomputed (`picks.recent_closed`, 3,500-row window)
| Class | Window n | Recomputed WR | Recomputed sumPnL | Recomputed PF | Published (`performance`) closed/PF | Intrabar truth (n / WR / PF) | Verdict |
|---|---:|---:|---:|---:|---|---|---|
| CRYPTO | 1,966 | 40.2% | -689.9 | **0.81** | 4,907 / 0.93 | 3,705 / 35.9% / 0.92 | NOT_READY, losing; full-ledger PF 0.93 flatters window |
| EQUITY (stocks) | 738 | 47.0% | +238.3 | **1.15** | 8 / 8.86 (!!) | 250 / 59.2% / 0.94 | Published PF 8.86 is on n=8; do not quote. NOT_READY |
| FOREX | 187 | 39.0% | -29.0 | **0.63** | 82 / 0.48 | 612 / 32.2% / 0.66 | NOT_READY, worst liquid class after BOND/ETF |
| COMMODITY | 7 | 42.9% | -4.2 | 0.60 | 0 / null | 229 / 40.2% / 1.03 | Only class with intrabar PF>1, but daily PF 0.17; WATCH, no position sizing yet |
| FUTURES | 0 | - | - | - | 0 / null | 52 / 42.3% / 1.09 | INSUFFICIENT_DATA; DB outcomes stale since 2026-10-31, trading_picks since 2026-11-04 |
| BOND | 35 | 37.1% | -7.7 | **0.59** | 3 / 0.06 | 26 / 7.7% / 0.39 | INSUFFICIENT_DATA and losing; published PF 0.06 vs window 0.59 proves non-reconciliation |
| ETF | 567 | 44.3% | +22.9 | 1.04 | 8 / 0.76 | 45 / 2.2% / **0.02** | Daily lane is fiction (see P0-4); INSUFFICIENT_DATA intraday truth |
| MUTUAL FUNDS | 0 | - | - | - | **class does not exist** | - | Phantom (sec. 4.3) |
| PENNY_STOCK / MEME | - | - | - | - | - | none / legacy_fallback | INSUFFICIENT_DATA, no intrabar ledger at all |

Overall headline (published): 16,126 closed, 7,914 valid unique (98 mirror duplicates removed, **7,567 integrity-excluded, 8,888 auto-expired excluded**), WR 41.8%, PF 0.94, expectancy -0.11, total PnL -62.65 (rolling-100 compound) vs -923.53 (raw sum) vs -99.0 (equal-weight compound) - three incompatible "totals" published side by side; `clean_metrics` concentration warning: 25.8% of PnL from BTCUSDT alone. Sharpe -1.31 ann., Sortino -3.12, Calmar -0.65, max DD 31.2%.

### 4.2 Coverage that contradicts the headline
- `regime_validation.data_coverage`: **21 of 16,126 closed picks have regime data (0.1%)**, 0 with alignment, active composition `with_regime_data = 0`. Yet `summary.regime_win_rates` publishes WRs (TRENDING_DOWN 13.8% n=29, etc.) and `smart_picks_feed.regime = NEUTRAL`, `readiness` says VIX 19.3 / LOW_VOL on a fresh snapshot. The "regime-aware" ML claims are unsupported by persisted data.
- `macro_context = {}`, `ta_baseline = {}` (empty objects still shipped), `bundles = []`, `audit_events = []`, `filter_events = []`, `extreme_conviction.total = 0`, `shadow_probation` disabled with 0 picks, `smart_picks_snapshot_summary` last batch 2026-11-11 with `batch_id: null`.
- `kill_switch` (12:10Z): 177 strategies, only 56 evaluated, 42 killed, 14 survivors - 121 strategies were never evaluated by the safety gate.
- `slippage_validation`: 76/198 strategies flagged, 38 CRITICAL (e.g. `forex_rsi2_mean_reversion` slippage = 48.5% of its PnL).
- `fwd_vs_bt_divergence` / `hf_decay_watchlist` / `backtest_vs_forward` (255 rows): e.g. `connors_rsi2` backtest WR 68.8% PF survivor verdict with `fwd_trades = 0` - backtest glory, zero forward evidence.

### 4.3 Asset-class definition bugs (code)
- **Mutual funds are phantom:** no class in `alpha_engine/asset_class.py:102-120` or `alpha_engine/config.py:1087-1134`; VFIAX/FXAIX-style tickers fall through to `equity` (`asset_class.py:259-260` default) with equity TP/SL/hold rules, no NAV/distribution/load/EOD-pricing treatment. MySQL `mf_*`/`mf2_*` (20+15 funds) frozen Feb-Mar 2026 (sec. 6).
- **"Bonds" are bond-ETF proxies:** BOND = TLT/IEF/HYG/etc. priced as equities (`alpha_engine/asset_class.py:28-35`, `alpha_engine/config.py:1035-1052`); coupon/yield/duration exists only in a sidecar QuantLib pricer (`alpha_engine/bond_pricer.py:142-177`) unused by pick PnL. Price-only PnL ignores distributions - material for BOND/ETF/dividend EQUITY.
- **BOND/FUTURES contradiction:** `alpha_engine/walkforward_validator.py:189-196` allows `ZN=F/ZB=F` as BOND, but `alpha_engine/asset_class.py:138-139` classifies any `=F` symbol as FUTURES first. Live DB agrees with COMMODITY for GC=F/SI=F/HE=F, which both paths can also claim.
- **Two divergent canonical classifiers** (`alpha_engine/asset_class.py:37-53` vs `alpha_engine/config.py:1020-1029,1087-1134`): IGIB/VCSH bond in one, ETF in the other; GLD/SLV/USO are ETF despite commodity exposure; `config.py:1127-1132` labels any 6-letter alpha string FOREX and any 1-5-letter string EQUITY. DB `trading_picks.category` proves it in production: `crypto` 39.8k vs `CRYPTO`, `equity` vs `EQUITY`, `bond` vs `BOND`, `meme` vs `MEMECOIN`, plus `index` 3,550 and empty 2,537.
- Explicit emitter `category` overrides symbol evidence (`alpha_engine/asset_class.py:236-237`) - a bond-tagged SPY is a "bond"; UNKNOWN copy-trader picks coerce to CRYPTO in the dashboard (`audit_trail/dashboard_generator.py:7900-7937`).
- Futures PnL is % of price, not contract-multiplier/margin P&L; no roll, funding (crypto perps), borrow, FX swap or commissions anywhere in the forward path (only 5-10bp TP/SL slippage, `alpha_engine/forward_validator.py:1278-1279,1374-1389`; the real cost model `alpha_engine/cost_model.py:61-73` is called by none of the validators/gatekeepers).

---

## 5. Every-column spot check (live payload, recomputed)

### 5.1 `picks.active` (displayed, n=20) - CLEAN with caveats
- 0 PnL mismatches vs `(current-entry)/entry` direction-aware; 0 sign flips; 0 inverted TP/SL; median age 2.2h, max 15h, 0 future timestamps.
- BUT: 19/20 have `pnl_pct` 0/null - 13 picks literally show `current_price == entry_price` (BTCUSDT 66,300.0, futures ES=F, all 10 ETFs) because the generator leaves the pick untouched when the price fetch fails (`audit_trail/dashboard_generator.py:1752-1755`) and the frontend then recomputes display PnL client-side (`audit_dashboard/template.html:4329,4457,4667` with inconsistent >100 vs >500 nulling caps). `exit_price`/`closed_at`/`resolved_at` are 100% null (correct for open), `entry_time` missing 15%, `ml_score` missing 20%, and ~40 columns are <50% populated (all `_conflict*/_dup*/va_cohort*/wf_*` internals - underscore fields leak into the public payload).
- Caveat: this cleanliness is gate-selected; it does not generalise to `active_raw`.

### 5.2 `picks.active_raw` (n=4,148) - FAIL
| Column | Finding |
|---|---|
| `status` | **3,377 EXPIRED**, 691 OPEN, 55 SL_HIT, 25 TP_HIT inside an "active" array |
| `current_price` | 86.4% zero/null; `pnl_pct` 92.4% zero/null; `score` 90.7% zero; `ml_score` 94.6% zero |
| `entry_price`/`take_profit`/`stop_loss` | 85 rows (2.0%) zero together (no geometry at all) |
| age | median 2,055h, p90 5,474h, max 6,420h; 2,943 rows >30d |
| PnL | 2 mismatches incl. NEARUSDT SHORT stored -99.0 vs recomputed -146.2 (capped); 256 exact zeros |
| TP/SL | 59 inverted vs direction |

### 5.3 `picks.recent_closed` (n=3,500 window) - arithmetic OK, ledger not
- 0 PnL mismatches >0.15pp on recomputation (the generator overwrites reported PnL from prices, `dashboard_generator.py:8059-8064` - which is why it reconciles here and not in MySQL), 0 missing entry/exit/TP/SL, exit reasons SL_HIT 1,451 / TP_HIT 884 / FORCE_CLOSED 622 / TIME_EXIT 516 / UNKNOWN 22.
- BUT: 48.3% missing `entry_time`, **`ml_score` 98.1% zero/null**, 42 TP/SL-inverted rows, 15 WON/LOST-vs-PnL-sign inconsistent, 11 exact-zero PnL, and this window is capped/reserved (`MAX_CLOSED_PICKS=3500`, generator:273-275,6948-7078) so it cannot reconcile with the 16,126-row headline by design. Per-class split: CRYPTO 1,966 / EQUITY 738 / ETF 567 / FOREX 187 / BOND 35 / COMMODITY 7 / FUTURES 0.

### 5.4 Individual columns (all arrays + summary)
| Column/field | Failure |
|---|---|
| `direction` | Silent LONG default when missing (generator:7797-7822, resolver:793-800); inverse: validator treats anything not exactly `BUY` as SHORT (`alpha_engine/forward_validator.py:1175,1192,1304`) and gatekeeper maps unknown direction to SHORT -1 (`ml_gatekeeper/gatekeeper.py:135`) - same row can be LONG in one lane and SHORT in another |
| `timestamp` vs `entry_time`/`signal_time` | `timestamp` is first-found of 17 keys incl. `last_checked`/`resolved_at` (generator:8159-8183); naive timestamps assumed UTC (up to 5h age error, generator:8185-8223), daily PnL bucketed by `timestamp[:10]` string slice (generator:14911) |
| `closed_at`/`resolved_at` | Always identical (16-key chain sets both to the same value, generator:8357-8390) - close vs resolve latency is unmeasurable |
| `status` vocabulary | Dashboard WON/LOST/FLAT/CLOSED/UNRESOLVED vs DB canonical TP_HIT/SL_HIT/LOST/EXPIRED/TIME_EXIT/ACTIVE/OPEN vs resolver CLOSED+exit_reason; `audit_sync.py:595` only accepts WON/LOST/EXPIRED, silently skipping TP_HIT/SL_HIT alpha trades - three ledgers that cannot reconcile |
| `exit_price` | For closed: can be back-derived from PnL (`entry*(1+-pnl/100)`), then PnL re-derived from exit - tautological; closed slimming strips `resolution_method` honesty tags (resolver:1482) |
| `pnl_pct` status edge | WON/LOST with pnl=0 gets fabricated +-0.01 sentinel (generator:7516-7539), landed in `flat_count` by the +-0.01 win threshold - status/count mismatch; `total_resolved` = wins+losses+flat mixes both |
| `forward_wr`/`strat_fwd_wr` | Scale ambiguity (fraction vs pct) fixed only in bundle code via `forward_metrics_compat.py:37-38` (<=1 -> x100); generator does not apply it, template does its own (template.html:1162) - display can be 100x off |
| `confidence` | `1<c<=100 -> c/100` heuristic (generator:8560-8567); a true 1.5% confidence becomes 0.015 |
| `score` family | 12+ score fields (`score, elite_score, ml_score, ml_composite_score, method_a_score, precursor_score, confluence_score, safety_score, trust_score...`); `max_safe_leverage` defaults to 2 stamped on picks that never specified leverage (generator:8461-8463) |
| `take_profit`/`stop_loss` | `tp_pct`/`sl_pct` (percents) accepted as absolute prices (generator:7827-7845); missing legs fabricated from ATR/class defaults (generator:8089-8131); resolver separately fabricates 3%/1.5% and clamps TP 2-4%, SL 1-2.5% (resolver:1391-1444) - dashboard TP/SL is not the strategy's TP/SL |
| `_metaWinProb, _source_score_breakdown, _dup*` | Internal fields published in the public JSON (generator:8452-8459) |
| Summary `total_pnl_pct` | Name suggests additive sum; is actually the last-100 compounded value (generator:16879); full-ledger EW compound admitted "fundamentally broken for N>1000" in a code comment (generator:14853-14862) yet still published |
| Price feeds | Generator equity: `stock_prices.json` cache with **no age check** -> yfinance -> FMP `apikey=demo` (generator:1505-1615), prices rounded to 2dp destroying penny/FX precision (`audit_trail/fetch_stock_prices.py:21-23`); crypto: Binance->CoinGecko (~120-symbol hardcoded map) -> **hardcoded XAG $33.50 / XAU $3050** fallback prices that fabricate PnL with no flag (generator:1215-1464) |

---

## 6. Databases checked (`dbpasses.txt` + live MySQL)

- **`dbpasses.txt` (file at repo-parent home, 18,338 bytes):** 70 labelled key entries; this audit used only the DB-env indirection in `tools/db_env.py` (`DB_PASS_STOCKS`/`DB_PASS_BACKTESTS` etc.), never printed a value, and stored none in this file. Hygiene flags for the owner: a token-shaped string appears in a label line and several November-dated keys exist - rotate any credential that has ever appeared in chat/transcripts (do not paste them to agents again; prefer per-DB env injection); `dbpasses.txt` remains a single point of compromise for FTP + all MySQL + LLM keys.
- **Freshness guardian run live (`tools/db_freshness_check.py`, exit 2 = RED overall):** `live_picks` GREEN 36.7 min (but that is `MAX(created_at)` over 90,588 OPEN rows - the count itself is the bug); `resolver_outputs` YELLOW 450 min; `signal_outcomes` YELLOW 464 min; `intrabar_resolution` YELLOW 436 min; `status_standardization` GREEN (0 non-canonical - genuinely good); `backtests` RED only because `MAX(imported_at)` over 34.6M rows times out (needs an index-sidecar - genuine P2, not proof backtests are stale).
- **`ejaguiar1_stocks.trading_picks`:** statuses OPEN 90,567 / TIME_EXIT 33,635 / TP_HIT 7,091 / LOST 5,621 / SL_HIT 3,874 / EXPIRED 2,391 / ACTIVE 21; **52,612 closed rows have pnl_pct=0** incl. 3,475 with `exit_price = entry_price` (`spot-flicker` closes); active nulls tiny (45 zero entry, 53 null TP/SL, 594 null `created_at` - those 594 also have NULL month in the OPEN age buckets); recent-30d closures per class show only **1,152 resolved rows in 30 days vs 14-19k new OPEN/month** - accrual outruns resolution ~400:1. Non-canonical exit_reason litter: `EXTREME_PNL_OUTLIER [was: TIME...`, `FORCE_CLOSED_TOXIC`, `RESOLVE_FAILED_MAX_RETRIES` etc. embedded in reason strings.
- **`ejaguiar1_stocks.at_signal_outcomes`:** 50,735 rows; per-class MAX(closed_at): CRYPTO/ETF 2026-11-14 (today, 08:21Z), EQUITY 11-13, FOREX 11-13, MEMECOIN 11-10, FUTURES 10-31, COMMODITY 10-22, BOND 11-10, UNKNOWN/blank-class 182+25 rows; 25,685 NULL `pnl_pct`, 16,153 NULL take_profit, 40,389 NULL... intrabar decisive (TP_HIT/SL_HIT) total only 5,159. `pnl_pct` chosen by class: FOREX/BOND/FUTURES rows are ~80-94% fraction-unit small values vs CRYPTO ~20% - the unit mix is emitter-dependent (sec. P0-1).
- **Backtests DB (`ejaguiar1_backtests`):** `bt_backtest_trades` est. 34.6M rows, `bt_backtest_runs` 285; freshness query times out on full-table MAX - add a `MAX(id)`-anchored check. No evidence backtests are stale; evidence the guardian cannot prove they are fresh.
- **Mutual funds (`mf_*`, `mf2_*`):** 20/15 funds; `mf_nav_history` MAX 2026-02-06 (5,000 rows); `mf2_nav_history` MAX 2026-03-27 (6,860); `mf2_tracked_picks` MAX created 2026-02-15; `mf2_category_perf`/`mf2_comparisons` empty. **Dead since Feb-Mar 2026.**
- **`etf_daily_ohlcv`:** 124,682 rows, MAX trade_date 2026-10-30 (15 days stale).
- Other live feed files at audit time: `hyro_pick_performance.json` generated 2026-11-08; `pick_funnel_snapshot.json` and `/data/smart_picks_feed.json` return 404 (the dashboard embeds its own copy, so the broken public URLs are invisible from the page).

---

## 7. ML/model defects (code, by severity)

**Critical/High**
1. **Lookahead in Claude Gainer ML:** today's `ath/atl/market_cap`, `is_yesterday_gainer`, `sector_momentum` used as features for every historical training day (`claude_gainer_ml/train_model.py:562-564,629-667`); on API failure it silently trains on synthetic pump-injected data and saves through the normal path (`:1080-1086`).
2. **Leakage features in the gatekeeper, opt-out not opt-in:** outcome-derived `forward_wr/strat_fwd_wr/eb_forward_wr/age_hours` retained unless `ML_GATE_DROP_LEAKAGE=1` (`ml_gatekeeper/gatekeeper.py:85-97,182-185`); per-class models train on the same dashboard window (`ml_gatekeeper/per_class_trainer.py:64-157`).
3. **No purge at train/test boundaries:** 12-bar/48-bar forward labels in the last train rows read test prices (`ml_crypto_predictor/train_base_models.py:74-87,115-117`; `production_engine.py:802-804`); censored samples default to `target=0` (marked losses, `:495-500`); scaler/LassoCV/MI/RFE fit on the full matrix (`ml_crypto_predictor/feature_selection.py:44-57,107-108,145-154`). TimeSeriesSplit exists in the crypto ensemble (`train_ensemble.py:179`) and the gatekeeper, but rows enter it unsorted in dashboard order (`gatekeeper.py:230-253`), so folds can contain future rows; isotonic calibration is fitted on OOF probs including never-validated first-fold 0.0 rows (`gatekeeper.py:305,345,403-406`).
4. **Benchmark harness is wrong where it matters most:** benchmark return always long, SHORT ledgers compared to a long SPY/BTC in the paired bootstrap (`alpha_engine/benchmark_closed_ledger.py:424-425,428`); BOND/FOREX/COMMODITY/FUTURES all benchmark to SPY (`:66-76`) so `pass_95` (`:448-449`) is meaningless for them; compounded return and benchmark return are computed over different row populations (`:367-378,450-452`); the sidecar (`audit_dashboard/benchmark_proof.html`, registry in AGENTS.md) is labelled "NOT MONEY-READY" but is deployed on all 3 sites from a manually regenerated JSON - re-verify it carries the 2026-10-19 MC fix.
5. **TP-before-SL assumption inflates WR:** same-bar TP+SL touches record TP first regardless of intraday path (`alpha_engine/forward_validator.py:1281-1302`; `crypto_gainer_ml/live_predictor.py:908-924`); SHORT branch lacks trailing-stop logic (`forward_validator.py:1304-1316`).
6. **`lightgbm_ensemble.py` is a placeholder presented as a model:** LightGBM never trained (commented `model.fit`), predictions are zeros, and zero defaults to SHORT (`lightgbm_ensemble.py:5-14,119,224-225,244,285-286`).

**Medium**
7. **Walk-forward is not walk-forward:** no model is refit per window; it re-averages realised PnL in overlapping folds (step 5 < test 10, double-counting trades), sorts timestamps lexicographically, drops `pnl==0` FLATs and caps +-100% before computing WR/PF/Sharpe (`alpha_engine/walkforward_validator.py:53,59-64,92,101-148`); per-class windows for BOND/FUTURES are train=3/test=2 yet publish OOS Sharpe (`:189-222`); Sharpe annualised by sqrt(252) as if one trade/day for every class/timeframe (`:340-348`), drawdown on a cumulative sum of percents. Same sqrt(252) habit in `model_health_agent.py:837-877`, which also uses `actuals` as both labels and prices, and in `forward_validator.py:1534,1541`.
8. **Multiple testing uncorrected:** per-strategy `p<0.05, n>=20` gates across 361 families + 285 baby/mutation strategies (normal-approx p, no FDR/DSR) in `walkforward_validator.py:369-383,425-445,457-573` and `forward_validator.py:1589-1607`; DSR/FDR modules exist (`alpha_engine/deflated_sharpe.py`, `anti_overfit_gate.py`) but are never invoked; `benchmark_closed_ledger.py:502-523` counts per-ledger `pass_95` with a shared seed and no cross-ledger correction. Approx **260 PF>1.5 "winners" are expected by chance alone** at this family count.
9. **Consensus backtest is in-sample:** `SOURCE_QUALITY` derived from the same closed picks it is backtested on; group members re-counted pick-by-pick, undoing the one-event-per-group fix; cum-PnL is a simple sum of percents (`ml_consensus/consensus.py:44-57,221-306`). Its own report (2026-11-12): consensus WR 44.6% (+1.93pp lift), cum PnL -7.35%.
10. **Empirical Bayes has no as-of cutoff and triple-counts:** scorer ingests all closed trades with no timestamp relative to the pick scored (future leakage retrospectively); nested SSD/SS/strategy levels blended 0.5/0.3/0.2 double-count the same trades; zero-PnL trades count as non-wins in the denominator (`empirical_bayes_scorer.py:38-65,121-162`).
11. **Training universe is only the hot window:** validators/gatekeeper/consensus read only `recent_closed` (500-3,500 rows), so older regimes vanish; documented post-filter n: COMMODITY ~=27, BOND ~=12 (`walkforward_validator.py:201-216`). Gatekeeper report (2026-11-01, n=3,500): fold-1 AUC 0.571/F1 0.264 - near-coin-flip, honestly reported in the file, not surfaced in the payload. Absolute price-level features (EMA/SMA/BB raw levels) make crypto models non-stationary (`train_base_models.py:37-57`).
12. **Costs absent:** see sec. 4.3 (futures/FX funding/roll/borrow, dividends). With FOREX expectancy around -0.34%/trade and flagged slippage up to 48% of PnL, cost omission flips borderline classes' sign.

Also noted: `data_freshness` in the payload is file-mtime/scan-time based only (generator:3187-3230) and resolves to `stale_warning=true` on any exception; regime fields needed at entry (`consensus_regime`, `regime_alignment`) are only added to active picks - historical closed picks can never recover coverage (payload's own `enrichment_note` admits this).

---

## 8. Proposed fixes (ordered, no code changed in this audit)

**P0 - stop the bleeding (this week)**
1. Resolver throughput: drain the 90,588 OPEN backlog - batch-resolve by asset class with per-class max-hold (the auto-expire already exists but writes into `active_raw` at >5762h - i.e. after 240 days); write expiry outcomes into the closed ledger or delete with a tombstone; alert when OPEN growth exceeds resolution for 2 consecutive days.
2. Kill the stale-green lie: surface the freshness guardian's YELLOW/RED inside `dashboard_data.json` (copy `last_resolved_at` per lane into `data_freshness`); do not publish a build whose resolver lane is >6h stale without a visible badge.
3. PnL unit contract: resolver writes `pnl_pct` as percent only, plus `pnl_source` (intrabar/daily/close-approx); backfill `at_signal_outcomes`/`trading_picks` by recomputing from entry/exit where both exist (5,400+3,543 rows); remove the generator's |pnl|<0.10 x100 guess and fail validation on unit ambiguity.
4. One clamp function shared by resolver/generator/frontend; reject |pnl| beyond class bounds at write time (would have stopped the 999,999% COMMODITY rows).
5. Remove/normalise `active_raw` from the public payload (or emit only OPEN/ACTIVE rows and count accordingly); reconcile the three active counts to one - `picks.active`.

**P1 - make the per-class stats honest (next 2 weeks)**
6. Intrabar-primary PF/WR per class on the dashboard cards (daily shown as "upper bound"); ETF is the test case (PF 0.02 vs 1.84).
7. Cross-check `EQUITY`/`BOND` published rows against the same ledger as `recent_closed` (PF 8.86-vs-1.15 / 0.06-vs-0.59 is a dataflow bug, not noise) - one stats module fed by one canonical closed table.
8. Wire `alpha_engine/cost_model.py` into forward_validator/walkforward/benchmark (commissions, spread, funding/borrow, roll, distributions for BOND/ETF/dividend EQUITY, futures multiplier economics).
9. Fix `benchmark_closed_ledger`: direction-aware benchmark returns, per-class benchmarks (TLT/IEF for BOND, DXY/basket for FOREX, futures continuous contracts), matched populations, per-ledger seeds + FDR across ledgers.
10. Unify the two asset classifiers into one (`alpha_engine/asset_class.py` authoritative), resolve the `=F`/BOND contradiction, plural-case-normalise DB `category` at write, add `MUTUAL_FUNDS` properly (NAV EOD pricing, no intraday TP/SL) or remove the mutual-fund surface/tables from the product.
11. Rename/retire zombie artifacts: stamp `walkforward`/`ml_health`/analyst/hyro JSONs with max-age and STALE flags; delete or quarantine the frozen `mf_*`/`mf2_*` schema and the 404'd public JSON URLs.

**P2 - ML hygiene (next month)**
12. Gatekeeper: default `ML_GATE_DROP_LEAKAGE=1` (drop `forward_wr/strat_fwd_wr/eb_forward_wr/age_hours` from features), chronological sort before TimeSeriesSplit, exclude unvalidated fold-0 rows from calibration.
13. Claude Gainer: point-in-time feature snapshots (ATH/mcap as of day i), fail-closed (no synthetic fallback to production save).
14. Real walk-forward (refit per fold, embargo/purge >= label horizon, non-overlapping test folds); suppress OOS Sharpe for n<30 folds; DSR/FDR applied as the promotion gate; fees after costs.
15. Retire or repair `lightgbm_ensemble.py` (placeholder zeros->SHORT must never reach a signal path); version-pin + date every served model in `ml_health`.

**P3 - contract tests**
16. CI: recomputed-PnL vs stored-PnL tolerance check per class (would have caught P0-1/P0-2), active-count reconciliation check, artifact-age budget check, `MAX()-by-id` freshness check for the 34M-row backtest table.

---

## 9. Limitations of this audit

- MySQL `table_rows` (information_schema) are InnoDB estimates; exact counts quoted come from `GROUP BY`/`COUNT` queries where run. Two full-table MAX queries on `bt_backtest_trades` timed out (reported, not bypassed).
- `recent_closed` is a 3,500-row capped window; full-ledger per-class recomputation was done in SQL (30-day and PF windows) but a full 16k-row independent re-derivation requires the canonical closed export - recommended as the P1 stats-module work.
- Price accuracy was verified arithmetically (stored vs recomputed from stored prices); whether stored entry/exit prices match exchange prints at the timestamp needs a market-data replay (the generator's hardcoded XAU/XAG fallback and demo-API lanes make this likely to fail for metals/FX - flagged, not proven here).
- No secrets are reproduced anywhere in this report; `dbpasses.txt` contents were not copied, and database access used the repo's own env indirection only.

*Report: `scratch-hippodraco.MD` (worktree `scratch-hippodraco`). Audit only - no production code, dashboards, or database rows were modified.*


---

## Appendix A — Peer-merge delta (2026-11-14 ~17:50–18:10Z, second review round)

Independent folder-by-folder re-review of every peer modified today (subagent-reviewed + firsthand verification). What changes vs the original audit:

### A.1 IMPLEMENTED by peers — our proposal already shipped (verify before duplicating)
- **QW-CRYPTO-3b is DONE upstream:** `finpredict-v3` commit `d8c8dd25581` (17:49Z) flips `ml_gatekeeper/gatekeeper.py:_drop_leakage_enabled()` to ON-by-default with `tests/test_gatekeeper_leakage_default.py` (4 tests). NOTE: a peer reports this commit is now an ancestor of `origin/main` — a production code change made during a read-only audit; flag for coordinator sign-off and verify ancestry before relying on it. The retrain-to-honest-AUC half of QW-CRYPTO-3b is still outstanding.
- **finpredict (v1) P0 truth fixes** (`updates/2026-11-14-p0-truth-fixes.md`, branch `fix/audit-p0-truth`): (1) FX `KeyError: 'LONG'` in `alpha_engine/scanner.py` direction bucketing — same direction-encoding trap family as our §7; (2) `summary_picks.json` WR>100% (INDEX 1141%, FUTURES 364%) from wins/losses counted over non-terminal rows — **new finding, adopted as QW-ALL-10**; (3) `None→0.0` entry coercion in `prediction_market_consensus.py` removed. These are real fixes with smoke verification; treat as the implementation pattern to copy.

### A.2 NEW findings adopted (were missed here)
| Finding | Source | Disposition |
|---|---|---|
| `live_picks.db` verified: 129/129 stale (all `last_updated` 2026-05-25, **173d**; 41 rows entered 2026-03-19 ≈240d); **11 strict / 8 material PnL sign flips**; 136× REGISTERED, 0 resolutions; `audit_trail.db` 8-9 tables empty | childlike (re-verified firsthand in main-repo DB) | Adopt as P1 SQLite-lane finding; correct our "peer-only, unverified" label → VERIFIED with corrected counts |
| Ghost cohorts: **22,947 duplicate/negligible rows** (MEMECOIN `meta_strategy` DOGEUSDT 3,569 rows at identical pnl 1.3226); `picks_now_track_record` 301/4,820 resolved (6.2%), 87.6% past TIME_EXIT | finpredict-v4 `evidence_db_health.json` (2026-11-14T14:13Z, fresh) | Adopt — extends P0-3 beyond the MySQL OPEN backlog |
| FOREX PR#6 block bypass: 2 live FOREX picks emitted by `non_crypto_consensus` evading `strategy_blocklist.py`; consensus inputs include retired `forex_rsi2_mean_reversion` | finpredict-v4 forex deep-dive | Adopt into FOREX.md — a "blocked" class is still emitting |
| AI-Challenge zombie registry: 5 crypto picks OPEN since 2026-03-15 (NEAR SHORT +143% through SL) separate from `active_raw` | finpredict-v4 market crossref | Adopt — third zombie store |
| CRYPTO RSI5070 shadow: n=430 PF net 1.113, CI-lb 0.916 < 1.15 gate → not promotable | finpredict-v4 crypto deep-dive | Adopt — no named crypto condition is promotable either |
| Actions health: 365 workflows, 28 last-run failures, ALPHA/Resolver/Crypto-Dispatch 5/5 bad; dashboard JS `dashboard_enhancements.js` malformed nested ternary **since 2026-10-04** deploying dead JS to all 3 sites (peer branch `fix/audit-js-syntax-and-deploy-guard` `ba1378cbfa9` adds `node --check` pre-FTP guard) | finpredict-v2 actions_deepdive GA1-GA4 + peer branch | Adopt — explains part of "empty fields" as frontend parse failure; confirm JS fix merges |
| FOREX date-only `entry_time` 105/277; COMMODITY generator uses crypto proxies; COMMODITY+FUTURES in `BLOCKED_ASSET_CLASSES`; MF output DOES exist untracked (`mutut_fund_rankings.json` 39KB, typo filename) + `alpha_engine/mutual_fund_ranker.py` untracked prototype absent from origin/main | finpredict-v2 REVIEW_SYNTHESIS | Adopt; MF file updates MUTUAL_FUNDS.md (untracked prototype ≠ coverage; retire still correct) |
| v2 statistics: policy-clean n=22,941 PF 0.2657 z=-23.60; N=658 families (≈33 false positives expected); PBO invalid; `summary_picks` WR>100% | finpredict-v2 | Adopt as corroborating statistics |

### A.3 REJECTED / corrected peer claims (do not propagate)
- **v4 stale-evidence recycling:** `evidence_pick_summary_stats.json` is 2026-05-25; every "dashboard vs raw-DB PF" number from it (CRYPTO 1.80-vs-0.371, EQUITY 5.56, Smart-Picks 91.7%/3-rows, FUTURES PF 131.6) is May data in a Nov archive. Same for "0 active / 26-day dashboard / DEAD" (read the Oct-19 local copy, not the live 14:30Z payload; its own fresh `evidence_db_health.json` contradicts it: active_count=21) and "`at_signal_outcomes` unresolved since Mar-04" (May-23 freshness file recycled; live = Nov-14 08:21Z). Baseline FAIL verdict unchanged; v4's freshness conclusions must carry date stamps or be struck.
- **v4 `proposed_fixes/` destructive items — RED-LINE:** literal `DELETE FROM trading_picks … MEMECOIN`, `UPDATE … TIME_EXIT→LOST, pnl_pct=0.0` (fabricates losses), unblock FUTURES/COMMODITY, invert ML confidence (based on numbers no evidence file contains), re-enable dashboard `push:` trigger. Also childlike proposed_fixes SQL targets a nonexistent top-level `asset_class` column (it is inside `metadata` JSON) → would no-op or hit wrong tables; MF stub scanner vetoed by all reviewers.
- **finpredict corrections to itself (adopted):** "61% spot-flicker" not reproducible (registry-wide 7.7%); June -1.4% superseded by live last-14d n=751 sum -333.2%; "37 active" was a May figure. Three-store framing (SQLite 129 / MySQL 90.5k / JSON) is the correct reconciliation model.
- **hilarious-seer stubs rewritten mid-review (17:52Z) and got shorter**; `db_fixes/` still empty; "2 files integrated / bonds_pnl_validator" still file-less → WEAK stands; use as corroboration only. **spice-hyena does not exist** in this workspace (no worktree/session) — nothing to review.
- **Childlike numeric corrections:** 129/129 (not 128/129), 173d (not 172d), WUSDT magnitude ≈2× off in its table (sign right, number wrong); `audit_trail.db` has `bt_backtest_runs=20, meta=1` (8 payload tables empty, not 9×0).

### A.4 Cross-review of THIS archive (finpredict-v3 PEER_REVIEW_R2)
v3's R2 review rates scratch-hippodraco **"most implementation-ready"** (verified file:line, effort, verify steps), adopts QW-ALL-1..9 as the implementation spine with v2 as reconciliation backbone, and flags our real weaknesses: (1) proposals only, uncommitted/unimplemented — correct, by design; (2) per-class numbers restate the parent audit without independent re-derivation — correct; (3) cross-class duplication (same-bar/freshness fixes recur) — partially fair, consolidated dependency note added to README; (4) hilarious "WEAK" rating should be carried as opinion — now labelled as such in PEER_REVIEW.md. Consensus across 6-9 peers: PnL-unit contract + NULL-tombstone drain are the two highest-value first fixes; 0/9 money-ready; no placeholder "solid" claims until a horizon harness passes.


### A.5 Final finpredict-family review (arrived after A.1-A.4; corrections to them)
1. **Correction to A.4:** the `PEER_REVIEW_R2` folder in finpredict-v3 is NOT empty - the consolidated/index/scratch/seer/v1/v2/v4 files exist and were read firsthand for A.4. The reviewer ranking it "reject (empty placeholder)" contradicts the on-disk content - carry A.4 (firsthand) over that ranking. A stale experimental variant of that folder may explain the discrepancy.
2. **Gatekeeper flip is NOT merge-safe yet (refines A.1):** the production bundle was trained WITH leakage (`leakage_dropped` stamped at `ml_gatekeeper/gatekeeper.py:448-450`), and the commit ships no retrained bundle - so default-on masking creates silent train/score skew in live scoring. Its A/B old-sleeve path (`:916,1007`) only *deletes* the env var for leakage_env_force=False, which under the new default now masks OLD too - the legacy-vs-clean comparison is broken. Merge only with: retrain + bundle re-stamp, explicit "0" for OLD sleeve, train/score parity test, and proper env-cleanup in the new tests (currently mutating os.environ). The direction is right; the merge as-is is not.
3. **finpredict P0 fixes - two adoption corrections:** the scanner fix defaults unknown directions to BUY, reproducing the silent-LONG-default defect family we flag elsewhere; adopt v2's OTHER-bucket + log-once variant instead. `tools/sync_summary_picks_json.py` fallback path `_from_local_json` still counts OPEN-with-pnl as resolved - fix that path before merging, don't rely on the min() clamp. The commit also sits on the finpredict worktree HEAD, not a clean `fix/audit-p0-truth` branch- re-cherry-pick per publish convention.
4. **Adopt verbatim:** v2 `MASTER_AUDIT.md` + GA1/GA2/GA4 (noting GA4 runtime p50 97.2min supersedes MASTER 84.5min; P0-3 Python-3.14 story downgraded to UNVERIFIED by GA1 itself); v3 `tools/pi_data_hygiene.py` (324 lines, read-only, 18 tests passing - not 11) as a CI *warn* gate; `pi_fundamental_ranker.py` as scaffold only (synthetic mock data, NO EDGE DETECTED is its honest output - no trading claim).
5. All four finpredict peers converge with the baseline verdict: FAIL, not money-ready; merge order per the reviewers: v1 cherry-pick (corrected) -> v3 hygiene warn-gate -> v2 canonical audit record (+ GA4 cron/timeout as separate CI PR) -> v4 raw-DB/SQLite findings corrected into master plan.
