# GPU/CPU push benchmark — RTX 5070 12GB

**Date:** 2026-05-19  
**Tool:** `python tools/ollama_gpu_push_benchmark.py`  
**Report:** `swarm_runs/gpu-push-benchmark/20260519T064741Z/REPORT.md`

## Hardware ceiling (measured)

| Tier | Examples | tok/s | VRAM | Notes |
|------|----------|-------|------|-------|
| **Tiny** 1–2B | `smollm2:1.7b`, `llama3.2:1b` | **165–266** | 100% GPU | Fast idea screen only |
| **Small** 3–4B | `llama3.2:3b`, `gemma3:4b` | **90–225** | GPU | Good harvest latency |
| **Medium** 7–9B | `qwen2.5-coder:7b`, `mistral-nemo` | **80–118** | GPU | Best quality/speed balance |
| **Large** 14B Q4 | `qwen2.5-coder:14b-instruct-q4_K_M` | **~62** | GPU auto | Best local harvest quality |
| **Large** reasoning | `deepseek-r1:14b`, `qwen3:14b` | varies | 10%/90% hybrid seen | Need `num_predict≥1200`; strip `` blocks |

## Techniques that work on this PC

1. **`num_gpu: -1`** in API options — Ollama auto-fits layers to 12GB (preferred).
2. **`num_ctx: 4096`** default; drop to **2048** to fit more layers on 14B+.
3. **`num_gpu: 0`** — CPU-only fallback (slow but runs when VRAM full).
4. **Q4_K_M quant** — 14B fits entirely on GPU; 32B needs CPU+GPU hybrid on 32GB RAM.
5. **Ollama cloud** for 70B+ (`gpt-oss:120b-cloud`, `deepseek-v3.1:671b-cloud`) — zero local VRAM.
6. **No LM Studio** — `ollama_import_gguf.py` + blob-path Modelfiles.

## Giants (in progress)

`--phase giants --pull-giants` attempts:

- `deepseek-r1:32b`
- `qwen2.5-coder:32b-instruct`
- `mixtral:8x7b-instruct-v0.1-q4_K_M`
- `llama3.3:70b-instruct-q3_K_M` (likely RAM-bound)

**C: ~528 GB free** — disk is not the limit; VRAM (12GB) and RAM (32GB) are.

## Commands

```powershell
python tools/ollama_gpu_push_benchmark.py --phase known
python tools/ollama_gpu_push_benchmark.py --phase offload
python tools/ollama_gpu_push_benchmark.py --phase giants --pull-giants
python tools/idea_harvest_mega.py --tier local --no-pull
```

## Harvest recommendation

| Use case | Model |
|----------|-------|
| Fast bulk screen | `smollm2:1.7b` or `llama3.2:1b` |
| Balanced local consult | `qwen2.5-coder:7b` |
| Deep structured harvest | `qwen2.5-coder:14b-instruct-q4_K_M` |
| Verdict-grade | Grok API / `deepseek-chat` (not local 14B reasoning without tuning) |
