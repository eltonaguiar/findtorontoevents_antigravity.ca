# 2026-05-31 — UNKNOWN asset_class backfill migration (ejaguiar1_stocks)

**Goal #1** — clean per-asset-class WR/PF on `/audit` by eliminating the
UNKNOWN cohort in `at_signal_outcomes`.

## Context

Peer **zoocode** confirmed via live DB query that
`ejaguiar1_stocks.at_signal_outcomes` carries **14,596 rows with
`asset_class = 'UNKNOWN'`**. These rows pollute every per-class panel on
`/audit` and silently drop trades from the cohort denominators used by
the money-maker verdict.

Two-layer fix:

1. **Dashboard layer (PR #103)** — `audit_trail/dashboard_generator.py:8104`
   `_coerce_asset_class` guard catches future writes that arrive with
   `UNKNOWN`/empty and re-derives from the symbol + source hints.
2. **Database layer (this migration)** — backfills the legacy 14,596-row
   backlog using the same symbol-pattern rules as `_derive_asset_class`
   (`audit_trail/dashboard_generator.py:3463-3546`).

## File

`tools/migrations/20260531_backfill_unknown_asset_class.sql`

Idempotent: every `UPDATE` is gated on `asset_class IN ('UNKNOWN','')`
so re-running it on a partially-backfilled table is safe.

## Patterns covered

| Class     | Rule                                                             |
|-----------|------------------------------------------------------------------|
| CRYPTO    | `%USDT`, `%USDC`, `%BUSD`, `%-USD`, `%PERP`, `BTC%`, `ETH%`, bare-ticker allowlist (BTC/ETH/SOL/…) |
| FOREX     | `%=X` or 6-char major pair (EURUSD, USDJPY, …)                   |
| COMMODITY | XAU/XAG/XPD/XPT prefixes + `%=F` (excluding index futures)        |
| FUTURES   | `ES=F`, `NQ=F`, `YM=F`, `RTY=F`, `VX=F`, `DXY`                   |
| BOND      | TLT/IEF/SHY/AGG/LQD/HYG/BND/TIP/MUB/EMB/… (mirrors `_AC_BOND_SYMBOLS`) |
| ETF       | SPY/QQQ/DIA/IWM/VTI + sector SPDRs (mirrors `_AC_ETF_SYMBOLS`)    |
| EQUITY    | Fallback for 1-5 char `[A-Z]+` tickers not claimed above          |

## Operator instructions

This file is **NOT executed by CI**. Run it once manually:

```bash
# 1. Backup
mysqldump ejaguiar1_stocks at_signal_outcomes \
  > /tmp/at_signal_outcomes_backup_20260531.sql

# 2. Apply migration
mysql ejaguiar1_stocks < tools/migrations/20260531_backfill_unknown_asset_class.sql \
  | tee /tmp/backfill_20260531.log

# 3. Verify
#    - PRE_BACKFILL row should show UNKNOWN ≈ 14,596
#    - POST_BACKFILL row should show UNKNOWN ≪ 14,596 (residual = unmatched symbols)
#    - RESIDUAL_UNKNOWN_SAMPLE lists the top 25 unmatched symbols for a
#      follow-up patch if any cluster is material.
```

## Acceptance

- `/audit` per-class panels stop showing the UNKNOWN cohort.
- `pf_registry.by_asset_class_policy_clean_net` denominators rise to match
  the true post-M-067 cohort (peer zoocode flagged ~14.6k missing).
- The dashboard-layer fix in PR #103 already catches new writes; this
  migration cleans the backlog only.

## Risk register

- **Misclassification of penny-stock crypto-looking tickers.** Mitigated
  by the bare-ticker allowlist (we only sweep BTC/ETH/SOL/… not arbitrary
  3-letter symbols).
- **Index futures swept into COMMODITY.** Mitigated by the explicit
  carve-out (`NOT IN ('ES=F','NQ=F','YM=F','RTY=F','VX=F')`).
- **EQUITY fallback over-broad.** Restricted to `^[A-Z]{1,5}$` and
  excludes crypto/metals allowlists; residual UNKNOWN sample at end of
  migration surfaces anything that still needs human review.
