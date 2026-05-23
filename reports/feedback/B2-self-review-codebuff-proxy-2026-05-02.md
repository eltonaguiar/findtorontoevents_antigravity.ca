# B2 Multi-AI Feedback — Codebuff Proxy Review (2026-05-02)

Item: **B2 — Asset-Class × Timeframe grid panel** from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md`

## A. Confirmed assumptions

1. **File paths are correct.** `audit_trail/dashboard_generator.py` is the right place to add `_build_ac_timeframe_grid(active_picks)` — the `generate()` function already builds `payload["performance"]["by_asset_class"]` (line ~13479) and `final_active_picks` is in scope at that point.
2. **Template hook point confirmed.** `renderOverview()` assembles `el('tab-overview').innerHTML` in sections; the Asset Class Breakdown panel ends with `</div>` at line ~10363. Inserting the grid panel between that and the System Leaderboard (`div id="ov-leaderboard-body"` at line ~10369) is clean and additive.
3. **Wire-Up Rule satisfied.** `_build_ac_timeframe_grid` will be called inside `generate()` directly on `final_active_picks` — already in the production pick-generation path per the same pattern as `verified_alpha_summary`. No orphan module.
4. **No prerequisites.** B2 is independent of B3 (Freshness extension), B4 (concept registry), etc. B3 already shipped via PR #579 — the `empty_timeframe_lanes` list it adds refers to a separate tool (`generate_asset_class_freshness_report.py`), not to the B2 grid payload.
5. **Risk is LOW.** The change is additive: new `payload["performance"]["asset_class_timeframe_grid"]` key plus new JS render. The existing `by_asset_class` data, the system leaderboard, and the filter logic are untouched.

## B. Surfaced contradictions / blockers

1. **B3 already merged without B2.** PR #579 (B3) added `empty_timeframe_lanes` to `generate_asset_class_freshness_report.py`. The queue lists B2 as a prerequisite for B3 ("so the human-facing rendering exists when the alert fires"). B3 shipped without B2 → the freshness tool already emits the lane data, but there's no grid panel to surface it. B2 should cross-link to the B3 artifact so the grid's empty-lane warnings can optionally pull from the pre-computed B3 data rather than re-computing from scratch.
2. **Current active picks have `trade_timeframe: null` for most rows** (dashboard cron hasn't yet rebuilt post-PR-#545). The grid must gracefully handle null timeframes — show them in an "Unknown" row rather than hiding them. Accept criteria should add: "null timeframe picks render in an 'Unknown' row; if 0 Unknown picks, row is omitted."
3. **B2 spec says "4×4 grid (CRYPTO/EQUITY/FOREX/BOND × SCALP/INTRADAY/SWING/POSITION)."** Current active picks include COMMODITY and ETF asset classes — the 4×4 spec is incomplete. Extend to 6×5 or use the full set of observed asset classes, including COMMODITY, ETF, and FUTURES.

## C. Recommended deltas

1. **Handle null timeframes** with an "Unknown" bucket — show count in an extra row below POSITION, annotated with "⚠ timeframe classifier not yet run."
2. **Extend asset classes beyond the 4 in spec** — include all non-null asset classes from `final_active_picks` plus a fixed base set (CRYPTO/EQUITY/FOREX/COMMODITY/BOND/ETF). Use a fixed column header so the grid always shows the full matrix even if some cells are 0.
3. **Optional cross-link to B3 artifact** — if `tools/data/asset_class_freshness_report.json` exists and has `empty_timeframe_lanes`, annotate those cells with a tooltip from the B3 data.
4. **Tests must not depend on live dashboard_data.json** — use synthetic `active_picks` fixtures to avoid brittle tests.

## D. Net verdict

**Ready-to-ship** with deltas C.1 and C.2 applied (null handling + extended asset classes). C.3 is optional enhancement; C.4 is required for reliable CI.
