---
name: ask-ring261T
description: Alias for /consult-ring261T. Consult Ring 2.6 1T (inclusionai/ring-2.6-1t) on OpenRouter. Use when user says "/ask-ring261T" or "ask ring".
---
# /ask-ring261T

This is an alias for `/consult-ring261T`. Both names do the same thing: send a question to **Ring 2.6 1T** (`inclusionai/ring-2.6-1t`) on OpenRouter and return the full reasoning response.

## What to do

Invoke the `consult-ring` skill and follow its steps exactly. In short:

1. Take the user's input as the prompt.
2. Write it to a temp file.
3. Call `api_consult.py --provider openrouter` with `OPENROUTER_MODEL=inclusionai/ring-2.6-1t` and `max_tokens=2000` (minimum).
4. Print Ring's response (`choices[0].message.content`).

Full documentation lives in `.claude/skills/consult-ring/SKILL.md`.
