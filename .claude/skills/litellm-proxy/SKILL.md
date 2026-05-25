---
name: litellm-proxy
description: Local LiteLLM proxy on http://localhost:4000 that fronts 14+ LLM providers (NVIDIA NIM, Groq, Cerebras, Together, Fireworks, GitHub Models, Gemini, DeepInfra, Nous, Mistral, AIMLAPI, Hypereal, Cloudflare, optional local vLLM) behind one OpenAI-compatible endpoint with auto-rotation on rate-limit / 429 / 401 failures. Use when the user says "/litellm-proxy", "start the rotating proxy", "set up routing for Roo/Kilo", or wants Roo / Kilo / any openai-SDK client to transparently fall through a key pool when one provider hits limits. Subcommands - start, stop, status, test.
---

# litellm-proxy

A single `http://localhost:4000/v1` endpoint that any `openai`-SDK client (Roo, Kilo, ChatGPT-style apps) can target. LiteLLM rotates through 12-14 working free-tier providers automatically — when one hits a rate limit or auth failure, the next in the chain serves the request transparently.

## What it gives you

- **One stable URL** (`http://localhost:4000/v1`) regardless of which upstream is healthy
- **One virtual model name** (`hybrid-model`) that resolves to the chain
- **Auto-rotation** on 429 / 401 / 5xx: failing provider cools down 5 min, others keep serving
- **All keys sourced from `~/dbpasses.txt`** at launch — never hardcoded in config
- **Cost + latency headers** on every response (`x-litellm-model-api-base`, `x-litellm-response-cost`, `x-litellm-attempted-retries`)

Verified 2026-05-25 end-to-end: `1+1?` → `2` (served by Hypereal/gpt-5.5-instant); 5-request burst served by 5 different upstreams (Fireworks, NVIDIA, Groq, Together, AIMLAPI); Cloudflare correctly recognised as RateLimitError and skipped.

## Quick start

```bash
# 1. One-time install (already done; only if .venv is rebuilt)
.venv/bin/python -m pip install 'litellm[proxy]'

# 2. Start (background)
bash tools/start_litellm_proxy.sh --background
#  → reads ~/dbpasses.txt, exports keys into env, launches on :4000
#  → logs to /tmp/litellm_proxy.log
#  → prints PID + kill command

# 3. Verify
curl -s http://localhost:4000/health/readiness        # → {"status":"healthy",...}
curl -s http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer anything" \
  -H "Content-Type: application/json" \
  -d '{"model":"hybrid-model","messages":[{"role":"user","content":"1+1?"}],"max_tokens":50}'

# 4. Stop
pkill -f 'litellm.*litellm_config'
```

## Roo / Kilo / OpenAI-SDK client setup

Point at the proxy with literally any placeholder API key:

```python
from openai import OpenAI
client = OpenAI(
    base_url="http://localhost:4000/v1",
    api_key="anything",   # LiteLLM accepts any placeholder; real auth is upstream
)
resp = client.chat.completions.create(
    model="hybrid-model",
    messages=[{"role": "user", "content": "Hello"}],
)
print(resp.choices[0].message.content)
```

For Roo / Kilo: in the OpenAI-compatible provider settings:
- **Base URL**: `http://localhost:4000/v1`
- **Model**: `hybrid-model`
- **API key**: any non-empty string

## Provider chain (in `litellm_config.yaml` order)

Tier 0 (deliberately first so rotation is testable): **Cloudflare** — currently 429-quota-exhausted; rotates immediately on every request.

Tier 1 (fast / sub-second): **Groq**, **Cerebras**

Tier 2 (generous free): **NVIDIA NIM**

Tier 3 (broad free): **Together AI**, **Fireworks**, **Mistral**, **Gemini**

Tier 4 (OpenAI-compat gateways): **GitHub Models**, **DeepInfra**, **AIMLAPI**, **Nous**, **Hypereal**

LiteLLM uses `routing_strategy: simple-shuffle` so it picks at random each request, spreading load. On failure it cools the failing instance for `cooldown_time: 300` seconds and retries the next.

## Observing rotation

Every response includes headers:

```
x-litellm-model-api-base:    https://api.groq.com/openai/v1   ← which upstream served
x-litellm-attempted-retries: 1                                 ← how many failed before this succeeded
x-litellm-response-cost:     0.00002                           ← dollars
x-litellm-response-duration-ms: 384
```

Tail the proxy log to watch live rotation:

```bash
tail -f /tmp/litellm_proxy.log | grep -iE '429|RateLimit|cooldown|api.[a-z]+\.'
```

## Direct-target a single provider (bypass rotation)

If you want to test or use one provider directly without fallback, address its concrete model name:

```bash
# example: hit groq directly (skips the hybrid-model chain)
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer anything" -H "Content-Type: application/json" \
  -d '{"model":"groq/llama-3.1-8b-instant","messages":[{"role":"user","content":"hi"}]}'
```

## Adding the local vLLM container as Tier 0

The repo's `DOCKER_VLLM.MD` documents how to run vLLM in Docker on port 8000. To put it FIRST in the chain (try local before any cloud), add this at the TOP of `model_list` in `litellm_config.yaml`:

```yaml
  - model_name: hybrid-model
    litellm_params:
      model: openai/Qwen/Qwen2.5-1.5B-Instruct   # or whichever model vLLM is serving
      api_base: http://localhost:8000/v1
      api_key: "local-vllm-key"                  # match --api-key passed to vLLM
      rpm: 100                                   # cap local throughput
```

Then restart the proxy. If vLLM is healthy it serves locally for ~free; on local OOM / context-overflow it falls through to the cloud chain.

## Known issues

- **`enable_fallbacks: true`** triggers a `WARNING: Key 'enable_fallbacks' is not a valid argument for Router.__init__()` on startup. Modern LiteLLM (1.86+) auto-fallbacks based on multiple model_list entries sharing a model_name — the explicit flag is redundant and ignored. Safe to ignore the warning.
- **Cloudflare provider quirk**: `account_id: os.environ/CF_ACCOUNT_ID` doesn't interpolate correctly on the `cloudflare/` provider prefix. We work around it by assembling `CF_API_BASE` in `start_litellm_proxy.sh` and using the `openai/` provider with the full per-account URL.
- **Thinking models (Gemini flash, GLM, Qwen3) need `max_tokens >= 100`** or they return empty content (the reasoning budget eats all the tokens before any visible output emits).
- **DB shows `Not connected` in `/health/readiness`** — that's expected; we run stateless without a database. Auth + rate-limit tracking is per-process in-memory.

## Files

- `litellm_config.yaml` — provider chain config
- `tools/start_litellm_proxy.sh` — launcher (sources keys from `~/dbpasses.txt`, exports CF_API_BASE, starts proxy)
- `~/dbpasses.txt` — keys file (gitignored, outside repo)
- `/tmp/litellm_proxy.log` — proxy log
- `tools/consult_multi.py` — sibling tool; shares the same key file + verified provider configs (use for one-shot consults / fan-outs; use the proxy for application-routing)
