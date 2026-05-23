# Swarm Model Test — 2026-05-18T05:29:33Z

Live connectivity + numeracy probe of every callable endpoint in `tools/swarm_models.py`. Class = the endpoint's DECLARED tier (reliable); `numerate` = did it pass a one-shot profit-factor probe (noisy sanity check — a declared-smart model failing it is flagged).

| endpoint | model | reachable | latency | numerate | class |
|---|---|---|---|---|---|
| deepseek | deepseek-reasoner | yes | 1.4s | yes | SMART |
| groq | llama-3.3-70b-versatile | NO | 0.0s | no | DEAD |
| cerebras | llama-3.3-70b | NO | 0.0s | no | DEAD |
| xai-grok | grok-3 | yes | 3.7s | yes | SMART |
| openrouter | deepseek/deepseek-chat | yes | 0.9s | no | SMART |
| kimi | moonshot-v1-32k | yes | 2.5s | no | SMART |
| mistral | mistral-large-latest | yes | 0.6s | no | SMART |
| mistral-codestral | codestral-latest | yes | 1.2s | yes | FAST |
| llm7 | qwen2.5-coder-32b | yes | 2.5s | yes | FAST |

## Classification

**SMART (5)** — quant reasoning, second-opinion consults: deepseek, xai-grok, openrouter, kimi, mistral

**FAST (2)** — breadth / quick checks, not quant verdicts: mistral-codestral, llm7

**DEAD (2)**: groq, cerebras

**Sanity flag** — declared-smart endpoints that failed the one-shot numeracy probe (probe noise, not necessarily a real problem; re-run to confirm): openrouter, kimi, mistral

## Consult-script fit

- `no_edge_cloud_consult.py` / `strategic_fork_consult.py` / `consult_ling_crypto.py` — verdict-grade reasoning -> use the SMART set only. A FAST model in a no-edge brainstorm produces confident noise.
- `pick_improvement_harvest.py` — idea breadth -> SMART + FAST both fine (more diverse inputs help; harness gates the result anyway).
- The asset-class diagnostic prompt (`reports/ASSET_CLASS_DIAGNOSTIC_PROMPT.md`) -> SMART set only; it demands numeric reasoning about PF/WR/walk-forward stability.
