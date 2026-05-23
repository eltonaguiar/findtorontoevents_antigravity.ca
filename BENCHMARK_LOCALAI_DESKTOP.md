# Local AI Desktop Benchmark — findtorontoevents.ca

**Hardware (reference):** i9-14900K (24C/32T) · RTX 5070 12GB GDDR7 · 32GB DDR5 · NVMe + `F:\Models\Ollama_GGUFs\`

**Prompt:** `swarm_runs/_prompts/MONEY_READY_HARVEST_v1.md` (compact) or `MONEY_READY_MASTER_v1.md` (full)

**Output dir:** `swarm_runs/local-gguf-consult/` and `swarm_runs/money-ready-consult/<timestamp>/phase3-local/`

## Model storage paths (for disk cleanup)

| Location | Contents |
|----------|----------|
| `F:\Models\Ollama_GGUFs\` | Library GGUF files (`library-*.gguf`) |
| `E:\Users\zerou\.lmstudio\models\` | LM Studio imported models |
| `C:\Users\zerou\.ollama\models\` | Ollama blobs (default install) |
| Repo `swarm_runs/local-gguf-consult/` | Consult outputs only (small) |

## Execution modes (Ollama only)

| Mode | When to use | Tool |
|------|-------------|------|
| **GPU 100%** | Model fits in 12GB VRAM (7B–14B Q4) | `ollama run` (auto GPU) |
| **Hybrid** | 14B+ if VRAM tight | Ollama offloads to CPU/RAM automatically |
| **CPU** | Embed models / fallback | `nomic-embed-text` only |

**Import GGUF:** `python tools/ollama_import_gguf.py --import-all` (Modelfile + blob path, no LM Studio).

## Sequential grill rule (2026-05-19)

**One model at a time.** Use `python tools/model_grill_sequential.py` (file lock + `ollama stop` between locals).  
Do **not** run parallel Ollama or parallel API grills — contention causes false FAILs.

**Roster refresh:** `python tools/api_model_roster.py --probe all` → `config/api_model_roster.json`

## Benchmark log (local throughput)

| Date (UTC) | Model | Backend | VRAM mode | Prompt | Elapsed (s) | OK | Chars | Notes |
|------------|-------|---------|-----------|--------|-------------|-----|-------|-------|
| 2026-05-19 | deepseek-r1:14b | ollama | GPU | harvest | 480+ | partial | 5887 | TIMEOUT on first pass; retry ok |
| 2026-05-19 | qwen2.5-coder:14b-instruct-q4_K_M | ollama | GPU | harvest | ~120 | Y | 4644 | Best local quality |
| 2026-05-19 | phi3.5:latest | ollama | GPU | harvest | ~90 | Y | 6469 | Noisy terminal artifacts |
| 2026-05-19 | qwen3:14b | ollama | GPU | harvest | ~180 | Y | 6819 | Strong per-class |
| 2026-05-19 | llama3.2:3b | ollama | GPU | harvest | ~60 | Y | 1113 | Fast, shallow |

| 2026-05-19 | library-gemma3-4b:latest | ollama | auto | harvest | 22.33 | Y | 10586 | mega harvest |

| 2026-05-19 | phi4-mini:latest | ollama | auto | harvest | 5.61 | Y | 1008 | mega harvest |

| 2026-05-19 | smollm2:1.7b | ollama | auto | harvest | 5.43 | Y | 1813 | mega harvest |

| 2026-05-19 | qwen2.5:3b | ollama | auto | harvest | 4.4 | Y | 1072 | mega harvest |

| 2026-05-19 | llama3.2:1b | ollama | auto | harvest | 5.82 | Y | 1389 | mega harvest |

| 2026-05-19 | gemma3:4b | ollama | auto | harvest | 19.74 | Y | 5144 | mega harvest |

| 2026-05-19 | library-qwen2.5-coder-7b:latest | ollama | auto | harvest | 17.77 | Y | 752 | mega harvest |

| 2026-05-19 | mercury-2 | api | auto | harvest | 2.38 | Y | 2631 | mega harvest |

| 2026-05-19 | grok-3-latest | api | auto | harvest | 11.32 | Y | 1598 | mega harvest |

| 2026-05-19 | library-qwen2.5-coder-14b:latest | ollama | auto | harvest | 69.48 | Y | 1925 | mega harvest |

| 2026-05-19 | llama-3.3-70b-versatile | api | auto | harvest | 1.4 | Y | 839 | mega harvest |

| 2026-05-19 | deepseek-chat | api | auto | harvest | 17.28 | Y | 2579 | mega harvest |

| 2026-05-19 | openrouter/free | api | auto | harvest | 17.92 | Y | 1201 | mega harvest |

| 2026-05-19 | nvidia/nemotron-3-nano-30b-a3b:free | api | auto | harvest | 12.04 | Y | 2027 | mega harvest |

| 2026-05-19 | openai | api | auto | harvest | 16.02 | Y | 2043 | mega harvest |

| 2026-05-19 | library-qwen2.5-coder-14b-instruct-q4_k_m:latest | ollama | auto | harvest | 46.13 | Y | 1542 | mega harvest |

| 2026-05-19 | library-mistral-nemo-latest:latest | ollama | auto | harvest | 17.45 | Y | 1227 | mega harvest |

| 2026-05-19 | library-llama3.1-latest:latest | ollama | auto | harvest | 9.33 | Y | 1197 | mega harvest |

| 2026-05-19 | library-deepseek-r1-14b:latest | ollama | auto | harvest | 85.1 | Y | 4153 | mega harvest |

| 2026-05-19 | qr-test-duplicate:latest | ollama | auto | harvest | 18.6 | Y | 389 | mega harvest |

| 2026-05-19 | qr-library-qwen2-5-coder-14b:latest | ollama | auto | harvest | 33.42 | Y | 1824 | mega harvest |

| 2026-05-19 | llama3.2:3b | ollama | auto | harvest | 34.33 | Y | 1306 | mega harvest |

| 2026-05-19 | mercury-2 | api | auto | harvest | 2.5 | Y | 2905 | mega harvest |

| 2026-05-19 | openrouter/free | api | auto | harvest | 6.08 | Y | 1697 | mega harvest |

| 2026-05-19 | llama-3.3-70b-versatile | api | auto | harvest | 1.37 | Y | 804 | mega harvest |

| 2026-05-19 | openai | api | auto | harvest | 0.67 | Y | 2043 | mega harvest |

| 2026-05-19 | grok-3-latest | api | auto | harvest | 10.91 | Y | 1389 | mega harvest |

| 2026-05-19 | deepseek-chat | api | auto | harvest | 11.99 | Y | 1786 | mega harvest |

| 2026-05-19 | nvidia/nemotron-3-nano-30b-a3b:free | api | auto | harvest | 9.47 | Y | 1917 | mega harvest |

| 2026-05-19 | qwen3:14b | ollama | auto | harvest | 42.52 | Y | 4374 | mega harvest |

| 2026-05-19 | library-gemma3-4b:latest | ollama | auto | harvest | 43.77 | Y | 8557 | mega harvest |

| 2026-05-19 | qwen3.5:9b | ollama | auto | harvest | 57.86 | Y | 10770 | mega harvest |

| 2026-05-19 | phi4-mini:latest | ollama | auto | harvest | 47.47 | Y | 2189 | mega harvest |

| 2026-05-19 | smollm2:1.7b | ollama | auto | harvest | 8.49 | Y | 1834 | mega harvest |

| 2026-05-19 | llama3.2:1b | ollama | 100% GPU | auto-gpu | 6.06 | Y | 159 | tiny 164.37 tok/s |

| 2026-05-19 | qwen2.5:3b | ollama | auto | harvest | 11.48 | Y | 1707 | mega harvest |

| 2026-05-19 | phi3.5:latest | ollama | auto | harvest | 16.23 | Y | 6879 | mega harvest |

| 2026-05-19 | smollm2:1.7b | ollama | 100% GPU | auto-gpu | 9.05 | Y | 847 | tiny 265.71 tok/s |

| 2026-05-19 | llama3.2:1b | ollama | auto | harvest | 6.41 | Y | 1090 | mega harvest |

| 2026-05-19 | gemma3:4b | ollama | auto | harvest | 28.25 | Y | 6010 | mega harvest |

| 2026-05-19 | qwen3:4b | ollama | auto | harvest | 42.56 | Y | 15474 | mega harvest |

| 2026-05-19 | qwen2.5:3b | ollama | 100% GPU | auto-gpu | 41.09 | Y | 1781 | tiny 216.37 tok/s |

| 2026-05-19 | library-qwen2.5-coder-7b:latest | ollama | auto | harvest | 29.48 | Y | 2800 | mega harvest |

| 2026-05-19 | qwen2.5-coder:14b-instruct-q4_K_M | ollama | auto | harvest | 162.78 | Y | 6785 | mega harvest |

| 2026-05-19 | phi4-mini:latest | ollama | unknown | auto-gpu | 160.29 | Y | 794 | small 189.54 tok/s |

| 2026-05-19 | library-qwen2.5-coder-14b:latest | ollama | auto | harvest | 193.31 | Y | 2113 | mega harvest |

| 2026-05-19 | qwen2.5-coder:7b | ollama | auto | harvest | 56.08 | Y | 104 | mega harvest |

| 2026-05-19 | gemma3:4b | ollama | unknown | auto-gpu | 54.9 | Y | 1655 | small 148.92 tok/s |

| 2026-05-19 | library-qwen2.5-coder-14b-instruct-q4_k_m:latest | ollama | auto | harvest | 68.1 | Y | 2844 | mega harvest |

| 2026-05-19 | deepseek-r1:14b | ollama | auto | harvest | 166.72 | Y | 5624 | mega harvest |

| 2026-05-19 | qwen3:4b | ollama | unknown | auto-gpu | 164.42 | N | 0 | small 161.74 tok/s |

| 2026-05-19 | library-mistral-nemo-latest:latest | ollama | auto | harvest | 123.63 | Y | 1302 | mega harvest |

| 2026-05-19 | mistral-nemo:latest | ollama | auto | harvest | 29.38 | Y | 1533 | mega harvest |

| 2026-05-19 | llama3.2:3b | ollama | 100% GPU | auto-gpu | 25.79 | Y | 183 | small 225.13 tok/s |

| 2026-05-19 | library-llama3.1-latest:latest | ollama | auto | harvest | 23.27 | Y | 1687 | mega harvest |

| 2026-05-19 | phi3.5:latest | ollama | unknown | auto-gpu | 9.38 | Y | 1452 | small 92.39 tok/s |

| 2026-05-19 | llama3.1:latest | ollama | auto | harvest | 17.32 | Y | 1121 | mega harvest |

| 2026-05-19 | library-deepseek-r1-14b:latest | ollama | auto | harvest | 191.08 | Y | 10539 | mega harvest |

| 2026-05-19 | qwen2.5-coder:7b | ollama | unknown | auto-gpu | 192.24 | Y | 84 | medium 118.27 tok/s |

| 2026-05-19 | qr-test-duplicate:latest | ollama | auto | harvest | 21.02 | Y | 568 | mega harvest |

| 2026-05-19 | llama3.1:latest | ollama | unknown | auto-gpu | 21.53 | Y | 1243 | medium 113.72 tok/s |

| 2026-05-19 | qr-library-qwen2-5-coder-14b:latest | ollama | auto | harvest | 99.43 | Y | 4795 | mega harvest |

| 2026-05-19 | mistral-nemo:latest | ollama | unknown | auto-gpu | 100.12 | Y | 851 | medium 80.38 tok/s |

| 2026-05-19 | llama3.2:3b | ollama | auto | harvest | 14.64 | Y | 820 | mega harvest |

| 2026-05-19 | qwen3.5:9b | ollama | unknown | auto-gpu | 12.33 | N | 0 | medium 82.52 tok/s |

| 2026-05-19 | qwen3:14b | ollama | auto | harvest | 42.61 | Y | 4027 | mega harvest |

| 2026-05-19 | qwen2.5-coder:14b-instruct-q4_K_M | ollama | unknown | auto-gpu | 44.31 | Y | 1113 | large 61.58 tok/s |

| 2026-05-19 | qwen3.5:9b | ollama | auto | harvest | 53.61 | Y | 11220 | mega harvest |

| 2026-05-19 | deepseek-r1:14b | ollama | unknown | auto-gpu | 51.53 | N | 0 | large 62.25 tok/s |

| 2026-05-19 | qwen3:14b | ollama | unknown | auto-gpu | 13.65 | N | 0 | large 60.09 tok/s |

| 2026-05-19 | phi3.5:latest | ollama | auto | harvest | 23.0 | Y | 7277 | mega harvest |

| 2026-05-19 | qwen3:4b | ollama | auto | harvest | 27.83 | Y | 14889 | mega harvest |

| 2026-05-19 | qwen3:14b | ollama | unknown | auto-gpu | 37.4 | N | 0 | large 60.39 tok/s |

| 2026-05-19 | qwen2.5-coder:14b-instruct-q4_K_M | ollama | auto | harvest | 187.76 | Y | 9515 | mega harvest |

| 2026-05-19 | qwen3:14b | ollama | unknown | max-gpu-99 | 185.51 | Y | 240 | large 59.7 tok/s |

| 2026-05-19 | deepseek-r1:32b | ollama | 52%/48% CPU/GPU | auto | 253.22 | N | 0 | giant 4.0 tok/s |

| 2026-05-19 | qwen3:14b | ollama | unknown | gpu-35 | 153.58 | N | 0 | large 18.05 tok/s |

| 2026-05-19 | deepseek-r1:32b | ollama | unknown | gpu99-ctx2k | 796.26 | N | 0 | giant 0.53 tok/s |

| 2026-05-19 | qwen3:14b | ollama | unknown | gpu-20 | 816.49 | N | 0 | large 9.52 tok/s |

| 2026-05-19 | mistral-nemo:latest | ollama | auto | harvest | 260.69 | Y | 1710 | mega harvest |

| 2026-05-19 | deepseek-r1:32b | ollama | 100% CPU | cpu | 278.59 | N | 0 | giant 2.55 tok/s |

| 2026-05-19 | llama3.1:latest | ollama | auto | harvest | 226.11 | Y | 802 | mega harvest |

| 2026-05-19 | qwen3:14b | ollama | 100% CPU | cpu-only | 311.25 | Y | 193 | large 5.18 tok/s |

| 2026-05-19 | mixtral:8x7b-instruct-v0.1-q4_K_M | ollama | 69%/31% CPU/GPU | auto | 146.31 | Y | 1782 | giant 6.72 tok/s |

| 2026-05-19 | llama3.3:70b-instruct-q3_K_M | ollama | 71%/29% CPU/GPU | auto | 608.91 | Y | 2041 | giant 0.91 tok/s |

| 2026-05-19 | qwen3:32b | ollama | 50%/50% CPU/GPU | auto | 103.92 | N | 0 | giant 4.28 tok/s |

| 2026-05-19 | qwen3:32b | ollama | 100% GPU | gpu99-ctx2k | 755.66 | N | 0 | giant 0.54 tok/s |

*Add rows after each `python tools/local_gguf_ollama_consult.py` or `local_gguf_consult.py` (LM Studio) run.*

## Recommended stack (May 2026)

1. **Paid cloud first:** Grok (SuperGrok) + xAI + Inception mercury-2 for verdict-grade consults.
2. **Fast local screen:** `mistral-nemo` (~80 tok/s) or `gemma3:4b` for idea breadth.
3. **Deep local pass:** `qwen3:14b` / `deepseek-r1:14b` at **100% GPU** with `num_predict≥800` (HTTP API).
4. **GPU push benchmark:** `python tools/ollama_gpu_push_benchmark.py --phase all`
5. **32B on this PC:** hybrid ~4.5 tok/s (`num_ctx=2048`, `num_gpu=35`) — batch consults only.
6. **Best “over spec” local:** `mixtral:8x7b-instruct-v0.1-q4_K_M` ~7.5 tok/s (MoE). 70B Q3 overnight only.
7. **Borderline research:** `python tools/borderline_model_lab.py` → `reports/BORDERLINE_MODEL_RESEARCH_2026-05-19.md`

### Critical API settings (12GB VRAM)

| Parameter | 14B | 32B / MoE | 70B Q3 |
|-----------|-----|-----------|--------|
| `num_predict` | **≥800** | 500–600 | 400 |
| `num_ctx` | 4096 | **2048** | 2048 |
| `num_gpu` | 99 (full GPU) | 35 or auto | auto |

## Commands

```powershell
cd e:\findtorontoevents_antigravity.ca
python tools/ollama_import_gguf.py --scan
python tools/ollama_import_gguf.py --import-all
python tools/local_gguf_ollama_consult.py --import-missing --all-installed
python tools/ai_consult_orchestrator.py --phase 3
```

## Ollama 0.24 on Windows

- Do **not** use `FROM F:\...\library-*.gguf` when the file is a **broken symlink** — use resolved blob path (see `tools/ollama_import_gguf.py`).
- Error `invalid model name` often means **missing blob**, not bad tag. Run `--scan` first.
- Modelfiles saved under `swarm_runs/ollama-modelfiles/`.


## Cloud + local intelligence log
| 2026-05-19 | inclusionai/ring-2.6-1t | api | cloud | r3 | 19.21 | Y | 5116 | intel=3 | cloud/openrouter |
| 2026-05-19 | deepseek-chat | api | cloud | r2 | 36.9 | Y | 6990 | intel=3 | cloud/deepseek |
| 2026-05-19 | mercury-2 | api | cloud | r1 | 2.53 | Y | 3953 | intel=3 | cloud/inception |
| 2026-05-19 | qwen3:14b | ollama | local | harvest | 27.3 | Y | 1619 | intel=2 | HTTP num_predict=1200 |
| 2026-05-19 | inclusionai/ring-2.6-1t | api | cloud | harvest | 19.26 | Y | 2546 | intel=3 | sequential grill |
| 2026-05-19 | openrouter/free | api | cloud | harvest | 32.48 | Y | 5768 | intel=4 | sequential grill |
| 2026-05-19 | deepseek-chat | api | cloud | harvest | 21.39 | Y | 4279 | intel=4 | sequential grill |
| 2026-05-19 | mercury-2 | api | cloud | harvest | 2.42 | Y | 2580 | intel=4 | sequential grill |
| 2026-05-19 | grok-3-latest | api | cloud | harvest | 7.06 | Y | 1477 | intel=3 | sequential grill |

| Date | Model | Backend | Tier | Prompt | Elapsed | OK | Chars | Notes |
|------|-------|---------|------|--------|---------|----|-------|-------|
