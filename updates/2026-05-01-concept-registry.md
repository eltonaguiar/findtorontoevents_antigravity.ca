# 2026-05-01 — B4: Concept Producer Registry + Feature Flags (Cursor Phase 2)

**PR:** feat/b4-concept-registry-2026-04-30  
**Item:** B4 from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md`  
**Risk:** MEDIUM (touches pick-loading path in dashboard_generator)

## What shipped

**`alpha_engine/concept_registry.py`** (new)

Centralises the source-system → concept-family derivation that was previously
inlined in `audit_trail/dashboard_generator.py` (PR #548). Public API:

| Symbol | Type | Purpose |
|--------|------|---------|
| `TAXONOMY_EMISSION` | `int` | Feature flag (default 1 — on) |
| `CONCEPT_SCORING_SHADOW` | `int` | Phase 3 flag (default 0 — off) |
| `CONCEPT_GATE_ENFORCE` | `int` | Phase 6 flag (default 0 — off) |
| `CONCEPT_FAMILIES` | `frozenset[str]` | Authoritative set of 8 known families |
| `WIRING_STATUS` | `dict` | Wiring status + caller per concept path |
| `get_concept_family(pick)` | `str` | Core derivation function |
| `validate_source_concept_coverage(name)` | `str` | CI gate helper |

**`audit_trail/dashboard_generator.py`** (surgical edit)

`assign_concept_fields()` now delegates to `concept_registry.get_concept_family`
instead of duplicating the derivation logic.  An `ImportError` guard preserves the
inline fallback so the dashboard cannot break if the module path is unavailable.

**`tests/test_concept_registry.py`** (new, 196 tests)

- All 8 concept-family branches unit-tested.
- Feature flags, `WIRING_STATUS`, `CONCEPT_FAMILIES` completeness assertions.
- **CI gate**: every `JSON_PICK_SOURCES` source name (148+ entries) is parametrised
  through `validate_source_concept_coverage` — all must return a non-empty family
  in `CONCEPT_FAMILIES`. Fails if a new source is added without a valid mapping.

## Feature flag rollout plan

| Flag | Default | Flip condition |
|------|---------|---------------|
| `TAXONOMY_EMISSION` | 1 (on) | Already on since PR #548. Downgrade = diagnostic only |
| `CONCEPT_SCORING_SHADOW` | 0 | B5 PR (after B4 has been on main ≥48h) |
| `CONCEPT_GATE_ENFORCE` | 0 | B6 PR (after B5 ≥7d shadow soak) |

## Wire-Up Rule

**Wired.** `dashboard_generator.py::assign_concept_fields` is in the production
`_normalize_pick` path. The registry module is imported there; no orphan.

## Phase 3 / B5 unlock

After this PR merges and has been on main ≥48h, B5 (concept-aware scoring) may
import from `alpha_engine.concept_registry` to gate scoring modifiers by concept
family without touching `dashboard_generator.py`.
