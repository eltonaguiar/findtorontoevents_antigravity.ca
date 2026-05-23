# Intelligence ranking — model grill 2026-05-19

**Harness:** `tools/model_grill_sequential.py` · prompts in `swarm_runs/_prompts/` · rubric 1–5 (repo paths, 11/11 honesty, wire_targets, depth).

## Cloud verdict table

| Rank | Model | Provider | Speed | Intel | Verdict |
|------|-------|----------|-------|-------|---------|
| 1 | **deepseek-chat** | DeepSeek | 21s | **4** | Best depth + harvest ideas; aligns paper-only |
| 1 | **pollinations** (router) | Pollinations | 20s | **4** | Surprisingly strong; some fake paths (`portfolio/`) |
| 2 | **mercury-2** | Inception | **2.4s** | 4 | Fastest paid; **REJECT** live EQUITY/ETF/BOND Y claims |
| 2 | **openrouter/free** | OpenRouter | 32s | 4 | Good router; watch false money-ready |
| 3 | **ring-2.6-1t** | OpenRouter | 19s | 3 | Fast Ring; comparable to Ling; not smarter than DeepSeek |
| 3 | **ling-2.6-1t** | OpenRouter | 6.5s | 3 | Faster than Ring; similar shallow intel |
| 3 | **grok-3-latest** | xAI | 7s | 3 | OK alignment; less detail |
| 4 | **groq llama-3.3-70b** | Groq | 1.9s | 1 | Fast but generic |
| — | cerebras / ofox / or-llama-free | — | — | 0 | FAIL this session (403/short error) |

## Ring vs Mercury vs Groq (user question)

| Metric | Ring 2.6-1t | Mercury-2 | Groq 70B |
|--------|---------------|------------|----------|
| Latency | ~19s (harvest) | **~2.4s** | ~1.9s |
| Intelligence (heuristic) | 3 | 4 (but wrong live-ready) | 1 |
| Cost | OpenRouter $ | Inception paid | Groq free tier |
| **Best value for quality** | Good free-tier speed | **Best speed/depth if you ignore false Y** | Breadth only |

**Conclusion:** Ring is **fast enough** to rival Mercury on latency for full harvest prompts, but **does not beat DeepSeek** on repo-specific intelligence. Use **Mercury for rapid drafts**, **DeepSeek for verdict-grade**, **Ring/Ling for free OpenRouter budget**.

## Local (Ollama)

| Status | Note |
|--------|------|
| **BLOCKED this session** | `ollama run` with full harvest prompt timed out (75–240s) on gemma3:4b, qwen14b, qwen2.5-coder-14b |
| **Prior mega-harvest** | qwen2.5-coder:14b, qwen3:14b, gemma3:4b OK when prompts completed |
| **Fix next** | Use Ollama HTTP API (`num_predict` cap) not CLI; fixed `14b` vs `4b` timeout bug in grill script |

## P0 engineering (unchanged across models)

1. `EMITTER_WHITELIST_FROM_REGISTRY` — Grok, DeepSeek, Pollinations agree
2. Toxic pair kill switch (`quan_engine`/CRYPTO, etc.)
3. Intraday crypto probe only new harness family

**Repro:** `swarm_runs/model-grill/20260519T081344Z/` (paid), `081835Z` (ring), `081935Z` (free)
