# Copy-trader & prediction-market data sources (repo map)

This file lists **real JSON / scraper outputs** under `copy_trader_intel/data/` and related paths. Use them for dashboards, consensus scoring, and `hc_filter.js` independence groups — **never** invent trader stats.

## Unified merge (operators)

```bash
python tools/build_unified_copytrade_candidates.py
```

**Output:** `copy_trader_intel/data/unified_copytrade_candidates.json`  
**Feeds included:** Hyperliquid qualified, Polymarket `qualified_traders`, trusted registry, Gate.io copy profiles.

## Prediction markets

| File | Role |
|------|------|
| `polymarket_trader_profiles.json` | Leaderboard + API-enriched wallets (`qualified_traders`, Bayes WR, archetypes) |
| `polymarket_picks.json` | (if present) downstream picks for audit |
| `prediction_market_agents/` | Strategy audit / scraper code |

`audit_dashboard/hc_filter.js` groups PM systems under `signalGroups.prediction_market` for multi-family consensus.

## Copy-trading venues (profiles / DBs)

| File | Role |
|------|------|
| `qualified_traders.json` | Hyperliquid-style qualified addresses |
| `trusted_traders.json` | Output of `trusted_trader_tracker.py` (trust scores from closed picks) |
| `gate_trader_profiles.json` | Gate.io copy-trading leaders |
| `binance_trader_profiles.json`, `bybit_trader_profiles.json`, `okx_trader_profiles.json` | Exchange copy feeds |
| `hyperliquid_trader_database.json`, `dex_trader_database.json` | HL / DEX whale DBs |
| `bingx_gate_mexc_trader_database.json` | Multi-exchange DB |
| `unified_trader_research.json` | Cross-platform deduped picks snapshot |

## Macro / sentiment (not wallet copy)

| File | Role |
|------|------|
| `coinglass_trader_profiles.json` | Per-symbol L/S, funding, OI-style metrics (regime context, not a wallet list) |
| `sentiment_signals.json` | Aggregated sentiment |

Wire these into **regime** or **score bonus** fields, not into the same array as copy wallets unless normalized.

## Security

- **Never** commit GitHub PATs, API keys, or exchange secrets. Use `.env` (gitignored) or OS credential store.
- If a token was pasted in chat or email, **revoke it** in GitHub settings and create a new one.

## See also

- `docs/COPY_TRADE_CANDIDATES.md`
- `TESTING_PROTOCOL.MD` (validation layers)
- `docs/ALL_STRATEGIES.md`
