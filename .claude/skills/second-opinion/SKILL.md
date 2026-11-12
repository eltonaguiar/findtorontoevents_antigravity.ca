---
name: second-opinion
description: Get a fast, near-zero-cost second opinion from the local stack (vLLM, Ollama, LiteLLM), keyless endpoints (Pollinations, OVH AI, LLM7), or keyed free tiers (Groq, Gemini, Mistral, HuggingFace, DeepInfra, Cohere, OpenRouter…). Use when a plan, diagnosis, or tradeoff needs triangulation, or the user says "second opinion", "ask another model", "what would X say".
---

# second-opinion — multi-provider triangulation

Live-probed **2026-11-03 00:5xZ** (`PONG` completion, latency measured). Raw results: `/tmp/probe_final.json`.
Key inventory reference: `/home/eaguiar2015/dbpasses_ASK_2026-11-02.txt` (2026-11-02 scan — its
labels are already stale in places, e.g. AIMLAPI was "quota exceeded" then worked again).

**Never copy keys from `~/dbpasses.txt` into a repo, a commit, or a script.** The script reads env only.

## Tier 1 — local, zero key, no quota (best for cheap fan-out)

| Provider | Endpoint | Model that answered | Latency |
|---|---|---|---|
| vLLM | `http://localhost:8000/v1` | `Qwen/Qwen2.5-14B-Instruct` | ~0.5s |
| Ollama | `http://localhost:11434/v1` (OpenAI-compatible) | `gemma4:31b-cloud` | ~0.4s |
| LiteLLM | `http://localhost:4000/v1` | `paid-mode` (its routing group) | ~1.7s |
| Open WebUI | `http://localhost:3000` | UI only, no chat API | HTTP 200 |

## Tier 2 — keyless public endpoints (no account, no key)

| Provider | Endpoint | Model | Latency |
|---|---|---|---|
| Pollinations | `https://text.pollinations.ai/openai` | `openai` | ~0.25s |
| OVH AI Endpoints | `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` | `Meta-Llama-3_3-70B-Instruct` | ~0.4s |
| LLM7 (anonymous) | `https://api.llm7.io/v1` | any token, e.g. `unused`; model `codestral-latest` | ~0.7s |

Dead / closed: **Hack Club AI** (`ai.hackclub.com` → 404 on every path), **DuckDuckGo chat**
(`duckchat/v1/status` returns no `x-vqd-4`), **OpenCode Zen** (`opencode.ai/zen/v1` → HTTP 400
"Upstream request failed" for `qwen3-coder`, `code-supernova`, `grok-code`).

## Tier 3 — keyed free tiers verified working

| Provider | Endpoint | Model | Latency | Note |
|---|---|---|---|---|
| Groq | `api.groq.com/openai/v1` | `openai/gpt-oss-120b` | 0.5s | 2 keys; `/models` lists a TTS model first — pin the ID |
| Cohere | `api.cohere.ai/compatibility/v1` | `command-r7b-12-2024` | 0.2s | fastest free |
| Mistral | `api.mistral.ai/v1` | `ministral-8b-2512` | 0.3s | `mistral-small-latest` is 429; only key #1 healthy |
| Gemini | `generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.5-flash-lite` | 0.5s | `gemini-2.5-flash` hits quota → fall back per model |
| HuggingFace | `router.huggingface.co/v1` | `meta-llama/Llama-3.1-8B-Instruct:novita` | 0.7s | 3 tokens |
| DeepInfra | `api.deepinfra.com/v1/openai` | `meta-llama/Meta-Llama-3.1-8B-Instruct` | 0.6s | 2 keys |
| AIMLAPI | `api.aimlapi.com/v1` | `gpt-4o-mini` | 0.6s | was listed blocked; works again |
| OpenRouter | `openrouter.ai/api/v1` | `nvidia/nemotron-3.5-lightning:free` | 1.4s | free models 429 upstream; rotate |
| PublicAI | `api.publicai.co/v1` | `swiss-ai/apertus-8b-instruct` | 1.8s | |
| ZAI | `api.z.ai/api/paas/v4` | `glm-4.5-flash` | 6.7s | slow, free tier |

## Tier 4 — paid but working (use sparingly)

`DeepSeek` (`deepseek-chat`, 0.8s) · `Cerebras` (`gpt-oss-120b`, ~0.4s, replaces
Inception Mercury retired 2026-12-28) · `xAI Grok` (`grok-4.20-0309-non-reasoning`, 0.3s).

## Dead / blocked as of 2026-11-03

| Provider | Failure |
|---|---|
| Inception Mercury | **service sunset 2026-12-28** — provider removed from `ask.py`; use `cerebras` |
| Together | 402 no credits (both keys) |
| Cerebras | 402 / model 404 for the free tier |
| Chutes | 429, no usable key parsed |
| Fireworks | 404 model not deployed (account suspended per ASK) |
| Featherless | 403 "active plan required" |
| OFOX | 402 insufficient credits |
| BluesMind | 503 no channel / model_not_found |
| Qwen DashScope | 429 then 403 "free quota exhausted" |
| SambaNova | 401 incorrect key |
| NVIDIA NIM | **410 Gone** — account/endpoint deprovisioned |
| Hyperbolic | 404 "inference endpoint decommissioned" |
| Venice | 402 no balance |
| Kimi/Moonshot | 404 model not found |
| OpenAI | 429 "no credits remaining" |
| Xiaomi MiMo | 401 invalid token |
| Novita | 403 not enough balance |
| GitHub Models | not an OpenAI-compatible path for this token (non-JSON response) |

## Usage

```bash
python3 .claude/skills/second-opinion/scripts/ask.py "your question"
python3 .claude/skills/second-opinion/scripts/ask.py --only vllm,ollama,pollinations "free local quorum"
python3 .claude/skills/second-opinion/scripts/ask.py --context notes.md "review this plan"
```

The script fans out in parallel, skips providers with no key, discovers local model IDs via
`/models`, retries the next model ID on 400/404, and never prints a key.

## How to ask so the answers are worth having

1. One question, ≤200 words of context. Long context makes every model agree with you.
2. Ask for the disagreement — "what would you do differently", "name the failure mode".
3. Ask for a decision plus reasoning, not a survey.
4. Treat agreement as weak evidence: shared training corpora share blind spots.
5. **Verify every factual claim yourself.** In one 2026-11-03 review, Mercury claimed the job
   pipeline deduped on "title-string match" (it dedupes on canonical title + employer + req id)
   and Groq claimed LinkedIn was missing entirely (a scanner for it already existed). Both were
   wrong about the codebase; only their critique of the *method* was useful.

## Gotchas

- **Model IDs rot faster than endpoints.** Always pin two IDs per provider and fall back.
- **429 ≠ dead.** Rotate key *and* model before declaring a provider blocked; Gemini and Mistral
  both passed on the second model with the same key.
- **`/models` lies.** Groq lists a TTS model first; HuggingFace lists invalid router IDs.
- **`dbpasses.txt` labels are inconsistent** — many have no trailing colon (`HUGGING_FACE_TOKEN`,
  `OPEN ROUTER API KEY`), so a naive `label:` parser silently finds no keys. Select key-shaped
  values instead.
- Free tiers throttle per key, not per provider: keep concurrency ≤4.
