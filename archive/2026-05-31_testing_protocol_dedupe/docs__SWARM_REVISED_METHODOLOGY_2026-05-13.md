# Revised Swarm Methodology — 2026-05-13

Comprehensive proposed redesign of `tools/swarm/` and `ruflo_swarm/`
covering 9 feature areas. To be reviewed by agent swarm + then
implemented in priority order.

Companion docs:
- `docs/SWARM_PROMPT_CRITIQUE.md` — Pattern 1 detail (single-engine pre-step)
- `docs/SWARM_MEMORY.md` — Memory-backend feature
- `docs/SWARM_TYPE_ROUTER.md` — User-intent → swarm-type recommendation

## 1. Reasoning-effort parameter (SHIPPED partial)

Status: `tools/swarm/api_consult.py` ships `SWARM_REASONING_EFFORT={low,medium,high,max}` env-gated whitelist (xai/openrouter/opencode). Other engines silently no-op.

**Remaining work:**
- Add CLI flag `--reasoning {low,medium,high,max}` to `swarm_run.py`
- Probe-list extension: Anthropic (`thinking: budget`), DeepSeek-R1 (`reasoning_content`), Kimi K2-thinking (model variant)
- Cost-multiplier table: `high` reasoning typically 3-10x token-cost; surface in pre-dispatch estimate

## 2. Prompt-critique pre-step (NEW — high leverage)

**Idea:** Before any expensive fanout, dispatch ONE cheap engine to critique
the prompt itself:
- "How would you improve this prompt?"
- "What ambiguities could cause inconsistent interpretation?"
- "What related topics may the prompt-creator have overlooked?"
- "What's the minimum prompt scaffolding that would reduce engine variance?"

Output: a `prompt_critique_<ts>.md` next to the prompt. User reviews + can:
- Accept original
- Apply suggested rewrites
- Add overlooked topics

**Implementation:** `swarm_run.py --critique-first` flag. Optionally
`--critique-engine xai` (defaults to xai for meta-reasoning per
`engine_meta_observations`). Cost: ~$0.001/critique vs $0.05 wasted
fanout on bad prompts.

**Output template:**
```
# Prompt critique — <timestamp>
## Summary verdict: NEEDS_REWRITE | OK_AS_IS | NEEDS_SCAFFOLDING

## Suggested rewrites
- ...

## Overlooked topics (consider adding)
- ...

## Ambiguities flagged
- ...

## Estimated variance reduction
- N% (low-medium-high)
```

## 3. Self-check pre-answer round (NEW — variant of #2)

**Variant of #2:** Instead of ONE engine critiquing, have EVERY participating
engine critique the prompt BEFORE answering. Then merge their critiques
into an improved prompt. Then re-fanout the improved prompt for the
actual answer.

**Tradeoff:** Costs 2x (critique pass + answer pass) but reduces variance
sharply when engines disagree on prompt interpretation.

**Use case:** strategic/exploratory questions where prompt-clarity matters
more than answer-speed. Skip for code-review style where deterministic
prompts already exist.

**Implementation:** `--critique-all` flag. Two-stage internal flow:
1. Fan out critiques to all engines
2. Merge critiques (deterministic: union of suggestions)
3. Display merged-improved prompt + ask user confirm
4. Re-fanout for actual answer

## 4. Memory backend (NEW — Holographic/Hindsight/OpenViking)

**Idea:** Cache prior swarm Q&A. Before any fanout, query memory for
similar question. Return cached answer (or augment with deltas) instead
of re-running the swarm.

**Backend candidates per user screenshot:**

| Provider | Storage | Cost | Approach | Best fit |
|---|---|---|---|---|
| **Hindsight** | Local or Cloud | Free (local) | Knowledge graph + reflect synthesis | High — best LongMemEval (91.4%) |
| **Holographic** | Local SQLite | Free | HRR algebra + trust scoring | Best for fully-local, zero-deps |
| **OpenViking** | Self-hosted | Free | Tiered L0/L1/L2 (80-90% token savings) | Best for cost reduction |
| Mem0 | Cloud | Freemium | Server-side LLM extraction | Skip — Freemium pricing risk |
| ByteRover | Local or Cloud | Freemium | Human-readable Markdown KB | Best for human-inspectable cache |

**Recommendation:** **Holographic** (zero-deps SQLite local) for v1 simplicity,
upgrade to Hindsight when knowledge-graph synthesis matters.

**Cache key:** SHA256(normalized_prompt). Normalize via:
- Strip timestamps, dates
- Strip commit SHAs older than 7 days
- Strip ephemeral session IDs

**Hit policy:**
- Same prompt SHA within 7 days → return cached (`--cache-mode strict`)
- Similar prompt (>70% semantic similarity) → return cached + flag delta
  (`--cache-mode loose`)
- Force-rerun via `--no-cache`

**Implementation:** new `tools/swarm/swarm_memory.py` module with
`get_cached(prompt_hash)`, `store_result(prompt_hash, results)`,
`semantic_lookup(prompt)`.

## 5. Swarm-type router (NEW — user-intent recognition)

**Idea:** User describes their need in plain English. System suggests
which swarm-type to use based on intent classification.

**Swarm types catalog:**

| Type | Engines | Cost | When |
|---|---|---|---|
| `fast-cheap` | groq+deepseek | ~$0.005 | Quick consensus / yes-no decisions |
| `consensus-3` | deepseek+xai+kilo | ~$0.03 | Standard 3-engine vote |
| `deep-strict` | claude+kilo+deepseek | ~$0.10 | High-stakes code review |
| `non-opus-4` | xai+deepseek+groq+cerebras | ~$0.04 | True cross-family diversity |
| `all-paid-api` | 7 engines | ~$0.15 | When budget allows; max coverage |
| `all-keyless-local` | ollama_local | $0 (compute time) | Zero-budget verification |
| `code-review` | deepseek+groq+xai | ~$0.04 | Code-specific |
| `strategic-meta` | xai+deepseek | ~$0.03 | Process-level / blind-spot mining |

**Recognition heuristic** (LLM call OR keyword routing):
- "is this safe to merge" → `code-review`
- "what am I missing" → `strategic-meta`
- "rank these options" → `consensus-3`
- "find a github library for X" → `non-opus-4` (cross-vendor coverage)

**Implementation:** `swarm_run.py --auto-type "free-form ask"` — calls one
xai routing pass + maps to preset + confirms with user before fanout.

## 6. Prompt-optimization wizard (NEW — extends #2)

**Idea:** User types a basic ask. System produces a fully-scaffolded
prompt with:
- Clear output schema
- Cited inputs (file paths, line numbers)
- Constraint section (CLAUDE.md / Wire-Up Rule etc)
- Bonus self-assessment line

Then asks user to confirm BEFORE dispatching the (expensive) fanout.

**Difference from #2:** #2 is engine-self-critique; #6 is template-driven
expansion of a too-short user input. Both can be combined.

**Implementation:**
```bash
python tools/swarm/swarm_run.py --optimize-prompt "Q: which github lib should we use for bond strategies"
# emits prompts/optimized_<ts>.md
# prompts user to review + confirm
# then runs fanout with the expanded version
```

## 7. Self-learning loop (NEW — leverages memory + verdicts)

**Idea:** After every swarm round, score each engine's verdict against
ground-truth (observed in main repo via subsequent commits / actual
outcome / DB-verify results).

**Inputs:**
- `swarm_runs/<ts>/_summary.json` (engine outputs)
- `git log` post-swarm (which engine's verdict actually got acted on)
- For trading prompts: real outcome 30/60/90d later

**Outputs:** persistent engine-reliability scoreboard:
```
{
  "engine": "xai",
  "rounds": 47,
  "agreed_with_ground_truth": 38,
  "agreement_rate": 0.808,
  "fabrication_count": 0,
  "specialty_strength": "meta-reasoning",
  "specialty_weakness": "speed"
}
```

**Use:** future `--auto-engines` picks per-question-class strongest engine
based on historical scoreboard.

## 8. Github research — top coding/research swarms

To inspect for feature ideas:
- **OpenAI Swarm** (github.com/openai/swarm) — handoff patterns
- **CrewAI** (github.com/crewAIInc/crewAI) — role-based crews
- **AutoGen** (github.com/microsoft/autogen) — multi-agent conversation framework
- **AgentVerse** (github.com/OpenBMB/AgentVerse) — debate orchestration
- **MetaGPT** (github.com/geekan/MetaGPT) — SOP role templates
- **CAMEL** (github.com/camel-ai/camel) — role-playing protocols
- **DSPy** (github.com/stanfordnlp/dspy) — prompt programming
- **Letta** (github.com/letta-ai/letta) — memory for agents (was MemGPT)

Plus proprietary inspection: Anthropic Computer Use, OpenAI Operator,
Cursor Composer, Cline (CLI Claude Engineer).

**Feature ideas worth extracting:**
- DSPy's auto-prompt-compilation (replace `--optimize-prompt` with
  learned-from-evals scaffolding)
- AutoGen's group-chat-with-moderator (replace flat fanout with
  debate-style turn-taking)
- CrewAI's role separation (we have personas/ already)
- Letta's memory layer (covers #4)

## 9. Costs of "smarter" — feature priorities

Not every feature is worth the complexity. Rank by impact/effort:

| Feature | Impact | Effort | Priority |
|---|---|---|---|
| 1 reasoning-effort | High | Low (partial done) | P0 — finish CLI flag |
| 2 prompt-critique pre-step | High | Low | P0 — one new script |
| 6 prompt-optimization wizard | High | Med | P1 |
| 4 memory backend (Holographic) | High | Med-High | P1 |
| 5 swarm-type router | Med | Low | P1 |
| 7 self-learning loop | High | High | P2 — needs eval framework |
| 3 self-check pre-answer (variant of #2) | Med | Med | P2 — cost doubles |
| 8 import OpenAI Swarm / DSPy patterns | Med | High | P3 — research first |

## What to ship first (recommendation)

P0 sprint (3-5h work):
1. CLI flag `--reasoning {low,medium,high,max}` on `swarm_run.py`
2. `swarm_run.py --critique-first` pre-step (write to `prompt_critique_*.md`)
3. Document via `examples/critique_then_fanout.yaml`

P1 sprint (later):
1. Holographic memory cache
2. Swarm-type router (intent-class → preset)
3. Prompt-optimization wizard

P2 sprint (advanced):
1. Self-learning scoreboard with engine routing
2. DSPy-style prompt compilation

## NFA

Research surface only. No code changes in this commit — only design.
Implementation requires explicit user approval + 4-engine swarm review
of THIS doc.
