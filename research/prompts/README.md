# Peer consult prompts

Prompts sent to other models via [`tools/consult_multi.py`](../../tools/consult_multi.py).
A peer's answer is an **advisor's opinion**, never evidence. If a peer names a
mechanism the repo has not measured, it becomes a hypothesis to test. If a peer
returns nothing, record `UNMEASURED` — never manufacture agreement.

## Provider status (probed 2026-11-22, this machine)

| provider | result |
|---|---|
| cloudflare | PONG |
| deepinfra | PONG |
| huggingface | PONG |
| nous | 404 Not Found |
| groq | 404 Not Found |
| cerebras | 404 Not Found |
| mistral | 429 Too Many Requests |
| gemini_api | 503 Service Unavailable |

**The `diverse5` preset is broken** (nvidia/groq/cerebras/together/fireworks).
Do not use `--fanout diverse5` until it is re-probed and passes. Use an
explicit `--peers` list of the PONG providers above.

## Standard invocation

```bash
mkdir -p /tmp/consult/<class>
python3 tools/consult_multi.py \
  --peers "cloudflare:@cf/meta/llama-3.1-8b-instruct,deepinfra:meta-llama/Meta-Llama-3.1-8B-Instruct,huggingface:openai/gpt-oss-20b" \
  --prompt-file research/prompts/<class>_edge_consult.md \
  --out-dir /tmp/consult/<class>
```

## Prompt contract

Every per-class prompt must contain:

1. **The mechanism under test** and why it might be real (economic reason).
2. **The measured evidence so far** with exact numbers (PF, n, CI, halves).
3. **The specific question** — usually "is this a documented, non-arbitraged
   edge, and what is the minimum sample for it to be credible?"
4. **The constraint** that the answer must be falsifiable: name a test.

Never include private data, credentials, or customer information in a prompt.
