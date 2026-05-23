---
name: consult-ring
description: Consult Ring 2.6 1T (inclusionai/ring-2.6-1t) on OpenRouter for deep reasoning on quant, strategy, hypothesis, or code questions. Use when the user says "/consult-ring261T", "/ask-ring261T", "ask ring", "ring second opinion", or wants the 1T-parameter extended-thinking model's take on a question.
---
# /consult-ring261T — Ring 2.6 1T Consultation

Consult **Ring 2.6 1T** (`inclusionai/ring-2.6-1t`) — a 1-trillion-parameter reasoning model with 262K context, available via OpenRouter. Specialises in chain-of-thought analysis, hypothesis evaluation, and quantitative strategy critique.

Aliases: `/consult-ring261T`, `/ask-ring261T`, "ask ring", "ring second opinion"

## Prerequisites

- `OPENROUTER_API_KEY` set in Windows environment (key: `sk-or-v1-c05470f494...`).
- Model: `inclusionai/ring-2.6-1t` (hard-coded; do NOT override with OPENROUTER_MODEL env var — other openrouter calls use different models).
- Endpoint: `https://openrouter.ai/api/v1/chat/completions`

## Usage

```
/consult-ring261T <question or prompt text>
/ask-ring261T <question or prompt text>
```

## How to invoke

### Recommended: python inline (no prompt-file needed)

Write the prompt to a temp file, then call `api_consult.py` with `OPENROUTER_MODEL` forced to `inclusionai/ring-2.6-1t`:

```powershell
# Write prompt to temp file
$prompt = "Your question here"
$prompt | Out-File -FilePath "$env:TEMP\ring_prompt.txt" -Encoding utf8

# Call via api_consult.py with model override
$env:OPENROUTER_MODEL = "inclusionai/ring-2.6-1t"
$env:OPENROUTER_MAX_TOKENS = "2000"
python tools/swarm/api_consult.py --provider openrouter --prompt-file "$env:TEMP\ring_prompt.txt"
```

### Bash version (via Bash tool)

```bash
PROMPT="Your question here"
echo "$PROMPT" > /tmp/ring_prompt.txt
OPENROUTER_MODEL="inclusionai/ring-2.6-1t" OPENROUTER_MAX_TOKENS=2000 \
  python tools/swarm/api_consult.py --provider openrouter --prompt-file /tmp/ring_prompt.txt
```

### Direct Python (when api_consult.py is unavailable or for one-liners)

```python
import os, json, urllib.request
key = os.environ["OPENROUTER_API_KEY"]
data = json.dumps({
    "model": "inclusionai/ring-2.6-1t",
    "messages": [{"role": "user", "content": PROMPT}],
    "max_tokens": 2000,
    "temperature": 0.3
}).encode()
req = urllib.request.Request(
    "https://openrouter.ai/api/v1/chat/completions",
    data=data,
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=120) as r:
    resp = json.loads(r.read())
print(resp["choices"][0]["message"]["content"])
```

## Required parameters

| Parameter | Value |
|-----------|-------|
| `model` | `inclusionai/ring-2.6-1t` (ALWAYS — never use default openrouter model) |
| `max_tokens` | **2000 minimum** — Ring returns `content=null` + dumps answer in `reasoning_details` when tokens are too low. Use 2000 for short questions, 4000 for deep analysis. |
| `temperature` | 0.3 (good for analysis); use 0.7 for creative/brainstorm |
| `timeout` | 120s — Ring's 1T parameter count means 30-90s response time is normal |

## Critical gotchas

- **`content=null` bug**: If `max_tokens < 1500`, Ring puts the real answer in `choices[0].message.reasoning_details` and leaves `content=null`. Always use `max_tokens >= 2000`.
- **OPENROUTER_MODEL env var conflict**: Other OpenRouter calls in this repo use different models. Set `OPENROUTER_MODEL=inclusionai/ring-2.6-1t` only for Ring calls, then unset or reset afterwards.
- **Reasoning trace**: Ring's `reasoning_details` field contains chain-of-thought reasoning (often very long). The final answer is always in `choices[0].message.content` when `max_tokens >= 2000`.
- **Response time**: 30-90 seconds is normal for this model. Do not retry on timeout until 120s has elapsed.

## When to use Ring vs other models

| Use Ring when... | Use something else when... |
|------------------|---------------------------|
| Deep hypothesis evaluation (H-0xx series) | Quick yes/no gate check (use swarm deepseek) |
| Strategy autopsy with long context | Fast iteration / many small questions (use ofox/groq) |
| Multi-factor quant synthesis (COMMODITY/FOREX/CRYPTO) | Code generation tasks (use kilo/cursor/codex) |
| Frontier-level critique of gate logic | Routine summarisation (use any cheap model) |
| 262K context is needed (large log files, full reports) | Cost matters — Ring tokens are expensive |

## What Ring is good at (observed in this repo)

- Evaluating hypothesis registry entries (H-001 through H-037+)
- Ranking free-data vs paid-data hypotheses
- Critiquing gate logic (MDD, DSR, PBO, WR floors)
- Recommending asset class priority given PF/WR/n data
- Synthesising multi-session audit outputs into actionable decisions

## Verify alive

```bash
OPENROUTER_MODEL="inclusionai/ring-2.6-1t" OPENROUTER_MAX_TOKENS=2000 \
  python tools/swarm/api_consult.py --provider openrouter \
  --prompt-file <(echo "Reply with exactly the word: VERIFIED")
```

Expect a response containing `VERIFIED`.

## Related

- Sibling skills: `consult-grok`, `consult-ofox`, `consult-gemini`, `consult-kilo`
- Session notes: Ring reviewed H-017 (liquidation cascade) and H-037 (VIX carry) on 2026-05-19
- Ring's H-037 recommendation: VIX term-structure carry is the top free-data hypothesis — pre-registered as H-037 in `reports/hypothesis_registry.json`
- Ring's COMMODITY verdict: enforce MDD gate (40% cap) — user decision still pending
