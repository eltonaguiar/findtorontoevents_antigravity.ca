# B6 — Cursor Phase 5 UI Chips & Filters: Multi-AI Feedback #1
## AI: Claude Sonnet 4.6 | Date: 2026-05-01

---

## A. Confirmed assumptions

1. **File paths correct.** `audit_dashboard/template.html` is the live
   template (never `index.html`). `audit_dashboard/hc_filter.js` (19.5 KB)
   exists. Both are the right hook points for a filter UI addition.

2. **Wire-Up Rule satisfied.** B6 adds a UI filter only; no new module,
   no new data emitter. The `concept_family` field is already emitted on
   every pick via `assign_concept_fields()` (PR #548) and now delegates to
   `alpha_engine/concept_registry.py` (PR #566 / B4). No orphan risk.

3. **Prerequisite correctly identified.** B4 is now ✅ merged
   (PR #566, merged 2026-05-01 21:23 UTC). `concept_family` is live in
   the payload.

4. **No test file to extend for pure UI.** No existing Playwright spec
   covers the concept filter. A new `tests/test_b6_concept_filter.js`
   unit spec will verify: (a) `f-concept` select option set matches
   CONCEPT_FAMILIES, (b) `matchFilter()` returns false for mismatched
   concept, (c) clear-filters resets `f-concept`.

---

## B. Surfaced contradictions / blockers

1. **All 37 active picks currently have `concept_family = "standard"`.** The
   dashboard_data.json was last rebuilt before B4 merged. After the next
   hourly cron rebuild with the concept registry live, picks will get
   richer families (breakout_momentum for rs-breakout-scout, value_quality
   for UEPS, etc.). B6 chips are forward-looking; implement now so they're
   ready when diversity appears.

2. **`cot_signals.json` is 46 days stale** (generated 2026-03-16) and uses an
   incompatible pick schema (`pair/signal/confidence/percentile` vs standard
   `symbol/direction/asset_class`). B7 (CFTC COT) needs a separate
   investigation before it can be implemented. It is NOT a blocker for B6.

3. **Concept WR/PF aggregation from payload**: The dashboard payload does not
   currently have a pre-computed `concept_stats` section. Client-side
   aggregation from closed picks is feasible but complex. Scope B6 to the
   filter select only; defer concept-level WR/PF panel to a follow-up PR
   (B6-b) once the generator emits `concept_stats`.

---

## C. Recommended deltas

1. **Use `<select>` not chips**: A `<select id="f-concept">` is consistent
   with the existing filter bar (10 other selects) and avoids stateful chip
   management. B6 description says "filter chips" but the project pattern is
   select-based; match it.

2. **Add `concept_family` fallback**: In `matchFilter()`, use
   `(pick.concept_family || 'standard') !== f.concept` so picks without
   the field still match `standard` correctly.

3. **Include in both filter arrays**: Lines 4338 and 11317 each have a
   forEach over filter IDs for clear-all and event-listener wiring
   respectively. Both need `'f-concept'` added.

4. **Add `concept` to filter state collector** at line 6458 alongside
   `timeframe`.

---

## D. Net verdict: ready-to-ship

Implementation is 5 targeted edits to `template.html` (≤25 lines total)
plus a unit test spec. No hc_filter.js changes needed — the HC gate
operates on tier/trust/score, not concept family. Risk: LOW (additive only,
existing filter selects unaffected).
