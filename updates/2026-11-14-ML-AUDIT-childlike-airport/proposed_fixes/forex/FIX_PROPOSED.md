# Proposed fixes — FOREX asset class

**Status:** proposed — pending review/implementation  
**Asset class:** FOREX (`ml_gatekeeper ASSET_CLASS_MAP FOREX:1`)  
**Audit source:** ML pick audit, live_picks.db snapshot 2026-11-14

## 1. Forex-specific findings

- **4 active forex picks** are stale: active since `2026-05-25` (~172 days), still marked `ACTIVE`, with `current_price = None` and `pnl = 0.0` (never resolved / zombie rows).
- Closed coverage is acceptable: FOREX 1,097 closed picks + 120 lowercase `forex` closed picks (case-duplicated class label in `asset_class` column).
- Active picks were never refreshed — no current price, no PnL, no exit events emitted for the 4 stale rows.
- Forex strategies exist in `alpha_engine/` but active-pick refresh is not tied to scanner re-runs.

## 2. Quick wins for forex

- Backfill `asset_class = 'FOREX'` (uppercase, consistent) for all forex rows in `live_picks.db` and `closed_picks.db` using `alpha_engine/asset_class.py` `FOREX_CODES`.
- Lowercase `forex` (120 closed rows) → normalize to `FOREX` so gatekeeper lookup (`ASSET_CLASS_MAP.get(asset_class.upper())`) still works but schema stays consistent.
- Emit exit events (TP/SL/time) for the 4 stale active picks using `audit_trail/universal_pick_resolver.py` so they leave the `ACTIVE` panel.
- Re-run forex scanners (`forex_smart_picks.py`, `fx_carry_vix_regime.py`, `fx_cot_extremes.py`, `fx_dxy_divergence.py`, `fx_kill_switch.py`, etc.) against live OANDA/yfx quotes to regenerate the active forex panel.
- Populate `strategy_stats` for forex strategy keys so ML gatekeeper scoring isn't null for forex picks.

## 3. Proposed fixes for forex

### 3.1 Refresh current_price/PnL for the 4 stale forex picks
- Target table: `live_picks` (and mirrored `closed_picks` history) in `live_picks.db`.
- Query: since `asset_class` lives in `metadata` JSON (not a top-level column), classify via Python `asset_class_from_symbol()` or `metadata LIKE '%forex%'`; target rows where status = `ACTIVE` and `current_price IS NULL OR pnl = 0.0`.
- Fetch live bid/ask from the same provider used by the scanners (OANDA/yfx failover via `forex_price_failover.py`).
- Update `current_price`, `pnl`, `pnl_pct`, `last_updated` per row; set `status = 'CLOSED'` or `'EXPIRED'` where age > max hold threshold.
- Record the fix in `updates/2026-11-14-ML-AUDIT-childlike-airport/forex_stale_active_fix.md` per the "Document Every Fix" rule.

### 3.2 Emit exit events
- Route the 4 resolved picks through `audit_trail/universal_pick_resolver.py` (TP/SL/time exit resolver).
- Append exit rows to `audit_trail/exit_events.json` (or the DB exit table) with `exit_reason ∈ {tp, sl, time, manual_stale_close}`.
- Remove resolved picks from `.picks.active` panel so they don't inflate `data_coverage.closed_without_regime` counts.

### 3.3 Re-run forex scanners
- Execute forex strategy batch: `forex_smart_picks.py`, `forex_carry_momentum_harvest.py`, `forex_carry_ppp.py`, `forex_cot_reversal.py`, `forex_price_failover.py`, `forex_strategies.py`, `forex_strategy_harness.py`, `forex_weekly_open_gap_fill.py`, `fx_asian_range_break.py`, `fx_carry_vix_regime.py`, `fx_cot_extremes.py`, `fx_dxy_divergence.py`, `fx_kill_switch.py`, `fx_overnight_reversal.py`, plus boosters `dxy_booster.py`, `usd_strength_scanner.py`.
- Gate new picks through `ml_gatekeeper/gatekeeper.py` (`ASSET_CLASS_MAP FOREX:1`) before inserting into `live_picks`.
- Respect `FOREX_CODES` frozenset (`alpha_engine/asset_class.py:22`) for symbol validation: EUR, GBP, USD, JPY, AUD, CAD, CHF, NZD, SEK, NOK, DKK, SGD, HKD, CNH, CNY, MXN, ZAR, TRY, INR.

### 3.4 Backfill asset_class via FOREX_CODES
- Run `alpha_engine/asset_class.py` classification over all picks missing/incorrectly cased `asset_class`.
- Map 6-char pairs (EURUSD → base/quote both in `FOREX_CODES`) and `=X` suffix symbols to `forex` per `asset_class_from_symbol()` (`alpha_engine/asset_class.py:141-156`) / `normalize_asset_class()` (`:214-230`). There is no `classify_asset_class()` function.
- Strategy-name hint fallback: `FOREX_STRATEGY_HINTS` (`alpha_engine/asset_class.py:90`) tags `forex`, `fx_`, `carry_trade`, `oanda`, `myfxbook`.

### 3.5 Populate strategy_stats
- Ensure `strategy_stats` has rows for each forex strategy key used by new picks (win rate, avg R, sample count).
- Null `strategy_stats` causes the ML gatekeeper to score forex picks as unproven; backfill from closed forex picks (1,097 + 120 rows).

## 4. Verification steps

1. Python check via `alpha_engine.asset_class.asset_class_from_symbol` on forex symbols (EURUSD, GBPJPY, USDJPY) → all return `'forex'`; count of `live_picks` rows with forex-classified metadata where status=`ACTIVE` → should be 0 stale; any remaining ACTIVE forex picks must have non-null `current_price` and `last_updated < 24h`.
2. Normalize closed-pick class casing: `FOREX` vs `forex` rows → single canonical uppercase class via `metadata` JSON.
3. Run `python3 -c "from alpha_engine.asset_class import asset_class_from_symbol; [print(s, asset_class_from_symbol(s)) for s in ['EURUSD','GBPJPY','USDJPY']]"` → returns `forex`.
4. Re-run gatekeeper on a sample forex pick → `asset_class_id == 1` (`ml_gatekeeper/gatekeeper.py:134`).
5. Confirm exit events exist for the 4 previously stale picks.
6. Re-run forex scanner batch and confirm new `ACTIVE` forex picks appear with fresh timestamps and populated `strategy_stats`.

## 5. Repo paths touched

- `alpha_engine/asset_class.py` — `FOREX_CODES` frozenset (line 22), `FOREX_STRATEGY_HINTS` (line 90), `asset_class_from_symbol()` (lines 141-156) / `normalize_asset_class()` (lines 214-230) forex classification
- `ml_gatekeeper/gatekeeper.py` — `ASSET_CLASS_MAP FOREX:1` (line 73), pick scoring (line 134)
- `audit_trail/universal_pick_resolver.py` — TP/SL/time exit emission for stale picks
- `alpha_engine/forex_smart_picks.py`, `forex_carry_momentum_harvest.py`, `forex_carry_ppp.py`, `forex_cot_reversal.py`, `forex_price_failover.py`, `forex_strategies.py`, `forex_strategy_harness.py`, `forex_weekly_open_gap_fill.py`
- `alpha_engine/fx_asian_range_break.py`, `fx_carry_vix_regime.py`, `fx_cot_extremes.py`, `fx_dxy_divergence.py`, `fx_kill_switch.py`, `fx_overnight_reversal.py`
- `alpha_engine/dxy_booster.py`, `usd_strength_scanner.py` — forex regime/strength boosters
- `live_picks.db` / `closed_picks.db` — stale active forex rows (4), case-normalization of `asset_class`
- `audit_trail/exit_events.json` — exit event append for resolved picks
- `updates/2026-11-14-ML-AUDIT-childlike-airport/forex_stale_active_fix.md` — fix documentation (mandatory per repo convention)

File written: `/home/eaguiar2015/findtorontoevents_antigravity.ca/updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/forex/FIX_PROPOSED.md`
