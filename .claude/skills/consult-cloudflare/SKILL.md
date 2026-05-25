---
name: consult-cloudflare
description: Consult any text-generation model on Cloudflare Workers AI (37+ models from Meta, OpenAI, Qwen, Mistral, Google, NVIDIA, Z-AI, IBM, DeepSeek, Moonshot). Use when the user says "/consult-cloudflare", "/consult-cf", "ask cloudflare", "cf workers ai", or names a CF-hosted model (llama-3.3-70b, gpt-oss-120b, nemotron-3-120b, qwen3-30b, glm-4.7-flash, etc.). Subcommands - list, run, models, search.
---

# consult-cloudflare

Query any Cloudflare Workers AI text-generation model via the REST API. Includes auto-discovery (list / search) so you never have to memorize model slugs.

## When to use

- User says `/consult-cloudflare`, `/consult-cf`, "ask cloudflare", "cf workers ai"
- User names a CF-hosted model: `llama-3.3-70b`, `gpt-oss-120b`, `nemotron-3-120b`, `qwen3-30b`, `glm-4.7-flash`, `mistral-small-24b`, `gemma-4-26b`, etc.
- User wants a multi-model consensus call across CF models (use the `fan-out` subcommand)
- User wants to discover what's on CF before picking a model (use `list` or `search`)

## Prerequisites

Two env vars (do NOT hardcode in commits):

```bash
export CF_API_TOKEN='cfut_...'   # Cloudflare API token with Workers AI scope
export CF_ACCOUNT_ID='3c1f...'   # 32-char hex account id (from dash.cloudflare.com right sidebar)
```

Verify the token works:

```bash
curl -s "https://api.cloudflare.com/client/v4/user/tokens/verify" -H "Authorization: Bearer $CF_API_TOKEN"
```

`{"success":true,"result":{"status":"active"}}` means good. If the token is scope-restricted (typical for `cfut_` user tokens), `/user`, `/accounts`, `/memberships` will return 401 — that's expected, only `/user/tokens/verify` and `/accounts/{id}/ai/*` are accessible.

## Subcommands

### `list` — show all text-generation models

```bash
curl -s "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/ai/models/search?per_page=200" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
| python3 -c "
import sys, json
d = json.load(sys.stdin)
text_gen = [m for m in d['result'] if (m.get('task') or {}).get('name') == 'Text Generation']
for m in sorted(text_gen, key=lambda x: x['name']):
    print(f\"{m['name']:60s}  {m.get('description','')[:80]}\")
"
```

Current catalog (as of 2026-05-25 — 37 text-generation models):

| Family | Slug |
|---|---|
| Meta — Llama dense | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` |
| Meta — Llama MoE | `@cf/meta/llama-4-scout-17b-16e-instruct` |
| Meta — smaller | `@cf/meta/llama-3.1-8b-instruct-fp8`, `@cf/meta/llama-3.2-3b-instruct`, `@cf/meta/llama-3.2-1b-instruct`, `@cf/meta/llama-3-8b-instruct`, `@cf/meta/llama-3.2-11b-vision-instruct`, `@cf/meta/llama-guard-3-8b` |
| NVIDIA | `@cf/nvidia/nemotron-3-120b-a12b` |
| OpenAI open weight | `@cf/openai/gpt-oss-120b`, `@cf/openai/gpt-oss-20b` |
| Qwen | `@cf/qwen/qwen3-30b-a3b-fp8`, `@cf/qwen/qwq-32b`, `@cf/qwen/qwen2.5-coder-32b-instruct` |
| DeepSeek | `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b` |
| Moonshot | `@cf/moonshotai/kimi-k2.6`, `@cf/moonshotai/kimi-k2.5` |
| Z-AI | `@cf/zai-org/glm-4.7-flash` |
| Google Gemma | `@cf/google/gemma-3-12b-it`, `@cf/google/gemma-4-26b-a4b-it`, `@cf/google/gemma-2b-it-lora`, `@cf/google/gemma-7b-it-lora`, `@hf/google/gemma-7b-it` |
| AISG | `@cf/aisingapore/gemma-sea-lion-v4-27b-it` |
| Mistral | `@cf/mistralai/mistral-small-3.1-24b-instruct`, `@cf/mistral/mistral-7b-instruct-v0.1`, `@cf/mistral/mistral-7b-instruct-v0.2-lora`, `@hf/mistral/mistral-7b-instruct-v0.2` |
| IBM | `@cf/ibm-granite/granite-4.0-h-micro` |
| Microsoft | `@cf/microsoft/phi-2` |
| Defog (SQL) | `@cf/defog/sqlcoder-7b-2` |
| Nous | `@hf/nousresearch/hermes-2-pro-mistral-7b` |
| Meta-Llama LoRA | `@cf/meta-llama/llama-2-7b-chat-hf-lora`, `@cf/meta/llama-2-7b-chat-fp16`, `@cf/meta/llama-2-7b-chat-int8`, `@cf/meta/llama-3.1-8b-instruct-awq`, `@cf/meta/llama-3-8b-instruct-awq` |

Always re-run the `list` command to get the live catalog — the table above goes stale.

### `search <pattern>` — filter the catalog

```bash
curl -s "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/ai/models/search?search=<pattern>" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
| python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)['result']]"
```

Example: `search=llama` → all 13 Llama variants. `search=120b` → the two largest (gpt-oss-120b, nemotron-3-120b).

### `run <model> <prompt>` — single call (non-streaming)

```bash
MODEL='@cf/meta/llama-3.3-70b-instruct-fp8-fast'
PROMPT='Your prompt here'

curl -s "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/ai/run/$MODEL" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "import json,sys; print(json.dumps({'messages':[{'role':'user','content':sys.argv[1]}],'max_tokens':4096,'temperature':0.4}))" "$PROMPT")" \
| python3 -c "import sys,json; r=json.load(sys.stdin); print(r['result']['response'] if r.get('success') else r['errors'])"
```

Python equivalent (cleaner for multi-turn or non-trivial payloads):

```python
import os, json, requests
acct, tok = os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"]
model = "@cf/openai/gpt-oss-120b"  # any slug from `list`
url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}"
payload = {
    "messages": [{"role": "user", "content": "Your prompt"}],
    "max_tokens": 4096,
    "temperature": 0.4,
    # "stream": True,  # SSE; see `stream` section below
}
r = requests.post(url, headers={"Authorization": f"Bearer {tok}"}, json=payload, timeout=180)
data = r.json()
print(data["result"]["response"] if data.get("success") else data["errors"])
```

### `run --stream` — SSE streaming

Workers AI returns Server-Sent Events when `stream: true`:

```python
r = requests.post(url, headers={"Authorization": f"Bearer {tok}"},
                  json={**payload, "stream": True}, stream=True, timeout=180)
for line in r.iter_lines():
    if not line: continue
    ln = line.decode("utf-8")
    if not ln.startswith("data: "): continue
    data = ln[6:].strip()
    if data == "[DONE]": break
    obj = json.loads(data)
    # Workers AI streams "{response: '...token...'}" per chunk (NOT OpenAI-shape)
    piece = obj.get("response", "")
    if piece: print(piece, end="", flush=True)
```

**Important shape gotcha:** Workers AI streaming chunks are `{"response": "<token>"}`, NOT the OpenAI `{"choices":[{"delta":{"content":"..."}}]}` shape. Don't reuse OpenAI parser code without adjusting.

### `fan-out <prompt> [--models slug1,slug2,...]` — multi-model consensus

For getting a cross-model second opinion (e.g. on a quant scoring formula). Default panel: `llama-3.3-70b`, `gpt-oss-120b`, `nemotron-3-120b`, `qwen3-30b`, `glm-4.7-flash`, `mistral-small-24b`. Run them sequentially or in a thread-pool; collect all responses; write to a single markdown report.

Reference implementation: `tools/swarm/cf_fanout.py` (create with this skill — see template below).

```python
# tools/swarm/cf_fanout.py
import os, json, sys, time, requests
ACCT, TOK = os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"]
DEFAULT_PANEL = [
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "@cf/meta/llama-4-scout-17b-16e-instruct",
    "@cf/nvidia/nemotron-3-120b-a12b",
    "@cf/openai/gpt-oss-120b",
    "@cf/qwen/qwen3-30b-a3b-fp8",
    "@cf/zai-org/glm-4.7-flash",
    "@cf/mistralai/mistral-small-3.1-24b-instruct",
]
def call(model, prompt, history=None):
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCT}/ai/run/{model}"
    messages = (history or []) + [{"role":"user","content":prompt}]
    r = requests.post(url, headers={"Authorization": f"Bearer {TOK}"},
                      json={"messages":messages, "max_tokens":4096, "temperature":0.4},
                      timeout=240)
    data = r.json()
    return data["result"]["response"] if data.get("success") else f"[ERROR {data.get('errors')}]"

if __name__ == "__main__":
    prompt = sys.stdin.read()
    models = sys.argv[1].split(",") if len(sys.argv) > 1 else DEFAULT_PANEL
    for m in models:
        t0 = time.time()
        out = call(m, prompt)
        print(f"\n=== {m} ({time.time()-t0:.1f}s, {len(out)} chars) ===\n{out}\n")
```

Usage:

```bash
echo "Give me a stock-prediction-algorithm scoring formula in 200 words" | \
  python3 tools/swarm/cf_fanout.py \
  '@cf/meta/llama-3.3-70b-instruct-fp8-fast,@cf/openai/gpt-oss-120b,@cf/qwen/qwen3-30b-a3b-fp8'
```

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `{"errors":[{"code":10000,"message":"Authentication error"}]}` on `/accounts` or `/user` | `cfut_` token is scope-restricted to Workers AI only | Don't try to introspect — use the token directly against `/accounts/{id}/ai/run/{model}` |
| `403 Forbidden` on a specific model | model requires "AI Models — Run" permission AND has billing implications | Verify the token includes "Workers AI Read+Run" scope at `dash.cloudflare.com/profile/api-tokens` |
| Streaming returns nothing | parser expects OpenAI shape | Workers AI SSE chunks are `{"response": "..."}` — see streaming section above |
| `model not found` | typo in slug — `qwen3-max` is NOT on CF (closest = `qwen3-30b-a3b-fp8` + `qwq-32b`) | Run `list` first to confirm available slugs |
| Response truncated mid-sentence | `max_tokens` floor too low | Bump to 4096-8192 (CF default is 256!) |

## Notes

- Workers AI is OpenAI-compatible-ish at the message-shape level (`{role, content}`) but NOT at the response-shape level: the JSON envelope is `{success: true, result: {response: "..."}}` not `{choices: [...]}`.
- All slugs start with `@cf/<vendor>/<model>` (Cloudflare-managed) or `@hf/<vendor>/<model>` (HuggingFace-mirrored).
- Token in this repo: see `/home/eaguiar2015/.bashrc` or ask user for `CF_API_TOKEN`. Account ID `3c1f2867a7120334ef745ceb9345d9e6` (host: zerounderscore@gmail.com).
- For non-CF NVIDIA models (DeepSeek-R1-distill, Kimi-k2.6, MiniMax-m2.7) use `/consult-nvidia-deepseek` — different endpoint, different model catalog.

## Reference

- CF Workers AI catalog (live): `https://api.cloudflare.com/client/v4/accounts/{acct}/ai/models/search?per_page=200`
- CF Workers AI REST docs: https://developers.cloudflare.com/workers-ai/get-started/rest-api/
- Companion skills: `/consult-nvidia-deepseek`, `/consult-ring`, `/consult-grok`, `/swarm-run` (multi-engine fan-out)
