# Polymarket Tools Vetting — 2026-05-16

Vetted by: Hermes Agent  
Sources fetched: GitHub raw READMEs + GitHub API metadata  
Date: 2026-05-16

---

## Safe to Integrate (no custody risk)

| Repo | What it does | Integration value | Effort |
|---|---|---|---|
| [leolopez007/polymarket-trade-tracker](https://github.com/leolopez007/polymarket-trade-tracker) | Given a wallet + market URL: PnL, maker/taker role split, on-chain receipt summary. Uses Polymarket Gamma/CLOB public APIs + free Polygon RPC. No private keys, no auto-trading. MIT, 80★, 31 forks, active (updated 2026-05-16). | High — directly gives us per-wallet edge metrics for the copy-trader intel pipeline, validates whale trade quality on Polymarket. | Low — stub already created at `copy_trader_intel/polymarket_trade_tracker_client.py` |
| [polymarket-apis (PyPI)](https://pypi.org/project/polymarket-apis/) | Unified Pydantic-typed Python client covering both CLOB and Gamma APIs. Read-only capable. | Medium — cleaner typed access to the same public endpoints our scraper already uses. | Low — `pip install polymarket-apis` |
| [py-clob-client (PyPI)](https://pypi.org/project/py-clob-client/) | Official Polymarket Python CLOB client. Supports read-only market data without credentials. | Medium — gives real-time orderbook depth for market-quality scoring. | Low |
| [PolyTrack](https://polytrack.org/) | Web platform — whale tracking, P&L alerts, trader performance. Public data. | Medium — manual intelligence source; API (if available) would feed whale-pick pipeline. | Low-medium |
| [Polywhaler](https://polywhaler.com/) | Tracks large trades with insider activity detection. Public data. | Medium — complements PolyTrack for large-trade signal. | Low-medium |
| [Dune Analytics Polymarket dashboards](https://dune.com/browse/dashboards?q=polymarket) | Community SQL dashboards over on-chain Polygon data. Free read access. | Medium — baseline for volume/market health comparisons. | Low (query fork) |
| [FinFeedAPI](https://finfeed.io/api/prediction-markets) | Unified prediction-market API aggregating Polymarket + Kalshi + others. | Medium — multi-market context signals. Pricing unknown; free tier likely. | Low-medium |
| [Sim.ai MCP for Polymarket](https://sim.ai/mcp/polymarket) | MCP integration that lets AI agents query Polymarket data. | Medium — pairs with Claude Code agent loops. | Low |

---

## Risky (requires wallet / private key — analytics-only / DRY_RUN)

| Repo | Risk | Notes |
|---|---|---|
| [MrFadiAi/Polymarket-bot](https://github.com/MrFadiAi/Polymarket-bot) | **HIGH** — requires MetaMask private key in `.env`; auto-executes live trades when `DRY_RUN=false`. TypeScript, MIT, 42★, 16 forks. | Has a `DRY_RUN=true` mode and multi-layer loss limits, but the key storage model (plaintext `.env`) is unacceptable for production. Useful as a strategy reference only — read the strategy logic, do not import or run against live wallets. |
| [Drakkar-Software/OctoBot-Prediction-Market](https://github.com/Drakkar-Software/OctoBot-Prediction-Market) | **MEDIUM-HIGH** — connects to Polymarket account credentials for copy-trading and arbitrage. Self-custody ("keys never leave your computer") but requires credential binding. GPL-3.0, 82★, 12 forks. | Paper trading mode available and well-documented. Arbitrage strategies under development. If ever evaluated, run strictly in paper mode on an isolated test wallet. Do NOT integrate into production pipeline. |

---

## Skip

| Repo | Reason |
|---|---|
| Generic Telegram bots (Polycule, PolyFocus, Polysight, PolyxBot, Polycool, PolyAlertHub) | Closed-source, non-integrable bots; no programmatic API surfaced; manual-use tools only. |
| Browser extensions (PolyPulse, Polyteller, Polyhelper, Nevua Plugin, PolymarketOddsConverter, Raycast extension) | Browser/UI only; no Python-callable API; out of scope for data pipeline. |
| `polymarket-spike-bot` / `polymarket-trading` / `polymarket-copy-trading-bot` / `polymarket-trade-copier` | GitHub URLs in Awesome list use placeholder `username/` paths — repos do not reliably exist; auto-trading risk; skip until confirmed live and safe. |
| `poly-maker` / `polymarket-marketmaking` | Market-making bots requiring credentials + live order submission. Not relevant to our read-only analytics goal. |

---

## Top 10 from Awesome-Polymarket-Tools not in our system

Items are ranked by immediate usefulness to the copy-trader intel pipeline.

1. **polymarket-apis** (PyPI) — Official-community Python client with Pydantic models for CLOB + Gamma; typed, well-maintained. `pip install polymarket-apis`.
2. **py-clob-client** (PyPI) — Official Polymarket Python CLOB client; orderbook depth + trade history without credentials.
3. **PolyTrack** (https://polytrack.org/) — Web whale tracker with P&L and alert data; potential API target for whale signal harvesting.
4. **Polywhaler** (https://polywhaler.com/) — Large-trade + insider-activity detection; complements PolyTrack.
5. **FinFeedAPI** (https://finfeed.io/api/prediction-markets) — Unified multi-market API (Polymarket + Kalshi + others); useful for cross-market signal correlation.
6. **Sim.ai MCP** (https://sim.ai/mcp/polymarket) — MCP tool for AI agents to query Polymarket; integrates directly with Claude Code agent loops.
7. **Bitquery Polymarket GraphQL** (https://graphql.bitquery.io/) — Blockchain-native analytics with smart-contract event decoding; useful for on-chain trade verification.
8. **@polybased/sdk** (npm) — Community TypeScript SDK with real-time WebSocket data; useful if a Node sidecar is needed.
9. **Dune Analytics Polymarket dashboards** (https://dune.com/) — Fork existing community SQL dashboards for custom volume/market-health metrics at no cost.
10. **Poly Whales Tracker** (https://polywhalestracker.com/) — Elite trader monitoring with performance history; third independent whale-data source.

---

## Recommended next integrations (ranked)

1. **leolopez007/polymarket-trade-tracker** (MIT, safe) — Stub already delivered at `copy_trader_intel/polymarket_trade_tracker_client.py`. Wire into `copy_trader_intel/polymarket_scraper.py` to enrich per-wallet scores with verified on-chain PnL and maker/taker role signals. Expected PR: `feat(copy-trader): wire polymarket trade tracker pnl enrichment`.

2. **polymarket-apis** (PyPI, safe) — Replace raw `urllib` calls in `polymarket_scraper.py` with the typed Pydantic client. Reduces maintenance surface, adds type safety, and surfaces API edge cases (rate limits, schema changes) earlier. Low effort: `pip install polymarket-apis`.

3. **py-clob-client** (PyPI, safe) — Add real-time orderbook depth as a market-quality signal: thin books → lower confidence on copy picks. Wire into the scoring path in `copy_trader_intel/consensus_pick_builder.py`.

4. **FinFeedAPI** (free tier, safe) — Pull Kalshi market probabilities as a cross-market sanity check on our Polymarket crypto signals. New `copy_trader_intel/finfeed_client.py` (read-only, follows existing scraper pattern).

5. **Dune Analytics dashboards** (safe, no API key for public queries) — Fork a community Polymarket dashboard to get weekly volume-by-market and trader-count metrics as a feed-health signal for our CRYPTO asset class (currently PF 1.25 / WR 44.6% — extra signal sources could help distinguish real edge from noise).

---

## Safety summary

| Repo | Private key? | Auto-trades? | Paid API? | Verdict |
|---|---|---|---|---|
| leolopez007/polymarket-trade-tracker | No | No | No (optional Alchemy/Infura) | Safe — integrate |
| MrFadiAi/Polymarket-bot | Yes (MetaMask export) | Yes (DRY_RUN=false) | No | RISKY — strategy reference only |
| Drakkar-Software/OctoBot-Prediction-Market | Credentials required | Yes (copy-trade/arbitrage) | No | RISKY — paper/test only |
