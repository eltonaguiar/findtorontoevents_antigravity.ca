# Engine Meta-Observations — Across 4 Swarm Rounds — 2026-05-13T01:50Z

Combining 4 multi-engine swarm rounds executed this session:
- Round A: groq + cerebras + xai + deepseek (next-P0 review)
- Round 2: post-concentration plan (same engines)
- Round 3: action-items NS-A through NS-E (non-opus-4 preset)
- Round 4: multi_family review (xai + deepseek + kimi + groq + cerebras)
- Round B: round_b (ollama_cloud + openrouter + opencode + kimi)
- Round C: round_c (ollama_local qwen3:14b)
- Round D: round_d (nous)

## Per-engine consistency across rounds

| Engine | Rounds | Avg quality | Speed | Failures | Notable |
|---|---|---|---|---|---|
| **xAI Grok-4** | 4 | High | 18-23s | 0 | Sole META-issue spotter (swarm-reliability gap) |
| **DeepSeek-V3** | 4 | High | 14-27s | 0 | Highest specificity; honest self-assessment "I'm a debugger not designer" |
| **Cerebras Llama-3.3** | 4 | Medium | 2-3s | 3-of-4 fab pattern | Round-4 was clean — first clean round |
| **Groq Llama-3.3** | 4 | Medium | 1-2s | 0 | Stable baseline; never novel |
| **Kimi K2** | 3 | Variable | 498s when works | 1 empty (Round 4 + Round B 655 bytes truncated) | Specialty notes when responds |
| **Opencode (Grok-4.x backend)** | 1 | High | 51s | 0 | "Cross-source contradiction detection" — strong on the kimi_signal_tracking 1174-vs-18 denominator catch |
| **Openrouter (GPT-4o-mini default)** | 1 | Medium | 8s | 0 | Standard analytical, no novel angle |
| **Ollama_cloud** | 1 | Medium-High | 26s | 0 | Convergent picks match paid engines |
| **Ollama_local qwen3:14b** | 1 | Medium | local | 0 | Convergent w/ paid; cheap |
| **Nous Hermes-4-70B** | 1 | Medium-High | ~5min | 0 | Convergent picks; novel framing on "comprehensive risk framework" gap |

## "Was it the model or the prompt?" — observations

### Where genius appeared

**xAI consistently** identified META-issues across multiple rounds (swarm
reliability auditing in Round 4 + supreme-plan blind spots in Round 2).
This is unlikely prompt-coincidence — DeepSeek + Groq got the SAME
prompts and didn't flag META-issues. Genuine architectural difference.

**DeepSeek consistently** found 4 distinct concrete blind spots vs
others' 1-2. This IS prompt-quality-dependent: when the prompt asked
"flag missing items" without scaffolding, DeepSeek auto-enumerated.
Other engines waited for cue. Useful in code-review style prompts.

**Opencode's "1174 vs 18 denominator" insight** was a true catch that
none of the other engines noted (the kimi PF reversal could have been
read as data integrity bug; opencode immediately spotted the resolver-
denominator difference). Strong on numerical provenance.

### Where consensus = coincidence

When 4 engines unanimously rank "AA-2 high ROI, AA-5 low ROI," that's
mostly **prompt clarity**, not genius. The prompt pre-labeled effort
hours + dependencies, leading every engine to the same calculus.

### Where consensus = real signal

When 4 engines independently flag the SAME blind spot ("no live-
monitoring for new sidecars" — appeared in DeepSeek + Cerebras + Nous
across 3 rounds), that converges across architectures. Worth treating
as truth.

### Prompt quality matters more than model in some cases

The structured 3-phase prompt produced consistent 800-word responses
from all 4 paid engines. The earlier round-1 8-question prompt (less
scaffolded) produced wildly different lengths (2k - 6k chars) and one
hallucination from Cerebras. Lesson: **schema-constrained prompts
reduce engine variance** + reduce fabrication risk.

## When to trust which engine

| Use case | Trust | Why |
|---|---|---|
| Numerical provenance audit (denominator checks, math) | opencode > DeepSeek > xAI | opencode caught kimi 1174-vs-18; DeepSeek caught capped_vs_raw 500-cap differences |
| Meta-process design (workflow improvements, blind spots) | xAI > all | only one to flag swarm-reliability + user-action-deadline gaps |
| Code review (find bugs in diff) | DeepSeek > xAI > groq | DeepSeek's debug-oriented self-assessment is accurate |
| Free-tier consensus (no API cost) | ollama_local + groq | Both convergent with paid engines; near-zero variance from baseline |
| Specialty topic (China-context, niche libraries) | Kimi (when works) | 50shadesofgwei github recall is impressive vs others' generic freqtrade |
| AVOID solo | Cerebras (historic fab) | Use only with dual-corroboration |

## Reasoning-level effort impact (new this commit)

Shipped: `SWARM_REASONING_EFFORT=high|max` env var injects `reasoning_effort`
field into OpenAI-compat body for xAI, OpenRouter, Opencode. Other engines
silently ignore (OpenAI-compat spec). Test before broad use:

```bash
SWARM_REASONING_EFFORT=high python tools/swarm/swarm_run.py \
  --prompt-file <some_prompt.md> \
  --engines xai \
  --out-dir swarm_runs/reasoning_test
# Compare output quality + token count vs default
```

If output quality lifts on xAI/Opencode without cost explosion: enable
default for STRATEGIC prompts. Keep OFF for code-review prompts (the
deterministic style xAI defaults to is already good there).

## Recommended pattern going forward

### Pattern 1: "prompt-critique pass" before fanout (user suggested)

Before any expensive multi-engine fanout, do a 1-engine pre-step asking:
- "How would you improve this prompt?"
- "What related topics may the prompt creator have overlooked?"
- "Are there ambiguities that could cause inconsistent interpretation?"

Saves swarm spend on bad prompts. Use **xAI** for this critique step
(strongest at meta-reasoning). One call ~$0.001 vs full fanout ~$0.05.

### Pattern 2: Two-stage swarm
- Stage 1: cheap engine fan-out (groq + ollama_local + ollama_cloud) for breadth
- Stage 2: expensive engines (xAI + DeepSeek) on top-3 contested items

Cost ~30% of full-paid fanout. Reserves expensive-engine attention for
where disagreement actually matters.

### Pattern 3: Engine-routing by question class

| Question | Use |
|---|---|
| "What's missing?" | xAI |
| "Is this code correct?" | DeepSeek |
| "Verify these numbers" | Opencode |
| "Ship this or not?" | Multi-engine consensus (deepseek + xai + groq) |
| "Find a github repo for X" | Kimi (specialty recall) + DeepSeek (verification) |

## NFA

Observational notes only. Reasoning-effort feature is opt-in env-gated;
defaults preserved. Engine routing patterns are recommendations not
enforcement.
