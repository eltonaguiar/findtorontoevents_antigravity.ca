# Copytrader Verified Sources Audit (2026-11-18)

**Requested:** find verified US copytrader sources, backtest/check reliability, free high-quality winning sources, check post date/time EST and future-bias, review GitHub/repo copytrader picks per asset class on `findtorontoevents.ca/audit`, integrate top-quality sources if present.

**Snapshot:** 2026-11-18 ~03:53 UTC (2026-11-17 10:53 PM EST). Workspace: `auditcopytrader` worktree. External web/GitHub search APIs unavailable in-session (Brave 422/rate-limit, Tavily 432); GitHub/source candidates below come from in-repo inventories (`copy_trader_intel/data/external_feeds_research.json`, `research_*_sources.json`, `research_verified_traders.json`) and existing reports.

## 1) Current copytrader sources in repo (audit-facing)

| Asset class | Feed/source | Source type | Stored evidence | Reliability / win status |
|---|---|---|---|---|
| CRYPTO | OKX/HL/Bitget/Bybit/BingX/Gate/DEX(Copin/dYdX/GMX/Drift)/Polymarket via `copy_trader_intel/main.py` + scrapers, merged by `copy-trader-intelligence.yml` | Public/web/on-chain copy/smart-money scraping | `okx_picks.json` 23 OPEN (2026-11-17T23:40:46Z); `polymarket_picks.json` 2 OPEN. `closed_trades.json` total 336: `copy_trader_intel`/crypto 319 (94W/184L/41 flat, **29.5% WR, +16.00% pnl sum**, dominated by `copy_hl_lb_None` 278 trades 33.8% WR); `copy_trader_binance` 10 flat; `copy_trader_bybit` 6 flat; clones mostly TIME_EXPIRED/0 pnl. | **Mixed/unproven as “top quality winning”.** Raw closed intel WR weak; clone categories previously negative (e.g. `docs/STRATEGY_INVESTIGATION_copy_trader_clones_CRYPTO_2026-05-19.md`: copy_trader_clones CRYPTO n=34 WR 44.1% PF 0.781 Kelly -0.123, kill recommended). |
| CRYPTO (forward-test portfolio sim) | `alpha_engine/portfolio_tracker_copytrader*.py` / `alpha_engine/data/portfolio_copytrader.json` | Internal simulated forward test (filters, sizing, TP/SL/time exits) | 738 closed positions, 711 nonzero pnl, **429W/711 = 60.3% WR**, +1820.09 sum pnl% on nonzero (start 10k → 23188.69). History includes corrected exits (e.g. TAO fix noted). | **Promising but simulated/derived, not exchange-verified fills.** Use as research signal, not proof of broker-realized edge. |
| FOREX | `multi_asset_copytrader_scraper.py` → `forex_copytrader_picks.json` / `multi_asset_picks.json` | Reverse-engineered strategies: RSI2 MR, z-score, carry, IG/Myfxbook/CFTC contrarian signals | 27 OPEN in latest multi-asset snapshot (2026-11-17T23:48:20Z), all `forward_test_only: true`, `forward_trades: 0`, `forward_wr: 0`. | **Unverified/forward-test only (no resolved wins/losses).** |
| COMMODITY | `multi_asset_*` (COT/commercial, futures momentum) | COT (Socrata) + market-data strategies | 5 OPEN, forward_test_only, 0 resolved. | **Unverified forward-only.** COT is high-quality data but must be lag-corrected, 1-per-release, forward-resolved (repo forensics flagged prior over-emission). |
| FUTURES | `multi_asset_*` | Momentum/technical | 2 OPEN, forward_test_only, 0 resolved. | **Unverified forward-only.** |
| EQUITY/STOCKS | `multi_asset_*` smart-money accumulation | Price/volume/SMA heuristics | 1 OPEN, forward_test_only, 0 resolved. | **Unverified forward-only.** |
| ETF/BOND (copytrader-specific) | None dedicated found | — | — | Covered by other audit systems only (thin). |

**Trader DB / “trusted” lists:** `copytrader_database.json` (200 unique: 49 crypto, 151 forex; quality dist 90-100:15, 70-89:100, 50-69:77, 30-49:8) and `trusted_copy_traders.md`. **Verification spot-check:** `python3 copy_trader_intel/copytrader_quality_backtest.py` (2026-11-18 run) queried 6 curated OKX codes → 5 “futures lead trader doesn't exist”; only `AD2B6E94` (FJ Investment) returned 100 trades and graded **F** (30% WR, PF 0.7, Sharpe -0.23, -$77,002.35 PnL, 510.8% max DD, red flags). **Conclusion:** claimed/curated trust/ROI is not currently API-verifiable for those IDs; do not treat as “top quality winning”.

## 2) Backtest / validation status (what’s real)

- **Available tools:** `copytrader_quality_backtest.py` (OKX history pull, quality/fraud metrics, strategy reverse-engineer, optional yfinance backtest), `multi_asset_backtester.py` + `multi_asset_config.json` (train/test split, TP/SL grid, significance thresholds), `consensus_backtester.py`, `portfolio_tracker_copytrader*.py` forward simulation.
- **Observed outcomes:** only crypto raw copy-intel closed sample is material and weak (~29.5% WR). Multi-asset per-class picks have **no forward-resolved outcomes yet**. Portfolio sim shows 60.3% WR on nonzero closed but is modelled (sizing/exits/filters), not source-verified execution.
- **Not yet “proven winners”:** no per-asset-class free copytrader source in stored data meets a strict bar (large resolved n, forward-only, positive PF/expectancy after costs, reproducible timestamps).

## 3) Timestamp / EST / future-bias review

**Sampled picks (UTC → EST, 2026-11-17 is EST = UTC-5):**

| Pick/source | Key times (UTC) | EST | Notes |
|---|---|---|---|
| `okx_copy_Shallow-Pair-Frog::SOLUSDT::2026-11-17_2340` (`copy_trader_okx`) | `open_time` 2026-11-17T17:00:31.061Z, capture `timestamp` 2026-11-17T23:40:46.818Z, `entry_date` 2026-11-17 | open 12:00:31.061 PM EST, capture 6:40:46.818 PM EST | Good: trader open time and ingest time both present. |
| `okx_copy_Shallow-Pair-Frog::BTCUSDT::2026-11-17_2340` | `open_time` 16:56:17.022Z, capture 23:40:46.818Z | open 11:56:17.022 AM EST, capture 6:40:46 PM EST | ~6h44m lag between position open and scrape capture — **must not backtest as if entered at open without lag/copy delay**. |
| `copy_pm_cleancoinflip::BTCUSDT::2026-11-17_2347` (`copy_trader_polymarket`) | `timestamp` 23:47:02.264Z, `entry_date` 2026-11-17 | 6:47:02.264 PM EST | No `open_time`/signal time recorded; capture time only. |
| `multi_asset_forex_rsi2_mean_reversion::EURUSD=X::2026-11-17_2347` | `timestamp` 23:47:37.186Z, `entry_date` 2026-11-17 | 6:47:37.186 PM EST | Forward-test only; needs bar-time/next-bar entry for bias-free eval. |
| `multi_asset_smart_money_accumulation::SNAP::2026-11-17_2348` | `timestamp` 23:48:20.301Z, `signal_timestamp` 2026-11-17T00:00:00Z, `entry_date` 2026-11-17 | signal 7:00:00 PM EST (prev day) / midnight UTC, capture 6:48:20 PM EST | Daily signal timestamp present; ensure execution is after signal (next open/bar). |
| Commodity COT example `multi_asset_cftc_cot_commercial_signal::GC=F` | `timestamp` 23:47:58.993Z | 6:47:58 PM EST | Must enforce COT release/publication lag and 1-signal-per-release. |

**Future-bias / “truly predicted” controls required:**
- Evaluate from `signal_time`/`source_open_time` + realistic copy/ingest delay (or `timestamp`/next tradable bar), never with hindsight fills.
- Do not use leaderboard lookback ROI/AUM as predictive label; require forward-resolved outcomes after signal time.
- Daily strategies: resolve on bars strictly after signal; avoid same-bar close leakage.
- Backtests: out-of-sample/walk-forward, include fees/slippage (`multi_asset_config.json`), and cap significance (min trades).
- COT/13F/filings: respect publication lag (COT ~Fri release for Tue data; 13F/Form4 disclosure delays).
- Flag picks missing `open_time`/`signal_timestamp` as lower-verifiability until enriched.

## 4) Free / GitHub-sourced candidates per asset class (from in-repo research, prioritized)

| Priority | Class | Free source | Why quality/verifiable | Integration guidance |
|---|---|---|---|---|
| P0 | CRYPTO | **Hyperliquid public info/on-chain API** (official SDK `hyperliquid-python-sdk`, MIT, read-only) | On-chain, timestamped positions/fills, reproducible; no fragile CEX UI scrape | Require N-wallet consensus, store fill/open timestamps, forward-only PnL; keep negative-Kelly clone feeds blocked. |
| P0 | COMMODITY, FUTURES, FX-futures proxy | **CFTC COT** (Socrata/open data + bulk, official/free) | Ground-truth positioning, weekly cadence, known publication lag | Enforce 1 signal/release + lag guard + report-date tracking; integrate with existing COT paths and forward resolution. |
| P1 | EQUITY/ETF | **SEC EDGAR 13F/Form 4**, **OpenInsider**, **Finviz** insider/analyst screens (all public/free) | Verifiable filings/transactions, timestamps + disclosure lag | Ingest as smart-money/insider flow with filing/tx dates; forward performance vs entry after disclosure; candidate to lift non-crypto copytrader contribution. |
| P1 | FOREX | **Myfxbook API** (community outlook/sentiment; verified accounts where accessible), **Gains Network gTrade** public REST | Structured sentiment/positioning; on-chain gTrade positions | Use sentiment/contrarian or on-chain positions with signal timestamps; do not trust unverifiable ROI claims. |
| P2 (vet) | Multi | Unofficial GitHub repos listed in `external_feeds_research.json` (Binance bapi refs/scrapers, eToro wrappers, Copin, etc.) | Useful endpoint references; some stale/unlicensed/TOS-risk | Use as implementation reference only; prefer official APIs, add schema/health checks, no blind ingestion. |

**Audit coverage note:** `findtorontoevents.ca/audit` already has crypto copytrader intel plumbing and multi-asset forward-test generators; EQUITY/ETF “copy/smart money” via EDGAR/OpenInsider/Finviz and disciplined COT/HL-on-chain consensus are the highest-quality free gaps to fill per asset class.

## 5) Integration recommendation (now)

- **Do not promote current copytrader feeds as “verified winning” yet.** Raw closed crypto copy intel is weak; multi-asset has zero resolved forward trades; curated trusted traders failed live verification in spot-check.
- **Integrate (safe, high-quality):** (1) HL on-chain consensus with strict wallet/time/forward gates for CRYPTO, (2) lag/dedupe-hardened COT for COMMODITY/FUTURES, (3) EDGAR/OpenInsider/Finviz-derived smart-money signals for EQUITY. Each must emit `signal_time_utc`, `ingest_time_utc`, `signal_time_est` and resolve forward-only with costs.
- **Backtest before enablement:** run `copytrader_quality_backtest.py` on fetchable traders and forward-resolve multi-asset picks OOS; require minimum resolved n + PF>1/positive expectancy + non-negative Kelly by source/asset class.
- **Dashboard:** label sources as `verified_forward`, `forward_test_only`, or `research` and show resolved n/WR/PF plus last signal time in UTC & EST.

## 6) Local LLM divide-and-conquer (available)

- LiteLLM proxy up (`http://localhost:4000`, `ULTRA_FREE_LOCAL_FAST` responsive) and Ollama up (`qwen2.5:3b` responsive). Used to draft supplementary source notes: `updates/2026-11-18-copytrader-local-llm-sources.md` (model-generated, advisory; verify before use).
