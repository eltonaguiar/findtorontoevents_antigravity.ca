---
name: consult-multi
description: Unified multi-provider AI consult tool. Wraps 11 LLM providers (NVIDIA NIM, Groq, Cerebras, Together, Fireworks, GitHub Models, HuggingFace, Gemini API, Cloudflare Workers AI, DeepInfra, Nous Research Portal) behind one CLI so multi-AI fan-outs and single-provider consults share one well-tested code path. Reads keys from ~/dbpasses.txt (gitignored). Use when the user says "/consult-multi", "fan to N peers", "multi-provider consult", or wants triangulation across many providers in one call. Subcommands - list, run (--provider), fan-out (--fanout).
---

# consult-multi

One CLI, 11 providers, one source of truth for keys. Built 2026-05-25 to consolidate the 9+ per-provider consult scripts and resolve the stale-env-var bug that made multi-provider fan-outs flaky.

## Why this exists

- Stale shell-env vars (`GROQ_API_KEY` etc. left over from old sessions) were silently shadowing the live values in `~/dbpasses.txt`, causing HTTP 403 auth rejections across Groq/Cerebras/Together. This tool reads file FIRST, env only as fallback.
- urllib's default `Python-urllib/3.X` User-Agent is rejected by Groq/Cerebras/Together with HTTP 403. This tool sends a real UA on every request.
- Per-provider tools each had their own auth/endpoint quirks; this consolidates them.

## When to use

- "Fan to N peers" — use `--fanout diverse5` (or any preset)
- "Consult provider X" — `--provider <name>` with optional `--model`
- "What providers do we have, which keys work" — `--list`
- Multi-AI triangulation on quant/strategy/code questions (the gold-standard pattern that debunked the COMMODITY edge on 2026-05-25 — 3-engine consensus DATA_QUALITY_LEAKAGE)

## Prerequisites

Keys live in `~/dbpasses.txt` (gitignored — never committed). The file has labelled blocks like:

```
NVIDIA:
nvapi-...

GROQ FREE KEY:
gsk_...
```

The script parses label-then-value pairs. Override per-key via env var if needed (e.g. `NVIDIA_API_KEY=...`) — file takes precedence over env to avoid stale-env-var shadowing.

## Subcommands

### `--list` — provider catalog + which keys are loaded

```bash
python3 tools/consult_multi.py --list
```

Output:
```
provider        has_key  default_model
nvidia              yes  meta/llama-3.1-8b-instruct
groq                yes  qwen/qwen3-32b
cerebras            yes  llama3.1-8b
...
```

### `--provider X` — single-provider call

```bash
python3 tools/consult_multi.py --provider groq --model llama-3.1-8b-instant \
  --prompt "What is 1+1?"

# or pipe a longer prompt
cat /tmp/q.md | python3 tools/consult_multi.py --provider nvidia --model moonshotai/kimi-k2.6
```

### `--fanout PRESET` — fan one prompt to N peers

```bash
python3 tools/consult_multi.py --fanout diverse5 --prompt-file /tmp/q.md \
  --out-dir /tmp/fanout_results
```

Presets (each writes one `.md` per peer to `--out-dir`):
- **`diverse5`** — nvidia/kimi + cloudflare/llama + groq/llama + gemini/flash + cerebras/llama. Default for "fan to 5 peers".
- **`fast4`** — groq/llama-instant + cerebras + fireworks + gemini-flash. Sub-second responses.
- **`reasoning4`** — kimi-K2.6 + gemini-pro + llama-405b + deepseek-v3. For heavy reasoning.
- **`all9`** — one model per provider. Maximum diversity.

## Verified provider status (2026-05-25, 14 providers)

| Provider | Status | Default model | Notes |
|---|---|---|---|
| nvidia | ✅ working | meta/llama-3.1-8b-instruct | Full NIM catalog accessible |
| groq | ✅ working | qwen/qwen3-32b | Fastest free-tier inference |
| cerebras | ✅ working | llama3.1-8b | 4 free models: glm-4.7, llama3.1-8b, qwen-3-235b, gpt-oss-120b |
| together | ✅ working | meta-llama/Meta-Llama-3-8B-Instruct-Lite | 257 models; Lite variants free |
| fireworks | ✅ working | accounts/fireworks/models/kimi-k2p5 | kimi-k2p5, glm-5p1, gpt-oss-120b free |
| github_models | ✅ working | gpt-4o-mini | Free quota on github_pat tokens |
| gemini_api | ✅ working | gemini-flash-latest | Primary key works; alt 429-blocked. Avoid thinking-models with low max_tokens (truncates without visible output). |
| deepinfra | ✅ working (alt key) | meta-llama/Meta-Llama-3.1-8B-Instruct | Primary key dead (401); alt works |
| nous | ✅ working | Hermes-4-405B | **USE ONLY FREE MODELS** per provider — balance=0 stops free access |
| mistral | ✅ working | mistral-small-latest | Direct REST, free tier |
| aimlapi | ✅ working | gpt-4o-mini | Free key preferred over $20-limit paid key |
| huggingface | ⚠️ quota | openai/gpt-oss-20b | 402 monthly free credits depleted; subscribe to PRO or wait month reset. The legacy `api-inference.huggingface.co` is DNS-unresolvable from this network — only the router endpoint is usable. |
| cloudflare | ⚠️ quota | @cf/meta/llama-3.1-8b-instruct | 429 daily 10,000-neuron quota exhausted; resets at UTC midnight |
| hypereal | ⚠️ paid | kimi-k2.6 | Frontier-model proxy (Claude Opus 4.7, GPT-5.5, Gemini 3.5, etc.). Requires $2 min credit balance; current balance=0. **Domain: hypereal.cloud** (NOT hyperbolic.xyz — common confusion). Anthropic models route via `/v1/messages`. |

**The 3 ⚠️ providers have valid keys** — they're quota-capped at the account level. Wait or pay.

## MANDATORY: leakage-context block

For any asset-class / edge / pick-performance question, prepend the leakage-context block from `.claude/skills/consult-nvidia-models/SKILL.md`. The 2026-05-25 COMMODITY-edge incident proved that unguarded multi-AI panels confidently reach the wrong answer when leakage signals are omitted (5/5 NIM panel said "COMMODITY #1 alpha"; the 3-engine codex/grok/gemini panel that DID see leakage signals classified it `DATA_QUALITY_LEAKAGE` at 90% confidence — the latter was right).

## Related skills

- `consult-nvidia-models` — multi-model NIM-only fan-out (subset of this tool)
- `consult-cloudflare-models` — multi-model CF-only fan-out (subset)
- `consult-nvidia-deepseek` / `consult-cloudflare` — single-provider variants
- `consult-codex` / `consult-grok` / `consult-gemini` / `consult-opencode` — single-CLI consults
- `swarm-run` / `swarm-second-opinion` — older provider-agnostic dispatcher (preserve for now)
