# Audit TRACK: super-signal `via` is source_system, not strategy id

## What users saw

Active picks with strategies like **`super signal (super) via kimi`** showed TRACK tooltips such as **n=0** on the symbol+strategy resolved ledger, **+3 pair closes**, and strategy-wide forward WR — implying “no history” for that combination.

## Root cause

In `cross_aggregation/super_signal.py`, the display name is built as:

- `strategy` = `super signal (tier) via {source_system of best feeder pick}`
- `via …` repeats the feeder’s **`source_system`** (e.g. `kimi`), **not** that pick’s **`strategy`** field (the real algo id on closed trades).

The dashboard’s symbol ledger (`_build_strategy_symbol_track_stats`) keys rows by **`(strategy, symbol)`** on closed picks. Historical KIMI closes store **algo names** in `strategy` and **`kimi` / `kimi_live_signals`** in `source_system`. Looking up **`kimi` as a strategy string** therefore finds **no rows** — a **keying bug**, not proof the symbol was never traded.

Excluded or stale closes are a separate, smaller issue: `_filter_valid_resolved_picks` drops rows without usable `pnl_pct` or certain non-performance exits; those never enter `resolved_closed` or the track maps.

## Fix (Python)

**File:** `audit_trail/dashboard_generator.py`

1. **`_build_source_symbol_track_stats`** — Same win/loss rules as strategy+symbol stats, keyed by **`source_system + symbol`**.
2. **`_super_signal_via_feeder_candidates`** — Tries aliases (e.g. `kimi` ↔ `kimi_live_signals`) for common naming drift.
3. After existing strategy-key and leaderboard-candidate fallbacks, **super-signal rows** resolve symbol track stats from **`_source_symbol_track_map`** using the `via` token as **system**.
4. **`track_level` / `_sym_trades`** — For super-signal labels, also count closes on **`resolved_closed`** where **`source_system`** matches feeder candidates and **symbol** matches, so “symbol” vs “strategy” display stays consistent.

## Verification

- Regenerate dashboard payload (CI / pipeline) and confirm a **`super signal … via kimi`** row on e.g. BNBUSDT shows non-zero **`sym_track_*`** when **`resolved_closed`** contains KIMI rows for that symbol.
- Tooltip may show **`Track key matched via source_system:kimi`** (or alias).

## Deploy

Dashboard JSON/HTML flow as usual; no separate FTP step for Python-only change until the next generator run.
