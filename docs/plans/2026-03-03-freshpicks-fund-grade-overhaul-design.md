# FreshPicks Fund-Grade Overhaul — Design Document

**Date:** 2026-03-03
**Status:** Approved
**Problem:** #freshpicks Discord feed is noisy — massive duplication (same picks every 5-30 min from 5 independent senders), static price ladders, confidence drift, low-quality scout picks (40% conf), no expiry/sizing fields.

## Root Cause

Five independent workflows call `send_fresh_pick()` directly:
1. `cross-aggregator.yml` (every 5 min) — has workflow-level dedup via `freshpicks_consensus_sent.json`
2. `alpha-engine-live.yml` (every 30 min) — **no dedup**
3. `deploy-riseoftheclaw.yml` / KIMI (every 15 min) — has `freshpicks_sent.json` per-system
4. `kimi-feb172026-live.yml` — **no dedup**
5. `claude-gainer-tracker.yml` — **no dedup**

`freshpicks_notify.py:send_fresh_pick()` has **zero gates** — it sends whatever it's given.

A parallel agent added dedup + quality filters + dynamic TP/SL + Kelly sizing to `send_top_picks_now.py`, but that only covers the manual/consensus path. The 4 workflow senders bypass all of it.

## Architecture: Centralized Gate (Approach A)

### Before (broken)
```
alpha-engine ──→ send_fresh_pick() ──→ Discord  (no gates)
KIMI ──────────→ send_fresh_pick() ──→ Discord  (no gates)
KIMI-feb17 ────→ send_fresh_pick() ──→ Discord  (no gates)
claude-gainer ─→ send_fresh_pick() ──→ Discord  (no gates)
cross-agg ─────→ send_fresh_pick() ──→ Discord  (workflow dedup only)
```

### After (fixed)
```
ALL callers ──→ send_fresh_pick() ──→ [GATE] ──→ Discord
                                        │
                                        ├─ G1: Dedup (30-min cooldown per symbol+direction)
                                        ├─ G2: Confidence floor (>= 0.65)
                                        ├─ G3: Losing strategy filter (WR >= 48%)
                                        ├─ G4: R:R sanity (>= 1.0)
                                        ├─ G5: Dynamic TP/SL (ATR-based when static detected)
                                        ├─ G6: Enrich: Kelly sizing + expiry field
                                        └─ G7: Rate cap (max 8 picks per 60-min window)
```

## Gate Details

### G1: Dedup / Throttle
- Key: `symbol + direction` (normalized — BTC-USD/BTCUSD/BTCUSDT all map to same key)
- Cooldown: **30 minutes** per symbol+direction
- Exception: if entry/TP/SL changed (price levels actually moved) → allow through
- State file: `data/freshpicks_gate_state.json` (persisted via git commit in workflows)
- Prune: entries older than 24h auto-removed

### G2: Confidence Floor
- Reject if `confidence < 0.65` (handles both 0-1 and 0-100 scales)
- This eliminates the 40% "scout" picks that dominate the feed

### G3: Losing Strategy Filter
- Load system's `closed_picks.json` if available
- Compute rolling WR over last 20 trades
- Block if WR < 48% (negative expected edge at any R:R)
- Known bad strategies from aggregator's BANNED_STRATEGIES list also blocked

### G4: R:R Sanity
- Require `risk:reward >= 1.0`
- Computed after G5 (dynamic TP/SL) so ATR-adjusted levels are used

### G5: Dynamic TP/SL
- Detect static ladders: `abs(tp - entry) / entry` is within 0.1% of round percentage (5%, 10%, 15%)
- OR TP/SL identical to previous send for same symbol (from dedup state)
- Override with: `SL = entry ± 1.5 * ATR`, `TP = entry ± 2.5 * ATR`
- ATR from Binance klines API (free, no key, 14-period hourly)
- Fallback: 2% of price if API unavailable

### G6: Enrich — Kelly Sizing + Expiry
- Kelly fraction: `f = (2*conf - 1) * edge / vol^2`, capped at 2% of portfolio
- Expiry: `now + 15 minutes` — shown as Discord relative timestamp `<t:...:R>`
- Both added as embed fields

### G7: Rate Cap
- Max 8 picks per 60-minute rolling window (across all systems)
- Prevents burst-sending when multiple workflows fire simultaneously
- Tracked in same state file as G1

## Files to Create/Modify

### New: `cross_aggregation/freshpicks_gate.py`
Shared gate logic module containing:
- `FreshPicksGate` class with all 7 gates
- Dedup cache load/save
- ATR fetcher (Binance klines)
- Kelly sizing
- Static ladder detection
- Rate limiter

### Modify: `cross_aggregation/freshpicks_notify.py`
- Import `FreshPicksGate`
- Add gate check at top of `send_fresh_pick()` — before any embed building
- Add sizing + expiry fields to embed
- Keep existing functionality (stats, trust badges, sandbox routing) untouched

### Modify: `scripts/send_top_picks_now.py`
- Replace inline dedup/quality/sizing logic with import from `freshpicks_gate.py`
- Keeps the consensus-specific loading logic

### Modify: `.github/workflows/cross-aggregator.yml`
- Add `data/freshpicks_gate_state.json` to `git add` step

### Modify: Other workflow YAMLs (4 files)
- Add `data/freshpicks_gate_state.json` to `git add` step in each
- No logic changes needed — gate is inside `send_fresh_pick()`

## Discord Embed Changes

New fields added to every freshpicks embed:
- **Size** — `"Size: 1.4% of portfolio"` (from Kelly)
- **Expires** — `<t:1709500000:R>` (Discord relative timestamp)
- **R:R** — `"1:2.50"` (if TP/SL available)

## State Persistence

`data/freshpicks_gate_state.json` structure:
```json
{
  "dedup": {
    "BTCUSDT__LONG": {
      "sent_at": "2026-03-03T18:00:00+00:00",
      "entry": 67000,
      "tp": 72000,
      "sl": 64000,
      "confidence": 0.82,
      "system": "alpha_engine"
    }
  },
  "rate_window": [
    "2026-03-03T17:55:00+00:00",
    "2026-03-03T17:58:00+00:00"
  ]
}
```

## Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| Picks per hour (same symbol) | 6-12 | 1-2 |
| Low-confidence picks (< 65%) | ~60% of feed | 0% |
| Losing strategy picks | Present | Filtered |
| Sizing info | None | Kelly fraction shown |
| Expiry info | None | 15-min countdown |
| Static TP/SL | ~40% of picks | 0% (ATR-replaced) |
