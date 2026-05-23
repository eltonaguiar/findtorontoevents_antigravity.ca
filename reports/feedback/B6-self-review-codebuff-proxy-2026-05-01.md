# B6 — Cursor Phase 5 UI Chips & Filters: Multi-AI Feedback #2
## AI: Self-review (Codebuff-proxy) | Date: 2026-05-01

---

## A. Confirmed assumptions

1. **concept_family field is in every active pick.** The field is emitted by
   `assign_concept_fields()` on every pick in the `_normalize_pick` path
   of `dashboard_generator.py`. After B4 merge the registry drives the
   classification.

2. **`hc_filter.js` does NOT need changes.** The HC gate evaluates trust_score,
   forward_wr, and score fields — not concept_family. Adding concept
   filtering to matchFilter() (in template.html) is sufficient and cleaner.

3. **Filter clear-all coverage.** Two forEach arrays exist (lines 4338 and
   11317) that need `'f-concept'` added. Missing either one breaks the
   Clear All button or event listeners.

---

## B. Surfaced contradictions

1. **`concept_family` = "standard" for all current picks**: The concept
   registry classifies strategies by name pattern. Current strategies
   (rs-breakout-scout, mtf-align-scout, stocks_ema_golden_cross,
   smart_money_accumulation) should map to `breakout_momentum`,
   `trend_following`, `trend_following`, `sentiment_driven` respectively —
   NOT standard. The "all standard" result indicates the dashboard hasn't
   rebuilt since B4 merged (< 5 minutes ago). After next cron rebuild,
   the diversity will appear.

2. **B7 is effectively blocked.** The B7 description is based on incorrect
   file paths (`alpha_engine/cot_strategies.py` doesn't exist; the actual
   module is `cot_positioning.py`). Additionally `cot_signals.json` has an
   incompatible schema and is 46 days stale. B7 needs a dedicated
   investigation PR before the live-wire can happen. The autonomous loop
   should mark B7 as ⏳ needs-investigation and skip to B6.

---

## C. Recommended deltas

1. Add a `title` attribute to `f-concept` explaining the concept taxonomy
   for discoverability.
2. Ensure `(pick.concept_family || 'standard')` fallback in the filter
   so legacy picks without the field match `standard` rather than being
   excluded.
3. Limit the concept select to the 8 canonical CONCEPT_FAMILIES plus
   `standard` — do not hard-code ad-hoc names.

---

## D. Net verdict: ready-to-ship

Low-risk, additive UI filter. Implementation is self-contained in
`audit_dashboard/template.html` (5 edits, ≤30 lines). Recommend shipping
without the WR/PF aggregation panel (defer to B6-b after `concept_stats`
lands in the generator). No hc_filter.js changes needed.
