# Borderline local model research — RTX 5070 12GB / 32GB RAM

**Generated:** 2026-05-19 (live experiments via `tools/borderline_model_lab.py`)  
**Hardware:** i9-14900K · **RTX 5070 12GB** · 32GB DDR5 · Ollama HTTP `/api/generate`

---

## Executive summary

| Tier | Models | Fits? | Best tok/s | Technique |
|------|--------|-------|------------|-----------|
| **A — Native GPU** | 7B–14B Q4, Mistral-Nemo 12B | ✅ Yes | 59–81 | `num_gpu=99`, `num_ctx=4096`, `num_predict≥800` |
| **B — Hybrid 32B** | Qwen2.5-Coder-32B, DeepSeek-R1-32B | ✅ Yes (slow) | **~4.5** | `num_ctx=2048`, auto or `num_gpu=35`, ~50/50 CPU/GPU |
| **C — MoE giant** | Mixtral 8×7B Q4_K_M | ✅ Yes | **~7.5** | MoE activates 2 experts; prefer **auto** over forced `num_gpu=35` |
| **D — 70B Q3** | Llama 3.3 70B Q3_K_M | ⚠️ Overnight | **~0.9** | Already quantized; 10+ min per short prompt |
| **Broken config** | Qwen3.5 9B | ❌ | fast but **0 visible chars** | Harmony/template — use Qwen3 14B instead |

**Root cause of earlier “FAIL” on 14B:** `num_predict=400` on reasoning models → empty/truncated output. **Fix:** `num_predict≥800`, `num_ctx=2048–4096`.

---

## Hardware ceiling (why models are “just outside”)

| Resource | Your limit | What it means |
|----------|------------|---------------|
| **VRAM** | 12,227 MiB (~11.9 GB usable) | Q4 14B weights ~8–9 GB + KV cache; 32B Q4 weights ~19 GB **must** spill to RAM |
| **RAM** | 32 GB | Holds offloaded layers + OS; 32B + 70B both run but bandwidth-limited |
| **PCIe** | Gen4 x16 | CPU↔GPU weight streaming when layers don’t fit |

**Rule of thumb (Q4_K_M):**

- **≤9 GB file** → full GPU at 4096 ctx (14B class)
- **~19 GB file** → hybrid ~50% GPU / 50% CPU at 2048 ctx
- **~28–34 GB file** → MoE or Q3 quant; expect &lt;10 tok/s unless overnight batch

---

## Techniques tested (what actually works)

### 1. Quantization (GGUF)

| Quant | Size multiplier | Quality | This PC |
|-------|-----------------|---------|---------|
| **Q4_K_M** | 1× (baseline) | Best speed/quality for 7–32B | Default for 14B/32B |
| **Q3_K_M** | ~0.75× | Visible quality loss | **Required** for 70B (`llama3.3:70b-instruct-q3_K_M`) |
| **Q2_K** | ~0.5× | Heavy degradation | Not tested — try only if Q3 OOMs |
| **Q8** | ~2× | Marginal gain | **Avoid** on 12GB — wastes VRAM |

Pull smaller tags when available:

```powershell
ollama pull deepseek-r1:14b          # ~9 GB — fits GPU
ollama pull qwen2.5-coder:32b-instruct  # ~19 GB — hybrid
ollama pull mixtral:8x7b-instruct-v0.1-q4_K_M  # MoE — best “giant” UX
# Avoid llama3.3:70b for interactive; batch only
```

### 2. Partial GPU offload (`num_gpu`)

Controls **layers on GPU**, not “which GPU.”

| Setting | 14B effect | 32B effect |
|---------|------------|------------|
| `num_gpu=99` (or `-1` auto) | **100% GPU**, ~60 tok/s | ~50% GPU hybrid |
| `num_gpu=35` | 100% GPU | ~45/55 hybrid, **best 32B quality** |
| `num_gpu=20` | 55/45 hybrid, ~9 tok/s | More CPU, slower |

**Custom Modelfile** (persist settings):

```dockerfile
FROM qwen3:14b
PARAMETER num_gpu 99
PARAMETER num_ctx 4096
```

```powershell
ollama create qwen3-14b-harvest -f Modelfile
```

### 3. Context window (`num_ctx`)

| num_ctx | VRAM for KV | Use case |
|---------|-------------|----------|
| **2048** | Lowest | Screening prompts, 32B/70B giants |
| **4096** | Medium | **Recommended** for 14B harvest |
| **8192** | Highest | Avoid on 12GB with 14B+ — causes false OOM/slow |

### 4. Output cap (`num_predict`)

| Model family | Minimum | Why |
|--------------|---------|-----|
| Qwen3 / DeepSeek-R1 | **800–1200** | Reasoning + table output; 400 → 0-char “FAIL” |
| Mistral / Llama 3 | 400–600 | Works at lower cap |
| 32B hybrids | 500–600 | ~2–4 min per response at 4 tok/s |

### 5. MoE (Mixtral)

- **Nominal** 47B params; **active** ~13B (2×7B experts).
- At Q4_K_M (~28 GB disk) runs **7.45 tok/s** hybrid — **best giant for interactive** consults on this box.
- **Do not** force `num_gpu=35` on Mixtral — caused instant FAIL in lab (OOM).

### 6. CPU-only fallback

- 14B at `num_gpu=0`: ~5 tok/s — viable for overnight batch, not grill loops.

---

## Live experiment results (2026-05-19)

### 14B class — **fully on GPU** (fix: `num_predict≥800`)

| Model | Best config | Time | tok/s | Processor |
|-------|-------------|------|-------|-----------|
| `qwen3:14b` | gpu99-ctx4k-p800 | 12.3s | **59.1** | 100% GPU |
| `deepseek-r1:14b` | gpu99-ctx4k-p800 | 18.3s | **61.4** | 100% GPU |
| `mistral-nemo:latest` | auto-ctx2k-p800 | 7.9s | **80.2** | 100% GPU |

`qwen3.5:9b` — **81 tok/s but 0 chars** in `response` (likely Qwen3.5 renderer outputs elsewhere or empty template). **Use `qwen3:14b` instead.**

### 32B class — **hybrid, usable for batch consults**

| Model | Best config | Time | tok/s | VRAM used |
|-------|-------------|------|-------|-----------|
| `qwen2.5-coder:32b-instruct` | gpu35-ctx2k-p600 | 135s | **4.49** | 11,695 MiB |
| `deepseek-r1:32b` | gpu35-ctx2k-p600 | 148s | **4.57** | ~11,200 MiB |

All 32B configs **OK** with 1.4–2.5k char answers at `num_ctx=2048`.

### MoE — **best “over spec” model**

| Model | Best config | Time | tok/s |
|-------|-------------|------|-------|
| `mixtral:8x7b-instruct-v0.1-q4_K_M` | auto-ctx2k-p500 | 134s | **7.45** |

### 70B — from prior benchmark (not re-run; ~10 min)

| Model | Config | Time | tok/s | Verdict |
|-------|--------|------|-------|---------|
| `llama3.3:70b-instruct-q3_K_M` | auto | 609s | 0.91 | Overnight batch only |

---

## Recommended local stack (May 2026, this desktop)

| Role | Model | Settings |
|------|-------|----------|
| **Fast screen** | `mistral-nemo:latest` or `gemma3:4b` | default Ollama |
| **Harvest quality** | `qwen3:14b` or `deepseek-r1:14b` | HTTP: `num_gpu=99`, `num_ctx=4096`, `num_predict=1200` |
| **Code-heavy** | `qwen2.5-coder:14b-instruct-q4_K_M` | Same as 14B |
| **“Bigger brain” batch** | `mixtral:8x7b-instruct-v0.1-q4_K_M` | `num_ctx=2048`, `num_predict=600`, expect ~2 min |
| **32B reasoning batch** | `deepseek-r1:32b` | `num_ctx=2048`, `num_gpu=35`, ~2.5 min |
| **Skip interactive** | `llama3.3:70b-*`, `qwen3:32b` (marginal vs Mixtral) | Cloud API cheaper |

---

## Commands

```powershell
cd e:\findtorontoevents_antigravity.ca

# Full matrix (long — hours)
python tools/borderline_model_lab.py

# Quick screen (14B + one giant)
python tools/borderline_model_lab.py --quick --models "qwen3:14b,mixtral:8x7b-instruct-v0.1-q4_K_M"

# Harvest with fixed HTTP caps
python tools/model_grill_sequential.py --job ollama:qwen3:14b --prompt harvest

# Import F:\ GGUF library
python tools/ollama_import_gguf.py --scan
```

---

## Next experiments (optional)

1. **Pull** `qwen2.5-coder:32b-instruct-q4_K_M` if separate tag exists (smaller than full 19G).
2. **Modelfile** `qwen3-14b-harvest` with baked `num_predict 1200` for grill script.
3. **KV cache quant** — watch Ollama release notes for `kv_cache_type` on Windows.
4. **Qwen3.5 9B** — debug `response` vs thinking blocks (may need parser change in lab).

**Repro:** `python tools/borderline_model_lab.py --quick`  
**Artifacts:** `reports/borderline_model_lab_latest.json`, `swarm_runs/borderline-lab/<timestamp>/`
