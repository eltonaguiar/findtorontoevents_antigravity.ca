# B20 — Wire penny_picks feed into JSON_PICK_SOURCES (2026-05-02)

## Summary

`findstocks/portfolio2/data/penny_picks_latest.json` was emitted fresh daily
(weekdays 12:00 UTC) by `.github/workflows/penny-stock-picks.yml` but was NOT
registered in `JSON_PICK_SOURCES`. The dashboard never read it. This PR wires
the feed following the same pattern as `tradingagents` (PR #544) and
`skyrocket_detector` (PR #546).

## Changes

### `audit_trail/dashboard_generator.py`

1. **New `top_picks` branch in `_extract_picks()`** (before the generic key loop):
   - Detects the `top_picks` key used by `penny_picks_latest.json`
   - Normalizes `rating` → `direction` (`STRONG_BUY`/`BUY` → `LONG`,
     `SELL`/`STRONG_SELL` → `SHORT`)
   - Sets `strategy = "penny_stock_screener"` if absent
   - Sets `asset_class = "EQUITY"` if absent (TSX-V and similar exchanges
     would otherwise be unclassified by the derive_asset_class heuristic)
   - Propagates parent-level `generated_at` into individual picks

2. **JSON_PICK_SOURCES registration** (after UEPS entry):
   ```python
   JSON_PICK_SOURCES.append((
       "penny_screener",
       "findstocks/portfolio2/data/penny_picks_latest.json",
       None,
   ))
   ```

### `tests/test_penny_picks_wireup.py` (new, 11 tests)

Pins the registration contract and schema normalization:
- `test_penny_screener_registered_in_json_pick_sources`
- `test_penny_screener_path_in_json_pick_sources`
- `test_penny_screener_no_closed_path`
- `test_extract_picks_handles_top_picks_key`
- `test_extract_picks_normalizes_direction_from_rating`
- `test_extract_picks_sets_strategy`
- `test_extract_picks_sets_asset_class_equity`
- `test_extract_picks_propagates_parent_timestamp`
- `test_extract_picks_preserves_existing_direction`
- `test_extract_picks_does_not_affect_picks_key_format`
- `test_live_penny_picks_file_extractable` (live file, skipped if absent)

## Wire-Up Rule compliance

Production caller: `_load_active_picks()` → `JSON_PICK_SOURCES` loop →
`_extract_picks()` → `_normalize_pick()` → `active.append(normalized)`.
This is the same path as every other registered source. NOT an orphan.

## Acceptance criteria

After merge + next dashboard rebuild:
- Picks from `penny_screener` source appear on /audit (modulo quality gates)
- All picks carry `direction=LONG` (screener is buy-only), `strategy=penny_stock_screener`,
  `asset_class=EQUITY`
- Existing /audit functionality unaffected

## Risk

LOW — pure additive registration. No gate changes. Quality gates (hc_filter,
passes_active_gate) handle legitimacy assessment separately.

## Refs

- Queue: `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` §4 B20
- Feedback docs: `reports/feedback/B20-*.md`
- Related: PR #544 (tradingagents), PR #546 (skyrocket_detector), PR #582 (ueps)
