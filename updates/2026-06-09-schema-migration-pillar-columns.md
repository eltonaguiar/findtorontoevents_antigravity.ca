# Schema Migration: 4 Pillar Columns Added (2026-06-09)

## What was done

Added 4 new columns to **both** `at_pick_outcomes` (39,908 rows) and `trading_picks` (47,216 rows) to support the 5-pillar reliability framework (P2 regime / P3 execution / P5 sector / P3 volatility):

| Column | Type | Nullable | Default | Pillar unlocked |
|---|---|---|---|---|
| `market_regime_id` | `ENUM('BULL','BEAR','SIDEWAYS','HIGH_VOL','RISK_OFF','UNKNOWN')` | NO | `UNKNOWN` | **P2** (regime attribution) |
| `sector` | `VARCHAR(64)` | YES | NULL | **P5** (concentration / effective beta) |
| `volatility_atr` | `DECIMAL(10,4)` | YES | NULL | **P3** (break-even slippage / TP-SL quality) |
| `execution_slippage_pct` | `DECIMAL(8,4)` | YES | NULL | **P3** (slippage per fill) |

**Total: 8 ALTER TABLE statements (4 columns × 2 tables).**

## What was NOT done (intentional, per user direction)

- **No backfill.** All `sector` / `volatility_atr` / `execution_slippage_pct` rows are still NULL. All `market_regime_id` rows are `UNKNOWN` (the default).
- The migration is a **pure schema-only change** — it does not modify any existing row's primary data.
- Picking up the backfill is deferred to a follow-up agent/session (yfinance rate-limits on 500+ tickers would block for hours; a different runtime context is the right home for it).

## How it was done

- Tool: `tools/migrate_add_pillar_columns.py`
- **Idempotent** — pre-checks `INFORMATION_SCHEMA.COLUMNS` and skips any column that already exists. Re-running it is a no-op (verified: 2nd run reported `added=0, skipped=8`).
- **Dry-run by default** — must pass `--apply` to execute. The dry-run produces the exact `ALTER TABLE` statements it would execute, so you can review before committing.
- Connects via the canonical `tools.db_env.get_stocks_creds()` resolver (no env-only creds, no silent auth fail — fixes the same class of bug that bit `tools/portfolios/export_json.py` on 2026-06-09).

## Verification (post-migration)

- ✅ Row counts unchanged: `at_pick_outcomes` 39,908, `trading_picks` 47,216
- ✅ All 4 new columns present on both tables with expected DDL
- ✅ `sector` / `volatility_atr` / `execution_slippage_pct` non-NULL rows = 0 (clean slate for backfill)
- ✅ `market_regime_id` value distribution = `{UNKNOWN: <full row count>}` (no real classification yet)
- ✅ Idempotency: re-running the tool is a no-op (8/8 columns skipped)

## Follow-up: backfill plan (deferred)

When a future session picks this up, the work splits into 4 parts, ordered by lowest-risk-first:

1. **`market_regime_id` backfill (cheapest)**
   - Source: existing OHLCV data in `crypto_ohlcv` + `stock_ohlcv` + (any forex/commodity OHLCV)
   - Rule (proxy): compute 3m return + 20d ATR / close ratio. Map to `BULL` / `BEAR` / `SIDEWAYS` / `HIGH_VOL` / `RISK_OFF` via fixed thresholds. Backfill ~80k rows in pure SQL, no external API calls.
   - Status: rules need sign-off; same heuristics as the academic Edge Hunt reports (2026-06-05/06).

2. **`sector` backfill (medium cost)**
   - Equity: copy from `stock_assets.sector` (pre-existing backfill source discovered during pre-flight — no yfinance call needed).
   - Crypto: hardcoded map (BTC/ETH = L1, stables = stable, alts = altcoin-L1/L2/defi, etc.).
   - Forex: bucket map (majors = major-fx, crosses = cross-fx, exotics = exotic-fx).
   - Commodity: hardcoded (energy / metal / agricultural).
   - Status: maps need to be authored; the 4 buckets are ~30-50 lines of Python.

3. **`volatility_atr` backfill (medium cost)**
   - Compute 14d ATR from `crypto_ohlcv.high/low/close` and `stock_ohlcv.high/low/close` (both already exist; 454k and 111k rows respectively).
   - Backfill per `(symbol, date)` join against `at_pick_outcomes.entry_time` (or `trading_picks.created_at`).
   - Status: SQL joins are straightforward; need to write a batched script to avoid timeouts.

4. **`execution_slippage_pct` backfill (highest cost)**
   - Requires actual fill-price data; not present in any current table.
   - Options: (a) compute from `trading_picks.entry_price` vs an external mid-price snapshot at fill-time, (b) leave NULL and proxy via 0.05% default for paper picks / 0.10% for live picks, (c) wire the price-failover chain to log the slippage at insert-time going forward.
   - Status: needs a decision; recommend option (b) for backward compatibility + option (c) going forward.

## Impact on the 5-pillar framework

Before this migration: **1 of 5 pillars (P4 Data) buildable end-to-end** from existing schema.
After this migration: **5 of 5 pillars addressable** in SQL — but only P4 will return real numbers until the backfill above runs. The picks-now "Reliability" tab can be built now as **P4 full + P1/P2/P3/P5 as `pending_backfill` stubs**, so the page is self-diagnosing from day one.

## Files

- Added: `tools/migrate_add_pillar_columns.py` (157 lines, idempotent, dry-run-by-default)
- Added: `updates/2026-06-09-schema-migration-pillar-columns.md` (this file)
