# OHLCV Deep Backfill — 2026-06-09

## Problem

`crypto_ohlcv` held only **~30 days** (720 bars) of 1h candles per symbol. Intrabar re-resolution (`tools/reresolve_intrabar.py`) and `intrabar_ohlcv_replay.py` could not validate picks older than that window — a **P0 measurement blocker** for proving statistical edge.

## Change

Extended `tools/refresh_crypto_ohlcv.py`:

- **Binance mirror failover** (`api`, `api1`, `api2`, `api3`)
- **`--days N`** — paginated deep backfill (1000-bar chunks)
- **`--top-symbols N`** — prioritize symbols by `trading_picks` volume

## Usage

```bash
# Preview
python3 tools/refresh_crypto_ohlcv.py --dry-run --days 180 --top-symbols 80

# Write to DB
python3 tools/refresh_crypto_ohlcv.py --execute --days 180 --top-symbols 80
```

## Verification

```bash
python3 -c "
import pymysql
from tools.db_env import get_stocks_creds
c=pymysql.connect(**get_stocks_creds()); cur=c.cursor()
cur.execute(\"SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp) FROM crypto_ohlcv WHERE symbol='BTCUSDT' AND timeframe='1h'\")
print(cur.fetchone())
"
```

Expect **~4320 bars** per symbol for 180 days.

## Run log (2026-06-09)

| Run | Symbols OK | Failed | Rows upserted | BTCUSDT bars |
|-----|------------|--------|---------------|--------------|
| Pass 1 (top 80) | 64 | 16 (`*-USD` alias + HYPEUSDT) | 227,462 | 4320 (~180d) |
| Pass 2 (after `-USD` normalize fix) | 78 | 2 (HYPEUSDT, GBP-USD forex) | 3,756 | — |

Intrabar dry-run after pass 1: **15,021 replayed**, 1,177 no_data, true WR **39.7%** (orig 47.1%). Report: `reports/reresolve_intrabar_latest.json`.

## Next step (operator greenlight)

After backfill completes: `python3 tools/reresolve_intrabar.py` (dry-run) → review → `--apply` with backup.
