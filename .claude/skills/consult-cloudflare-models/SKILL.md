---
name: consult-cloudflare-models
description: Multi-model fan-out across Cloudflare Workers AI. Lists all available text-gen models (Llama 3.3 70B, GPT-OSS 120B, Nemotron 3 120B, Qwen 3, GLM 4.7, Mistral, Phi, Gemma, etc.) and fans a single prompt to N of them in parallel, then aggregates replies. Use when the user says "/consult-cloudflare-models", "/consult-cloudflaremodels", "ask cloudflare models", "cf fan-out", or wants triangulation across multiple CF-hosted models. Subcommands - list, search, run, fan-out.
---

# consult-cloudflare-models

Fan a single prompt across multiple Cloudflare Workers AI text-generation models in one call. Complements `consult-cloudflare` (single-model with `list/search/run` subcommands) by being multi-model-by-default.

## When to use

- User says `/consult-cloudflare-models`, `/consult-cloudflaremodels`, "ask cloudflare models", "cf fan-out", "cf second opinions"
- User names ≥2 CF-hosted models: `llama-3.3-70b`, `gpt-oss-120b`, `nemotron-3-120b`, `qwen3-30b`, `glm-4.7-flash`, `mistral-small-24b`, `gemma-4-26b`
- User wants a triangulated panel across families
- User wants the `list` of available models before picking
- User explicitly wants CF (not NIM) for cost / region / latency reasons

For single-model CF calls use `consult-cloudflare`.

## Prerequisites

```bash
export CF_API_TOKEN='cfut_...'   # Cloudflare API token with Workers AI scope
export CF_ACCOUNT_ID='3c1f...'   # 32-char hex account id (dash.cloudflare.com right sidebar)
```

Verify the token:

```bash
curl -s "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer $CF_API_TOKEN"
```

`{"success":true,"result":{"status":"active"}}` = good. If the token is scope-restricted (typical for `cfut_` user tokens), `/user`, `/accounts`, `/memberships` will return 401 — only `/user/tokens/verify` and `/accounts/{id}/ai/*` are accessible. That's fine; the fan-out only needs the AI endpoint.

## Subcommands

### `list` — show all text-gen models on CF

```bash
curl -s "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/ai/models/search?per_page=200" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for m in d.get('result', []):
    if 'text-generation' in (m.get('task') or {}).get('name','').lower():
        print(m['name'])
"
```

### `search <keyword>` — filter

```bash
KW="${KW:-llama}"
curl -s "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/ai/models/search?per_page=200" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  | python3 -c "
import sys, json, os
kw = os.environ['KW'].lower()
for m in json.load(sys.stdin).get('result', []):
    if kw in m['name'].lower(): print(m['name'])
"
```

Useful keywords: `llama`, `gpt-oss`, `nemotron`, `qwen`, `glm`, `mistral`, `gemma`, `phi`, `deepseek`.

### `run <model> <prompt>` — single-model call

Use `consult-cloudflare` for this. Or directly (note: model name needs the `@cf/` prefix):

```bash
MODEL="${MODEL:-@cf/meta/llama-3.3-70b-instruct-fp8-fast}"
PROMPT="${PROMPT:-Give me a one-sentence answer.}"
curl -s --max-time 90 \
  "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/ai/run/$MODEL" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "
import json, os
print(json.dumps({
  'messages': [{'role': 'user', 'content': os.environ['PROMPT']}],
  'max_tokens': 1500,
}))")" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('result', {}).get('response', d))
"
```

### `fan-out` — fan one prompt to N CF models (the headline command)

```bash
# 1. Pick the panel — diversify families (note: CF uses @cf/ prefix on names)
PANEL=(
  "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
  "@cf/openai/gpt-oss-120b"
  "@cf/nvidia/nemotron-3-120b"
  "@cf/qwen/qwen3-30b-a3b-fp8"
  "@cf/z-ai/glm-4.7-flash"
  "@cf/mistralai/mistral-small-3.1-24b-instruct"
)

# 2. Write the prompt to a file
cat > /tmp/cf_prompt.txt <<'EOF'
Your prompt here. Self-contained — no tool access. Ask for quantitative + cited answers only.
EOF

# 3. Fan out (sequential)
mkdir -p /tmp/cf_fanout
for MODEL in "${PANEL[@]}"; do
  SLUG=$(echo "$MODEL" | tr '/@.-' '_____')
  PROMPT="$(cat /tmp/cf_prompt.txt)" MODEL="$MODEL" python3 -c "
import json, os, subprocess
model = os.environ['MODEL']
payload = {
  'messages': [{'role': 'user', 'content': os.environ['PROMPT']}],
  'max_tokens': 1500,
  'temperature': 0.3,
}
url = f'https://api.cloudflare.com/client/v4/accounts/{os.environ[\"CF_ACCOUNT_ID\"]}/ai/run/{model}'
r = subprocess.run(['curl','-s','--max-time','90', url,
  '-H', f'Authorization: Bearer {os.environ[\"CF_API_TOKEN\"]}',
  '-H', 'Content-Type: application/json',
  '-d', json.dumps(payload)], capture_output=True, text=True, timeout=95)
try:
    d = json.loads(r.stdout)
    if d.get('success') is False:
        out = f'ERROR: {d.get(\"errors\", d)}'
    else:
        out = d.get('result', {}).get('response') or json.dumps(d)[:1000]
except Exception as exc:
    out = f'ERROR: {exc}; raw={r.stdout[:400]}'
print(out)
" > "/tmp/cf_fanout/$SLUG.md" 2>&1
  echo "  -> /tmp/cf_fanout/$SLUG.md ($(wc -c < /tmp/cf_fanout/$SLUG.md) bytes)"
  sleep 0.5
done

# 4. Aggregate
for f in /tmp/cf_fanout/*.md; do
  echo "=== $(basename "$f" .md) ==="
  head -20 "$f"
  echo
done
```

## Curated panels

```bash
# Wide diversity (default for triangulation)
PANEL_WIDE=(
  "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
  "@cf/openai/gpt-oss-120b"
  "@cf/nvidia/nemotron-3-120b"
  "@cf/qwen/qwen3-30b-a3b-fp8"
  "@cf/z-ai/glm-4.7-flash"
)

# Smaller / cheaper (rapid checks)
PANEL_FAST=(
  "@cf/meta/llama-3.1-8b-instruct"
  "@cf/qwen/qwen3-8b-instruct"
  "@cf/google/gemma-3-4b-it"
)

# Reasoning-heavy
PANEL_REASON=(
  "@cf/openai/gpt-oss-120b"
  "@cf/nvidia/nemotron-3-120b"
  "@cf/mistralai/mistral-large-2"
)
```

## CF-specific pitfalls

- **`@cf/` prefix is required** in the run URL path — `meta/llama-3.3-70b-instruct-fp8-fast` won't resolve.
- **Some models reject `temperature`** — if you get a 400 about "unsupported field", drop it from the payload.
- **Rate limits are per-account, not per-model** — fan-out hits the same bucket. 5 models with `sleep 0.5` is fine; 20 will throttle.
- **Response shape varies**: most return `{"result": {"response": "..."}}` but some (especially older models) return `{"result": [{"response": "..."}]}` or just `{"result": "..."}`. The fan-out template above handles the common case; if a model gives empty output, inspect the raw response in `/tmp/cf_fanout/<slug>.md`.
- **`fp8-fast` variants** have ~30% lower latency at ~equivalent quality on Llama 3.3 — prefer them for fan-outs.

## When NOT to use

- Single-model question — use `consult-cloudflare` instead, simpler payload.
- Network-restricted environments (CF API needs egress to `api.cloudflare.com`) — fall back to NIM if NVIDIA egress is open.
- Production decision-making — multi-model votes are inputs to a human decision, not the decision itself.

## Related

- `consult-cloudflare` — single-model CF consult, has its own `list/search/run` subcommands
- `consult-nvidia-models` — same fan-out shape but NVIDIA NIM provider
- `swarm-run` / `swarm-second-opinion` — provider-agnostic fan-out / 3-engine consensus
- `tools/swarm/api_consult.py` — backend behind the existing consult skills
