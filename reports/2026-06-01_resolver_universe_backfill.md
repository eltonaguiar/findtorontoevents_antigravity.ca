# Resolver Universe Backfill — 2026-06-01

## TL;DR

`at_pick_outcomes` was measuring only 1.16% of closed picks. Three root causes fixed; table now holds 37,884 rows with **100% overlap** to closed `trading_picks`. Per-class strategy measurement is finally trustworthy.

## Before / After

| Metric | Before | After |
|---|---:|---:|
| `at_pick_outcomes` total rows | 402 | **37,884** |
| Overlap with closed `trading_picks` | 0 | **34,701** (100%) |
| MAX(`resolved_at`) | 2026-06-01 00:59 | 2026-06-01 14:33 |

## Root causes uncovered + fixed

1. **Two parallel pick universes** — `at_pick_outcomes` (resolver, JSON-derived hex-no-dash IDs) and `trading_picks` (live scanners, UUID-with-dashes) shared **zero** pick_ids. Joining for per-class analytics produced empty results.
2. **`pick_id char(36)` too narrow** — closed picks from live scanners use 37–65 char composite IDs (e.g. `kilo_btcusdt_long_20260531_120000`), silently dropped by `INSERT IGNORE` against a `char(36)` column. Widened to `varchar(100)`.
3. **`closed_at` missing on 27,291 closed picks** — 99.8% of `TIME_EXIT` rows in `trading_picks` had NULL `closed_at` despite a non-NULL `updated_at`. Backfill used `COALESCE(closed_at, updated_at, created_at)` as `resolved_at`.

## Backfill provenance (`resolver_version`)

| Tag | Rows | Description |
|---|---:|---|
| `universal_v2` | 402 | Original (pre-backfill) via `audit_trail/universal_pick_resolver.py` |
| `backfill_2026-06-01` | 3,984 | Pass 1: closed_at NOT NULL, char(36)-fitting IDs |
| `backfill_updated_2026-06-01` | 7,891 | Pass 2: COALESCE for NULL closed_at |
| `backfill_widened_2026-06-01` | 25,607 | Pass 3: after ALTER pick_id → varchar(100) |
| **Total** | **37,884** | |

## Per-class verdict (now measurable)

| Class | n_decisive | WR% | PF | Tier verdict |
|---|---:|---:|---:|---|
| CRYPTO | 5,348 | 49.8 | 1.09 | T3-borderline (coinflip with small positive PF) |
| FOREX | 2,463 | 40.4 | 2.17 | Asymmetric — wins 2-3× bigger than losses |
| COMMODITY | 872 | 35.4 | 0.39 | NOT_READY (negative expectancy) |
| EQUITY | 162 | 41.4 | 0.52 | NOT_READY |
| ETF | 35 | 11.4 | 1.13 | INSUFFICIENT_DATA |
| BOND | 28 | 14.3 | 1.50 | INSUFFICIENT_DATA |
| FUTURES | 26 | 19.2 | 10.34 | INSUFFICIENT_DATA + fat-tail artifact |

**0 of 7 classes meet Tier 2** (PF>1.5, WR>50%, MDD<20%). FOREX is the only class showing asymmetric edge worth investigating (PF 2.17 despite sub-50% WR).

## Notable source-level findings

| Source | n | WR% | PF | Note |
|---|---:|---:|---:|---|
| mega_mutation | 283 | 65.4 | 3.33 | Kilo's "PROMISING" candidate — partially confirmed but n<500 |
| prediction_market_agents | 2,319 | 86.8 | 32.17 | Either real edge or measurement artifact — investigate |
| multi_asset_copytrader | 14,932 | 37.0 | 1.12 | High-volume, mediocre |
| non_crypto_consensus | 2,789 | 50.7 | 0.81 | Coinflip + losing PF |
| polymarket_whale_tracker | 1,497 | 0.0 | 0.0 | All-EXPIRED (never decisively resolved) |
| short_dominant_engine | 1,534 | 100.0 | ∞ | Suspiciously perfect — investigate |

## Safety

- Backup: `ejaguiar1_backups.at_pick_outcomes_pre_backfill_20260601_1500` (402 rows pre-state).
- ALTER widened pick_id without data loss (varchar(100) is a superset).
- All inserts used `INSERT IGNORE` — idempotent, no overwrites of the original 402 `universal_v2` rows.
- All four resolver_version tags preserved for provenance and selective rollback.

## Next layer

1. Patch the live writer so new `TIME_EXIT` rows set `closed_at` directly (eliminates need for `updated_at` fallback going forward).
2. Investigate `prediction_market_agents` (PF 32) and `short_dominant_engine` (100% WR) — likely measurement bugs.
3. Per-class fixed-window WR/PF / DSR / PBO once cohort filters defined.
4. Wire `audit_trail/universal_pick_resolver.py` to also read from `trading_picks` (single source of truth) so the next live resolver tick doesn't introduce another universe.
