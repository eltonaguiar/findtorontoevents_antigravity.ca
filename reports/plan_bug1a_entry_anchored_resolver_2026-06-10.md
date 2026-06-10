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

---

## v2 — POST-DEBATE REVISIONS (2026-06-10 swarm: Meta → R1[PRO 74/RED 52/RISK 58] → R2 → Synthesis)
**Verdict: REVISE / NO-GO as written.** The diagnosis is verbatim-verified, but the v1 design had
two CRITICAL look-ahead REINTRODUCTION vectors + a crash bug + a fictional-observability claim.
These revisions SUPERSEDE the conflicting parts above. Full debate: `reports/bug1a_debate_outcome_2026-06-10.md`.

### Corrected claims (v1 was wrong)
- **NOT a "port" of `reresolve_intrabar.py`.** That tool entry-anchors via a SQL range query
  (`fetch_ohlcv(start=created_at)`); its `replay()` does NO internal entry filter. The production
  resolver hits the **LIVE yfinance/binance API** (yfinance 1h intraday caps ~60d). So the entry
  filter must live INSIDE the production helper + handle the API-can't-reach-back case.
- **DB observability claim was fictional.** The JSON `resolution_method` (`:1288` = intrabar/close_approx)
  NEVER reaches `at_pick_outcomes` — the DB column is a STATUS enum mapped from `exit_reason` (`:901-920`).
  No `intrabar_ambiguous`/`intrabar_bad_geometry` columns exist. → either add additive nullable columns
  (backup-table first) OR explicitly DEFER to a JSON sidecar + logs; stop claiming DB-level /audit attribution.

### MUST-FIX before implementing (the 11, resolved as decisions)
1. **[CRITICAL] DELETE the "fall back to recent-window if entry unparseable" branch** — `_parse_timestamp`
   returns None for offset timestamps (`+00:00`/`-05:00`, judge-verified), so it'd replay unfiltered stale
   bars = Bug 1A reintroduced. Unparseable entry → **None → close_approx, never an unfiltered window.**
2. **[CRITICAL] Also fix `_parse_timestamp`** to accept ISO offsets (try `datetime.fromisoformat` first,
   normalize to UTC ms) so most picks ARE entry-anchored, not silently dumped to close_approx.
3. **[CRITICAL] Partial-API degrade rule:** if the OLDEST returned bar's ts > `entry_ms` (+1-bar tol),
   or the response is empty/short → treat as zero entry-forward bars → **None → close_approx** (don't
   fake-resolve on a window that starts after entry). Designed code + test, not an "open question".
4. **[HIGH] Keep the 3-tuple return.** The sole caller (`:1275`) strict-unpacks `reason, exit_price,
   pnl_pct`. Carry `ambiguous`/`bad_geometry` on the **pick dict** (`pick["_intrabar_ambiguous"]` etc.),
   not a 4th tuple element (would ValueError on the hot path). Derive `entry_ms` INSIDE the function;
   `(pick, bars)` signature unchanged.
5. **[HIGH] tz/ms:** `entry_ms = int(_parse_timestamp(pick["timestamp"]).timestamp()*1000)` with a None
   guard. yfinance index must be tz-aware (localize UTC if naive) before `*1000`; binance `int(k[0])`.
6. **[HIGH] No-touch MUST keep returning None** (do NOT adopt the reference `replay()` TIME_EXIT return —
   a truthy value blocks the close_approx fallback at `:1270`).
7. **[HIGH] BAD_GEOMETRY on BOTH paths:** the close_approx `check_tp_sl` (`:761-785`) has no geometry
   guard, so a corrupt LONG (sl>entry) still fires a trivial SL_HIT there. On geometry-fail → return None
   AND set `pick["_intrabar_bad_geometry"]=True` so the caller skips `check_tp_sl` too; surface as
   BAD_GEOMETRY (not silently mapped to EXPIRED via the `:918-920` else-branch).
8. **[HIGH] Backward-compat proof:** with `RESOLVER_ENTRY_ANCHORED` OFF the resolver is **byte-for-byte
   identical** to today (status/pnl_pct/JSON resolution_method). Ship logic flag-OFF.
9. **[HIGH] Shadow-diff blocking gate (PR2):** pre-register a numeric threshold (HOLD default-ON if
   >X% intrabar→close_approx flips, OR any class WR moves >Y abs pts, OR any class crosses a money-ready
   T2 boundary). Run vs a **CLEAN snapshot** (not the contaminated live DB). Persist per-class +
   per-T2-lead before/after WR/PF/n to `reports/`. Default-ON is a SEPARATE PR.
10. **[HIGH] Historical rows:** this resolver IS the measurement layer (~83% of the clean cohort
    resolved in a 6-day burst), so flipping the flag forward does NOT fix the dominant /audit term.
    Decide: (a) leave historical fake-intrabar rows + /audit dispute banner, OR (b) one-time backup-table
    + reverse-SQL re-resolve (mirror `reresolve_intrabar.py:267-304`). Guardrail: NO money-ready
    promotion off the un-migrated window.
11. **[MEDIUM] Fetch cost / entry boundary:** symbol-level fetch keyed on the oldest unresolved pick's
    entry per symbol, built in the SAME pass that populates `all_syms_ohlc` (`:1034-1050`); max-horizon
    cap (e.g. 336 1h-bars, within the ~60d intraday ceiling); picks older than cap → close_approx/EXPIRED.
    Entry boundary: **first eligible bar = open_time ≥ entry_ms** (drop the partial entry bar).

### Two-PR rollout (consensus)
- **PR1 (logic, flag default-OFF):** the entry-anchored helper + the 3 critical degrade rules + the
  3-tuple-with-dict-flags contract; harness flipped RED→GREEN (xfail markers → strict/plain asserts);
  prove OFF-path byte-identical. NO DB writes change.
- **PR2 (default-ON):** gated on the reviewed shadow-diff (clean snapshot, pre-registered blocking
  threshold) + quant sign-off that no class silently crosses a T2 boundary + the historical-row decision.

### Harness — status (debate-mandated cases ADDED this pass)
`tests/test_resolver_intrabar_accuracy.py` now 14 cases: 7 pass (current-correct incl. gap-through #8 +
un-timestamped defensive-keep) + 7 xfail (offset-entry, partial-API, entry==bar, stale-window, pre-entry,
ambiguous-via-dict-flag, bad-geometry). Remaining harness TODO for the fix PR: a DB-upsert-mapping test
(BAD_GEOMETRY not silently written as EXPIRED — needs the caller/DB path), and flip all xfail→strict.
