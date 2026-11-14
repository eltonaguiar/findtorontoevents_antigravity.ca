# CRYPTO — Quick-Win Fix Proposals

Verified 2026-11-14 (live payload). Micro-audit for the CRYPTO asset class.

## Class Verdict

**ALIVE** — curated picks are live and moving (NEARUSDT +2.74%), but the `active_raw` feed is buried under ~3k zombie/zero/null rows that poison any class-level metric.

## Evidence

- Active curated picks: NEARUSDT +2.74% live; XRPUSDT / BTCUSDT pinned to entry (0%) while Binance live shows +1.28% / +0.95% (BTC 66,300 vs dash 65,672; XRP 0.9842 vs 0.9716).
- `active_raw` crypto: n=3,577; 3,085 older than 7d; 3,170 null `current_price`; 3,322 pnl=0; 3,100 EXPIRED.
- Zombie factory: `inverse_mutations`/`inverse_luxalgo_confluence` ≈2,267 rows, 20 symbols, daily re-emission since 2026-05-23.
- Garbage: XRPUSDT SHORT entry=0.0 (2026-11-14T13:54, source `prediction_market_consensus`); BTCUSDT entry 0.3322/1.334; ETHUSDT 0.092.
- 218 duplicate ids; 55 ids appear in both `active_raw` and `recent_closed` with conflicting status; 12 `LOST` rows with positive pnl; SL-above-entry rows.

---

## Quick Wins

### QW-C1 — Reject zero/tiny-entry garbage at resolution
- **Problem:** `prediction_market_consensus` and other sources emit XRPUSDT SHORT entry=0.0 and BTCUSDT 0.3322/ETHUSDT 0.092 entries that flow straight into the active feed.
- **Fix:** In `_extract_pick_fields`, treat `entry <= 0` or `entry < 1e-3 * symbol_price` as invalid: skip/flag the row instead of accepting 0.0 (mirror the `_snapshot_prediction_market_entry` guard that already refuses `current_price <= 0`).
- **Impact:**High / **Effort:** Low / **Risk:** Low.
- **Target file(s):** `audit_trail/universal_pick_resolver.py` (`_extract_pick_fields` ~line 802, `_snapshot_prediction_market_entry` ~line 872). Verified.

### QW-C2 — Quarantine zombie feed rows at ingestion
- **Problem:** `inverse_mutations`/`inverse_luxalgo_confluence` re-emit ~2,267 EXPIRED/zero/null rows daily (entries ids timestamped per-day), flooding `active_raw` (3,085 older than 7d).
- **Fix:** In the dashboard feed registry, drop `inverse_*` rows that are EXPIRED, have `current_price=None`, `pnl=0`, or are older than a 7-day gate before they reach `active_raw`.
- **Impact:** High / **Effort:** Low–Medium / **Risk:** Medium (must not drop genuine open inverse picks — gate on EXPIRED/null, not on symbol).
- **Target file(s):** `audit_trail/dashboard_generator.py` (feed registry line ~4062 wires `alpha_engine/data/inverse_picks.json`); emitter side `alpha_engine/inverse_loser_mutations.py` (id stamp line ~231). Verified.

### QW-C3 — Refresh stale current_price pinned to entry
- **Problem:** XRPUSDT & BTCUSDT `current_price` are pinned to entry (0%) while Binance live shows real moves (+1.28%/+0.95%) — live panel reads flat by construction.
- **Fix:** After resolution, backfill `current_price` for open crypto picks from a live Binance price (failover yfinance) instead of defaulting to entry when the payload price is null/stale.
- **Impact:** High / **Effort:** Medium / **Risk:** Medium (rate limits; cache per symbol).
- **Target file(s):** `audit_trail/universal_pick_resolver.py` (`_per_pick_price` ~line 693); `audit_trail/fetch_stock_prices.py` (add Binance path). Verified.

### QW-C4 — Dedupe + resolve cross-bucket conflicts
- **Problem:** 218 duplicate ids, and 55 ids exist in both `active_raw` and `recent_closed` with conflicting status (e.g. EXPIRED vs OPEN).
- **Fix:** Dedupe by `id` (keep the newest/closed variant) in the merge/normalize step; log a conflict count so the duplicated pair is surfaced once.
- **Impact:** Medium / **Effort:** Low / **Risk:** Low.
- **Target file(s):** `audit_trail/dashboard_generator.py` (`_normalize_pick` / active-merge path). Verified.

### QW-C5 — Neutralize status/PnL contradictions
- **Problem:** 12 `LOST` rows carry positive pnl; SL-above-entry (or TP-below-entry for SHORT) rows render nonsensical PnL.
- **Fix:** Extend the `_heal_no_price_row` heal-on-load pattern to also flag rows where status direction contradicts pnl sign, and to reject SL/TP ordering violations (SL>entry for LONG, SL<entry for SHORT) by nulling the bad leg.
- **Impact:** Medium / **Effort:** Low / **Risk:** Low.
- **Target file(s):** `audit_trail/universal_pick_resolver.py` (`_heal_no_price_row` ~line 931). Verified.

---

## Notes
- All target files above verified to exist in this worktree. Binance-vs-dashboard price deltas from the Nov 14 live payload.
- Rows with no verified source are marked elsewhere; none in this file.
