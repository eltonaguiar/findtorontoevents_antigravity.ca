# B2 Multi-AI Feedback — DeepSeek-Reasoner Proxy Review (2026-05-02)

Item: **B2 — Asset-Class × Timeframe grid panel** from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md`

## A. Confirmed assumptions

1. **`_build_ac_timeframe_grid(active_picks)` is the right helper signature.** Takes the same `final_active_picks` list that populates `payload["picks"]["active"]`; no additional data sources needed.
2. **`payload["performance"]` is the correct payload key.** It currently holds `by_asset_class`, `hourly_24h`, `asset_class_health` — adding `asset_class_timeframe_grid` is consistent with the existing structure.
3. **Template rendering pattern is consistent.** The existing collapsible panels (`ov-ac-body`, `ov-leaderboard-body`) follow a consistent pattern: `<div style="cursor:pointer" onclick="toggle">...<h2>Title</h2></div><div id="...">content</div>`. The grid panel should follow the same pattern.
4. **No existing test file to extend.** There is no `tests/test_ac_timeframe_grid.py`. New test file is correct.
5. **B3 (merged #579) already provides `empty_timeframe_lanes` in a separate tool.** B2 should not depend on B3's artifact — it computes the grid directly from active picks.

## B. Surfaced contradictions / blockers

1. **Spec says "4×4 grid"** but the production pick set includes COMMODITY (from `futures_momentum`, `cftc_cot_commercial_signal`), ETF (from `etf_sector_rotation`), and FUTURES. The grid should dynamically include all observed asset classes to avoid silently hiding data.
2. **Template is 16,000+ lines of hand-coded HTML.** Inserting multi-line JS at a precise location requires careful search for the insertion anchor (`ov-leaderboard-body` div header) to avoid accidentally breaking the existing section.
3. **Grid is purely computed from `final_active_picks`** — this means it reflects picks AFTER quality gates. The spec says "active-pick counts per cell" which aligns with `final_active_picks` (gated). This is correct behaviour.
4. **Drill-down links for grid cells** — the existing `drillLink()` function already exists in `renderOverview()` and supports `data-filter-key` / `data-filter-val` / `data-tab`. The grid cells should reuse this for `f-asset` × `f-timeframe` double filtering, but the existing filter system may only support single-key filtering at a time. Fallback: make cells click-through to the active picks tab pre-filtered by asset class only.

## C. Recommended deltas

1. **Use `D.performance?.asset_class_timeframe_grid` in JS** with a safe fallback: if the key is absent (old payload), compute the grid client-side from `D.picks?.active`. This allows gradual rollout without breaking old payloads.
2. **Grid column order**: SCALP → INTRADAY → SWING → POSITION (increasing time horizon). If null exists, add as last column.
3. **Empty lane criterion**: 0 active picks in cell → show `⚠ 0` in amber/yellow with title tooltip. Non-zero → show count (optionally as drill-link to active picks filtered by asset_class).
4. **Add a "Total" column** summing active picks per asset class row.

## D. Net verdict

**Ready-to-ship** with delta C.1 applied (JS fallback for old payloads) and C.3 (empty cell styling). C.4 (total column) is optional but improves readability.
