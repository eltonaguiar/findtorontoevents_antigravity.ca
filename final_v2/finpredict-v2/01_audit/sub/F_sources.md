# Subagent F — Data-source / strategy authenticity audit

Audit time: **2026-11-14T16:12Z** · Repo (read-only): `.kilo/worktrees/finpredict-v2` · Live: `https://findtorontoevents.ca/audit`
Scope: whether each named source actually fetches live external data, requires keys, falls back to synthetic data, and what is actually surfaced/resolved in the live dashboard.

## VERDICT: **FAIL** (partial authenticity failure)

The raw market-data fetchers are mostly **REAL** (Kalshi, Polymarket Gamma/CLOB, Binance, Hyperliquid, Bybit, multi-asset Yahoo/CFTC). But the published source layer is not trustworthy end-to-end:

1. **Polymarket wallet/whale pipeline is dead**: Data API **v1 retired → HTTP 410**. Confirmed in CI log: `[WARN] HTTP 410 for https://data-api.polymarket.com/v1/leaderboard`, `Saved 0 trader profiles`, `Saved 0 live picks`.
2. **Polymarket reverse engine is real but emits 0 picks**: CI log `Polymarket strict filter kept 0/100 markets`, `Generated 0 Polymarket picks`.
3. **copy_trader_intel named system is "dead" in the dashboard** because its `active_picks.json` is gitignored (`**/data/active_picks.json`, `.gitignore:322`) and never deployed. Fresh per-venue data exists but is merged under `alpha_engine`/`multi_asset_copytrader`.
4. **`funding_rate_arb` and `btc_breakout` are hard-coded "ghost" systems** — fetched every hour but deliberately skipped by the dashboard (`audit_trail/dashboard_generator.py:4417-4431`, skip at `:8870`). The comment "never produced data files" is false: `funding_rate_picks.json` has 25 OPEN picks.
5. **HyroTrader is not a live execution source**: 7 picks are `pending_entry` with `entry_price=None`; journal `last_session_date=2026-04-08`; `n_closed=0`; several Hyro JSONs are weeks/months stale.
6. **`summary_picks.json` publishes arithmetically impossible win rates** (e.g. BOND 127.8%, INDEX 1141.2%, FUTURES 363.9%) because wins/losses use different, overlapping populations than the resolved denominator (root cause below).

Classification: **REAL** = calls a live external API and emits from it; **DEAD/BROKEN** = real code path but external API retired or file never deployed; **GHOST** = runs but is excluded from the dashboard; **UNVERIFIED/LIVE-NONE** = data real but no executed/actionable picks.

---

## Summary table (live dashboard snapshot `generated_at=2026-11-14T14:30:07Z`)

| Source | Classification | API endpoint | Key present | Live picks (active panel / active_raw) | Newest pick ts | Resolved outcomes | Evidence |
|---|---|---|---|---|---|---|---|
| **Kalshi MTF consensus** (`pm_kalshi_signals`) | **REAL** | `https://api.elections.kalshi.com/trade-api/v2` (public, no key) | Not required | **2 / 4** (XRP, BTC panel; +DOGE, SOL raw) | `2026-11-14T13:53:28.525051Z` | **0** | `alpha_engine/kalshi_signals.py:33,14`; `prediction_market_agents/kalshi_signal_agent.py:43`; dashboard `picks.active_raw` |
| Kalshi signals (alpha_engine path) | REAL but not surfaced | same Kalshi v2 | Not required | 0 attributed (different emitter) | CI log 13:51Z | 0 | CI log `Kalshi BTCUSDT (crypto): LONG (conf=0.61, 2/4 TFs)` |
| **Polymarket reverse signals** | REAL integration, **0 emitted** | `gamma-api.polymarket.com`, `clob.polymarket.com` | Not required | **0** (`polymarket_signals=empty`) | n/a | 0 | `alpha_engine/polymarket_signals.py:31-33,373,603`; CI log `kept 0/100 markets` |
| **Polymarket wallet/whale** | **DEAD (HTTP 410)** | `data-api.polymarket.com/v1/leaderboard`, `/positions` | Not required | 0 | n/a | 0 | `copy_trader_intel/polymarket_scraper.py:46,49`; `prediction_market_agents/polymarket_whale_tracker.py:43`; CI log `HTTP 410` |
| **prediction_market_consensus** | **REAL inputs; thin/duplicated output** | Kalshi + Polymarket + wallet (aggregator) | Not required | **0 panel / 6 raw = 3 unique** (dupes under `alpha_engine`) | `2026-11-14T13:54:51.499Z` | **1 WON (+2.45%), 2 SL_HIT (−1.76%, −1.57%)** | `alpha_engine/prediction_market_consensus.py:35-41,424,635`; dashboard raw |
| **copy_trader_intel** (named) | **DEAD in dashboard** | Hyperliquid `api.hyperliquid.xyz`, Bybit beehive, Bitget V2 (auth), etc. | Bitget/Dune/Nansen env set; CoinGlass unset | **0** | file not deployed | 1 win legacy | `dashboard_generator.py:4023-4025`; `.gitignore:322`; live system `status=dead` |
| **multi_asset_copytrader** | **REAL** | Yahoo Finance, CFTC Socrata, Myfxbook/IG HTML, Binance | Not required | **1 / 68** | `2026-11-14T13:06:02Z` | **21 W / 18 L** (39 closed) | `copy_trader_intel/multi_asset_copytrader_scraper.py:1-40`; live system `active`, wr=53.8 |
| Copy-trader per-venue scrapers | REAL, merged/tracked inconsistently | Hyperliquid (47,887 leaderboard rows live), Bybit, OKX, Bitget, CoinGlass fallbacks | see above | bybit 6 picks committed @15:25Z; 50 `copy_trader_intel` rows in `alpha_engine/data/active_picks.json` @16:06Z | `2026-11-14T16:06Z` (alpha file) | mixed | `copy_trader_intel/hyperliquid_scraper.py:29-30`; `copy_trader_intel/bitget_scraper.py:506` |
| **HyroTrader / hyro_*** | **UNVERIFIED / LIVE-NONE** | Binance mirrors + KuCoin via `hyro_backtest.fetch_candles` | Not required | **0 in dashboard** (0 `hyro` refs) | bridge `2026-11-14T14:22Z`; signal monitor `2026-04-12`; perf `2026-11-08` | **0 closed** (`n_closed=0`); account `last_session_date=2026-04-08` | `tools/hyro_quan_bridge.py:1-15,56`; live `hyrotrader_picks.json` all `pending_entry`, `entry_price=None` |
| **funding_rate_arb** | **REAL fetcher, GHOST-excluded** | `fapi.binance.com` etc. | Not required | **0 surfaced** (ghost) | artifact `2026-11-14T01:37Z`, 25 OPEN | 0 | `alpha_engine/funding_rate_arb.py:38,143`; `dashboard_generator.py:4053,4422,8870` |
| **btc_breakout** | **REAL fetcher, GHOST-excluded** | Binance/KuCoin/CryptoCompare/CoinGecko | Not required | **0 surfaced** (0 signals) | `2026-11-14T14:13:39Z` | 0 | `alpha_engine/btc_breakout_strategy.py:48,67,448`; `dashboard_generator.py:4054,4429` |
| **production_scanner** | **REAL orchestrator** | reads strategy/scan outputs; shared Binance funding failover | per underlying | n/a | n/a | n/a | `alpha_engine/production_scanner.py:95,1915,3840`; only 2 benign "mock/placeholder" comments at `:759,2722` |

No target file contained `random()` / `np.random` used to fabricate prices (only `MIN_WIN_RATE = 0.52 # slightly above random` and a `regime_random` feature name). Synthetic markers found are bounded: Bitget's `synthetic` fallback (position **direction defaulted to long**, entry from live Binance price, `bitget_scraper.py:496-510,808-819`), Myfxbook metal-FX cross-rate derivation (`myfxbook_scraper.py:279-298`), and Gains' hardcoded `PAIR_INDEX_MAP` fallback (symbol mapping only, `gains_scraper.py:90,233`).

---

## 1. Kalshi MTF consensus (deep dive)

**Where emitted.** Two independent implementations exist:
- `alpha_engine/kalshi_signals.py` — `get_kalshi_signals()` at `:467`, `generate_kalshi_picks()` at `:621`, writes `alpha_engine/data/kalshi_signals.json`.
- `prediction_market_agents/kalshi_signal_agent.py` — `scan_kalshi()` at `:411`, writes `prediction_market_agents/data/kalshi_signals.json`. **This is the emitter of the dashboard picks** (`source=kalshi_signal_agent`, `source_system=pm_kalshi_signals`).

**Is it real?** Yes.
- Public API, no key: `KALSHI_API_BASE = https://api.elections.kalshi.com/trade-api/v2` (`kalshi_signals.py:33`, doc `:14`).
- Live probe 16:07Z: `GET /events?series_ticker=KXBTC` → **HTTP 200**, 3 open events (`KXBTC-26NOV1412` strikes 17:00Z, `...1417`, `...2017`).
- `GET /markets?event_ticker=KXBTC-26NOV1412` → **HTTP 200, 188 active markets**, strikes ~63.6k–78.3k with `yes_ask_dollars` 0.01–0.18.
- CI log from the 13:14Z dashboard run shows real series iteration: `Analyzing Kalshi series KXBTC15M / KXBTC / KXBTCD / BTCD / ...`, then `Kalshi BTCUSDT (crypto): LONG (conf=0.61, 2/4 TFs)` at 13:51:56Z.

**Live counts / freshness (dashboard snapshot 14:30:07Z):**
- `picks.active`: 2 — XRPUSDT SHORT (conf 0.766), BTCUSDT SHORT (conf 0.673).
- `picks.active_raw`: 4 — adds DOGEUSDT LONG (conf 0.897), SOLUSDT LONG (conf 0.935).
- All timestamps `2026-11-14T13:53:28.525051+00:00`. Age at snapshot ≈ 37 min; at audit time ≈ 2h19m (cadence is 2-hourly PM agents + 30-min polymarket workflow, so acceptable).
- `picks.recent_closed`: **0** Kalshi rows. System row `pm_kalshi_signals: status=active, wins=0, losses=0, win_rate=0.0`. No Kalshi rows in `leaderboard` (1,004), `predictions_leaderboard` (222), or `backtest_vs_forward` (255). **Zero resolved outcomes.**

**Cross-check against public market data:**
- Pick DOGE LONG entry `0.06147`; Binance DOGE 14:00Z candle range `0.06100–0.06262` → inside.
- Pick SOL LONG entry `74.38`; Binance SOL 14:00Z range `73.71–75.56` → inside.
- Pick XRP SHORT entry `0.9842`; Binance XRP 13:00Z range `0.9866–0.9983`, 14:00Z close `0.9821` → consistent with ~13:53–14:00Z.
- Pick BTC SHORT entry `66300`; Binance BTC 14:00Z range `65802.73–66873.14` → inside. BTC now `65505` (16:06Z), so the SHORT is currently ~+2% in favour.
- Each pick has real TP/SL (`DOGE TP 0.06318378 / SL 0.06044378`, `reason: "Kalshi consensus: LONG DOGEUSDT (3/3 timeframes agree, net score: +0.32)"`).
- **Conclusion: not synthetic.** Entry prices track real spot and the Kalshi ladder is live. The dashboard shows `current_price == entry` / `pnl 0.0` on the Kalshi rows at 14:30Z even though price moved — a **resolver/snapshot lag**, not fabricated data.

**Caveats:**
- `prediction_market_agents/data/*_signals.json` is matched by `.gitignore:324` (`**/data/*_signals.json`) and is **not committed** (GitHub contents API 404; only `orchestrator_summary.json`, `pm_leadlag_report.json`, etc. are on `main`). The picks exist only inside the CI run and the deployed `dashboard_data.json`, so they cannot be re-audited from the repo.
- Kalshi contributes to the `consensus` panel while unresolved: SOL LONG consensus lists `pm_kalshi_signals` + `kalshi_mtf_consensus` among 10 systems at `avg_confidence 0.682 / VERY HIGH`. An untested source is being weighted alongside proven ones.

---

## 2. Polymarket

**Reverse-engineered signals (`alpha_engine/polymarket_signals.py`) — REAL but 0 output.**
- Endpoints: Gamma `https://gamma-api.polymarket.com` (`:31`), CLOB `https://clob.polymarket.com` (`:33`), Data API `:32`.
- Live probes: `gamma-api.polymarket.com/markets` → HTTP 200 with real markets (`Xi Jinping out before 2027?`, volume $17.3M, outcomePrices `["0.0165","0.9835"]`); `clob.polymarket.com/time` → HTTP 200.
- CI log 13:51Z: `Polymarket strict filter kept 0/100 markets` → `Generated 0 Polymarket probability signals`, `0 momentum signals`, `Saved 0 picks`.
- Live: `polymarket_signals` system `status=empty`, 0 active/closed, 0 leaderboard rows.

**Wallet / whale / copy-trade path — DEAD.**
- `copy_trader_intel/polymarket_scraper.py:46` `https://data-api.polymarket.com/v1/leaderboard`, `:48-49` `/positions`, `/closed-positions`.
- `prediction_market_agents/polymarket_whale_tracker.py:43` `https://data-api.polymarket.com/positions`.
- `alpha_engine/polymarket_signals.py:599` `DATA_API_BASE + "/v1/leaderboard"` (in `get_top_predictors`; not on the main flow).
- Live probe: `GET https://data-api.polymarket.com/v1/leaderboard?limit=3` → **HTTP 410** `{"error":"Data API v1 has been retired","migration":"https://data-api.polymarket.com/v2/"}`. `GET /positions?...` → **HTTP 410**.
- CI log 13:51:48Z: `[WARN] HTTP 410 for .../v1/leaderboard?limit=50`, `Polymarket leaderboard returned no rows`, `Saved 0 trader profiles`, `Saved 0 live picks`.
- v2 exists (`/v2/leaderboard` → HTTP 200, `data[].user_id/pnl/volume`), but the repo does not use it.
- Consequence: `pm_whale_signals=empty`, `copy_trader_intel/data/polymarket_picks.json = []`, `prediction_market_consensus.wallet_input = 0`.

---

## 3. prediction_market_consensus

- Aggregator: `alpha_engine/prediction_market_consensus.py`. Sources: wallet copy (`:35`), Polymarket reverse (`:36`), Kalshi (`:37`). Gate: `MIN_SOURCE_CATEGORIES = 2` (`:41`), enforced at `:424`.
- Live output (`alpha_engine/data/prediction_market_picks.json`, committed): `updated_at 2026-11-14T15:49:26Z`, `wallet_input=0`, `polymarket_input=1`, `kalshi_input=10`, **`pick_count=0`, `picks=[]`**.
- Yet the 14:30Z dashboard contains 3 unique PMC picks emitted 13:54:51Z: DOGE LONG, SOL LONG, XRP SHORT. They appear **twice each** — once with `source_system=prediction_market_consensus` (OPEN, pnl 0) and once with `source_system=alpha_engine` (resolved):
  - DOGE LONG `SL_HIT −1.76%`
  - SOL LONG `SL_HIT −1.57%`
  - XRP SHORT `OPEN +1.14%`
  - plus `recent_closed`: DOGE SHORT `WON +2.4513%` (2026-11-09, source `alpha_engine`).
- So PMC has **real resolver outcomes**, but the data-flow is inconsistent: the committed artifact says 0 picks while the dashboard carries 3, and the same IDs are double-counted under two source systems.
- Quality note: the DOGE pick's own reason string says **"Prediction market consensus: 1 sources agree LONG DOGEUSDT ... Sources: kalshi_signal_agent"** — i.e. it was emitted from a **single** source category despite `MIN_SOURCE_CATEGORIES = 2`. This is a gate-bypass/score-gap issue worth a separate audit.
- Leaderboard `prediction_market_consensus`: 1 forward trade, 100% WR — too small to mean anything.

---

## 4. copy_trader_intel (and multi_asset_copytrader)

**Named `copy_trader_intel` system: DEAD in dashboard.**
- Dashboard registry reads `copy_trader_intel/data/active_picks.json` (`audit_trail/dashboard_generator.py:4023-4025`).
- That path matches `.gitignore:322` (`**/data/active_picks.json`) → never committed; GitHub contents API 404. Live system row: `status=dead, active_picks=0, wins=1, losses=0`.
- `closed_trades.json` (tracked, 336 rows) newest `2026-05-25T20:49Z` — ~5.6 months stale. `clone_active_picks.json` picks are `2026-03-19` and mostly `EXPIRED`; clone closed picks are May 2026.

**Per-venue scrapers: REAL.**
- Hyperliquid: `https://api.hyperliquid.xyz/info` + `https://stats-data.hyperliquid.xyz/Mainnet/leaderboard` (`hyperliquid_scraper.py:29-30`). Live probe: leaderboard HTTP 200, **47,887 rows**.
- Bybit beehive: `https://api2.bybitglobal.com/fapi/beehive/public/v1` (`bybit_scraper.py:43`); plain curl is **403 Akamai** — the scraper uses `curl_cffi` TLS fingerprinting or subprocess fallback (doc `:22-24`). Committed `bybit_picks.json` on `main` is fresh: 6 picks, newest `2026-11-14T15:25:08Z`.
- Bitget: V2 authenticated endpoints (`bitget_scraper.py:116-118`); `BITGET_API_KEY/SECRET/PASSPHRASE` present in this shell. **Synthetic fallback exists**: when V2 returns nothing it builds positions from `currentTradingList` with `holdSide: "long"` default and `openPrice: "0"`, then fills entry from live Binance price (`:496-510`, `:808-819`). These are flagged `synthetic: True` but default direction is an assumption, not observed data.
- CoinGlass: v3 requires `COINGLASS_API_KEY` (`coinglass_scraper.py:15,151`); **key UNSET** in this environment. Falls back to no-key exchange APIs (Binance/OKX/Bybit) at `:353`.
- Dune/Nansen: require `DUNE_API_KEY` / `NANSEN_API_KEY` (`dune_scraper.py:194`, `nansen_scraper.py:131`); both SET in this shell.
- `copytrader_source_harvester.py` actively **removes** placeholder traders (`FXL-Signal-N`, `FF-System-N`) rather than emitting them (`:11-14,133-170,1360-1383`).
- CI merge conflicts: the 15:10Z copy-trader run hit `CONFLICT (content)` on ~30 data files including `bybit_picks.json`, then logged `Stash pop conflict — keeping our generated files` before pushing. Freshness is therefore race-dependent.

**Fresh merged surface:** `alpha_engine/data/active_picks.json` on `main` (16:06Z) has 130 picks: **50 tagged `copy_trader_intel`** and **30 tagged `multi_asset_copytrader`**. These reach the dashboard under the `alpha_engine` system, not under the copy-trader system rows.

**`multi_asset_copytrader`: REAL and active.**
- `copy_trader_intel/multi_asset_copytrader_scraper.py` — "NO API KEYS NEEDED"; sources Yahoo Finance/yfinance, CFTC Socrata (`https://publicreporting.cftc.gov/resource/6dca-aqww.json`), Myfxbook/IG/DailyFX HTML, Binance/OKX/Bybit (`:1-40`, `:1104-1106`, `:1745`).
- Live dashboard: `status=active`, **12 active** system count (1 in `picks.active`, 68 in `active_raw`), **39 closed: 21 W / 18 L (53.8%)**, newest `2026-11-14T13:06:02Z` (ES=F LONG), FX/stock picks at same timestamp. Real resolved outcomes with prices (`forex_rsi2_mean_reversion AUDUSD=X LOST −0.5%`, etc.).
- Committed `multi_asset_picks.json` on `main`: `generated_at 2026-11-14T16:06:57Z`, 32 picks.

---

## 5. HyroTrader / hyro modules

- **Underlying data is real**: `tools/hyro_quan_bridge.py` imports `hyro_backtest.fetch_candles` (Binance mirrors + KuCoin, `:24,56`), writes `data_source: "hyro_backtest.fetch_candles (Binance mirrors + KuCoin)"`, lookback 45d. Live `hyro_quan_bridge.json` `generated_at 2026-11-14T14:22:55Z`, 53,864 B — fresh.
- **But HyroTrader is not a live pick source:**
  - `hyrotrader_picks.json` (live, 11.5 KB): 7 picks, **all `status: pending_entry`**, `entry_price/stop_loss/take_profit = None`; stats are backtest strings (`+$1125 PnL, PF 2.15, 52% WR, 54 trades/6mo`).
  - Account snapshot: `equity_usdt 4929.34`, `cumulative_pnl_usdt -70.66`, `last_session_date 2026-04-08`, `trading_days_logged 0`.
  - `hyrotrader_closed_picks.json`: `generated_utc 2026-05-30T23:38Z`, `n_closed 0`, note "Real fills only — auto-invented PnL is forbidden".
  - `hyro_signal_monitor.json`: `scan_time 2026-04-12T03:17Z` (**~7 months stale**). `hyrotrader_short_term_entries.json`: `2026-04-14` (7 months). `hyro_pick_performance.json`: `2026-11-08T02:14Z` (6 days stale) with 45 W / 27 L / 15 pending, 62.5% WR.
  - **Zero `hyro` references in `dashboard_data.json`**; Hyro lives on a separate `/audit/hyrotrader/` page.
- `alpha_engine/hyrotrader_short_term_scanner.py:55` says "using sample data" on missing file but returns `[]` (no fabricated picks); its "mock pick" at `:113` is only a scoring container over real Binance klines. Output is stale/unrouted (no workflow caller found).
- Verdict: **UNVERIFIED as a live trading/ledger source; REAL as a backtest/analysis feed.**

---

## 6. funding_rate_arb and btc_breakout (ghost-excluded)

**`funding_rate_arb.py` — REAL fetcher.**
- Binance USDⓈ-M futures public API, no key: `FAPI_BASES = [fapi.binance.com, fapi1, fapi2]` (`:38-47`), `scan_funding_rate_arb()` `:143`, writes `alpha_engine/data/funding_rate_picks.json` (`:63`).
- Live FAPI probe `premiumIndex?symbol=BTCUSDT` → HTTP 200, `lastFundingRate 0.00003497`, `markPrice 65454.9`.
- Committed artifact on `main`: `scanned_at 2026-11-14T01:37:52Z`, `total_pairs_scanned 898`, `picks_generated 25`, 25 picks, all `OPEN` (none resolved). ~14.5 h stale vs the hourly cadence (either scanner failures or unchanged dedup in recent runs).
- **BUT it is a ghost system**: registered at `dashboard_generator.py:4053`, then hard-excluded at `:4422` (`_GHOST_SYSTEMS`, "never produced data files") and skipped at `:8870`. **0 refs in the live dashboard** (`funding_rate_arb` count = 0). The comment is factually wrong — the file exists with 25 picks.

**`btc_breakout_strategy.py` — REAL fetcher.**
- Binance spot + KuCoin + CryptoCompare + CoinGecko fallbacks (`:52-69`), 1H klines, writes `alpha_engine/data/btc_breakout_picks.json` (`:48`), `scan_btc_breakout()` `:448`.
- Committed artifact on `main`: `generated_at 2026-11-14T14:13:39Z`, `signals_found 0`, `picks []`. Fresh and real; simply no qualifying breakout (range filter 0.5%–5%, volume >1.5×).
- Also a ghost system: `dashboard_generator.py:4054` + `:4429` + `:8870`. **0 refs in the live dashboard.**

---

## 7. production_scanner.py

- Real orchestrator, no synthetic price generation. Imports shared funding-rate failover (`:95`), calls `_fetch_top_funding()` (`:1915`), `main()` at `:3840`, circuit-breaker logic at `:3874+`.
- Only two synthetic-word hits are benign: `:759 "mocked here or pulled from track"` (comment) and `:2722 "placeholder for future soft-flag logic"`.
- It consumes merged pick pools; it does not itself fetch Kalshi/Polymarket. Authenticity therefore depends on the upstream emitters above.

---

## 8. `summary_picks.json` root cause (WR > 100%, wins+losses ≠ resolved)

**Live symptom** (`https://findtorontoevents.ca/audit/data/summary_picks.json`, `generated_at 2026-11-14T14:30:06Z`, `source=mysql.trading_picks`):

| Class | total | resolved | wins | losses | WR | wins+losses−resolved |
|---|---|---|---|---|---|---|
| BOND | 1,603 | 72 | 92 | 156 | **127.8%** | +176 |
| COMMODITY | 19,502 | 1,447 | 3,476 | 3,466 | **240.2%** | +5,495 |
| EQUITY | 13,383 | 820 | 1,332 | 2,148 | **162.4%** | +2,660 |
| ETF | 1,002 | 73 | 170 | 183 | **232.9%** | +280 |
| FOREX | 60,666 | 5,806 | 8,536 | 8,968 | **147.0%** | +11,698 |
| FUTURES | 945 | 61 | 222 | 357 | **363.9%** | +518 |
| INDEX | 3,549 | 17 | 194 | 251 | **1141.2%** | +428 |
| CRYPTO | 39,825 | 10,444 | 10,262 | 13,746 | 98.3% | +13,564 |

Source: `tools/sync_summary_picks_json.py`.

**Root cause A — MySQL path (`_from_mysql`, lines 62-65).** Three different populations are combined:
```sql
-- :63 resolved
SUM(CASE WHEN status IN ('WON','LOST','CLOSED','EXPIRED','TP_HIT','SL_HIT') THEN 1 ELSE 0 END) AS resolved
-- :64 wins
SUM(CASE WHEN status = 'WON' OR (pnl_pct IS NOT NULL AND pnl_pct > 0 AND status NOT IN ('LOST','ACTIVE','OPEN')) THEN 1 ELSE 0 END) AS wins
-- :65 losses
SUM(CASE WHEN status = 'LOST' OR (pnl_pct IS NOT NULL AND pnl_pct < 0) THEN 1 ELSE 0 END) AS losses
```
- `wins` and `losses` are **independent and overlapping**: a `WON` row with `pnl_pct < 0` counts as both; a `LOST` row with `pnl_pct > 0` counts as both.
- `losses` has **no status whitelist** → `ACTIVE`/`OPEN`/`PENDING` rows with negative mark-to-market pnl are counted as losses even though they are not resolved.
- `wins` admits any status except `LOST/ACTIVE/OPEN` with `pnl>0` (e.g. `PENDING`, `WATCH`, `PARTIAL`) that is not in the `resolved` set.
- `win_rate_pct = wins / resolved` (`:161`) divides a mixed-population numerator by a different denominator → >100%.

**Root cause B — local JSON fallback (`_from_local_json`, lines 130-140).** Same class of error:
```python
if st in RESOLVED or pnl is not None:   # :130  open marks count as "resolved"
    s["resolved"] += 1
    if pnl is not None:
        if pnl_f > 0 or st == "WON":    # :137  wins
            s["wins"] += 1
        elif pnl_f < 0 or st == "LOST":  # :139  losses
            s["losses"] += 1
```
- Any pick with a non-null `pnl_pct` (including `ACTIVE`) is counted `resolved`.
- `wins`/`losses` overlap (`LOST` + positive pnl, `WON` + negative pnl).
- A pick can be counted in both wins and losses; `wins + losses` is not constrained to `<= resolved`.

**Effect:** the artifact is not just cosmetically wrong; every WR/PF/expectancy derived from it is invalid. Note the *dashboard* overall summary is separately computed and sane (`overall_win_rate 41.8%`, `wins 3,537 / losses 4,858`), so this is an **artifact-level** defect, not the main dashboard metric. `audit_dashboard/incidents.html:129` already records a related P1 ("identical last_pick across asset classes — fixture suspicion") and the fix was never made; the current failure mode is arithmetic, not fixtures.

**Minimal correct formulation:** compute one resolved set, then classify within it, e.g.
```sql
resolved = status IN ('WON','LOST','CLOSED','EXPIRED','TP_HIT','SL_HIT','STOPPED','TARGET_HIT')
wins     = status IN ('WON','TP_HIT','TARGET_HIT') OR (resolved AND pnl_pct > 0)
losses   = status IN ('LOST','SL_HIT','STOPPED')  OR (resolved AND pnl_pct < 0)
wr       = wins / NULLIF(wins + losses, 0)
```
and assert `wins + losses <= resolved` in a unit test. The generator has no tests today.

---

## 9. Key presence (names only; no secret values read or printed)

| Variable | State | Used by |
|---|---|---|
| `BITGET_API_KEY` / `BITGET_API_SECRET` / `BITGET_API_PASSPHRASE` | SET | `copy_trader_intel/bitget_scraper.py:241` |
| `DUNE_API_KEY` | SET | `copy_trader_intel/dune_scraper.py:194` |
| `NANSEN_API_KEY` | SET | `copy_trader_intel/nansen_scraper.py:131` |
| `COINGLASS_API_KEY` | **UNSET** | `copy_trader_intel/coinglass_scraper.py:151` (falls back to no-key exchange APIs) |
| Kalshi / Polymarket / Binance / Hyperliquid public | no key needed | verified HTTP 200 above |

`dbpasses.txt` exists in the parent repo but was not read; no secret was printed.

---

## 10. Method / limitations

- Live snapshot used: `GET https://findtorontoevents.ca/audit/data/dashboard_data.json` (HTTP 200, 25,099,200 B; `generated_at 2026-11-14T14:30:07Z`, `data_freshness.last_dashboard_build 14:34:54Z`, age 0.7 h at build).
- Counts are from that snapshot; the in-progress 15:14Z dashboard run and post-14:30Z source commits (e.g. `alpha_engine/data/active_picks.json` @16:06Z, `bybit_picks.json` @15:25Z) are newer than the snapshot and are called out separately.
- CI evidence read with `gh run view --log` for runs `43611779394` (polymarket), `43598734241` (audit-dashboard), `43608764529` (copy-trader). No repo files were modified.
- `kalshi_signals.json` / `polymarket_signals.json` could not be inspected directly because they are gitignored and never committed; their existence and contents are inferred from the CI log plus the deployed dashboard payload.
- Cannot measure resolver accuracy for Kalshi (0 resolved) or Hyro (0 executed). Those are explicitly marked, not assumed.
