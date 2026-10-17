# LiteLLM proxy — free-first policy + local providers (Ollama / vLLM)

**Date:** 2026-10-03
**Status:** Implemented + verified. Not committed.
**Goal:** use $0 capacity (local GPU + free cloud tiers) first, and reach a paid API only after every free option is exhausted.

## 1. Fallback reordering — paid is now last

`free-mode-large` previously fell back to **`paid-mode-large` first**, so any transient
free-tier rate-limit sent traffic straight to paid. Measured cause of opencode bursts
landing on xAI Grok.

Before → after:

| group | before | after |
|---|---|---|
| `free-mode-large` | `paid-mode-large, paid-mode, free-mode` | **`free-mode, free-mode-fast, free-mode-tools, paid-mode-large, paid-mode`** |
| `free-mode` | `free-mode-large, paid-mode` | **`free-mode-large, free-mode-fast, free-mode-tools, paid-mode`** |
| `hybrid-model` | `free-mode-large, free-mode, paid-mode` | **`free-mode, free-mode-large, free-mode-fast, paid-mode`** |
| `free-mode-fast` | `free-mode, free-mode-large, paid-mode-fast` | **`free-mode, free-mode-large, free-mode-tools, paid-mode-fast`** |
| `free-mode-tools` | `paid-mode-fast, paid-mode, free-mode-fast` | **`free-mode, free-mode-fast, free-mode-large, paid-mode-fast`** |

`paid-mode*` → still prefers paid siblings then free (unchanged semantics).

## 2. Local providers added to the free groups

### Ollama daemon `:11434` (auth lives in `~/.ollama/id_ed25519`, no bearer key)
`dbpasses.txt` holds an **ssh-ed25519 PUBLIC KEY** for Ollama — it cannot be used as a
token, which is why the provider was skipped historically. It is not needed at all.

Verified free on this account (2026-10-03):

| model | status |
|---|---|
| `gpt-oss:120b-cloud` | ✅ free |
| `gpt-oss:20b-cloud` | ✅ free |
| `minimax-m3:cloud` | ❌ "not included in your free usage" |
| `deepseek-v3.1:671b`, `kimi-k2:1t`, `glm-4.6`, `qwen3-coder:480b`, `deepseek-v3.2`, `kimi-k2.5`, `minimax-m2`, `glm-4.7` | retired |
| `qwen2.5:7b` (local GPU) | ✅ free, unlimited |

Local models **larger than ~7B fail to load** while vLLM holds memory:
`qwen3:30b-a3b` needs 20.7 GiB (20.0 available), `deepseek-r1:32b` needs 24 GiB (19.9 available).

### Local vLLM `:8000`
`hosted_vllm/Qwen/Qwen2.5-14B-Instruct`, GPU-backed, $0, unlimited.

## 3. THE BUG — deployments silently never selected

A local provider can be registered, healthy, callable **directly**, and still be picked
**zero times** inside a group.

Reproduced: **0 local picks across 36+ requests**.

Two independent causes, both now fixed:

1. **`model_info.max_input_tokens` unset** → the entry reports `max_input_tokens: null`.
2. **`rpm` unset** → **`simple-shuffle` is weighted by `rpm`.** Cloud entries in these
   groups declare `rpm` (1-15), so they carry weight; a deployment with no `rpm` gets
   weight 1 and is effectively starved. This was the dominant cause.

A/B evidence:

| config | result over 18 calls (free-mode-large) |
|---|---|
| no `rpm` (max_input_tokens set) | gemini 18 / local **0** |
| `enable_pre_call_checks: false` (to rule it out) | gemini 18 / local **0** |
| **`rpm: 30` on Ollama, `rpm: 60` on vLLM** | **OLLAMA 6 / gemini 6 / VLLM-local 6** |

So `enable_pre_call_checks` was NOT the cause; rpm weighting was.

**Rule for adding any self-hosted/uncapped provider:** set BOTH `model_info.max_input_tokens`
AND `rpm` on the deployment.

## 4. Tool / web capability

| provider | tool calling |
|---|---|
| local vLLM (current launch) | ❌ vLLM was started without `--enable-auto-tool-choice --tool-call-parser hermes` |
| local Ollama 7B | limited |
| `gpt-oss:*-cloud` (free) | ✅ |
| `free-mode-tools` (Groq / Cerebras / Bluesmind) | ✅ free |

So for tool/web workloads the free tier still covers it — via `free-mode-tools` and the
free `gpt-oss` cloud models — paid is not required.

To let local vLLM serve tool calls, restart it with:
`.venv/bin/vllm serve Qwen/Qwen2.5-14B-Instruct --port 8000 --max-model-len 16384 --gpu-memory-utilization 0.85 --enable-auto-tool-choice --tool-call-parser hermes`

## Verification

- YAML parses; proxy healthy; 136 model_list entries.
- 18× `free-mode-large`: **6 Ollama / 6 Gemini / 6 local vLLM**, zero paid.
- Fallback order printed from the parsed YAML and confirmed free-first.
- Ollama reachable through the proxy (`served_by: http://localhost:11434`).

## Files touched

- `litellm_config.yaml` — fallback reorder; +8 local deployments; `model_info` + `rpm` on them.
- `updates/2026-10-03-litellm-free-first-and-local-providers.md` (this file)

**Not committed / not pushed.**
