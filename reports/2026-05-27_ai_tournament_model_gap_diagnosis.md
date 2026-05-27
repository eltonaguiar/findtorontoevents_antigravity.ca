---
title: "Why /audit/ai-tournament.html shows only 3 models"
date: 2026-05-27
status: diagnosis complete, fix proposed
---

# AI Tournament — Model Coverage Gap

## TL;DR

The dashboard correctly shows **only 3 models** (grok3, deepseek_v4, cerebras_llama4) because **only those 3 model API keys are configured as GitHub Actions secrets**. The other 7 registered models (gpt4o_mini, cursor_agent, claude_opus, mercury, ring_261T, gemini_25_pro, mistral_large) are silently skipped during pick generation.

You have **many more keys locally** in `~/dbpasses.txt` (free + paid) — but **those keys never reach the GH Actions runner**. The pipeline only sees secrets you've explicitly set via `gh secret set`.

## Three-way mismatch

| Layer | What's there |
|---|---|
| **Config** (`config/model_persona_mapping.json`) | 10 models registered, expecting 8 distinct env vars |
| **GH Actions secrets** (`gh secret list`) | 9 API-key secrets, but only 3 match the names the workflow reads |
| **Workflow env** (`.github/workflows/ai-tournament-pipeline.yml:79-86`) | Reads 8 env vars — 4 of which have no matching secret |

## Per-model status (post-merge state)

| Model | env var workflow reads | GH secret set? | Submits? |
|---|---|---|---|
| **deepseek_v4** | DEEPSEEK_API_KEY | ✓ | ✓ daily |
| **cerebras_llama4** | CEREBRAS_API_KEY | ✓ | ✓ daily |
| **grok3** | XAI_API_KEY | ✓ | ✓ daily |
| gpt4o_mini | OPENAI_API_KEY | ✗ MISSING | ✗ |
| cursor_agent | ANTHROPIC_API_KEY | ✗ MISSING | ✗ |
| claude_opus | ANTHROPIC_API_KEY | ✗ MISSING | ✗ |
| mercury | OPENROUTER_API_KEY | ✓ | ✗ (key set but no picks — investigate) |
| ring_261T | OPENROUTER_API_KEY | ✓ | ✗ (same as mercury — same issue) |
| **gemini_25_pro** | GOOGLE_AI_API_KEY | ✗ but **GEMINI_FREE_KEY exists** | **✗ env-var mismatch** |
| mistral_large | MISTRAL_API_KEY | ✗ MISSING | ✗ |

**6 models could submit if you wire keys correctly.** Two more (mercury, ring_261T) need separate debugging (key is set but they're not producing output).

## Untapped keys you have locally (per ~/dbpasses.txt)

Not in the GH secrets list and not used by the workflow, but available locally:

- **NVIDIA** (NVIDIA Integrate API — DeepSeek v4 Pro, MiniMax, Kimi-K2.6, Nemotron, Qwen, Llama-4, Mistral, GPT-OSS)
- **GROK** (xAI key — alternative to XAI_API_KEY)
- **NSCALE_API_KEY** (Nscale)
- **SCALEWAY_ACCESS_KEY_ID / SECRET_KEY**
- **ZAI** (Z.AI GLM-4.7)
- **CEREBRAS_FREE_API_KEY** (alternate Cerebras free-tier)
- **GOOGLE GEMINI API KEY ALT2** (alternate Gemini)

You could 3-5× the model fleet with keys you already own.

## Three fixes (ordered by leverage)

### FIX 1 — Add the 3 missing API key secrets (highest leverage)
```bash
# Run on this machine (keys are in ~/dbpasses.txt):
gh secret set OPENAI_API_KEY < <(grep -A1 "^OPENAI" ~/dbpasses.txt | tail -1)
gh secret set ANTHROPIC_API_KEY < <(grep -A1 "^ANTHROPIC" ~/dbpasses.txt | tail -1)
gh secret set MISTRAL_API_KEY < <(grep -A1 "^MISTRAL API KEY" ~/dbpasses.txt | tail -1)
```
**Wakes up 4 models**: gpt4o_mini, cursor_agent, claude_opus, mistral_large.

### FIX 2 — Resolve the GEMINI env-var mismatch
The workflow at line 85 reads `GOOGLE_AI_API_KEY` but the secret is named `GEMINI_FREE_KEY`. Two options:

A. Rename the secret:
```bash
gh secret set GOOGLE_AI_API_KEY < <(gh secret list  # then re-paste GEMINI_FREE_KEY value)
```
B. Edit the workflow to read GEMINI_FREE_KEY:
```yaml
GOOGLE_AI_API_KEY: ${{ secrets.GOOGLE_AI_API_KEY || secrets.GEMINI_FREE_KEY || '' }}
```
**Wakes up gemini_25_pro.**

### FIX 3 — Investigate why mercury + ring_261T are silently no-op
OPENROUTER_API_KEY is set but neither model is producing picks. Possible causes:
- Rate-limit / paid-tier requirement on OpenRouter
- Model-ID mismatch in `populate_picks.py` (slug may have changed since 2026-05-21)
- Prompt-response parsing failure (model returns text but JSON-extractor misses it)

To diagnose: run `OPENROUTER_API_KEY=$(grep -A1 OPENROUTER ~/dbpasses.txt | tail -1) python3 tools/populate_picks.py` locally and grep for "mercury\|ring_261T" in the output.

## After FIX 1 + 2 land

You'd jump from 3 → **7 active models**. With grok3 currently at PF_CI_lo=1.30 (only statistically-profitable one), adding 4 more contributors:
- Tightens cross-model consensus signal (TICK 16's NVDA/QQQ/HG=F directional consensus would have more sources)
- Builds n faster — `min_n_to_rank=30` per model is the gate to rank-eligibility; more daily-submitters means more daily picks per model
- Provides diversification — claude_opus and gpt4o_mini are different model families than the current 3 (all open-weights / xAI), so their picks are statistically less correlated

## After FIX 3 lands (mercury + ring_261T submitting)

9 models active. Plus you'd have an extra OpenRouter slot to add anything else from that catalog (anthropic models via OR, even more diverse model families).

## Stretch — add the untapped local providers

Workflow expansion (separate PR):
- Add NVIDIA_API_KEY env var + map to nvidia_deepseek_v4 / nvidia_minimax / nvidia_kimi_k26 / nvidia_nemotron in config
- Add ZAI_API_KEY for glm_4_7
- Add SCALEWAY_ACCESS_KEY_ID / SCALEWAY_SECRET_KEY for Scaleway models
- Add NSCALE_API_KEY for Nscale models

Could easily reach **15-20 active models** within a week.

## What I will NOT do without your authorization

- I will **NOT** run `gh secret set` myself (touches your secrets store — high blast radius).
- I will **NOT** copy your keys out of `~/dbpasses.txt` (treat as sensitive credential vault).
- I can prepare a **PR for FIX 2** (workflow YAML edit only — no secrets involved) if you want that done autonomously.

## Recommended next actions

1. **You run FIX 1** — `gh secret set` for OPENAI_API_KEY, ANTHROPIC_API_KEY, MISTRAL_API_KEY. ~30 seconds.
2. **I open PR for FIX 2** — workflow YAML fallback to GEMINI_FREE_KEY. ~5 min CI.
3. **Tomorrow's ai-tournament cron** runs with 7+ models. Leaderboard populates with broader sample.
4. **In parallel: I investigate mercury/ring_261T** (FIX 3) via local pipeline run.
