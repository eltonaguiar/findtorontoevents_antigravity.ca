# Swarm Paper Picks — Decommission + Lessons Learned (2026-06-12)

Operator request: remove the "Swarm Paper Picks" panel from /audit, archive the data, and derive any usable insights from winners vs losers first.

## What was decommissioned
- **UI:** nav pill + `#swarm-pick-tracking-section` panel removed from `audit_dashboard/template.html` (315 lines). Regenerates to the live page on the next hourly dashboard build.
- **Payload:** `swarm_picks_data` emit removed from `audit_trail/dashboard_generator.py`.
- **Pipeline:** the promote + resolve steps removed from `.github/workflows/ai-leaderboard-freshness.yml` (they fed/resolved the book).
- **Data:** NO DB table existed (verified `SHOW TABLES LIKE '%swarm%'` = empty). The JSON book is archived in place: `swarm_picks_OLD.json`, `swarm_leaderboard_OLD.json`, `swarm_pattern_tags_OLD.json`. The AI-attribution leaderboard builder still reads the frozen archive (`build_ai_leaderboard.py::DEFAULT_PICKS` → `_OLD`).
- Dormant writers left untouched (tools/swarm/* have no remaining scheduled caller).

## The book (2026-05-11 → 2026-06-06)
340 picks · only **31 ever resolved** (13W/18L · WR 41.9% · PF 1.61) · 309 perpetually open after the resolver stalled — 91% of the experiment was never measured (304 of the unresolved are the moderate/strong consensus tiers, i.e. the bulk of what the experiment was designed to test).

## Insights from winners vs losers (ALL small-n: n=31 resolved; nothing here sizes anything)
1. **The LONG/SHORT asymmetry replicates independently (the one transferable signal).** Swarm LONG: n=20, WR 30.0%, PF 0.83. Swarm SHORT: n=11, WR 63.6%, PF 4.37. This mirrors the main CRYPTO book almost exactly (LONG 30.1%/0.684 n=1051 vs SHORT 55.8%/1.359 n=104, intrabar). A separate pick lineage, separate resolver, same pattern → independent corroboration for INCIDENT_CRYPTO#23 (the P0C CRYPTO-LONG block).
2. **Consensus did NOT add edge.** unanimous tier PF 1.31 (n=5) ≤ single-model PF 1.41 (n=17); by models_agreed, 4-5 agreeing (PF 1.12/0.98) underperformed 2-3 agreeing (PF 2.76/5.90). At this n it's noise either way — but the experiment's core thesis ("more models agreeing = better picks") is unsupported by its own data. Do not rebuild this without a pre-registered hypothesis + the velocity harness.
3. **The `losing_cell` pattern tag worked as a NEGATIVE filter.** Picks tagged `losing_cell` went 20% WR / PF 0.53 (n=5) vs `sparse_cell` 46.2% / 1.99 (n=26). The cell-classifier concept (route AWAY from historically-losing strategy cells) is worth carrying into the entry-conditions lane — it is the same shape as our stamp NEGATIVE conditions (forex_contrarian_NEGATIVE etc.), which are working.
4. **Process lesson (the real failure):** a forward experiment without a guaranteed resolver is not an experiment. 91% unresolved means the swarm book can never reach a verdict. This is the same masked-failure family as P0A — any future forward lane must ship WITH its hourly resolution driver + a freshness assertion, or it will silently rot.

## Verdict
No promotable edge found; one corroborating data point (LONG bleed), one reusable concept (negative cell-filter), one process rule (no lane without a resolver). Book frozen; page decluttered.
