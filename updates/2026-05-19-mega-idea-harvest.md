# Mega idea harvest — multi-model money-ready consult

**Date:** 2026-05-19  
**Goal:** Harvest actionable per-asset-class ideas from many models (API + local Ollama).

## Orchestrator

```powershell
cd e:\findtorontoevents_antigravity.ca

# API + Grok WSL + OpenRouter free + Groq + llm7/mistral (~15–20 calls)
python tools/idea_harvest_mega.py --tier api --max-parallel 4 --no-pull --skip-import

# All local Ollama tags (sequential, GPU) — ~25+ models, hours
python tools/idea_harvest_mega.py --tier local --no-pull --skip-import

# Everything + optional small ollama pulls when C: has space
python tools/idea_harvest_mega.py --tier all --pull-small
```

**Outputs:** `swarm_runs/idea-harvest/<timestamp>/`
- `api/*.md` — per-model responses
- `local/*.md` — Ollama runs with elapsed_s
- `harvest_ideas.json` — extracted wire_targets + harvest lines
- `HARVEST_AGGREGATE.md` — ranked paths + samples
- `manifest.json` — run log

## Model matrix (API tier)

| Provider | Models |
|----------|--------|
| **Grok WSL** | SuperGrok (`grok -p`) |
| **xAI / Inception / DeepSeek** | paid keys |
| **OpenRouter** | `openrouter/free`, Ring 2.6, Llama 3.3 70B free, Qwen 2.5 72B free, Gemma2, Mistral Small, Nemotron nano, DeepSeek R1 free |
| **Groq** | Llama 3.3 70B, Mixtral, Gemma2 9B |
| **LLM7 / Mistral** | via `tools/swarm_models.py` |
| **Pollinations** | keyless fallback |

**HuggingFace router:** skipped when account returns HTTP 402 (credits depleted).

## Local Ollama

- Import library GGUFs: `python tools/ollama_import_gguf.py --import-all`
- Includes new tags: `library-gemma3-4b:latest`, `library-*` duplicates, all `qwen*`/`phi*`/`deepseek*` in `ollama list` (non-cloud).

## Disk

- **C:** ~559 GB free — safe for `ollama pull` small models (`gemma3:4b`, `llama3.2:1b`, etc.)
- Models stored under `C:\Users\zerou\.ollama\models\`
- F: symlinks are pointers only (no duplicate weight files)

## Ground rules for harvest

Responses must respect: **11/11 hypotheses killed**, `pf_registry` canonical, no live-money from registry PF alone. Filter ideas through `tools/edge_stability_harness.py` before implementation.

## Next after runs complete

1. Read `HARVEST_AGGREGATE.md` in latest `swarm_runs/idea-harvest/` folder.
2. Cross-check with `reports/QUANT_RESCUE_SWARM_VERDICT_2026-05-19_cursor.md`.
3. Promote top 3 wire_targets per class to `reports/hypothesis_registry.json` pre-registration.
