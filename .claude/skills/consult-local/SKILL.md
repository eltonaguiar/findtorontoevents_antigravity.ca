---
name: consult-local
description: One-shot second opinions / parallel drafting via the LOCAL AI fleet — vLLM (:8000 Qwen2.5-14B), Ollama (:11434, 23 models incl. llama3.3:70b + deepseek-r1:32b), LiteLLM proxy (:4000, 15 cloud groups). Use when the user says "/consult-local", "ask the local fleet", "local second opinion", or when a quick sanity-check/draft shouldn't burn cloud quota. Zero-key, low-latency.
---

# /consult-local — local-fleet second opinions

Three OpenAI-compatible-ish endpoints, all local. Prefer this for: quick sanity checks on a plan,
adversarial "try to refute X" passes, drafting boilerplate, and triangulating a claim before a
heavier cloud swarm. (For multi-engine review swarms use /swarm-run or /consult-PROXY instead.)

## Pick the engine
| Need | Engine | Why |
|---|---|---|
| fast structured second opinion | **vLLM :8000** (`Qwen/Qwen2.5-14B-Instruct`) | GPU, ~16k ctx, OpenAI-compatible |
| deepest local reasoning | **Ollama** `deepseek-r1:32b` or `llama3.3:70b` | strongest local; slower |
| balanced/quick | **Ollama** `qwen3:30b-a3b` or `qwen2.5:14b` | good speed/quality |
| cloud-grade w/ rotation | **LiteLLM :4000** `deepseek-chat-direct` / `free-mode` | when local isn't enough |

## One-shot commands (verified patterns)

```bash
# vLLM (OpenAI-compatible) — FIRST CHOICE for a quick opinion
curl -s -m 90 http://localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "Qwen/Qwen2.5-14B-Instruct",
  "messages": [{"role":"user","content":"<PROMPT — include all data inline; it cannot fetch>"}],
  "max_tokens": 700, "temperature": 0.2
}' | python3 -c "import sys,json;print(json.load(sys.stdin)['choices'][0]['message']['content'])"

# Ollama (native API)
curl -s -m 180 http://localhost:11434/api/generate -d '{
  "model": "deepseek-r1:32b", "prompt": "<PROMPT>", "stream": false
}' | python3 -c "import sys,json;print(json.load(sys.stdin)['response'])"

# LiteLLM proxy (cloud rotation; same chat/completions shape, model: deepseek-chat-direct etc.)
curl -s -m 90 http://localhost:4000/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "deepseek-chat-direct",
  "messages": [{"role":"user","content":"<PROMPT>"}], "max_tokens": 700
}' | python3 -c "import sys,json;c=json.load(sys.stdin)['choices'][0]['message'];print(c.get('content') or c.get('reasoning_content',''))"
```

## Rules (from this repo's hard-won lessons)
1. **Feed data inline, never let the model claim to fetch** (CLAUDE.md: models fabricate /audit numbers).
2. **Treat quantitative outputs as UNVERIFIED** — re-verify any n/WR/PF via direct SQL before acting
   (`feedback-subagent-stat-fabrication-2026-06-05`).
3. For *decisions*, ask 2+ engines independently and look for convergence; for *refutation* passes,
   prompt "try to refute X, default to refuted if uncertain".
4. Health check first if a call hangs: `/startaiservers` skill (or `curl -s -m3 localhost:8000/v1/models`,
   `localhost:11434/api/tags`, `localhost:4000/health/readiness`).
5. vLLM GB10 memory: ONE model at a time (~84 GiB usable); the 57GB MoE OOMs — don't restart vLLM with it.

## Parallel drafting pattern
Fan N prompts to vLLM/Ollama in background `curl ... &` jobs, collect to /tmp files, then synthesize.
For repo-aware parallel CODING agents, prefer Claude subagents (they have tools); use the local fleet
for opinion/text-only fan-out.
