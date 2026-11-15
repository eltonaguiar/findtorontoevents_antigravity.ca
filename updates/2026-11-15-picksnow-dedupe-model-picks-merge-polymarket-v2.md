# 2026-11-15 — Picks-now pipeline fixes: Live PnL dedupe, model-picks merge, Polymarket v2 migration

## Summary

Three verified defects in the financial-prediction pipeline, fixed together:

| # | Symptom | Root cause (verified) | Fix |
|---|---------|----------------------|-----|
| 1 | `picks_now_live_pnl.json` served 4,390 rows with 10–30× duplicate picks (SGOV ×15, BND ×30, TLT ×10) | `picks_now_tracker` has no UNIQUE constraint; writers only guard per-symbol-per-UTC-day, so always-on picks accumulate one open row per day and never resolve (`resolve_picks_now.py` requires TP>0 AND SL>0 AND live OHLC bars). `live_pnl_tracker.build()` dumped **all** `exit_pnl_pct IS NULL` rows. | Dedupe in the exporter: one row per `(symbol, direction)`, newest (`generated_at DESC` first occurrence) kept. Raw count preserved as `n_rows_raw`. |
| 2 | finpredict-v4 model picks (VTI/TLT/SGOV/BND) silently wiped from `picks_now.json` every 06/12/18 UTC refresh; emitter output (`picks_now_model_finpredict_v4.json`) had **zero** pipeline consumers | `picks-now-refresh.yml` regenerates `picks_now.json` from scratch via `picks_now_professional.py` and commits only that file; `save_picks_to_db.py` reads only `picks_now.json`. The peer-added `model-picks-emission.yml` (01:22 UTC) ran the emitter but its picks never merged anywhere. | New `tools/merge_model_picks.py` re-appends model picks after each regeneration; wired into both workflows (merge → freshness assert → DB save ordering). Model JSON added to the refresh workflow's plumbing commit block. |
| 3 | Polymarket pipeline dead: copy-trader scraper got HTTP 410 everywhere (v1 retired), signal generator kept **0 of 500** markets | `copy_trader_intel/polymarket_scraper.py` used retired Data API v1 + `__NEXT_DATA__` HTML scrape (page now serves RSC chunks). `alpha_engine/polymarket_signals.py` `PRICE_TARGET_RE` gate rejected "Bitcoin Up or Down" markets (classified `updown`, no `$` target → `UPDOWN_*` thresholds were dead code); Gamma API caps `limit` at 100/page so the 500-market scan only ever saw 100. | Scraper migrated to `/api/v2/leaderboard` + `/api/v2/positions` (cursor pagination, snake_case→camelCase row mapping). Signals: price-target gate now applies only to `price_above/price_below/range` types; Gamma fetch paginates via `offset` until `ACTIVE_MARKET_LIMIT`. |

## Files changed

- `tools/live_pnl_tracker.py` — new `dedupe_open_rows()` helper applied in `build()` right after the SQL fetch, before price fetch/PnL/summary/by_class. Payload gains `n_rows_raw`; `n_open` = deduped count. `--apply`/`--summary` unchanged.
- `tools/merge_model_picks.py` — **new**. Appends model picks whose symbol is absent from `picks_now.json` (case-insensitive). Preserves all other top-level keys incl. `generated_at` (freshness assert stays green). Missing/corrupt/stale (>48h) model file → warn + exit 0 (staleness still merges; documented rationale: monthly-rebalance model, hard-skip would drop allocation picks for days). Atomic write (tempfile + `os.replace`). `--dest/--src` overrides for testing.
- `.github/workflows/picks-now-refresh.yml` — step "Merge finpredict-v4 model picks" after Generate-picks, before Freshness assert; commit block now also ships `picks_now_model_finpredict_v4.json` (guarded `git hash-object` + `update-index` in the same temp index).
- `.github/workflows/model-picks-emission.yml` — step "Merge model picks into picks_now.json" between emitter and `save_picks_to_db.py`, so model picks reach `picks_now_tracker` without manual pre-merging.
- `copy_trader_intel/polymarket_scraper.py` — v2 endpoints, row normalizers, cursor pagination, `fetch_crypto_leaderboard` via `category=crypto` API (two sorts merged by wallet) replacing dead HTML scrape.
- `alpha_engine/polymarket_signals.py` — conditional price-target gate + Gamma offset pagination. Thresholds/`ASSET_RULES`/output schema/`_probability_signal_direction` untouched.

## Verification

**Fix 1**
- `py_compile` OK.
- Synthetic test (6 rows, `generated_at DESC`): → 4 rows, keys `[SGOV/LONG, BND/LONG, BTCUSDT/SHORT, BTCUSDT/LONG]`, newest SGOV (`2026-11-15`) kept.
- Live DB run (`--summary`): `4390 raw rows → 185 open` after dedupe, 0 duplicate (symbol, direction) pairs in a full build to a temp JSON; repo data file untouched by the test.

**Fix 2**
- `py_compile` + YAML parse of both workflows OK.
- Idempotency on real files (temp copies): run 1 and run 2 both → `merged 0 new, skipped 4 duplicates` (VTI/TLT/SGOV/BND already present), 29 picks, all unique, `generated_at` preserved (`2026-11-14T12:04:17`).
- Add-path test (BND removed from dest): run 1 → `merged 1, skipped 3`; run 2 → `merged 0`. Missing/corrupt/stale src → exit 0 with warning.

**Fix 3** — see "Fix 3 validation" section below (appended when landed).

## Fix 3 validation (landed)

**Endpoint correction (found by the implementing child):** the canonical v2 base is `https://data-api.polymarket.com/v2/` — `polymarket.com/api/v2/` 404s (Next.js page route). Proven three ways: lb-api 410 message names the data-api URL; the cursor-only `offset` error reproduces at `data-api.polymarket.com/v2/leaderboard?offset=100`; response shapes match the probed payloads byte-for-byte.

**Signals (`alpha_engine/polymarket_signals.py`)**
- `_classify_market("Bitcoin Up or Down - November 15, 11:30AM-11:45AM ET")` → `updown`; the normalized market is now KEPT (p=0.55, BTCUSDT) — gate no longer kills it.
- `fetch_crypto_markets(500)` → **6 markets kept (was 0)**; `market_type` counts `{price_above: 3, price_below: 3}`. Pagination verified: 500 raw fetched (was hard-capped at 100/page).
- Diagnostic over the 500 raw markets: 7 contain "up or down" → all 7 now classify `updown` and clear the price gate; they then die only at the intentionally-unchanged guards (5 × `low_vol` < $1,000, 2 × expired). More updown picks would require lowering `MIN_MARKET_VOLUME_USD` — out of scope, thresholds untouched by design.

**Scraper (`copy_trader_intel/polymarket_scraper.py`)**
- `fetch_leaderboard(10)` → 10 rows, legacy keys (`proxyWallet/userName/verifiedBadge/pnl/vol/rank`); #1 VirIntrepidus pnl=444,068.
- `fetch_crypto_leaderboard(10)` → 10 merged rows (profitRank/volRank populated).
- Wallet `0x45185b…`: closed=17 rows (size/initial/realized/ISO timestamp ✓), open=8 rows (currentValue/status ✓); signatures unchanged.
- **Post-review patch (mine, after child report):** v2 zeroes `entry_cost_usdc` on CLOSED rows leaving dust (observed 0.013 on a $420k lifetime position), which `_historical_exposure` would take as `initialValue` and weight at ~$0 in `_group_directional_markets` notional math. Rule now: trust `entry_cost_usdc` only when ≥ 50% of `total_size × avg_price`, else use that notional. Verified live: closed `initialValue` 308k–517k (was 0.013), open rows keep real entry costs (458k/228k/187k).

**Test suite:** `tests/test_polymarket_scraper_scoring.py` 10 passed; `tests/test_pm_consensus_overlay.py` + `tests/test_polymarket_volume_filter.py` 27 passed. py_compile OK on all three edited Python files; both workflows parse as YAML.

**Residual risks:** kept-market count fluctuates with Gamma inventory (6 now); `fetch_crypto_leaderboard` is single-page `limit=120` (spec'd); pre-existing `Hyperliquid`→LINKUSDT `ASSET_RULES` quirk untouched (changes forbidden).

## Risks / notes

- Fix 1 excludes older open rows for the same (symbol, direction) from the snapshot; their `current_price`/`current_pnl_pct` DB columns no longer refresh under `--apply` (only the kept newest row does). Dashboard impact: none — it renders the JSON.
- Fix 2's commit block uses the existing isolated-temp-index pattern; `if [ -f ]` guard skips the model JSON when absent; tree-unchanged short-circuit keeps no-op runs clean.
- All changes are additive; no schema, threshold, or output-key changes except the added `n_rows_raw`.
