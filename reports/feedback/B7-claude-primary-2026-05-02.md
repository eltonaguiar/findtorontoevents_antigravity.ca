# B7 Multi-AI Feedback — Claude (Primary) — 2026-05-02

## Item reviewed
B7 — CFTC COT live-wire (prerequisite audit PR: schema fix + freshness guard)

## A. Confirmed assumptions

1. **File paths are correct.** `alpha_engine/cot_positioning.py` exists and contains
   both the `cot_positioning_strategy()` function (full pick schema) and the `__main__`
   block (simplified schema). The `__main__` block writes `alpha_engine/data/cot_signals.json`
   with `{pair, signal, confidence, percentile}` entries — not the full pick format.

2. **`_normalize_pick` partially handles the COT schema.** Line 6107 already resolves
   `symbol = raw.get("symbol", raw.get("pair", ...))` and line 6111 resolves
   `direction` from `raw.get("signal", ...)`. However, `strategy` and `asset_class`
   are missing from the raw COT picks, so they'd reach the dashboard unlabeled.

3. **`_FRESHNESS_REQUIRED_HOURS` is the correct hook.** The guard at lines 7038-7053
   already performs mtime-based freshness gating before `_extract_picks` is called.
   Adding `"cot_positioning": 14 * 24` would silently skip stale data at the system
   level.

4. **Content-based freshness is also needed.** `cot_signals.json` mtime ≠ `generated_at`.
   The content timestamp shows 2026-03-16 (47d) but the file mtime is ~7d. A content-level
   check inside `_extract_picks` is necessary to catch this divergence.

5. **The adapter pattern is established.** `_extract_picks` already has a `top_picks`
   adapter for penny_picks (lines 6842-6863) and a `long_picks` adapter for UEPS
   (lines 6812-6838). Adding a `scanner == "cot_positioning"` branch follows this
   exact pattern.

6. **Wire-Up Rule satisfied.** `cot_positioning` is in `VERIFIED_STRATEGIES` (line 4834),
   so it has known-good historical performance. Adding to JSON_PICK_SOURCES is the
   "last mile" wiring step. This meets the Wire-Up Rule: the strategy is wired into
   the production pick-loading path (`build_html` → `_load_all_picks` → JSON_PICK_SOURCES).

7. **No `alpha_engine/cot_strategies.py` exists.** The B7 description mentions it as
   "existing scaffold from PR #526" but the file is absent. This is a stale reference —
   the scaffold is `alpha_engine/cot_positioning.py`.

## B. Surfaced contradictions / blockers

1. **`cot_signals.json` 47d stale; COT cron may be inactive.** The content
   `generated_at: 2026-03-16` predates the last 6 weeks of trading. Even after the
   schema fix lands, the actual picks will be filtered out by the freshness guard until
   the cron refreshes the file. This is correct behavior but means B7's "14-day shadow
   run" doesn't start until the data source is live again. The B7 PR should explicitly
   note this: the guard will auto-lift when cot_positioning.py runs next.

2. **No cron currently runs `cot_positioning.py` on a schedule.** The forex-agent.yml
   references `cot_positioning_forex` as a strategy name in a filter list but does NOT
   call `python alpha_engine/cot_positioning.py` as a job step. B7 proper (the actual
   "flip to default-ON" step) would need a workflow step added to the forex cron. This
   prerequisite audit PR should document this gap but NOT add the workflow step — that
   belongs in B7 proper once the schema is confirmed clean.

3. **`symbol = "GBPUSD"` (no `=X`) is used by the `__main__` block but `_normalize_pick`
   won't add the suffix.** The adapter must ensure `p["symbol"] = pair + "=X"` for
   yfinance compatibility. The `cot_positioning_strategy()` function does this at line 163
   but the `__main__` block stores `pair` (no suffix). Fix confirmed in adapter.

## C. Recommended deltas

1. **Scope the PR to the prerequisite only.** Do NOT set `CFTC_COT_FETCHER_ENABLED=1`
   in any workflow in this PR — that's B7 proper. This PR's scope: schema adapter +
   freshness guard + JSON_PICK_SOURCES entry + cot_positioning.py __main__ fix + tests.

2. **Use content-based freshness check (not just mtime) in the `_extract_picks` adapter.**
   Parse `generated_at` from the file and return `[]` if it's > 14 days old. This handles
   the mtime ≠ content-age divergence.

3. **Fix `cot_positioning.py` __main__ to write full pick schema** so future data is
   immediately compatible without relying solely on the adapter. The adapter stays as
   defense-in-depth.

4. **Add to `_FRESHNESS_REQUIRED_HOURS`** as a belt-and-suspenders guard alongside the
   content check.

5. **Test: assert empty result when `generated_at` is 47d stale.** This is the most
   important test — it proves the freshness guard works and stale picks don't surface.

## D. Net verdict

**ready-to-ship** (prerequisite audit scope). The core changes are small, additive,
and fully defensive (stale data is suppressed, not surfaced). Risk is LOW. Recommend
shipping this PR as the B7 prerequisite, then reopening B7 proper (workflow cron step
+ flag flip) as a separate PR once the schema is confirmed clean in production.
