---
name: consult-cloudflaremodels
description: Query multiple AI models via Cloudflare Workers AI API for second opinions on trading data, code, or analysis. Use when the user says "/consult-cloudflaremodels", "ask cloudflare models", or wants peer model consensus via Cloudflare's AI gateway.
---

# consult-cloudflaremodels

Query multiple Cloudflare Workers AI models for consensus analysis, non-interactively.

## When to use

User asks "ask cloudflare models" / "/consult-cloudflaremodels" / multi-model second opinion from Cloudflare Workers AI.

## Prerequisites

- Cloudflare Account ID and API Token (stored in environment or provided by user)
- API endpoint: `https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/{MODEL}`
- Key models available: `@cf/meta/llama-4-scout-17b-16e-instruct`, `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b`, `@cf/qwen/qwen3-235b-a22b`, `@cf/meta/llama-3.1-405b-instruct`

## The one command that works

```bash
python3 -c "
import json, subprocess, time

ACCOUNT_ID = 'YOUR_CLOUDFLARE_ACCOUNT_ID'
API_TOKEN = 'YOUR_CLOUDFLARE_API_TOKEN'
BASE_URL = f'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run'
PROMPT = 'YOUR_ANALYSIS_PROMPT_HERE'

models = [
    '@cf/meta/llama-4-scout-17b-16e-instruct',
    '@cf/deepseek-ai/deepseek-r1-distill-qwen-32b',
    '@cf/qwen/qwen3-235b-a22b',
    '@cf/meta/llama-3.1-405b-instruct',
]

for model in models:
    payload = {
        'messages': [{'role': 'user', 'content': PROMPT}],
        'max_tokens': 1500,
        'temperature': 0.3,
    }
    try:
        resp = subprocess.run([
            'curl', '-s', '--max-time', '90',
            f'{BASE_URL}/{model}',
            '-H', f'Authorization: Bearer {API_TOKEN}',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps(payload)
        ], capture_output=True, text=True, timeout=95)
        data = json.loads(resp.stdout)
        if data.get('success'):
            content = data['result']['response']
            print(f'=== {model} ===')
            print(content[:2000])
        else:
            print(f'=== {model} === ERROR: {data.get(\"errors\",[{}])[0].get(\"message\",\"unknown\")}')
    except Exception as e:
        print(f'=== {model} === EXCEPTION: {e}')
    time.sleep(0.5)
"
```

## Recommended Models (Cloudflare Workers AI)

| Model | Provider | Notes |
|-------|----------|-------|
| `@cf/meta/llama-4-scout-17b-16e-instruct` | Meta | Top performer in our tournament (WR=61.4%, Sharpe=0.326) |
| `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b` | DeepSeek/Qwen | Strong reasoning, good for coding/math |
| `@cf/qwen/qwen3-235b-a22b` | Alibaba | Multilingual, good instruction following |
| `@cf/meta/llama-3.3-70b-instruct` | Meta | Reliable daily driver |
| `@cf/meta/llama-3.2-3b-instruct` | Meta | Fast/cheap for quick checks |

## Known issues

- **Account setup required** — Cloudflare Workers AI requires account setup and API token generation at dash.cloudflare.com
- **Rate limits** — Free tier has daily request limits; add sleep between calls
- **Model availability** — Not all models are available in all regions; check Cloudflare docs for current catalog
- **Response format** — Cloudflare wraps responses differently than OpenAI API; parse `result.response` field

## Related skills

- `consult-nvidiamodels` — Multi-model consensus via NVIDIA NIM API (primary recommended skill)
- `consult-gemini` — Single-model second opinion from Google Gemini
