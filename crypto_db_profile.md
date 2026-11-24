# Crypto DB Profile (ejaguiar1_stocks proxy)

**DB**: `ejaguiar1_stocks` on `mysql.50webs.com` (MySQL 8.4.7)  
**Profiled by**: `funds-crypto-profiler` (slice: crypto)  
**Date**: 2026-11-18

## Summary

- **Tables**: 8 crypto_* tables in `ejaguiar1_stocks` (accessed via proxy)
- **Active data**: `crypto_assets` (14), `crypto_ohlcv` (1,157,064 rows), `crypto_exchange_netflow` (20 rows)
- **Empty/inactive**: `crypto_indicators`, `crypto_patterns`, `crypto_signals`, `crypto_whale_movements`, `crypto_whale_wallets` (all 0 rows, stale since Feb 2026)
- **Latest update**: `crypto_ohlcv` at 2026-11-18 01:03:08 (live)

## Table Inventory

| Table | Rows | Engine | Last Updated | Collation | Status |
|-------|------|--------|--------------|-----------|--------|
| crypto_assets | 14 | InnoDB | never | utf8mb4_0900_ai_ci | reference |
| crypto_ohlcv | 1,157,064 | InnoDB | 2026-11-18 01:03:08 | utf8mb4_0900_ai_ci | LIVE |
| crypto_exchange_netflow | 20 | MyISAM | 2026-02-16 06:56:40 | utf8mb3_general_ci | stale |
| crypto_indicators | 0 | InnoDB | never | utf8mb4_0900_ai_ci | empty |
| crypto_patterns | 0 | InnoDB | never | utf8mb4_0900_ai_ci | empty |
| crypto_signals | 0 | InnoDB | never | utf8mb4_0900_ai_ci | empty |
| crypto_whale_movements | 0 | MyISAM | 2026-02-12 22:10:34 | utf8mb3_general_ci | stale/empty |
| crypto_whale_wallets | 0 | MyISAM | 2026-02-12 22:10:34 | utf8mb3_general_ci | stale/empty |

## Schema Details

### crypto_assets (14 rows)
- `id` int PK
- `symbol` varchar(20) unique
- `name` varchar(100)
- `asset_type` enum('major','altcoin','meme','defi','nft','layer2')
- `market_cap_category` enum('mega','large','mid','small','micro','nano')
- `is_meme` tinyint(1)
- `blockchain` varchar(50)
- `created_at` timestamp
- `updated_at` timestamp

**Assets**: BTC, ETH, BNB, SOL, ADA, XRP, DOGE, SHIB, PEPE, MATIC, ARB, OP, UNI, AAVE

### crypto_ohlcv (1,157,064 rows)
- `id` bigint PK
- `symbol` varchar(20)
- `timeframe` varchar(10) — all '1h'
- `timestamp` bigint (epoch ms)
- `open` decimal(18,8)
- `high` decimal(18,8)
- `low` decimal(18,8)
- `close` decimal(18,8)
- `volume` decimal(24,8)

**Coverage**: 14 symbols × ~82,648 bars each ≈ full 1h coverage Jan 2025 – Mar 2026

### crypto_exchange_netflow (20 rows, stale since Feb 2026)
- `id` int PK
- `blockchain` varchar(20)
- `exchange_name` varchar(50)
- `netflow_24h` decimal(20,8)
- `netflow_7d` decimal(20,8)
- `calculated_at` timestamp

**Exchanges**: Binance, Coinbase, Kraken, Huobi (ETH netflow only)

## Data Quality Notes

1. **Live feed only for OHLCV**: `crypto_ohlcv` updated 2026-11-18 (current); netflow frozen since Feb 2026
2. **Indicator pipeline empty**: `crypto_indicators`, `crypto_patterns`, `crypto_signals` all 0 rows — no technical analysis pipeline active
3. **Whale tracking dead**: `crypto_whale_movements`, `crypto_whale_wallets` empty since Feb 2026
4. **No dedicated crypto DB**: All tables live in `ejaguiar1_stocks`; no separate `ejaguiar1_crypto` database found
5. **MyISAM legacy**: `crypto_exchange_netflow`, `crypto_whale_*` use MyISAM (legacy, no FK support)

## Recommendations

1. **Reactivate netflow**: Restart ETH exchange netflow ingestion (last update Feb 16, 2026)
2. **Build indicator pipeline**: Populate `crypto_indicators` (SMA, EMA, RSI, MACD) from OHLCV
3. **Signal generation**: Implement pattern detection → `crypto_signals` for trading strategies
4. **Archive dead tables**: Drop or archive `crypto_whale_movements`, `crypto_whale_wallets` (0 rows, 9 months stale)
5. **Migrate to InnoDB**: Convert `crypto_exchange_netflow` to InnoDB for consistency
6. **Verify crypto_ohlcv completeness**: Check for gaps in 1h bars per symbol