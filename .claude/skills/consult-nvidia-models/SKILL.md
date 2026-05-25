---
name: consult-nvidia-models
description: Multi-model fan-out across NVIDIA Integrate API (NIM). Lists all available text-gen models (DeepSeek v4 Pro, MiniMax, Kimi-K2.6, Nemotron, GPT-OSS, Z-AI GLM, Qwen, Llama-4, Mistral, etc.) and fans a single prompt to N of them in parallel, then aggregates replies. Use when the user says "/consult-nvidia-models", "/consult-nvidiamodels", "ask nvidia models", "nvidia multi-model", "nvidia fan-out", or wants triangulation across multiple NIM-hosted models. Subcommands - list, search, run, fan-out.
---

# consult-nvidia-models

Fan a single prompt across multiple NVIDIA-hosted text-generation models in one call. Complements `consult-nvidia-deepseek` (single-model) by being multi-model-by-default.

## When to use

- User says `/consult-nvidia-models`, `/consult-nvidiamodels`, "ask nvidia models", "nvidia fan-out", "nvidia second opinions"
- User names ≥2 NIM-hosted models: `deepseek-v4-pro`, `minimax-m2.7`, `kimi-k2.6`, `nemotron-ultra-253b`, `gpt-oss-120b`, `glm-5.1`, `qwen3-coder-480b`, `llama-4-maverick`, `mistral-large-3-675b`
- User wants a triangulated second-opinion call across families (e.g. "what do MiniMax + Kimi + GLM all say")
- User wants the `list` of available models before picking
- User wants to fan a quant/audit/strategy question to a panel of models

For single-model NIM calls, prefer `consult-nvidia-deepseek` — it's optimised for that path.

## Prerequisites

Set the API key in env (never hardcode):

```bash
export NVIDIA_API_KEY='nvapi-...'   # preferred name
# or NGC_API_KEY (also accepted by tools/swarm/api_consult.py)
```

Verify the key works:

```bash
curl -s --max-time 10 "https://integrate.api.nvidia.com/v1/models" \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  | python3 -c "import sys,json; print('OK,', len(json.load(sys.stdin).get('data',[])), 'models')"
```

## Subcommands

### `list` — show all text-gen models on NIM

```bash
curl -s --max-time 30 "https://integrate.api.nvidia.com/v1/models" \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin).get('data',[])]"
```

### `search <keyword>` — filter the list

```bash
KW="${KW:-glm}"
curl -s --max-time 30 "https://integrate.api.nvidia.com/v1/models" \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  | python3 -c "
import sys, json, os
kw = os.environ['KW'].lower()
for m in json.load(sys.stdin).get('data', []):
    if kw in m['id'].lower(): print(m['id'])
"
```

Useful keywords: `deepseek`, `minimax`, `kimi`, `nemotron`, `gpt-oss`, `glm`, `qwen`, `llama-4`, `mistral`, `phi`.

### `run <model> <prompt>` — single-model call

Use `consult-nvidia-deepseek` for this. Or directly:

```bash
MODEL="${MODEL:-deepseek-ai/deepseek-v4-pro}"
PROMPT="${PROMPT:-Give me a one-sentence answer.}"
curl -s --max-time 90 "https://integrate.api.nvidia.com/v1/chat/completions" \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "
import json, os
print(json.dumps({
  'model': os.environ['MODEL'],
  'messages': [{'role': 'user', 'content': os.environ['PROMPT']}],
  'max_tokens': 1500,
  'temperature': 0.3,
}))")" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

### `fan-out` — fan one prompt to N models, sequential calls (the headline command)

Save prompt to a file (avoids quoting hell), pick a model panel, fan out:

```bash
# 1. Pick the panel — diversify families
PANEL=(
  "deepseek-ai/deepseek-v4-pro"
  "minimaxai/minimax-m2.7"
  "moonshotai/kimi-k2.6"
  "nvidia/llama-3.1-nemotron-ultra-253b-v1"
  "openai/gpt-oss-120b"
  "z-ai/glm-5.1"
)

# 2. Write the prompt to a file
cat > /tmp/nim_prompt.txt <<'EOF'
Your prompt here. Keep it self-contained; the models have no tool/file access.
Tell them: be quantitative, cite the numbers in the prompt verbatim, do not invent.
EOF

# 3. Fan out (sequential — parallelism via & is fine but rate-limits bite)
mkdir -p /tmp/nim_fanout
for MODEL in "${PANEL[@]}"; do
  SLUG=$(echo "$MODEL" | tr '/.-' '___')
  PROMPT="$(cat /tmp/nim_prompt.txt)" python3 -c "
import json, os, sys, subprocess, time
model = '$MODEL'
payload = {
  'model': model,
  'messages': [{'role': 'user', 'content': os.environ['PROMPT']}],
  'max_tokens': 1500,
  'temperature': 0.3,
}
r = subprocess.run(['curl','-s','--max-time','90',
  'https://integrate.api.nvidia.com/v1/chat/completions',
  '-H', f'Authorization: Bearer {os.environ[\"NVIDIA_API_KEY\"]}',
  '-H', 'Content-Type: application/json',
  '-d', json.dumps(payload)], capture_output=True, text=True, timeout=95)
try:
    d = json.loads(r.stdout)
    out = d['choices'][0]['message']['content']
except Exception as exc:
    out = f'ERROR: {exc}; raw={r.stdout[:400]}'
print(out)
" > "/tmp/nim_fanout/$SLUG.md" 2>&1
  echo "  -> /tmp/nim_fanout/$SLUG.md ($(wc -c < /tmp/nim_fanout/$SLUG.md) bytes)"
  sleep 0.5  # polite spacing
done

# 4. Aggregate
for f in /tmp/nim_fanout/*.md; do
  echo "=== $(basename "$f" .md) ==="
  head -20 "$f"
  echo
done
```

## Curated panels (for common use cases)

```bash
# Wide diversity (use as default for triangulation)
PANEL_WIDE=(
  "deepseek-ai/deepseek-v4-pro"
  "minimaxai/minimax-m2.7"
  "moonshotai/kimi-k2.6"
  "openai/gpt-oss-120b"
  "z-ai/glm-5.1"
)

# Reasoning-heavy
PANEL_REASON=(
  "nvidia/llama-3.1-nemotron-ultra-253b-v1"
  "nvidia/nemotron-3-super-120b-a12b"
  "qwen/qwen3.5-397b-a17b"
  "mistralai/mistral-large-3-675b-instruct-2512"
)

# Coding-heavy
PANEL_CODE=(
  "qwen/qwen3-coder-480b-a35b-instruct"
  "mistralai/codestral-22b-instruct-v0.1"
  "deepseek-ai/deepseek-coder-6.7b-instruct"
  "openai/gpt-oss-120b"
)
```

## Pitfalls

- **NVIDIA NIM keys hang silently** on some models if you exceed per-key rate. If a model takes >60s with no chunks, kill it and try a sibling.
- **`temperature` defaults differ by model**; pin to `0.3` for analysis/triangulation, `0.7+` for brainstorm.
- **`max_tokens`**: NIM caps differ. 1500 is safe; 4096 works for most reasoning models.
- **Streaming**: omit `stream: true` for fan-out — non-stream is easier to capture per-model.
- **Output volume**: each reply ~1.5-4 KB. Fan-out of 5 models = ~15 KB total — fine for a session, but pipe to files instead of stdout if you're going wider than 10 models.
- **Cross-model disagreement** is the whole point. Look at the *distribution* of answers, not the average. The 2026-05-25 commodity-edge triangulation (3 engines all flagged DATA_QUALITY_LEAKAGE at ~90% confidence) is the gold-standard pattern.

## When NOT to use

- A question that needs file/web access — NIM models are text-in/text-out only. Feed them the JSON/file content verbatim.
- A question one model would answer just as well — use `consult-nvidia-deepseek` to save tokens.
- Operational-safety questions (e.g. "should I run this SQL on prod?") — escalate to a human, not a multi-model vote.

## Related

- `consult-nvidia-deepseek` — single-model NIM consult (this skill's sibling)
- `consult-cloudflare-models` — same shape but Cloudflare Workers AI provider
- `swarm-run` — local swarm dispatcher that already supports NIM/Cloudflare as engines
- `swarm-second-opinion` — 3-engine quick consensus across mixed providers
- `tools/swarm/api_consult.py` — backend the existing `consult-*` skills call
