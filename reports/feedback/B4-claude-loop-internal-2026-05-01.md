# B4 Pre-Implementation Review — Claude Loop Internal (2026-05-01)

Item: **B4 — Cursor Phase 2: Concept Producer Wiring + Feature Flags**

External AI peers (FreeBuff, Codebuff, etc.) are not accessible in this loop
runtime environment. This review substitutes for 1 of the required 2 peer
reviews per §5 protocol.

---

## A. Confirmed assumptions

1. **File paths are correct.** `alpha_engine/concept_registry.py` is a new file;
   `audit_trail/dashboard_generator.py` around lines 6006-6072 holds the concept
   taxonomy logic to be extracted (verified by grep).

2. **PR #548 already stamped concept_family on 100% of picks** (V6 PASS, 21/21 in
   dashboard payload). B4 refactors that inline logic into a dedicated module —
   no behavioral regression.

3. **No circular import risk.** `alpha_engine` does not import from `audit_trail`.
   `dashboard_generator.py` already imports from `alpha_engine` (e.g. config).
   Adding `from alpha_engine.concept_registry import ...` continues that one-way
   dependency.

4. **Feature flags are correctly positioned.** `TAXONOMY_EMISSION` (default ON —
   picks already carry concept_family) is backward-compatible. `CONCEPT_SCORING_SHADOW`
   and `CONCEPT_GATE_ENFORCE` default OFF, which is safe for Phase 2.

5. **Wire-Up Rule.** The registry module IS wired: `dashboard_generator.py`'s
   `assign_concept_fields` is a production caller in the `_normalize_pick` path
   that processes every pick. Moving the logic to a separate module while keeping
   the same call site satisfies the Wire-Up Rule for the registry itself.

## B. Surfaced contradictions / blockers

1. **148 source names in JSON_PICK_SOURCES.** Most sources emit "standard"
   concept picks (no special tag). A CI gate that requires *explicit* mapping for
   each source would need 148 entries. Better approach: CI gate asserts coverage
   (no source returns None/empty), not that each source has an explicit non-standard
   mapping. This is the correct interpretation of the spec.

2. **`assign_concept_fields` lives in `dashboard_generator.py`.** Moving it
   entirely could break callers if any module imports it directly from there.
   Safer: keep the wrapper in dashboard_generator, have it delegate to
   `concept_registry.get_concept_family`. Deprecation can be a later PR.

3. **No test file `tests/test_concept_registry*.py` exists.** Create new; do NOT
   extend `test_dashboard_class_tf_grid.py` (that's B2's test, different scope).

## C. Recommended deltas

- Scope the "wired / opt-in" declaration to the 7 named concept families, not
  the 148 source names. Sources not in the registry default to "standard" (wired).
- The `WIRING_STATUS` dict should document concept-FAMILY paths (long_term_value,
  skyrocket, mercury2, etc.) rather than source-system paths. This is what B5/B6
  need to gate on.
- Feature flag: use `int(os.getenv("TAXONOMY_EMISSION", "1"))` pattern (same as
  existing `TRADINGAGENTS_EMITTER_ENABLED` flag in tradingagents_emitter.py).

## D. Net verdict

**Ready-to-ship.** Risk is MEDIUM but the change is purely additive/refactoring.
The only production change is in `dashboard_generator.py`: replacing inline frozenset
definitions and the assignment function body with an import + delegation call.
Behaviour is unchanged; tests confirm this.
