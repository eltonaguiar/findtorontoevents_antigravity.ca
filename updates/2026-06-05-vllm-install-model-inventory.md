# vLLM Install and Model Inventory (2026-06-05)

This note captures the filesystem audit findings (including the Claude dump) and a fresh local verification run.

## Executive Summary

- vLLM is installed in this repo virtual environment, not globally.
- Active vLLM binary: `.venv/bin/vllm` (version `0.21.0`).
- vLLM Python package location: `.venv/lib/python3.13/site-packages`.
- Hugging Face model cache contains multiple Qwen checkpoints, including `Qwen3-Coder-30B-A3B-Instruct` (~57G).
- LiteLLM proxy is running on port `4000`.
- A vLLM server process is currently running on port `8000` with Qwen3-Coder-30B-A3B-Instruct and tuned flags.

## Verified Install Location

- Binary: `/home/eaguiar2015/findtorontoevents_antigravity.ca/.venv/bin/vllm`
- Version: `0.21.0`
- Package metadata:
  - Name: `vllm`
  - Version: `0.21.0`
  - Location: `/home/eaguiar2015/findtorontoevents_antigravity.ca/.venv/lib/python3.13/site-packages`

## Runtime Processes (verification snapshot)

- LiteLLM:
  - `/home/eaguiar2015/findtorontoevents_antigravity.ca/.venv/bin/python .venv/bin/litellm --config litellm_config.yaml --port 4000 --num_workers 1`
- vLLM:
  - `/home/eaguiar2015/findtorontoevents_antigravity.ca/.venv/bin/python3 ./.venv/bin/vllm serve /home/eaguiar2015/.cache/huggingface/hub/models--Qwen--Qwen3-Coder-30B-A3B-Instruct/snapshots/b2cff646eb4bb1d68355c01b18ae02e7cf42d120 --host 127.0.0.1 --port 8000 --max-model-len 4096 --gpu-memory-utilization 0.84`

## Hugging Face Model Cache Inventory

Path root: `/home/eaguiar2015/.cache/huggingface/hub/`

- `models--google--gemma-4-12b-it` -> `32K` (stub)
- `models--nvidia--Nemotron-Mini-4B-Instruct` -> `36K` (stub)
- `models--TinyLlama--TinyLlama-1.1B-Chat-v1.0` -> `36K` (stub)
- `models--Qwen--Qwen3-0.6B` -> `1.5G`
- `models--Qwen--Qwen2.5-1.5B-Instruct` -> `2.9G`
- `models--mistralai--Mistral-7B-Instruct-v0.3` -> `4.2G`
- `models--Qwen--Qwen2.5-3B-Instruct` -> `5.8G`
- `models--Qwen--Qwen3-4B` -> `7.6G`
- `models--Qwen--Qwen2.5-7B-Instruct` -> `15G`
- `models--Qwen--Qwen3-8B` -> `16G`
- `models--Qwen--Qwen2.5-14B-Instruct` -> `28G`
- `models--Qwen--Qwen3-Coder-30B-A3B-Instruct` -> `57G`

Approximate total local model footprint in this HF cache subset: about `138G`.

## Notes From Prior Claude Audit (kept for continuity)

- It correctly identified:
  - vLLM in repo venv (`.venv/bin/vllm`)
  - version `0.21.0`
  - HF cache model layout and sizes
- It previously concluded no active vLLM process.
- Current verification now shows an active vLLM process on `:8000`.

## Operational Conclusion

For this workspace, vLLM is local-first and repo-scoped:

- Install/runtime anchor: `findtorontoevents_antigravity.ca/.venv`
- Model weights anchor: `/home/eaguiar2015/.cache/huggingface/hub/`
- Proxy/routing anchor: `litellm_config.yaml` + LiteLLM process on `:4000`

If desired, next step is to run a stable readiness and quality benchmark matrix (`local-vllm` vs `local-ollama`) and append measured results to this file.

## Local Ollama Model Inventory (2026-06-05 refresh)

Command used: `ollama list`

### Current models

- `minimax-m3:cloud` | `d03a959f45c0` | `-` | `7 minutes ago`
- `deepseek-r1:32b` | `edba8017331d` | `19 GB` | `9 minutes ago`
- `qwen3:30b-a3b` | `ad815644918f` | `18 GB` | `10 minutes ago`
- `artiku348/loker.v2.1-cld-cdr-480b:latest` | `56c4f69bf367` | `-` | `2 weeks ago`
- `qwen2.5-coder:7b-instruct-q5_K_M` | `771d6745a8b6` | `5.4 GB` | `2 weeks ago`
- `qwen2.5-coder:7b` | `dae161e27b0e` | `4.7 GB` | `2 weeks ago`
- `qwen2.5:7b-instruct-fp16` | `59805ce4a404` | `15 GB` | `2 weeks ago`
- `qwen2.5:7b-instruct-q8_0` | `2d9500c94841` | `8.1 GB` | `2 weeks ago`
- `qwen2.5:7b-instruct-q6_K` | `a7e494737d58` | `6.3 GB` | `2 weeks ago`
- `qwen2.5:7b-instruct-q5_K_M` | `a1040ddd2b49` | `5.4 GB` | `2 weeks ago`
- `qwen2.5:7b` | `845dbda0ea48` | `4.7 GB` | `2 weeks ago`
- `llama3.2:3b` | `a80c4f17acd5` | `2.0 GB` | `2 weeks ago`
- `phi4-mini:latest` | `78fad5d182a7` | `2.5 GB` | `2 weeks ago`
- `llama3.2:1b` | `baf6a787fdff` | `1.3 GB` | `2 weeks ago`
- `gemma2:9b` | `ff02c3702f32` | `5.4 GB` | `2 weeks ago`
- `qwen2.5-coder:3b` | `f72c60cabf62` | `1.9 GB` | `2 weeks ago`
- `qwen2.5:3b` | `357c53fb659c` | `1.9 GB` | `2 weeks ago`
- `gemma3:12b` | `f4031aab637d` | `8.1 GB` | `2 weeks ago`
- `llama3.1:8b` | `46e0c10c039e` | `4.9 GB` | `2 weeks ago`
- `qwen2.5-coder:14b` | `9ec8897f747e` | `9.0 GB` | `2 weeks ago`
- `qwen2.5:14b` | `7cdf5a0187d5` | `9.0 GB` | `2 weeks ago`
- `nomic-embed-text:latest` | `0a109f422b47` | `274 MB` | `2 weeks ago`
- `qwen2.5:32b` | `9f13ba1299af` | `19 GB` | `2 weeks ago`
- `llama3.3:70b` | `a6eb4748fd29` | `42 GB` | `2 weeks ago`

### Notes

- Entries with size `-` are not local full-weight footprints in the same way as standard local GGUF-backed models.
- `minimax-m3:cloud` is present in Ollama inventory, but the `:cloud` tag indicates non-standard local-only behavior.
