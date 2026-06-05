# vLLM Filesystem Audit — 2026-06-05

## Installation

| Item | Path |
|---|---|
| **Binary** | `/home/eaguiar2015/findtorontoevents_antigravity.ca/.venv/bin/vllm` |
| **Version** | `0.21.0` |
| **Site-packages** | `.venv/lib/python3.13/site-packages/vllm` |
| **Runtime cache** | `~/.cache/vllm/` |
| **uv wheel cache** | `~/.cache/uv/wheels-v6/pypi/vllm` |
| **uv archive cache** | `~/.cache/uv/archive-v0/uw9SIVpo99Bpxrdq/vllm` |

vLLM is installed inside the **repo-local virtualenv** (`.venv`), not globally or in conda.
A Hermes skill stub also exists at `~/.hermes/skills/mlops/inference/vllm` but is not an install.

---

## Model Weights (`~/.cache/huggingface/hub/`)

All fully-downloaded models:

| Model | Size |
|---|---|
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | **57 GB** |
| `Qwen/Qwen2.5-14B-Instruct` | 28 GB |
| `Qwen/Qwen3-8B` | 16 GB |
| `Qwen/Qwen2.5-7B-Instruct` | 15 GB |
| `Qwen/Qwen3-4B` | 7.6 GB |
| `Qwen/Qwen2.5-3B-Instruct` | 5.8 GB |
| `mistralai/Mistral-7B-Instruct-v0.3` | 4.2 GB |
| `Qwen/Qwen2.5-1.5B-Instruct` | 2.9 GB |
| `Qwen/Qwen3-0.6B` | 1.5 GB |
| **Total** | **~138 GB** |

Stub-only entries (metadata only, weights not pulled):

| Model | Cache size |
|---|---|
| `google/gemma-4-12b-it` | 32 KB |
| `nvidia/Nemotron-Mini-4B-Instruct` | 36 KB |
| `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | 36 KB |

---

## Current Runtime State

- **vLLM server:** NOT running (no active process)
- **LiteLLM proxy:** RUNNING — PID `826355`, port `4000`, config `litellm_config.yaml`
  - Serving cloud APIs only (Groq, Gemini, NVIDIA NIM, Mistral, Fireworks, etc.)
  - No local vLLM backend wired into the proxy config

---

## Skill / Command Wiring

vLLM management skills live in:
- `FREELLM/.claude/commands/startvllmp.md` → `/startvllmp`
- `FREELLM/.claude/commands/stopvllmp.md` → `/stopvllmp`
- `FREELLM/.claude/commands/statusvllmp.md` → `/statusvllmp`
- `FREELLM/tools/vllmp_mode_status.py` — health + request-count reporter

Same skill files are mirrored in worktrees:
- `audit-truth-review-2026-06-04/.claude/commands/`
- `audit-truth-layer-worktree/.claude/commands/`

---

## Notes

- All weights are Qwen-family except one Mistral; Qwen3-Coder-30B is by far the largest at 57 GB.
- The three stub entries (gemma-4-12b, Nemotron-Mini-4B, TinyLlama) were referenced/inspected but never fully downloaded.
- To start a local vLLM endpoint, use `/startvllmp` or run manually:
  ```
  .venv/bin/vllm serve <model-id> --port 8000
  ```
