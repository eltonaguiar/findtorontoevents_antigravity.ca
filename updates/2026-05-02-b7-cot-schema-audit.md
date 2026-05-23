# B7 Prerequisite: COT Schema Audit + Fix — 2026-05-02

**PR:** fix/b7-cot-schema-audit-2026-05-02  
**Action item:** B7 prerequisite from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md`  
**Risk:** LOW (additive, zero net behavior change until cron refreshes the data)

## Problem

`alpha_engine/data/cot_signals.json` was generated on 2026-03-16 (47 days ago) and
used a simplified schema `{pair, signal, confidence, percentile}` incompatible with
the dashboard's `_extract_picks()` + `_normalize_pick()` pipeline. The source was also
not registered in `JSON_PICK_SOURCES`, so COT picks never reached the `/audit` dashboard.

Two root causes:

1. **`cot_positioning.py` `__main__` block** wrote a simplified schema. The module's
   `cot_positioning_strategy()` function (used by the scanner) correctly wrote full picks
   (`symbol`, `direction`, `strategy`, `asset_class`, etc.), but the `__main__` entrypoint
   (run directly to refresh `cot_signals.json`) wrote only `pair`/`signal`/`confidence`/`percentile`.

2. **No JSON_PICK_SOURCES entry.** `cot_positioning` was listed in `VERIFIED_STRATEGIES`
   and conceptually included in B7, but never wired into `JSON_PICK_SOURCES` — so
   `build_html()` never loaded the file.

## Investigation findings

| Finding | Detail |
|---------|--------|
| `cot_signals.json` content age | 47 days (2026-03-16 generated_at) |
| `cot_signals.json` file mtime | ~7 days (diverges from content age) |
| Schema in file | `{pair, signal, confidence, percentile}` — legacy |
| `_normalize_pick` handling | Partially OK — resolves `pair`→`symbol` and `signal`→direction, but `strategy` and `asset_class` are empty |
| `_FRESHNESS_REQUIRED_HOURS` | Not populated for `cot_positioning` — no mtime guard |
| JSON_PICK_SOURCES | Not registered — picks never loaded |
| COT cron | No workflow step calls `cot_positioning.py` directly; `forex-agent.yml` references `cot_positioning_forex` as a strategy filter name only |

## Changes

### `alpha_engine/cot_positioning.py`

`__main__` block now writes the full pick schema compatible with `_normalize_pick`:
- `symbol = pair + "=X"` (yfinance format)
- `direction = "SHORT"/"LONG"` (from signal)
- `strategy = "cftc_cot_commercial_signal"`
- `asset_class = "FOREX"`
- `timeframe = "1w"` (CFTC data is weekly)
- `generated_at` (fresh timestamp per run)
- COT-specific extras preserved: `pair`, `signal`, `percentile`, `cot_reason`, etc.

### `audit_trail/dashboard_generator.py`

Three additions:

1. **`_FRESHNESS_REQUIRED_HOURS["cot_positioning"] = 14 * 24`** — mtime-based gate.
   If `cot_signals.json` hasn't been written in 14 days, skip it entirely (no stale
   picks reach the dashboard).

2. **`_extract_picks` COT adapter** (inserted before the `top_picks` branch). When
   `data.get("scanner") == "cot_positioning"`:
   - Content-based freshness check: parses `generated_at` and returns `[]` if age > 14d.
     Handles the mtime ≠ content-age divergence case.
   - Maps legacy `pair` → `symbol` (adds `=X`), `signal` → `direction`, and sets
     `strategy`, `asset_class`, `timeframe` defaults.
   - Full new-format picks (from the fixed `__main__`) pass through unchanged.

3. **`JSON_PICK_SOURCES.append(("cot_positioning", "alpha_engine/data/cot_signals.json", None))`**
   — registers the source. Picks will be loaded once the cron refreshes the data.

### `tests/test_cot_schema_wireup.py` (new — 16 tests)

Covers:
- JSON_PICK_SOURCES registration (name + path + None closed-path)
- `_FRESHNESS_REQUIRED_HOURS` presence and ≥7-day threshold
- Stale data (47d) → returns `[]`
- Fresh data → returns picks
- Legacy schema adapter: `pair`→`symbol=X`, `SELL`→`SHORT`, `BUY`→`LONG`
- `strategy` = `"cftc_cot_commercial_signal"`, `asset_class` = `"FOREX"`, `timeframe` = `"1w"`
- Parent timestamp propagation
- New-format picks (already have `symbol`) pass through unchanged
- Module import + `COT_STRATEGIES` registry

## What this PR does NOT do (B7 proper)

This prerequisite PR deliberately **omits** setting `CFTC_COT_FETCHER_ENABLED=1` in
any workflow and **omits** adding a `python alpha_engine/cot_positioning.py` step to
`forex-agent.yml`. Those belong in B7 proper, which should ship once:

1. This prerequisite is merged and the schema is confirmed clean in production.
2. The forex-agent cron is verified healthy.
3. The 14-day shadow run starts and produces at least one cycle of fresh COT data.

## Current behavior after this PR

Until the COT cron runs next and refreshes `cot_signals.json`:
- The content-freshness guard returns `[]` for the stale 47-day-old file.
- Zero COT picks appear on `/audit` (correct — stale data is silent).

Once the cron runs and produces fresh data (within the 14-day window):
- COT picks appear on `/audit` tagged with `strategy=cftc_cot_commercial_signal`,
  `asset_class=FOREX`, `timeframe=1w`.
- The shadow-run 14-day observation period begins automatically.

## Wire-Up Rule compliance

`cot_positioning` is in `VERIFIED_STRATEGIES` (dashboard_generator.py:4834) and is
now registered in `JSON_PICK_SOURCES` (the production pick-loading path). The
strategy has documented historical WR 55-62% (see `alpha_engine/cot_positioning.py`
module docstring). Wire-Up Rule is satisfied.
