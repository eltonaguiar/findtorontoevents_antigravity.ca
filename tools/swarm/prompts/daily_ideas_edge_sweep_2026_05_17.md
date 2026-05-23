# DAILY_IDEAS Edge Sweep — 2026-05-17
# Task: Extract actionable statistical edge improvements from all agent DAILY_IDEAS files

## Context

We run a live algorithmic trading dashboard at findtorontoevents.ca/audit tracking picks across 7 asset classes:
- EQUITY (PF~1.41, WR~52.7%, n=421) — T2 candidate
- COMMODITY (PF~1.78, WR~46.9%, n=750) — meets T2 PF, lift WR
- CRYPTO (PF~2.66 filtered, WR~50%+) — MONEY_READY after removing low-PF volume
- ETF (PF~1.24, WR~55.2%, n=87) — borderline, accumulating toward n≥100
- BOND (PF~1.72, WR~55.6%, n=18) — meets T2 but below charter floor
- FOREX (PF~0.27, WR~46.4%) — mutation protocol in progress, NOT_READY
- FUTURES (mixed) — multi_asset_copytrader WR=3% blocked

Performance tiers (hedge-fund grade):
- Tier 1 (Renaissance): PF>2 / WR>55% / MDD<10%
- Tier 2: PF>1.5 / WR>50% / MDD<20%
- Floor: PF≥1.3, n≥30

## Your Task

Read and synthesize the following DAILY_IDEAS files. These were written by multiple AI agents (Antigravity, Cursor, Grok, Kimi, HuggingFace, Nvidia, Ollama, OpenMonoAgent, XiaoMi Mimo, GH Copilot, Kilocode, LLMARENA) each sharing their top ideas for improving statistical edge.

Key files to analyze (read as many as you can):
1. C:\findtorontoevents_antigravity.ca\DAILY_IDEAS.MD
2. C:\findtorontoevents_antigravity.ca\daily_idea_antigravity.MD
3. C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_GROK_2026_05_16.MD
4. C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_KIMICLI_2026_05_16.MD
5. C:\findtorontoevents_antigravity.ca\daily_ideas_KimiCode.MD
6. C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_CURSORCLI_2026_05_16.MD
7. C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_HUGGINGFACE.MD
8. C:\findtorontoevents_antigravity.ca\daily_ideas_Kilocode_laguna.MD
9. C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_LLMARENA_May162026.MD
10. C:\findtorontoevents_antigravity.ca\daily_ideas_nvidia.MD
11. C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_OLLAMA.MD
12. C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_OPENMONOAGENT.MD
13. C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_XIAOMIMIMO_May172026.MD
14. C:\findtorontoevents_antigravity.ca\reports\daily_ideas_synthesis_2026-05-16.md
15. C:\findtorontoevents_antigravity.ca\reports\daily_ideas_edge_per_class_20260513T010800Z.md
16. C:\findtorontoevents_antigravity.ca\reports\grok_sessions\dAILY_IDEAS_GROK_MAY162026_502pmEST.MD

## Existing infrastructure (grep the codebase to verify before claiming "not implemented"):

Key files to cross-reference:
- `alpha_engine/` — strategy modules, kelly_position_sizer.py, outcome_resolver.py
- `audit_trail/quality_gates.py` — current gates, BLOCKED_ASSET_STRATEGY_PAIRS, BLOCKED_SOURCE_SYSTEMS
- `audit_trail/pcg5_gates.py` — portfolio concentration gates
- `tools/swarm/swarm_pick_schema.py` — passes_tier_gate()
- `audit_dashboard/data/dashboard_data.json` — live performance data
- `reports/MASTER_ACTION_PLAN_2026-05-15.md` — current action plan

## Output Format

Produce a ranked list of actionable edge improvements. For each idea:

### IDEA-N: [Short title]
**Asset class:** EQUITY / CRYPTO / COMMODITY / ETF / BOND / FOREX / ALL
**Source(s):** which agent file(s) mentioned this
**Effort:** S (< 2 hours code) / M (2-8 hours) / L (> 1 day)
**Expected lift:** quantified if possible (e.g., "WR +3-5% based on backtests in file")
**Implementation path:** specific files + functions to modify
**Already in codebase?:** YES (cite file:line) / NO / PARTIAL (cite what exists)
**Why this would work:** 2-3 sentences of reasoning
**Confidence:** HIGH / MEDIUM / LOW (based on evidence quality in source files)

## Prioritization Criteria

Rank ideas by: (1) asset class criticality — COMMODITY WR lift and CRYPTO volume cleanup are highest priority; (2) effort-to-expected-lift ratio; (3) evidence quality (agent consensus > single agent claim).

## Critical Rules
- Do NOT claim an idea is "not implemented" without grepping the repo first
- Do NOT claim performance figures without citing the source file + n + timeframe
- If multiple agents agree on the same idea, that's a strong signal — highlight it
- Focus on ideas that would move us from our current stats toward Tier 1/2 targets
- Exclude ideas that require production DB writes, PHP coordination, or external API keys we don't have

## Questions to answer

1. Which 3-5 new strategy types appear most consistently across agents that we haven't implemented?
2. Which symbols/instruments are agents recommending that aren't in our current pick universe?
3. What filtering improvements (new gates, new confidence thresholds) do agents suggest?
4. What data sources do agents suggest that would improve signal quality?
5. Are there any cross-asset class signals (e.g., CRYPTO → EQUITY momentum transfer) that multiple agents suggest?

Workspace: C:\findtorontoevents_antigravity.ca\
