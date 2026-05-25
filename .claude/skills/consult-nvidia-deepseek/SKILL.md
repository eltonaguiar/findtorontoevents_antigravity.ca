---
name: consult-nvidia-deepseek
description: Consult NVIDIA Integrate API with DeepSeek v4 Pro by default (or override model, e.g. minimaxai/minimax-m2.7). Use when the user says "/CONSULT-NVIDIA-DEEPSEEK", "/consult-nvidia-deepseek", or asks for an NVIDIA-hosted second opinion.
---
# consult-nvidia-deepseek
Query NVIDIA Integrate API non-interactively for a second opinion.

## When to use
- User asks for `/CONSULT-NVIDIA-DEEPSEEK` or `/consult-nvidia-deepseek`
- User wants NVIDIA-hosted model output (DeepSeek v4 Pro default)
- User wants to override to another NVIDIA Integrate model such as `minimaxai/minimax-m2.7`

## Prerequisites
- Set an NVIDIA API key in env (do not hardcode keys in prompts/files):
  - `NVIDIA_API_KEY` (preferred)
  - or `NGC_API_KEY`

Example:
```bash
export NVIDIA_API_KEY='nvapi-...'
```

## One-liner via existing swarm consult tool
Default model (`deepseek-ai/deepseek-v4-pro`):
```bash
echo "Give me a second-opinion summary in 5 bullets." | python tools/swarm/api_consult.py --provider nvidia_deepseek -
```

Override model (example `minimaxai/minimax-m2.7`):
```bash
echo "Compare 9.11 vs 9.8." | python tools/swarm/api_consult.py --provider nvidia_deepseek --model minimaxai/minimax-m2.7 -
```

## Direct Python OpenAI SDK pattern
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="YOUR_NVAPI_KEY",
)

completion = client.chat.completions.create(
    model="deepseek-ai/deepseek-v4-pro",  # or minimaxai/minimax-m2.7
    messages=[{"role": "user", "content": "Your prompt here"}],
    temperature=1,
    top_p=0.95,
    max_tokens=8192,
    extra_body={"chat_template_kwargs": {"thinking": False}},
    stream=False,
)

print(completion.choices[0].message.content)
```

Streaming variant (model override example):
```python
completion = client.chat.completions.create(
    model="minimaxai/minimax-m2.7",
    messages=[{"role": "user", "content": "Your prompt here"}],
    temperature=1,
    top_p=0.95,
    max_tokens=8192,
    stream=True,
)

for chunk in completion:
    if not getattr(chunk, "choices", None):
        continue
    delta = chunk.choices[0].delta
    if getattr(delta, "content", None) is not None:
        print(delta.content, end="")
```

## Notes
- Base URL is OpenAI-compatible: `https://integrate.api.nvidia.com/v1`
- Keep keys in environment variables only.
- This skill is model-flexible: DeepSeek is default, but any supported NVIDIA Integrate model can be passed with `--model`.
