---
name: consult-nvidiamodels
description: Query multiple AI models via NVIDIA NIM API for second opinions on trading data, code, or analysis. Use when the user says "/consult-nvidiamodels", "ask nvidia models", "nim second opinion", or wants peer model consensus on quantitative/analytical questions.
---

# consult-nvidiamodels

Query multiple NVIDIA NIM-hosted models for consensus analysis, non-interactively.

## When to use

User asks "ask nvidia models" / "/consult-nvidiamodels" / "get peer model opinions" / multi-model second opinion from NVIDIA NIM.

## Prerequisites

- API key stored in environment: `NVIDIA_API_KEY` (preferred) or `NVIDIA_NIM_API_KEY`. **Never** hardcode.
- Base URL: `https://integrate.api.nvidia.com/v1`

```bash
export NVIDIA_API_KEY='nvapi-...'   # your own key; rotate per Cloudflare/NVIDIA dashboard
```

## The one command that works

```bash
python3 -c "
import json, subprocess, time, os, sys

API_KEY = os.environ.get('NVIDIA_API_KEY') or os.environ.get('NVIDIA_NIM_API_KEY')
if not API_KEY:
    sys.exit('set NVIDIA_API_KEY (or NVIDIA_NIM_API_KEY) in env first')
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
    '-H', 'Authorization: Bearer $NVIDIA_API_KEY',
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
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(m['id']) for m in d.get('data',[])]"
```

## Known issues

- **minimaxai/minimax-m2.7** — May return empty responses on free-tier accounts. Fall back to Kimi K2.6 or GPT-OSS-120B.
- **nvidia/llama-3.1-nemotron-ultra-253b-v1** — Returns 404 for some accounts. Use `nvidia/llama-3.3-nemotron-super-49b-v1.5` instead.
- **API key exposure** — 2026-05-25: a previously-hardcoded key was removed from this file and replaced with `$NVIDIA_API_KEY` env lookup. The removed key was already in git history before that scrub; **it must be rotated at the NVIDIA dashboard** since a `git log -p` will still surface it. Always read from env going forward.
- **Rate limits** — Add `time.sleep(0.5)` between calls to avoid 429 errors.
- **Timeout** — Large models (253B+) may need 90s+ timeout. Set `--max-time` accordingly.
- **Response truncation** — Some models may return very long responses. The `max_tokens: 1500` parameter controls output length.

## 🔴 MANDATORY: Leakage-Context Block

**Every prompt sent to NVIDIA NIM models MUST include a leakage-context block** listing known data-quality incidents that intersect the asset classes or data sources being analyzed. Multi-model consensus is worthless when all models are shown the same corrupted inputs.

### Template (include at TOP of prompt, before the analysis request):

```
LEAKAGE CONTEXT — Read before analyzing:

The following data-quality incidents affect the dataset you are about to analyze.
Your first task is to determine whether ANY of these incidents invalidate
the numbers presented. If so, flag it explicitly in your response and adjust
your analysis accordingly.

Known incidents:
- H-101 (COMMODITY): COT look-ahead leakage — pre-dedup commodity data shows
  PF=4.31/WR=58.4% but post-policy ground truth is PF=0.31/WR=10.7%.
  The CFTC COT publication lag (T+3) was not respected. Any commodity
  analysis citing PF>1.0 is contaminated unless proven otherwise.
- M-095 (COMMODITY): CT=F cotton over-emission — 230 closed picks from 16
  unique dates = 14.4 picks/date average. One profitable trade counted 230×.
- M-069 (NET): Slippage-adjusted re-judgment — wins reclassified as losses.
- QUALITY_BUCKETS (ALL): The `quality_bucket` field (profitable_tp,
  moderate_confidence, etc.) in performance_report_*.json is POST-HOC
  circular — buckets are defined by exit outcome, not pre-hoc gates.
  `profitable_tp` = "all TP_HIT picks". Do not treat as a classifier.

Be skeptical. If data suggests one symbol/source dominates, flag concentration risk.
If you see PF>3.0 on a single asset class, check for look-ahead or survivorship bias.
```

### When to use:
- ALWAYS when analyzing any asset-class performance numbers from findtorontoevents.ca
- ALWAYS when asked about COMMODITY edge (H-101/M-095 must be stated)
- ALWAYS when referencing `performance_report_*.json` quality_bucket data
- SKIP only when the question is purely theoretical/hypothetical with no dataset reference

### Lesson from 2026-05-25 incident:
5/5 NIM models converged on "COMMODITY is #1 edge" because all were shown the same pre-dedup contaminated data (PF=4.31) without being told about H-101. The 3-engine Codex/Gemini/Grok panel that WAS shown leakage evidence correctly classified it at ~90% confidence. **The difference was the prompt, not the model quality.**

## Result compilation pattern

After querying multiple models, compile findings by:
1. Identifying unanimous agreements (highest confidence)
2. Noting model-specific unique insights
3. Presenting allocation/action recommendations with model consensus level
4. Saving full results to JSON for audit trail
5. **Cross-referencing each model's output against the known leakage incidents** — flag any model that endorses a known-bad signal without addressing the leakage evidence

## Related skills

- `consult-gemini` — Single-model second opinion from Google Gemini
- `consult-codex` — Single-model second opinion from OpenAI Codex
- `consult-cursor-agent` — Single-model second opinion from Cursor Agent
- `consult-opencode` — Single-model second opinion from opencode
- `consult-cloudflaremodels` — Multi-model consensus via Cloudflare Workers AI
