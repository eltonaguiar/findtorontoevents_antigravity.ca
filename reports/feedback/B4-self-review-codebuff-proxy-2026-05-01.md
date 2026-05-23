# B4 Pre-Implementation Review — Codebuff-Proxy Self-Review (2026-05-01)

This review approximates the Codebuff peer review required by §5 protocol.
External AI access is unavailable in the loop runtime environment.

---

## A. Confirmed assumptions

1. `alpha_engine/concept_registry.py` is the correct location. Other strategy
   modules (`tradingagents_emitter.py`, `elite_scorer.py`) already live there;
   a concept registry follows the same placement pattern.

2. The six-branch derivation logic in `assign_concept_fields` (long_term_value →
   skyrocket → tradingagents → penny_stock → meme_coin → mercury2 → reverse_engineer →
   standard) is complete and covers all currently active source systems (confirmed:
   V6 PASS 21/21 on live dashboard).

3. Feature flags match the rollout plan: TAXONOMY_EMISSION=1 (Phase 1 already
   shipped), CONCEPT_SCORING_SHADOW=0 (Phase 3/B5, future), CONCEPT_GATE_ENFORCE=0
   (Phase 6/B6, future). No flag flips in this PR.

## B. Surfaced contradictions / blockers

1. **Missing test file for `assign_concept_fields`** — PR #548 shipped the
   function but has no dedicated unit tests. B4 should add them to protect the
   refactored registry from future regression.

2. **dashboard_generator.py is ~9000 lines** — any edit risks unintended diff
   noise. Keep the change surgical: move only the two frozensets and add one import
   line; leave `assign_concept_fields` body largely intact with delegation call.

3. **Import ordering in dashboard_generator.py** — if `alpha_engine.concept_registry`
   is slow to import or raises at module load time, it would break the dashboard
   generator. Guard with try/except fallback to inline definitions.

## C. Recommended deltas

- Add a `try/except ImportError` guard in `dashboard_generator.py` so if
  `alpha_engine.concept_registry` can't be found (e.g. running in an environment
  where only `audit_trail/` is present), the inline fallback definitions are used.
  This prevents a deploy regression if the module is accidentally excluded.
- In the registry, expose `CONCEPT_FAMILIES: frozenset[str]` as the authoritative
  list of known concept families. Used by CI gate + B6 UI to enumerate chips.
- Add `__all__` to the registry module to make the public API explicit.

## D. Net verdict

**Ready-to-ship.** The ImportError guard and CONCEPT_FAMILIES constant are the
only deltas to apply. All other assumptions are correct.
