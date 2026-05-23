# B7 Multi-AI Feedback — Codebuff (Proxy) — 2026-05-02

## Item reviewed
B7 — CFTC COT live-wire prerequisite audit PR

## A. Confirmed assumptions

1. **`_extract_picks` is the right hook.** Every JSON_PICK_SOURCES entry passes through
   `_extract_picks` → `_normalize_pick`. Adding a `scanner == "cot_positioning"` branch
   mirrors the `top_picks` branch added for B20 penny_picks at lines 6842-6863.

2. **`VERIFIED_STRATEGIES` already contains `cot_positioning` and
   `cftc_cot_commercial_signal`** (lines 4833-4834). This means quality-gate code that
   checks `strategy in VERIFIED_STRATEGIES` will accept COT picks without additional
   changes.

3. **No existing test file for COT.** `tests/test_cot*` returns empty. A new
   `tests/test_cot_schema_wireup.py` is the right place, following the
   `tests/test_penny_picks_wireup.py` and `tests/test_ueps_dashboard_wireup.py` naming
   convention.

4. **`cot_positioning.py` __main__ schema is the root cause.** The function
   `cot_positioning_strategy()` (lines 138-183) writes `symbol`, `direction`,
   `asset_class` etc. The `__main__` block (lines 195-232) writes only `pair`, `signal`,
   `confidence`, `percentile`. Fixing `__main__` to write full schema is a 10-line
   change.

## B. Surfaced contradictions / blockers

1. **`asset_class` in `cot_positioning_strategy()` is lowercase `"forex"` not uppercase
   `"FOREX"`.** Line 179: `"asset_class": "forex"`. The `_infer_asset_class()` normalizer
   in dashboard_generator.py handles both via `.upper()` in the normalize path, but the
   adapter should explicitly set `"FOREX"` (uppercase) for consistency.

2. **No closed-picks path for COT.** COT picks have no `closed_picks` file. The
   JSON_PICK_SOURCES entry should use `None` for the closed path (as with tradingagents,
   ueps, penny_screener). This is correctly scoped.

3. **`timeframe` is `"1w"` in the function output but COT picks might be incorrectly
   classified by `_infer_timeframe`.** The classifier sees `"1w"` and maps it to SWING.
   This is correct for weekly COT signals.

4. **`source_system` set in the raw pick dict may be overridden.** `_normalize_pick`
   accepts `source_system` as a parameter (the sys_name from JSON_PICK_SOURCES, which
   would be `"cot_positioning"`). The pick dict also having `source_system` is redundant
   but harmless. Recommend NOT setting it in the adapter to avoid confusion — let
   `sys_name` from JSON_PICK_SOURCES be the authoritative source.

## C. Recommended deltas

1. **Uppercase `asset_class`.** Set `"FOREX"` not `"forex"` in the adapter.
2. **Do not set `source_system` in the adapter dict.** It's redundant with `sys_name`.
3. **Use `timedelta` from `datetime` stdlib** for the content-freshness check — no
   external dependencies.
4. **Test: assert `"cot_positioning"` in `_FRESHNESS_REQUIRED_HOURS`.** Prevents a
   future edit from accidentally removing the guard.
5. **Test: the adapter maps `"SELL"` → `"SHORT"` and `"BUY"` → `"LONG"` correctly.**
   `_normalize_pick` handles this in its `direction` normalization, but confirming the
   adapter sets `direction` is good defense.

## D. Net verdict

**ready-to-ship** with the deltas above (all minor). The PR is well-scoped, low-risk,
and produces zero net behavior change until the COT cron refreshes the data (freshness
guard blocks stale 47d content). Approve after applying the uppercase `asset_class`
fix and removing redundant `source_system` from the adapter dict.
