# Prediction-Market Repo Scout — 2026-11-18

## Top 5 (verified via GitHub API; no fabricated repos)

| # | Repo | Stars | Last push | License | What it does | Verdict | Reuse |
|---|------|-------|-----------|---------|--------------|---------|-------|
| 1 | [warproxxx/poly_data](https://github.com/warproxxx/poly_data) | 2353 | 2026-09-08 | GPL-3.0 | Polymarket data retriever: markets, order events, trades | PARTIAL | Historical order-book/trade tape for microstructure features |
| 2 | [warproxxx/poly-maker](https://github.com/warproxxx/poly-maker) | 1532 | 2026-07-09 | MIT | Market-making bot for Polymarket (two-sided liquidity) | PARTIAL | MM quoting logic, spread/sizing templates |
| 3 | [Polymarket/agents](https://github.com/Polymarket/agents) | 3819 | 2024-11-05 | MIT | AI-agent trading framework | DECORATIVE | Archived; stale; no verified edge |
| 4 | [Polymarket/py-clob-client](https://github.com/Polymarket/py-clob-client) | 1225 | 2026-05-25 | MIT | Python CLOB client | PARTIAL | API client for live order placement (archived but forkable) |
| 5 | [Polymarket/polymarket-subgraph](https://github.com/Polymarket/polymarket-subgraph) | 223 | 2026-02-13 | LGPL-3.0 | Public subgraph manifest for on-chain trade/volume/user/liquidity | PARTIAL | On-chain settlement data, trade history |

## What we already have vs. what this adds
We already have: copy-trader intel (polymarket_picks.json 7082B), prediction_market_consensus, pm_odds_history, Kalshi snapshots (stale, single file 2026-04-26), and pm_*_signals (ghost streams). The above repos add: (a) a real Polymarket historical trade/order-event tape (poly_data) we lack entirely; (b) market-making quoting logic (poly-maker) to borrow for liquidity-provision experiments; (c) an on-chain subgraph for settlement verification. Nothing replaces our copy-trader lane; it fills the data-archival gap.

## Dead / stale / hallucination-prone
- Polymarket/agents (archived, last push 2024-11) — DECORATIVE; do not treat as live tooling.
- Polymarket/py-clob-client (archived) — fork or use clob-client-v2 (TS, active, 76 stars) instead.
- Kalshi repos from web search (polymarket-kalshi-arbitrage, kalshi-polymarket-arbitrage-bot, pm-kalshi-arb, prediction-market-arbitrage) — could NOT be opened/verified; treat as hallucination-prone until confirmed. Do not rely on them.

## CopyTrader question
Copy-trading on Kalshi/Polymarket is DECORATIVE as a standalone edge: our pm_*_signals streams are ghost systems (never committed rows), and polymarket_picks.json is a static 7KB file with no dedicated DB table. Copy-trading is real only as a *signal input* (follower of informed flow), not as a self-contained strategy. Minimum viable data to make it work: (1) continuous Polymarket order-book + trade tape (poly_data-style) to detect informed flow; (2) wallet-level position tracking (subgraph); (3) Kalshi snapshot freshness (currently 7 months stale). We do NOT need MORE copy-trader sources — our 5-platform scrape (OKX/Bitget/Hyperliquid/Binance/eToro) is already over-collected; the bottleneck is data freshness + verification, not source count.

## Consistent proven edge as of 2026-11-18
NO — UNPROVEN. No repo or internal artifact demonstrates a consistently proven edge on event contracts; all PM signals are ghost/unverified and Kalshi data is stale.

## Cheapest concrete next step
Wire poly_data-style historical trade tape ingestion into our PM lane and backtest favorite-longshot + correlated-market mispricing on a 30-day rolling window before any capital deployment.