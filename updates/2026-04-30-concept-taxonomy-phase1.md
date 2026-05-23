# 2026-04-30 — Concept taxonomy Phase 1 (Cursor's `assign_concept_fields`)

## What this PR ships

Phase 1 of [Cursor's "Audit Concepts Integration" plan](C:\Users\zerou\.cursor\plans\audit_concepts_integration_2c10565d.plan.md):
a deterministic helper that stamps `concept_family` + `concept_source`
on every pick that flows through `audit_trail.dashboard_generator._normalize_pick`.

## Concept families

| Family | Triggers |
|---|---|
| `long_term_value` | `pick_type == "long_term_value"` OR `source_system` starts with `value_screener` / `ueps_` |
| `skyrocket` | `strategy == "skyrocket_detector"` OR `source_system == "skyrocket_detector"` (PR #546's penny detector) |
| `tradingagents` | `strategy == "tradingagents_consensus"` OR `source_system == "tradingagents"` (PR #544's emitter) |
| `penny_stock` | `category == "penny"` (any pick that isn't already tagged skyrocket) |
| `meme_coin` | `meme` substring in strategy/source OR `category == "meme"` |
| `mercury2` | `source_system in {"mercury2", "mercury2_fast", "revival_mercury2", "ai_challenge_mercury"}` (explicit list, no glob) |
| `reverse_engineer` | strategy in explicit registry (winner_reverse_engineer / strategy_reverse_engineer / gainer_predictor / gainer_predictor_score) |
| `standard` | default (everything else) |

## Specificity ordering

Order matters when multiple rules could apply:

1. `long_term_value` (most specific — pick_type is an explicit declaration)
2. `skyrocket` (strategy name takes precedence over category)
3. `tradingagents`
4. `penny_stock` (would otherwise also match for skyrocket picks)
5. `meme_coin`
6. `mercury2`
7. `reverse_engineer`
8. `standard`

## Backward compatibility

- Default `concept_family="standard"` — picks without a match are not broken.
- Already-tagged picks (upstream emitter sets `concept_family`) are
  **preserved untouched** — gives downstream producers a way to assert
  custom labels without re-deriving.
- Helper mutates in-place AND returns the dict (chainable).
- Non-dict inputs return unchanged (defensive guard).

## Why this lands now

Per Cursor's plan: Phase 1 (taxonomy emission) must ship and bake before
Phases 2-6 (concept-aware scoring, gates, UI filters). This PR is the
prerequisite — no scoring changes, no UI changes, just the field stamping.

The taxonomy unblocks:
- Phase 2: concept registry + JSON_PICK_SOURCES audit (separate PR)
- Phase 2.5: feature-flag rollout staging
- Phase 3: concept-aware scoring (skyrocket reconciliation, Mercury2 modifier)
- Phase 5: UI chips/filters for concept families
- Phase 6: CI taxonomy-coverage check

## Files

- `audit_trail/dashboard_generator.py` (+87 LOC):
  - New module-level constants `_MERCURY2_SOURCES`, `_REVERSE_ENGINEER_STRATEGIES`.
  - New helper `assign_concept_fields(pick: dict) -> dict`.
  - Single-line call from `_normalize_pick`'s tail.
- `tests/test_concept_taxonomy.py` (new, 35 tests).
- `updates/2026-04-30-concept-taxonomy-phase1.md` (this doc).

## Test coverage

35/35 pytest cases:
- 24 parameterized concept-family derivation cases (one per registry rule, including specificity edges).
- 4 concept_source attribution + already-tagged-preserved cases.
- 3 mutation-contract / defensive-guard cases.
- 2 specificity-ordering cases (long_term_value vs meme; skyrocket vs meme).
- 2 `_normalize_pick` integration cases (real call site stamps + standard default).

## Verification

After merge + next `audit-dashboard.yml` cron run:

1. `audit_dashboard/data/dashboard_data.json` → every pick under
   `picks.active`, `picks.active_raw`, `picks.recent_closed` carries
   `concept_family` + `concept_source`.
2. Coverage spot-check: UEPS picks (after PR #547 lands) tag as
   `long_term_value`; skyrocket detector picks tag as `skyrocket`;
   TradingAgents picks tag as `tradingagents`; the existing 24 active
   `enhanced_ml_A_xgboost` rows tag as `standard`.
3. No existing field is overwritten or removed — backward compatible.

## Risk: LOW

- Pure additive metadata stamping; no scoring, gating, or filtering
  behavior changes.
- Helper is pure function (no I/O, no globals beyond two frozensets).
- Already-tagged picks are preserved untouched — no risk of overriding
  upstream attribution.
- Non-dict inputs return unchanged — won't crash on malformed payloads.

## Sequence

1. PR #545 ✅ TF classifier + BOND + PEAD persistence (merged 17:53 UTC)
2. PR #546 ✅ penny skyrocket detector wireup (merged 20:05 UTC)
3. PR #547 — UEPS active-sync workflow fix (open, awaiting CI)
4. **PR #549 (this) — concept taxonomy Phase 1**
5. PR #548 (deferred) — TF=LONG_TERM dashboard label (UI follow-up; smaller scope)
6. PR #550+ (later) — Cursor's Phase 2-6 (scoring, gates, UI, watchdog)

Note: PR #548 was renumbered to land after #549 because Phase 1 taxonomy
is the prerequisite for any concept-based UI filter — and the dashboard
label change is an additive UI tweak that can ship anytime.

## Out of scope (explicitly deferred per Cursor's plan)

- Concept-aware scoring modifiers (Phase 3).
- Concept UI filters / chips (Phase 5).
- KPI panel for concept WR/PF aggregation (Phase 6).
- Asset-Class × Timeframe grid panel (Codebuff Commit 4).
- Freshness watchdog `empty_timeframe_lanes` extension (Codebuff Commit 5).
