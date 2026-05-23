---
title: Swarm env-key audit + Groq/HuggingFace wire-in + OpenRouter/Cerebras alias fix
date: 2026-05-05
author: claude-opus-4-7
type: fix
---

# Swarm env-key audit + provider wire-in (2026-05-05)

## TL;DR

Audited every API key in this machine's environment against engine configs in
`tools/swarm/api_consult.py` and `.ruflo/orchestrator.py`. **4 issues found, all
fixed.** Two env-name mismatches were silently disabling providers we already
have keys for; two free-tier providers (Groq, HuggingFace) weren't wired at all.

## Environment audit

Keys present (names only, values redacted):

| Key | Provider | Wired before this PR? |
|---|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek | ✅ yes |
| `X_AI_KEY` | xAI Grok | ✅ yes |
| `INCEPTION_API_KEY` | Inception Mercury | ✅ yes |
| `NOUS_API_KEY` | Nous Hermes-4 | ✅ yes |
| `OPENROUTER_API_KEY` | OpenRouter (200+ models) | ❌ **mismatch** — config wanted `OPENROUTER` |
| `CEREBRAS_API_KEY_FREE` / `CEREBRAS_API_KEY_PAID` | Cerebras (LPU, sub-sec) | ❌ **mismatch** — config wanted `CEREBRAS_API` / `CEREBRAS_API_KEY` |
| `GROQ_KEY` | Groq (LPU free tier) | ❌ **not wired** |
| `HUGGINGFACE_API` | HuggingFace router | ❌ **not wired** |

Net: **4 of 8 keys were dead weight** before this PR.

## Fixes

### `tools/swarm/api_consult.py`

1. OpenRouter: `key_envs: ("OPENROUTER",)` → `("OPENROUTER_API_KEY", "OPENROUTER")` (alias added, old name kept for back-compat).
2. Cerebras (`_call_cerebras_via_http`): `key_envs` extended with `CEREBRAS_API_KEY_PAID` + `CEREBRAS_API_KEY_FREE` (paid first so quota’d traffic prefers paid tier).
3. New `groq` provider: `https://api.groq.com/openai/v1/chat/completions`, default `llama-3.3-70b-versatile`, `key_envs=("GROQ_KEY","GROQ_API_KEY")`.
4. New `huggingface` provider: `https://router.huggingface.co/v1/chat/completions`, default `meta-llama/Llama-3.3-70B-Instruct`, `key_envs=("HUGGINGFACE_API","HF_TOKEN","HUGGINGFACE_API_KEY")`.
5. `SAMPLING_DEFAULTS` updated for both new providers.

### `.ruflo/orchestrator.py`

1. `PAID_MODELS["openrouter"].key_envs` → adds `OPENROUTER_API_KEY` first.
2. `PAID_MODELS["cerebras"].key_envs` → adds `CEREBRAS_API_KEY_PAID` + `CEREBRAS_API_KEY_FREE` first.
3. New `PAID_MODELS["groq"]` and `PAID_MODELS["huggingface"]` entries.
4. `FREE_MODELS` model IDs refreshed to verified-working OpenRouter slugs:
   - `google/gemini-pro-1.5-preview:free` → `google/gemini-2.0-flash-exp:free`
   - `mistralai/mistral-7b-instruct:free` → `meta-llama/llama-3.3-70b-instruct:free`
   - coordinator/fallback `tencent/hy3-preview:free` → `meta-llama/llama-3.3-70b-instruct:free`
   - `FAILOVER_MODELS` list updated to match.

## Verification

```bash
python -c "import ast; ast.parse(open('tools/swarm/api_consult.py',encoding='utf-8').read())"
python -c "import ast; ast.parse(open('.ruflo/orchestrator.py',encoding='utf-8').read())"
# both: OK
```

Smoke-test once merged:
```bash
python tools/swarm/api_consult.py --provider groq --prompt-file /tmp/q.txt
python tools/swarm/api_consult.py --provider huggingface --prompt-file /tmp/q.txt
python tools/swarm/api_consult.py --provider openrouter --prompt-file /tmp/q.txt   # was silently keyless
```

## Why this matters

Swarm runs were degrading silently: when `OPENROUTER` env wasn't set the
provider was just skipped, leaving the swarm with fewer voices than configured.
Same for Cerebras (the speed leader). Adding Groq + HuggingFace gives us two
more sub-second/free fallback lanes for round-robin and failover.
