# Phase 9 — DAILY_IDEAS Scan Plan (2026-05-31)

**Purpose:** enumerate every `DAILY_IDEAS*` / `daily_ideas*` file in the repo, bucket the contents, and produce a ranked NEXT-SWEEP candidates list **after** the Phase 1–8 incident batch lands. No execution this phase — review only.

## Scope

Canonical repo root (`.qwen/tmp/review-pr-*` mirrors excluded as duplicates of canonical files used during PR reviews).

### Files in scope (20 canonical)

| Path | Lines | Last modified | Role |
|---|---|---|---|
| `DAILY_IDEAS.MD` | 3677 | 2026-05-30 | Master log (May 8 – May 29 user brainstorms + 2-engine swarm verdicts) |
| `daily_ideas.MD` | 8 | 2026-05-31 | Today's queued prompt (parallelswarm incidents) |
| `DAILY_IDEAS_KIMICLI_2026_05_16.MD` | 123 | 2026-05-25 | Kimi CLI ideas batch |
| `DAILY_IDEAS_GROK_2026_05_16.MD` | 142 | 2026-05-25 | Grok ideas batch |
| `daily_ideas_ghcopilot_auto.MD` | 245 | 2026-05-25 | GH Copilot infra ideas |
| `DAILY_IDEAS_OLLAMA.MD` | 120 | 2026-05-25 | Ollama local-LLM ideas |
| `daily_ideas_KimiCode.MD` | 579 | 2026-05-25 | KimiCode infra/schema deep-dive |
| `DAILY_IDEAS_PROMPTS.MD` | 1174 | 2026-05-25 | Prompt-suite catalogue (5 master prompts + 6 sub-sections) |
| `DAILY_IDEAS_OPENMONOAGENT.MD` | 148 | 2026-05-25 | OpenMonoAgent ideas |
| `DAILY_IDEAS_LLMARENA_May162026.MD` | 290 | 2026-05-25 | LM-Arena multi-model ideas |
| `DAILY_IDEAS_XIAOMIMIMO_May172026.MD` | 70 | 2026-05-25 | Xiaomi MiMo small-model ideas |
| `DAILY_IDEAS_CURSORCLI_2026_05_16.MD` | 95 | 2026-05-25 | Cursor CLI ideas |
| `daily_ideas_nvidia.MD` | 81 | 2026-05-25 | NVIDIA models ideas |
| `DAILY_IDEAS_HUGGINGFACE.MD` | 75 | 2026-05-25 | HF ideas |
| `daily_ideas_Kilocode_laguna.MD` | 258 | 2026-05-25 | Kilocode ideas |
| `reports/DAILY_IDEAS_DIGEST_FOR_RESCUE_2026-05-19.md` | 47 | 2026-05-25 | Cross-file rescue digest |
| `reports/daily_ideas_edge_sweep_2026_05_17.md` | 185 | 2026-05-25 | **Synthesized top-15 ranked (canonical baseline)** |
| `reports/daily_ideas_synthesis_2026-05-16.md` | 172 | 2026-05-25 | May-16 cross-agent synthesis |
| `reports/daily_ideas_synthesis_2026-05-15.md` | 232 | 2026-05-25 | May-15 cross-agent synthesis |
| `reports/daily_ideas_edge_per_class_20260513T010800Z.md` | 287 | 2026-05-25 | May-13 per-class edge teardown |

## Method

1. **Anchor on the synthesis files** (`reports/daily_ideas_edge_sweep_2026_05_17.md`, `reports/DAILY_IDEAS_DIGEST_FOR_RESCUE_2026-05-19.md`) — these already de-dup the 15 LLM-specific files into a single ranked top-15 with status tags.
2. **Layer DAILY_IDEAS.MD additions** since 2026-05-17 (IDEAs A through L user brainstorm, May-24 swarm verdicts on IDEA-A/E/H, May-29 200-day MA prompt).
3. **Filter status against today's session ledger** (PRs #150–#188 + commits `5676eace2`, `1688956c7`, `fc5d2f9f2`, `4ce0d712c`, `7cf01814e`, `64c86b7b5`):
   - Phase 1–8 already shipped: NULL pnl reconcile (#187), retire `cta_golden_cross_200` + `prediction_market_consensus` (#182, #180), FOREX consolidation (`5676eace2`), UNKNOWN backfill (`1688956c7`), MySQL sync hard-fail (#152), profitable-but-filtered lane (#136), portfolios meta-effectiveness (#83), audit/cli severity preserve (#76), pnl backfill 162 LOST→WON (#187), peer-scan zero red flags (#188).
   - Items in `edge_sweep_2026_05_17.md` already marked SHIPPED → drop.
   - Items marked OPEN/BLOCKED → re-evaluate.
4. **Cross-check against the CLAUDE.md status snapshot** (post-M-067 cohort) — any idea that contradicts today's incident-batch diagnoses gets flagged RED.
5. **Rank surviving candidates** by:
   - (a) blast radius small → high rank (docs/1-file ≫ multi-file)
   - (b) edge-per-class impact high → high rank
   - (c) certainty of payoff (shipped-elsewhere ≫ speculative)

## Buckets

- **ACTIONABLE-NOW** — small blast radius, verified gap (incidents-batch sister item), can ship next session
- **ACTIONABLE-LATER** — verified value but multi-file / depends on Phase-4 PF-registry wire-up landing
- **PARKED** — DEFER verdict already on file (e.g. IDEA-E deferred 2026-05-24)
- **OUTDATED-SUPERSEDED** — already shipped in incidents batch / prior PRs
- **OPERATOR-PENDING** — needs human (DB secret rotation, paid API tier, manual reminder)

## Deliverables

- This plan: `reports/peer_claude-phase9-daily-ideas-review_plan_2026-05-31.md`
- Ranked result: `reports/peer_claude-phase9-daily-ideas-review_result_2026-05-31.md`

## Out of scope

- Executing any idea (user wants Phase 1–8 to settle first; /money-maker-readyv2 is the next sequenced phase).
- Re-running multi-agent swarms (the May-15/16/17/19 syntheses are the canonical aggregations).
- The 15 `.qwen/tmp/review-pr-*` duplicate trees (content-identical to canonical files).
