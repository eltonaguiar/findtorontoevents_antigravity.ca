# Persona Router Architecture

**Status:** design draft (2026-05-04). Not yet implemented. Inspired by Kimi's two-layer routing pattern that the user surfaced after dispatching the generative invent-personas subagent. This doc supersedes "ask Mercury to invent personas" as the **primary** mechanism. The generative approach becomes the **fallback** path only.

## Why routing beats generation

Generation pitfalls we'd hit otherwise:
- **Persona drift** — every call produces slightly different personas; can't compare results across runs.
- **Hallucinated specialists** — model invents "Kafka Consensus Engineer" for a problem that doesn't need one.
- **Latency + cost** — every problem pays for design-time LLM calls before any actual work happens.
- **Unauditability** — no versioning; persona quality varies per random seed.

Routing wins:
- **Deterministic** — same input → same persona selection. Reproducible.
- **Fast** — keyword + embedding match runs in <50ms; no LLM call needed for the common case.
- **Versioned library** — personas are committed files; changes go through PR review.
- **Auditable** — routing decisions log which personas matched, with confidence scores.
- **Composable** — multi-step tasks chain via explicit `[HANDOFF: <persona>]` tags rather than implicit "next agent figures it out."

## Two-layer architecture

```
problem.md → [Layer 1: Domain Router] → base persona(s) (1-3)
                                          ↓
                              [Layer 2: Capability Matcher] → variant + tool spec
                                          ↓
                              [Orchestrator] → fan-out → run
                                          ↓
                              [Handoff Parser] → next persona | done
                                          ↓
                              [Fallback: invent_personas] (only if no match ≥ confidence threshold)
```

### Layer 1 — Domain Router

**Input:** problem text + optional `--hint <tag>`
**Output:** ranked list of base persona names with confidence scores

**Implementation:** `tools/swarm/persona_router.py`
- Pass 1: regex/keyword matcher against `tools/swarm/agent_personas/INDEX.md` "trigger keywords" column (we'll add this column). Examples:
  - `race condition`, `stopPropagation`, `mutex`, `setTimeout` → `race-condition-specialist`
  - `timezone`, `UTC`, `getMonth`, `Date(`, `year wrap` → `datetime-timezone-specialist`
  - `MutationObserver`, `React reconciliation`, `inline style` → `react-dom-specialist`
  - `forex`, `EUR`, `JPY`, `pip`, `pair` → `forex-specialist`
  - `crypto`, `BTCUSDT`, `funding rate` → `crypto-specialist`
  - …etc.
- Pass 2: lightweight embedding similarity (optional — only if pass 1 returns 0 high-confidence matches). Use a small local embedder (sentence-transformers all-MiniLM-L6-v2 or simpler hash-based) over the first 200 tokens of each persona's `Scope` section. Keeps inference local; no LLM call.
- Pass 3: fallback to one tiny LLM call against `inception` (Mercury, fast+cheap) for a JSON output `{primary_persona, confidence, alternates}`. Only fires if both prior passes underperform.

**Confidence thresholds:**
- ≥0.7 → confident match; route directly
- 0.4-0.7 → return top-3 candidates, run all in parallel + add a coordinator
- <0.4 → fallback to `invent_personas.py` (generative path); log as "novel domain"

### Layer 2 — Capability Matcher

**Input:** selected base persona(s) + problem metadata
**Output:** specialization variant + tool requirements + depth/format

**Decision axes (orthogonal):**
- **Tools needed:** static-only / web-fetch / code-exec / playwright / FTP / gh-cli
- **Depth:** quick (single round, 1 engine) / standard (3-round × 5-engine) / deep (3-round × 8-engine + red-team)
- **Output format:** prose / structured JSON / code patch / playwright test / PR comment
- **Verification required:** none / unit-test / live-runtime-trace / human-eyeball

**Implementation:** add a `variants:` block to each persona file's frontmatter with axis-keyed sub-prompts. Matcher reads the axes from the problem metadata (or asks user to confirm via single prompt). Default to "standard depth + prose output + unit-test verification" when ambiguous.

### Handoff protocol

Every persona's required output format includes:

```markdown
## Next step
[HANDOFF: <persona-name> | DONE]
**Reason:** <one sentence>
**Context to pass:** <bullet list of facts/files/lines the next persona needs>
```

The orchestrator parses this tag after each persona's output and:
- `DONE` → run the coordinator-synthesizer to produce final report
- `[HANDOFF: <persona>]` → invoke that persona with the context block prepended to its prompt

Multi-step tasks are explicit. No implicit "next agent figures it out."

### Fallback — generative invent-personas

When Layer 1 returns confidence <0.4 across the entire library, fall back to the generative `invent_personas.py` (the subagent currently building this — its output becomes a NEW persona file, gets reviewed by a human, and is committed to the library so future runs of the same domain skip the fallback). The generative path is **rare-by-design** — every successful generation should reduce future generation calls by adding to the library.

## File layout (after full implementation)

```
tools/swarm/
  persona_router.py              ← new (Layer 1)
  capability_matcher.py          ← new (Layer 2)
  handoff_parser.py              ← new (parse [HANDOFF: x] tags)
  invent_personas.py             ← FALLBACK path (subagent currently building)
  agent_personas/
    INDEX.md                     ← extend with trigger_keywords column + variants block
    ROUTER_ARCHITECTURE.md       ← this file
    INVENT_PERSONAS_PROTOCOL.md  ← rewritten as fallback-path doc
    blueprints/                  ← generated test blueprints (rare; only when fallback fires)
    *.md                         ← existing personas; updated to include
                                   trigger_keywords + variants frontmatter + Next-step section
  swarm_dispatch.ps1             ← extend to call router first; pass results to fan-out
```

## Implementation phases

**Phase 1 — passive routing (1 day).** Build `persona_router.py` with regex pass only. Add `trigger_keywords:` to each persona's frontmatter. Output: a logging-only router that prints what IT would have selected, but doesn't change current behavior. Lets us validate routing decisions against actual swarm runs without breaking anything.

**Phase 2 — active routing (1 day).** Wire router into `swarm_dispatch.ps1` and `swarm_run.py` as `--auto-route`. Default off; manually opt-in via flag.

**Phase 3 — capability matcher + variants (2 days).** Add `variants:` block to each persona; build matcher; wire in.

**Phase 4 — handoff protocol (1 day).** Add `## Next step` section to every persona's required output format. Build `handoff_parser.py`. Wire orchestrator to chain.

**Phase 5 — fallback integration (0.5 day).** When router confidence <0.4, invoke `invent_personas.py` (already being built); after generation, prompt human to review + commit before re-running.

**Phase 6 — embedding pass (optional, 1 day).** Add local embedding similarity to Layer 1 if regex matches alone underperform.

Total: ~6.5 days for the complete two-layer + handoff system.

## What ships first

If short on time, **Phase 1 alone** is the highest-leverage win — it gives us deterministic routing logs we can compare to actual swarm runs to measure how often routing would have picked the right specialist. Do not build Phases 3-4 until Phase 1's data shows the regex-only router is matching ≥80% of recent runs.

## Blast radius vs the dispatched subagent's work

The subagent currently building `invent_personas.py` produces:
- `tools/swarm/invent_personas.py`
- `tools/swarm/agent_personas/INVENT_PERSONAS_PROTOCOL.md`
- `.claude/commands/swarm-invent.md`
- `tools/swarm/agent_personas/blueprints/` directory

None of those conflict with this router architecture. The subagent's work becomes the FALLBACK path. After it commits, we:
1. Rewrite `INVENT_PERSONAS_PROTOCOL.md` to clarify it's the fallback (not the primary mechanism).
2. Build phase 1 router on top.

🤖 Authored 2026-05-04 by the swarm-orchestrating Claude after the user pointed out that Kimi's actual production architecture uses routing, not generation.

---

## Addendum — Consensus Updates from Mercury + Grok (2026-05-04)

User cross-checked this design with Mercury (Inception Labs) and Grok (xAI). Three independent architectures converged. Refinements consolidated below — adopt these as the authoritative spec.

### 1. Concrete confidence thresholds

Per Mercury's empirical recommendation:
- **≥ 0.75** → confident; route directly to top match.
- **0.60 – 0.75** → return top-3 candidates; fan out parallel + coordinator.
- **< 0.60** → fall back. Never let a low-confidence routing pass through silently.

Replaces the rough 0.7 / 0.4 thresholds in the original draft.

### 2. Structured JSON handoff (NOT bare string tags)

Per Grok: handoff format upgrades from `[HANDOFF: x]` to structured JSON, parseable by JSON-mode / Outlines / Guidance. Required output block at the bottom of every persona's response:

```json
{
  "handoff": "<persona-name-or-DONE>",
  "reason": "<one sentence>",
  "context_summary": "<bullet-summary of state to pass>",
  "confidence": <float 0..1>
}
```

Why: bare `[HANDOFF: X]` is regex-fragile (multi-word persona names, special chars in reason). JSON is self-validating, parseable, future-proof. The orchestrator parses with `json.loads` after extracting the fenced block.

Regex fallback for legacy outputs: `\[HANDOFF:\s*(\w+(?:-\w+)*)\]`.

### 3. Persona registry as a single YAML file

Per both Mercury and Grok: switch from per-file frontmatter to a single version-controlled registry file: `tools/swarm/agent_personas/_registry.yaml`. Schema:

```yaml
version: "1.0.0"   # bump on breaking changes
personas:
  - name: race-condition-specialist
    base: critic                       # base persona class (8-15 base classes max)
    file: race_condition_specialist.md
    trigger_keywords:
      - stopPropagation
      - stopImmediatePropagation
      - mutex
      - capture-phase
      - synthetic click
      - rapid click
    embedding_text: |                  # short paragraph used for embedding similarity
      Concurrency bugs in single-threaded JS that look serial but interleave...
    variants:
      quick:    { tools: [Read, Grep], depth: single-pass }
      standard: { tools: [Read, Grep, Bash], depth: 3-round }
      deep:     { tools: [Read, Grep, Bash, Playwright], depth: 3-round + redteam }
    handoff_targets:                   # which personas it commonly hands off to
      - datetime-timezone-specialist   # if date logic is adjacent
      - react-dom-specialist           # if DOM-mutation is involved
      - coordinator-synthesizer        # for final wrap-up
    confidence_floor_for_match: 0.65   # per-persona override of global 0.75
    version: 1
    added: 2026-05-04
```

The persona MD file remains the system-prompt source of truth; the registry is the routing index. Both are committed.

### 4. Base persona classes (8-15, fixed)

Per Mercury + Grok consensus, every specialist must inherit from one of these base classes — keeps the routing table tractable:

| Base | Specialisations (examples in this repo) |
|---|---|
| **Researcher** | (none yet — would handle "find me X in the codebase / web") |
| **Coder** | (none yet — could split: front-end, back-end, data) |
| **Analyst** | forex / crypto / equity / etf / commodity / bond specialists |
| **Critic / Reviewer** | race-condition / datetime-timezone / react-dom specialists |
| **Coordinator** | coordinator-synthesizer (already exists) |
| **Planner** | (none yet) |
| **Translator** | (none yet) |
| **Cross-verifier** | cross-verification-auditor (already exists) |
| **ML-validator** | ml-validation-specialist (already exists) |
| **Generalist (fallback)** | new — see §5 |

Adding a new persona = picking a base class + filling out the registry + writing the MD file. Routing then "just works" because the registry tells the router how to match.

### 5. Generalist fallback persona (NEW)

Per all three architectures: when confidence <0.60, route to a **generalist** persona BEFORE invoking generative invent-personas. New file: `tools/swarm/agent_personas/generalist_kimi.md` (name nods to the source). The generalist:
- Reads the problem and produces a best-effort review using a broad system prompt.
- Includes an explicit "I am the generalist fallback. The router could not match a domain specialist with confidence ≥0.60. If this query recurs, consider adding a specialist persona via `invent_personas.py`." line in its output footer.
- Logs the unmatched query to `swarm_runs/_unmatched_queries.jsonl` for periodic review.

So the fallback chain is now:
```
Router → match ≥0.75 → specialist
       → match 0.60-0.75 → top-3 specialists + coordinator
       → match <0.60 → GENERALIST persona (NEW level)
                     → if generalist also fails / user re-prompts → invent_personas (LAST resort)
```

Generative invent-personas becomes a **rare-by-design** event triggered only after generalist + manual review.

### 6. Embedding model: `all-MiniLM-L6-v2`

Per Grok's specific recommendation. Reasons: small (90MB), local (no API call), fast (~30ms on CPU), good enough for short technical paragraphs. Alternative: `bge-small-en-v1.5`. Sentence-transformers is the wrapper.

Add as Phase 6 (optional) — implement only if Phase 1 regex matching alone hits <80% accuracy on a labeled validation set.

### 7. Optional tiny classifier (further fallback before generalist)

Per Grok: between embedding similarity and the generalist fallback, an optional tiny classifier (Phi-3-mini / Gemma-2B / Qwen2.5-3B distilled to intent classification) can give a probabilistic "best-guess" with confidence score. Only fires when embedding similarity ≥0.50 but <0.60 — i.e. "kinda matches but not enough." Adds a third routing pass without escalating to a full LLM call.

Mark as Phase 7 — only build if observability data shows >5% of queries land in the 0.50-0.60 ambiguous band.

### 8. Observability

Log every routing decision to `swarm_runs/_routing_log.jsonl`:
```json
{"ts":"2026-05-04T03:00:00Z", "query_hash":"abc123", "matched_persona":"race-condition-specialist", "confidence":0.82, "method":"regex", "fallback_used":false, "outcome":"success", "user_feedback":null}
```

Periodically review and retrain. A/B test alternate routing heuristics (regex-only vs regex+embedding vs regex+embedding+classifier).

### 9. Where the running invent-personas subagent's work fits

Subagent (currently building `tools/swarm/invent_personas.py`) produces the **last-resort fallback path**. Per the consolidated architecture above, it fires at most a few times per quarter once the library + router are mature. Its output gets human-reviewed and committed to the registry, which means future calls of the same domain skip the fallback entirely. Self-extinguishing system.

When the subagent finishes:
1. Rewrite `INVENT_PERSONAS_PROTOCOL.md` to flag it as the **third-level fallback** (after generalist), not the primary mechanism.
2. Add a banner to `invent_personas.py` saying "this should fire <1% of swarm calls; if it's firing more, the registry is incomplete — add the missing personas manually."

### 10. Implementation phase update

Original 6 phases tightened with consolidated thresholds + JSON handoff:

| Phase | What | Days |
|---|---|---|
| 1 | `_registry.yaml` + regex router + logging-only routing | 1 |
| 2 | Wire active routing into `swarm_dispatch.ps1` + `swarm_run.py` (`--auto-route`) | 1 |
| 3 | Capability matcher + `variants:` block per persona | 2 |
| 4 | JSON-handoff parser + orchestrator chain loop | 1 |
| 5 | Generalist fallback persona + invent-personas integration | 0.5 |
| 6 | (optional) Embedding similarity pass | 1 |
| 7 | (optional) Tiny classifier pass | 1 |
| 8 | Observability log + A/B harness | 0.5 |
| **Total** | | **8 days** (6 days for required phases) |

### 11. Stack choices for Phase 1

- Router service: pure Python, no FastAPI yet (keep simple — call it from `swarm_run.py` directly). Add FastAPI only if the router becomes its own deployable service.
- Persona invocation: existing `worker_runner.py` (no orchestration framework yet). Reassess LangGraph / CrewAI in Phase 4 when the chain loop gets non-trivial.
- State store: in-memory dict (current `_calls.jsonl` + `_sessions.db` already cover persistence).
- Observability: structured JSONL → eventual pull into Grafana via the existing `swarm_stats.py` pipeline.

🤖 Consolidated 2026-05-04 from 3 independent architectures: this Claude's original draft + Mercury (Inception Labs) + Grok (xAI). All three converged on the same skeleton; differences were specificity (thresholds, embedding model, JSON handoff format) which are now baked in.
