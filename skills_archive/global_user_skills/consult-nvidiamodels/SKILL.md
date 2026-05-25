---
name: consult-nvidiamodels
description: Query multiple AI models via NVIDIA NIM API for second opinions on trading data, code, or analysis. Use when the user says "/consult-nvidiamodels", "ask nvidia models", "nim second opinion", or wants peer model consensus on quantitative/analytical questions.
---

# consult-nvidiamodels

Query multiple NVIDIA NIM-hosted models for consensus analysis, non-interactively.

## When to use

User asks "ask nvidia models" / "/consult-nvidiamodels" / "get peer model opinions" / multi-model second opinion from NVIDIA NIM.

## Prerequisites

- API key stored in environment: `NVIDIA_NIM_API_KEY` (or hardcoded — see Known Issues)
- Default key: `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`
- Base URL: `https://integrate.api.nvidia.com/v1`

## The one command that works

```bash
python3 -c "
import json, subprocess, time

API_KEY = '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'
BASE_URL = 'https://integrate.api.nvidia.com/v1'
PROMPT = '''YOUR_ANALYSIS_PROMPT_HERE'''

models = [
    'moonshotai/kimi-k2.6',          # Kimi K2.6 — strongest open-source reasoning
    'openai/gpt-oss-120b',           # GPT-OSS-120B — strong general-purpose
    'z-ai/glm-5.1',                   # GLM-5.1 — excellent multilingual/instruction following
    'nvidia/llama-3.3-nemotron-super-49b-v1.5',  # Nemotron Super — great throughput/accuracy
    'mistralai/mistral-nemotron',     # Mistral Nemotron — fast + good quality
]

for model in models:
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': PROMPT}],
        'max_tokens': 1500,
        'temperature': 0.3,
    }
    try:
        resp = subprocess.run([
            'curl', '-s', '--max-time', '90',
            f'{BASE_URL}/chat/completions',
            '-H', f'Authorization: Bearer {API_KEY}',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps(payload)
        ], capture_output=True, text=True, timeout=95)
        data = json.loads(resp.stdout)
        content = data['choices'][0]['message']['content']
        print(f'=== {model} ===')
        print(content[:2000])
    except Exception as e:
        print(f'=== {model} === ERROR: {e}')
    time.sleep(0.5)
"
```

## Recommended Model Tier List

### S-Tier (Best reasoning/analysis):
| Model ID | Provider | Strengths |
|----------|----------|-----------|
| `moonshotai/kimi-k2.6` | Moonshot AI | Strongest open-source, long context, quantitative analysis |
| `minimaxai/minimax-m2.7` | MiniMax | Excellent reasoning, coding, agentic tasks (may need pro account) |
| `openai/gpt-oss-120b` | OpenAI/NVIDIA | Strong general-purpose, good structured output |

### A-Tier (Excellent, very close to S-Tier):
| Model ID | Provider | Strengths |
|----------|----------|-----------|
| `nvidia/llama-3.3-nemotron-super-49b-v1.5` | NVIDIA | Great throughput + accuracy balance |
| `qwen/qwen3.5-397b-a17b` | Qwen/Alibaba | Top-tier multilingual, strong reasoning |
| `z-ai/glm-5.1` | Zhipu AI | Excellent multilingual, instruction following |

### B-Tier (Strong daily drivers):
| Model ID | Provider | Strengths |
|----------|----------|-----------|
| `mistralai/mistral-nemotron` | Mistral/NVIDIA | Fast + good quality |
| `mistralai/mistral-large-3-675b-instruct-2512` | Mistral | Large context, solid reasoning |
| `nvidia/nemotron-3-nano-30b-a3b` | NVIDIA | Efficient, good for quick checks |

## Verify alive

```bash
python3 -c "
import json, subprocess
resp = subprocess.run([
    'curl', '-s', '--max-time', '15',
    'https://integrate.api.nvidia.com/v1/chat/completions',
    '-H', 'Authorization: Bearer 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',
    '-H', 'Content-Type: application/json',
    '-d', '{\"model\":\"nvidia/nemotron-nano-12b-v2-vl\",\"messages\":[{\"role\":\"user\",\"content\":\"reply with exactly: NIM_PONG\"}],\"max_tokens\":20}'
], capture_output=True, text=True, timeout=20)
if resp.returncode == 0:
    d = json.loads(resp.stdout)
    print(d.get('choices',[{}])[0].get('message',{}).get('content','FAIL'))
else:
    print('HTTP ERROR')
"
```

## List available models

```bash
curl -s --max-time 30 "https://integrate.api.nvidia.com/v1/models" \
  -H "Authorization: Bearer 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" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(m['id']) for m in d.get('data',[])]"
```

## Known issues

- **minimaxai/minimax-m2.7** — May return empty responses on free-tier accounts. Fall back to Kimi K2.6 or GPT-OSS-120B.
- **nvidia/llama-3.1-nemotron-ultra-253b-v1** — Returns 404 for some accounts. Use `nvidia/llama-3.3-nemotron-super-49b-v1.5` instead.
- **API key exposure** — The key is hardcoded in this skill. For production, use environment variable `NVIDIA_NIM_API_KEY`.
- **Rate limits** — Add `time.sleep(0.5)` between calls to avoid 429 errors.
- **Timeout** — Large models (253B+) may need 90s+ timeout. Set `--max-time` accordingly.
- **Response truncation** — Some models may return very long responses. The `max_tokens: 1500` parameter controls output length.

## Result compilation pattern

After querying multiple models, compile findings by:
1. Identifying unanimous agreements (highest confidence)
2. Noting model-specific unique insights
3. Presenting allocation/action recommendations with model consensus level
4. Saving full results to JSON for audit trail

## Related skills

- `consult-gemini` — Single-model second opinion from Google Gemini
- `consult-codex` — Single-model second opinion from OpenAI Codex
- `consult-cursor-agent` — Single-model second opinion from Cursor Agent
- `consult-opencode` — Single-model second opinion from opencode
- `consult-cloudflaremodels` — Multi-model consensus via Cloudflare Workers AI
