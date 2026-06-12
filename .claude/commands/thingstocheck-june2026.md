---
description: Investigate /audit for hidden edges, debug 0/8 profitable classes, picks-now 21% WR, tournament/leaderboard staleness
---

Read and follow `.claude/skills/thingstocheck-june2026/SKILL.md`.

Deliverable: `PLAN_INSIGHTS_<MODEL>_<DATE>_<TIME>EST.MD` (append `_A`, `_B` if exists).

Quick checks:
1. `money_ready_verdict.json` → intrabar_truth per class
2. `entry_conditions_forward.json` → forward stamp lanes
3. `picks_now_track_record.json` → forward-tested WR
4. `ai_tournament_leaderboard.json` → model WR with MISPRICED_ENTRY excluded
5. Live pages: /audit/, picks-now, pick_funnel, ai-tournament, portfolio_history

User prompt template saved in skill — investigate why no per-class profit after months of work.
