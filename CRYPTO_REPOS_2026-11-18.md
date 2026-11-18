# CRYPTO_REPOS_2026-11-18

**Sweep date:** 2026-11-18
**Method:** Every repo below was opened via the live GitHub API (`api.github.com/repos/<owner>/<repo>`) on 2026-11-18 between 17:47Z and 17:53Z. Stars / `pushed_at` / `license.spdx_id` / `archived` are the API's own values, not from memory.
**Scope:** spot & perps, funding/basis, LOB microstructure, on-chain, exchange APIs, options, MM.
**Baseline for "what we already have":** `crypto_db_profile.md` + `CROSS_DB_DATA_QUALITY_MATRIX.md` (this repo root).

---

## Headline verdict

> [!IMPORTANT]
> **No repo in this sweep constitutes a *proven edge*.** The verdict is still **NONE**.
> The five viable repos below are **infrastructure** — data plumbing, exchange connectivity, execution. None of them ships a signed, out-of-sample-tested strategy that we could deploy. Crypto funding/basis is a real, economically-motivated carry premium, but no repo here is a shortcut to it; we would have to build and validate the signal ourselves.

---

## Top 5 — ranked

### 1. ccxt/ccxt — **VIABLE**
- **URL:** https://github.com/ccxt/ccxt
- **Stars:** 44,920 · **Last commit:** 2026-11-18T12:46:54Z · **License:** MIT
- **What it does:** Unified API/abstraction across 100+ venues incl. Binance, Bybit, OKX, Coinbase, Deribit. One interface for OHLCV, funding-rate history, order book, tickers, and order placement.
- **Data needed:** none — it *is* the data path. Free public endpoints cover the history we'd need for funding/basis research.
- **Edge claim:** none, and it doesn't pretend otherwise. Falsifiability N/A.
- **Biggest reason it would NOT work:** it is a transport layer, not alpha. MIT license and generality mean it is the *commoditized* part of the stack — every competitor has it. Its abstractions also smooth over exactly the venue-specific quirks (funding interval conventions, contract multipliers, index vs mark price) that basis arb actually turns on.
- **What we already have vs what this adds:** We have `crypto_ohlcv` (1.15M 1h bars, 14 symbols, Jan 2025–Mar 2026) served from our MySQL. We have **zero** funding-rate, basis, mark/index-price, or perp-specific history. ccxt is the concrete fix: it gives us `fetchFundingRateHistory` per venue, which is the missing column set. **This is the single highest-value adoption in this sweep.**

### 2. freqtrade/freqtrade — **PARTIAL**
- **URL:** https://github.com/freqtrade/freqtrade
- **Stars:** 57,037 · **Last commit:** 2026-11-17T06:21:00Z · **License:** GPL-3.0
- **What it does:** Full crypto bot: backtesting, hyperopt, dry-run, live trading, FreqAI (ML). Supports spot and futures, funding-fee modelling in futures backtests.
- **Edge claim:** **Not falsifiable as shipped.** It embeds no strategy — it is a harness for *your* strategy. The "it makes money" reputation online is community anecdotes.
- **Biggest reason it would NOT work:** hyperopt is an overfitting machine. With 14 symbols and ~82k hourly bars, freqtrade's optimizer will trivially find a curve that looks great in-sample and dies out of sample. Also GPL-3.0 is copyleft — fine for internal research, a real constraint if we ever want to ship anything derived from it in the public site.
- **What we already have vs what this adds:** We have a signal/pick/outcome pipeline with backtest DBs already. freqtrade adds **funding-fee-aware futures backtesting**, which our current stack does not model at all. That one capability is the reason to look at it; the rest duplicates what we have.

### 3. nautechsystems/nautilus_trader — **PARTIAL**
- **URL:** https://github.com/nautechsystems/nautilus_trader
- **Stars:** 31,665 · **Last commit:** 2026-11-18T14:12:52Z · **License:** LGPL-3.0
- **What it does:** Rust-core, Python-API event-driven engine. Tick- and L2-order-book-native, deterministic backtest, first-class time-bar aggregation, real crypto venue adapters.
- **Edge claim:** none shipped; it's an engine. But the *determinism* is the notable property — same code path in backtest and live, which is the standard way people accidentally fool themselves and is also the standard way to avoid it.
- **Biggest reason it would NOT work:** wrong tool for where we are. Our whole corpus is 1h bars. Nautilus's value only materialises at tick/L2 resolution, and we have no L2 history to feed it. Steep Rust/Python boundary, heavy deps. It would be a large migration for zero current signal.
- **What we already have vs what this adds:** Adds a genuinely correct microstructure-capable engine. Does **not** add data — and without L2 history that capability is inert. Revisit only if/when we purchase or capture tick data.

### 4. hummingbot/hummingbot — **PARTIAL**
- **URL:** https://github.com/hummingbot/hummingbot
- **Stars:** 21,262 · **Last commit:** 2026-11-18T13:37:49Z · **License:** Apache-2.0
- **What it does:** Market-making / liquidity-provision bot framework with an explicit strategy catalogue: pure MM, cross-exchange MM, and — relevant here — **spot-perp funding arbitrage** and triangular arb. Live order-book management built in.
- **Edge claim:** **Partly falsifiable, and weak.** Funding-arb is a real structural premium (you're paid to take one side of a crowded perp book), but the pooled return depends on entry timing, fee tier, and leg risk. Hummingbot ships no PnL track record; its published strategies are unvalidated templates.
- **Biggest reason it would NOT work:** this is where the honest answer gets uncomfortable. Retail funding arb on Binance/Bybit/OKX is one of the most crowded trades in crypto. With taker fees at ~5-7bps/side plus funding-interval mark risk on both legs, the net carry for a no-fee-tier participant is frequently negative. Winner requires fee rebates, colocation-quality latency, or size — none of which we have. Apache-2.0 is the most permissive licence here, which is a genuine plus.
- **What we already have vs what this adds:** Adds the **only pre-built funding/basis strategy logic** found in this sweep, plus a live execution path. That is the closest thing to a testable edge claim we found. But the claim is a template, not evidence.

### 5. jesse-ai/jesse — **PARTIAL (leaning DECORATIVE for us)**
- **URL:** https://github.com/jesse-ai/jesse
- **Stars:** 8,822 · **Last commit:** 2026-11-17T13:29:36Z · **License:** MIT
- **What it does:** Clean Python backtester/research framework with crypto focus; good ergonomics, ML/DL tooling, multi-symbol.
- **Edge claim:** none shipped — framework only.
- **Biggest reason it would NOT work:** it overlaps almost entirely with what freqtrade gives us plus our existing backtest DBs, but with a smaller ecosystem and no live-trading maturity comparable to freqtrade/hummingbot. Adding it would be a second redundant research stack. MIT licence is the one clear advantage.
- **What we already have vs what this adds:** adds a pleasant MIT-licensed research surface. Adds no data, no venue coverage, no strategy. **Skip unless MIT is a hard requirement** and GPL freqtrade is disqualified.

---

## What we already have vs what this sweep adds (summary)

| We already have | Gap this sweep exposes | Repo that closes it |
|---|---|---|
| `crypto_ohlcv` 1.15M 1h bars, 14 symbols (live) | No funding rates, no basis, no perp mark/index, no L2 | **ccxt** (funding history) |
| `crypto_indicators` / `crypto_patterns` / `crypto_signals` = **0 rows** | No indicator or signal pipeline at all | freqtrade/jesse (harness only) |
| `crypto_exchange_netflow` 20 rows, frozen Feb 2026 | No live on-chain metric feed | duneanalytics/dune-client (see below) |
| `crypto_whale_movements` / `crypto_whale_wallets` = **0 rows, dead since Feb 2026** | Whale tracking abandoned, and no repo here revives it credibly | none — see copy-trading section |
| Existing backtest DBs + pick/outcome pipeline | Backtests don't model funding fees on perps | freqtrade (funding-aware futures backtest) |

---

## Supporting repos (verified real, not top-5)

- **duneanalytics/dune-client** — https://github.com/duneanalytics/dune-client — 140★, pushed 2026-11-09, Apache-2.0. Official Dune API client. Low stars but it *is* the official, working path to on-chain metrics (exchange netflow, stablecoin supply, whale cohort balances). **The pragmatic replacement for our dead `crypto_exchange_netflow` pipeline.** Requires a Dune API key; free tier is rate-limited.
- **polakowo/vectorbt** — https://github.com/polakowo/vectorbt — 9,886★, pushed 2026-11-11, license `NOASSERTION` (partial Apache-2.0 + commercial split, so **check terms before dependency**). Fast vectorised backtesting; good for screening many funding-rate variants cheaply.
- **exchange-core/exchange-core** — https://github.com/exchange-core/exchange-core — 2,672★, pushed 2026-11-18, Apache-2.0. Ultra-fast Java LMAX-Disruptor matching engine. Real, but a *building-an-exchange* tool, not an alpha tool. **DECORATIVE for us.**

---

## Dead / stale / hallucination flags

> [!WARNING]
> **Nine of the URLs returned by web search in this sweep do not exist.** They were `404 Not Found` when checked against the GitHub API. Web-search summaries in this domain are heavily prone to inventing plausible-sounding repo names. Do not cite any crypto repo without an API check.

Verified non-existent (`Not Found` via API on 2026-11-18):
- `michaelgav/Deribit-Backtester`
- `saleh-mir/deribit-backtest`
- `0xMaki/crypto-options-backtester`
- `MichaelH94/optopsy`
- `joelbenitah/backtrader-deribit`
- `DefiLlama-Labs/deribito`
- `polakowo/orderbook` (the real polakowo repo is `vectorbt`)
- `marketneutral/limit-order-book`
- `bitmex/bitmex-hft-trading`

Other flags:
- **askmike/gekko** — https://github.com/askmike/gekko — 10,177★, MIT, but **ARCHIVED, last push 2020-02-16**. Appears in nearly every "best crypto bot" listicle. **Dead. Do not use.**
- **openbb-finance/OpenBB** — returned `301 Moved Permanently`; repo relocated, path changed. Not evaluated.
- **crypto options / Deribit:** the sweep found **no verifiable, maintained open-source Deribit backtester.** Every candidate was hallucinated. Treat "open-source crypto options backtesting" as currently unserved.

---

## Copy-trading / signal-following / whale-tracking — **DECORATIVE**

Short answer: **no repo in this sweep makes a copy-trading edge practical, and the structural case for it is weak.**

- **Following exchange leaderboards (Binance/Bybit copy-trade):** survivorship bias is the entire product. Leaderboards display current account equity with drawdowns often hidden or reset; the top accounts are the survivors of a large population, many running martingale or high-leverage directional bets that blow up. There is no rank-history archive to backtest against, so **the edge is not falsifiable** — which is disqualifying for us.
- **On-chain whale tracking:** our own DB already reflects the outcome — `crypto_whale_movements` and `crypto_whale_wallets` sit at **0 rows, last touched Feb 2026**. That is a fair proxy for how much value the previous attempt extracted. Labels ("whale") are also circular: you identify whales by past profitable trades and then trade their next ones, which is peak in-sample reasoning. `dune-client` makes the *data* accessible but supplies no signal.
- **Signal-following / Telegram-Discord alpha groups:** unreproducible, unpriceable, and we cannot audit whether the "signal" preceded the move.

> [!NOTE]
> The one place genuine copy-behaviour exists is **funding/basis carry** — not following accounts, but following a mechanical, publicly observable payment. That is a real premium, and it is exactly the thing hummingbot templates and ccxt funding history let us measure. It is also crowded.

---

## Verdict on a proven edge

**NONE.** As of 2026-11-18 this sweep found **no repo that constitutes a consistent, proven, out-of-sample-validated crypto edge.** What we found is a competent toolchain. The edge, if it exists for us, is in the data and the validation discipline, not in any repository.

### Next concrete experiment (do this, not another repo search)

**Falsifiable test: is the cash-and-carry / funding basis premium positive for us net of realistic costs?**
1. Pull perp funding-rate history for BTC/ETH and 6-8 majors from 2 venues via ccxt (Binance, Bybit), 2024-01-01 → present. This is the first dataset we do not already have.
2. Construct the delta-neutral carry series: long spot, short perp, PnL = funding received − round-trip taker fees − borrow/transfer friction. Model entry on funding events only, not continuously.
3. Evaluate out-of-sample split: fit nothing (it's parameter-free) → report Sharpe, hit rate of positive funding intervals, and **net** annualised carry at 5bps, 2bps, and 0bps/rebate fee tiers.
4. **Kill criterion, stated in advance:** if net carry at the 5bps tier has a Sharpe below ~1.0 and a negative or flat median per-interval return, the retail carry trade is closed to us and we stop. If it survives at 5bps, the next question is capacity and leg risk, not signal.

That test is cheap, takes days not weeks, uses only free public data, and produces a number that is either an edge or a no. It is strictly better than adopting freqtrade or hummingbot on reputation.
