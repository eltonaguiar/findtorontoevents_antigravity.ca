---
name: api-model-roster
description: >-
  Probe and refresh API keys + model lists for cloud LLM providers (OpenRouter Ring,
  Cerebras, Groq, DeepSeek, Inception, Kimi, HF, etc.). Saves config/api_model_roster.json.
  Use when starting a model grill, after key rotation, or when /api-model-roster, "check API keys",
  "which models are callable", "refresh OpenRouter free models". Enforces ONE model at a time
  for local Ollama via model_grill_sequential.py.
---

# API Model Roster

## Rules

1. **Cloud:** parallel across **different API keys/providers**; **never** parallel two jobs on the same provider (rate limits).
2. **Local Ollama:** **one model at a time**; `ollama stop` between runs; hard timeouts (75s tiny → 420s 32B).
3. **No indefinite waits** — on timeout, log FAIL and continue.
4. **Refresh OpenRouter** before Ring tests — free model IDs rotate.

## Key env vars (check in order)

| Provider | Env vars |
|----------|----------|
| Cerebras free/paid | `CEREBRAS_FREE_API_KEY`, `CEREBRAS_PAID_API_KEY`, `CEREBRAS_API_KEY` |
| Groq | `GROQ_API_KEY` |
| OpenRouter | `OPENROUTER`, `OPENROUTER_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| Inception | `INCEPTION_AI_KEY` |
| xAI | `XAI_API_KEY` |
| Kimi | `KIMI_API_KEY`, `KIMI_MOONSHOT_APIKEY` |
| HF | `HUGGING_FACE_TOKEN` |
| Chutes | `CHUTES_API_KEY_FREE` |
| OFOX | `OFOX_API_KEY` |
| LLM7 | `LLM7_API_KEY_FREE` |
| Mistral | `MISTRA_API_KEY_FREE` |
| Ollama cloud | `OLLAMA_CLOUD_KEY` |
| OpenCode / Kilo | `OPENCODE_API_KEY`, `KILOCODE_API_KEY` (CLI) |

Windows: keys set via `setx` are read from registry by `tools/api_model_roster.py` and `tools/swarm_models.py`.

## Commands

```powershell
cd e:\findtorontoevents_antigravity.ca

# Status only (no API calls)
python tools/api_model_roster.py --status

# Probe one provider (lists models + ping test)
python tools/api_model_roster.py --probe openrouter

# Probe all providers sequentially (~15 min)
python tools/api_model_roster.py --probe all

# List Ring variants from last OpenRouter probe
python tools/api_model_roster.py --list-ring

# Sequential grill (cloud paid wave, harvest prompt only)
python tools/model_grill_sequential.py --wave paid --prompt harvest --api-timeout 150

# Ring comparison
python tools/model_grill_sequential.py --wave ring --prompt harvest

# Local smoke (3 models, unload between)
python tools/model_grill_sequential.py --wave local_smoke --prompt harvest
```

## Outputs

| File | Purpose |
|------|---------|
| `config/api_model_roster.json` | Keys present, model lists, ping results, Ring IDs |
| `swarm_runs/model-grill/<timestamp>/` | Per-model responses + manifest.json |
| `BENCHMARK_LOCALAI_DESKTOP.md` | Intelligence log table (appended) |

## OpenRouter Ring

After `--probe openrouter`, check `ring_models` in JSON. Test each sequentially:

```powershell
python tools/model_grill_sequential.py --job openrouter:inclusionai/ring-2.5 --prompt harvest
```

Paid Ring may replace `:free` suffix — do not assume 404 means dead; refresh roster first.

## When a provider fails

| HTTP | Action |
|------|--------|
| 402 | HF/Chutes credits — skip wave, document in roster JSON |
| 404 | Wrong model ID — refresh `/models`, update job string |
| 429 | Wait 30s, retry once, then skip |
| Timeout | Skip; do not block pipeline |
