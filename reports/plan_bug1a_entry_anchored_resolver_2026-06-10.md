# Plan: Bug 1A — Entry-Anchored Intrabar Resolution (`universal_pick_resolver.py`)

## Context / problem
The production live resolver `audit_trail/universal_pick_resolver.py` (hourly, feeds /audit) replays
intrabar OHLC to decide TP/SL first-touch — the accurate method. BUT (2026-06-10 review, Bug 1A):
- The OHLC pre-fetch (`:1041-1043`) pulls only the **most-recent** bars (`yfinance period="5d"`,
  `binance limit=48`), NOT bars from each pick's entry.
- Bars carry **no timestamp** (`_fetch_binance_klines_ohlcv:542-548` discards `k[0]` open_time;
  `_fetch_yfinance_ohlcv` likewise).
- Result: for any pick older than the fetch window, `_check_tp_sl_intrabar` (`:558-595`, logic itself
  correct) replays the **wrong recent bars** against the pick's TP/SL → confidently-wrong "intrabar"
  resolution = look-ahead. This is the "layered inaccurate resolving method" the operator flagged.

The proven-correct pattern already exists in `tools/reresolve_intrabar.py` (entry-anchored fetch via
`start = created_at`, fixed forward horizon, SL-first ties, `ambiguous` flag) and
`tools/reresolve_intrabar_signal_outcomes.py` (+ `valid_geometry` guard). This plan brings the
production resolver up to that standard, **safely** (this repo has had outages from rushed resolver
edits — so: test harness first, behind a verification gate, shadow-diff before it changes live numbers).

## Goals / non-goals
- GOAL: eliminate the stale-window look-ahead; resolve each pick only against bars at/after its entry.
- GOAL: when no entry-forward intrabar bars exist, fall through to the (already-tagged) `close_approx`
  path rather than fake-resolve on stale bars.
- GOAL: while here, port the `ambiguous` flag + `valid_geometry` guard (Bug 1C) — low marginal cost.
- NON-GOAL: changing TP/SL semantics, the split-adjustment (already correct), or the close_approx
  tagging (already shipped). NON-GOAL: rewriting the standalone tools (already accurate).

## Design (proposed)
1. **Bar timestamps (additive, zero-risk):**
   - `_fetch_binance_klines_ohlcv`: add `"timestamp": int(k[0])` (open_time ms) to each bar dict.
   - `_fetch_yfinance_ohlcv`: add `"timestamp": int(index.timestamp()*1000)` per row.
2. **Entry-anchored fetch window:** the pre-fetch is symbol-level (shared across that symbol's picks).
   Compute, per symbol, the OLDEST unresolved pick's entry; size the fetch to cover entry→now
   (cap at a max horizon, e.g. 14d / 336 1h-bars, to bound API cost). Binance: pass `startTime`;
   yfinance: `start=`. Fall back to the current recent-window fetch only if entry can't be parsed.
3. **Entry-forward filter in `_check_tp_sl_intrabar(pick, bars)`:**
   - Parse pick entry ms via the existing `_parse_timestamp(pick["timestamp"])`.
   - Skip bars with `bar["timestamp"] < entry_ms`. If a bar lacks `timestamp` (defensive), keep it
     (preserves current behavior for any un-stamped source).
   - If zero bars remain after filter → return None (caller → `close_approx`, already tagged). This is
     the key anti-look-ahead behavior: an old pick with only stale bars NO LONGER fake-resolves.
4. **Bug 1C (port from the standalone tools):** add an `ambiguous` flag when both TP & SL fall in the
   same bar (still resolve SL-first, conservative), and a `valid_geometry` guard (LONG: sl<entry<tp;
   SHORT: tp<entry<sl) that returns a `BAD_GEOMETRY` skip instead of a trivial SL_HIT on corrupt rows.
5. **Surface the method:** already done — `resolution_method` ∈ {intrabar, close_approx}; add
   `intrabar_ambiguous` + `intrabar_bad_geometry` to the resolved dict for observability.

## Rollout safety (must-have, given hot hourly resolver)
- **Test harness FIRST** (`tests/test_resolver_intrabar_accuracy.py`) — TDD: encodes the acceptance
  criteria; the stale-window + entry-filter tests FAIL on current code (proving they catch Bug 1A) and
  PASS after the fix.
- **Shadow-diff before flip:** add an env flag `RESOLVER_ENTRY_ANCHORED` (default OFF). When OFF,
  behavior is unchanged. Run ON in a dry-run against a snapshot, diff resolution outcomes (how many
  flip intrabar→close_approx, how many TP↔SL flip) vs current, review the delta, THEN default it ON.
- **No DB writes in the test path**; `py_compile` + pytest locally; the live resolver change ships only
  after the harness is green AND the shadow-diff is reviewed.

## Files
- `audit_trail/universal_pick_resolver.py` — `_fetch_binance_klines_ohlcv`, `_fetch_yfinance_ohlcv`,
  `_check_tp_sl_intrabar`, the pre-fetch loop (`~:1034-1050`), caller (`~:1255-1264`).
- `tests/test_resolver_intrabar_accuracy.py` — NEW harness (this plan ships it).

## Acceptance criteria (what the harness asserts)
1. SL-before-TP intrabar (LONG: a bar with low≤sl before any high≥tp) → `SL_HIT` (not TP_HIT).
2. TP-before-SL → `TP_HIT`.
3. Same-bar both-touched → `SL_HIT` + `ambiguous=True` (conservative).
4. **Stale window:** pick entry AFTER all provided bars → returns None (no fake resolve) → close_approx.
5. Entry-forward filter: bars before entry are ignored (a pre-entry SL touch does NOT fire).
6. SHORT direction mirrored correctly.
7. Bad geometry (LONG sl>entry) → BAD_GEOMETRY skip, not a trivial SL_HIT.
8. Gap-through (bar opens beyond TP) → TP_HIT at tp (or the conservative fill), not skipped.

## Open questions for the debate
- Per-symbol entry-anchored fetch cost (API calls × symbols × horizon) vs a single wide fetch — which?
- Max horizon cap (14d?) — picks older than that: resolve as EXPIRED/TIME_EXIT or close_approx?
- Should the entry filter use bar OPEN time or CLOSE time as the "≥ entry" boundary (off-by-one-bar)?
- Default `RESOLVER_ENTRY_ANCHORED` ON immediately after harness-green, or hold for a shadow-diff cycle?
