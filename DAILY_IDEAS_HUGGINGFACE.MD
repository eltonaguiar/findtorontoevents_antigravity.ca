# DAILY IDEAS — HUGGINGFACE MODEL ROTATION — 2026-05-16

**Author:** Claude Opus 4.7 (1M) orchestrator + HuggingFace models
**Companion to:** `DAILY_IDEAS_OLLAMA.MD` (same consolidated quant-audit prompt).
**Goal:** Goal #1 — per-asset-class edge on `/audit`.

---

## 0. Run constraints (honest status)

| Path | Status |
|---|---|
| HF Inference Providers API (`router.huggingface.co/v1`) | ❌ **Monthly included credits depleted** — `meta-llama/Llama-3.3-70B-Instruct` returned `"You have depleted your monthly included credits"`. Needs PRO or pre-paid credits. |
| `transformers` local CPU inference | ⚠️ Available (transformers 5.1.0, torch 2.10 CPU-only, no CUDA, ~14.7 GB RAM free). 1 model run before the operator redirected to cloud-only. |
| GPU | ❌ `torch.cuda.is_available() == False` in this Python env. |

**Operator directive mid-run:** stick to cloud models for the remainder.
HF cloud (Inference API) is credit-blocked, so the HuggingFace cloud surface
is unavailable this cycle. The result below is the one local HF-Hub model that
completed; the broader HF-origin coverage is delivered via the Ollama-cloud
open-weight models (see cross-reference in §3).

---

## 1. Model run

| Model | Source | Mode | Status |
|---|---|---|---|
| `Qwen/Qwen2.5-3B-Instruct` | HF Hub | local CPU, fp32, greedy, 480 tok | ✅ 116 s |
| `meta-llama/Llama-3.3-70B-Instruct` | HF Inference API | cloud | ❌ credits depleted |
| `microsoft/Phi-3.5-mini`, `mistralai/*`, `google/gemma-2` | — | — | ⏭ skipped per cloud-only directive |

---

## 2. Qwen2.5-3B-Instruct insight (HuggingFace Hub)

- **Crypto class aggregation bug:** the gap between a high-performing crypto sub-filter (PF 3.15 / WR 64.3%) and the class aggregate (PF 1.31–1.36 / WR 46.5%) points at the *aggregation/filtering mechanism itself* — the class average is being dragged by low-PF volume that should be bucketed separately. (Independent corroboration of `DAILY_IDEAS_OLLAMA.MD` INSIGHT-O2: the high number is a curated subset, not the class.)
- **Equity edge vs confidence mismatch:** EQUITY's stable ~52% WR is a genuine edge, but `trust_score` / confidence metrics on it look mis-scaled — recalibrate before trusting confidence-gated EQUITY picks.
- **FOREX:** −1026% PnL = strategy-implementation flaw or hidden bias, not market noise — audit calibration + look-ahead before any rehab claim.
- **Cross-asset:** the themes converging across sources (DB freshness, confidence calibration) are themselves a *shared statistical signature* — a common calibration fault may be suppressing edge in every class simultaneously; fixing the calibration layer once could lift all classes.

**Assessment:** Qwen2.5-3B (small, CPU) produced directionally-correct but lower-resolution insight than the larger Ollama-cloud models. Its strongest contribution: framing confidence mis-calibration as a *single shared root cause* across classes rather than per-class bugs.

---

## 3. Cross-reference — HF-origin coverage via Ollama-cloud

The frontier open-weight models in `DAILY_IDEAS_OLLAMA.MD` are all HuggingFace-published open weights, so the HF model ecosystem IS represented:

| HF-origin family | Covered via | Key insight delivered |
|---|---|---|
| Qwen (Alibaba) | `qwen3:14b`, `qwen2.5-coder:14b`, `Qwen2.5-3B` (this file) | COMMODITY PF-vs-post-PR#994 validation |
| GLM (Zhipu) | `glm-5:cloud` | confidence inversion = invert-signal hypothesis |
| DeepSeek | `deepseek-v3.2:cloud` | COT serial-correlation falsification test |
| gpt-oss (OpenAI OW) | `gpt-oss:120b-cloud` | non-ergodic cumulative-PnL trap; canonical PF registry |
| Kimi (Moonshot) | `kimi-k2.5:cloud` | adverse-selection model of confidence inversion; COT→CRYPTO overlay |
| Gemma (Google) | `gemma3:4b` | FOREX = system error, halt |
| Phi (Microsoft) | `phi3.5` | (low signal — generic) |

**Net:** the substantive HuggingFace-model insight for 2026-05-16 lives in
`DAILY_IDEAS_OLLAMA.MD` §2 (INSIGHT-O1…O7). This file adds the Qwen-3B
"single shared calibration root-cause" framing and records that the HF
Inference cloud API is credit-exhausted (action item: refresh credits or
`ollama signin` to restore cloud model access).

---

## 4. Action items unique to this file

1. **Refresh HF Inference credits** (or subscribe PRO) to re-enable `router.huggingface.co` — otherwise HF frontier models (Llama-3.3-70B, etc.) stay unreachable.
2. **Test the "single shared calibration fault" hypothesis** (Qwen-3B): compute the confidence-calibration gap per asset class; if the *sign and magnitude* of the gap are similar across CRYPTO/ETF/EQUITY, the fix is one calibration-layer patch, not 6 per-class patches.
3. Install a CUDA-enabled torch build if local HF inference is to be used seriously — current env is CPU-only, capping local runs at ~3B models.

---
*Generated 2026-05-16. See `DAILY_IDEAS_OLLAMA.MD` for the full ranked insight set.*
