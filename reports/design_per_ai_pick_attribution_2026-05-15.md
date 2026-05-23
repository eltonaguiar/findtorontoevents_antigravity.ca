# Design — Per-AI Pick Attribution ("AI Leaderboard")

**Date:** 2026-05-15 · **Status:** Phase 1 implemented · **Author:** Claude (Opus 4.7) + 3-agent design swarm.

## Goal

Track which AI engine/persona made each trading pick, its rationale, horizon, and
asset class — then join realized outcomes to rank **which AI is best per asset class
and per horizon** (short vs long term), and surface *why* (rationale themes).
North-star feature logged in `DAILY_IDEAS.MD` (2026-05-15).

## Headline finding — the repo already ships ~80% of this

A 3-agent design swarm (data-model / scoring / UI facets) found the plumbing exists:

- `audit_dashboard/data/swarm_picks.json` — durable pick book, schema in
  `tools/swarm/swarm_pick_schema.py`. Each pick carries `models_consulted[]`, and
  per-vote `underlying_model` is **REQUIRED** (2026-05-12 schema decision, "so the
  leaderboard can roll up by underlying-model identity") — `name`, `role`, `vote`,
  `confidence_0_100`, `timeframe`, `justification_summary`, plus an embedded
  `outcome` resolved nightly by `tools/swarm/outcome_resolver_swarm.py`.
- `research/asset_class/<class>/run_*/p2_candidates.json` — research runs tag each
  candidate with `proposed_by_engine`.
- `tools/edge/edge_stability.py` — the per-asset-class consistency pattern + the
  `wilson_ci()` helper to reuse.

So the feature is mostly an **aggregation + rendering** task, not a capture task.

## Architecture

```
swarm_picks.json ──► build_ai_leaderboard.py ──► ai_leaderboard_index.json ──► ai_leaderboard.html
(pick book,           (read-only aggregator,      (per-engine × asset-class      (dashboard page)
 underlying_model     fan per engine, join         × horizon metrics)
 + outcome)           outcome, score)
```

### Data model & capture

Canonical record = the existing `swarm_picks.json` pick. Three derived fields
proposed for the schema (Phase 2 — not required for Phase 1, the builder derives
them on the fly): `attributed_engine` (denormalised top engine), `rationale_text`
(concat of `justification_summary`), `horizon` (short/medium/long from `timeframe`).
Capture hook: `append_picks()` in `swarm_pick_schema.py` (already a production
caller via `tv_pick_capture.py`). Mainline production picks (`smart_picks_engine.py`)
currently only stamp `source_system` (a *strategy*, not an *engine*) — a Phase-2
adapter stamps `underlying_model="rule_engine"` so rule picks are comparable.
Backfill: mine `research/asset_class/*/run_*/p2_candidates.json::proposed_by_engine`.

### Scoring & leaderboard logic

- **Join:** fan each pick to every `models_consulted[].underlying_model`; join the
  embedded `outcome.pnl_pct`. Unresolved picks (`pnl_pct is None`) excluded from
  WR/PF, counted separately (`total_picks` vs `n`).
- **Per (engine × asset_class × horizon) cell:** n, WR, PF, expectancy, Wilson 95% CI.
- **Small-n defence (the core risk — 3 lucky picks must not top the board):**
  1. `MIN_N_RANKED` floor — a cell below it renders greyed, `classification:building`,
     rank-ineligible. (Phase 1 = 20; raise toward the n≥100 Tier-2 charter floor.)
  2. **Shrinkage rank score** — never raw WR:
     `wr_shrunk = (wins + α·p_class) / (n + α)` with `α=50`, `p_class` = pooled
     asset-class WR; `rank_score = wr_shrunk·100 + 12·ln(PF) − 0.15·CI_halfwidth`.
     A thin engine's wide Wilson interval directly docks its score.
- **Horizon split:** score each (engine × class × horizon) cell independently —
  never pool horizons (a scalp return distribution ≠ a swing one).
- **Convergence guard** (memory `feedback_multi_ai_convergence_trap`): Phase 2 —
  Jaccard-overlap engine picks; collapse correlated picks to one effective
  observation so a swarm of clones reading one stale input cannot sweep the board.

### UI surface

New page `audit_dashboard/ai_leaderboard.html` (not bolted onto `research_index.html`
— that is forward-looking research-run catalog; this is backward-looking performance).
Modeled on `edge_stability.html`: dark theme, client-side `fetch()` of one JSON,
XSS-safe `esc()`. Ranking table (engine rows, sorted by rank score) → click → drill
into per-asset-class + per-horizon breakdown. Nav link added from
`audit_dashboard/template.html` (the editable file — never `index.html`).

### Data contract

`audit_dashboard/data/ai_leaderboard/ai_leaderboard_index.json` —
`{schema_version, as_of, min_n_ranked, shrinkage_alpha, totals, engines:[{engine,
overall, by_asset_class, by_horizon, best_asset_class}]}`.

### Integration & deploy

`build_ai_leaderboard.py` is a pure read-only aggregator (touches only
`data/ai_leaderboard/`, never the pick book or live HTML). Wire as a step in the
existing `swarm-pick-review.yml` workflow, after `outcome_resolver_swarm.py` (outcomes
freshest there; that workflow already commits `[skip ci]`). FTP-deploy
`ai_leaderboard.html` + `data/ai_leaderboard/*.json` to `/findtorontoevents.ca/audit/`.

## Phased rollout

| Phase | Scope | Status |
|---|---|---|
| **1** | `build_ai_leaderboard.py` (per-engine + per-asset-class + per-horizon roll-up, shrinkage rank score), `ai_leaderboard.html`, unit tests | **DONE (this PR)** |
| 2 | Wire into `swarm-pick-review.yml`; `template.html` nav link; research-run backfill; mainline `rule_engine` adapter; convergence guard | OPEN |
| 3 | Rationale-theme analysis (TF-IDF keyword diff winner vs loser → "engine X wins citing momentum") via `tools/swarm/pattern_miner.py` | OPEN |

Effort estimate (design swarm): ~6.5 engineering days total; Phase 1 was the
independently-shippable headline.

## Current data reality

`swarm_picks.json` today: 38 picks, 5 resolved, all `underlying_model=claude-opus-4-7`
(single-model — see `MASTER_ACTION_PLAN` M-051: route swarm personas to genuinely
different models for real ensemble diversity). The leaderboard is thin now by
construction; it fills as picks resolve and M-051 lands multi-model swarm. The
**infrastructure** is the Phase-1 deliverable.

## Files

- `tools/ai_attribution/build_ai_leaderboard.py` — aggregator (Phase 1).
- `audit_dashboard/ai_leaderboard.html` — dashboard page.
- `audit_dashboard/data/ai_leaderboard/ai_leaderboard_index.json` — generated payload.
- `tests/test_ai_leaderboard.py` — 7 unit tests.
